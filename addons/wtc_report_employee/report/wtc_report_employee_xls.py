import xlwt
from datetime import datetime
import time
from openerp.osv import orm
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
from .wtc_report_employee import wtc_report_employee_print
from openerp.tools.translate import translate
import string

class wtc_report_employee_print_xls(wtc_report_employee_print):

    def __init__(self, cr, uid, name, context):
        super(wtc_report_employee_print_xls, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'datetime': datetime,
            'wanted_list_overview': self.pool.get('hr.employee')._report_xls_employee_fields(cr, uid, context),
            '_': self._,
        })

    def _(self, src):
        lang = self.context.get('lang', 'en_US')
        return translate(self.cr, 'report.employee', 'report', lang, src) or src

class report_employee_xls(report_xls):

    def __init__(self, name, table, rml=False, parser=False, header=True, store=False):
        super(report_employee_xls, self).__init__(name, table, rml, parser, header, store)

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
                'header': [1, 7, 'text', _render("_('No')")],
                'lines': [1, 0, 'number', _render("p['no']")],
                'totals': [1, 7, 'number', None]},
            'branch_code': {
                'header': [1, 22, 'text', _render("_('Branch Code')")],
                'lines': [1, 0, 'text', _render("p['branch_code']")],
                'totals': [1, 22, 'number', None]},
            'branch_name': {
                'header': [1, 22, 'text', _render("_('Branch Name')")],
                'lines': [1, 0, 'text', _render("p['branch_name']")],
                'totals': [1, 22, 'number', None]},
            'area_code': {
                'header': [1, 22, 'text', _render("_('Area Code')")],
                'lines': [1, 0, 'text', _render("p['area_code']")],
                'totals': [1, 22, 'number', None]},
            'area_desc': {
                'header': [1, 22, 'text', _render("_('Area Description')")],
                'lines': [1, 0, 'text', _render("p['area_desc']")],
                'totals': [1, 22, 'number', None]},
            'employee_nip': {
                'header': [1, 22, 'text', _render("_('NIP')")],
                'lines': [1, 0, 'text', _render("p['employee_nip']")],
                'totals': [1, 22, 'number', None]},
            'resource_name': {
                'header': [1, 30, 'text', _render("_('Name')")],
                'lines': [1, 0, 'text', _render("p['resource_name']")],
                'totals': [1, 30, 'number', None]},
            'employee_street': {
                'header': [1, 30, 'text', _render("_('Street')")],
                'lines': [1, 0, 'text', _render("p['employee_street']")],
                'totals': [1, 30, 'number', None]},
            'employee_street2': {
                'header': [1, 30, 'text', _render("_('Street 2')")],
                'lines': [1, 0, 'text', _render("p['employee_street2']")],
                'totals': [1, 30, 'number', None]},
            'rt': {
                'header': [1, 22, 'text', _render("_('RT')")],
                'lines': [1, 0, 'text', _render("p['rt']")],
                'totals': [1, 22, 'number', None]},
            'rw': {
                'header': [1, 22, 'text', _render("_('RW')")],
                'lines': [1, 0, 'text', _render("p['rw']")],
                'totals': [1, 22, 'number', None]},
            'province': {
                'header': [1, 22, 'text', _render("_('Province')")],
                'lines': [1, 0, 'text', _render("p['province']")],
                'totals': [1, 22, 'number', None]},
            'city': {
                'header': [1, 22, 'text', _render("_('City')")],
                'lines': [1, 0, 'text', _render("p['city']")],
                'totals': [1, 22, 'number', None]},
            'kecamatan': {
                'header': [1, 22, 'text', _render("_('Kecamatan')")],
                'lines': [1, 0, 'text', _render("p['kecamatan']")],
                'totals': [1, 22, 'number', None]},
            'kelurahan': {
                'header': [1, 22, 'text', _render("_('Kelurahan')")],
                'lines': [1, 0, 'text', _render("p['kelurahan']")],
                'totals': [1, 22, 'number', None]},
            'job_name': {
                'header': [1, 30, 'text', _render("_('Job Name')")],
                'lines': [1, 0, 'text', _render("p['job_name']")],
                'totals': [1, 30, 'number', None]},
            'group_name': {
                'header': [1, 22, 'text', _render("_('Group Name')")],
                'lines': [1, 0, 'text', _render("p['group_name']")],
                'totals': [1, 22, 'number', None]},
            'tgl_masuk': {
                'header': [1, 22, 'text', _render("_('Tgl Masuk')")],
                'lines': [1, 0, 'text', _render("p['tgl_masuk']")],
                'totals': [1, 22, 'number', None]},
            'tgl_keluar': {
                'header': [1, 22, 'text', _render("_('Tgl Keluar')")],
                'lines': [1, 0, 'text', _render("p['tgl_keluar']")],
                'totals': [1, 22, 'number', None]},
            'created_by': {
                'header': [1, 22, 'text', _render("_('Created By')")],
                'lines': [1, 0, 'text', _render("p['created_by']")],
                'totals': [1, 22, 'number', None]},
            'created_date': {
                'header': [1, 30, 'text', _render("_('Created On')")],
                'lines': [1, 0, 'text', _render("p['created_date']")],
                'totals': [1, 30, 'number', None]},
            'updated_by': {
                'header': [1, 22, 'text', _render("_('Last Updated By')")],
                'lines': [1, 0, 'text', _render("p['updated_by']")],
                'totals': [1, 22, 'number', None]},
            'updated_date': {
                'header': [1, 30, 'text', _render("_('Last Updated On')")],
                'lines': [1, 0, 'text', _render("p['updated_date']")],
                'totals': [1, 30, 'number', None]},
        }

    def generate_xls_report(self, _p, _xs, data, objects, wb):
        wanted_list_overview = _p.wanted_list_overview
        self.col_specs_template_overview.update({})
        _ = _p._

        for r in _p.reports:
            ws_o = wb.add_sheet('Report Employee')
            
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
            c_specs_o = [('report_name', 1, 0, 'text', 'Report Employee')]
            row_data = self.xls_row_template(c_specs_o, ['report_name'])
            row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=cell_style)
            
            # Tanggal
            cell_style = xlwt.easyxf(_xs['left'])
            report_name = ' '.join([_('Per Tanggal'), _(time.strftime('%Y-%m-%d %H:%M:%S') if data['date'] == False else str(data['date']))])
            c_specs_o = [('report_name', 1, 0, 'text', report_name)]
            row_data = self.xls_row_template(c_specs_o, ['report_name'])
            row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=cell_style)
            row_pos_o += 1
            
            # Report Column Headers
            c_specs_o = map(lambda x: self.render(x, self.col_specs_template_overview, 'header', render_space={'_': _p._}), wanted_list_overview)
            row_data = self.xls_row_template(c_specs_o, [x[0] for x in c_specs_o])
            row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=self.rh_cell_style, set_column_size=True)
            ws_o.set_horz_split_pos(row_pos_o)
            
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
            
            # Footer
            ws_o.write(row_pos_o + 1, 0, time.strftime('%Y-%m-%d %H:%M:%S') + ' ' + str(self.pool.get('res.users').browse(self.cr, self.uid, self.uid).name))

report_employee_xls('report.Report Employee', 'hr.employee', parser = wtc_report_employee_print_xls)
