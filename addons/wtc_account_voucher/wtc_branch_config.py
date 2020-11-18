from openerp import models, fields, api, _

class wtc_branch_config(models.Model):
    _inherit = 'wtc.branch.config'
   
    wtc_payment_request_account_id = fields.Many2one('account.journal', string='Account Payment Request',help='Account Untuk Payment Request')
    wtc_other_receivable_account_id = fields.Many2one('account.journal', string='Account Other Receivable',help='Account Untuk Other Receivable')
    wtc_account_voucher_pembulatan_account_id = fields.Many2one('account.account', string='Account Pembulatan')
    nilai_pembulatan = fields.Float(string='Nilai Pembulatan')
   
      