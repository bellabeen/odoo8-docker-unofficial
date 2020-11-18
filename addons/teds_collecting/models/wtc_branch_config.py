from openerp import api, fields, models

class wtc_branch_config(models.Model):
    _inherit = 'wtc.branch.config'

    journal_collecting_id = fields.Many2one('account.journal', string='Journal Collecting')

