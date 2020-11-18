import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp import netsvc

class wtc_subsidi_barang(osv.osv):
    _inherit = "wtc.subsidi.barang"      
    _columns = {
                'approval_ids': fields.one2many('wtc.approval.line','transaction_id',string="Table Approval",domain=[('form_id','=',_inherit)]),
                'approval_state': fields.selection([('b','Belum Request'),('rf','Request For Approval'),('a','Approved'),('r','Reject')],'Approval State', readonly=True),  
    }
    
    _defaults ={
                'approval_state':'b'
                }
    
    def wtc_request_approval(self, cr, uid, ids, context=None):
        obj_subsidi_barang = self.browse(cr, uid, ids, context=context)
        obj_matrix = self.pool.get("wtc.approval.matrixbiaya")
        if not obj_subsidi_barang.subsidi_barang_line:
            raise osv.except_osv(('Perhatian !'), ("Line belum diisi"))
        obj_matrix.request(cr, uid, ids, obj_subsidi_barang, 'nilai_promo')
        self.write(cr, uid, ids, {'state': 'waiting_for_approval','approval_state':'rf'})        
        return True
               
    def wtc_approval(self, cr, uid, ids, context=None):
        obj_subsidi_barang = self.browse(cr, uid, ids, context=context)
        if not obj_subsidi_barang.subsidi_barang_line:
            raise osv.except_osv(('Perhatian !'), ("Line belum diisi"))
        approval_sts = self.pool.get("wtc.approval.matrixbiaya").approve(cr, uid, ids, obj_subsidi_barang)
        if approval_sts == 1:
            self.write(cr, uid, ids, {'approval_state':'a','state':'approved','confirm_uid':uid,'confirm_date':datetime.now()})
        elif approval_sts == 0:
            raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group approval"))
        return True
    
    def wtc_perpanjang_periode(self, cr, uid, ids, context=None):    
             val = self.browse(cr, uid, ids)      
             so = self.pool.get('dealer.sale.order.line.brgbonus.line')
             so_search= so.search(cr,uid,[
                                          ('barang_subsidi_id','=',val.name)
                                          ])
             so_search2= so.search(cr,uid,[
                                          ('barang_subsidi_id','!=',val.name)
                                          ])
             if so_search:
                self.write(cr, uid, ids , {'state':'editable'})
             elif so_search2 :
                 self.write(cr, uid, ids , {'state':'on_revision'})           
             return True
         
    def wtc_revise(self, cr, uid, ids, context=None):    
             val = self.browse(cr, uid, ids)      
             so = self.pool.get('dealer.sale.order.line.brgbonus.line')
             so_search= so.search(cr,uid,[
                                          ('barang_subsidi_id','=',val.name)
                                          ])
             so_search2= so.search(cr,uid,[
                                          ('barang_subsidi_id','!=',val.name)
                                          ])             
             if so_search:
                self.write(cr, uid, ids , {'state':'editable'})
             elif so_search2:
                self.write(cr, uid, ids , {'state':'on_revision'})
             return True
        
