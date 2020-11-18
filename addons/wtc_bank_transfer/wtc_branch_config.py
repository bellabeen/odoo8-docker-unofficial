from openerp import models, fields, api

class wtc_branch_config(models.Model):
    _inherit = "wtc.branch.config"
    
    bank_transfer_fee_account_id = fields.Many2one('account.account',string="Account Bank Transfer Fee",domain=[('type','=','other')],help="Account ini.(prefix:8121)")
    bank_transfer_cancel_journal_id = fields.Many2one('account.journal',string='Jurnal Pembatalan Bank Transfer', help='Jurnal pembatalan settlement')