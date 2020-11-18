import time
import base64
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
import pytz 


class wtc_cancel_proses_stnk(osv.osv):
    _name = "wtc.cancel.proses.stnk"
    _order = 'id desc'
    
    def _get_default_date(self,cr,uid,context=None):
        return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=None) 
    
    _columns = {
                'name':fields.char(string='Name'),
                'state':fields.selection([('draft','Draft'),('post','Posted')],string='State'),
                'date':fields.date('Date'),
                'proses_stnk_id' : fields.many2one('wtc.proses.stnk',domain="[('state','=','posted')]",string='No Proses STNK'),
                'cancel_line' : fields.one2many('wtc.cancel.proses.stnk.line','cancel_proses_stnk_id',string='Cancel line'),             
                'confirm_uid':fields.many2one('res.users',string="Posted by"),
                'confirm_date':fields.datetime('Posted on'),
                }  
      
    _defaults = {
                 'state':'draft',
                 'date':_get_default_date
                 }
    
    def create(self,cr,uid,vals,context=None):
        vals['name'] = self.pool.get('ir.sequence').get_sequence(cr, uid, 'CPS', context=context)
        vals['date'] = self._get_default_date(cr, uid, context)
        if not vals.get('cancel_line') :
            raise osv.except_osv(('Perhatian !'), ("harap isi detail !"))             
        res = super(wtc_cancel_proses_stnk,self).create(cr,uid,vals,context=context)
        return res
    
    
    def wtc_cancel_proses_stnk(self, cr, uid, ids, context=None):
        val = self.browse(cr,uid,ids)
        pf = self.pool.get('wtc.proses.stnk').browse(cr,uid,[val.proses_stnk_id.id])  
        lot_pool = self.pool.get('stock.production.lot') 
        if len(pf.serial_number_ids) == 1 :
            self.pool.get('wtc.proses.stnk').write(cr,uid,pf.id,{'state':'cancel','cancel_uid':uid,'cancel_date':datetime.now()})         
        for x in val.cancel_line :
            lot_search = lot_pool.search(cr,uid,[
                        ('branch_id','=',pf.branch_id.id),
                        ('proses_stnk_id','=',pf.id),
                        ('name','=',x.name.name),
                        ('tgl_proses_birojasa','=',False),
                        ('inv_pajak_progressive_id','=',False)
                        ])
            if not lot_search :
                raise osv.except_osv(('Perhatian !'), ("No Engine %s tidak bisa di cancel, atau sudah melakukan proses pajak progressive atau poses birojasa, cek data kembali")%(x.name.name))
            if lot_search :
                lot_browse = lot_pool.browse(cr,uid,lot_search)
                if  lot_browse.penerimaan_stnk_id or lot_browse.penerimaan_bpkb_id or lot_browse.proses_biro_jasa_id or lot_browse.inv_pajak_progressive_id or lot_browse.penyerahan_stnk_id or lot_browse.penyerahan_polisi_id or lot_browse.penyerahan_notice_id  :
                    raise osv.except_osv(('Perhatian !'), ("No faktur engine \'%s\' telah diproses, data tidak bisa di cancel !")%(lot_browse.name))                    
                else : 
                    lot_browse.write({'state_stnk': 'terima_faktur','tgl_proses_stnk':False,'proses_stnk_id':False})                    
        self.write(cr, uid, ids, {'state': 'post', 'date':self._get_default_date(cr, uid, context),'confirm_uid':uid,'confirm_date':datetime.now()})
        return True
     
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Cancel Proses STNK sudah di validate ! tidak bisa didelete !"))
        return super(wtc_cancel_proses_stnk, self).unlink(cr, uid, ids, context=context)
         
class wtc_cancel_proses_stnk_line(osv.osv):
    _name = "wtc.cancel.proses.stnk.line"
    
    _columns = {
                'name':fields.many2one('stock.production.lot',string='No Engine',domain="[('proses_stnk_id','=',parent.proses_stnk_id)]"),
                'cancel_proses_stnk_id':fields.many2one('wtc.cancel.proses.stnk',string='No Cancel permohonan'),
                'chassis_no' : fields.related('name','chassis_no',type='char',string='Chassis No'),
                }       
    
    _sql_constraints = [
    ('unique_name_cancel_proses_stnk_id', 'unique(name,cancel_proses_stnk_id)', 'Detail Engine duplicate, mohon cek kembali !'),
]    
        
    def onchange_engine(self,cr,uid,ids,engine_id,context=None):
        value = {}
        if engine_id :
            lot = self.pool.get('stock.production.lot').browse(cr,uid,engine_id)
            value['chassis_no'] = lot.chassis_no or False
        return {'value':value}