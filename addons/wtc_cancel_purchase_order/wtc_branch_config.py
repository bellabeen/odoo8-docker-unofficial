from openerp import models, fields, api, _

class wtc_branch_config(models.Model):
    _inherit = 'wtc.branch.config'
    
    purchase_order_cancel_journal_id = fields.Many2one('account.journal',string='Jurnal Pembatalan Purchase Order', help='Jurnal pembatalan purchase order')