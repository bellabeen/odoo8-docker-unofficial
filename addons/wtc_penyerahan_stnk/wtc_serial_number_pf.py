import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
  
class wtc_stock_production_lot_penyerahan(osv.osv):
    _inherit = 'stock.production.lot'
    _columns = {
                'penyerahan_stnk_id' : fields.many2one('wtc.penyerahan.stnk',string="No Penyerahan STNK"),
                'penyerahan_notice_id' : fields.many2one('wtc.penyerahan.stnk',string='No Penyerahan Notice'),                
                'penyerahan_polisi_id' : fields.many2one('wtc.penyerahan.stnk',string="No Penyerahan No Polisi"),
                'penyerahan_bpkb_id' : fields.many2one('wtc.penyerahan.bpkb',string='No Penyerahan BPKB'),
                'tgl_penyerahan_stnk' : fields.date('Tgl Penyerahan STNK'),
                'tgl_penyerahan_plat' : fields.date('Tgl Penyerahan Polisi'),
                'tgl_penyerahan_bpkb' : fields.date('Tgl Penyerahan BPKB'),
                'tgl_penyerahan_notice' : fields.date('Tgl Penyerahan Notice'),
            }
