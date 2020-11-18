from openerp import models, fields
from openerp.exceptions import Warning
from datetime import timedelta,datetime,date
import tempfile
import pysftp


class MftServConf(models.Model):
    _name = "teds.mft.serv.conf"
    _description = "Configuration MFT Server"
    
    # @api.model
    # def create(self,val,context=None):
    #     object_cek=self.search([('active','=',True)])
    #     if object_cek and val['active'] == True :
    #         raise Warning ('Perhatian, Terdapat Configuration Yang Active!')
    #     return super(MftServConf,self).create(val)
    
    host_remote = fields.Char(string='Host Remote', required=True)
    user_remote = fields.Char(string='User Remote', required=True)
    password_remote = fields.Char(string='Password Remote', required=True)
    folder_path_remote = fields.Char(string='Folder Path Remote',required=True)
    active = fields.Boolean(string='Active')