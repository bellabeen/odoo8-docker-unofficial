import time
from datetime import datetime
from openerp import models, fields, api

class wtc_branch_config(models.Model):
    _name = "wtc.branch.config"

    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
        
    name = fields.Char(string="Name",readonly=True)
    branch_id = fields.Many2one('wtc.branch',string="Branch",required=True, default=_get_default_branch)

    _sql_constraints = [
    ('unique_name', 'unique(name)', 'Data Branch sudah ada. Mohon cek kembali !')]
    
    @api.model
    def create(self,vals):
        branch = self.env['wtc.branch'].search([('id','=',vals['branch_id'])])
        vals['name'] = branch.code
        return super(wtc_branch_config, self).create(vals)
