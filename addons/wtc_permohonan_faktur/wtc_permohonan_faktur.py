import time
import base64
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
import pytz 

class Eksport_cddb(osv.osv_memory):
    _name = "eksport.cddb"
    _columns = {
                'type': fields.selection((('cddb','CDDB'), ('udstk','UDSTK')), 'File'),
                'name': fields.char('File Name', 35),
                'data_file': fields.binary('File'),
                }   
    _defaults = {'type' :'cddb'}
    
    def export_file(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids)[0]
        trx_id = context.get('active_id',False) 
        trx_obj = self.pool.get('wtc.permohonan.faktur').browse(cr,uid,trx_id,context=context)
 
        if val.type == 'cddb' :
            result = self.eksport_cddb(cr, uid, ids, trx_obj,context)
        elif val.type == 'udstk' :
            result = self.eksport_udstk(cr, uid, ids, trx_obj,context)
        
        
        form_id  = 'view.wizard.eksport.cddb'
 
        view_id = self.pool.get('ir.ui.view').search(cr,uid,[                                     
                                                             ("name", "=", form_id), 
                                                             ("model", "=", 'eksport.cddb'),
                                                             ])
     
        return {
            'name' : _('Export File'),
            'view_type': 'form',
            'view_id' : view_id,
            'view_mode': 'form',
            'res_id': ids[0],
            'res_model': 'eksport.cddb',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True,
            'context': context
        }
        
    def _get_default_date(self,cr,uid,context=None):
        return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=None) 
            
    def eksport_cddb(self, cr, uid, ids,trx_obj, context=None):
        result = ''
        for x in trx_obj.serial_number_ids :
            if not x.cddb_id :
                raise osv.except_osv(('Perhatian !'), ("Customer CDDB belum diisi dalam nomor mesin %s")%(x.name))                
            date = x.cddb_id.birtdate
            if not date :
                raise osv.except_osv(('Perhatian !'), ("Tanggal lahir belum diisi untuk CDDB %s")%(x.cddb_id.customer_id.name))
            if x.dealer_sale_order_id :                
                sales_ahm = self.flp_id(cr, uid, ids, x.dealer_sale_order_id, context)
            elif not x.dealer_sale_order_id :
                sales_ahm = 'TA'
            bulan = str(date[5:7])
            tanggal = str(date[8:10])
            tahun = str(date[:4])
            new_date = tanggal+bulan+tahun
            no_telp = x.cddb_id.no_telp
            kecamatan = x.cddb_id.kecamatan
            if not x.cddb_id.kecamatan :
                kecamatan = x.cddb_id.kecamatan_id.name
            if not x.cddb_id.no_telp :
                no_telp = 01234
            
            alamat = str(x.cddb_id.street) + ' RT/RW.' + str(x.cddb_id.rt) + '/' + str(x.cddb_id.rw)
            result += x.name[:5] +';'+ x.name[5:12] +';'+ x.cddb_id.no_ktp +';'+ x.cddb_id.kode_customer +';'+ str(x.cddb_id.jenis_kelamin_id.value) +';'+ new_date+';'+ alamat+';'+ x.cddb_id.kelurahan+';'+ str(kecamatan)+';'+ str(x.cddb_id.city_id.code)+';'+ str(x.cddb_id.zip_id.zip)+';'+ str(x.cddb_id.state_id.code)+';'+ str(x.cddb_id.agama_id.value)+';'+ str(x.cddb_id.pekerjaan_id.value) +';'+ str(x.cddb_id.pengeluaran_id.value)+';'+ str(x.cddb_id.pendidikan_id.value)+';'+ str(x.cddb_id.penanggung_jawab)+';'+ str(x.cddb_id.no_hp)+';'+ str(no_telp)+';'+ str(x.cddb_id.dpt_dihubungi)+';'+ str(x.cddb_id.merkmotor_id.value)+';'+ str(x.cddb_id.jenismotor_id.value)+';'+ str(x.cddb_id.penggunaan_id.value)+';'+ str(x.cddb_id.pengguna_id.value)+';'+sales_ahm+';'
            result += '\n'  
        kodeMD = trx_obj.branch_id.default_supplier_id.ahm_code
        kodeDealer = trx_obj.branch_id.ahm_code
        tanggal = self._get_default_date(cr,uid,context=context).strftime('%y%m%d')
        if not kodeMD :
            raise osv.except_osv(('Perhatian !'), ("AHM kode Principle belum diisi di Data Customer."))
        if not kodeDealer :
            raise osv.except_osv(('Perhatian !'), ("AHM kode belum diisi di Master Branch."))
        start_date = self._get_default_date(cr,uid,context=context).strftime("%y%m%d%H%M")
        kode = str(kodeMD[:3]) +'-'+ str(kodeDealer[:5]) + '-'+str(tanggal) +'-'+ str(start_date)
        nama = kode + '.CDDB'
        out = base64.encodestring(result)
        cddb = self.write(cr, uid, ids, {'data_file':out, 'name': nama}, context=context)
        
        return cddb
    
    def flp_id (self,cr,uid,ids,so,context=None):
        employeee_pool = self.pool.get('hr.employee')
        employee_search = employeee_pool.search(cr,uid,[
                                                        ('user_id','=',so.user_id.id)
                                                        ])
        sales_ahm = False
        
        if employee_search :
            for x in employeee_pool.browse(cr,uid,employee_search) :
                sales_ahm = x.sales_ahm
                if sales_ahm :
                    break
        section_id = so.section_id
        while not sales_ahm :
            user_id = section_id.user_id and section_id.user_id.id or False
            if user_id :
                search = employeee_pool.search(cr,uid,[
                                                         ('user_id','=',user_id)
                                                         ]) 
                
                if search :
                    for x in employeee_pool.browse(cr,uid,employee_search) :
                        sales_ahm = x.sales_ahm
                        if sales_ahm :
                            break
            section_id = section_id.parent_id
            if not section_id and not sales_ahm:
                sales_ahm = 'TA'
                         
        return sales_ahm

    
    def eksport_udstk(self, cr, uid, ids,trx_obj, context=None):
        result = ''
        for x in trx_obj.serial_number_ids :
            alamat = str(x.customer_stnk.street_tab) + ' RT/RW.' + str(x.customer_stnk.rt_tab) + '/' + str(x.customer_stnk.rw_tab)
            kecamatan = x.cddb_id.kecamatan
            if not x.cddb_id.kecamatan :
                kecamatan = x.cddb_id.kecamatan_id.name
                
            result += x.chassis_no +';'+ x.name[:5] +';'+ x.name[5:12] +';'+ x.customer_stnk.name +';'+ alamat+';'+ x.cddb_id.kelurahan+';'+ str(kecamatan)+';'+ str(x.cddb_id.city_id.code)+';'+ str(x.cddb_id.zip_id.zip)+';'+ str(x.cddb_id.state_id.code)+';'+str(x.jenis_penjualan)+';'+str(trx_obj.branch_id.ahm_code)+';'
            result += '\n'  
        kodeMD = trx_obj.branch_id.default_supplier_id.ahm_code
        kodeDealer = trx_obj.branch_id.ahm_code
        tanggal = self._get_default_date(cr,uid,context=context).strftime('%y%m%d')
        if not kodeMD :
            raise osv.except_osv(('Perhatian !'), ("AHM kode Principle belum diisi di Data Customer."))
        if not kodeDealer :
            raise osv.except_osv(('Perhatian !'), ("AHM kode belum diisi di Master Branch."))   
        start_date = self._get_default_date(cr,uid,context=context).strftime("%y%m%d%H%M")
        kode = str(kodeMD[:3]) +'-'+ str(kodeDealer[:5]) + '-'+str(tanggal) +'-'+ str(start_date)
        nama = kode + '.UDSTK'
        out = base64.encodestring(result)
        udstk = self.write(cr, uid, ids, {'data_file':out, 'name': nama}, context=context)
        
        return udstk
    
