import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
import string  

class wtc_cddb(osv.osv):
    _name = "wtc.cddb"

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            tit = "%s" % (record.cddb_code,)
            res.append((record.id, tit))
        return res
    
    def _get_code(self, cr, uid, context=None):
        if context is None: context = {}
        return context.get('kode_customer', False)
    
             
    _columns = {
                "kartukeluarga_ids": fields.related("customer_id", "kartukeluarga_ids", type="one2many",
                                          relation="wtc.kartu.keluarga"),
                'customer_id' : fields.many2one('res.partner','customer_id'),
                'name' :fields.char('Name'),
                'status_hp_id' : fields.many2one('wtc.questionnaire','Status HP',domain=[('type','=','Status HP')]),
                'status_rumah_id' : fields.many2one('wtc.questionnaire','Status Rumah',domain=[('type','=','Status Rumah')]),
                'kode_customer' : fields.selection([('G','Group Customer'),('I','Individual Customer(Regular)'),('J','Individual Customer (Joint Promo)'),('C','Individual Customer (Kolektif)')], string="Kode Customer", change_default=True),
                'penanggung_jawab' : fields.char('Penanggung Jawab'),
                'jenis_kelamin_id' : fields.many2one('wtc.questionnaire','Jenis Kelamin',domain=[('type','=','JenisKelamin')]),
                'dpt_dihubungi' : fields.selection([('Y','Ya'),('N','Tidak')],string="Dapat Dihubungi"),
                'agama_id' : fields.many2one('wtc.questionnaire','Agama',domain=[('type','=','Agama')]),
                'pendidikan_id' : fields.many2one('wtc.questionnaire','Pendidikan',domain=[('type','=','Pendidikan')]),
                'pekerjaan_id' : fields.many2one('wtc.questionnaire','Pekerjaan',domain=[('type','=','Pekerjaan')]),
                'pengeluaran_id' : fields.many2one('wtc.questionnaire','Pengeluaran',domain=[('type','=','Pengeluaran')]),
                'merkmotor_id' : fields.many2one('wtc.questionnaire','Merk Motor',domain=[('type','=','MerkMotor')]),
                'jenismotor_id' : fields.many2one('wtc.questionnaire','Jenis Motor',domain=[('type','=','JenisMotor')]),
                'penggunaan_id' : fields.many2one('wtc.questionnaire','Penggunaan',domain=[('type','=','Penggunaan')]),
                'pengguna_id' : fields.many2one('wtc.questionnaire','Pengguna',domain=[('type','=','Pengguna')]),
                'program' : fields.selection([('1','Loyality Member Card'),('2','Comunity Program')],string="Program"),
                'id_program' : fields.char('ID'),
                'no_ktp':fields.char('No KTP'),
                'cddb_code':fields.char(string="CDDB Code"),
                'birtdate':fields.date('Day of Birth'),
                'no_hp':fields.char('Mobile'),
                'no_telp' : fields.char('Phone'),
                'street': fields.char('Address'),
                'street2': fields.char(),
                'rt':fields.char('RT', size=3),
                'rw':fields.char('RW',size=3),
                'zip_id':fields.many2one('wtc.kelurahan', 'ZIP Code',domain="[('kecamatan_id','=',kecamatan_id),('state_id','=',state_id),('city_id','=',city_id)]"),
                'kelurahan':fields.char('Kelurahan',size=100), 
                'kecamatan_id':fields.many2one('wtc.kecamatan','Kecamatan', size=128,domain="[('state_id','=',state_id),('city_id','=',city_id)]"),
                'kecamatan':fields.char('Kecamatan', size=100),
                'city_id':fields.many2one('wtc.city','City',domain="[('state_id','=',state_id)]"),
                'state_id':fields.many2one('res.country.state', 'Province'),
                'default_code':fields.char(string="Default Code"),
                'suku':fields.char(string="Suku"),
                'pin_bbm':fields.char(string="PIN BBM"),
                'hobi' : fields.many2one('wtc.questionnaire','Hobi',domain=[('type','=','Hobi')]),
                'facebook':fields.char(string="Facebook"),
                'instagram':fields.char(string="Instagram"),
                'twitter':fields.char(string="Twitter"),
                'path':fields.char(string="Path"),
                'jabatan':fields.char(string="Jabatan"),
                'no_wa':fields.char(string="No WhatsApp (WA)"),
                'gol_darah':fields.many2one('wtc.questionnaire','Golongan Darah',domain=[('type','=','GolonganDarah')]),
                'youtube':fields.char(string="Youtube")




                
      }

    _defaults = {
        'kode_customer':_get_code,
    }

    _sql_constraints = [
    ('unique_name_code', 'unique(customer_id,cddb_code)', 'Data CDDB sudah ada, silahkan cek kembali Nama Konsumen dan Code CDDB !'),
] 

    def change_rtrw(self,cr,uid,ids,rt,rw,context=None):   
        value = {}
        warning = {}
        if rt :
            if len(rt) > 3 :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('RT tidak boleh lebih dari 3 digit ! ')),
                }
                value = {
                         'rt':False
                         }
            else :
                cek = rt.isdigit()
                if not cek :
                    warning = {
                        'title': ('Perhatian !'),
                        'message': (('RT hanya boleh angka ! ')),
                    }
                    value = {
                             'rt':False
                             }
        if rw :
            if len(rw) > 3 :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('RW tidak boleh lebih dari 3 digit ! ')),
                }
                value = {
                         'rw':False
                         }
            else :            
                cek = rw.isdigit()
                if not cek :
                    warning = {
                        'title': ('Perhatian !'),
                        'message': (('RW hanya boleh angka ! ')),
                    }
                    value = {
                             'rw':False
                             }       
        return {'warning':warning,'value':value} 
             
    def change_nomor(self,cr,uid,ids,nohp,notelp,context=None):
        value = {}
        warning = {}
        if nohp :
            if len(nohp) > 12 :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('No HP tidak boleh lebih dari 12 digit ! ')),
                }
                value = {
                         'no_hp':False
                         }
            else :
                cek = nohp.isdigit()
                if not cek :
                    warning = {
                        'title': ('Perhatian !'),
                        'message': (('No HP hanya boleh angka ! ')),
                    }
                    value = {
                             'no_hp':False
                             }
        if notelp :
            if len(notelp) > 11 :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('No Telepon tidak boleh lebih dari 11 digit ! ')),
                }
                value = {
                         'no_telp':False
                         }
            else :            
                cek = notelp.isdigit()
                if not cek :
                    warning = {
                        'title': ('Perhatian !'),
                        'message': (('No Telepon hanya boleh angka ! ')),
                    }
                    value = {
                             'no_telp':False
                             }       
        return {'warning':warning,'value':value} 
           
    def create(self,cr,uid,vals,context=None):          
        partner = self.pool.get('res.partner').browse(cr,uid,vals['customer_id'])
        cddb = super(wtc_cddb, self).create(cr, uid, vals, context=context) 
        data = self.browse(cr,uid,cddb)
        cddb_code = self.get_cddb_code(cr, uid, data.id, partner.name,data.customer_id,context)
  
        if data.kode_customer == 'I' or data.kode_customer == 'C' :
            data.write({'penanggung_jawab':'N'})
            if data.no_hp == False :
                data.write({'no_hp':'01234'})
        
        data.write({'cddb_code':cddb_code})
        return cddb

    def get_cddb_code(self,cr,uid,ids,name,customer_id,context=None):
        cddb_code = name.replace(' ','')
        cddb_code = cddb_code[:10]
        cddb = self.pool.get('wtc.cddb').search(cr,uid,[
                                                        ('customer_id','=',customer_id.id),
                                                        ])
        split_code = []
        cddb_brw = self.pool.get('wtc.cddb').browse(cr,uid,cddb)
            
        if len(cddb) == 1 :
            
            a = '001'
            cddb_code = cddb_code + a
                    
        elif cddb_brw :
            for x in cddb_brw :
                if x.cddb_code :
                    split = int(x.cddb_code[-3:])
                    split_code.append(split)
            split = max(split_code)
            code = split + 1
            code = str(code)
            
            if len(code) == 1 :
                cddb_code = cddb_code + '00' + code
            elif len(code) == 2 :
                cddb_code = cddb_code + '0' + code
            else :
                cddb_code = cddb_code + code

        return cddb_code
                    
    def write(self,cr,uid,ids,vals,context=None):
        lot = self.pool.get('stock.production.lot')
        lot_search = lot.search(cr,uid,[
                                        ('cddb_id','=',ids),
                                        ('lot_status_cddb','!=','ok')
                                        ])
        if lot_search :
            lot_browse = lot.browse(cr,uid,lot_search)
            for x in lot_browse :
                if x.lot_status_cddb == 'udstk' :
                    lot_browse.write({'lot_status_cddb':'ok'})
                if x.lot_status_cddb == 'ok' :
                    lot_browse.write({'lot_status_cddb':'ok'})
                if x.lot_status_cddb == 'not' :
                    lot_browse.write({'lot_status_cddb':'cddb'})                    
            
        return super(wtc_cddb, self).write(cr, uid, ids, vals, context=context) 
    
    def unlink(self,cr,uid,ids,context=None):
        lot = self.pool.get('stock.production.lot')
        lot_search = lot.search(cr,uid,[
                                        ('cddb_id','=',ids)
                                        ])
        if lot_search :
            lot_browse = lot.browse(cr,uid,lot_search)
            lot_browse.write({'lot_status_cddb':'not'})
            
        return super(wtc_cddb, self).unlink(cr, uid, ids, context=context) 
    
    def get_domain(self,cr,uid,ids,val,no_hp,name,context=None):
        domain = {}
        value = {}
        warning = {}
        obj = self.pool.get('wtc.questionnaire')
        cekname = name.upper()
        
        if val :
            if cekname[:2] == "PT" or cekname[:2] == "CV" :
                if val not in ['G','J']:
                    warning = {
                                'title': ('Perhatian !'),
                                'message': (('PT atau CV hanya boleh memilih Group Customer / Joint Promo ! ')),                       
                               }
                    value = {
                             'kode_customer':False,
                             }
                    return {'warning':warning,'value':value}  
                 
            elif 'KOPERASI' in cekname or 'KOPRASI' in cekname or 'DINAS' in cekname:
                if val not in ['G','J']:
                    warning = {
                                'title': ('Perhatian !'),
                                'message': (('Koperasi atau Dinas hanya boleh memilih Group Customer / Joint Promo ! ')),                       
                               }
                    value = {
                             'kode_customer':False,
                             }
                    return {'warning':warning,'value':value}                             
        
        #JenisKelamin
        if name :
            search_jk = obj.search(cr,uid,[
                                           ('type','=','JenisKelamin'),
                                           ('name','=','GROUP CUSTOMER/JOINT PROMO')
                                           ])
            browse_jk = obj.browse(cr,uid,search_jk)
            
            #Agama
            search_agm = obj.search(cr,uid,[
                                           ('type','=','Agama'),
                                           ('name','=','GROUP CUSTOMER/JOINT PROMO')
                                           ])
            #Hobi
            search_agm = obj.search(cr,uid,[
                                           ('type','=','Hobi'),
                                           ('name','=','GROUP CUSTOMER/JOINT PROMO')
                                           ])
            #GolDarah
            search_agm = obj.search(cr,uid,[
                                           ('type','=','GolonganDarah'),
                                           ('name','=','GROUP CUSTOMER/JOINT PROMO')
                                           ])
            browse_agm = obj.browse(cr,uid,search_agm)
            
            #Pendidikan
            search_pdd = obj.search(cr,uid,[
                                           ('type','=','Pendidikan'),
                                           ('name','=','GROUP CUSTOMER/JOINT PROMO')
                                           ])
            browse_pdd = obj.browse(cr,uid,search_pdd)   
            
            #Pekerjaan
            search_pkj = obj.search(cr,uid,[
                                           ('type','=','Pekerjaan'),
                                           ('name','=','GROUP CUSTOMER/JOINT PROMO')
                                           ])
            browse_pkj = obj.browse(cr,uid,search_pkj)     
            
            #Pengeluaran        
            search_png = obj.search(cr,uid,[
                                           ('type','=','Pengeluaran'),
                                           ('name','=','GROUP CUSTOMER/JOINT PROMO')
                                           ])
            browse_png = obj.browse(cr,uid,search_png) 
            
            #MerkMotor        
            search_mmt = obj.search(cr,uid,[
                                           ('type','=','MerkMotor'),
                                           ('name','=','GROUP CUSTOMER/JOINT PROMO')
                                           ])
            browse_mmt = obj.browse(cr,uid,search_mmt)
    
            #JenisMotor        
            search_jmt = obj.search(cr,uid,[
                                           ('type','=','JenisMotor'),
                                           ('name','=','GROUP CUSTOMER/JOINT PROMO')
                                           ])
            browse_jmt = obj.browse(cr,uid,search_jmt)
    
            #Penggunaan      
            search_penggunaan = obj.search(cr,uid,[
                                           ('type','=','Penggunaan'),
                                           ('name','=','GROUP CUSTOMER/JOINT PROMO')
                                           ])
            browse_penggunaan = obj.browse(cr,uid,search_penggunaan)
            
            #Pengguna     
            search_pengguna = obj.search(cr,uid,[
                                           ('type','=','Pengguna'),
                                           ('name','=','GROUP CUSTOMER/JOINT PROMO')
                                           ])
            browse_pengguna = obj.browse(cr,uid,search_pengguna)
            
            #StatusRumah     
            search_str = obj.search(cr,uid,[
                                           ('type','=','Status Rumah'),
                                           ('name','=','GROUP CUSTOMER')
                                           ])
            browse_str = obj.browse(cr,uid,search_str)
    
            #StatusHP   
            search_hp = obj.search(cr,uid,[
                                           ('type','=','Status HP'),
                                           ('name','=','Tidak Memiliki')
                                           ])
            browse_hp = obj.browse(cr,uid,search_hp)
            
            if no_hp :
                #Status HP
                domain['status_hp_id']=[('type','=','Status HP'),('name','!=','Tidak Memiliki')]
                
            if no_hp == False :
                #Value HP
                domain['status_hp_id']=[('type','=','Status HP'),('name','=','Tidak Memiliki')]
                value['status_hp_id']=browse_hp.id 
                    
            if val == 'G' :
                #StatusRumah
                domain['status_rumah_id']=[('type','=','Status Rumah'),('name','=','GROUP CUSTOMER')]
                value['status_rumah_id']=browse_str.id
                
            if val == 'G' or val == 'J' :
                #JenisKelamin
                domain['jenis_kelamin_id']=[('type','=','JenisKelamin'),('name','=','GROUP CUSTOMER/JOINT PROMO')]
                value['jenis_kelamin_id']=browse_jk.id
                
                #Agama
                domain['agama_id']=[('type','=','Agama'),('name','=','GROUP CUSTOMER/JOINT PROMO')]
                value['agama_id']=browse_agm.id
                
                #Hobi
                domain['hobi']=[('type','=','Hobi'),('name','=','GROUP CUSTOMER/JOINT PROMO')]
                value['hobi']=browse_agm.id

                #GolDarah
                domain['gol_darah']=[('type','=','GolonganDarah'),('name','=','GROUP CUSTOMER/JOINT PROMO')]
                value['gol_darah']=browse_agm.id

                #Pendidikan            
                domain['pendidikan_id']=[('type','=','Pendidikan'),('name','=','GROUP CUSTOMER/JOINT PROMO')]
                value['pendidikan_id']=browse_pdd.id
                
                #Pekerjaan
                domain['pekerjaan_id']=[('type','=','Pekerjaan'),('name','=','GROUP CUSTOMER/JOINT PROMO')]
                value['pekerjaan_id']=browse_pkj.id
                
                #Pengeluaran
                domain['pengeluaran_id']=[('type','=','Pengeluaran'),('name','=','GROUP CUSTOMER/JOINT PROMO')]
                value['pengeluaran_id']=browse_png.id            
                
                #MerkMotor
                domain['merkmotor_id']=[('type','=','MerkMotor'),('name','=','GROUP CUSTOMER/JOINT PROMO')]
                value['merkmotor_id']=browse_mmt.id            
                
                #JenisMotor
                domain['jenismotor_id']=[('type','=','JenisMotor'),('name','=','GROUP CUSTOMER/JOINT PROMO')]
                value['jenismotor_id']=browse_jmt.id 
                
                #Penggunaan
                domain['penggunaan_id']=[('type','=','Penggunaan'),('name','=','GROUP CUSTOMER/JOINT PROMO')]
                value['penggunaan_id']=browse_penggunaan.id
                
                #Pengguna
                domain['pengguna_id']=[('type','=','Pengguna'),('name','=','GROUP CUSTOMER/JOINT PROMO')]
                value['pengguna_id']=browse_pengguna.id
                
            else :
                domain['status_rumah_id']=[('type','=','Status Rumah'),('name','!=','GROUP CUSTOMER')]
                value['status_rumah_id']=False
                domain['jenis_kelamin_id']=[('type','=','JenisKelamin'),('name','!=','GROUP CUSTOMER/JOINT PROMO')] 
                value['jenis_kelamin_id']=False  
                domain['agama_id']=[('type','=','Agama'),('name','!=','GROUP CUSTOMER/JOINT PROMO')]
                value['agama_id']=False
                domain['hobi']=[('type','=','Hobi'),('name','!=','GROUP CUSTOMER/JOINT PROMO')]
                value['hobi']=False
                domain['gol_darah']=[('type','=','GolonganDarah'),('name','!=','GROUP CUSTOMER/JOINT PROMO')]
                value['gol_darah']=False
                domain['pendidikan_id']=[('type','=','Pendidikan'),('name','!=','GROUP CUSTOMER/JOINT PROMO')]
                value['pendidikan_id']=False
                domain['pekerjaan_id']=[('type','=','Pekerjaan'),('name','!=','GROUP CUSTOMER/JOINT PROMO')]
                value['pekerjaan_id']=False
                domain['pengeluaran_id']=[('type','=','Pengeluaran'),('name','!=','GROUP CUSTOMER/JOINT PROMO')]
                value['pengeluaran_id']=False
                domain['merkmotor_id']=[('type','=','MerkMotor'),('name','!=','GROUP CUSTOMER/JOINT PROMO')]
                value['merkmotor_id']=False
                domain['jenismotor_id']=[('type','=','JenisMotor'),('name','!=','GROUP CUSTOMER/JOINT PROMO')]
                value['jenismotor_id']=False
                domain['penggunaan_id']=[('type','=','Penggunaan'),('name','!=','GROUP CUSTOMER/JOINT PROMO')]
                value['penggunaan_id']=False
                domain['pengguna_id']=[('type','=','Pengguna'),('name','!=','GROUP CUSTOMER/JOINT PROMO')]   
                value['pengguna_id']=False          
            return {'domain':domain,'value':value}
        
    def _onchange_kecamatan(self, cr, uid, ids, kecamatan_id):
        if kecamatan_id:
            kec = self.pool.get("wtc.kecamatan").browse(cr, uid, kecamatan_id)
            return {
                    'value' : {'kecamatan':kec.name}
                    }
        else:
            return {
                    'value' : {'kecamatan':False}}
        return True
    
    def _onchange_zip(self, cr, uid, ids, zip_id):
        if zip_id:
            kel = self.pool.get("wtc.kelurahan").browse(cr, uid, zip_id)
            return {'value' : {'kelurahan':kel.name,}}
        else:
            return {'value' : {'kelurahan':False,}}
        return True
        
    def get_customer(self, cr, uid, ids, name,default_code,no_ktp,birthday,street,street2,rt,rw,state,city,kecamatan_id,kecamatan,zip,kelurahan,phone,mobile):
        result = {}     
        if name :
           result.update({'name': name,'no_ktp':no_ktp,'birtdate':birthday,'street':street,'street2':street2,'rt':rt,'rw':rw,'state_id':state,'city_id':city,'kecamatan_id':kecamatan_id,'kecamatan':kecamatan,'zip_id':zip,'kelurahan':kelurahan,'no_hp':mobile,'no_telp':phone})
        return { 'value' : result}
           
    def onchange_jenis(self,cr,uid,ids,jenis,kode,context=None):
        domain = {}
        value = {}
        if jenis :
            search = self.pool.get('wtc.questionnaire').search(cr,uid,[
                                         ('id','=',jenis)
                                         ])
            browse = self.pool.get('wtc.questionnaire').browse(cr,uid,search)
            search_mmt = self.pool.get('wtc.questionnaire').search(cr,uid,[
                                       ('type','=','MerkMotor'),
                                       ('name','=','GROUP CUSTOMER/JOINT PROMO')
                                       ])
            browse_mmt = self.pool.get('wtc.questionnaire').browse(cr,uid,search_mmt)
            if search :
                value['merkmotor_id']=False
                if browse.name == 'Belum pernah memiliki' :
                    domain['merkmotor_id']=[('type','=','MerkMotor'),('value','=','6')]
                if browse.name != 'Belum pernah memiliki' :
                    if kode == 'G' or kode == 'J' :
                        value['merkmotor_id']=browse_mmt.id
                        domain['merkmotor_id']=[('type','=','MerkMotor'),('name','=','GROUP CUSTOMER/JOINT PROMO')]
                        
                    else :
                        domain['merkmotor_id']=[('type','=','MerkMotor'),('name','!=','GROUP CUSTOMER/JOINT PROMO'),('value','!=','6')]

        
        return {'domain':domain,'value':value}   

    def onchange_punctuation(self,cr,uid,ids,no_ktp,penanggung_jawab,context=None):    
        value = {}
        warning = {}
        if no_ktp :
            no_ktp = "".join(l for l in no_ktp if l not in string.punctuation)  
            value = {
                     'no_ktp':no_ktp
                     }  
        if penanggung_jawab :
            penanggung_jawab = "".join(l for l in penanggung_jawab if l not in string.punctuation)  
            value = {
                     'penanggung_jawab':penanggung_jawab
                     }                                  
        return {'value':value}    
            
class wtc_kartu_keluarga(osv.osv):
    _name = "wtc.kartu.keluarga"
    _columns = {
                'customer_id' : fields.many2one('res.partner','Customer'),
                'name' : fields.char('Nama'),
                'nik' : fields.char('Nik'),
                'tgl_lahir' : fields.date('Tgl Lahir'),
                'hub' : fields.selection([('1','Suami'),('2','Istri'),('3','Anak'),('4','Saudara'),('5','Ayah'),('6','Ibu')],string="Hubungan")
                }
    
           
           
           
           
           
           
           
