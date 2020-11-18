import time
from datetime import datetime
from openerp.osv import fields, osv
from string import whitespace

class wtc_penerimaan_stnk(osv.osv):
    _name = "wtc.penerimaan.stnk"
    _order = "tgl_terima desc,id desc"
    
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
        'state': fields.selection([('draft', 'Draft'), ('posted','Posted'),('cancel','Canceled')], 'State', readonly=True),
        'penerimaan_line': fields.one2many('wtc.penerimaan.stnk.line','penerimaan_notice_id',string="Table Penerimaan STNk"), 
        'partner_id':fields.many2one('res.partner','Biro Jasa',domain=[('biro_jasa','=',True)]),
        'tgl_terima' : fields.date('Tanggal'),
        'lokasi_stnk_id' : fields.many2one('wtc.lokasi.stnk',string="Lokasi",domain="[('branch_id','=',branch_id),('type','=','internal')]"),
        'engine_no': fields.related('penerimaan_line', 'name', type='char', string='No Engine'),
        'customer_stnk': fields.related('penerimaan_line', 'customer_stnk', type='many2one', relation='res.partner', string='Customer STNK'),
        'confirm_uid':fields.many2one('res.users',string="Posted by"),
        'confirm_date':fields.datetime('Posted on'),
        'cancel_uid':fields.many2one('res.users',string="Cancelled by"),
        'cancel_date':fields.datetime('Cancelled on'),         
    }
    _defaults = {
      'state':'draft',
      'division' : 'Unit',
      'tgl_terima': _get_default_date,
      'branch_id': _get_default_branch,
     }   

    def birojasa_change(self,cr,uid,ids,branch_id,birojasa_id,context=None):
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
        return {'domain':domain}       
     
    def cancel_penerimaan(self,cr,uid,ids,context=None):
        val = self.browse(cr,uid,ids)  
        lot_pool = self.pool.get('stock.production.lot') 
        for x in val.penerimaan_line :
            lot_search = lot_pool.search(cr,uid,[
                        ('branch_id','=',val.branch_id.id),
                        ('biro_jasa_id','=',val.partner_id.id),
                        ('id','=',x.name.id),
                        ('lokasi_stnk_id','=',val.lokasi_stnk_id.id),
                        ])
            if not lot_search :
                raise osv.except_osv(('Perhatian !'), ("No Engine Tidak Ditemukan."))
            if lot_search :
                lot_browse = lot_pool.browse(cr,uid,lot_search)
                
                if lot_browse.penerimaan_notice_id.id == val.id :
                    lot_browse.write({
                                      'penerimaan_notice_id':False,
                                      'no_notice':False,
                                      'tgl_notice':False,
                                      'tgl_terima_notice':False})
                    
                if lot_browse.penerimaan_stnk_id.id == val.id :
                    lot_browse.write({
                                      'penerimaan_stnk_id':False,
                                      'no_stnk':False,
                                      'tgl_stnk':False,
                                      'tgl_terima_stnk':False})  
                if lot_browse.penerimaan_no_polisi_id.id == val.id  :            
                    lot_browse.write({
                                      'penerimaan_no_polisi_id':False,
                                      'no_polisi':False,
                                      'tgl_terima_notice':False})
                lot_browse.write({
                                  'lokasi_stnk_id':False
                                  })
                
        self.write(cr, uid, ids, {'state': 'cancel','cancel_uid':uid,'cancel_date':datetime.now()})
        return True
    
    def post_penerimaan(self,cr,uid,ids,context=None):
        val = self.browse(cr,uid,ids)
        lot_pool = self.pool.get('stock.production.lot') 
        tanggal = self._get_default_date(cr, uid, context)
        self.write(cr, uid, ids, {'state': 'posted','tgl_terima':tanggal,'confirm_uid':uid,'confirm_date':datetime.now()})  
        for x in val.penerimaan_line :
            if not x.no_notice and not x.no_stnk and not x.no_polisi:
              raise osv.except_osv(('Perhatian !'), ("Silahkan cek penerimaan, tidak ada data yg diterima !"))
            
            vals_lot = {'lokasi_stnk_id':val.lokasi_stnk_id.id}
            if not x.name.no_notice :
                if x.no_notice:
                  vals_lot['tgl_notice'] =  x.tgl_notice
                  vals_lot['no_notice'] = x.no_notice
                  vals_lot['tgl_terima_notice'] = val.tgl_terima
                
            if not x.name.no_stnk :
                if x['no_stnk'] :
                  vals_lot['tgl_stnk'] = x.tgl_stnk
                  vals_lot['no_stnk'] = x.no_stnk
                  vals_lot['tgl_terima_stnk'] = val.tgl_terima
                  
            if not x.name.no_polisi:
                if x['no_polisi']:
                  vals_lot['no_polisi'] = x.no_polisi
            
            if x.is_terima_nopol:
              if not x.name.tgl_terima_no_polisi:
                vals_lot['tgl_terima_no_polisi'] = val.tgl_terima
            
            lot_browse = lot_pool.browse(cr,uid,x.name.id)
            lot_browse.write(vals_lot)
                                      
        return True
    
    def create(self, cr, uid, vals, context=None):
        if not vals['penerimaan_line'] :
            raise osv.except_osv(('Perhatian !'), ("Tidak ada detail penerimaan. Data tidak bisa di save."))
        lot_pool = self.pool.get('stock.production.lot')
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'PST')
        vals['tgl_terima'] = self._get_default_date(cr, uid, context)        
        penerimaan_id = super(wtc_penerimaan_stnk, self).create(cr, uid, vals, context=context) 
        
        obj = self.browse(cr,uid,penerimaan_id)         
        for x in obj.penerimaan_line :
          if not x.no_notice and not x.no_stnk and not x.is_terima_nopol:
            raise osv.except_osv(('Perhatian !'), ("Silahkan cek penerimaan, tidak ada data yg diterima !"))
          
          if not x.name.no_notice:
              if x.no_notice:
                x.name.penerimaan_notice_id = penerimaan_id
          if not x.name.no_stnk:
              if x.no_stnk:
                x.name.penerimaan_stnk_id = penerimaan_id
          if not x.name.penerimaan_no_polisi_id:
              if x.is_terima_nopol:
                x.name.penerimaan_no_polisi_id = penerimaan_id                     
        return penerimaan_id

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        val = self.browse(cr,uid,ids)    
        penerimaan_pool = self.pool.get('wtc.penerimaan.stnk.line')
        lot_pool = self.pool.get('stock.production.lot')
        vals.get('penerimaan_line',[]).sort(reverse=True)
        
        lot = vals.get('penerimaan_line', False)
        
        if lot :
            del[vals['penerimaan_line']]
            for x,item in enumerate(lot) :
                lot_id = item[1]

                if item[0] == 2 :
                    id_lot = item[2]
                    search = penerimaan_pool.search(cr,uid,[
                                                            ('id','=',lot_id)
                                                            ])
                    if not search :
                        raise osv.except_osv(('Perhatian !'), ("Nomor Engine tidak ada didalam daftar"))
                    browse = penerimaan_pool.browse(cr,uid,search)
                     
                    lot_search = lot_pool.search(cr,uid,[
                       ('id','=',browse.name.id)
                       ])
                    if not lot_search :
                        raise osv.except_osv(('Perhatian !'), ("Nomor Engine tidak ada didalam daftar"))
                    lot_browse = lot_pool.browse(cr,uid,lot_search)

                    lot_browse.write({
                                       'penerimaan_notice_id':False,
                                       'penerimaan_stnk_id':False,
                                       'penerimaan_no_polisi_id':False,
                                       'tgl_notice': False,
                                       'no_notice':False,
                                       'tgl_stnk':False,
                                       'no_stnk':False,
                                       'no_polisi':False,
                                       'state_stnk':'proses_stnk',
                                       'lokasi_stnk_id':False,
                                     })
                    penerimaan_pool.unlink(cr,uid,lot_id, context=context)
                elif item[0] == 0 :
                    values = item[2]
                    lot_search = lot_pool.search(cr,uid,[
                                                        ('id','=',values['name'])
                                                        ])
                    if not lot_search :
                        raise osv.except_osv(('Perhatian !'), ("Nomor Engine tidak ada didalam daftar Engine Nomor"))
            
                
                    lot_browse = lot_pool.browse(cr,uid,lot_search)
                    
                    penerimaan_pool.create(cr, uid, {
                                    'name':lot_browse.id,
                                    'penerimaan_notice_id':val.id,
                                    'customer_stnk':lot_browse.customer_stnk.id,
                                    'tgl_notice':values['tgl_notice'],
                                    'no_notice':values['no_notice'],
                                    'tgl_stnk':values['tgl_stnk'],
                                    'no_stnk':values['no_stnk'],
                                    'no_polisi':values['no_polisi'],
                                    'is_terima_nopol':values['is_terima_nopol'],
                                    })
                    
                    if values['no_notice'] :
                        lot_browse.write({
                               'penerimaan_notice_id':val.id,
                               })   
                    if values['no_stnk'] :
                        lot_browse.write({
                               'penerimaan_stnk_id':val.id,  
                                                           }) 
                    if values['is_terima_nopol'] :
                        lot_browse.write({
                               'penerimaan_no_polisi_id':val.id,
                                          })
                elif item[0] == 1 :
                    data = item[2]
                    penerimaan_search = penerimaan_pool.search(cr,uid,[
                                                                       ('id','=',lot_id)
                                                                       ])
                    penerimaan_browse = penerimaan_pool.browse(cr,uid,penerimaan_search)
                    if penerimaan_search :
                        if 'no_polisi' in data :
                            penerimaan_browse.write({
                                                     'no_polisi':data['no_polisi']
                                                     })
                        elif 'no_stnk' in data :
                            penerimaan_browse.write({
                                                     'tgl_stnk':data['tgl_stnk'],
                                                     'no_stnk':data['no_stnk'],
                                                     })
                                                        
        return super(wtc_penerimaan_stnk, self).write(cr, uid, ids, vals, context=context) 

    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Penerimaan Faktur sudah di validate ! tidak bisa didelete !"))

        lot_pool = self.pool.get('stock.production.lot')

        for x in self.browse(cr, uid, ids, context=context):
            for y in x.penerimaan_line :
                lot_search = lot_pool.search(cr,uid,[
                                                     ('id','=',y.name.id)
                                                     ])
                if lot_search :
                    vals_lot = {'lokasi_stnk_id': False}
                    lot_browse = lot_pool.browse(cr,uid,lot_search)
                    if y.no_notice :
                        vals_lot['no_notice'] = False
                        vals_lot['tgl_notice'] = False
                        vals_lot['tgl_terima_notice'] = False
                    if y.no_stnk :
                        vals_lot['no_stnk'] = False
                        vals_lot['tgl_stnk'] = False
                        vals_lot['tgl_terima_stnk'] = False
                    if y.no_polisi or y.is_terima_nopol:
                        vals_lot['no_polisi'] = False
                        vals_lot['tgl_terima_no_polisi'] = False
                    lot_browse.write(vals_lot)
        return super(wtc_penerimaan_stnk, self).unlink(cr, uid, ids, context=context)

        
