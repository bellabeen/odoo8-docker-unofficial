from openerp.osv import fields, osv

class teds_stock_picking(osv.osv):
    _inherit = "stock.picking"

    def _create_nrfs(self, cr, uid, move_obj, context=None):
        fm_obj = self.pool.get('b2b.file.fm').search(cr, uid, [('no_mesin','=',move_obj.name)])
        self.pool.get('teds.nrfs').create(cr, uid, {
            'branch_id': move_obj.picking_id.branch_id.id,
            'lot_id': move_obj.restrict_lot_id.id,
            'tipe_nrfs': 'LKUAS',
            'origin': move_obj.picking_id.name,
            'tgl_nrfs': move_obj.picking_id._get_default_date(),
            'kapal_ekspedisi': fm_obj.nama_kapal if fm_obj else False
        }, context)