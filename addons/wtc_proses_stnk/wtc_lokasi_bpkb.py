import time
from datetime import datetime
from openerp.osv import fields, osv

class wtc_lokasi_bpkb(osv.osv):
    _name = "wtc.lokasi.bpkb"
    
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
        
    _columns = {
                'name' : fields.char('Nama'),
                'description' : fields.char('Description'),
                'branch_id' : fields.many2one('wtc.branch',string="Branch"),
                'alamat' : fields.char('Alamat'),
                'city_id' : fields.many2one('wtc.city', 'Kota'),
                'bpkb_ids' : fields.one2many('stock.production.lot','lokasi_bpkb_id',string="BPKB Line"),
                'type': fields.selection([('internal', 'Internal Location'), ('transit','Transit Location')], 'Type'),
                'customer_stnk': fields.related('stnk_ids', 'customer_stnk', type='many2one', relation='res.partner', string='Customer STNK'),
                'engine_no': fields.related('stnk_ids', 'name', type='char', string='No Engine'),
                'no_stnk': fields.related('stnk_ids', 'no_stnk', type='char', string='No STNK'),
                                     
                }    
    
    _defaults = {
        'branch_id': _get_default_branch,
    }
        
    _sql_constraints = [
    ('unique_lokasi_bpkb', 'unique(name,branch_id)', 'Lokasi BPKB duplicate, mohon cek kembali !'),
]  
    
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.bpkb_ids.name :
                raise osv.except_osv(('Perhatian !'), ("Master Lokasi tidak bisa didelete !"))
        return super(wtc_lokasi_bpkb, self).unlink(cr, uid, ids, context=context)