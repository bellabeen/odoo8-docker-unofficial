import time
import pytz
from openerp import SUPERUSER_ID
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse
from openerp.osv import fields, osv
from openerp import netsvc
from openerp import pooler
from openerp import tools
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.osv.orm import browse_record, browse_null
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP

class wtc_program_subsidi(osv.osv):
    _name = 'wtc.program.subsidi'
    _inherit = ['mail.thread']
    
    def _get_max(self, cr, uid, ids, field_name, arg, context=None):
        res ={}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] ={
                            'nilai_promo': 0.0
                            }
            nilai_max =0.0
        for line in order.program_subsidi_line :
            if nilai_max < line.total_diskon :
                nilai_max = line.total_diskon
            res[order.id]['nilai_promo']=nilai_max
        return res
    
    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('wtc.program.subsidi.line').browse(cr, uid, ids, context=context):
            result[line.program_subsidi_id.id] = True
        return result.keys()

    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
    
    _columns = { 
                'branch_id':fields.many2one('wtc.branch','Branch', required=True),
                'division':fields.selection([('Unit','Unit')], 'Division', change_default=True, select=True,required=True),                     
                'area_id':fields.many2one('wtc.area',string='Area',required=True),
                'name':fields.char("Name", size=30,required=True),
                'date_start':fields.date("Date Start",required=True),
                'date_end':fields.date("Date End",required=True),
                'keterangan':fields.text("Keterangan"),                
                 'nilai_promo':fields.function(_get_max,string='Nilai Promo',
                 store={
                        'wtc.program.subsidi': (lambda self, cr, uid, ids, c={}: ids, ['program_subsidi_line'], 10),
                        'wtc.program.subsidi.line': (_get_order, ['diskon_ahm', 'diskon_md', 'diskon_dealer', 'diskon_finco', 'diskon_others'], 10),
                    },
                     multi='sums', help="Subtotal Diskon."),
                'instansi_id':fields.many2one('res.partner','Instansi',domain=[('finance_company','=',True)]),
                'tipe_subsidi':fields.selection([('fix','Fix'),('non','Non Fix')], "Tipe Subsidi", change_default=True, select=True,required=True),                     
                'state': fields.selection([('draft', 'Draft'),('waiting_for_approval','Waiting For Approval'), ('approved', 'Approved'),('rejected','Rejected'),('editable','Editable'),('on_revision','On Revision')], 'State', readonly=True),
                'program_subsidi_line':fields.one2many('wtc.program.subsidi.line','program_subsidi_id',"Program Subsidi",copy=True),
                'partner_ref':fields.char('Kode Program MD',size=50,required=True),
                'active':fields.boolean('Active'),
                'confirm_uid':fields.many2one('res.users',string="Approved by"),
                'confirm_date':fields.datetime('Approved on'),
    }
    _defaults ={
                'state': 'draft',
                'branch_id': _get_default_branch,
                'active': True,
                'division':'Unit'
                
                }
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
        if not vals['program_subsidi_line'] :
            raise osv.except_osv(('Perhatian !'), ("Tidak ada detail Program Subsidi. Data tidak bisa di save."))
        return super(wtc_program_subsidi, self).create(cr, uid, vals, context=context)

         
    def unlink(self, cr, uid, ids, context=None):
         for item in self.browse(cr, uid, ids, context=context):
             if item.state != 'draft':
                 raise osv.except_osv(('Perhatian !'), ("Program Subsidi tidak bisa didelete !"))
         return super(wtc_program_subsidi, self).unlink(cr, uid, ids, context=context)
    
    def copy(self, cr, uid, id, default=None, context=None):
        subsidi_line = []
        if default is None:
            default = {}
            
        for program_subsidi in self.browse(cr,uid,id):
            #end_date = parse(program_subsidi.date_end) + timedelta(days=2)
            start_date = datetime.strptime(program_subsidi.date_start,'%Y-%m-%d') + timedelta(days=1)
            end_date = datetime.strptime(program_subsidi.date_start,'%Y-%m-%d') + timedelta(days=2)
            default.update({
                            'branch_id': program_subsidi.branch_id.id,
                            'division': program_subsidi.division,
                            'area_id': program_subsidi.area_id.id,
                            'name': program_subsidi.name,
                            'date_start': start_date,
                            'date_end': end_date,
                            'keterangan': program_subsidi.keterangan,                
                            'instansi_id': program_subsidi.instansi_id.id,
                            'tipe_subsidi': program_subsidi.tipe_subsidi,                     
                            'state': 'draft',
                            'partner_ref': program_subsidi.partner_ref,
                            'active': True,
                            'approval_state': 'b',
                            })
            for lines in program_subsidi.program_subsidi_line:
                subsidi_line.append([0,False,{
                                              'product_template_id':lines.product_template_id.id,
                                            'tipe_dp': lines.tipe_dp,
                                            'amount_dp': lines.amount_dp,
                                            'diskon_ahm':lines.diskon_ahm,
                                            'diskon_md':lines.diskon_md,
                                            'diskon_dealer':lines.diskon_dealer,
                                            'diskon_finco':lines.diskon_finco,
                                            'diskon_others':lines.diskon_others,
                                            
                                              }])
            default.update({'program_subsidi_line':subsidi_line})
                
        return super(wtc_program_subsidi, self).copy(cr, uid, id, default=default, context=context)
        
    def write(self,cr,uid,ids,vals,context=None):
        val = self.browse(cr,uid,ids)
        date_start = val.date_start
        date_end = val.date_end
        new_start = vals.get('date_start',date_start)
        new_end = vals.get('date_end',date_end)
        user = self.pool.get('res.users').browse(cr,uid,uid)
        if date_start != new_start or date_end != new_end :
            if val.state == 'on_revision' and not vals.get('state') and not vals.get('approval_state'):
                self.message_post(cr, uid, val.id, body=_("Previous Date : %s - %s <br/> Effective Date : %s - %s <br/> Revised by %s ")%(date_start,date_end,new_start,new_end,user.name), context=context) 
            elif val.state == 'editable' and not vals.get('state') and not vals.get('approval_state'):
                self.message_post(cr, uid, val.id, body=_("Previous Date : %s - %s <br/> Effective Date : %s - %s <br/> Edited by %s ")%(date_start,date_end,new_start,new_end,user.name), context=context) 
        return super(wtc_program_subsidi, self).write(cr, uid, ids, vals, context=context)       
    
