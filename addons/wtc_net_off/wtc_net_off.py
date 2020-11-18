import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp import SUPERUSER_ID
from lxml import etree

class wtc_net_off(models.Model):
    _name = 'wtc.net.off'
    _description = 'Net Off'
    _order = 'date desc'
    
    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('waiting_for_approval','Waiting For Approval'),
        ('post','Posted'),
        ('cancel','Cancelled')
    ]
                    
    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
            
    @api.one
    @api.depends('net_off_line.debit')
    def _compute_debit(self):
        total_debit = 0.0
        for x in self.net_off_line :
            total_debit += x.debit
        if self.net_off_line :
            if total_debit == 0.0 :
                    raise osv.except_osv(('Perhatian !'), ("Total credit atau debit harus lebih dari 0 !"))   
            
        self.total_debit = total_debit

    @api.one
    @api.depends('net_off_line.credit')
    def _compute_credit(self):
        total_credit = 0.0
        for x in self.net_off_line :
            total_credit += x.credit
        if self.net_off_line :
            if total_credit == 0.0 :
                raise osv.except_osv(('Perhatian !'), ("Total credit atau debit harus lebih dari 0 !"))   
                        
        self.total_credit = total_credit
                    
    @api.one
    @api.depends('net_off_line.amount_residual')
    def _compute_residual(self):
        total_residual = 0.0
        for x in self.net_off_line :
            total_residual += x.amount_residual
        self.total_residual = total_residual
                     
    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()
                                
    name = fields.Char(string='No')
    branch_id = fields.Many2one('wtc.branch', string='Branch', required=True, default=_get_default_branch)
    date = fields.Date(string="Date",required=True,readonly=True,default=_get_default_date)
    net_off_line = fields.One2many('wtc.net.off.line','net_off_id',string='')
    state= fields.Selection(STATE_SELECTION, string='State', readonly=True,default='draft')
    reconcile_id = fields.Many2one('account.move.reconcile', 'Reconcile No', readonly=True, ondelete='set null', select=2, copy=False)
    description = fields.Char(string='Description')
    confirm_uid = fields.Many2one('res.users',string="Confirmed by")
    confirm_date = fields.Datetime('Confirmed on')
    approval_ids = fields.One2many('wtc.approval.line','transaction_id',string="Table Approval",domain=[('form_id','=',_name)])
    approval_state =  fields.Selection([
                                        ('b','Belum Request'),
                                        ('rf','Request For Approval'),
                                        ('a','Approved'),
                                        ('r','Reject')
                                        ],'Approval State', readonly=True,default='b')
    account_id = fields.Many2one('account.account',string='Account',domain="[('type','in',('receivable','payable'))]")
    partner_id = fields.Many2one('res.partner',string='Partner')    
    total_debit = fields.Float(string='Total Debit',digits=dp.get_precision('Account'), store=True,compute='_compute_debit')
    total_credit = fields.Float(string='Total Credit',digits=dp.get_precision('Account'), store=True,compute='_compute_credit')
    division = fields.Selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum'),('Finance','Finance')], string='Division',default='Umum', required=True,change_default=True, select=True)
    total_residual = fields.Float(string='Total Residual',digits=dp.get_precision('Account'), store=True,compute='_compute_residual')
     
    @api.onchange('account_id','partner_id','branch_id')
    def onchange_account_partner(self):
        if self.account_id or self.partner_id or self.branch_id:
            self.net_off_line = []

    @api.model
    def create(self,vals,context=None):
            
        vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'NO') 
        vals['date'] = self._get_default_date()           
        if len(vals.get('net_off_line')) < 2 :
            raise osv.except_osv(('Perhatian !'), ("Detail Net Off tidak boleh kurang dari 2!"))   
        res = super(wtc_net_off, self).create(vals)
        cek = self.cek_total_amount()
        return res 

    @api.one      
    def cek_total_amount(self):
        total_credit = 0.0
        total_debit = 0.0

        count = 0
        for x in self.net_off_line :
            count += 1

        if count < 2 :
            raise osv.except_osv(('Perhatian !'), ("Detail Net Off tidak boleh kurang dari 2!")) 
        return True

    @api.multi
    def write(self,values,context=None): 
        res = super(wtc_net_off,self).write(values)
        cek = self.cek_total_amount()
        return res
        
    @api.cr_uid_ids_context
    def action_create_reconcile(self,cr,uid,ids,context=None):
        account_move_line = self.pool.get('account.move.line')
        move_line_ids = []
        vals = self.browse(cr,uid,ids)
        for x in vals.net_off_line :
            if x.move_line_id.reconcile_partial_id :
                move_line_ids += [y.id for y in x.move_line_id.reconcile_partial_id.line_partial_ids]
            else :
                move_line_ids.append(x.move_line_id.id)
        if move_line_ids  :
            reconcile_id = account_move_line.reconcile_partial(cr, uid, move_line_ids, 'auto',context=context)

        if reconcile_id :
            self.write(cr,uid,ids,{'reconcile_id':reconcile_id,'state':'post'})
        return True
                                            
    @api.multi
    def wkf_request_approval(self):
        obj_matrix = self.env["wtc.approval.matrixbiaya"]
        amount = 0.0
        if self.total_credit < self.total_debit :
            amount = self.total_credit
        elif self.total_credit == self.total_debit :
            amount = self.total_credit or self.total_debit
        else :
            amount = self.total_debit
            
        obj_matrix.request_by_value(self, amount)
        
        self.write({'state':'waiting_for_approval','approval_state':'rf'})

    @api.multi      
    def wkf_approval(self):       
        approval_sts = self.env['wtc.approval.matrixbiaya'].approve(self)
        if approval_sts == 1:
            self.write({'date':self._get_default_date(),'approval_state':'a','confirm_uid':self._uid,'confirm_date':datetime.now()})
            reconcile = self.action_create_reconcile()
        elif approval_sts == 0:
                raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group Approval"))    
            
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
    
    @api.one
    def wkf_set_to_draft(self):
        self.write({'state':'draft','approval_state':'r'})     
                            
    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Net Off tidak bisa didelete !"))
        return super(wtc_net_off, self).unlink(cr, uid, ids, context=context) 
                                
