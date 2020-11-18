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

  
class wtc_report_bank_transfer(osv.osv_memory):
   
    _inherit = "wtc.report.all.pettycash"

    wbf = {}


    def _print_excel_report_bank_transfer(self, cr, uid, ids, data, context=None):  
        branch_ids = data['branch_ids']
        division = data['division']
        journal_id = data['journal_bt_id'][0] if data['journal_id'] else False
        state_bank_transfer = data['state_bank_transfer']
        start_date = data['start_date']
        end_date = data['end_date']
        digits = self.pool['decimal.precision'].precision_get(cr, uid, 'Account')
      
        
        query = """
            select 
            bt.id as bt_id,
            bt.name as bt_name, 
            b.code as branch_code, 
            bt.division as bt_division, 
            j.name as journal_name , 
            bt.date as bt_date, 
            bt.description as bt_description, 
            bt.amount_total as bt_amount, 
            bt.bank_fee as bt_bank_fee,
            bt.state as bt_state, 
            r.name as bank_transfer_name, 
            l.branch_destination_id as branch_destination_code, 
            jl.name as journal_line_name, 
            l.description as line_name, 
            l.amount as line_amount,
            re.name as reimburse_ref
            from wtc_bank_transfer bt
            left join wtc_bank_transfer_line l ON l.bank_transfer_id = bt.id 
            left join wtc_branch b ON b.id = bt.branch_id
            left join account_journal j ON j.id = bt.payment_from_id
            left join wtc_bank_transfer r ON r.id = l.bank_transfer_id
            left join account_journal jl ON jl.id = l.payment_to_id
            inner join wtc_reimbursed re ON re.id = l.reimbursement_id
            where bt.id is not null and re.id is not null        
        """
        query_end = ''
        if branch_ids :
            query_end += " AND bt.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        if start_date :
            query_end += " AND bt.date >= '%s' " % str(start_date)
        if end_date :
            query_end += " AND bt.date <= '%s' " % str(end_date)
        if division :
            query_end += " AND bt.division = '%s'" % str(division) 
        if state_bank_transfer :
            query_end += " AND bt.state = '%s'" % str(state_bank_transfer) 
        if journal_id :
            query_end += " AND bt.payment_from_id = '%s'" % str(journal_id)             
            
        query_order = "order by b.code,r.date"

        cr.execute(query + query_end + query_order)
        all_lines = cr.fetchall()

        # print ">>>>>>>>>>>>>>>>>>",query + query_end + query_order)
        # all_lines = cr.dictfetchall()


        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet1 = workbook.add_worksheet('Report Bank Transfer')
        worksheet2 = workbook.add_worksheet('Report Bank Transfer Details')

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


        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        filename = 'Report Bank Transfer'+str(date)+'.xlsx'        
        worksheet1.write('A1', company_name , wbf['company'])
        worksheet1.write('A2', 'Bank Transfer' , wbf['title_doc'])
        worksheet1.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])
        

        # filename = 'Laporan Faktur Pajak Gabungan D'+str(date)+'.xlsx'        
        worksheet2.write('A1', company_name , wbf['company'])
        worksheet2.write('A2', 'Report Bank Transfer Details' , wbf['title_doc'])
        worksheet2.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])
        
        
        row=5
        rowsaldo = row
        row+=1

        worksheet1.write('A%s' % (row+1), 'No' , wbf['header'])
        worksheet1.write('B%s' % (row+1), 'Bank Transfer Ref' , wbf['header'])
        worksheet1.write('C%s' % (row+1), 'Branch Code' , wbf['header'])
        worksheet1.write('D%s' % (row+1), 'Total Amount' , wbf['header'])


        worksheet2.write('A%s' % (row+1), 'No' , wbf['header'])
        worksheet2.write('B%s' % (row+1), 'Bank Transfer Ref' , wbf['header'])
        worksheet2.write('C%s' % (row+1), 'Branch' , wbf['header'])
        worksheet2.write('D%s' % (row+1), 'Division' , wbf['header'])
        worksheet2.write('E%s' % (row+1), 'Date' , wbf['header'])
        worksheet2.write('F%s' % (row+1), 'Reimburse Ref' , wbf['header'])
        worksheet2.write('G%s' % (row+1), 'Description' , wbf['header'])
        worksheet2.write('H%s' % (row+1), 'Branch Destination' , wbf['header'])
        worksheet2.write('I%s' % (row+1), 'State' , wbf['header'])
        worksheet2.write('J%s' % (row+1), 'Total Amount' , wbf['header'])
 

        row+=2               
        no = 1     
        row1 = row
        
        line_amount = line_amount = 0

        for res in all_lines:

            bt_id = res[0]
            bt_name = res[1].encode('ascii','ignore').decode('ascii') if res[1] != None else ''
            branch_code = res[2].encode('ascii','ignore').decode('ascii') if res[2] != None else ''
            bt_division =  res[3].encode('ascii','ignore').decode('ascii') if res[3] != None else ''
            journal_name = res[4].encode('ascii','ignore').decode('ascii') if res[4] != None else ''
            bt_date = res[5]
            bt_description = res[6].encode('ascii','ignore').decode('ascii') if res[6] != None else ''
            bt_amount =  res[7] if res[7] != None else 0
            bt_bank_fee = res[8]
            bt_state = res[9]
            bank_transfer_name = res[10]
            branch_destination_code = res[11]
            journal_line_name = res[12].encode('ascii','ignore').decode('ascii') if res[12] != None else ''
            line_name = res[13].encode('ascii','ignore').decode('ascii') if res[13] != None else ''
            line_amount = res[14]
            reimburse_ref = res[15]
           
           
        
            worksheet1.write('A%s' % row, no, wbf['content_number'])                    
            worksheet1.write('B%s' % row, bt_name, wbf['content_number'])
            worksheet1.write('C%s' % row, branch_code, wbf['content'])
            worksheet1.write('D%s' % row, line_amount, wbf['content'])

            # if bt_name == bt_name :
            #     worksheet1.write_formula('D%s' % row, '=D%s+(%d)' % (row-1, line_amount), wbf['content_float'])
            # else :
            #     worksheet1.write('D%s' % row, line_amount, wbf['content_float'])


            worksheet2.write('A%s' % row, no, wbf['content_number']) 
            worksheet2.write('B%s' % row, bt_name, wbf['content'])  
            worksheet2.write('C%s' % row, branch_code, wbf['content'])
            worksheet2.write('D%s' % row, bt_division, wbf['content'])
            worksheet2.write('E%s' % row, bt_date, wbf['content_date'])
            worksheet2.write('F%s' % row, reimburse_ref, wbf['content'])
            worksheet2.write('G%s' % row, line_name, wbf['content'])
            worksheet2.write('H%s' % row, branch_destination_code, wbf['content'])
            worksheet2.write('I%s' % row, bt_state, wbf['content'])   
            worksheet2.write('J%s' % row, line_amount, wbf['content_float'])   
                

    
            no+=1
            row+=1

            line_amount = line_amount
            

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
        formula_total_line_amount_satu = '{=subtotal(9,D%s:D%s)}' % (row1, row-1) 
      
        ##sheet 2
        formula_total_line_amount = '{=subtotal(9,J%s:J%s)}' % (row1, row-1) 



        ##sheet 1
        worksheet1.write_formula(row-1,3,formula_total_line_amount_satu, wbf['total_float'], line_amount)                  

        ##sheet 2
        worksheet2.write_formula(row-1,9,formula_total_line_amount, wbf['total_float'], line_amount)                  



        worksheet1.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer']) 
        worksheet2.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])     
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        return True
