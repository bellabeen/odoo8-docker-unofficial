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

class  wtc_report_bank_transfer(osv.osv_memory):
    _name = "wtc.report.bank.transfer.wizard"
    _description = "Report Bank Transfer"

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
    
    def _get_categ_ids(self, cr, uid, division, context=None):
        obj_categ = self.pool.get('product.category')
        all_categ_ids = obj_categ.search(cr, uid, [])
        categ_ids = obj_categ.get_child_ids(cr, uid, all_categ_ids, division)
        return categ_ids
        
    _columns = {
        'state_x': fields.selection( ( ('choose','choose'),('get','get'))), #xls
        'data_x': fields.binary('File', readonly=True),
        'name': fields.char('Filename', 100, readonly=True), 
        'branch_ids': fields.many2many('wtc.branch', 'wtc_report_bank_transfer_branch_rel', 'wtc_report_bank_transfer_wizard_id',
            'branch_id', 'Branches', copy=False),
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        
           
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
        
     
        start_date = data['start_date']
        end_date = data['end_date']
        branch_ids = data['branch_ids'] 
              
        tz = '7 hours'
        
        query_where = " WHERE 1=1 "
    
        if start_date :
            query_where += " AND bt.date >= '%s'" % str(start_date)
        if end_date :
            end_date = end_date + ' 23:59:59'
            query_where += " AND bt.date <= to_timestamp('%s', 'YYYY-MM-DD HH24:MI:SS') + interval '%s'" % (end_date,tz)
        if branch_ids :
            query_where += " AND bt.branch_id in %s" % str(tuple(branch_ids)).replace(',)', ')')
       
              
        query_order = "order by bt.state, bt.date"
                                                     
        
        query = """
                  select b1.code as sender_branch_code
                , b1.name as sender_branch_name
                , bt.division
                , bt.name as transaction_name
                , bt.date as transaction_date
                , bt.state as transaction_state
                , aj1.name as sender_journal_name
                , aa1.code as sender_account_code
                , aa1.name as sender_account_name
                , bt.amount as sender_amount
                , bt.bank_fee as sender_bank_fee
                , bt.description as sender_description
                , r.name as reimbursed_name
                , b2.code as dest_branch_code
                , b2.name as dest_branch_name
                , aj2.name as dest_journal_name
                , aa2.code as dest_account_code
                , aa2.name as dest_account_name
                , btl.amount as dest_amount
                , btl.description as dest_description
                from wtc_bank_transfer bt
                inner join wtc_bank_transfer_line btl on bt.id = btl.bank_transfer_id
                left join wtc_reimbursed r on btl.reimbursement_id = r.id
                left join wtc_branch b1 on bt.branch_id = b1.id
                left join wtc_branch b2 on btl.branch_destination_id = b2.code
                left join account_journal aj1 on bt.payment_from_id = aj1.id
                left join account_journal aj2 on btl.payment_to_id = aj2.id
                left join account_account aa1 on aj1.default_credit_account_id = aa1.id
                left join account_account aa2 on aj2.default_debit_account_id = aa2.id
                %s %s
            """ % (query_where,query_order)                     
                    
        cr.execute (query)
        ress = cr.fetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('BANK TRANSFER')
        worksheet.set_column('B1:B1', 13)
        worksheet.set_column('C1:C1', 21)
        worksheet.set_column('D1:D1', 25)
        worksheet.set_column('E1:E1', 18)
        worksheet.set_column('F1:F1', 20)
        worksheet.set_column('G1:G1', 11)
        worksheet.set_column('H1:H1', 30)
        worksheet.set_column('I1:I1', 11)
        worksheet.set_column('J1:J1', 18)
        worksheet.set_column('K1:K1', 15)
        worksheet.set_column('L1:L1', 20)
        worksheet.set_column('M1:M1', 20)
        worksheet.set_column('N1:N1', 20)
        worksheet.set_column('O1:O1', 20)
        worksheet.set_column('P1:P1', 20)
        worksheet.set_column('Q1:Q1', 20)
        worksheet.set_column('R1:R1', 20)
        worksheet.set_column('S1:S1', 20)
        worksheet.set_column('T1:T1', 20)
        worksheet.set_column('U1:U1', 20)
        worksheet.set_column('V1:V1', 20)
        worksheet.set_column('W1:W1', 20)
        worksheet.set_column('X1:X1', 20)
        worksheet.set_column('Y1:Y1', 20)
        worksheet.set_column('Z1:Z1', 20)
        worksheet.set_column('AA1:AA1', 8)
        worksheet.set_column('AB1:AB1', 8)
        worksheet.set_column('AC1:AC1', 20)
        worksheet.set_column('AD1:AD1', 20)      
                        
        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        filename = 'Report Bank Trasnfer '+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report Bank Trasnfer' , wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])
        row=3
        rowsaldo = row
        row+=1
        
        worksheet.merge_range('A%s:A%s' % (5,6), 'No', wbf['total'])    
        worksheet.merge_range('B%s:M%s' % (row+1,row+1), 'Sender', wbf['total'])  
        worksheet.write('B%s' % (row+2), 'Branch Code' , wbf['header'])  
        worksheet.write('C%s' % (row+2), 'Branch Name' , wbf['header'])
        worksheet.write('D%s' % (row+2), 'Division' , wbf['header'])
        worksheet.write('E%s' % (row+2), 'Transaction Name' , wbf['header'])
        worksheet.write('F%s' % (row+2), 'Date' , wbf['header'])
        worksheet.write('G%s' % (row+2), 'State' , wbf['header'])
        worksheet.write('H%s' % (row+2), 'Payment Method' , wbf['header'])
        worksheet.write('I%s' % (row+2), 'Account Code' , wbf['header'])
        worksheet.write('J%s' % (row+2), 'Account Name' , wbf['header'])
        worksheet.write('K%s' % (row+2), 'Amount' , wbf['header'])
        worksheet.write('L%s' % (row+2), 'Bank Transfer Fee' , wbf['header'])
        worksheet.write('M%s' % (row+2), 'Description' , wbf['header'])
        worksheet.merge_range('N%s:U%s' % (row+1,row+1), 'Recipients', wbf['total'])  
        
        worksheet.write('N%s' % (row+2), 'Reimbursed No' , wbf['header'])
        worksheet.write('O%s' % (row+2), 'Branch Destination Code' , wbf['header'])
        worksheet.write('P%s' % (row+2), 'Branch Destination Name' , wbf['header'])                
        worksheet.write('Q%s' % (row+2), 'Payment Method' , wbf['header'])
        worksheet.write('R%s' % (row+2), 'Account Code' , wbf['header'])
        worksheet.write('S%s' % (row+2), 'Account Name' , wbf['header'])
        worksheet.write('T%s' % (row+2), 'Amount' , wbf['header'])
        worksheet.write('U%s' % (row+2), 'Description' , wbf['header'])

                       
        row+=3              
        no = 1     
        row1 = row
        
        total_sender_amount = 0
        total_sender_bank_fee = 0
        total_dest_amount = 0

        
        for res in ress:
            
            branch_code = str(res[0].encode('ascii','ignore').decode('ascii')) if res[0] != None else ''
            branch_name = str(res[1].encode('ascii','ignore').decode('ascii')) if res[1] != None else ''
            division = str(res[2].encode('ascii','ignore').decode('ascii')) if res[2] != None else ''
            transaction_name = str(res[3].encode('ascii','ignore').decode('ascii')) if res[3] != None else ''
            transaction_state = datetime.strptime(res[4], "%Y-%m-%d") if res[4] else ''
            state = str(res[5].encode('ascii','ignore').decode('ascii')) if res[5] != None else ''
            sender_journal_name = str(res[6].encode('ascii','ignore').decode('ascii')) if res[6] != None else ''
            sender_account_code = str(res[7].encode('ascii','ignore').decode('ascii')) if res[7] != None else ''
            sender_account_name = str(res[8].encode('ascii','ignore').decode('ascii')) if res[8] != None else ''
            sender_amount = res[9]
            sender_bank_fee=res[10]
            sender_description = str(res[11].encode('ascii','ignore').decode('ascii')) if res[11] != None else ''
            reimbursed_name = str(res[12].encode('ascii','ignore').decode('ascii')) if res[12] != None else ''
            dest_branch_code = str(res[13].encode('ascii','ignore').decode('ascii')) if res[13] != None else ''
            dest_branch_name = str(res[14].encode('ascii','ignore').decode('ascii')) if res[14] != None else ''
            dest_journal_name = str(res[15].encode('ascii','ignore').decode('ascii')) if res[15] != None else ''
            dest_account_code = str(res[16].encode('ascii','ignore').decode('ascii')) if res[16] != None else ''
            dest_account_name = str(res[17].encode('ascii','ignore').decode('ascii')) if res[17] != None else ''
            dest_amount=res[18]
            dest_descriptionprod_name = str(res[19].encode('ascii','ignore').decode('ascii')) if res[19] != None else ''
           
          
          
            worksheet.write('A%s' % row, no , wbf['content_number'])                    
            worksheet.write('B%s' % row, branch_code , wbf['content'])
            worksheet.write('C%s' % row, branch_name , wbf['content'])
            worksheet.write('D%s' % row, division , wbf['content'])
            worksheet.write('E%s' % row, transaction_name , wbf['content'])
            worksheet.write('F%s' % row, transaction_state , wbf['content_datetime_12_hr'])
            worksheet.write('G%s' % row, state , wbf['content'])
            worksheet.write('H%s' % row, sender_journal_name , wbf['content']) 
            worksheet.write('I%s' % row, sender_account_code, wbf['content'])  
            worksheet.write('J%s' % row, sender_account_name , wbf['content'])
            worksheet.write('K%s' % row, sender_amount , wbf['content_float'])
            worksheet.write('L%s' % row, sender_bank_fee , wbf['content_float'])
            worksheet.write('M%s' % row, sender_description , wbf['content'])
            worksheet.write('N%s' % row, reimbursed_name , wbf['content'])
            worksheet.write('O%s' % row, dest_branch_code , wbf['content'])
            worksheet.write('P%s' % row, dest_branch_name , wbf['content'])
            worksheet.write('Q%s' % row, dest_journal_name, wbf['content'])
            worksheet.write('R%s' % row, dest_account_code , wbf['content']) 
            worksheet.write('S%s' % row, dest_account_name , wbf['content'])
            worksheet.write('T%s' % row, dest_amount , wbf['content_float'])
            worksheet.write('U%s' % row, dest_descriptionprod_name , wbf['content'])
           
           
            no+=1
            row+=1
            
            total_sender_amount += sender_amount 
            total_sender_bank_fee += sender_bank_fee
            total_dest_amount += dest_amount

            
        
#         worksheet.autofilter('A5:AD%s' % (row))  
        worksheet.freeze_panes(5, 3)
        
        #TOTAL
        worksheet.merge_range('A%s:C%s' % (row,row), 'Total', wbf['total'])    
        worksheet.merge_range('D%s:J%s' % (row,row), '', wbf['total'])
        worksheet.merge_range('M%s:S%s' % (row,row), '', wbf['total'])
        worksheet.merge_range('U%s:U%s' % (row,row), '', wbf['total'])
        
        formula_sender_amount = '{=subtotal(9,K%s:K%s)}' % (row1, row-1) 
        formula_sender_bank_fee  = '{=subtotal(9,L%s:L%s)}' % (row1, row-1) 
        formula_dest_amount= '{=subtotal(9,T%s:T%s)}' % (row1, row-1) 



        worksheet.write_formula(row-1,10,formula_sender_amount, wbf['total_float'], formula_sender_amount)                  
        worksheet.write_formula(row-1,11,formula_sender_bank_fee, wbf['total_float'], formula_sender_bank_fee)
        worksheet.write_formula(row-1,19,formula_dest_amount, wbf['total_float'],formula_dest_amount)
        worksheet.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])  
                   
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_bank_transfer', 'view_report_bank_transfer_wizard')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.report.bank.transfer.wizard',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }

wtc_report_bank_transfer()
