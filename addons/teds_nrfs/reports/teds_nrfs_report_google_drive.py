import tempfile
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from calendar import monthrange
from openerp import models, fields, api
from openerp.exceptions import Warning

class ReportNrfsGoogleDrive(models.Model):
    _inherit = "teds.report.google.drive"

    def generate_excel_nrfs(self):
        today = (datetime.now() + relativedelta(hours=7)).date()
        start_date = today.replace(day=1).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
        datas = self.env['teds.nrfs.report.wizard']._generate_excel_buffer_nrfs(start_date=start_date, end_date=end_date, state=None, include_not_done=True)
        temp_dir = False
        if datas:
            temp_dir = tempfile.gettempdir()
            local_path = temp_dir+'/'+datas[1]
            f = open(local_path,"w+b")
            f.write(datas[0].getvalue())
            datas[0].close()
            teds_file_obj = self.create({'name': datas[1], 'tipe': 'Report Nrfs Md'})
        return {'temp_dir':temp_dir, 'filename':datas[1], 'teds_file_obj': teds_file_obj}

    @api.multi
    def send_file_report_nrfs(self):
        config_obj = self.env['teds.report.google.drive.config.line'].search([('tipe','=','Report Nrfs Md')],limit=1)
        if not config_obj:
            raise Warning('Konfigurasi folder GDrive untuk tipe NRFS tidak ditemukan!')
        file_obj = self.generate_excel_nrfs()
        temp_dir = file_obj.get('temp_dir')
        filename = file_obj.get('filename')
        teds_file_obj = file_obj.get('teds_file_obj')
        if temp_dir:
            path = temp_dir+'/'+filename
            today = datetime.now() + relativedelta(hours=7)
            nama_file = 'Report NRFS TDM ' + today.strftime("%m%Y") + '.xlsx'
            gdrive_file_id = {'id': ''}
            if today.day == 1: # Awal bulan: upload baru
                gdrive_file_id = self.google_upload(nama_file, path, config_obj.folder)
            else: # Bukan awal bulan: update file
                gdrive_file_id['id'] = self.search([('tipe','=','Report Nrfs Md'),('id','!=',teds_file_obj.id)], order="id desc", limit=1).gdrive_file_id
                if gdrive_file_id['id']:
                    self.google_upload(nama_file, path, config_obj.folder, "update", gdrive_file_id['id'])
                else: # Bukan awal bulan: upload baru (mestinya hanya eksekusi sekali)
                    gdrive_file_id = self.google_upload(nama_file, path, config_obj.folder)
            teds_file_obj.suspend_security().write({'gdrive_file_id': str(gdrive_file_id['id'])})