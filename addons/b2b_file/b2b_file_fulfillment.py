import itertools
from lxml import etree
from datetime import datetime, timedelta
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import openerp.addons.decimal_precision as dp
from openerp.osv import osv
from openerp import workflow


class b2b_file_fulfillment(models.Model):
    _name = "b2b.file.fulfillment"
    _description = "B2B File Fulfillment"
    
    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()
    
    supplier_invoice_number = fields.Char(string='Supplier Invoice Number')
    no_invoice = fields.Char(string='Invoice')
    keterangan = fields.Char(string='Keterangan')
    invoice_id = fields.Many2one('account.invoice',string='Invoice',domain=[('type','=','in_invoice')],required=True)
    date = fields.Date(string='Date',readonly=True,default=_get_default_date)
    branch_id = fields.Many2one('wtc.branch',string='Branch',required=True,domain=[('code','=','MML')])
    division = fields.Selection([('Unit','Unit'),('Sparepart','Sparepart')],required=True,string='Division',default="Unit")
    confirm_date = fields.Datetime('Confirmed on')
    confirm_uid = fields.Many2one('res.users',string="Confirmed by")
    cancel_date = fields.Datetime('Cancelled on')
    cancel_uid = fields.Many2one('res.users',string="Cancelled by")
    state = fields.Selection([
                    ('draft', 'Draft'),                                
                    ('done', 'Done'),
                    ],string='Status',default='draft')
    
    
    def _get_journal_id(self, cr, uid, ids, branch_id,context=None):
        set_account_journal = {}
        obj_account = self.pool.get('wtc.branch.config').search(cr,uid,[('branch_id','=',branch_id),])
        jornal=self.pool.get('wtc.branch.config').browse(cr,uid,obj_account)
        journal_id=self.pool.get('wtc.branch.config').browse(cr,uid,obj_account).wtc_po_journal_unit_id.id
        account_id=self.pool.get('wtc.branch.config').browse(cr,uid,obj_account).wtc_po_journal_unit_id.default_credit_account_id.id
        set_account_journal.update({'journal_id':journal_id,'account_id': account_id, })
        return set_account_journal
    
    
    @api.multi
    def action_confirm(self):

        obj_pph=self.env['account.tax'].search([('name','ilike','PPh 22')])
        obj_branch=self.env['wtc.branch'].search([('branch_type','=','MD')], limit=1)
        obj_location=self.env['stock.picking.type'].search([('branch_id','=',obj_branch.id),('code','=','incoming')])[0]
        account_and_journal = self._get_journal_id(obj_branch.id)
        
        
        
         
        obj_inv=self.env['b2b.file.inv.header'].search([('no_faktur','=',self.invoice_id.supplier_invoice_number)])
        for line_inv in obj_inv.b2b_file_inv_line :
            obj_warna=self.env['product.attribute.value'].search([('code','=',line_inv.kode_warna)])   
            obj_product=self.env['product.product'].search([('name','=',line_inv.kode_type),('attribute_value_ids','=',obj_warna.id)])
            if not obj_product :
                obj_product=self.env['product.product'].search([('name','=',line_inv.kode_type)])
            if obj_product.property_stock_account_input :
                account_id = obj_product.property_stock_account_input.id
            elif obj_product.categ_id.property_stock_account_input_categ :
                account_id = obj_product.categ_id.property_stock_account_input_categ.id
            elif obj_product.categ_id.parent_id.property_stock_account_input_categ :
                account_id = obj_product.categ_id.parent_id.property_stock_account_input_categ.id
                          
            obj_check_inv_line=self.env['account.invoice.line'].search([
                                                                    ('invoice_id','=',self.invoice_id.id),
                                                                    ('product_id','=',obj_product.id),
                                                                    ('quantity','=',line_inv.qty),
                                                                    ])
            if not obj_check_inv_line :
                self.invoice_id.write({'state':'draft','move_id':False})
                obj_move=self.env['account.move'].search([('name','=',self.no_invoice)])
                obj_move.write({'state':'draft'})
                obj_move.unlink()
                workflow.trg_delete(self._uid, 'account.invoice', self.invoice_id.id, self._cr)
                workflow.trg_create(self._uid, 'account.invoice', self.invoice_id.id, self._cr)
                invoice_line = {
                        'name':[str(name) for id, name in obj_product.name_get()][0],
                        'product_id':obj_product.id,
                        'quantity':line_inv.qty,
                        'price_unit':(line_inv.amount+line_inv.ppn+(line_inv.discount_type_cash+line_inv.discount_other+line_inv.discount_quotation)*1.1)/line_inv.qty,
                        'invoice_id':self.invoice_id.id,
                        'invoice_line_tax_id': [(6,0,[obj_product.supplier_taxes_id.id,obj_pph.id])] ,
                        'account_id': account_id,
                        'purchase_line_id':line_inv.purchase_order_line_id,
                        'consolidated_qty':line_inv.qty,
                        #'force_cogs': force_cogs                             
                    }
                invoice_line_id=self.env['account.invoice.line'].create(invoice_line) 
            
            obj_sl_ok=self.env['b2b.file.sl'].search([('no_sipb','=',line_inv.no_sipb),
                                                           ('kode_type','=',line_inv.kode_type),
                                                           ('kode_warna','=',line_inv.kode_warna),
                                                           ('no_ship_list','=',line_inv.no_ship_list)])
              
            for sl_ok in obj_sl_ok :
                obj_sipb_lot=self.env['b2b.file.sipb'].search([('no_sipb','=',sl_ok.no_sipb),
                                                      ('kode_type','=',sl_ok.kode_type),
                                                      ('kode_warna','=',sl_ok.kode_warna),
                                                      ])
                  
                obj_fm=self.env['b2b.file.fm'].search([('no_sipb','=',sl_ok.no_sipb),
                                                      ('kode_type','=',sl_ok.kode_type),
                                                      ('kode_warna','=',sl_ok.kode_warna),
                                                      ('no_mesin','=',sl_ok.no_mesin),
                                                      ('no_rangka','=',sl_ok.no_rangka),
                                                      ])
                  
                obj_pucrhase_order=self.env['purchase.order'].search([('name','=',obj_sipb_lot.no_po_md)])
                if not obj_pucrhase_order :
                    obj_pucrhase_order=self.env['purchase.order'].search([('origin','=',obj_sipb_lot.no_po_md)])
      
                obj_check_lot=self.env['stock.production.lot'].search([
                                                                 ('name','=',sl_ok.no_mesin),
                                                                 ('chassis_no','=',sl_ok.no_rangka),
                                                                 ])
                if not obj_check_lot:
                    update_lot={
                            'chassis_no' : sl_ok.no_rangka, 
                            'name' : sl_ok.no_mesin,
                            'branch_id':obj_branch.id,
                            'division' : 'Unit',
                            'product_id':obj_product.id,
                            'supplier_id':obj_branch.default_supplier_id.id,
                            'location_id' :obj_location.default_location_src_id.id,
                            'hpp' :(line_inv.amount+(line_inv.discount_type_cash+line_inv.discount_other+line_inv.discount_quotation))/line_inv.qty,
                            'purchase_order_id' :obj_pucrhase_order and obj_pucrhase_order.id,
                            'no_sipb':sl_ok.no_sipb,
                            'no_faktur':obj_fm.no_faktur,
                            'no_ship_list':sl_ok.no_ship_list,
                            'tgl_ship_list':sl_ok.tgl_ship_list,
                            'state':'intransit'
                            }
                    update_lot_id=self.env['stock.production.lot'].create(update_lot) 
                self.write({'state':'done'}) 
                obj_inv.write({'state':'done'})                
    
    
    @api.onchange('invoice_id')
    def invoice_id_change(self):
        dom = {}
        if self.invoice_id:
           self.supplier_invoice_number=self.invoice_id.supplier_invoice_number
           self.no_invoice=self.invoice_id.number
           
           
    