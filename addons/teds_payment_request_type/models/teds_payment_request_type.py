from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning
from datetime import date, datetime, timedelta,time

class PaymentRequestType(models.Model):
    _inherit = "wtc.payments.request.type"

    active = fields.Boolean('Active',default=True)
    type = fields.Selection([('NC','Payment Request'),('PCO','Petty Cash')],string="Type")
    payment_request_type_ids = fields.One2many('teds.payments.request.type.line','type_id')

    _sql_constraints = [('unique_name_type', 'unique(name,type)', 'Payment Type duplicat !')]

    @api.model
    def create(self,vals):
        if not vals.get('payment_request_type_ids'):
            raise Warning('Detail type tidak boleh kosong !')
        return super(PaymentRequestType,self).create(vals)
    
    @api.multi
    def write(self,vals):
        write = super(PaymentRequestType,self).write(vals)
        if not self.payment_request_type_ids:
            raise Warning('Detail type tidak boleh kosong !')
        return write

    @api.onchange('name')
    def onchange_name(self):
        if self.name:
            self.name = self.name.upper()

class PaymentRequestTypeLine(models.Model):
    _name = "teds.payments.request.type.line"

    type_id = fields.Many2one('wtc.payments.request.type',ondelete='cascade')
    name = fields.Char('Name',index=True)
    account_id = fields.Many2one('account.account','Account',domain=[('active','=',True)])

    @api.model
    def create(self,vals):
        if vals.get('name'):
            vals['name'] = vals['name'].upper()
        return super(PaymentRequestTypeLine,self).create(vals)    
    
    @api.multi
    def write(self,vals):
        if vals.get('name'):
            vals['name'] = vals['name'].upper()
        return super(PaymentRequestTypeLine,self).write(vals)    

    @api.onchange('name')
    def onchange_name(self):
        if self.name:
            self.name = self.name.upper()