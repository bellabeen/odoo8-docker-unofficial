from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning
from cStringIO import StringIO
import xlsxwriter
import base64
from datetime import date, datetime, timedelta,time
from dateutil.relativedelta import relativedelta
import calendar

class LaporanRincianKendaraanWiazard(models.TransientModel):
    _name = "teds.laporan.rincian.kendaraan.wizard"
    _description = "Laporan Rincian Kendaraan"

    wbf = {}

    def _get_default_branch(self):
        branch_ids = False
        branch_ids = self.env.user.branch_ids
        if branch_ids and len(branch_ids) == 1 :
            return [branch_ids[0].id]
        return False
    
    
    @api.model
    def _get_default_date(self): 
        return self.env['wtc.branch'].get_default_date()

    name = fields.Char('Filename', readonly=True)
    state_x = fields.Selection( ( ('choose','choose'),('get','get')),default=lambda *a: 'choose')
    data_x = fields.Binary('File', readonly=True)
    branch_ids = fields.Many2many('wtc.branch', 'teds_laporan_rincian_kendaraan_branch_rel', 'teds_laporan_rincian_kendaraan_wizard_id', 'branch_id', 'Dealer',default=_get_default_branch)
    tgl_beli = fields.Date('Tgl Beli',default=_get_default_date)
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')

    @api.multi
    def add_workbook_format(self,workbook):      
        self.wbf['header'] = workbook.add_format({'bold': 1,'align': 'center','bg_color': '#10F0F0','font_color': '#000000'})
        self.wbf['header'].set_border()
        self.wbf['header'].set_font_size(10)


        self.wbf['header_no'] = workbook.add_format({'bold': 1,'align': 'center','bg_color': '#10F0F0','font_color': '#000000'})
        self.wbf['header_no'].set_border()
        self.wbf['header_no'].set_align('vcenter')
                
        self.wbf['footer'] = workbook.add_format({'align':'left'})
        
        self.wbf['content_datetime'] = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss'})
        self.wbf['content_datetime'].set_left()
        self.wbf['content_datetime'].set_right()
        
        self.wbf['content_datetime_12_hr'] = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm AM/PM'})
        self.wbf['content_datetime_12_hr'].set_left()
        self.wbf['content_datetime_12_hr'].set_right()        
                
        self.wbf['content_date'] = workbook.add_format({'num_format': 'yyyy-mm-dd'})
        self.wbf['content_date'].set_left()
        self.wbf['content_date'].set_right() 
        
        self.wbf['title_doc'] = workbook.add_format({'bold': 1,'align': 'center'})
        self.wbf['title_doc'].set_font_size(10)
        
        self.wbf['company'] = workbook.add_format({'align': 'left'})
        self.wbf['company'].set_font_size(11)
        
        self.wbf['content'] = workbook.add_format()
        self.wbf['content'].set_left()
        self.wbf['content'].set_right() 
        
        self.wbf['content_float'] = workbook.add_format({'align': 'right','num_format': '#,##0.00'})
        self.wbf['content_float'].set_right() 
        self.wbf['content_float'].set_left()

        self.wbf['content_center'] = workbook.add_format({'align': 'centre'})
        self.wbf['content_center'].set_align('vcenter')
        self.wbf['content_center'].set_font_size(10)
        
        self.wbf['content_number'] = workbook.add_format({'align': 'right'})
        self.wbf['content_number'].set_right() 
        self.wbf['content_number'].set_left() 
                
        self.wbf['content_percent'] = workbook.add_format({'align': 'right','num_format': '0.00%'})
        self.wbf['content_percent'].set_right() 
        self.wbf['content_percent'].set_left() 
                
        self.wbf['total_float'] = workbook.add_format({'bold':1,'bg_color': '#FFFFDB','align': 'right','num_format': '#,##0.00'})
        self.wbf['total_float'].set_top()
        self.wbf['total_float'].set_bottom()            
        self.wbf['total_float'].set_left()
        self.wbf['total_float'].set_right()         
        
        self.wbf['total_number'] = workbook.add_format({'align':'right','bg_color': '#FFFFDB','bold':1})
        self.wbf['total_number'].set_top()
        self.wbf['total_number'].set_bottom()            
        self.wbf['total_number'].set_left()
        self.wbf['total_number'].set_right()
        
        self.wbf['total'] = workbook.add_format({'bold':1,'bg_color': '#FFFFDB','align':'center'})
        self.wbf['total'].set_left()
        self.wbf['total'].set_right()
        self.wbf['total'].set_top()
        self.wbf['total'].set_bottom()
        
        return workbook

    @api.multi
    def action_export(self):
        self.ensure_one()

        query_where = " WHERE dso.state in ('progress','done')"
    
        if self.branch_ids:
            branch = [b.id for b in self.branch_ids]
            query_where += " AND dso.branch_id in %s" % str(tuple(branch)).replace(',)', ')')

        if self.start_date:
            query_where += " AND dso.date_order >= '%s'" % str(self.start_date)
        if self.end_date:
            query_where += " AND dso.date_order <= '%s'" % str(self.end_date)

        query = """
            SELECT
                b.name as nama_dealer
                , b.street || ' ' || COALESCE(kec.name,' ') || ' ' || COALESCE(city.name,' ') as alamat_dealer
                , COALESCE(b.npwp,'-') as npwp
                , COALESCE(b.no_pkp,'-') as pengukuhan_pkp
                , COALESCE(fpo.name,'-') as faktur_pajak
                , fpo.date as tgl_faktur
                , p.name as nama_pembeli
                , COALESCE(p.npwp,'-') as npwp_pembeli
                , p.street || ', RT '|| COALESCE(p.rt,' ') || '/' || COALESCE(p.rw,' ') || ' ' || COALESCE(kec2.name,'') || ' - ' || COALESCE(kel.name,'') || ' ' || COALESCE(city.name,' ') as alamat_pemb 
                , lot.name as no_mesin
                , lot.chassis_no as no_rangka
                , pt.description || ' (' || pav.name || ')' as tipe
                , COALESCE(pp.default_code,'-') as jenis
                , COALESCE(lot.tahun,'-') as tahun
                , dsol.price_unit / 1.1 as price_unit
                , (dsol.price_unit  - (dsol.price_unit / 1.1)) as ppn
                , dsol.price_unit as subtotal
                , '-' as ket
            FROM dealer_sale_order dso
            INNER JOIN dealer_sale_order_line dsol ON dsol.dealer_sale_order_line_id = dso.id
            LEFT JOIN wtc_faktur_pajak_out fpo ON fpo.id = dso.faktur_pajak_id
            INNER JOIN stock_production_lot lot ON lot.id = dsol.lot_id
            INNER JOIN product_product pp ON pp.id = lot.product_id
            INNER JOIN product_template pt ON pt.id = pp.product_tmpl_id
            LEFT JOIN product_attribute_value_product_product_rel rel ON rel.prod_id = pp.id
            LEFT JOIN product_attribute_value pav ON pav.id = rel.att_id                       
            INNER JOIN wtc_branch b ON b.id = dso.branch_id
            LEFT JOIN wtc_city city ON city.id = b.city_id
            LEFT JOIN wtc_kecamatan kec ON kec.id = b.kecamatan_id
            INNER JOIN res_partner p ON p.id = dso.partner_id
            LEFT JOIN wtc_city city2 ON city2.id = p.city_id
            LEFT JOIN wtc_kecamatan kec2 ON kec2.id = p.kecamatan_id
            LEFT JOIN wtc_kelurahan kel ON kel.id = p.zip_id
            %s
        """ %(query_where)

        self._cr.execute (query)
        ress =  self._cr.dictfetchall()
        
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Laporan Kelengkapan Unit')
        worksheet.set_column('A1:A1', 29)
        worksheet.set_column('B1:B1', 50)
        worksheet.set_column('C1:C1', 23)
        worksheet.set_column('D1:D1', 20)
        worksheet.set_column('E1:E1', 8)
        worksheet.set_column('F1:F1', 20)
        worksheet.set_column('G1:G1', 17)
        worksheet.set_column('H1:H1', 30)
        worksheet.set_column('I1:I1', 20)
        worksheet.set_column('J1:J1', 50)
        worksheet.set_column('K1:K1', 20)
        worksheet.set_column('L1:L1', 23)
        worksheet.set_column('M1:M1', 35)
        worksheet.set_column('N1:N1', 30)
        worksheet.set_column('O1:O1', 15)
        worksheet.set_column('P1:P1', 25)
        worksheet.set_column('Q1:Q1', 15)
        worksheet.set_column('R1:R1', 15)
        worksheet.set_column('S1:S1', 20)
        worksheet.set_column('T1:T1', 15)

        date= self._get_default_date()
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        month = False
        tahun = False
        if self.tgl_beli:
            bln = self.tgl_beli[5:7]
            month = (calendar.month_name[int(bln)])
            tahun = self.tgl_beli[0:4]


        
        filename = 'Laporan Rincian Kendaraan'+' '+str(date)+'.xlsx'        
        worksheet.merge_range('A2:T2', 'LAMPIRAN SURAT KEDARAN NOMOR : SE-31/PJ/2013 TANGGAL 5 JULI 2013 TENTANG PELAPORAN PEMUNGUTAN PPN DAN PPnBM ATAS PENYERAHAN KENDARAAN BERMOTOR' , wbf['title_doc'])
        worksheet.merge_range('A4:T4', 'DAFTAR RINCIAN KENDARAAN BERMOTOR' , wbf['title_doc'])
        worksheet.merge_range('A5:T5', 'BULAN %s TAHUN %s' %(month,tahun), wbf['title_doc'])

        row=4
        rowsaldo = row
        row+=1
        worksheet.write('A%s' % (row+1), 'Nama Perusahaan' , wbf['header'])
        worksheet.write('B%s' % (row+1), 'Alamat Perusahaan' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'NPWP Perusahaan' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'No. Pengukuhan PKP' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'No.' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'Faktur Pajak' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'Tanggal Faktur' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'Nama Pembeli' , wbf['header'])
        worksheet.write('I%s' % (row+1), 'NPWP Pembeli' , wbf['header'])
        worksheet.write('J%s' % (row+1), 'Alamat Pembeli' , wbf['header'])
        worksheet.write('K%s' % (row+1), 'No. Rangka' , wbf['header'])
        worksheet.write('L%s' % (row+1), 'No. Mesin' , wbf['header'])
        worksheet.write('M%s' % (row+1), 'Tipe/Merk' , wbf['header'])
        worksheet.write('N%s' % (row+1), 'Jenis/Model' , wbf['header'])
        worksheet.write('O%s' % (row+1), 'Tahun' , wbf['header'])
        worksheet.write('P%s' % (row+1), 'Harga Jual Kendaraan' , wbf['header'])
        worksheet.write('Q%s' % (row+1), 'PPN' , wbf['header'])
        worksheet.write('R%s' % (row+1), 'PPN BM' , wbf['header'])
        worksheet.write('S%s' % (row+1), 'Jumlah' , wbf['header'])
        worksheet.write('T%s' % (row+1), 'Keterangan' , wbf['header'])

        row+=2               
        no = 1     
        row1 = row

        for res in ress:
            nama_dealer = str(res['nama_dealer'].encode('ascii','ignore').decode('ascii'))
            alamat_dealer  = str(res['alamat_dealer'].encode('ascii','ignore').decode('ascii')) if res['alamat_dealer'] != None else ''
            npwp = str(res['npwp']).encode('ascii','ignore').decode('ascii')
            pengukuhan_pkp = str(res['pengukuhan_pkp']).encode('ascii','ignore').decode('ascii')
            faktur_pajak = str(res['faktur_pajak']).encode('ascii','ignore').decode('ascii')
            tgl_faktur = str(res['tgl_faktur']) if res['tgl_faktur'] != None else '-'
            nama_pembeli = str(res['nama_pembeli']).encode('ascii','ignore').decode('ascii')
            npwp_pembeli = str(res['npwp_pembeli']).encode('ascii','ignore').decode('ascii')
            alamat_pemb = str(res['alamat_pemb']).encode('ascii','ignore').decode('ascii')
            no_mesin = str(res['no_mesin'])
            no_rangka = str(res['no_rangka'])
            tipe = str(res['tipe']).encode('ascii','ignore').decode('ascii')
            jenis = str(res['jenis']).encode('ascii','ignore').decode('ascii')
            tahun = str(res['tahun'])
            price_unit = res['price_unit']
            ppn = res['ppn']
            subtotal = res['subtotal']
            ket = str(res['ket'])
            
            worksheet.write('A%s' % row, nama_dealer , wbf['content'])
            worksheet.write('B%s' % row, alamat_dealer , wbf['content'])
            worksheet.write('C%s' % row, npwp , wbf['content'])
            worksheet.write('D%s' % row, pengukuhan_pkp , wbf['content'])
            worksheet.write('E%s' % row, no ,wbf['content_center'])
            worksheet.write('F%s' % row, faktur_pajak , wbf['content_center'])
            worksheet.write('G%s' % row, tgl_faktur , wbf['content_center'])
            worksheet.write('H%s' % row, nama_pembeli , wbf['content_center'])
            worksheet.write('I%s' % row, npwp_pembeli , wbf['content_center'])
            worksheet.write('J%s' % row, alamat_pemb , wbf['content'])
            worksheet.write('K%s' % row, no_rangka , wbf['content_center'])
            worksheet.write('L%s' % row, no_mesin , wbf['content_center'])
            worksheet.write('M%s' % row, tipe , wbf['content_center'])
            worksheet.write('N%s' % row, jenis , wbf['content_center'])
            worksheet.write('O%s' % row, tahun , wbf['content_center'])
            worksheet.write('P%s' % row, price_unit , wbf['content_number'])
            worksheet.write('Q%s' % row, ppn , wbf['content_number'])
            worksheet.write('R%s' % row, '-' , wbf['content_number'])
            worksheet.write('S%s' % row, subtotal , wbf['content_number'])
            worksheet.write('T%s' % row, '' , wbf['content'])

            no+=1
            row+=1

        # worksheet.autofilter('A6:T%s' % (row))  
        # worksheet.freeze_panes(6, 3)
               
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write({'state_x':'get', 'data_x':out, 'name': filename})
        fp.close()

        ir_model_data = self.env['ir.model.data']
        form_res = ir_model_data.get_object_reference('teds_laporan_rincian_kendaraan', 'view_teds_laporan_rincian_kendaraan_wizard')
        
        form_id = form_res and form_res[1] or False
        return {
            'name':('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.laporan.rincian.kendaraan.wizard',
            'res_id': self.ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }