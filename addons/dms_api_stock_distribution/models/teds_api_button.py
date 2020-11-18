from openerp import models, fields, api
from datetime import datetime

class ApiButton(models.Model):
    _inherit = "teds.api.button"

    # Kirim Distribusi Qty Approved
    @api.multi
    def api_stock_distribution_qty_approved(self):
        self.env['wtc.stock.distribution'].sudo().api_stock_distribution_qty_approved()


    # Kirim Distribution Reject
    @api.multi
    def api_reject_stock_distribution(self):
        self.env['wtc.stock.distribution'].sudo().api_reject_stock_distribution()


    # Kirim Data Packing Stock Ke DMS Division Sparepart
    @api.multi
    def api_dms_stock_picking_to_hoki_sparepart(self):
        self.env['wtc.stock.packing'].sudo().api_dms_stock_picking_to_hoki_sparepart()
    
    # Kirim Data Packing Stock Ke DMS Division Unit
    @api.multi
    def api_dms_stock_picking_to_hoki_unit(self):
        self.env['wtc.stock.packing'].sudo().api_dms_stock_picking_to_hoki_unit()

    # Kirim Data Booking Unit Gudang
    @api.multi
    def api_dms_stock_picking_booking(self):
        self.env['stock.picking'].sudo().api_stock_picking_booking_unit()

    
    # @api.multi
    # def api_dms_stock_picking_whi(self):
    #     self.env['wtc.stock.packing'].sudo().api_dms_stock_picking_whi()

