import time
import pytz 
from openerp.report import report_sxw
from openerp.osv import osv
from datetime import datetime, timedelta
from openerp import pooler
import fungsi_terbilang





class wtc_settlement(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(wtc_settlement, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'no_urut': self.no_urut,
            'terbilang':self.terbilang,
            'waktu_local': self.waktu_local,
            'amount_total':self.amount_tot_nya,
        })
        
        self.no = 0
    def no_urut(self):
        self.no+=1
        return self.no
    
    def terbilang(self,amount):
        hasil = fungsi_terbilang.terbilang(amount, "idr", 'id')
        return hasil


    def amount_tot_nya(self):
        val = self.pool.get('wtc.settlement').browse(self.cr, self.uid, self.ids)
        total_amount=0
        for line in val.settlement_line:
            for disc in line.settlement_id:
                total_amount += disc.amount_total
        return total_amount


    def waktu_local(self):
        tanggal = datetime.now().strftime('%y%m%d')
        menit = datetime.now()
        user = self.pool.get('res.users').browse(self.cr, self.uid, self.uid)
        tz = pytz.timezone(user.tz) if user.tz else pytz.utc
        start = pytz.utc.localize(menit).astimezone(tz)
        start_date = start.strftime("%d-%m-%Y %H:%M")
        return start_date


# report_sxw.report_sxw('report.rml.settlement.done', 'wtc.settlement', 'addons/wtc_advance_payment/report/wtc_settlement_done_report.rml', parser = wtc_settlement, header = False)
class report_advance_payment_done(osv.AbstractModel):
    _name = 'report.wtc_advance_payment.settlement_done'
    _inherit = 'report.abstract_report'
    _template = 'wtc_advance_payment.settlement_done'
    _wrapped_report_class = wtc_settlement
