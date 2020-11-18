import time
import cStringIO
import xlsxwriter
from cStringIO import StringIO
import base64
import tempfile
import os
from openerp import models, fields, api, _
#from openerp.tools.translate import _
from datetime import datetime, timedelta,date
from dateutil.relativedelta import relativedelta
from xlsxwriter.utility import xl_rowcol_to_cell
import logging
import re
import pytz
from lxml import etree

class export_bank_mutasi(models.TransientModel):
    _name = "teds.export.bank.mutasi"
    
    def _get_default_branch(self):
        branch_ids = False
        branch_ids = self.env.user.branch_ids
        if branch_ids and len(branch_ids) == 1 :
            return branch_ids[0].id
        return False

    @api.model
    def _get_default_date(self): 
        return self.env['wtc.branch'].get_default_date()

    @api.model
    def _get_default_datetime(self): 
        return self.env['wtc.branch'].get_default_datetime_model()

    def _get_default_start_date(self):
        return date.today().replace(day=1)

    def _get_default_end_date(self):
        return date.today() - relativedelta(days=1)

    wbf = {}

    name = fields.Char('Filename', readonly=True)
    state_x = fields.Selection([('choose','choose'),('get','get')], default='choose')
    data_x = fields.Binary('File', readonly=True)
    options = fields.Selection([('All','All'),('No Sistem Kosong','No Sistem Kosong')], 'Options',default='No Sistem Kosong') 
    tgl_upload = fields.Date('Tanggal Upload')
    tgl_mutasi = fields.Date('Tanggal Mutasi')
    start_date = fields.Date('Start Date',default=_get_default_start_date)
    end_date = fields.Date('End Date',default=_get_default_end_date)
    status = fields.Selection([
        ('All','All'),
        ('Outstanding','Outstanding'),
        ('Reconciled','Reconciled')],default='All')

    account_id = fields.Many2one('account.account',string='Account',domain="[('type','=','liquidity'),('branch_id','=',branch_id)]")
    branch_id = fields.Many2one('wtc.branch', string='Branch', required=True, default=_get_default_branch)
 
    @api.multi
    def add_workbook_format(self, workbook):      
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

        self.wbf['content_number'] = workbook.add_format({'align': 'center'})
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

    @api.multi
    def excel_report(self):
        self.ensure_one()
        if self.options:
            return self._print_export_bank_mutasi()

    def _print_export_bank_mutasi(self):
        branch_id = self.branch_id.id
        tgl_upload = self.tgl_upload
        tgl_mutasi = self.tgl_mutasi
        account_id = self.account_id.id
        status = self.status
        options = self.options

        query_where = "WHERE 1=1 "
        if branch_id:
            query_where += " AND bm.branch_id = '%s'" %str(branch_id)
        if tgl_upload:
            query_where += " AND bm.date_upload = '%s'" %str(tgl_upload)
        if tgl_mutasi:
            query_where += " AND bm.date = '%s'" %str(tgl_mutasi)
        if self.start_date:
            query_where += " AND bm.date >= '%s'" %str(self.start_date)
        if self.end_date:
            query_where += " AND bm.date <= '%s'" %str(self.end_date)

        if status:
            if status == 'Outstanding':
                query_where += " AND bm.state = 'Outstanding'"
            elif status == 'Reconciled':
                query_where += " AND bm.state in ('Reconciled','Auto Reconcile')"
        if account_id :
            query_where += " AND bm.account_id = '%s'" %str(account_id)
        if options == 'No Sistem Kosong':
            query_where += " AND (bm.no_sistem = '' or bm.no_sistem IS NULL)"
        
        query = """
                    SELECT name
                        , date
                        , date_upload
                        , remark
                        , teller
                        , debit
                        , credit
                        , saldo
                        , coa
                        , no_sistem
                        , state
                    FROM teds_bank_mutasi bm %s
                """ % (query_where)
        self.env.cr.execute(query)
        ress = self.env.cr.dictfetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)       
        workbook = self.add_workbook_format(workbook)
        wbf = self.wbf
        worksheet = workbook.add_worksheet('Bank Mutasi')
        worksheet.set_column('A1:A1', 26)
        worksheet.set_column('B1:B1', 13)
        worksheet.set_column('C1:C1', 36)
        worksheet.set_column('D1:D1', 22)
        worksheet.set_column('E1:E1', 20)
        worksheet.set_column('F1:F1', 20)
        worksheet.set_column('G1:G1', 19)
        worksheet.set_column('H1:H1', 19)
        worksheet.set_column('I1:I1', 26)
        worksheet.set_column('J1:J1', 20)

      
        date = self._get_default_datetime()
        date = date.strftime("%d-%m-%Y %H:%M:%S")

        # company_name = self.branch_id.company_id.name
        # user_id = self.env['res.user'].search([('id','=',self._uid)])
        # user = user_id.name 
        filename = 'Export Bank Mutasi'+str(date)+'.xlsx'

        worksheet.write('A1', 'Name' , wbf['header'])
        worksheet.write('B1', 'Tanggal' , wbf['header'])
        worksheet.write('C1', 'Remark' , wbf['header'])
        worksheet.write('D1', 'Teller' , wbf['header'])
        worksheet.write('E1', 'Debit' , wbf['header'])
        worksheet.write('F1', 'Credit' , wbf['header'])
        worksheet.write('G1', 'Saldo Akhir' , wbf['header'])
        worksheet.write('H1', 'COA' , wbf['header'])
        worksheet.write('I1', 'No Sistem' , wbf['header'])
        worksheet.write('J1', 'Status' , wbf['header'])

        row=1
        row+=1
        for res in ress:
            name = str(res.get('name').encode('ascii','ignore').decode('ascii')) if res.get('name') != None else ''
            date = str(res.get('date').encode('ascii','ignore').decode('ascii')) if res.get('date') != None else ''
            remark = str(res.get('remark').encode('ascii','ignore').decode('ascii')) if res.get('remark') != None else ''
            teller = str(res.get('teller').encode('ascii','ignore').decode('ascii')) if res.get('teller') != None else ''
            debit = res.get('debit') if res.get('debit') != None else 0
            credit = res.get('credit') if res.get('credit') != None else 0
            saldo = res.get('saldo') if res.get('saldo') != None else 0
            coa = str(res.get('coa').encode('ascii','ignore').decode('ascii')) if res.get('coa') != None else ''
            no_sistem = str(res.get('no_sistem').encode('ascii','ignore').decode('ascii')) if res.get('no_sistem') != None else ''
            state = res.get('state','')

            worksheet.write('A%s' % row, name , wbf['content_number'])                    
            worksheet.write('B%s' % row, date , wbf['content'])
            worksheet.write('C%s' % row, remark , wbf['content'])
            worksheet.write('D%s' % row, teller , wbf['content'])
            worksheet.write('E%s' % row, debit , wbf['content_float'])
            worksheet.write('F%s' % row, credit , wbf['content_float'])
            worksheet.write('G%s' % row, saldo , wbf['content_float'])
            worksheet.write('H%s' % row, coa , wbf['content'])  
            worksheet.write('I%s' % row, no_sistem , wbf['content'])
            worksheet.write('J%s' % row, state , wbf['content'])
            row+=1
        
        worksheet.autofilter('A1:J1') 

        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write({'state_x':'get', 'data_x':out, 'name': filename})
        fp.close()

        res = self.env.ref('teds_bank_reconcile.view_teds_export_bank_mutasi_wizard', False)

        form_id = res and res.id or False

        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.export.bank.mutasi',
            'res_id': self.ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        } 