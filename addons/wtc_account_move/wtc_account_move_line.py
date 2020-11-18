from openerp import models, fields, api

class wtc_account_move_line(models.Model):
    _inherit = 'account.move.line'
    
    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
        
    branch_id = fields.Many2one('wtc.branch', string='Branch', required=False, default=_get_default_branch)
    division = fields.Selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum'),('Finance','Finance')], 'Division', change_default=True, select=False)
    kwitansi = fields.Boolean('kwitansi')
    kwitansi_id = fields.Many2one('wtc.register.kwitansi.line',string='No Kwitansi')
    ref_asset_id = fields.Many2one('account.asset.asset',string='Ref Asset No') 
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.search(['|','|',('name', operator, name),('move_id.name', operator, name),('ref', operator, name)] + args, limit=limit)
        return recs.name_get() 
    
    @api.cr_uid_ids_context
    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        result = []

        for line in self.browse(cr, uid, ids, context=context):
            if line.name != '/':  
                if line.invoice.qq_id :
                    result.append((line.id, (line.move_id.name or '')+' ('+line.name+')'+'-'+line.invoice.qq_id.name))
                else :
                    result.append((line.id, (line.move_id.name or '')+' ('+line.name+')'))
            else:
                if line.invoice.qq_id :
                    result.append((line.id, line.move_id.name+'-'+line.invoice.qq_id.name))
                else :
                    result.append((line.id, line.move_id.name))
        return result
    