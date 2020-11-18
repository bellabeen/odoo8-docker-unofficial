from openerp import models, fields, api
from datetime import datetime
from openerp.osv import osv
import openerp.addons.decimal_precision as dp
from openerp import workflow
class wtc_return_pembelian(models.Model):
    _name = "wtc.return.pembelian"
    _description = "Return Pembelian"
    
    @api.multi
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date()
    
    @api.model
    def _get_default_date_model(self):
        return self.env['wtc.branch'].get_default_date_model()
    
    @api.one
    @api.depends('return_pembelian_line.amount_subtotal','return_pembelian_line.tax_amount')
    def _compute_amount(self):
        total_discount = self.discount_cash+self.discount_lain+self.discount_program
        if total_discount>0:
            amount_untaxed = sum(line.amount_subtotal for line in self.return_pembelian_line)-total_discount
            amount_taxed = amount_untaxed*0.1
            self.amount_total = amount_untaxed+amount_taxed
            self.amount_tax=amount_taxed
            self.amount_untaxed = sum(line.amount_subtotal for line in self.return_pembelian_line)
        else :
            self.amount_untaxed = sum(line.amount_subtotal for line in self.return_pembelian_line)
            self.amount_tax = sum(line.tax_amount for line in self.return_pembelian_line)*0.1
            self.amount_total = self.amount_untaxed + self.amount_tax
        
    def _get_default_location(self):
        default_location_id = {}
        obj_picking_type=self.env['stock.picking.type'].search([('branch_id','=',self.branch_id.id),('code','=','incoming')])
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
    
    @api.depends('no_faktur')
    def _readonly_value_tgl_faktur(self):
        for record in self: 
            record.tgl_faktur=record.no_faktur.date_invoice 
    
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
    supplier_id = fields.Many2one('res.partner', string='Supplier', required=True, domain="['|',('principle','!=',False),('branch','!=',False)]")
    no_faktur = fields.Many2one ('account.invoice','No Invoice')
    return_pembelian_line = fields.One2many('wtc.return.pembelian.line','return_pembelian_id')
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
    
    # def create(self,cr,uid,vals,context=None):
    #     vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr,uid,vals['branch_id'],'RB')
    #     return super(wtc_return_pembelian,self).create(cr,uid,vals,context=context)
    @api.model
    def create(self,values,context=None):
        if not values['return_pembelian_line'] :
            raise osv.except_osv(('Perhatian !'), ('Detail Transaksi Retur Pembelian Belum diIsi')) 
        for x in values['return_pembelian_line'] :
            if x[2]['qty'] <= 0 :
                raise osv.except_osv(('Perhatian !'), ('Qty  Tidak Boleh Lebih Kecil atau Sama Dengan 0')) 
        values['name'] = self.env['ir.sequence'].get_per_branch(values['branch_id'], 'RB')
        
        return super(wtc_return_pembelian,self).create(values)
        
    @api.multi
    def button_dummy(self, context=None):
        return True    
    
    @api.onchange('branch_id')
    def branch_change(self):
        if self.branch_id:
            self.supplier_id=False
            self.no_faktur=False
            self.return_pembelian_line= False
    
    @api.onchange('supplier_id')
    def supplier_ochange(self):
        if self.supplier_id:
            self.no_faktur=False
            self.return_pembelian_line= False
            
    @api.onchange('division')
    def division_change(self):
        if self.division :
            self.no_faktur=False
            self.return_pembelian_line= False
            
    @api.onchange('supplier_id')
    def supplier_change(self):
        dom = {}
        invoice_ids = []
        if self.supplier_id :
            invoice=self.env['account.invoice'].search([
                                                        ('partner_id','=',self.supplier_id.id),
                                                        ('branch_id','=',self.branch_id.id),
                                                        ('division','=',self.division),
                                                        ('state','in',['open','paid']),
                                                        ('tipe','=','purchase')])
            for x in invoice :
                invoice_ids.append(x.id)
            dom['no_faktur']=[('id','in',invoice_ids)]
            self.payment_term=self.supplier_id.property_payment_term.id
        return {'domain':dom}
    
    @api.onchange('no_faktur')
    def no_faktur_change(self):
        if self.no_faktur :
            self.tgl_faktur=self.no_faktur.date_invoice
            self.return_pembelian_line= False
            
            
    @api.multi
    def _get_branch_journal_config(self,branch_id):
        result = {}
        branch_journal_id = self.env['wtc.branch.config'].search([('branch_id','=',branch_id)])
        if not branch_journal_id:
            raise osv.except_osv(('Perhatian !'), ('Jurnal Retur Pembelian cabang belum dibuat, silahkan setting dulu.'))
        branch_journal = branch_journal_id
        if not(branch_journal.wtc_retur_pembelian_journal_unit_id and branch_journal.wtc_retur_pembelian_journal_sparepart_id):
           raise osv.except_osv(('Perhatian !'), ('Jurnal Retur Pembelian belum lengkap, silahkan setting dulu.'))
        result.update({
                  'wtc_retur_pembelian_journal_unit_id':branch_journal.wtc_retur_pembelian_journal_unit_id,
                  'wtc_retur_pembelian_journal_sparepart_id':branch_journal.wtc_retur_pembelian_journal_sparepart_id,
                  })
        return result
    
    @api.multi
    def create_invoice(self):
        invoice_lines=[]
        obj_model_id = self.env['ir.model'].search([ ('model','=',self.__class__.__name__) ])
        journal_config = self._get_branch_journal_config(self.branch_id.id)  
        if self.division == 'Unit' :
            journal_id=journal_config['wtc_retur_pembelian_journal_unit_id']
        else :
            journal_id=journal_config['wtc_retur_pembelian_journal_sparepart_id']
        invoice = {
            'name':self.name,
            'origin': self.name,
            'branch_id':self.branch_id.id,
            'division':self.division,
            'partner_id':self.supplier_id.id,
            'date_invoice':self.date,
            'journal_id': journal_id.id,
            'payment_term':self.payment_term.id,
            'account_id':journal_id.default_debit_account_id.id,
            'transaction_id':self.id,
            'model_id':obj_model_id.id,
            'amount_untaxed':self.amount_untaxed,
            'amount_tax':self.amount_tax,
            'amount_total':self.amount_total,
            'type': 'out_invoice',
            'discount_cash':self.discount_cash,
            'discount_program':self.discount_program,
            'discount_lain':self.discount_lain,
            'tipe':'retur_pembelian'                                        
            }
        for line_inv in self.return_pembelian_line :
            account=self.env['product.product']._get_account_id(line_inv.product_id.id)
            if self.division == 'Unit':
                force_cogs=line_inv.lot_id.hpp
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
                'partner_id': self.supplier_id.id,
                'invoice_state': 'invoiced',
                'transaction_id': self.id,
                'model_id': obj_model_id.id,
                'origin': self.name
            }
        for line in self.return_pembelian_line :
            self.env['stock.picking'].compare_sale_stock(self.branch_id.id,self.division,line.product_id.id,line.qty)
            if self.division == 'Unit':
                undelivered_value=line.lot_id.hpp
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
                                'branch_id': line.return_pembelian_id.branch_id.id,
                                'origin': line.return_pembelian_id.name ,
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
            'name': 'Account Invoice',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': picking.id
            }
        
    
        
