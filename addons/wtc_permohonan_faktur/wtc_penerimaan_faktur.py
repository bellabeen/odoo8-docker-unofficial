import time
from datetime import datetime
from openerp.osv import fields, osv

class wtc_penerimaan_faktur(osv.osv):
    _name = "wtc.penerimaan.faktur"
    _order = "tgl_terima desc"
    
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
        'state': fields.selection([('draft', 'Draft'), ('posted','Posted'),('cancel','Canceled')], 'State', readonly=True),
        'penerimaan_line': fields.one2many('wtc.penerimaan.faktur.line','penerimaan_faktur_id',string="Table Permintaan Faktur"), 
        'partner_id':fields.related('branch_id','default_supplier_id',type='many2one',relation='res.partner',readonly=True,string='Supplier'),
        'ahm_code':fields.related('branch_id','ahm_code',type='char',readonly=True,string='AHM Code'),
        'tgl_terima' : fields.date('Tanggal'),
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

    def onchange_branch_penerimaan_faktur(self, cr, uid, ids, branch_id):
        branch_obj = self.pool.get('wtc.branch')
        branch_search = branch_obj.search(cr,uid,[
                                                  ('id','=',branch_id)
                                                  ])
        branch_browse = branch_obj.browse(cr,uid,branch_search)   
        return {'value':{'partner_id':branch_browse.default_supplier_id.id,'ahm_code':branch_browse.ahm_code}}
    
    def cancel_penerimaan(self,cr,uid,ids,context=None):
        self.write(cr, uid, ids, {'state': 'cancel','cancel_uid':uid,'cancel_date':datetime.now()})        
        val = self.browse(cr,uid,ids)  
        lot_pool = self.pool.get('stock.production.lot') 
        for x in val.penerimaan_line :
            lot_search = lot_pool.search(cr,uid,[
                        ('branch_id','=',val.branch_id.id),
                        ('penerimaan_faktur_id','=',val.id),
                        ('id','=',x.name.id)
                        ])
            if not lot_search :
                raise osv.except_osv(('Perhatian !'), ("No Engine Tidak Ditemukan."))
            if lot_search :
                lot_browse = lot_pool.browse(cr,uid,lot_search)
                if lot_browse.proses_stnk_id or lot_browse.penerimaan_notice_id or lot_browse.penerimaan_stnk_id or lot_browse.penerimaan_bpkb_id or lot_browse.proses_biro_jasa_id :
                    raise osv.except_osv(('Perhatian !'), ("No faktur engine \'%s\' telah diproses, data tidak bisa di cancel !")%(lot_browse.name))                    
                else : 
                    lot_browse.write({'state_stnk': 'mohon_faktur','tgl_terima':False,'penerimaan_faktur_id':False,'faktur_stnk':False,'tgl_cetak_faktur':False})
        return True
    
    def post_penerimaan(self,cr,uid,ids,context=None):
        val = self.browse(cr,uid,ids)
        lot_pool = self.pool.get('stock.production.lot') 
        tanggal = self._get_default_date(cr, uid, context=context)
        self.write(cr, uid, ids, {'state': 'posted','tgl_terima':tanggal,'confirm_uid':uid,'confirm_date':datetime.now()})               
        for x in val.penerimaan_line :
            x.name.write({
                   'state_stnk':'terima_faktur',
                   'tgl_cetak_faktur': x.tgl_cetak_faktur,
                   'faktur_stnk':x.faktur_stnk,
                   'tgl_terima':val.tgl_terima,
                   'penerimaan_faktur_id': val.id,
                   }) 
            x.write({'state':'posted',})  
        return True
 
    def _check_double_entries(self,cr,uid,lot_id):
        line_obj = self.pool.get('wtc.penerimaan.faktur.line')
        line_search = line_obj.search(cr,uid,[('name','=',lot_id)])
        if line_search:
            lines = line_obj.browse(cr,uid,line_search)
            for x in lines:
                if x.state!='cancel':
                    raise osv.except_osv(('Perhatian !'), ("Nomor mesin %s sudah diinput di penerimaan faktur %s") % (x.name.name,x.penerimaan_faktur_id.name))
    
    def create(self, cr, uid, vals, context=None):
        if not vals['penerimaan_line'] :
            raise osv.except_osv(('Perhatian !'), ("Tidak ada detail penerimaan. Data tidak bisa di save."))
        lot_penerimaan = []
        lot_pool = self.pool.get('stock.production.lot')
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'TF')
        vals['tgl_terima'] = self._get_default_date(cr, uid, context=context)
        for x in vals['penerimaan_line']:
            self._check_double_entries(cr,uid,x[2]['name'])
        penerimaan_id = super(wtc_penerimaan_faktur, self).create(cr, uid, vals, context=context) 
        return penerimaan_id

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        vals.get('penerimaan_line',[]).sort(reverse=True)

        collect = self.browse(cr,uid,ids)
        lot_penerimaan = []
        lot_pool = self.pool.get('stock.production.lot')
        line_pool = self.pool.get('wtc.penerimaan.faktur.line')

        lot = vals.get('penerimaan_line', False)
        if lot :
            for x,item in enumerate(lot) :
                lot_id = item[1]
                if item[0] in (0,1):
                    self._check_double_entries(cr, uid, item[2]['name'])
        return super(wtc_penerimaan_faktur, self).write(cr, uid, ids, vals, context=context) 

    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Penerimaan Faktur sudah di post ! tidak bisa didelete !"))
        return super(wtc_penerimaan_faktur, self).unlink(cr, uid, ids, context=context)
    
        
class wtc_penerimaan_faktur_line(osv.osv):
    _name = "wtc.penerimaan.faktur.line"
    _columns = {
                'name' : fields.many2one('stock.production.lot','No Engine',domain="['|',('create_date','=','2015-09-30 00:00:00'),('penerimaan_faktur_id','=',False),('tgl_faktur','!=',False),('state_stnk','=','mohon_faktur'),('branch_id','=',parent.branch_id)]"),
                'penerimaan_faktur_id' : fields.many2one('wtc.penerimaan.faktur','Penerimaan Faktur'),
                'customer_stnk':fields.related('name','customer_stnk',type='many2one',relation='res.partner',readonly=True,string='Customer STNK'),
                'tgl_cetak_faktur' : fields.date('Tanggal Cetak',required=True),
                'faktur_stnk' : fields.char('No Faktur STNK',required=True),
                'chassis_no':fields.related('name','chassis_no',type='char',readonly=True,string='No Chassis'),
                'state': fields.selection([('cancel','Canceled'), ('posted','Posted')],'State'),
                }
    _sql_constraints = [
    ('unique_name_penerimaan_faktur_id', 'unique(name,penerimaan_faktur_id)', 'Detail Engine duplicate, mohon cek kembali !'),
]      
    def onchange_engine(self, cr, uid, ids, name):
        lot_obj = self.pool.get('stock.production.lot')
        lot_browse = lot_obj.browse(cr,uid,name)   
        return {
                'value':{
                         'chassis_no':lot_browse.chassis_no,
                         'customer_stnk':lot_browse.customer_stnk.id,
                         'tgl_cetak_faktur':lot_browse.tgl_cetak_faktur,
                         'faktur_stnk':lot_browse.faktur_stnk if lot_browse.faktur_stnk else lot_browse.no_faktur 
                         }
                }
    
    def onchange_faktur_stnk(self,cr,uid,ids,faktur_stnk,context=None):
        if faktur_stnk :
            faktur_stnk = faktur_stnk.replace(' ', '').upper()
            
            return {
                    'value' : {'faktur_stnk':faktur_stnk}
                    }  
    
    
    