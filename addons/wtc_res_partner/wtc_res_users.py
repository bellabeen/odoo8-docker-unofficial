from openerp.osv import fields, osv

class wtc_res_users(osv.osv):
    _inherit = 'res.users'

    def create(self, cr, uid, vals, context=None):
        if vals.get('login') and not vals.get('default_code') :
            vals['default_code'] = vals.get('login')
        user_id = super(wtc_res_users, self).create(cr, uid, vals, context=context)
        return user_id
    
    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            tit = "[%s] %s" % (record.login, record.name)
            res.append((record.id, tit))
        return res    
    
    def unlink(self,cr,uid,ids,context=None):
        for item in self.browse(cr, uid, ids, context=context):
                raise osv.except_osv(('Perhatian !'), ("Tidak boleh menghapus users"))
        return False
        
    def name_search(self, cr, user, name='', args=None, operator='ilike',
                             context=None, limit=100):
        if not args:
            args = []

        ids = []
        if len(name) < 11:
            ids = self.search(cr, user, [('login', 'ilike', name)] + args,
                              limit=limit, context=context)

        search_domain = [('name', operator, name)]
        if ids: search_domain.append(('id', 'not in', ids))
        ids.extend(self.search(cr, user, search_domain + args,
                               limit=limit, context=context))

        locations = self.name_get(cr, user, ids, context)
        return sorted(locations, key=lambda (id, name): ids.index(id))    