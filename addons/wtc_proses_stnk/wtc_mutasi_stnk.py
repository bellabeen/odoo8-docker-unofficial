import time
from datetime import datetime
from openerp.osv import fields, osv
from string import whitespace

class wtc_mutasi_stnk(osv.osv):
    _name = "wtc.mutasi.stnk"
    _order = "tgl_mutasi desc,id desc"
    
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
        
    def _get_default_date(self,cr,uid,context=None):
        return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)
    


    def print_report_pdf_mutasi_stnk(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = self.read(cr, uid, ids,context=context)[0]

        return self.pool['report'].get_action(cr, uid, [], 'wtc_proses_stnk.wtc_mutasi_stnk_report', data=data, context=context)
        

    _columns = {
        'branch_id': fields.many2one('wtc.branch', string='Branch', required=True),
        'division':fields.selection([('Unit','Unit')], 'Division', change_default=True, select=True),
        'name': fields.char('No Reference',size=20, readonly=True),
        'state': fields.selection([('draft', 'Draft'), ('posted','Posted'),('cancel','Canceled')], 'State', readonly=True),
        'mutasi_line': fields.one2many('wtc.mutasi.stnk.line','mutasi_stnk_id',string="Table Mutasi STNK"), 
        'tgl_mutasi' : fields.date('Tanggal Mutasi'),
        'source_location_id' : fields.many2one('wtc.lokasi.stnk',string="Source Location"),
        'destination_location_id' : fields.many2one('wtc.lokasi.stnk',string="Destination Location"), 
        'destination_branch_id': fields.many2one('wtc.branch', string='Destination Branch', required=True),
        'engine_no': fields.related('mutasi_line', 'name', type='char', string='No Engine'),
        'customer_stnk': fields.related('mutasi_line', 'customer_stnk', type='many2one', relation='res.partner', string='Customer STNK'),
        'confirm_uid':fields.many2one('res.users',string="Confirmed by"),
        'confirm_date':fields.datetime('Confirmed on'),          
    }
    _defaults = {
      'state':'draft',
      'division' : 'Unit',
      'tgl_mutasi': _get_default_date,
      'branch_id': _get_default_branch,
     }
    
    def onchange_source(self,cr,uid,ids,context=None):
        result = {}
        value = {}
        value = {
                 'mutasi_line':False,
                 'destination_location_id':False                 
                 }        
        result['value'] = value
        return result 
    
    def onchange_branch(self,cr,uid,ids,branch,destination_branch) :
        domain = {}
        result = {}
        value = {}
        if branch and destination_branch :
            if branch == destination_branch :
                domain['destination_location_id'] = [('type','=','internal'),('branch_id','=',destination_branch)]
            if branch != destination_branch :
                domain['destination_location_id'] = [('type','=','transit'),('branch_id','=',destination_branch)]
        value = {
                 'mutasi_line':False
                 }    
        result['domain'] = domain  
        result['value'] = value
        return result  

    def onchange_destination(self,cr,uid,ids,source,destination,context=None):
        result = {}
        value = {}
        warning = {}
        if not source :
            context = {}
        if not destination :
            context = {}
        if source or destination:
            if source == destination :
                value = {'destination_location_id':False,'mutasi_line':False}
                warning = {
                    'title': ('Perhatian !'),
                    'message': ('Destination Location tidak boleh sama dengan Source Location'),
                }   
            else :
                value = {'mutasi_line':False}
      
        result['value'] = value
        result['warning'] = warning
        
        return {'value':value,'warning':warning}
    
    def create(self, cr, uid, vals, context=None):
        if not vals['mutasi_line'] :
            raise osv.except_osv(('Perhatian !'), ("Tidak ada detail Mutasi. Data tidak bisa di save."))
        lot_mutasi = []
        for x in vals['mutasi_line']:
            lot_mutasi.append(x.pop(2))
        lot_pool = self.pool.get('stock.production.lot')
        mutasi_pool = self.pool.get('wtc.mutasi.stnk.line')
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'MUS')
        
        vals['tgl_mutasi'] = self._get_default_date(cr, uid, context)
        del[vals['mutasi_line']]

        
        mutasi_id = super(wtc_mutasi_stnk, self).create(cr, uid, vals, context=context) 

        if mutasi_id :         
            for x in lot_mutasi :
                lot_search = lot_pool.search(cr,uid,[
                            ('id','=',x['name'])
                            ])
                lot_browse = lot_pool.browse(cr,uid,lot_search) 
                mutasi_pool.create(cr, uid, {
                                                     'name':lot_browse.id,
                                                     'mutasi_stnk_id':mutasi_id,
                                                     'customer_stnk':lot_browse.customer_stnk.id,
                                                     'tgl_stnk':lot_browse.tgl_stnk,
                                                     'no_stnk':lot_browse.no_stnk,
                                                     'no_polisi':lot_browse.no_polisi
                                                    })
                           
        else :
            return False
        return mutasi_id
    
    def write(self,cr,uid,ids,vals,context=None):
        vals.get('mutasi_line',[]).sort(reverse=True)
        return super(wtc_mutasi_stnk, self).write(cr, uid, ids, vals,context=context)
    
    def post_mutasi(self,cr,uid,ids,context=None):
        val = self.browse(cr,uid,ids)
        lot_pool = self.pool.get('stock.production.lot') 
        tanggal = self._get_default_date(cr, uid, context)
        self.write(cr, uid, ids, {'state': 'posted','tgl_mutasi':tanggal,'confirm_uid':uid,'confirm_date':datetime.now()})              
        for x in val.mutasi_line :
            lot_search = lot_pool.search(cr,uid,[
                ('id','=',x.name.id)
                ])
            lot_browse = lot_pool.browse(cr,uid,lot_search)
            lot_browse.write({
                   'lokasi_stnk_id':val.destination_location_id.id
                   })   
        return True
 
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Mutasi sudah di post ! tidak bisa didelete !"))
        return super(wtc_mutasi_stnk, self).unlink(cr, uid, ids, context=context)
            
class wtc_mutasi_stnk_line(osv.osv):
    _name = "wtc.mutasi.stnk.line"
    _columns = {
                'name' : fields.many2one('stock.production.lot','No Engine',domain="[('lokasi_stnk_id','=',parent.source_location_id)]",change_default=True,),
                'mutasi_stnk_id' : fields.many2one('wtc.mutasi.stnk','Mutasi STNK'),
                'customer_stnk':fields.related('name','customer_stnk',type='many2one',relation='res.partner',readonly=True,string='Customer STNK'),
                'tgl_stnk' : fields.related('name','tgl_stnk',type='date',readonly=True,string='Tgl JTP STNK'),
                'no_stnk' : fields.related('name','no_stnk',type='char',readonly=True,string='No STNK'),
                'no_polisi' : fields.related('name','no_polisi',type='char',readonly=True,string='No Polisi'),
                }  
    
    _sql_constraints = [
    ('unique_name_mutasi_stnk_id', 'unique(name,mutasi_stnk_id)', 'Detail Engine duplicate, mohon cek kembali !'),
]
    
    def onchange_engine(self, cr, uid, ids, name,branch_id,division,source,destination):
        if not branch_id or not division or not source or not destination:
            raise osv.except_osv(('Perhatian !'), ('Sebelum menambah detil transaksi,\n harap isi branch, division, source location dan destination location terlebih dahulu.'))
    
    
        value = {}
        if name :
            lot_obj = self.pool.get('stock.production.lot')
            lot_search = lot_obj.search(cr,uid,[
                                                      ('id','=',name)
                                                      ])
            if lot_search :
                lot_browse = lot_obj.browse(cr,uid,lot_search)          
                value = {
                         'customer_stnk':lot_browse.customer_stnk.id,
                         'tgl_stnk':lot_browse.tgl_stnk,
                         'no_stnk':lot_browse.no_stnk,
                         'no_polisi':lot_browse.no_polisi
                         }        
        return {'value':value}