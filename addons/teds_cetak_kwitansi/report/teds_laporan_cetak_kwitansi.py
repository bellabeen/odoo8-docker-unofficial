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

class LaporanListingCetakKwitansiWizard(models.TransientModel):
    _name = "teds.laporan.listing.cetak.kwitansi.wizard"

    wbf = {}

    def _get_default_branch(self):
        branch_ids = False
        branch_ids = self.env.user.branch_ids
        if branch_ids and len(branch_ids) == 1 :
            return [branch_ids[0]]
        return False

    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()

    name = fields.Char('Filename')
    state_x = fields.Selection([('choose','choose'),('get','get')], default='choose')
    data_x = fields.Binary('File', readonly=True)
    branch_ids = fields.Many2many('wtc.branch', 'teds_listing_cetak_kwitansi_report_branch_rel', 'kwitansi_id', 'branch_id')
    start_date = fields.Date('Start Date',default=_get_default_date)
    end_date = fields.Date('End Date',default=_get_default_date)

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

        self.wbf['content_number'] = workbook.add_format({'align': 'center'})
        self.wbf['content_number'].set_right() 
        self.wbf['content_number'].set_left() 
        
        
        self.wbf['content_float'] = workbook.add_format({'align': 'right','num_format': '#,##0.00'})
        self.wbf['content_float'].set_right() 
        self.wbf['content_float'].set_left()
        
        self.wbf['total'] = workbook.add_format({'bg_color': '#FFFFDB'})
        self.wbf['total'].set_right() 
        self.wbf['total'].set_left()
        self.wbf['total'].set_top()
        self.wbf['total'].set_bottom()

        return workbook

    @api.multi
    def excel_report(self):
        query_where = " WHERE lck.state != 'draft'"
        if self.start_date:
            query_where += " AND lck.date >= '%s'" %str(self.start_date)
        if self.end_date:
            query_where += " AND lck.date <= '%s'" %str(self.end_date)
        if self.branch_ids:
            branch = [b.id for b in self.branch_ids]
            query_where += " AND lck.branch_id in %s" % str(tuple(branch)).replace(',)', ')')

        query = """
            SELECT lck.name as no_kwitansi
            , lck.date as tanggal_kwitansi
            , b.code as kode_cabang
            , b.name as nama_cabang
            , lck.nama_pembayar
            , lck.redaksi
            , lck.total as jumlah
            , j.name as no_rekening
            , lck.nama_rekening
            , lck.no_faktur_pajak
            , lck.no_refrence
            , lck.no_bukti_pembayaran
            , lck.tgl_pembayaran
            , lck.jenis_transaksi
            , lck.state
            FROM teds_listing_cetak_kwitansi lck
            INNER JOIN wtc_branch b ON b.id = lck.branch_id
            INNER JOIN account_journal j ON j.id = lck.journal_id 
            %s
            ORDER BY lck.name ASC
        """ %(query_where)
        self.env.cr.execute(query)
        ress = self.env.cr.dictfetchall() 

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Listing Kwitansi')
        worksheet.set_column('B1:B1',18)
        worksheet.set_column('C1:C1',17)
        worksheet.set_column('D1:D1',12)
        worksheet.set_column('E1:E1',18)
        worksheet.set_column('F1:F1',25)
        worksheet.set_column('G1:G1',28)
        worksheet.set_column('H1:H1',18)
        worksheet.set_column('I1:I1',25)
        worksheet.set_column('J1:J1',22)
        worksheet.set_column('K1:K1',22)
        worksheet.set_column('L1:L1',22)
        worksheet.set_column('M1:M1',22)
        worksheet.set_column('N1:N1',22)
        worksheet.set_column('O1:O1',22)
        worksheet.set_column('P1:P1',20)

        date = datetime.now()
        date = date.strftime("%d-%m-%Y %H:%M:%S")

        filename = 'Laporan Listing Cetak Kwitansi %s.xlsx'%str(date)
        worksheet.merge_range('A1:C1', 'Laporan Listing Kwitansi', wbf['company'])
        worksheet.merge_range('A2:C2', 'Periode %s - %s'%(self.start_date,self.end_date), wbf['company'])

        row=2
        row +=1
        worksheet.write('A%s' %(row+1), 'No', wbf['header_no'])
        worksheet.write('B%s' %(row+1), 'No Kwitansi', wbf['header'])
        worksheet.write('C%s' %(row+1), 'Tanggal Kwitansi', wbf['header'])
        worksheet.write('D%s' %(row+1), 'Kode Cabang', wbf['header'])
        worksheet.write('E%s' %(row+1), 'Nama Cabang', wbf['header'])
        worksheet.write('F%s' %(row+1), 'Nama Pembayar', wbf['header'])
        worksheet.write('G%s' %(row+1), 'Redaksi Kwitansi', wbf['header'])
        worksheet.write('H%s' %(row+1), 'Jumlah Pembayaran', wbf['header'])
        worksheet.write('I%s' %(row+1), 'No Rekening', wbf['header'])
        worksheet.write('J%s' %(row+1), 'Nama Rekening', wbf['header'])
        worksheet.write('K%s' %(row+1), 'No Faktur Pajak', wbf['header'])
        worksheet.write('L%s' %(row+1), 'No Refrence', wbf['header'])
        worksheet.write('M%s' %(row+1), 'Jenis Transaksi', wbf['header'])
        worksheet.write('N%s' %(row+1), 'No Bukti Pembayaran', wbf['header'])
        worksheet.write('O%s' %(row+1), 'Tanggal Pembayaran', wbf['header'])
        worksheet.write('P%s' %(row+1), 'State', wbf['header'])

        row +=2
        
        no = 1
        row1 = row

        for res in ress:
            worksheet.write('A%s' % row, no , wbf['content_number'])  
            worksheet.write('B%s' % row, res.get('no_kwitansi') , wbf['content'])                    
            worksheet.write('C%s' % row, res.get('tanggal_kwitansi') , wbf['content'])
            worksheet.write('D%s' % row, res.get('kode_cabang') , wbf['content'])
            worksheet.write('E%s' % row, res.get('nama_cabang') , wbf['content'])
            worksheet.write('F%s' % row, res.get('nama_pembayar') , wbf['content'])
            worksheet.write('G%s' % row, res.get('redaksi') , wbf['content']) 
            worksheet.write('H%s' % row, res.get('jumlah') , wbf['content_float'])
            worksheet.write('I%s' % row, res.get('no_rekening') , wbf['content'])
            worksheet.write('J%s' % row, res.get('nama_rekening') , wbf['content'])
            worksheet.write('K%s' % row, res.get('no_faktur_pajak') , wbf['content'])
            worksheet.write('L%s' % row, res.get('no_refrence') , wbf['content'])
            worksheet.write('M%s' % row, res.get('jenis_transaksi') , wbf['content'])
            worksheet.write('N%s' % row, res.get('no_bukti_pembayaran') , wbf['content'])
            worksheet.write('O%s' % row, res.get('tgl_pembayaran') , wbf['content'])
            worksheet.write('P%s' % row, res.get('state','').title() , wbf['content'])

            no +=1
            row +=1

        worksheet.autofilter('A4:P4')  
        worksheet.merge_range('A%s:P%s' % (row,row), '', wbf['total'])

        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write({'state_x':'get', 'data_x':out, 'name': filename})
        fp.close()

        form_id = self.env.ref('teds_cetak_kwitansi.view_teds_laporan_listing_cetak_kwitansi_wizard').id
    
        return {
            'name': ('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.laporan.listing.cetak.kwitansi.wizard',
            'res_id': self.ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }