import time
import cStringIO
import xlsxwriter
from cStringIO import StringIO
import base64
import tempfile
import os
from openerp import models, fields, api
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from xlsxwriter.utility import xl_rowcol_to_cell

class ReportPajakProgressiveWizard(models.TransientModel):
    _name = "teds.report.pajak.progressive.wizard"

    def _get_default_date(self):
        return datetime.now()

    name = fields.Char('Filename')
    file_excel = fields.Binary('File Excel')
    start_date = fields.Date('Start Date',default=_get_default_date)
    end_date = fields.Date('End Date',default=_get_default_date)
    branch_ids = fields.Many2many('wtc.branch', 'teds_pajak_progressive_report_branch_rel', 'report_id', 'branch_id')
    state_x = fields.Selection([('choose','choose'),('get','get')],default='choose')
        
    wbf = {}

    @api.multi
    def add_workbook_format(self,workbook):      
        self.wbf['header'] = workbook.add_format({'bold': 1,'align': 'center','bg_color': '#FFFFDB','font_color': '#000000'})
        self.wbf['header'].set_border()
        self.wbf['header'].set_font_size(10)

        self.wbf['footer'] = workbook.add_format({'align':'left'})
        
        self.wbf['title_doc'] = workbook.add_format({'bold': 1,'align': 'left'})
        self.wbf['title_doc'].set_font_size(10)
        
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

        self.wbf['total'] = workbook.add_format({'bold':1,'bg_color': '#FFFFDB','align':'center'})
        self.wbf['total'].set_left()
        self.wbf['total'].set_right()
        self.wbf['total'].set_top()
        self.wbf['total'].set_bottom()

        self.wbf['total_float'] = workbook.add_format({'bold':1,'bg_color': '#FFFFDB','align': 'right','num_format': '#,##0.00'})
        self.wbf['total_float'].set_top()
        self.wbf['total_float'].set_bottom()            
        self.wbf['total_float'].set_left()
        self.wbf['total_float'].set_right()
                        
        return workbook


    @api.multi
    def excel_report(self):
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Pajak Progressive')
        worksheet.set_column('A1:A1', 5)
        worksheet.set_column('B1:B1', 14)
        worksheet.set_column('C1:C1', 23)
        worksheet.set_column('D1:D1', 20)
        worksheet.set_column('E1:E1', 17)
        worksheet.set_column('F1:F1', 30)
        worksheet.set_column('G1:G1', 17)
        worksheet.set_column('H1:H1', 20)
        worksheet.set_column('I1:I1', 20)
        worksheet.set_column('J1:J1', 17)
        worksheet.set_column('K1:K1', 17)
        worksheet.set_column('L1:L1', 20)
        worksheet.set_column('M1:M1', 17)
        worksheet.set_column('N1:N1', 15)
        worksheet.set_column('O:O1', 17)
        
        filename = 'Report Pajak Progressive %s.xlsx'%(datetime.now().strftime("%d-%m-%Y %H:%M:%S"))

        worksheet.merge_range('A1:C1', 'PT. Tunas Dwipa Matra', wbf['title_doc'])
        worksheet.merge_range('A2:C2', 'Report Pajak Progressive', wbf['title_doc'])

        worksheet.write('A4', 'No' , wbf['header'])
        worksheet.write('B4', 'Branch Code' , wbf['header'])
        worksheet.write('C4', 'Branch Name' , wbf['header'])
        worksheet.write('D4', 'No Sale Order' , wbf['header'])
        worksheet.write('E4', 'Partner Code' , wbf['header'])
        worksheet.write('F4', 'Partner Name' , wbf['header'])
        worksheet.write('G4', 'No Telp' , wbf['header'])
        worksheet.write('H4', 'Salesman' , wbf['header'])
        worksheet.write('I4', 'Sales Kordinator' , wbf['header'])
        worksheet.write('J4', 'No Engine' , wbf['header'])
        worksheet.write('K4', 'No Chassis' , wbf['header'])
        worksheet.write('L4', 'No Invoice' , wbf['header'])
        worksheet.write('M4', 'Total Invoice' , wbf['header'])
        worksheet.write('N4', 'Date' , wbf['header'])
        
        row=5
        no = 1    
        query_where = " WHERE pp.state = 'confirmed' AND ai.state != 'paid'"
        if self.branch_ids:
            branch_ids = [b.id for b in self.branch_ids]
            query_where += " AND b.id in %s "%(str(tuple(branch_ids)).replace(',)', ')'))
        if self.start_date:
            query_where += " AND pp.tanggal >= '%s'"%(self.start_date)
        if self.end_date:
            query_where += " AND pp.tanggal <= '%s'"%(self.end_date)

        query = """
            SELECT b.code as branch_code
            , b.name as branch_name
            , lot.name as engine
            , lot.chassis_no as chassis
            , so.name as no_so
            , p.display_name as customer
            , p.default_code as partner_code
            , p.name as partner_name
            , p.mobile as no_telp
            , hr.name_related as sales
            , hr2.name_related  as koordinator
            , ai.number as no_invoce
            , ai.date_invoice 
            , ai.date_due
            , AGE(CURRENT_TIMESTAMP, ai.date_invoice+ INTERVAL '7 hours') as overdue
            , ai.amount_total
            FROM wtc_pajak_progressive pp
            INNER JOIN wtc_pajak_progressive_line ppl ON ppl.pajak_progressive_id = pp.id
            INNER JOIN stock_production_lot lot ON lot.id = ppl.lot_id
            INNER JOIN wtc_branch b ON b.id = lot.branch_id
            INNER JOIN dealer_sale_order so ON so.id = lot.dealer_sale_order_id
            INNER JOIN account_invoice ai ON ai.id = lot.inv_pajak_progressive_id
            INNER JOIN res_partner p ON p.id = lot.customer_id
            INNER JOIN res_users u ON u.id = so.user_id
            INNER JOIN resource_resource rr ON rr.user_id = u.id
            INNER JOIN hr_employee hr ON hr.resource_id = rr.id

            INNER JOIN res_users u2 ON u2.id = so.sales_koordinator_id
            INNER JOIN resource_resource rr2 ON rr2.user_id = u2.id
            INNER JOIN hr_employee hr2 ON hr2.resource_id = rr2.id
            %s
        """%(query_where)
        self.env.cr.execute(query)
        ress = self.env.cr.dictfetchall()

        for res in ress:
            worksheet.write('A%s' % row, no , wbf['content'])
            worksheet.write('B%s' % row, res.get('branch_code') , wbf['content'])
            worksheet.write('C%s' % row, res.get('branch_name') , wbf['content'])
            worksheet.write('D%s' % row, res.get('no_so') , wbf['content'])
            worksheet.write('E%s' % row, res.get('partner_code') ,wbf['content'])
            worksheet.write('F%s' % row, res.get('partner_name') , wbf['content'])
            worksheet.write('G%s' % row, res.get('no_telp') , wbf['content_number'])
            worksheet.write('H%s' % row, res.get('sales') , wbf['content'])
            worksheet.write('I%s' % row, res.get('koordinator') , wbf['content'])
            worksheet.write('J%s' % row, res.get('engine') , wbf['content'])
            worksheet.write('K%s' % row, res.get('chassis') , wbf['content'])
            worksheet.write('L%s' % row, res.get('no_invoce') , wbf['content'])
            worksheet.write('M%s' % row, res.get('amount_total') , wbf['content_float'])
            worksheet.write('N%s' % row, res.get('date_invoice') , wbf['content'])
            
            no+=1
            row+=1

        worksheet.autofilter('A4:N%s' % (row))  

        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user = self.env['res.users'].browse(self._uid).name
        
        
        worksheet.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])

        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write({'state_x':'get', 'file_excel':out, 'name': filename})
        fp.close()
        form_id = self.env.ref('teds_report_pajak_progressive.view_teds_report_pajak_progressive_wizard').id
        
        return {
            'name': ('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.report.pajak.progressive.wizard',
            'res_id': self.ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }

