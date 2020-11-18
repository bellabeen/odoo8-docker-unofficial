from openerp import models, fields, api, _

class wtc_branch_config(models.Model):
    _inherit = 'wtc.branch.config'
   
    wtc_so_journal_unit_id = fields.Many2one('account.journal', string='Jurnal Penjualan Unit',help='Journal pembentukan invoice penjualan unit')
    wtc_so_journal_sparepart_id = fields.Many2one('account.journal', string='Jurnal Penjualan Sparepart',help='Journal pembentukan invoice penjualan sparepart')
    wtc_so_account_discount_cash_id = fields.Many2one('account.account',string='Account Discount Cash Customer')
    wtc_so_account_discount_program_id = fields.Many2one('account.account',string='Account Discount Program Customer')
    wtc_so_account_discount_lainnya_id = fields.Many2one('account.account',string='Account Discount lainnya Customer')
    wtc_so_journal_bind_bonus_jual_id = fields.Many2one('account.journal', string='Jurnal Blind Bonus Jual Unit',help='Journal pembentukan invoice blind bonus jual unit')
    wtc_so_account_discount_cash_sparepart_id = fields.Many2one('account.account',string='Account Discount Cash Sparepart Customer')
    wtc_so_account_discount_cash_oil_id = fields.Many2one('account.account',string='Account Discount Cash Oli Customer')
   