from openerp.osv import fields, osv

class wtc_kelurahan(osv.osv):
    _name = 'wtc.kelurahan'
    
    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            tit = "[%s] %s" % (record.zip, record.name)
            res.append((record.id, tit))
        return res
    
    _columns = {
        'name': fields.char('Name',size=128,required=True),
        'code': fields.char('Code',size=128),
        'zip': fields.char('Zip Code',size=10,required=True),
        'kecamatan_id':fields.many2one('wtc.kecamatan','Kecamatan',required=True),
        'city_id':fields.related('kecamatan_id','city_id',type='many2one', relation='wtc.city', readonly=True, string='City', store=False),
        'state_id':fields.related('city_id','state_id',type='many2one', relation='res.country.state', readonly=True, string='Province', store=False),
        'active':fields.boolean('Active'),
     }
    _sql_constraints = [
       ('code_unique', 'unique(zip)', 'Kode POS tidak boleh ada yang sama.'),  
    ]

    def name_search(self, cr, user, name='', args=None, operator='ilike',
                             context=None, limit=100):
        if not args:
            args = []

        ids = []
        if len(name) < 6:
            ids = self.search(cr, user, [('zip', 'ilike', name)] + args,
                              limit=limit, context=context)

        search_domain = [('name', operator, name)]
        if ids: search_domain.append(('id', 'not in', ids))
        ids.extend(self.search(cr, user, search_domain + args,
                               limit=limit, context=context))

        locations = self.name_get(cr, user, ids, context)
        return sorted(locations, key=lambda (id, name): ids.index(id))
