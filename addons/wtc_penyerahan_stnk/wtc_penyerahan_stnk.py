import time
from datetime import datetime
from openerp.osv import fields, osv

class wtc_penyerahan_stnk(osv.osv):
    _name = "wtc.penyerahan.stnk"
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
                'partner_id':fields.many2one('res.partner','Customer',domain=[('customer','=',True)]),
                'keterangan':fields.char('Keterangan'),
                'tanggal':fields.date('Tanggal'),
                'penyerahan_line' : fields.one2many('wtc.penyerahan.stnk.line','penyerahan_id',string="Penyerahan STNK"),  
                'state': fields.selection([('draft', 'Draft'), ('posted','Posted'),('cancel','Canceled')], 'State', readonly=True),
                'engine_no': fields.related('penyerahan_line', 'name', type='char', string='No Engine'),
                'customer_stnk': fields.related('penyerahan_line', 'customer_stnk', type='many2one', relation='res.partner', string='Customer STNK'),
                'no_stnk': fields.related('penyerahan_line', 'no_stnk', type='char', string='No STNK'),
                'confirm_uid':fields.many2one('res.users',string="Posted by"),
                'confirm_date':fields.datetime('Posted on'),
                'cancel_uid':fields.many2one('res.users',string="Cancelled by"),
                'cancel_date':fields.datetime('Cancelled on'),                      
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
        branch= val.branch_id
        warning = ""



        for x in val.penyerahan_line :
            lot_browse = x.name 
            vals = {}
            if (lot_browse.inv_pengurusan_stnk_bpkb_id and lot_browse.inv_pengurusan_stnk_bpkb_id.state!='paid') or (lot_browse.inv_pajak_progressive_id and lot_browse.inv_pajak_progressive_id.state!='paid' and branch.pajak_progressive):
                warning += "Tidak bisa proses, invoice pajak progressive %s belum dibayar!" %(lot_browse.name)
                
            if not lot_browse.tgl_penyerahan_stnk :
                if x.tgl_ambil_stnk :
                    vals['tgl_penyerahan_stnk'] = x.tgl_ambil_stnk
                    # lot_browse.write({
                    #        'tgl_penyerahan_stnk':x.tgl_ambil_stnk,
                    #        })  
            if not lot_browse.tgl_penyerahan_plat :
                if x.tgl_ambil_polisi :
                    vals['tgl_penyerahan_plat'] = x.tgl_ambil_polisi
                    # lot_browse.write({
                    #        'tgl_penyerahan_plat':x.tgl_ambil_polisi,
                    #        })
            if not lot_browse.tgl_penyerahan_notice :
                if x.tgl_ambil_notice :
                    vals['tgl_penyerahan_notice'] = x.tgl_ambil_notice
                    # lot_browse.write({
                    #        'tgl_penyerahan_notice':x.tgl_ambil_notice,
                    #        })
            if lot_browse.tgl_penyerahan_stnk and lot_browse.tgl_penyerahan_notice and lot_browse.tgl_penyerahan_plat: 
                vals['lokasi_stnk_id'] = False
                # lot_browse.write({
                #    'lokasi_stnk_id':False
                # }) 
            lot_browse.write(vals)                   
        if warning != "":
            raise osv.except_osv(("Perhatian !"), warning)
       
        return True
    
    def create(self, cr, uid, vals, context=None):
        if not vals['penyerahan_line'] :
            raise osv.except_osv(('Perhatian !'), ("Tidak ada detail penyerahan. Data tidak bisa di save."))
        lot_penyerahan = []
        for x in vals['penyerahan_line']:
            lot_penyerahan.append(x.pop(2))
        lot_pool = self.pool.get('stock.production.lot')
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'ENCS')
        vals['tanggal'] = self._get_default_date(cr, uid, context=context)

        for y in lot_penyerahan :
            id = y['name']
            engine = self.pool.get('stock.production.lot').browse(cr,uid,[id])
            if y['tgl_ambil_stnk']:       
                if not engine.no_stnk :     
                    raise osv.except_osv(('Perhatian !'), ("No STNK belum diterima, tidak bisa input tanggal ambil STNK"))
            if y['tgl_ambil_polisi']:
                if not engine.no_polisi :
                    raise osv.except_osv(('Perhatian !'), ("No Polisi belum diterima, tidak bisa input tanggal ambil Plat"))                
                
        del[vals['penyerahan_line']]        
        penyerahan_id = super(wtc_penyerahan_stnk, self).create(cr, uid, vals, context=context) 

        if penyerahan_id :         
            for x in lot_penyerahan :
                lot_search = lot_pool.search(cr,uid,[
                            ('id','=',x['name'])
                            ])
                lot_browse = lot_pool.browse(cr,uid,lot_search)
 
                penyerahan_pool = self.pool.get('wtc.penyerahan.stnk.line')
                penyerahan_pool.create(cr, uid, {
                                                    'name':lot_browse.id,
                                                    'penyerahan_id':penyerahan_id,
                                                    'customer_stnk':lot_browse.customer_stnk.id,
                                                    'no_stnk':lot_browse.no_stnk,
                                                    'no_polisi':lot_browse.no_polisi,
                                                    'no_notice':lot_browse.no_notice,
                                                    'tgl_ambil_stnk':x.get('tgl_ambil_stnk'),
                                                    'tgl_ambil_polisi':x.get('tgl_ambil_polisi'),
                                                    'tgl_ambil_notice':x.get('tgl_ambil_notice')
                                                    })  
                res = {}                
                if not lot_browse.tgl_penyerahan_stnk :
                    if x['tgl_ambil_stnk'] :
                        res['penyerahan_stnk_id'] = penyerahan_id
                        # lot_browse.write({
                        #        'penyerahan_stnk_id':penyerahan_id,
                        #        }) 
                
                if not lot_browse.tgl_penyerahan_plat :
                    if x['tgl_ambil_polisi'] :
                        res['penyerahan_polisi_id'] = penyerahan_id
                        # lot_browse.write({
                        #        'penyerahan_polisi_id':penyerahan_id,
                        #                   })
                if not lot_browse.tgl_penyerahan_notice :
                    if x['tgl_ambil_notice'] :
                        res['penyerahan_notice_id'] = penyerahan_id
                        # lot_browse.write({
                        #        'penyerahan_notice_id':penyerahan_id,
                        #                   })                        
                lot_browse.write(res)           
        else :
            return False
        return penyerahan_id

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        vals.get('penyerahan_line',[]).sort(reverse=True)            
        val = self.browse(cr,uid,ids)    
        penyerahan_pool = self.pool.get('wtc.penyerahan.stnk.line')
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
                                       'penyerahan_stnk_id':False,
                                       'penyerahan_polisi_id':False,
                                       'penyerahan_notice_id':False,
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
                                    'no_stnk':lot_browse.no_stnk,
                                    'no_polisi':lot_browse.no_polisi,
                                    'no_notice':lot_browse.no_notice,
                                    'tgl_ambil_stnk':values['tgl_ambil_stnk'],
                                    'tgl_ambil_polisi':values['tgl_ambil_polisi'],
                                    'tgl_ambil_notice':values['tgl_ambil_notice']
                                    })
                    res={}
                    if values['tgl_ambil_stnk'] :
                        res['penyerahan_stnk_id'] = val.id
                        # lot_browse.write({
                        #        'penyerahan_stnk_id':val.id,  
                        #                                    }) 
                    if values['tgl_ambil_polisi'] :
                        res['penyerahan_polisi_id'] = val.id
                        # lot_browse.write({
                        #        'penyerahan_polisi_id':val.id,
                        #                   })
                    if values['tgl_ambil_notice'] :
                        res['penyerahan_notice_id'] = val.id
                        # lot_browse.write({    
                        #        'penyerahan_notice_id':val.id,
                        #                   })           
                    lot_browse.write(res)             
                elif item[0] == 1 :
                    data = item[2]
                    penyerahan_search = penyerahan_pool.search(cr,uid,[
                                                                       ('id','=',lot_id)
                                                                       ])
                    penyerahan_browse = penyerahan_pool.browse(cr,uid,penyerahan_search)
                    res={}
                    if penyerahan_search :
                        if 'tgl_ambil_stnk' in data :
                            res['tgl_ambil_stnk'] = data['tgl_ambil_stnk']
                            # penyerahan_browse.write({
                            #                          'tgl_ambil_stnk':data['tgl_ambil_stnk']
                            #                          })
                        elif 'tgl_ambil_polisi' in data :
                            res['tgl_ambil_polisi'] = data['tgl_ambil_polisi']
                            # penyerahan_browse.write({
                            #                          'tgl_ambil_polisi':data['tgl_ambil_polisi'],
                            #                          })
                        elif 'tgl_ambil_notice' in data :
                             res['tgl_ambil_notice'] = data['tgl_ambil_notice']
                            # penyerahan_browse.write({
                            #                          'tgl_ambil_notice':data['tgl_ambil_notice'],
                            #                          })                            
                        penyerahan_browse.write(res)
        return super(wtc_penyerahan_stnk, self).write(cr, uid, ids, vals, context=context) 

    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Penyerahan STNK/No Polisi sudah di validate ! tidak bisa didelete !"))

        lot_pool = self.pool.get('stock.production.lot')

        for x in self.browse(cr, uid, ids, context=context):
            for y in x.penyerahan_line :
                lot_search = lot_pool.search(cr,uid,[
                                                     ('id','=',y.name.id)
                                                     ])
                if lot_search :
                    lot_browse = lot_pool.browse(cr,uid,lot_search)
                    if y.no_stnk :
                        lot_browse.write({
                                          'penyerahan_stnk_id':False,
                                          'tgl_penyerahan_stnk':False,})     
                    if y.no_polisi :
                        lot_browse.write({
                                          'penyerahan_polisi_id':False,
                                          'tgl_penyerahan_plat':False})                        

        return super(wtc_penyerahan_stnk, self).unlink(cr, uid, ids, context=context)    
    
      
