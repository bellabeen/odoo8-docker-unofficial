import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp import netsvc
from openerp import SUPERUSER_ID

class wtc_bank_transfer_approval(osv.osv):
    _inherit = "wtc.bank.transfer"
      
    _columns = {
                'approval_ids': fields.one2many('wtc.approval.line','transaction_id',string="Table Approval",domain=[('form_id','=',_inherit)]),
                'approval_state': fields.selection([('b','Belum Request'),('rf','Request For Approval'),('a','Approved'),('r','Reject')],'Approval State', readonly=True),
    }
    
    _defaults ={
                'approval_state':'b'
                }

    def need_approval(self, cr, uid, ids, *args):
        branch_pool = self.pool.get('wtc.branch')
        obj_bj = self.browse(cr, uid, ids)
        need_approval = False
        for line in obj_bj.line_ids :
            branch = branch_pool.search(cr, SUPERUSER_ID, [('code','=',line.branch_destination_id),('branch_type','=','HO')])
            if line.reimbursement_id :
                need_approval = True
                break
            if branch :
                need_approval = True
                break
        return need_approval
    
    def wkf_request_approval(self, cr, uid, ids, context=None):
        obj_matrix = self.pool.get("wtc.approval.matrixbiaya")
        obj_bj = self.browse(cr, uid, ids)
        if not obj_bj.line_ids:
            raise osv.except_osv(('Perhatian !'), ("Line belum diisi"))
        if obj_bj.bank_fee :
            config = self.pool.get('wtc.branch.config').search(cr,uid,[
                                                                   ('branch_id','=',obj_bj.branch_id.id)
                                                                   ])   
            if config :
                config_browse = self.pool.get('wtc.branch.config').browse(cr,uid,config)
                for x in config_browse :
                    if not x.bank_transfer_fee_account_id :
                        raise osv.except_osv(('Perhatian !'), ("Account Bank Transfer Fee belum diisi di Master Branch Config untuk %s")%(obj_bj.branch_id.name))
        obj_matrix.request_by_value(cr, uid, ids, obj_bj, obj_bj.amount)
        self.write(cr, uid, ids, {'state': 'waiting_for_approval','approval_state':'rf'})
        return True
           
    def wkf_approval(self, cr, uid, ids, context=None):
        obj_bj = self.browse(cr, uid, ids, context=context)
        if not obj_bj.line_ids:
            raise osv.except_osv(('Perhatian !'), ("Line belum diisi"))
        approval_sts = self.pool.get("wtc.approval.matrixbiaya").approve(cr, uid, ids, obj_bj)
        if approval_sts == 1:
            self.write(cr, uid, ids, {'approval_state':'a'})
        elif approval_sts == 0:
            raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group approval"))
        if obj_bj.payment_from_id.type == 'cash' :
            if obj_bj.amount > obj_bj.payment_from_id.default_debit_account_id.balance or obj_bj.amount_show > obj_bj.payment_from_id.default_debit_account_id.balance :
                raise osv.except_osv(('Perhatian !'), ("Saldo kas tidak mencukupi !"))   
        return True

    def has_approved(self, cr, uid, ids, *args):
        obj_bj = self.browse(cr, uid, ids)
        return obj_bj.approval_state == 'a'

    def has_rejected(self, cr, uid, ids, *args):
        obj_bj = self.browse(cr, uid, ids)
        if obj_bj.approval_state == 'r':
            self.write(cr, uid, ids, {'state':'draft'})
            return True
        return False

    def wkf_set_to_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'r'})

    def wkf_set_to_draft_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'b'})
