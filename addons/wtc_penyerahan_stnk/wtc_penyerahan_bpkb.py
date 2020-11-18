import time
from datetime import datetime
from openerp.osv import fields, osv

class wtc_penyerahan_bpkb(osv.osv):
    _name = "wtc.penyerahan.bpkb"
    _order ="tanggal desc"
    
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids    
    
    def _get_default_date(self,cr,uid,context=None):
        return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=None)    
    
    _columns = {
                'name': fields.char('No Reference',size=20, readonly=True),
                'branch_id': fields.many2one('wtc.branch', string='Branch', required=True),
                'division':fields.selection([('Unit','Unit')], 'Division', change_default=True, select=True),
                'penerima':fields.char('Penerima'),
                'partner_id':fields.many2one('res.partner','A/N BPKB'),
                'keterangan':fields.char('Keterangan'),
                'tanggal':fields.date('Tanggal'),
                'penyerahan_line' : fields.one2many('wtc.penyerahan.bpkb.line','penyerahan_id',string="Penyerahan STNK"),  
                'state': fields.selection([('draft', 'Draft'), ('posted','Posted'),('cancel','Canceled')], 'State', readonly=True),
                'engine_no': fields.related('penyerahan_line', 'name', type='char', string='No Engine'),
                'customer_stnk': fields.related('penyerahan_line', 'customer_stnk', type='many2one', relation='res.partner', string='Customer STNK'),
                'no_bpkb': fields.related('penyerahan_line', 'no_bpkb', type='char', string='No BPKB'),
                'tgl_penyerahan_bpkb' :fields.date('Tgl Penyerahan BPKB'),
                'cetak_ke' : fields.integer('Cetak Ke'),     
                'confirm_uid':fields.many2one('res.users',string="Posted by"),
                'confirm_date':fields.datetime('Posted on'),
                'cancel_uid':fields.many2one('res.users',string="Cancelled by"),
                'cancel_date':fields.datetime('Cancelled on'),
                'partner_type' : fields.selection([('customer','Customer'),('fincoy','Finance Company')],string='Partner Type')                 
                 
                }
 
    _defaults = {
      'state':'draft',
      'division' : 'Unit',
      'tanggal': _get_default_date,
      'tgl_penyerahan_bpkb': _get_default_date,
      'cetak_ke' : 0,
      'branch_id': _get_default_branch,
      'partner_type' : 'customer'
      
     } 
    
    def post_penyerahan(self,cr,uid,ids,context=None):
        val = self.browse(cr,uid,ids)
        lot_pool = self.pool.get('stock.production.lot') 
        tanggal = self._get_default_date(cr, uid, context=context)
        self.write(cr, uid, ids, {'state': 'posted','tanggal':tanggal,'confirm_uid':uid,'confirm_date':datetime.now()})               
        for x in val.penyerahan_line :
            x.write({'lokasi_bpkb_id': x.name.lokasi_bpkb_id.id})
            x.name.write({
                   'tgl_penyerahan_bpkb':tanggal,
                   'lokasi_bpkb_id':False,
                   'penyerahan_bpkb_id': val.id,
                   })   
        return True
    
    def create(self, cr, uid, vals, context=None):
        if not vals['penyerahan_line'] :
            raise osv.except_osv(('Perhatian !'), ("Tidak ada detail penyerahan. Data tidak bisa di save."))
        lot_penyerahan = []
#         for x in vals['penyerahan_line']:
#             lot_penyerahan.append(x.pop(2))
#         lot_pool = self.pool.get('stock.production.lot')
        penyerahan_pool = self.pool.get('wtc.penyerahan.bpkb.line')
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'ENCB')
        
        vals['tanggal'] = self._get_default_date(cr, uid, context=context)
#         del[vals['penyerahan_line']]

        
        penyerahan_id = super(wtc_penyerahan_bpkb, self).create(cr, uid, vals, context=context) 

