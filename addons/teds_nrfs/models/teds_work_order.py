from datetime import date, datetime, timedelta
from openerp.osv import fields, osv

class teds_work_order(osv.osv):
    _inherit = "wtc.work.order"

    _columns = {
        'nrfs_id':fields.many2one('teds.nrfs','No Case NRFS'),
    }

    def _nrfs_update_tgl_selesai(self, cr, uid, ids, wo_obj):
        if wo_obj.nrfs_id:
            wo_obj.nrfs_id.write({'tgl_selesai_actual': date.today(), 'state': 'done'})