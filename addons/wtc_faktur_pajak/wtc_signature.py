from datetime import datetime, timedelta
from openerp import models, fields, api, _

class wtc_signature(models.Model):
    _name = 'wtc.signature'
    _description = 'Signature Report'
    
    name = fields.Char(string="Name")
    
    _sql_constraints = [
    ('unique_model_id', 'unique(name)', 'Master data duplicate !'),
    ]    