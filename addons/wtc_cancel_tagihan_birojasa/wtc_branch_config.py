from openerp import models, fields, api, _

class wtc_branch_config(models.Model):
    _inherit = 'wtc.branch.config'
    
    birojasa_cancel_journal_id = fields.Many2one('account.journal',string='Jurnal Pembatalan Tagihan Birojasa', help='Jurnal pembatalan tagihan birojasa')
    pajak_progressive_cancel_journal_id = fields.Many2one('account.journal', string='Jurnal Pembatalan Pajak Progressive', help='Jurnal pembatalan pajak progressive')
    