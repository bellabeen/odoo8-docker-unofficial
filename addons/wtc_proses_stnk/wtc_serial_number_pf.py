import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
  
class wtc_stock_production_lot_proses_stnk(osv.osv):
    _inherit = 'stock.production.lot'
    _columns = {
                'proses_stnk_id': fields.many2one('wtc.proses.stnk',string="No Proses STNK"), 
                'tgl_proses_stnk' : fields.date('Tgl Proses STNK'),
                'penerimaan_stnk_id' : fields.many2one('wtc.penerimaan.stnk', string="No Penerimaan STNK"),
                'tgl_terima_stnk' : fields.date('Tgl Terima STNK'),
                'proses_biro_jasa_id' : fields.many2one('wtc.proses.birojasa',string="No Proses Biro Jasa"),
                'tgl_proses_birojasa' : fields.date('Tgl Proses Birojasa'),
                'no_notice_copy' : fields.char('No Notice Copy'),
                'tgl_notice_copy' : fields.date('Tgl Notice Copy'),
                'penerimaan_notice_id' : fields.many2one('wtc.penerimaan.stnk', string="No Penerimaan Notice"),
                'tgl_terima_notice' : fields.date('Tgl Terima Notice'),
                'penerimaan_no_polisi_id' : fields.many2one('wtc.penerimaan.stnk', string="No Penerimaan No Polisi"),
                'tgl_terima_no_polisi' : fields.date(' Tgl Terima No Polisi'),
                'penerimaan_bpkb_id' : fields.many2one('wtc.penerimaan.bpkb', string="No Penerimaan BPKB"),
                'tgl_terima_bpkb' : fields.date('Tgl Terima BPKB'),
                'lokasi_bpkb_id' : fields.many2one('wtc.lokasi.bpkb',string='Lokasi BPKB'),
                'no_urut_bpkb' : fields.char('No Urut'),
                'lokasi_stnk_id' : fields.many2one('wtc.lokasi.stnk',string='Lokasi STNK'),
                'inv_pajak_progressive_id' : fields.many2one('account.invoice','Invoice Pajak Progressive'),
                'inv_proses_birojasa':fields.many2one('account.invoice','Invoice Proses Biro Jasa'),
                'state_pajak_progressive' : fields.related('inv_pajak_progressive_id','state',type="char",string="State Pajak Progressive",readonly=True)
            }
