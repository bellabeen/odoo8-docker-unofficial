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
from openerp.sql_db import db_connect
from openerp.tools.config import config

class wtc_report_cash_non_pettycash(osv.osv_memory):
   
    _inherit = "wtc.report.cash"

    wbf = {}



    def _print_excel_report_non_pettycash(self, cr, uid, ids, data, context=None):        
        
        branch_ids = data['branch_ids']
        journal_ids = data['journal_ids']
        status = data['status']
        start_date = data['start_date']
        end_date = data['end_date']
        option = data['option']  
                     
        tz = '7 hours'
        journal_type = ['bank','cash','edc']
        query_where = " WHERE 1=1  "
        if option == 'All Non Petty Cash' :
            journal_type = ['bank','cash','edc']
            #query_where += " AND a.type or ('liquidity', 'receivable') "
        elif option == 'Cash' :
            journal_type = ['cash']
            #query_where += " AND a.type = 'liquidity' "
        elif option == 'EDC' :
            journal_type = ['edc']
            #query_where += " AND a.type = 'receivable' "
        elif option == 'Bank' :
            journal_type = ['bank']
            #query_where += " AND a.type = 'liquidity' "  
        elif option == 'Petty Cash' :
            journal_type = ['pettycash']
            #query_where += " AND a.type = 'liquidity' "
             
        if branch_ids :
            query_where += " AND aml.branch_id in %s " % str(tuple(branch_ids)).replace(',)', ')')             
            
        if not journal_ids :
            journal_ids = self.pool.get('account.journal').search(cr, uid, [('branch_id','in',branch_ids),('type','in',journal_type)])
        if journal_ids :
            journals = self.pool.get('account.journal').browse(cr, uid, journal_ids)
            query_where += " AND aml.account_id in %s " % str(tuple([x.default_debit_account_id.id for x in journals])).replace(',)', ')')
                          
        query_where_saldo = query_where

        if status == 'outstanding' :
            query_where += " AND aml.reconcile_id is Null "
        elif status == 'reconcile' :
            query_where += " AND aml.reconcile_id is not Null "   
                        
        if start_date :
            query_where_saldo += " AND aml.date < '%s' " % start_date
            query_where += " AND aml.date >= '%s' " % start_date
        if end_date :
            query_where += " AND aml.date <= '%s' " % end_date            

        query_saldo_awal = """
            (SELECT
            '%s' as tanggal
            , b.code as branch_code
            , '11:59 PM' as Jam
            , '' as kwitansi_name
            , a.code as account_code
            , 'Saldo Awal ' || a.code as keterangan
            , sum(aml.debit - aml.credit) as balance
            , 'saldo_awal' as journal_type
            , '' as scr
            , 0 as id
            FROM account_move_line aml 
            LEFT JOIN account_account a ON a.id = aml.account_id 
            LEFT JOIN wtc_branch b ON b.id = aml.branch_id 
            %s
            GROUP BY b.code, a.code
            ORDER BY a.code, b.code)
            """ % (datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=1), query_where_saldo)
                                                     
        query_trx = """
            (SELECT 
            aml.date as tanggal, 
            b.code as branch_code, 
            to_char(am.create_date + interval '%s', 'HH12:MI AM') as Jam, 
            k.name as kwitansi_name, 
            a.code as account_code, 
            aml.name as keterangan, 
            aml.debit - aml.credit as balance, 
            j.type as journal_type, 
            am.name as scr 
            , aml.id as id
            FROM account_move_line aml 
            LEFT JOIN account_move am ON am.id = aml.move_id 
            LEFT JOIN account_journal j ON j.id = aml.journal_id 
            LEFT JOIN account_account a ON a.id = aml.account_id 
            LEFT JOIN wtc_register_kwitansi_line k ON k.id = aml.kwitansi_id 
            LEFT JOIN wtc_branch b ON b.id = aml.branch_id 
            %s
            ORDER BY a.code, b.code, aml.id)
            """ % (tz,query_where) 

        query = """
            SELECT * 
            FROM (%s UNION %s) a
            ORDER BY branch_code, id
            """ % (query_saldo_awal, query_trx)

        conn_str = 'postgresql://' \
           + config.get('report_db_user', False) + ':' \
           + config.get('report_db_password', False) + '@' \
           + config.get('report_db_host', False) + ':' \
           + config.get('report_db_port', False) + '/' \
           + config.get('report_db_name', False)
        conn = db_connect(conn_str, True)
        cur = conn.cursor(False)
        cur.autocommit(True)

        cur.execute (query)
        # cr.execute (query)
        # ress = cr.fetchall()
        ress = cur.fetchall()
        cur.close()
        
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Cash')
        worksheet.set_column('B1:B1', 13)
        worksheet.set_column('C1:C1', 10)
        worksheet.set_column('D1:D1', 20)
        worksheet.set_column('E1:E1', 25)
        worksheet.set_column('F1:F1', 29)
        worksheet.set_column('G1:G1', 20)
        worksheet.set_column('H1:H1', 20)
        worksheet.set_column('I1:I1', 20)
        worksheet.set_column('J1:J1', 20)
        worksheet.set_column('K1:K1', 20) 
        worksheet.set_column('L1:L1', 20)    
        worksheet.set_column('M1:M1', 20)
                        
        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        filename = 'Report Cash '+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'LAPORAN PENERIMAAN DAN PENGELUARAN HARIAN' , wbf['title_doc'])
        
        worksheet.write('A4', 'Options : %s'%(option) , wbf['company'])
        worksheet.write('A5', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else date[:10]) , wbf['company'])
        
        row=5
        rowsaldo = row
        row+=1
        worksheet.write('A%s' % (row+1), 'No' , wbf['header'])
        worksheet.write('B%s' % (row+1), 'Kode Cabang' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'Tanggal' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'Jam' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'No Kwitansi' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'REK' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'Keterangan' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'Saldo Awal' , wbf['header'])
        worksheet.write('I%s' % (row+1), 'Tunai' , wbf['header'])
        worksheet.write('J%s' % (row+1), 'Bank & Checks' , wbf['header'])
        worksheet.write('K%s' % (row+1), 'EDC' , wbf['header'])
        worksheet.write('L%s' % (row+1), 'Total' , wbf['header'])
        worksheet.write('M%s' % (row+1), 'SCR' , wbf['header'])
           
        row+=2               
        no = 1     
        row1 = row
        
        total_tunai = 0
        total_bank_and_checks = 0
        total_edc = 0
        total_total = 0
        
        for res in ress:
            
            branch_code= res[1]
            tanggal= datetime.strptime(res[0], "%Y-%m-%d").date() if res[0] else ''
            jam= res[2]
            kwitansi_name= res[3] 
            account_code= res[4]
            keterangan= res[5].encode('ascii','ignore').decode('ascii') if res[5] != None else ''    
            saldo_awal = res[6] if res[7] == 'saldo_awal' else 0.0
            tunai= res[6] if res[7] == 'cash' else 0.0 
            bank_check= res[6] if res[7] == 'bank' else 0.0 
            edc= res[6] if res[7] == 'edc' else 0.0 
            total= res[6]
            move_name= res[8]
                                    
            worksheet.write('A%s' % row, no , wbf['content_number'])                    
            worksheet.write('B%s' % row, branch_code , wbf['content'])
            worksheet.write('C%s' % row, tanggal , wbf['content_date'])
            worksheet.write('D%s' % row, jam , wbf['content'])
            worksheet.write('E%s' % row, kwitansi_name , wbf['content'])
            worksheet.write('F%s' % row, account_code , wbf['content'])
            worksheet.write('G%s' % row, keterangan , wbf['content'])
            worksheet.write('H%s' % row, saldo_awal , wbf['content_float']) 
            worksheet.write('I%s' % row, tunai , wbf['content_float']) 
            worksheet.write('J%s' % row, bank_check, wbf['content_float'])  
            worksheet.write('K%s' % row, edc , wbf['content_float'])
            if no == 1 :
                worksheet.write('L%s' % row, total , wbf['content_float'])
            else :
                worksheet.write_formula('L%s' % row, '=L%s+(%d)' % (row-1, total), wbf['content_float'])
            worksheet.write('M%s' % row, move_name , wbf['content'])
            no+=1
            row+=1
                
            total_tunai = tunai
            total_bank_and_checks = bank_check
            total_edc = edc
            total_total = total
        
        worksheet.autofilter('A7:M%s' % (row))  
        worksheet.freeze_panes(7, 3)
        
        #TOTAL
        worksheet.merge_range('A%s:C%s' % (row,row), 'Total', wbf['total'])    
        worksheet.merge_range('D%s:G%s' % (row,row), '', wbf['total'])
        worksheet.write('M%s'%(row), '', wbf['total'])
        
        formula_total_saldo_awal = '{=subtotal(9,H%s:H%s)}' % (row1, row-1) 
        formula_total_tunai = '{=subtotal(9,I%s:I%s)}' % (row1, row-1) 
        formula_total_bank_and_checks = '{=subtotal(9,J%s:J%s)}' % (row1, row-1) 
        formula_total_edc = '{=subtotal(9,K%s:K%s)}' % (row1, row-1) 
        formula_total_total = '=H%s+I%s+J%s+K%s' % (row, row, row, row) 

        worksheet.write_formula(row-1,7,formula_total_saldo_awal, wbf['total_number'], total_tunai)                  
        worksheet.write_formula(row-1,8,formula_total_tunai, wbf['total_number'], total_tunai)                  
        worksheet.write_formula(row-1,9,formula_total_bank_and_checks, wbf['total_float'], total_bank_and_checks)
        worksheet.write_formula(row-1,10,formula_total_edc, wbf['total_float'],total_edc)
        worksheet.write_formula(row-1,11,formula_total_total, wbf['total_float'],total_total)  

        worksheet.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])  
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        return True
