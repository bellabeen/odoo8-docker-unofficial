from openerp import fields, api, models

class StockProductionLot(models.Model):
    _inherit = "stock.production.lot"

    change_lot_ids = fields.One2many("teds.change.lot","lot_id",string="Detail Pengubahan Data")
