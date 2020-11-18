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

  
class wtc_report_pettycash_in(osv.osv_memory):
   
    _inherit = "wtc.report.all.pettycash"

    wbf = {}


    def _print_excel_report_pettycash_in(self, cr, uid, ids, data, context=None):  
        branch_ids = data['branch_ids']
        division = data['division']
        journal_id = data['journal_id'][0] if data['journal_id'] else False
        state_pettycash_in = data['state_pettycash_in']
        start_date = data['start_date']
        end_date = data['end_date']
        pettycash_id = data['pettycash_id'][0] if data['pettycash_id'] else False
        digits = self.pool['decimal.precision'].precision_get(cr, uid, 'Account')
      
        
        query = """
            SELECT 
            pci.id as pci_id, 
            pci.name as pci_name, 
            b.code as branch_code, 
            bd.code as branch_destination_code, 
            pci.division as pci_division, 
            pci.date as pci_date,
            pco.name as pco_name,
            pci.amount as pci_amount,
            j.name as journal_name,
            pci.state as pci_state,
            a.name as account_name,
            l.name as line_name,
            l.amount as line_amount
            FROM wtc_pettycash_in pci
            inner join wtc_pettycash_in_line l ON l.pettycash_id = pci.id
            left join wtc_branch b ON b.id = pci.branch_id
            left join wtc_branch bd ON bd.id = pci.branch_destination_id
            left join account_journal j ON j.id = pci.journal_id
            left join account_account a ON a.id = l.account_id
            left join wtc_pettycash pco ON pco.id = pci.pettycash_id
            where pci.id is not null       
            """
            
        query_end = ''
        if branch_ids :
            query_end += " AND pci.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        if start_date :
            query_end += " AND pci.date >= '%s' " % str(start_date)
        if end_date :
            query_end += " AND pci.date <= '%s' " % str(end_date)
        if division :
            query_end += " AND pci.division = '%s'" % str(division) 
        if state_pettycash_in :
            query_end += " AND pci.state = '%s'" % str(state_pettycash_in) 
        if journal_id :
            query_end += " AND pci.journal_id = '%s'" % str(journal_id)             
        if pettycash_id :
            query_end += " AND pci.pettycash_id = '%s'" % str(pettycash_id)
            
        query_order = "order by b.code,pci.date"

        cr.execute(query + query_end + query_order)
        all_lines = cr.fetchall()

        # print ">>>>>>>>>>>>>>>>>>",(query + query_end + query_order)
        # all_lines = cr.dictfetchall()


        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet1 = workbook.add_worksheet('Report Petty Cash In')
        worksheet2 = workbook.add_worksheet('Report Petty Cash In Details')

        worksheet1.set_column('B1:B1', 20)
        worksheet1.set_column('C1:C1', 20)
        worksheet1.set_column('D1:D1', 20)
        worksheet1.set_column('E1:E1', 20)

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


        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        filename = 'Report Petty Cash In'+str(date)+'.xlsx'        
        worksheet1.write('A1', company_name , wbf['company'])
        worksheet1.write('A2', 'Report Petty Cash In' , wbf['title_doc'])
        worksheet1.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])
        

        # filename = 'Laporan Faktur Pajak Gabungan D'+str(date)+'.xlsx'        
        worksheet2.write('A1', company_name , wbf['company'])
        worksheet2.write('A2', 'Report Petty Cash In Details' , wbf['title_doc'])
        worksheet2.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])
        
        
        row=5
        rowsaldo = row
        row+=1

        worksheet1.write('A%s' % (row+1), 'No' , wbf['header'])
        worksheet1.write('B%s' % (row+1), 'Petty Cash Ref' , wbf['header'])
        worksheet1.write('C%s' % (row+1), 'Branch Code' , wbf['header'])
        worksheet1.write('D%s' % (row+1), 'Pettycash Out Ref' , wbf['header'])
        worksheet1.write('E%s' % (row+1), 'Total Amount' , wbf['header'])


        worksheet2.write('A%s' % (row+1), 'No' , wbf['header'])
        worksheet2.write('B%s' % (row+1), 'Petty Cash Ref' , wbf['header'])
        worksheet2.write('C%s' % (row+1), 'Branch' , wbf['header'])
        worksheet2.write('D%s' % (row+1), 'Branch Destination' , wbf['header'])
        worksheet2.write('E%s' % (row+1), 'Petty Cash Out Ref' , wbf['header'])
        worksheet2.write('F%s' % (row+1), 'Division' , wbf['header'])
        worksheet2.write('G%s' % (row+1), 'Date' , wbf['header'])
        worksheet2.write('H%s' % (row+1), 'Journal' , wbf['header'])
        worksheet2.write('I%s' % (row+1), 'Description' , wbf['header'])
        worksheet2.write('J%s' % (row+1), 'State' , wbf['header'])
        worksheet2.write('K%s' % (row+1), 'Total Amount' , wbf['header'])


        row+=2               
        no = 1     
        row1 = row
        
        line_amount = 0

        for res in all_lines:

            pci_id = res[0]
            pci_name = res[1].encode('ascii','ignore').decode('ascii') if res[1] != None else ''
            branch_code = res[2].encode('ascii','ignore').decode('ascii') if res[2] != None else ''
            branch_destination_code =  res[3].encode('ascii','ignore').decode('ascii') if res[3] != None else ''
            pci_division = res[4].encode('ascii','ignore').decode('ascii') if res[4] != None else ''
            pci_date = res[5]
            pco_name = res[6]
            pci_amount =  res[7] if res[7] != None else 0
            journal_name = res[8]
            pci_state = res[9]
            account_name = res[10]
            line_name = res[11].encode('ascii','ignore').decode('ascii') if res[11] != None else ''
            line_amount = res[12]
           
           
    
            worksheet1.write('A%s' % row, no, wbf['content_number'])                    
            worksheet1.write('B%s' % row, pci_name, wbf['content_number'])
            worksheet1.write('C%s' % row, branch_code, wbf['content'])
            worksheet1.write('D%s' % row, pco_name, wbf['content_float'])
            worksheet1.write('E%s' % row, line_amount, wbf['content_float'])

            worksheet2.write('A%s' % row, no, wbf['content_number']) 
            worksheet2.write('B%s' % row, pci_name, wbf['content'])  
            worksheet2.write('C%s' % row, branch_code, wbf['content'])
            worksheet2.write('D%s' % row, branch_destination_code, wbf['content'])
            worksheet2.write('E%s' % row, pco_name, wbf['content'])
            worksheet2.write('F%s' % row, pci_division, wbf['content'])
            worksheet2.write('G%s' % row, pci_date, wbf['content_date'])
            worksheet2.write('H%s' % row, journal_name, wbf['content'])
            worksheet2.write('I%s' % row, line_name, wbf['content'])  
            worksheet2.write('J%s' % row, pco_state, wbf['content'])      
            worksheet2.write('K%s' % row, line_amount, wbf['content_float'])
            
  
    
            no+=1
            row+=1


            line_amount = line_amount
            

        worksheet1.autofilter('A7:D%s' % (row))  
        worksheet1.freeze_panes(7, 3)

        worksheet2.autofilter('A7:J%s' % (row))  
        worksheet2.freeze_panes(7, 3)

        #TOTAL
        ##sheet 1
        worksheet1.merge_range('A%s:D%s' % (row,row), 'Total', wbf['total'])    
        worksheet1.write('E%s'%(row), '', wbf['total'])
        ##sheet 2
        worksheet2.merge_range('A%s:C%s' % (row,row), 'Total', wbf['total'])    
        worksheet2.merge_range('D%s:J%s' % (row,row), '', wbf['total'])
        worksheet2.write('K%s'%(row), '', wbf['total'])
        

        ##sheet 1
        formula_total_line_amount_satu = '{=subtotal(9,E%s:E%s)}' % (row1, row-1) 
      
        ##sheet 2
        formula_total_line_amount = '{=subtotal(9,K%s:K%s)}' % (row1, row-1) 



        ##sheet 1
        worksheet1.write_formula(row-1,4,formula_total_line_amount_satu, wbf['total_float'], line_amount)                  

        ##sheet 2
        worksheet2.write_formula(row-1,10,formula_total_line_amount, wbf['total_float'], line_amount)        

        worksheet1.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer']) 
        worksheet2.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])     
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        return True