class wtc_return_pembelian_line(models.Model):
    _name = "wtc.return.pembelian.line"
    
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
            
    @api.depends('return_pembelian_id')     
    def _readonly_value_price(self):
        for record in self:
            if record.lot_id :
                record.division=record.return_pembelian_id.division
                obj_inv_line=self.env['account.invoice.line'].search([
                                                              ('invoice_id','=',record.return_pembelian_id.no_faktur.id),
                                                              ('product_id','=',record.product_id.id)
                                                              ])
                price=(obj_inv_line.price_subtotal/obj_inv_line.quantity)*1.1
                self.price_unit=price
            

                   
    @api.depends('return_pembelian_id')     
    def _get_division(self):
        for record in self:
            record.division=record.return_pembelian_id.division

    
    product_id = fields.Many2one('product.product','Product',required=True)
    name = fields.Char('Description',required=True,compute='_readonly_value_name')
    lot_id = fields.Many2one('stock.production.lot','Engine')
    price_unit = fields.Float('Unit Price',required=True)
    tax_id = fields.Many2many('account.tax','return_pembelian_line_tax', 'return_pembelian_id', 'tax_id', 'Taxes') 
    amount_subtotal = fields.Float(compute='_amount_line', string='Subtotal', digits_compute= dp.get_precision('Account'),store=True)
    qty = fields.Float(string='Quantity', digits= dp.get_precision('Product Unit of Measure'),required=True)
    return_pembelian_id = fields.Many2one('wtc.return.pembelian')
    untax_amount = fields.Float('Untax Amount')
    tax_amount = fields.Float(compute='_amount_line',string='Tax Amount', digits_compute= dp.get_precision('Account'),store=True)
    division = fields.Char(compute='_get_division', store=True)


    @api.onchange('product_id')
    def product_change(self):
        
        obj_consolidate=self.env['consolidate.invoice']
        if not self.return_pembelian_id.branch_id or not self.return_pembelian_id.division :
            raise osv.except_osv(('Warning'), ('Data Branch,Division Harus diIsi Terlebih Dahulu') )
        product_ids=[]
        domain={}
        lot_ids=[]
        categ_ids =self.env['product.category'].get_child_ids(self.return_pembelian_id.division)
        products=self.env['product.product'].search([('categ_id','in',categ_ids)])
        product_ids=[b.id for b in products]
        self.qty=1
        if self.return_pembelian_id.no_faktur : 
            if self.product_id :
                consolidate=obj_consolidate.search([('invoice_id','=',self.return_pembelian_id.no_faktur.id)])
                for header in consolidate :
                    for line in header.consolidate_line :
                        product_ids.append(line.product_id.id)
                        if self.return_pembelian_id.division == 'Unit':
                            obj_quant=self.env['stock.quant'].search([('lot_id','=',line.name.id),
                                                                      ('reservation_id','=',False),
                                                                      ('consolidated_date','!=',False),
                                                                      ])
                            if obj_quant and self.product_id:
                                lot=self.env['stock.production.lot'].search([
                                                                     ('id','=',obj_quant.lot_id.id),
                                                                     ('product_id','=',self.product_id.id),
                                                                     ('state','=','stock')
                                                                     ])
                                lot_ids.append(lot.id)
                                domain['lot_id']=[('id','in',lot_ids)] 
                        else :
                            obj_inv_line=self.env['account.invoice.line'].search([
                                                                      ('invoice_id','=',self.return_pembelian_id.no_faktur.id),
                                                                      ('product_id','=',self.product_id.id)
                                                                      ])
                            price=(obj_inv_line.price_subtotal/obj_inv_line.quantity)*1.1
                            self.price_unit=price
                            
        else :
            if self.product_id :
                obj_quant=self.env['stock.quant'].search([
                                          ('reservation_id','=',False),
                                          ('consolidated_date','!=',False),
                                          ('product_id','=',self.product_id.id),
                                        ])
                if obj_quant :
                    for quant in obj_quant :
                        lot=self.env['stock.production.lot'].search([
                                                         ('id','=',quant.lot_id.id),
                                                         ('product_id','=',self.product_id.id),
                                                         ('state','=','stock')
                                                         ])
                        lot_ids.append(lot.id)
                    domain['lot_id']=[('id','in',lot_ids)] 
                              
        domain['product_id']=[('id','in',product_ids)]
        self.name=self.product_id.description
        self.tax_id=self.product_id.supplier_taxes_id
        return {'domain':domain}
            
        

