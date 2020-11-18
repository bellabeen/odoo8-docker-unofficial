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

class StockOpnameBpkbWizard(models.TransientModel):
    _name = "teds.stock.opname.bpkb.wizard"

    name = fields.Char('Filename')
    file_excel = fields.Binary('File Excel')
    opname_bpkb_id = fields.Many2one('teds.stock.opname.bpkb','Opname')    

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
    def action_download_excel(self):
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Stock Opname BPKB')
        worksheet.set_column('A1:A1', 5)
        worksheet.set_column('B1:B1', 10)
        worksheet.set_column('C1:C1', 20)
        worksheet.set_column('D1:D1', 23)
        worksheet.set_column('E1:E1', 28)
        worksheet.set_column('F1:F1', 17)
        worksheet.set_column('G1:G1', 15)
        worksheet.set_column('H1:H1', 15)
        worksheet.set_column('I1:I1', 28)
        worksheet.set_column('J1:J1', 15)
        worksheet.set_column('K1:K1', 28)
        worksheet.set_column('L1:L1', 35)
        worksheet.set_column('M1:M1', 25)
        worksheet.set_column('N1:N1', 25)
        worksheet.set_column('O:O1', 20)
        worksheet.set_column('P1:P1', 15)

        worksheet2 = workbook.add_worksheet('Stock Opname BPKB Other')
        worksheet2.set_column('A1:A1', 5)
        worksheet2.set_column('B1:B1', 10)
        worksheet2.set_column('C1:C1', 20)
        worksheet2.set_column('D1:D1', 23)
        worksheet2.set_column('E1:E1', 28)
        worksheet2.set_column('F1:F1', 17)
        worksheet2.set_column('G1:G1', 15)
        worksheet2.set_column('H1:H1', 15)
        worksheet2.set_column('I1:I1', 28)
        worksheet2.set_column('J1:J1', 15)
        worksheet2.set_column('K1:K1', 28)
        worksheet2.set_column('L1:L1', 20)
        worksheet2.set_column('M1:M1', 20)
        worksheet2.set_column('N1:N1', 20)
        
        filename = str(self.opname_bpkb_id.name)+'.xlsx'     

        worksheet.merge_range('A1:C1', 'No Refrensi: %s'%(self.opname_bpkb_id.name) , wbf['title_doc'])   
        
        worksheet.write('A3', 'No' , wbf['header'])
        worksheet.write('B3', 'Branch Code' , wbf['header'])
        worksheet.write('C3', 'Branch Name' , wbf['header'])
        worksheet.write('D3', 'Nama BPKB' , wbf['header'])
        worksheet.write('E3', 'Validasi Nama BPKB' , wbf['header'])
        worksheet.write('F3', 'Tanggal Penerimaan' , wbf['header'])
        worksheet.write('G3', 'Lokasi BPKB' , wbf['header'])
        worksheet.write('H3', 'No Engine' , wbf['header'])
        worksheet.write('I3', 'Validasi No Engine' , wbf['header'])
        worksheet.write('J3', 'No BPKB' , wbf['header'])
        worksheet.write('K3', 'Validasi No BPKB' , wbf['header'])
        worksheet.write('L3', 'Ceklis Fisik BPKB' , wbf['header'])
        worksheet.write('M3', 'Finance Company' , wbf['header'])
        worksheet.write('N3', 'Keterangan' , wbf['header'])
        worksheet.write('O3', 'Umur' , wbf['header'])
        worksheet.write('P3', 'Over Due' , wbf['header'])


        row=4             
        no = 1     
        for detail in self.opname_bpkb_id.detail_ids:
            worksheet.write('A%s' % row, no , wbf['content'])
            worksheet.write('B%s' % row, self.opname_bpkb_id.branch_id.code , wbf['content'])
            worksheet.write('C%s' % row, self.opname_bpkb_id.branch_id.name , wbf['content'])
            worksheet.write('D%s' % row, detail.customer_bpkb_id.name , wbf['content'])
            worksheet.write('E%s' % row, detail.validasi_nama_bpkb ,wbf['content'])
            worksheet.write('F%s' % row, detail.tgl_penerimaan , wbf['content'])
            worksheet.write('G%s' % row, detail.lokasi_bpkb , wbf['content'])
            worksheet.write('H%s' % row, detail.lot_id.name , wbf['content'])
            worksheet.write('I%s' % row, detail.validasi_no_engine , wbf['content'])
            worksheet.write('J%s' % row, detail.no_bpkb , wbf['content'])
            worksheet.write('K%s' % row, detail.validasi_no_bpkb , wbf['content'])
            worksheet.write('L%s' % row, detail.validasi_ceklis_fisik_bpkb , wbf['content'])
            worksheet.write('M%s' % row, detail.finco_id.name if detail.finco_id else '' , wbf['content'])
            worksheet.write('N%s' % row, detail.keterangan if detail.keterangan else '-' , wbf['content'])
            worksheet.write('O%s' % row, detail.umur , wbf['content'])
            worksheet.write('P%s' % row, detail.over_due , wbf['content'])

            no+=1
            row+=1

        worksheet.autofilter('A3:P%s' % (row))  
        worksheet.merge_range('A%s:P%s' % (row,row), '', wbf['total'])

        # SHEET 2
        worksheet2.merge_range('A1:C1', 'No Refrensi: %s'%(self.opname_bpkb_id.name) , wbf['title_doc'])   
        worksheet2.write('A3', 'No' , wbf['header'])
        worksheet2.write('B3', 'Branch Code' , wbf['header'])
        worksheet2.write('C3', 'Branch Name' , wbf['header'])
        worksheet2.write('D3', 'Nama BPKB' , wbf['header'])
        worksheet2.write('E3', 'No Engine' , wbf['header'])
        worksheet2.write('F3', 'Keterangan' , wbf['header'])

        row2=4
        no2 = 1     
        for other in self.opname_bpkb_id.other_bpkb_ids:
            worksheet2.write('A%s' % row2, no2 , wbf['content'])
            worksheet2.write('B%s' % row2, self.opname_bpkb_id.branch_id.code , wbf['content'])
            worksheet2.write('C%s' % row2, self.opname_bpkb_id.branch_id.name , wbf['content'])
            worksheet2.write('D%s' % row2, other.nama_bpkb , wbf['content'])
            worksheet2.write('E%s' % row2, other.no_engine , wbf['content'])
            worksheet2.write('F%s' % row2, other.keterangan if other.keterangan else '', wbf['content'])
            
            no2+=1
            row2+=1
        worksheet2.autofilter('A3:F%s' % (row2))
        worksheet2.merge_range('A%s:F%s' % (row2,row2), '', wbf['total'])

        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write({'name':filename, 'file_excel':out})
        fp.close()

