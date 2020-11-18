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

class wtc_report_stock_unit_location(osv.osv_memory):
   
    _inherit = "wtc.report.stock.unit.wizard"

    wbf = {}
    
    def _print_excel_report_location(self, cr, uid, ids, data, context=None):        
        
        # product_ids = data['product_ids']
        branch_ids = data['branch_ids'] 
        location_ids = data['location_ids']
        options = data['options']
              
     
        query = """
            select b.code
            , b.name
            , sl.complete_name
            , sl.jenis
            , sl.start_date
            , sl.end_date
            , sl.maximum_qty as kapasitas
            , COALESCE(sc.qty,0) as jumlah_stok
            from stock_location sl
            inner join wtc_branch b on sl.branch_id = b.id
            left join (
              select q.location_id, coalesce(c3.name, coalesce(c2.name, c.name)) as categ, sum(q.qty) as qty
              from stock_quant q
              left join product_product p on q.product_id = p.id 
              left join product_template pt on p.product_tmpl_id = pt.id
              left join product_category c on pt.categ_id = c.id 
              left join product_category c2 on c.parent_id = c2.id
              left join product_category c3 on c2.parent_id = c3.id
              where c3.name = 'Unit' or c2.name = 'Unit' or c.name = 'Unit'
              group by q.location_id, categ
            ) as sc on sl.id = sc.location_id
            where sl.usage = 'internal'  
            """
       
        
        # categ_ids = self.pool.get('product.category').get_child_ids(cr,uid,ids,'Unit') 

        # query +="and h.id in %s" % str(
        #     tuple(categ_ids)).replace(',)', ')')

        query_where=""
        if branch_ids :
            query_where +=" AND  sl.branch_id in %s " % str(
                tuple(branch_ids)).replace(',)', ')')
        
        if location_ids :
            query_where+="AND  sl.id  in %s" % str(
                tuple(location_ids)).replace(',)', ')')
          
        query_order="order by b.code, sl.complete_name "

        cr.execute (query+query_where+query_order)
        ress = cr.fetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Stock Unit Per Location')
        worksheet.set_column('B1:B1', 13)
        worksheet.set_column('C1:C1', 20)
        worksheet.set_column('D1:D1', 20)
        worksheet.set_column('E1:E1', 20)
        worksheet.set_column('F1:F1', 13)
        worksheet.set_column('G1:G1', 13)
        worksheet.set_column('H1:H1', 20)
        worksheet.set_column('I1:I1', 22)
        worksheet.set_column('J1:J1', 13)
        worksheet.set_column('K1:K1', 15)
        worksheet.set_column('L1:L1', 15)
        worksheet.set_column('M1:M1', 17)
        worksheet.set_column('N1:N1', 9)
        worksheet.set_column('O1:O1', 20)
        worksheet.set_column('P1:P1', 12)
        worksheet.set_column('Q1:Q1', 12)
        worksheet.set_column('R1:R1', 12)
        worksheet.set_column('S1:S1', 12)
        worksheet.set_column('T1:T1', 20)
        worksheet.set_column('U1:U1', 20)
                        
        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        filename = 'Stock Unit Per Location '+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Stock Unit Per Location' , wbf['title_doc'])
 
        row=3
        rowsaldo = row
        row+=1
        worksheet.write('A%s' % (row+1), 'No' , wbf['header'])
        worksheet.write('B%s' % (row+1), 'Kode Cabang' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'Cabang' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'Nama Lokasi' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'Jenis Lokasi' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'Start Date' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'End Date' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'Kapasitas' , wbf['header'])
        worksheet.write('I%s' % (row+1), 'Jumlah Stok' , wbf['header'])

        row+=2 
                
        no = 1     
        row1 = row
        
                
        for res in ress:
            code = str(res[0].encode('ascii','ignore').decode('ascii')) if res[0] != None else ''
            name = str(res[1].encode('ascii','ignore').decode('ascii')) if res[1] != None else ''
            complete_name = str(res[2].encode('ascii','ignore').decode('ascii')) if res[2] != None else ''
            jenis = res[3]
            start_date = res[4]
            end_date = res[5]
            kapasitas = res[6]
            jumlah_stok = res[7]
            
            worksheet.write('A%s' % row, no , wbf['content_number'])                    
            worksheet.write('B%s' % row, code , wbf['content'])
            worksheet.write('C%s' % row, name , wbf['content'])
            worksheet.write('D%s' % row, complete_name , wbf['content'])
            worksheet.write('E%s' % row, jenis , wbf['content'])
            worksheet.write('F%s' % row, start_date , wbf['content_date'])
            worksheet.write('G%s' % row, end_date , wbf['content_date'])
            worksheet.write('H%s' % row, kapasitas , wbf['content_number']) 
            worksheet.write('I%s' % row, jumlah_stok , wbf['content_number'])  
                                  
            no+=1
            row+=1
                    
        worksheet.autofilter('A5:I%s' % (row))  
        worksheet.freeze_panes(5, 3)
        
        #TOTAL
        # worksheet.merge_range('A%s:C%s' % (row,row), 'Total', wbf['total'])  
        # worksheet.merge_range('D%s:F%s' % (row,row), 'Total', wbf['total'])    
 
                       
        # formula_total_jumlah =  '{=subtotal(9,G%s:G%s)}' % (row1, row-1)
        # formula_total_jumlah_picking =  '{=subtotal(9,H%s:H%s)}' % (row1, row-1)
        # formula_total_stock_avb =  '{=subtotal(9,I%s:I%s)}' % (row1, row-1)
                  
        # worksheet.write_formula(row-1,6,formula_total_jumlah, wbf['total_number'], total_jumlah)
        # worksheet.write_formula(row-1,7,formula_total_jumlah_picking, wbf['total_number'], total_jumlah_picking)
        # worksheet.write_formula(row-1,8,formula_total_stock_avb, wbf['total_number'], total_stock_avb)
        

        # worksheet.write('S%s'%(row), '', wbf['total'])  
        worksheet.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])  
                   
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_stock', 'view_wtc_report_stock_unit_wizard')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.report.stock.unit.wizard',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }