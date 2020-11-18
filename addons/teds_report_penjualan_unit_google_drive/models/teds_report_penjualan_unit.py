from openerp import models, fields, api
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import tempfile

class ReportGoogleDrive(models.Model):
    _inherit = "teds.report.google.drive"


    @api.multi
    def send_file_report_penjualan(self):
        obj = self.generate_excel_penjualan_unit()
        temp_dir = obj.get('temp_dir')
        filename = obj.get('filename')
        if temp_dir:
            path = temp_dir+'/'+filename
            date = datetime.now() + relativedelta(hours=7)
            date = date.strftime("%Y-%m-%d %H:%M:%S")
            nama_file = 'Report Stock Penjualan TDM '+str(date)+'.xlsx'        
            
            folder = self.env['teds.report.google.drive.config.line'].search([('tipe','=','Penjualan Unit')],limit=1).folder

            self.google_upload(nama_file,path,folder)
  
        
    def generate_excel_penjualan_unit(self):
        date = datetime.now() + relativedelta(hours=7)
        start_date = date.date().replace(day=1)
        end_date =  date.date() - relativedelta(days=1)
        if date.date().day == 1:
            end_date = start_date
            
        date = date.strftime("%Y-%m-%d")     
        data = {
            'product_ids': [],
            'location_ids': [], 
            'branch_ids': [],
            'sales_koordinator_id':[],
            'user_id':[],
            'options':'detail_per_chassis_engine',
            'start_date':start_date,
            'end_date':end_date,
            'state':'progress_done_cancelled',
            'finco_ids':[],
        }
        fp = self.env['wtc.report.penjualan.wizard']._print_excel_report(data)
        temp_dir = False
        filename = False
        if fp:
            filename = 'report_stock_penjualan_'+str(date)+'.xlsx'        
            temp_dir = tempfile.gettempdir()
            local_path = temp_dir+'/'+filename
            f = open(local_path,"w+b")
            f.write(fp.getvalue())
            
            self.create({
                'name':filename,
                'tipe':'Penjualan Unit',
            })
            fp.close()
        return {'filename':filename,'temp_dir':temp_dir}
        