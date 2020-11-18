import time
import pytz
from openerp import SUPERUSER_ID
from datetime import datetime,timedelta
from dateutil.relativedelta import relativedelta

from openerp.osv import fields, osv
from openerp import netsvc
from openerp import pooler
from openerp import tools
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.osv.orm import browse_record, browse_null
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP

class wtc_subsidi_barang(osv.osv):
    _name = 'wtc.subsidi.barang'
    def _get_max(self, cr, uid, ids, field_name, arg, context=None):
        res ={}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] ={
                            'nilai_promo': 0.0
                            }
            nilai_max =0.0
        for line in order.subsidi_barang_line :
            if nilai_max < line.total_diskon :
                nilai_max = line.total_diskon
            res[order.id]['nilai_promo']=nilai_max
        return res
    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('wtc.subsidi.barang.line').browse(cr, uid, ids, context=context):
            result[line.subsidi_barang_id.id] = True
        return result.keys()

    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
    
    _columns = { 
                'branch_id':fields.many2one('wtc.branch','Branch', required=True),
                'division':fields.selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum')], 'Division', change_default=True, select=True,required=True),                     
                'name':fields.char("Name", size=30,required=True),
                'date_start':fields.date("Date Start",required=True),
                'date_end':fields.date("Date End",required=True),
                'keterangan':fields.text("Keterangan"),
                'product_template_id':fields.many2one('product.product',"Product",required=True),
                'nilai_promo':fields.function(_get_max, string="Nilai Promo",
                store={
                        'wtc.subsidi.barang': (lambda self, cr, uid, ids, c={}: ids, ['subsidi_barang_line'], 10),
                        'wtc.subsidi.barang.line': (_get_order, ['diskon_ahm', 'diskon_md', 'diskon_dealer', 'diskon_finco', 'diskon_others'], 10),
                    },
                    multi='sums',help="Subtotal Diskon."),
                'subsidi_barang_line':fields.one2many('wtc.subsidi.barang.line','subsidi_barang_id',"Subsidi Barang",required=True),       
                'state': fields.selection([('draft', 'Draft'),('waiting_for_approval','Waiting For Approval'), ('approved', 'Approved'),('rejected','Rejected'),('editable','Editable'),('on_revision','On Revision')], 'State', readonly=True),
                'area_id':fields.many2one('wtc.area','Area',required=True),
                'partner_ref':fields.char('Kode Program MD',size=50,required=True),
                'active':fields.boolean('Active'),
                'confirm_uid':fields.many2one('res.users',string="Approved by"),
                'confirm_date':fields.datetime('Approved on'),               
             }
    _defaults ={
                'state': 'draft',
                'branch_id': _get_default_branch,
                'active': True
                }
    
    def _get_domain_product_tmp(self,cr,uid,ids,context=None):
        domain = {} 
        categ_ids = self.pool.get('product.category').get_child_ids(cr,uid,ids,'Umum')
        filter = []
        if categ_ids :
            categ = self.pool.get('product.category').browse(cr,uid,categ_ids)
            for x in categ :
                if x.name == 'DIRECT GIFT' :
                    filter.append(x.id)
        domain['product_template_id'] = [('type','!=','view'),('categ_id','in',filter)]      
        return {'domain':domain}
        
    def _check_dates(self, cr, uid, ids, context=None):
        if context == None:
            context = {}
        obj_task = self.browse(cr, uid, ids[0], context=context)
        start = obj_task.date_start or False
        end = obj_task.date_end or False
        if start and end :
            if start > end:
                return False
        return True
    
    _constraints = [
      (_check_dates, 'Perhatian !, Date end harus lebih besar dari',['date_start']),
    ]
    def button_dummy(self, cr, uid, ids, context=None):
        return True 
    
    def create(self,cr,uid,vals,context=None):
        if not vals['subsidi_barang_line'] :
            raise osv.except_osv(('Perhatian !'), ("Tidak ada detail Subsidi Barang. Data tidak bisa di save."))
        return super(wtc_subsidi_barang, self).create(cr, uid, vals, context=context)
    
    def unlink(self, cr, uid, ids, context=None):
         for item in self.browse(cr, uid, ids, context=context):
             if item.state != 'draft':
                 raise osv.except_osv(('Perhatian !'), ("Subsidi Barang tidak bisa didelete !"))
         return super(wtc_subsidi_barang, self).unlink(cr, uid, ids, context=context)
     
    def copy(self, cr, uid, id, default=None, context=None):
        subsidi_line = []
        if default is None:
            default = {}
            
        for subsidi_barang in self.browse(cr,uid,id):
            #end_date = parse(subsidi_barang.date_end) + timedelta(days=2)
            start_date = datetime.strptime(subsidi_barang.date_start,'%Y-%m-%d') + timedelta(days=1)
            end_date = datetime.strptime(subsidi_barang.date_start,'%Y-%m-%d') + timedelta(days=2)
            default.update({
                            'branch_id': subsidi_barang.branch_id.id,
                            'division': subsidi_barang.division,
                            'area_id': subsidi_barang.area_id.id,
                            'name': subsidi_barang.name,
                            'date_start': start_date,
                            'date_end': end_date,
                            'keterangan': subsidi_barang.keterangan,
                            'product_template_id':subsidi_barang.product_template_id.id,                
                            'state': 'draft',
                            'partner_ref': subsidi_barang.partner_ref,
                            'active': True,
                            'approval_state': 'b',
                            })
            for lines in subsidi_barang.subsidi_barang_line:
                subsidi_line.append([0,False,{
                                              'product_id':lines.product_id.id,
                                            'qty': lines.qty,
                                            'diskon_ahm':lines.diskon_ahm,
                                            'diskon_md':lines.diskon_md,
                                            'diskon_dealer':lines.diskon_dealer,
                                            'diskon_finco':lines.diskon_finco,
                                            'diskon_others':lines.diskon_others,
                                            
                                              }])
            default.update({'subsidi_barang_line':subsidi_line})
                
        return super(wtc_subsidi_barang, self).copy(cr, uid, id, default=default, context=context)
     
