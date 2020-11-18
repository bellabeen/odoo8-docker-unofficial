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



class wtc_all_pettycash(osv.osv_memory):
    _name = 'wtc.report.all.pettycash'
    _description = 'WTC Report All Petty Cash'
    _rec_name = 'option'
    
    wbf={}

    def _get_branch_ids(self, cr, uid, context=None):
        branch_ids_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
        branch_ids = [b.id for b in branch_ids_user]
        return branch_ids
        
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(wtc_all_pettycash, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        branch_ids_user=self.pool.get('res.users').browse(cr,uid,uid).branch_ids
        branch_ids=[b.id for b in branch_ids_user]
        
        doc = etree.XML(res['arch'])      
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
        for node in nodes_branch:
            node.set('domain', '[("id", "in", '+ str(branch_ids)+')]')
        res['arch'] = etree.tostring(doc)
        return res
    

    def _get_default(self,cr,uid,date=False,user=False,context=None):
        if date :
            return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)
        else :
            return self.pool.get('res.users').browse(cr, uid, uid)

    
    _columns = {
        'state_x': fields.selection( ( ('choose','choose'),('get','get'))), #xls
        'data_x': fields.binary('File', readonly=True),
        'name': fields.char('Filename', 100, readonly=True), 
        'option': fields.selection([
                                    ('pettycash_out','Petty Cash Out'),
                                    ('pettycash_in','Petty Cash In'),
                                    ('reimbursed','Reimbursed Petty Cash'),
                                    ('bank_transfer','Bank Transfer'),
                                    ], 'Option', change_default=True, select=True),
        'state_pettycash_out' : fields.selection([
                                    ('draft', 'Draft'),
                                    ('waiting_for_approval','Waiting Approval'),
                                    ('approved', 'Approved'),
                                    ('posted', 'Posted'),
                                    ('reimbursed', 'Reimbursed'),
                                  ],string='State PCO'), 
        'state_pettycash_in' : fields.selection([
                                    ('draft', 'Draft'),
                                    ('posted', 'Posted'),
                                    ('cancel', 'Cancelled'),
                                  ],string='State PCI'),   
        'state_reimburse' : fields.selection([
                                    ('draft', 'Draft'),
                                    ('request', 'Requested'),
                                    ('approved', 'Approved'),
                                    ('reject', 'Rejected'),
                                    ('paid', 'Paid'),
                                    ('cancel', 'Cancelled'),
                                  ],string='State RPC'),    
        'state_bank_transfer' : fields.selection([
                                    ('draft', 'Draft'),
                                    ('waiting_for_approval','Waiting For Approval'),
                                    ('app_approve', 'Approved'),
                                    ('approved','Posted'),
                                  ],string='State BT'),                                             
        'pettycash_id' : fields.many2one('wtc.pettycash',string='Petty Cash',domain="[('state','=','posted'),('division','=',division)]"),                
        'division': fields.selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum')], 'Division', change_default=True, select=True),                 
        'branch_ids': fields.many2many('wtc.branch', 'wtc_all_pettycash_branch_rel', 'wtc_all_pettycash',
                                        'branch_id', 'Branch', copy=False),      
        'journal_id' : fields.many2one('account.journal',string='Payment Method',domain="[('type','=','pettycash')]"),          
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),   
        'journal_bt_id' : fields.many2one('account.journal',string="Bank",domain="['|',('type','=','cash'),('type','=','bank')]"),
                                         
    }
    _defaults = {
        'start_date':_get_default,
        'end_date':_get_default,
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

        if data['option']  == 'pettycash_out' :
            self._print_excel_report_pettycash_out(cr, uid, ids, data, context=context)

        if data['option'] == 'pettycash_in' :
            self._print_excel_report_pettycash_in(cr, uid, ids, data, context=context)

        if data['option'] == 'reimbursed' :
            self._print_excel_report_reimbursed(cr, uid, ids, data, context=context)

        if data['option'] == 'bank_transfer' :
            self._print_excel_report_bank_transfer(cr, uid, ids, data, context=context)


        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_all_pettycash', 'view_wtc_report_all_pettycash')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.report.all.pettycash',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }


    def _print_excel_report_pettycash_out(self, cr, uid, ids, data, context=None): 

        branch_ids = data['branch_ids']
        division = data['division']
        journal_id = data['journal_id'][0] if data['journal_id'] else False
        state_pettycash_out = data['state_pettycash_out']
        start_date = data['start_date']
        end_date = data['end_date']
        # digits = self.pool['decimal.precision'].precision_get(self.cr, self.uid, 'Account')


        query = """
            SELECT 
            pco.id as pco_id, 
            pco.name as pco_name, 
            b.code as branch_code, 
            bd.code as branch_destination_code, 
            pco.division as pco_division, 
            pco.date as pco_date, 
            pco.amount as pco_amount, 
            pco.amount_real as pco_amount_real, 
            j.name as journal_name,
            p.name as partner_name,
            pco.state as pco_state,
            a.name as account_name,
            l.name as line_name,
            l.amount as line_amount, 
            l.amount_real as line_amount_real
            FROM wtc_pettycash pco
            inner join wtc_pettycash_line l ON l.pettycash_id = pco.id
            left join wtc_branch b ON b.id = pco.branch_id
            left join wtc_branch bd ON bd.id = pco.branch_destination_id
            left join account_journal j ON j.id = pco.journal_id
            left join res_users u ON u.id = pco.user_id
            left join account_account a ON a.id = l.account_id
            left join res_partner p ON p.id  = u.partner_id
            where pco.id is not null       
        """
        query_end = ''
        if branch_ids :
            query_end += " AND pco.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        if start_date :
            query_end += " AND pco.date >= '%s' " % str(start_date)
        if end_date :
            query_end += " AND pco.date <= '%s' " % str(end_date)
        if division :
            query_end += " AND pco.division = '%s'" % str(division) 
        if state_pettycash_out :
            query_end += " AND pco.state = '%s'" % str(state_pettycash_out) 
        if journal_id :
            query_end += " AND pco.journal_id = '%s'" % str(journal_id)             
                                               
        query_order = "order by b.code,pco.date"

        cr.execute(query + query_end + query_order)
        all_lines = cr.fetchall()

        pettycash_out = []

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet1 = workbook.add_worksheet('Report Petty Cash Out')
        worksheet2 = workbook.add_worksheet('Report Petty Cash Out Details')

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
        
        filename = 'Report Petty Cash Out'+str(date)+'.xlsx'        
        worksheet1.write('A1', company_name , wbf['company'])
        worksheet1.write('A2', 'Report Petty Cash Out' , wbf['title_doc'])
        worksheet1.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])
        

        # filename = 'Laporan Faktur Pajak Gabungan D'+str(date)+'.xlsx'        
        worksheet2.write('A1', company_name , wbf['company'])
        worksheet2.write('A2', 'Report Petty Cash Out Details' , wbf['title_doc'])
        worksheet2.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])
        
        
        row=5
        rowsaldo = row
        row+=1

        worksheet1.write('A%s' % (row+1), 'No' , wbf['header'])
        worksheet1.write('B%s' % (row+1), 'Petty Cash Ref' , wbf['header'])
        worksheet1.write('C%s' % (row+1), 'Branch Code' , wbf['header'])
        worksheet1.write('D%s' % (row+1), 'Total Amount' , wbf['header'])
        worksheet1.write('E%s' % (row+1), 'Total Amount Real' , wbf['header'])


        worksheet2.write('A%s' % (row+1), 'No' , wbf['header'])
        worksheet2.write('B%s' % (row+1), 'Petty Cash Ref' , wbf['header'])
        worksheet2.write('C%s' % (row+1), 'Branch' , wbf['header'])
        worksheet2.write('D%s' % (row+1), 'Branch Destination' , wbf['header'])
        worksheet2.write('E%s' % (row+1), 'Division' , wbf['header'])
        worksheet2.write('F%s' % (row+1), 'Date' , wbf['header'])
        worksheet2.write('G%s' % (row+1), 'Journal' , wbf['header'])
        worksheet2.write('H%s' % (row+1), 'Responsible' , wbf['header'])
        worksheet2.write('I%s' % (row+1), 'Description' , wbf['header'])
        worksheet2.write('J%s' % (row+1), 'State' , wbf['header'])
        worksheet2.write('K%s' % (row+1), 'Total Amount' , wbf['header'])
        worksheet2.write('L%s' % (row+1), 'Total Amount Real' , wbf['header'])
        



        row+=2               
        no = 1     
        row1 = row
        
        line_amount = 0
        line_amount_real = 0
      

        for res in all_lines:
    
            pco_id = res[0]
            pco_name  = res[1].encode('ascii','ignore').decode('ascii') if res[1] != None else ''
            branch_code  = res[2].encode('ascii','ignore').decode('ascii') if res[2] != None else ''
            branch_destination_code = res[3].encode('ascii','ignore').decode('ascii') if res[3] != None else ''
            pco_division = res[4].encode('ascii','ignore').decode('ascii') if res[4] != None else ''
            pco_date = res[5]
            pco_amount = res[6] if res[6] != None else 0
            pco_amount_real = res[7] if res[6] != None else 0
            journal_name = res[8]
            partner_name = res[9]
            pco_state = res[10]
            account_name = res[11]
            line_name = res[12]
            line_amount = res[13]
            line_amount_real = res[14]


            # sum_total_amount += line_amount
            # sum_amount_real += line_amount_real


            worksheet1.write('A%s' % row, no, wbf['content_number'])                    
            worksheet1.write('B%s' % row, pco_name, wbf['content'])
            worksheet1.write('C%s' % row, branch_code, wbf['content'])
            worksheet1.write('D%s' % row, line_amount, wbf['content_float'])
            worksheet1.write('E%s' % row, line_amount_real, wbf['content_float'])

            worksheet2.write('A%s' % row, no, wbf['content_number']) 
            worksheet2.write('B%s' % row, pco_name, wbf['content'])  
            worksheet2.write('C%s' % row, branch_code, wbf['content'])
            worksheet2.write('D%s' % row, branch_destination_code, wbf['content'])
            worksheet2.write('E%s' % row, pco_division, wbf['content'])
            worksheet2.write('F%s' % row, pco_date, wbf['content_date'])
            worksheet2.write('G%s' % row, journal_name, wbf['content'])
            worksheet2.write('H%s' % row, partner_name, wbf['content'])        
            worksheet2.write('I%s' % row, line_name, wbf['content'])
            worksheet2.write('J%s' % row, pco_state, wbf['content'])
            worksheet2.write('K%s' % row, line_amount, wbf['content_float'])
            worksheet2.write('L%s' % row, line_amount_real, wbf['content_float'])
            
  

            no+=1
            row+=1

            line_amount = line_amount
            line_amount_real = line_amount_real
            

        worksheet1.autofilter('A7:C%s' % (row))  
        worksheet1.freeze_panes(7, 3)

        worksheet2.autofilter('A7:J%s' % (row))  
        worksheet2.freeze_panes(7, 3)

        #TOTAL
        ##sheet 1
        worksheet1.merge_range('A%s:C%s' % (row,row), 'Total', wbf['total'])    
        worksheet1.write('D%s'%(row), '', wbf['total'])
        worksheet1.write('E%s'%(row), '', wbf['total'])
        ##sheet 2
        worksheet2.merge_range('A%s:C%s' % (row,row), 'Total', wbf['total'])    
        worksheet2.merge_range('D%s:J%s' % (row,row), '', wbf['total'])
        worksheet2.write('K%s'%(row), '', wbf['total'])
        worksheet2.write('L%s'%(row), '', wbf['total'])
        
        

        ##sheet 1
        formula_total_line_amount_satu = '{=subtotal(9,D%s:D%s)}' % (row1, row-1) 
        formula_total_line_amount_real_satu = '{=subtotal(9,E%s:E%s)}' % (row1, row-1) 
      
        ##sheet 2
        formula_total_line_amount = '{=subtotal(9,K%s:K%s)}' % (row1, row-1) 
        formula_total_line_amount_real = '{=subtotal(9,L%s:L%s)}' % (row1, row-1) 



        ##sheet 1
        worksheet1.write_formula(row-1,3,formula_total_line_amount_satu, wbf['total_float'], line_amount)
        worksheet1.write_formula(row-1,4,formula_total_line_amount_real_satu, wbf['total_float'], line_amount_real)                    

        ##sheet 2
        worksheet2.write_formula(row-1,10,formula_total_line_amount, wbf['total_float'], line_amount) 
        worksheet2.write_formula(row-1,11,formula_total_line_amount_real, wbf['total_float'], line_amount_real) 



      
        worksheet1.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer']) 
        worksheet2.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])     
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        return True

    # def print_report_all_pettycash(self, cr, uid, ids, context=None):
    #     if context is None :
    #         context = {}
    #     data = self.read(cr, uid, ids)[0]
    #     if len(data['branch_ids']) == 0 :
    #         data.update({'branch_ids': self._get_branch_ids(cr, uid, context)})
    #     if context.get('options') == 'pettycash_out' :
    #         return {'type': 'ir.actions.report.xml', 'report_name': 'Report Petty Cash Out', 'datas': data}            
    #     elif context.get('options') == 'pettycash_in' :
    #         return {'type': 'ir.actions.report.xml', 'report_name': 'Report Petty Cash In', 'datas': data}            
    #     elif context.get('options') == 'reimbursed' :
    #         return {'type': 'ir.actions.report.xml', 'report_name': 'Report Reimburse Petty Cash', 'datas': data}            
    #     elif context.get('options') == 'bank_transfer' :
    #         return {'type': 'ir.actions.report.xml', 'report_name': 'Report Bank Transfer', 'datas': data}            

    # def xls_export(self, cr, uid, ids, context=None):
    #     return self.print_report_all_pettycash(cr, uid, ids, context=context)
