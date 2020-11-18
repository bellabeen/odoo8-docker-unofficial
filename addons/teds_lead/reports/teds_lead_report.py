import base64
from cStringIO import StringIO
import xlsxwriter
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import models, fields, api, _

class LeadReport(models.TransientModel):
    _name = "teds.lead.report.wizard"
    _description = "Laporan Buku Tamu"

    @api.model
    def _get_default_date(self): 
        return self.env['wtc.branch'].get_default_date()
        
    @api.model
    def _get_date_min_30(self): 
        return self.env['wtc.branch'].get_default_date() + relativedelta(days=-30)

    def _set_domain_branch_ids(self):
        return [('id','in',[b.id for b in self.env.user.branch_ids])]

    name = fields.Char('Nama File', readonly=True)
    state_x = fields.Selection([('choose','choose'),('get','get')], default=lambda *a: 'choose')
    data_x = fields.Binary('File', readonly=True)
    branch_ids = fields.Many2many('wtc.branch', 'teds_lead_report_branch_rel', 'wizard_id', 'branch_id', 'Dealer', copy=False, domain=_set_domain_branch_ids)
    start_date = fields.Date('Start Date',default=_get_date_min_30)    
    end_date = fields.Date('End Date',default=_get_default_date)    
    data_source = fields.Selection([
        ('apps', 'Non Web'),
        ('all', 'All'),
        ],default='apps', string='Data Source') 
    state = fields.Selection([
        ('all', 'All'),
        ('open', 'Open'),
        ('dealt', 'Dealt'),
        ('proposed','Proposed'),
        ('reciept','Reciept'),
        ('approved','Approved'),
        ('reject','Reject'),
        ('spk','SPK'),
        ],default='all', string='State')
    wbf = {}

    @api.multi
    def add_workbook_format(self,workbook):
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
        
        self.wbf['content_float'] = workbook.add_format({'align': 'right','num_format': '#,##0.00'})
        self.wbf['content_float'].set_right() 
        self.wbf['content_float'].set_left()

        self.wbf['content_center'] = workbook.add_format({'align': 'centre'})
        self.wbf['content_center'].set_right() 
        self.wbf['content_center'].set_left() 
        
        self.wbf['content_number'] = workbook.add_format({'align': 'right'})
        self.wbf['content_number'].set_right() 
        self.wbf['content_number'].set_left()
        
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
        worksheet = workbook.add_worksheet('Buku Tamu')

        company_name = self.env.user.company_id.name
        date_generate = (self._get_default_date() + relativedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S")
        filename = 'Laporan_Buku_Tamu_%s.xlsx' % (str(date_generate).replace(" ","_").replace(":","-"))
        user_generate = self.env['res.users'].sudo().browse([self._uid]).name
        # COLUMN HEADER
        col_header = [
            {'name': 'No', 'max_size': 4},
            {'name': 'Kode Dealer', 'max_size': 13},
            {'name': 'Nama Dealer', 'max_size': 13},
            {'name': 'Tanggal', 'max_size': 9},
            {'name': 'Status', 'max_size': 10},
            {'name': 'Nomor KTP', 'max_size': 11},
            {'name': 'Nama Konsumen', 'max_size': 17}, #5
            {'name': 'Alamat', 'max_size': 8},
            {'name': 'Kelurahan', 'max_size': 11},
            {'name': 'Kecamatan', 'max_size': 11},
            {'name': 'Kab / Kota', 'max_size': 12},
            {'name': 'Jenis Kelamin', 'max_size': 15}, #10
            {'name': 'Nomor HP', 'max_size': 10},
            {'name': 'Salesman', 'max_size': 10},
            {'name': 'Jenis Pembelian', 'max_size': 17},
            {'name': 'DP', 'max_size': 4}, #15
            {'name': 'Fincoy', 'max_size': 8},
            {'name': 'Tipe Unit', 'max_size': 11},
            {'name': 'Kode Unit', 'max_size': 11},
            {'name': 'Warna', 'max_size': 7},
            {'name': 'Segmen Unit', 'max_size': 13},
            {'name': 'Series Unit', 'max_size': 13}, #20
            {'name': 'Tanggal Deal', 'max_size': 14},
            {'name': 'Jaringan Penjualan', 'max_size': 20},
            {'name': 'Tipe Activity', 'max_size': 15},
            {'name': 'Titik Keramaian', 'max_size': 17}, #25
            {'name': 'Source Location', 'max_size': 17}, #25
            {'name': 'Data Source', 'max_size': 17}, #25
        ]
        # write table header
        row = 4
        ncol = 0
        for i in col_header:
            worksheet.write(row, ncol, i['name'], wbf['header'])
            ncol += 1
        # freeze panes
        worksheet.freeze_panes(5, 3)
        # write content header
        worksheet.merge_range(0, 0, 0, ncol-1, company_name, wbf['title_doc'])
        worksheet.merge_range(1, 0, 1, ncol-1, 'Laporan Buku Tamu', wbf['title_doc'])
        worksheet.merge_range(2, 0, 2, ncol-1, 'Tanggal : %s s/d %s' % (str(self.start_date) if self.start_date else '-', str(self.end_date) if self.end_date else '-'), wbf['company'])
        # fetch data
        where = " WHERE 1=1"    
        if self.branch_ids:
            where += " AND lead.branch_id IN %s" % str(tuple([b.id for b in self.branch_ids])).replace(',)', ')')
        else:
            where += " AND lead.branch_id IN %s" % str(tuple([b.id for b in self.env.user.branch_ids])).replace(',)', ')')
        if self.start_date:
            where += " AND lead.date  >= '%s'" % str(self.start_date)
        if self.end_date:
            where += " AND lead.date  <= '%s'" % str(self.end_date)
        if self.state in ['open','dealt','cancel']:
            where += " AND lead.state = '%s'" % str(self.state)
        if self.data_source == 'apps':
            where += " AND lead.data_source in ('apps','dgi')"


        get_lead_query = """
            SELECT 
                branch.code as branch_code,
                branch.name as branch_name,
                CASE WHEN sale_order.id is not null and sale_order.state in ('approved','progress','done') THEN 'DO Teds'
                    ELSE CASE WHEN lead.state = 'cancel' THEN 'Cancel'
                            ELSE CASE WHEN lead.state = 'open' THEN initcap(lead.minat)
                                ELSE 'Deal' END
                            END
                    END
                AS status,
                lead.no_ktp,
                lead.name_customer,
                lead.street,
                lead.data_source as data_source,
                kl.name as kel,
                k.name as kec,
                c.name as kota,
                kelamin.name as jenis_kelamin,
                lead.mobile,
                empl.name_related as sales,
                lead.date as tanggal,
                CASE
                    WHEN lead.payment_type = '1' THEN 'Cash'
                    WHEN lead.payment_type = '1' THEN 'Credit'
                END AS jenis_pembelian,
                lead.uang_muka as dp,
                partner.name as finco,
                prod_temp.name as name_unit,
                prod.default_code as code_unit,
                warna_unit.name as warna,
                prod_type.name as prod_type,
                prod_temp.series as prod_series,
                lead.deal_date + INTERVAL '7 hours' as deal,
                lead.jaringan_penjualan,
                sp.name AS activity_type,
                tk.name AS titik_keramaian,
                location.name AS source_location,
                CASE WHEN lead.data_source = 'apps' THEN
                    CASE WHEN lead.version_name is not null THEN
                        CASE WHEN lead.version_name = '1.0' THEN 'thor 1.0' ELSE lead.version_name END
                    ELSE 'Other' END
                ELSE CASE WHEN lead.data_source = 'dgi' THEN 'DGI' ELSE 'Web' END
                END AS version_name
            FROM teds_lead as lead
            LEFT JOIN wtc_branch as branch ON branch.id = lead.branch_id
            LEFT JOIN res_partner as partner ON partner.id = lead.finco_id
            LEFT JOIN product_product prod ON prod.id =  lead.product_id
            LEFT JOIN product_template as prod_temp ON prod_temp.id = prod.product_tmpl_id
            LEFT JOIN product_attribute_value_product_product_rel f ON f.prod_id = prod.id
            LEFT JOIN product_attribute_value warna_unit ON warna_unit.id = f.att_id
            LEFT JOIN product_category as prod_type on prod_type.id = prod_temp.categ_id
            LEFT JOIN wtc_questionnaire kelamin on lead.jenis_kelamin_id=kelamin.id
            LEFT JOIN res_country_state cs ON cs.id = lead.state_id
            LEFT JOIN wtc_city c ON c.id = lead.kabupaten_id
            LEFT JOIN wtc_kecamatan k ON k.id = lead.kecamatan_id
            LEFT JOIN wtc_kelurahan kl ON kl.id = lead.zip_code_id
            LEFT JOIN hr_employee empl ON empl.id = lead.employee_id
            LEFT JOIN teds_act_type_sumber_penjualan sp ON lead.sumber_penjualan_id = sp.id
            LEFT JOIN titik_keramaian tk ON lead.titik_keramaian_id = tk.id
            LEFT JOIN stock_location as location on location.id = lead.sales_source_location_id
            LEFT JOIN dealer_spk as spk on spk.id = lead.spk_id
            LEFT JOIN dealer_sale_order as sale_order on sale_order.id = spk.dealer_sale_order_id
            %s  
        """ % (where)
        self._cr.execute(get_lead_query)
        lead_ress =  self._cr.dictfetchall()
        row += 1
        no = 1
        for x in lead_ress:
            col = 0
            worksheet.write(row, col, no, wbf['content_center'])
            if len(str(no)) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(str(no)) + 2
            col += 1
            x['branch_code'] = '' if x['branch_code'] == None else x['branch_code']
            worksheet.write(row, col, x['branch_code'], wbf['content_center'])
            if len(x['branch_code']) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(x['branch_code']) + 2
            col += 1
            x['branch_name'] = '' if x['branch_name'] == None else x['branch_name']
            worksheet.write(row, col, x['branch_name'], wbf['content'])
            if len(x['branch_name']) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(x['branch_name']) + 2
            col += 1
            x['tanggal'] = '' if x['tanggal'] == None else x['tanggal']
            worksheet.write(row, col, x['tanggal'], wbf['content_center'])
            if len(x['tanggal']) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(x['tanggal']) + 2
            col += 1
            x['status'] = '' if x['status'] == None else x['status']
            worksheet.write(row, col, x['status'], wbf['content_center'])
            if len(x['status']) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(x['status']) + 2
            col += 1
            x['no_ktp'] = '' if x['no_ktp'] == None else x['no_ktp']
            worksheet.write(row, col, x['no_ktp'], wbf['content_center'])
            if len(x['no_ktp']) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(x['no_ktp']) + 2
            col += 1
            x['name_customer'] = '' if x['name_customer'] == None else x['name_customer']
            worksheet.write(row, col, x['name_customer'], wbf['content'])
            if len(x['name_customer']) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(x['name_customer']) + 2
            col += 1
            x['street'] = '' if x['street'] == None else x['street']
            worksheet.write(row, col, x['street'], wbf['content'])
            if len(x['street']) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(x['street']) + 2
            col += 1
            x['kel'] = '' if x['kel'] == None else x['kel']
            worksheet.write(row, col, x['kel'], wbf['content_center'])
            if len(x['kel']) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(x['kel']) + 2
            col += 1
            x['kec'] = '' if x['kec'] == None else x['kec']
            worksheet.write(row, col, x['kec'], wbf['content_center'])
            if len(x['kec']) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(x['kec']) + 2
            col += 1
            x['kota'] = '' if x['kota'] == None else x['kota']
            worksheet.write(row, col, x['kota'], wbf['content_center'])
            if len(x['kota']) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(x['kota']) + 2
            col += 1
            x['jenis_kelamin'] = '' if x['jenis_kelamin'] == None else x['jenis_kelamin']
            worksheet.write(row, col, x['jenis_kelamin'], wbf['content_center'])
            if len(x['jenis_kelamin']) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(x['jenis_kelamin']) + 2
            col += 1
            x['mobile'] = '' if x['mobile'] == None else x['mobile']
            worksheet.write(row, col, x['mobile'], wbf['content_center'])
            if len(str(x['mobile'])) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(str(x['mobile'])) + 2            
            col += 1
            x['sales'] = '' if x['sales'] == None else x['sales']
            worksheet.write(row, col, x['sales'], wbf['content'])
            if len(x['sales']) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(x['sales']) + 2
            col += 1
            x['jenis_pembelian'] = '' if x['jenis_pembelian'] == None else x['jenis_pembelian']
            worksheet.write(row, col, x['jenis_pembelian'], wbf['content_center'])
            if len(x['jenis_pembelian']) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(x['jenis_pembelian']) + 2
            col += 1
            x['dp'] = '' if x['dp'] == None else x['dp']
            worksheet.write(row, col, x['dp'], wbf['content_float'])
            if len(str(x['dp'])) + 6 >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(str(x['dp'])) + 6
            col += 1
            x['finco'] = '' if x['finco'] == None else x['finco']
            worksheet.write(row, col, x['finco'], wbf['content'])
            if len(x['finco']) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(x['finco']) + 2
            col += 1
            x['name_unit'] = '' if x['name_unit'] == None else x['name_unit']
            worksheet.write(row, col, x['name_unit'], wbf['content'])
            if len(x['name_unit']) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(x['name_unit']) + 2
            col += 1
            x['code_unit'] = '' if x['code_unit'] == None else x['code_unit']
            worksheet.write(row, col, x['code_unit'], wbf['content_center'])
            if len(x['code_unit']) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(x['code_unit']) + 2
            col += 1
            x['warna'] = '' if x['warna'] == None else x['warna']
            worksheet.write(row, col, x['warna'], wbf['content_center'])
            if len(x['warna']) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(x['warna']) + 2
            col += 1
            x['prod_type'] = '' if x['prod_type'] == None else x['prod_type']
            worksheet.write(row, col, x['prod_type'], wbf['content_center'])
            if len(x['prod_type']) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(x['prod_type']) + 2
            col += 1
            x['prod_series'] = '' if x['prod_series'] == None else x['prod_series']
            worksheet.write(row, col, x['prod_series'], wbf['content_center'])
            if len(x['prod_series']) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(x['prod_series']) + 2
            col += 1
            x['deal'] = '' if x['deal'] == None else x['deal']
            worksheet.write(row, col, x['deal'], wbf['content_center'])
            if len(x['deal']) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(x['deal']) + 2
            col += 1
            x['jaringan_penjualan'] = '' if x['jaringan_penjualan'] == None else x['jaringan_penjualan']
            worksheet.write(row, col, x['jaringan_penjualan'], wbf['content_center'])
            if len(x['jaringan_penjualan']) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(x['jaringan_penjualan']) + 2
            col += 1
            x['activity_type'] = '' if x['activity_type'] == None else x['activity_type']
            worksheet.write(row, col, x['activity_type'], wbf['content_center'])
            if len(x['activity_type']) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(x['activity_type']) + 2
            col += 1
            x['titik_keramaian'] = '' if x['titik_keramaian'] == None else x['titik_keramaian']
            worksheet.write(row, col, x['titik_keramaian'], wbf['content'])
            if len(x['titik_keramaian']) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(x['titik_keramaian']) + 2
            col += 1
            x['source_location'] = '' if x['source_location'] == None else x['source_location']
            worksheet.write(row, col, x['source_location'], wbf['content'])
            if len(x['source_location']) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(x['source_location']) + 2
            col += 1
            x['version_name'] = '' if x['version_name'] == None else x['version_name']
            worksheet.write(row, col, x['version_name'], wbf['content'])
            if len(x['version_name']) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(x['version_name']) + 2
            row += 1
            no += 1
        # set column
        for i in range(0, ncol):
            worksheet.set_column(i, i, col_header[i]['max_size'])
        # autofilter
        if lead_ress:
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
        form_id = self.env.ref('teds_lead.teds_lead_report_wizard_view_form').id
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.lead.report.wizard',
            'res_id': self.ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }