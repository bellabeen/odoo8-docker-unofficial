import time
from datetime import datetime
from openerp import models, fields, api
from openerp.osv import osv
from openerp.tools.translate import _

class wtc_p2p_periode(models.Model):
    _name = "wtc.p2p.periode"
    _description ="P2P Periode"
        
    name = fields.Char(string='Name')
    start_date = fields.Date(string='Effective Start Date')
    end_date = fields.Date(string='Effective End Date')
    periode_start_date = fields.Date(string='Periode Start Date')
    periode_end_date = fields.Date(string='Periode End Date')
    
    _sql_constraints = [
    ('unique_name', 'unique(name)', 'Master data sudah pernah dibuat !'),
    ]  
    
    @api.onchange('start_date','end_date')
    def onchange_date(self):
        warning = {}
        if self.start_date and self.end_date :
            if self.end_date < self.start_date :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('Effective End Date tidak boleh kurang dari Effective Start Date ! ')),
                } 
                self.end_date = False                  
        return {'warning':warning}

    @api.onchange('periode_start_date','periode_end_date')
    def onchange_periode_date(self):
        warning = {}
        if self.periode_start_date and self.periode_end_date :
            if self.periode_end_date < self.periode_start_date :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('Periode End Date tidak boleh kurang dari Periode Start Date ! ')),
                } 
                self.periode_end_date = False                  
        return {'warning':warning}
        
    @api.onchange('name')
    def change_name(self):   
        warning = {}
        if self.name :
            if len(self.name) > 6 :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('Name tidak boleh lebih dari 6 digit ! ')),
                }
                self.name = False
            else :            
                cek = self.name.isdigit()
                if not cek :
                    warning = {
                        'title': ('Perhatian !'),
                        'message': (('Name hanya boleh angka ! ')),
                    }
                    self.name = False
        return {'warning':warning}     