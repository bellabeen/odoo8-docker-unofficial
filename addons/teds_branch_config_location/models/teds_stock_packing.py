from openerp import models, fields, api

class StockPacking(models.Model):
    _inherit = "wtc.stock.packing"

    @api.one
    @api.depends('rel_origin')
    def compute_type_source(self):
        if self.rel_origin:
            tipe_origin = False
            origin_split = self.rel_origin.split('/')
            if origin_split[0] == 'MO':
                mo_obj = self.env['wtc.mutation.order'].sudo().search([('name','=',self.rel_origin)],limit=1)
                if mo_obj:
                    tipe_origin = mo_obj.distribution_id.type_id.name
                
            elif origin_split[0] == 'PO':
                po_obj = self.env['purchase.order'].sudo().search([('name','=',self.rel_origin)],limit=1)
                if po_obj:
                    tipe_origin = po_obj.purchase_order_type_id.name
            
            elif origin_split[0] == 'SO':
                so_obj = self.env['sale.order'].sudo().search([('name','=',self.rel_origin)],limit=1)
                if so_obj:
                    tipe_origin = so_obj.distribution_id.type_id.name
            
            elif origin_split[0] == 'WO':
                wo_obj = self.env['wtc.work.order'].sudo().search([('name','=',self.rel_origin)],limit=1)
                if wo_obj:
                    if wo_obj.part_hotline_id:
                        tipe_origin = 'Hotline'
                    

            if tipe_origin:
                self.tipe_source = tipe_origin
                
    tipe_source = fields.Char('Tipe Source',compute='compute_type_source')