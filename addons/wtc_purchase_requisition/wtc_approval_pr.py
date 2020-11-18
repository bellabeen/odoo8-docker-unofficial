import time
from datetime import datetime
from openerp.osv import fields, osv

class wtc_purchase_requisition(osv.osv):
    _inherit = "purchase.requisition"
    STATE_SELECTION = [
                       ('draft', 'Draft'),
                       ('waiting_for_approval','Waiting Approval'),
                       ('confirmed', 'Waiting Approval'),
                       ('request_approval','RFA'), 
                       ('in_progress', 'Confirmed'),
                       ('open', 'Bid Selection'), 
                       ('done', 'PO Created'),
                       ('cancel', 'Cancelled')]  
     
    _columns = {
                'approval_ids': fields.one2many('wtc.approval.line','transaction_id',string="Table Approval",domain=[('form_id','=',_inherit)],),
                'state': fields.selection(STATE_SELECTION,
                                    'Status', track_visibility='onchange', required=True,
                                    copy=False),
                'purchase_ids': fields.one2many('purchase.order', 'requisition_id', 'Purchase Orders', states={'request_approval':[('readonly',True)],'done': [('readonly', True)]}),
                'line_ids': fields.one2many('purchase.requisition.line', 'requisition_id', 'Products to Purchase', states={'request_approval':[('readonly',True)],'done': [('readonly', True)]}, copy=True),
                'approval_state': fields.selection([('b','Belum Request'),('rf','Request For Approval'),('a','Approved'),('r','Reject')],'Approval State', readonly=True),


    }
    _defaults ={
                'approval_state':'b'
                }
    
    def wkf_request_approval(self, cr, uid, ids, context=None):
        obj_pr = self.browse(cr, uid, ids, context=context)
        if not obj_pr.line_ids:
            raise osv.except_osv(('Perhatian !'), ("Produk belum diisi"))
        
        total = 0
        for qty in obj_pr.line_ids :
            total = total + qty.product_qty

        obj_matrix = self.pool.get("wtc.approval.matrixbiaya")
        obj_matrix.request_by_value(cr, uid, ids, obj_pr, total)
        self.write(cr, uid, ids, {'state': 'waiting_for_approval','approval_state':'rf'})
        return True        
    
    def wkf_approval(self, cr, uid, ids, context=None):
        obj_pr = self.browse(cr, uid, ids, context=context) 
        if not obj_pr.line_ids:
            raise osv.except_osv(('Perhatian !'), ("Produk belum diisi"))
        approval_sts = self.pool.get("wtc.approval.matrixbiaya").approve(cr, uid, ids, obj_pr)
        if approval_sts == 1:
            self.write(cr, uid, ids, {'approval_state':'a'})
        elif approval_sts == 0:
            raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group approval"))
   
        return True

    def has_approved(self, cr, uid, ids, *args):
        obj_pr = self.browse(cr, uid, ids)
        return obj_pr.approval_state == 'a'

    def has_rejected(self, cr, uid, ids, *args):
        obj_pr = self.browse(cr, uid, ids)
        if obj_pr.approval_state == 'r':
            self.write(cr, uid, ids, {'state':'draft'})
            return True
        return False

    def wkf_set_to_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'r'}) 
        
    def wkf_set_to_draft_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'b'})          