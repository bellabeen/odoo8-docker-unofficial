from openerp.osv import fields, osv


class work_order_wip(osv.osv_memory):
    _name = 'work_order.wip'
    _description = 'WIP'

    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False  
        return branch_ids 

    def _get_default_date(self,cr,uid,ids,context=None):
        return self.pool.get('wtc.branch').get_default_date(cr,uid,ids,context=context)
    
    _columns = {
        'branch_id':fields.many2one('wtc.branch','Branch',required=True),    }
    _defaults = {
        'branch_id':_get_default_branch,    
    }

    def print_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        obj = self.browse(cr, uid, ids, context=context)
        
        datas = {'ids': context.get('active_ids', [])}
        res = {
            'branch_id':obj.branch_id.id,
            'branch_name':obj.branch_id.name,
        }
        datas['form'] = res
        return self.pool['report'].get_action(cr, uid, [], 'wtc_work_order.wtc_work_order_wip_report', data=datas, context=context)
