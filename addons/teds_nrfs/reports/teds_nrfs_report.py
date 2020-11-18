import pytz
from datetime import datetime
import base64
from cStringIO import StringIO
import csv
import xlsxwriter
from openerp import models, fields, api, _

class NrfsReport(models.TransientModel):
    _name = "teds.nrfs.report.wizard"
    _description = "Laporan NRFS"

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
    state = fields.Selection([
        ('rfa', 'Diidentifikasi oleh tim Warehouse'),
        ('approved', 'SPK untuk tim Vendor'),
        ('confirmed', 'Dikonfirmasi tim Vendor'), # all stock part OK
        ('in_progress', 'Diperbaiki tim Vendor'),
        ('done', 'Penanganan selesai')
    ],string='Status')
    wbf = {}

    def _query_nrfs_report(self, **kwargs):
        tz_user = pytz.timezone(self.env.context.get('tz')) if self.env.context.get('tz') else pytz.utc
        tz_from = tz_user.localize(datetime.now()).astimezone(pytz.utc)
        tz_to = pytz.utc.localize(datetime.now())
        tz_offset = int(round((tz_to - tz_from).total_seconds()/3600,0))
        where = " WHERE 1=1 "
        if 'start_date' in kwargs and kwargs.get('start_date') != None:
            where += " AND nrfs.tgl_nrfs >= '%s'" % str(kwargs['start_date'])
        if 'end_date' in kwargs  and kwargs.get('end_date') != None:
            where += " AND nrfs.tgl_nrfs <= '%s'" % str(kwargs['end_date'])
        if 'state' in kwargs  and kwargs.get('state') != None:
            if kwargs['state'] == 'rfa':
                where += " AND nrfs.state IN ('draft','rfa') "
            else:
                where += " AND nrfs.state = '%s' " % str(kwargs['state'])
        if 'include_not_done' in kwargs  and kwargs.get('include_not_done'):
            where += " OR nrfs.state != 'done' "
        nrfs_query = """
            SELECT 
                nrfs.name AS no_nrfs,
                nrfs.tgl_nrfs,
                nrfs.origin,
                lot.name AS no_mesin,
                lot.chassis_no AS no_rangka,
                pt_unit.description,
                (
                    SELECT DATE(pelaksana_date + INTERVAL '%d hours') 
                    FROM teds_nrfs_approval 
                    WHERE lot_id = nrfs.id 
                    AND type = 'Approve NRFS' 
                    ORDER BY id DESC LIMIT 1
                ) AS tgl_spk,
                COALESCE(p.name,'') AS vendor,
                nrfs.no_po_urg AS no_po_urg,
                nrfs.tgl_po_urg AS tgl_po_urg,
                COALESCE(wo.name,'') AS no_wo,
                DATE(wo.confirm_date + INTERVAL '%d hours') AS tgl_start_wo,
                DATE(wo.date_confirm) AS tgl_done_wo
            FROM teds_nrfs nrfs
            JOIN stock_production_lot lot ON nrfs.lot_id = lot.id
            LEFT JOIN res_partner p ON nrfs.branch_partner_id = p.id
            JOIN product_product pp_unit ON lot.product_id = pp_unit.id
            JOIN product_template pt_unit ON pp_unit.product_tmpl_id = pt_unit.id
            LEFT JOIN wtc_work_order wo ON nrfs.id = wo.nrfs_id
            %s  
        """ % (tz_offset, tz_offset, where)
        return nrfs_query

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

    def _generate_excel_buffer_nrfs(self, **kwargs):
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)
        workbook = self.add_workbook_format(workbook)
        worksheet = workbook.add_worksheet('NRFS')
        wbf = self.wbf

        if 'start_date' in kwargs:
            start_date = kwargs['start_date']
        if 'end_date' in kwargs:
            end_date = kwargs['end_date']
        if 'state' in kwargs:
            state = kwargs['state']
        if 'include_not_done' in kwargs:
            include_not_done = kwargs['include_not_done']

        company_name = self.env.user.company_id.name
        date_generate = self._get_default_date().strftime("%Y-%m-%d %H:%M:%S")
        filename = 'Laporan_NRFS_%s.xlsx' % (str(date_generate).replace(" ","_").replace(":","-"))
        user_generate = self.env['res.users'].sudo().browse([self._uid]).name
        # COLUMN HEADER
        col_header = [
            {'name': 'No Case NRFS', 'max_size': 14},
            {'name': 'Tanggal NRFS', 'max_size': 14},
            {'name': 'Source Document', 'max_size': 17},
            {'name': 'No Mesin', 'max_size': 10}, 
            {'name': 'No Rangka', 'max_size': 11}, #5
            {'name': 'Tipe Unit', 'max_size': 11},
            {'name': 'Tanggal SPK', 'max_size': 13},
            {'name': 'Vendor', 'max_size': 8},
            {'name': 'No PO Urgent', 'max_size': 14},
            {'name': 'Tgl PO Urgent', 'max_size': 15}, #10
            {'name': 'No WO Claim', 'max_size': 13}, 
            {'name': 'Tgl Start WO', 'max_size': 14},
            {'name': 'Tgl Done WO', 'max_size': 13}
        ]
        # write table header
        row = 4
        ncol = 0
        for i in col_header:
            worksheet.write(row, ncol, i['name'], wbf['header'])
            ncol += 1
        # write content header
        worksheet.merge_range(0, 0, 0, ncol-1, company_name, wbf['title_doc'])
        worksheet.merge_range(1, 0, 1, ncol-1, 'Laporan NRFS', wbf['title_doc'])
        worksheet.merge_range(2, 0, 2, ncol-1, 'Tanggal : %s s/d %s' % (start_date if start_date else '-', end_date if end_date else '-'), wbf['company'])
        # fetch data
        get_nrfs_query = self._query_nrfs_report(start_date=start_date, end_date=end_date, state=state, include_not_done=include_not_done)
        self._cr.execute(get_nrfs_query)
        nrfs_ress =  self._cr.dictfetchall()
        row += 1
        for x in nrfs_ress:
            col = 0
            worksheet.write(row, col, x['no_nrfs'], wbf['content_center'])
            if len(str(x['no_nrfs'])) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(str(x['no_nrfs'])) + 2
            col += 1
            worksheet.write(row, col, x['tgl_nrfs'], wbf['content_center'])
            if len(str(x['tgl_nrfs'])) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(str(x['tgl_nrfs'])) + 2
            col += 1
            worksheet.write(row, col, x['origin'], wbf['content_center'])
            if len(str(x['origin'])) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(str(x['origin'])) + 2
            col += 1
            worksheet.write(row, col, x['no_mesin'], wbf['content_center'])
            if len(str(x['no_mesin'])) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(str(x['no_mesin'])) + 2
            col += 1
            worksheet.write(row, col, x['no_rangka'], wbf['content_center'])
            if len(str(x['no_rangka'])) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(str(x['no_rangka'])) + 2
            col += 1
            worksheet.write(row, col, x['description'], wbf['content'])
            if len(str(x['description'])) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(str(x['description'])) + 2
            col += 1
            worksheet.write(row, col, x['tgl_spk'], wbf['content_center'])
            if len(str(x['tgl_spk'])) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(str(x['tgl_spk'])) + 2
            col += 1
            worksheet.write(row, col, x['vendor'], wbf['content'])
            if len(str(x['vendor'])) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(str(x['vendor'])) + 2
            col += 1
            worksheet.write(row, col, x['no_po_urg'], wbf['content_center'])
            if len(str(x['no_po_urg'])) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(str(x['no_po_urg'])) + 2
            col += 1
            worksheet.write(row, col, x['tgl_po_urg'], wbf['content_center'])
            if len(str(x['tgl_po_urg'])) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(str(x['tgl_po_urg'])) + 2
            col += 1
            worksheet.write(row, col, x['no_wo'], wbf['content_center'])
            if len(str(x['no_wo'])) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(str(x['no_wo'])) + 2
            col += 1
            worksheet.write(row, col, x['tgl_start_wo'], wbf['content_center'])
            if len(str(x['tgl_start_wo'])) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(str(x['tgl_start_wo'])) + 2
            col += 1
            worksheet.write(row, col, x['tgl_done_wo'], wbf['content_center'])
            if len(str(x['tgl_done_wo'])) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(str(x['tgl_done_wo'])) + 2
            row += 1
        # set column
        for i in range(0, ncol):
            worksheet.set_column(i, i, col_header[i]['max_size'])
        # autofilter
        if nrfs_ress:
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
        return fp, filename

    @api.multi    
    def export_to_xls(self):
        datas = self._generate_excel_buffer_nrfs(start_date=self.start_date, end_date=self.end_date, state=self.state, include_not_done=False)
        file_data = base64.encodestring(datas[0].getvalue())
        datas[0].close()
        self.write({'state_x': 'get', 'data_x': file_data, 'name': datas[1]})
        form_id = self.env.ref('teds_nrfs.teds_nrfs_report_wizard_view_form').id
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.nrfs.report.wizard',
            'res_id': self.ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }

    def _generate_csv_buffer_nrfs(self, start_date, end_date, state):
        date_generate = self._get_default_date().strftime("%Y-%m-%d %H:%M:%S")
        filename = 'Laporan_NRFS_%s.csv' % (str(date_generate).replace(" ","_").replace(":","-"))
        # fetch data
        get_nrfs_query = self._query_nrfs_report(start_date=start_date, end_date=end_date, state=state)
        self._cr.execute(get_nrfs_query)
        nrfs_ress =  self._cr.fetchall()
        # write data
        fp = StringIO()
        writer = csv.writer(fp, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        if nrfs_ress:
            writer.writerow([
                'No Case NRFS',
                'Tanggal NRFS',
                'Source Document',
                'No Mesin',
                'No Rangka',
                'Tipe Unit',
                'Tanggal SPK',
                'Vendor',
                'No PO Urgent',
                'Tgl PO Urgent',
                'No WO Claim',
                'Tgl Start WO',
                'Tgl Done WO'
            ])
        else:
            writer.writerow(['Data tidak ada...'])
        for x in nrfs_ress:
            writer.writerow(x)            
        file_data = base64.encodestring(fp.getvalue())
        fp.close()
        return file_data, filename
    
    @api.multi   
    def export_to_csv(self):
        datas = self._generate_csv_buffer_nrfs(start_date=self.start_date, end_date=self.end_date, state=self.state)
        self.write({'state_x': 'get', 'data_x': datas[0], 'name': datas[1]})
        form_id = self.env.ref('teds_nrfs.teds_nrfs_report_wizard_view_form').id
        return {
            'name': _('Download CSV'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.nrfs.report.wizard',
            'res_id': self.ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }