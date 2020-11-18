import base64
from cStringIO import StringIO
import xlsxwriter
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import models, fields, api, _

class b2b_file_sl_report(models.TransientModel):
    _name = "teds.b2b.file.sl.report.wizard"
    _description = "Laporan Shipping List"

    @api.model
    def _get_default_date(self): 
        return self.env['wtc.branch'].get_default_date()

    name = fields.Char('Nama File', readonly=True)
    state_x = fields.Selection([
        ('choose','Choose'),
        ('get','Result')
    ], default=lambda *a: 'choose')
    data_x = fields.Binary('File', readonly=True)
    start_date = fields.Date('Start date')
    end_date = fields.Date('End date')
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

        self.wbf['content_center'] = workbook.add_format({'align': 'centre'})
        self.wbf['content_center'].set_right() 
        self.wbf['content_center'].set_left()
        
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
        worksheet = workbook.add_worksheet('Shipping List AHM')

        company_name = self.env.user.company_id.name
        date_generate = (self._get_default_date() + relativedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S")
        filename = 'Laporan_Shipping_List_%s.xlsx' % (str(date_generate).replace(" ","_").replace(":","-"))
        user_generate = self.env['res.users'].sudo().browse([self._uid]).name
        # COLUMN HEADER
        col_header = [
            {'name': 'No', 'max_size': 4},
            {'name': 'Kode MD', 'max_size': 9},
            {'name': 'No Shipping List', 'max_size': 18},
            {'name': 'Tgl Shipping List', 'max_size': 19}, 
            {'name': 'No Mesin', 'max_size': 10}, #5
            {'name': 'No Rangka', 'max_size': 11},
            {'name': 'Kode Tipe', 'max_size': 11},
            {'name': 'Kode Warna', 'max_size': 12}, 
            {'name': 'No SIPB', 'max_size': 9},
            {'name': 'Nopol Expedisi', 'max_size': 16} #10
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
        worksheet.merge_range(1, 0, 1, ncol-1, 'Laporan Picking Slip', wbf['title_doc'])
        worksheet.merge_range(2, 0, 2, ncol-1, 'Tanggal : %s s/d %s' % (str(self.start_date) if self.start_date else '-', str(self.end_date) if self.end_date else '-'), wbf['company'])
        # fetch data
        where = " WHERE 1=1 "
        if self.start_date:
            where += " AND tgl_ship_list >= '%s'" % str(self.start_date)
        if self.end_date:
            where += " AND tgl_ship_list <= '%s'" % str(self.end_date)
        get_sl_query = """
            SELECT 
                kode_md,
                no_ship_list,
                tgl_ship_list,
                no_mesin,
                no_rangka,
                kode_type,
                kode_warna,
                no_sipb,
                nopol_expedisi
            FROM b2b_file_sl
            %s  
        """ % (where)
        self._cr.execute(get_sl_query)
        sl_ress =  self._cr.dictfetchall()
        row += 1
        no = 1
        for x in sl_ress:
            col = 0
            worksheet.write(row, col, no, wbf['content_center'])
            if len(str(no)) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(str(no)) + 2
            col += 1
            worksheet.write(row, col, x['kode_md'], wbf['content_center'])
            if len(x['kode_md']) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(x['kode_md']) + 2
            col += 1
            worksheet.write(row, col, x['no_ship_list'], wbf['content_center'])
            if len(x['no_ship_list']) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(x['no_ship_list']) + 2
            col += 1
            worksheet.write(row, col, x['tgl_ship_list'], wbf['content_center'])
            if len(x['tgl_ship_list']) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(x['tgl_ship_list']) + 2
            col += 1
            worksheet.write(row, col, x['no_mesin'], wbf['content_center'])
            if len(x['no_mesin']) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(x['no_mesin']) + 2
            col += 1
            worksheet.write(row, col, x['no_rangka'], wbf['content_center'])
            if len(x['no_rangka']) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(x['no_rangka']) + 2
            col += 1
            worksheet.write(row, col, x['kode_type'], wbf['content_center'])
            if len(x['kode_type']) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(x['kode_type']) + 2
            col += 1
            worksheet.write(row, col, x['kode_warna'], wbf['content_center'])
            if len(x['kode_warna']) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(x['kode_warna']) + 2
            col += 1
            worksheet.write(row, col, x['no_sipb'], wbf['content_center'])
            if len(x['no_sipb']) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(x['no_sipb']) + 2
            col += 1
            worksheet.write(row, col, x['nopol_expedisi'], wbf['content_center'])
            if len(x['nopol_expedisi']) >= col_header[col]['max_size']:
                col_header[col]['max_size'] = len(x['nopol_expedisi']) + 2
            row += 1
            no += 1
        # set column
        for i in range(0, ncol):
            worksheet.set_column(i, i, col_header[i]['max_size'])
        # autofilter
        if sl_ress:
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
        form_id = self.env.ref('b2b_file.teds_b2b_file_sl_report_wizard_view_form').id
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.b2b.file.sl.report.wizard',
            'res_id': self.ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }
