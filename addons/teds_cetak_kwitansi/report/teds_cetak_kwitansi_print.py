import time
from openerp.osv import osv
from openerp.report import report_sxw
import fungsi_terbilang

class ListingCetakKwitansiPrint(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(ListingCetakKwitansiPrint, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'terbilang': self.terbilang          
        })
   
        
    def terbilang(self,amount):
        hasil = fungsi_terbilang.terbilang(amount, "idr", 'id')
        return hasil
    
class ListingCetakKwitansiDataPrint(osv.AbstractModel):
    _name = 'report.teds_cetak_kwitansi.teds_lisiting_cetak_kwitansi_print'
    _inherit = 'report.abstract_report'
    _template = 'teds_cetak_kwitansi.teds_lisiting_cetak_kwitansi_print'
    _wrapped_report_class = ListingCetakKwitansiPrint