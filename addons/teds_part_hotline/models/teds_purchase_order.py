from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning
from datetime import date, datetime, timedelta,time
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.one
    @api.depends('purchase_order_type_id')
    def compute_type_value(self):
        if self.purchase_order_type_id:
                self.type_value = self.purchase_order_type_id.name.upper().strip()

    type_value = fields.Char('Type',compute='compute_type_value')
    part_hotline_id = fields.Many2one('teds.part.hotline','No Hotline')

    
    @api.onchange('purchase_order_type_id')
    def onchange_hotline(self):
        self.part_hotline_id = False
    
    @api.onchange('part_hotline_id')
    def onchange_part_hotline(self):
        self.order_line = False
        if self.part_hotline_id:
            ids = []
            product_category = self.env['product.category'].sudo().search([('name','=','Sparepart')],limit=1)
            if not product_category:
                raise Warning('Product Category Sparepart tidak ditemukan !')
            for x in self.part_hotline_id.part_detail_ids:
                if x.status_po == 'draft':
                    price = 0
                    uom_id = x.product_id.uom_po_id.id
                    if self.pricelist_id:
                        date_order_str = datetime.strptime(self.date_order, DEFAULT_SERVER_DATETIME_FORMAT).strftime(DEFAULT_SERVER_DATE_FORMAT)
                        price = self.pricelist_id.price_get(x.product_id.id, x.qty or 1.0, self.partner_id or False, context={'uom': uom_id, 'date': date_order_str})[self.pricelist_id.id]
                    else:
                        price = x.product_id.standard_price
                    
                    supplierinfo = False
                    for supplier in x.product_id.seller_ids:
                        if self.partner_id and (supplier.name.id == self.partner_id):
                            supplierinfo = supplier
                            if supplierinfo.product_uom.id != uom_id:
                                res['warning'] = {'title': _('Warning!'), 'message': _('The selected supplier only sells this product by %s') % supplierinfo.product_uom.name }
                                raise Warning('The selected supplier only sells this product by %s' % supplierinfo.product_uom.name)
                    dt = self.env['purchase.order.line']._get_date_planned(supplierinfo, self.date_order).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                
                    taxes_ids = self.env['account.fiscal.position'].map_tax(x.product_id.supplier_taxes_id)
                    product_qty = x.qty - x.qty_spl
                    if product_qty > 0:
                        ids.append([0,False,{
                            'categ_id':product_category.id,
                            'product_id':x.product_id.id,
                            'name':x.product_id.description,
                            'product_qty':product_qty,
                            'price_unit':price,
                            'price_unit_show':price,
                            'product_uom':uom_id,
                            'qty_invoiced':0,
                            'received':0,
                            'taxes_id':[[6,0,[taxes_ids.id]]],
                            'taxes_id_show':[[6,0,[taxes_ids.id]]],
                            'date_planned':dt,
                            'state':'draft'
                        }])
            if len(ids) > 0:
                self.order_line = ids
            else:
                raise Warning('Detail product sudah tidak ada !')

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    @api.onchange('date_planned')
    def onchange_date_plan_hotline(self):
        part_hotline_id = self.order_id.part_hotline_id
        if part_hotline_id:
            raise Warning('Type Hotline tidak bisa menambahkan product !')