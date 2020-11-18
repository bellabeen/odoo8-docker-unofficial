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

    def laporan_so_asset(self):
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
            , sot.pdi
            , sot.adh
            , sot.soh
            , sot.date as tgl_so
            , sot.generate_date
            , cp.name as create_by
            , sot.create_date as create_on
            , posp.name as post_by
            , sot.post_date as post_on
            , sot.state
            FROM teds_stock_opname_asset sot
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
        worksheet = workbook.add_worksheet('Asset')
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

        filename = 'Laporan Stock Opname Asset %s.xlsx'%str(date)
        worksheet.merge_range('A1:C1', 'Laporan Stock Opname Asset', wbf['company'])        
        worksheet.merge_range('A2:C2', 'Periode %s %s'%(calendar.month_name[int(self.periode)],self.tahun), wbf['company'])
        worksheet.merge_range('A3:C3', 'Status %s'%(self.status), wbf['company'])

        row=4
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
            worksheet.write('F%s' % row, 'Administrasi' , wbf['content'])
            worksheet.write('G%s' % row, res.get('pdi') , wbf['content']) 
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
            worksheet.autofilter('A5:N%s' % (row))  
            worksheet.merge_range('A%s:N%s' % (row,row), '', wbf['total'])
        else:
            worksheet.autofilter('A5:L%s' % (row))  
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

    def laporan_so_detail_asset(self):
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Stock Opname Asset')
        worksheet.set_column('A1:A1', 5)
        worksheet.set_column('B1:B1', 24)
        worksheet.set_column('C1:C1', 14)
        worksheet.set_column('D1:D1', 24)
        worksheet.set_column('E1:E1', 23)
        worksheet.set_column('F1:F1', 30)
        worksheet.set_column('G1:G1', 10)
        worksheet.set_column('H1:H1', 35)
        worksheet.set_column('I1:I1', 20)
        worksheet.set_column('J1:J1', 20)
        worksheet.set_column('K1:K1', 20)
        worksheet.set_column('L1:L1', 20)
        worksheet.set_column('M1:M1', 30)
        
        worksheet2 = workbook.add_worksheet('Asset Tidak Tercatat')
        worksheet2.set_column('A1:A1', 5)
        worksheet2.set_column('B1:B1', 24)
        worksheet2.set_column('C1:C1', 14)
        worksheet2.set_column('D1:D1', 24)
        worksheet2.set_column('E1:E1', 20)
        worksheet2.set_column('F1:F1', 23)
        worksheet2.set_column('G1:G1', 28)
        worksheet2.set_column('H1:H1', 28)
        worksheet2.set_column('I1:I1', 25)
        worksheet2.set_column('J1:J1', 28)
        
        date = datetime.now()       
        date = date.strftime("%d-%m-%Y %H:%M:%S")

        filename = 'Laporan Stock Opname Asset Detail %s.xlsx'%str(date)
        worksheet.merge_range('A1:C1', 'Stock Opname Asset Detail', wbf['company'])   
        worksheet.merge_range('A2:C2', 'Periode %s - %s' %(calendar.month_name[int(self.periode)],self.tahun) , wbf['company'])  

        worksheet.write('A4', 'No' , wbf['header'])
        worksheet.write('B4', 'No Stock Opname' , wbf['header'])
        worksheet.write('C4', 'Code' , wbf['header'])
        worksheet.write('D4', 'Cabang' , wbf['header'])
        worksheet.write('E4', 'Kode Asset' , wbf['header'])
        worksheet.write('F4', 'Nama Asset' , wbf['header'])
        worksheet.write('G4', 'Kategory' , wbf['header'])
        worksheet.write('H4', 'Kategory Desc' , wbf['header'])
        worksheet.write('I4', 'Lokasi Fisik Asset' , wbf['header'])
        worksheet.write('J4', 'PIC Asset' , wbf['header'])
        worksheet.write('K4', 'Kondisi Fisik Asset' , wbf['header'])
        worksheet.write('L4', 'No Engine' , wbf['header'])
        worksheet.write('M4', 'Keterangan' , wbf['header'])
        
        
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
            , sotl.code as kode_asset
            , sotl.name as nama_asset
            , sotl.kategory
            , sotl.description
            , sotl.validasi_lokasi
            , sotl.validasi_pic
            , sotl.validasi_kondisi_fisik
            , sotl.no_mesin
            , sotl.keterangan
            FROM teds_stock_opname_asset sot
            INNER JOIN teds_stock_opname_asset_line sotl ON sotl.opname_id = sot.id
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
            worksheet.write('E%s' % row, res.get('kode_asset') , wbf['content'])
            worksheet.write('F%s' % row, res.get('nama_asset') ,wbf['content'])
            worksheet.write('G%s' % row, res.get('kategory') , wbf['content'])
            worksheet.write('H%s' % row, res.get('description') , wbf['content'])
            worksheet.write('I%s' % row, res.get('validasi_lokasi') , wbf['content'])
            worksheet.write('J%s' % row, res.get('validasi_pic') , wbf['content'])
            worksheet.write('K%s' % row, res.get('validasi_kondisi_fisik') , wbf['content'])
            worksheet.write('L%s' % row, res.get('no_mesin') , wbf['content'])
            worksheet.write('M%s' % row, res.get('keterangan') , wbf['content'])
             
            no+=1
            row+=1

        worksheet.autofilter('A4:M%s' % (row))  
        worksheet.merge_range('A%s:M%s' % (row,row), '', wbf['total'])

        # Sheet 2
        worksheet2.merge_range('A1:C1', 'Stock Opname Asset Detail', wbf['company'])   
        worksheet2.merge_range('A2:C2', 'Periode %s - %s' %(calendar.month_name[int(self.periode)],self.tahun) , wbf['company'])  

        worksheet2.write('A4', 'No' , wbf['header'])
        worksheet2.write('B4', 'No Stock Opname' , wbf['header'])
        worksheet2.write('C4', 'Code' , wbf['header'])
        worksheet2.write('D4', 'Cabang' , wbf['header'])
        worksheet2.write('E4', 'Nama Asset' , wbf['header'])
        worksheet2.write('F4', 'Lokasi Fisik Unit' , wbf['header'])
        worksheet2.write('G4', 'PIC Asset' , wbf['header'])
        worksheet2.write('H4', 'Kondisi Fisik Asset' , wbf['header'])
        worksheet2.write('I4', 'No Mesin' , wbf['header'])
        worksheet2.write('J4', 'Keterangan' , wbf['header'])

        row2 = 5
        no2 = 1
        query_other = """
            SELECT 
            sot.name as no_so
            , b.code as branch_code
            , b.name as branch_name
            , soto.name
            , soto.lokasi_fisik_unit
            , soto.pic
            , soto.kondisi_fisik
            , soto.no_mesin
            , soto.keterangan
            FROM teds_stock_opname_asset sot
            INNER JOIN teds_stock_opname_asset_other soto ON soto.opname_id = sot.id
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
            worksheet2.write('E%s' % row2, res.get('name') , wbf['content'])
            worksheet2.write('F%s' % row2, res.get('lokasi_fisik_unit') ,wbf['content'])
            worksheet2.write('G%s' % row2, res.get('pic') , wbf['content'])
            worksheet2.write('H%s' % row2, res.get('kondisi_fisik') , wbf['content'])
            worksheet2.write('I%s' % row2, res.get('no_mesin') , wbf['content'])
            worksheet2.write('J%s' % row2, res.get('keterangan') , wbf['content'])
            
            no2 += 1
            row2 += 1

        worksheet2.autofilter('A4:J%s' % (row2))  
        worksheet2.merge_range('A%s:J%s' % (row2,row2), '', wbf['total'])
        

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