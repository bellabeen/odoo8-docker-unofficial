import xlwt
from xlwt import *
from datetime import datetime
from openerp.osv import orm
from openerp import tools
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
from .wtc_report_trial_balance_import_sun import wtc_trial_balance_import_sun_report_print
from openerp.tools.translate import translate
import logging
_logger = logging.getLogger(__name__)
import time

_ir_translation_name = 'wtc.report.trial.balance'

class wtc_trial_balance_import_sun_print_xls(wtc_trial_balance_import_sun_report_print):

    def __init__(self, cr, uid, name, context):
        super(wtc_trial_balance_import_sun_print_xls, self).__init__(
            cr, uid, name, context=context)
        moveline_obj = self.pool.get('account.move.line')
        self.context = context
        wl_overview = moveline_obj._report_xls_trial_balance_import_sun_fields(
            cr, uid, context)
        tmpl_upd_overview = moveline_obj._report_xls_arap_overview_template(
            cr, uid, context)
        wl_details = moveline_obj._report_xls_arap_details_fields(
            cr, uid, context)
        tmpl_upd_details = moveline_obj._report_xls_arap_overview_template(
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


class trial_balance_import_sun_report_xls(report_xls):

    def __init__(self, name, table, rml=False,
                 parser=False, header=True, store=False):
        super(trial_balance_import_sun_report_xls, self).__init__(
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
        ph_cell_format = _xs['bold'] + _xs['fill'] + _xs['borders_all']
        self.ph_cell_style = xlwt.easyxf(ph_cell_format)
        self.ph_cell_style_center = xlwt.easyxf(ph_cell_format  + _xs['center'] )
        self.ph_cell_style_decimal = xlwt.easyxf(
            ph_cell_format + _xs['right'],
            num_format_str=report_xls.decimal_format)
        self.rh_cell_style_center_blue = xlwt.easyxf(
            _xs['bold'] + fill_blue + _xs['borders_all'] + _xs['center'])
        
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
        self.pd_cell_style_decimal_fill = xlwt.easyxf(
            pd_cell_format + _xs['right'] + _xs['fill'] + _xs['bold'] ,
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
            'no': {
                'header': [1, 5, 'text', _render("_('No')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'number', _render("p['no']"),None,self.pd_cell_style_center],
                'totals': [1, 5, 'text', None]},                                             
            'branch_code': {
                'header': [1, 15, 'text', _render("_('Cab')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['branch_code'] or ''")],
                'totals': [1, 0, 'text', None]},  
            'account_code': {
                'header': [1, 20, 'text', _render("_('No Rek')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['account_code'] or ''")],
                'totals': [1, 0, 'text', None]},                                              
            'account': {
                'header': [1, 10, 'text', _render("_('Account')"),None,self.rh_cell_style_center_blue],
                'lines': [1, 0, 'text', _render("p['account'] or ''")],
                'totals': [1, 0, 'text', None]},  
            'profit_centre': {
                'header': [1, 15, 'text', _render("_('Profit Center')"),None,self.rh_cell_style_center_blue],
                'lines': [1, 0, 'text', _render("p['profit_centre'] or ''")],
                'totals': [1, 0, 'text', None]},                                  
            'div': {
                'header': [1, 10, 'text', _render("_('Div')"),None,self.rh_cell_style_center_blue],
                'lines': [1, 0, 'text', _render("p['div'] or ''")],
                'totals': [1, 0, 'text', None]},  
            'dept': {
                'header': [1, 10, 'text', _render("_('Dept')"),None,self.rh_cell_style_center_blue],
                'lines': [1, 20, 'text', _render("p['dept'] or ''")],
                'totals': [1, 0, 'text', None]},  
            'class': {
                'header': [1, 10, 'text', _render("_('Class')"),None,self.rh_cell_style_center_blue],
                'lines': [1, 0, 'text', _render("p['class'] or ''")],
                'totals': [1, 0, 'text', None]},  
            'type': {
                'header': [1, 10, 'text', _render("_('Type')"),None,self.rh_cell_style_center_blue],
                'lines': [1, 0, 'text', _render("p['type'] or ''")],
                'totals': [1, 0, 'text', None]},  
            'account_name': {
                'header': [1, 35, 'text', _render("_('Keterangan')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['account_name'] or ''")],
                'totals': [1, 0, 'text', None]},                                              
            'transaction_amount': {
                'header': [1, 20, 'text', _render("_('Transaction Amount')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'number', _render("p['transaction_amount']"),None,self.pd_cell_style_decimal],
                'totals': [1, 0, 'text', None]},  
            'date_stop': {
                'header': [1, 18, 'text', _render("_('Transaction Date')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("p['date_stop'] or ''")],
                'totals': [1, 0, 'text', None]},                                  
            'trans_reference': {
                'header': [1, 15, 'text', _render("_('Trans Reference')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("_(' ')")],
                'totals': [1, 0, 'text', None]},  
            'memo_amount': {
                'header': [1, 15, 'text', _render("_('Memo Amount')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'text', _render("_(' ')")],
                'totals': [1, 0, 'text', None]},  
            'debit': {
                'header': [1, 20, 'text', _render("_('Debit')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'number', _render("p['debit']"),None,self.pd_cell_style_decimal],
                'totals': [1, 0, 'text', None]},   
            'credit': {
                'header': [1, 20, 'text', _render("_('Credit')"),None,self.rh_cell_style_center],
                'lines': [1, 0, 'number', _render("p['credit']"),None,self.pd_cell_style_decimal],
                'totals': [1, 0, 'text', None]},                                                                                                                                                                                                                                                                                                          
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       
        }                                   

        # XLS Template
        self.col_specs_template_details = {
        

        }

    def generate_xls_report(self, _p, _xs, data, objects, wb):

        wanted_list_overview = _p.wanted_list_overview
        wanted_list_details = _p.wanted_list_details
        self.col_specs_template_overview.update(_p.template_update_overview)
        self.col_specs_template_details.update(_p.template_update_details)
        _ = _p._
        
        username = self.pool.get('res.users').browse(self.cr,self.uid,self.uid).name
        for r in _p.reports:
            title_short = r['title_short'].replace('/', '-')
            ws_o = wb.add_sheet(title_short)
           
            for ws in [ws_o]:
                ws.panes_frozen = True
                ws.remove_splits = True
                ws.portrait = 0  # Landscape
                ws.fit_width_to_pages = 1
            row_pos_o = 0
            row_pos_d = 0

            # set print header/footer
            for ws in [ws_o]:
                ws.header_str = self.xls_headers['standard']
                ws.footer_str = self.xls_footers['standard']

            # COMPANY NAME
            cell_style_company = xlwt.easyxf(_xs['left'])
            c_specs_o = [
                ('company_name', 1, 0, 'text', str(_p.company.name)),
            ]
            row_data = self.xls_row_template(c_specs_o, ['company_name'])
            row_pos_o += self.xls_write_row(
                ws_o, row_pos_o, row_data, row_style=cell_style_company)
            
            #TITLE
            cell_style = xlwt.easyxf(_xs['xls_title'])         
            report_name = ' '.join(
                [_('LAPORAN MUTASI PER CABANG')])
            c_specs_o = [
                ('title', 1, 20, 'text', report_name),
            ]
            row_data = self.xls_row_template(c_specs_o, ['title'])
            row_pos_o = self.xls_write_row(
                ws_o, row_pos_o, row_data, row_style=cell_style)
            
            ## Tanggal Start Date & End Date ##
            cell_style = xlwt.easyxf(_xs['left'])
            report_name = ' '.join(
                [_('Tanggal'), _('-' if data['start_date'] == False else str(data['start_date'])), _('s/d'), _('-' if data['end_date'] == False else str(data['end_date'])),
                 _p.report_info])
            c_specs_o = [
                ('report_name', 1, 0, 'text', report_name),
            ]
            row_data = self.xls_row_template(c_specs_o, ['report_name'])
            row_pos_o = self.xls_write_row(
                ws_o, row_pos_o, row_data, row_style=cell_style)
            row_pos_o += 1
            
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
            
            row_data_begin = row_pos_o
            
            no = 0
            for p in r['move_lines']:
                c_specs_o = map(
                    lambda x: self.render(
                        x, self.col_specs_template_overview, 'lines'),
                    wanted_list_overview)
                for x in c_specs_o :
                    if x[0] == 'no' :
                        no += 1
                        x[4] = no                  
                row_data = self.xls_row_template(
                    c_specs_o, [x[0] for x in c_specs_o])
                row_pos_o = self.xls_write_row(
                    ws_o, row_pos_o, row_data, row_style=self.pd_cell_style)

                row_pos_d += 1  
            row_data_end = row_pos_o
                   
            ws_o.write(row_pos_o, 0, None,self.ph_cell_style)
            ws_o.write(row_pos_o, 1, None,self.ph_cell_style)
            ws_o.write(row_pos_o, 2, None,self.ph_cell_style)   
            ws_o.set_vert_split_pos(3)
            ws_o.write(row_pos_o, 3,None,self.ph_cell_style)  
            ws_o.write(row_pos_o, 4,None,self.ph_cell_style)  
            ws_o.write(row_pos_o, 5, None,self.ph_cell_style)
            ws_o.write(row_pos_o, 6, None,self.ph_cell_style) 
            ws_o.write(row_pos_o, 7, None,self.ph_cell_style)
            ws_o.write(row_pos_o, 8, None,self.ph_cell_style)
            ws_o.write(row_pos_o, 9, "Total",self.ph_cell_style) 
            ws_o.write(row_pos_o, 10, xlwt.Formula("SUM(K"+str(row_data_begin)+":K"+str(row_data_end)+")"),self.pd_cell_style_decimal_fill)
            ws_o.write(row_pos_o, 11, None,self.ph_cell_style)
            ws_o.write(row_pos_o, 12, None,self.ph_cell_style)
            ws_o.write(row_pos_o, 13, None,self.ph_cell_style)
            ws_o.write(row_pos_o, 14, xlwt.Formula("SUM(O"+str(row_data_begin)+":O"+str(row_data_end)+")"),self.pd_cell_style_decimal_fill)            
            ws_o.write(row_pos_o, 15, xlwt.Formula("SUM(P"+str(row_data_begin)+":P"+str(row_data_end)+")"),self.pd_cell_style_decimal_fill)            
            ws_o.write(row_pos_o+1, 0, _p.report_date+" "+username)



trial_balance_import_sun_report_xls(
    'report.wtc_report_trial_balance_import_sun_xls',
    'account.move.line',
    parser=wtc_trial_balance_import_sun_print_xls)
