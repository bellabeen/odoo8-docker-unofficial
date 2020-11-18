import xlwt
from datetime import datetime
import time
from openerp.osv import orm
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
from .wtc_report_regenerate_faktur_pajak import wtc_report_regenerate_faktur_pajak_print
from openerp.tools.translate import translate
import string

class wtc_report_regenerate_faktur_pajak_print_xls(wtc_report_regenerate_faktur_pajak_print):

    def __init__(self, cr, uid, name, context):
        super(wtc_report_regenerate_faktur_pajak_print_xls, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'datetime': datetime,
            'wanted_list_overview': self.pool.get('wtc.regenerate.faktur.pajak.gabungan')._report_xls_regenerate_faktur_pajak_fields(cr, uid, context),
            'wanted_list_details': self.pool.get('wtc.regenerate.faktur.pajak.gabungan')._report_xls_regenerate_faktur_pajak_detail_fields(cr, uid, context),            
            '_': self._,
        })

    def _(self, src):
        lang = self.context.get('lang', 'en_US')
        return translate(self.cr, 'report.Laporan Regenerate Faktur Pajak', 'report', lang, src) or src

class report_regenerate_faktur_pajak_xls(report_xls):

    def __init__(self, name, table, rml=False, parser=False, header=True, store=False):
        super(report_regenerate_faktur_pajak_xls, self).__init__(name, table, rml, parser, header, store)

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
        self.pd_cell_style_decimal_detail = xlwt.easyxf(ph_cell_format + _xs['right'], num_format_str=report_xls.decimal_format)
        self.detail_header = xlwt.easyxf(_xs['fill'] + _xs['borders_all'])
        
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
            'ref': {
                'header': [1, 22, 'text', _render("_('Transaction Ref')")],
                'lines': [1, 0, 'text', _render("p['ref']")],
                'totals': [1, 22, 'text', _render("_('transaction_ref')")]},            
            'form_name': {
                'header': [1, 22, 'text', _render("_('Form Name')")],
                'lines': [1, 0, 'text', _render("p['form_name']")],
                'totals': [1, 22, 'number', None]},
            'sum_tax_amount': {
                'header': [1, 17, 'text', _render("_('Total Tax')")],
                'lines': [1, 0, 'number', _render("p['sum_tax_amount']")],
                'totals': [1, 22, 'number', None]},
            'sum_untaxed_amount': {
                'header': [1, 17, 'text', _render("_('Total Untaxed')")],
                'lines': [1, 0, 'number', _render("p['sum_untaxed_amount']")],
                'totals': [1, 22, 'number', None]},
            'sum_total_amount': {
                'header': [1, 17, 'text', _render("_('Grand Total')")],
                'lines': [1, 0, 'number', _render("p['sum_total_amount']")],
                'totals': [1, 22, 'number', None]},                                                                                                                                    
        }

        # XLS Template Detail
        self.col_specs_template_details = {
            'no': {
                'header1': [1, 5, 'text', _render("_('No')")],
                'header2': [1, 0, 'number', _render("p['no']"),None,self.detail_header],
                'lines': [1, 0, 'text', None],
                'totals1': [1, 0, 'text', None],
                'totals2': [1, 0, 'text', None]},                                                                          
            'ref': {
                'header1': [1, 20, 'text', _render("_('Transaction Ref')")],
                'header2': [1, 0, 'text', _render("p['ref']"),None,self.detail_header],
                'lines': [1, 0, 'text', None],
                'totals1': [1, 0, 'text', None],
                'totals2': [1, 0, 'text', None]},                             
            'form_name': {
                'header1': [1, 20, 'text', _render("_('Form Name')")],
                'header2': [1, 0, 'text', _render("p['form_name'] or 'n/a'"),None,self.detail_header],
                'lines': [1, 0, 'text', None],
                'totals1': [1, 0, 'text', None],
                'totals2': [1, 0, 'text', None]},                             
            'date': {
                'header1': [1, 12, 'text', _render("_('Date')")],
                'header2': [1, 0, 'text', _render("p['date'] or 'n/a'"),None,self.detail_header],
                'lines': [1, 0, 'text', None],
                'totals1': [1, 0, 'text', None],
                'totals2': [1, 0, 'text', None]},                                
            'state': {
                'header1': [1, 8, 'text', _render("_('State')")],
                'header2': [1, 0, 'text', _render("p['state']"),None,self.detail_header],
                'lines': [1, 0, 'text', None],
                'totals1': [1, 0, 'text', None],
                'totals2': [1, 0, 'text', None]},                                                                                                                                                                     
            'transaction_no': {
                'header1': [1, 20, 'text',_render("_('Transaction No')")],
                'header2': [1, 0, 'text', None],
                'lines': [1, 0, 'text',_render("l['transaction_no']"), None,self.pd_cell_style_decimal],
                'totals1': [1, 0, 'text', _render("_('Transaction No')")],
                'totals2': [1, 0, 'text', None,_render("_('Model')"),self.rt_cell_style_decimal]}, 
            'no_faktur': {
                'header1': [1, 15, 'text',_render("_('No Faktur Pajak')")],
                'header2': [1, 0, 'text', None],
                'lines': [1, 0, 'text',_render("l['no_faktur']")],
                'totals1': [1, 0, 'text', _render("_('no_faktur No')")],
                'totals2': [1, 0, 'text', None,_render("_('Model')"),self.rt_cell_style_decimal]}, 
            'partner_code': {
                'header1': [1, 15, 'text',_render("_('Partner Code')")],
                'header2': [1, 0, 'text', None],
                'lines': [1, 0, 'text',_render("l['partner_code']")],
                'totals1': [1, 0, 'text', _render("_('partner_code')")],
                'totals2': [1, 0, 'text', None,_render("_('Model')"),self.rt_cell_style_decimal]}, 
            'partner_name': {
                'header1': [1, 15, 'text',_render("_('Partner Name')")],
                'header2': [1, 0, 'text', None],
                'lines': [1, 0, 'text',_render("l['partner_name']")],
                'totals1': [1, 0, 'text', _render("_('Transaction No')")],
                'totals2': [1, 0, 'text', None,_render("_('Model')"),self.rt_cell_style_decimal]},                                                                                                                                   
            'sum_untaxed_amount': {
                'header1': [1, 20, 'text',_render("_('Untaxed Amount')")],
                'header2': [1, 0, 'number', _render("p['sum_untaxed_amount']"),None,self.pd_cell_style_decimal_detail],
                'lines': [1, 0, 'number',_render("l['untaxed_amount']"), None,self.pd_cell_style_decimal],
                'totals1': [1, 0, 'text', _render("_('untaxed_amount')")],
                'totals2': [1, 0, 'text', None,_render("_('untaxed_amount')"),self.rt_cell_style_decimal]},  
            'sum_tax_amount': {
                'header1': [1, 20, 'text',_render("_('Tax Amount')")],
                'header2': [1, 0, 'number', _render("p['sum_tax_amount']"),None,self.pd_cell_style_decimal_detail],
                'lines': [1, 0, 'number',_render("l['tax_amount']"), None,self.pd_cell_style_decimal],
                'totals1': [1, 0, 'text', _render("_('tax_amount')")],
                'totals2': [1, 0, 'text', None,_render("_('tax_amount')"),self.rt_cell_style_decimal]},
            'sum_total_amount': {
                'header1': [1, 20, 'text',_render("_('Total Amount')")],
                'header2': [1, 0, 'number', _render("p['sum_total_amount']"),None,self.pd_cell_style_decimal_detail],
                'lines': [1, 0, 'number',_render("l['total_amount']"), None,self.pd_cell_style_decimal],
                'totals1': [1, 0, 'text', _render("_('tax_amount')")],
                'totals2': [1, 0, 'text', None,_render("_('tax_amount')"),self.rt_cell_style_decimal]},
            'total_line': {
                'header1': [1, 10, 'text', _render("_('#Total Line')")],
                'header2': [1, 0, 'number', _render("p['total_line']"),None,self.detail_header],
                'lines': [1, 0, 'text', None],
                'totals1': [1, 0, 'text', None],
                'totals2': [1, 0, 'text', None]},                                                                                                                                                                                                                                         
     }   
    def generate_xls_report(self, _p, _xs, data, objects, wb):
        wanted_list_overview = _p.wanted_list_overview
        wanted_list_details = _p.wanted_list_details
        self.col_specs_template_overview.update({})
        self.col_specs_template_details.update({})
        _ = _p._

        for r in _p.reports:
            ws_o = wb.add_sheet('Laporan Faktur Pajak Gabungan')
            ws_d = wb.add_sheet(('Laporan Faktur Pajak Gabungan' + ' ' + _('Details'))[:31])
            
            for ws in [ws_o,ws_d]:
                ws.panes_frozen = True
                ws.remove_splits = True
                ws.portrait = 0  # Landscape
                ws.fit_width_to_pages = 1
            row_pos_o = 0
            row_pos_d = 0
            
            # set print header/footer
            for ws in [ws_o,ws_d]:
                ws.header_str = self.xls_headers['standard']
                ws.footer_str = self.xls_footers['standard']

            # Company Name
            cell_style = xlwt.easyxf(_xs['left'])
            
            c_specs_o = [('report_name', 1, 0, 'text', _p.company.name)]
            row_data = self.xls_row_template(c_specs_o, ['report_name'])
            row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=cell_style)
                        
            c_specs_d = [('report_name', 1, 0, 'text', _p.company.name)]
            row_data = self.xls_row_template(c_specs_d, ['report_name'])
            row_pos_d = self.xls_write_row(ws_d, row_pos_d, row_data, row_style=cell_style)
                                    
            # Title
            cell_style = xlwt.easyxf(_xs['xls_title'])
            
            c_specs_o = [('report_name', 1, 0, 'text', 'Laporan Faktur Pajak Gabungan')]
            row_data = self.xls_row_template(c_specs_o, ['report_name'])
            row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=cell_style)
            
            c_specs_d = [('report_name', 1, 0, 'text', 'Laporan Faktur Pajak Gabungan Details')]
            row_data = self.xls_row_template(c_specs_d, ['report_name'])
            row_pos_d = self.xls_write_row(ws_d, row_pos_d, row_data, row_style=cell_style)
                        
            # Start Date & End Date
            cell_style = xlwt.easyxf(_xs['left'])
            report_name = ' '.join([_('Tanggal'), _('-' if data['start_date'] == False else str(data['start_date'])), _('s/d'), _('-' if data['end_date'] == False else str(data['end_date']))])
            
            c_specs_o = [('report_name', 1, 0, 'text', report_name)]
            row_data = self.xls_row_template(c_specs_o, ['report_name'])
            row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=cell_style)
            row_pos_o += 1
            
            c_specs_d = [('report_name', 1, 0, 'text', report_name)]
            row_data = self.xls_row_template(c_specs_d, ['report_name'])
            row_pos_d = self.xls_write_row(ws_d, row_pos_d, row_data, row_style=cell_style)
            row_pos_d += 1
                        
            # Report Column Headers
            c_specs_o = map(lambda x: self.render(x, self.col_specs_template_overview, 'header', render_space={'_': _p._}), wanted_list_overview)
            row_data = self.xls_row_template(c_specs_o, [x[0] for x in c_specs_o])
            row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=self.rh_cell_style, set_column_size=True)
            ws_o.set_horz_split_pos(row_pos_o)
            
            c_specs_d = map(lambda x: self.render(x, self.col_specs_template_details, 'header1',render_space={'_': _p._}),wanted_list_details)
            row_data = self.xls_row_template(c_specs_d, [x[0] for x in c_specs_d])
            row_pos_d = self.xls_write_row(ws_d, row_pos_d, row_data, row_style=self.rh_cell_style,set_column_size=True)
            ws_d.set_horz_split_pos(row_pos_d)
            
            row_pos_d += 1
                        
            row_data_begin = row_pos_o
            partner_debit_cells = []
            partner_credit_cells = []            
            # Columns and Rows
            no = 0
            row_data_detail_start = 0
            row_data_detail_end = 0
            for p in r['pajak']:
                
                c_specs_o = map(lambda x: self.render(x, self.col_specs_template_overview, 'lines'),wanted_list_overview)
                for x in c_specs_o :
                    if x[0] == 'no' :
                        no += 1
                        x[4] = no                    
                row_data = self.xls_row_template(c_specs_o, [x[0] for x in c_specs_o])
                row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=self.pd_cell_style)
                row_pos_d += 1
                                
                #next sheet
                no -= 1
                c_specs_d = map(lambda x: self.render(x, self.col_specs_template_details, 'header2'),wanted_list_details)
                for x in c_specs_d :
                    if x[0] == 'no' :
                        no += 1
                        x[4] = no                  
                row_data = self.xls_row_template(c_specs_d, [x[0] for x in c_specs_d])
                row_pos_d = self.xls_write_row(ws_d, row_pos_d, row_data, row_style=self.ph_cell_style)
                
                if row_data_detail_start != 0 :
                    row_data_detail_start += row_pos_d
                    
                for l in p['lines']:
                    debit_cell = rowcol_to_cell(row_pos_d, 6)
                    credit_cell = rowcol_to_cell(row_pos_d, 7)
                    bal_formula = debit_cell + '-' + credit_cell
                    c_specs_d = map(lambda x: self.render(x, self.col_specs_template_details, 'lines'),wanted_list_details)
                    row_data = self.xls_row_template(c_specs_d, [x[0] for x in c_specs_d])
                    row_pos_d = self.xls_write_row(ws_d, row_pos_d, row_data,row_style=self.pd_cell_style)
                
                if row_data_detail_end != 0 :
                    row_data_detail_end += row_pos_d                
                
            row_data_end = row_pos_o
            
            # Totalstb
            ws_o.write(row_pos_o, 0, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 1, 'Totals', self.ph_cell_style)   
            ws_o.write(row_pos_o, 2, None, self.rt_cell_style_decimal)
            ws_o.write(row_pos_o, 3, xlwt.Formula("SUM(D"+str(row_data_begin)+":D"+str(row_data_end)+")"), self.ph_cell_style)
            ws_o.write(row_pos_o, 4, xlwt.Formula("SUM(E"+str(row_data_begin)+":E"+str(row_data_end)+")"), self.ph_cell_style)
            ws_o.write(row_pos_o, 5, xlwt.Formula("SUM(F"+str(row_data_begin)+":F"+str(row_data_end)+")"), self.ph_cell_style)
              
            #Footer
            ws_o.write(row_pos_o + 1, 0, None)
            ws_o.write(row_pos_o + 2, 0, time.strftime('%Y-%m-%d %H:%M:%S') + ' ' + str(self.pool.get('res.users').browse(self.cr, self.uid, self.uid).name))

report_regenerate_faktur_pajak_xls('report.Laporan Regenerate Faktur Pajak', 'wtc.regenerate.faktur.pajak.gabungan', parser = wtc_report_regenerate_faktur_pajak_print_xls)