#     @api.onchange('product_id')
#     def product_change(self):
#         product_ids=[]
#         domain={}
#         lot_ids=[]
#         self.qty=1
#         obj_consolidate=self.env['consolidate.invoice']
#         if not self.return_pembelian_id.branch_id or not self.return_pembelian_id.division :
#             raise osv.except_osv(('Warning'), ('Data Branch,Division Harus diIsi Terlebih Dahulu') ) 
#         if self.return_pembelian_id.no_faktur :
#             consolidate=obj_consolidate.search([('invoice_id','=',self.return_pembelian_id.no_faktur.id)])
#             for header in consolidate :
#                 for line in header.consolidate_line :
#                     product_ids.append(line.product_id.id)
#                     if self.return_pembelian_id.division == 'Unit':
#                         obj_quant=self.env['stock.quant'].search([('lot_id','=',line.name.id),
#                                                                   ('reservation_id','=',False),
#                                                                   ('consolidated_date','!=',False),
#                                                                   ])
#                         if obj_quant and self.product_id:
#                             lot=self.env['stock.production.lot'].search([
#                                                                  ('id','=',obj_quant.lot_id.id),
#                                                                  ('product_id','=',self.product_id.id),
#                                                                  ('state','=','stock')
#                                                                  ])
#                             lot_ids.append(lot.id)
#                             domain['lot_id']=[('id','in',lot_ids)] 
#         else :
#             categ_ids =self.env['product.category'].get_child_ids('Unit')
#             products=self.env['product.product'].search([('categ_id','in',categ_ids)])
#             product_ids=[b.id for b in products]
#             obj_quant=self.env['stock.quant'].search([('reservation_id','=',False),
#                                                       ('consolidated_date','!=',False),
#                                                       ('product_id','in',product_ids),
#                                                     ])
#             if obj_quant :
#                 for quant in obj_quant :
#                     lot=self.env['stock.production.lot'].search([
#                                                          ('id','=',quant.lot_id.id),
#                                                          ('product_id','=',self.product_id.id),
#                                                          ('state','=','stock')
#                                                          ])
#                     lot_ids.append(lot.id)
#                 domain['lot_id']=[('id','in',lot_ids)] 
#         if self.return_pembelian_id.division == 'Sparepart' and self.product_id:
#             obj_inv_line=self.env['account.invoice.line'].search([
#                                                       ('invoice_id','=',self.return_pembelian_id.no_faktur.id),
#                                                       ('product_id','=',self.product_id.id)
#                                                       ])
#             price=(obj_inv_line.price_subtotal/obj_inv_line.quantity)*1.1
#             self.price_unit=price
# 
#             
#         domain['product_id']=[('id','in',product_ids)]
#         self.name=self.product_id.description
#         self.tax_id=self.product_id.supplier_taxes_id
#         return {'domain':domain}
        
    @api.onchange('lot_id')
    def lot_change(self):
        price=0
        if self.lot_id and self.return_pembelian_id.no_faktur:
            obj_inv_line=self.env['account.invoice.line'].search([
                                                          ('invoice_id','=',self.return_pembelian_id.no_faktur.id),
                                                          ('product_id','=',self.product_id.id)
                                                          ])
            price=(obj_inv_line.price_subtotal/obj_inv_line.quantity)*1.1
            self.price_unit=price
        else:
             self.price_unit=self.lot_id.hpp * 1.1
            
    
    @api.onchange('qty')
    def qty_change(self):
        if self.qty :
            if self.return_pembelian_id.division =='Unit' and self.qty > 1 :
                self.qty=1

        
        
    