import time
from datetime import datetime
from openerp.report import report_sxw
from openerp.osv import osv
from openerp import pooler
#import fungsi_terbilang
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
import pytz 
from openerp.tools.translate import _
import base64

class wtc_proses_stnk(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(wtc_proses_stnk, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'waktu_local': self.waktu_local,
            
        })
        
    def waktu_local(self):
        tanggal = datetime.now().strftime('%y%m%d')
        menit = datetime.now()
        user = self.pool.get('res.users').browse(self.cr, self.uid, self.uid)
        tz = pytz.timezone(user.tz) if user.tz else pytz.utc
        start = pytz.utc.localize(menit).astimezone(tz)
        start_date = start.strftime("%d-%m-%Y %H:%M")
        return start_date
 
report_sxw.report_sxw('report.rml.proses.stnk', 'wtc.proses.stnk', 'addons/wtc_proses_stnk/report/wtc_proses_stnk_report.rml', parser = wtc_proses_stnk, header = False)