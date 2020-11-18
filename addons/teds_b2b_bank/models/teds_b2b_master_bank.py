from openerp import models, fields, api
from datetime import timedelta,datetime,date

class B2bMasterBank(models.Model):
    _name = "teds.b2b.master.bank"
    
    def _get_default_date(self):
        return datetime.now()

    name = fields.Char('Bank Account')
    config_id = fields.Many2one('teds.b2b.api.config','Config')
    branch_id = fields.Many2one('wtc.branch','Branch')
    schedule_id = fields.Many2one('teds.b2b.api.schedule','Schedule')
    account_id = fields.Many2one('account.account','Account')
    balance = fields.Float('Balance')
    plafon = fields.Float('Plafon')
    currency = fields.Char('Currency')
    float_amount = fields.Float('Float Amount')
    hold_amount = fields.Float('Hold Amount')
    available_balance = fields.Float('Available Balance')
    is_fetch_statement = fields.Boolean('Fetch Statement')
    last_balance_check = fields.Datetime('Last Balance Check',default=_get_default_date)
    last_fetch = fields.Datetime('Last Fetch',default=_get_default_date)

    _sql_constraints = [('name', 'unique(name)', 'Bank Account tidak boleh duplikat !')]