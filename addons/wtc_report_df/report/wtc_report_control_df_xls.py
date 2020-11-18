import xlwt
from datetime import datetime
from openerp.osv import orm
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
from .wtc_report_control_df import wtc_report_control_df_print
from openerp.tools.translate import translate
import logging
_logger = logging.getLogger(__name__)

_ir_translation_name = 'wtc.report.control.df'


class wtc_report_control_df_print_xls(wtc_report_control_df_print):

    def __init__(self, cr, uid, name, context):
        super(wtc_report_control_df_print_xls, self).__init__(
            cr, uid, name, context=context)
        partner_obj = self.pool.get('wtc.stock.packing')
        self.context = context
        wl_overview = partner_obj._report_xls_arap_overview_fields(
            cr, uid, context)
        tmpl_upd_overview = partner_obj._report_xls_arap_overview_template(
            cr, uid, context)
        wl_details = partner_obj._report_xls_arap_details_fields(
            cr, uid, context)
        tmpl_upd_details = partner_obj._report_xls_arap_overview_template(
            cr, uid, context)
        self.localcontext.update({
            'datetime': datetime,
            'wanted_list_overview': wl_overview,
            'template_update_overview': tmpl_upd_overview,
            'wanted_list_details': wl_details,
            'template_update_details': tmpl_upd_details,
            '_': self._,
        })

    def _(self, src):
        lang = self.context.get('lang', 'en_US')
        return translate(
            self.cr, _ir_translation_name, 'report', lang, src) or src