class wtc_program_subsidi_line(osv.osv):
    _name = 'wtc.program.subsidi.line'
    
    def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
        res={}
        for line in self.browse(cr, uid, ids, context=context):
            price = (line.diskon_ahm or 0.0) + (line.diskon_md or 0.0)+ (line.diskon_dealer or 0.0)+(line.diskon_finco or 0.0) + (line.diskon_others or 0.0)
            res[line.id]=price
        return res
    
    _columns = { 
                'program_subsidi_id':fields.many2one('wtc.program.subsidi',"Program Subsidi" ,ondelete='cascade'),
                'product_template_id': fields.many2one('product.template', 'Product', required=True),
                'tipe_dp': fields.selection([('min','Min'),('max','Max')], 'Tipe DP', change_default=True, select=True),
                'amount_dp':fields.float("DP Minimal"),
                'diskon_ahm':fields.float("Diskon AHM"),
                'diskon_md':fields.float("Diskon MD"),
                'diskon_dealer':fields.float("Diskon Dealer"),
                'diskon_finco':fields.float("Diskon Finco"),
                'diskon_others':fields.float("Diskon Others"),
                'total_diskon':fields.function(_amount_line, string='Total Diskon',store=True),

                }
    _defaults = {
                  'amount_dp': 0.0,
                  'diskon_ahm': 0.0,
                  'diskon_md': 0.0,
                  'diskon_dealer': 0.0,
                  'diskon_finco': 0.0,
                  'diskon_others': 0.0,
                  }
    _sql_constraints = [
    ('unique_product_ps', 'unique(program_subsidi_id,product_template_id)', 'Tidak boleh ada produk yg sama didalam satu master program subsidi !'),
    ]
    
    def _get_domain_program_subsidi(self,cr,uid,ids,context=None):
        domain = {} 
        categ_ids = self.pool.get('product.category').get_child_ids(cr,uid,ids,'Unit')
        domain['product_template_id'] = [('type','!=','view'),('categ_id','in',categ_ids)]      
        return {'domain':domain}   