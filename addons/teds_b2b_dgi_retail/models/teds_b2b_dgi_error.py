from openerp import models, fields, api
from datetime import datetime

class B2bDGIErrorLog(models.Model):
    _name = "teds.b2b.dgi.error.log"
    _order = "date DESC"

    def _get_default_date(self):
        return datetime.now()

    name = fields.Char('Name')
    origin = fields.Char('Origin')
    url = fields.Char('URL')
    request_type = fields.Selection([
        ('post','POST'),
        ('get','GET'),
        ('put','PUT'),
        ('delete','Delete')],string="Request Type")
    error = fields.Char('Error')
    date = fields.Datetime('Date',default=_get_default_date)