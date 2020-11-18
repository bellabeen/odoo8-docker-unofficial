import time
import fungsi_terbilang
from openerp.report import report_sxw
from datetime import datetime, timedelta
from openerp.osv import osv
import pytz 


# from openerp import pooler

# from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP

# from openerp.tools.translate import _
# import base64
# from datetime import datetime

class wtc_work_inv(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(wtc_work_inv, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'no_urut': self.no_urut,
            'tgl':self.get_date,
            'usr':self.get_user,
            'invoice_id': self.invoice_id,
            'type_wo': self.type_wo,
            'waktu_local': self.waktu_local,
            'totals':self.total
            
        })

        self.no = 0


    def total(self, amount):
        # amount = self.pool.get('wtc.work.order').browse(self.cr, self.uid, self.ids).amount_total
        totalnya = fungsi_terbilang.terbilang(amount, "idr", 'id')
        return totalnya

    def no_urut(self):
        self.no+=1
  
        return self.no

    def type_wo(self):
        wo = self.pool.get('wtc.work.order').browse(self.cr, self.uid, self.ids).type_wo
        return wo
    
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
       
    def invoice_id(self):
        wo_name = self.pool.get('wtc.work.order').browse(self.cr, self.uid, self.ids).name
        invoice_id = self.pool.get('account.invoice').search(self.cr, self.uid,[('origin','=',wo_name)])
        invoice_obj = self.pool.get('account.invoice').browse(self.cr, self.uid, invoice_id)
        return invoice_obj
    
   
    
# report_sxw.report_sxw('report.rml.work.order.invoice', 'wtc.work.order', 'addons/wtc_work_order/report/wtc_work_order_invoice_report.rml', parser = wtc_work_order, header = False)
class report_wtc_work_inv(osv.AbstractModel):
    _name = 'report.wtc_work_order.wtc_work_order_invoice_report'
    _inherit = 'report.abstract_report'
    _template = 'wtc_work_order.wtc_work_order_invoice_report'
    _wrapped_report_class = wtc_work_inv

