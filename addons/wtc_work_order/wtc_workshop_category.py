from openerp import models, fields, api, _, SUPERUSER_ID
import time
from datetime import datetime
from openerp.osv import osv
import string


class wtc_workshop_category(models.Model):
    _name = 'wtc.workshop.category'
    _description='Category Workshop'
    
    name=fields.Char(string="Workshop Category", required=True)
    
    _sql_constraints = [
    ('unique_name', 'unique(name)', 'Master data sudah pernah dibuat !'),
    ] 
    
    @api.onchange('name')
    def change_name(self):
        if self.name :
            self.name = self.name.replace(" ", "")
            self.name = self.name.upper()