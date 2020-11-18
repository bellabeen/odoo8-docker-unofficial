import time
from lxml import etree
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

  
class wtc_report_faktur_pajak_generate(osv.osv_memory):
   
    _inherit = "wtc.report.faktur.pajak"

    wbf = {}


    def _print_excel_report_faktur_pajak_generate(self, cr, uid, ids, data, context=None):  
        thn_penggunaan = data['thn_penggunaan']
        state_generate_faktur_pajak = data['state_generate_faktur_pajak']
        start_date = data['start_date']
        end_date = data['end_date']
        
        where_thn_penggunaan = " 1=1 "
        if thn_penggunaan :
            where_thn_penggunaan = " gfp.thn_penggunaan = '%s'" % str(thn_penggunaan)
            
        where_start_date = " 1=1 "
        if start_date :
            where_start_date = " gfp.date >= '%s'" % str(start_date)
        where_end_date = " 1=1 "
        if end_date :
            where_end_date = " gfp.date <= '%s'" % str(end_date)
            
        where_state_generate_faktur_pajak = " 1=1 "
        if state_generate_faktur_pajak  :
            where_state_generate_faktur_pajak = " gfp.state = '%s'" % str(state_generate_faktur_pajak)
      
        
        query_faktur_pajak = """
        select 
        gfp.id as gfp_id,
        gfp.name as gfp_name,
        gfp.no_document as gfp_no_document,
        gfp.date as gfp_date,
        gfp.thn_penggunaan as gfp_thn,
        gfp.tgl_terbit as gfp_tgl_terbit,
        gfp.counter_start as gfp_counter_start,
        gfp.counter_end as gfp_counter_end,
        gfp.prefix as gfp_prefix,
        gfp.padding as gfp_padding,
        gfp.state as state,
        pajak.total as pajak_total,
        fp.name as fp_code,
        fp.state as fp_state
        from wtc_faktur_pajak gfp
        inner join wtc_faktur_pajak_out fp on fp.faktur_pajak_id = gfp.id 
        left join (select faktur_pajak_id,count(id) as total from wtc_faktur_pajak_out group by faktur_pajak_id) pajak on pajak.faktur_pajak_id = gfp.id           
        """
        
        where = "WHERE " + where_thn_penggunaan + " AND " + where_state_generate_faktur_pajak + " AND " + where_start_date + " AND " + where_end_date
        order = "order by gfp.name,gfp.date"

        cr.execute(query_faktur_pajak + where + order)
        all_lines = cr.fetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet1 = workbook.add_worksheet('Laporan Faktur Pajak')
        worksheet2 = workbook.add_worksheet('Laporan Faktur Pajak D')

        worksheet1.set_column('B1:B1', 20)
        worksheet1.set_column('C1:C1', 20)
        worksheet1.set_column('D1:D1', 20)
  

        worksheet2.set_column('B1:B1', 20)
        worksheet2.set_column('C1:C1', 20)
        worksheet2.set_column('D1:D1', 20)
        worksheet2.set_column('E1:E1', 20)
        worksheet2.set_column('F1:F1', 20)
        worksheet2.set_column('G1:G1', 20)
        worksheet2.set_column('H1:H1', 20)
        worksheet2.set_column('I1:I1', 20)
        worksheet2.set_column('J1:J1', 20)
        worksheet2.set_column('K1:K1', 20)
        worksheet2.set_column('L1:L1', 20)
        worksheet2.set_column('M1:M1', 20)
        worksheet2.set_column('N1:N1', 20)
  

        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        filename = 'Laporan Generate Faktur Pajak'+str(date)+'.xlsx'        
        worksheet1.write('A1', company_name , wbf['company'])
        worksheet1.write('A2', 'Laporan Generate Paktur Pajak' , wbf['title_doc'])
        worksheet1.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])
        

        # filename = 'Laporan Faktur Pajak Gabungan D'+str(date)+'.xlsx'        
        worksheet2.write('A1', company_name , wbf['company'])
        worksheet2.write('A2', 'Laporan Generate Paktur Pajak Details' , wbf['title_doc'])
        worksheet2.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])
        
        
        row=5
        rowsaldo = row
        row+=1

        worksheet1.write('A%s' % (row+1), 'No' , wbf['header'])
        worksheet1.write('B%s' % (row+1), 'Generate Number' , wbf['header'])
        worksheet1.write('C%s' % (row+1), 'No Document' , wbf['header'])
        worksheet1.write('D%s' % (row+1), 'Total Generated' , wbf['header'])


        worksheet2.write('A%s' % (row+1), 'No' , wbf['header'])
        worksheet2.write('B%s' % (row+1), 'Generate Ref' , wbf['header'])
        worksheet2.write('C%s' % (row+1), 'No Document' , wbf['header'])
        worksheet2.write('D%s' % (row+1), 'Date' , wbf['header'])
        worksheet2.write('E%s' % (row+1), 'Thn Penggunaan' , wbf['header'])
        worksheet2.write('F%s' % (row+1), 'Tgl Terbit' , wbf['header'])
        worksheet2.write('G%s' % (row+1), 'Counter Start' , wbf['header'])
        worksheet2.write('H%s' % (row+1), 'Counter End' , wbf['header'])
        worksheet2.write('I%s' % (row+1), 'Prefix' , wbf['header'])
        worksheet2.write('J%s' % (row+1), 'Padding' , wbf['header'])
        worksheet2.write('K%s' % (row+1), 'State' , wbf['header'])
        worksheet2.write('L%s' % (row+1), 'Code Faktur Pajak' , wbf['header'])
        worksheet2.write('M%s' % (row+1), 'State' , wbf['header'])
        worksheet2.write('N%s' % (row+1), '# Generated' , wbf['header'])


        row+=2               
        no = 1     
        row1 = row
        
        pajak_total = 0

        for res in all_lines:

            gfp_id = res[0]
            gfp_name = res[1].encode('ascii','ignore').decode('ascii') if res[1] != None else ''
            gfp_no_document = res[2].encode('ascii','ignore').decode('ascii') if res[2] != None else ''
            gfp_date =  res[3].encode('ascii','ignore').decode('ascii') if res[3] != None else ''
            gfp_thn = res[4]
            gfp_tgl_terbit = res[5].encode('ascii','ignore').decode('ascii') if res[5] != None else ''
            gfp_counter_start = res[6]
            gfp_counter_end =  res[7]
            gfp_prefix = res[8]
            gfp_padding = res[9]
            state = res[10]
            pajak_total = res[11]
            fp_code = res[12].encode('ascii','ignore').decode('ascii') if res[12] != None else ''
            fp_state = res[13].encode('ascii','ignore').decode('ascii') if res[13] != None else ''
           
        
            worksheet1.write('A%s' % row, no, wbf['content_number'])                    
            worksheet1.write('B%s' % row, gfp_name, wbf['content_number'])
            worksheet1.write('C%s' % row, gfp_no_document, wbf['content'])
            worksheet1.write('D%s' % row, pajak_total, wbf['content_float'])

            worksheet2.write('A%s' % row, no, wbf['content_number']) 
            worksheet2.write('B%s' % row, gfp_name, wbf['content'])  
            worksheet2.write('C%s' % row, gfp_no_document, wbf['content'])
            worksheet2.write('D%s' % row, gfp_date, wbf['content'])
            worksheet2.write('E%s' % row, gfp_thn, wbf['content'])
            worksheet2.write('F%s' % row, gfp_tgl_terbit, wbf['content_date'])
            worksheet2.write('G%s' % row, gfp_counter_start, wbf['content'])
            worksheet2.write('H%s' % row, gfp_counter_end, wbf['content'])
            worksheet2.write('I%s' % row, gfp_prefix, wbf['content'])
            worksheet2.write('J%s' % row, gfp_padding, wbf['content'])
            worksheet2.write('K%s' % row, state, wbf['content'])
            worksheet2.write('L%s' % row, fp_code, wbf['content'])
            worksheet2.write('M%s' % row, fp_state, wbf['content'])
            worksheet2.write('N%s' % row, pajak_total, wbf['content_float'])

    
            no+=1
            row+=1

            pajak_total = pajak_total

        worksheet1.autofilter('A7:C%s' % (row))  
        worksheet1.freeze_panes(7, 3)

        worksheet2.autofilter('A7:M%s' % (row))  
        worksheet2.freeze_panes(7, 3)
        
        #TOTAL
        ##sheet 1
        worksheet1.merge_range('A%s:C%s' % (row,row), 'Total', wbf['total'])    
        worksheet1.write('D%s'%(row), '', wbf['total'])
      

        ##sheet 1
        formula_total_pajak_total = '{=subtotal(9,D%s:D%s)}' % (row1, row-1) 
 

        ##sheet 1
        worksheet1.write_formula(row-1,3,formula_total_pajak_total, wbf['total_float'], pajak_total)                  

        worksheet1.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer']) 
        worksheet2.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])     
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        return True