class wtc_penerimaan_stnk_line(osv.osv):
    _name = "wtc.penerimaan.stnk.line"
    _columns = {
                'name' : fields.many2one('stock.production.lot','No Engine',domain="['|',('create_date','=','2015-09-30 00:00:00'),('tgl_proses_stnk','!=',False),('state_stnk','=','proses_stnk'),('branch_id','=',parent.branch_id),('biro_jasa_id','=',parent.partner_id),'|',('tgl_terima_stnk','=',False),'|',('tgl_terima_no_polisi','=',False),('tgl_terima_notice','=',False)]",change_default=True,),
                'penerimaan_notice_id' : fields.many2one('wtc.penerimaan.stnk','Penerimaan Notice'),
                'customer_stnk':fields.related('name','customer_stnk',type='many2one',relation='res.partner',readonly=True,string='Customer STNK'),
                'tgl_notice' : fields.date('Tgl JTP Notice'),
                'no_notice' : fields.char('No Notice'),
                'tgl_stnk' : fields.date('Tgl JTP STNK'),
                'no_stnk' : fields.char('No STNK'),
                'no_polisi' : fields.char('No Polisi'),
                'is_terima_nopol':fields.boolean('Terima Plat?')
                }
    _sql_constraints = [
    ('unique_name_penerimaan_notice_id', 'unique(name,penerimaan_notice_id)', 'Detail Engine duplicate, mohon cek kembali !'),
]      
    def onchange_no_polisi(self,cr,uid,ids,no_polisi,context=None):
        if no_polisi :
            no_polisi = no_polisi.replace(' ', '').upper()
            
            return {
                    'value' : {'no_polisi':no_polisi}
                    }

    def onchange_no_notice(self,cr,uid,ids,no_notice,context=None):
        if no_notice :
            no_notice = no_notice.replace(' ', '').upper()
            
            return {
                    'value' : {'no_notice':no_notice}
                    }
            
    def onchange_no_stnk(self,cr,uid,ids,no_stnk,context=None):
        if no_stnk :
            no_stnk = no_stnk.replace(' ', '').upper()
            
            return {
                    'value' : {'no_stnk':no_stnk}
                    }
            
    def onchange_engine(self, cr, uid, ids, name,branch_id,division):
        if not branch_id or not division:
            raise osv.except_osv(('No Branch Defined!'), ('Sebelum menambah detil transaksi,\n harap isi branch dan division terlebih dahulu.'))
       
        result = {}
        warning = {}
        value = {}
        val = self.browse(cr,uid,ids)
        lot_obj = self.pool.get('stock.production.lot')
        lot_search = lot_obj.search(cr,uid,[
                                              ('id','=',name)
                                              ])
        lot_browse = lot_obj.browse(cr,uid,lot_search)  
        
        if name : 
            if lot_browse.penerimaan_notice_id.id != False and lot_browse.tgl_notice == False:
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('No Engine \'%s\' telah diproses dengan no penerimaan \'%s\' mohon post atau cancel terlebih dahulu, atau hapus dari detail penerimaan ! ') % (lot_browse.name,lot_browse.penerimaan_notice_id.name)),
                }
                value = {
                         'name':False,
                         }
                    
            elif lot_browse.penerimaan_stnk_id.id != False and lot_browse.tgl_stnk == False :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('No STNK Engine \'%s\' telah diproses dengan no penerimaan \'%s\' mohon post atau cancel terlebih dahulu, atau hapus dari detail penerimaan ! ') % (lot_browse.name,lot_browse.penerimaan_stnk_id.name)),
                }
                value = {
                         'name':False,
                         }  
            elif lot_browse.penerimaan_no_polisi_id.id != False and lot_browse.tgl_terima_no_polisi == False :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('No Polisi Engine \'%s\' telah diproses dengan no penerimaan \'%s\' mohon post atau cancel terlebih dahulu, atau hapus dari detail penerimaan ! ') % (lot_browse.name,lot_browse.penerimaan_no_polisi_id.name)),
                }
                value = {
                         'name':False,
                         } 
   
            if not warning :
                if lot_browse.no_notice_copy == False :
        
                    value = {
                             'customer_stnk':lot_browse.customer_stnk.id,
                             'tgl_notice':lot_browse.tgl_notice,
                             'no_notice':lot_browse.no_notice,
                             'tgl_stnk':lot_browse.tgl_stnk,
                             'no_stnk':lot_browse.no_stnk,
                             'no_polisi':lot_browse.no_polisi,
                             }
        
                elif lot_browse.no_notice_copy :
                    value = {
                             'customer_stnk':lot_browse.customer_stnk.id,
                             'tgl_notice':lot_browse.tgl_notice_copy,
                             'no_notice':lot_browse.no_notice_copy,
                             'tgl_stnk':lot_browse.tgl_stnk,
                             'no_stnk':lot_browse.no_stnk,
                             'no_polisi':lot_browse.no_polisi,
                             }

            result['value'] = value
            result['warning'] = warning 
        return result
