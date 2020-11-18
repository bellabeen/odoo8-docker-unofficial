import time
from openerp.report import report_sxw
import time
import fungsi_terbilang

class wtc_kwitansi(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(wtc_kwitansi, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'terbilang':self.terbilang
        })
    
    def terbilang(self,amount):
        hasil = fungsi_terbilang.terbilang(amount, "idr", 'id')
        return hasil
    
report_sxw.report_sxw('report.print.kwitansi', 'account.voucher', 'addons/WTC/wtc_kwitansi/report/wtc_kwitansi_report.rml', parser = wtc_kwitansi, header = False)