import time
from datetime import datetime
from openerp.osv import fields, osv

class wtc_kategori_nilai_mesin(osv.osv):
    _name = "wtc.kpb.engine.type"     
    _columns = {
                'engine_no' :fields.char('Engine Number'),
                'name':fields.char('Kategori'),
                'kategori_line': fields.one2many('wtc.kpb.engine.price','kategori_id', string='Kategori Nilai Mesin'),
    }
    _sql_constraints = [
    ('unique_name_engine_no', 'unique(name,engine_no)', 'Nomor Engine dan Nama Kategori harus unik !'),
]    
class wtc_kategori_nilai_mesin_line(osv.osv):
    _name = "wtc.kpb.engine.price"
    _rec_name = "kpb_ke"
    _columns = {
                
                'kategori_id' : fields.many2one('wtc.kpb.engine.type',string="Kategori Nilai Mesin"),
                'kpb_ke' :fields.integer('KPB Ke'),
                'jasa':fields.float('Jasa'),
                'oli':fields.float('Oli'),

                } 
    