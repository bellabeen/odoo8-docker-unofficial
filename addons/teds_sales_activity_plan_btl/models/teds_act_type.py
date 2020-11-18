from openerp import models, fields, api
from datetime import datetime, timedelta

class ActType(models.Model):
    _name = "teds.act.type.sumber.penjualan"

    name = fields.Char('Activity Type')
    code = fields.Char('Code')
    is_btl = fields.Boolean('Activity ?')
    is_location = fields.Boolean('Location ?')

    _sql_constraints = [('code_unique', 'unique(code)', 'Act Type Penjualan tidak boleh duplikat !')]

    @api.model
    def create(self,vals):
        vals['name'] = vals['name'].title()
        vals['code'] = vals['code'].upper()
        return super(ActType,self).create(vals)

    @api.multi
    def write(self,vals):
        if vals.get('name',False):
            vals['name'] = vals['name'].title()
        if vals.get('code',False):
            vals['code'] = vals['code'].upper()
        return super(ActType,self).write(vals)