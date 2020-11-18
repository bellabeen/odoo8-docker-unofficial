import time
from datetime import datetime
import string 
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import api
from openerp.osv.expression import get_unaccent_wrapper


class res_partner(osv.osv):
    _inherit = 'res.partner'
    
    def _get_payment_term(self, cr, uid, context=None):
        obj_payment_term = self.pool.get('account.payment.term')
        id_payment_term = obj_payment_term.search(cr, uid, [('name','=','Immediate Payment')])
        if id_payment_term :
            return id_payment_term[0]
        return False

    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
    
    def _journal_item_count_view(self, cr, uid, ids, field_name, arg, context=None):
        MoveLine = self.pool('account.move.line')
        res = {}
        for partner_id in ids:
            res[partner_id]={
                             'journal_item_count_view':0
                             }
            res[partner_id]['journal_item_count_view']=MoveLine.search_count(cr, uid, [('partner_id', '=', partner_id)], context=context)
        return res
        
    _columns = {
                'parent_name': fields.related('parent_id', 'name', type='char', readonly=True, string='Parent name'),
                'default_code': fields.char('Partner Code'),
#                 'code_sequence_id': fields.many2one('ir.sequence.type', 'Sequence Code', required=True),
                'principle': fields.boolean('Principle'),
                'biro_jasa': fields.boolean('Biro Jasa'),
                'forwarder': fields.boolean('Forwarder'),
                'supplier': fields.boolean('General Supplier', help="Check this box if this contact is a supplier. If it's not checked, purchase people will not see it when encoding a purchase order."),
                'showroom': fields.boolean('Showroom'),
                'ahass': fields.boolean('Ahass'),
                'dealer': fields.boolean('Dealer'),
                'finance_company': fields.boolean('Finance Company'),

                'ahm_code': fields.char('AHM Code'),
                'dealer_code': fields.char('Dealer Code'),
                'kode_pajak_id':fields.selection([('1','[1]'),('2','[2]'),('3','[3]'),('4','[4]'),('5','[5]'),('6','[6]'),('7','[7]'),('8','[8]')],'Kode Pajak'),
                'pkp' : fields.boolean('PKP'),
                'alamat_pkp': fields.char('Alamat PKP'),
                'npwp': fields.char('No.NPWP'),
                'tgl_kukuh': fields.date('Tgl Kukuh'),
                
                #Alamat di Header
                'rt':fields.char('RT', size=3),
                'rw':fields.char('RW',size=3),
                'zip_id':fields.many2one('wtc.kelurahan', 'ZIP Code',domain="[('kecamatan_id','=',kecamatan_id),('state_id','=',state_id),('city_id','=',city_id)]"),
                'kelurahan':fields.char('Kelurahan',size=100), 
                'kecamatan_id':fields.many2one('wtc.kecamatan','Kecamatan', size=128,domain="[('state_id','=',state_id),('city_id','=',city_id)]"),
                'kecamatan':fields.char('Kecamatan', size=100),
                'city_id':fields.many2one('wtc.city','City',domain="[('state_id','=',state_id)]"),
                                
                #Alamat di Tab Customer Info
                'sama':fields.boolean(''), #diberi required True
                'street_tab': fields.char('Address'),
                'street2_tab': fields.char(),
                'rt_tab':fields.char('RT', size=3),
                'rw_tab':fields.char('RW',size=3),
                'zip_tab_id':fields.many2one('wtc.kelurahan', 'ZIP Code',domain="[('kecamatan_id','=',kecamatan_tab_id),('state_id','=',state_tab_id),('city_id','=',city_tab_id)]"),
                'kelurahan_tab':fields.char('Kelurahan',size=100), 
                'kecamatan_tab_id':fields.many2one('wtc.kecamatan','Kecamatan', size=128,domain="[('state_id','=',state_tab_id),('city_id','=',city_tab_id)]"),
                'kecamatan_tab':fields.char('Kecamatan', size=100),
                'city_tab_id':fields.many2one('wtc.city','City',domain="[('state_id','=',state_tab_id)]"),
                'state_tab_id':fields.many2one('res.country.state', 'Province'),
                
                #Field yang ada di Tab Customer Info
                'birthday':fields.date('Date of Birth'),
                'hp_status':fields.selection([('aktif','Aktif'),('TidakAktif','Tidak Aktif')],'HP Status'),
                'gender':fields.selection([('lakilaki', 'Laki-laki'),('perempuan', 'Perempuan')],'Jenis Kelamin'),
                'no_kk':fields.char('No. KK',50),
                'religion':fields.selection([('Islam', 'Islam'),('Kristen', 'Kristen'),('Katholik', 'Katholik'),('Hindu', 'Hindu'),('Budha', 'Budha')],'Religion'),
                'no_ktp':fields.char('No.KTP',50),
                'property_account_payable': fields.property(
                    type='many2one',
                    relation='account.account',
                    string="Account Payable",
                    domain="[('type', '=', 'receivable')]",
                    help="This account will be used instead of the default one as the payable account for the current partner",
                    required=True),
                'property_account_receivable': fields.property(
                    type='many2one',
                    relation='account.account',
                    string="Account Receivable",
                    domain="[('type', '=', 'payable')]",
                    help="This account will be used instead of the default one as the receivable account for the current partner",
                    required=True),                
                'pendidikan':fields.selection([('noSD', 'Tidak Tamat SD'),('sd', 'SD'),('sltp', 'SLTP/SMP'),('slta', 'SLTA/SMA'),('akademik', 'Akademi/Diploma'),('sarjana', 'Sarjana(S1)'),('pascasarjana', 'Pasca Sarjana')],'Pendidikan'),
                'pekerjaan':fields.selection([('pNegeri', 'Pegawai Negeri'),('pSwasta', 'Pegawai Swasta'),('ojek', 'Ojek'),('pedagang', 'Pedagang/Wiraswasta'),('pelajar', 'Pelajar/Mahasiswa'),('guru', 'Guru/Dosen'),('tni', 'TNI/Polri'),('irt', 'Ibu Rumah Tangga'),('petani/nelayan', 'Petani/Nelayan'),('pro', 'Profesional(Contoh : Dokter)'),('lain', 'Lainnya')],'Pekerjaan'),
                'pengeluaran':fields.selection([('<900', '< Rp.900.000,-'),('900125', 'Rp.900.001,- s/d Rp.1.250.000,-'),('125175', 'Rp.1.250.001,- s/d Rp.1.750.000,-'),('175250', 'Rp.1.750.001,- s/d Rp.2.500.000,-'),('250400', 'Rp.2.500.001,- s/d Rp.4.000.000,-'),('400600', 'Rp.4.000.001,- s/d Rp.6.000.000,-'),('600000', '> Rp.6.000.000,-')],'Pengeluaran /Bulan'),
                'rel_code': fields.related('default_code', string='Partner Code', type="char", readonly="True"),
                'branch_id':fields.many2one('wtc.branch',string='Branch'),
                'direct_customer': fields.boolean(string='Direct Customer'),
                'branch': fields.boolean(string='Branch (Boolean)'),
                
                #Forwarder
                'driver_lines': fields.one2many('wtc.driver.line','partner_id','Driver'),
                'plat_number_lines': fields.one2many('wtc.plat.number.line','partner_id','Plat Number'),
                'journal_item_count_view': fields.function(_journal_item_count_view, string="Journal Items", type="integer",multi=True),
}
    
    _defaults = {
        'tz': api.model(lambda self: self.env.context.get('tz', 'Asia/Jakarta')),
        'sama': True,
        'pkp': True,
        'default_code': 'STK/',
        'branch_id':_get_default_branch
        
    }
 
