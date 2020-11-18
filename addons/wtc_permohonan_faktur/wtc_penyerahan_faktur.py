import time
from datetime import datetime
from openerp.osv import fields, osv

class wtc_penyerahan_faktur(osv.osv):
    _name = "wtc.penyerahan.faktur"
    _order = "tanggal desc"
    
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
                'partner_id':fields.many2one('res.partner','Customer',domain=[('customer','=',True)]),
                'keterangan':fields.char('Keterangan'),
                'tanggal':fields.date('Tanggal'),
                'penyerahan_line' : fields.one2many('wtc.penyerahan.faktur.line','penyerahan_id',string="Penyerahan STNK"),  
                'state': fields.selection([('draft', 'Draft'), ('posted','Posted'),('cancel','Canceled')], 'State', readonly=True),
                'engine_no': fields.related('penyerahan_line', 'name', type='char', string='No Engine'),
                'customer_stnk': fields.related('penyerahan_line', 'customer_stnk', type='many2one', relation='res.partner', string='Customer STNK'),
                'confirm_uid':fields.many2one('res.users',string="Posted by"),
                'confirm_date':fields.datetime('Posted on'),                     
                }
 
    _defaults = {
      'state':'draft',
      'division' : 'Unit',
      'tanggal': _get_default_date,
      'branch_id': _get_default_branch,

     } 
    def onchange_partner(self,cr,uid,ids,partner):
        value = {}
        if partner :
            res_partner = self.pool.get('res.partner').search(cr,uid,[
                                                                      ('id','=',partner)
                                                                      ])
            res_partner_browse = self.pool.get('res.partner').browse(cr,uid,res_partner)            
            value = {'penerima':res_partner_browse.name}          
        return {'value':value}    
    
    def post_penyerahan(self,cr,uid,ids,context=None):
        val = self.browse(cr,uid,ids)
        lot_pool = self.pool.get('stock.production.lot') 
        tanggal = self._get_default_date(cr, uid, context=context)
        self.write(cr, uid, ids, {'state': 'posted','tanggal':tanggal,'confirm_uid':uid,'confirm_date':datetime.now()})       
 
        for x in val.penyerahan_line :
            lot_search = lot_pool.search(cr,uid,[
                        ('id','=',x.name.id)
                        ])
            lot_browse = lot_pool.browse(cr,uid,lot_search)   
 
            lot_browse.write({
                    'tgl_penyerahan_faktur':x.tgl_ambil_faktur,
                     })      
                           
        return True
    
    def create(self, cr, uid, vals, context=None):
        if not vals['penyerahan_line'] :
            raise osv.except_osv(('Perhatian !'), ("Tidak ada detail penyerahan. Data tidak bisa di save."))
        lot_penyerahan = []
        for x in vals['penyerahan_line']:
            lot_penyerahan.append(x.pop(2))
        lot_pool = self.pool.get('stock.production.lot')
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'PFK')
        vals['tanggal'] = self._get_default_date(cr, uid, context=context),
        del[vals['penyerahan_line']]        
        penyerahan_id = super(wtc_penyerahan_faktur, self).create(cr, uid, vals, context=context) 
        if penyerahan_id :         
            for x in lot_penyerahan :
                
                lot_search = lot_pool.search(cr,uid,[
                            ('id','=',x['name'])
                            ])
                lot_browse = lot_pool.browse(cr,uid,lot_search)
                penyerahan_pool = self.pool.get('wtc.penyerahan.faktur.line')
                penyerahan_pool.create(cr, uid, {
                                                    'name':lot_browse.id,
                                                    'penyerahan_id':penyerahan_id,
                                                    'customer_stnk':13,
                                                    'tgl_cetak_faktur':lot_browse.tgl_cetak_faktur,
                                                    'faktur_stnk':lot_browse.faktur_stnk,
                                                    'tgl_ambil_faktur':x['tgl_ambil_faktur'],
                                                    })  
                lot_browse.write({
                       'penyerahan_faktur_id':penyerahan_id,
                                  })
        else :
            return False
        return penyerahan_id

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        val = self.browse(cr,uid,ids)    
        vals.get('penyerahan_line',[]).sort(reverse=True)        
        penyerahan_pool = self.pool.get('wtc.penyerahan.faktur.line')
        lot_pool = self.pool.get('stock.production.lot')
        lot = vals.get('penyerahan_line', False)
        if lot :
            del[vals['penyerahan_line']]
            for x,item in enumerate(lot) :
                lot_id = item[1]

                if item[0] == 2 :
                    id_lot = item[2]
                    search = penyerahan_pool.search(cr,uid,[
                                                            ('id','=',lot_id)
                                                            ])
                    if not search :
                        raise osv.except_osv(('Perhatian !'), ("Nomor Engine tidak ada didalam daftar"))
                    browse = penyerahan_pool.browse(cr,uid,search)
                     
                    lot_search = lot_pool.search(cr,uid,[
                       ('id','=',browse.name.id)
                       ])
                    if not lot_search :
                        raise osv.except_osv(('Perhatian !'), ("Nomor Engine tidak ada didalam daftar"))
                    lot_browse = lot_pool.browse(cr,uid,lot_search)

                    lot_browse.write({
                                       'penyerahan_faktur_id':False,
                                     })
                    penyerahan_pool.unlink(cr,uid,lot_id, context=context)
                elif item[0] == 0 :
                    values = item[2]
                    lot_search = lot_pool.search(cr,uid,[
                                                        ('id','=',values['name'])
                                                        ])
                    if not lot_search :
                        raise osv.except_osv(('Perhatian !'), ("Nomor Engine tidak ada didalam daftar Engine Nomor"))
            
                
                    lot_browse = lot_pool.browse(cr,uid,lot_search)
                    
                    penyerahan_pool.create(cr, uid, {
                                    'name':lot_browse.id,
                                    'penyerahan_id':val.id,
                                    'customer_stnk':lot_browse.customer_stnk.id,
                                    'tgl_cetak_faktur':lot_browse.tgl_cetak_faktur,
                                    'faktur_stnk':lot_browse.faktur_stnk,
                                    'tgl_ambil_faktur':values['tgl_ambil_faktur'],
                                    })
                    
                    lot_browse.write({
                           'penyerahan_faktur_id':val.id,  
                                                       }) 
                elif item[0] == 1 :
                    data = item[2]
                    penyerahan_search = penyerahan_pool.search(cr,uid,[
                                                                       ('id','=',lot_id)
                                                                       ])
                    penyerahan_browse = penyerahan_pool.browse(cr,uid,penyerahan_search)
                    if penyerahan_search :
                        if 'tgl_ambil_faktur' in data :
                            penyerahan_browse.write({
                                                     'tgl_ambil_faktur':data['tgl_ambil_faktur']
                                                     })
                                                        
        return super(wtc_penyerahan_faktur, self).write(cr, uid, ids, vals, context=context) 

    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Penyerahan Faktur sudah di validate ! tidak bisa didelete !"))

        lot_pool = self.pool.get('stock.production.lot')

        for x in self.browse(cr, uid, ids, context=context):
            for y in x.penyerahan_line :
                lot_search = lot_pool.search(cr,uid,[
                                                     ('id','=',y.name.id)
                                                     ])
                if lot_search :
                    lot_browse = lot_pool.browse(cr,uid,lot_search)
                    lot_browse.write({
                                      'tgl_penyerahan_faktur':False,})     
                       

        return super(wtc_penyerahan_faktur, self).unlink(cr, uid, ids, context=context)    
    
