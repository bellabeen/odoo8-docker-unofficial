from openerp.osv import fields, osv
from openerp import tools, api
    
class wtc_kecamatan(osv.osv):
    _name = 'wtc.kecamatan'
    
    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            tit = "[%s] %s" % (record.code, record.name)
            res.append((record.id, tit))
        return res
     
    def get_province_by_city(self, cr, uid, ids, city_id):
        if city_id == city_id:
            city= self.pool.get("wtc.city").browse(cr, uid, city_id)
            return {'value': {'state_id':city.state_id.id}}
        return True
    
    _columns = {
        'code':fields.char('Code',size=128,required=True),
        'name':fields.char('Name',size=128,required=True),
        'city_id': fields.many2one('wtc.city','City',required=True),
        'state_id':fields.related('city_id','state_id',type='many2one', relation='res.country.state', readonly=True, string='Province', store=False),
        'kelurahan_ids': fields.one2many('wtc.kelurahan', 'kecamatan_id', string='Kelurahan', readonly=True),
        'active':fields.boolean('Active'),
    }
    
    _sql_constraints = [
       ('code_unique', 'unique(code)', 'Code Kecamatan tidak boleh ada yang sama.'),  
    ]

    def name_search(self, cr, user, name='', args=None, operator='ilike',
                             context=None, limit=100):
        if not args:
            args = []

        ids = []
        if len(name) < 8:
            ids = self.search(cr, user, [('code', 'ilike', name)] + args,
                              limit=limit, context=context)

        search_domain = [('name', operator, name)]
        if ids: search_domain.append(('id', 'not in', ids))
        ids.extend(self.search(cr, user, search_domain + args,
                               limit=limit, context=context))

        locations = self.name_get(cr, user, ids, context)
        return sorted(locations, key=lambda (id, name): ids.index(id))
