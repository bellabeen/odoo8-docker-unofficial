import pytz
import fungsi_terbilang
from datetime import datetime
from openerp import models, fields, api

class PrintPaymentRequest(models.AbstractModel):
    _name = 'report.wtc_dn_nc.teds_payment_request'

    def waktu_local(self):
        menit = datetime.now()
        user = self.env['res.users'].browse(self._uid)
        tz = pytz.timezone(user.tz) if user.tz else pytz.utc
        start = pytz.utc.localize(menit).astimezone(tz)
        start_date = start.strftime("%d-%m-%Y %H:%M")
        return start_date

    def hari_tempo(self):
        nc_id = self.env.context.get('active_id', 0)
        data = self.env['wtc.dn.nc'].browse(nc_id)
        data = abs((datetime.strptime(data.date_due,"%Y-%m-%d") - datetime.strptime(data.date,"%Y-%m-%d")).days)
        return data

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
            'hari_tempo': self.hari_tempo,
            'terbilang': self.terbilang
        }
        return self.env['report'].render('wtc_dn_nc.teds_payment_request', docargs)