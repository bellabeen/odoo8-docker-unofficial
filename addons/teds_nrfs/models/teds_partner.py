from openerp import models, fields, api

class teds_partner(models.Model):
    _inherit = "res.partner"

    id_ekspedisi_ahm = fields.Char(string='ID Ekspedisi AHM')