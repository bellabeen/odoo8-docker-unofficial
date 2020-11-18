from openerp import models, fields, api, _

class wtc_branch_config(models.Model):
    _inherit = 'wtc.branch.config'
    
    dso_cancel_journal_id = fields.Many2one('account.journal', string='Jurnal Pembatalan Dealer Sale Order', help='Jurnal pembatalan dealer sale order')
    payment_cancel_journal_id = fields.Many2one('account.journal', string='Jurnal Pembatalan Customer Payment', help='Jurnal pembatalan customer payment')
    so_cancel_unit_journal_id = fields.Many2one('account.journal', string='Jurnal Pembatalan Sale Order Unit', help='Jurnal pembatalan sale order unit')
    so_cancel_sparepart_journal_id = fields.Many2one('account.journal', string='Jurnal Pembatalan Sale Order Sparepart', help='Jurnal pembatalan sale order sparepart')
    