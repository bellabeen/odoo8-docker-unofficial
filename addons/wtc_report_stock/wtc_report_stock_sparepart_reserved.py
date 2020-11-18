import time
import cStringIO
import xlsxwriter
from cStringIO import StringIO
import base64
import tempfile
import os
from openerp.osv import fields, osv
from openerp.tools.translate import _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from xlsxwriter.utility import xl_rowcol_to_cell
import logging
import re
import pytz
_logger = logging.getLogger(__name__)
from lxml import etree

class wtc_report_stock_sparepart_reserved(osv.osv_memory):
    _inherit = "wtc.report.stock.sparepart.wizard"

    wbf = {}

    def _print_excel_report_stock_sparepart_reserved(self, cr, uid, ids, data, context=None):
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

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Stock Sparepart Reserved')
        worksheet.set_column('B1:B1', 13)
        worksheet.set_column('C1:C1', 21)
        worksheet.set_column('D1:D1', 25)
        worksheet.set_column('E1:E1', 20)
        worksheet.set_column('F1:F1', 20)
        worksheet.set_column('G1:G1', 20)
        worksheet.set_column('H1:H1', 30)
        worksheet.set_column('I1:I1', 15)
        worksheet.set_column('J1:J1', 15)
        worksheet.set_column('K1:K1', 20)
        worksheet.set_column('L1:L1', 20)
        worksheet.set_column('M1:M1', 20)
        worksheet.set_column('N1:N1', 20)
        worksheet.set_column('O1:O1', 20)

        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        filename = 'Report Stock Sparepart Reserved '+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report Stock Sparepart Reserved' , wbf['title_doc'])
        worksheet.write('A3', ' ' , wbf['company'])
        row=3
        rowsaldo = row
        row+=1
        worksheet.write('A%s' % (row+1), 'No' , wbf['header'])
        worksheet.write('B%s' % (row+1), 'Branch Code' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'Branch Name' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'Profit Center' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'Kategori' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'Kode Product' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'Nama Barang' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'Lokasi' , wbf['header'])
        worksheet.write('I%s' % (row+1), 'Aging' , wbf['header'])
        worksheet.write('J%s' % (row+1), 'Quantity' , wbf['header'])
        worksheet.write('K%s' % (row+1), 'Harga Satuan' , wbf['header'])
        worksheet.write('L%s' % (row+1), 'Total Harga' , wbf['header'])
        worksheet.write('M%s' % (row+1), 'Status' , wbf['header'])
        worksheet.write('N%s' % (row+1), 'Transaction Name' , wbf['header'])
        worksheet.write('O%s' % (row+1), 'Picking Name' , wbf['header'])
    
        row+=2               
        no = 1     
        row1 = row
        
        total_qty = 0
        total_stock = 0
        for res in ress:
            branch_code = str(res[0].encode('ascii','ignore').decode('ascii')) if res[0] != None else ''
            branch_name = str(res[1].encode('ascii','ignore').decode('ascii')) if res[1] != None else ''
            profit_centre = str(res[2].encode('ascii','ignore').decode('ascii')) if res[2] != None else ''
            product_desc = str(res[3].encode('ascii','ignore').decode('ascii')) if res[3] != None else ''
            categ_name = str(res[4].encode('ascii','ignore').decode('ascii')) if res[4] != None else ''
            product_name = str(res[5].encode('ascii','ignore').decode('ascii')) if res[5] != None else ''
            location_name = str(res[6].encode('ascii','ignore').decode('ascii')) if res[8] != None else ''
            
            aging =res[7]
            qty = res[8]
            total_qty += qty

            harga_satuan = res[9]
            total_harga = res[10]
            total_stock += total_harga
            status='Stock (Reserved)'
            transaction_name = str(res[11].encode('ascii','ignore').decode('ascii')) if res[11] != None else ''
            picking_name = str(res[12].encode('ascii','ignore').decode('ascii')) if res[12] != None else ''
            
            worksheet.write('A%s' % row, no , wbf['content_number'])                    
            worksheet.write('B%s' % row, branch_code , wbf['content'])
            worksheet.write('C%s' % row, branch_name , wbf['content'])
            worksheet.write('D%s' % row, profit_centre , wbf['content'])
            worksheet.write('E%s' % row, categ_name , wbf['content'])
            worksheet.write('F%s' % row, product_name , wbf['content'])
            worksheet.write('G%s' % row, product_desc , wbf['content'])
            worksheet.write('H%s' % row, location_name , wbf['content'])
            worksheet.write('I%s' % row, aging , wbf['content_float'])
            worksheet.write('J%s' % row, qty , wbf['content_float'])
            worksheet.write('K%s' % row, harga_satuan , wbf['content_float'])
            worksheet.write('L%s' % row, total_harga , wbf['content_float'])
            worksheet.write('M%s' % row, status , wbf['content'])
            worksheet.write('N%s' % row, transaction_name , wbf['content'])
            worksheet.write('O%s' % row, picking_name, wbf['content'])
            no+=1
            row+=1
        
        worksheet.autofilter('A5:O%s' % (row))  
        worksheet.freeze_panes(5, 3)
        
        #TOTAL
        worksheet.merge_range('A%s:C%s' % (row,row), 'Total', wbf['total'])    
        worksheet.merge_range('D%s:I%s' % (row,row), '', wbf['total'])
        worksheet.write_blank('K%s' % (row), '', wbf['total'])
        worksheet.merge_range('M%s:O%s' % (row,row), '', wbf['total'])
        if row-1 >= row1 :
            worksheet.write_formula('J%s' % (row),'{=subtotal(9,J%s:J%s)}' % (row1, row-1), wbf['total_float'], total_qty)
            worksheet.write_formula('L%s' % (row),'{=subtotal(9,L%s:L%s)}' % (row1, row-1), wbf['total_float'], total_stock)
        else :
            worksheet.write_blank('J%s' % (row), '', wbf['total_float'])
            worksheet.write_blank('L%s' % (row), '', wbf['total_float'])
        
        worksheet.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])  
                   
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()
