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

class account_voucher(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(account_voucher, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'no_urut': self.no_urut,
            'terbilang':self.terbilang,
            'hari':self.hari,
            'pajak':self.pajak,
            'waktu_local':self.waktu_local
        
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
    
    def terbilang(self,amount):
        hasil = fungsi_terbilang.terbilang(amount, "idr", 'id')
        return hasil
    
    def hari(self):
        data = self.pool.get('account.voucher').browse(self.cr, self.uid, self.ids)
        data=abs((datetime.strptime(data.date_due,"%Y-%m-%d")- datetime.strptime(data.date,"%Y-%m-%d")).days)
        return data
    
    def pajak(self,data2):
        data2 = self.pool.get('account.voucher').browse(self.cr, self.uid, self.ids)
        data2=data2.tax_amount+data2.amount
        return data2
    
    
    

        
            
report_sxw.report_sxw('report.rml.payments.request', 'account.voucher', 'addons/account_voucher/report/wtc_payments_request_report.rml', parser = account_voucher, header = False)