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
import calendar

class LaporanStockOpnameWizard(models.TransientModel):
    _inherit = "teds.laporan.stock.opname.wizard"

    def laporan_so_dg(self):
        query_where = " WHERE 1=1"
        if self.status == 'Outstanding':
            query_where += " AND sot.state = 'draft'"
        if self.status == 'Done':
            query_where += " AND sot.state = 'posted'"
        if self.branch_ids:
            branch_ids = [b.id for b in self.branch_ids]   
            query_where +=" AND sot.branch_id in %s" % str(tuple(branch_ids)).replace(',)', ')')
        if self.periode and self.tahun:
            query_where +=" AND to_char(sot.date,'MM') = '%s' AND to_char(sot.date,'YYYY') = '%s'" %(self.periode,self.tahun)


        query = """
            SELECT 
            b.code as code
            , b.name as branch
            , sot.name as no_so
            , sot.staff_bbn
            , sot.adh
            , sot.soh
            , sot.date as tgl_so
            , sot.division
            , sot.generate_date
            , cp.name as create_by
            , sot.create_date as create_on
            , posp.name as post_by
            , sot.post_date as post_on
            , sot.state
            FROM teds_stock_opname_direct_gift sot
            INNER JOIN wtc_branch b ON b.id = sot.branch_id
            INNER JOIN res_users c ON c.id = sot.create_uid
            INNER JOIN res_partner cp ON cp.id = c.partner_id 
            LEFT JOIN res_users pos ON pos.id = sot.post_uid
            LEFT JOIN res_partner posp ON posp.id = pos.partner_id 
            %s
        """ % (query_where)

        self.env.cr.execute(query)
        ress = self.env.cr.dictfetchall() 

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Direct Gift')
        worksheet.set_column('B1:B1',6)
        worksheet.set_column('C1:C1',22)
        worksheet.set_column('D1:D1',22)
        worksheet.set_column('E1:E1',13)
        worksheet.set_column('F1:F1',13)
        worksheet.set_column('G1:G1',24)
        worksheet.set_column('H1:H1',24)
        worksheet.set_column('I1:I1',24)
        worksheet.set_column('J1:J1',24)
        worksheet.set_column('K1:K1',24)
        worksheet.set_column('L1:L1',12)
        worksheet.set_column('M1:M1',24)
        worksheet.set_column('N1:N1',24)



        
        date = datetime.now()
        date = date.strftime("%d-%m-%Y %H:%M:%S")

        filename = 'Laporan Stock Opname Direct Gift %s.xlsx'%str(date)
        worksheet.merge_range('A1:C1', 'Laporan Stock Opname Direct Gift', wbf['company'])        
        worksheet.merge_range('A2:C2', 'Periode %s %s Status %s'%(calendar.month_name[int(self.periode)],self.tahun,self.status), wbf['company'])

        row=2
        row +=1
        worksheet.write('A%s' %(row+1), 'No', wbf['header_no'])
        worksheet.write('B%s' %(row+1), 'Code', wbf['header_no'])
        worksheet.write('C%s' %(row+1), 'Cabang', wbf['header_no'])
        worksheet.write('D%s' %(row+1), 'No SO', wbf['header_no'])
        worksheet.write('E%s' %(row+1), 'Tgl SO', wbf['header_no'])
        worksheet.write('F%s' %(row+1), 'Division', wbf['header_no'])
        worksheet.write('G%s' %(row+1), 'Staff BBN', wbf['header_no'])
        worksheet.write('H%s' %(row+1), 'ADH', wbf['header_no'])
        worksheet.write('I%s' %(row+1), 'SOH', wbf['header_no'])
        worksheet.write('J%s' %(row+1), 'Generate on', wbf['header_no'])
        worksheet.write('K%s' %(row+1), 'Create by', wbf['header_no'])
        worksheet.write('L%s' %(row+1), 'State', wbf['header_no'])

        if self.status != 'Outstanding':
            worksheet.write('M%s' %(row+1), 'Posted on', wbf['header_no'])
            worksheet.write('N%s' %(row+1), 'Posted by', wbf['header_no'])

        row +=2
        
        no = 1
        row1 = row

        for res in ress:
            worksheet.write('A%s' % row, no , wbf['content_number'])  
            worksheet.write('B%s' % row, res.get('code') , wbf['content'])                    
            worksheet.write('C%s' % row, res.get('branch') , wbf['content'])
            worksheet.write('D%s' % row, res.get('no_so') , wbf['content'])
            worksheet.write('E%s' % row, res.get('tgl_so') , wbf['content'])
            worksheet.write('F%s' % row, res.get('division') , wbf['content'])
            worksheet.write('G%s' % row, res.get('staff_bbn') , wbf['content']) 
            worksheet.write('H%s' % row, res.get('adh') , wbf['content'])
            worksheet.write('I%s' % row, res.get('soh') , wbf['content'])
            worksheet.write('J%s' % row, res.get('generate_date') , wbf['content'])
            worksheet.write('K%s' % row, res.get('create_by') , wbf['content'])
            worksheet.write('L%s' % row, res.get('state') , wbf['content'])
            if self.status != 'Outstanding':
                worksheet.write('M%s' % row, res.get('post_on') , wbf['content'])
                worksheet.write('N%s' % row, res.get('post_by') , wbf['content'])

            no +=1
            row +=1                    
           
        
        if self.status != 'Outstanding':
            worksheet.autofilter('A4:N%s' % (row))
            worksheet.merge_range('A%s:N%s' % (row,row), '', wbf['total'])
        else:
            worksheet.autofilter('A4:L%s' % (row))
            worksheet.merge_range('A%s:L%s' % (row,row), '', wbf['total'])

        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write({'state_x':'get', 'data_x':out, 'name': filename})
        fp.close()

        form_id = self.env.ref('teds_stock_opname.view_teds_laporan_stock_opname_wizard').id
    
        return {
            'name': ('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.laporan.stock.opname.wizard',
            'res_id': self.ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }

    def laporan_so_detail_dg(self):
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Stock Opname Direct Gift')
        worksheet.set_column('A1:A1', 5)
        worksheet.set_column('B1:B1', 24)
        worksheet.set_column('C1:C1', 12)
        worksheet.set_column('D1:D1', 23)
        worksheet.set_column('E1:E1', 35)
        worksheet.set_column('F1:F1', 30)
        worksheet.set_column('G1:G1', 15)
        worksheet.set_column('H1:H1', 15)
        worksheet.set_column('I1:I1', 18)
        worksheet.set_column('J1:J1', 15)
        worksheet.set_column('K1:K1', 17)
        worksheet.set_column('L1:L1', 17)
        worksheet.set_column('M1:M1', 17)
        worksheet.set_column('N1:N1', 17)
        worksheet.set_column('O1:O1', 17)
        worksheet.set_column('P1:P1', 17)
        worksheet.set_column('Q1:Q1', 17)
        
        worksheet2 = workbook.add_worksheet('Stock Opname Direct Gift Other')
        worksheet2.set_column('A1:A1', 5)
        worksheet2.set_column('B1:B1', 24)
        worksheet2.set_column('C1:C1', 12)
        worksheet2.set_column('D1:D1', 23)
        worksheet2.set_column('E1:E1', 35)
        worksheet2.set_column('F1:F1', 30)
        worksheet2.set_column('G1:G1', 15)
        worksheet2.set_column('H1:H1', 15)
        worksheet2.set_column('I1:I1', 18)
        worksheet2.set_column('J1:J1', 15)
        worksheet2.set_column('K1:K1', 17)
        worksheet2.set_column('L1:L1', 17)
        worksheet2.set_column('M1:M1', 17)
        worksheet2.set_column('N1:N1', 17)
        worksheet2.set_column('O1:O1', 17)
        worksheet2.set_column('P1:P1', 17)
        worksheet2.set_column('Q1:Q1', 17)
        
        date = datetime.now()       
        date = date.strftime("%d-%m-%Y %H:%M:%S")

        filename = 'Laporan Stock Opname Direct Gift Detail %s.xlsx'%str(date)
        worksheet.merge_range('A1:C1', 'Stock Opname Direct Gift Detail', wbf['company'])   
        worksheet.merge_range('A2:C2', 'Periode %s - %s' %(calendar.month_name[int(self.periode)],self.tahun) , wbf['company'])  

        worksheet.write('A4', 'No' , wbf['header'])
        worksheet.write('B4', 'No Stock Opname' , wbf['header'])
        worksheet.write('C4', 'Code' , wbf['header'])
        worksheet.write('D4', 'Cabang' , wbf['header'])
        worksheet.write('E4', 'Product' , wbf['header'])
        worksheet.write('F4', 'Description' , wbf['header'])
        worksheet.write('G4', 'Harga Satuan' , wbf['header'])
        worksheet.write('H4', 'Qty Sistem' , wbf['header'])
        worksheet.write('I4', 'Amount Total Sistem' , wbf['header'])
        worksheet.write('J4', 'Qty Fisik Baik' , wbf['header'])
        worksheet.write('K4', 'Qty Fisik Rusak' , wbf['header'])
        worksheet.write('L4', 'Total Qty Fisik' , wbf['header'])
        worksheet.write('M4', 'Amount Total Fisik' , wbf['header'])
        worksheet.write('N4', 'Selisih Qty' , wbf['header'])
        worksheet.write('O4', 'Selisih Amount' , wbf['header'])
        worksheet.write('P4', 'Saldo Logbook' , wbf['header'])
        worksheet.write('Q4', 'Aging' , wbf['header'])
        

        row=5 
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

        query_where = " WHERE 1=1"
        if self.status == 'Outstanding':
            query_where += " AND sot.state = 'draft'"
        if self.status == 'Done':
            query_where += " AND sot.state = 'posted'"
        if self.branch_ids:
            branch_ids = [b.id for b in self.branch_ids]   
            query_where +=" AND sot.branch_id in %s" % str(tuple(branch_ids)).replace(',)', ')')
        if self.periode and self.tahun:
            query_where +=" AND to_char(sot.date,'MM') = '%s' AND to_char(sot.date,'YYYY') = '%s'" %(self.periode,self.tahun)

        query = """
            SELECT sot.name as no_so
            , b.code as branch_code
            , b.name as branch_name
            , pt.name as product
            , sotl.name as description
            , COALESCE(sotl.harga_satuan,0) as harga_satuan
            , sotl.qty
            , COALESCE(sotl.qty_fisik_baik,0) as qty_fisik_baik
            , COALESCE(sotl.qty_fisik_rusak,0) as qty_fisik_rusak
            , COALESCE(sotl.saldo_log_book,0) as saldo_log_book
            , sotl.aging
            FROM teds_stock_opname_direct_gift sot
            INNER JOIN teds_stock_opname_direct_gift_line sotl ON sotl.opname_id = sot.id
            INNER JOIN wtc_branch b ON b.id = sot.branch_id
            INNER JOIN product_product pp ON pp.id = sotl.product_id
            INNER JOIN product_template pt ON pt.id = pp.product_tmpl_id
            %s
        """ % (query_where)

        self.env.cr.execute(query)
        ress = self.env.cr.dictfetchall()
        for res in ress:
            qty = res.get('qty')
            qty_fisik_baik = res.get('qty_fisik_baik')
            qty_fisik_rusak = res.get('qty_fisik_rusak')
            harga_satuan = res.get('harga_satuan')
            amount = harga_satuan * qty 
            qty_fisik_total = qty_fisik_baik + qty_fisik_rusak
            amount_total = harga_satuan * qty_fisik_total
            selisih_qty = qty_fisik_total - qty
            selisih_amount = harga_satuan * selisih_qty

            worksheet.write('A%s' % row, no , wbf['content'])
            worksheet.write('B%s' % row, res.get('no_so') , wbf['content'])
            worksheet.write('C%s' % row, res.get('branch_code') , wbf['content'])
            worksheet.write('D%s' % row, res.get('branch_name') , wbf['content'])
            worksheet.write('E%s' % row, res.get('product') , wbf['content'])
            worksheet.write('F%s' % row, res.get('description') ,wbf['content'])
            worksheet.write('G%s' % row, harga_satuan , wbf['content_float'])
            worksheet.write('H%s' % row, qty , wbf['content_number'])
            worksheet.write('I%s' % row, amount , wbf['content_float'])
            worksheet.write('J%s' % row, qty_fisik_baik , wbf['content_number'])
            worksheet.write('K%s' % row, qty_fisik_rusak , wbf['content_number'])
            worksheet.write('L%s' % row, qty_fisik_total , wbf['content_number'])
            worksheet.write('M%s' % row, amount_total , wbf['content_float'])
            worksheet.write('N%s' % row, selisih_qty , wbf['content_float'])
            worksheet.write('O%s' % row, selisih_amount , wbf['content_float'])
            worksheet.write('P%s' % row, res.get('saldo_log_book') , wbf['content_number'])
            worksheet.write('Q%s' % row, res.get('aging') , wbf['content'])
            
            no+=1
            row+=1

            total_harga_satuan += harga_satuan
            total_qty += qty
            total_amount += amount
            total_qty_fisik_baik += qty_fisik_baik
            total_qty_fisik_rusak += qty_fisik_rusak
            total_qty_fisik += qty_fisik_total
            total_amount_total += amount_total
            total_selisih_qty += selisih_qty
            total_selisih_amount += selisih_amount
            total_saldo_logbook += res.get('saldo_log_book')

        worksheet.autofilter('A4:Q%s' % (row))  

        worksheet.merge_range('A%s:F%s' % (row,row), '', wbf['total'])
        formula_harga_satuan = '{=subtotal(9,G%s:G%s)}' % (row1, row-1) 
        formula_qty = '{=subtotal(9,H%s:H%s)}' % (row1, row-1) 
        formula_amount = '{=subtotal(9,I%s:I%s)}' % (row1, row-1) 
        formula_qty_fisik_baik = '{=subtotal(9,J%s:J%s)}' % (row1, row-1) 
        formula_qty_fisik_rusak = '{=subtotal(9,K%s:K%s)}' % (row1, row-1) 
        formula_qty_fisik = '{=subtotal(9,L%s:L%s)}' % (row1, row-1) 
        formula_amount_total = '{=subtotal(9,M%s:M%s)}' % (row1, row-1) 
        formula_selisih_qty = '{=subtotal(9,N%s:N%s)}' % (row1, row-1) 
        formula_selisih_amount = '{=subtotal(9,O%s:O%s)}' % (row1, row-1) 
        formula_logbook = '{=subtotal(9,P%s:P%s)}' % (row1, row-1) 

        worksheet.write_formula(row-1,6,formula_harga_satuan, wbf['total_float'], total_harga_satuan)
        worksheet.write_formula(row-1,7,formula_qty, wbf['total_float'], total_qty)
        worksheet.write_formula(row-1,8,formula_amount, wbf['total_float'], total_amount)
        worksheet.write_formula(row-1,9,formula_qty_fisik_baik, wbf['total_float'], total_qty_fisik_baik)
        worksheet.write_formula(row-1,10,formula_qty_fisik_rusak, wbf['total_float'], total_qty_fisik_rusak)
        worksheet.write_formula(row-1,11,formula_qty_fisik, wbf['total_float'], total_qty_fisik)
        worksheet.write_formula(row-1,12,formula_amount_total, wbf['total_float'], total_amount_total)
        worksheet.write_formula(row-1,13,formula_selisih_qty, wbf['total_float'], total_selisih_qty)
        worksheet.write_formula(row-1,14,formula_selisih_amount, wbf['total_float'], total_selisih_amount)
        worksheet.write_formula(row-1,15,formula_logbook, wbf['total_float'], total_saldo_logbook)
        
        worksheet.write('Q%s' %row,'', wbf['total'])
        
        # SHEET 2
        worksheet2.merge_range('A1:C1', 'Stock Opname Direct Gift Detail', wbf['company'])   
        worksheet2.merge_range('A2:C2', 'Periode %s - %s' %(calendar.month_name[int(self.periode)],self.tahun) , wbf['company'])  
        
        worksheet2.write('A4', 'No' , wbf['header'])
        worksheet2.write('B4', 'No Stock Opname' , wbf['header'])
        worksheet2.write('C4', 'Code' , wbf['header'])
        worksheet2.write('D4', 'Cabang' , wbf['header'])
        worksheet2.write('E4', 'Nama Barang' , wbf['header'])
        worksheet2.write('F4', 'Qty Fisik Baik' , wbf['header'])
        worksheet2.write('G4', 'Qty Fisik Rusak' , wbf['header'])
        worksheet2.write('H4', 'Total Qty Fisik' , wbf['header'])
        worksheet2.write('I4', 'Saldo Logbook' , wbf['header'])

        row2=5
        row3 = row2
        no2 = 1    
        other_total_qty_fisik_baik = 0
        other_total_qty_fisik_rusak = 0
        other_total_qty_fisik = 0
        other_total_saldo_logbook = 0

        query_other = """
            SELECT 
            sot.name as no_so
            , b.code as branch_code
            , b.name as branch_name
            , soto.nama_product
            , soto.qty_fisik_baik
            , soto.qty_fisik_rusak
            , soto.qty_fisik_baik + soto.qty_fisik_rusak as qty_fisik_total
            , COALESCE(soto.saldo_log_book,0) saldo_log_book
            FROM teds_stock_opname_direct_gift sot
            INNER JOIN teds_stock_opname_direct_gift_other soto ON soto.opname_id = sot.id
            INNER JOIN wtc_branch b ON b.id = sot.branch_id
            %s
            ORDER BY sot.name ASC
        """ % (query_where)
        self.env.cr.execute(query_other)
        ress = self.env.cr.dictfetchall() 
        for res in ress:
            worksheet2.write('A%s' % row2, no2 , wbf['content'])
            worksheet2.write('B%s' % row2, res.get('no_so') , wbf['content'])
            worksheet2.write('C%s' % row2, res.get('branch_code') , wbf['content'])
            worksheet2.write('D%s' % row2, res.get('branch_name') , wbf['content'])
            worksheet2.write('E%s' % row2, res.get('nama_product') , wbf['content'])
            worksheet2.write('F%s' % row2, res.get('qty_fisik_baik') ,wbf['content'])
            worksheet2.write('G%s' % row2, res.get('qty_fisik_rusak') , wbf['content_float'])
            worksheet2.write('H%s' % row2, res.get('qty_fisik_total') , wbf['content_number'])
            worksheet2.write('I%s' % row2, res.get('saldo_log_book') , wbf['content_number'])
            
            no2+=1
            row2+=1

            other_total_qty_fisik_baik += res.get('qty_fisik_baik')
            other_total_qty_fisik_rusak += res.get('qty_fisik_rusak')
            other_total_qty_fisik += res.get('qty_fisik_total')
            other_total_saldo_logbook += res.get('saldo_log_book')

        worksheet2.autofilter('A4:I%s' % (row2))  

        worksheet2.merge_range('A%s:E%s' % (row2,row2), '', wbf['total'])
        other_formula_qty_fisik_baik = '{=subtotal(9,F%s:F%s)}' % (row2, row3-1) 
        other_formula_qty_fisik_rusak = '{=subtotal(9,G%s:G%s)}' % (row2, row3-1) 
        other_formula_qty_fisik = '{=subtotal(9,H%s:H%s)}' % (row2, row3-1) 
        other_formula_logbook = '{=subtotal(9,I%s:I%s)}' % (row2, row3-1) 

        worksheet2.write_formula(row2-1,5,other_formula_qty_fisik_baik, wbf['total_float'], other_total_qty_fisik_baik)
        worksheet2.write_formula(row2-1,6,other_formula_qty_fisik_rusak, wbf['total_float'], other_total_qty_fisik_rusak)
        worksheet2.write_formula(row2-1,7,other_formula_qty_fisik, wbf['total_float'], other_total_qty_fisik)
        worksheet2.write_formula(row2-1,8,other_formula_logbook, wbf['total_float'], other_total_saldo_logbook)

        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write({'state_x':'get', 'data_x':out, 'name': filename})
        fp.close()

        form_id = self.env.ref('teds_stock_opname.view_teds_laporan_stock_opname_detail_wizard').id
        
        return {
            'name': ('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.laporan.stock.opname.wizard',
            'res_id': self.ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }