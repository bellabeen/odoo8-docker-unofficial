import base64
from cStringIO import StringIO
import xlsxwriter
# import ipdb
from datetime import datetime
from openerp import api, fields, models

class ApiLogWorkOrderReport(models.TransientModel):
    _name = "teds.api.log.work.order.report"
    _description = "Laporan Error B2B WO"

    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()

    def _get_default_branch(self):
        if self.env.user.area_id.code != 'ALL':
            return self.env.user.branch_ids
        else:
            return False

    start_date = fields.Date(string='Start Date', default=_get_default_date)
    end_date = fields.Date(string='End Date', default=_get_default_date)
    branch_ids = fields.Many2many('wtc.branch', 'teds_api_log_work_order_branch_rel', 'report_id','branch_id', string='Dealer')
    name = fields.Char(string='Filename', readonly=True)
    report_file = fields.Binary(string='Report',readonly=True)
    state_x = fields.Selection( ( ('choose','choose'),('get','get')),default=lambda *a: 'choose')

    wbf = {}
    SHEET_COLS = [
        'A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z',
        'AA','AB','AC','AD','AE','AF','AG','AH','AI','AJ','AK','AL','AM','AN','AO','AP','AQ','AR','AS','AT','AU','AV','AW','AX','AY','AZ',
        'BA','BB','BC','BD','BE','BF','BG','BH','BI','BJ','BK','BL','BM','BN','BO','BP','BQ','BR','BS','BT','BU','BV','BW','BX','BY','BZ'  
    ]

    @api.multi
    def add_workbook_format(self,workbook):      
        self.wbf['header'] = workbook.add_format({'bold': 1,'align': 'center','bg_color': '#FFFFDB','font_color': '#000000'})
        self.wbf['header'].set_border()

        self.wbf['header_no'] = workbook.add_format({'bold': 1,'align': 'center','bg_color': '#FFFFDB','font_color': '#000000'})
        self.wbf['header_no'].set_border()
        self.wbf['header_no'].set_align('vcenter')
                
        self.wbf['footer'] = workbook.add_format({'align':'left'})
        
        self.wbf['content_datetime'] = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss'})
        self.wbf['content_datetime'].set_left()
        self.wbf['content_datetime'].set_right()
        
        self.wbf['content_datetime_12_hr'] = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm AM/PM'})
        self.wbf['content_datetime_12_hr'].set_left()
        self.wbf['content_datetime_12_hr'].set_right()        
                
        self.wbf['content_date'] = workbook.add_format({'num_format': 'yyyy-mm-dd'})
        self.wbf['content_date'].set_left()
        self.wbf['content_date'].set_right() 
        
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
        
        self.wbf['content_number'] = workbook.add_format({'align': 'left'})
        self.wbf['content_number'].set_right() 
        self.wbf['content_number'].set_left() 
                
        self.wbf['content_percent'] = workbook.add_format({'align': 'right','num_format': '0.00%'})
        self.wbf['content_percent'].set_right() 
        self.wbf['content_percent'].set_left() 
                
        self.wbf['total_float'] = workbook.add_format({'bold':1,'bg_color': '#FFFFDB','align': 'right','num_format': '#,##0.00'})
        self.wbf['total_float'].set_top()
        self.wbf['total_float'].set_bottom()            
        self.wbf['total_float'].set_left()
        self.wbf['total_float'].set_right()         
        
        self.wbf['total_number'] = workbook.add_format({'align':'right','bg_color': '#FFFFDB','bold':1})
        self.wbf['total_number'].set_top()
        self.wbf['total_number'].set_bottom()            
        self.wbf['total_number'].set_left()
        self.wbf['total_number'].set_right()
        
        self.wbf['total'] = workbook.add_format({'bold':1,'bg_color': '#FFFFDB','align':'center'})
        self.wbf['total'].set_left()
        self.wbf['total'].set_right()
        self.wbf['total'].set_top()
        self.wbf['total'].set_bottom()
        
        return workbook

    @api.multi
    def generate_report(self):
        # workbook
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(workbook)
        wbf = self.wbf
        # workbook content
        date_generate = self._get_default_date().strftime("%Y-%m-%d_%H:%M:%S")
        self.name = 'Laporan_Error_B2B_WO_'+str(date_generate)+'.xlsx'        
        user_generate = self.env['res.users'].sudo().browse([self._uid]).name
        col_header = [
            {'name': 'No', 'max_size': 4},
            {'name': 'Dealer', 'max_size': 8},
            {'name': 'Nomor WO', 'max_size': 10},
            {'name': 'Tanggal WO', 'max_size': 12},
            {'name': 'Tipe WO', 'max_size': 9},
            {'name': 'Kode Error', 'max_size': 12},
            {'name': 'Error', 'max_size': 7}
        ]
        # ipdb.set_trace()
        col_num = self._generate_col_num(col_header)
        # ipdb.set_trace()
        worksheet = workbook.add_worksheet('Laporan Error B2B WO')
        worksheet.merge_range('A1:%s1' % (col_num[-1]), 'Laporan Error B2B WO', wbf['title_doc'])
        worksheet.merge_range('A2:%s2' % (col_num[-1]), 'Tanggal WO: %s s/d %s' % (str(self.start_date), str(self.end_date)), wbf['company'])
        # write header
        row = 4
        for idx, vals in enumerate(col_header):
            worksheet.write('%s%s' % (col_num[idx], row), vals['name'], wbf['header'])
        # freeze panes
        worksheet.freeze_panes(4, 2)
        # query
        branch_ids = [p.id for p in self.branch_ids]
        # ipdb.set_trace()
        query = """
            SELECT 
                row_number() OVER () AS no,
                CONCAT('[', b.code, '] ', b.name) AS dealer,
                wo.name AS wo_name,
                wo.date AS wo_date,
                wo.type AS wo_service_type,
                api_log.name AS error_code, 
                api_log.description AS error
            FROM teds_api_log api_log
            JOIN wtc_work_order wo ON CAST(api_log.transaction_id AS INTEGER) = wo.id
            JOIN wtc_branch b ON wo.branch_id = b.id
            WHERE api_log.model_name = 'wtc.work.order'
            AND CAST(api_log.transaction_id AS INTEGER) IN (
                SELECT id FROM wtc_work_order
                WHERE branch_id IN %s
                AND date BETWEEN '%s' AND '%s'
            )
        """ % (str(tuple(branch_ids)).replace(",)", ")"), self.start_date, self.end_date)
        self._cr.execute(query)
        logs = self._cr.fetchall()

        row = 5
        for x in logs:
            for idx, vals in enumerate(col_num):
                if idx in [0,2,3,4]:
                    worksheet.write('%s%s' % (vals, row), x[idx], wbf['content_center'])
                else:
                    worksheet.write('%s%s' % (vals, row), x[idx], wbf['content_number'])
                
                if len(str(x[idx])) > col_header[idx]['max_size']:
                    col_header[idx]['max_size'] = len(str(x[idx])) + 2
            row += 1
        # ipdb.set_trace()
        # set column width
        for idx, vals in enumerate(col_header):
            worksheet.set_column('%s1:%s1' % (col_num[idx], col_num[idx]), vals['max_size'])
        # set autofilter if logs = True
        if logs:
            worksheet.autofilter('A4:%s%s' % (col_num[-1], row-1))
        # close row
        worksheet.merge_range('A%s:%s%s' % (row, col_num[-1], row), '', wbf['total'])            
        # audit trail
        worksheet.write('A%s'%(row+2), '%s %s' % (str(date_generate), user_generate), wbf['footer'])

        workbook.close()
        out = base64.encodestring(fp.getvalue())
        self.write({'state_x':'get', 'report_file':out, 'name': self.name})
        fp.close()

        ir_model_data = self.env['ir.model.data']
        form_res = ir_model_data.get_object_reference('teds_api_work_order', 'view_teds_api_log_work_order_report')

        form_id = form_res and form_res[1] or False
        return {
            'name':('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.api.log.work.order.report',
            'res_id': self.ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }

    def _generate_col_num(self, col_header):
        col_num = []
        for idx, vals in enumerate(col_header):
            col_num.append(self.SHEET_COLS[idx])
        return col_num