#     _sql_constraints = [
#     ('unique_res_partner_duplicate_code', 'unique(default_code)', 'Kode Customer Duplicate !'),
#     ]
        
    def unlink(self,cr,uid,ids,context=None):
        for item in self.browse(cr, uid, ids, context=context):
                raise osv.except_osv(('Perhatian !'), ("Tidak boleh menghapus partner"))
        return False
            
    def default_get(self, cr, uid, fields, context=None):
         context = context or {}
         res = super(res_partner, self).default_get(cr, uid, fields, context=context)
         if 'property_payment_term' in fields:
             res.update({'property_payment_term': self._get_payment_term(cr, uid)})
         return res
    
    def onchange_customer(self, cr, uid, ids, customer):
        if not customer:
            return {
                'value':{
                    'no_ktp':False,
                    'birthday':False,
                    'gender':False,
                    'religion':False,
                    'no_kk':False,
                    'pendidikan':False,
                    'pekerjaan':False,
                    'pengeluaran':False,
                    'sama':'',
                    }
                }
        return True

    def onchange_dealer(self, cr, uid, ids, dealer, finance_company, principle, ahm_code, dealer_code):
        def_ahm_code = False
        def_dealer_code = False
        
        if dealer:
            def_ahm_code = True
            def_dealer_code = True
        if finance_company:
            def_ahm_code = True
        if principle:
            def_ahm_code = True
        
        return {
                'value':{
                         'ahm_code':ahm_code if def_ahm_code else False,
                         'dealer_code': dealer_code if def_dealer_code else False,
                         }
                }
    
    def showroom_ahass_change(self, cr, uid, ids, showroom, ahass, dealer, context=None):
        value = {}
        value['dealer'] = False
        if showroom or ahass :
            value['dealer'] = True
        return {'value':value}
    
    def onchange_pkp(self, cr, uid, ids, pkp, context=None):
        if not pkp==False:
            return {
                'value':{
                       'npwp':'',
                       'tgl_kukuh':False,
                    }
            }
       
        return True
    
    def onchange_forwarder(self, cr, uid, ids, forwarder, context=None):
        if not forwarder :
            return {'value' : {'plat_number_lines':False, 'driver_lines':False}}
        return True
    
    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            name = record.name
            if record.parent_id and not record.is_company:
                name = "%s, %s" % (record.parent_name, name)
            if context.get('show_address_only'):
                name = self._display_address(cr, uid, record, without_company=True, context=context)
            if context.get('show_address'):
                name = name + "\n" + self._display_address(cr, uid, record, without_company=True, context=context)
            name = name.replace('\n\n','\n')
            name = name.replace('\n\n','\n')
            if context.get('show_email') and record.email:
                name = "%s <%s>" % (name, record.email)
            if record.default_code:
                name = "[%s] %s" % (record.default_code, name)
            res.append((record.id, name))
        return res

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if name and operator in ('=', 'ilike', '=ilike', 'like', '=like'):

            self.check_access_rights(cr, uid, 'read')
            where_query = self._where_calc(cr, uid, args, context=context)
            self._apply_ir_rules(cr, uid, where_query, 'read', context=context)
            from_clause, where_clause, where_clause_params = where_query.get_sql()
            where_str = where_clause and (" WHERE %s AND " % where_clause) or ' WHERE '

            # search on the name of the contacts and of its company
            search_name = name
            if operator in ('ilike', 'like'):
                search_name = '%%%s%%' % name
            if operator in ('=ilike', '=like'):
                operator = operator[1:]

            unaccent = get_unaccent_wrapper(cr)

            query = """SELECT id
                         FROM res_partner
                      {where} ({email} {operator} {percent}
                           OR {display_name} {operator} {percent}
                           OR {default_code} {operator} {percent})
                     ORDER BY {display_name}, {default_code}
                    """.format(where=where_str, operator=operator,
                               email=unaccent('email'),
                               display_name=unaccent('display_name'),
                               default_code=unaccent('default_code'),
                               percent=unaccent('%s'))

            where_clause_params += [search_name, search_name, search_name]

            if limit:
                query += ' limit %s'
                where_clause_params.append(limit)
            cr.execute(query, where_clause_params)
            ids = map(lambda x: x[0], cr.fetchall())

            if ids:
                return self.name_get(cr, uid, ids, context)
            else:
                return []
        return super(res_partner,self).name_search(cr, uid, name, args, operator=operator, context=context, limit=limit)
        
    def create(self, cr, uid, vals, context=None):
        if vals.get('default_code','STK/') == 'STK/' :
            vals['default_code'] = self.pool.get('ir.sequence').get_sequence(cr, uid, 'STK')
        return super(res_partner, self).create(cr, uid, vals, context=context)
    
    def onchange_letter(self,cr,uid,ids,sama,street=None,street2=None,rt=None,rw=None,state_id=None,city_id=None,kecamatan_id=None,kecamatan=None,zip_id=None,kelurahan=None,context=None):
        value ={}
        if not sama :
                value = {
                         'street_tab':False,
                         'street2_tab':False,
                         'rt_tab':False,
                         'rw_tab':False,
                         'state_tab_id':False,
                         'city_tab_id':False,
                         'kecamatan_tab_id':False,
                         'kecamatan_tab':False,
                         'zip_tab_id':False,
                         'kelurahan_tab':False,                         
                         }
        if sama :
                value = {
                         'street_tab':street,
                         'street2_tab':street2,
                         'rt_tab':rt,
                         'rw_tab':rw,
                         'state_tab_id':state_id,
                         'city_tab_id':city_id,
                         'kecamatan_tab_id':kecamatan_id,
                         'kecamatan_tab':kecamatan,
                         'zip_tab_id':zip_id,
                         'kelurahan_tab':kelurahan,                         
                         }            
        return {'value':value}

    def _onchange_kecamatan_tab(self, cr, uid, ids, kecamatan_id):
        if kecamatan_id:
            kec = self.pool.get("wtc.kecamatan").browse(cr, uid, kecamatan_id)
            return {
                    'value' : {'kecamatan_tab':kec.name}
                    }
        else:
            return {
                    'value' : {'kecamatan_tab':False}}
        return True
    
    def _onchange_zip_tab(self, cr, uid, ids, zip_id):
        if zip_id:
            kel = self.pool.get("wtc.kelurahan").browse(cr, uid, zip_id)
            return {'value' : {'kelurahan_tab':kel.name,}}
        else:
            return {'value' : {'kelurahan_tab':False,}}
        return True
        
    def onchange_address(self,cr,uid,ids,street=None,street2=None,rt=None,rw=None,state_id=None,city_id=None,kecamatan_id=None,kecamatan=None,zip_id=None,kelurahan=None,context=None):
        value ={}
        warning = {}
        if street :
            value['street_tab'] = street
        if street2 :
            value['street2_tab'] = street2
        if rt :
            if len(rt) > 3 :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('RT tidak boleh lebih dari 3 digit ! ')),
                }
                value = {
                         'rt':False
                         }
            cek = rt.isdigit()
            if not cek :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('RT hanya boleh angka ! ')),
                }
                value = {
                         'rt':False
                         }  
            else :
                value['rt_tab'] = rt
        if rw :
            if len(rw) > 3 :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('RW tidak boleh lebih dari 3 digit ! ')),
                }
                value = {
                         'rw':False
                         }
            cek = rw.isdigit()
            if not cek :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('RW hanya boleh angka ! ')),
                }
                value = {
                         'rw':False
                         }   
            else :            
                value['rw_tab'] = rw   
        if state_id :
            value['state_tab_id'] = state_id
        if city_id :
            value['city_tab_id'] = city_id              
        if kecamatan_id :
            kec = self.pool.get("wtc.kecamatan").browse(cr, uid, kecamatan_id)         
            value['kecamatan_tab_id'] = kecamatan_id
            value['kecamatan_tab'] = kec.name
            if kecamatan_id and not kecamatan : 
                value['kecamatan'] = kec.name
        if zip_id :
            kel = self.pool.get("wtc.kelurahan").browse(cr, uid, zip_id)
            value['zip_tab_id'] = zip_id
            value['kelurahan_tab'] = kel.name   
            value['kelurahan'] = kel.name                
        return {'value':value,'warning':warning}     
             
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
    
    def onchange_punctuation(self,cr,uid,ids,no_ktp,context=None):    
        value = {}
        warning = {}
        if no_ktp :
            ktp = self.search(cr,uid,[('no_ktp','=',no_ktp)])
            if ktp :
                    warning = {
                        'title': ('Perhatian !'),
                        'message': (('No KTP %s sudah pernah dibuat ! ')%(no_ktp)),
                    }    
                    value = {
                             'no_ktp':False
                             }
            if not warning :            
                no_ktp = "".join(l for l in no_ktp if l not in string.punctuation)  
                value = {
                         'no_ktp':no_ktp
                         }                                 
        return {'value':value,'warning':warning}
    
