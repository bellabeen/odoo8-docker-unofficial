import time
from datetime import datetime
from openerp.osv import fields, osv
from string import whitespace

class wtc_penerimaan_bpkb(osv.osv):
    _name = "wtc.penerimaan.bpkb"
    _order = "tgl_terima desc,id desc"
    
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
        
    def _get_default_date(self,cr,uid,context=None):
        return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)
    

    def print_report_pdf_penerimaan_bpkb(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = self.read(cr, uid, ids,context=context)[0]

        return self.pool['report'].get_action(cr, uid, [], 'wtc_proses_stnk.wtc_penerimaan_bpkb_report', data=data, context=context)
        

    _columns = {
        'branch_id': fields.many2one('wtc.branch', string='Branch', required=True),
        'division':fields.selection([('Unit','Unit')], 'Division', change_default=True, select=True),
        'name': fields.char('No Reference',size=20, readonly=True),
        'state': fields.selection([('draft', 'Draft'), ('posted','Posted'),('cancel','Canceled')], 'State', readonly=True),
        'penerimaan_line': fields.one2many('wtc.penerimaan.bpkb.line','penerimaan_bpkb_id',string="Table Penerimaan BPKB"), 
        'partner_id':fields.many2one('res.partner','Biro Jasa',domain=[('biro_jasa','=',True)]),
        'tgl_terima' : fields.date('Tanggal'),
        'lokasi_bpkb_id' : fields.many2one('wtc.lokasi.bpkb',string="Lokasi",domain="[('branch_id','=',branch_id),('type','=','internal')]"),
        'engine_no': fields.related('penerimaan_line', 'name', type='char', string='No Engine'),
        'customer_stnk': fields.related('penerimaan_line','customer_stnk', type='many2one', relation='res.partner', string='Customer STNK'),
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
                        ('state_stnk','=','proses_stnk'),
                        ('tgl_terima_bpkb','=',val.tgl_terima),
                        ('no_bpkb','=',x.no_bpkb),
                        ('lokasi_bpkb_id','=',val.lokasi_bpkb_id.id),
                        ('id','=',x.name.id)
                        ])
            if not lot_search :
                raise osv.except_osv(('Perhatian !'), ("No Engine Tidak Ditemukan."))
            if lot_search :
                lot_browse = lot_pool.browse(cr,uid,lot_search)
                lot_browse.write({
                                  'penerimaan_bpkb_id': False,
                                  'tgl_terima_bpkb':False,
                                  'tgl_bpkb':False,
                                  'no_bpkb':False,
                                  'lokasi_bpkb_id':False,
                                  'no_urut_bpkb':False
                                })
        self.write(cr, uid, ids, {'state': 'cancel','cancel_uid':uid,'cancel_date':datetime.now()})
        return True
    
    def post_penerimaan(self,cr,uid,ids,context=None):
        val = self.browse(cr,uid,ids)
        lot_pool = self.pool.get('stock.production.lot') 
        tanggal = self._get_default_date(cr, uid, context)
        self.write(cr, uid, ids, {'state': 'posted','tgl_terima':tanggal,'confirm_uid':uid,'confirm_date':datetime.now()})               
        for x in val.penerimaan_line :
            lot_search = lot_pool.search(cr,uid,[
                ('id','=',x.name.id)
                ])
            lot_browse = lot_pool.browse(cr,uid,lot_search)
            lot_browse.write({
                   'no_bpkb':x.no_bpkb,
                   'tgl_bpkb': x.tgl_bpkb,
                   'tgl_terima_bpkb':val.tgl_terima,
                   'no_urut_bpkb':x.no_urut_bpkb,
                   'lokasi_bpkb_id':val.lokasi_bpkb_id.id
                   })   
        return True
    
    def create(self, cr, uid, vals, context=None):
        if not vals['penerimaan_line'] :
            raise osv.except_osv(('Perhatian !'), ("Tidak ada detail penerimaan. Data tidak bisa di save."))
        lot_penerimaan = []
        for x in vals['penerimaan_line']:
            lot_penerimaan.append(x.pop(2))
        lot_pool = self.pool.get('stock.production.lot')
        penerimaan_pool = self.pool.get('wtc.penerimaan.bpkb.line')
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'PSB')
        
        vals['tgl_terima'] = self._get_default_date(cr, uid, context)
        del[vals['penerimaan_line']]

        
        penerimaan_id = super(wtc_penerimaan_bpkb, self).create(cr, uid, vals, context=context) 

        if penerimaan_id :         
            for x in lot_penerimaan :
                lot_search = lot_pool.search(cr,uid,[
                            ('id','=',x['name'])
                            ])
                lot_browse = lot_pool.browse(cr,uid,lot_search)
                lot_browse.write({
                       'penerimaan_bpkb_id':penerimaan_id,
                       })   
                no_urut = penerimaan_pool.get_no_urut(cr,uid,vals['branch_id'],context)
                penerimaan_pool.create(cr, uid, {
                                                     'name':lot_browse.id,
                                                     'penerimaan_bpkb_id':penerimaan_id,
                                                     'customer_stnk':lot_browse.customer_stnk.id,
                                                     'tgl_bpkb':x['tgl_bpkb'],
                                                     'no_bpkb':x['no_bpkb'],
                                                     'lokasi_bpkb_id':vals['lokasi_bpkb_id'],
                                                     'no_urut_bpkb':no_urut
                                                    })
                           
        else :
            return False
        return penerimaan_id

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        vals.get('penerimaan_line',[]).sort(reverse=True)
        collect = self.browse(cr,uid,ids)
        lot_penerimaan = []
        lot_pool = self.pool.get('stock.production.lot')
        line_pool = self.pool.get('wtc.penerimaan.bpkb.line')
        lot = vals.get('penerimaan_line', False)

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
                    del[vals['penerimaan_line']]
                    lot_browse.write({
                                   'penerimaan_bpkb_id':False,
                                   'tgl_bpkb':False,
                                   'no_bpkb':False,
                                   'lokasi_bpkb_id':False,
                                   'no_urut_bpkb':False,
                                   'tgl_terima_bpkb':False
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
                           'penerimaan_bpkb_id':collect.id,
                           }) 
        write_method = super(wtc_penerimaan_bpkb, self).write(cr, uid, ids, vals, context=context) 
        value = self.browse(cr,uid,ids)       
        penerimaan_bpkb_line = line_pool.search(cr,uid,[
                                                        ('penerimaan_bpkb_id','=',value.id)
                                                        ])
        penerimaan_bpkb_line_brw = line_pool.browse(cr,uid,penerimaan_bpkb_line)
        for x in penerimaan_bpkb_line_brw :
            if not x.no_urut_bpkb :
                no_urut = line_pool.get_no_urut(cr,uid,collect.branch_id.id,context)     
                x.write({'no_urut_bpkb':no_urut})
        return write_method

    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Penerimaan BPKB sudah di post ! tidak bisa didelete !"))

        lot_pool = self.pool.get('stock.production.lot')
        lot_search = lot_pool.search(cr,uid,[
                                           ('penerimaan_bpkb_id','=',ids)
                                           ])
        lot_browse = lot_pool.browse(cr,uid,lot_search)
        for x in lot_browse :
            x.write({
                     'no_bpkb': False,
                     'tgl_bpkb':False,
                     'tgl_terima_bpkb':False,
                     'lokasi_bpkb_id':False,
                     'no_urut_bpkb':False
                     })
        return super(wtc_penerimaan_bpkb, self).unlink(cr, uid, ids, context=context)

        
