from openerp.osv import osv, fields
from openerp import SUPERUSER_ID, api

class stock_quant(osv.osv):
    _inherit = "stock.quant"
    
    def _get_stock_product_branch(self, cr, uid, warehouse_id, product_id):
        stock = 0
        quant_obj = self.pool.get('stock.quant')
        location_ids = self.pool.get('stock.location').search(cr, uid, [('warehouse_id','=', warehouse_id), ('usage', '=', 'internal')])
        if location_ids:
            quant_ids = quant_obj.search(cr, uid, [('location_id','in', location_ids),('product_id','=',product_id),('consolidated_date','!=',False)])
            location_ids = str(tuple(location_ids)).replace(',)', ')')
            query = """select sum(qty) from stock_quant where product_id=%s and location_id in %s and consolidated_date is not null""" % (product_id,location_ids)
            cr.execute (query)
            ress = cr.fetchall()
            for res in ress:
                stock = res[0]
#             if quant_ids:
#                 for quants in self.pool.get('stock.quant').browse(cr, uid, quant_ids):
#                     stock += quants.qty
        return stock

class stock_move(osv.osv):
    _inherit = "stock.move"
    
    def action_done(self, cr, uid, ids, context=None):
        self.product_price_branch_update_before_done(cr, uid, ids, context=context)
        res = super(stock_move, self).action_done(cr, uid, ids, context=context)
        return res
    
    def product_price_branch_update_before_done(self, cr, uid, ids, context=None):
        obj_product_price = self.pool.get('product.price.branch')
        product_obj = self.pool.get('product.product')
        tax_obj = self.pool.get('account.tax')
        cur_obj=self.pool.get('res.currency')
        for move in self.browse(cr, uid, ids, context=context):
            #adapt standard price on incomming moves if the product cost_method is 'average'
            if (move.location_id.usage == 'supplier' or move.location_id.usage == 'transit' or move.location_id.usage == 'inventory' or move.location_id.warehouse_id != move.location_dest_id.warehouse_id or move.picking_id.is_reverse) and (move.product_id.cost_method == 'average'):
                product = move.product_id
                cur = cur_obj.search(cr,uid,[('name','=','IDR')])
                cur = cur_obj.browse(cr, uid, cur[0])
                product_avail = self.pool.get('stock.quant')._get_stock_product_branch(cr, uid, move.location_dest_id.warehouse_id.id, move.product_id.id)
                #handle negative product available 
                product_avail = max(product_avail,0)
                # Get the standard price
                if move.location_id.usage == 'transit' or move.location_id.usage == 'internal' or move.location_id.usage == 'inventory':
                    amount_unit_source = move.price_unit/1.1
                    amount_unit = obj_product_price._get_price(cr, uid, move.location_dest_id.warehouse_id.id, move.product_id.id)
                    new_std_price = ((amount_unit * product_avail) + (amount_unit_source * move.product_qty)) / (product_avail + move.product_qty)
                    new_std_price = cur_obj.round(cr, uid, cur, new_std_price)
                    if amount_unit!=new_std_price:
                        self.update_price_branch(cr, uid, move.location_dest_id.warehouse_id.id, move.product_id.id, new_std_price)
                elif move.location_id.usage == 'supplier' and move.branch_id.branch_type=='MD':
                    if move.picking_id.partner_id.id!=move.picking_id.branch_id.default_supplier_id.id:
                        return True
                    
                    amount_unit = obj_product_price._get_price(cr, uid, move.location_dest_id.warehouse_id.id, move.product_id.id)
                    move_price = move.price_unit/1.1
                    new_std_price = ((amount_unit * product_avail) + (move_price * move.product_qty)) / (product_avail + move.product_qty)
                    new_std_price = cur_obj.round(cr, uid, cur, new_std_price)
                    if amount_unit!=new_std_price:
                        self.update_price_branch(cr, uid, move.location_dest_id.warehouse_id.id, move.product_id.id, new_std_price)
                elif move.location_id.usage == 'customer':
                    amount_unit = obj_product_price._get_price(cr, uid, move.location_dest_id.warehouse_id.id, move.product_id.id)
                    move_price = move.real_hpp
                    new_std_price = ((amount_unit * product_avail) + (move_price * move.product_qty)) / (product_avail + move.product_qty)
                    new_std_price = cur_obj.round(cr, uid, cur, new_std_price)
                    if amount_unit!=new_std_price:
                        self.update_price_branch(cr, uid, move.location_dest_id.warehouse_id.id, move.product_id.id, new_std_price)
                # Write the standard price, as SUPERUSER_ID because a warehouse manager may not have the right to write on products
                
    def update_price_branch(self,cr,uid,warehouse_id,product_id,new_std_price):
        obj_product_price = self.pool.get('product.price.branch')
        product_price_id = obj_product_price.search(cr, uid, [('warehouse_id','=',warehouse_id),('product_id','=',product_id)])
        if product_price_id:
            obj_product_price.write(cr, SUPERUSER_ID, product_price_id, {'cost': new_std_price})
        else:
            obj_product_price.create(cr, SUPERUSER_ID, {'warehouse_id': warehouse_id,
                                                    'product_id': product_id,
                                                    'cost': new_std_price
                                                    })
        return True
                
        