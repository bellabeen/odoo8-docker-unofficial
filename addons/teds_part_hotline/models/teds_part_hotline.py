from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning
from datetime import date, datetime, timedelta,time

class PartHotline(models.Model):
    _name = "teds.part.hotline"
    _inherit = ['ir.needaction_mixin']

    def _get_default_branch(self):
        branch_ids = False
        branch_ids = self.env.user.branch_ids
        if branch_ids and len(branch_ids) == 1 :
            return branch_ids[0].id
        return False
   
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()
    
    def _get_default_datetime(self):
        return self.env['wtc.branch'].get_default_datetime_model()

    @api.depends('part_detail_ids.subtotal','part_detail_ids.price_tax')
    def _amount_total(self):
        for me in self:
            me.amount_untaxed = sum(line.subtotal for line in me.part_detail_ids)
            me.amount_tax = sum(line.price_tax for line in me.part_detail_ids)
            me.amount_total = me.amount_untaxed + me.amount_tax

    @api.depends('alokasi_dp_ids.amount_hl_allocation')
    def _compute_dp(self):
        for me in self:
            total = sum([x.amount_hl_allocation for x in me.alokasi_dp_ids])
            me.amount_dp = total

    @api.depends('amount_total')
    def _compute_minimal_dp(self):
        for me in self:
            minimal_dp = 0
            if int(me.amount_total) >= 0:
                minimal_dp = me.amount_total / 2
            me.minimal_dp = minimal_dp

    name = fields.Char('Name')
    branch_id = fields.Many2one('wtc.branch','Branch',default=_get_default_branch)
    division = fields.Selection([('Sparepart','Sparepart')],string='Division',default='Sparepart')
    date = fields.Date('Date',default=_get_default_date,readonly=True)
    lot_id = fields.Many2one('stock.production.lot','No Engine')
    chassis_no = fields.Char('No Chassis',related='lot_id.chassis_no',readonly=True)
    no_polisi = fields.Char('No Polisi',related='lot_id.no_polisi',readonly=True)
    customer_id = fields.Many2one('res.partner','Customer',related='lot_id.customer_id',store=True)
    jenis_po = fields.Selection([
        ('Claim C1','Claim C1'),
        ('Claim C2','Claim C2'),
        ('No Claim','No Claim')],string='Jenis PO')
    pembawa = fields.Char('Pembawa')
    no_telp = fields.Char('No Telp')
    state = fields.Selection([
        ('draft','Draft'),
        ('waiting_for_approval','Waiting Approval'),
        ('approved','Approved'),
        ('done','Done'),
        ('cancel','Cancelled')],default='draft')
    part_detail_ids = fields.One2many('teds.part.hotline.detail','hotline_id')
    part_hotline_available_ids = fields.One2many('teds.part.hotline.available','hotline_id')
    is_check_available = fields.Boolean('Check Available')
    amount_untaxed = fields.Float('Untaxed Amount',compute='_amount_total',store=True)
    amount_tax = fields.Float('Taxes',compute='_amount_total',store=True)
    amount_total = fields.Float('Total',compute='_amount_total',store=True)
    is_exception = fields.Boolean('Exceptions ?',help="Exceptions:\n a. Hotline untuk part claim C1 dan C2 tanpa DP \n b. Stok tersedia (Available))")
    alokasi_dp_ids = fields.One2many('teds.part.hotline.alokasi.dp','hotline_id')
    amount_dp = fields.Float('Amount DP',compute='_compute_dp')

    approval_ids = fields.One2many('wtc.approval.line','transaction_id',string="Table Approval",domain=[('form_id','=',_name)])
    approval_state = fields.Selection([
        ('b','Belum Request'),
        ('rf','Request For Approval'),
        ('a','Approved'),
        ('r','Reject')],'Approval State', readonly=True,default='b')
    status_po = fields.Selection([('draft','Draft'),('done','Done')],default='draft',string="Status PO")
    status_wo = fields.Selection([('draft','Draft'),('done','Done')],default='draft',string="Status WO")
    cancel_uid = fields.Many2one('res.users','Cancel by')
    cancel_date = fields.Datetime('Cancel on')
    minimal_dp = fields.Float('Minimal DP',compute='_compute_minimal_dp')
    tgl_order_po = fields.Date('Tanggal Order ke MD')

    @api.model
    def _needaction_domain_get(self):
        return [('state', '=', 'waiting_for_approval')] 

    @api.model
    def create(self,vals):
        if not vals['part_detail_ids']:
            raise Warning('Part detail tidak boleh kosong !')
        vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'HOTLINE') 
        create = super(PartHotline,self).create(vals)
        return create

    @api.multi
    def write(self,vals):
        write = super(PartHotline,self).write(vals)
        for x in self.part_detail_ids:
            if x.state == 'draft':
                super(PartHotline,self).write({'is_check_available':False})
        if self.status_po == 'done' and self.status_wo == 'done':
            super(PartHotline,self).write({'state':'done'})
        return write

    @api.multi
    def unlink(self):
        for x in self :
            if x.state != 'draft' :
                raise Warning('Transaksi yang berstatus selain Draft tidak bisa dihapus.')
        return super(PartHotline, self).unlink()

    @api.multi
    def action_reset_po(self):
        self.status_po = 'draft'
    
    @api.multi
    def action_reset_wo(self):
        vals = {'status_wo':'draft'}
        if self.state == 'done':
            vals['state'] = 'approved'
        self.write(vals)

    @api.multi
    def action_change_product(self):
        self.ensure_one()
        form_id = self.env.ref('teds_part_hotline.view_teds_part_hotline_change_product_form').id
        return {
            'name': ('Change Product'),
            'res_model': 'teds.part.hotline',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'views': [(form_id, 'form')],
            'view_mode': 'form',
            'target': 'new',
            'view_type': 'form',
            'res_id': self.id,
        }

    @api.multi
    def action_change_product_form(self):
        return True

    @api.multi
    def action_check_available_part(self):
        if not self.part_detail_ids:
            raise Warning('Part detail tidak boleh kosong !')
        
        prod_ids = {}            
        for x in self.part_detail_ids:
            x.state = 'open'
            prod_ids[x.product_id.id] = x.id

        cek_stock = """
            SELECT l.branch_id
                , l.complete_name as location
                , q.product_id
                , date_part('days', now() - q.in_date) as aging
                , (
                    sum(
                    CASE WHEN q.consolidated_date IS NOT NULL 
                    THEN q.qty ELSE 0 END
                    ) + 
                    sum(
                    CASE WHEN q.consolidated_date IS NULL 
                    THEN q.qty ELSE 0 END)
                    ) - 
                    CASE WHEN l.usage='internal' 
                    THEN COALESCE(
                        (
                            SELECT sum(product_uom_qty) 
                            FROM stock_move sm 
                            LEFT JOIN stock_picking sp ON sm.picking_id = sp.id 
                            LEFT JOIN stock_picking_type spt ON sp.picking_type_id = spt.id
                            LEFT JOIN stock_location stl ON sm.location_dest_id = stl.id 
                            WHERE spt.code in ('outgoing','interbranch_out') 
                            AND sp.branch_id=l.branch_id 
                            AND sp.state not in ('draft','cancel','done') 
                            AND sp.division = 'Sparepart' 
                            AND sm.product_id = q.product_id
                        ),0) ELSE 0 END as stock 
            FROM stock_quant q
            INNER JOIN stock_location l ON q.location_id = l.id AND l.usage = 'internal'
            LEFT JOIN product_product p ON q.product_id = p.id
            LEFT JOIN product_template t ON p.product_tmpl_id = t.id
            LEFT JOIN product_category c ON t.categ_id = c.id 
            LEFT JOIN product_category c2 ON c.parent_id = c2.id 
            WHERE (c.name = 'Sparepart' or c2.name = 'Sparepart')  and q.product_id in %s
            GROUP BY l.id,q.product_id,l.usage,q.id
        """ %(str(tuple(prod_ids.keys())).replace(',)', ')'))
        self.env.cr.execute(cek_stock)
        ress = self.env.cr.dictfetchall()

        part_hotline_available_ids = []
        if ress:
            for res in ress:
                branch_id = res.get('branch_id')
                product_id = res.get('product_id')
                qty_stock = res.get('stock')
                location = res.get('location') 
                aging = res.get('aging')
                if qty_stock > 0:
                    if prod_ids.get(product_id):
                        part_detail_obj = self.env['teds.part.hotline.detail'].search([
                            ('hotline_id','=',self.id),
                            ('product_id','=',product_id)],limit=1)
                        if part_detail_obj:
                            part_detail_obj.write({'is_available':True})

                    part_hotline_available_ids.append([0,False,{
                        'branch_id':branch_id,
                        'product_id':product_id,
                        'qty':qty_stock,
                        'name':location,
                        'aging':int(aging),
                    }])
        vals = {'is_check_available':True}
        self.part_hotline_available_ids = False
        if len(part_hotline_available_ids) > 0:
            vals['part_hotline_available_ids'] = part_hotline_available_ids
        self.write(vals)
        
    @api.multi
    def action_rfa(self):
        message = ''
        warning = {}
        if not self.part_detail_ids:
            raise Warning('Part detail tidak boleh kosong !')
        
        total = 0
        for dp in self.alokasi_dp_ids:
            if dp.amount_hl_allocation > dp.hl_id.amount_residual_currency:
                raise Warning('Nilai Alokasi tidak boleh lebih besar dari Amount Balance ! Number %s \n Nilai Amount Residual RP. %s ' %(dp.hl_id.ref,dp.hl_id.amount_residual_currency))
            
        max_qty = 1
        warning_status_dp = False
        warning_available = False

        if self.amount_dp < (self.amount_total / 2):
            warning_status_dp = True
        for x in self.part_detail_ids:
            if x.state == 'draft':
                return True
            if x.is_available:
                warning_available = True
            if x.qty > max_qty:
                max_qty = x.qty 
        
        # Status Value 0 Open , 2 SPV Part , 1 SSA 
        total_value = 0
        if self.is_exception:
            if int(max_qty) > 1 or warning_available:
                total_value = 2
            
            if warning_status_dp:
                total_value = 1

        else:
            no = 1
            if warning_available:
                message += '%s. Product %s tersedia di cabang sekitar ! \n'%(no,x.product_id.name_get().pop()[1])
                no += 1
                # raise Warning('Product %s tersedia di cabang sekitar ! \n Gunakan exceptions jika dibutuhkan'%(x.product_id.name_get().pop()[1]))
            if warning_status_dp:
                message += '%s. DP minimal harus setengah dari Amount Total ! \n'%(no)
                no += 1
                # raise Warning('DP minimal harus setengah dari Amount Total ! \n Gunakan exceptions jika dibutuhkan')
            if int(max_qty) > 1:
                message += '%s. Max qty hanya boleh 1 per product ! \n'%(no)
                no += 1
                # raise Warning('Max qty hanya boleh 1 per product ! \n Gunakan exceptions jika dibutuhkan')
        if message:
            message += 'Gunakan exceptions jika dibutuhkan'
            raise Warning('Perhatian ! \n %s'%(message))

        vals = {'state':'approved','approval_state':'a'}
        if total_value != 0:
            obj_matrix = self.env['wtc.approval.matrixbiaya']
            obj_matrix.request_by_value(self,total_value)
            vals['state'] = 'waiting_for_approval'
            vals['approval_state'] = 'rf'
        self.write(vals)

    @api.multi
    def action_approved(self):
        approval_sts = self.env['wtc.approval.matrixbiaya'].approve(self)
        if approval_sts == 1:
            self.write({'approval_state':'a','state':'approved'})
        elif approval_sts == 0:
            raise Warning('Perhatian !\n User tidak termasuk group approval')
   
        return True

    
    @api.onchange('customer_id')
    def onchange_pembawa(self):
        self.pembawa = False
        self.no_telp = False
        if self.customer_id:
            self.pembawa = self.customer_id.name
            self.no_telp = self.customer_id.mobile

    @api.multi
    def cek_po_done(self):
        status_po = self.env['teds.part.hotline.detail'].sudo().search([
            ('hotline_id','=',self.id),
            ('status_po','=','draft')])
        if not status_po:
            self.status_po = 'done'
    
    @api.multi
    def cek_wo_done(self):
        status_wo = self.env['teds.part.hotline.detail'].sudo().search([
            ('hotline_id','=',self.id),
            ('status_wo','=','draft')])
        if not status_wo:
            self.status_wo = 'done'



