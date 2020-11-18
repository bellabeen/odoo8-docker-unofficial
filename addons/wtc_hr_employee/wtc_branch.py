from openerp import fields, models

class Wtc_Branch(models.Model):
    _inherit = 'wtc.branch'

    area_id = fields.Many2one('wtc.area',string='Default Area')
