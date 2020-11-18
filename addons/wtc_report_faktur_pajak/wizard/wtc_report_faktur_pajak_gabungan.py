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

  
class wtc_report_faktur_pajak_gabungan(osv.osv_memory):
   
    _inherit = "wtc.report.faktur.pajak"

    wbf = {}


    def _print_excel_report_faktur_pajak_gabungan(self, cr, uid, ids, data, context=None):  



        branch_ids = data['branch_ids']
        division = data['division']
        partner_ids = data['partner_ids']        
        state_gabungan_faktur_pajak = data['state_gabungan_faktur_pajak']
        start_date = data['start_date']
        end_date = data['end_date']
        digits = self.pool['decimal.precision'].precision_get(cr, uid, 'Account')
              
        query = """
            SELECT 
            fpg.id as fpg_id, 
            b.code as branch_code, 
            fpg.division as division, 
            fpg.name as transaction_ref, 
            fp.name as code_pajak, 
            fpg.date as date, 
            fpg.start_date as start_date, 
            fpg.end_date as end_date,
            p.default_code as partner_code, 
            p.name as partner_name, 
            fpg.date_pajak as tgl_document, 
            pajak.total as count_line,m.name as model_name,
            l.name as transaction_no, l.date as transaction_date, 
            l.untaxed_amount as untaxed_amount, 
            l.tax_amount as tax_amount,
            l.total_amount as total_amount,
            fpg.state as state
            FROM wtc_faktur_pajak_gabungan fpg
            left join wtc_branch b on b.id = fpg.branch_id
            left join wtc_faktur_pajak_out fp on fp.id = fpg.faktur_pajak_id
            left join res_partner p ON p.id = fpg.customer_id
            left join wtc_faktur_pajak_gabungan_line l ON l.pajak_gabungan_id = fpg.id
            left join ir_model m ON m.model = l.model
            left join (select pajak_gabungan_id,count(id) as total from wtc_faktur_pajak_gabungan_line group by pajak_gabungan_id) pajak on pajak.pajak_gabungan_id = fpg.id    
            where fpg.name is not null        
        """
        query_end = ''
        if branch_ids :
            query_end += " AND fpg.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        if partner_ids :
            query_end += " AND fpg.customer_id in %s" % str(
                tuple(partner_ids)).replace(',)', ')')  
        if start_date :
            query_end += " AND fpg.date >= '%s' " % str(start_date)
        if end_date :
            query_end += " AND fpg.date <= '%s' " % str(end_date)
        if division :
            query_end += " AND fpg.division = '%s'" % str(division) 
        if state_gabungan_faktur_pajak :
            query_end += " AND fpg.state = '%s'" % str(state_gabungan_faktur_pajak) 
                                               
        query_order = "order by b.code,fpg.date"

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
  


        worksheet2.set_column('B1:B1', 13)
        worksheet2.set_column('C1:C1', 10)
        worksheet2.set_column('D1:D1', 20)
        worksheet2.set_column('E1:E1', 20)
        worksheet2.set_column('F1:F1', 20)
        worksheet2.set_column('G1:G1', 20)
        worksheet2.set_column('H1:H1', 20)
        worksheet2.set_column('I1:I1', 25)
        worksheet2.set_column('J1:J1', 20)
        worksheet2.set_column('K1:K1', 15)
        worksheet2.set_column('L1:L1', 20)
        worksheet2.set_column('M1:M1', 20)
        worksheet2.set_column('N1:N1', 20)
        worksheet2.set_column('O1:O1', 20)


        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        filename = 'Laporan Faktur Pajak Gabungan'+str(date)+'.xlsx'        
        worksheet1.write('A1', company_name , wbf['company'])
        worksheet1.write('A2', 'Laporan Paktur Pajak Gabungan' , wbf['title_doc'])
        worksheet1.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])
        

        # filename = 'Laporan Faktur Pajak Gabungan D'+str(date)+'.xlsx'        
        worksheet2.write('A1', company_name , wbf['company'])
        worksheet2.write('A2', 'Laporan Paktur Pajak Gabungan Details' , wbf['title_doc'])
        worksheet2.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])
        
        
        row=5
        rowsaldo = row
        row+=1

        worksheet1.write('A%s' % (row+1), 'No' , wbf['header'])
        worksheet1.write('B%s' % (row+1), 'Transaction Ref' , wbf['header'])
        worksheet1.write('C%s' % (row+1), 'Partner' , wbf['header'])
        worksheet1.write('D%s' % (row+1), 'Total Tax' , wbf['header'])
        worksheet1.write('E%s' % (row+1), 'Total Untaxed' , wbf['header'])
        worksheet1.write('F%s' % (row+1), 'Grand Total' , wbf['header'])



        worksheet2.write('A%s' % (row+1), 'No' , wbf['header'])
        worksheet2.write('B%s' % (row+1), 'Branch' , wbf['header'])
        worksheet2.write('C%s' % (row+1), 'Division' , wbf['header'])
        worksheet2.write('D%s' % (row+1), 'No Faktur Pajak' , wbf['header'])
        worksheet2.write('E%s' % (row+1), 'Create Date' , wbf['header'])
        worksheet2.write('F%s' % (row+1), 'Start Date' , wbf['header'])
        worksheet2.write('G%s' % (row+1), 'End Date' , wbf['header'])
        worksheet2.write('H%s' % (row+1), 'Code Partner' , wbf['header'])
        worksheet2.write('I%s' % (row+1), 'Partner' , wbf['header'])
        worksheet2.write('J%s' % (row+1), 'Document Date' , wbf['header'])
        worksheet2.write('K%s' % (row+1), 'State' , wbf['header'])
        worksheet2.write('L%s' % (row+1), 'Transaction No' , wbf['header'])
        worksheet2.write('M%s' % (row+1), 'Tax Amount' , wbf['header'])
        worksheet2.write('N%s' % (row+1), 'Untaxed Amount' , wbf['header'])
        worksheet2.write('O%s' % (row+1), 'Total Amount' , wbf['header'])
           

        row+=2               
        no = 1     
        row1 = row
        

        total_amount= 0
        untaxed_amount = 0
        tax_amount = 0
    

        for res in all_lines:

           
            fpg_id = res[0]
            branch_code = res[1].encode('ascii','ignore').decode('ascii') if res[1] != None else ''
            division = res[2].encode('ascii','ignore').decode('ascii') if res[2] != None else ''
            transaction_ref =  res[3].encode('ascii','ignore').decode('ascii') if res[3] != None else ''
            code_pajak = res[4]
            date = res[5].encode('ascii','ignore').decode('ascii') if res[5] != None else ''
            start_date = res[6]
            end_date =  res[7]
            partner_code = res[8]
            partner_name = res[9]
            tgl_document = res[10]
            count_line = res[11]
            model_name = res[12]
            transaction_no = res[13].encode('ascii','ignore').decode('ascii') if res[13] != None else ''
            transaction_date = res[14].encode('ascii','ignore').decode('ascii') if res[14] != None else ''
            untaxed_amount = res[15]            
            tax_amount = res[16]
            total_amount = res[17]
            state = res[18]

            
        
            worksheet1.write('A%s' % row, no, wbf['content_number'])                    
            worksheet1.write('B%s' % row, transaction_ref, wbf['content_number'])
            worksheet1.write('C%s' % row, partner_name, wbf['content'])
            worksheet1.write('D%s' % row, total_amount, wbf['content_float'])
            worksheet1.write('E%s' % row, untaxed_amount, wbf['content_float'])
            worksheet1.write('F%s' % row, tax_amount, wbf['content_float'])

            worksheet2.write('A%s' % row, no, wbf['content_number']) 
            worksheet2.write('B%s' % row, branch_code, wbf['content'])  
            worksheet2.write('C%s' % row, division, wbf['content'])
            worksheet2.write('D%s' % row, code_pajak, wbf['content'])
            worksheet2.write('E%s' % row, date, wbf['content_date'])
            worksheet2.write('F%s' % row, start_date, wbf['content_date'])
            worksheet2.write('G%s' % row, end_date, wbf['content'])
            worksheet2.write('H%s' % row, partner_code, wbf['content_number'])
            worksheet2.write('I%s' % row, partner_name, wbf['content'])
            worksheet2.write('J%s' % row, tgl_document, wbf['content_float'])
            worksheet2.write('K%s' % row, state, wbf['content'])
            worksheet2.write('L%s' % row, transaction_ref, wbf['content'])
            worksheet2.write('M%s' % row, total_amount, wbf['content_float'])
            worksheet2.write('N%s' % row, untaxed_amount, wbf['content_float'])
            worksheet2.write('O%s' % row, tax_amount, wbf['content_float'])

    
            no+=1
            row+=1
                
            total_amount = total_amount
            untaxed_amount = untaxed_amount
            tax_amount = tax_amount

        worksheet1.autofilter('A7:C%s' % (row))  
        worksheet1.freeze_panes(7, 3)

        worksheet2.autofilter('A7:L%s' % (row))  
        worksheet2.freeze_panes(7, 3)
        
        #TOTAL
        ##sheet 1
        worksheet1.merge_range('A%s:C%s' % (row,row), 'Total', wbf['total'])    
        worksheet1.write('D%s'%(row), '', wbf['total'])
        ##sheet 2
        worksheet2.merge_range('A%s:C%s' % (row,row), 'Total', wbf['total'])    
        worksheet2.merge_range('D%s:L%s' % (row,row), '', wbf['total'])
        worksheet2.write('M%s'%(row), '', wbf['total'])
        

        ##sheet 1
        formula_total_all_amount_satu = '{=subtotal(9,D%s:D%s)}' % (row1, row-1) 
        formula_total_all_untaxed_dua = '{=subtotal(9,E%s:E%s)}' % (row1, row-1) 
        formula_total_all_tax_amount_tiga = '{=subtotal(9,F%s:F%s)}' % (row1, row-1) 
        ##sheet 2
        formula_total_all_amount = '{=subtotal(9,M%s:M%s)}' % (row1, row-1) 
        formula_total_all_untaxed_amount = '{=subtotal(9,N%s:N%s)}' % (row1, row-1) 
        formula_total_all_tax_amount = '{=subtotal(9,O%s:O%s)}' % (row1, row-1) 


        ##sheet 1
        worksheet1.write_formula(row-1,3,formula_total_all_amount_satu, wbf['total_float'], total_amount)                  
        worksheet1.write_formula(row-1,4,formula_total_all_untaxed_dua, wbf['total_float'], untaxed_amount)                  
        worksheet1.write_formula(row-1,5,formula_total_all_tax_amount_tiga, wbf['total_float'], tax_amount)
        ##sheet 2
        worksheet2.write_formula(row-1,12,formula_total_all_amount, wbf['total_float'], total_amount)                  
        worksheet2.write_formula(row-1,13,formula_total_all_untaxed_amount, wbf['total_float'], untaxed_amount)                  
        worksheet2.write_formula(row-1,14,formula_total_all_tax_amount, wbf['total_float'], tax_amount)


        worksheet1.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer']) 
        worksheet2.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])     
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        return True


