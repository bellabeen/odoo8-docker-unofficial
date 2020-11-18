from openerp import models, fields, api

class BranchConfigLocation(models.Model):
    _name = "teds.branch.config.location"

    branch_id = fields.Many2one('wtc.branch','Branch')
    division = fields.Selection([('Sparepart','Sparepart'),('Unit','Unit')])
    type_id = fields.Many2one('wtc.purchase.order.type','Type')
    location_id = fields.Many2one('stock.location','Location')

    _sql_constraints = [('branch_division_type_unique', 'unique(branch_id,division,type_id)', 'Data Lokasi Type sudah ada !.')]