from openerp import models, fields, api
from datetime import date, datetime, timedelta,time
from dateutil.relativedelta import relativedelta
from openerp.exceptions import Warning

class CashCountValidasi(models.Model):
    _name = "teds.cash.count.validasi"

    name = fields.Char('Name')
    type = fields.Selection([
        ('cash','Cash'),
        ('petty_cash','Petty Cash'),
        ('reimburse_petty_cash','Reimburse Petty Cash')])
    note = fields.Char('Note')
