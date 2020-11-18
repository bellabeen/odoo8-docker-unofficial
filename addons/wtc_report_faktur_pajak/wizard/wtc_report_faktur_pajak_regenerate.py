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

  
class wtc_report_faktur_pajak_regenerate(osv.osv_memory):
   
    _inherit = "wtc.report.faktur.pajak"

    wbf = {}


    def _print_excel_report_regenerate_faktur_pajak(self, cr, uid, ids, data, context=None):  

        model_ids = data['model_ids']        
        state_regenerate_faktur_pajak = data['state_regenerate_faktur_pajak']
        start_date = data['start_date']
        end_date = data['end_date']
        digits = self.pool['decimal.precision'].precision_get(cr, uid, 'Account')
        
        query = """
        select 
        rfp.id as rfp_id,
        rfp.name as ref,
        m.name as form_name,
        rfp.date as date,
        rfp.state as state,
        pajak.total as total_line,
        l.name as transaction_no,
        l.untaxed_amount as untaxed_amount,
        l.tax_amount as tax_amount,
        l.amount_total as total_amount,
        p.default_code as partner_code,
        p.name as partner_name,
        l.date as date_order,
        fp.name as no_faktur
        from wtc_regenerate_faktur_pajak_gabungan rfp
        left join ir_model m on m.id = rfp.model_id
        left join wtc_regenerate_faktur_pajak_gabungan_line l on l.regenerate_id = rfp.id
        left join res_partner p on p.id = l.partner_id
        left join wtc_faktur_pajak_out fp on fp.id = l.no_faktur_pajak
        left join (select regenerate_id,count(id) as total from wtc_regenerate_faktur_pajak_gabungan_line group by regenerate_id) pajak on pajak.regenerate_id = rfp.id 
        where rfp.id is not null 
        """
        
        query_end = ''
        if model_ids :
            query_end += " AND m.id in %s" % str(
                tuple(model_ids)).replace(',)', ')')  
        if start_date :
            query_end += " AND rfp.date >= '%s' " % str(start_date)
        if end_date :
            query_end += " AND rfp.date <= '%s' " % str(end_date)
        if state_regenerate_faktur_pajak :
            query_end += " AND rfp.state = '%s'" % str(state_regenerate_faktur_pajak) 
                                               
        query_order = "order by rfp.name,rfp.date"

        cr.execute(query + query_end + query_order)
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
        worksheet1.set_column('E1:E1', 20)
        worksheet1.set_column('F1:F1', 20)  


        worksheet2.set_column('B1:B1', 20)
        worksheet2.set_column('C1:C1', 20)
        worksheet2.set_column('D1:D1', 20)
        worksheet2.set_column('E1:E1', 10)
        worksheet2.set_column('F1:F1', 25)
        worksheet2.set_column('G1:G1', 20)
        worksheet2.set_column('H1:H1', 20)
        worksheet2.set_column('I1:I1', 20)
        worksheet2.set_column('J1:J1', 20)
        worksheet2.set_column('K1:K1', 20)
        worksheet2.set_column('L1:L1', 20)
        # worksheet2.set_column('M1:M1', 20)


        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        filename = 'Laporan Regenerate Faktur Pajak'+str(date)+'.xlsx'        
        worksheet1.write('A1', company_name , wbf['company'])
        worksheet1.write('A2', 'Laporan Regenerate Paktur Pajak' , wbf['title_doc'])
        worksheet1.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])
        

        # filename = 'Laporan Faktur Pajak Gabungan D'+str(date)+'.xlsx'        
        worksheet2.write('A1', company_name , wbf['company'])
        worksheet2.write('A2', 'Laporan Regenerate Faktur Pajak Details' , wbf['title_doc'])
        worksheet2.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])
        

        
        row=5
        rowsaldo = row
        row+=1
        


        worksheet1.write('A%s' % (row+1), 'No' , wbf['header'])
        worksheet1.write('B%s' % (row+1), 'Transaction Ref' , wbf['header'])
        worksheet1.write('C%s' % (row+1), 'Form Name' , wbf['header'])
        worksheet1.write('D%s' % (row+1), 'Total Tax' , wbf['header'])
        worksheet1.write('E%s' % (row+1), 'Total Untaxed' , wbf['header'])
        worksheet1.write('F%s' % (row+1), 'Grand Total' , wbf['header'])



        worksheet2.write('A%s' % (row+1), 'No' , wbf['header'])
        worksheet2.write('B%s' % (row+1), 'Transaction Ref' , wbf['header'])
        worksheet2.write('C%s' % (row+1), 'Form Name' , wbf['header'])
        worksheet2.write('D%s' % (row+1), 'Date' , wbf['header'])
        worksheet2.write('E%s' % (row+1), 'State' , wbf['header'])
        worksheet2.write('F%s' % (row+1), 'Transaction No' , wbf['header'])
        worksheet2.write('G%s' % (row+1), 'No Faktur Pajak' , wbf['header'])
        worksheet2.write('H%s' % (row+1), 'Partner Code' , wbf['header'])
        worksheet2.write('I%s' % (row+1), 'Partner Name' , wbf['header'])
        worksheet2.write('J%s' % (row+1), 'Untaxed Amount' , wbf['header'])
        worksheet2.write('K%s' % (row+1), 'Tax Amount' , wbf['header'])
        worksheet2.write('L%s' % (row+1), 'Total Amount' , wbf['header'])
        # worksheet2.write('M%s' % (row+1), 'Total Line' , wbf['header'])

        row+=2               
        no = 1     
        row1 = row
        

        untaxed_amount = 0
        tax_amount = 0
        total_amount= 0
        total_line = 0

        for res in all_lines:
           
            rfp_id = res[0]
            ref = res[1]
            form_name = res[2]
            date =  res[3]
            state = res[4]
            total_line = res[5]
            transaction_no = res[6]
            untaxed_amount =  res[7]
            tax_amount = res[8]
            total_amount = res[9]
            partner_code = res[10]
            partner_name = res[11]
            date_order = res[12]
            no_faktur = res[13]
  
    
            
            worksheet1.write('A%s' % row, no, wbf['content_number'])                    
            worksheet1.write('B%s' % row, ref, wbf['content_number'])
            worksheet1.write('C%s' % row, form_name, wbf['content'])
            worksheet1.write('D%s' % row, total_amount, wbf['content_float'])
            worksheet1.write('E%s' % row, untaxed_amount, wbf['content_float'])
            worksheet1.write('F%s' % row, tax_amount, wbf['content_float'])

            worksheet2.write('A%s' % row, no, wbf['content_number']) 
            worksheet2.write('B%s' % row, ref, wbf['content'])  
            worksheet2.write('C%s' % row, form_name, wbf['content'])
            worksheet2.write('D%s' % row, date, wbf['content_date'])
            worksheet2.write('E%s' % row, state, wbf['content'])
            worksheet2.write('F%s' % row, transaction_no, wbf['content'])
            worksheet2.write('G%s' % row, no_faktur, wbf['content_number'])
            worksheet2.write('H%s' % row, partner_code, wbf['content'])
            worksheet2.write('I%s' % row, partner_name, wbf['content'])
            worksheet2.write('J%s' % row, untaxed_amount, wbf['content_float'])
            worksheet2.write('K%s' % row, tax_amount, wbf['content_float'])
            worksheet2.write('L%s' % row, total_amount, wbf['content_float'])
            # worksheet2.write('M%s' % row, total_line, wbf['content_float'])


            no+=1
            row+=1
                
            untaxed_amount = untaxed_amount
            tax_amount = tax_amount
            total_amount = total_amount

        worksheet1.autofilter('A7:C%s' % (row))  
        worksheet1.freeze_panes(7, 3)

        worksheet2.autofilter('A7:I%s' % (row))  
        worksheet2.freeze_panes(7, 3)

       #TOTAL
        ##sheet 1
        worksheet1.merge_range('A%s:C%s' % (row,row), 'Total', wbf['total'])    
        worksheet1.write('D%s'%(row), '', wbf['total'])
        ##sheet 2
        worksheet2.merge_range('A%s:C%s' % (row,row), 'Total', wbf['total'])    
        worksheet2.merge_range('D%s:I%s' % (row,row), '', wbf['total'])
        worksheet2.write('J%s'%(row), '', wbf['total'])
        

        ##sheet 1
        formula_total_all_untaxed_dua = '{=subtotal(9,D%s:D%s)}' % (row1, row-1) 
        formula_total_all_tax_amount_tiga = '{=subtotal(9,E%s:E%s)}' % (row1, row-1) 
        formula_total_all_amount_satu = '{=subtotal(9,F%s:F%s)}' % (row1, row-1) 
        ##sheet 2
        formula_total_all_untaxed_amount = '{=subtotal(9,J%s:J%s)}' % (row1, row-1)
        formula_total_all_tax_amount = '{=subtotal(9,K%s:K%s)}' % (row1, row-1) 
        formula_total_all_amount = '{=subtotal(9,L%s:L%s)}' % (row1, row-1) 
        # formula_total_all_total_line = '{=subtotal(9,M%s:M%s)}' % (row1, row-1) 


        ##sheet 1                
        worksheet1.write_formula(row-1,3,formula_total_all_untaxed_dua, wbf['total_float'], untaxed_amount)                  
        worksheet1.write_formula(row-1,4,formula_total_all_tax_amount_tiga, wbf['total_float'], tax_amount)
        worksheet1.write_formula(row-1,5,formula_total_all_amount_satu, wbf['total_float'], total_amount) 
        ##sheet 2
        worksheet2.write_formula(row-1,9,formula_total_all_untaxed_amount, wbf['total_float'], untaxed_amount)                  
        worksheet2.write_formula(row-1,10,formula_total_all_tax_amount, wbf['total_float'], tax_amount)                  
        worksheet2.write_formula(row-1,11,formula_total_all_amount, wbf['total_float'], total_amount)
        # worksheet2.write_formula(row-1,12,formula_total_all_total_line, wbf['total_float'], total_line)


        worksheet1.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer']) 
        worksheet2.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])     
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        return True