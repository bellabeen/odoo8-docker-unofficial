import time
from datetime import datetime
from openerp import models, fields, api, _
from openerp import workflow

class account_invoice(models.Model):
    _inherit = "account.invoice"
    
    dealer_sale_order_store_line_id = fields.Many2one('dealer.sale.order.line',string='Dealer Sale Order Line')
    tipe = fields.Selection(selection_add=[('accrue', 'Accrue')])

    @api.multi
    def confirm_paid(self):
        paid = super(account_invoice,self).confirm_paid()
        if self.model_id.model=='dealer.sale.order' and self.tipe in ('customer','finco'):
            obj_dso = self.env['dealer.sale.order']
            dso = obj_dso.browse(self.transaction_id).check_done()
        return paid