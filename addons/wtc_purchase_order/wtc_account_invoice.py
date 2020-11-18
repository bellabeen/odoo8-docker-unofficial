import itertools
from lxml import etree
from datetime import datetime, timedelta
from openerp import models, fields, api, _, workflow
from openerp.exceptions import except_orm, Warning, RedirectWarning
import openerp.addons.decimal_precision as dp
from openerp.osv import osv

class wtc_account_invoice(models.Model):
    _inherit = 'account.invoice'
    
    def _register_hook(self, cr):
        selection = self._columns['tipe'].selection
        if ('purchase', 'purchase') not in selection:
            self._columns['tipe'].selection.append(
                    ('purchase', 'purchase'))
        return super(wtc_account_invoice, self)._register_hook(cr)
    
    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()
    
    @api.one
    @api.depends('invoice_line.price_subtotal', 'tax_line.amount','discount_cash','discount_program','discount_lain')
    def _compute_amount(self):
        self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line) 
        self.amount_tax = sum(line.amount for line in self.tax_line)
        self.amount_total = self.amount_untaxed + self.amount_tax - self.discount_cash - self.discount_lain - self.discount_program
        
    discount_cash = fields.Float(string='Discount Cash',digits= dp.get_precision('Discount Cash'),default=0.0)
    discount_program = fields.Float(string='Discount Program',digits= dp.get_precision('Discount Cash'),default=0.0)
    discount_lain = fields.Float(string='Discount Lain',digits= dp.get_precision('Discount Cash'),default=0.0)
    
    
    def _get_branch_journal_config(self,branch_id):
        result = {}
        obj_branch_config = self.env['wtc.branch.config'].search([('branch_id','=',self.branch_id.id)])
        if not obj_branch_config:
            raise Warning( ("Konfigurasi jurnal cabang belum dibuat, silahkan setting dulu"))
        else:
            if not(obj_branch_config.wtc_po_account_discount_cash_id and obj_branch_config.wtc_po_account_discount_program_id and obj_branch_config.wtc_po_account_discount_lainnya_id and obj_branch_config.wtc_po_account_discount_all_workshop_id):
                raise Warning( ("Konfigurasi cabang jurnal Diskon belum dibuat, silahkan setting dulu"))
        result.update({
                  'wtc_po_account_discount_cash_id':obj_branch_config.wtc_po_account_discount_cash_id,
                  'wtc_po_account_discount_program_id':obj_branch_config.wtc_po_account_discount_program_id,
                  'wtc_po_account_discount_lainnya_id':obj_branch_config.wtc_po_account_discount_lainnya_id,
                  'wtc_po_account_discount_all_workshop_id':obj_branch_config.wtc_po_account_discount_all_workshop_id,
                  })
        
        return result
    
    def _get_pricelist(self):
        if self.division == 'Unit' :
            current_pricelist = self.branch_id.pricelist_unit_purchase_id.id
        elif self.division == 'Sparepart' :
            current_pricelist = self.branch_id.pricelist_part_purchase_id.id
