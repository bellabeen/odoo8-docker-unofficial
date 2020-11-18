from openerp.osv import osv, fields

class wtc_account_journal(osv.osv):
    _inherit = 'account.journal'

    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
    
    _columns = {
        'code': fields.char('Code', size=8, required=True, help="The code will be displayed on reports."),
	    'branch_id':fields.many2one('wtc.branch', string='Branch'),
    }
    _defaults = {
      'branch_id': _get_default_branch,
     }
    def _auto_init(self, cr, context=None):
    	self._sql_constraints = [
	        ('code_company_uniq', 'unique (code, branch_id, company_id)', 'The code of the journal must be unique per branch !'),
	        ('name_company_uniq', 'unique (name, company_id)', 'The name of the journal must be unique per company !'),
    	]
    	super(wtc_account_journal,self)._auto_init(cr, context)

    def copy(self, cr, uid, id, default=None, context=None):
        default = dict(context or {})
        #journal = self.browse(cr, uid, id, context=context)
        #default.update(
        #    code=_("%s (copy)") % (journal['code'] or ''),
        #    name=_("%s (copy)") % (journal['name'] or ''))
        return super(wtc_account_journal, self).copy(cr, uid, id, default, context=context)
