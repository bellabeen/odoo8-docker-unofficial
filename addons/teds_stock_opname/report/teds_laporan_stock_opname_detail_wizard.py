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
    
    # Laporan SO Detail
    @api.multi
    def excel_report_detail(self):
        if self.options == 'STNK':
            return self.laporan_so_detail_stnk()
        elif self.options == 'BPKB':
            return self.laporan_so_detail_bpkb()
        elif self.options == 'Direct Gift':
            return self.laporan_so_detail_dg()
        elif self.options == 'Unit':
            return self.laporan_so_detail_unit()
        elif self.options == 'Asset':
            return self.laporan_so_detail_asset()
        else:
            raise Warning("Options tidak dikenal !")

    def laporan_so_detail_stnk(self):
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Stock Opname STNK')
        worksheet.set_column('A1:A1', 5)
        worksheet.set_column('B1:B1', 20)
        worksheet.set_column('C1:C1', 10)
        worksheet.set_column('D1:D1', 20)
        worksheet.set_column('E1:E1', 28)
        worksheet.set_column('F1:F1', 20)
        worksheet.set_column('G1:G1', 20)
        worksheet.set_column('H1:H1', 20)
        worksheet.set_column('I1:I1', 25)
        worksheet.set_column('J1:J1', 28)
        worksheet.set_column('K1:K1', 17)
        worksheet.set_column('L1:L1', 28)
        worksheet.set_column('M1:M1', 22)
        worksheet.set_column('N1:N1', 22)
        worksheet.set_column('O1:O1', 25)

        worksheet2 = workbook.add_worksheet('Stock Opname STNK Other')
        worksheet2.set_column('A1:A1', 5)
        worksheet2.set_column('B1:B1', 20)
        worksheet2.set_column('C1:C1', 10)
        worksheet2.set_column('D1:D1', 20)
        worksheet2.set_column('E1:E1', 30)
        worksheet2.set_column('F1:F1', 18)
        worksheet2.set_column('G1:G1', 20)
        
        date = datetime.now()
        date = date.strftime("%d-%m-%Y %H:%M:%S")

        filename = 'Laporan Stock Opname STNK Detail %s.xlsx'%str(date)
        worksheet.merge_range('A1:C1', 'Stock Opname STNK Detail', wbf['company'])   
        worksheet.merge_range('A2:C2', 'Periode %s - %s' %(calendar.month_name[int(self.periode)],self.tahun) , wbf['company'])  

        worksheet.write('A4', 'No' , wbf['header'])
        worksheet.write('B4', 'No Stock Opname' , wbf['header'])
        worksheet.write('C4', 'Branch Code' , wbf['header'])
        worksheet.write('D4', 'Branch Name' , wbf['header'])
        worksheet.write('E4', 'Nama STNK' , wbf['header'])
        worksheet.write('F4', 'Validasi Nama STNK' , wbf['header'])
        worksheet.write('G4', 'Tanggal Penerimaan' , wbf['header'])
        worksheet.write('H4', 'Lokasi STNK' , wbf['header'])
        worksheet.write('I4', 'No Engine' , wbf['header'])
        worksheet.write('J4', 'Validasi No Engine' , wbf['header'])
        worksheet.write('K4', 'No Polisi' , wbf['header'])
        worksheet.write('L4', 'Validasi No Polisi' , wbf['header'])
        worksheet.write('M4', 'Ceklis Fisik STNK' , wbf['header'])
        worksheet.write('N4', 'Keterangan' , wbf['header'])
        worksheet.write('O4', 'Umur' , wbf['header'])
        
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
            , stnk.name as nama_stnk
            , sotl.validasi_nama_stnk
            , sotl.tgl_penerimaan
            , sotl.lokasi_stnk
            , lot.name as no_mesin
            , sotl.validasi_no_engine
            , sotl.no_polisi
            , sotl.validasi_no_polisi
            , sotl.validasi_ceklis_fisik_stnk
            , sotl.keterangan
            , sotl.umur
            FROM teds_stock_opname_stnk sot
            INNER JOIN teds_stock_opname_stnk_line sotl ON sotl.opname_id = sot.id
            INNER JOIN wtc_branch b ON b.id = sot.branch_id
            INNER JOIN res_partner stnk ON stnk.id = sotl.customer_stnk_id
            INNER JOIN stock_production_lot lot ON lot.id = sotl.lot_id
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
            worksheet.write('E%s' % row, res.get('nama_stnk') , wbf['content'])
            worksheet.write('F%s' % row, res.get('validasi_nama_stnk') ,wbf['content'])
            worksheet.write('G%s' % row, res.get('tgl_penerimaan') , wbf['content'])
            worksheet.write('H%s' % row, res.get('lokasi_stnk') , wbf['content'])
            worksheet.write('I%s' % row, res.get('no_mesin') , wbf['content'])
            worksheet.write('J%s' % row, res.get('validasi_no_engine') , wbf['content'])
            worksheet.write('K%s' % row, res.get('no_polisi') , wbf['content'])
            worksheet.write('L%s' % row, res.get('validasi_no_polisi') , wbf['content'])
            worksheet.write('M%s' % row, res.get('validasi_ceklis_fisik_stnk') , wbf['content'])
            worksheet.write('N%s' % row, res.get('keterangan') , wbf['content'])
            worksheet.write('O%s' % row, res.get('umur') , wbf['content'])

            no+=1
            row+=1

        worksheet.autofilter('A4:O%s' % (row))
        worksheet.merge_range('A%s:O%s' % (row,row), '', wbf['total']) 

        # SHEET 2
        worksheet2.merge_range('A1:C1', 'Stock Opname STNK Detail', wbf['company'])   
        worksheet2.merge_range('A2:C2', 'Periode %s - %s' %(calendar.month_name[int(self.periode)],self.tahun) , wbf['company'])  

        worksheet2.write('A4', 'No' , wbf['header'])
        worksheet2.write('B4', 'No Stock Opname' , wbf['header'])
        worksheet2.write('C4', 'Branch Code' , wbf['header'])
        worksheet2.write('D4', 'Branch Name' , wbf['header'])
        worksheet2.write('E4', 'Nama STNK' , wbf['header'])
        worksheet2.write('F4', 'No Engine' , wbf['header'])
        worksheet2.write('G4', 'Keterangan' , wbf['header'])

        row2=5
        no2 = 1    
        
        query_other = """
            SELECT 
            sot.name as no_so
            , b.code as branch_code
            , b.name as branch_name
            , soto.nama_stnk
            , soto.no_engine
            , soto.keterangan
            FROM teds_stock_opname_stnk sot
            INNER JOIN teds_stock_opname_stnk_other soto ON soto.opname_id = sot.id
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
            worksheet2.write('E%s' % row2, res.get('nama_stnk') , wbf['content'])
            worksheet2.write('F%s' % row2, res.get('no_engine') , wbf['content'])
            worksheet2.write('G%s' % row2, res.get('keterangan'), wbf['content'])
            
            no2+=1
            row2+=1
        worksheet2.autofilter('A4:G%s' % (row2))
        worksheet2.merge_range('A%s:G%s' % (row2,row2), '', wbf['total'])

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

    def laporan_so_detail_bpkb(self):
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Stock Opname BPKB')
        worksheet.set_column('A1:A1', 5)
        worksheet.set_column('B1:B1', 20)
        worksheet.set_column('C1:C1', 10)
        worksheet.set_column('D1:D1', 20)
        worksheet.set_column('E1:E1', 23)
        worksheet.set_column('F1:F1', 28)
        worksheet.set_column('G1:G1', 17)
        worksheet.set_column('H1:H1', 15)
        worksheet.set_column('I1:I1', 15)
        worksheet.set_column('J1:J1', 28)
        worksheet.set_column('K1:K1', 15)
        worksheet.set_column('L1:L1', 28)
        worksheet.set_column('M1:M1', 35)
        worksheet.set_column('N1:N1', 25)
        worksheet.set_column('O1:O1', 25)
        worksheet.set_column('P:P1', 20)
        worksheet.set_column('Q1:Q1', 15)

        worksheet2 = workbook.add_worksheet('Stock Opname BPKB Other')
        worksheet2.set_column('A1:A1', 5)
        worksheet2.set_column('B1:B1', 20)
        worksheet2.set_column('C1:C1', 10)
        worksheet2.set_column('D1:D1', 20)
        worksheet2.set_column('E1:E1', 23)
        worksheet2.set_column('F1:F1', 28)
        worksheet2.set_column('G1:G1', 17)
        worksheet2.set_column('H1:H1', 15)
        worksheet2.set_column('I1:I1', 15)
        worksheet2.set_column('J1:J1', 28)
        worksheet2.set_column('K1:K1', 15)
        worksheet2.set_column('L1:L1', 28)
        worksheet2.set_column('M1:M1', 20)
        worksheet2.set_column('N1:N1', 20)
        worksheet2.set_column('O1:O1', 20)
        
        date = datetime.now()
        date = date.strftime("%d-%m-%Y %H:%M:%S")

        filename = 'Laporan Stock Opname BPKB Detail %s.xlsx'%str(date)
        worksheet.merge_range('A1:C1', 'Stock Opname BPKB Detail', wbf['company'])   
        worksheet.merge_range('A2:C2', 'Periode %s - %s' %(calendar.month_name[int(self.periode)],self.tahun) , wbf['company'])   
        
        worksheet.write('A4', 'No' , wbf['header'])
        worksheet.write('B4', 'No Stock Opname' , wbf['header'])
        worksheet.write('C4', 'Branch Code' , wbf['header'])
        worksheet.write('D4', 'Branch Name' , wbf['header'])
        worksheet.write('E4', 'Nama BPKB' , wbf['header'])
        worksheet.write('F4', 'Validasi Nama BPKB' , wbf['header'])
        worksheet.write('G4', 'Tanggal Penerimaan' , wbf['header'])
        worksheet.write('H4', 'Lokasi BPKB' , wbf['header'])
        worksheet.write('I4', 'No Engine' , wbf['header'])
        worksheet.write('J4', 'Validasi No Engine' , wbf['header'])
        worksheet.write('K4', 'No BPKB' , wbf['header'])
        worksheet.write('L4', 'Validasi No BPKB' , wbf['header'])
        worksheet.write('M4', 'Ceklis Fisik BPKB' , wbf['header'])
        worksheet.write('N4', 'Finance Company' , wbf['header'])
        worksheet.write('O4', 'Keterangan' , wbf['header'])
        worksheet.write('P4', 'Umur' , wbf['header'])
        worksheet.write('Q4', 'Over Due' , wbf['header'])


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
            , stnk.name as nama_stnk
            , sotl.validasi_nama_bpkb
            , sotl.tgl_penerimaan
            , sotl.lokasi_bpkb
            , lot.name as no_mesin
            , sotl.validasi_no_engine
            , sotl.no_bpkb
            , sotl.validasi_no_bpkb
            , sotl.validasi_ceklis_fisik_bpkb
            , finco.name as finco
            , sotl.keterangan
            , sotl.umur
            , sotl.over_due
            FROM teds_stock_opname_bpkb sot
            INNER JOIN teds_stock_opname_bpkb_line sotl ON sotl.opname_id = sot.id
            INNER JOIN wtc_branch b ON b.id = sot.branch_id
            INNER JOIN res_partner stnk ON stnk.id = sotl.customer_bpkb_id
            LEFT JOIN res_partner finco ON stnk.id = sotl.finco_id
            INNER JOIN stock_production_lot lot ON lot.id = sotl.lot_id
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
            worksheet.write('E%s' % row, res.get('nama_stnk') , wbf['content'])
            worksheet.write('F%s' % row, res.get('validasi_nama_bpkb') ,wbf['content'])
            worksheet.write('G%s' % row, res.get('tgl_penerimaan') , wbf['content'])
            worksheet.write('H%s' % row, res.get('lokasi_bpkb') , wbf['content'])
            worksheet.write('I%s' % row, res.get('no_mesin') , wbf['content'])
            worksheet.write('J%s' % row, res.get('validasi_no_engine') , wbf['content'])
            worksheet.write('K%s' % row, res.get('no_bpkb') , wbf['content'])
            worksheet.write('L%s' % row, res.get('validasi_no_bpkb') , wbf['content'])
            worksheet.write('M%s' % row, res.get('validasi_ceklis_fisik_bpkb') , wbf['content'])
            worksheet.write('N%s' % row, res.get('finco') , wbf['content'])
            worksheet.write('O%s' % row, res.get('keterangan') , wbf['content'])
            worksheet.write('P%s' % row, res.get('umur') , wbf['content'])
            worksheet.write('Q%s' % row, res.get('over_due') , wbf['content'])
            no+=1
            row+=1

        worksheet.autofilter('A4:Q%s' % (row))  
        worksheet.merge_range('A%s:Q%s' % (row,row), '', wbf['total'])

        # SHEET 2
        worksheet2.merge_range('A1:C1', 'Stock Opname BPKB Detail', wbf['company'])   
        worksheet2.merge_range('A2:C2', 'Periode %s - %s' %(calendar.month_name[int(self.periode)],self.tahun) , wbf['company'])

        worksheet2.write('A4', 'No' , wbf['header'])
        worksheet2.write('B4', 'No Stock Opname' , wbf['header'])
        worksheet2.write('C4', 'Branch Code' , wbf['header'])
        worksheet2.write('D4', 'Branch Name' , wbf['header'])
        worksheet2.write('E4', 'Nama BPKB' , wbf['header'])
        worksheet2.write('F4', 'No Engine' , wbf['header'])
        worksheet2.write('G4', 'Keterangan' , wbf['header'])

        row2=5
        no2 = 1     

        query_other = """
            SELECT 
            sot.name as no_so
            , b.code as branch_code
            , b.name as branch_name
            , soto.nama_bpkb
            , soto.no_engine
            , soto.keterangan
            FROM teds_stock_opname_bpkb sot
            INNER JOIN teds_stock_opname_bpkb_other soto ON soto.opname_id = sot.id
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
            worksheet2.write('E%s' % row2, res.get('nama_bpkb') , wbf['content'])
            worksheet2.write('F%s' % row2, res.get('no_engine') , wbf['content'])
            worksheet2.write('G%s' % row2, res.get('keterangan'), wbf['content'])
            
            no2+=1
            row2+=1
        worksheet2.autofilter('A4:G%s' % (row2))
        worksheet2.merge_range('A%s:G%s' % (row2,row2), '', wbf['total'])

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


    def laporan_so_detail_dg(self):
        return True
    def laporan_so_detail_unit(self):
        return True
    def laporan_so_detail_asset(self):
        return True