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

class wtc_account_voucher(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(wtc_account_voucher, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'no_urut': self.no_urut,
            'terbilang':self.terbilang,
            'total_debit':self.total_debit,
            'total_credit':self.total_credit,
            'total_writeoff':self.total_writeoff,
            'waktu_local':self.waktu_local,
            'tgl':self.get_date,
            'usr':self.get_user,
            'terbilang': self.terbilang,
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
        object_debit = self.pool.get('wtc.account.voucher').browse(self.cr, self.uid, self.ids)
        total=0
        for i in object_debit.line_dr_ids :
            total += i.amount
        return total
    
    def total_credit(self):
        object_credit = self.pool.get('wtc.account.voucher').browse(self.cr, self.uid, self.ids)
        total=0
        for i in object_credit.line_cr_ids :
            total += i.amount
        return total
    
    def total_writeoff(self):
        object_writeoff = self.pool.get('wtc.account.voucher').browse(self.cr, self.uid, self.ids)
        total=0
        for i in object_writeoff.line_wo_ids :
            total += i.amount
        return total

    def get_date(self):
        date= self._get_default(self.cr, self.uid, date=True)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        return date

    def get_user(self):
        user = self._get_default(self.cr, self.uid, user=True).name
        return user

    def _get_default(self,cr,uid,date=False,user=False):
        if date :
            return self.pool.get('wtc.branch').get_default_date_model(self.cr, self.uid)
        else :
            return self.pool.get('res.users').browse(self.cr, self.uid, uid)
                
# report_sxw.report_sxw('report.rml.wtc.supplier.payment', 'wtc.account.voucher', 'addons/wtc_account_voucher/report/wtc_supplier_payment_report_new.rml', parser = wtc_account_voucher, header = False)
class report_wtc_supplier_payment_report(osv.AbstractModel):
    _name = 'report.wtc_account_voucher.wtc_supplier_payment_report_new'
    _inherit = 'report.abstract_report'
    _template = 'wtc_account_voucher.wtc_supplier_payment_report_new'
    _wrapped_report_class = wtc_account_voucher