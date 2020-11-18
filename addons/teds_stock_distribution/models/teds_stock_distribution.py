from openerp import models, fields, api

class StockDistribution(models.Model):
    _inherit = "wtc.stock.distribution"

    is_download = fields.Boolean('Is Download')