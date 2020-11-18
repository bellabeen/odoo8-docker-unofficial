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

class StockOpnameUnitWizard(models.TransientModel):
    _name = "teds.stock.opname.unit.wizard"

    name = fields.Char('Filename')
    file_excel = fields.Binary('File Excel')
    opname_unit_id = fields.Many2one('teds.stock.opname.unit','Opname')    

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
        worksheet = workbook.add_worksheet('Stock Opname Unit')
        worksheet.set_column('A1:A1', 5)
        worksheet.set_column('B1:B1', 9)
        worksheet.set_column('C1:C1', 23)
        worksheet.set_column('D1:D1', 40)
        worksheet.set_column('E1:E1', 20)
        worksheet.set_column('F1:F1', 20)
        worksheet.set_column('G1:G1', 20)
        worksheet.set_column('H1:H1', 23)
        worksheet.set_column('I1:I1', 15)
        worksheet.set_column('J1:J1', 15)
        worksheet.set_column('K1:K1', 18)
        worksheet.set_column('L1:L1', 20)
        worksheet.set_column('M1:M1', 18)
        worksheet.set_column('N1:N1', 24)
        worksheet.set_column('O1:O1', 55)
        worksheet.set_column('P1:P1', 20)
        worksheet.set_column('Q:Q1', 25)
        
        worksheet2 = workbook.add_worksheet('Stock Opname Accesories')
        worksheet2.set_column('A1:A1', 5)
        worksheet2.set_column('B1:B1', 9)
        worksheet2.set_column('C1:C1', 23)
        worksheet2.set_column('D1:D1', 25)
        worksheet2.set_column('E1:E1', 20)
        worksheet2.set_column('F1:F1', 10)
        worksheet2.set_column('G1:G1', 12)
        worksheet2.set_column('H1:H1', 12)
        worksheet2.set_column('I1:I1', 12)
        worksheet2.set_column('J1:J1', 25)
        worksheet2.set_column('K1:K1', 17)
        worksheet2.set_column('L1:L1', 10)
        worksheet2.set_column('M1:M1', 25)
        worksheet2.set_column('N1:N1', 15)
        
        filename = str(self.opname_unit_id.name)+'.xlsx'     

        worksheet.merge_range('A1:C1', 'No Refrensi: %s'%(self.opname_unit_id.name) , wbf['title_doc'])   
        
        worksheet.write('A3', 'No' , wbf['header'])
        worksheet.write('B3', 'Code' , wbf['header'])
        worksheet.write('C3', 'Cabang' , wbf['header'])
        worksheet.write('D3', 'Product' , wbf['header'])
        worksheet.write('E3', 'Engine No' , wbf['header'])
        worksheet.write('F3', 'Chassis No' , wbf['header'])
        worksheet.write('G3', 'Validasi Fisik' , wbf['header'])
        worksheet.write('H3', 'Validasi Engine' , wbf['header'])
        worksheet.write('I3', 'Validasi Chassis' , wbf['header'])
        worksheet.write('J3', 'Product Type' , wbf['header'])
        worksheet.write('K3', 'Warna' , wbf['header'])
        worksheet.write('L3', 'Validasi Warna' , wbf['header'])
        worksheet.write('M3', 'Incoming Date' , wbf['header'])
        worksheet.write('N3', 'Validasi Taging' , wbf['header'])
        worksheet.write('O3', 'Location' , wbf['header'])
        worksheet.write('P3', 'Kondisi Fisik' , wbf['header'])
        worksheet.write('Q3', 'Keterangan' , wbf['header'])
        

        row=4 
        no = 1    

        for detail in self.opname_unit_id.detail_ids:
            worksheet.write('A%s' % row, no , wbf['content'])
            worksheet.write('B%s' % row, self.opname_unit_id.branch_id.code , wbf['content'])
            worksheet.write('C%s' % row, self.opname_unit_id.branch_id.name , wbf['content'])
            worksheet.write('D%s' % row, detail.name , wbf['content'])
            worksheet.write('E%s' % row, detail.engine_no ,wbf['content'])
            worksheet.write('F%s' % row, detail.chassis_no , wbf['content'])
            worksheet.write('G%s' % row, detail.validasi_fisik if detail.validasi_fisik else '' , wbf['content'])
            worksheet.write('H%s' % row, detail.validasi_engine if detail.validasi_engine else '' , wbf['content'])
            worksheet.write('I%s' % row, detail.validasi_chassis if detail.validasi_chassis else '' , wbf['content'])
            worksheet.write('J%s' % row, detail.product_type , wbf['content'])
            worksheet.write('K%s' % row, detail.product_warna , wbf['content'])
            worksheet.write('L%s' % row, detail.validasi_warna if detail.validasi_warna else '' , wbf['content'])
            worksheet.write('M%s' % row, detail.incoming_date , wbf['content'])
            worksheet.write('N%s' % row, detail.validasi_taging if detail.validasi_taging else '' , wbf['content'])
            worksheet.write('O%s' % row, detail.lokasi , wbf['content'])
            worksheet.write('P%s' % row, detail.kondisi_fisik if detail.kondisi_fisik else '' , wbf['content'])
            worksheet.write('Q%s' % row, detail.keterangan if detail.keterangan else '', wbf['content'])

            
            no+=1
            row+=1

        worksheet.autofilter('A3:Q%s' % (row))  
        worksheet.merge_range('A%s:Q%s' % (row,row), '', wbf['total'])

        # Aksesoris
        worksheet2.merge_range('A1:C1', 'No Refrensi: %s'%(self.opname_unit_id.name) , wbf['title_doc'])   
        
        worksheet2.write('A3', 'No' , wbf['header'])
        worksheet2.write('B3', 'Code' , wbf['header'])
        worksheet2.write('C3', 'Cabang' , wbf['header'])
        worksheet2.write('D3', 'Product' , wbf['header'])
        worksheet2.write('E3', 'Category' , wbf['header'])
        worksheet2.write('F3', 'Good' , wbf['header'])
        worksheet2.write('G3', 'Not Good' , wbf['header'])
        worksheet2.write('H3', 'Total Fisik' , wbf['header'])
        worksheet2.write('I3', 'Total Unit' , wbf['header'])
        worksheet2.write('J3', 'Ket Not Good' , wbf['header'])
        worksheet2.write('K3', '(+/- NG dr SO lalu)' , wbf['header'])
        worksheet2.write('L3', 'Selisih' , wbf['header'])
        worksheet2.write('M3', 'Ket Selisih' , wbf['header'])
        worksheet2.write('N3', 'Selisih SO Lalu' , wbf['header'])
        

        row_s =4 
        no2 = 1    

        for detail in self.opname_unit_id.aksesoris_ids:
            worksheet2.write('A%s' % row_s, no2 , wbf['content'])
            worksheet2.write('B%s' % row_s, self.opname_unit_id.branch_id.code , wbf['content'])
            worksheet2.write('C%s' % row_s, self.opname_unit_id.branch_id.name , wbf['content'])
            worksheet2.write('D%s' % row_s, detail.name , wbf['content'])
            worksheet2.write('E%s' % row_s, detail.category ,wbf['content'])
            worksheet2.write('F%s' % row_s, detail.qty_good , wbf['content'])
            worksheet2.write('G%s' % row_s, detail.qty_not_good , wbf['content'])
            worksheet2.write('H%s' % row_s, detail.total , wbf['content'])
            worksheet2.write('I%s' % row_s, detail.total_unit , wbf['content'])
            worksheet2.write('J%s' % row_s, detail.ket_not_good if detail.ket_not_good else '' , wbf['content'])
            worksheet2.write('K%s' % row_s, detail.last_not_good , wbf['content'])
            worksheet2.write('L%s' % row_s, detail.selisih , wbf['content'])
            worksheet2.write('M%s' % row_s, detail.keterangan_selisih if detail.keterangan_selisih else '' , wbf['content'])
            worksheet2.write('N%s' % row_s, detail.selisih_so_lalu , wbf['content'])
            
            no2 +=1
            row_s +=1

        worksheet2.autofilter('A3:N%s' % (row_s))  
        worksheet2.merge_range('A%s:N%s' % (row_s,row_s), '', wbf['total'])

        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write({'name':filename, 'file_excel':out})
        fp.close()

