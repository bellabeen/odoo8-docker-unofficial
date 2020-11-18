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

class wtc_report_cash(osv.osv_memory):
   
    _name = "wtc.report.cash"
    _description = "Cash Report"

    wbf = {}



    
    def print_pdf_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = self.read(cr, uid, ids,context=context)[0]
        
        if data['option'] == 'Cash' :
             return self.pool['report'].get_action(cr, uid, [], 'wtc_report_cash.wtc_report_non', data=data, context=context)
        
        elif data['option'] == 'Bank' :
            return self.pool['report'].get_action(cr, uid, [], 'wtc_report_cash.wtc_report_non', data=data, context=context)

        elif data['option'] == 'EDC' :
            return self.pool['report'].get_action(cr, uid, [], 'wtc_report_cash.wtc_report_non', data=data, context=context)

        elif data['option'] == 'Petty Cash' :
            return self.pool['report'].get_action(cr, uid, [], 'wtc_report_cash.wtc_report_pettycash_pdf', data=data, context=context)

    



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
        res = super(wtc_report_cash, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        branch_ids_user=self.pool.get('res.users').browse(cr,uid,uid).branch_ids
        branch_ids=[b.id for b in branch_ids_user]
        
        doc = etree.XML(res['arch'])      
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
        nodes_journal_ids = doc.xpath("//field[@name='journal_ids']")
        nodes_journal = doc.xpath("//field[@name='journal_id']")
        for node in nodes_branch:
            node.set('domain', '[("id", "in", '+ str(branch_ids)+')]')
        for node in nodes_journal:
            node.set('domain', '[("branch_id", "in", '+ str(branch_ids)+'),("type","=","pettycash")]')  
        for node in nodes_journal_ids:
            node.set('domain', '[("branch_id", "in", '+ str(branch_ids)+')]')                        
        res['arch'] = etree.tostring(doc)
        return res
        
    _columns = {
        'state_x': fields.selection( ( ('choose','choose'),('get','get'))), #xls
        'data_x': fields.binary('File', readonly=True),
        'name': fields.char('Filename', 100, readonly=True), 
        'option': fields.selection([('Petty Cash','Petty Cash'),('All Non Petty Cash','All Non Petty Cash'),('Cash','Cash'),('Bank','Bank & Checks'),('EDC','EDC'),('Outstanding EDC','Outstanding EDC'), ('cash_reconcile', 'Cash Reconcile')], 'Option', change_default=True, select=True), 
        'status': fields.selection([('outstanding','Outstanding'),('reconcile','Reconciled')], 'Status', change_default=True, select=True),         
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'branch_ids': fields.many2many('wtc.branch', 'wtc_report_cash_branch_rel', 'wtc_report_cash',
                                        'branch_id', 'Branch', copy=False),
        'journal_ids': fields.many2many('account.journal', 'wtc_report_cash_journal_rel', 'wtc_report_cash',
                                        'journal_id', 'Journal', copy=False, ),             
        'journal_id' : fields.many2one('account.journal',string="Journal",domain="[('type','=','pettycash')]")       
    }

    _defaults = {
        'state_x': lambda *a: 'choose',
         'start_date':datetime.today(),
         'end_date':datetime.today(),
         'option':'All Non Petty Cash'

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
        

    def excel_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
            
        data = self.read(cr, uid, ids,context=context)[0]
        if len(data['branch_ids']) == 0 :
            data.update({'branch_ids': self._get_branch_ids(cr, uid, context)})
        if data['option'] == 'Petty Cash' :
            self._print_excel_report_pettycash(cr, uid, ids, data, context=context)
        elif data['option'] == 'cash_reconcile' :
            self._print_excel_report_cash_reconcile(cr, uid, ids, data, context=context)
        else :
            self._print_excel_report_non_pettycash(cr, uid,ids,data,context=context)

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_cash', 'view_report_cash')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.report.cash',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }
    
    def _print_excel_report_pettycash(self, cr, uid, ids, data, context=None):        
        
        start_date = data['start_date']
        end_date = data['end_date']
        option = data['option']
        journal_id = data['journal_id'][0] if data['journal_id'] else False   
        branch_ids = data['branch_ids']
        if not journal_id :
            raise osv.except_osv(('Error !'), ('Journal tidak ditemukan')) 

        journal_pool = self.pool.get('account.journal').browse(cr,uid,journal_id)
        default_account = journal_pool.default_debit_account_id or journal_pool.default_credit_account_id
        default_account_code = default_account.code
        default_account_name = default_account.name
        default_account_sap = default_account.sap
                      
        tz = '7 hours'
        query_where = " WHERE a.type = 'liquidity' "
        query_saldo_where = ""
        if branch_ids :
            query_where += " AND aml.branch_id in %s " % str(tuple(branch_ids)).replace(',)', ')') 
        if not journal_id :
            journal_ids = self.pool.get('account.journal').search(cr, uid, [('branch_id','in',branch_ids),('type','=','pettycash')])
        if journal_id and isinstance(journal_id, (int, long)) :
            journal_ids = [journal_id]
        if journal_ids :
            journals = self.pool.get('account.journal').browse(cr, uid, journal_ids)
            query_where += " AND aml.account_id in %s " % str(tuple([x.default_debit_account_id.id for x in journals if x.type == 'pettycash'])).replace(',)', ')')
            query_saldo_where += " AND aml.account_id in %s " % str(tuple([x.default_debit_account_id.id for x in journals if x.type == 'pettycash'])).replace(',)', ')')
        if start_date :
            query_where += " AND aml.date >= '%s' " % start_date
        if end_date :
            query_where += " AND aml.date <= '%s' " % end_date

        query_saldo = """
            SELECT SUM(debit - credit) as balance
            FROM account_move_line aml
            WHERE date < '%s'
            %s
            GROUP BY account_id
        """ % (start_date, query_saldo_where)
        cr.execute (query_saldo)
        result = cr.fetchall()
        saldo_awal = 0
        if len(result) > 0 and len(result[0]) > 0:
            saldo_awal += result[0][0]
                                                     
        query = """
            SELECT 
            aml.date as date, 
            am.state as state, 
            am.name as move_line_name, 
            p.name as partner_name, 
            aml.name as keterangan, 
            aml.debit as debit, 
            aml.credit as credit, 
            res.name as user_name, 
            to_char(aml.create_date + interval '%s', 'HH12:MI AM') as Jam,
            s.name as name_reimbursed
            FROM account_move_line aml 
            LEFT JOIN account_move am ON am.id = aml.move_id 
            LEFT JOIN account_account a ON a.id = aml.account_id 
            LEFT JOIN account_journal aj ON aj.default_debit_account_id = aml.account_id
            LEFT JOIN res_partner p ON p.id = aml.partner_id 
            LEFT JOIN wtc_branch b ON b.id = aml.branch_id 
            LEFT JOIN res_users u ON u.id = aml.create_uid 
            LEFT JOIN res_partner res ON res.id = u.partner_id 
            LEFT JOIN wtc_pettycash m ON  m.move_id=am.id
            LEFT JOIN wtc_reimbursed s  ON s.id=m.reimbursed_id
            %s
            ORDER BY aml.id
            """ % (tz,query_where)
                    
        cr.execute (query)
        
        ress = cr.fetchall()

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
                        
        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        filename = 'Report Petty Cash '+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Laporan Buku Besar Harian Per Posting' , wbf['title_doc'])
        
        worksheet.write('A4', 'Options : Petty Cash' , wbf['company'])
        worksheet.write('A5', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])
        
        worksheet.write('A7', 'No.Rekening : %s - %s'%(str(default_account_code),str(default_account_name)) , wbf['company'])
        worksheet.write('A8', 'No.Sun : %s'%(str(default_account_sap)) , wbf['company'])
        
        worksheet.write('E7', 'Saldo Awal Tanggal :' , wbf['company'])
        worksheet.write('E8', 'Mutasi Debit :' , wbf['company'])
        worksheet.write('E9', 'Mutasi Credit :' , wbf['company'])
        worksheet.write('E10', 'Saldo Akhir Tanggal:' , wbf['company'])
        
        row=11
        rowsaldo = row
        row+=1
        worksheet.write('A%s' % (row+1), 'No' , wbf['header'])
        worksheet.write('B%s' % (row+1), 'Tgl Konf' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'Status' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'No Mutasi' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'Partner' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'Keterangan' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'Debet' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'Credit' , wbf['header'])
        worksheet.write('I%s' % (row+1), 'Saldo' , wbf['header'])
        worksheet.write('J%s' % (row+1), 'Posting' , wbf['header'])
        worksheet.write('K%s' % (row+1), 'Jam' , wbf['header'])
        worksheet.write('L%s' % (row+1), 'No PCR' , wbf['header'])
           
        row+=2               
        no = 1     
        row1 = row
        
        total_debit = 0
        total_credit = 0
        total_saldo = saldo_awal
        
        for res in ress:
            
            tgl_konf = datetime.strptime(res[0], "%Y-%m-%d").date() if res[0] else ''
            state = res[1].encode('ascii','ignore').decode('ascii') if res[1] != None else ''  
            move_line_name = res[2].encode('ascii','ignore').decode('ascii') if res[2] != None else ''  
            partner_name = res[3].encode('ascii','ignore').decode('ascii') if res[3] != None else ''   
            keterangan = res[4].encode('ascii','ignore').decode('ascii') if res[4] != None else ''  
            debit = res[5]
            credit = res[6]
            saldo = debit - credit
            user_name = res[7].encode('ascii','ignore').decode('ascii') if res[7] != None else ''   
            jam = res[8].encode('ascii','ignore').decode('ascii') if res[8] != None else ''
            name_reimbursed = res[9]
            worksheet.write('A%s' % row, no , wbf['content_number'])                    
            worksheet.write('B%s' % row, tgl_konf , wbf['content_date'])
            worksheet.write('C%s' % row, state , wbf['content'])
            worksheet.write('D%s' % row, move_line_name , wbf['content'])
            worksheet.write('E%s' % row, partner_name , wbf['content'])
            worksheet.write('F%s' % row, keterangan , wbf['content'])
            worksheet.write('G%s' % row, debit , wbf['content_float'])
            worksheet.write('H%s' % row, credit , wbf['content_float']) 
            if no == 1 :
                worksheet.write_formula('I%s' % row, '=%s+(%s)' % (saldo_awal, saldo), wbf['content_float'])
            else :
                worksheet.write_formula('I%s' % row, '=I%s+(%d)' % (row-1, saldo), wbf['content_float'])
            worksheet.write('J%s' % row, user_name , wbf['content'])
            worksheet.write('K%s' % row, jam , wbf['content'])
            worksheet.write('L%s' % row, name_reimbursed , wbf['content'])
            
            no+=1
            row+=1
                
            total_debit += debit
            total_credit += credit
            total_saldo += saldo
        
        worksheet.autofilter('A13:K%s' % (row))  
        worksheet.freeze_panes(13, 3)

        worksheet.write_number('F7', saldo_awal , wbf['content_float'])
        worksheet.write('F8', total_debit , wbf['content_float'])
        worksheet.write('F9', total_credit , wbf['content_float'])
        worksheet.write('F10', saldo_awal+total_debit-total_credit , wbf['content_float'])
        
        #TOTAL
        worksheet.merge_range('A%s:E%s' % (row,row), '', wbf['total'])    
        worksheet.write('F%s'%(row), 'Total Per Tanggal', wbf['total'])
        worksheet.merge_range('I%s:K%s' % (row,row), '', wbf['total']) 
        
        formula_total_debit = '{=subtotal(9,G%s:G%s)}' % (row1, row-1) 
        formula_total_credit = '{=subtotal(9,H%s:H%s)}' % (row1, row-1) 

        worksheet.write_formula(row-1,6,formula_total_debit, wbf['total_number'], total_debit)                  
        worksheet.write_formula(row-1,7,formula_total_credit, wbf['total_float'], total_credit)

        worksheet.write('A%s'%(row+3), '%s %s' % (str(date),user) , wbf['footer'])  
        
        worksheet.write('A%s'%(row+5), '        OPERATOR          DIPERIKSA          DIPERIKSA2          DICEK ULANG          DISETUJUI', wbf['footer'])
        worksheet.write('A%s'%(row+6), '       Bag.Komputer          Bag.Arsip               Kep.Kasir                Petugas Kas              Pimpinan', wbf['footer'])
        worksheet.write('A%s'%(row+10),'       (..................)            (..................)          (..................)            (..................)             (..................)', wbf['footer'])
        worksheet.write('A%s'%(row+12), 'NB:- harus ditandatangi kepala bagian masing-2,dan dicocokkan nilainya.', wbf['footer'])
    
                   
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        return True

wtc_report_cash()
