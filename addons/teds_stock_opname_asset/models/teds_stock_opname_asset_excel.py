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

class StockOpnameAssetWizard(models.TransientModel):
    _name = "teds.stock.opname.asset.wizard"

    name = fields.Char('Filename')
    file_excel = fields.Binary('File Excel')
    opname_asset_id = fields.Many2one('teds.stock.opname.asset','Opname')    

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
        worksheet = workbook.add_worksheet('Stock Opname Asset')
        worksheet.set_column('A1:A1', 5)
        worksheet.set_column('B1:B1', 10)
        worksheet.set_column('C1:C1', 20)
        worksheet.set_column('D1:D1', 23)
        worksheet.set_column('E1:E1', 28)
        worksheet.set_column('F1:F1', 8)
        worksheet.set_column('G1:G1', 35)
        worksheet.set_column('H1:H1', 19)
        worksheet.set_column('I1:I1', 18)
        worksheet.set_column('J1:J1', 17)
        worksheet.set_column('K1:K1', 19)
        worksheet.set_column('L1:L1', 30)
        
        worksheet2 = workbook.add_worksheet('Asset Tidak Tercatat')
        worksheet2.set_column('A1:A1', 5)
        worksheet2.set_column('B1:B1', 24)
        worksheet2.set_column('C1:C1', 20)
        worksheet2.set_column('D1:D1', 23)
        worksheet2.set_column('E1:E1', 28)
        worksheet2.set_column('F1:F1', 20)
        worksheet2.set_column('G1:G1', 35)
        
        filename = str(self.opname_asset_id.name)+'.xlsx'     

        worksheet.merge_range('A1:C1', 'No Refrensi: %s'%(self.opname_asset_id.name) , wbf['title_doc'])   
        
        worksheet.write('A3', 'No' , wbf['header'])
        worksheet.write('B3', 'Code' , wbf['header'])
        worksheet.write('C3', 'Cabang' , wbf['header'])
        worksheet.write('D3', 'Kode Asset' , wbf['header'])
        worksheet.write('E3', 'Nama Asset' , wbf['header'])
        worksheet.write('F3', 'Kategory' , wbf['header'])
        worksheet.write('G3', 'Kategory Desc' , wbf['header'])
        worksheet.write('H3', 'Lokasi Fisik Asset' , wbf['header'])
        worksheet.write('I3', 'PIC Asset' , wbf['header'])
        worksheet.write('J3', 'Konidisi Fisik Asset' , wbf['header'])
        worksheet.write('K3', 'No Engine' , wbf['header'])
        worksheet.write('L3', 'Keterangan' , wbf['header'])
        
        
        row=4             
        no = 1     
        for detail in self.opname_asset_id.detail_ids:
            worksheet.write('A%s' % row, no , wbf['content'])
            worksheet.write('B%s' % row, self.opname_asset_id.branch_id.code , wbf['content'])
            worksheet.write('C%s' % row, self.opname_asset_id.branch_id.name , wbf['content'])
            worksheet.write('D%s' % row, detail.code , wbf['content'])
            worksheet.write('E%s' % row, detail.name ,wbf['content'])
            worksheet.write('F%s' % row, detail.kategory , wbf['content'])
            worksheet.write('G%s' % row, detail.description , wbf['content'])
            worksheet.write('H%s' % row, detail.validasi_lokasi if detail.validasi_lokasi else '' , wbf['content'])
            worksheet.write('I%s' % row, detail.validasi_pic if detail.validasi_pic else '' , wbf['content'])
            worksheet.write('J%s' % row, detail.validasi_kondisi_fisik if detail.validasi_kondisi_fisik else '' , wbf['content'])
            worksheet.write('K%s' % row, detail.no_mesin if detail.no_mesin else '' , wbf['content'])
            worksheet.write('L%s' % row, detail.keterangan if detail.keterangan else '' , wbf['content'])
             
            no+=1
            row+=1

        worksheet.autofilter('A3:L%s' % (row))  
        worksheet.merge_range('A%s:L%s' % (row,row), '', wbf['total'])

        # Sheet 2
        worksheet2.write('A1', 'No' , wbf['header'])
        worksheet2.write('B1', 'Nama Asset' , wbf['header'])
        worksheet2.write('C1', 'Lokasi Fisik Unit' , wbf['header'])
        worksheet2.write('D1', 'PIC Asset' , wbf['header'])
        worksheet2.write('E1', 'Kondisi Fisik Asset' , wbf['header'])
        worksheet2.write('F1', 'No Mesin' , wbf['header'])
        worksheet2.write('G1', 'Keterangan' , wbf['header'])

        row2 = 2
        no2 = 1
        for other in self.opname_asset_id.other_asset_ids:
            worksheet2.write('A%s' % row2, no2 , wbf['content'])
            worksheet2.write('B%s' % row2, other.name if other.name else '' , wbf['content'])
            worksheet2.write('C%s' % row2, other.lokasi_fisik_unit if other.lokasi_fisik_unit else '' , wbf['content'])
            worksheet2.write('D%s' % row2, other.pic if other.pic else '' , wbf['content'])
            worksheet2.write('E%s' % row2, other.kondisi_fisik if other.kondisi_fisik else '' ,wbf['content'])
            worksheet2.write('F%s' % row2, other.no_mesin if other.no_mesin else '' , wbf['content'])
            worksheet2.write('G%s' % row2, other.keterangan if other.keterangan else '' , wbf['content'])
            
            no2 += 1
            row2 += 1

        worksheet2.autofilter('A1:G%s' % (row2))  
        worksheet2.merge_range('A%s:G%s' % (row2,row2), '', wbf['total'])
        

        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write({'name':filename, 'file_excel':out})
        fp.close()

