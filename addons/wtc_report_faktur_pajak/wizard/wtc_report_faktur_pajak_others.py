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

  
class wtc_report_faktur_pajak_others(osv.osv_memory):
   
    _inherit = "wtc.report.faktur.pajak"

    wbf = {}


    def _print_excel_report_faktur_pajak_others(self, cr, uid, ids, data, context=None):  

        pajak_gabungan = data['pajak_gabungan']
        partner_ids = data['partner_ids']
        state_other_faktur_pajak = data['state_other_faktur_pajak']
        thn_penggunaan = data['thn_penggunaan']
        start_date = data['start_date']
        end_date = data['end_date']
      
        
        query = """
        select 
        fpo.name as reference, 
        fp.name as no_faktur,
        p.default_code as partner_code, 
        p.name as partner_name,
        fpo.date as date,
        fpo.pajak_gabungan as pajak_gabungan,
        fpo.thn_penggunaan as thn_penggunaan,
        fpo.tgl_terbit as tgl_terbit,
        fpo.kwitansi_no as no_kwitansi,
        fpo.untaxed_amount as untaxed_amount,
        fpo.total_amount as amount_total,
        fpo.tax_amount as tax_amount,
        fpo.state as state
        from wtc_faktur_pajak_other fpo
        inner join wtc_faktur_pajak_out fp ON fp.id = fpo.faktur_pajak_id
        inner join res_partner p ON p.id = fpo.partner_id
        where fpo.id is not null 
        """
        
        query_end = ''
        if start_date :
            query_end += " AND fpo.date >= '%s'" % str(start_date)
            
        if end_date :
            query_end += " AND fpo.date <= '%s'" % str(end_date)
                            
        if pajak_gabungan :
            query_end += " AND fpo.pajak_gabungan = 't' "
            
        if state_other_faktur_pajak :
            query_end += " AND fpo.state = '%s'" % str(state_other_faktur_pajak)
            
        if thn_penggunaan :
            query_end += " AND fpo.thn_penggunaan = '%s'" % str(thn_penggunaan)  
                
        if partner_ids :
            query_end += " AND p.id in %s" % str(tuple(partner_ids)).replace(',)', ')')
                        
        query_order = "order by fpo.name, fpo.id"

        cr.execute(query + query_end + query_order)
        all_lines = cr.fetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Laporan Faktur Pajak Other')

        worksheet.set_column('B1:B1', 20)
        worksheet.set_column('C1:C1', 20)
        worksheet.set_column('D1:D1', 20)
        worksheet.set_column('E1:E1', 25)
        worksheet.set_column('F1:F1', 15)
        worksheet.set_column('G1:G1', 10)
        worksheet.set_column('H1:H1', 10)
        worksheet.set_column('I1:I1', 20)
        worksheet.set_column('J1:J1', 18)
        worksheet.set_column('K1:K1', 20)
        worksheet.set_column('L1:L1', 20)   
        worksheet.set_column('M1:M1', 20)   
        worksheet.set_column('N1:N1', 20)   



        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        filename = 'Laporan Faktur Pajak Other'+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Laporan Paktur Pajak Other' , wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])
        

        
        row=5
        rowsaldo = row
        row+=1

        worksheet.write('A%s' % (row+1), 'No' , wbf['header'])
        worksheet.write('B%s' % (row+1), 'Reference' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'No Faktur Pajak' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'Partner Code' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'Partner Name' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'Date' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'Pajak Gabungan' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'Tahun Penggunaan' , wbf['header'])
        worksheet.write('I%s' % (row+1), 'Tanggal Tarbit' , wbf['header'])
        worksheet.write('J%s' % (row+1), 'No Kwitansi' , wbf['header'])
        worksheet.write('K%s' % (row+1), 'Untaxed Amount' , wbf['header'])
        worksheet.write('L%s' % (row+1), 'Tax Amount' , wbf['header'])
        worksheet.write('M%s' % (row+1), 'Amount Total' , wbf['header'])
        worksheet.write('N%s' % (row+1), 'State' , wbf['header'])
           

        row+=2               
        no = 1     
        row1 = row
        
        
        untaxed_amount = 0
        tax_amount = 0
        amount_total= 0

        for res in all_lines:
           

            reference = res[0].encode('ascii','ignore').decode('ascii') if res[0] != None else ''
            no_faktur  = res[1].encode('ascii','ignore').decode('ascii') if res[1] != None else ''
            partner_code  = res[2]
            partner_name = res[3].encode('ascii','ignore').decode('ascii') if res[3] != None else ''
            date = res[4].encode('ascii','ignore').decode('ascii') if res[3] != None else ''
            pajak_gabungan = res[5] if res[5] != 'True' else 'False'
            thn_penggunaan = res[6]
            tgl_terbit = res[7]
            no_kwitansi = res[8]
            untaxed_amount = res[9]
            amount_total = res[10]
            tax_amount = res[11]
            state = res[12]

        
            worksheet.write('A%s' % row, no, wbf['content_number'])                    
            worksheet.write('B%s' % row, reference, wbf['content'])
            worksheet.write('C%s' % row, no_faktur, wbf['content_number'])
            worksheet.write('D%s' % row, partner_code, wbf['content'])
            worksheet.write('E%s' % row, partner_name, wbf['content'])
            worksheet.write('F%s' % row, date, wbf['content_date'])
            worksheet.write('G%s' % row, pajak_gabungan, wbf['content'])
            worksheet.write('H%s' % row, thn_penggunaan, wbf['content'])
            worksheet.write('I%s' % row, tgl_terbit, wbf['content_date'])
            worksheet.write('J%s' % row, no_kwitansi, wbf['content'])
            worksheet.write('K%s' % row, state, wbf['content'])

            worksheet.write('L%s' % row, untaxed_amount, wbf['content_float'])
            worksheet.write('M%s' % row, tax_amount, wbf['content_float'])
            worksheet.write('N%s' % row, amount_total, wbf['content_float'])
           

            no+=1
            row+=1
                
            untaxed_amount = untaxed_amount
            tax_amount = tax_amount
            amount_total = amount_total

        worksheet.autofilter('A7:J%s' % (row))  
        worksheet.freeze_panes(7, 3)

         #TOTAL
        worksheet.merge_range('A%s:C%s' % (row,row), 'Total', wbf['total'])    
        worksheet.merge_range('D%s:J%s' % (row,row), '', wbf['total'])
        worksheet.write('L%s'%(row), '', wbf['total'])


        formula_total_untaxed_amount = '{=subtotal(9,L%s:L%s)}' % (row1, row-1) 
        formula_total_tax_amount = '{=subtotal(9,M%s:M%s)}' % (row1, row-1) 
        formula_total_amount = '{=subtotal(9,N%s:N%s)}' % (row1, row-1) 

             
        worksheet.write_formula(row-1,11,formula_total_untaxed_amount, wbf['total_float'], untaxed_amount)                  
        worksheet.write_formula(row-1,12,formula_total_tax_amount, wbf['total_float'], tax_amount)
        worksheet.write_formula(row-1,13,formula_total_amount, wbf['total_float'], amount_total) 



        worksheet.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])
        
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()


        return True


