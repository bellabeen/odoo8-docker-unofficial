import time
from openerp.osv import osv
from openerp.report import report_sxw
from datetime import datetime, timedelta
import fungsi_terbilang
import pytz 

class wtc_print_subsidi_leasing(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(wtc_print_subsidi_leasing, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
           'no_urut': self.no_urut,
           'belajar':self.belajar,
           'ps_finco':self.ps_finco_nya,
           'terbilang':self.terbilang,
           'waktu_lokal':self.waktu_local,
        })
        
        self.no = 0
    def no_urut(self):
        self.no+=1
        return self.no
    
    def belajar(self):
        return "yuhuhuuu"

    def terbilang(self,amount):
        hasil = fungsi_terbilang.terbilang(amount, "idr", 'id')
        return hasil

    def ps_finco_nya(self):
        val = self.pool.get('dealer.sale.order').browse(self.cr, self.uid, self.ids)
        total_ps_finco=0
        for line in val.dealer_sale_order_line:
            for disc in line.discount_line:
                total_ps_finco += disc.ps_finco
        return total_ps_finco
    
    def waktu_local(self):
        tanggal = datetime.now().strftime('%y%m%d')
        menit = datetime.now()
        user = self.pool.get('res.users').browse(self.cr, self.uid, self.uid)
        tz = pytz.timezone(user.tz) if user.tz else pytz.utc
        start = pytz.utc.localize(menit).astimezone(tz)
        start_date = start.strftime("%d-%m-%Y %H:%M")
        return start_date
    
class report_wtc_print_subsidi_leasing(osv.AbstractModel):
    _name = 'report.dealer_sale_order.wtc_report_print_subsidi_leasing'
    _inherit = 'report.abstract_report'
    _template = 'dealer_sale_order.wtc_report_print_subsidi_leasing'
    _wrapped_report_class = wtc_print_subsidi_leasing
    
   