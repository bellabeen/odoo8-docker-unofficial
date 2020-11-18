from openerp import models, fields, api
from datetime import datetime,date
from datetime import datetime, timedelta,date
from openerp.exceptions import except_orm, Warning, RedirectWarning

class PricelistRequest(models.Model):
    _name = "teds.pricelist.request"

    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date() + timedelta(hours=7)
    
    @api.model
    def _get_default_datetime(self):
        return datetime.now()

    def _get_default_branch(self):
        branch_ids = False
        branch_ids = self.env.user.branch_ids
        if branch_ids and len(branch_ids) == 1 :
            return [branch_ids[0].id]
        return False    

    name = fields.Char('No Refrence')
    branch_id = fields.Many2one('wtc.branch','Branch',default=_get_default_branch)
    date = fields.Date('Date',default=_get_default_date)
    state = fields.Selection([
        ('draft','Draft'),
        ('waiting_for_approval','Waiting For Approval'),
        ('approved','Approved'),
        ('reject','Reject'),
        ('confirmed','Confirmed')],default='draft')
    detail_ids = fields.One2many('teds.pricelist.request.detail','request_id')

    # Approved
    approve_uid = fields.Many2one('res.users','Approved by')
    approve_date = fields.Datetime('Approved on')
    confirm_uid = fields.Many2one('res.users','Confirmed by')
    confirm_date = fields.Datetime('Confirmed on')
    reject_uid = fields.Many2one('res.users','Reject by')
    reject_date = fields.Datetime('Reject on')
    reject_reason = fields.Text('Reason Reject')
    

    @api.model
    def create(self,vals):
        vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'RPL')
        if not vals.get('detail_ids'):
            raise Warning('Detail tidak boleh kosong !')
        return super(PricelistRequest,self).create(vals)

    @api.multi
    def write(self,vals):
        write = super(PricelistRequest,self).write(vals)
        if not self.detail_ids:
            raise Warning('Detail tidak boleh kosong !')
        return write    

    @api.multi
    def action_rfa(self):
        if self.state != 'draft':
            raise Warning('State tidak sesuai !')
        self.state = 'waiting_for_approval'

    @api.multi
    def action_approved(self):    
        if self.state != 'waiting_for_approval':
            raise Warning('State tidak sesuai !')

        cek_group = self.env['res.users'].has_group('teds_pricelist_request.group_approved_pricelist_request_button')
        if not cek_group:
            raise Warning('User tidak termasuk dalam group !')

        self.action_confirm()


    @api.multi
    def action_reject(self):
        self.ensure_one()
        if self.state != 'waiting_for_approval':
            raise Warning('State tidak sesuai !')

        form_id = self.env.ref('teds_pricelist_request.view_teds_pricelist_request_reject_form').id
        return {
            'name': ('Reject'),
            'res_model': 'teds.pricelist.request',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'views': [(form_id, 'form')],
            'view_mode': 'form',
            'target': 'new',
            'view_type': 'form',
            'res_id': self.id,
        }

    @api.multi
    def action_reject_form(self):
        if self.state != 'waiting_for_approval':
            raise Warning('State tidak sesuai !')
        self.write({
            'state':'reject',
            'reject_uid':self._uid,
            'reject_date':self._get_default_datetime(),
        })

    @api.multi
    def action_confirm(self):
        cek_group = self.env['res.users'].has_group('teds_pricelist_request.group_confirm_pricelist_request_button')
        if not cek_group:
            raise Warning('User tidak termasuk dalam group !')
        
        if self.confirm_date:
            raise Warning('Pricelist Request sudah di confirm !')
        if not self.detail_ids:
            raise Warning('Detail tidak boleh kosong !')
        for x in self.detail_ids:
            pricelist_version = x._get_pricelist_version(x.pricelist_version_id.id)
            domain = [('price_version_id','=',pricelist_version)]
            if x.product_template_id:
                domain.append(('product_tmpl_id','=',x.product_template_id.id))
            else:
                domain.append(('product_id','=',x.product_id.id))
            pricelist_item = self.env['product.pricelist.item'].search(domain,limit=1)
            if pricelist_item:
                pricelist_item.write({
                    'price_surcharge':x.new_price,
                    'sequence':x.sequence,
                })
            else:
                vals_item = {
                    'sequence':x.sequence,
                    'base':1,
                    'price_discount':-1,
                    'price_surcharge':x.new_price,
                    'price_version_id':pricelist_version,
                }
                if x.product_template_id:
                    vals_item['product_tmpl_id'] = x.product_template_id.id
                    vals_item['name'] = x.product_template_id.name
                elif x.product_id:
                    vals_item['product_id'] = x.product_id.id
                    vals_item['name'] = x.product_id.name_get().pop()[1]
                create_item = self.env['product.pricelist.item'].create(vals_item)
        
        self.write({
            'state':'confirmed',
            'approve_uid':self._uid,
            'approve_date':self._get_default_datetime(),
            'confirm_uid':self._uid,
            'confirm_date':self._get_default_datetime(),
        })

    @api.multi
    def action_cancel_approved(self):
        if self.state not in ('waiting_for_approval','approved'):
            raise Warning('User tidak termasuk dalam group !')
        self.write({
            'state':'draft',
            'approve_date':False,
            'approve_uid':False,
        })