class PartHotlineDetail(models.Model):
    _name = "teds.part.hotline.detail"

    @api.one
    @api.depends('product_id','qty','price')
    def compute_subtotal(self):
        price_tax = 0
        price_subtotal = 0
        price = self.price * (1-(0.0) / 100.0)    
        taxes = self.tax_id.compute_all(price,self.qty,self.product_id)
        if taxes.get('taxes',False):
            price_tax = taxes.get('taxes',0)[0].get('amount',0)
            price_subtotal = taxes.get('total',0)
        self.price_tax = price_tax
        self.subtotal = price_subtotal
    
    @api.one
    @api.depends('price')
    def compute_price(self):
        self.price_show = self.price 
    
    @api.one
    @api.depends('tax_id')
    def compute_taxes(self):
        self.tax_show_id = self.tax_id


    hotline_id = fields.Many2one('teds.part.hotline','Part Hotline',ondelete='cascade')
    product_id = fields.Many2one('product.product','Product',domain=[('id','=',0)])
    name = fields.Char('Description',related="product_id.default_code",readonly=True)
    qty = fields.Float('Qty',default=1)
    qty_spl = fields.Float('Qty PO')
    qty_wo = fields.Float('Qty WO')
    price = fields.Float('Price')
    price_show = fields.Float('Price',compute='compute_price')
    tax_id = fields.Many2many('account.tax', 'part_hotline_tax', 'part_hotline_id', 'tax_id', 'Taxes')
    tax_show_id = fields.Many2many('account.tax', 'part_hotline_tax', 'part_hotline_id', 'tax_id', 'Taxes',compute='compute_taxes')
    price_tax = fields.Float('Price Tax',compute="compute_subtotal",store=True)
    subtotal = fields.Float('Subtotal',compute="compute_subtotal",store=True)
    is_available = fields.Boolean('Available') 
    state = fields.Selection([
        ('draft','Draft'),
        ('open','Open'),
        ('reserved','Reserved')],default='draft')
    status_po = fields.Selection([('draft','Draft'),('done','Done')],default='draft',string="State PO")
    status_wo = fields.Selection([('draft','Draft'),('done','Done')],default='draft',string="State WO")
    no_po = fields.Char('No Purchase Order')
    no_wo = fields.Char('No Work Order')
    tgl_po = fields.Date('Tgl Purchase Order')

    
    
    _sql_constraints = [('hotline_product_unique', 'unique(hotline_id,product_id)', 'Product tidak boleh duplicat !')]

    @api.model
    def create(self,vals):
        # if vals['state']: == 'draft':
        #     if self.hotline_id.state != 'draft':
        #         raise Warning('Error')
        create = super(PartHotlineDetail,self).create(vals)
        if create.state == 'draft':
            if create.hotline_id.state != 'draft':
                raise Warning ('Error')
        return create

    @api.onchange('product_id')
    def onchange_product(self):
        categ_ids = self.env['product.category'].sudo().get_child_ids('Sparepart')
        dom = {'product_id':[('categ_id','in',categ_ids)]}
        if self.product_id:
            pricelist = self.hotline_id.branch_id.pricelist_part_sales_id
            if self._origin:
                pricelist = self._origin.hotline_id.branch_id.pricelist_part_sales_id
            price_get = pricelist.price_get(self.product_id.id,1)
            price = price_get[pricelist.id]
            self.price = price
            self.tax_id = self.product_id.taxes_id
        return {'domain':dom}


