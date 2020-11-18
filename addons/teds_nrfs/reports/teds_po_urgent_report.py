import base64
from cStringIO import StringIO
import xlsxwriter
import pytz
from openerp import models, fields, api, _

class PoUrgentReport(models.TransientModel):
    _name = "teds.po.urgent.report.wizard"
    _description = "Laporan PO Urgent"

    @api.model
    def _get_default_date(self): 
        return self.env['wtc.branch'].get_default_date()

    name = fields.Char('Nama File', readonly=True)
    state_x = fields.Selection([
        ('choose','Choose'),
        ('get','Result')
    ], default=lambda *a: 'choose')
    data_x = fields.Binary('File', readonly=True)
    start_date = fields.Date('Start date',default=_get_default_date)
    end_date = fields.Date('End date',default=_get_default_date)
    wbf = {}

    @api.multi
    def add_workbook_format(self,workbook):
        self.wbf['header'] = workbook.add_format({'bold': 1,'align': 'center','bg_color': '#FFFFDB','font_color': '#000000'})
        self.wbf['header'].set_border()
                
        self.wbf['footer'] = workbook.add_format({'align':'left'})
        
        self.wbf['title_doc'] = workbook.add_format({'bold': 1,'align': 'left'})
        self.wbf['title_doc'].set_font_size(12)
        
        self.wbf['company'] = workbook.add_format({'align': 'left'})
        self.wbf['company'].set_font_size(11)

        self.wbf['content'] = workbook.add_format()
        self.wbf['content'].set_left()
        self.wbf['content'].set_right()

        self.wbf['content_center'] = workbook.add_format({'align': 'centre'})
        self.wbf['content_center'].set_right() 
        self.wbf['content_center'].set_left()

        self.wbf['content_float'] = workbook.add_format({'align': 'right','num_format': '#,##0.00'})
        self.wbf['content_float'].set_right() 
        self.wbf['content_float'].set_left()
        
        self.wbf['total'] = workbook.add_format({'bold':1,'bg_color': '#FFFFDB','align':'center'})
        self.wbf['total'].set_left()
        self.wbf['total'].set_right()
        self.wbf['total'].set_top()
        self.wbf['total'].set_bottom()

        self.wbf['info'] = workbook.add_format({'bold':1})
        self.wbf['info'].set_left()
        self.wbf['info'].set_right()
        self.wbf['info'].set_top()
        self.wbf['info'].set_bottom()        
        return workbook

    @api.multi    
    def export_to_xls(self):
        wbf = self.wbf
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(workbook)
        worksheet = workbook.add_worksheet('PO Urgent')

        company_name = self.env.user.company_id.name
        date_generate = self._get_default_date().strftime("%Y-%m-%d %H:%M:%S")
        filename = 'Laporan_PO_NRFS_%s.xlsx' % (str(date_generate).replace(" ","_").replace(":","-"))
        user_generate = self.env['res.users'].sudo().browse([self._uid]).name
        # COLUMN HEADER
        col_header = [
            {'name': 'No', 'max_size': 4},
            {'name': 'Kode Part', 'max_size': 11}, 
            {'name': 'Deskripsi Part', 'max_size': 16}, #5
            {'name': 'Qty', 'max_size': 5},
            {'name': 'Nomor PO Urg', 'max_size': 16},
            {'name': 'Tanggal PO Urg', 'max_size': 18},
            {'name': 'Tanggal Delivery', 'max_size': 18},
            {'name': 'Source', 'max_size': 8},
            {'name': 'Nomor Mesin', 'max_size': 13}, 
            {'name': 'Nomor Rangka', 'max_size': 14}, #10
            {'name': 'Tipe Unit', 'max_size': 11}, 
            {'name': 'Tahun Rakit', 'max_size': 13},
            {'name': 'Nama Konsumen', 'max_size': 15},
            {'name': 'Alamat', 'max_size': 8},
            {'name': 'Kota', 'max_size': 6}, #15
            {'name': 'Nomor Telp', 'max_size': 12},
            {'name': 'Nama PPO', 'max_size': 10},
            {'name': 'Tgl Kirim PPO', 'max_size': 15},
            {'name': 'Nomor Distribusi', 'max_size': 18},
        ]
        # write table header
        row = 4
        ncol = 0
        for i in col_header:
            worksheet.write(row, ncol, i['name'], wbf['header'])
            ncol += 1
        # write content header
        worksheet.merge_range(0, 0, 0, ncol-1, company_name, wbf['title_doc'])
        worksheet.merge_range(1, 0, 1, ncol-1, 'Laporan PO NRFS', wbf['title_doc'])
        worksheet.merge_range(2, 0, 2, ncol-1, 'Tanggal : %s s/d %s' % (str(self.start_date) if self.start_date else '-', str(self.end_date) if self.end_date else '-'), wbf['company'])
        # fetch data
        where = " WHERE 1=1 AND nrfsl.is_sparepart_pesan = True "
        if self.start_date:
            where += " AND nrfs.tgl_nrfs >= '%s'" % str(self.start_date)
        if self.end_date:
            where += " AND nrfs.tgl_nrfs <= '%s'" % str(self.end_date)
        get_po_query = """
            SELECT 
                CAST(ROW_NUMBER() OVER () AS VARCHAR) AS no,
                pt.name AS kode_part,
                pt.description,
                nrfsl.qty,
                nrfs.no_po_urg,
                nrfs.tgl_po_urg,
                DATE(nrfs.tgl_po_urg + INTERVAL '10 days') AS delivery_date,
                nrfs.name AS source_doc,
                lot.name AS no_mesin,
                lot.chassis_no AS no_rangka,
                pt_unit.description AS tipe_unit,
                lot.tahun,
                b.name AS nama_kons,
                COALESCE(b.street,'') AS alamat_kons,
                COALESCE(city.name,'') AS kota_kons,
                COALESCE(b.phone,'') AS no_telp,
                COALESCE(nrfs.nama_file_ppo_urg) AS nama_file_ppo,
                COALESCE(nrfs.tgl_kirim_ppo_urg) AS tgl_kirim_ppo,
                COALESCE(nrfsl.no_distribusi) AS no_distribusi
            FROM teds_nrfs nrfs
            JOIN teds_nrfs_line nrfsl ON nrfs.id = nrfsl.lot_id
            JOIN product_product pp ON nrfsl.part_id = pp.id
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
            JOIN stock_production_lot lot ON nrfs.lot_id = lot.id
            JOIN product_product pp_unit ON lot.product_id = pp_unit.id
            JOIN product_template pt_unit ON pp_unit.product_tmpl_id = pt_unit.id
            JOIN res_partner p ON nrfs.branch_partner_id = p.id
            JOIN wtc_branch b ON p.id = b.partner_id
            LEFT JOIN wtc_city city on b.city_id = city.id
            %s  
        """ % (where)
        self._cr.execute(get_po_query)
        po_ress =  self._cr.dictfetchall()
        row += 1
        for x in po_ress:
            col = 0
            worksheet.write(row, col, x['no'], wbf['content_center'])
            if len(str(x['no'])) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(str(x['no'])) + 2
            col += 1
            worksheet.write(row, col, x['kode_part'], wbf['content_center'])
            if len(str(x['kode_part'])) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(str(x['kode_part'])) + 2
            col += 1
            worksheet.write(row, col, x['description'], wbf['content'])
            if len(str(x['description'])) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(str(x['description'])) + 2
            col += 1
            worksheet.write(row, col, x['qty'], wbf['content_float'])
            if len(str(x['qty'])) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(str(x['qty'])) + 2
            col += 1
            worksheet.write(row, col, x['no_po_urg'], wbf['content_center'])
            if len(str(x['no_po_urg'])) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(str(x['no_po_urg'])) + 2
            col += 1
            worksheet.write(row, col, x['tgl_po_urg'], wbf['content_center'])
            if len(str(x['tgl_po_urg'])) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(str(x['tgl_po_urg'])) + 2
            col += 1
            worksheet.write(row, col, x['delivery_date'], wbf['content_center'])
            if len(str(x['delivery_date'])) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(str(x['delivery_date'])) + 2
            col += 1
            worksheet.write(row, col, x['source_doc'], wbf['content_center'])
            if len(str(x['source_doc'])) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(str(x['source_doc'])) + 2
            col += 1
            worksheet.write(row, col, x['no_mesin'], wbf['content_center'])
            if len(str(x['no_mesin'])) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(str(x['no_mesin'])) + 2
            col += 1
            worksheet.write(row, col, x['no_rangka'], wbf['content_center'])
            if len(str(x['no_rangka'])) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(str(x['no_rangka'])) + 2
            col += 1
            worksheet.write(row, col, x['tipe_unit'], wbf['content'])
            if len(str(x['tipe_unit'])) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(str(x['tipe_unit'])) + 2
            col += 1
            worksheet.write(row, col, x['tahun'], wbf['content_center'])
            if len(str(x['tahun'])) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(str(x['tahun'])) + 2
            col += 1
            worksheet.write(row, col, x['nama_kons'], wbf['content_center'])
            if len(str(x['nama_kons'])) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(str(x['nama_kons'])) + 2
            col += 1
            worksheet.write(row, col, x['alamat_kons'], wbf['content'])
            if len(str(x['alamat_kons'])) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(str(x['alamat_kons'])) + 2
            col += 1
            worksheet.write(row, col, x['kota_kons'], wbf['content'])
            if len(str(x['kota_kons'])) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(str(x['kota_kons'])) + 2
            col += 1
            worksheet.write(row, col, x['no_telp'], wbf['content_center'])
            if len(str(x['no_telp'])) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(str(x['no_telp'])) + 2
            col += 1
            worksheet.write(row, col, x['nama_file_ppo'], wbf['content_center'])
            if len(str(x['nama_file_ppo'])) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(str(x['nama_file_ppo'])) + 2
            col += 1
            worksheet.write(row, col, x['tgl_kirim_ppo'], wbf['content_center'])
            if len(str(x['tgl_kirim_ppo'])) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(str(x['tgl_kirim_ppo'])) + 2
            col += 1
            worksheet.write(row, col, x['no_distribusi'], wbf['content_center'])
            if len(str(x['no_distribusi'])) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(str(x['no_distribusi'])) + 2
            row += 1
        # set column
        for i in range(0, ncol):
            worksheet.set_column(i, i, col_header[i]['max_size'])
        # autofilter
        if po_ress:
            worksheet.autofilter(4, 0, row-1, ncol-1)
        else:
            worksheet.merge_range(row, 0, row, ncol-1, 'Data tidak ada...', wbf['info'])
            row += 1
        # close table
        worksheet.merge_range(row, 0, row, ncol-1, '', wbf['total'])
        # audit trail
        worksheet.merge_range(row+2, 0, row+2, 3, '%s %s' % (str(date_generate).replace("_"," "), user_generate), wbf['footer'])
        # close excel
        workbook.close()
        out = base64.encodestring(fp.getvalue())
        self.write({'state_x':'get', 'data_x':out, 'name': filename})
        fp.close()
        form_id = self.env.ref('teds_nrfs.teds_po_urgent_report_wizard_view_form').id
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.po.urgent.report.wizard',
            'res_id': self.ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }