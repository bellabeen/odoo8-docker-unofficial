from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning
from datetime import date,timedelta,datetime

class LeadStage(models.Model):
    _name = "teds.lead.stage"

    name = fields.Char('Stage')
    type = fields.Selection([
        ('lead','Lead'),
        ('stnk','STNK'),
        ('bpkb','BPKB'),
        ('faktur','Faktur')],string="Type")

    _sql_constraints = [('name_unique', 'unique(name)', 'Nama stage tidak boleh ada yang sama !')]
    
    @api.model
    def create(self,vals):
        if vals.get('name'):
            vals['name'] = vals['name'].upper()    
        return super(LeadStage,self).create(vals)

    @api.multi
    def write(self,vals):
        if vals.get('name'):
            vals['name'] = vals['name'].upper()
        return super(LeadStage,self).write(vals)
