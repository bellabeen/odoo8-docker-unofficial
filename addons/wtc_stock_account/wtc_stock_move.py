from openerp.osv import fields, osv

class wtc_stock_move(osv.osv):
    _inherit = "stock.move"

    def get_price_unit(self, cr, uid, move, context=None):
        price_unit = super(wtc_stock_move, self).get_price_unit(cr, uid, move, context=context)
        if move.purchase_line_id and move.branch_id.branch_type == 'DL':
            return 0.01
        return move.price_unit/1.1 or move.product_id.standard_price
    