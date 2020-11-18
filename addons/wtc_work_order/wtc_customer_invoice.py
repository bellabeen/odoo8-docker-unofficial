import time
from datetime import datetime
from openerp.osv import fields, osv

class wtc_pengajuan_birojasa(osv.osv):
    _inherit = "account.invoice"     
    _columns = {
        'workorder_id': fields.many2one('wtc.work.order', string='No. WO'),
        'merge_inv': fields.selection([('not', 'Not Paid'), ('paid','paid')], 'Merge Invoice', readonly=True),
    }
    
    _defaults = {
                 'merge_inv':'not'
                 }
    
# class wtc_view_picking(osv.osv):
#     _inherit = "wtc.picking.slip"     
#     _columns = {
#         'workorder_id': fields.many2one('wtc.work.order', string='No. WO'),
#     }