class wtc_subsidi_barang_line(osv.osv):
    _name = 'wtc.subsidi.barang.line'
    def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
        if context is None:
            context = {}
        res={}
        for line in self.browse(cr, uid, ids, context=context):
            price = (line.diskon_ahm or 0.0) + (line.diskon_md or 0.0)+ (line.diskon_dealer or 0.0)+(line.diskon_finco or 0.0) + (line.diskon_others or 0.0)
            res[line.id]=price
        return res

    _columns = { 
                'subsidi_barang_id':fields.many2one('wtc.subsidi.barang',"Subsidi Barang",required=True),
                'product_id': fields.many2one('product.template', 'Product', required=True),
                'qty': fields.integer("Qty",required=True),
                'diskon_ahm':fields.float("Diskon AHM"),
                'diskon_md':fields.float("Diskon MD"),
                'diskon_dealer':fields.float("Diskon Dealer"),
                'diskon_finco':fields.float("Diskon Finco"),
                'diskon_others':fields.float("Diskon Others"),
                'total_diskon':fields.function(_amount_line, string='Total Diskon',store=True),
                
                }
    _defaults = {
                  'diskon_ahm': 0.0,
                  'diskon_md': 0.0,
                  'diskon_dealer': 0.0,
                  'diskon_finco': 0.0,
                  'diskon_others': 0.0,
                  'qty': 1,
                  }
    
    _sql_constraints = [
        ('unique_product_bs', 'unique(subsidi_barang_id,product_id)', 'Tidak boleh ada produk yg sama didalam satu master subsidi barang !'),
    ]

    def qty_change(self, cr, uid, ids, qty, context=None):
        if qty:
            if qty<=0:
                return {'value':{'qty':1},'warning':{'title':'Perhatian !', 'message':'Qty harus > 0'}}
        return {}
    
    def _get_domain_product(self,cr,uid,ids,context=None):
        domain = {} 
        categ_ids = self.pool.get('product.category').get_child_ids(cr,uid,ids,'Unit')
        domain['product_id'] = [('type','!=','view'),('categ_id','in',categ_ids)]      
        return {'domain':domain} 