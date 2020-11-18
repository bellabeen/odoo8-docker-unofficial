import cStringIO
import xlsxwriter
from cStringIO import StringIO
import base64
import os
from openerp import models, fields, api
from datetime import datetime, timedelta,date
from dateutil.relativedelta import relativedelta
import calendar

class ReportPembelianPartAhmWizard(models.TransientModel):
    _name = "teds.report.pembelian.part.ahm.wizard"

    wbf = {}
    
    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()
    

    name = fields.Char('Filename', readonly=True)
    state_x = fields.Selection([('choose','choose'),('get','get')], default='choose')
    data_x = fields.Binary('File', readonly=True)
    branch_ids = fields.Many2many('wtc.branch', 'teds_report_po_ahm_branch_rel', 'report_id','branch_id', string='Branch')
    start_date = fields.Date('Start Date',default=_get_default_date)
    end_date = fields.Date('End Date',default=_get_default_date)
    division  = fields.Selection([('Unit','Unit'),('Sparepart','Sparepart')],default="Sparepart")

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
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet("Pembelian Part AHM")
        worksheet.set_column('A1:A1', 5)
        worksheet.set_column('B1:B1', 24)
        worksheet.set_column('C1:C1', 24)
        worksheet.set_column('D1:D1', 23)
        worksheet.set_column('E1:E1', 27)
        worksheet.set_column('F1:F1', 24)
        worksheet.set_column('G1:G1', 24)
        worksheet.set_column('H1:H1', 20)
        
        date = datetime.now()
        date = date.strftime("%d-%m-%Y %H:%M:%S")

        filename = 'Laporan Pembelian Part AHM %s.xlsx'%(str(date))
        worksheet.merge_range('A1:C1', 'Laporan Pembelian Part AHM', wbf['company'])   
        worksheet.merge_range('A2:C2', 'Periode %s - %s' %(self.start_date,self.end_date) , wbf['company'])  

        worksheet.write('A4', 'No' , wbf['header'])
        worksheet.write('B4', 'Branch Code' , wbf['header'])
        worksheet.write('C4', 'Branch Name' , wbf['header'])
        worksheet.write('D4', 'Supplier' , wbf['header'])
        worksheet.write('E4', 'Picking Name' , wbf['header'])
        worksheet.write('F4', 'Packing Name' , wbf['header'])
        worksheet.write('G4', 'Part Code' , wbf['header'])
        worksheet.write('H4', 'Part Name' , wbf['header'])
        worksheet.write('I4', 'No Invoice' , wbf['header'])
        worksheet.write('J4', 'Kode PS' , wbf['header'])
        worksheet.write('K4', 'Quantity' , wbf['header'])
        
        row=5
        no = 1     

        query_where = "WHERE 1=1 AND spa.state = 'posted' AND spi.partner_id = b.default_supplier_id AND b.branch_type = 'MD'"
        if self.division:
            query_where += " AND spi.division = '%s'" %self.division
        if self.start_date:
            query_where += " AND (spi.date + INTERVAL '7 hours')::date >= '%s'" %self.start_date
        if self.end_date:
            query_where += " AND (spi.date + INTERVAL '7 hours')::date <= '%s'" %self.end_date
        
        query = """
            SELECT
            b.code as branch_code
            , b.name as branch_name
            , p.name as supplier
            , spa.name as packing_name
            , spi.name as picking_name
            , pt.name as part_code
            , pp.default_code as part_name
            , spal.quantity
            , spi.origin as kode_ps
            , (SELECT no_invoice 
            FROM b2b_file_ps ps
            INNER JOIN b2b_file_fdo_line fhl ON ps.kode_ps = fhl.kode_ps
            INNER JOIN b2b_file_fdo_header fh ON fh.id = fhl.b2b_file_fdo_header_id
            WHERE ps.kode_ps = spi.origin AND ps.kode_sparepart = pt.name
            LIMIT 1
            )
            from stock_picking spi
            INNER JOIN wtc_stock_packing spa ON spa.picking_id = spi.id
            INNER JOIN wtc_branch b on b.id = spi.branch_id
            LEFT JOIN res_partner p ON p.id = b.default_supplier_id
            INNER JOIN wtc_stock_packing_line spal ON spal.packing_id = spa.id
            INNER JOIN product_product pp ON pp.id = spal.product_id
            INNER JOIN product_template pt ON pt.id = pp.product_tmpl_id
            %s            
            ORDER BY spa.name ASC
        """ %query_where
        self.env.cr.execute(query)
        ress = self.env.cr.dictfetchall() 
        for res in ress:
            worksheet.write('A%s' % row, no , wbf['content_number'])
            worksheet.write('B%s' % row, res.get('branch_code') , wbf['content'])
            worksheet.write('C%s' % row, res.get('branch_name') , wbf['content'])
            worksheet.write('D%s' % row, res.get('supplier') , wbf['content'])
            worksheet.write('E%s' % row, res.get('picking_name') , wbf['content'])
            worksheet.write('F%s' % row, res.get('packing_name') , wbf['content'])
            worksheet.write('G%s' % row, res.get('part_code') , wbf['content'])
            worksheet.write('H%s' % row, res.get('part_name') , wbf['content'])
            worksheet.write('I%s' % row, res.get('no_invoice') , wbf['content'])
            worksheet.write('J%s' % row, res.get('kode_ps') , wbf['content'])
            worksheet.write('K%s' % row, res.get('quantity') , wbf['content_float'])

            no+=1
            row+=1

        worksheet.autofilter('A4:K%s' % (row))
        worksheet.merge_range('A%s:K%s' % (row,row), '', wbf['total']) 

        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write({'state_x':'get', 'data_x':out, 'name': filename})
        fp.close()

        form_id = self.env.ref('teds_report_part_ahm.view_teds_report_pembelian_part_ahm_wizard').id
    
        return {
            'name': ('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.report.pembelian.part.ahm.wizard',
            'res_id': self.ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }