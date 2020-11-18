from openerp.osv import osv, fields

class wtc_stock_picking_mutation(osv.osv):
    _inherit = 'stock.picking'
    
    def transfer(self, cr, uid, picking, context=None):
        res = super(wtc_stock_picking_mutation, self).transfer(cr, uid, picking, context=context)
        for move in picking.move_lines :
            if move.product_id.categ_id.isParentName('Extras') :
                return res
            
        if picking.picking_type_id.code == 'interbranch_in' and picking.model_id.model == 'wtc.mutation.order' :
            obj_order = self.pool.get('wtc.mutation.order').browse(cr, uid, picking.transaction_id)
            qty = {}
            qty2 = {}
            qty3 = {}
            for x in picking.move_lines :
                qty[x.product_id] = qty.get(x.product_id,0) + x.product_uom_qty
                qty2[x.product_id] = qty2.get(x.product_id,0) + x.product_uom_qty
                qty3[x.product_id] = qty3.get(x.product_id,0) + x.product_uom_qty
            
            for x in obj_order.order_line :
                qty[x.product_id] = qty.get(x.product_id,0) + x.supply_qty
                x.write({'supply_qty':qty[x.product_id]})
            for x in obj_order.distribution_id.distribution_line :
                qty2[x.product_id] = qty2.get(x.product_id,0) + x.supply_qty
                x.write({'supply_qty':qty2[x.product_id]})
            for x in obj_order.distribution_id.sudo().request_id.request_line :
                qty3[x.product_id] = qty3.get(x.product_id,0) + x.supply_qty
                x.write({'supply_qty':qty3[x.product_id]})
            obj_order.is_done()
        return res
    