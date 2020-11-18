from openerp import models, fields, api
from datetime import datetime,date
from openerp.exceptions import except_orm, Warning, RedirectWarning

class InsentiveSalesReport(models.TransientModel):
    _name = "teds.insentive.salesman.report.wizard"

    def _get_tahun(self):
        return date.today().year

    wbf = {}

    name = fields.Char('Filename')
    state_x = fields.Selection([('choose','choose'),('get','get')], default='choose')
    data_x = fields.Binary('File', readonly=True)
    job_title = fields.Selection([
        ('Sales Payroll','Sales Payroll'),
        ('Sales Partner','Sales Partner'),
        ('Sales Counter','Sales Counter'),
        ('Sales Kordinator','Sales Kordinator')],string="Job Title")

    bulan = fields.Selection([
        ('1','Januari'),
        ('2','Februari'),
        ('3','Maret'),
        ('4','April'),
        ('5','Mei'),
        ('6','Juni'),
        ('7','Juli'),
        ('8','Agustus'),
        ('9','September'),
        ('10','Oktober'),
        ('11','November'),
        ('12','Desember')], 'Periode', required=True)
    tahun = fields.Char('Tahun', default=_get_tahun,required=True)

    @api.multi
    def add_workbook_format(self, workbook):
        self.wbf['header'] = workbook.add_format({'bold': 1,'align': 'center','bg_color': '#FFFFDB','font_color': '#000000'})
        self.wbf['header'].set_border()
        self.wbf['header'].set_font_size(10)


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
        self.wbf['title_doc'].set_font_size(10)
        
        self.wbf['company'] = workbook.add_format({'bold':1,'align': 'left'})
        self.wbf['company'].set_font_size(11)
        
        self.wbf['content'] = workbook.add_format()
        self.wbf['content'].set_left()
        self.wbf['content'].set_right() 
        
        self.wbf['content_float'] = workbook.add_format({'align': 'right','num_format': '#,##0.00'})
        self.wbf['content_float'].set_right() 
        self.wbf['content_float'].set_left()

        self.wbf['content_center'] = workbook.add_format({'align': 'centre'})
        self.wbf['content_center'].set_align('vcenter')
        self.wbf['content_center'].set_font_size(10)
        
        self.wbf['content_number'] = workbook.add_format({'align': 'right'})
        self.wbf['content_number'].set_right() 
        self.wbf['content_number'].set_left() 
                
        self.wbf['content_right'] = workbook.add_format({'align': 'right'})
        self.wbf['content_right'].set_right() 
        self.wbf['content_right'].set_left() 
                
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
        
        self.wbf['total_number_float'] = workbook.add_format({'align':'right','bg_color': '#FFFFDB','bold':1})
        self.wbf['total_number_float'].set_top()
        self.wbf['total_number_float'].set_bottom()            
        self.wbf['total_number_float'].set_left()
        self.wbf['total_number_float'].set_right()
       
        self.wbf['total'] = workbook.add_format({'bold':1,'bg_color': '#FFFFDB','align':'center'})
        self.wbf['total'].set_left()
        self.wbf['total'].set_right()
        self.wbf['total'].set_top()
        self.wbf['total'].set_bottom()
        
        return workbook

    def generate_branch(self):
        datas = {}
        
        branches = """
            SELECT id
            , code
            , name
            FROM wtc_branch
            WHERE branch_type = 'DL'
        """
        self._cr.execute(branches)
        ress = self._cr.dictfetchall()
        for res in ress:
            if not datas.get(res.get('id')):
                datas[res['id']] = {'branch_code':res['code'],'branch_name':res['name']}
        return datas

    @api.multi
    def excel_report(self):
        self.ensure_one()

        if self.job_title == 'Sales Payroll':
            return self.sales_payroll_report()
        elif self.job_title == 'Sales Partner':
            return self.sales_partner_report()
        elif self.job_title == 'Sales Counter':
            return self.sales_counter_report()
        elif self.job_title == 'Sales Kordinator':
            return self.sales_kordinator_report()

