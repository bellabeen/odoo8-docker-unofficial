import cStringIO
import xlsxwriter
from cStringIO import StringIO
import base64
import os
from openerp import models, fields, api
from datetime import datetime, timedelta,date
from dateutil.relativedelta import relativedelta
import calendar

class ReportPaymentKlikWizard(models.TransientModel):
    _name = "teds.report.payment.klik.wizard"

    wbf = {}
    
    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()
    

    name = fields.Char('Filename', readonly=True)
    state_x = fields.Selection([('choose','choose'),('get','get')], default='choose')
    data_x = fields.Binary('File', readonly=True)
    options = fields.Selection([
      ('All','All'),
      ('Supplier Payment','Supplier Payment'),
      ('Advance Payment','Advance Payment'),
      ('Settlement Advance Payment','Settlement Advance Payment'),
      ('Bank Transfer','Bank Transfer')])
    branch_ids = fields.Many2many('wtc.branch', 'teds_report_payment_klik_branch_rel', 'payment_id','branch_id', string='Branch')
    start_date = fields.Date('Start Date',default=_get_default_date)
    end_date = fields.Date('End Date',default=_get_default_date)
    division  = fields.Selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum')])

    @api.multi
    def add_workbook_format(self, workbook):      
        self.wbf['header'] = workbook.add_format({'bold': 1,'align': 'center','bg_color': '#FFFFDB','font_color': '#000000'})
        self.wbf['header'].set_border()

        self.wbf['header_no'] = workbook.add_format({'bold': 1,'align': 'center','bg_color': '#FFFFDB','font_color': '#000000'})
        self.wbf['header_no'].set_border()
        self.wbf['header_no'].set_align('vcenter')
                
        self.wbf['footer'] = workbook.add_format({'align':'left'})
                    
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
        
        self.wbf['total'] = workbook.add_format({'bold':1,'bg_color': '#FFFFDB','align':'center'})
        self.wbf['total'].set_left()
        self.wbf['total'].set_right()
        self.wbf['total'].set_top()
        self.wbf['total'].set_bottom()
        
        return workbook

    @api.multi
    def excel_report(self):
        if self.options == 'Supplier Payment':
            self.laporan_supplier_payment()
        elif self.options == 'Advance Payment':
            self.laporan_advance_payment()
        elif self.options == 'Settlement Advance Payment':
            self.laporan_settlement_advance_payment()
        elif self.options == 'Bank Transfer':
            self.laporan_bank_transfer()
        else:
            self.laporan_all()
        form_id = self.env.ref('teds_report_payment_klik.view_teds_laporan_payment_klik_wizard').id
    
        return {
            'name': ('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.report.payment.klik.wizard',
            'res_id': self.ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }
    def laporan_all(self):
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(workbook)
        wbf=self.wbf
        date = datetime.now()
        date = date.strftime("%d-%m-%Y %H:%M:%S")

        filename = 'Laporan Payment Klik %s %s.xlsx'%(self.options,str(date))

    # Supplier Payment
        worksheet_supplier_payment = workbook.add_worksheet('Supplier Payment')
        worksheet_supplier_payment.set_column('A1:A1', 5)
        worksheet_supplier_payment.set_column('B1:B1', 20)
        worksheet_supplier_payment.set_column('C1:C1', 23)
        worksheet_supplier_payment.set_column('D1:D1', 23)
        worksheet_supplier_payment.set_column('E1:E1', 35)
        worksheet_supplier_payment.set_column('F1:F1', 20)
        worksheet_supplier_payment.set_column('G1:G1', 32)
        worksheet_supplier_payment.set_column('H1:H1', 30)
        worksheet_supplier_payment.set_column('I1:I1', 30)
        worksheet_supplier_payment.set_column('J1:J1', 35)

        worksheet_supplier_payment.merge_range('A1:C1', 'Laporan Supplier Payment', wbf['company'])   
        worksheet_supplier_payment.merge_range('A2:C2', 'Periode %s - %s' %(self.start_date,self.end_date) , wbf['company'])  

        worksheet_supplier_payment.write('A4', 'No' , wbf['header'])
        worksheet_supplier_payment.write('B4', 'Cabang' , wbf['header'])
        worksheet_supplier_payment.write('C4', 'Cabang Untuk' , wbf['header'])
        worksheet_supplier_payment.write('D4', 'Number' , wbf['header'])
        worksheet_supplier_payment.write('E4', 'Payment Method' , wbf['header'])
        worksheet_supplier_payment.write('F4', 'Paid Amount' , wbf['header'])
        worksheet_supplier_payment.write('G4', 'Nama Partner' , wbf['header'])
        worksheet_supplier_payment.write('H4', 'Approved/Payment klik by' , wbf['header'])
        worksheet_supplier_payment.write('I4', 'No.Rekening Tujuan' , wbf['header'])
        worksheet_supplier_payment.write('J4', 'Description' , wbf['header'])
          
        row_supplier_payment=5
        no_supplier_payment = 1     

        query_where_sp = " WHERE av.is_payment = True AND av.type = 'payment'"
        if self.start_date:
            query_where_sp += " AND (av.payment_klik_date + INTERVAL '7 hours')::date >= '%s'" %self.start_date
        if self.end_date:
            query_where_sp += " AND (av.payment_klik_date + INTERVAL '7 hours')::date <= '%s'" %self.end_date
        if self.branch_ids:
            branch = [b.id for b in self.branch_ids]
            query_where_sp += " AND av.branch_id in %s" % str(tuple(branch)).replace(',)', ')')
        if self.division:
            query_where_sp += " AND av.division = '%s'" %self.division

        query_sp = """
            SELECT
            b.code as cabang
            , b2.name as cabang_untuk
            , av.number
            , aj.name as payment_methode
            , av.amount as paid_amount
            , p.name as partner
            , av.no_rekening_tujuan
            , pk.name as payment_klik_name
            , av.name as description
            FROM wtc_account_voucher av
            INNER JOIN wtc_branch b ON b.id = av.branch_id
            INNER JOIN wtc_branch b2 ON b2.id = av.inter_branch_id
            INNER JOIN account_journal aj ON aj.id = av.journal_id
            INNER JOIN res_partner p ON p.id = av.partner_id
            LEFT JOIN res_users u ON u.id = av.payment_klik_uid
            LEFT JOIN res_partner pk ON pk.id = u.partner_id
            %s
        """ %query_where_sp
        self.env.cr.execute(query_sp)
        ress = self.env.cr.dictfetchall() 
        for res in ress:
            worksheet_supplier_payment.write('A%s' % row_supplier_payment, no_supplier_payment , wbf['content_number'])
            worksheet_supplier_payment.write('B%s' % row_supplier_payment, res.get('cabang') , wbf['content'])
            worksheet_supplier_payment.write('C%s' % row_supplier_payment, res.get('cabang_untuk') , wbf['content'])
            worksheet_supplier_payment.write('D%s' % row_supplier_payment, res.get('number') , wbf['content'])
            worksheet_supplier_payment.write('E%s' % row_supplier_payment, res.get('payment_methode') , wbf['content'])
            worksheet_supplier_payment.write('F%s' % row_supplier_payment, res.get('paid_amount') , wbf['content_float'])
            worksheet_supplier_payment.write('G%s' % row_supplier_payment, res.get('partner') , wbf['content'])
            worksheet_supplier_payment.write('H%s' % row_supplier_payment, res.get('payment_klik_name') , wbf['content'])
            worksheet_supplier_payment.write('I%s' % row_supplier_payment, res.get('no_rekening_tujuan') , wbf['content'])
            worksheet_supplier_payment.write('J%s' % row_supplier_payment, res.get('description') , wbf['content'])

            no_supplier_payment+=1
            row_supplier_payment+=1

        worksheet_supplier_payment.autofilter('A4:J%s' % (row_supplier_payment))
        worksheet_supplier_payment.merge_range('A%s:J%s' % (row_supplier_payment,row_supplier_payment), '', wbf['total']) 

    # Bank Transfer
        worksheet_bank_transfer = workbook.add_worksheet('Bank Transfer')
        worksheet_bank_transfer.set_column('A1:A1', 5)
        worksheet_bank_transfer.set_column('B1:B1', 20)
        worksheet_bank_transfer.set_column('C1:C1', 25)
        worksheet_bank_transfer.set_column('D1:D1', 28)
        worksheet_bank_transfer.set_column('E1:E1', 20)
        worksheet_bank_transfer.set_column('F1:F1', 25)
        worksheet_bank_transfer.set_column('G1:G1', 33)
        worksheet_bank_transfer.set_column('H1:H1', 35)
        worksheet_bank_transfer.set_column('I1:I1', 30)
        worksheet_bank_transfer.set_column('J1:J1', 35)
        
        worksheet_bank_transfer.merge_range('A1:C1', 'Laporan Bank Transfer', wbf['company'])   
        worksheet_bank_transfer.merge_range('A2:C2', 'Periode %s - %s' %(self.start_date,self.end_date) , wbf['company'])  

        worksheet_bank_transfer.write('A4', 'No' , wbf['header'])
        worksheet_bank_transfer.write('B4', 'Branch Code' , wbf['header'])
        worksheet_bank_transfer.write('C4', 'Transaction Name' , wbf['header'])
        worksheet_bank_transfer.write('D4', 'Payment Method' , wbf['header'])
        worksheet_bank_transfer.write('E4', 'Amount' , wbf['header'])
        worksheet_bank_transfer.write('F4', 'Branch Destination Name' , wbf['header'])
        worksheet_bank_transfer.write('G4', 'Account Name' , wbf['header'])
        worksheet_bank_transfer.write('H4', 'Detail Description' , wbf['header'])
        worksheet_bank_transfer.write('I4', 'Approved/Payment klik by' , wbf['header'])
        worksheet_bank_transfer.write('J4', 'Description' , wbf['header'])
          
        row_bank_transfer=5
        no_bank_transfer = 1     

        query_where_bt = " WHERE bt.is_payment = True"
        if self.start_date:
            query_where_bt += " AND (bt.payment_klik_date + INTERVAL '7 hours')::date >= '%s'" %self.start_date
        if self.end_date:
            query_where_bt += " AND (bt.payment_klik_date + INTERVAL '7 hours')::date <= '%s'" %self.end_date
        if self.branch_ids:
            branch = [b.id for b in self.branch_ids]
            query_where_bt += " AND bt.branch_id in %s" % str(tuple(branch)).replace(',)', ')')
        if self.division:
            query_where_bt += " AND bt.division = '%s'" %self.division

        query_bt = """
            SELECT
            b.code as branch_code
            , bt.name as transaction_name
            , aj.name as sender_journal_name
            , bt.amount as amount
            , b2.name as branch_dest_name
            , aj2.name as account_name
            , btl.description as dest_description
            , pk.name as payment_klik_name
            , bt.description
            FROM wtc_bank_transfer bt
            INNER JOIN (
                SELECT
                bank_transfer_id
                , payment_to_id
                , branch_destination_id
                , description 
                FROM wtc_bank_transfer_line 
                GROUP BY bank_transfer_id,branch_destination_id,payment_to_id,description 
            ) btl ON bt.id = btl.bank_transfer_id
            INNER JOIN wtc_branch b ON b.id = bt.branch_id 
            LEFT JOIN account_journal aj ON aj.id = bt.payment_from_id
            LEFT JOIN wtc_branch b2 ON b2.code = btl.branch_destination_id
            LEFT JOIN account_journal aj2 ON aj2.id = btl.payment_to_id
            LEFT JOIN res_users u ON u.id = bt.payment_klik_uid
            LEFT JOIN res_partner pk ON pk.id = u.partner_id
            %s
        """ %query_where_bt
        self.env.cr.execute(query_bt)
        ress = self.env.cr.dictfetchall() 
        for res in ress:
            worksheet_bank_transfer.write('A%s' % row_bank_transfer, no_bank_transfer , wbf['content_number'])
            worksheet_bank_transfer.write('B%s' % row_bank_transfer, res.get('branch_code') , wbf['content'])
            worksheet_bank_transfer.write('C%s' % row_bank_transfer, res.get('transaction_name') , wbf['content'])
            worksheet_bank_transfer.write('D%s' % row_bank_transfer, res.get('sender_journal_name') , wbf['content'])
            worksheet_bank_transfer.write('E%s' % row_bank_transfer, res.get('amount') , wbf['content_float'])
            worksheet_bank_transfer.write('F%s' % row_bank_transfer, res.get('branch_dest_name') , wbf['content'])
            worksheet_bank_transfer.write('G%s' % row_bank_transfer, res.get('account_name') , wbf['content'])
            worksheet_bank_transfer.write('H%s' % row_bank_transfer, res.get('dest_description') , wbf['content'])
            worksheet_bank_transfer.write('I%s' % row_bank_transfer, res.get('payment_klik_name') , wbf['content'])
            worksheet_bank_transfer.write('J%s' % row_bank_transfer, res.get('description') , wbf['content'])

            no_bank_transfer+=1
            row_bank_transfer+=1

        worksheet_bank_transfer.autofilter('A4:J%s' % (row_bank_transfer))
        worksheet_bank_transfer.merge_range('A%s:J%s' % (row_bank_transfer,row_bank_transfer), '', wbf['total'])

    # Advance Payment
        worksheet_advance_payment = workbook.add_worksheet('Advance Payment')
        worksheet_advance_payment.set_column('A1:A1', 5)
        worksheet_advance_payment.set_column('B1:B1', 20)
        worksheet_advance_payment.set_column('C1:C1', 25)
        worksheet_advance_payment.set_column('D1:D1', 28)
        worksheet_advance_payment.set_column('E1:E1', 20)
        worksheet_advance_payment.set_column('F1:F1', 25)
        worksheet_advance_payment.set_column('G1:G1', 30)
        worksheet_advance_payment.set_column('H1:H1', 30)
        worksheet_advance_payment.set_column('I1:I1', 35)
        
        worksheet_advance_payment.merge_range('A1:C1', 'Laporan Advance Payment', wbf['company'])   
        worksheet_advance_payment.merge_range('A2:C2', 'Periode %s - %s' %(self.start_date,self.end_date) , wbf['company'])  

        worksheet_advance_payment.write('A4', 'No' , wbf['header'])
        worksheet_advance_payment.write('B4', 'Cabang' , wbf['header'])
        worksheet_advance_payment.write('C4', 'No Bukti' , wbf['header'])
        worksheet_advance_payment.write('D4', 'Keterangan' , wbf['header'])
        worksheet_advance_payment.write('E4', 'Diberikan Ke' , wbf['header'])
        worksheet_advance_payment.write('F4', 'Total' , wbf['header'])
        worksheet_advance_payment.write('G4', 'Approved/Payment klik by' , wbf['header'])
        worksheet_advance_payment.write('H4', 'No. Rekening Tujuan' , wbf['header'])
        worksheet_advance_payment.write('I4', 'Description' , wbf['header'])
          
        row_advance_payment=5
        no_advance_payment = 1     

        query_ap_where = " WHERE ap.is_payment = True"
        if self.start_date:
            query_ap_where += " AND (ap.payment_klik_date + INTERVAL '7 hours')::date >= '%s'" %self.start_date
        if self.end_date:
            query_ap_where += " AND (ap.payment_klik_date + INTERVAL '7 hours')::date <= '%s'" %self.end_date
        if self.branch_ids:
            branch = [b.id for b in self.branch_ids]
            query_ap_where += " AND ap.branch_id in %s" % str(tuple(branch)).replace(',)', ')')
        if self.division:
            query_ap_where += " AND ap.division = '%s'" %self.division

        query_ap = """
            SELECT
            b.code as cabang
            , ap.name as no_bukti
            , ap.description as keterangan
            , p.name as diberikan_kepada
            , ap.amount as total
            , pk.name as payment_klik_name
            , ap.no_rekening_tujuan
            , ap.description
            FROM wtc_advance_payment ap
            INNER JOIN wtc_branch b ON b.id = ap.branch_id 
            LEFT JOIN res_users u ON u.id = ap.user_id
            LEFT JOIN res_partner p ON p.id = u.partner_id
            LEFT JOIN res_users u2 ON u2.id = ap.payment_klik_uid
            LEFT JOIN res_partner pk ON pk.id = u2.partner_id
            %s
        """ %query_ap_where
        self.env.cr.execute(query_ap)
        ress = self.env.cr.dictfetchall() 
        for res in ress:
            worksheet_advance_payment.write('A%s' % row_advance_payment, no_advance_payment , wbf['content_number'])
            worksheet_advance_payment.write('B%s' % row_advance_payment, res.get('cabang') , wbf['content'])
            worksheet_advance_payment.write('C%s' % row_advance_payment, res.get('no_bukti') , wbf['content'])
            worksheet_advance_payment.write('D%s' % row_advance_payment, res.get('keterangan') , wbf['content'])
            worksheet_advance_payment.write('E%s' % row_advance_payment, res.get('diberikan_kepada') , wbf['content'])
            worksheet_advance_payment.write('F%s' % row_advance_payment, res.get('total') , wbf['content_float'])
            worksheet_advance_payment.write('G%s' % row_advance_payment, res.get('payment_klik_name') , wbf['content'])
            worksheet_advance_payment.write('H%s' % row_advance_payment, res.get('no_rekening_tujuan') , wbf['content'])
            worksheet_advance_payment.write('I%s' % row_advance_payment, res.get('description') , wbf['content'])
            
            no_advance_payment+=1
            row_advance_payment+=1

        worksheet_advance_payment.autofilter('A4:I%s' % (row_advance_payment))
        worksheet_advance_payment.merge_range('A%s:I%s' % (row_advance_payment,row_advance_payment), '', wbf['total'])
    
    # Settlement Advance Payment
        worksheet_settlement_advance_payment = workbook.add_worksheet('Settlement Advance Payment')
        worksheet_settlement_advance_payment.set_column('A1:A1', 5)
        worksheet_settlement_advance_payment.set_column('B1:B1', 20)
        worksheet_settlement_advance_payment.set_column('C1:C1', 25)
        worksheet_settlement_advance_payment.set_column('D1:D1', 28)
        worksheet_settlement_advance_payment.set_column('E1:E1', 20)
        worksheet_settlement_advance_payment.set_column('F1:F1', 25)
        worksheet_settlement_advance_payment.set_column('G1:G1', 30)
        worksheet_settlement_advance_payment.set_column('H1:H1', 30)
        worksheet_settlement_advance_payment.set_column('I1:I1', 35)
        
        worksheet_settlement_advance_payment.merge_range('A1:C1', 'Laporan Settlement Advance Payment', wbf['company'])   
        worksheet_settlement_advance_payment.merge_range('A2:C2', 'Periode %s - %s' %(self.start_date,self.end_date) , wbf['company'])  

        worksheet_settlement_advance_payment.write('A4', 'No' , wbf['header'])
        worksheet_settlement_advance_payment.write('B4', 'Cabang' , wbf['header'])
        worksheet_settlement_advance_payment.write('C4', 'No Bukti' , wbf['header'])
        worksheet_settlement_advance_payment.write('D4', 'Keterangan' , wbf['header'])
        worksheet_settlement_advance_payment.write('E4', 'Diberikan Ke' , wbf['header'])
        worksheet_settlement_advance_payment.write('F4', 'Total' , wbf['header'])
        worksheet_settlement_advance_payment.write('G4', 'Total Kembalian/Tambahan' , wbf['header'])
        worksheet_settlement_advance_payment.write('H4', 'Approved/Payment klik by' , wbf['header'])
        worksheet_settlement_advance_payment.write('I4', 'Description' , wbf['header'])
          
        row_settlement_advance_payment=5
        no_settlement_advance_payment = 1     

        query_stl_where = " WHERE st.is_payment = True"
        if self.start_date:
            query_stl_where += " AND (st.payment_klik_date + INTERVAL '7 hours')::date >= '%s'" %self.start_date
        if self.end_date:
            query_stl_where += " AND (st.payment_klik_date + INTERVAL '7 hours')::date <= '%s'" %self.end_date
        if self.branch_ids:
            branch = [b.id for b in self.branch_ids]
            query_stl_where += " AND st.branch_id in %s" % str(tuple(branch)).replace(',)', ')')
        if self.division:
            query_stl_where += " AND st.division = '%s'" %self.division

        query_stl = """
            SELECT
            b.code as cabang
            , st.name as no_bukti
            , st.description as keterangan
            , p.name as diberikan_kepada
            , st.amount_total as total
            , st.amount_gap
            , pk.name as payment_klik_name
            , st.description
            FROM wtc_settlement st
            INNER JOIN wtc_branch b ON b.id = st.branch_id 
            LEFT JOIN res_users u ON u.id = st.user_id
            LEFT JOIN res_partner p ON p.id = u.partner_id
            LEFT JOIN res_users u2 ON u2.id = st.payment_klik_uid
            LEFT JOIN res_partner pk ON pk.id = u2.partner_id
            %s
        """ %query_stl_where
        self.env.cr.execute(query_stl)
        ress = self.env.cr.dictfetchall() 
        for res in ress:
            worksheet_settlement_advance_payment.write('A%s' % row_settlement_advance_payment, no_settlement_advance_payment , wbf['content_number'])
            worksheet_settlement_advance_payment.write('B%s' % row_settlement_advance_payment, res.get('cabang') , wbf['content'])
            worksheet_settlement_advance_payment.write('C%s' % row_settlement_advance_payment, res.get('no_bukti') , wbf['content'])
            worksheet_settlement_advance_payment.write('D%s' % row_settlement_advance_payment, res.get('keterangan') , wbf['content'])
            worksheet_settlement_advance_payment.write('E%s' % row_settlement_advance_payment, res.get('diberikan_kepada') , wbf['content'])
            worksheet_settlement_advance_payment.write('F%s' % row_settlement_advance_payment, res.get('total') , wbf['content_float'])
            worksheet_settlement_advance_payment.write('G%s' % row_settlement_advance_payment, res.get('amount_gap') , wbf['content_float'])
            worksheet_settlement_advance_payment.write('H%s' % row_settlement_advance_payment, res.get('payment_klik_name') , wbf['content'])
            worksheet_settlement_advance_payment.write('I%s' % row_settlement_advance_payment, res.get('description') , wbf['content'])
            
            no_settlement_advance_payment+=1
            row_settlement_advance_payment+=1

        worksheet_settlement_advance_payment.autofilter('A4:I%s' % (row_settlement_advance_payment))
        worksheet_settlement_advance_payment.merge_range('A%s:I%s' % (row_settlement_advance_payment,row_settlement_advance_payment), '', wbf['total']) 
        
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write({'state_x':'get', 'data_x':out, 'name': filename})
        fp.close()
        
    def laporan_supplier_payment(self):
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet(self.options)
        worksheet.set_column('A1:A1', 5)
        worksheet.set_column('B1:B1', 20)
        worksheet.set_column('C1:C1', 23)
        worksheet.set_column('D1:D1', 23)
        worksheet.set_column('E1:E1', 35)
        worksheet.set_column('F1:F1', 20)
        worksheet.set_column('G1:G1', 32)
        worksheet.set_column('H1:H1', 30)
        worksheet.set_column('I1:I1', 30)
        worksheet.set_column('J1:J1', 30)
        
        date = datetime.now()
        date = date.strftime("%d-%m-%Y %H:%M:%S")

        filename = 'Laporan Payment Klik %s %s.xlsx'%(self.options,str(date))
        worksheet.merge_range('A1:C1', 'Laporan %s' %(self.options), wbf['company'])   
        worksheet.merge_range('A2:C2', 'Periode %s - %s' %(self.start_date,self.end_date) , wbf['company'])  

        worksheet.write('A4', 'No' , wbf['header'])
        worksheet.write('B4', 'Cabang' , wbf['header'])
        worksheet.write('C4', 'Cabang Untuk' , wbf['header'])
        worksheet.write('D4', 'Number' , wbf['header'])
        worksheet.write('E4', 'Payment Method' , wbf['header'])
        worksheet.write('F4', 'Paid Amount' , wbf['header'])
        worksheet.write('G4', 'Nama Partner' , wbf['header'])
        worksheet.write('H4', 'Approved/Payment klik by' , wbf['header'])
        worksheet.write('I4', 'No.Rekening Tujuan' , wbf['header'])
        worksheet.write('J4', 'Description' , wbf['header'])
          
        row=5
        no = 1     

        query_where = " WHERE av.is_payment = True AND av.type = 'payment'"
        if self.start_date:
            query_where += " AND (av.payment_klik_date + INTERVAL '7 hours')::date >= '%s'" %self.start_date
        if self.end_date:
            query_where += " AND (av.payment_klik_date + INTERVAL '7 hours')::date <= '%s'" %self.end_date
        if self.branch_ids:
            branch = [b.id for b in self.branch_ids]
            query_where += " AND av.branch_id in %s" % str(tuple(branch)).replace(',)', ')')
        if self.division:
            query_where += " AND av.division = '%s'" %self.division

        query = """
            SELECT
            b.code as cabang
            , b2.name as cabang_untuk
            , av.number
            , aj.name as payment_methode
            , av.amount as paid_amount
            , p.name as partner
            , av.no_rekening_tujuan
            , pk.name as payment_klik_name
            , av.name as description
            FROM wtc_account_voucher av
            INNER JOIN wtc_branch b ON b.id = av.branch_id
            INNER JOIN wtc_branch b2 ON b2.id = av.inter_branch_id
            INNER JOIN account_journal aj ON aj.id = av.journal_id
            INNER JOIN res_partner p ON p.id = av.partner_id
            LEFT JOIN res_users u ON u.id = av.payment_klik_uid
            LEFT JOIN res_partner pk ON pk.id = u.partner_id
            %s
        """ %query_where
        self.env.cr.execute(query)
        ress = self.env.cr.dictfetchall() 
        for res in ress:
            worksheet.write('A%s' % row, no , wbf['content_number'])
            worksheet.write('B%s' % row, res.get('cabang') , wbf['content'])
            worksheet.write('C%s' % row, res.get('cabang_untuk') , wbf['content'])
            worksheet.write('D%s' % row, res.get('number') , wbf['content'])
            worksheet.write('E%s' % row, res.get('payment_methode') , wbf['content'])
            worksheet.write('F%s' % row, res.get('paid_amount') , wbf['content_float'])
            worksheet.write('G%s' % row, res.get('partner') , wbf['content'])
            worksheet.write('H%s' % row, res.get('payment_klik_name') , wbf['content'])
            worksheet.write('I%s' % row, res.get('no_rekening_tujuan') , wbf['content'])
            worksheet.write('J%s' % row, res.get('description') , wbf['content'])

            no+=1
            row+=1

        worksheet.autofilter('A4:J%s' % (row))
        worksheet.merge_range('A%s:J%s' % (row,row), '', wbf['total']) 
        
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write({'state_x':'get', 'data_x':out, 'name': filename})
        fp.close()

    def laporan_bank_transfer(self):
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet(self.options)
        worksheet.set_column('A1:A1', 5)
        worksheet.set_column('B1:B1', 20)
        worksheet.set_column('C1:C1', 25)
        worksheet.set_column('D1:D1', 28)
        worksheet.set_column('E1:E1', 20)
        worksheet.set_column('F1:F1', 25)
        worksheet.set_column('G1:G1', 33)
        worksheet.set_column('H1:H1', 35)
        worksheet.set_column('I1:I1', 30)
        worksheet.set_column('J1:J1', 35)
        
        date = datetime.now()
        date = date.strftime("%d-%m-%Y %H:%M:%S")

        filename = 'Laporan Payment Klik %s %s.xlsx'%(self.options,str(date))
        worksheet.merge_range('A1:C1', 'Laporan %s' %(self.options), wbf['company'])   
        worksheet.merge_range('A2:C2', 'Periode %s - %s' %(self.start_date,self.end_date) , wbf['company'])  

        worksheet.write('A4', 'No' , wbf['header'])
        worksheet.write('B4', 'Branch Code' , wbf['header'])
        worksheet.write('C4', 'Transaction Name' , wbf['header'])
        worksheet.write('D4', 'Payment Method' , wbf['header'])
        worksheet.write('E4', 'Amount' , wbf['header'])
        worksheet.write('F4', 'Branch Destination Name' , wbf['header'])
        worksheet.write('G4', 'Account Name' , wbf['header'])
        worksheet.write('H4', 'Detail Description' , wbf['header'])
        worksheet.write('I4', 'Approved/Payment klik by' , wbf['header'])
        worksheet.write('J4', 'Description' , wbf['header'])
          
        row=5
        no = 1     

        query_where = " WHERE bt.is_payment = True"
        if self.start_date:
            query_where += " AND (bt.payment_klik_date + INTERVAL '7 hours')::date >= '%s'" %self.start_date
        if self.end_date:
            query_where += " AND (bt.payment_klik_date + INTERVAL '7 hours')::date <= '%s'" %self.end_date
        if self.branch_ids:
            branch = [b.id for b in self.branch_ids]
            query_where += " AND bt.branch_id in %s" % str(tuple(branch)).replace(',)', ')')
        if self.division:
            query_where += " AND bt.division = '%s'" %self.division

        query = """
            SELECT
            b.code as branch_code
            , bt.name as transaction_name
            , aj.name as sender_journal_name
            , bt.amount as amount
            , b2.name as branch_dest_name
            , aj2.name as account_name
            , btl.description as dest_description
            , pk.name as payment_klik_name
            , bt.description
            FROM wtc_bank_transfer bt
            INNER JOIN (
                SELECT
                bank_transfer_id
                , payment_to_id
                , branch_destination_id
                , description 
                FROM wtc_bank_transfer_line 
                GROUP BY bank_transfer_id,branch_destination_id,payment_to_id,description 
            ) btl ON bt.id = btl.bank_transfer_id
            INNER JOIN wtc_branch b ON b.id = bt.branch_id 
            LEFT JOIN account_journal aj ON aj.id = bt.payment_from_id
            LEFT JOIN wtc_branch b2 ON b2.code = btl.branch_destination_id
            LEFT JOIN account_journal aj2 ON aj2.id = btl.payment_to_id
            LEFT JOIN res_users u ON u.id = bt.payment_klik_uid
            LEFT JOIN res_partner pk ON pk.id = u.partner_id
            %s
        """ %query_where
        self.env.cr.execute(query)
        ress = self.env.cr.dictfetchall() 
        for res in ress:
            worksheet.write('A%s' % row, no , wbf['content_number'])
            worksheet.write('B%s' % row, res.get('branch_code') , wbf['content'])
            worksheet.write('C%s' % row, res.get('transaction_name') , wbf['content'])
            worksheet.write('D%s' % row, res.get('sender_journal_name') , wbf['content'])
            worksheet.write('E%s' % row, res.get('amount') , wbf['content_float'])
            worksheet.write('F%s' % row, res.get('branch_dest_name') , wbf['content'])
            worksheet.write('G%s' % row, res.get('account_name') , wbf['content'])
            worksheet.write('H%s' % row, res.get('dest_description') , wbf['content'])
            worksheet.write('I%s' % row, res.get('payment_klik_name') , wbf['content'])
            worksheet.write('J%s' % row, res.get('description') , wbf['content'])

            no+=1
            row+=1

        worksheet.autofilter('A4:J%s' % (row))
        worksheet.merge_range('A%s:J%s' % (row,row), '', wbf['total']) 
        
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write({'state_x':'get', 'data_x':out, 'name': filename})
        fp.close()
    
    def laporan_advance_payment(self):
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet(self.options)
        worksheet.set_column('A1:A1', 5)
        worksheet.set_column('B1:B1', 20)
        worksheet.set_column('C1:C1', 25)
        worksheet.set_column('D1:D1', 28)
        worksheet.set_column('E1:E1', 20)
        worksheet.set_column('F1:F1', 25)
        worksheet.set_column('G1:G1', 30)
        worksheet.set_column('H1:H1', 30)
        worksheet.set_column('I1:I1', 35)
        
        date = datetime.now()
        date = date.strftime("%d-%m-%Y %H:%M:%S")

        filename = 'Laporan Payment Klik %s %s.xlsx'%(self.options,str(date))
        worksheet.merge_range('A1:C1', 'Laporan %s' %(self.options), wbf['company'])   
        worksheet.merge_range('A2:C2', 'Periode %s - %s' %(self.start_date,self.end_date) , wbf['company'])  

        worksheet.write('A4', 'No' , wbf['header'])
        worksheet.write('B4', 'Cabang' , wbf['header'])
        worksheet.write('C4', 'No Bukti' , wbf['header'])
        worksheet.write('D4', 'Keterangan' , wbf['header'])
        worksheet.write('E4', 'Diberikan Ke' , wbf['header'])
        worksheet.write('F4', 'Total' , wbf['header'])
        worksheet.write('G4', 'Approved/Payment klik by' , wbf['header'])
        worksheet.write('H4', 'No.Rekening Tujuan' , wbf['header'])
        worksheet.write('I4', 'Description' , wbf['header'])
          
        row=5
        no = 1     

        query_where = " WHERE ap.is_payment = True"
        if self.start_date:
            query_where += " AND (ap.payment_klik_date + INTERVAL '7 hours')::date >= '%s'" %self.start_date
        if self.end_date:
            query_where += " AND (ap.payment_klik_date + INTERVAL '7 hours')::date <= '%s'" %self.end_date
        if self.branch_ids:
            branch = [b.id for b in self.branch_ids]
            query_where += " AND ap.branch_id in %s" % str(tuple(branch)).replace(',)', ')')
        if self.division:
            query_where += " AND ap.division = '%s'" %self.division

        query = """
            SELECT
            b.code as cabang
            , ap.name as no_bukti
            , ap.description as keterangan
            , p.name as diberikan_kepada
            , ap.amount as total
            , pk.name as payment_klik_name
            , ap.no_rekening_tujuan
            , ap.description
            FROM wtc_advance_payment ap
            INNER JOIN wtc_branch b ON b.id = ap.branch_id 
            LEFT JOIN res_users u ON u.id = ap.user_id
            LEFT JOIN res_partner p ON p.id = u.partner_id
            LEFT JOIN res_users u2 ON u2.id = ap.payment_klik_uid
            LEFT JOIN res_partner pk ON pk.id = u2.partner_id
            %s
        """ %query_where
        self.env.cr.execute(query)
        ress = self.env.cr.dictfetchall() 
        for res in ress:
            worksheet.write('A%s' % row, no , wbf['content_number'])
            worksheet.write('B%s' % row, res.get('cabang') , wbf['content'])
            worksheet.write('C%s' % row, res.get('no_bukti') , wbf['content'])
            worksheet.write('D%s' % row, res.get('keterangan') , wbf['content'])
            worksheet.write('E%s' % row, res.get('diberikan_kepada') , wbf['content'])
            worksheet.write('F%s' % row, res.get('total') , wbf['content_float'])
            worksheet.write('G%s' % row, res.get('payment_klik_name') , wbf['content'])
            worksheet.write('H%s' % row, res.get('no_rekening_tujuan') , wbf['content'])
            worksheet.write('I%s' % row, res.get('description') , wbf['content'])
            
            no+=1
            row+=1

        worksheet.autofilter('A4:I%s' % (row))
        worksheet.merge_range('A%s:I%s' % (row,row), '', wbf['total']) 
        
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write({'state_x':'get', 'data_x':out, 'name': filename})
        fp.close()
    
    def laporan_settlement_advance_payment(self):
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet(self.options)
        worksheet.set_column('A1:A1', 5)
        worksheet.set_column('B1:B1', 20)
        worksheet.set_column('C1:C1', 25)
        worksheet.set_column('D1:D1', 28)
        worksheet.set_column('E1:E1', 20)
        worksheet.set_column('F1:F1', 25)
        worksheet.set_column('G1:G1', 30)
        worksheet.set_column('H1:H1', 30)
        worksheet.set_column('I1:I1', 35)
        
        date = datetime.now()
        date = date.strftime("%d-%m-%Y %H:%M:%S")

        filename = 'Laporan Payment Klik %s %s.xlsx'%(self.options,str(date))
        worksheet.merge_range('A1:C1', 'Laporan %s' %(self.options), wbf['company'])   
        worksheet.merge_range('A2:C2', 'Periode %s - %s' %(self.start_date,self.end_date) , wbf['company'])  

        worksheet.write('A4', 'No' , wbf['header'])
        worksheet.write('B4', 'Cabang' , wbf['header'])
        worksheet.write('C4', 'No Bukti' , wbf['header'])
        worksheet.write('D4', 'Keterangan' , wbf['header'])
        worksheet.write('E4', 'Diberikan Ke' , wbf['header'])
        worksheet.write('F4', 'Total' , wbf['header'])
        worksheet.write('G4', 'Total Kembalian/Tambahan' , wbf['header'])
        worksheet.write('H4', 'Approved/Payment klik by' , wbf['header'])
        worksheet.write('I4', 'Description' , wbf['header'])
          
        row=5
        no = 1     

        query_where = " WHERE st.is_payment = True"
        if self.start_date:
            query_where += " AND (st.payment_klik_date + INTERVAL '7 hours')::date >= '%s'" %self.start_date
        if self.end_date:
            query_where += " AND (st.payment_klik_date + INTERVAL '7 hours')::date <= '%s'" %self.end_date
        if self.branch_ids:
            branch = [b.id for b in self.branch_ids]
            query_where += " AND st.branch_id in %s" % str(tuple(branch)).replace(',)', ')')
        if self.division:
            query_where += " AND st.division = '%s'" %self.division

        query = """
            SELECT
            b.code as cabang
            , st.name as no_bukti
            , st.description as keterangan
            , p.name as diberikan_kepada
            , st.amount_total as total
            , st.amount_gap
            , pk.name as payment_klik_name
            , st.description
            FROM wtc_settlement st
            INNER JOIN wtc_branch b ON b.id = st.branch_id 
            LEFT JOIN res_users u ON u.id = st.user_id
            LEFT JOIN res_partner p ON p.id = u.partner_id
            LEFT JOIN res_users u2 ON u2.id = st.payment_klik_uid
            LEFT JOIN res_partner pk ON pk.id = u2.partner_id
            %s
        """ %query_where
        self.env.cr.execute(query)
        ress = self.env.cr.dictfetchall() 
        for res in ress:
            worksheet.write('A%s' % row, no , wbf['content_number'])
            worksheet.write('B%s' % row, res.get('cabang') , wbf['content'])
            worksheet.write('C%s' % row, res.get('no_bukti') , wbf['content'])
            worksheet.write('D%s' % row, res.get('keterangan') , wbf['content'])
            worksheet.write('E%s' % row, res.get('diberikan_kepada') , wbf['content'])
            worksheet.write('F%s' % row, res.get('total') , wbf['content_float'])
            worksheet.write('G%s' % row, res.get('amount_gap') , wbf['content_float'])
            worksheet.write('H%s' % row, res.get('payment_klik_name') , wbf['content'])
            worksheet.write('I%s' % row, res.get('description') , wbf['content'])
            
            no+=1
            row+=1

        worksheet.autofilter('A4:I%s' % (row))
        worksheet.merge_range('A%s:I%s' % (row,row), '', wbf['total']) 
        
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write({'state_x':'get', 'data_x':out, 'name': filename})
        fp.close()