class partner_open_arap_xls(report_xls):

    def __init__(self, name, table, rml=False,
                 parser=False, header=True, store=False):
        super(partner_open_arap_xls, self).__init__(
            name, table, rml, parser, header, store)

        # Cell Styles
        _xs = self.xls_styles
        # header

        # Report Column Headers format
        rh_cell_format = _xs['bold'] + _xs['fill'] + _xs['borders_all']
        self.rh_cell_style = xlwt.easyxf(rh_cell_format)
        self.rh_cell_style_center = xlwt.easyxf(
            rh_cell_format + _xs['center'])
        self.rh_cell_style_right = xlwt.easyxf(rh_cell_format + _xs['right'])

        # Partner Column Headers format
        fill_blue = 'pattern: pattern solid, fore_color 27;'
        ph_cell_format = _xs['bold'] + fill_blue + _xs['borders_all']
        self.ph_cell_style = xlwt.easyxf(ph_cell_format)
        self.ph_cell_style_decimal = xlwt.easyxf(
            ph_cell_format + _xs['right'],
            num_format_str=report_xls.decimal_format)

        # Partner Column Data format
        pd_cell_format = _xs['borders_all']
        self.pd_cell_style = xlwt.easyxf(pd_cell_format)
        self.pd_cell_style_center = xlwt.easyxf(
            pd_cell_format + _xs['center'])
        self.pd_cell_style_date = xlwt.easyxf(
            pd_cell_format + _xs['left'],
            num_format_str=report_xls.date_format)
        self.pd_cell_style_decimal = xlwt.easyxf(
            pd_cell_format + _xs['right'],
            num_format_str=report_xls.decimal_format)
        

        # totals
        rt_cell_format = _xs['bold'] + _xs['fill'] + _xs['borders_all']
        self.rt_cell_style = xlwt.easyxf(rt_cell_format)
        self.rt_cell_style_right = xlwt.easyxf(rt_cell_format + _xs['right'])
        self.rt_cell_style_decimal = xlwt.easyxf(
            rt_cell_format + _xs['right'],
            num_format_str=report_xls.decimal_format)

        # XLS Template
        self.col_specs_template_overview = {
            'code': {
                'header': [1, 10, 'text', _render("_('Code')")],
                'lines': [1, 0, 'text', _render("p['p_name'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'no_transaksi': {
                'header': [1, 22, 'text', _render("_('No Transaksi')")],
                'lines': [1, 0, 'text', _render("p['p_ref'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'kode_cabang': {
                'header': [1, 22, 'text', _render("_('Kode Cabang')")],
                'lines': [1, 0, 'text', _render("p['kode_cabang'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'nama_branch': {
                'header': [1, 22, 'text', _render("_('Nama Dealer')")],
                'lines': [1, 0, 'text', _render("p['nama_branch'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'no_invoice': {
                'header': [1, 22, 'text', _render("_('No Invoice')")],
                'lines': [1, 0, 'text', _render("p['no_invoice'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'tanggal_invoice': {
                'header': [1, 22, 'text', _render("_('Tanggal Invoice')")],
                'lines': [1, 0, 'text', _render("p['tanggal_invoice'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'date_due': {
                'header': [1, 22, 'text', _render("_('Tanggal JTP')")],
                'lines': [1, 0, 'text', _render("p['date_due'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
            'amount_total': {
                'header': [1, 20, 'text', _render("_('Amount Total')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'number', _render("p['amount_total']"),None,self.pd_cell_style_decimal],
                'totals': [1, 0, 'text', None]},
            'qty_invoice': {
                'header': [1, 20, 'text', _render("_('Qty Invoice')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'number', _render("p['qty_invoice']"),None,self.pd_cell_style_decimal],
                'totals': [1, 0, 'text', None]},
            'qty_sj': {
                'header': [1, 20, 'text', _render("_('Qty Surat Jalan')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'number', _render("p['qty_sj']"),None,self.pd_cell_style_decimal],
                'totals': [1, 0, 'text', None]},
            'tanggal_picking': {
                'header': [1, 22, 'text', _render("_('Tanggal Picking')")],
                'lines': [1, 0, 'text', _render("p['tanggal_picking'] or 'n/a'")],
                'totals': [1, 0, 'text', None]},
        }

        # XLS Template
        self.col_specs_template_details = {
            'code': {
                'header1': [1, 10, 'text', _render("_('Code')")],
                'header2': [1, 0, 'text', _render("p['p_name'] or 'n/a'")],
                'lines': [1, 0, 'text', None],
                'totals1': [1, 0, 'text', None],
                'totals2': [1, 0, 'text', None]},
            
            'no_transaksi': {
                'header1': [1, 20, 'text', _render("_('No Transaksi')")],
                'header2': [1, 0, 'text', _render("p['no_transaksi'] or 'n/a'")],
                'lines': [1, 0, 'text', None],
                'totals1': [1, 0, 'text', None],
                'totals2': [1, 0, 'text', None]},
            
            
            'kode_cabang': {
                'header1': [1,  0, 'text', _render("_('Kode Cabang')")],
                'header2': [1, 0, 'text', _render("p['kode_cabang'] or 'n/a'")],
                'lines': [1, 0, 'text', None],
                'totals1': [1, 0, 'text', None],
                'totals2': [1, 0, 'text', None]},
                                           
            'nama_branch': {
                'header1': [1, 30, 'text', _render("_('Nama Dealer')")],
                'header2': [1, 0, 'text', _render("p['nama_branch'] or 'n/a'")],
                'lines': [1, 0, 'text', None],
                'totals1': [1, 0, 'text', None],
                'totals2': [1, 0, 'text', None]},
                                           
            'no_invoice': {
                'header1': [1, 20, 'text', _render("_('No Invoice')")],
                'header2': [1, 0, 'text', _render("p['no_invoice'] or 'n/a'")],
                'lines': [1, 0, 'text', None],
                'totals1': [1, 0, 'text', None],
                'totals2': [1, 0, 'text', None]},
                                           
            'tanggal_invoice': {
                'header1': [1, 20, 'text', _render("_('Tanggal Invoice')")],
                'header2': [1, 0, 'text', _render("p['tanggal_invoice'] or 'n/a'")],
                'lines': [1, 0, 'text', None],
                'totals1': [1, 0, 'text', None],
                'totals2': [1, 0, 'text', None]},
                                           
            'date_due': {
                'header1': [1, 20, 'text', _render("_('Tanggal JTP')")],
                'header2': [1, 0, 'text', _render("p['date_due'] or 'n/a'")],
                'lines': [1, 0, 'text', None],
                'totals1': [1, 0, 'text', None],
                'totals2': [1, 0, 'text', None]},
            
            'amount_total': {
                'header1': [1, 20, 'text', _render("_('Amount Total')"),None,self.rh_cell_style_center],
                'header2': [1, 0, 'text', _render("p['amount_total'] or 'n/a'")],
                'lines': [1, 0, 'text', None],
                'totals1': [1, 0, 'text', None],
                'totals2': [1, 0, 'text', None]},
                                           
            'qty_invoice': {
                'header1': [1, 20, 'text', _render("_('Total Invoice')"),None,self.rh_cell_style_center],
                'header2': [1, 0, 'text', _render("p['qty_invoice'] or 'n/a'")],
                'lines': [1, 0, 'text', None],
                'totals1': [1, 0, 'text', None],
                'totals2': [1, 0, 'text', None]},
                                           
                                           
            'qty_sj': {
                'header1': [1, 20, 'text', _render("_('Qty Surat Jalan')"),None,self.rh_cell_style_center],
                'header2': [1, 0, 'text', _render("p['qty_sj'] or 'n/a'")],
                'lines': [1, 0, 'text', None],
                'totals1': [1, 0, 'text', None],
                'totals2': [1, 0, 'text', None]},
                                           
            
            'tanggal_picking': {
                'header1': [1, 20, 'text', _render("_('Tanggal Picking')"),None,self.rh_cell_style_center],
                'header2': [1, 0, 'text', _render("p['tanggal_picking'] or 'n/a'")],
                'lines': [1, 0, 'text', None],
                'totals1': [1, 0, 'text', None],
                'totals2': [1, 0, 'text', None]},
                                           
            'no_picking': {
                'header1': [
                    1, 25, 'text',
                    _render("_('No Picking')"), None,
                    self.rh_cell_style_center],
                'header2': [
                    1, 0, 'text', None,
                    None,
                    self.ph_cell_style_decimal],
                'lines': [
                    1, 0, 'text',
                    _render("p['no_picking']"), None,
                    self.pd_cell_style_decimal],
                'totals1': [1, 0, 'text', _render("_('Debit')")],
                'totals2': [
                    1, 0, 'number', None,
                    _render("debit_formula"),
                    self.rt_cell_style_decimal]},
                                           
            'no_packing': {
                'header1': [
                    1, 25, 'text',
                    _render("_('No Packing')"), None,
                    self.rh_cell_style_center],
                'header2': [
                    1, 0, 'text', None,
                    None,
                    self.ph_cell_style_decimal],
                'lines': [
                    1, 0, 'text',
                    _render("p['no_packing']"), None,
                    self.pd_cell_style_decimal],
                'totals1': [1, 0, 'text', _render("_('Debit')")],
                'totals2': [
                    1, 0, 'number', None,
                    _render("debit_formula"),
                    self.rt_cell_style_decimal]},
                                           
            'no_mesin': {
                'header1': [
                    1, 25, 'text',
                    _render("_('No Mesin')"), None,
                    self.rh_cell_style_center],
                'header2': [
                    1, 0, 'text', None,
                    None,
                    self.ph_cell_style_decimal],
                'lines': [
                    1, 0, 'text',
                    _render("p['no_mesin']"), None,
                    self.pd_cell_style_decimal],
                'totals1': [1, 0, 'text', _render("_('Debit')")],
                'totals2': [
                    1, 0, 'number', None,
                    _render("debit_formula"),
                    self.rt_cell_style_decimal]},
                                           
            
            'no_chassis': {
                'header1': [
                    1, 25, 'text',
                    _render("_('No Chassis')"), None,
                    self.rh_cell_style_center],
                'header2': [
                    1, 0, 'text', None,
                    None,
                    self.ph_cell_style_decimal],
                'lines': [
                    1, 0, 'text',
                    _render("p['no_chassis']"), None,
                    self.pd_cell_style_decimal],
                'totals1': [1, 0, 'text', _render("_('Debit')")],
                'totals2': [
                    1, 0, 'number', None,
                    _render("debit_formula"),
                    self.rt_cell_style_decimal]},                          
        }

    def generate_xls_report(self, _p, _xs, data, objects, wb):
        username = self.pool.get('res.users').browse(self.cr,self.uid,self.uid).name
        wanted_list_overview = _p.wanted_list_overview
        wanted_list_details = _p.wanted_list_details
        self.col_specs_template_overview.update(_p.template_update_overview)
        self.col_specs_template_details.update(_p.template_update_details)
        _ = _p._
        # TODO : adapt to allow rendering space extensions by inherited module
        # add objects to the render space for use in custom reports
        partner_obj = self.pool.get('res.partner')  # noqa: disable F841, report_xls namespace trick
        address_obj = self.pool.get('res.partner.address')  # noqa: disable F841, report_xls namespace trick

        for wl in [wanted_list_overview, wanted_list_details]:
            debit_pos = 'debit' in wl and wl.index('debit')
            credit_pos = 'credit' in wl and wl.index('credit')
            if not (credit_pos and debit_pos) and 'balance' in wl:
                raise orm.except_orm(
                    _('Customisation Error!'),
                    _("The 'Balance' field is a calculated XLS field "
                      "requiring the presence of "
                      "the 'Debit' and 'Credit' fields !"))

        for r in _p.reports:
            title_short = r['title_short'].replace('/', '-')
            ws_o = wb.add_sheet(title_short)
            ws_d = wb.add_sheet((title_short + ' ' + _('Details'))[:31])
            for ws in [ws_o, ws_d]:
                ws.panes_frozen = True
                ws.remove_splits = True
                ws.portrait = 0  # Landscape
                ws.fit_width_to_pages = 1
            row_pos_o = 0
            row_pos_d = 0

            # set print header/footer
            for ws in [ws_o, ws_d]:
                ws.header_str = self.xls_headers['standard']
                ws.footer_str = self.xls_footers['standard']

            # Title
            cell_style = xlwt.easyxf(_xs['xls_title'])
            report_name = '  -  '.join(
                [_p.company.name, r['title']])
            c_specs_o = [
                ('report_name', 1, 0, 'text', report_name),
            ]
            
            row_data = self.xls_row_template(c_specs_o, ['report_name'])
            row_pos_o = self.xls_write_row(
                ws_o, row_pos_o, row_data, row_style=cell_style)
            row_pos_o += 1
            
            
            report_name = '  -  '.join(
                [_p.company.name, r['title'], _('Details')])
            c_specs_d = [
                ('report_name', 1, 0, 'text', report_name),
            ]
            row_data = self.xls_row_template(c_specs_d, ['report_name'])
            row_pos_d = self.xls_write_row(
                ws_d, row_pos_d, row_data, row_style=cell_style)
            row_pos_d += 1
            

            
            

            # Report Column Headers
            c_specs_o = map(
                lambda x: self.render(
                    x, self.col_specs_template_overview, 'header',
                    render_space={'_': _p._}),
                wanted_list_overview)
            row_data = self.xls_row_template(
                c_specs_o, [x[0] for x in c_specs_o])
            row_pos_o = self.xls_write_row(
                ws_o, row_pos_o, row_data, row_style=self.rh_cell_style,
                set_column_size=True)
            ws_o.set_horz_split_pos(row_pos_o)

            c_specs_d = map(
                lambda x: self.render(
                    x, self.col_specs_template_details, 'header1',
                    render_space={'_': _p._}),
                wanted_list_details)
            row_data = self.xls_row_template(
                c_specs_d, [x[0] for x in c_specs_d])
            row_pos_d = self.xls_write_row(
                ws_d, row_pos_d, row_data, row_style=self.rh_cell_style,
                set_column_size=True)
            ws_d.set_horz_split_pos(row_pos_d)
            row_pos_d += 1
            partner_debit_cells = []
            partner_credit_cells = []
            
            if r['partners'] != 'null' :
                for p in r['partners']:
                    debit_cell_o = rowcol_to_cell(row_pos_o, 2)
                    credit_cell_o = rowcol_to_cell(row_pos_o, 3)
                    bal_formula_o = debit_cell_o + '-' + credit_cell_o  # noqa: disable F841, report_xls namespace trick
                    c_specs_o = map(
                        lambda x: self.render(
                            x, self.col_specs_template_overview, 'lines'),
                        wanted_list_overview)
                    row_data = self.xls_row_template(
                        c_specs_o, [x[0] for x in c_specs_o])
                    row_pos_o = self.xls_write_row(
                        ws_o, row_pos_o, row_data, row_style=self.pd_cell_style)
    
                    row_pos_d += 1
    
                    debit_cell_d = rowcol_to_cell(row_pos_d, 6)
                    credit_cell_d = rowcol_to_cell(row_pos_d, 7)
                    partner_debit_cells.append(debit_cell_d)
                    partner_credit_cells.append(credit_cell_d)
                    bal_formula_d = debit_cell_d + '-' + credit_cell_d  # noqa: disable F841, report_xls namespace trick
    
                    line_cnt = len(p['lines'])
                    debit_start = rowcol_to_cell(row_pos_d + 1, 6)
                    debit_stop = rowcol_to_cell(row_pos_d + line_cnt, 6)
                    debit_formula = 'SUM(%s:%s)' % (debit_start, debit_stop)
                    credit_start = rowcol_to_cell(row_pos_d + 1, 7)
                    credit_stop = rowcol_to_cell(row_pos_d + line_cnt, 7)
                    credit_formula = 'SUM(%s:%s)' % (credit_start, credit_stop)
                    c_specs_d = map(
                        lambda x: self.render(
                            x, self.col_specs_template_details, 'header2'),
                        wanted_list_details)
                    row_data = self.xls_row_template(
                        c_specs_d, [x[0] for x in c_specs_d])
                    row_pos_d = self.xls_write_row(
                        ws_d, row_pos_d, row_data, row_style=self.ph_cell_style)
    
                    for l in p['lines']:
    
                        debit_cell = rowcol_to_cell(row_pos_d, 6)
                        credit_cell = rowcol_to_cell(row_pos_d, 7)
                        bal_formula = debit_cell + '-' + credit_cell
                        c_specs_d = map(
                            lambda x: self.render(
                                x, self.col_specs_template_details, 'lines'),
                            wanted_list_details)
                        row_data = self.xls_row_template(
                            c_specs_d, [x[0] for x in c_specs_d])
                        row_pos_d = self.xls_write_row(
                            ws_d, row_pos_d, row_data,
                            row_style=self.pd_cell_style)


partner_open_arap_xls(
    'report.wtc.report.control.df.xls',
    'account.period',
    parser=wtc_report_control_df_print_xls)
