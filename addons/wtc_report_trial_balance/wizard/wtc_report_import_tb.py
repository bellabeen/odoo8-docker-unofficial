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


class wtc_report_import_tb(osv.osv_memory):

    _inherit = "wtc.report.trial.balance"

    wbf = {}
    
    def get_fiscalyear(self,cr,uid,ids,period_id):
        # cr = self.cr
        query_fiscal = "SELECT fiscalyear_id FROM account_period WHERE id = %s"
        
        cr.execute(query_fiscal, (period_id, ))
        fiscalyear_id = cr.fetchall()
        return fiscalyear_id[0][0]
    
    def get_period(self,cr,uid,ids,period_id,fiscalyear_id):
        # cr = self.cr
        query_period = "SELECT id from account_period " \
            "WHERE id < %s AND fiscalyear_id = %s "
            
        cr.execute(query_period, (period_id,fiscalyear_id ))
        period_ids = cr.fetchall() 
        period_id_kolek = []
        for id in period_ids:
            period_id_kolek.append(id)      
        if not period_id_kolek :
            return False 
             
        return period_id_kolek


    def _print_excel_report_import_tb(self, cr, uid, ids, data, context=None):
        # cr = self.cr
        # uid = self.uid
        # context = self.context
# 
        branch_ids = data['branch_ids']
        account_ids = data['account_ids']
        period_id = data['period_id']
        status = data['status']
        start_date = data['start_date']
        end_date = data['end_date']
        title_prefix = ''
        title_short_prefix = ''
        
        date_stop = self.pool.get('account.period').browse(cr,uid,period_id[0]).date_stop
        date_stop = datetime.strptime(date_stop, '%Y-%m-%d').strftime('%d %B %Y')
        report_import_trial_balance = {
            'type': 'BukuBesar',
            'title': '',
            'title_short': title_short_prefix + ', ' + _('LAPORAN BUKU BESAR'),
            'period': date_stop,
            'start_date': start_date,
            'end_date': end_date
            }  

        where_account = " 1=1 "
        if account_ids :
            where_account=" a.id  in %s " % str(
                tuple(account_ids)).replace(',)', ')')              
        where_branch = " 1=1 "
        if branch_ids :
            where_branch = " b.id in %s " % str(
                tuple(branch_ids)).replace(',)', ')')             
        else :
            area_user = self.pool.get('res.users').browse(cr,uid,uid).branch_ids
            branch_ids_user = [b.id for b in area_user]
            where_branch = " b.id in %s " % str(
                tuple(branch_ids_user))
        where_move_state = " 1=1 "
        if status == 'all' :
            where_move_state=" m.state is not Null "
        elif status == 'posted' :
            where_move_state=" m.state = 'posted' "   
        where_prev_period = " 1=1 "
        where_period = " 1=1 "                               
        if period_id :
            fiscalyear_id = self.get_fiscalyear(cr,uid,ids,period_id[0])
            period_ids = self.get_period(cr,uid,ids,period_id[0], fiscalyear_id)
            if period_ids :
                where_prev_period =" l.period_id  in %s " % str(
                    tuple(period_ids)).replace(',)', ')')
            else :
                where_prev_period = " 1!=1 "
                
            where_period = " l.period_id = '%s' " % period_id[0]
            
            where_prev_start_date = " 1!=1 "
            where_start_date = " 1=1 "
            where_end_date = " 1=1 "
            if start_date :
                where_prev_start_date = " l.date < '%s' " % start_date
                where_start_date = " l.date >= '%s' " % start_date
            if end_date :
                where_end_date = " l.date <= '%s' " % end_date


        query_trial_balance = "SELECT a.code as account_code, a.name as account_name, a.sap as account_sap, b.profit_centre as profit_centre, b.name as branch_name, COALESCE(line.saldo_awal_debit,0) as saldo_awal_debit, "\
            "COALESCE(line.saldo_awal_credit,0) as saldo_awal_credit, "\
            "COALESCE(line.mutasi_debit,0) as mutasi_debit, "\
            "COALESCE(line.mutasi_credit,0) as mutasi_credit, "\
            "saldo_awal_debit - saldo_awal_credit as saldo_awal, "\
            "saldo_awal_debit - saldo_awal_credit + mutasi_debit - mutasi_credit as saldo_akhir "\
            "FROM account_account a "\
            "LEFT JOIN "\
            "(SELECT COALESCE(aml1.account_id,aml2.account_id) as account_id, COALESCE(aml1.branch_id,aml2.branch_id) as branch_id, "\
            "COALESCE(aml1.saldo_awal_debit,0) as saldo_awal_debit, "\
            "COALESCE(aml1.saldo_awal_credit,0) as saldo_awal_credit, "\
            "COALESCE(aml2.mutasi_debit,0) as mutasi_debit, "\
            "COALESCE(aml2.mutasi_credit,0) as mutasi_credit FROM "\
            "(SELECT l.account_id as account_id, l.branch_id as branch_id, SUM(l.debit) as saldo_awal_debit, SUM(l.credit) as saldo_awal_credit "\
            "FROM account_move_line l LEFT JOIN account_move m ON l.move_id = m.id WHERE "+where_move_state+" AND ("+where_prev_period+" OR ("+where_period+" AND "+where_prev_start_date+")) GROUP BY l.account_id, l.branch_id) AS aml1 "\
            "FULL OUTER JOIN "\
            "(SELECT l.account_id as account_id, l.branch_id as branch_id, SUM(l.debit) as mutasi_debit, SUM(l.credit) as mutasi_credit "\
            "FROM account_move_line l LEFT JOIN account_move m ON l.move_id = m.id WHERE "+where_move_state+" AND "+where_period+" AND "+where_start_date+" AND "+where_end_date+" GROUP BY l.account_id, l.branch_id) AS aml2 "\
            "ON aml1.account_id = aml2.account_id AND aml1.branch_id = aml2.branch_id) line ON line.account_id = a.id "\
            "LEFT JOIN wtc_branch b ON line.branch_id = b.id "\
            "WHERE a.type != 'view' AND a.type != 'consolidation' AND a.type != 'closed' AND b.id is not null "\
            "AND "+where_branch+" AND "+where_account+" "\
            "ORDER BY b.code, a.parent_left"    
        
        move_selection = ""
        report_info = _('')
        move_selection += ""
            
        reports = [report_import_trial_balance]


        cr.execute(query_trial_balance)
        all_lines = cr.dictfetchall()


        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Laporan Mutasi Per Cabang')

        worksheet.set_column('B1:B1', 13)
        worksheet.set_column('C1:C1', 21)
        worksheet.set_column('D1:D1', 40)
        worksheet.set_column('E1:E1', 15)
        worksheet.set_column('F1:F1', 15)
        worksheet.set_column('G1:G1', 19)
        worksheet.set_column('H1:H1', 11)
        worksheet.set_column('I1:I1', 25)
        worksheet.set_column('J1:J1', 40)
        worksheet.set_column('K1:K1', 19)
        worksheet.set_column('L1:L1', 20)



        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        filename = 'Report Import Trial Balance '+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Laporan Mutasi Per Cabang' , wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date),str(end_date)) , wbf['company'])


        row=5
        rowsaldo = row
        row+=1

        worksheet.write('A%s' % (row+1), 'No' , wbf['header'])
        worksheet.write('B%s' % (row+1), 'No Rek' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'Branch' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'Account' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'Profit Centre' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'Div' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'Dept' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'Class' , wbf['header'])
        worksheet.write('I%s' % (row+1), 'Type' , wbf['header'])
        worksheet.write('J%s' % (row+1), 'Keterangan' , wbf['header'])
        worksheet.merge_range('K%s:L%s' % (row+1,row+1), 'MUTASI', wbf['header'])    
      
 

        row=6
        rowsaldo = row
        row+=1

        worksheet.write('A%s' % (row+1), '' , wbf['header'])
        worksheet.write('B%s' % (row+1), '' , wbf['header'])
        worksheet.write('C%s' % (row+1), '' , wbf['header'])
        worksheet.write('D%s' % (row+1), '' , wbf['header'])
        worksheet.write('E%s' % (row+1), '' , wbf['header'])
        worksheet.write('F%s' % (row+1), '' , wbf['header'])
        worksheet.write('G%s' % (row+1), '' , wbf['header'])
        worksheet.write('H%s' % (row+1), '' , wbf['header'])
        worksheet.write('I%s' % (row+1), '' , wbf['header'])
        worksheet.write('J%s' % (row+1), '' , wbf['header'])
        worksheet.write('K%s' % (row+1), 'Debit' , wbf['header']) 
        worksheet.write('L%s' % (row+1), 'Credit' , wbf['header']) 

        row+=2       
        no = 1
        row1 = row

        mutasi_debit = 0
        mutasi_credit = 0

        for x in all_lines:


            branch_name = x['branch_name'].encode('ascii','ignore').decode('ascii') if x['branch_name'] != None else ''
            account = x['account_sap'].split('-')[0].encode('ascii','ignore').decode('ascii') if len(x['account_sap'].split('-')) > 0 and x['account_sap'] != None else x['account_sap'].encode('ascii','ignore').decode('ascii') 
            profit_centre = x['profit_centre'].encode('ascii','ignore').decode('ascii') if x['profit_centre'] != None else '' 
            div = x['account_sap'].split('-')[1].encode('ascii','ignore').decode('ascii') if len(x['account_sap'].split('-')) > 1 and x['account_sap'] != None else ''
            dept = x['account_sap'].split('-')[2] if len(x['account_sap'].split('-')) > 2 and x['account_sap'] != None else '' 
            clas = x['account_sap'].split('-')[3] if len(x['account_sap'].split('-')) > 3 and x['account_sap'] != None else ''
            tipe = x['account_sap'].split('-')[4] if len(x['account_sap'].split('-')) > 4 and x['account_sap'] != None else ''
            account_code = x['account_code'].encode('ascii','ignore').decode('ascii') if x['account_code'] != None else ''  
            account_name = x['account_name'].encode('ascii','ignore').decode('ascii') if x['account_name'] != None else ''
            mutasi_debit = x['mutasi_debit']
            mutasi_credit = x['mutasi_credit']


            worksheet.write('A%s' % row, no, wbf['content_number']) 
            worksheet.write('B%s' % row, account_code, wbf['content'])  
            worksheet.write('C%s' % row, branch_name, wbf['content'])
            worksheet.write('D%s' % row, account, wbf['content'])
            worksheet.write('E%s' % row, profit_centre, wbf['content'])
            worksheet.write('F%s' % row, div, wbf['content'])
            worksheet.write('G%s' % row, dept, wbf['content'])
            worksheet.write('H%s' % row, clas, wbf['content'])
            worksheet.write('I%s' % row, tipe, wbf['content'])   
            worksheet.write('J%s' % row, account_name, wbf['content']) 
            worksheet.write('K%s' % row, mutasi_debit, wbf['content_float'])      
            worksheet.write('L%s' % row, mutasi_credit, wbf['content_float'])
           
            
            no+=1
            row+=1

            mutasi_debit = mutasi_debit
            mutasi_credit = mutasi_credit
          
        worksheet.autofilter('A7:J%s' % (row))  
        worksheet.freeze_panes(7, 3)

         #TOTAL
        #sheet 1
        worksheet.merge_range('A%s:J%s' % (row,row), 'Total', wbf['total'])    
        worksheet.write('K%s'%(row), '', wbf['total'])
        worksheet.write('L%s'%(row), '', wbf['total'])

        #sheet 1
        formula_debit = '{=subtotal(9,K%s:K%s)}' % (row1, row-1) 
        formula_kredit = '{=subtotal(9,L%s:L%s)}' % (row1, row-1)
        
        #sheet 1
        worksheet.write_formula(row-1,10,formula_debit, wbf['total_float'], mutasi_debit)  
        worksheet.write_formula(row-1,11,formula_kredit, wbf['total_float'], mutasi_credit) 
             
      
        worksheet.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer']) 
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()


# wtc_report_trial_balance()