class PricelistRequestDetail(models.Model):
    _name = "teds.pricelist.request.detail"

    @api.depends('pricelist_id')
    def _compute_pricelist(self):
        for me in self:
            me.pricelist_show_id = me.pricelist_id
    
    @api.depends('pricelist_version_id')
    def _compute_pricelist_version(self):
        for me in self:
            me.pricelist_version_show_id = me.pricelist_version_id
    
    @api.depends('last_price')
    def _compute_last_price(self):
        for me in self:
            me.last_price_show = me.last_price
    @api.depends('last_price','new_price')
    def _compute_selsisih(self):
        for me in self:
            me.selisih = me.new_price - me.last_price

    def _domain_product(self):
        categ_ids = self.env['product.category'].get_child_ids('Unit')
        return [('categ_id','in',categ_ids)]


    request_id = fields.Many2one('teds.pricelist.request',ondelete='cascade')
    division = fields.Selection([
        ('Unit','Unit')],string="Division",default="Unit")
    type = fields.Selection([
        ('purchase','Purchase Pricelist'),
        ('sale','Sale Pricelist'),
        ('sale_bbn_hitam','Sale BBN Hitam Pricelist'),
        ('sale_bbn_merah','Sale BBN Merah Pricelist')],string="Type")
    pricelist_id = fields.Many2one('product.pricelist','Pricelist')
    pricelist_version_id = fields.Many2one('product.pricelist.version','Pricelist Version')
    pricelist_show_id = fields.Many2one('product.pricelist','Pricelist',compute="_compute_pricelist")
    pricelist_version_show_id = fields.Many2one('product.pricelist.version','Pricelist Version',compute="_compute_pricelist_version")
    product_template_id = fields.Many2one('product.template','Product Template',domain=_domain_product)
    product_id = fields.Many2one('product.product','Product',domain=_domain_product)
    sequence = fields.Integer('Sequence',default=5)
    last_price = fields.Float('Harga Lama')
    last_price_show = fields.Float('Harga Lama',compute='_compute_last_price')
    new_price = fields.Float('Harga Baru')
    selisih = fields.Float('Selisih',compute="_compute_selsisih")

    @api.model
    def create(self,vals):
        if not vals.get('product_template_id') and not vals.get('product_id'):
            raise Warning('Pilih Product or Product Template !')
        return super(PricelistRequestDetail,self).create(vals)
    
    @api.multi
    def write(self,vals):
        write = super(PricelistRequestDetail,self).write(vals)
        if not self.product_template_id and not self.product_id:
            raise Warning('Pilih Product or Product Template !')
        return write
    
    @api.onchange('division')
    def onchange_type(self):
        self.type = False
        
    @api.onchange('type','division')
    def onchange_pricelist(self):
        self.pricelist_version_id = False
        self.pricelist_id = False
        self.detail_ids = False
        if self.type and self.division:
            join_pricelist = ""
            if self.type == 'purchase' and self.division == 'Unit':
                join_pricelist = "b.pricelist_unit_purchase_id"
            elif self.type == 'purchase' and self.division == 'Sparepart':
                join_pricelist = "b.pricelist_part_purchase_id"
            elif self.type == 'sale' and self.division == 'Unit':
                join_pricelist = "b.pricelist_unit_sales_id"
            elif self.type == 'sale' and self.division == 'Sparepart':
                join_pricelist = "b.pricelist_part_sales_id"
            elif self.type == 'sale_bbn_hitam' and self.division == 'Unit':
                join_pricelist = "b.pricelist_bbn_hitam_id"
            elif self.type == 'sale_bbn_merah' and self.division == 'Unit':
                join_pricelist = "b.pricelist_bbn_merah_id"
            else:
                warning = {'title':'Perhatian !','message':'Pricelist not found in Branch Config!'}
                self.type = False
                self.division = False
                return {"warning":warning}

            query = """
                SELECT 
                pp.id as pricelist_id
                , ppv.id as pricelist_version_id
                FROM wtc_branch b
                INNER JOIN product_pricelist pp ON pp.id = %s
                INNER JOIN product_pricelist_version ppv ON ppv.pricelist_id = pp.id 
                AND ppv.active = True
                AND date_start <= now()::date
                AND date_end >= now()::date
                WHERE b.id = %d
            """%(join_pricelist,self.request_id.branch_id.id)
            self.env.cr.execute(query)
            ress = self.env.cr.fetchall() 
            if len(ress) > 1:
                warning = {'title':'Perhatian !','message':'You cannot have 2 pricelist versions that overlap!'}
                self.type = False
                self.division = False
                return {"warning":warning}
            if not ress:
                warning = {'title':'Perhatian !','message':'Pricelist %s not found in Branch Config!'%self.type}
                self.type = False
                self.division = False
                return {"warning":warning}
            self.pricelist_id = ress[0][0]
            self.pricelist_version_id = ress[0][1]

    @api.multi
    def check_price_old(self,pricelist,type,product):
        pricelist = self._get_pricelist_version(pricelist)
        domain = [('price_version_id','=',pricelist)]
        if type == 'product':
            domain.append(('product_id','=',product))
        else:
            domain.append(('product_tmpl_id','=',product))  
        
        price = self.env['product.pricelist.item'].search(domain,limit=1).price_surcharge
        return price

    def _get_pricelist_version(self,pricelist):
        pricelist_item = self.env['product.pricelist.item'].search([('price_version_id','=',pricelist)])
        if len(pricelist_item) == 1:
            if pricelist_item.base_pricelist_id:
                base_pricelist_id = pricelist_item.base_pricelist_id.id
                query = """
                    SELECT ppv.id as pricelist_version_id
                    FROM product_pricelist pp
                    INNER JOIN product_pricelist_version ppv ON ppv.pricelist_id = pp.id 
                    AND ppv.active = True
                    AND date_start <= now()::date
                    AND date_end >= now()::date
                    WHERE pp.id = %d
                """%(base_pricelist_id)
                self.env.cr.execute(query)
                ress = self.env.cr.fetchall() 
            
                if len(ress) > 1:
                    warning = {'title':'Perhatian !','message':'You cannot have 2 pricelist versions that overlap!'}
                    self.type = False
                    self.division = False
                    return {"warning":warning}
                if not ress:
                    warning = {'title':'Perhatian !','message':'Pricelist %s not found in Branch Config!'%self.type}
                    self.type = False
                    self.division = False
                    return {"warning":warning}
                pricelist = ress[0][0]
        return pricelist

    @api.onchange('sequence')
    def onchange_sequence(self):
        if not self.request_id.branch_id:
            raise Warning('Silahkan isi data Branch terlebih dahulu !')
    
    @api.onchange('product_template_id')
    def onchange_product(self):
        self.product_id =  False
        self.last_price = False
        if self.product_template_id:
            price = self.check_price_old(self.pricelist_version_id.id,'template',self.product_template_id.id)
            self.last_price = price
    
    @api.onchange('product_id')
    def onchange_product_template(self):
        self.product_template_id =  False
        self.last_price = False
        if self.product_id:
            price = self.check_price_old(self.pricelist_version_id.id,'product',self.product_id.id)
            self.last_price = price



