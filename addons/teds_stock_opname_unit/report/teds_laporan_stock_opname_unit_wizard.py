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

    def laporan_so_unit(self):
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
            FROM teds_stock_opname_unit sot
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
        worksheet = workbook.add_worksheet('Unit')
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

        filename = 'Laporan Stock Opname Unit %s.xlsx'%str(date)
        worksheet.merge_range('A1:C1', 'Laporan Stock Opname Unit', wbf['company'])        
        worksheet.merge_range('A2:C2', 'Periode %s %s Status %s'%(calendar.month_name[int(self.periode)],self.tahun,self.status), wbf['company'])

        row=2
        row +=1
        worksheet.write('A%s' %(row+1), 'No', wbf['header_no'])
        worksheet.write('B%s' %(row+1), 'Code', wbf['header_no'])
        worksheet.write('C%s' %(row+1), 'Cabang', wbf['header_no'])
        worksheet.write('D%s' %(row+1), 'No SO', wbf['header_no'])
        worksheet.write('E%s' %(row+1), 'Tgl SO', wbf['header_no'])
        worksheet.write('F%s' %(row+1), 'Division', wbf['header_no'])
        worksheet.write('G%s' %(row+1), 'PDI', wbf['header_no'])
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

    def laporan_so_detail_unit(self):
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Stock Opname Unit')
        worksheet.set_column('A1:A1', 5)
        worksheet.set_column('B1:B1', 24)
        worksheet.set_column('C1:C1', 10)
        worksheet.set_column('D1:D1', 23)
        worksheet.set_column('E1:E1', 40)
        worksheet.set_column('F1:F1', 20)
        worksheet.set_column('G1:G1', 20)
        worksheet.set_column('H1:H1', 20)
        worksheet.set_column('I1:I1', 23)
        worksheet.set_column('J1:J1', 15)
        worksheet.set_column('K1:K1', 15)
        worksheet.set_column('L1:L1', 18)
        worksheet.set_column('M1:M1', 20)
        worksheet.set_column('N1:N1', 18)
        worksheet.set_column('O1:O1', 24)
        worksheet.set_column('P1:P1', 55)
        worksheet.set_column('Q1:Q1', 20)
        worksheet.set_column('R1:R1', 25)
        
        worksheet2 = workbook.add_worksheet('Stock Opname Accesories')
        worksheet2.set_column('A1:A1', 5)
        worksheet2.set_column('B1:B1', 24)
        worksheet2.set_column('C1:C1', 10)
        worksheet2.set_column('D1:D1', 23)
        worksheet2.set_column('E1:E1', 25)
        worksheet2.set_column('F1:F1', 20)
        worksheet2.set_column('G1:G1', 10)
        worksheet2.set_column('H1:H1', 12)
        worksheet2.set_column('I1:I1', 12)
        worksheet2.set_column('J1:J1', 12)
        worksheet2.set_column('K1:K1', 25)
        worksheet2.set_column('L1:L1', 17)
        worksheet2.set_column('M1:M1', 10)
        worksheet2.set_column('N1:N1', 25)
        worksheet2.set_column('O1:O1', 15)
        
        date = datetime.now()       
        date = date.strftime("%d-%m-%Y %H:%M:%S")

        filename = 'Laporan Stock Opname Unit Detail %s.xlsx'%str(date)
        worksheet.merge_range('A1:C1', 'Stock Opname Unit Detail', wbf['company'])   
        worksheet.merge_range('A2:C2', 'Periode %s - %s' %(calendar.month_name[int(self.periode)],self.tahun) , wbf['company'])   
        
        worksheet.write('A4', 'No' , wbf['header'])
        worksheet.write('B4', 'No Stock Opname' , wbf['header'])
        worksheet.write('C4', 'Code' , wbf['header'])
        worksheet.write('D4', 'Cabang' , wbf['header'])
        worksheet.write('E4', 'Product' , wbf['header'])
        worksheet.write('F4', 'Engine No' , wbf['header'])
        worksheet.write('G4', 'Chassis No' , wbf['header'])
        worksheet.write('H4', 'Validasi Fisik' , wbf['header'])
        worksheet.write('I4', 'Validasi Engine' , wbf['header'])
        worksheet.write('J4', 'Validasi Chassis' , wbf['header'])
        worksheet.write('K4', 'Product Type' , wbf['header'])
        worksheet.write('L4', 'Warna' , wbf['header'])
        worksheet.write('M4', 'Validasi Warna' , wbf['header'])
        worksheet.write('N4', 'Incoming Date' , wbf['header'])
        worksheet.write('O4', 'Validasi Taging' , wbf['header'])
        worksheet.write('P4', 'Location' , wbf['header'])
        worksheet.write('Q4', 'Kondisi Fisik' , wbf['header'])
        worksheet.write('R4', 'Keterangan' , wbf['header'])
        
        row=5
        no = 1    

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
            sot.name as no_so
            , b.code as branch_code
            , b.name as branch_name
            , sotl.name
            , sotl.engine_no
            , sotl.chassis_no
            , sotl.validasi_fisik
            , sotl.validasi_engine
            , sotl.validasi_chassis
            , sotl.product_type
            , sotl.product_warna
            , sotl.validasi_warna
            , sotl.incoming_date
            , sotl.validasi_taging
            , sotl.lokasi
            , sotl.kondisi_fisik
            , sotl.keterangan
            FROM teds_stock_opname_unit sot
            INNER JOIN teds_stock_opname_unit_line sotl ON sotl.opname_id = sot.id
            INNER JOIN wtc_branch b ON b.id = sot.branch_id
            %s
            ORDER BY sot.name ASC
        """ % (query_where)
        self.env.cr.execute(query)
        ress = self.env.cr.dictfetchall() 
        for res in ress:
            worksheet.write('A%s' % row, no , wbf['content'])
            worksheet.write('B%s' % row, res.get('no_so') , wbf['content'])
            worksheet.write('C%s' % row, res.get('branch_code') , wbf['content'])
            worksheet.write('D%s' % row, res.get('branch_name') , wbf['content'])
            worksheet.write('E%s' % row, res.get('name') , wbf['content'])
            worksheet.write('F%s' % row, res.get('engine_no') ,wbf['content'])
            worksheet.write('G%s' % row, res.get('chassis_no') , wbf['content'])
            worksheet.write('H%s' % row, res.get('validasi_fisik') , wbf['content'])
            worksheet.write('I%s' % row, res.get('validasi_engine') , wbf['content'])
            worksheet.write('J%s' % row, res.get('validasi_chassis') , wbf['content'])
            worksheet.write('K%s' % row, res.get('product_type') , wbf['content'])
            worksheet.write('L%s' % row, res.get('product_warna') , wbf['content'])
            worksheet.write('M%s' % row, res.get('validasi_warna') , wbf['content'])
            worksheet.write('N%s' % row, res.get('incoming_date') , wbf['content'])
            worksheet.write('O%s' % row, res.get('validasi_taging') , wbf['content'])
            worksheet.write('P%s' % row, res.get('lokasi') , wbf['content'])
            worksheet.write('Q%s' % row, res.get('kondisi_fisik') , wbf['content'])
            worksheet.write('R%s' % row, res.get('keterangan'), wbf['content'])

            
            no+=1
            row+=1

        worksheet.autofilter('A4:R%s' % (row))  
        worksheet.merge_range('A%s:R%s' % (row,row), '', wbf['total'])

        # Aksesoris
        worksheet.merge_range('A1:C1', 'Stock Opname Unit Detail', wbf['company'])   
        worksheet.merge_range('A2:C2', 'Periode %s - %s' %(calendar.month_name[int(self.periode)],self.tahun) , wbf['company'])   

        worksheet2.write('A4', 'No' , wbf['header'])
        worksheet2.write('B4', 'No Stock Opname' , wbf['header'])
        worksheet2.write('C4', 'Code' , wbf['header'])
        worksheet2.write('D4', 'Cabang' , wbf['header'])
        worksheet2.write('E4', 'Product' , wbf['header'])
        worksheet2.write('F4', 'Category' , wbf['header'])
        worksheet2.write('G4', 'Good' , wbf['header'])
        worksheet2.write('H4', 'Not Good' , wbf['header'])
        worksheet2.write('I4', 'Total Fisik' , wbf['header'])
        worksheet2.write('J4', 'Total Unit' , wbf['header'])
        worksheet2.write('K4', 'Ket Not Good' , wbf['header'])
        worksheet2.write('L4', '(+/- NG dr SO lalu)' , wbf['header'])
        worksheet2.write('M4', 'Selisih' , wbf['header'])
        worksheet2.write('N4', 'Ket Selisih' , wbf['header'])
        worksheet2.write('O4', 'Selisih SO Lalu' , wbf['header'])
        

        row_s =5
        no2 = 1    

        query_other = """
            SELECT 
            sot.name as no_so
            , b.code as branch_code
            , b.name as branch_name
            , soto.name
            , soto.category
            , soto.qty_good
            , soto.qty_not_good
            , soto.qty_good + soto.qty_not_good as total
            , soto.total_unit
            , soto.ket_not_good
            , soto.last_not_good
            , soto.total_unit - (soto.qty_good + soto.qty_not_good)  as selisih
            , soto.keterangan_selisih
            , soto.selisih_so_lalu
            FROM teds_stock_opname_unit sot
            INNER JOIN teds_stock_opname_aksesoris_unit soto ON soto.opname_id = sot.id
            INNER JOIN wtc_branch b ON b.id = sot.branch_id
            %s
            ORDER BY sot.name ASC
        """ % (query_where)
        self.env.cr.execute(query_other)
        ress = self.env.cr.dictfetchall() 
        for res in ress:
            worksheet2.write('A%s' % row_s, no2 , wbf['content'])
            worksheet2.write('B%s' % row_s, res.get('no_so') , wbf['content'])
            worksheet2.write('C%s' % row_s, res.get('branch_code') , wbf['content'])
            worksheet2.write('D%s' % row_s, res.get('branch_name') , wbf['content'])
            worksheet2.write('E%s' % row_s, res.get('name') , wbf['content'])
            worksheet2.write('F%s' % row_s, res.get('category') ,wbf['content'])
            worksheet2.write('G%s' % row_s, res.get('qty_good') , wbf['content'])
            worksheet2.write('H%s' % row_s, res.get('qty_not_good') , wbf['content'])
            worksheet2.write('I%s' % row_s, res.get('total') , wbf['content'])
            worksheet2.write('J%s' % row_s, res.get('total_unit') , wbf['content'])
            worksheet2.write('K%s' % row_s, res.get('ket_not_good')  , wbf['content'])
            worksheet2.write('L%s' % row_s, res.get('last_not_good') , wbf['content'])
            worksheet2.write('M%s' % row_s, res.get('selisih') , wbf['content'])
            worksheet2.write('N%s' % row_s, res.get('keterangan_selisih') , wbf['content'])
            worksheet2.write('O%s' % row_s, res.get('selisih_so_lalu') , wbf['content'])
            
            no2 +=1
            row_s +=1

        worksheet2.autofilter('A4:O%s' % (row_s))  
        worksheet2.merge_range('A%s:O%s' % (row_s,row_s), '', wbf['total'])
        
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