#         if penyerahan_id :         
#             for x in lot_penyerahan :
#                 lot_search = lot_pool.search(cr,uid,[
#                             ('id','=',x['name'])
#                             ])
#                 if not lot_search :
#                     raise osv.except_osv(('Perhatian !'), ("No Engine tidak ditemukan !"))
#                 lot_browse = lot_pool.browse(cr,uid,lot_search)
#                 lot_browse.write({
#                        'penyerahan_bpkb_id':penyerahan_id,
#                        })   
#                 penyerahan_pool.create(cr, uid, {
#                                                      'name':lot_browse.id,
#                                                      'penyerahan_id':penyerahan_id,
#                                                      'customer_stnk':lot_browse.customer_stnk.id,
#                                                      'no_bpkb':lot_browse.no_bpkb,
#                                                      'no_urut':lot_browse.no_urut_bpkb,
#                                                      'tgl_ambil_bpkb':x['tgl_ambil_bpkb']
#                                                     })
#                            
#         else :
#             return False
        return penyerahan_id

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        vals.get('penyerahan_line',[]).sort(reverse=True)

        collect = self.browse(cr,uid,ids)
        lot_penyerahan = []
        lot_pool = self.pool.get('stock.production.lot')
        line_pool = self.pool.get('wtc.penyerahan.bpkb.line')
        lot = vals.get('penyerahan_line', False)
        if lot :
            for x,item in enumerate(lot) :
                lot_id = item[1]
                if item[0] == 2 :               
                    line_search = line_pool.search(cr,uid,[
                                                           ('id','=',lot_id)
                                                           ])
                    line_browse = line_pool.browse(cr,uid,line_search)
                    lot_search = lot_pool.search(cr,uid,[
                                           ('id','=',line_browse.name.id)
                                           ])
                    if not line_search :
                        raise osv.except_osv(('Perhatian !'), ("Nomor Engine tidak ada didalam daftar Penerimaan Line"))
                    if not lot_search :
                        raise osv.except_osv(('Perhatian !'), ("Nomor Engine tidak ada didalam daftar Engine Nomor"))
                    lot_browse = lot_pool.browse(cr,uid,lot_search)
                    del[vals['penyerahan_line']]
                    lot_browse.write({
                                   'penyerahan_bpkb_id':False,
                                   'tgl_penyerahan_bpkb':False
                                     })
                    line_pool.unlink(cr,uid,lot_id, context=context)
                        
                elif item[0] == 0 :
                    values = item[2]
                    lot_search = lot_pool.search(cr,uid,[
                                                        ('id','=',values['name'])
                                                        ])
                    if not lot_search :
                        raise osv.except_osv(('Perhatian !'), ("Nomor Engine tidak ada didalam daftar Engine Nomor"))
                    
                    lot_browse = lot_pool.browse(cr,uid,lot_search)
                    lot_browse.write({
                           'penyerahan_bpkb_id':collect.id,
                           }) 
                    
        return super(wtc_penyerahan_bpkb, self).write(cr, uid, ids, vals, context=context) 

    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Penyerahan BPKB sudah di post ! tidak bisa didelete !"))

        lot_pool = self.pool.get('stock.production.lot')
        lot_search = lot_pool.search(cr,uid,[
                                           ('penyerahan_bpkb_id','=',ids)
                                           ])
        lot_browse = lot_pool.browse(cr,uid,lot_search)
        for x in lot_browse :
            x.write({
                     'tgl_penyerahan_bpkb':False,
                     })
        return super(wtc_penyerahan_bpkb, self).unlink(cr, uid, ids, context=context)   
    
    def onchange_partner(self,cr,uid,ids,partner,penerima,context=None):
        warning = {}  
        value = {}  
        result = {}  
        obj_browse = self.pool.get('res.partner').browse(cr,uid,[partner]) 
        if partner :
            res_partner = self.pool.get('res.partner').search(cr,uid,[
                                                                      ('id','=',partner)
                                                                      ])
            res_partner_browse = self.pool.get('res.partner').browse(cr,uid,res_partner)            
            if obj_browse.finance_company :
                value = {'penerima':res_partner_browse.name}
        if partner and penerima :
            if obj_browse.finance_company and penerima != obj_browse.name:
                warning = {
                        'title': ('Perhatian !'),
                        'message': ('A/N BPKB adalah Finance Company, Nama Penerima harus sama'),
                    } 
                if warning :
                    value = {'penerima':False}

        result['value'] = value         
        result['warning'] = warning
        return result
    
    def onchange_partner_type(self,cr,uid,ids,partner_type,context=None):
        dom={}        
        val={}
        if partner_type :
            val['partner_id'] = False
            if partner_type == 'fincoy' :
                dom['partner_id'] = [('finance_company','!=',False)]               
            elif partner_type == 'customer' :
                dom['partner_id'] = [('customer','!=',False)]                                 
        return {'domain':dom,'value':val} 
        
