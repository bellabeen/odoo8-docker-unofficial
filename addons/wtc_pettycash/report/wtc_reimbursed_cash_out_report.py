import time
from openerp.report import report_sxw
from openerp.osv import osv
from openerp import pooler
import fungsi_terbilang
from datetime import datetime, timedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
import pytz 
from openerp.tools.translate import _
import base64

class wtc_reimbursed(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(wtc_reimbursed, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'no_urut': self.no_urut,
            'terbilang': self.terbilang,
            'waktu_local': self.waktu_local,
            
        })
        
        self.no = 0
    def no_urut(self):
        self.no+=1
       
        return self.no
    
    def terbilang(self,amount):
        hasil = fungsi_terbilang.terbilang(amount, "idr", 'id')
        return hasil
    
    def waktu_local(self):
        return self.pool.get('wtc.branch').get_default_date(self.cr,self.uid,self.ids).strftime("%d-%m-%Y %H:%M")





    
report_sxw.report_sxw('report.rml.wtc.reimbursed', 'wtc.reimbursed', 'addons/wtc_pettycash/report/wtc_reimbursed_cash_out_report.rml', parser = wtc_reimbursed, header = False)