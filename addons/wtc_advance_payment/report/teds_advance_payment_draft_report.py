import pytz
import fungsi_terbilang
from datetime import datetime
from openerp import models, fields, api

class PrintAdvancePayment(models.AbstractModel):
    _name = "report.wtc_advance_payment.teds_advance_payment"

    def waktu_local(self):
        menit = datetime.now()
        user = self.env['res.users'].browse(self._uid)
        tz = pytz.timezone(user.tz) if user.tz else pytz.utc
        start = pytz.utc.localize(menit).astimezone(tz)
        start_date = start.strftime("%d-%m-%Y %H:%M:%S")
        return start_date

    def terbilang(self,amount):
        hasil = fungsi_terbilang.terbilang(amount, "idr", 'id')
        return hasil

    @api.model
    def render_html(self, docids, data=None):
        docs = self.env[self.env.context.get('active_model')].browse(self.env.context.get('active_ids', []))
        docargs = {
            'docs': docs,
            'data': data['form'], # data lengkap pada form aktif
            'user': data['user'], # nama user
            'tanggal': self.waktu_local,
            'terbilang': self.terbilang
        }
        return self.env['report'].render('wtc_advance_payment.teds_advance_payment', docargs)

