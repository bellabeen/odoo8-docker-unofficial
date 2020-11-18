from openerp.osv import osv, fields
from openerp.tools.float_utils import float_round as round

class account_invoice_line(osv.osv):
    
    _inherit = "account.invoice.line"
    
    def move_line_get(self, cr, uid, invoice_id, context=None):
        res = super(account_invoice_line,self).move_line_get(cr, uid, invoice_id, context=context)
        inv = self.pool.get('account.invoice').browse(cr, uid, invoice_id, context=context)
        
        #for dealer unit
        if inv.type in ('out_invoice','out_refund'):
            for i_line in inv.invoice_line:
                res.extend(self._wtc_anglo_saxon_sale_move_lines(cr, uid, i_line, res, context=context))
                
#         elif inv.type in ('out_invoice','out_refund') and inv.division=='Sparepart':
#             for i_line in inv.invoice_line:
#                 res.extend(self._wtc_anglo_saxon_wo_move_lines(cr, uid, i_line, res, context=context))
        
#         elif inv.type in ('in_invoice','in_refund'):
#             for i_line in inv.invoice_line:
#                 res.extend(self._anglo_saxon_purchase_move_lines(cr, uid, i_line, res, context=context))
        return res
    
    def _get_price(self, cr, uid, inv, company_currency, i_line, price_unit):
        cur_obj = self.pool.get('res.currency')
        decimal_precision = self.pool.get('decimal.precision')
        if inv.currency_id.id != company_currency:
            price = cur_obj.compute(cr, uid, company_currency, inv.currency_id.id, price_unit * i_line.quantity, context={'date': inv.date_invoice})
        else:
            price = price_unit * i_line.quantity
        return round(price, decimal_precision.precision_get(cr, uid, 'Account'))

    
    def _wtc_anglo_saxon_sale_move_lines(self, cr, uid, i_line, res, context=None):
        """Return the additional move lines for sales invoices and refunds.

        i_line: An account.invoice.line object.
        res: The move line entries produced so far by the parent move_line_get.
        """
         
        inv = i_line.invoice_id
        company_currency = inv.company_id.currency_id.id
        move_lines = []
        
        if i_line.product_id and i_line.product_id.valuation == 'real_time':
            dacc = i_line.product_id.property_stock_account_output and i_line.product_id.property_stock_account_output.id
            if not dacc:
                dacc = i_line.product_id.categ_id.property_stock_account_output_categ and i_line.product_id.categ_id.property_stock_account_output_categ.id
            # in both cases the credit account cacc will be the expense account
            # first check the product, if empty check the category
            cacc = i_line.product_id.property_account_expense and i_line.product_id.property_account_expense.id
            decimal_precision = self.pool.get('decimal.precision')
            account_prec = decimal_precision.precision_get(cr, uid, 'Account')
            
            if not cacc:
                cacc = i_line.product_id.categ_id.property_account_expense_categ and i_line.product_id.categ_id.property_account_expense_categ.id
            if dacc and cacc:
                price_unit=0
                if i_line.force_cogs :
                    price_unit = i_line.force_cogs
                    price_unit = round(price_unit,account_prec)
                else :
                    if i_line.product_id.product_tmpl_id.cost_method == 'real':
                        purchase_pricelist = i_line.invoice_id.branch_id.pricelist_unit_purchase_id.id
                        if not purchase_pricelist:
                            return []
                        price = self.pool.get('product.pricelist').price_get(cr, uid, [purchase_pricelist], i_line.product_id.id, 1,0)[purchase_pricelist]
                        price_unit =  round(price/1.1, account_prec) * i_line.quantity
                        
                    elif i_line.product_id.product_tmpl_id.cost_method == 'average' and inv.model_id.model== 'sale.order':
                        sale_order_id = self.pool.get('sale.order').search(cr, uid, [('id','=',inv.transaction_id)])
                        sale_order = self.pool.get('sale.order').browse(cr, uid, sale_order_id[0])
                        product_price_branch_obj = self.pool.get('product.price.branch')
                        
                        product_price_avg_id = product_price_branch_obj._get_price(cr, uid, sale_order.warehouse_id.id, i_line.product_id.id)
                        
                        if not product_price_avg_id:
                            return []
                        price_unit = product_price_avg_id * i_line.quantity
                        price_unit = round(price_unit,account_prec)
                        
                move_lines.append({
                        'type':'src',
                        'name': i_line.name[:64],
                        'price_unit':round(price_unit / i_line.quantity, account_prec),
                        'quantity':i_line.quantity,
                        'price':price_unit,
                        'account_id':dacc,
                        'product_id':i_line.product_id.id,
                        'uos_id':i_line.uos_id.id,
                        'account_analytic_id': False,
                        'taxes':i_line.invoice_line_tax_id,
                        'branch_id': i_line.invoice_id.branch_id.id
                        })

                move_lines.append({
                        'type':'src',
                        'name': i_line.name[:64],
                        'price_unit':round(price_unit / i_line.quantity, account_prec),
                        'quantity':i_line.quantity,
                        'price': -1 * price_unit,
                        'account_id':cacc,
                        'product_id':i_line.product_id.id,
                        'uos_id':i_line.uos_id.id,
                        'account_analytic_id': False,
                        'taxes':i_line.invoice_line_tax_id,
                        'branch_id': i_line.invoice_id.branch_id.id
                        })
                

