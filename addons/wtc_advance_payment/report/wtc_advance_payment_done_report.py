import time
from openerp.report import report_sxw
from openerp.osv import osv
from openerp import pooler
import fungsi_terbilang

class wtc_advance_payment(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(wtc_advance_payment, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'no_urut': self.no_urut,
            'terbilang':self.terbilang
        })
        
        self.no = 0
    def no_urut(self):
        self.no+=1
        return self.no
    
    def terbilang(self,amount):
        hasil = fungsi_terbilang.terbilang(amount, "idr", 'id')
        return hasil
    
report_sxw.report_sxw('report.rml.advance.payment.done', 'wtc.advance.payment', 'addons/wtc_advance_payment/report/wtc_advance_payment_done_report.rml', parser = wtc_advance_payment, header = False)