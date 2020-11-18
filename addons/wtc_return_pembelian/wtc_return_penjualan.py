from openerp import models, fields, api
from datetime import datetime
from openerp.osv import osv
import openerp.addons.decimal_precision as dp
from openerp import workflow

class wtc_return_penjualan(models.Model):
    _name = "wtc.return.penjualan"
    _description = "Return Penjualan"
    
    @api.multi
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date()
    
    @api.model
    def _get_default_date_model(self):
        return self.env['wtc.branch'].get_default_date_model()
    
    @api.one
    @api.depends('return_penjualan_line.amount_subtotal','return_penjualan_line.tax_amount')
    def _compute_amount(self):
        total_discount = self.discount_cash+self.discount_lain+self.discount_program
        if total_discount>0:
            amount_untaxed = sum(line.amount_subtotal for line in self.return_penjualan_line)-total_discount
            amount_taxed = amount_untaxed*0.1
            self.amount_total = amount_untaxed+amount_taxed
            self.amount_tax=amount_taxed
            self.amount_untaxed = sum(line.amount_subtotal for line in self.return_penjualan_line)
        else :
            self.amount_untaxed = sum(line.amount_subtotal for line in self.return_penjualan_line)
            self.amount_tax = sum(line.tax_amount for line in self.return_penjualan_line)*0.1
            self.amount_total = self.amount_untaxed + self.amount_tax
    
    @api.depends('no_faktur')
    def _readonly_value_tgl_faktur(self):
        for record in self: 
            record.tgl_faktur=record.no_faktur.date_invoice 
            
    def _get_default_location(self):
        default_location_id = {}
        obj_picking_type=self.env['stock.picking.type'].search([('branch_id','=',self.branch_id.id),('code','=','outgoing')])
        if obj_picking_type :
            for pick_type in obj_picking_type :
                    if not pick_type.default_location_src_id.id :
                         raise osv.except_osv(('Perhatian !'), ("Location destination Belum di Setting"))
                    default_location_id.update({
                        'picking_type_id':pick_type.return_picking_type_id.id,
                        'source':pick_type.default_location_dest_id.id,
                        'destination': pick_type.default_location_src_id.id,
                    }) 
        else:
            raise osv.except_osv(('Error !'), ('Tidak ditemukan default lokasi untuk penjualan di konfigurasi cabang \'%s\'!') % (val.branch_id.name,)) 
        return default_location_id   
    

    name = fields.Char('Name')
    state = fields.Selection([
            ('draft', 'Draft'),
            ('validate', 'Validated'),
            ('waiting_for_approval','Waiting Approval'),
            ('approved', 'Approved'),
            ('posted', 'Posted'),        
            ('cancel', 'Cancelled'),
            ('reject', 'Rejected'),
            ],'state',default='draft')
    division = fields.Selection([('Unit','Unit'),('Sparepart','Sparepart')],required=True)
    branch_id = fields.Many2one('wtc.branch','Branch',required=True)
    tgl_faktur = fields.Date('Tanggal Invoice',compute='_readonly_value_tgl_faktur')
    date = fields.Date('Date',default=_get_default_date, required=True)
    payment_term = fields.Many2one('account.payment.term','Payment Term')
    customer_id = fields.Many2one('res.partner', string='Customer', required=True, domain="['|',('customer','!=',False),('branch','!=',False)]")
    no_faktur = fields.Many2one ('account.invoice','No Invoice',required=True)
    return_penjualan_line = fields.One2many('wtc.return.penjualan.line','return_penjualan_id')
    amount_untaxed = fields.Float(string='Untaxed Amount', digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_tax = fields.Float(string='Taxes', digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_amount')
    amount_total = fields.Float(string='Total', digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_amount')
    confirm_uid = fields.Many2one('res.users',string="Confirmed by")
    confirm_date = fields.Datetime('Confirmed on')
    discount_cash = fields.Float('Discount Cash')
    discount_program = fields.Float('Discount Program')
    discount_lain = fields.Float('Discount Lain')
    
    
    @api.model
    def create(self,values,context=None):
        if not values['return_penjualan_line'] :
            raise osv.except_osv(('Perhatian !'), ('Detail Transaksi Retur Penjualan Belum diIsi')) 
        for x in values['return_penjualan_line'] :
            if x[2]['qty'] <= 0 :
                 raise osv.except_osv(('Perhatian !'), ('Qty  Tidak Boleh Lebih Kecil atau Sama Dengan 0')) 
        values['name'] = self.env['ir.sequence'].get_per_branch(values['branch_id'], 'RJ')
        return_penjualans = super(wtc_return_penjualan,self).create(values)
        return return_penjualans
    
    @api.multi
    def button_dummy(self, context=None):
        return True  
    
    
    @api.multi
    def _get_branch_journal_config(self,branch_id):
        result = {}
        branch_journal_id = self.env['wtc.branch.config'].search([('branch_id','=',branch_id)])
        if not branch_journal_id:
            raise osv.except_osv(('Perhatian !'), ('Jurnal Retur Penjualan cabang belum dibuat, silahkan setting dulu.'))
        branch_journal = branch_journal_id
        if not(branch_journal.wtc_retur_penjualan_journal_unit_id and branch_journal.wtc_retur_penjualan_journal_sparepart_id):
           raise osv.except_osv(('Perhatian !'), ('Jurnal Retur Penjualan belum lengkap, silahkan setting dulu.'))
        result.update({
                  'wtc_retur_penjualan_journal_unit_id':branch_journal.wtc_retur_penjualan_journal_unit_id,
                  'wtc_retur_penjualan_journal_sparepart_id':branch_journal.wtc_retur_penjualan_journal_sparepart_id,
                  })
        return result
    
    @api.multi
    def create_invoice(self):
        invoice_lines=[]
        obj_model_id = self.env['ir.model'].search([ ('model','=',self.__class__.__name__) ])
        journal_config = self._get_branch_journal_config(self.branch_id.id)  
        if self.division == 'Unit' :
            journal_id=journal_config['wtc_retur_penjualan_journal_unit_id']
        else :
            journal_id=journal_config['wtc_retur_penjualan_journal_sparepart_id']
        invoice = {
            'name':self.name,
            'origin': self.name,
            'branch_id':self.branch_id.id,
            'division':self.division,
            'partner_id':self.customer_id.id,
            'date_invoice':self.date,
            'journal_id': journal_id.id,
            'payment_term':self.payment_term.id,
            'account_id':journal_id.default_debit_account_id.id,
            'transaction_id':self.id,
            'model_id':obj_model_id.id,
            'amount_untaxed':self.amount_untaxed,
            'amount_tax':self.amount_tax,
            'amount_total':self.amount_total,
            'type': 'out_refund',
            'discount_cash':self.discount_cash,
            'discount_program':self.discount_program,
            'discount_lain':self.discount_lain,
            'tipe':'retur_penjualan'                                        
            }
        for line_inv in self.return_penjualan_line :
            account=self.env['product.product']._get_account_id(line_inv.product_id.id)
            if self.division == 'Unit':
                force_cogs=line_inv.lot_id.hpp
                force_cogs+=line_inv.lot_id.freight_cost if line_inv.lot_id.freight_cost else 0
            else :
                price_branch = self.env['product.price.branch']._get_price(self.branch_id.warehouse_id.id,line_inv.product_id.id)    
                force_cogs=price_branch* line_inv.qty
            invoice_lines.append([0,False,{
                                'name':self.name,
                                'product_id':line_inv.product_id.id,
                                'quantity':line_inv.qty,
                                'origin':self.name,
                                'price_unit':line_inv.price_unit,
                                'invoice_line_tax_id': [(6, 0, [x.id for x in line_inv.tax_id])],
                                'account_id': account,
                                'force_cogs': force_cogs
                                 }])
        invoice['invoice_line']=invoice_lines
        create_invoice=self.env['account.invoice'].create(invoice)
        create_invoice.button_reset_taxes()  
        workflow.trg_validate(self._uid, 'account.invoice', create_invoice.id, 'invoice_open', self._cr)
        return True
    
    @api.multi
    def create_picking(self):
        stock_move=[]
        location=self._get_default_location()
        obj_model_id = self.env['ir.model'].search([ ('model','=',self.__class__.__name__) ]) 
        picking = {
                'picking_type_id': location['picking_type_id'],
                'division':self.division,
                'move_type': 'direct',
                'branch_id': self.branch_id.id,
                'partner_id': self.customer_id.id,
                'invoice_state': 'invoiced',
                'transaction_id': self.id,
                'model_id': obj_model_id.id,
                'origin': self.name
            }
        for line in self.return_penjualan_line :
            if self.division == 'Unit':
                undelivered_value = line.lot_id.hpp
                undelivered_value += line.lot_id.freight_cost if line.lot_id.freight_cost else 0
                location_id=line.lot_id.location_id.id
                price_unit=(undelivered_value*1.1)/line.qty
            else :
                price_branch = self.env['product.price.branch']._get_price(self.branch_id.warehouse_id.id,line.product_id.id)  
                undelivered_value=price_branch* line.qty
                location_id=location['source']
                price_unit=(undelivered_value*1.1)/line.qty
            stock_move.append([0,False,{
                                'name': self.name or '',
                                'product_uom':line.product_id.uom_id.id,
                                'product_uos': line.product_id.uom_id.id,
                                'picking_type_id':location['picking_type_id'], 
                                'product_id': line.product_id.id,
                                'product_uos_qty': line.qty,
                                'product_uom_qty': line.qty,
                                'state': 'draft',
                                'restrict_lot_id': line.lot_id.id,
                                'location_id': location_id,
                                'location_dest_id': location['destination'],
                                'branch_id': self.branch_id.id,
                                'origin': self.name ,
                                'price_unit': price_unit,
                                'undelivered_value':undelivered_value ,
                            }])
        picking['move_lines']=stock_move
        create_picking = self.env['stock.picking'].create(picking)
        if create_picking:
            create_picking.action_confirm()
            create_picking.action_assign()
        return True
    
    
    @api.multi
    def action_confirm(self,context=None):
        self.create_picking()
        self.create_invoice()
        self.write({'state':'posted'})
              
        
    @api.multi
    def action_view_invoice(self):
        obj_model_id = self.env['ir.model'].search([ ('model','=',self.__class__.__name__) ])
        invoice=self.env['account.invoice'].search([('transaction_id','=',self.id),('model_id','=',obj_model_id.id)])
        res = self.env['ir.model.data'].get_object_reference('account', 'invoice_form')
        
        result = {
            'name': 'Account Invoice',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'context': "{'type':'in_invoice', 'journal_type': 'purchase'}",
            'nodestroy': True,
            'target': 'current',
            'res_id': invoice.id
            }
        result['views'] = [(res and res[1] or False, 'form')]
        result['res_id'] = invoice.id
        return result
    

        
    @api.multi
    def action_view_delivery_order(self):
        obj_model_id = self.env['ir.model'].search([ ('model','=',self.__class__.__name__) ])
        picking=self.env['stock.picking'].search([('transaction_id','=',self.id),('model_id','=',obj_model_id.id)])
        return {
            'name': 'Delivery Order ',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': picking.id
            }
    
    
    @api.onchange('branch_id')
    def branch_change(self):
        if self.branch_id:
            self.customer_id=False
            self.no_faktur=False
            self.return_penjualan_line= False
    
    @api.onchange('customer_id')
    def customer_change(self):
        dom = {}
        invoice_ids = []
        self.no_faktur=False
        self.return_penjualan_line= False
        if self.customer_id :
            invoice=self.env['account.invoice'].search([
                                                        ('partner_id','=',self.customer_id.id),
                                                        ('branch_id','=',self.branch_id.id),
                                                        ('division','=',self.division),
                                                        ('state','in',['open','paid']),
                                                        ('type','=','out_invoice')])
            for x in invoice :
                invoice_ids.append(x.id)
            dom['no_faktur']=[('id','in',invoice_ids)]
            self.payment_term=self.customer_id.property_payment_term.id
        return {'domain':dom}
    
    @api.onchange('no_faktur')
    def no_faktur_change(self):
        if self.no_faktur :
            self.tgl_faktur=self.no_faktur.date_invoice
            self.return_penjualan_line= False
    

class wtc_return_penjualan_line(models.Model):
    _name = "wtc.return.penjualan.line"
    
    @api.one
    @api.depends('price_unit','tax_id','qty')
    def _amount_line(self):
        taxes = 0.0
        amount_subtotal = 0.0
        if self.tax_id :
            for detail in self.tax_id :
                tax = detail.compute_all(self.price_unit,self.qty)
                for x in tax['taxes'] :
                    taxes += x['price_unit']
                amount_subtotal += tax['total'] if tax else 0.0
            self.amount_subtotal = amount_subtotal
            self.tax_amount = taxes
        else :
            self.amount_subtotal = self.price_unit * self.qty
            

    @api.depends('product_id')
    def _readonly_value_name(self):
        for record in self:
            record.name=record.product_id.description
                   
    @api.depends('return_penjualan_id')     
    def _get_division(self):
        for record in self:
            record.division=record.return_penjualan_id.division
    
    @api.depends('return_penjualan_id')     
    def _readonly_value_price(self):
        for record in self:
            if record.lot_id :
                record.division=record.return_penjualan_id.division
                obj_inv_line=self.env['account.invoice.line'].search([
                                                              ('invoice_id','=',record.return_penjualan_id.no_faktur.id),
                                                              ('product_id','=',record.product_id.id)
                                                              ])
                price=(obj_inv_line.price_subtotal/obj_inv_line.quantity)*1.1
                self.price_unit=price
            
    product_id = fields.Many2one('product.product','Product',required=True)
    name = fields.Char('Description',required=True,compute='_readonly_value_name')
    lot_id = fields.Many2one('stock.production.lot','Engine')
    price_unit = fields.Float('Unit Price',compute='_readonly_value_price')
    tax_id = fields.Many2many('account.tax','return_penjualan_line_tax', 'return_penjualan_id', 'tax_id', 'Taxes') 
    amount_subtotal = fields.Float(compute='_amount_line', string='Subtotal', digits_compute= dp.get_precision('Account'),store=True)
    qty = fields.Float(string='Quantity', digits= dp.get_precision('Product Unit of Measure'),required=True)
    return_penjualan_id = fields.Many2one('wtc.return.penjualan')
    untax_amount = fields.Float('Untax Amount')
    tax_amount = fields.Float(compute='_amount_line',string='Tax Amount', digits_compute= dp.get_precision('Account'),store=True)
    division = fields.Char(compute='_get_division', store=True)
    
    
    @api.onchange('product_id')
    def product_change(self):
        product_ids=[]
        domain={}
        lot_ids=[]
        for inv_line in self.return_penjualan_id.no_faktur.invoice_line :
            product_ids.append(inv_line.product_id.id)
        if self.product_id :
            self.qty=1
            if  self.division == 'Unit' :
                obj_picking=self.env['stock.picking'].search([('model_id','=',self.return_penjualan_id.no_faktur.model_id.id),
                                                      ('transaction_id','=',self.return_penjualan_id.no_faktur.transaction_id),
                                                      ('division','=','Unit'),
                                                      ])
                if obj_picking:
                   for pic in obj_picking :
                        for pack in pic.pack_operation_ids :
                            lot=self.env['stock.production.lot'].search([
                                                                         ('id','=',pack.lot_id.id),
                                                                         ('product_id','=',self.product_id.id),
                                                                         ('state','=','sold')
                                                                         ])
                            lot_ids.append(lot.id)
                        domain['lot_id']=[('id','in',lot_ids)] 
            else :
                obj_inv_line=self.env['account.invoice.line'].search([
                                                          ('invoice_id','=',self.return_penjualan_id.no_faktur.id),
                                                          ('product_id','=',self.product_id.id)
                                                          ])
                price=(obj_inv_line.price_subtotal/obj_inv_line.quantity)*1.1
                self.price_unit=price 
        domain['product_id']=[('id','in',product_ids)]
        self.name=self.product_id.description
        self.tax_id=self.product_id.taxes_id
        return {'domain':domain}
    
    @api.onchange('lot_id')
    def lot_change(self):
        price=0
        if self.lot_id and self.return_penjualan_id.no_faktur:
            obj_inv_line=self.env['account.invoice.line'].search([
                                                          ('invoice_id','=',self.return_penjualan_id.no_faktur.id),
                                                          ('product_id','=',self.lot_id.product_id.id)
                                                          ])
            price=(obj_inv_line.price_subtotal/obj_inv_line.quantity)*1.1
            self.price_unit=price
            
    @api.multi
    def check_qty_sparepart_inv(self,product_id):
        obj_inv_line=self.env['account.invoice.line'].search([
                                                          ('invoice_id','=',self.return_penjualan_id.no_faktur.id),
                                                          ('product_id','=',product_id)
                                                          ])
        qty_inv=obj_inv_line.quantity
        return qty_inv
        
    
    @api.onchange('qty')
    def qty_change(self):
        if self.qty :
            if self.return_penjualan_id.division =='Unit' and self.qty > 1 :
                self.qty=1
            if self.return_penjualan_id.division =='Sparepart':
                qty_inv=self.check_qty_sparepart_inv(self.product_id.id)
                if self.qty > qty_inv :
                    raise osv.except_osv(('Perhatian !'), ('Qty lebih besar dari qty invoice'))
    

            
            
      
    
    