class wtc_permohonan_faktur(osv.osv):
    _name = 'wtc.permohonan.faktur'
    _inherit = ['mail.thread']
    _description = "Permohonan Faktur"
    _order = "tgl_mohon_faktur desc"
    
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids    
    
    def _get_default_date(self,cr,uid,context=None):
        return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=None) 
        
    _columns = {
        'branch_id': fields.many2one('wtc.branch', string='Branch', required=True),
        'division':fields.selection([('Unit','Unit')], 'Division', change_default=True, select=True),
        'name': fields.char('No Reference',size=20, readonly=True),
        'tgl_mohon_faktur': fields.date('Tanggal'),
        'state': fields.selection([('draft', 'Draft'),('waiting_for_approval','Waiting For Approval'), ('approved','Posted'),('confirmed', 'Waiting Approval'),('cancel','Canceled')], 'State', readonly=True),
        'serial_number_ids': fields.one2many('stock.production.lot','permohonan_faktur_id',string="Table Permohonan Faktur"), 
        'partner_id':fields.related('branch_id','default_supplier_id',type='many2one',relation='res.partner',readonly=True,string='Supplier'),
        'ahm_code':fields.related('branch_id','ahm_code',type='char',readonly=True,string='AHM Code'),
        'engine_no': fields.related('serial_number_ids', 'name', type='char', string='No Engine'),
        'customer_stnk': fields.related('serial_number_ids', 'customer_stnk', type='many2one', relation='res.partner', string='Customer STNK'),  
        'exception_faktur' : fields.boolean('Exception Faktur'),
        'confirm_uid':fields.many2one('res.users',string="Posted by"),
        'confirm_date':fields.datetime('Posted on'),
        'cancel_uid':fields.many2one('res.users',string="Cancelled by"),
        'cancel_date':fields.datetime('Cancelled on'),          
    }
    _defaults = {
      'branch_id': _get_default_branch,
      'tgl_mohon_faktur': _get_default_date,
      'state':'draft',
      'division' : 'Unit',
      
     }    
            
    def cancel_permohonan(self,cr,uid,ids,context=None):
        val = self.browse(cr,uid,ids)  
        lot_pool = self.pool.get('stock.production.lot') 
        for x in val.serial_number_ids :
            lot_search = lot_pool.search(cr,uid,[
                        ('branch_id','=',val.branch_id.id),
                        ('permohonan_faktur_id','=',val.id),
                        ('name','=',x.name)
                        ])
            if not lot_search :
                raise osv.except_osv(('Perhatian !'), ("No Engine Tidak Ditemukan."))
            if lot_search :
                lot_browse = lot_pool.browse(cr,uid,lot_search)
                if lot_browse.penerimaan_faktur_id or lot_browse.penerimaan_notice_id or lot_browse.proses_stnk_id or lot_browse.penerimaan_stnk_id or lot_browse.penerimaan_bpkb_id or lot_browse.proses_biro_jasa_id :
                    raise osv.except_osv(('Perhatian !'), ("No faktur engine \'%s\' telah diproses, data tidak bisa di cancel !")%(lot_browse.name))                    
                else : 
                    lot_browse.write({'state_stnk': False,'tgl_faktur':False,'permohonan_faktur_id':False})
        self.write(cr, uid, ids, {'state': 'cancel','cancel_uid':uid,'cancel_date':datetime.now()})
        self.message_post(cr, uid, val.id, body=_("Permohononan Faktur canceled "), context=context) 

        return True
    
    def post_permohonan(self,cr,uid,ids,context=None):                                
        val = self.browse(cr,uid,ids)  
        lot_pool = self.pool.get('stock.production.lot') 
        engine = ''
        tanggal = self._get_default_date(cr, uid, context=context)
        self.write(cr, uid, ids, {'state': 'approved','tgl_mohon_faktur':tanggal,'confirm_uid':uid,'confirm_date':datetime.now()})         
        for x in val.serial_number_ids :
            lot_search = lot_pool.search(cr,uid,[
                        ('branch_id','=',val.branch_id.id),
                        ('tgl_faktur','=',False),
                        ('state','in',('paid','sold','sold_offtr','paid_offtr')),
                        ('name','=',x.name)
                        
                        ])
            if lot_search :
                lot_browse = lot_pool.browse(cr,uid,lot_search)
                if lot_browse.dealer_sale_order_id :
                    if lot_browse.dealer_sale_order_id.state == 'cancelled' :
                        raise osv.except_osv(('Perhatian !'), ("Sales Order atas engine %s sudah terbatalkan.")%(lot_browse.name))
                lot_browse.write({
                       'state_stnk':'mohon_faktur',
                       'tgl_faktur': val.tgl_mohon_faktur,
                       })
            engine += ('- '+str(x.name)+'<br/>')
        self.message_post(cr, uid, val.id, body=_("Permohononan Faktur posted <br/> No Engine : <br/>  %s ")%(engine), context=context)                 
        return True
    
    def onchange_exception(self,cr,uid,ids,exception_faktur,serial_number_ids,branch_id,context=None):
        value = {}
        if not exception_faktur  :
            value = {
                     'serial_number_ids' : False,
#                      'branch_id' : False,
                     'partner_id' : False,
                     'ahm_code' : False
                     }
        if exception_faktur and serial_number_ids:
            value = {
                     'serial_number_ids' : False,
                     'branch_id' : False,
                     'ahm_code' : False,
                     'partner_id' : False,
                     }
        return {'value':value}
    
    def onchange_branch_permohonan_faktur(self, cr, uid, ids, branch_id,exception,context=None):
        line = self.pool.get('stock.production.lot')
        
        if ids :
            obj = self.browse(cr,uid,ids)
            for x in obj.serial_number_ids :
                line_search = line.search(cr,uid,[
                                      ('permohonan_faktur_id','=',obj.id)
                                      ])
                if line_search :
                    line_browse = line.browse(cr,uid,line_search)
                    line_browse.write({
                                       'permohonan_faktur_id':False
                                       })
            
            
        if context is None:
            context = {}
        lot = []
        if branch_id :
            lot_pool = self.pool.get('stock.production.lot')
            if not exception:
                lot_search = lot_pool.search(cr,uid,[
                                            ('branch_id','=',branch_id),
                                            ('state','=','paid'),
                                            ('tgl_faktur','=',False),
                                            ('permohonan_faktur_id','=',False),
                                            ('lot_status_cddb','=','ok')
                                            ])
                
                if not lot_search :
                    lot = []
                elif lot_search :
                    lot_browse = lot_pool.browse(cr,uid,lot_search)           
                    for x in lot_browse :
                        lot.append([0,0,{
                                         'name':x.name,                               
                                         'chassis_no':x.chassis_no,
                                         'product_id':x.product_id.id,
                                         'customer_id':x.customer_id.id,
                                         'customer_stnk':x.customer_stnk.id,
                                         'state':x.state,
                        }])
            if exception :
                lot_search = lot_pool.search(cr,uid,[
                                            ('branch_id','=',branch_id),
                                            ('tgl_faktur','=',False),
                                            ('permohonan_faktur_id','=',False),
                                            ('lot_status_cddb','=','ok'),'|',
                                            ('state','=','sold'),'|',
                                            ('state','=','sold_offtr'),
                                            ('state','=','paid_offtr'),
                                            ])
                
                if not lot_search :
                    lot = []
                elif lot_search :
                    lot_browse = lot_pool.browse(cr,uid,lot_search)           
                    for x in lot_browse :
                        lot.append([0,0,{
                                         'name':x.name,                               
                                         'chassis_no':x.chassis_no,
                                         'product_id':x.product_id.id,
                                         'customer_id':x.customer_id.id,
                                         'customer_stnk':x.customer_stnk.id,
                                         'state':x.state,
                        }])
            branch_search = self.pool.get('wtc.branch').search(cr,uid,[('id','=',branch_id)])
            branch_browse = self.pool.get('wtc.branch').browse(cr,uid,branch_search)
            return {'value':{'serial_number_ids': lot,'partner_id':branch_browse.default_supplier_id.id,'ahm_code':branch_browse.ahm_code}}
    
    def create(self, cr, uid, vals, context=None):
        if not vals['serial_number_ids'] :
            raise osv.except_osv(('Perhatian !'), ("Tidak ada detail permohonan. Data tidak bisa di save."))

        lot_collect = []
        for x in vals['serial_number_ids']:
            lot_collect.append(x.pop(2))

        del[vals['serial_number_ids']]
        lot_pool = self.pool.get('stock.production.lot')
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'PF')
        vals['tgl_mohon_faktur'] = self._get_default_date(cr, uid, context=context)
        permohonan_id = super(wtc_permohonan_faktur, self).create(cr, uid, vals, context=context) 
        if permohonan_id : 
            for x in lot_collect :
                lot_search = lot_pool.search(cr,uid,[
                            ('branch_id','=',vals['branch_id']),
                            ('tgl_faktur','=',False),
                            ('name','=',x['name']),
                            ('state','in',('paid','sold'))
                            ])
                lot_browse = lot_pool.browse(cr,uid,lot_search)
                if lot_browse.permohonan_faktur_id:
                    raise osv.except_osv(('Perhatian !'), ("Data telah diproses di transaksi %s Periksa kembali data Anda.") % (lot_browse.permohonan_faktur_id.name))
                lot_browse.write({
                       'permohonan_faktur_id':permohonan_id,
                       })  
        else:
            raise osv.except_osv(('Perhatian !'), ("Data telah diproses user lain. Periksa kembali data Anda."))
        return permohonan_id  
    
    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        collect = self.browse(cr,uid,ids)
        lot = vals.get('serial_number_ids', False)
        dellot = ''
        if lot :
            del[vals['serial_number_ids']]
            for x,item in enumerate(lot) :
                lot_pool = self.pool.get('stock.production.lot')
                lot_id = item[1]

                if item[0] == 2 :
                    lot_search = lot_pool.search(cr,uid,[
                       ('id','=',lot_id)
                       ])
                    if not lot_search :
                        raise osv.except_osv(('Perhatian !'), ("Nomor Engine tidak ada didalam daftar"))
                    lot_browse = lot_pool.browse(cr,uid,lot_search)
                    lot_browse.write({
                                   'state_stnk':False,
                                   'permohonan_faktur_id':False,
                                   'tgl_faktur':False,
                                     })
                    dellot += ('- '+str(lot_browse.name)+'<br/>')
                elif item[0] == 0 :
                    values = item[2]
                    lot_search = lot_pool.search(cr,uid,[
                                                        ('name','=',values['name'])
                                                        ])
                    if not lot_search :
                        raise osv.except_osv(('Perhatian !'), ("Nomor Engine tidak ada didalam daftar Engine Nomor"))
            
                
                    lot_browse = lot_pool.browse(cr,uid,lot_search)
                    lot_browse.write({
                                      'permohonan_faktur_id':collect.id
                                      })
            if dellot :
                self.message_post(cr, uid, collect.id, body=_("Delete Engine No <br/> %s")%(dellot), context=context)                               

        return super(wtc_permohonan_faktur, self).write(cr, uid, ids, vals, context=context) 

    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Permohonan Faktur sudah di post ! tidak bisa didelete !"))

        lot_pool = self.pool.get('stock.production.lot')
        lot_search = lot_pool.search(cr,uid,[
                                           ('permohonan_faktur_id','=',ids)
                                           ])
        lot_browse = lot_pool.browse(cr,uid,lot_search)
        for x in lot_browse :
            x.write({'state_stnk': False,'tgl_faktur':False,'permohonan_faktur_id':False})
        return super(wtc_permohonan_faktur, self).unlink(cr, uid, ids, context=context)
    
    def action_button_permohonan(self,cr,uid,ids,context=None):
        lot = self.pool.get('stock.production.lot')
        cabang = []
        for val in ids :
            vals = lot.browse(cr,uid,val)
            if vals.branch_id not in cabang :
                cabang.append(vals.branch_id)
        form_id  = 'permohonan.faktur.form'
        view_pool = self.pool.get("ir.ui.view")
        vit = view_pool.search(cr,uid, [
                                     ("name", "=", form_id), 
                                     ("model", "=", 'wtc.permohonan.faktur'), 
                                    ])
        form_browse = view_pool.browse(cr,uid,vit)
        
        return {
            'name': 'Permohonan Faktur',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.permohonan.faktur',
            'type': 'ir.actions.act_window',
            'view_id' : form_browse.id,
            'nodestroy': True,
            'target': 'new',
#             'res_id': vals.customer_stnk.id
            } 
        
