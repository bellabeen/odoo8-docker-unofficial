import time
from datetime import datetime
from openerp import models, fields, api
from openerp.osv import osv
from openerp.tools.translate import _

class wtc_p2p_config(models.Model):
    _name = "wtc.p2p.config"
    _description ="P2P Configuration"
    _rec_name = 'supplier_id'
    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
        
    supplier_id = fields.Many2one('res.partner', string='Supplier', required=True, domain="['|',('principle','!=',False),('branch','!=',False)]")
    tentative_1 = fields.Integer(string='Tentative 1 (%)')
    tentative_2 = fields.Integer(string='Tentative 2 (%)')
    
    _sql_constraints = [
    ('unique_supplier_id', 'unique(supplier_id)', 'Master data sudah pernah dibuat !'),
    ]    
    
    @api.onchange('tentative_1','tentative_2')
    def onchange_tentative(self):
        warning = {}
        if self.tentative_1 > 100 :
            warning = {
                'title': ('Perhatian !'),
                'message': (('Nilai tentative 1 tidak boleh lebih dari 100% ! ')),
            } 
            self.tentative_1 = 0
            
        if self.tentative_2 > 100 :
            warning = {
                'title': ('Perhatian !'),
                'message': (('Nilai tentative 2 tidak boleh lebih dari 100% ! ')),
            } 
            self.tentative_2 = 0
        return {'warning':warning}    