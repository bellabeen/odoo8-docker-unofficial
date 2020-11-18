import base64
import shutil
from openerp import models, fields, api
from openerp.exceptions import Warning,ValidationError

class ConfigFiles(models.Model):
    _name = "teds.config.files"
    _description = "Configuration of Saved Files"
    
    host_remote = fields.Char(string='Host Remote', required=True)
    user_remote = fields.Char(string='User Remote', required=True)
    password_remote = fields.Char(string='Password Remote', required=True)
    folder_path_remote = fields.Char(string='Folder Path Remote',required=True)
    folder_path_local = fields.Char(string='Folder Path Local',required=True)

    def _config_check(self):
        obj = self.search([])
        if not obj:
            raise Warning('Belum ada konfigurasi berkas!')
        return obj

    @api.model
    def create(self,vals):
        cek = self.search([]) 
        if len(cek) > 0:
            raise Warning('Konfigurasi sudah dibuat!')
        return super(ConfigFiles,self).create(vals)

    def upload_file(self,file_name,file):
        config_obj = self._config_check()
        local_path = config_obj.folder_path_local
        link = local_path+'/'+file_name
        data = base64.decodestring(file)
        open(link, 'wb').write(data)

    def get_file(self,file_name):
        config_obj = self._config_check()
        local_path = config_obj.folder_path_local
        file_get = open(local_path+'/'+file_name, 'rb').read()
        file = base64.encodestring(file_get)
        return file

    def copy_file(self, original, target):
        config_obj = self._config_check()
        local_path = config_obj.folder_path_local
        shutil.copyfile(local_path+'/'+original, local_path+'/'+target)

    @api.multi
    def name_get(self, context=None):
        if context is None:
            context = {}
        res = []
        for record in self :
            tit = "%s / %s" % (record.host_remote, record.user_remote)
            res.append((record.id, tit))
        return res