class wtc_net_off_line(models.Model):
    _name = 'wtc.net.off.line'
    _rec_name = 'move_line_id'
        
    move_line_id = fields.Many2one('account.move.line',domain='[("reconcile_id","=",False)]',string='Journal Items')
    account_id = fields.Many2one('account.account',string="Account")
    branch_id = fields.Many2one('wtc.branch',string='Branch')   
    partner_id = fields.Many2one('res.partner',string='Partner') 
    credit = fields.Float(string='Credit') 
    debit = fields.Float(string='Debit')
    reconcile_partial_id = fields.Many2one(related='move_line_id.reconcile_partial_id',relation='account.move.reconcile', string='Partial Reconcile', readonly=True)
    amount_residual = fields.Float(related='move_line_id.amount_residual',string='Amount Residual')
    net_off_id = fields.Many2one('wtc.net.off',string='Net Off') 
     
    @api.onchange('move_line_id')
    def onchange_move_line_id(self):
        dom = {}
        dom['move_line_id'] = "[('reconcile_id','=',False),\
        ('account_id','=',"+ str(self.net_off_id.account_id.id)+"),\
        ('branch_id','=',"+ str(self.net_off_id.branch_id.id)+"),\
        ('partner_id','=',"+ str(self.net_off_id.partner_id.id)+")]"

        if self.move_line_id :
            self.account_id = self.move_line_id.account_id.id
            self.branch_id = self.move_line_id.branch_id.id
            self.partner_id = self.move_line_id.partner_id.id
            self.credit = self.move_line_id.credit
            self.debit = self.move_line_id.debit
            self.amount_residual = self.move_line_id.amount_residual
            self.reconcile_partial_id = self.move_line_id.reconcile_partial_id.id
        return {'domain':dom}
    
    @api.onchange('credit','debit','account_id','partner_id','branch_id','amount_residual')
    def change_move_line(self):
        if self.credit and self.move_line_id :
            self.credit = self.move_line_id.credit
        if self.debit and self.move_line_id :
            self.debit = self.move_line_id.debit   
        if self.account_id and self.move_line_id :
            self.account_id = self.move_line_id.account_id.id
        if self.partner_id and self.move_line_id :
            self.partner_id = self.move_line_id.partner_id.id   
        if self.branch_id and self.move_line_id :
            self.branch_id = self.move_line_id.branch_id.id    
        if self.amount_residual and self.move_line_id :
            self.amount_residual = self.move_line_id.amount_residual   
        if self.reconcile_partial_id and self.move_line_id :
            self.reconcile_partial_id = self.move_line_id.reconcile_partial_id.id 
                                                                                                
    _sql_constraints = [('unique_name_move_line_id', 'unique(net_off_id,move_line_id)', 'Tidak boleh ada journal yang sama dalam satu net off  !')] 
        