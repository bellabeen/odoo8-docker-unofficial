from openerp import models, fields, api
from datetime import datetime

class ApiButton(models.Model):
    _name = "teds.api.button"

    name = fields.Char('Name')

    @api.multi
    def api_dms_sale_order(self):
        self.env['dealer.sale.order'].sudo().api_dms_sale_order()
    
    @api.multi
    def api_dms_penerimaan_stnk(self):
        self.env['wtc.penerimaan.stnk'].sudo().api_dms_penerimaan_stnk()

    @api.multi
    def api_dms_penerimaan_bpkb(self):
        self.env['wtc.penerimaan.bpkb'].sudo().api_dms_penerimaan_bpkb()
    
    @api.multi
    def api_dms_penyerahan_stnk(self):
        self.env['wtc.penyerahan.stnk'].sudo().api_dms_penyerahan_stnk()
    
    @api.multi
    def api_dms_penyerahan_bpkb(self):
        self.env['wtc.penyerahan.bpkb'].sudo().api_dms_penyerahan_bpkb()
    
    @api.multi
    def api_teds_work_order_limit(self):
        self.env['wtc.work.order'].sudo().api_teds_work_order_limit()
    
    @api.multi
    def api_teds_work_order_part_sales(self):
        self.env['wtc.work.order'].sudo().api_teds_work_order_part_sales()

    @api.multi
    def api_teds_work_order_bundling(self):
        self.env['wtc.work.order'].sudo().api_teds_work_order_bundling()
        
    @api.multi
    def api_teds_work_order_error(self):
        self.env['wtc.work.order'].sudo().api_teds_work_order_error()
