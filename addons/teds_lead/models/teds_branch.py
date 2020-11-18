from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning
from datetime import date,timedelta,datetime

class Branch(models.Model):
    _inherit = "wtc.branch"

    is_allow_lead = fields.Boolean('Is Allow Lead Deal ?',default=True)