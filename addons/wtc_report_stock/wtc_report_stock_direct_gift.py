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

class wtc_report_stock_direct_gift(osv.osv_memory):
    _name = "wtc.report.stock.direct.gift.wizard"
    _description = "Report Stock Direct Gift"

    wbf = {}

    def _get_default(self,cr,uid,date=False,user=False,context=None):
        if date :
            return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)
        else :
            return self.pool.get('res.users').browse(cr, uid, uid)
        
    def _get_branch_ids(self, cr, uid, context=None):
        branch_ids_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
        branch_ids = [b.id for b in branch_ids_user]
        return branch_ids
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(wtc_report_stock_direct_gift, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        categ_ids = self.pool.get('product.category').get_child_ids(cr,uid,view_id,'Umum')
        branch_ids_user=self.pool.get('res.users').browse(cr,uid,uid).branch_ids
        branch_ids=[b.id for b in branch_ids_user]
        
        doc = etree.XML(res['arch'])
        nodes = doc.xpath("//field[@name='product_ids']")
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
        nodes_location = doc.xpath("//field[@name='location_ids']")
        for node in nodes:
            node.set('domain', '[("categ_id", "in", '+ str(categ_ids)+')]')
        for node in nodes_branch:
            node.set('domain', '[("id", "=", '+ str(branch_ids)+')]')
        for node in nodes_location:
            node.set('domain', '[("branch_id", "=", '+ str(branch_ids)+')]')
        res['arch'] = etree.tostring(doc)
        return res
        
    _columns = {
        'state_x': fields.selection( ( ('choose','choose'),('get','get'))), #xls
        'data_x': fields.binary('File', readonly=True),
        'name': fields.char('Filename', 100, readonly=True), 
        'options': fields.selection([('stock','Stock'),('transit','Transit')], 'Options',change_default=True, select=True),
        'branch_ids': fields.many2many('wtc.branch', 'wtc_report_stock_direct_gift_branch_rel', 'wtc_report_stock_direct_gift_wizard_id',
                                        'branch_id', 'Branch', copy=False),
        'product_ids': fields.many2many('product.product', 'wtc_report_stock_direct_gift_product_rel', 'wtc_report_stock_direct_gift_wizard_id',
                                        'product_id', 'Product', copy=False, ),
        'location_ids': fields.many2many('stock.location', 'wtc_report_stock_direct_gift_location_rel', 'wtc_report_stock_direct_gift_wizard_id',
                                        'location_id', 'Location', copy=False, domain=[('usage','=','internal')]),
        'company_id': fields.many2one('res.company', 'Company', readonly=True)
    }

    _defaults = {
        'state_x': lambda *a: 'choose',

    }
    

    def add_workbook_format(self, cr, uid, workbook):      
        self.wbf['header'] = workbook.add_format({'bold': 1,'align': 'center','bg_color': '#FFFFDB','font_color': '#000000'})
        self.wbf['header'].set_border()

        self.wbf['header_no'] = workbook.add_format({'bold': 1,'align': 'center','bg_color': '#FFFFDB','font_color': '#000000'})
        self.wbf['header_no'].set_border()
        self.wbf['header_no'].set_align('vcenter')
                
        self.wbf['footer'] = workbook.add_format({'align':'left'})
        
        self.wbf['content_datetime'] = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss'})
        self.wbf['content_datetime'].set_left()
        self.wbf['content_datetime'].set_right()
        
        self.wbf['content_datetime_12_hr'] = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm AM/PM'})
        self.wbf['content_datetime_12_hr'].set_left()
        self.wbf['content_datetime_12_hr'].set_right()        
                
        self.wbf['content_date'] = workbook.add_format({'num_format': 'yyyy-mm-dd'})
        self.wbf['content_date'].set_left()
        self.wbf['content_date'].set_right() 
        
        self.wbf['title_doc'] = workbook.add_format({'bold': 1,'align': 'left'})
        self.wbf['title_doc'].set_font_size(12)
        
        self.wbf['company'] = workbook.add_format({'align': 'left'})
        self.wbf['company'].set_font_size(11)
        
        self.wbf['content'] = workbook.add_format()
        self.wbf['content'].set_left()
        self.wbf['content'].set_right() 
        
        self.wbf['content_float'] = workbook.add_format({'align': 'right','num_format': '#,##0.00'})
        self.wbf['content_float'].set_right() 
        self.wbf['content_float'].set_left()

        self.wbf['content_center'] = workbook.add_format({'align': 'centre'})
        
        self.wbf['content_number'] = workbook.add_format({'align': 'right'})
        self.wbf['content_number'].set_right() 
        self.wbf['content_number'].set_left() 
                
        self.wbf['content_percent'] = workbook.add_format({'align': 'right','num_format': '0.00%'})
        self.wbf['content_percent'].set_right() 
        self.wbf['content_percent'].set_left() 
                
        self.wbf['total_float'] = workbook.add_format({'bold':1,'bg_color': '#FFFFDB','align': 'right','num_format': '#,##0.00'})
        self.wbf['total_float'].set_top()
        self.wbf['total_float'].set_bottom()            
        self.wbf['total_float'].set_left()
        self.wbf['total_float'].set_right()         
        
        self.wbf['total_number'] = workbook.add_format({'align':'right','bg_color': '#FFFFDB','bold':1})
        self.wbf['total_number'].set_top()
        self.wbf['total_number'].set_bottom()            
        self.wbf['total_number'].set_left()
        self.wbf['total_number'].set_right()
        
        self.wbf['total'] = workbook.add_format({'bold':1,'bg_color': '#FFFFDB','align':'center'})
        self.wbf['total'].set_left()
        self.wbf['total'].set_right()
        self.wbf['total'].set_top()
        self.wbf['total'].set_bottom()
        
        return workbook
        

    def excel_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
            
        data = self.read(cr, uid, ids,context=context)[0]
        if len(data['branch_ids']) == 0 :
            data.update({'branch_ids': self._get_branch_ids(cr, uid, context)})
        return self._print_excel_report(cr, uid, ids, data, context=context)
    
    def _print_excel_report(self, cr, uid, ids, data, context=None):        
        
        product_ids = data['product_ids']
        branch_ids = data['branch_ids'] 
        location_ids = data['location_ids']
              
        tz = '7 hours'
        
        query_where = " "
    
        if product_ids :
            query_where += " AND quant.product_id in %s" % str(tuple(product_ids)).replace(',)', ')')
        if branch_ids :
            query_where += " AND b.id in %s" % str(tuple(branch_ids)).replace(',)', ')')
        if location_ids :
            query_where += " AND quant.location_id in %s" % str(tuple(location_ids)).replace(',)', ')')
        
        query_order = "order by branch_code,product_name,location_name"
                                                     
        query = """
                SELECT b.code as branch_code
                    , b.name as branch_name
                    , b.profit_centre as branch_profit_center
                    , quant.default_code as product_desc
                    , quant.categ_name
                    , quant.product_name
                    , quant.location_name
                    , date_part('days', now() - quant.in_date) as aging
                    , quant.qty_titipan
                    , CASE WHEN quant.location_usage='internal' THEN COALESCE((
                        SELECT sum(product_uom_qty) 
                        FROM stock_move sm 
                        LEFT JOIN stock_picking sp ON sm.picking_id=sp.id 
                        LEFT JOIN stock_picking_type spt ON sp.picking_type_id=spt.id
                        WHERE spt.code IN ('outgoing','interbranch_out') 
                        AND sp.branch_id=quant.branch_id 
                        AND sp.state not IN ('draft','cancel','done') 
                        AND sm.product_id=quant.product_id 
                        AND sm.location_id=quant.location_id),0) 
                    ELSE 0 END
                    as qty_reserved
                    , quant.qty_stock
                    , COALESCE(ppb.cost, 0.01) as harga_satuan
                FROM 
                    (SELECT l.branch_id
                        , l.warehouse_id
                        , l.complete_name as location_name
                        , l.usage as location_usage
                        , p.default_code
                        , t.name as product_name
                        , COALESCE(c.name, c2.name) as categ_name
                        , q.product_id
                        , min(q.in_date) as in_date
                        , sum(CASE WHEN q.consolidated_date IS NULL THEN q.qty ELSE 0 END) as qty_titipan
                        , sum(CASE WHEN q.consolidated_date IS NOT NULL THEN q.qty ELSE 0 END) as qty_stock
                        , sum(CASE WHEN q.reservation_id IS NOT NULL THEN q.qty ELSE 0 END) as qty_reserved
                        , q.location_id
                    FROM stock_quant q
                    INNER JOIN stock_location l ON q.location_id = l.id AND l.usage IN ('internal','transit','nrfs')
                    LEFT JOIN product_product p ON q.product_id = p.id
                    LEFT JOIN product_template t ON p.product_tmpl_id = t.id
                    LEFT JOIN product_category c ON t.categ_id = c.id 
                    LEFT JOIN product_category c2 ON c.parent_id = c2.id 
                    WHERE 1=1 AND (c.name = 'Umum' OR c2.name = 'Umum')
                    GROUP BY l.branch_id, l.warehouse_id, l.complete_name, l.usage, p.default_code, t.name, categ_name, q.product_id, q.location_id
                    ) as quant
                LEFT JOIN wtc_branch b ON quant.branch_id = b.id
                LEFT JOIN product_price_branch ppb ON ppb.product_id = quant.product_id AND ppb.warehouse_id = quant.warehouse_id
                WHERE 1=1 
                %s %s
                """ % (query_where,query_order)                     
        

        cr.execute (query)
    
        ress = cr.fetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Stock Direct Gift')
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
        worksheet.set_column('P1:P1', 20)
        worksheet.set_column('Q1:Q1', 20)   
        worksheet.set_column('R1:R1', 20)   
                        
        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        filename = 'Report Stock Direct Gift '+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report Stock Direct Gift' , wbf['title_doc'])
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
        worksheet.write('J%s' % (row+1), 'Quantity Titipan' , wbf['header'])
        worksheet.write('K%s' % (row+1), 'Amount Titipan' , wbf['header'])
        worksheet.write('L%s' % (row+1), 'Quantity Reserved' , wbf['header'])
        worksheet.write('M%s' % (row+1), 'Amount Reserved' , wbf['header'])
        worksheet.write('N%s' % (row+1), 'Harga Satuan' , wbf['header'])
        worksheet.write('O%s' % (row+1), 'Quantity Available' , wbf['header'])
        worksheet.write('P%s' % (row+1), 'Amount Available' , wbf['header'])
        worksheet.write('Q%s' % (row+1), 'Total Stock (Qty)' , wbf['header'])
        worksheet.write('R%s' % (row+1), 'Total Stock (Amt)' , wbf['header'])
    
        row+=2               
        no = 1     
        row1 = row
        
        total_qty_titipan = 0
        total_qty_reserved = 0
        total_qty_stock = 0
        total_qty = 0
        total_amt_titipan = 0
        total_amt_reserved = 0
        total_amt_stock = 0
        total_amt = 0
        total_qty_available = 0
        total_amt_available = 0
        total_price = 0
        
        for res in ress:
            branch_code = str(res[0].encode('ascii','ignore').decode('ascii')) if res[0] != None else ''
            branch_name = str(res[1].encode('ascii','ignore').decode('ascii')) if res[1] != None else ''
            profit_centre = str(res[2].encode('ascii','ignore').decode('ascii')) if res[2] != None else ''
            product_desc = str(res[3].encode('ascii','ignore').decode('ascii')) if res[3] != None else ''
            categ_name = str(res[4].encode('ascii','ignore').decode('ascii')) if res[4] != None else ''
            product_name = str(res[5].encode('ascii','ignore').decode('ascii')) if res[5] != None else ''
            location_name = str(res[6].encode('ascii','ignore').decode('ascii')) if res[8] != None else ''
            aging = res[7]
            qty_titipan = res[8]
            qty_reserved = res[9]
            qty_stock = res[10]
            harga_satuan = res[11]

            total_qty_titipan += qty_titipan
            total_amt_titipan += qty_titipan * 0.01
            total_qty_reserved += qty_reserved
            total_amt_reserved += qty_reserved * harga_satuan
            total_qty_stock += qty_stock+qty_titipan
            total_amt_stock += qty_stock * harga_satuan + qty_titipan * 0.01
            qty_available=qty_stock-qty_reserved
            amount_available=qty_available * harga_satuan
            total_qty_available+=qty_available
            total_amt_available+=amount_available
            total_price += harga_satuan 
            
            worksheet.write('A%s' % row, no , wbf['content_number'])                    
            worksheet.write('B%s' % row, branch_code , wbf['content'])
            worksheet.write('C%s' % row, branch_name , wbf['content'])
            worksheet.write('D%s' % row, profit_centre , wbf['content'])
            worksheet.write('E%s' % row, categ_name , wbf['content'])
            worksheet.write('F%s' % row, product_name , wbf['content'])
            worksheet.write('G%s' % row, product_desc , wbf['content'])
            worksheet.write('H%s' % row, location_name , wbf['content'])
            worksheet.write('I%s' % row, aging , wbf['content_float'])
            worksheet.write('J%s' % row, qty_titipan , wbf['content_float'])
            worksheet.write('K%s' % row, qty_titipan * 0.01 , wbf['content_float'])
            worksheet.write('L%s' % row, qty_reserved , wbf['content_float'])
            worksheet.write('M%s' % row, qty_reserved * harga_satuan , wbf['content_float'])
            worksheet.write('N%s' % row, harga_satuan, wbf['content_float'])
            worksheet.write('O%s' % row, qty_available, wbf['content_float'])
            worksheet.write('P%s' % row, amount_available, wbf['content_float'])
            worksheet.write('Q%s' % row, qty_titipan + qty_stock , wbf['content_float'])
            worksheet.write('R%s' % row, qty_titipan * 0.01 + qty_stock * harga_satuan, wbf['content_float'])

            no+=1
            row+=1
        
        worksheet.autofilter('A5:R%s' % (row))  
        worksheet.freeze_panes(5, 3)
        
        #TOTAL
        worksheet.merge_range('A%s:C%s' % (row,row), 'Total', wbf['total'])    
        worksheet.merge_range('D%s:I%s' % (row,row), '', wbf['total'])
        if row-1 >= row1 :
            worksheet.write_formula('J%s' % (row),'{=subtotal(9,J%s:J%s)}' % (row1, row-1), wbf['total_float'], total_qty_titipan)
            worksheet.write_formula('K%s' % (row),'{=subtotal(9,K%s:K%s)}' % (row1, row-1), wbf['total_float'], total_amt_titipan)
            worksheet.write_formula('L%s' % (row),'{=subtotal(9,L%s:L%s)}' % (row1, row-1), wbf['total_float'], total_qty_reserved)
            worksheet.write_formula('M%s' % (row),'{=subtotal(9,M%s:M%s)}' % (row1, row-1), wbf['total_float'], total_amt_reserved)
            worksheet.write_formula('N%s' % (row),'{=subtotal(9,N%s:N%s)}' % (row1, row-1), wbf['total_float'], total_price)
            worksheet.write_formula('O%s' % (row),'{=subtotal(9,O%s:O%s)}' % (row1, row-1), wbf['total_float'], total_qty_available)
            worksheet.write_formula('P%s' % (row),'{=subtotal(9,P%s:P%s)}' % (row1, row-1), wbf['total_float'], total_amt_available)
            worksheet.write_formula('Q%s' % (row),'{=subtotal(9,Q%s:Q%s)}' % (row1, row-1), wbf['total_float'], total_qty_stock)
            worksheet.write_formula('R%s' % (row),'{=subtotal(9,R%s:R%s)}' % (row1, row-1), wbf['total_float'], total_amt_stock)
        else :
            worksheet.write_blank('J%s' % (row), '', wbf['total_float'])
            worksheet.write_blank('K%s' % (row), '', wbf['total_float'])
            worksheet.write_blank('L%s' % (row), '', wbf['total_float'])
            worksheet.write_blank('M%s' % (row), '', wbf['total_float'])
            worksheet.write_blank('N%s' % (row), '', wbf['total_float'])
            worksheet.write_blank('O%s' % (row), '', wbf['total_float'])
            worksheet.write_blank('P%s' % (row), '', wbf['total_float'])
            worksheet.write_blank('Q%s' % (row), '', wbf['total_float'])
            worksheet.write_blank('R%s' % (row), '', wbf['total_float'])
        
        worksheet.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])  
                   
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_stock', 'view_report_stock_direct_gift_wizard')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.report.stock.direct.gift.wizard',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }

wtc_report_stock_direct_gift()
