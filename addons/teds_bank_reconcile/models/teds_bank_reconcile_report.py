import time
import cStringIO
import xlsxwriter
from cStringIO import StringIO
import base64
import tempfile
import os
from openerp import models, fields, api, _
#from openerp.tools.translate import _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from xlsxwriter.utility import xl_rowcol_to_cell
import logging
import re
import pytz
from lxml import etree

class teds_bank_reconcile_report(models.TransientModel):
    _name = "teds.bank.reconcile.report"
    _description = "TEDS Bank Reconcile Report"


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
        return self.env['wtc.branch'].get_default_datetime()

    wbf = {}

    name = fields.Char('Filename', readonly=True)
    state_x = fields.Selection([('choose','choose'),('get','get')], default='choose')
    data_x = fields.Binary('File', readonly=True)
    options = fields.Selection([('Outstanding','Outstanding')], 'Options',default='Outstanding') 
    start_date = fields.Date('Start Date',default=_get_default_date)
    end_date = fields.Date('End Date', default=_get_default_date)
    branch_id = fields.Many2one('wtc.branch', string='Branch', required=True, default=_get_default_branch)
    account_id = fields.Many2one('account.account',string='Account',domain="[('type','=','liquidity'),('branch_id','=',branch_id)]")
    journal_id = fields.Many2one('account.journal',string='Journal',domain="[('branch_id','=',branch_id),('type','=','bank')]")
    # no_sistem = fields.Char('No Sistem')

    # @api.onchange('branch_id')
    # def onchange_branch_id(self):
    #     branch_id = self.branch_id.id
    #     if self.journal_id.branch_id == branch_id:
    #         self.journal_id = True
    #     else:
    #         self.journal_id = False

    # @api.onchange('options')
    # def onchange_start_date(self):
    #     if self.options == 'No Sistem':
    #         self.start_date = False
    #         self.end_date = False
        


    @api.multi
    def add_workbook_format(self, workbook):
        self.wbf['company'] = workbook.add_format({'bold':1,'align': 'left','font_color':'#000000','num_format': 'dd-mm-yyyy'})
        self.wbf['company'].set_font_size(10)
        
        self.wbf['bg_gl'] = workbook.add_format({'bg_color':'#21610B','font_color':'#FFFFFF','align':'center'})
        self.wbf['bg_gl'].set_border(2)
        self.wbf['bg_gl'].set_font_size(10)
        
        self.wbf['bg_rk'] = workbook.add_format({'bg_color':'#0000FF','font_color':'#FFFFFF','align':'center'})
        self.wbf['bg_rk'].set_border(2)
        self.wbf['bg_rk'].set_font_size(10)

        self.wbf['header'] = workbook.add_format({'bold': 1,'align': 'center','font_color': '#000000'})
        self.wbf['header'].set_top()
        self.wbf['header'].set_bottom()
        self.wbf['header'].set_font_size(10)
 
        self.wbf['header_right'] = workbook.add_format({'bold': 1,'align': 'center','font_color': '#000000'})
        self.wbf['header_right'].set_top()
        self.wbf['header_right'].set_bottom()
        self.wbf['header_right'].set_right(2)
        self.wbf['header_right'].set_font_size(10)

        self.wbf['header_right2'] = workbook.add_format({'bold': 1,'align': 'center','font_color': '#000000'})
        self.wbf['header_right2'].set_right(2)
        
        self.wbf['header_saldo'] = workbook.add_format({'bold': 1,'align': 'left','font_color': '#0080ff'})
        self.wbf['header_saldo'].set_font_size(10)
        
        self.wbf['header_saldo_right'] = workbook.add_format({'bold': 1,'align': 'right','font_color': '#0080ff','num_format': '#,##0.00'})
        self.wbf['header_saldo_right'].set_right(2)
        self.wbf['header_saldo_right'].set_font_size(10)


        self.wbf['footer_border'] = workbook.add_format({})
        self.wbf['footer_border'].set_border(2)

        self.wbf['content'] = workbook.add_format({'align': 'left','font_color': '#000000'})
        self.wbf['content'].set_font_size(10)
        
        self.wbf['content_date'] = workbook.add_format({'align': 'center','num_format': 'yyyy-mm-dd','font_color': '#000000'})
        self.wbf['content_date'].set_font_size(10)
        
        self.wbf['content_float'] = workbook.add_format({'align': 'right','num_format': '#,##0.00'})
        self.wbf['content_float'].set_font_size(10)
        self.wbf['content_float'].set_right(2) 

        self.wbf['content_new'] = workbook.add_format({'align': 'left','font_color': '#2E9AFE'})
        self.wbf['content_new'].set_font_size(10)
        
        self.wbf['content_date_new'] = workbook.add_format({'align': 'center','num_format': 'yyyy-mm-dd','font_color': '#2E9AFE'})
        self.wbf['content_date_new'].set_font_size(10)
        
        self.wbf['content_float_new'] = workbook.add_format({'align': 'right','num_format': '#,##0.00','font_color': '#2E9AFE'})
        self.wbf['content_float_new'].set_font_size(10)
        self.wbf['content_float_new'].set_right(2)
        
        self.wbf['footer1'] = workbook.add_format({'font_color':'#B45F04'})
        self.wbf['footer1'].set_font_size(10)
        self.wbf['footer1'].set_bottom(2)

        self.wbf['footer1_right'] = workbook.add_format({'font_color':'#B45F04','align':'right','num_format':'#,##0.00'})
        self.wbf['footer1_right'].set_font_size(10)
        self.wbf['footer1_right'].set_bottom(2)
        self.wbf['footer1_right'].set_right(2) 

        self.wbf['header2'] = workbook.add_format()
        self.wbf['header2'].set_font_size(10)
        self.wbf['header2'].set_top(2)
        self.wbf['header2'].set_right(2)
                
        
        return workbook

    @api.multi
    def excel_report(self):
        self.ensure_one()

        if self.options == 'Outstanding':
            return self._print_export_account_outstanding()
        

    def _print_export_account_outstanding(self):
        branch_id = self.branch_id.id
        account_id = self.account_id.id

        code_branch = self.branch_id.code
        name_branch = self.branch_id.name
        profit_branch = self.branch_id.profit_centre
        periode = self.end_date
        account_code = self.account_id.code
        account_name = self.account_id.name
        account_sap = self.account_id.sap[0:6]
        account_sap_code = self.account_id.sap[-3:]

        total_jumlah_kiri = 0
        total_jumlah_kanan = 0

        saldo_sb_rec = 0
        saldo_rk = 0

        # Query Saldo Sebelum Reconcile
        query_sb_rec = """
                        SELECT SUM(debit-credit) as jumlah_saldo 
                        FROM account_move_line 
                        WHERE date <= '%s'
                    """ %(periode)
        
        where_sb_rec = " AND 1=1"
        # if branch_id:
        #     where_sb_rec += " AND branch_id='%s'" %str(branch_id)
        if account_id:
            where_sb_rec += " AND account_id='%s'" %str(account_id)

        self.env.cr.execute(query_sb_rec+where_sb_rec)
        ress_sb_rec = self.env.cr.dictfetchall()
        a = ress_sb_rec[0]
        saldo_qr_rec = a.get('jumlah_saldo')
        if saldo_qr_rec != None:
            saldo_sb_rec += saldo_qr_rec 

            total_jumlah_kiri += saldo_qr_rec
        
        # Query Saldo Rekening Koran
        query_saldo_rk = """
                        SELECT SUM(credit-debit) as jumlah_saldo 
                        FROM teds_bank_mutasi 
                        WHERE (date <= '%s' or date is null)
                    """ %(periode)
        
        where_saldo_rk = " AND 1=1"
        # if branch_id:
        #     where_saldo_rk += " AND branch_id='%s'" %str(branch_id)
        if account_id:
            where_saldo_rk += " AND account_id='%s'" %str(account_id)
        
        self.env.cr.execute(query_saldo_rk+where_saldo_rk)
        ress_saldo_rk = self.env.cr.dictfetchall()
        b = ress_saldo_rk[0]
        saldo_qr_rk = b.get('jumlah_saldo')
        if saldo_qr_rk != None:
            saldo_rk += saldo_qr_rk

            total_jumlah_kanan += saldo_rk

        order_by = "ORDER BY date ASC"
        # Query Data Account Move Line
        query_aml = """
                    SELECT 
                        date,ref,name,debit,credit 
                    FROM account_move_line WHERE (effective_date_reconcile > '%s' OR effective_date_reconcile is null)
                """ %(periode)
        where_aml = " AND 1=1"
        # if branch_id:
        #     where_aml += " AND branch_id='%s'" %str(branch_id)
        if account_id:
            where_aml += " AND account_id='%s'" %str(account_id)
        self.env.cr.execute(query_aml+where_aml+order_by)
        ress1 = self.env.cr.dictfetchall()

        # Query Data Bank Mutasi
        query_bm = """
                    SELECT
                        date,no_sistem,remark,credit,debit 
                    FROM teds_bank_mutasi 
                    WHERE (effective_date_reconcile > '%s' OR effective_date_reconcile is null)
                """ %(periode)
        where_bm = " AND 1=1"
        # if branch_id:
        #     where_bm += " AND branch_id='%s'" %str(branch_id)
        if account_id:
            where_bm += " AND account_id='%s'" %str(account_id)
        self.env.cr.execute(query_bm+where_bm+order_by)
        ress2 = self.env.cr.dictfetchall()


        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)       
        workbook = self.add_workbook_format(workbook)
        wbf = self.wbf
        worksheet = workbook.add_worksheet('Journal')
        worksheet.set_column('A1:A1', 15)
        worksheet.set_column('B1:B1', 22)
        worksheet.set_column('C1:C1', 54)
        worksheet.set_column('D1:D1', 24)
        worksheet.set_column('E1:E1', 17)
        worksheet.set_column('F1:F1', 24)
        worksheet.set_column('G1:G1', 21)
        worksheet.set_column('H1:H1', 24)

        date_now = self._get_default_datetime()
        date1 = date_now.strftime("%d-%m-%Y %H:%M:%S")
        date2 = date_now.strftime("%d-%m-%Y")


        company_name = self.branch_id.company_id.name
        user_id = self.env['res.users'].search([('id','=',self._uid)])
        user = user_id.name 
        filename = 'Report Bank Reconcile'+str(date1)+'.xlsx'

        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'REKONSILIASI BANK' , wbf['company'])
        
        worksheet.write('A4', 'CABANG' , wbf['company'])
        worksheet.write('B4', "[%s] %s" %(code_branch,name_branch) , wbf['company'])
        worksheet.write('A5', 'PERIODE' , wbf['company'])
        worksheet.write('B5', periode , wbf['company'])
        worksheet.write('A6', 'ACCOUNT' , wbf['company'])
        worksheet.write('B6', account_code , wbf['company'])
        worksheet.write('C6', "%s-%s-%s" %(account_sap,profit_branch,account_sap_code) , wbf['company'])

        worksheet.write('A7', 'Description' , wbf['company'])
        worksheet.write('B7', account_name , wbf['company'])

        row=9
        worksheet.merge_range('A%s:D%s' % (row,row), 'SALDO GL TEDS', wbf['bg_gl'])
        worksheet.merge_range('E%s:H%s' % (row,row), 'SALDO REKENING KORAN', wbf['bg_rk'])

        worksheet.write('A%s' % (row+1), 'Tanggal' , wbf['header'])
        worksheet.write('B%s' % (row+1), 'No. Sistem' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'Keterangan' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'Jumlah' , wbf['header_right'])
        worksheet.write('E%s' % (row+1), 'Tanggal' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'No. Sistem' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'Keterangan' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'Jumlah' , wbf['header_right'])

        row+=1
        worksheet.write('D%s' % (row+1), '' , wbf['header_right2'])
        worksheet.write('H%s' % (row+1), '' , wbf['header_right2'])

        row+=1
        

        worksheet.write('B%s' % (row+1), 'Saldo Sebelum Reconcile ' , wbf['header_saldo'])
        worksheet.write('D%s' % (row+1), saldo_sb_rec , wbf['header_saldo_right'])

        worksheet.write('F%s' % (row+1), 'Saldo Rekening Koran ' , wbf['header_saldo'])
        worksheet.write('H%s' % (row+1), saldo_rk , wbf['header_saldo_right'])

        row+=1
        row1=row
       
        worksheet.write('D%s' % (row+1), '' , wbf['header_right2'])
        worksheet.write('H%s' % (row+1), '' , wbf['header_right2'])

        row +=2

        jumlah_bm = 0
        for res in ress2:
            date = datetime.strptime(res.get('date'), "%Y-%m-%d").date() if res.get('date') != None else ''
            no_sistem = str(res.get('no_sistem').encode('ascii','ignore').decode('ascii')) if res.get('no_sistem') != None else ''
            remark = str(res.get('remark').encode('ascii','ignore').decode('ascii')) if res.get('remark') != None else '' 
            credit = res.get('credit') if res.get('credit') else 0 
            debit = res.get('debit') if res.get('debit') else 0
            jumlah_bm = credit-debit
            if jumlah_bm >= 0:

                # total_jumlah_kanan += jumlah_bm

                worksheet.write('A%s' % row, date , wbf['content_date'])                    
                worksheet.write('B%s' % row, no_sistem , wbf['content'])
                worksheet.write('C%s' % row, remark , wbf['content'])
                worksheet.write('D%s' % row, jumlah_bm , wbf['content_float'])
                worksheet.write('H%s' % row, '' , wbf['content_float'])

                row+=1

                worksheet.write('D%s' % (row+1), '' , wbf['header_right2'])
                worksheet.write('H%s' % (row+1), '' , wbf['header_right2'])
       
        row+=1
        worksheet.write('D%s' % (row+1), '' , wbf['header_right2'])
        worksheet.write('H%s' % (row+1), '' , wbf['header_right2'])
        
        jumlah_aml = 0
        for res in ress1:
            date = datetime.strptime(res.get('date'), "%Y-%m-%d").date() if res.get('date') != None else ''
            ref = str(res.get('ref').encode('ascii','ignore').decode('ascii')) if res.get('ref') != None else ''
            name = str(res.get('name').encode('ascii','ignore').decode('ascii')) if res.get('name') != None else ''
            debit = res.get('debit') if res.get('debit') else 0
            credit = res.get('credit') if res.get('credit') else 0
            jumlah_aml = credit-debit
            if jumlah_aml >= 0:     
                total_jumlah_kiri += jumlah_aml

                worksheet.write('A%s' % row, date , wbf['content_date_new'])                    
                worksheet.write('B%s' % row, ref , wbf['content_new'])
                worksheet.write('C%s' % row, name , wbf['content_new'])
                worksheet.write('D%s' % row, jumlah_aml , wbf['content_float_new'])
                worksheet.write('H%s' % row, '' , wbf['content_float'])

                row+=1

                worksheet.write('D%s' % (row+1), '' , wbf['header_right2'])
                worksheet.write('H%s' % (row+1), '' , wbf['header_right2'])
        
        row+=1
        worksheet.write('D%s' % (row+1), '' , wbf['header_right2'])
        worksheet.write('H%s' % (row+1), '' , wbf['header_right2'])
        for res in ress2:
            date = datetime.strptime(res.get('date'), "%Y-%m-%d").date() if res.get('date') != None else ''
            no_sistem = str(res.get('no_sistem').encode('ascii','ignore').decode('ascii')) if res.get('no_sistem') != None else ''
            remark = str(res.get('remark').encode('ascii','ignore').decode('ascii')) if res.get('remark') != None else '' 
            credit = res.get('credit') if res.get('credit') else 0 
            debit = res.get('debit') if res.get('debit') else 0
            jumlah_bm = credit-debit
            if jumlah_bm < 0:

                # total_jumlah_kanan += jumlah_bm

                worksheet.write('A%s' % row, date , wbf['content_date'])                    
                worksheet.write('B%s' % row, no_sistem , wbf['content'])
                worksheet.write('C%s' % row, remark , wbf['content'])
                worksheet.write('D%s' % row, jumlah_bm , wbf['content_float'])
                worksheet.write('H%s' % row, '' , wbf['content_float'])

                row+=1

                worksheet.write('D%s' % (row+1), '' , wbf['header_right2'])
                worksheet.write('H%s' % (row+1), '' , wbf['header_right2'])
                   
        row+=1
        worksheet.write('D%s' % (row+1), '' , wbf['header_right2'])
        worksheet.write('H%s' % (row+1), '' , wbf['header_right2'])
        for res in ress1:
            date = datetime.strptime(res.get('date'), "%Y-%m-%d").date() if res.get('date') != None else ''
            ref = str(res.get('ref').encode('ascii','ignore').decode('ascii')) if res.get('ref') != None else ''
            name = str(res.get('name').encode('ascii','ignore').decode('ascii')) if res.get('name') != None else ''
            debit = res.get('debit') if res.get('debit') else 0
            credit = res.get('credit') if res.get('credit') else 0
            jumlah_aml = credit-debit
            if jumlah_aml < 0:     
                total_jumlah_kiri += jumlah_aml

                worksheet.write('A%s' % row, date , wbf['content_date_new'])                    
                worksheet.write('B%s' % row, ref , wbf['content_new'])
                worksheet.write('C%s' % row, name , wbf['content_new'])
                worksheet.write('D%s' % row, jumlah_aml , wbf['content_float_new'])
                worksheet.write('H%s' % row, '' , wbf['content_float'])

                row+=1

                worksheet.write('D%s' % (row+1), '' , wbf['header_right2'])
                worksheet.write('H%s' % (row+1), '' , wbf['header_right2'])

        worksheet.write('C%s' % (row+1), ' ' , wbf['header_saldo'])
        worksheet.write('D%s' % (row+1), '' , wbf['header_right2'])
        worksheet.write('H%s' % (row+1), '' , wbf['header_right2'])

        worksheet.write('C%s' % (row+1), 'Pembulat ' , wbf['header_saldo'])
        worksheet.write('D%s' % (row+1), '' , wbf['header_right2'])
        worksheet.write('H%s' % (row+1), '' , wbf['header_right2'])

        
        row+=1
        worksheet.write('D%s' % (row+1), '' , wbf['header_right2'])
        worksheet.write('H%s' % (row+1), '' , wbf['header_right2'])

        row+=1
        worksheet.write('B%s' % (row+1), 'Saldo Setelah Rekonsiliasi ' , wbf['header_saldo'])
        # worksheet.write('D%s' % (row+1), '0 ' , wbf['header_saldo_right'])
        worksheet.write('F%s' % (row+1), 'Saldo Setelah Rekonsiliasi ' , wbf['header_saldo'])
        # worksheet.write('H%s' % (row+1), '0 ' , wbf['header_saldo_right'])
        
        row+=1
        worksheet.write('A%s' % (row+1), '' , wbf['footer1'])
        worksheet.write('B%s' % (row+1), '' , wbf['footer1'])
        worksheet.write('C%s' % (row+1), 'Selisih terhadap Rekening Koran / Listing ' , wbf['footer1'])
        worksheet.merge_range('E%s:H%s' % (row+1,row+1), '', wbf['footer1_right'])

        formula_total_ssr_kiri =  '{=subtotal(9,D%s:D%s)}' % (row1, row-1)
        formula_total_ssr_kanan =  '{=subtotal(9,H%s:H%s)}' % (row1, row-1)
        formula_selisih =  '=D%s-H%s' % (row, row)

        worksheet.write('D%s' % (row+1), formula_selisih , wbf['footer1_right'])
        
        worksheet.write_formula(row-1,3,formula_total_ssr_kiri, wbf['header_saldo_right'], total_jumlah_kiri)
        worksheet.write_formula(row-1,7,formula_total_ssr_kanan, wbf['header_saldo_right'], total_jumlah_kanan)


        row+=2
        worksheet.merge_range('A%s:H%s' % (row+1,row+1), '', wbf['header2'])
        
        row+=1
        worksheet.write('C%s' % (row+1), 'Dipersiapkan Oleh,' , wbf['content'])
        worksheet.write('D%s' % (row+1), 'Di Periksa Oleh,' , wbf['content'])
        worksheet.write('F%s' % (row+1), 'Di Setujui Oleh,' , wbf['content'])
        worksheet.write('H%s' % (row+1), '' , wbf['header_saldo_right'])

        row+=1
        worksheet.write('H%s' % (row+1), '' , wbf['header_saldo_right'])

        row+=1
        worksheet.write('C%s' % (row+1), 'Nama:' , wbf['content'])
        worksheet.write('D%s' % (row+1), 'Nama:' , wbf['content'])
        worksheet.write('F%s' % (row+1), 'Nama:' , wbf['content'])
        worksheet.write('H%s' % (row+1), '' , wbf['header_saldo_right'])

        row+=1
        worksheet.write('C%s' % (row+1), 'Tanggal:' , wbf['content'])
        worksheet.write('D%s' % (row+1), 'Tanggal:' , wbf['content'])
        worksheet.write('F%s' % (row+1), 'Tanggal:' , wbf['content'])
        worksheet.write('H%s' % (row+1), '' , wbf['header_saldo_right'])

        row+=1
        worksheet.merge_range('A%s:H%s' % (row+1,row+1), '', wbf['footer1_right'])
        
        row+=1
        worksheet.write('A%s'%(row+2), '%s %s' % (date2,user) , wbf['content']) 

        worksheet.freeze_panes(12, 2)

        
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write({'state_x':'get', 'data_x':out, 'name': filename})
        fp.close()

        res = self.env.ref('teds_bank_reconcile.view_teds_bank_reconcile_report_wizard', False)

        form_id = res and res.id or False

        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.bank.reconcile.report',
            'res_id': self.ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }