from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning
from datetime import date, datetime, timedelta,time

class WorkOrder(models.Model):
    _inherit = "wtc.work.order"

    type = fields.Selection(selection_add=[('HOTLINE', 'Hotline')])
    part_hotline_id = fields.Many2one('teds.part.hotline','No Hotline')
    
    @api.onchange('type')
    def onchange_type(self):
        self.part_hotline_id = False
    
    @api.onchange('part_hotline_id')
    def onchange_part_hotline(self):
        self.work_lines = False
        if self.part_hotline_id:
            self.lot_id = self.part_hotline_id.lot_id.id
            ids = []
            for x in self.part_hotline_id.part_detail_ids:
                product_qty = x.qty - x.qty_wo
                if product_qty > 0:
                    if x.status_wo == 'draft' and x.status_po == 'done':
                        ids.append([0,False,{
                            'categ_id':'Sparepart',
                            'product_id':x.product_id.id,
                            'name' :x.product_id.description,
                            'name_show':x.product_id.description,
                            'product_qty':product_qty, 
                            'discount':0,
                            'price_unit':x.price,
                            'price_unit_show':x.price,
                            'product_uom':1,
                            'warranty': x.product_id.warranty,
                            'tax_id': [(6,0,[x.product_id.taxes_id.id])],
                            'tax_id_show': [(6,0,[x.product_id.taxes_id.id])],
                            'state':'draft',
                        }])
            if len(ids) > 0:
                self.work_lines = ids
            else:
                raise Warning('Detail product sudah tidak ada !')