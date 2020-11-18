from openerp import models, fields, api
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import tempfile

class ReportGoogleDrive(models.Model):
    _inherit = "teds.report.google.drive"


    @api.multi
    def send_file_report_unit(self):
        obj = self.generate_excel_stock_unit()
        temp_dir = obj.get('temp_dir')
        filename = obj.get('filename')
        if temp_dir:
            path = temp_dir+'/'+filename
            date = datetime.now() + relativedelta(hours=7)
            date = date.strftime("%Y-%m-%d %H:%M:%S")
            nama_file = 'Report Stock Unit TDM '+str(date)+'.xlsx'        
            
            folder = self.env['teds.report.google.drive.config.line'].search([('tipe','=','Stock Unit')],limit=1).folder

            self.google_upload(nama_file,path,folder)
  
    @api.multi
    def send_file_report_unit_type(self):
        obj = self.generate_excel_stock_unit_type()
        temp_dir = obj.get('temp_dir')
        filename = obj.get('filename')
        if temp_dir:
            path = temp_dir+'/'+filename
            date = datetime.now() + relativedelta(hours=7)
            date = date.strftime("%Y-%m-%d %H:%M:%S")
            nama_file = 'Report Stock Unit Type TDM '+str(date)+'.xlsx'        
            
            folder = self.env['teds.report.google.drive.config.line'].search([('tipe','=','Stock Unit Type')],limit=1).folder

            self.google_upload(nama_file,path,folder)
  
        
    def generate_excel_stock_unit(self):
        date = datetime.now() 
        date = date.strftime("%Y-%m-%d")     
        data = {
            'product_ids': [],
            'location_ids': [], 
            'branch_ids': [],
        }
        fp = self.env['wtc.report.stock.unit.wizard']._query_report_detail(data)
        temp_dir = False
        filename = False
        if fp:
            filename = 'report_stock_unit_'+str(date)+'.xlsx'        
            temp_dir = tempfile.gettempdir()
            local_path = temp_dir+'/'+filename
            f = open(local_path,"w+b")
            f.write(fp.getvalue())
            
            self.create({
                'name':filename,
                'tipe':'Stock Unit',
            })
            fp.close()
        return {'filename':filename,'temp_dir':temp_dir}
    
    def generate_excel_stock_unit_type(self):
        date = datetime.now() 
        date = date.strftime("%Y-%m-%d")     
        md_id = self.env['wtc.branch'].search([('branch_type','=','MD')],limit=1).id
        data = {
            'product_ids': [],
            'location_ids': [], 
            'branch_ids': [md_id],
        }
        fp = self.env['wtc.report.stock.unit.wizard']._query_report_type_warna(data)
        temp_dir = False
        filename = False
        if fp:
            filename = 'report_stock_unit_type'+str(date)+'.xlsx'        
            temp_dir = tempfile.gettempdir()
            local_path = temp_dir+'/'+filename
            f = open(local_path,"w+b")
            f.write(fp.getvalue())
            
            self.create({
                'name':filename,
                'tipe':'Stock Unit Type',
            })
            fp.close()
        return {'filename':filename,'temp_dir':temp_dir}