class wtc_penyerahan_faktur_line(osv.osv):
    _name = "wtc.penyerahan.faktur.line"
    _columns = {
                'name' : fields.many2one('stock.production.lot','No Engine',change_default=True,),                
                'penyerahan_id' : fields.many2one('wtc.penyerahan.faktur','Penyerahan Faktur'),
                'customer_stnk':fields.related('name','customer_stnk',type='many2one',relation='res.partner',readonly=True,string='Customer STNK'),
                'tgl_cetak_faktur' : fields.related('name','tgl_cetak_faktur',type="date",readonly=True,string='Tgl Cetak Faktur'),
                'faktur_stnk' : fields.related('name','faktur_stnk',type="char",readonly=True,string='No Faktur STNK'),
                'tgl_ambil_faktur' :fields.date('Tgl Ambil Faktur')
                
                }
    _sql_constraints = [
    ('unique_name_penyerahan_id', 'unique(name,penyerahan_id)', 'Detail Engine duplicate, mohon cek kembali !'),
]
    
    def _get_default_date(self,cr,uid,context=None):
        return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=None)
         
    _defaults = {
      'tgl_ambil_faktur': _get_default_date,

     } 
        
    def onchange_engine(self, cr, uid, ids, name,branch_id,division,customer,penerima_stnk):
        if not branch_id or not division or not penerima_stnk:
            raise osv.except_osv(('Perhatian !'), ('Sebelum menambah detil transaksi,\n harap isi branch, division, peneriman STNK terlebih dahulu.'))
    
        value = {}
        domain = {}
        result = {}
        
        if customer :
            domain['name'] ="[('penerimaan_faktur_id','!=',False),('faktur_stnk','!=',False),('state_stnk','=','terima_faktur'),('branch_id','=',parent.branch_id),('customer_id','=',parent.partner_id),('tgl_penyerahan_faktur','=',False),'|',('state','=','sold_offtr'),('state','=','paid_offtr')]"
        elif not customer :
            domain['name'] ="[('penerimaan_faktur_id','!=',False),('faktur_stnk','!=',False),('state_stnk','=','terima_faktur'),('branch_id','=',parent.branch_id),('tgl_penyerahan_faktur','=',False),'|',('state','=','sold_offtr'),('state','=','paid_offtr')]"
                
        if name :
            lot_obj = self.pool.get('stock.production.lot')
            lot_search = lot_obj.search(cr,uid,[
                                                      ('id','=',name)
                                                      ])
            if lot_search :
                lot_browse = lot_obj.browse(cr,uid,lot_search)          
                value = {
                         'customer_stnk':lot_browse.customer_stnk.id,
                         'tgl_cetak_faktur':lot_browse.tgl_cetak_faktur,
                         'faktur_stnk':lot_browse.faktur_stnk,
                         }        
        return {'domain':domain,'value':value}