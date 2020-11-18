from datetime import timedelta,datetime
from openerp import models, fields, api

class ApiCheckStockMD(models.Model):
    _name = "teds.api.check.stock"

    @api.multi
    def check_stock_md(self,vals):
        product = vals.get('product')
        query = """
            SELECT 
                l.branch_id as branch_id
                , p.id as product_id
                , p.default_code as prod_code
                , t.name as prod_name
                , sum(case when q.consolidated_date IS NULL THEN q.qty ELSE 0 END) as qty_intransit
                , sum(case when q.consolidated_date IS NOT NULL THEN q.qty ELSE 0 END) as qty_stock
                , case WHEN l.usage='internal' then COALESCE(
                    (SELECT sum(product_uom_qty) FROM stock_move sm 
                    LEFT JOIN stock_picking sp on sm.picking_id=sp.id 
                    LEFT JOIN stock_picking_type spt on sp.picking_type_id=spt.id
                    LEFT JOIN stock_location stl on sm.location_dest_id=stl.id 
                    WHERE spt.code in ('outgoing','interbranch_out')
                    AND sp.branch_id=l.branch_id 
                    AND sp.state not in ('draft','cancel','done') 
                    AND sp.division='Sparepart' 
                    AND sm.product_id=q.product_id
                    AND sm.location_id=q.location_id
                    ),0
                ) 
                else 0 end as qty_reserved_end
            FROM stock_quant q
            INNER JOIN stock_location l ON q.location_id = l.id AND l.usage = 'internal'
            LEFT JOIN wtc_branch b ON b.id = l.branch_id
            LEFT JOIN product_product p ON q.product_id = p.id
            LEFT JOIN product_template t ON p.product_tmpl_id = t.id
            LEFT JOIN product_category c ON t.categ_id = c.id 
            LEFT JOIN product_category c2 ON c.parent_id = c2.id 
            WHERE (c.name = 'Sparepart' or c2.name = 'Sparepart')  
            AND (t.name ilike '%s%%' OR p.default_code ilike '%s%%')
            AND b.branch_type = 'MD'
            GROUP BY l.branch_id, l.warehouse_id, l.complete_name, l.usage, p.id, t.name, q.product_id,q.location_id
        """ %(product,product)

        self._cr.execute(query)
        ress = self._cr.dictfetchall()
        result = {}
        qty_intransit = 0
        qty_reserved = 0
        qty_stock = 0
        data = []
        if len(ress) > 0:
            pricelist = self.env['wtc.branch'].sudo().search([('branch_type','=','MD')]).pricelist_part_sales_id
            
            for res in ress:
                if not result.get(res['prod_name']):
                    harga_satuan = pricelist.price_get(res.get('product_id'),1)[pricelist.id]

                    result[res['prod_name']] = {
                        'code':res['prod_code'],
                        'name':res['prod_name'],
                        'qty_intransit':res['qty_intransit'],
                        'qty_reserved_end':res['qty_reserved_end'],
                        'qty_stock':res['qty_stock'],
                        'harga_satuan':harga_satuan
                    }
                else:
                    result[res['prod_name']]['qty_intransit'] += res['qty_intransit']
                    result[res['prod_name']]['qty_reserved_end'] += res['qty_reserved_end']
                    result[res['prod_name']]['qty_stock'] += res['qty_stock']

        else:
            return {'data':data}
        return {'data':result.values()}
