import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
  
class wtc_stock_production_lot_pengurusan_stnk_bpkb(osv.osv):
    _inherit = 'stock.production.lot'
    _columns = {
                'pengurusan_stnk_bpkb_id' : fields.many2one('wtc.pengurusan.stnk.bpkb',string='Pengurusan STNK & BPKB'),
                'tgl_pengurusan_stnk_bpkb' : fields.date('Tgl Pengurusan STNK dan BPKB'),
                'total_jasa' : fields.float('Total Jasa'),
                'inv_pengurusan_stnk_bpkb_id' : fields.many2one('account.invoice','Invoice Pengurusan STNK & BPKB'),
                'state_pengurusan_stnk' : fields.related('inv_pengurusan_stnk_bpkb_id','state',type="char",string="State Pengurusan STNK",readonly=True)
           
            }
