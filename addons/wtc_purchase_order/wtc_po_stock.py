from openerp.osv import osv, fields

class wtc_po_stock(osv.osv):
    _inherit = 'stock.picking'

    def transfer(self, cr, uid, picking, context=None):
        res = super(wtc_po_stock, self).transfer(cr, uid, picking, context=context)
        if picking.picking_type_id.code == 'incoming' and picking.model_id.model == 'purchase.order' :
            obj_order = self.pool.get('purchase.order').browse(cr, uid, picking.transaction_id)
            qty = {}
            for x in picking.move_lines :
                qty[x.product_id] = qty.get(x.product_id,0) + x.product_uom_qty
            for x in obj_order.order_line :
                qty[x.product_id] = qty.get(x.product_id,0) + x.received
                x.write({'received':qty[x.product_id]})
        elif picking.picking_type_id.code == 'outgoing' and picking.model_id.model == 'purchase.order' :
            obj_order = self.pool.get('purchase.order').browse(cr, uid, picking.transaction_id)
            if obj_order.state not in ['cancel','done','close'] :
                qty = {}
                for x in picking.move_lines :
                    qty[x.product_id] = qty.get(x.product_id,0) + x.product_uom_qty
                for x in obj_order.order_line :
                    qty[x.product_id] = -(qty.get(x.product_id,0)) + x.received
                    x.write({'received':qty[x.product_id]})
        elif picking.picking_type_id.code == 'incoming' and picking.location_id.usage == 'supplier' and not picking.transaction_id :
            for move in picking.move_lines :
                if move.purchase_line_id :
                    received = move.purchase_line_id.received
                    move.purchase_line_id.received = received + move.product_uom_qty
        elif picking.picking_type_id.code == 'outgoing' and picking.location_dest_id.usage == 'supplier' and not picking.transaction_id :
            for move in picking.move_lines :
                if move.purchase_line_id :
                    received = move.purchase_line_id.received
                    move.purchase_line_id.received = received - move.product_uom_qty
        return res