class wtc_penyerahan_stnk_line(osv.osv):
    _name = "wtc.penyerahan.stnk.line"
    _columns = {
                'name' : fields.many2one('stock.production.lot','No Engine',change_default=True,),                
                'penyerahan_id' : fields.many2one('wtc.penyerahan.stnk','Penyerahan STNK'),
                'customer_stnk':fields.related('name','customer_stnk',type='many2one',relation='res.partner',readonly=True,string='Customer STNK'),
                'no_stnk' : fields.related('name','no_stnk',type="char",readonly=True,string='No STNK'),
                'no_polisi' : fields.related('name','no_polisi',type="char",readonly=True,string='No Polisi'),
                'tgl_ambil_stnk' : fields.date('Tgl Ambil STNK'),
                'tgl_ambil_polisi' : fields.date('Tgl Ambil No Polisi'),
                'no_notice' : fields.related('name','no_notice',type="char",readonly=True,string='No Notice'),
                'tgl_ambil_notice' : fields.date('Tgl Ambil Notice'),
                
                
                }
    _sql_constraints = [
    ('unique_name_penyerahan_id', 'unique(name,penyerahan_id)', 'Detail Engine duplicate, mohon cek kembali !'),
]
    def onchange_engine(self, cr, uid, ids, name,branch_id,division,customer,penerima_stnk):
        if not branch_id or not division or not penerima_stnk:
            raise osv.except_osv(('Perhatian !'), ('Sebelum menambah detil transaksi,\n harap isi branch, division, peneriman STNK terlebih dahulu.'))
    
        value = {}
        domain = {}
        result = {}
        message = {}
        branch=self.pool.get('wtc.branch').browse(cr,uid,branch_id)

        if customer :
            if branch.pajak_progressive:
                domain['name'] ="['|',('create_date','=','2015-09-30 00:00:00'),('proses_biro_jasa_id','!=',False),('state_stnk','=','proses_stnk'),('lokasi_stnk_id.branch_id','=',parent.branch_id),('customer_id','=',parent.partner_id),'|',('tgl_terima_notice','!=',False),('tgl_terima_stnk','!=',False),'|',('tgl_penyerahan_stnk','=',False),('tgl_penyerahan_plat','=',False)]"
            else:
                domain['name'] ="['|',('create_date','=','2015-09-30 00:00:00'),('state_stnk','=','proses_stnk'),('lokasi_stnk_id.branch_id','=',parent.branch_id),('customer_id','=',parent.partner_id),'|',('tgl_terima_notice','!=',False),('tgl_terima_stnk','!=',False),'|',('tgl_penyerahan_stnk','=',False),('tgl_penyerahan_plat','=',False)]"
        elif not customer :
            if branch.pajak_progressive:
                domain['name'] ="['|',('create_date','=','2015-09-30 00:00:00'),('proses_biro_jasa_id','!=',False),('state_stnk','=','proses_stnk'),('lokasi_stnk_id.branch_id','=',parent.branch_id),'|',('tgl_terima_notice','!=',False),('tgl_terima_stnk','!=',False),'|',('tgl_penyerahan_stnk','=',False),('tgl_penyerahan_plat','=',False)]"
            else:
                domain['name'] ="['|',('create_date','=','2015-09-30 00:00:00'),('state_stnk','=','proses_stnk'),('lokasi_stnk_id.branch_id','=',parent.branch_id),'|',('tgl_terima_notice','!=',False),('tgl_terima_stnk','!=',False),'|',('tgl_penyerahan_stnk','=',False),('tgl_penyerahan_plat','=',False)]"
               
        if name :
            lot_obj = self.pool.get('stock.production.lot')
            lot_browse = lot_obj.browse(cr,uid,name)
            if (lot_browse.inv_pengurusan_stnk_bpkb_id and lot_browse.inv_pengurusan_stnk_bpkb_id.state!='paid') or  (lot_browse.inv_pajak_progressive_id and lot_browse.inv_pajak_progressive_id.state!='paid' and branch.pajak_progressive):
                 value = {
                          'name': False
                          }
                 message = {'title':'Perhatian !','message':'Tidak bisa proses, invoice pajak progressive "%s" belum dibayar!' % (lot_browse.name)} 
                        
            else:
                value = {
                         'customer_stnk':lot_browse.customer_stnk.id,
                         'no_stnk':lot_browse.no_stnk,
                         'no_polisi':lot_browse.no_polisi,
                         'tgl_ambil_stnk':lot_browse.tgl_penyerahan_stnk,
                         'tgl_ambil_polisi':lot_browse.tgl_penyerahan_plat,
                         'no_notice':lot_browse.no_notice,
                         'tgl_ambil_notice':lot_browse.tgl_penyerahan_notice,
                         }  

        return {'domain':domain,'value':value, 'warning':message}