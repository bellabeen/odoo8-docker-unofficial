import xlwt
from datetime import datetime
import time
from openerp.osv import orm
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
from .wtc_report_faktur_pajak import wtc_report_faktur_pajak_print
from openerp.tools.translate import translate
import string

class wtc_report_faktur_pajak_print_xls(wtc_report_faktur_pajak_print):

    def __init__(self, cr, uid, name, context):
        super(wtc_report_faktur_pajak_print_xls, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'datetime': datetime,
            'wanted_list_overview': self.pool.get('wtc.faktur.pajak.out')._report_xls_faktur_pajak_fields(cr, uid, context),
            '_': self._,
        })

    def _(self, src):
        lang = self.context.get('lang', 'en_US')
        return translate(self.cr, 'report.faktur_pajak', 'report', lang, src) or src

class report_faktur_pajak_xls(report_xls):

    def __init__(self, name, table, rml=False, parser=False, header=True, store=False):
        super(report_faktur_pajak_xls, self).__init__(name, table, rml, parser, header, store)

        # Cell Styles
        _xs = self.xls_styles

        # Report Column Headers format
        rh_cell_format = _xs['bold'] + _xs['fill'] + _xs['borders_all']
        self.rh_cell_style = xlwt.easyxf(rh_cell_format)
        self.rh_cell_style_center = xlwt.easyxf(rh_cell_format + _xs['center'])
        self.rh_cell_style_right = xlwt.easyxf(rh_cell_format + _xs['right'])

        # Partner Column Headers format
        fill_blue = 'pattern: pattern solid, fore_color 27;'
        ph_cell_format = _xs['bold'] + _xs['fill'] + _xs['borders_all']
        self.ph_cell_style = xlwt.easyxf(ph_cell_format)
        self.ph_cell_style_decimal = xlwt.easyxf(ph_cell_format + _xs['right'], num_format_str=report_xls.decimal_format)
        
        # Partner Column Data format
        pd_cell_format = _xs['borders_all']
        self.pd_cell_style = xlwt.easyxf(pd_cell_format)
        self.pd_cell_style_center = xlwt.easyxf(pd_cell_format + _xs['center'])
        self.pd_cell_style_date = xlwt.easyxf(pd_cell_format + _xs['left'], num_format_str=report_xls.date_format)
        self.pd_cell_style_decimal = xlwt.easyxf(pd_cell_format + _xs['right'], num_format_str=report_xls.decimal_format)

        # totals
        rt_cell_format = _xs['bold'] + _xs['fill'] + _xs['borders_all']
        self.rt_cell_style = xlwt.easyxf(rt_cell_format)
        self.rt_cell_style_right = xlwt.easyxf(rt_cell_format + _xs['right'])
        self.rt_cell_style_decimal = xlwt.easyxf(rt_cell_format + _xs['right'], num_format_str=report_xls.decimal_format)

        # XLS Template
        self.col_specs_template_overview = {
            'no': {
                'header': [1, 5, 'text', _render("_('No')")],
                'lines': [1, 0, 'number', _render("p['no']")],
                'totals': [1, 5, 'number', None]},
            'code_pajak': {
                'header': [1, 22, 'text', _render("_('Code Pajak')")],
                'lines': [1, 0, 'text', _render("p['code_pajak']")],
                'totals': [1, 22, 'text', _render("_('code_pajak')")]},
            
            'form_name': {
                'header': [1, 22, 'text', _render("_('Form Name')")],
                'lines': [1, 0, 'text', _render("p['form_name']")],
                'totals': [1, 22, 'number', None]},
            'pajak_gabungan': {
                'header': [1, 15, 'text', _render("_('Pajak Gabungan')")],
                'lines': [1, 0, 'text', _render("p['pajak_gabungan']")],
                'totals': [1, 22, 'text', _render("_('Total')")]},
            'partner_code': {
                'header': [1, 22, 'text', _render("_('Partner Code')")],
                'lines': [1, 0, 'text', _render("p['partner_code']")],
                'totals': [1, 22, 'text', _render("_('Total')")]},
            'partner_name': {
                'header': [1, 22, 'text', _render("_('Partner Name')")],
                'lines': [1, 0, 'text', _render("p['partner_name']")],
                'totals': [1, 22, 'number', None]},
            'date': {
                'header': [1, 10, 'text', _render("_('Tgl Transaksi')")],
                'lines': [1, 0, 'text', _render("p['date']")],
                'totals': [1, 22, 'number', None]},
            'tgl_terbit': {
                'header': [1, 10, 'text', _render("_('Tgl Terbit')")],
                'lines': [1, 0, 'text', _render("p['tgl_terbit']")],
                'totals': [1, 22, 'number', None]},
            'thn_penggunaan': {
                'header': [1, 10, 'text', _render("_('Tahun')")],
                'lines': [1, 0, 'number', _render("p['thn_penggunaan']")],
                'totals': [1, 22, 'number', None]},
            'cetak_ke': {
                'header': [1, 10, 'text', _render("_('Cetak Ke')")],
                'lines': [1, 0, 'number', _render("p['cetak_ke']")],
                'totals': [1, 22, 'number', None]},
            'state': {
                'header': [1, 10, 'text', _render("_('State')")],
                'lines': [1, 0, 'text', _render("p['state']")],
                'totals': [1, 22, 'number', None]},                                            
            'untaxed_amount': {
                'header': [1, 22, 'text', _render("_('Untaxed Amount')")],
                'lines': [1, 0, 'number', _render("p['untaxed_amount']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', None]},
            'tax_amount': {
                'header': [1, 22, 'text', _render("_('Tax Amount')")],
                'lines': [1, 0, 'number', _render("p['tax_amount']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', None]},
            'amount_total': {
                'header': [1, 22, 'text', _render("_('Amount Total')")],
                'lines': [1, 0, 'number', _render("p['amount_total']"), None, self.pd_cell_style_decimal],
                'totals': [1, 22, 'number', None]},
        }

    def generate_xls_report(self, _p, _xs, data, objects, wb):
        wanted_list_overview = _p.wanted_list_overview
        self.col_specs_template_overview.update({})
        _ = _p._

        for r in _p.reports:
            ws_o = wb.add_sheet('Laporan Faktur Pajak')
            
            for ws in [ws_o]:
                ws.panes_frozen = True
                ws.remove_splits = True
                ws.portrait = 0  # Landscape
                ws.fit_width_to_pages = 1
            row_pos_o = 0

            # set print header/footer
            for ws in [ws_o]:
                ws.header_str = self.xls_headers['standard']
                ws.footer_str = self.xls_footers['standard']

            # Company Name
            cell_style = xlwt.easyxf(_xs['left'])
            c_specs_o = [('report_name', 1, 0, 'text', _p.company.name)]
            row_data = self.xls_row_template(c_specs_o, ['report_name'])
            row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=cell_style)
            
            # Title
            cell_style = xlwt.easyxf(_xs['xls_title'])
            c_specs_o = [('report_name', 1, 0, 'text', 'Laporan Faktur Pajak')]
            row_data = self.xls_row_template(c_specs_o, ['report_name'])
            row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=cell_style)
            
            # Start Date & End Date
            cell_style = xlwt.easyxf(_xs['left'])
            report_name = ' '.join([_('Tanggal'), _('-' if data['start_date'] == False else str(data['start_date'])), _('s/d'), _('-' if data['end_date'] == False else str(data['end_date']))])
            c_specs_o = [('report_name', 1, 0, 'text', report_name)]
            row_data = self.xls_row_template(c_specs_o, ['report_name'])
            row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=cell_style)
            row_pos_o += 1
            
            # Report Column Headers
            c_specs_o = map(lambda x: self.render(x, self.col_specs_template_overview, 'header', render_space={'_': _p._}), wanted_list_overview)
            row_data = self.xls_row_template(c_specs_o, [x[0] for x in c_specs_o])
            row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=self.rh_cell_style, set_column_size=True)
            ws_o.set_horz_split_pos(row_pos_o)
            
            row_data_begin = row_pos_o
            
            # Columns and Rows
            no = 0
            for p in r['datas']:
                c_specs_o = map(lambda x: self.render(x, self.col_specs_template_overview, 'lines'), wanted_list_overview)
                for x in c_specs_o :
                    if x[0] == 'no' :
                        no += 1
                        x[4] = no
                row_data = self.xls_row_template(c_specs_o, [x[0] for x in c_specs_o])
                row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=self.pd_cell_style)
            
            row_data_end = row_pos_o
            
            # Totals
            ws_o.write(row_pos_o, 0, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 1, 'Totals', self.ph_cell_style)   
            ws_o.write(row_pos_o, 2, None, self.rt_cell_style_decimal)
            ws_o.set_vert_split_pos(3)
            ws_o.write(row_pos_o, 3, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 4, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 5, None, self.rt_cell_style_decimal)   
            ws_o.write(row_pos_o, 6, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 7, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 8, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 9, None, self.rt_cell_style_decimal)   
            ws_o.write(row_pos_o, 10, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 11, xlwt.Formula("SUM(L"+str(row_data_begin)+":L"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 12, xlwt.Formula("SUM(M"+str(row_data_begin)+":M"+str(row_data_end)+")"), self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 13, xlwt.Formula("SUM(N"+str(row_data_begin)+":N"+str(row_data_end)+")"), self.rt_cell_style_decimal)
             
            # Footer
            ws_o.write(row_pos_o + 1, 0, None)
            ws_o.write(row_pos_o + 2, 0, time.strftime('%Y-%m-%d %H:%M:%S') + ' ' + str(self.pool.get('res.users').browse(self.cr, self.uid, self.uid).name))

report_faktur_pajak_xls('report.Laporan Faktur Pajak', 'wtc.faktur.pajak', parser = wtc_report_faktur_pajak_print_xls)
