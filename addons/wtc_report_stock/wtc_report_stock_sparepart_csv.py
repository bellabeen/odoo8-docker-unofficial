import itertools
import tempfile
from cStringIO import StringIO
import base64
import csv
import codecs
from openerp.osv import orm, fields
from openerp.tools.translate import _


class AccountCSVExport(orm.TransientModel):
    _inherit = "wtc.report.stock.sparepart.wizard"

    wbf = {}

        

    # def _get_header_account(self, cr, uid, ids, context=None):
    #     return [_(u'CODE'),
    #             _(u'NAME'),
    #             _(u'DEBIT'),
    #             _(u'CREDIT'),
    #             _(u'BALANCE'),
    #             ]

    def _get_rows_account(self, cr, uid, ids,data, context=None):
        """
        Return list to generate rows of the CSV file
        """
        location_status = data['location_status']
        product_ids = data['product_ids']
        branch_ids = data['branch_ids'] 
        location_ids = data['location_ids']

              
        tz = '7 hours'
        
        query_where = " WHERE 1=1 "
        remark = ''
    
        if location_status == 'all' :
            query_where += " AND quant.location_usage in ('internal', 'transit') "
        else :
            query_where += " AND quant.location_usage = '%s' " % location_status
        if product_ids :
            query_where += " AND quant.product_id in %s" % str(tuple(product_ids)).replace(',)', ')')
        if branch_ids :
            query_where += " AND quant.branch_id in %s" % str(tuple(branch_ids)).replace(',)', ')')
        if location_ids :
            query_where += " AND quant.location_id in %s" % str(tuple(location_ids)).replace(',)', ')')

        query = """
            select b.code as branch_code
            , b.name as branch_name
            , b.profit_centre as branch_profit_center
            , quant.default_code as product_desc
            , quant.categ_name
            , quant.product_name
            , quant.location_name
            , date_part('days', now() - quant.in_date) as aging
            , quant.qty_titipan
            , quant.qty_reserved
            , quant.qty_stock
            , COALESCE(ppb.cost, 0.01) as harga_satuan
            from 
            (select l.branch_id
                , l.warehouse_id
                , l.complete_name as location_name
                , l.usage as location_usage
                , p.default_code
                , t.name as product_name
                , COALESCE(c.name, c2.name) as categ_name
                , q.product_id
                , min(q.in_date) as in_date
                , sum(case when q.consolidated_date IS NULL THEN q.qty ELSE 0 END) as qty_titipan
                , sum(case when q.consolidated_date IS NOT NULL AND q.reservation_id IS NULL THEN q.qty ELSE 0 END) as qty_stock
                , sum(case when q.reservation_id IS NOT NULL THEN q.qty ELSE 0 END) as qty_reserved
            from stock_quant q
            INNER JOIN stock_location l ON q.location_id = l.id AND l.usage in ('internal','transit')
            LEFT JOIN product_product p ON q.product_id = p.id
            LEFT JOIN product_template t ON p.product_tmpl_id = t.id
            LEFT JOIN product_category c ON t.categ_id = c.id 
            LEFT JOIN product_category c2 ON c.parent_id = c2.id 
            WHERE 1=1 and (c.name = 'Sparepart' or c2.name = 'Sparepart')
            group by l.branch_id, l.warehouse_id, l.complete_name, l.usage, p.default_code, t.name, categ_name, q.product_id
            ) as quant
            LEFT JOIN wtc_branch b ON quant.branch_id = b.id
            LEFT JOIN product_price_branch ppb ON ppb.product_id = quant.product_id and ppb.warehouse_id = quant.warehouse_id
            %s
            order by branch_code,product_name,location_name
            """ % (query_where)
        
       
        cr.execute (query)
        res = cr.fetchall()

        rows = []

        
        for line in res:
            qty_stock = str(line[10]) if line[10] != None else ''
        
            sparepart=line[0]+";"+line[5]+";"+qty_stock
            rows.append(list(
              {
              sparepart
              })
              )
        return rows




    def _get_rows_account_reserved(self, cr, uid, ids,data, context=None):
        """
        Return list to generate rows of the CSV file
        """
        location_status = data['location_status']
        product_ids = data['product_ids']
        branch_ids = data['branch_ids'] 
        location_ids = data['location_ids']

        query_where = " WHERE 1=1 "

        if location_status == 'all' :
            query_where += " AND quant.location_usage in ('internal', 'transit') "
        else :
            query_where += " AND quant.location_usage = '%s' " % location_status
        if product_ids :
            query_where += " AND quant.product_id in %s" % str(tuple(product_ids)).replace(',)', ')')
        if branch_ids :
            query_where += " AND quant.branch_id in %s" % str(tuple(branch_ids)).replace(',)', ')')
        if location_ids :
            query_where += " AND quant.location_id in %s" % str(tuple(location_ids)).replace(',)', ')')

        query = """
                select b.code as branch_code
                , b.name as branch_name
                , b.profit_centre as branch_profit_center
                , quant.description as product_desc
                , quant.categ_name
                , quant.product_name
                , quant.location_name
                , date_part('days', now() - quant.in_date) as aging
                , quant.qty as quantity
                , COALESCE(ppb.cost, 0.01) as harga_satuan
                , quant.qty * COALESCE(ppb.cost,0.01) as total_harga
                , sm.origin as transaction_name
                , sp.name as picking_name
                from 
                (select l.id as location_id, l.branch_id, l.warehouse_id, l.complete_name as location_name, l.usage as location_usage, t.description, t.name as product_name, COALESCE(c.name, c2.name) as categ_name, q.product_id, min(q.in_date) as in_date, sum(q.qty) as qty
                    , q.reservation_id
                    from stock_quant q
                    INNER JOIN stock_location l ON q.location_id = l.id AND l.usage in ('internal','transit')
                    LEFT JOIN product_product p ON q.product_id = p.id
                    LEFT JOIN product_template t ON p.product_tmpl_id = t.id
                    LEFT JOIN product_category c ON t.categ_id = c.id 
                    LEFT JOIN product_category c2 ON c.parent_id = c2.id 
                    WHERE 1=1 and (c.name = 'Sparepart' or c2.name = 'Sparepart') and q.reservation_id IS NOT NULL
                    group by l.id, l.branch_id, l.warehouse_id, l.complete_name, t.description, t.name, categ_name, q.product_id, reservation_id
                ) as quant
                LEFT JOIN wtc_branch b ON quant.branch_id = b.id
                LEFT JOIN product_price_branch ppb ON ppb.product_id = quant.product_id and ppb.warehouse_id = quant.warehouse_id
                LEFT JOIN stock_move sm ON quant.reservation_id = sm.id
                LEFT JOIN stock_picking sp ON sm.picking_id = sp.id
                %s
                order by branch_code,product_name,location_name
                """ % (query_where)
        
       
        cr.execute (query)
        ress = cr.fetchall()

        rowsss = []

        for linee in ress:
            qty = str(linee[8]) if linee[8] != None else ''
        
            reserved=linee[0]+";"+linee[5]+";"+qty
            rowsss.append(list(
              {
              reserved
              })
              )

        return rowsss

