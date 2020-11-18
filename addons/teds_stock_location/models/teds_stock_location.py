from openerp import models, fields, api
from datetime import date, datetime, timedelta,time

class StockLocationDashboard(models.TransientModel):
    _name = "teds.stock.location.dashboard"

    branch_id = fields.Many2one('wtc.branch','Branch')
    location_id = fields.Many2one('stock.location','Location')
    location = fields.Char('Location')
    jenis_lokasi = fields.Char('Jenis Lokasi')
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    kapasitas = fields.Float('Kapasitas')
    qty_stock = fields.Float('Qty Stock')

    def action_stock_location(self):
        tree_id = self.env.ref('teds_stock_location.view_teds_stock_location_dashboard_tree').id
        graph_id = self.env.ref('teds_stock_location.view_teds_stock_location_dashboard_graph').id
        users = self.env['res.users'].sudo().browse(self._uid)
        branch_ids = [b.id for b in users.branch_ids]

        if branch_ids:
            obj = self.search([('branch_id','in',branch_ids)])
            if obj:
                obj.unlink()

            query = """
                SELECT b.id as branch_id
                , sl.id as location_id
                , sl.name as loc_name
                , initcap(sl.jenis) as jenis
                , sl.start_date 
                , sl.end_date
                , sl.maximum_qty as kapasitas
                , COALESCE(sc.qty,0) as qty_stock
                FROM stock_location sl
                INNER JOIN wtc_branch b on sl.branch_id = b.id
                LEFT JOIN (
                  SELECT q.location_id
                  , coalesce(c3.name, coalesce(c2.name, c.name)) as categ
                  , sum(q.qty) as qty
                  FROM stock_quant q
                  LEFT JOIN product_product p on q.product_id = p.id 
                  LEFT JOIN product_template pt on p.product_tmpl_id = pt.id
                  LEFT JOIN product_category c on pt.categ_id = c.id 
                  LEFT JOIN product_category c2 on c.parent_id = c2.id
                  LEFT JOIN product_category c3 on c2.parent_id = c3.id
                  WHERE c3.name = 'Unit' or c2.name = 'Unit' or c.name = 'Unit'
                  GROUP BY q.location_id, categ
                ) as sc on sl.id = sc.location_id
                WHERE sl.usage = 'internal' 
                AND b.id in %s
                AND (sl.end_date >= now() OR sc.qty > 0)

            """ % str(tuple(branch_ids)).replace(',)', ')')
            self.env.cr.execute(query)

            ress = self.env.cr.dictfetchall()
            for res in ress:
                vals = {
                    'branch_id': res.get('branch_id'),
                    'location_id': res.get('location_id'),
                    'location': res.get('loc_name'),
                    'jenis_lokasi': res.get('jenis') if res.get('jenis') != None else 'Stock',
                    'start_date': res.get('start_date'),
                    'end_date': res.get('end_date'),
                    'kapasitas': res.get('kapasitas'),
                    'qty_stock': res.get('qty_stock')
                }
                create = self.create(vals)
        domain = [('branch_id', 'in', [b.id for b in users.branch_ids])]
        return {
            'type': 'ir.actions.act_window',
            'name': 'Stock Location Unit',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'teds.stock.location.dashboard',
            'domain': domain,        
            'views': [(tree_id, 'tree'),(graph_id, 'graph')],
        }