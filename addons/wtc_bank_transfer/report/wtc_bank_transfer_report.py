import time
from datetime import datetime
from openerp.report import report_sxw
from openerp.osv import osv
from openerp import pooler
import fungsi_terbilang
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
import pytz 
from openerp.tools.translate import _
import base64


class bank_transfer(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(bank_transfer, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'no_urut': self.no_urut,
            'totals':self.total,
            'waktu_local':self.waktu_local,
            'tgl':self.get_date,
            'usr':self.get_user,
      
        
        })
        self.no = 0
    def no_urut(self):
        self.no+=1
        return self.no
    
    def waktu_local(self):
        tanggal = datetime.now().strftime('%y%m%d')
        menit = datetime.now()
        user = self.pool.get('res.users').browse(self.cr, self.uid, self.uid)
        tz = pytz.timezone(user.tz) if user.tz else pytz.utc
        start = pytz.utc.localize(menit).astimezone(tz)
        start_date = start.strftime("%d-%m-%Y %H:%M")
        return start_date

    def get_date(self):
        date= self._get_default(self.cr, self.uid, date=True)
        date = date.strftime("%Y-%m-%d %H:%M")
        return date

    def get_user(self):
        user = self._get_default(self.cr, self.uid, user=True).name
        return user

    def _get_default(self,cr,uid,date=False,user=False):
        if date :
            return self.pool.get('wtc.branch').get_default_date_model(self.cr, self.uid)
        else :
            return self.pool.get('res.users').browse(self.cr, self.uid, uid)
    

    def total(self):
        amount=self.pool.get('wtc.bank.transfer').browse(self.cr, self.uid, self.ids).amount_total
        totalnya=fungsi_terbilang.terbilang(amount, "idr", 'id')
        return totalnya

    
class report_bank_transfer(osv.AbstractModel):
    _name = 'report.wtc_bank_transfer.wtc_bank_transfer_report'
    _inherit = 'report.abstract_report'
    _template = 'wtc_bank_transfer.wtc_bank_transfer_report'
    _wrapped_report_class = bank_transfer