import base64
from cStringIO import StringIO
import xlsxwriter
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from openerp import models, fields, api, _

class MatrixApprovalReport(models.TransientModel):
    _name = "wtc.matrix.approval.report.wizard"
    _description = "Laporan Matrix Approval"

    @api.model
    def _get_default_date(self): 
        return self.env['wtc.branch'].get_default_date()
        
    @api.model
    def _get_date_min_30(self): 
        return self.env['wtc.branch'].get_default_date() + relativedelta(days=-30)

    def _set_domain_branch_ids(self):
        return [('id','in',[b.id for b in self.env.user.branch_ids])]
    
    def _domain_product(self):
        categ_ids = self.env['product.category'].get_child_ids('Unit')
        return [('categ_id','in',categ_ids)]

    name = fields.Char('Nama File', readonly=True)
    state_x = fields.Selection([('choose','choose'),('get','get')], default=lambda *a: 'choose')
    data_x = fields.Binary('File', readonly=True)
    matrix_type = fields.Selection([
        ('biaya', 'Biaya'),
        ('discount', 'Discount'),
        ],default='biaya', string='Tipe Matrix') 
    report_type = fields.Selection([
        ('all', 'Semua di 1 sheet'),
        ('config', '1 config/product 1 sheet'),
        ('branch', '1 branch 1 sheet'),
        ],default='all', string='Tipe Output Laporan') 
    approval_config_ids = fields.Many2many('wtc.approval.config', 'teds_matrix_approval_report_config_rel', 'wizard_id', 'approval_id', 'Config', copy=False)
    product_template_ids = fields.Many2many('product.template', 'teds_matrix_approval_report_product_template_rel', 'wizard_id', 'product_template_id', 'Product', domain=_domain_product,copy=False)
    branch_ids = fields.Many2many('wtc.branch', 'teds_matrix_approval_report_branch_rel', 'wizard_id', 'branch_id', 'Dealer', copy=False, domain=_set_domain_branch_ids)
    
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

        self.wbf['content_border'] = workbook.add_format()
        self.wbf['content_border'].set_right()  
        self.wbf['content_border'].set_left()  
        self.wbf['content_border'].set_top()  
        
        self.wbf['content_float'] = workbook.add_format({'align': 'right','num_format': '#,##0.00'})
        self.wbf['content_float'].set_right() 
        self.wbf['content_float'].set_left()

        self.wbf['content_float_border'] = workbook.add_format({'align': 'right','num_format': '#,##0.00'})
        self.wbf['content_float_border'].set_right() 
        self.wbf['content_float_border'].set_left()
        self.wbf['content_float_border'].set_top()  

        self.wbf['content_center'] = workbook.add_format({'align': 'centre'})
        self.wbf['content_center'].set_right() 
        self.wbf['content_center'].set_left() 

        self.wbf['content_center_border'] = workbook.add_format({'align': 'centre'})
        self.wbf['content_center_border'].set_right()  
        self.wbf['content_center_border'].set_left()  
        self.wbf['content_center_border'].set_top()  
        
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
        if self.matrix_type == 'biaya':
            if self.report_type == 'all':
                return self.export_report_biaya_all()
            elif self.report_type == 'branch':
                return self.export_report_biaya_branch()
            elif self.report_type == 'config':
                return self.export_report_biaya_config()
        elif self.matrix_type == 'discount':
            if self.report_type == 'all':
                return self.export_report_discount_all()
            elif self.report_type == 'branch':
                return self.export_report_discount_branch()
            elif self.report_type == 'config':
                return self.export_report_discount_product()
    
    # BIAYA
    @api.multi
    def export_report_biaya_all(self):
        wbf = self.wbf
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(workbook)
        worksheet = workbook.add_worksheet('Matrix Approval')

        company_name = self.env.user.company_id.name
        date_generate = (self._get_default_date() + relativedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S")
        filename = 'Laporan_Matrix_Approval_%s.xlsx' % (str(date_generate).replace(" ","_").replace(":","-"))
        user_generate = self.env['res.users'].sudo().browse([self._uid]).name
        # COLUMN HEADER
        col_header = [
            {'name': 'No', 'max_size': 4},
            {'name': 'Kode Dealer', 'max_size': 9},
            {'name': 'Nama Dealer', 'max_size': 13},
            {'name': 'Transaksi', 'max_size': 13},
            {'name': 'Divisi', 'max_size': 10},
            {'name': 'Group', 'max_size': 11},
            {'name': 'Limit', 'max_size': 25}, #5
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
        worksheet.merge_range(1, 0, 1, ncol-1, 'Laporan Matrix Approval', wbf['title_doc'])
        worksheet.merge_range(2, 0, 2, ncol-1, 'Tanggal : %s' % date.today().strftime('%Y-%m-%d'), wbf['company'])
        # fetch data
        where = " WHERE 1=1"    
        if self.branch_ids:
            where += " AND matrix.branch_id IN %s" % str(tuple([b.id for b in self.branch_ids])).replace(',)', ')')
        else:
            where += " AND matrix.branch_id IN %s" % str(tuple([b.id for b in self.env.user.branch_ids])).replace(',)', ')')
        if self.approval_config_ids:
            where += " AND config.id IN %s" % str(tuple([c.id for c in self.approval_config_ids])).replace(',)', ')')

        get_lead_query = """
            SELECT 
                branch.code as branch_code
                ,branch.name as branch_name
                ,config.name as config_name
                , json_agg(json_build_object(
                    'division', matrix.division,
                    'group_name', groups.name,
                    'limitation', matrix_line.limit
                )::jsonb) as matrix_approval
            FROM wtc_approval_matrixbiaya_header as matrix
                LEFT JOIN wtc_approval_matrixbiaya as matrix_line on matrix_line.header_id = matrix.id
                LEFT JOIN wtc_approval_config as config on config.id = matrix.form_id
                LEFT JOIN res_groups as groups on groups.id = matrix_line.group_id
                LEFT JOIN wtc_branch as branch on branch.id = matrix.branch_id
            %s
            GROUP BY branch.id,config.id
            ORDER BY branch.id,config.id
        """ % (where)
        self._cr.execute(get_lead_query)
        lead_ress =  self._cr.dictfetchall()
        if lead_ress:
            row += 1
            no = 1
            for x in lead_ress:
                col = 1
                x['branch_code'] = '' if x['branch_code'] == None else x['branch_code']
                worksheet.write(row, col, x['branch_code'], wbf['content_center_border'])
                if len(x['branch_code']) >= col_header[col]['max_size']:
                    col_header[col]['max_size'] = len(x['branch_code']) + 2
                col += 1
                x['branch_name'] = '' if x['branch_name'] == None else x['branch_name']
                worksheet.write(row, col, x['branch_name'], wbf['content_border'])
                if len(x['branch_name']) >= col_header[col]['max_size']:
                    col_header[col]['max_size'] = len(x['branch_name']) + 2
                col += 1
                x['config_name'] = '' if x['config_name'] == None else x['config_name']
                worksheet.write(row, col, x['config_name'], wbf['content_center_border'])
                if len(x['config_name']) >= col_header[col]['max_size']:
                    col_header[col]['max_size'] = len(x['config_name']) + 2
                col += 1
                x['matrix_approval'] = '' if x['matrix_approval'] == None else x['matrix_approval']
                if x['matrix_approval']:
                    col_matrix = col
                    is_header = 0
                    for line in x['matrix_approval']:
                        col = col_matrix
                        
                        worksheet.write(row, 0, no, wbf['content_center'])
                        if len(str(no)) >= col_header[col]['max_size']:
                            col_header[col]['max_size'] = len(str(no)) + 2
                        # Untuk Border kanan kiri
                        if is_header != 0:
                            worksheet.write(row, 1, '', wbf['content_center'])
                            worksheet.write(row, 2, '', wbf['content_center'])
                            worksheet.write(row, 3, '', wbf['content_center'])
                            content_format = wbf['content_center']
                            content_float_format = wbf['content_float']
                        else:
                            content_format = wbf['content_center_border']
                            content_float_format = wbf['content_float_border']

                        line['division'] = '' if line['division'] == None else line['division']
                        worksheet.write(row, col, line['division'], content_format)
                        if len(line['division']) >= col_header[col]['max_size']:
                            col_header[col]['max_size'] = len(line['division']) + 2
                        col += 1
                        line['group_name'] = '' if line['group_name'] == None else line['group_name']
                        worksheet.write(row, col, line['group_name'], content_format)
                        if len(line['group_name']) >= col_header[col]['max_size']:
                            col_header[col]['max_size'] = len(line['group_name']) + 2
                        col += 1
                        line['limitation'] = '' if line['limitation'] == None else line['limitation']
                        worksheet.write(row, col, line['limitation'], content_float_format)
                        if len(str(line['limitation'])) >= col_header[col]['max_size']:
                            col_header[col]['max_size'] = len(str(line['limitation'])) + 2
                        row += 1
                        no += 1
                        is_header += 1
                        
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
            self.data_x = out
            self.name = filename
            fp.close()
            return {
                'type': 'ir.actions.act_url',
                'name': 'contract',
                'url':'/web/binary/saveas?model=wtc.matrix.approval.report.wizard&field=data_x&filename_field=name&id=%d'%(self.id)
            } 
        else:
            raise Warning("Tidak ada data")
    
    @api.multi
    def export_report_biaya_config(self):
        wbf = self.wbf
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(workbook)

        company_name = self.env.user.company_id.name
        date_generate = (self._get_default_date() + relativedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S")
        filename = 'Laporan_Matrix_Approval_%s.xlsx' % (str(date_generate).replace(" ","_").replace(":","-"))
        user_generate = self.env['res.users'].sudo().browse([self._uid]).name
        # COLUMN HEADER
        col_header = [
            {'name': 'No', 'max_size': 4},
            {'name': 'Branch Code', 'max_size': 13},
            {'name': 'Branch Name', 'max_size': 13},
            {'name': 'Divisi', 'max_size': 10},
            {'name': 'Group', 'max_size': 11},
            {'name': 'Limit', 'max_size': 25}, #5
        ]
        # fetch data
        where = " WHERE 1=1"    
        if self.branch_ids:
            where += " AND matrix.branch_id IN %s" % str(tuple([b.id for b in self.branch_ids])).replace(',)', ')')
        else:
            where += " AND matrix.branch_id IN %s" % str(tuple([b.id for b in self.env.user.branch_ids])).replace(',)', ')')
        if self.approval_config_ids:
            where += " AND config.id IN %s" % str(tuple([c.id for c in self.approval_config_ids])).replace(',)', ')')

        get_lead_query = """
            SELECT 					
                config.name as config_name
                , json_agg(json_build_object(
                    'config_name', config.name,
                    'branch_code', branch.code,
                    'branch_name', branch.name, 
                    'division', matrix.division,
                    'group_name', groups.name,
                    'limitation', matrix_line.limit
                )::jsonb) as matrix_approval
            FROM wtc_approval_matrixbiaya_header as matrix
                LEFT JOIN wtc_approval_matrixbiaya as matrix_line on matrix_line.header_id = matrix.id
                LEFT JOIN wtc_approval_config as config on config.id = matrix.form_id
                LEFT JOIN res_groups as groups on groups.id = matrix_line.group_id
                LEFT JOIN wtc_branch as branch on branch.id = matrix.branch_id
            %s
            GROUP BY config.id
            ORDER BY config.id
        """ % (where)
        self._cr.execute(get_lead_query)
        lead_ress =  self._cr.dictfetchall()
        if lead_ress:
            for x in lead_ress:
                # Create Sheet
                x['config_name'] = '' if x['config_name'] == None else x['config_name']
                worksheet = workbook.add_worksheet(x['config_name'])
                # write table header
                row = 4
                ncol = 0
                no = 1
                for i in col_header:
                    worksheet.write(row, ncol, i['name'], wbf['header'])
                    ncol += 1
                # freeze panes
                worksheet.freeze_panes(5, 0)
                # write content header
                worksheet.merge_range(0, 0, 0, ncol-1, company_name, wbf['title_doc'])
                worksheet.merge_range(1, 0, 1, ncol-1, 'Laporan Matrix Approval', wbf['title_doc'])
                worksheet.merge_range(2, 0, 2, ncol-1, 'Tanggal : %s' % date.today().strftime('%Y-%m-%d'), wbf['company'])
                row += 1
                
                col = 1
                x['matrix_approval'] = '' if x['matrix_approval'] == None else x['matrix_approval']
                if x['matrix_approval']:
                    col_matrix = col
                    is_header = 0
                    for line in x['matrix_approval']:
                        col = col_matrix
                        
                        worksheet.write(row, 0, no, wbf['content_center'])
                        if len(str(no)) >= col_header[col]['max_size']:
                            col_header[col]['max_size'] = len(str(no)) + 2
                        # Untuk Border kanan kiri
                        if is_header != 0:
                            worksheet.write(row, 1, '', wbf['content_center'])
                            worksheet.write(row, 2, '', wbf['content_center'])
                            worksheet.write(row, 3, '', wbf['content_center'])
                            
                        content_format = wbf['content_center']
                        content_float_format = wbf['content_float']
                        
                        line['branch_name'] = '' if line['branch_name'] == None else line['branch_name']
                        worksheet.write(row, col, line['branch_name'], content_format)
                        if len(line['branch_name']) >= col_header[col]['max_size']:
                            col_header[col]['max_size'] = len(line['branch_name']) + 2
                        col += 1
                        line['branch_code'] = '' if line['branch_code'] == None else line['branch_code']
                        worksheet.write(row, col, line['branch_code'], content_format)
                        if len(line['branch_code']) >= col_header[col]['max_size']:
                            col_header[col]['max_size'] = len(line['branch_code']) + 2
                        col += 1
                        line['division'] = '' if line['division'] == None else line['division']
                        worksheet.write(row, col, line['division'], content_format)
                        if len(line['division']) >= col_header[col]['max_size']:
                            col_header[col]['max_size'] = len(line['division']) + 2
                        col += 1
                        line['group_name'] = '' if line['group_name'] == None else line['group_name']
                        worksheet.write(row, col, line['group_name'], content_format)
                        if len(line['group_name']) >= col_header[col]['max_size']:
                            col_header[col]['max_size'] = len(line['group_name']) + 2
                        col += 1
                        line['limitation'] = '' if line['limitation'] == None else line['limitation']
                        worksheet.write(row, col, line['limitation'], content_float_format)
                        if len(str(line['limitation'])) >= col_header[col]['max_size']:
                            col_header[col]['max_size'] = len(str(line['limitation'])) + 2
                        row += 1
                        no += 1
                        is_header += 1
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
            self.data_x = out
            self.name = filename
            fp.close()
            return {
                'type': 'ir.actions.act_url',
                'name': 'contract',
                'url':'/web/binary/saveas?model=wtc.matrix.approval.report.wizard&field=data_x&filename_field=name&id=%d'%(self.id)
            } 
        else:
            raise Warning("Tidak ada data")
    
    @api.multi
    def export_report_biaya_branch(self):
        wbf = self.wbf
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(workbook)

        company_name = self.env.user.company_id.name
        date_generate = (self._get_default_date() + relativedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S")
        filename = 'Laporan_Matrix_Approval_%s.xlsx' % (str(date_generate).replace(" ","_").replace(":","-"))
        user_generate = self.env['res.users'].sudo().browse([self._uid]).name
        # COLUMN HEADER
        col_header = [
            {'name': 'No', 'max_size': 4},
            {'name': 'Branch Name', 'max_size': 14},
            {'name': 'Transaksi', 'max_size': 13},
            {'name': 'Divisi', 'max_size': 10},
            {'name': 'Group', 'max_size': 11},
            {'name': 'Limit', 'max_size': 25}, #5
        ]
        # fetch data
        where = " WHERE 1=1"    
        if self.branch_ids:
            where += " AND matrix.branch_id IN %s" % str(tuple([b.id for b in self.branch_ids])).replace(',)', ')')
        else:
            where += " AND matrix.branch_id IN %s" % str(tuple([b.id for b in self.env.user.branch_ids])).replace(',)', ')')
        if self.approval_config_ids:
            where += " AND config.id IN %s" % str(tuple([c.id for c in self.approval_config_ids])).replace(',)', ')')

        get_lead_query = """
            SELECT 
                branch.code as branch_code
                ,branch.name as branch_name
                , json_agg(json_build_object(
                    'branch_code', branch.code,
                    'branch_name', branch.name,
                    'config_name', config.name,
                    'division', matrix.division,
                    'group_name', groups.name,
                    'limitation', matrix_line.limit
                )::jsonb) as matrix_approval
            FROM wtc_approval_matrixbiaya_header as matrix
                LEFT JOIN wtc_approval_matrixbiaya as matrix_line on matrix_line.header_id = matrix.id
                LEFT JOIN wtc_approval_config as config on config.id = matrix.form_id
                LEFT JOIN res_groups as groups on groups.id = matrix_line.group_id
                LEFT JOIN wtc_branch as branch on branch.id = matrix.branch_id
            %s
            GROUP BY branch.id
            ORDER BY branch.id
        """ % (where)
        self._cr.execute(get_lead_query)
        lead_ress =  self._cr.dictfetchall()
        if lead_ress:
            for x in lead_ress:
                # Create Sheet
                x['branch_code'] = '' if x['branch_code'] == None else x['branch_code']
                worksheet = workbook.add_worksheet(x['branch_code'])
                # write table header
                row = 4
                ncol = 0
                no = 1
                for i in col_header:
                    worksheet.write(row, ncol, i['name'], wbf['header'])
                    ncol += 1
                # freeze panes
                worksheet.freeze_panes(5, 0)
                # write content header
                worksheet.merge_range(0, 0, 0, ncol-1, company_name, wbf['title_doc'])
                worksheet.merge_range(1, 0, 1, ncol-1, 'Laporan Matrix Approval', wbf['title_doc'])
                worksheet.merge_range(2, 0, 2, ncol-1, 'Tanggal : %s' % date.today().strftime('%Y-%m-%d'), wbf['company'])
                row += 1
                
                col = 1
                x['matrix_approval'] = '' if x['matrix_approval'] == None else x['matrix_approval']
                if x['matrix_approval']:
                    col_matrix = col
                    is_header = 0
                    for line in x['matrix_approval']:
                        col = col_matrix
                        
                        worksheet.write(row, 0, no, wbf['content_center'])
                        if len(str(no)) >= col_header[col]['max_size']:
                            col_header[col]['max_size'] = len(str(no)) + 2
                        # Untuk Border kanan kiri
                        if is_header != 0:
                            worksheet.write(row, 1, '', wbf['content_center'])
                            worksheet.write(row, 2, '', wbf['content_center'])
                            worksheet.write(row, 3, '', wbf['content_center'])
                            
                        content_format = wbf['content_center']
                        content_float_format = wbf['content_float']
                        
                        line['branch_name'] = '' if line['branch_name'] == None else line['branch_name']
                        worksheet.write(row, col, line['branch_name'], content_format)
                        if len(line['branch_name']) >= col_header[col]['max_size']:
                            col_header[col]['max_size'] = len(line['branch_name']) + 2
                        col += 1
                        line['config_name'] = '' if line['config_name'] == None else line['config_name']
                        worksheet.write(row, col, line['config_name'], content_format)
                        if len(line['config_name']) >= col_header[col]['max_size']:
                            col_header[col]['max_size'] = len(line['config_name']) + 2
                        col += 1
                        line['division'] = '' if line['division'] == None else line['division']
                        worksheet.write(row, col, line['division'], content_format)
                        if len(line['division']) >= col_header[col]['max_size']:
                            col_header[col]['max_size'] = len(line['division']) + 2
                        col += 1
                        line['group_name'] = '' if line['group_name'] == None else line['group_name']
                        worksheet.write(row, col, line['group_name'], content_format)
                        if len(line['group_name']) >= col_header[col]['max_size']:
                            col_header[col]['max_size'] = len(line['group_name']) + 2
                        col += 1
                        line['limitation'] = '' if line['limitation'] == None else line['limitation']
                        worksheet.write(row, col, line['limitation'], content_float_format)
                        if len(str(line['limitation'])) >= col_header[col]['max_size']:
                            col_header[col]['max_size'] = len(str(line['limitation'])) + 2
                        row += 1
                        no += 1
                        is_header += 1
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
            self.data_x = out
            self.name = filename
            fp.close()
            return {
                'type': 'ir.actions.act_url',
                'name': 'contract',
                'url':'/web/binary/saveas?model=wtc.matrix.approval.report.wizard&field=data_x&filename_field=name&id=%d'%(self.id)
            } 
        else:
            raise Warning("Tidak ada data")
    
    # Discount
    @api.multi
    def export_report_discount_all(self):
        wbf = self.wbf
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(workbook)
        worksheet = workbook.add_worksheet('Matrix Approval')

        company_name = self.env.user.company_id.name
        date_generate = (self._get_default_date() + relativedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S")
        filename = 'Laporan_Matrix_Approval_%s.xlsx' % (str(date_generate).replace(" ","_").replace(":","-"))
        user_generate = self.env['res.users'].sudo().browse([self._uid]).name
        # COLUMN HEADER
        col_header = [
            {'name': 'No', 'max_size': 4},
            {'name': 'Kode Dealer', 'max_size': 9},
            {'name': 'Nama Dealer', 'max_size': 13},
            {'name': 'Divisi', 'max_size': 10},
            {'name': 'Product Template', 'max_size': 13},
            {'name': 'Group', 'max_size': 11},
            {'name': 'Limit', 'max_size': 25}, #5
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
        worksheet.merge_range(1, 0, 1, ncol-1, 'Laporan Matrix Approval', wbf['title_doc'])
        worksheet.merge_range(2, 0, 2, ncol-1, 'Tanggal : %s' % date.today().strftime('%Y-%m-%d'), wbf['company'])
        # fetch data
        where = " WHERE 1=1"    
        if self.branch_ids:
            where += " AND matrix.branch_id IN %s" % str(tuple([b.id for b in self.branch_ids])).replace(',)', ')')
        else:
            where += " AND matrix.branch_id IN %s" % str(tuple([b.id for b in self.env.user.branch_ids])).replace(',)', ')')
        if self.product_template_ids:
            where += " AND product_template.id IN %s" % str(tuple([c.id for c in self.product_template_ids])).replace(',)', ')')

        get_lead_query = """
            SELECT 
                branch.code as branch_code
                ,branch.name as branch_name
                ,'[' || product_template.name || '] ' || product_template.description as product_template_name
                ,matrix.division as division
                , json_agg(json_build_object(
                    'group_name', groups.name,
                    'limitation', matrix_line.limit
                )::jsonb) as matrix_approval
            FROM wtc_approval_matrixdiscount_header as matrix
                LEFT JOIN wtc_approval_matrixdiscount as matrix_line on matrix_line.wtc_approval_md_id = matrix.id
                LEFT JOIN product_template as product_template on product_template.id = matrix.product_template_id
                LEFT JOIN res_groups as groups on groups.id = matrix_line.group_id
                LEFT JOIN wtc_branch as branch on branch.id = matrix.branch_id
            %s
            GROUP BY branch.id,product_template.id,matrix.id
            ORDER BY branch.id,product_template.id
        """ % (where)
        self._cr.execute(get_lead_query)
        lead_ress =  self._cr.dictfetchall()
        if lead_ress:
            row += 1
            no = 1
            for x in lead_ress:
                col = 1
                x['branch_code'] = '' if x['branch_code'] == None else x['branch_code']
                worksheet.write(row, col, x['branch_code'], wbf['content_center_border'])
                if len(x['branch_code']) >= col_header[col]['max_size']:
                    col_header[col]['max_size'] = len(x['branch_code']) + 2
                col += 1
                x['branch_name'] = '' if x['branch_name'] == None else x['branch_name']
                worksheet.write(row, col, x['branch_name'], wbf['content_border'])
                if len(x['branch_name']) >= col_header[col]['max_size']:
                    col_header[col]['max_size'] = len(x['branch_name']) + 2
                col += 1
                x['division'] = '' if x['division'] == None else x['division']
                worksheet.write(row, col, x['division'], wbf['content_border'])
                if len(x['division']) >= col_header[col]['max_size']:
                    col_header[col]['max_size'] = len(x['division']) + 2
                col += 1
                x['product_template_name'] = '' if x['product_template_name'] == None else x['product_template_name']
                worksheet.write(row, col, x['product_template_name'], wbf['content_center_border'])
                if len(x['product_template_name']) >= col_header[col]['max_size']:
                    col_header[col]['max_size'] = len(x['product_template_name']) + 2
                col += 1
                x['matrix_approval'] = '' if x['matrix_approval'] == None else x['matrix_approval']
                if x['matrix_approval']:
                    col_matrix = col
                    is_header = 0
                    for line in x['matrix_approval']:
                        col = col_matrix
                        
                        worksheet.write(row, 0, no, wbf['content_center'])
                        if len(str(no)) >= col_header[col]['max_size']:
                            col_header[col]['max_size'] = len(str(no)) + 2
                        # Untuk Border kanan kiri
                        if is_header != 0:
                            worksheet.write(row, 1, '', wbf['content_center'])
                            worksheet.write(row, 2, '', wbf['content_center'])
                            worksheet.write(row, 3, '', wbf['content_center'])
                            content_format = wbf['content_center']
                            content_float_format = wbf['content_float']
                        else:
                            content_format = wbf['content_center_border']
                            content_float_format = wbf['content_float_border']
                        line['group_name'] = '' if line['group_name'] == None else line['group_name']
                        worksheet.write(row, col, line['group_name'], content_format)
                        if len(line['group_name']) >= col_header[col]['max_size']:
                            col_header[col]['max_size'] = len(line['group_name']) + 2
                        col += 1
                        line['limitation'] = '' if line['limitation'] == None else line['limitation']
                        worksheet.write(row, col, line['limitation'], content_float_format)
                        if len(str(line['limitation'])) >= col_header[col]['max_size']:
                            col_header[col]['max_size'] = len(str(line['limitation'])) + 2
                        row += 1
                        no += 1
                        is_header += 1
                        
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
            self.data_x = out
            self.name = filename
            fp.close()
            return {
                'type': 'ir.actions.act_url',
                'name': 'contract',
                'url':'/web/binary/saveas?model=wtc.matrix.approval.report.wizard&field=data_x&filename_field=name&id=%d'%(self.id)
            } 
        else:
            raise Warning("Tidak ada data")
    
    @api.multi
    def export_report_discount_product(self):
        wbf = self.wbf
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(workbook)

        company_name = self.env.user.company_id.name
        date_generate = (self._get_default_date() + relativedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S")
        filename = 'Laporan_Matrix_Approval_%s.xlsx' % (str(date_generate).replace(" ","_").replace(":","-"))
        user_generate = self.env['res.users'].sudo().browse([self._uid]).name
        # COLUMN HEADER
        col_header = [
            {'name': 'No', 'max_size': 4},
            {'name': 'Branch Code', 'max_size': 13},
            {'name': 'Branch Name', 'max_size': 13},
            {'name': 'Divisi', 'max_size': 10},
            {'name': 'Produk', 'max_size': 10},
            {'name': 'Group', 'max_size': 11},
            {'name': 'Limit', 'max_size': 25}, #5
        ]
        # fetch data
        where = " WHERE 1=1"    
        if self.branch_ids:
            where += " AND matrix.branch_id IN %s" % str(tuple([b.id for b in self.branch_ids])).replace(',)', ')')
        else:
            where += " AND matrix.branch_id IN %s" % str(tuple([b.id for b in self.env.user.branch_ids])).replace(',)', ')')
        if self.product_template_ids:
            where += " AND product_template.id IN %s" % str(tuple([c.id for c in self.product_template_ids])).replace(',)', ')')

        get_lead_query = """
            SELECT 					
                product_template.name as product_template_code
                , json_agg(json_build_object(
                    'product_template_name', '[' || product_template.name || '] ' || product_template.description,
                    'branch_code', branch.code,
                    'branch_name', branch.name, 
                    'division', matrix.division,
                    'group_name', groups.name,
                    'limitation', matrix_line.limit
                )::jsonb) as matrix_approval
            FROM wtc_approval_matrixdiscount_header as matrix
                LEFT JOIN wtc_approval_matrixdiscount as matrix_line on matrix_line.wtc_approval_md_id = matrix.id
                LEFT JOIN product_template as product_template on product_template.id = matrix.product_template_id
                LEFT JOIN res_groups as groups on groups.id = matrix_line.group_id
                LEFT JOIN wtc_branch as branch on branch.id = matrix.branch_id
            %s
            GROUP BY product_template.id
            ORDER BY product_template.id
        """ % (where)
        self._cr.execute(get_lead_query)
        lead_ress =  self._cr.dictfetchall()
        if lead_ress:
            for x in lead_ress:
                # Create Sheet
                x['product_template_code'] = '' if x['product_template_code'] == None else x['product_template_code']
                worksheet = workbook.add_worksheet(x['product_template_code'])
                # write table header
                row = 4
                ncol = 0
                no = 1
                for i in col_header:
                    worksheet.write(row, ncol, i['name'], wbf['header'])
                    ncol += 1
                # freeze panes
                worksheet.freeze_panes(5, 0)
                # write content header
                worksheet.merge_range(0, 0, 0, ncol-1, company_name, wbf['title_doc'])
                worksheet.merge_range(1, 0, 1, ncol-1, 'Laporan Matrix Approval', wbf['title_doc'])
                worksheet.merge_range(2, 0, 2, ncol-1, 'Tanggal : %s' % date.today().strftime('%Y-%m-%d'), wbf['company'])
                row += 1
                
                col = 1
                x['matrix_approval'] = '' if x['matrix_approval'] == None else x['matrix_approval']
                if x['matrix_approval']:
                    col_matrix = col
                    is_header = 0
                    for line in x['matrix_approval']:
                        col = col_matrix
                        
                        worksheet.write(row, 0, no, wbf['content_center'])
                        if len(str(no)) >= col_header[col]['max_size']:
                            col_header[col]['max_size'] = len(str(no)) + 2
                        # Untuk Border kanan kiri
                        if is_header != 0:
                            worksheet.write(row, 1, '', wbf['content_center'])
                            worksheet.write(row, 2, '', wbf['content_center'])
                            worksheet.write(row, 3, '', wbf['content_center'])
                            
                        content_format = wbf['content_center']
                        content_float_format = wbf['content_float']
                        
                        line['branch_name'] = '' if line['branch_name'] == None else line['branch_name']
                        worksheet.write(row, col, line['branch_name'], content_format)
                        if len(line['branch_name']) >= col_header[col]['max_size']:
                            col_header[col]['max_size'] = len(line['branch_name']) + 2
                        col += 1
                        line['branch_code'] = '' if line['branch_code'] == None else line['branch_code']
                        worksheet.write(row, col, line['branch_code'], content_format)
                        if len(line['branch_code']) >= col_header[col]['max_size']:
                            col_header[col]['max_size'] = len(line['branch_code']) + 2
                        col += 1
                        line['division'] = '' if line['division'] == None else line['division']
                        worksheet.write(row, col, line['division'], content_format)
                        if len(line['division']) >= col_header[col]['max_size']:
                            col_header[col]['max_size'] = len(line['division']) + 2
                        col += 1
                        line['product_template_name'] = '' if line['product_template_name'] == None else line['product_template_name']
                        worksheet.write(row, col, line['product_template_name'], content_format)
                        if len(line['product_template_name']) >= col_header[col]['max_size']:
                            col_header[col]['max_size'] = len(line['product_template_name']) + 2
                        col += 1
                        line['group_name'] = '' if line['group_name'] == None else line['group_name']
                        worksheet.write(row, col, line['group_name'], content_format)
                        if len(line['group_name']) >= col_header[col]['max_size']:
                            col_header[col]['max_size'] = len(line['group_name']) + 2
                        col += 1
                        line['limitation'] = '' if line['limitation'] == None else line['limitation']
                        worksheet.write(row, col, line['limitation'], content_float_format)
                        if len(str(line['limitation'])) >= col_header[col]['max_size']:
                            col_header[col]['max_size'] = len(str(line['limitation'])) + 2
                        row += 1
                        no += 1
                        is_header += 1
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
            self.data_x = out
            self.name = filename
            fp.close()
            return {
                'type': 'ir.actions.act_url',
                'name': 'contract',
                'url':'/web/binary/saveas?model=wtc.matrix.approval.report.wizard&field=data_x&filename_field=name&id=%d'%(self.id)
            } 
        else:
            raise Warning("Tidak ada data")
    
    @api.multi
    def export_report_discount_branch(self):
        wbf = self.wbf
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(workbook)

        company_name = self.env.user.company_id.name
        date_generate = (self._get_default_date() + relativedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S")
        filename = 'Laporan_Matrix_Approval_%s.xlsx' % (str(date_generate).replace(" ","_").replace(":","-"))
        user_generate = self.env['res.users'].sudo().browse([self._uid]).name
        # COLUMN HEADER
        col_header = [
            {'name': 'No', 'max_size': 4},
            {'name': 'Branch Name', 'max_size': 14},
            {'name': 'Transaksi', 'max_size': 13},
            {'name': 'Divisi', 'max_size': 10},
            {'name': 'Group', 'max_size': 11},
            {'name': 'Limit', 'max_size': 25}, #5
        ]
        # fetch data
        where = " WHERE 1=1"    
        if self.branch_ids:
            where += " AND matrix.branch_id IN %s" % str(tuple([b.id for b in self.branch_ids])).replace(',)', ')')
        else:
            where += " AND matrix.branch_id IN %s" % str(tuple([b.id for b in self.env.user.branch_ids])).replace(',)', ')')
        if self.product_template_ids:
            where += " AND product_template.id IN %s" % str(tuple([c.id for c in self.product_template_ids])).replace(',)', ')')

        get_lead_query = """
            SELECT 
                branch.code as branch_code
                ,branch.name as branch_name
                , json_agg(json_build_object(
                    'branch_code', branch.code,
                    'branch_name', branch.name,
                    'product_template_name', '[' || product_template.name || '] ' || product_template.description,
                    'division', matrix.division,
                    'group_name', groups.name,
                    'limitation', matrix_line.limit
                )::jsonb) as matrix_approval
            FROM wtc_approval_matrixdiscount_header as matrix
                LEFT JOIN wtc_approval_matrixdiscount as matrix_line on matrix_line.wtc_approval_md_id = matrix.id
                LEFT JOIN product_template as product_template on product_template.id = matrix.product_template_id
                LEFT JOIN res_groups as groups on groups.id = matrix_line.group_id
                LEFT JOIN wtc_branch as branch on branch.id = matrix.branch_id
            %s
            GROUP BY branch.id
            ORDER BY branch.id
        """ % (where)
        self._cr.execute(get_lead_query)
        lead_ress =  self._cr.dictfetchall()
        if lead_ress:
            for x in lead_ress:
                # Create Sheet
                x['branch_code'] = '' if x['branch_code'] == None else x['branch_code']
                worksheet = workbook.add_worksheet(x['branch_code'])
                # write table header
                row = 4
                ncol = 0
                no = 1
                for i in col_header:
                    worksheet.write(row, ncol, i['name'], wbf['header'])
                    ncol += 1
                # freeze panes
                worksheet.freeze_panes(5, 0)
                # write content header
                worksheet.merge_range(0, 0, 0, ncol-1, company_name, wbf['title_doc'])
                worksheet.merge_range(1, 0, 1, ncol-1, 'Laporan Matrix Approval', wbf['title_doc'])
                worksheet.merge_range(2, 0, 2, ncol-1, 'Tanggal : %s' % date.today().strftime('%Y-%m-%d'), wbf['company'])
                row += 1
                
                col = 1
                x['matrix_approval'] = '' if x['matrix_approval'] == None else x['matrix_approval']
                if x['matrix_approval']:
                    col_matrix = col
                    is_header = 0
                    for line in x['matrix_approval']:
                        col = col_matrix
                        
                        worksheet.write(row, 0, no, wbf['content_center'])
                        if len(str(no)) >= col_header[col]['max_size']:
                            col_header[col]['max_size'] = len(str(no)) + 2
                        # Untuk Border kanan kiri
                        if is_header != 0:
                            worksheet.write(row, 1, '', wbf['content_center'])
                            worksheet.write(row, 2, '', wbf['content_center'])
                            worksheet.write(row, 3, '', wbf['content_center'])
                            
                        content_format = wbf['content_center']
                        content_float_format = wbf['content_float']
                        
                        line['branch_name'] = '' if line['branch_name'] == None else line['branch_name']
                        worksheet.write(row, col, line['branch_name'], content_format)
                        if len(line['branch_name']) >= col_header[col]['max_size']:
                            col_header[col]['max_size'] = len(line['branch_name']) + 2
                        col += 1
                        line['division'] = '' if line['division'] == None else line['division']
                        worksheet.write(row, col, line['division'], content_format)
                        if len(line['division']) >= col_header[col]['max_size']:
                            col_header[col]['max_size'] = len(line['division']) + 2
                        col += 1
                        line['product_template_name'] = '' if line['product_template_name'] == None else line['product_template_name']
                        worksheet.write(row, col, line['product_template_name'], content_format)
                        if len(line['product_template_name']) >= col_header[col]['max_size']:
                            col_header[col]['max_size'] = len(line['product_template_name']) + 2
                        col += 1
                        line['group_name'] = '' if line['group_name'] == None else line['group_name']
                        worksheet.write(row, col, line['group_name'], content_format)
                        if len(line['group_name']) >= col_header[col]['max_size']:
                            col_header[col]['max_size'] = len(line['group_name']) + 2
                        col += 1
                        line['limitation'] = '' if line['limitation'] == None else line['limitation']
                        worksheet.write(row, col, line['limitation'], content_float_format)
                        if len(str(line['limitation'])) >= col_header[col]['max_size']:
                            col_header[col]['max_size'] = len(str(line['limitation'])) + 2
                        row += 1
                        no += 1
                        is_header += 1
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
            self.data_x = out
            self.name = filename
            fp.close()
            return {
                'type': 'ir.actions.act_url',
                'name': 'contract',
                'url':'/web/binary/saveas?model=wtc.matrix.approval.report.wizard&field=data_x&filename_field=name&id=%d'%(self.id)
            } 
        else:
            raise Warning("Tidak ada data")
    