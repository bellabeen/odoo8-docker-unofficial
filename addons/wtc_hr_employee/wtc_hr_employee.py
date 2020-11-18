import time
from datetime import datetime,timedelta
from dateutil.relativedelta import relativedelta
from openerp.tools.translate import _
from openerp.osv import osv, fields
from openerp import SUPERUSER_ID
from openerp.osv.orm import setup_modifiers
from lxml import etree
from openerp.exceptions import Warning

class wtc_employee (osv.osv):
    _inherit = 'hr.employee'
    
    def _onchange_province(self, cr, uid, ids, state_id):
        if state_id:
            return {'domain' : {'city_id':[('state_id','=',state_id)]},
                    'value' : {'city_id':False}}
        else:
            return {'domain' : {'city_id':[('state_id','=',False)]},
                    'value' : {'city_id':False}}
        return True
    
    def _onchange_city(self, cr, uid, ids, city_id):
        if city_id:
            return {'domain' : {'kecamatan_id':[('city_id','=',city_id)]},
                    'value' : {'kecamatan_id':False}}
        else:
            return {'domain' : {'kecamatan_id':[('city_id','=',False)]},
                    'value' : {'kecamatan_id':False}}
        return True
            
    def _onchange_kecamatan(self, cr, uid, ids, kecamatan_id):
        if kecamatan_id:
            kec = self.pool.get("wtc.kecamatan").browse(cr, uid, kecamatan_id)
            return {'domain' : {'zip_id':[('kecamatan_id','=',kecamatan_id)]},
                    'value' : {'kecamatan':kec.name,'zip_id':False}
                    }
        else:
            return {'domain' : {'zip_id':[('kecamatan_id','=',False)]},
                    'value' : {'kecamatan':False,'zip_id':False}}
        return True
    
    def _onchange_zip(self, cr, uid, ids, zip_id):
        if zip_id:
            kel = self.pool.get("wtc.kelurahan").browse(cr, uid, zip_id)
            return {'value' : {'kelurahan':kel.name,}}
        else:
            return {'value' : {'kelurahan':False,}}
        return True

    def _onchange_branch(self, cr, uid, ids, branch_id):
        if branch_id :
            branch_id = self.pool['wtc.branch'].browse(cr,uid,branch_id)
            return {'value' : {'area_id':branch_id.area_id.id}}
        return True
    
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids    
    
    _columns = { 
                 'branch_id':fields.many2one('wtc.branch',string = 'Branch'),
                 'division':fields.selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum'),('Finance','Finance')],'Division', change_default=True,select=True),
                 'npwp' : fields.char('No NPWP'),            
                 'shift':fields.selection([('WIB','WIB'),('WIT','WIT'),('WITA','WITA')],'Shift', change_default=True,select=True),
                 'area_id':fields.many2one('wtc.area',string = 'Area'),
                 'sales_ahm':fields.char('Sales Ahm'),
                 'no_kontrak':fields.char('No Kontrak'),
                 'tgl_masuk':fields.date('Tgl Masuk'),
                 'tgl_keluar':fields.date('Tgl Keluar'),
                 'nip':fields.char('NIP'),
                 'street':fields.char('Address'),
                 'street2': fields.char(),
                 'rt':fields.char('rt',size = 3),
                 'rw':fields.char('rw',size = 3),
                 'kelurahan':fields.char('Kelurahan',size = 100),
                 'kecamatan_id':fields.many2one('wtc.kecamatan','Kecamatan'),
                 'kecamatan':fields.char('Kecamatan', size=100),
                 'city_id':fields.many2one('wtc.city','City'),
                 'state_id':fields.many2one('res.country.state','Province'),
                 'zip_id':fields.many2one('wtc.kelurahan','ZIP Code'),
                 'phone':fields.char('No Telp'),
                 'mobile':fields.char('No.Handphone'),
                 'fax':fields.char('Fax'),
                 'email':fields.char('Email'),
                 'pmt_ke':fields.selection([('0','0'),('1','1'),('2','2'),('3','3')],'PMT ke', change_default=True,select=True),
                 'job_id': fields.many2one('hr.job', 'Job Title',domain="['|',('department_id','=',department_id),('department_id','=',False)]"),
                 'branch_control' : fields.related('job_id','branch_control',type='boolean',string='Branch Control'),
                 'login':fields.char('User Name'),
                 'user': fields.boolean('User'),
                 'bank':fields.selection([('bca','BCA'),('bri','BRI'),('mandiri','Mandiri')],'Bank'),
                 'no_rekening':fields.char('No Rekening'),
                 # 'user_nip':fields.char('User Nip')
                }
                
    _defaults={
                'tgl_masuk':time.strftime('%Y-%m-%d'),
                'branch_id': _get_default_branch,
               }
    
    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            tit = "[%s] %s" % (record.nip, record.name)
            res.append((record.id, tit))
        return res    
    
    def name_search(self, cr, user, name='', args=None, operator='ilike',
                             context=None, limit=100):
        if not args:
            args = []

        ids = []
        if len(name) < 11:
            ids = self.search(cr, user, [('nip', 'ilike', name)] + args,
                              limit=limit, context=context)

        search_domain = [('name', operator, name)]
        if ids: search_domain.append(('id', 'not in', ids))
        ids.extend(self.search(cr, user, search_domain + args,
                               limit=limit, context=context))

        locations = self.name_get(cr, user, ids, context)
        return sorted(locations, key=lambda (id, name): ids.index(id))
        
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(wtc_employee, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        if context.get('branch_control') :          
            doc = etree.XML(res['arch'])
            nodes_branch = doc.xpath("//field[@name='job_id']")
            for node in nodes_branch:
                node.set('domain', '[("branch_control", "!=", False)]')
            res['arch'] = etree.tostring(doc)

        user_hr_department = self.pool['res.users'].has_group(cr, uid, 'wtc_hr_employee.groups_hr_department')
        if not user_hr_department :
            doc = etree.XML(res['arch'])
            nodes = doc.xpath("//field[@name='area_id']")
            for node in nodes:
                node.set('readonly', '1')
                node.set('domain', "[('branch_ids.id','=',branch_id)]")
                setup_modifiers(node, res['fields']['area_id'])
            res['arch'] = etree.tostring(doc)

        return res

    def get_user_password(self,cr,uid,vals,context=None):
        user_pool = self.pool.get('res.users')
        name = vals['name'].replace(' ', '').upper()
        name = name[:10]

        user_ids = user_pool.search(cr, uid, [('login', '=', name), '|', ('active', '=', False), ('active', '=', True)])
        i = 0
        while len(user_ids) > 0:
            i = i + 1
            name = name[:7] + str(i).zfill(3)
            user_ids = user_pool.search(cr, uid,[('login', '=', name), '|', ('active', '=', False), ('active', '=', True)])
        password = name.title() + vals['nip']
        return name,password

    def get_employee_vals(self,cr,uid,vals,context=None):
        if not vals.get('nip') :
            vals['nip'] = self.pool.get('ir.sequence').get_nik_per_branch(cr, uid, vals['branch_id'])
        if not vals.get('work_email') :
            vals['work_email'] = vals['nip']
        if vals.get('branch_id'):
            user_hr_department = self.pool['res.users'].has_group(cr, uid, 'wtc_hr_employee.groups_hr_department')
            if not user_hr_department :
                area_id = self.pool.get('wtc.branch').get_default_area_branch(cr, uid, vals['branch_id'])
                vals['area_id'] = area_id
        if vals.get('nip',False):
            self.check_nip(cr,uid,vals['nip'],context)
        return vals

    def check_employee_constraints(self,cr,uid,vals,context=None):
        bank = vals.get('bank')
        if bank == 'bca':
            if len(vals.get('no_rekening', '')) != 10:
                raise osv.except_osv(('Perhatian !'), ("Digit rekening harus 10"))
        elif bank == 'bri':
            if len(vals.get('no_rekening', '')) != 15:
                raise osv.except_osv(('Perhatian !'), ("Digit rekening harus 15"))

        group_id = False
        if vals.get('job_id') :
            job_id = self.pool.get('hr.job').browse(cr, uid, vals['job_id'])
            group_id = job_id.group_id.id
            if not group_id:
                raise osv.except_osv(('Perhatian !'), ("User Group belum diisi di Master 'Job' !"))


            ######## Cek Tanggal Keluar ########
#         if vals['tgl_keluar'] :
#             vals['active'] = False
#             user_pool.write(cr,uid,user,{'active':False})
        return group_id

    def check_nip(self,cr,uid,nip,context=None):
        cek_nip = self.search(cr,uid,[('nip','=',nip)],limit=1,context=context)
        if cek_nip:
            obj_emp = self.browse(cr, uid, cek_nip[0])
            raise Warning('NIP %s sudah terdaftar atas nama %s !'%(nip,obj_emp.name))


    def get_timezone(self, cr, uid, vals,context=None):
        tz = 'Asia/Jakarta'
        if vals['shift'] == 'WITA':
            tz = 'Asia/Pontianak'
        elif vals['shift'] == 'WIT' :
            tz = 'Asia/Jayapura'
        return tz

    def create_user(self, cr,uid,vals,group_id,context=None):
        name,password = self.get_user_password(cr,uid,vals,context=context)
        tz = self.get_timezone(cr,uid,vals,context=context)
        user_pool = self.pool.get('res.users')
        if vals.get('user') == True:
            user_vals = {'name': vals['name'],
                         'login': name,
                         'password': password,
                         'groups_id': [(6, 0, [group_id])],
                         'tz': tz,
                         'email': vals['work_email'],
                         }
            if vals.get('area_id'):
                user_vals['area_id'] = vals['area_id']
            user = user_pool.create(cr, SUPERUSER_ID, user_vals)

            vals['user_id'] = user
            vals['login'] = name
        return vals

    def create(self,cr,uid,vals,context=None):
        group_id = self.check_employee_constraints(cr,uid,vals,context=context)
            # Pilih Bank Mandiri hanya bisa untuk non Magang
        jobs = self.pool.get('hr.job').search(cr,uid,[('name','in',('SALESMAN PARTNER','SALESMAN MAGANG'))],context=context)
        if jobs:
            if vals.get('bank','') == 'mandiri' and vals.get('job_id',False) in jobs:
                raise Warning('Tidak dapat memilih Bank Mandiri pada salesman partner/magang.')
        vals = self.get_employee_vals(cr,uid,vals,context=context)
        vals = self.create_user(cr,uid,vals,group_id,context=context)
        employee =  super(wtc_employee, self).create(cr, uid, vals, context=context) 
        return employee

    def write(self,cr,uid,ids,vals,context=None):
        user_pool = self.pool.get('res.users')  
        job_pool = self.pool.get('hr.job')
        users = self.browse(cr,uid,ids)

        jobs = self.pool.get('hr.job').search(cr,uid,[('name','in',('SALESMAN PARTNER','SALESMAN MAGANG'))],context=context)
        for user in users :
            user_vals = {}
            # Pilih Bank Mandiri hanya bisa untuk non Magang
            if jobs:
                if vals.get('bank',user.bank) == 'mandiri' and vals.get('job_id',user.job_id.id) in jobs:
                    raise Warning('Tidak dapat memilih Bank Mandiri pada salesman partner/magang.')

            group = job_pool.browse(cr,uid,user['job_id'].id)
            group_id =[(6,0,[group.group_id.id])]

            name = user['name'].replace(' ', '').upper()
            name = name[:10]

            bank = vals.get('bank', user.bank)
            if bank == 'bca':
                if len(vals.get('no_rekening',user.no_rekening)) != 10:
                    raise osv.except_osv(('Perhatian !'), ("Digit rekening harus 10"))

            elif bank == 'bri':
                if len(vals.get('no_rekening',user.no_rekening)) != 15:
                    raise osv.except_osv(('Perhatian !'), ("Digit rekening harus 15"))
            
            user_ids = user_pool.search(cr, uid, [('login','=',name),'|',('active','=',False),('active','=',True)])
            i = 0
            while len(user_ids) > 0 :
                i = i + 1
                name = name[:7] + str(i).zfill(3)
                user_ids = user_pool.search(cr, uid, [('login','=',name),'|',('active','=',False),('active','=',True)])

            shift = 'Asia/Jakarta'
            if user['shift'] == 'WITA':
                shift = 'Asia/Pontianak'
            elif user['shift'] == 'WIT' :
                shift = 'Asia/Jayapura'

            if vals.get('nip'):
                self.check_nip(cr,uid,vals['nip'],context)

            if vals.get('tgl_keluar'):
                date_tgl_keluar = datetime.strptime(vals['tgl_keluar'],'%Y-%m-%d').date()
                tgl_skr = (datetime.now()+relativedelta(hours=7)).date()
                if date_tgl_keluar < tgl_skr:
                    user_vals['active']=False
                else:
                    user_vals['active']=True
            else:
                user_vals['active']=True
            
            if vals.get('shift') :
                if vals.get('shift') == 'WIB' :
                    user_vals['tz'] = 'Asia/Jakarta'
                elif vals.get('shift') == 'WITA' :
                    user_vals['tz'] = 'Asia/Pontianak'
                elif vals.get('shift') == 'WIT' :
                    user_vals['tz'] = 'Asia/Jayapura'
            if vals.get('job_id') :
                job_id = job_pool.browse(cr,uid,vals['job_id'])
                user_vals['groups_id'] =[(6,0,[job_id.group_id.id])]
            if vals.get('area_id') :
                user_vals['area_id'] = vals['area_id']
    #         if vals.get('nip') :
    #             user_vals['login'] = vals['nip']
            if vals.get('work_email') :
                user_vals['email'] = vals['work_email']
            if vals.get('name') :
                user_vals['name'] = vals['name']

            area_id = user.area_id.id
            if vals.get('branch_id'):
                user_hr_department = self.pool['res.users'].has_group(cr, uid, 'wtc_hr_employee.groups_hr_department')
                if not user_hr_department:
                    area_id = self.pool.get('wtc.branch').get_default_area_branch(cr, uid, vals['branch_id'])
                    vals['area_id'] = area_id
                
            if user_vals and user.user_id :
                user_pool.write(cr,SUPERUSER_ID,user.user_id.id,user_vals)

            if not vals.get('tgl_keluar') and vals.get('user') == True and user.user_id.id == False :
                user_vals = {'name':user['name'],
                             'login': name,
                             'groups_id':[(6,0,[group.group_id.id])],
                             'tz':shift,
                             'email':user['work_email']}
                password = False
                if vals.get('nip',False):
                    password = user.name + vals['nip']

                if vals.get('user',False):
                    password = user.name + user.nip

                if password:
                    user_vals['password'] = password
                
                if area_id :
                    user_vals['area_id'] = area_id
                user_id = user_pool.create(cr,SUPERUSER_ID, user_vals)
              
                vals['user_id'] = user_id
                vals['login'] = name

            if vals.get('user')==False :
                user_pool.write(cr,SUPERUSER_ID,user.user_id.id,{'active': False})

        res = super(wtc_employee, self).write(cr, uid, ids, vals, context=context)
        return res
            
    def get_user_resign(self,cr,uid,context):
        query = """ 
            select ru.id,hre.tgl_keluar from hr_employee hre 
            left join resource_resource rr on rr.id=hre.resource_id
            left join res_users ru on ru.id=rr.user_id
            where hre.tgl_keluar is not null and ru.active ='t'
        """
        cr.execute (query)
        ress = cr.dictfetchall()

        ids = []
        for res in ress:
            res_id = res['id']
            tgl_keluar = datetime.strptime(res['tgl_keluar'],'%Y-%m-%d').date()
            tgl_skr = datetime.strptime(datetime.now().strftime('%Y-%m-%d'),'%Y-%m-%d').date()
            if tgl_keluar < tgl_skr:
                ids.append(res_id)
        if ids:
            ids = str(ids).replace("[","(")
            ids = str(ids).replace("]",")")
            query_usr = """ update res_users set active='f' where id in %s """ %(ids)
            cr.execute (query_usr)

    def unlink(self,cr,uid,ids,context=None):
        for item in self.browse(cr, uid, ids, context=context):
            raise osv.except_osv(('Perhatian !'), ("Tidak boleh menghapus Karyawan"))
        return False

    def onchange_department(self, cr, uid, ids, job_id, context=None):
        if job_id:
            department = self.pool.get('hr.job').browse(cr, uid, job_id).department_id.id
            return {'value': {'department_id': department}}
        return True

class wtc_resource_resource(osv.osv):
    _inherit = 'resource.resource'
    
    _sql_constraints = [
    ('unique_user_id', 'unique(user_id)', 'User tidak boleh sama  !'),
    ]   
