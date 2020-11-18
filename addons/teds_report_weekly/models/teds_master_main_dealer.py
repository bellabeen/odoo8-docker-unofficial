from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning

class ReportWkeelyMasterMainDealer(models.Model):
    _name = "teds.report.weekly.master.main.dealer"

    name = fields.Char('Main Dealer')

    @api.model
    def create(self,vals):
        if vals.get('name'):
            vals['name'] = vals['name'].upper()
        return super(ReportWkeelyMasterMainDealer,self).create(vals)
    
    @api.multi
    def write(self,vals):
        if vals.get('name'):
            vals['name'] = vals['name'].upper()
        return super(ReportWkeelyMasterMainDealer,self).write(vals)


    
    _sql_constraints = [('unique_name', 'unique(name)', 'Main Dealer tidak boleh duplikat !')]

