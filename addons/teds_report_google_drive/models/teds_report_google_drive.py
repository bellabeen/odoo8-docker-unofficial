from datetime import datetime, timedelta
from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning
from cStringIO import StringIO
import tempfile
import base64
import os

import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload


SCOPES = ['https://www.googleapis.com/auth/drive']

class ReportGoogleDriveType(models.Model):
    _name = "teds.report.google.drive.type"

    name = fields.Char('Name')

    @api.model
    def create(self,vals):
        vals['name'] = vals['name'].title()
        return super(ReportGoogleDriveType,self).create(vals)
    
    @api.multi
    def write(self,vals):
        if vals.get('name'):
            vals['name'] = vals['name'].title()
        return super(ReportGoogleDriveType,self).write(vals)

class ReportGoogleDriveConfig(models.Model):
    _name = "teds.report.google.drive.config"

    name = fields.Char('Name')
    pickle_file = fields.Binary('Pickle FIle')
    credential_file = fields.Binary('Credential File')
    detail_ids = fields.One2many('teds.report.google.drive.config.line','config_id')

    @api.model
    def create(self,vals):
        cek = self.search([])
        if cek:
            raise Warning('Config sudah ada !')
        return super(ReportGoogleDriveConfig,self).create(vals)

class ReportGoogleDriveConfigLine(models.Model):
    _name = "teds.report.google.drive.config.line"

    def _get_type(self):
        tipes = self.env['teds.report.google.drive.type'].search([])
        ids = []
        for tipe in tipes:
            ids.append((tipe.name,tipe.name))
        return ids

    config_id = fields.Many2one('teds.report.google.drive.config','Config',ondelete='cascade')
    tipe = fields.Selection(selection=_get_type,string='Type')
    folder = fields.Char('Folder Google Drive')


class ReportGoogleDrive(models.Model):
    _name = "teds.report.google.drive"

    @api.model
    def _get_default_date(self): 
        return datetime.now().today()
  
    name = fields.Char('Nama File')
    tipe = fields.Char('Report Type')
    date = fields.Date('Tanggal',default=_get_default_date)
    gdrive_file_id = fields.Char('ID File GDrive')
    
    def google_upload(self, nama_file, path, folder, options="create", file_id=None):
        creds = None
        config = self.env['teds.report.google.drive.config'].search([],limit=1)
        d1 = base64.decodestring(config.pickle_file)
        d2 = base64.decodestring(config.credential_file)
        fobj = tempfile.NamedTemporaryFile(delete=False)
        fobj2 = tempfile.NamedTemporaryFile(delete=False)
        pickle_file = fobj.name
        credential_file = fobj2.name
        fobj.write(d1)
        fobj.close()
        
        fobj2.write(d2)
        fobj2.close()

        # pickle_file = b64decode(config.pickle_file)
        # print "pickle_file////////////",pickle_file
        # credentials_file = b64decode(config.credential_file)
        # print "credential_file////////////////",credential_file

        if os.path.exists(pickle_file):
            with open(pickle_file, 'rb') as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    credential_file, SCOPES)
                creds = flow.run_local_server()
            with open(pickle_file, 'wb') as token:
                pickle.dump(creds, token)

        service = build('drive', 'v3', credentials=creds, cache_discovery=False)

        media = MediaFileUpload(path, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        if options == 'create':
            file_metadata = {'name': nama_file,'parents': [folder]}
            file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        elif options == 'update':
            file = service.files().update(fileId=file_id, media_body=media, fields='id').execute()
        return file


        