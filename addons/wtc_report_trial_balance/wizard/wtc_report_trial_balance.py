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
from openerp.sql_db import db_connect
from openerp.tools.config import config

class report_trial_balance(osv.osv_memory):
    _name = 'wtc.report.trial.balance'
    _description = 'Report Buku Besar'

    wbf={}
    
    def _get_branch_ids(self, cr, uid, context=None):
        branch_ids_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
        branch_ids = [b.id for b in branch_ids_user]
        return branch_ids

    def _get_default(self,cr,uid,date=False,user=False,context=None):
        if date :
            return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)
        else :
            return self.pool.get('res.users').browse(cr, uid, uid)

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(report_trial_balance, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        branch_ids_user=self.pool.get('res.users').browse(cr,uid,uid).branch_ids
        branch_ids=[b.id for b in branch_ids_user]
        
        doc = etree.XML(res['arch'])      
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
        for node in nodes_branch:
            node.set('domain', '[("id", "in", '+ str(branch_ids)+')]')
        res['arch'] = etree.tostring(doc)
        return res
    
    _columns = {
        'state_x': fields.selection( ( ('choose','choose'),('get','get'))), #xls
        'data_x': fields.binary('File', readonly=True),
        'name': fields.char('Filename', 100, readonly=True), 
        'option': fields.selection([('trial_balance','Detail Trial Balance'),('import_sun','Import Sun'),('import_tb','Import Trial Balance')], 'Option', change_default=True, select=True), 
        'period_id' : fields.many2one('account.period',string='Period'),
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'status': fields.selection([('all','All Entries'),('posted','Posted')], 'Status', change_default=True, select=True), 
        'branch_ids': fields.many2many('wtc.branch', 'wtc_report_trial_balance_branch_rel', 'wtc_report_trial_balance',
                                        'branch_id', 'Branch', copy=False),
        'account_ids': fields.many2many('account.account', 'wtc_report_trial_balance_account_rel', 'wtc_report_trial_balance',
                                        'account_id', 'Account', copy=False, ),
        'journal_ids': fields.many2many('account.journal', 'wtc_report_trial_balance_journal_rel', 'wtc_report_trial_balance',
                                        'journal_id', 'Journal', copy=False, ),                                                                            
    }

    _defaults = {
                 'status':'all',
                 'option':'trial_balance'
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




    def period_change(self, cr, uid, ids, period_id, context=None):
        value = {}
        value['start_date'] = False
        value['end_date'] = False
        return {'value':value}
    
    def date_change(self, cr, uid, ids, period_id, start_date, end_date, context=None):
        value = {}
        Warning = {}
        if period_id :
            obj_period_id = self.pool.get('account.period').browse(cr, uid, period_id)
            if start_date and (start_date < obj_period_id.date_start or start_date > obj_period_id.date_stop) :
                warning = {'title':'Perhatian', 'message':'Start Date dan End Date harus termasuk ke dalam Period !'}
                value['start_date'] = False
                return {'value':value, 'warning':warning}
            elif end_date :
                if not start_date :
                    warning = {'title':'Perhatian', 'message':'Silahkan isi Start Date terlebih dahulu !'}
                    value['end_date'] = False
                    return {'value':value, 'warning':warning}
                elif end_date > obj_period_id.date_stop or end_date < obj_period_id.date_start :
                    warning = {'title':'Perhatian', 'message':'Start Date dan End Date harus termasuk ke dalam Period !'}
                    value['end_date'] = False
                    return {'value':value, 'warning':warning}
            
            if start_date and end_date and start_date > end_date :
                warning = {'title':'Perhatian', 'message':'End Date tidak boleh kurang dari Start Date !'}
                value['start_date'] = False
                value['end_date'] = False
                return {'value':value, 'warning':warning}
        else :
            value['start_date'] = False
            value['end_date'] = False
        return {'value':value}
    

    def excel_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        data = self.read(cr, uid, ids,context=context)[0]
        if len(data['branch_ids']) == 0 :
            data.update({'branch_ids': self._get_branch_ids(cr, uid, context)})

        if data['option']  == 'trial_balance' :
            self._print_excel_report_trial_balance(cr, uid, ids, data, context=context)

        if data['option'] == 'import_sun' :
            self._print_excel_report_import_sun(cr, uid, ids, data, context=context)

        if data['option'] == 'import_tb' :
            self._print_excel_report_import_tb(cr, uid, ids, data, context=context)


        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_trial_balance', 'view_report_trial_balance')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.report.trial.balance',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }
    

    def _print_excel_report_import_sun(self, cr, uid, ids, data, context=None):

        branch_ids = data['branch_ids']
        account_ids = data['account_ids']        
        journal_ids = data['journal_ids']
        period_id = data['period_id']
        status = data['status']
        start_date = data['start_date']
        end_date = data['end_date']
        title_prefix = ''
        title_short_prefix = ''

        date_stop = self.pool.get('account.period').browse(cr,uid,period_id[0]).date_stop
        date_stop = datetime.strptime(date_stop, '%Y-%m-%d').strftime('%d %B %Y')
    

        report_trial_balance_import_sun = {
            'type': 'import_sun',
            'title': '',
            'title_short': title_short_prefix + ', ' + _('LAPORAN MUTASI PER CABANG')   , 
            'period': date_stop
            }  

        where_account = " 1=1 "
        if account_ids :
            where_account=" aml.account_id  in %s " % str(
                tuple(account_ids)).replace(',)', ')')   
                           
        where_branch = " 1=1 "
        if branch_ids :
            where_branch = " aml.branch_id in %s " % str(
                tuple(branch_ids)).replace(',)', ')')             
        else :
            area_user = self.pool.get('res.users').browse(cr,uid,uid).branch_ids
            branch_ids_user = [b.id for b in area_user]
            where_branch = " aml.branch_id in %s " % str(
                tuple(branch_ids_user))
            
        where_journal = " 1=1 "
        if journal_ids :
            where_account=" aml.journal_id  in %s " % str(
                tuple(journal_ids)).replace(',)', ')')   
            
        where_move_state = " 1=1 "
        if status == 'all' :
            where_move_state=" m.state is not Null "
        elif status == 'posted' :
            where_move_state=" m.state = 'posted' "  
             
        where_period = " 1=1 "                               
        if period_id :
            where_period = " aml.period_id = '%s' " % period_id[0]
        
        where_start_date = " 1=1 "
        where_end_date = " 1=1 "                               
        if start_date :
            where_start_date = " aml.date >= '%s' " % start_date
        if end_date :
            where_end_date = " aml.date <= '%s' " % end_date


        query_trial_balance = "SELECT b.code as branch_code, a.code as account_code, a.sap as account_sap, a.name as account_name, "\
            "b.profit_centre as profit_centre, l.branch_id, l.account_id, l.debit as debit, l.credit as credit, l.debit - l.credit as balance , p.date_stop as date_stop "\
            "FROM account_account a INNER JOIN "\
            "(SELECT aml.branch_id, aml.account_id, aml.period_id, SUM(aml.debit) as debit, SUM(aml.credit) as credit "\
            "FROM account_move_line aml "\
            "WHERE "+where_branch+" AND "+where_account+" AND "+where_period+" AND "+where_start_date+" AND "+where_end_date+" AND "+where_journal+" "\
            "GROUP BY aml.branch_id, aml.account_id, aml.period_id) l "\
            "ON a.id = l.account_id "\
            "INNER JOIN wtc_branch b ON l.branch_id = b.id "\
            "LEFT JOIN account_period p ON p.id = l.period_id "\
            "ORDER BY l.branch_id,a.parent_left "
                
        
        move_selection = ""
        report_info = _('')
        move_selection += ""
        
        conn_str = 'postgresql://' \
           + config.get('report_db_user', False) + ':' \
           + config.get('report_db_password', False) + '@' \
           + config.get('report_db_host', False) + ':' \
           + config.get('report_db_port', False) + '/' \
           + config.get('report_db_name', False)
        conn = db_connect(conn_str, True)
        cur = conn.cursor(False)
        cur.autocommit(True)

        # cr.execute(query_trial_balance)
        # all_lines = cr.dictfetchall()
        cur.execute(query_trial_balance)
        all_lines = cur.dictfetchall()
        cur.close()
        
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Laporan Mutasi Per Cabang')

        worksheet.set_column('B1:B1', 10)
        worksheet.set_column('C1:C1', 20)
        worksheet.set_column('D1:D1', 20)
        worksheet.set_column('E1:E1', 15)
        worksheet.set_column('F1:F1', 15)
        worksheet.set_column('G1:G1', 19)
        worksheet.set_column('H1:H1', 11)
        worksheet.set_column('I1:I1', 20)
        worksheet.set_column('J1:J1', 40)
        worksheet.set_column('K1:K1', 19)
        worksheet.set_column('L1:L1', 18)
        worksheet.set_column('M1:M1', 20)
        worksheet.set_column('N1:N1', 20)
        worksheet.set_column('O1:O1', 25)
        worksheet.set_column('P1:P1', 19)


        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        filename = 'Report Terial Balance Import Sun '+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Laporan Mutasi Per Cabang' , wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date),str(end_date)) , wbf['company'])


        row=5
        rowsaldo = row
        row+=1

        worksheet.write('A%s' % (row+1), 'No' , wbf['header'])
        worksheet.write('B%s' % (row+1), 'Cab' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'No Rek' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'Account' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'Profit Center' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'Div' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'Dept' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'Class' , wbf['header'])
        worksheet.write('I%s' % (row+1), 'Type' , wbf['header'])
        worksheet.write('J%s' % (row+1), 'Keterangan' , wbf['header'])
        worksheet.write('K%s' % (row+1), 'Transaction Amount' , wbf['header'])
        worksheet.write('L%s' % (row+1), 'Transaction Date' , wbf['header'])
        worksheet.write('M%s' % (row+1), 'Trans Reference' , wbf['header'])
        worksheet.write('N%s' % (row+1), 'Memo Amount' , wbf['header'])
        worksheet.write('O%s' % (row+1), 'Debit' , wbf['header'])
        worksheet.write('P%s' % (row+1), 'Credit' , wbf['header'])

 
        row+=2       
        no = 1
        row1 = row

        transaction_amount = 0
        debit = 0
        credit = 0


        for x in all_lines:

            branch_code = x['branch_code'].encode('ascii','ignore').decode('ascii') if x['branch_code'] != None else ''
            account_code = x['account_code'].encode('ascii','ignore').decode('ascii') if x['account_code'] != None else ''
            account_name =  x['account_name'].encode('ascii','ignore').decode('ascii') if x['account_name'] != None else ''
            profit_centre = x['profit_centre'].encode('ascii','ignore').decode('ascii') if x['profit_centre'] != None else ''
            debit = x['debit']
            credit = x['credit']
            transaction_amount = x['balance']
            date_stop = x['date_stop'].encode('ascii','ignore').decode('ascii') if x['date_stop'] != None else ''
            account = x['account_sap'].split('-')[0].encode('ascii','ignore').decode('ascii') if len(x['account_sap'].split('-')) > 0 and x['account_sap'] != None else x['account_sap'].encode('ascii','ignore').decode('ascii')
            div = x['account_sap'].split('-')[1].encode('ascii','ignore').decode('ascii') if len(x['account_sap'].split('-')) > 1 and x['account_sap'] != None else ''
            dept = x['account_sap'].split('-')[2] if len(x['account_sap'].split('-')) > 2 and x['account_sap'] != None else ''
            clas = x['account_sap'].split('-')[3] if len(x['account_sap'].split('-')) > 3 and x['account_sap'] != None else ''
            tipe =  x['account_sap'].split('-')[4] if len(x['account_sap'].split('-')) > 4 and x['account_sap'] != None else ''
            

            worksheet.write('A%s' % row, no, wbf['content_number']) 
            worksheet.write('B%s' % row, branch_code, wbf['content'])  
            worksheet.write('C%s' % row, account_code, wbf['content'])
            worksheet.write('D%s' % row, account, wbf['content'])
            worksheet.write('E%s' % row, profit_centre, wbf['content'])
            worksheet.write('F%s' % row, div, wbf['content'])
            worksheet.write('G%s' % row, dept, wbf['content'])
            worksheet.write('H%s' % row, clas, wbf['content'])
            worksheet.write('I%s' % row, tipe, wbf['content'])   
            worksheet.write('J%s' % row, account_name, wbf['content']) 
            worksheet.write('K%s' % row, transaction_amount, wbf['content_float'])      
            worksheet.write('L%s' % row, date_stop, wbf['content_date'])
            # worksheet.write('M%s' % row, )
            # worksheet.write('N%s' % row, )
            worksheet.write('O%s' % row, debit, wbf['content_float'])
            worksheet.write('P%s' % row, credit, wbf['content_float'])
            
            no+=1
            row+=1

            transaction_amount = transaction_amount
            debit = debit
            credit = credit

        worksheet.autofilter('A7:J%s' % (row))  
        worksheet.autofilter('L7:N%s' % (row)) 
        worksheet.freeze_panes(7, 3)


        #TOTAL
        #sheet 1
        worksheet.merge_range('A%s:J%s' % (row,row), 'Total', wbf['total'])    
        worksheet.merge_range('L%s:N%s' % (row,row), '', wbf['total']) 

        worksheet.write('K%s'%(row), '', wbf['total'])
        worksheet.write('O%s'%(row), '', wbf['total'])
        worksheet.write('P%s'%(row), '', wbf['total'])
       

        #sheet 1
        formula_transaction_almount = '{=subtotal(9,K%s:K%s)}' % (row1, row-1) 
        formula_debit = '{=subtotal(9,O%s:O%s)}' % (row1, row-1) 
        formula_kredit = '{=subtotal(9,P%s:P%s)}' % (row1, row-1)
        
       

        #sheet 1
        worksheet.write_formula(row-1,10,formula_transaction_almount, wbf['total_float'], transaction_amount)  
        worksheet.write_formula(row-1,14,formula_debit, wbf['total_float'], debit) 
        worksheet.write_formula(row-1,15,formula_kredit, wbf['total_float'], credit)                

      
        worksheet.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer']) 
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()


# wtc_report_trial_balance()



    # def print_report(self, cr, uid, ids, context=None):
    #     if context is None:
    #         context = {}
    #     branch_ids_user=self.pool.get('res.users').browse(cr,uid,uid).branch_ids
    #     data = self.read(cr, uid, ids)[0]
    #     branch_ids = data['branch_ids']
    #     cek=len(branch_ids)
        
    #     if cek == 0 :
    #         branch_ids=[b.id for b in branch_ids_user]
    #     else :
    #         branch_ids=data['branch_ids']
        
    #     account_ids = data['account_ids']
    #     period_id = data['period_id']
    #     status = data['status']
    #     start_date = data['start_date']
    #     end_date = data['end_date']

    #     data.update({
    #         'branch_ids': branch_ids,
    #         'account_ids': account_ids,
    #         'period_id': period_id,
    #         'status': status,
    #         'start_date': start_date,
    #         'end_date': end_date,
            
    #     })
    #     if context.get('options') == 'trial_balance':
    #         return {'type': 'ir.actions.report.xml',
    #                 'report_name': 'wtc_report_trial_balance_xls',
    #                 'datas': data}
            
    #     elif context.get('options') == 'import_sun':
    #         return {'type': 'ir.actions.report.xml',
    #                 'report_name': 'wtc_report_trial_balance_import_sun_xls',
    #                 'datas': data}      
    #     elif context.get('options') == 'import_tb':
    #         return {'type': 'ir.actions.report.xml',
    #                 'report_name': 'wtc_report_import_trial_balance_xls',
    #                 'datas': data}                    
    #     else:
    #         context['landscape'] = True
    #         return self.pool['report'].get_action(
    #             cr, uid, [],
    #             'wtc_account_move.report_trial_balance',
    #             data=data, context=context)
            
    # def xls_export(self, cr, uid, ids, context=None):
    #     return self.print_report(cr, uid, ids, context)          












    
   


