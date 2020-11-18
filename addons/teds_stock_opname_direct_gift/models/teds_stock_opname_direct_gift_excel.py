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

class StockOpnameDirectGiftWizard(models.TransientModel):
    _name = "teds.stock.opname.direct.gift.wizard"

    name = fields.Char('Filename')
    file_excel = fields.Binary('File Excel')
    opname_dg_id = fields.Many2one('teds.stock.opname.direct.gift','Opname')    

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
        worksheet = workbook.add_worksheet('Stock Opname Direct Gift')
        worksheet.set_column('A1:A1', 5)
        worksheet.set_column('B1:B1', 12)
        worksheet.set_column('C1:C1', 23)
        worksheet.set_column('D1:D1', 35)
        worksheet.set_column('E1:E1', 30)
        worksheet.set_column('F1:F1', 15)
        worksheet.set_column('G1:G1', 15)
        worksheet.set_column('H1:H1', 18)
        worksheet.set_column('I1:I1', 15)
        worksheet.set_column('J1:J1', 17)
        worksheet.set_column('K1:K1', 17)
        worksheet.set_column('L1:L1', 17)
        worksheet.set_column('M1:M1', 17)
        worksheet.set_column('N1:N1', 17)
        worksheet.set_column('O:O1', 17)
        
        worksheet2 = workbook.add_worksheet('Stock Opname Direct Gift Other')
        worksheet2.set_column('A1:A1', 5)
        worksheet2.set_column('B1:B1', 12)
        worksheet2.set_column('C1:C1', 23)
        worksheet2.set_column('D1:D1', 35)
        worksheet2.set_column('E1:E1', 30)
        worksheet2.set_column('F1:F1', 15)
        worksheet2.set_column('G1:G1', 15)
        worksheet2.set_column('H1:H1', 18)
        worksheet2.set_column('I1:I1', 15)
        worksheet2.set_column('J1:J1', 17)
        worksheet2.set_column('K1:K1', 17)
        worksheet2.set_column('L1:L1', 17)
        worksheet2.set_column('M1:M1', 17)
        worksheet2.set_column('N1:N1', 17)
        worksheet2.set_column('O1:O1', 17)
        worksheet2.set_column('P1:P1', 17)
        
        filename = str(self.opname_dg_id.name)+'.xlsx'     

        worksheet.merge_range('A1:C1', 'No Refrensi: %s'%(self.opname_dg_id.name) , wbf['title_doc'])   
        
        worksheet.write('A3', 'No' , wbf['header'])
        worksheet.write('B3', 'Branch Code' , wbf['header'])
        worksheet.write('C3', 'Branch Name' , wbf['header'])
        worksheet.write('D3', 'Product' , wbf['header'])
        worksheet.write('E3', 'Description' , wbf['header'])
        worksheet.write('F3', 'Harga Satuan' , wbf['header'])
        worksheet.write('G3', 'Qty Sistem' , wbf['header'])
        worksheet.write('H3', 'Amount Total Sistem' , wbf['header'])
        worksheet.write('I3', 'Qty Fisik Baik' , wbf['header'])
        worksheet.write('J3', 'Qty Fisik Rusak' , wbf['header'])
        worksheet.write('K3', 'Total Qty Fisik' , wbf['header'])
        worksheet.write('L3', 'Amount Total Fisik' , wbf['header'])
        worksheet.write('M3', 'Selisih Qty' , wbf['header'])
        worksheet.write('N3', 'Selisih Amount' , wbf['header'])
        worksheet.write('O3', 'Saldo Logbook' , wbf['header'])
        worksheet.write('P3', 'Aging' , wbf['header'])
        

        row=4 
        row1 = row            
        no = 1    
        total_harga_satuan = 0
        total_qty = 0
        total_amount = 0
        total_qty_fisik_baik = 0
        total_qty_fisik_rusak = 0
        total_qty_fisik = 0
        total_amount_total = 0
        total_selisih_qty = 0
        total_selisih_amount = 0
        total_saldo_logbook = 0

        for detail in self.opname_dg_id.detail_ids:
            worksheet.write('A%s' % row, no , wbf['content'])
            worksheet.write('B%s' % row, self.opname_dg_id.branch_id.code , wbf['content'])
            worksheet.write('C%s' % row, self.opname_dg_id.branch_id.name , wbf['content'])
            worksheet.write('D%s' % row, detail.product_id.name_get().pop()[1] , wbf['content'])
            worksheet.write('E%s' % row, detail.name ,wbf['content'])
            worksheet.write('F%s' % row, detail.harga_satuan , wbf['content_float'])
            worksheet.write('G%s' % row, detail.qty , wbf['content_number'])
            worksheet.write('H%s' % row, detail.amount , wbf['content_float'])
            worksheet.write('I%s' % row, detail.qty_fisik_baik , wbf['content_number'])
            worksheet.write('J%s' % row, detail.qty_fisik_rusak , wbf['content_number'])
            worksheet.write('K%s' % row, detail.qty_fisik_total , wbf['content_number'])
            worksheet.write('L%s' % row, detail.amount_total , wbf['content_float'])
            worksheet.write('M%s' % row, detail.selisih_qty , wbf['content_float'])
            worksheet.write('N%s' % row, detail.selisih_amount , wbf['content_float'])
            worksheet.write('O%s' % row, detail.saldo_log_book , wbf['content_number'])
            worksheet.write('P%s' % row, detail.aging , wbf['content'])
            
            no+=1
            row+=1

            total_harga_satuan += detail['harga_satuan']
            total_qty += detail['qty']
            total_amount += detail['amount']
            total_qty_fisik_baik += detail['qty_fisik_baik']
            total_qty_fisik_rusak += detail['qty_fisik_rusak']
            total_qty_fisik += detail['qty_fisik_total']
            total_amount_total += detail['amount_total']
            total_selisih_qty += detail['selisih_qty']
            total_selisih_amount += detail['selisih_amount']
            total_saldo_logbook += detail['saldo_log_book']

        worksheet.autofilter('A3:P%s' % (row))  

        worksheet.merge_range('A%s:E%s' % (row,row), '', wbf['total'])
        formula_harga_satuan = '{=subtotal(9,F%s:F%s)}' % (row1, row-1) 
        formula_qty = '{=subtotal(9,G%s:G%s)}' % (row1, row-1) 
        formula_amount = '{=subtotal(9,H%s:H%s)}' % (row1, row-1) 
        formula_qty_fisik_baik = '{=subtotal(9,I%s:I%s)}' % (row1, row-1) 
        formula_qty_fisik_rusak = '{=subtotal(9,J%s:J%s)}' % (row1, row-1) 
        formula_qty_fisik = '{=subtotal(9,K%s:K%s)}' % (row1, row-1) 
        formula_amount_total = '{=subtotal(9,L%s:L%s)}' % (row1, row-1) 
        formula_selisih_qty = '{=subtotal(9,M%s:M%s)}' % (row1, row-1) 
        formula_selisih_amount = '{=subtotal(9,N%s:N%s)}' % (row1, row-1) 
        formula_logbook = '{=subtotal(9,O%s:O%s)}' % (row1, row-1) 

        worksheet.write_formula(row-1,5,formula_harga_satuan, wbf['total_float'], total_harga_satuan)
        worksheet.write_formula(row-1,6,formula_qty, wbf['total_float'], total_qty)
        worksheet.write_formula(row-1,7,formula_amount, wbf['total_float'], total_amount)
        worksheet.write_formula(row-1,8,formula_qty_fisik_baik, wbf['total_float'], total_qty_fisik_baik)
        worksheet.write_formula(row-1,9,formula_qty_fisik_rusak, wbf['total_float'], total_qty_fisik_rusak)
        worksheet.write_formula(row-1,10,formula_qty_fisik, wbf['total_float'], total_qty_fisik)
        worksheet.write_formula(row-1,11,formula_amount_total, wbf['total_float'], total_amount_total)
        worksheet.write_formula(row-1,12,formula_selisih_qty, wbf['total_float'], total_selisih_qty)
        worksheet.write_formula(row-1,13,formula_selisih_amount, wbf['total_float'], total_selisih_amount)
        worksheet.write_formula(row-1,14,formula_logbook, wbf['total_float'], total_saldo_logbook)
        
        worksheet.write('P%s' %row,'', wbf['total'])
        
        # SHEET 2
        worksheet2.merge_range('A1:C1', 'No Refrensi: %s'%(self.opname_dg_id.name) , wbf['title_doc'])   
        
        worksheet2.write('A3', 'No' , wbf['header'])
        worksheet2.write('B3', 'Branch Code' , wbf['header'])
        worksheet2.write('C3', 'Branch Name' , wbf['header'])
        worksheet2.write('D3', 'Nama Barang' , wbf['header'])
        worksheet2.write('E3', 'Qty Fisik Baik' , wbf['header'])
        worksheet2.write('F3', 'Qty Fisik Rusak' , wbf['header'])
        worksheet2.write('G3', 'Total Qty Fisik' , wbf['header'])
        worksheet2.write('H3', 'Saldo Logbook' , wbf['header'])

        row2=4 
        row3 = row2
        no2 = 1    
        other_total_qty_fisik_baik = 0
        other_total_qty_fisik_rusak = 0
        other_total_qty_fisik = 0
        other_total_saldo_logbook = 0

        for other in self.opname_dg_id.other_dg_ids:
            worksheet2.write('A%s' % row2, no2 , wbf['content'])
            worksheet2.write('B%s' % row2, self.opname_dg_id.branch_id.code , wbf['content'])
            worksheet2.write('C%s' % row2, self.opname_dg_id.branch_id.name , wbf['content'])
            worksheet2.write('D%s' % row2, other.nama_product , wbf['content'])
            worksheet2.write('E%s' % row2, other.qty_fisik_baik ,wbf['content'])
            worksheet2.write('F%s' % row2, other.qty_fisik_rusak , wbf['content_float'])
            worksheet2.write('G%s' % row2, other.qty_fisik_total , wbf['content_number'])
            worksheet2.write('H%s' % row2, other.saldo_log_book , wbf['content_number'])
            
            no2+=1
            row2+=1

            other_total_qty_fisik_baik += other['qty_fisik_baik']
            other_total_qty_fisik_rusak += other['qty_fisik_rusak']
            other_total_qty_fisik += other['qty_fisik_total']
            other_total_saldo_logbook += other['saldo_log_book']

        worksheet2.autofilter('A3:H%s' % (row2))  

        worksheet2.merge_range('A%s:D%s' % (row2,row2), '', wbf['total'])
        other_formula_qty_fisik_baik = '{=subtotal(9,E%s:E%s)}' % (row2, row3-1) 
        other_formula_qty_fisik_rusak = '{=subtotal(9,F%s:F%s)}' % (row2, row3-1) 
        other_formula_qty_fisik = '{=subtotal(9,G%s:G%s)}' % (row2, row3-1) 
        other_formula_logbook = '{=subtotal(9,H%s:H%s)}' % (row2, row3-1) 

        worksheet2.write_formula(row2-1,4,other_formula_qty_fisik_baik, wbf['total_float'], other_total_qty_fisik_baik)
        worksheet2.write_formula(row2-1,5,other_formula_qty_fisik_rusak, wbf['total_float'], other_total_qty_fisik_rusak)
        worksheet2.write_formula(row2-1,6,other_formula_qty_fisik, wbf['total_float'], other_total_qty_fisik)
        worksheet2.write_formula(row2-1,7,other_formula_logbook, wbf['total_float'], other_total_saldo_logbook)
        

        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write({'name':filename, 'file_excel':out})
        fp.close()

