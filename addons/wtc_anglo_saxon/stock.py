from openerp.osv import osv, fields
from openerp.tools.float_utils import float_round as round

class stock_quant(osv.osv):
    _inherit = "stock.quant"
    
    def _get_default_date(self,cr,uid,ids,context=None):
        return self.pool.get('wtc.branch').get_default_date(cr,uid,ids,context=context)
    
    def _get_cogs_product(self,cr,uid,product_id,invoice_id):
        price_cogs = 0
        obj_inv_line = self.pool.get('account.invoice.line')
        inv_line_id =  obj_inv_line.search(cr,uid,[('invoice_id','=',invoice_id),('product_id','=',product_id)])
        
        if not inv_line_id:
            return price_cogs
        
        for inv_line in obj_inv_line.browse(cr,uid,inv_line_id[0]):
            price_cogs = inv_line.force_cogs/inv_line.quantity
        return price_cogs
    
    def _prepare_account_move_line(self, cr, uid, move, qty, cost, credit_account_id, debit_account_id, context=None):
        res = super(stock_quant,self)._prepare_account_move_line(cr, uid, move, qty, cost, credit_account_id, debit_account_id, context=context)
        #add branch and division on stock journal
        product_price_obj = self.pool.get('product.price.branch')
        new_valuation_amount = 0.0
        real_hpp = 0.0
        for item in res:
            item[2].update({'branch_id': move.branch_id.id or move.picking_id.branch_id.id,
                            'division': move.picking_id.division,
                            'date': self._get_default_date(cr, uid, move.id),
                            })
            
        
        currency_obj = self.pool.get('res.currency')
        
 
        if move.picking_id.model_id.name == 'Return Pembelian':
            acc_debit=move.product_id.categ_id.property_stock_account_output_categ.id
            acc_kredit=move.product_id.categ_id.property_stock_valuation_account_id.id
                    
            res[0][2].update({'account_id': acc_debit})
            res[1][2].update({'account_id': acc_kredit})
            
        if move.location_dest_id.usage=='transit':
            mutation_account = move.product_id.product_tmpl_id.property_account_mutation.id or move.product_id.product_tmpl_id.categ_id.property_account_mutation_categ.id
            if not mutation_account:
                raise osv.except_osv(('Warning!'), ('No Interbranch account,\n Please configure at Product Category.'))
            res[0][2].update({'account_id': mutation_account})
            
        if move.product_id.cost_method == 'average':
            if move.location_id.usage == 'internal':
                new_valuation_amount = product_price_obj._get_price(cr, uid, move.location_dest_id.warehouse_id.id, move.product_id.id)
                move.update({'real_hpp':new_valuation_amount})
                
            elif move.location_id.usage == 'transit' or move.location_id.usage=='inventory':
                new_valuation_amount = move.price_unit/1.1
                 
            elif move.location_id.usage == 'supplier' and move.branch_id.branch_type=='MD':
                if move.picking_id.partner_id.id==move.picking_id.branch_id.default_supplier_id.id:
                    new_valuation_amount = move.price_unit/1.1
                else:
                    new_valuation_amount = 0.01
                
            elif move.location_id.usage == 'customer':
                new_valuation_amount = move.real_hpp
            new_valuation_amount = currency_obj.round(cr, uid, move.company_id.currency_id, new_valuation_amount * qty)
            res[0][2].update({'debit': new_valuation_amount > 0 and new_valuation_amount or 0,
                            'credit': new_valuation_amount < 0 and -new_valuation_amount or 0,
                            })
            res[1][2].update({'credit': new_valuation_amount > 0 and new_valuation_amount or 0,
                            'debit': new_valuation_amount < 0 and -new_valuation_amount or 0,
                            })
            valuation_amount = new_valuation_amount
                
        else:
            valuation_amount = move.product_id.cost_method == 'real' and cost or move.product_id.standard_price
            move.update({'real_hpp':valuation_amount})
            valuation_amount = currency_obj.round(cr, uid, move.company_id.currency_id, valuation_amount * qty)
        #the standard_price of the product may be in another decimal precision, or not compatible with the coinage of
        #the company currency... so we need to use round() before creating the accounting entries.
        valuation_amount = currency_obj.round(cr, uid, move.company_id.currency_id, valuation_amount)
        partner_id = (move.picking_id.partner_id and self.pool.get('res.partner')._find_accounting_partner(move.picking_id.partner_id).id) or False
        price_diff = 0.0
        
        #get force_cogs value from account invoice line, the value has been multiplied with product_qty
        cogs_inv = currency_obj.round(cr, uid, move.company_id.currency_id, move.undelivered_value * qty)
        
        if cogs_inv >0:
            if currency_obj.round(cr, uid, move.company_id.currency_id, cogs_inv) != valuation_amount:
                
                pricediff_acc = move.product_id.property_account_creditor_price_difference and move.product_id.property_account_creditor_price_difference.id
                if not pricediff_acc:
                    pricediff_acc = move.product_id.categ_id.property_account_creditor_price_difference_categ and move.product_id.categ_id.property_account_creditor_price_difference_categ.id
                
                output_acc = move.product_id.property_stock_account_output and move.product_id.property_stock_account_output_categ.id
                if not output_acc:
                    output_acc = move.product_id.categ_id.property_stock_account_output_categ and move.product_id.categ_id.property_stock_account_output_categ.id    
                
                if not (pricediff_acc and output_acc):
                    raise osv.except_osv(('Perhatian!'),('Tidak Ditemukan account price different product %s!') % (move.product_id.name))
                price_diff = round(cogs_inv - valuation_amount,2)
                if price_diff != 0:
                    debit_diff_vals = {
                        'name': move.name,
                        'product_id': move.product_id.id,
                        'quantity': qty,
                        'product_uom_id': move.product_id.uom_id.id,
                        'ref': move.picking_id and move.picking_id.name or False,
                        'date': self._get_default_date(cr, uid, move.id),
                        'partner_id': partner_id,
                        'debit': price_diff > 0 and price_diff or 0 if not move.picking_id.is_reverse else price_diff < 0 and -price_diff or 0,
                        'credit': price_diff < 0 and -price_diff or 0 if not move.picking_id.is_reverse else price_diff > 0 and price_diff or 0,
                        'account_id': output_acc,
                        'branch_id': move.branch_id.id or move.picking_id.branch_id.id,
                        'division': move.picking_id.division,
                        }
                    res.append((0,0,debit_diff_vals))
                    credit_diff_vals = {
                        'name': 'Price Different '+move.name,
                        'product_id': move.product_id.id,
                        'quantity': qty,
                        'product_uom_id': move.product_id.uom_id.id,
                        'ref': move.picking_id and move.picking_id.name or False,
                        'date': self._get_default_date(cr, uid, move.id),
                        'partner_id': partner_id,
                        'debit': price_diff < 0 and -price_diff or 0 if not move.picking_id.is_reverse else price_diff > 0 and price_diff or 0,
                        'credit': price_diff > 0 and price_diff or 0 if not move.picking_id.is_reverse else price_diff < 0 and -price_diff or 0,
                        'account_id': pricediff_acc,
                        'branch_id': move.branch_id.id or move.picking_id.branch_id.id,
                        'division': move.picking_id.division,
                        }
                    res.append((0,0,credit_diff_vals))
        
        if move.location_id.usage=='transit':
            mutation_account = move.product_id.product_tmpl_id.property_account_mutation.id or move.product_id.product_tmpl_id.categ_id.property_account_mutation_categ.id
            if not mutation_account:
                raise osv.except_osv(('Warning!'), ('No Interbranch account,\n Please configure at Product Category.'))
            res[0][2].update({'branch_id': move.location_dest_id.branch_id.id})
            res[1][2].update({'branch_id': move.location_id.sudo().branch_id.id,'account_id':mutation_account})
            interco_debit = res[0][2].copy()
            interco_credit = res[1][2].copy()
            interco_debit.update({
                            'name': 'Interco Interbranch '+move.name,
                            'debit': 0,
                            'credit': interco_debit['debit'],
                            'account_id': move.location_dest_id.branch_id.inter_company_account_id.id
                            })
            
            res.append((0,0,interco_debit))
            
            interco_credit.update({
                            'name': 'Interco Interbranch '+move.name,
                            'debit': interco_credit['credit'],
                            'credit': 0,
                            'account_id': move.location_id.sudo().branch_id.inter_company_account_id.id
                            })
            
            res.append((0,0,interco_credit))
        return res
    