class wtc_penerimaan_bpkb_line(osv.osv):
    _name = "wtc.penerimaan.bpkb.line"
    _columns = {
                'name' : fields.many2one('stock.production.lot','No Engine',domain="['|',('create_date','=','2015-09-30 00:00:00'),('tgl_proses_stnk','!=',False),('state_stnk','=','proses_stnk'),('branch_id','=',parent.branch_id),('biro_jasa_id','=',parent.partner_id),('no_bpkb','=',False),('penerimaan_bpkb_id','=',False)]",change_default=True,),
                'penerimaan_bpkb_id' : fields.many2one('wtc.penerimaan.bpkb','Penerimaan BPKB'),
                'customer_stnk':fields.related('name','customer_stnk',type='many2one',relation='res.partner',readonly=True,string='Customer STNK'),
                'tgl_bpkb' : fields.date('Tgl Jadi BPKB'),
                'no_bpkb' : fields.char('No BPKB'),
                'no_urut_bpkb' : fields.char('No Urut')
                }
    _sql_constraints = [
    ('unique_name_penerimaan_bpkb_id', 'unique(name,penerimaan_bpkb_id)', 'Detail Engine duplicate, mohon cek kembali !'),
]
    def get_no_urut(self,cr,uid,branch_id,context=None) :
        doc_code = self.pool.get('wtc.branch').browse(cr, uid, branch_id).doc_code
        seq_name = 'BP'
        seq = self.pool.get('ir.sequence')
        ids = seq.search(cr, uid, [('name','=',seq_name)])
        if not ids:
            prefix = seq_name
            ids = seq.create(cr, uid, {'name':seq_name,
                                 'implementation':'no_gap',
                                 'prefix':prefix,
                                 'padding':8})
        return seq.get_id(cr, uid, ids)
        
    def onchange_engine(self, cr, uid, ids, name,branch_id,division):
        if not branch_id or not division:
            raise osv.except_osv(('No Branch Defined!'), ('Sebelum menambah detil transaksi,\n harap isi branch dan division terlebih dahulu.'))
       
        value = {}
        lot_obj = self.pool.get('stock.production.lot')
        lot_search = lot_obj.search(cr,uid,[
                                                  ('id','=',name)
                                                  ])
        if lot_search :
            lot_browse = lot_obj.browse(cr,uid,lot_search)          
            value = {
                     'customer_stnk':lot_browse.customer_stnk.id,
                     }        
        return {'value':value}

    def onchange_no_bpkb(self,cr,uid,ids,no_bpkb,context=None):
        if no_bpkb :
            no_bpkb = no_bpkb.replace(' ', '').upper()
            
            return {
                    'value' : {'no_bpkb':no_bpkb}
                    }
