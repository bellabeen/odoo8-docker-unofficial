from openerp import models, fields, api, _

class wtc_branch_config(models.Model):
    _inherit = 'wtc.branch.config'
   
    wtc_advance_payment_account_id = fields.Many2one('account.account', string='Account Advance Payment',help='Account Piutang untuk Advance Payment')
    
   
      