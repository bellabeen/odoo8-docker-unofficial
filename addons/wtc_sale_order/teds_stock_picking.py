from openerp.osv import fields, osv

class wtc_stock_picking(osv.osv):
    _inherit = 'stock.picking'

    def _get_qty_rfa_approved(self, cr, uid, branch_id, division, product_id):
        get_qty_query = """
            SELECT COALESCE(SUM(sol.product_uom_qty),0) AS qty
            FROM sale_order_line sol
            JOIN sale_order so ON sol.order_id = so.id
            WHERE so.branch_id = %d
            AND so.division = '%s'
            AND so.state IN ('waiting_for_approval','approved')
            AND sol.product_id = %d
        """ % (branch_id, division, product_id)
        cr.execute(get_qty_query)
        ress_qty = cr.fetchone()
        return ress_qty[0]

    def compare_sale_rfa_approved_stock(self, cr, uid, branch_id, division, product_id, qty):
        """ 
            Membandingkan qty per product di sale order / mutation order MD + sale order RFA / Approved MD + confirmed sale order/mutation dengan stock RFS

            Jika qty penjumlahan tsb melebihi stock maka tidak bisa continue
        """
        if division == 'Unit':
            qty_rfa_approved = self._get_qty_rfa_approved(cr, uid, branch_id, division, product_id)
            qty_in_picking = self._get_qty_picking(cr, uid, branch_id, division, product_id)
            qty_in_lot = self._get_qty_lot(cr, uid, branch_id, product_id)
            if (qty_rfa_approved + qty_in_picking + qty) > qty_in_lot:
                raise osv.except_osv(('Perhatian!'), ("Stock product %s tidak mencukupi.\nJumlah Stock yang ada %s, Stock yang sedang dalam proses %s, Qty order %s" % (self.pool.get('product.product').browse(cr,uid,product_id)['name'], qty_in_lot, qty_rfa_approved + qty_in_picking, qty)))
        elif division == 'Sparepart':
            qty_rfa_approved = self._get_qty_rfa_approved(cr, uid, branch_id, division, product_id)
            qty_in_picking = self._get_qty_picking(cr, uid, branch_id, division, product_id)
            qty_in_quant = self._get_qty_quant(cr, uid, branch_id, product_id)
            if (qty_rfa_approved + qty_in_picking + qty) > qty_in_quant:
                raise osv.except_osv(('Perhatian!'), ("Stock product %s tidak mencukupi.\nJumlah Stock yang ada %s, Stock yang sedang dalam proses %s, Qty order %s" % (self.pool.get('product.product').browse(cr,uid,product_id)['name'], qty_in_quant, qty_rfa_approved + qty_in_picking, qty) ))
        return True