class PartHotlineAvailable(models.Model):
    _name = "teds.part.hotline.available"

    name = fields.Char('Location')
    hotline_id = fields.Many2one('teds.part.hotline','Part Hotline',ondelete='cascade')
    branch_id = fields.Many2one('wtc.branch','Branch')
    product_id = fields.Many2one('product.product','Product')
    qty = fields.Float('Qty')
    aging = fields.Char('Aging')

class AlocationDPHotline(models.Model):
    _name = "teds.part.hotline.alokasi.dp"

    @api.depends('amount_hl_original')
    def compute_amount_origin(self):
        for me in self:
            me.amount_hl_original_show = me.amount_hl_original
    
    @api.depends('amount_hl_balance')
    def compute_amount_balance(self):
        for me in self:
            me.amount_hl_balance_show = me.amount_hl_balance


    hotline_id = fields.Many2one('teds.part.hotline',ondelete='cascade')
    hl_id = fields.Many2one('account.move.line','Hutang Lain')
    amount_hl_original = fields.Float('HL Original')
    amount_hl_balance = fields.Float('HL Balance')
    amount_hl_allocation = fields.Float('Allocation')
    amount_hl_original_show = fields.Float('Amount Original',compute='compute_amount_origin')
    amount_hl_balance_show = fields.Float('Amount Balance',compute='compute_amount_balance')

    _sql_constraints = [('hotline_hl_unique', 'unique(hotline_id,hl_id)', 'Hutang Lain tidak boleh duplicat !')]

    @api.constrains('amount_hl_allocation')
    @api.one
    def cek_amount_hl_alocation(self):
        if self.amount_hl_allocation:
            if self.amount_hl_allocation > self.hl_id.amount_residual_currency:
                raise Warning('Nilai Alokasi tidak boleh lebih besar dari Amount Balance ! Number %s \n Nilai Amount Residual RP. %s ' %(self.hl_id.ref,self.hl_id.amount_residual_currency))
            

    @api.onchange('hl_id')
    def onchange_hl(self):
        self.amount_hl_original = False
        self.amount_hl_original_show = False
        self.amount_hl_balance = False
        self.amount_hl_balance_show = False

        if self.hl_id:
            self.amount_hl_original = abs(self.hl_id.credit)
            self.amount_hl_original_show = abs(self.hl_id.credit)
            self.amount_hl_balance = abs(self.hl_id.amount_residual_currency)
            self.amount_hl_balance_show = abs(self.hl_id.amount_residual_currency)
            self.amount_hl_allocation = abs(self.hl_id.amount_residual_currency)