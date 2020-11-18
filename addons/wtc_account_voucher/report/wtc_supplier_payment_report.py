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
            'total_debit':self.total_debit,
            'total_credit':self.total_credit,
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
    
    def total_debit(self):
        object_debit = self.pool.get('account.voucher').browse(self.cr, self.uid, self.ids)
        total=0
        for i in object_debit.line_dr_ids :
            total += i.amount
        return total
    
    def total_credit(self):
        object_credit = self.pool.get('account.voucher').browse(self.cr, self.uid, self.ids)
        total=0
        for i in object_credit.line_cr_ids :
            total += i.amount
        return total

    
    
    

        
            
report_sxw.report_sxw('report.rml.supplier.payment', 'account.voucher', 'addons/account_voucher/report/wtc_supplier_payment_report.rml', parser = account_voucher, header = False)