class wtc_driver_line(osv.osv):
    _name = "wtc.driver.line"
    _rec_name = 'driver'
    _columns = {
        'partner_id': fields.many2one('res.partner', 'Forwarder'),
        'driver': fields.char('Driver'),
        }
    
    def driver_change(self, cr, uid, ids, driver, context=None):
        value = {}
        if driver :
            driver = driver.upper()
            value['driver'] = driver
        return {'value':value}

    def create(self, cr, uid, vals, context=None):
        if vals.get('driver',False):
            vals['driver'] = str(vals['driver']).strip().upper()
        return super(wtc_driver_line, self).create(cr, uid, vals, context=context)
    
class wtc_plat_number_line(osv.osv):
    _name = "wtc.plat.number.line"
    _rec_name = 'plat_number'
    _columns = {
        'partner_id': fields.many2one('res.partner', 'Forwarder'),
        'plat_number': fields.char('Plat Number'),
        }
    
    def plat_number_change(self, cr, uid, ids, plat_number, context=None):
        value = {}
        warning = {}
        if plat_number :
            plat_number = plat_number.upper()
            plat_number = plat_number.replace(' ','')
            value['plat_number'] = plat_number
            
            for x in plat_number :
                if x in string.punctuation :
                    warning = {'title': 'Perhatian', 'message': 'Plat Number hanya boleh huruf dan angka !'}
                    value['plat_number'] = False
        return {'value':value, 'warning':warning}

    def create(self, cr, uid, vals, context=None):
        if vals.get('plat_number',False):
            vals['plat_number'] = str(vals['plat_number']).replace(" ","").upper()
            if not str(vals['plat_number']).isalnum():
                raise osv.except_osv(('Warning!'), ("Nomor polisi hanya boleh huruf dan angka"))
            if len(vals['plat_number']) > 11:
                raise osv.except_osv(('Warning!'), ("Nomor polisi ekspedisi lebih dari 11 karakter"))
        return super(wtc_plat_number_line, self).create(cr, uid, vals, context=context)
    