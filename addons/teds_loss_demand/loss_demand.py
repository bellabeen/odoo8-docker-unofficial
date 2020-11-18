import itertools
from lxml import etree
from datetime import datetime, timedelta
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import openerp.addons.decimal_precision as dp
from openerp.osv import osv


class TedsLossDemand(models.Model):
    _name = 'teds.loss.demand'
    _description = 'Loss Demand'

  
    @api.multi
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date()

    def _get_default_branch(self):
        branch_ids = False
        branch_ids = self.env.user.branch_ids
        if branch_ids and len(branch_ids) == 1 :
            return branch_ids[0].id
        return False



    branch_id = fields.Many2one('wtc.branch', string ='Branch', default=_get_default_branch)  
    product_id = fields.Many2one('product.product', string ='Product')
    date = fields.Date('Tanggal',default=_get_default_date)
    partner_id = fields.Many2one('res.partner',string='Customer')
    mobile = fields.Char('Mobile', required=True)
    division =fields.Selection([('Sparepart','Sparepart')], 'Division', change_default=True, default='Sparepart',select=True)

    @api.onchange('partner_id','mobile')
    def onchange_partner_id(self):
        mobile = []

        if self.partner_id:
            obj_customer = self.env['res.partner'].search([('id','=',self.partner_id.id)])
            mobilex = obj_customer.mobile

            if obj_customer :
                self.mobile = mobilex


    @api.model
    def create(self,values,context=None):
        value = []
        branch = values['branch_id']
        product = values['product_id']

        if branch and product :
            query = """ 
                   select l.branch_id
                            , p.default_code
                            , t.name as product_name
                            , q.product_id
                            , sum(case when q.consolidated_date IS NULL THEN q.qty ELSE 0 END) as qty_titipan
                            , sum(case when q.consolidated_date IS NOT NULL THEN q.qty ELSE 0 END) as qty_stock
                            , case WHEN l.usage='internal' then COALESCE(
                                (select sum(product_uom_qty) from stock_move sm left join stock_picking sp on sm.picking_id=sp.id 
                                    left join stock_picking_type spt on sp.picking_type_id=spt.id
                                    left join stock_location stl on sm.location_dest_id=stl.id 
                                    where spt.code in ('outgoing','interbranch_out') 
                                        and sp.branch_id=l.branch_id 
                                        and sp.state not in ('draft','cancel','done') 
                                        and sp.division='Sparepart' 
                                        and sm.product_id=q.product_id
                                ),0
                            ) 
                            else 0 end as qty_reserved_end
                            from stock_quant q
                            INNER JOIN stock_location l ON q.location_id = l.id AND l.usage = 'internal'
                            LEFT JOIN product_product p ON q.product_id = p.id
                            LEFT JOIN product_template t ON p.product_tmpl_id = t.id
                            LEFT JOIN product_category c ON t.categ_id = c.id 
                            LEFT JOIN product_category c2 ON c.parent_id = c2.id 
                            WHERE (c.name = 'Sparepart' or c2.name = 'Sparepart')  and q.product_id = %s and l.branch_id = %s
                            group by l.branch_id, l.warehouse_id, l.complete_name, l.usage, p.default_code, t.name, q.product_id
                    """%(product,branch)
            self._cr.execute (query)

            ress = self._cr.fetchall()
          
            qty_intransit = 0
            qty_reserved = 0
            qty_stok = 0

            for x in ress :
                qty_intransit += x[4]
                qty_reserved += x[6]
                qty_stok += x[5]

            total_available = qty_stok - qty_reserved
            stock_intransit = qty_intransit
            stock_available = total_available
            stock_reserved = qty_reserved
            total_stock = qty_stok + qty_intransit

            if total_stock > 0 :
                raise osv.except_osv(('Perhatian !'), ("Stock masih Tersedia !")) 

        create= super(TedsLossDemand,self).create(values)
        return create