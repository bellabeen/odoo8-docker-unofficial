import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
  
class wtc_proses_stnk(osv.osv):
    _name = 'wtc.proses.stnk'
    _inherit = ['mail.thread']
    _description = "Proses STNK"
    _order = "tgl_proses_stnk desc,id desc"
    
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
           
    def _get_default_date(self,cr,uid,context=None):
        return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)
                
    _columns = {
        'branch_id': fields.many2one('wtc.branch', string='Branch', required=True),
        'division':fields.selection([('Unit','Unit')], 'Division', change_default=True, select=True),
        'name': fields.char('No Reference',size=20, readonly=True),
        'tgl_proses_stnk': fields.date('Tanggal'),
        'state': fields.selection([('draft', 'Draft'), ('posted','Posted'),('cancel','Canceled')], 'State', readonly=True),
        'serial_number_ids': fields.one2many('stock.production.lot','proses_stnk_id',string="Table Proses STNK"), 
        'partner_id':fields.many2one('res.partner','Biro Jasa',domain=[('biro_jasa','=',True)]),
        'engine_no': fields.related('serial_number_ids', 'name', type='char',string='No Engine'),
        'customer_stnk': fields.related('serial_number_ids', 'customer_stnk', type='many2one', relation='res.partner', string='Customer STNK'),
        'confirm_uid':fields.many2one('res.users',string="Posted by"),
        'confirm_date':fields.datetime('Posted on'),
        'cancel_uid':fields.many2one('res.users',string="Cancelled by"),
        'cancel_date':fields.datetime('Cancelled on'),         
    }
    _defaults = {
      'tgl_proses_stnk': _get_default_date,
      'state':'draft',
      'division' : 'Unit',
      'branch_id': _get_default_branch,
     }    
    
    def cancel_proses(self,cr,uid,ids,context=None):
        val = self.browse(cr,uid,ids)  
        lot_pool = self.pool.get('stock.production.lot') 
        for x in val.serial_number_ids :
            lot_search = lot_pool.search(cr,uid,[
                        ('branch_id','=',val.branch_id.id),
                        ('proses_stnk_id','=',val.id),
                        ('name','=',x.name),
                        ])
            if lot_search :
                lot_browse = lot_pool.browse(cr,uid,lot_search)
                if lot_browse.penerimaan_stnk_id.id or lot_browse.penerimaan_notice_id.id or lot_browse.penerimaan_bpkb_id.id or lot_browse.proses_biro_jasa_id.id :
                    raise osv.except_osv(('Perhatian !'), ("No faktur engine \'%s\' telah diproses, data tidak bisa di cancel !")%(lot_browse.name))                    
                else : 
                    lot_browse.write({'state_stnk': 'terima_faktur','tgl_proses_stnk':False,'proses_stnk_id':False})
            
            if not lot_search :
                raise osv.except_osv(('Perhatian !'), ("Tidak ada detail penerimaan. Data tidak bisa di save."))
        self.write(cr, uid, ids, {'state': 'cancel','cancel_uid':uid,'cancel_date':datetime.now()})
        self.message_post(cr, uid, val.id, body=_("Proses STNK canceled "), context=context) 
        
        return True
    
    def post_proses(self,cr,uid,ids,context=None):                                
        val = self.browse(cr,uid,ids)  
        lot_pool = self.pool.get('stock.production.lot') 
        engine = ''
        tanggal = self._get_default_date(cr, uid, context)
        self.write(cr, uid, ids, {'state': 'posted','tgl_proses_stnk':tanggal,'confirm_uid':uid,'confirm_date':datetime.now()})
        for x in val.serial_number_ids :
            lot_search = lot_pool.search(cr,uid,[
                        ('branch_id','=',val.branch_id.id),
                        ('biro_jasa_id','=',val.partner_id.id),
                        ('state_stnk','=','terima_faktur'),
                        ('tgl_terima','!=',False),
                        ('tgl_proses_stnk','=',False),
                        ('name','=',x.name)
                        ])
            if not lot_search :
                raise osv.except_osv(('Perhatian !'), ("Tidak ada detail penerimaan. Data tidak bisa di save."))
            if lot_search :
                lot_browse = lot_pool.browse(cr,uid,lot_search)
                lot_browse.write({
                        'state_stnk':'proses_stnk',
                        'tgl_proses_stnk': val.tgl_proses_stnk,
                       })
            engine += ('- '+str(x.name)+'<br/>')
     
        self.message_post(cr, uid, val.id, body=_("Proses STNK posted <br/> No Engine : <br/>  %s ")%(engine), context=context)                             
        
        return True
    
    def onchange_engine_line(self, cr, uid, ids, branch_id,partner_id,context=None):
        line = self.pool.get('stock.production.lot')
        value = {}
        if ids :
            obj = self.browse(cr,uid,ids)
            if obj.serial_number_ids.name :
                for x in obj.serial_number_ids :
                    line_search = line.search(cr,uid,[
                                          ('proses_stnk_id','=',obj.id)
                                          ])
                    if line_search :
                        line_browse = line.browse(cr,uid,line_search)
                        line_browse.write({
                                           'proses_stnk_id':False
                                           })
            
            
        if context is None:
            context = {}
        if branch_id is None :
            context = {}
        if partner_id is None :
            context = {}
        if branch_id and partner_id :
            lot_pool = self.pool.get('stock.production.lot')
            lot_search = lot_pool.search(cr,uid,[
                                        ('branch_id','=',branch_id),
                                        ('biro_jasa_id','=',partner_id),
                                        ('state_stnk','=','terima_faktur'),
                                        ('tgl_terima','!=',False),
                                        ('tgl_proses_stnk','=',False),
                                        ('proses_stnk_id','=',False),'|',
                                        ('state','=','sold'),
                                        ('state','=','paid'),
                                        ])
            lot = []
            if not lot_search :
                lot = []
            elif lot_search :
                lot_browse = lot_pool.browse(cr,uid,lot_search)           
                for x in lot_browse :
                    lot.append([0,0,{
                                     'name':x.name,                               
                                     'chassis_no':x.chassis_no,
                                     'customer_stnk':x.customer_stnk.id,
                                     'faktur_stnk':x.faktur_stnk,
                                     'tgl_faktur':x.tgl_faktur,
                                     'tgl_terima':x.tgl_terima
                    }])   
            value['serial_number_ids']= lot
        domain = {}
        birojasa = []
        birojasa_srch = self.pool.get('wtc.harga.birojasa').search(cr,uid,[
                                                                      ('branch_id','=',branch_id)
                                                                      ])
        if birojasa_srch :
            birojasa_brw = self.pool.get('wtc.harga.birojasa').browse(cr,uid,birojasa_srch)
            for x in birojasa_brw :
                birojasa.append(x.birojasa_id.id)
        domain['partner_id'] = [('id','in',birojasa)]                    
        return {'value':value,'domain':domain}
    
