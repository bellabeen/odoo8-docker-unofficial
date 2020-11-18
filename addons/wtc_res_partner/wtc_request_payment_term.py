import time
from datetime import datetime
from openerp import models, fields, api
from openerp.osv import osv

class wtc_request_payment_term(models.Model):
    _name = 'wtc.request.payment.term'
    _description = 'Request Payment Term'

    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('waiting_for_approval','Waiting For Approval'),
        ('confirmed', 'Waiting Approval'),
        ('approved','Approved'),
        ('cancel','Cancelled')
    ]
    
    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
            
    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()
                
    name = fields.Char(string='Ref')
    branch_id = fields.Many2one('wtc.branch', string='Branch', required=True)
    division = fields.Selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum'),('Finance','Finance')], string='Division',default='Unit', required=True,change_default=True, select=True)    
    partner_id = fields.Many2one('res.partner',domain=[('customer','=',True)],required=True)
    current_payment_term_show_id = fields.Many2one(related="partner_id.property_payment_term",relation='account.payment.term',string="Current Payment Term",readonly=True)
    current_payment_term_id = fields.Many2one('account.payment.term',string="Current Payment Term",readonly=True)
    new_payment_term_id = fields.Many2one('account.payment.term',string="New Payment Term",required=True)
    state= fields.Selection(STATE_SELECTION, string='State', readonly=True,default='draft')
    confirm_uid = fields.Many2one('res.users',string="Approved by")
    confirm_date = fields.Datetime('Approved on')
    cancel_uid = fields.Many2one('res.users',string="Cancelled by")
    cancel_date = fields.Datetime('Cancelled on')
    approval_field = fields.Float(string='Approval Fields')
    date = fields.Date(string='Date',default=_get_default_date)
        
    @api.onchange('current_payment_term_show_id')
    def change_term(self):
        if self.current_payment_term_show_id :
            self.current_payment_term_id = self.current_payment_term_show_id
#     @api.one
#     def approved_request(self):
#         if self.partner_id :
#             partner = self.env['res.partner'].search([('id','=',self.partner_id)])
#             partner.write({'property_payment_term':self.new_payment_term_id})
#         self.write({'state':'approved','confirm_uid':self._uid,'confirm_date':datetime.now()})
#         return True
          
    @api.model
    def create(self,vals,context=None):
        vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'RPT')   
        vals['date'] = self._get_default_date()                          
        return super(wtc_request_payment_term, self).create(vals)
        
    @api.one
    def cancel_request(self):
        self.write({'state':'cancel','cancel_uid':self._uid,'cancel_date':datetime.now()})
        return True     