class wtc_penyerahan_bpkb_line(osv.osv):
    _name = "wtc.penyerahan.bpkb.line"
    
    def _get_default_date(self,cr,uid,context=None):
        return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=None)     
    
    _columns = {
                'name' : fields.many2one('stock.production.lot','No Engine',domain="['|',('create_date','=','2015-09-30 00:00:00'),('tgl_proses_birojasa','!=',False),('tgl_terima_bpkb','!=',False),('state_stnk','=','proses_stnk'),('lokasi_bpkb_id.branch_id','=',parent.branch_id),('tgl_penyerahan_bpkb','=',False),'|',('finco_id','=',parent.partner_id),'&',('customer_id','=',parent.partner_id),('finco_id','=',False)]",change_default=True),        
                'penyerahan_id' : fields.many2one('wtc.penyerahan.bpkb','Penyerahan STNK'),
                'customer_stnk':fields.related('name','customer_stnk',type='many2one',relation='res.partner',readonly=True,string='Customer STNK'),
                'no_bpkb' : fields.related('name','no_bpkb',type="char",readonly=True,string='No BPKB'),
                'tgl_ambil_bpkb' : fields.date('Tgl Ambil BPKB'),
                'no_urut':fields.related('name','no_urut_bpkb',type='char',readonly=True,string='No Urut'),
                'lokasi_bpkb_id': fields.many2one('wtc.lokasi.bpkb')
                }
    _defaults = {

      'tgl_ambil_bpkb': _get_default_date,
     }
    _sql_constraints = [
    ('unique_name_penyerahan_id', 'unique(name,penyerahan_id)', 'Detail Engine duplicate, mohon cek kembali !'),
]    
    def onchange_engine(self, cr, uid, ids, name,branch_id,division,birojasa,penerima_bpkb):
        if not branch_id or not division or not birojasa or not penerima_bpkb:
            raise osv.except_osv(('Perhatian !'), ('Sebelum menambah detil transaksi,\n harap isi branch, division, peneriman STNK dan Customer STNK terlebih dahulu.'))
    
        warning={}
        value = {}
        if name :
            lot_obj = self.pool.get('stock.production.lot')
            search_double = self.search(cr,uid,[
                                                      ('name','=',name),
                                                      ('penyerahan_id','!=',False)
                                                      ])
            if search_double:
                for double_browse in self.browse(cr,uid,search_double):
                    if double_browse.penyerahan_id.state!='cancel':
                        warning = {
                            'title': ('Perhatian !'),
                            'message': (('No Engine \'%s\' telah diproses dengan no penyerahan BPKB \'%s\' mohon post atau cancel terlebih dahulu, atau hapus dari detail penerimaan ! ') % (double_browse.name.name,double_browse.penyerahan_id.name)),
                        }
                        value = {
                                 'name':False,
                                 }
                        return {'warning':warning,'value':value}
                        
            lot_browse=lot_obj.browse(cr,uid,name)
            if lot_browse:
                value = {
                         'customer_stnk':lot_browse.customer_stnk.id,
                         'no_bpkb':lot_browse.no_bpkb,
                         'no_urut':lot_browse.no_urut_bpkb
                         }        
        return {'warning':warning,'value':value}