# Override method create()
    def create(self, cr, uid, vals, context=None):
        if not vals['serial_number_ids'] :
            raise osv.except_osv(('Perhatian !'), ("Tidak ada detail proses STNK. Data tidak bisa di save."))

        lot_collect = []
        for x in vals['serial_number_ids']:
            lot_collect.append(x.pop(2))
        del[vals['serial_number_ids']]
        lot_pool = self.pool.get('stock.production.lot')
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'BJ')
        vals['tgl_proses_stnk'] = self._get_default_date(cr, uid, context)
        try :

            proses_stnk_id = super(wtc_proses_stnk, self).create(cr, uid, vals, context=context) 
            if proses_stnk_id : 
                        
                for x in lot_collect :
                    lot_search = lot_pool.search(cr,uid,[
                                ('branch_id','=',vals['branch_id']),
                                ('biro_jasa_id','=',vals['partner_id']),
                                ('state_stnk','=','terima_faktur'),
                                ('tgl_terima','!=',False),
                                ('tgl_proses_stnk','=',False),
                                ('name','=',x['name'])
                                ])
                    if lot_search :
                        lot_browse = lot_pool.browse(cr,uid,lot_search)
                        lot_browse.write({
                               'proses_stnk_id':proses_stnk_id,
                               })  
                                    
            else :
                return False
            cr.commit()
        except Exception:
            cr.rollback()
            raise osv.except_osv(('Perhatian !'), ("Data telah diproses user lain. Periksa kembali data Anda."))
        return proses_stnk_id  

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
            
        collect = self.browse(cr,uid,ids)

        lot = vals.get('serial_number_ids', False)
       
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
                                   'proses_stnk_id':False,
                                   'tgl_proses_stnk':False,
                                     })
                    self.message_post(cr, uid, collect.id, body=_("Delete Engine No \'%s\'")%(lot_browse.name), context=context)                                                                           
                elif item[0] == 0 :
                    values = item[2]
                    lot_search = lot_pool.search(cr,uid,[
                                                        ('name','=',values['name'])
                                                        ])
                    if not lot_search :
                        raise osv.except_osv(('Perhatian !'), ("Nomor Engine tidak ada didalam daftar Engine Nomor"))
            
                
                    lot_browse = lot_pool.browse(cr,uid,lot_search)
                    lot_browse.write({
                                      'proses_stnk_id':collect.id
                                      })                    
            
        return super(wtc_proses_stnk, self).write(cr, uid, ids, vals, context=context) 

    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Permohonan Faktur sudah di validate ! tidak bisa didelete !"))

        lot_pool = self.pool.get('stock.production.lot')
        lot_search = lot_pool.search(cr,uid,[
                                           ('proses_stnk_id','=',ids)
                                           ])
        lot_browse = lot_pool.browse(cr,uid,lot_search)
        for x in lot_browse :
            x.write({'tgl_proses_stnk':False})
        return super(wtc_proses_stnk, self).unlink(cr, uid, ids, context=context)
    