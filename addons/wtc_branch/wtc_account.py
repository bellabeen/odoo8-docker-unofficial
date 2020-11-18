from openerp.osv import fields, osv

class account_account(osv.osv):
    _inherit = 'account.account'
    
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
        
    _columns = {
                'branch_id': fields.many2one('wtc.branch', 'Branch'),
    }
    _defaults = {
        'branch_id': _get_default_branch,
    }    