class wtc_cancel_permohonan_faktur(osv.osv):
    _name = "wtc.cancel.permohonan.faktur"
    _order = 'id desc'
    
    def _get_default_date(self,cr,uid,context=None):
        return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=None) 
    
    _columns = {
                'name':fields.char(string='Name'),
                'state':fields.selection([('draft','Draft'),('post','Posted')],string='State'),
                'date':fields.date('Date'),
                'permohonan_faktur_id' : fields.many2one('wtc.permohonan.faktur',domain="[('state','=','approved')]",string='No Permohonan Faktur'),
                'cancel_line' : fields.one2many('wtc.cancel.permohonan.faktur.line','cancel_permohonan_faktur_id',string='Cancel line'),             
                'confirm_uid':fields.many2one('res.users',string="Posted by"),
                'confirm_date':fields.datetime('Posted on'),
                }  
      
    _defaults = {
                 'state':'draft',
                 'date':_get_default_date
                 }
    
    def create(self,cr,uid,vals,context=None):
        vals['name'] = self.pool.get('ir.sequence').get_sequence(cr, uid, 'CPF', context=context)
        vals['date'] = self._get_default_date(cr, uid, context)
        if not vals.get('cancel_line') :
            raise osv.except_osv(('Perhatian !'), ("harap isi detail !"))             
        res = super(wtc_cancel_permohonan_faktur,self).create(cr,uid,vals,context=context)
        return res
    
    
    def wtc_cancel_permohonan_faktur(self, cr, uid, ids, context=None):
        val = self.browse(cr,uid,ids)
        pf = self.pool.get('wtc.permohonan.faktur').browse(cr,uid,[val.permohonan_faktur_id.id])  
        lot_pool = self.pool.get('stock.production.lot')
        if len(pf.serial_number_ids) == 1 :
            self.pool.get('wtc.permohonan.faktur').write(cr,uid,pf.id,{'state':'cancel','cancel_uid':uid,'cancel_date':datetime.now()})         
        for x in val.cancel_line :
            lot_search = lot_pool.search(cr,uid,[
                        ('branch_id','=',pf.branch_id.id),
                        ('permohonan_faktur_id','=',pf.id),
                        ('name','=',x.name.name)
                        ])
            if not lot_search :
                raise osv.except_osv(('Perhatian !'), ("No Engine Tidak Ditemukan."))
            if lot_search :
                lot_browse = lot_pool.browse(cr,uid,lot_search)
                if lot_browse.penerimaan_faktur_id or lot_browse.penerimaan_notice_id or lot_browse.proses_stnk_id or lot_browse.penerimaan_stnk_id or lot_browse.penerimaan_bpkb_id or lot_browse.proses_biro_jasa_id :
                    raise osv.except_osv(('Perhatian !'), ("No faktur engine \'%s\' telah diproses, data tidak bisa di cancel !")%(lot_browse.name))                    
                else : 
                    lot_browse.write({'state_stnk': False,'tgl_faktur':False,'permohonan_faktur_id':False})        
        self.write(cr, uid, ids, {'state': 'post', 'date':self._get_default_date(cr, uid, context),'confirm_uid':uid,'confirm_date':datetime.now()})
        return True
     
     
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Cancel Permohonan Faktur sudah di validate ! tidak bisa didelete !"))
        return super(wtc_cancel_permohonan_faktur, self).unlink(cr, uid, ids, context=context)
                   
class wtc_cancel_permohonan_faktur_line(osv.osv):
    _name = "wtc.cancel.permohonan.faktur.line"
    
    _columns = {
                'name':fields.many2one('stock.production.lot',string='No Engine',domain="[('permohonan_faktur_id','=',parent.permohonan_faktur_id)]"),
                'cancel_permohonan_faktur_id':fields.many2one('wtc.cancel.permohonan.faktur',string='No Cancel permohonan'),
                'chassis_no' : fields.related('name','chassis_no',type='char',string='Chassis No'),
                }       
    
    _sql_constraints = [
    ('unique_name_cancel_permohonan_faktur_id', 'unique(name,cancel_permohonan_faktur_id)', 'Detail Engine duplicate, mohon cek kembali !'),
]    
        
    def onchange_engine(self,cr,uid,ids,engine_id,context=None):
        value = {}
        if engine_id :
            lot = self.pool.get('stock.production.lot').browse(cr,uid,engine_id)
            value['chassis_no'] = lot.chassis_no or False
        return {'value':value}