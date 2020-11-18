from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning
from datetime import date, datetime, timedelta,time

class MasterLokasiAsset(models.Model):
    _name = "teds.master.lokasi.asset"

    name = fields.Char('Lokasi',index=True)
    active = fields.Boolean('Active',default=True)

class AccountAsset(models.Model):
    _inherit = "account.asset.asset"

    lokasi_asset_id = fields.Many2one('teds.master.lokasi.asset','Lokasi Asset')
    