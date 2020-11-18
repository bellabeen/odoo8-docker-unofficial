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

class report_advance_payment(osv.osv_memory):
    _name = 'wtc.report.advance.payment'
    _description = 'Report Advance Payment'
    _rec_name = 'name'


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
        res = super(report_advance_payment, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
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
        'fname': fields.char('Filename', 100, readonly=True), 

        'name' : fields.char(string="Name"),
        'options': fields.selection([('Advanced Payment','Advance Payment'),('Settlement Advance Payment','Settlement Advance Payment')], 'Options', change_default=True, select=True),
        'status': fields.selection([('reconciled','Reconciled'),('outstanding','Outstanding')], 'Status', change_default=True, select=True),
        'division': fields.selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum')], 'Division', change_default=True, select=True),         
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'branch_ids': fields.many2many('wtc.branch', 'wtc_report_advance_payment_branch_rel', 'wtc_report_advance_payment',
                                        'branch_id', 'Branch', copy=False),
        'partner_ids': fields.many2many('res.partner', 'wtc_report_advance_payment_partner_rel', 'wtc_report_advance_payment',
                                        'partner_id', 'Partner', copy=False, ), 
        'journal_ids': fields.many2many('account.journal', 'wtc_report_advance_payment_journal_rel', 'wtc_report_advance_payment',
                                        'journal_id', 'Journal', copy=False, ),         
        'account_ids': fields.many2many('account.account', 'wtc_report_advance_payment_account_rel', 'wtc_report_advance_payment',
                                        'account_id', 'Account', copy=False, ),                                      
    }

    _defaults = {
                 'start_date':datetime.today(),
                 'end_date':datetime.today(),
                 'name':'#',
                 'status' : 'outstanding'
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
            
        if data['options']=='Advanced Payment':
            self._print_excel_report(cr, uid, ids, data, context=context)
        else:
            self._print_excel_report_settlement(cr, uid, ids, data, context=context)
        
        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_advance_payment', 'view_report_advance_payment')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.report.advance.payment',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }
       
    

    def _print_excel_report(self, cr, uid, ids, data, context=None):

        branch_ids = data['branch_ids']
        partner_ids = data['partner_ids']
        journal_ids = data['journal_ids']
        account_ids = data['account_ids']
        division = data['division']
        start_date = data['start_date']
        end_date = data['end_date']
        status = data['status']
        options = data['options']
        title_prefix = ''
        title_short_prefix = ''

        # report_advance_payment = {
        #     'type': 'Advance Payment',
        #     'title': '',
        #     'title_short': title_short_prefix + ', ' + ('LAPORAN BON SEMENTARA'),
        #     'start_date': start_date,
        #     'end_date': end_date          
        #     }  

        where_partner = " 1=1 "
        if partner_ids :
            where_partner=" p.id  in %s " % str(
                tuple(partner_ids)).replace(',)', ')')  
                            
        where_branch = " 1=1 "
        if branch_ids :
            where_branch = " b.id in %s " % str(
                tuple(branch_ids)).replace(',)', ')')             
        else :
            area_user = self.pool.get('res.users').browse(cr,uid,uid).branch_ids
            branch_ids_user = [b.id for b in area_user]
            if branch_ids_user :
                where_branch = " b.id in %s " % str(
                    tuple(branch_ids_user))
        
        where_journal = " 1=1 "
        if journal_ids :
            where_journal=" j.id  in %s " % str(
                tuple(journal_ids)).replace(',)', ')')   
                 
        where_account = " 1=1 "
        if account_ids :
            where_account=" a.id  in %s " % str(
                tuple(account_ids)).replace(',)', ')') 
                                          
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

        where_status = " 1=1 "
        if status == 'reconciled' :
            where_status = " l.reconcile_id is not null "
        elif status == 'outstanding' :
            where_status = " l.reconcile_id is null "
        
        query_advance_payment = "SELECT b.code as branch_code, "\
            "a.code as no_rek, "\
            "l.date as date, "\
            "m.name as no_bukti, "\
            "l.reconcile_id as reconcile_id, "\
            "ap.description as keterangan, "\
            "p.name as partner, "\
            "l.debit as total, "\
            "ps.name as user, "\
            "l.date_maturity as due_date "\
            "FROM account_move_line l "\
            "LEFT JOIN wtc_branch b ON b.id = l.branch_id "\
            "LEFT JOIN wtc_advance_payment ap ON ap.account_move_id = l.move_id "\
            "LEFT JOIN res_users u ON u.id = l.create_uid "\
            "LEFT JOIN res_partner p ON p.id = l.partner_id "\
            "LEFT JOIN res_partner ps ON ps.id = u.partner_id "\
            "LEFT JOIN account_move m ON m.id = l.move_id "\
            "LEFT JOIN account_account a ON a.id = l.account_id "\
            "LEFT JOIN account_journal j ON j.id = l.journal_id "\
            "WHERE a.type = 'receivable' AND ap.account_move_id is not null AND "+where_journal+" AND "+where_status+" AND "+where_partner+" AND "+where_branch+" AND " ""\
            ""+where_account+" AND "+where_division+" AND "+where_start_date+" AND "+where_end_date+" "\
            "ORDER BY l.date,b.code"

        move_selection = ""
        report_info = ('')
        move_selection += ""
            
        # reports = [report_advance_payment]

        cr.execute(query_advance_payment)
        all_lines = cr.dictfetchall()
