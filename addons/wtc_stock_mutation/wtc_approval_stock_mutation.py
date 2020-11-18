from openerp import models, fields, api
import time
from datetime import datetime
import itertools
from lxml import etree
from openerp import models,fields, exceptions, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp import netsvc

class wtc_approval_stock_mutation(models.Model):
    _inherit = 'wtc.mutation.request'
    
    approval_ids = fields.One2many('wtc.approval.line', 'transaction_id', string="Table Approval", domain=[('form_id','=',_inherit)])
    approval_state = fields.Selection([
                                       ('b','Belum Request'),
                                       ('rf','Request For Approval'),
                                       ('a','Approved'),
                                       ('r','Reject')
                                       ], 'Approval State', readonly=True, default='b')
    confirm_uid = fields.Many2one('res.users',string="Approved by")
    confirm_date = fields.Datetime('Approved on')
    cancel_uid = fields.Many2one('res.users',string="Cancelled by")
    cancel_date = fields.Datetime('Cancelled on')    
        
    @api.multi
    def wkf_request_approval(self):
        obj_matrix = self.env['wtc.approval.matrixbiaya']
        obj_matrix.request(self, 'amount_total')
        self.write({'state':'waiting_for_approval', 'approval_state':'rf'})
        return True
    
    @api.multi
    def wkf_approval(self):
        approval_sts = self.env['wtc.approval.matrixbiaya'].approve(self)
        if approval_sts == 1 :
            self.write({'rel_date':datetime.today(),'approval_state':'a', 'state':'approved','confirm_uid':self._uid,'confirm_date':datetime.now()})
            self.wkf_confirm_order()
        elif approval_sts == 0 :
            raise exceptions.ValidationError( ("User tidak termasuk group approval"))
        return True
    
    @api.multi
    def has_approved(self):
        if self.approval_state == 'a':
            return True
        return False
    
    @api.multi
    def has_rejected(self):
        if self.approval_state == 'r':
            self.write({'state':'draft'})
            return True
        return False
    
    @api.cr_uid_ids_context
    def wkf_set_to_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'r'})
    
    @api.cr_uid_ids_context
    def wkf_set_to_draft_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'b'})
            
class wtc_reject_approval_stock_mutation(models.TransientModel):
    _name = "wtc.reject.approval.stock.mutation"
     
    reason = fields.Text('Reason')
     
    @api.multi
    def wtc_reject_approval(self, context=None):
        user = self.env['res.users'].browse(self)['group_id']
        po_id = context.get('active_id',False) #When you call any wizard then in this function ids parameter contain the list of ids of the current wizard record. So, to get the purchase order ID you have to get it from context.
        
        line = self.env['wtc.mutation.request'].browse(po_id,context=context)
        objek = False
        for x in line.approval_ids :
            for y in user :
                    if y == x.group_id :
                        objek = True
                        for z in line.approval_ids :
                            if z.reason == False :
                                z.write({
                                        'reason':self.reason,
                                        'value':line.amount_total,
                                        'sts':'3',
                                        'pelaksana_id':self.uid,
                                        'tanggal':datetime.today()
                                        })
         
                                self.env['wtc.mutation.request'].write( {'state':'draft','approval_state':'r'})
        if objek == False :
            raise exceptions.ValidationError("User tidak termasuk group approval")
        
        return True
     