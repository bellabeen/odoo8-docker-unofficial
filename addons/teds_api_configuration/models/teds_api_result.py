from openerp import models, fields, api
from datetime import datetime
import time

class ApiResult(models.Model):
    _name = "teds.api.result"

    name = fields.Char('Code')
    description = fields.Text('Description')

    _sql_constraints = [('name_unique', 'unique(name)', 'Code tidak boleh duplikat.')]