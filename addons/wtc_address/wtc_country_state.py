from openerp.osv import fields, osv

class wtc_country_state (osv.osv):
    _inherit = 'res.country.state'
    
    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            tit = "[%s] %s" % (record.code, record.name)
            res.append((record.id, tit))
        return res
    
    def get_kec(self, cr, uid, ids, kec_id):
        if kec_id != False:
            kec= self.pool.get("wtc.kecamatan").browse(cr, uid,kec_id).name
            return {'value': {'kec_name':kec }}
        return True
     
    _columns = {
        'code':fields.char('Code',size=7),
        'city_ids': fields.one2many('wtc.city', 'state_id', string='City', readonly=True),
    }
    _sql_constraints = [
       ('code_unique', 'unique(code)', 'Kode Provinsi tidak boleh ada yang sama.'),  
    ]