#                 if i_line.invoice_id.tipe=='customer' or i_line.invoice_id.tipe=='finco':
#                     move_jaket = self._get_move_jaket(cr,uid,i_line.invoice_id.origin) 
#                     if move_jaket:
#                         for item in move_jaket:
#                             move_lines.append(item)
        return move_lines
    
    def _get_move_jaket(self,cr,uid,sale_order):
        res_dacc = {}
        res_cacc = {}
        barang_bonuses = {}
        nilai_promo = 0.0
        obj_so = self.pool.get('dealer.sale.order')
        so_id = obj_so.search(cr,uid,[('name','=',sale_order)])
        
        if so_id:
            for sale_order in obj_so.browse(cr,uid,so_id):
                if sale_order.dealer_sale_order_line and sale_order.dealer_sale_order_line.barang_bonus_line:
                    for barang_bonus in sale_order.dealer_sale_order_line.barang_bonus_line:
                        if not barang_bonuses.get(barang_bonus.product_subsidi_id.id,False):
                            barang_bonuses[barang_bonus.product_subsidi_id.id] = {}
                        decimal_precision = self.pool.get('decimal.precision')
                        account_prec = decimal_precision.precision_get(cr, uid, 'Account')
                        dacc = barang_bonus.product_subsidi_id.property_stock_account_output and barang_bonus.product_subsidi_id.property_stock_account_output.id
                        if not dacc:
                            dacc = barang_bonus.product_subsidi_id.categ_id.property_stock_account_output_categ and barang_bonus.product_subsidi_id.categ_id.property_stock_account_output_categ.id
                        # in both cases the credit account cacc will be the expense account
                        # first check the product, if empty check the category
                        cacc = barang_bonus.product_subsidi_id.property_account_expense and barang_bonus.product_subsidi_id.property_account_expense.id
                       
                        if not cacc:
                            cacc = barang_bonus.product_subsidi_id.categ_id.property_account_expense_categ and barang_bonus.product_subsidi_id.categ_id.property_account_expense_categ.id
                        if dacc and cacc:
                            barang_bonuses[barang_bonus.product_subsidi_id.id]['qty'] = barang_bonuses[barang_bonus.product_subsidi_id.id].get('qty',0) + barang_bonus.barang_qty
                            barang_bonuses[barang_bonus.product_subsidi_id.id]['price_barang'] = barang_bonuses[barang_bonus.product_subsidi_id.id].get('price_barang',0) + barang_bonus.price_barang
                        else:
                            raise osv.except_osv(('Perhatian!'),('Tidak Ditemukan account stock product %s!') % (barang_bonus.product_subsidi_id.name))
                    for key, value in barang_bonuses.items():
                        product_id = self.pool.get('product.product').browse(cr,uid,key)
                        res_dacc = {
                           'type':'src',
                           'name':product_id.name,
                           'price_unit':round(value['price_barang'] / value['qty'], account_prec),
                           'quantity':value['qty'],
                           'price':value['price_barang'],
                           'account_id':dacc,
                           'product_id': product_id.id,
                           'branch_id': sale_order.branch_id.id,
                          }
                        res_cacc = {
                           'type':'src',
                           'name':product_id.name,
                           'price_unit':round(value['price_barang'] / value['qty'], account_prec),
                           'quantity':value['qty'],
                           'price':-1*value['price_barang'],
                           'account_id':cacc,
                           'product_id': product_id.id,
                           'branch_id': sale_order.branch_id.id,
                          }
                
        return res_dacc,res_cacc    
    
    
    