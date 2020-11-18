import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp import netsvc
from openerp.tools.translate import _


class wtc_program_subsidi(osv.osv):
    _inherit = "wtc.program.subsidi"      
    _columns = {
                'approval_ids': fields.one2many('wtc.approval.line','transaction_id',string="Table Approval",domain=[('form_id','=',_inherit)]),
                'approval_state': fields.selection([('b','Belum Request'),('rf','Request For Approval'),('a','Approved'),('r','Reject')],'Approval State', readonly=True),  
    }
    
    _defaults ={
                'approval_state':'b'
                }
    
    def wtc_request_approval(self, cr, uid, ids, context=None):
        obj_program_subsidi = self.browse(cr, uid, ids, context=context)
        obj_matrix = self.pool.get("wtc.approval.matrixbiaya")
        if not obj_program_subsidi.program_subsidi_line:
            raise osv.except_osv(('Perhatian !'), ("Line belum diisi"))
        obj_matrix.request(cr, uid, ids, obj_program_subsidi, 'nilai_promo')
        self.write(cr, uid, ids, {'state': 'waiting_for_approval','approval_state':'rf'})        
        return True
    
           
    def wtc_approval(self, cr, uid, ids, context=None):               
        obj_program_subsidi = self.browse(cr, uid, ids, context=context)
        if not obj_program_subsidi.program_subsidi_line:
            raise osv.except_osv(('Perhatian !'), ("Line belum diisi"))
        approval_sts = self.pool.get("wtc.approval.matrixbiaya").approve(cr, uid, ids, obj_program_subsidi)
        if approval_sts == 1:
            self.write(cr, uid, ids, {'approval_state':'a','state':'approved','confirm_uid':uid,'confirm_date':datetime.now()})
        elif approval_sts == 0:
            raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group approval"))
        return True
    
    def wtc_perpanjang_periode(self, cr, uid, ids, context=None):    
            val = self.browse(cr, uid, ids)    
            user = self.pool.get('res.users').browse(cr,uid,uid)  
            so = self.pool.get('dealer.sale.order.line.discount.line')
            so_search= so.search(cr,uid,[
                                         ('program_subsidi','=',val.name)
                                         ])
            if so_search:
               self.write(cr, uid, ids , {'state':'editable'})
            elif not so_search :
                self.write(cr, uid, ids , {'state':'on_revision'})     
            self.message_post(cr, uid, val.id, body=_("Perpanjangan periode by %s ")%(user.name), context=context) 
      
            return True
         
    def wtc_revise(self, cr, uid, ids, context=None):    
             val = self.browse(cr, uid, ids)      
             so = self.pool.get('dealer.sale.order.line.discount.line')
             so_search= so.search(cr,uid,[
                                          ('program_subsidi','=',val.name)
                                          ])           
             if so_search:
                self.write(cr, uid, ids , {'state':'editable'})
             elif not so_search:
                self.write(cr, uid, ids , {'state':'on_revision'})
             return True
 