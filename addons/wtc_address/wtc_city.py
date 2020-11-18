from openerp.osv import fields, osv


class wtc_city(osv.osv):
    _name = 'wtc.city'
    
    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            tit = "[%s] %s" % (record.code, record.name)
            res.append((record.id, tit))
        return res

    _columns = {
        'code': fields.char('Code',size=128,required=True),
        'name':fields.char('Name',size=128,required=True),
        'state_id':fields.many2one('res.country.state', 'Province',required=True),
        'kecamatan_ids': fields.one2many('wtc.kecamatan', 'city_id', string='Kecamatan', readonly=True),
        'active':fields.boolean('Active'),
    }
    _sql_constraints = [
       ('code_unique', 'unique(code)', 'Code City tidak boleh ada yang sama.'),  
    ]

    def name_search(self, cr, user, name='', args=None, operator='ilike',
                             context=None, limit=100):
        if not args:
            args = []

        ids = []
        if len(name) < 5:
            ids = self.search(cr, user, [('code', 'ilike', name)] + args,
                              limit=limit, context=context)

        search_domain = [('name', operator, name)]
        if ids: search_domain.append(('id', 'not in', ids))
        ids.extend(self.search(cr, user, search_domain + args,
                               limit=limit, context=context))

        locations = self.name_get(cr, user, ids, context)
        return sorted(locations, key=lambda (id, name): ids.index(id))
