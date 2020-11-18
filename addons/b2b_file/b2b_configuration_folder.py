import time
from datetime import datetime
from openerp import models, fields, api
from openerp.osv import osv



class b2b_configuration_folder(models.Model):
    _name = "b2b.configuration.folder"
    _descriptoin= "B2B Configuration File"
    
    
    @api.model
    def create(self,val,context=None):
        
        object_cek=self.search([('active','=',True)])
        if object_cek and val['active'] == True :
            raise osv.except_osv(('Perhatian !'), ('Terdapat Configuration Yang Active!'))      
        return super(b2b_configuration_folder,self).create(val)
    
    
    folder_in = fields.Char(string='Folder In',required=True)
    folder_proses = fields.Char(string='Folder Proses',required=True)
    folder_archin = fields.Char(string='Folder Archin',required=True)
    folder_error = fields.Char(string='Folder Error',required=True)
    active = fields.Boolean(string='Active')
    
    
    