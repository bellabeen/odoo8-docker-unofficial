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

class wtc_report_journal(osv.osv_memory):
   
    _name = "wtc.report.journal"
    _description = "Journal Report"

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
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(wtc_report_journal, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
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
        'option': fields.selection([('account','Detail per Account')], 'Option', change_default=True, select=True), 
        'division': fields.selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum')], 'Division', change_default=True, select=True),         
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'period_id' : fields.many2one('account.period',string='Period'),
        'branch_ids': fields.many2many('wtc.branch', 'wtc_report_journal_branch_rel', 'wtc_report_journal',
                                        'branch_id', 'Branch', copy=False),
        'account_ids': fields.many2many('account.account', 'wtc_report_journal_account_rel', 'wtc_report_journal',
                                        'account_id', 'Account', copy=False, ), 
        'journal_ids': fields.many2many('account.journal', 'wtc_report_journal_journal_rel', 'wtc_report_journal',
                                        'journal_id', 'Journal', copy=False, ),
        'partner_ids': fields.many2many('res.partner', 'wtc_report_journal_partner_rel', 'wtc_report_journal',
                                        'partner_id', 'Partner', copy=False),         
    }

    _defaults = {
        'state_x': lambda *a: 'choose',
        'start_date':datetime.today(),
        'end_date':datetime.today(),
        'option':'account'        
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
        
        branch_ids = data['branch_ids']
        account_ids = data['account_ids']
        journal_ids = data['journal_ids']
        partner_ids = data['partner_ids']
        division = data['division']
        period_id = data['period_id']
        start_date = data['start_date']
        end_date = data['end_date']          
        
        where_period = " 1=1 "
        if period_id :
            where_period = " ap.id = %s" % str(period_id[0])
            
        where_account = " 1=1 "
        if account_ids :
            where_account=" a.id  in %s " % str(
                tuple(account_ids)).replace(',)', ')')  
                            
        where_branch = " 1=1 "
        if branch_ids :
            where_branch = " b.id in %s " % str(
                tuple(branch_ids)).replace(',)', ')')             
            
        where_journal = " 1=1 "
        if journal_ids :
            where_journal=" j.id  in %s " % str(
                tuple(journal_ids)).replace(',)', ')')   
        
        where_partner = " 1=1 "
        if partner_ids :
            where_partner=" p.id  in %s " % str(
                tuple(partner_ids)).replace(',)', ')')
                          
        where_division = " 1=1 "
        if division == 'Unit' :
            where_division=" l.division = 'Unit' "
        elif division == 'Sparepart' :
            where_division=" l.division = 'Sparepart' "  
        elif division == 'Umum' :
            where_division=" l.division = 'Umum' "  
                        
        where_start_date = " 1=1 "
        where_end_date = " 1=1 "                               
        if start_date :
            where_start_date = " l.date >= '%s' " % start_date
        if end_date :
            where_end_date = " l.date <= '%s' " % end_date
        

        query_saldo = """
            SELECT 
            COALESCE(SUM (l.debit-l.credit),0) as balance 
            FROM account_move_line l
            LEFT JOIN account_move m ON l.move_id = m.id
            LEFT JOIN account_period ap ON ap.id = m.period_id
            LEFT JOIN account_account a ON a.id = l.account_id
            LEFT JOIN wtc_branch b ON b.id = l.branch_id
            LEFT JOIN account_journal j ON j.id = l.journal_id
            LEFT JOIN account_move_reconcile r ON r.id = l.reconcile_id or r.id = l.reconcile_partial_id
            LEFT JOIN res_partner p ON p.id = l.partner_id
            LEFT JOIN product_product prod ON prod.id = l.product_id

            WHERE %s and %s and %s and %s and %s and %s and %s and %s
        """  %(where_period,where_account,where_branch,where_journal,where_partner,where_division,where_start_date,where_end_date)
        
        conn_str = 'postgresql://' \
           + config.get('report_db_user', False) + ':' \
           + config.get('report_db_password', False) + '@' \
           + config.get('report_db_host', False) + ':' \
           + config.get('report_db_port', False) + '/' \
           + config.get('report_db_name', False)
        conn = db_connect(conn_str, True)
        cur = conn.cursor(False)
        cur.autocommit(True)
        
        # cr.execute (query_saldo)
        cur.execute (query_saldo)
        # result = cr.fetchall()
        result = cur.fetchall()

        saldo_awal = 0

        if len(result) > 0 and len(result[0]) > 0:
            saldo_awal += result[0][0]
   



        # cr.execute (
        cur.execute (
        "SELECT a.code as account_code, "\
        "a.name as account_name, "\
        "a.sap as account_sap, "\
        "b.profit_centre as profit_centre, "\
        "b.code as branch_name, "\
        "l.division as division, "\
        "l.date as tanggal, "\
        "m.name as no_sistem, "\
        "l.name as no_bukti, "\
        "l.ref as keterangan, "\
        "l.debit as debit, "\
        "l.credit as credit, "\
        "r.name as reconcile_name, "\
        "j.name as journal_name, "\
        "ap.code as perid_code, "\
        "p.default_code as partner_code, " \
        "p.name as partner_name " \
        ", prod.name_template as product_code " \
        "FROM account_move_line l "\
        "LEFT JOIN account_move m ON m.id = l.move_id "\
        "LEFT JOIN account_period ap ON ap.id = m.period_id "\
        "LEFT JOIN account_account a ON a.id = l.account_id "\
        "LEFT JOIN wtc_branch b ON b.id = l.branch_id "\
        "LEFT JOIN account_journal j ON j.id = l.journal_id "\
        "LEFT JOIN account_move_reconcile r ON r.id = l.reconcile_id or r.id = l.reconcile_partial_id "\
        "LEFT JOIN res_partner p ON p.id = l.partner_id "\
        "LEFT JOIN product_product prod ON prod.id = l.product_id "\
        "WHERE a.type != 'view' AND a.type != 'consolidation' AND a.type != 'closed' AND b.id is not null "\
        "AND "+where_period+" AND "+where_account+" AND "+where_branch+" AND "+where_journal+" AND "+where_division+" AND "+where_start_date+" AND "+where_end_date+" AND "+where_partner+" "\
        "ORDER BY a.name, b.name, l.date"                    
        )
            
        # ress = cr.fetchall()
        ress = cur.fetchall()
        cur.close()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Journal')
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
        worksheet.set_column('M1:M1', 20)
        worksheet.set_column('N1:N1', 13)
        worksheet.set_column('O1:O1', 25)
        worksheet.set_column('P1:P1', 19)
        worksheet.set_column('Q1:Q1', 19)
        worksheet.set_column('R1:R1', 19)
        
        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        filename = 'Report Journal '+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report Journal' , wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date),str(end_date)) , wbf['company'])

        worksheet.write('E2', 'Saldo Awal Tanggal :' , wbf['company'])
        worksheet.write('E3', 'Mutasi Debit :' , wbf['company'])
        worksheet.write('E4', 'Mutasi Credit :' , wbf['company'])
        worksheet.write('E5', 'Saldo Akhir Tanggal:' , wbf['company'])

        row=5
        rowsaldo = row
        row+=1
        worksheet.write('A%s' % (row+1), 'No' , wbf['header'])
        worksheet.write('B%s' % (row+1), 'Periode' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'No Rek' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'Nama Rek' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'Branch' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'Division' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'No Sun' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'Tanggal' , wbf['header'])
        worksheet.write('I%s' % (row+1), 'No Sistem' , wbf['header'])
        worksheet.write('J%s' % (row+1), 'Name' , wbf['header'])
        worksheet.write('K%s' % (row+1), 'Reference' , wbf['header'])
        worksheet.write('L%s' % (row+1), 'Debit' , wbf['header'])
        worksheet.write('M%s' % (row+1), 'Credit' , wbf['header'])
        worksheet.write('N%s' % (row+1), 'Reconcile' , wbf['header'])
        worksheet.write('O%s' % (row+1), 'Journal' , wbf['header'])
        worksheet.write('P%s' % (row+1), 'Partner Code' , wbf['header'])                
        worksheet.write('Q%s' % (row+1), 'Partner Name' , wbf['header'])
        worksheet.write('R%s' % (row+1), 'Product Name' , wbf['header'])
        row+=2 
                
        no = 1
        total_debit =0
        total_credit = 0        
        row1 = row
        branch_code = False
        
        for res in ress:
#             if branch_code != res[0] :
#                 worksheet.write('B%s' % row, "SUBTOTAL %s" % branch_code , wbf['lr'])
#                 row += 2
#                 no = 1
            
            perid_code = res[14].encode('ascii','ignore').decode('ascii') if res[14] != None else ''                                                    
            account_code = res[0].encode('ascii','ignore').decode('ascii') if res[0] != None else ''
            account_name = res[1].encode('ascii','ignore').decode('ascii') if res[1] != None else ''
            branch_name = res[4].encode('ascii','ignore').decode('ascii') if res[4] != None else ''
            division = res[5].encode('ascii','ignore').decode('ascii') if res[5] != None else ''
            account_sap = res[2][:6].encode('ascii','ignore').decode('ascii') +'-'+ res[3].encode('ascii','ignore').decode('ascii') + res[2][6:].encode('ascii','ignore').decode('ascii') if res[2] != None and res[3] != None else ''
            tanggal = datetime.strptime(res[6], "%Y-%m-%d").date() if res[6] else ''
            no_sistem = res[7].encode('ascii','ignore').decode('ascii') if res[7] != None else ''
            no_bukti = res[8].encode('ascii','ignore').decode('ascii') if res[8] != None else ''
            keterangan = res[9].encode('ascii','ignore').decode('ascii') if res[9] != None else ''
            debit = res[10]
            credit = res[11]
            reconcile_name = res[12].encode('ascii','ignore').decode('ascii') if res[12] != None else ''
            journal_name = res[13].encode('ascii','ignore').decode('ascii') if res[13] != None else ''
            partner_code = res[15].encode('ascii','ignore').decode('ascii') if res[15] != None else ''
            partner_name = res[16].encode('ascii','ignore').decode('ascii') if res[16] != None else ''
            product_code = res[17].encode('ascii','ignore').decode('ascii') if res[17] != None else ''

            total_debit += debit
            total_credit += credit                    
                            
            worksheet.write('A%s' % row, no , wbf['content_number'])                    
            worksheet.write('B%s' % row, perid_code , wbf['content'])
            worksheet.write('C%s' % row, account_code , wbf['content'])
            worksheet.write('D%s' % row, account_name , wbf['content'])
            worksheet.write('E%s' % row, branch_name , wbf['content'])
            worksheet.write('F%s' % row, division , wbf['content'])
            worksheet.write('G%s' % row, account_sap , wbf['content'])
            worksheet.write('H%s' % row, tanggal , wbf['content_date'])  
            worksheet.write('I%s' % row, no_sistem , wbf['content'])
            worksheet.write('J%s' % row, no_bukti , wbf['content'])
            worksheet.write('K%s' % row, keterangan , wbf['content'])
            worksheet.write('L%s' % row, debit , wbf['content_float'])
            worksheet.write('M%s' % row, credit , wbf['content_float'])
            worksheet.write('N%s' % row, reconcile_name , wbf['content'])
            worksheet.write('O%s' % row, journal_name , wbf['content'])
            worksheet.write('P%s' % row, partner_code , wbf['content'])
            worksheet.write('Q%s' % row, partner_name , wbf['content'])
            worksheet.write('R%s' % row, product_code , wbf['content'])
            no+=1
            row+=1
            
        worksheet.autofilter('A7:R%s' % (row))
        worksheet.freeze_panes(7, 7)

        worksheet.write_number('F2', saldo_awal , wbf['content_float'])
        worksheet.write_number('F3', total_debit , wbf['content_float'])
        worksheet.write_number('F4', total_credit , wbf['content_float'])
        worksheet.write('F5', saldo_awal+total_debit-total_credit , wbf['content_float'])
        
        #TOTAL
        worksheet.merge_range('A%s:C%s' % (row,row), 'Total', wbf['total'])    
        worksheet.merge_range('D%s:K%s' % (row,row), '', wbf['total']) 
        worksheet.merge_range('N%s:R%s' % (row,row), '', wbf['total']) 
        
        formula_debit = '{=subtotal(9,L%s:L%s)}' % (row1, row-1)
        formula_credit = '{=subtotal(9,M%s:M%s)}' % (row1, row-1)
        
        worksheet.write_formula(row-1,11,formula_debit, wbf['total_float'], total_debit)
        worksheet.write_formula(row-1,12,formula_credit, wbf['total_float'], total_credit)
        
        worksheet.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])  
                   
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_journal', 'view_report_journal')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.report.journal',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }

wtc_report_journal()