#         elif self.division == 'Umum' :
#             current_pricelist = self.branch_id.pricelist_umum_purchase_id.id            
        else :
            current_pricelist = self.partner_id.property_product_pricelist_purchase.id
        return current_pricelist
    
    def purchase_unit(self, cr, uid, ids, contex=None):
        invoice_id = self.browse(cr, uid, ids)
        if invoice_id.division == 'Unit' and invoice_id.branch_id.default_supplier_id == invoice_id.partner_id and invoice_id.branch_id.branch_type == 'MD' and invoice_id.type == 'in_invoice':
            return True
        elif invoice_id.division == 'Unit' and invoice_id.branch_id.default_supplier_id == invoice_id.partner_id and all(line.purchase_line_id.id <> False for line in invoice_id.invoice_line) :
            return True
        return False
    
    @api.model
    def create(self,values,context=None):
	if not values.get('transaction_id'):
    	    raise osv.except_osv(('Warning'), ('You are not authorized to create invoice!'))
	return super(wtc_account_invoice,self).create(values)

    
    def action_invoice_bb_create(self, cr, uid, ids, contex=None):
        invoice_id = self.browse(cr, uid, ids)
        if invoice_id.purchase_unit() :
            if invoice_id.branch_id.blind_bonus_beli <= 0 :
                raise osv.except_osv(('Perhatian'), ('Amount Blind Bonus cabang tidak boleh 0, silahkan konfigurasi ulang'))
            
            obj_branch_config = self.pool.get('purchase.order')._get_branch_journal_config(cr, uid, invoice_id.branch_id.id)
            if not (obj_branch_config['wtc_po_journal_blind_bonus_beli_id'] or obj_branch_config['wtc_po_account_blind_bonus_beli_dr_id'].id or obj_branch_config['wtc_po_account_blind_bonus_beli_cr_id'].id):
                raise osv.except_osv(('Perhatian'), ('Account Blind Bonus Belum diisi atau belum lengkap, silahkan konfigurasi ulang'))
            
            total_qty = 0
            for line in invoice_id.invoice_line :
                total_qty += line.quantity
                
            inv_bb_line_vals = [(0, 0, {
                'name': 'Blind Bonus Beli',
                'quantity': total_qty,
                'origin': invoice_id.origin,
                'price_unit': invoice_id.branch_id.blind_bonus_beli,
                'account_id': obj_branch_config['wtc_po_account_blind_bonus_beli_cr_id'].id
                })]
            
            #inv bb perfomrnace dr
            inv_bb_line_vals.append([0,0,{
                                    'name': 'Blind Bonus Performance Dr',
                                    'quantity': total_qty,
                                    'origin': invoice_id.origin,
                                    'price_unit':  -1*invoice_id.branch_id.blind_bonus_beli_performance,
                                    'account_id': obj_branch_config['wtc_po_account_blind_bonus_performance_dr_id'].id
                                          }])
            #inv bb perfomrnace cr
            inv_bb_line_vals.append([0,0,{
                                    'name': 'Blind Bonus Performance Cr',
                                    'quantity': total_qty,
                                    'origin': invoice_id.origin,
                                    'price_unit': invoice_id.branch_id.blind_bonus_beli_performance,
                                    'account_id': obj_branch_config['wtc_po_account_blind_bonus_performance_cr_id'].id
                                          }])
            
            inv_bb_vals = {
                'name': invoice_id.origin,
                'origin': invoice_id.origin,
                'branch_id': invoice_id.branch_id.id,
                'division': invoice_id.division,
                'partner_id': invoice_id.partner_id.id,
                'date_invoice': invoice_id.date_invoice,
                'document_date': self._get_default_date(cr,uid),
                'reference_type': 'none',
                'type': 'out_invoice',
                #'payment_term':val.payment_term,
                'tipe': 'blind_bonus_beli',
                'journal_id': obj_branch_config['wtc_po_journal_blind_bonus_beli_id'].id,
                'account_id': obj_branch_config['wtc_po_account_blind_bonus_beli_dr_id'].id,
                'invoice_line': inv_bb_line_vals,
                'model_id': invoice_id.model_id.id,
                'transaction_id': invoice_id.transaction_id
                }
            
            id_inv_bb = self.create(cr, uid, inv_bb_vals)
            workflow.trg_validate(uid, 'account.invoice', id_inv_bb, 'invoice_open', cr)
            return id_inv_bb
        return False
    
    def invoice_validate(self, cr, uid, ids, context=None):
        res = super(wtc_account_invoice, self).invoice_validate(cr, uid, ids, context=context)
        invoice_id = self.browse(cr, uid, ids, context=context)
        for invoice_line in invoice_id.invoice_line :
            if invoice_line.purchase_line_id :
                purchase_line_id = invoice_line.purchase_line_id
                current_invoiced = purchase_line_id.qty_invoiced
                new_invoiced = invoice_line.quantity + current_invoiced
                if new_invoiced > purchase_line_id.product_qty :
                    raise Warning(("Quantity product '%s' melebihi quantity PO !\nQty invoice: '%s', Qty PO: '%s'" %(purchase_line_id.product_id.name, int(new_invoiced), int(purchase_line_id.product_qty))))
                elif new_invoiced < purchase_line_id.product_qty :
                    purchase_line_id.write({'qty_invoiced':new_invoiced, 'invoiced':False})
                else :
                    purchase_line_id.write({'qty_invoiced':new_invoiced, 'invoiced':True})
                    
            if invoice_line.invoice_id.branch_id.branch_type=='DL' and invoice_line.invoice_id.type=='in_invoice' and invoice_line.invoice_id.tipe=='purchase' and not invoice_line.purchase_line_id:
                raise Warning( ("Tidak ditemukan purchase order line dalam produk %s, klik regenerate invoice line untuk mengupdate data!") % invoice_line.product_id.name)
    
        #create invoice bbn
        invoice_id.action_invoice_bb_create()
        return res
    
    @api.multi
    def finalize_invoice_move_lines(self, move_lines):
        move_lines = super(wtc_account_invoice,self).finalize_invoice_move_lines(move_lines)
        if self.type=='in_invoice' and self.tipe =='purchase': ## DEALER ##
            for lines in self.invoice_line:
		
                if lines.product_id:
                    current_pricelist = self._get_pricelist()
                    if not current_pricelist:
                        raise Warning( ("Tidak ditemukan konfigurasi pricelist beli cabang sekarang, konfigurasi dulu!"))
                    
                    current_price = self.pool.get('product.pricelist').price_get(self._cr,self._uid,[current_pricelist], lines.product_id.id, 1)[current_pricelist]
                    if round(current_price,2) != round(lines.price_unit,2):
                        raise Warning( ("Harga produk tidak sesuai dengan harga di pricelist sekarang, klik Renew Price untuk memperbarui harga!"))
        
        if self.type=='in_invoice': ## DEALER & MAIN DEALER ##
            if self.discount_cash>0 or self.discount_lain>0 or self.discount_program>0:
                date = self._get_default_date().strftime('%Y-%m-%d')
                for line in move_lines :
                    if line[2]['credit'] > 0 :
                        date = line[2]['date']
                        line[2]['credit'] = self.amount_total
                        line[2]['date_maturity'] = self.date_due
                        break
                journal_config = self._get_branch_journal_config(self.branch_id.id)
                
                if self.discount_cash>0:
                    
                    move_lines.append((0,0,{
                               'name': 'Diskon Cash '+ self.name or self.number,
                               'ref' : 'Diskon Cash '+ self.name or self.number, 
                                'partner_id': self.partner_id.id,
                                'account_id': journal_config['wtc_po_account_discount_cash_id'].id if self.division=='Unit' else journal_config['wtc_po_account_discount_all_workshop_id'].id,
                                'date': date,
                                'debit': 0.0,
                                'credit': self.discount_cash,
                                'branch_id': self.branch_id.id,
                                'division': self.division,
                        }))
                    
                if self.discount_program>0:
                    move_lines.append((0,0,{
                                'name': 'Diskon Program '+ self.name or self.number,
                                'ref' : 'Diskon Program '+ self.name or self.number,
                                'partner_id': self.partner_id.id,
                                'account_id': journal_config['wtc_po_account_discount_program_id'].id if self.division=='Unit' else journal_config['wtc_po_account_discount_all_workshop_id'].id,
                                'date': date,
                                'debit': 0.0,
                                'credit': self.discount_program,
                                'branch_id': self.branch_id.id,
                                'division': self.division,
                                
                        }))
    
                    
                if self.discount_lain>0:
                    move_lines.append((0,0,{
                               'name': 'Diskon Lain '+ self.name or self.number,
                               'ref': 'Diskon Lain '+ self.name or self.number,
                                'partner_id': self.partner_id.id,
                                'account_id': journal_config['wtc_po_account_discount_lainnya_id'].id if self.division=='Unit' else journal_config['wtc_po_account_discount_all_workshop_id'].id,
                                'date': date,
                                'debit': 0.0,
                                'credit': self.discount_lain,
                                'branch_id': self.branch_id.id,
                                'division': self.division,
                        }))
        return move_lines
    
    
    @api.onchange('discount_cash','discount_program','discount_lain')
    def onchange_discount(self):
        if self.discount_cash < 0  or self.discount_lain<0 or self.discount_program<0:
            self.discount_cash = 0
            self.discount_lain = 0 
            self.discount_program = 0
            return {'warning':{'title':'Perhatian !','message':'Discount tidak boleh negatif'}}
        
    @api.multi
    def renew_price(self):
        for lines in self.invoice_line:
            if lines.product_id :
                current_pricelist = self._get_pricelist()

                if not current_pricelist:
                    raise Warning( ("Tidak ditemukan konfigurasi pricelist beli cabang sekarang, konfigurasi dulu!"))
                
                current_price = self.pool.get('product.pricelist').price_get(self._cr,self._uid,[current_pricelist], lines.product_id.id, 1)[current_pricelist]
                 
                if not current_price:
                    raise Warning( ("Tidak ditemukan harga produk %s di pricelist yg aktif!") % lines.product_id.name)
                
                lines.write({'price_unit':current_price})

        self.button_reset_taxes()
        
        return True
    
    @api.multi
    def regenerate_invoice(self):
        if not self.tipe=='purchase' and  not self.branch_id.branch_type=='DL':
            raise Warning( ("Regenerate invoice hanya bisa untuk invoice pembelian saja!"))
            
        purchase_order_id = self.env['purchase.order'].search([('id','=',self.transaction_id)]) 
        if not purchase_order_id:
            raise Warning( ("Tidak ditemukan purchase order untuk invoice ini!"))
        for lines in self.invoice_line:
            if not lines.purchase_line_id:
                purchase_line_id = self.env['purchase.order.line'].search([('order_id','=',self.transaction_id),('product_id','=',lines.product_id.id)])
                if purchase_line_id:
                    lines.write({
                                 'purchase_line_id': purchase_line_id.id,
                                 'account_id': lines.product_id.categ_id.property_stock_account_input_categ.id
                                 })