#         print">>>>>>>>>>>>>>>>>>>>>>>>>>>",(query_advance_payment)


        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('%s' %(options))

        worksheet.set_column('B1:B1', 13)
        worksheet.set_column('C1:C1', 20)
        worksheet.set_column('D1:D1', 20)
        worksheet.set_column('E1:E1', 30)
        worksheet.set_column('F1:F1', 20)
        worksheet.set_column('G1:G1', 20)
        worksheet.set_column('H1:H1', 20)
        worksheet.set_column('I1:I1', 20)
        worksheet.set_column('J1:J1', 20)
        worksheet.set_column('K1:K1', 20)



        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        filename = 'LAPORAN BON SEMENTARA %s '%(options)+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Laporan Bon Sementara' , wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date),str(end_date)) , wbf['company'])

        row=5
        rowsaldo = row
        row+=1

        worksheet.write('A%s' % (row+1), 'No' , wbf['header'])
        worksheet.write('B%s' % (row+1), 'Cabang' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'No Rek' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'Tanggal' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'No Bukti' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'Sts' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'Keterangan' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'Diberikan Ke' , wbf['header'])
        worksheet.write('I%s' % (row+1), 'Total' , wbf['header'])
        worksheet.write('J%s' % (row+1), 'Pembuat' , wbf['header'])
        worksheet.write('K%s' % (row+1), 'Tanggal Jatuh Tempo' , wbf['header'])

        row+=2       
        no = 1
        row1 = row

        total = 0
        for x in all_lines:

            branch_code = x['branch_code'].encode('ascii','ignore').decode('ascii') if x['branch_code'] != None else ''
            no_rek = x['no_rek'].encode('ascii','ignore').decode('ascii') if x['no_rek'] != None else ''  
            date = x['date'].encode('ascii','ignore').decode('ascii') if x['date'] != None else ''    
            no_bukti = x['no_bukti'].encode('ascii','ignore').decode('ascii') if x['no_bukti'] != None else ''    
            sts = 'Reconciled' if x['reconcile_id'] else 'Outstanding'
            keterangan = x['keterangan'].encode('ascii','ignore').decode('ascii') if x['keterangan'] != None else ''
            partner = x['partner'].encode('ascii','ignore').decode('ascii') if x['partner'] != None else ''    
            total = x['total']
            user = x['user'].encode('ascii','ignore').decode('ascii') if x['user'] != None else ''
            due_date = x['due_date'].encode('ascii','ignore').decode('ascii') if x['due_date'] != None else ''  


            worksheet.write('A%s' % row, no, wbf['content_number']) 
            worksheet.write('B%s' % row, branch_code, wbf['content'])  
            worksheet.write('C%s' % row, no_rek, wbf['content'])
            worksheet.write('D%s' % row, date, wbf['content_date'])
            worksheet.write('E%s' % row, no_bukti, wbf['content'])
            worksheet.write('F%s' % row, sts, wbf['content'])
            worksheet.write('G%s' % row, keterangan, wbf['content'])
            worksheet.write('H%s' % row, partner, wbf['content'])
            worksheet.write('I%s' % row, total, wbf['content_float'])   
            worksheet.write('J%s' % row, user, wbf['content']) 
            worksheet.write('K%s' % row, due_date, wbf['content_date'])      
            
            no+=1
            row+=1
            total = total

        worksheet.autofilter('A7:G%s' % (row))  
        worksheet.freeze_panes(7, 3)

        #TOTAL
        #sheet 1
        worksheet.merge_range('A%s:H%s' % (row,row), 'Total', wbf['total'])    
        worksheet.write('I%s'%(row), '', wbf['total'])
        worksheet.merge_range('J%s:K%s' % (row,row), '', wbf['total'])  
       

        #sheet 1
        formula_total= '{=subtotal(9,H%s:H%s)}' % (row1, row-1) 
       
        
        #sheet 1
        worksheet.write_formula(row-1,7,formula_total, wbf['total_float'], total)  
      
      
        worksheet.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer']) 
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'fname': filename}, context=context)
        fp.close()

#         ir_model_data = self.pool.get('ir.model.data')
#         form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_advance_payment', 'view_report_advance_payment')
# 
#         form_id = form_res and form_res[1] or False
#         return {
#             'name': _('Download XLS'),
#             'view_type': 'form',
#             'view_mode': 'form',
#             'res_model': 'wtc.report.advance.payment',
#             'res_id': ids[0],
#             'view_id': False,
#             'views': [(form_id, 'form')],
#             'type': 'ir.actions.act_window',
#             'target': 'current'
#         }

report_advance_payment()

   