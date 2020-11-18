from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning
from datetime import date, datetime, timedelta,time

class StockPacking(models.Model):
    _inherit = "wtc.stock.packing"

    @api.one
    @api.depends('rel_origin','tipe_source')
    def compute_source_hotline(self):
        if self.rel_origin:
            origin_split = self.rel_origin.split('/')
            if self.tipe_source == 'Hotline':
                if origin_split[0] == 'PO':
                    po_obj = self.env['purchase.order'].sudo().search([('name','=',self.rel_origin)],limit=1)
                    if po_obj:
                        if po_obj.part_hotline_id:
                            self.part_hotline_id = po_obj.part_hotline_id.id

            if origin_split[0] == 'WO':
                wo_obj = self.env['wtc.work.order'].sudo().search([('name','=',self.rel_origin)],limit=1)
                if wo_obj:
                    if wo_obj.part_hotline_id:
                        self.part_hotline_id = wo_obj.part_hotline_id.id

            
    part_hotline_id = fields.Many2one('teds.part.hotline','No Hotline',compute="compute_source_hotline",store=True)

    @api.one
    def post(self):
        super(StockPacking,self).post()
        if self.part_hotline_id:
            hotline_id = False
            model = self.picking_id.model_id.model
            for line in self.packing_line:
                hotline_prod = self.env['teds.part.hotline.detail'].sudo().search([
                    ('hotline_id','=',self.part_hotline_id.id),
                    ('product_id','=',line.product_id.id)],limit=1)
                if not hotline_prod and model != 'wtc.work.order':
                    raise Warning('No Hotline %s tidak memesan product %s, Cek kembali No Hotline !'%(self.part_hotline_id.name,line.product_id.name_get().pop()[1]))

                if hotline_prod:
                    vals_detail = {}
                    qty_prod = hotline_prod.qty
                    if model == 'wtc.work.order':
                        qty_wo_awal = hotline_prod.qty_wo
                        qty_wo_akhir = qty_wo_awal + line.quantity

                        if hotline_prod.status_wo != 'draft':
                            raise Warning('Product %s sudah disupply, Qty Spl WO %s !'%(line.product_id.name_get().pop()[1],qty_wo_awal))

                        if qty_wo_akhir > qty_prod:
                            raise Warning('Product Hotline %s, Qty sudah melebihi qty supply ! \n Qty Product %s, Qty Supply WO %s, Cek kembali No Hotline !'%(line.product_id.name_get().pop()[1],qty_prod,qty_wo_akhir))

                        vals_detail['qty_wo'] = qty_wo_akhir
                        vals_detail['no_wo'] = self.rel_origin

                        if int(qty_prod) == int(qty_wo_akhir):
                            vals_detail['status_wo'] = 'done'

                    else:
                        qty_spl_awal = hotline_prod.qty_spl
                        qty_spl_akhir = qty_spl_awal + line.quantity

                        if hotline_prod.status_po != 'draft':
                            raise Warning('Product %s sudah disupply, Qty Spl PO %s !'%(line.product_id.name_get().pop()[1],qty_spl_awal))
                        
                        if qty_spl_akhir > qty_prod:
                            raise Warning('Product Hotline %s, Qty sudah melebihi qty supply ! \n Qty Product %s, Qty Supply PO %s, Cek kembali No Hotline !'%(line.product_id.name_get().pop()[1],qty_prod,qty_spl_akhir))
                        
                        vals_detail['qty_spl'] = qty_spl_akhir
                        vals_detail['no_po'] = self.rel_origin
                        vals_detail['tgl_po'] = self.date
                        
                        if int(qty_prod) == int(qty_spl_akhir):
                            vals_detail['status_po'] = 'done' 
                    
                    hotline_prod.sudo().write(vals_detail)
                    hotline_id = hotline_prod.hotline_id
            
            if hotline_id:
                hotline_id.cek_po_done()
                hotline_id.cek_wo_done()