class wtc_account_invoice_line(models.Model):
    _inherit = 'account.invoice.line'
    
    @api.one
    @api.depends('price_unit', 'discount', 'invoice_line_tax_id', 'quantity',
        'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id','discount_amount')
    def _compute_price(self):
        price = self.price_unit * (1 - (self.discount or 0.0) / 100.0) - self.discount_amount or 0.0
        taxes = self.invoice_line_tax_id.compute_all(price, self.quantity, product=self.product_id, partner=self.invoice_id.partner_id)
        self.price_subtotal = taxes['total']
        if self.invoice_id:
            self.price_subtotal = self.invoice_id.currency_id.round(self.price_subtotal)
    
    discount_amount = fields.Float(string='Discount',digits= dp.get_precision('Discount'),default=0.0)
    price_unit_show = fields.Float(related='price_unit', string='Unit Price')
    quantity_show = fields.Float(related='quantity', string='Quantity')
    
    @api.onchange('discount_amount','discount')
    def onchange_discount(self):
        if self.discount_amount < 0  or self.discount<0:
            self.discount_amount = 0
            self.discount = 0 
            return {'warning':{'title':'Perhatian !','message':'Discount tidak boleh negatif'}}
    
class wtc_account_invoice_tax(models.Model):
    _inherit = "account.invoice.tax"
    
    @api.v8
    def compute(self, invoice):
        tax_grouped = super(wtc_account_invoice_tax, self).compute(invoice)
	currency = invoice.currency_id.with_context(date=invoice.date_invoice or fields.Date.context_today(invoice))
        total_discount = 0.0
        total_discount = (invoice.discount_cash + invoice.discount_program + invoice.discount_lain)

        if total_discount > 0 :
            #TODO:: UPDATE WITH PERCENT & VALUE FROM account.tax AND CONSIDER price_include FLAG
            for t in tax_grouped.values():
                account_tax = self.env['account.tax'].search([('name','=',t['name'])])
                if account_tax and account_tax.type == 'percent' :
                    t['amount'] = currency.round(t['amount']-total_discount*account_tax.amount)
                    t['tax_amount'] = currency.round(t['tax_amount']-total_discount*account_tax.amount)
                else : ## DEFAULT 10% TAX ##
                    t['amount'] = currency.round(t['amount']-total_discount*0.1)
                    t['tax_amount'] = currency.round(t['tax_amount']-total_discount*0.1)
                t['base'] = currency.round(t['base']-total_discount)
                t['base_amount'] = currency.round(t['base_amount']-total_discount)

        return tax_grouped

    
    
