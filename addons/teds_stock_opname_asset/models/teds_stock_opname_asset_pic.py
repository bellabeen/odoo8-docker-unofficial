from openerp import models, fields, api

class StockOpnameAssetPic(models.Model):
    _name = "teds.stock.opname.asset.pic"

    name = fields.Char('Name')

    _sql_constraints = [('unique_name', 'unique(name)', 'Name sudah ada !')]
