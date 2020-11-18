from openerp import models, fields, api, _

class wtc_branch_config(models.Model):
    _inherit = 'wtc.branch.config'
   
    wtc_retur_pembelian_journal_unit_id = fields.Many2one('account.journal', string='Jurnal Retur Pembelian Unit',help='Journal pembentukan invoice Retur Pembelian Unit')
    wtc_retur_pembelian_journal_sparepart_id = fields.Many2one('account.journal', string='Jurnal Retur Pembelian Sparepart',help='Journal pembentukan invoice Retur Pembelian Sparepart')
    wtc_retur_pembelian_account_discount_cash_id = fields.Many2one('account.account',string='Account Retur Pembelian Discount Cash Customer')
    wtc_retur_pembelian_account_discount_program_id = fields.Many2one('account.account',string='Account Retur Pembelian Discount Program Customer')
    wtc_retur_pembelian_account_discount_lainnya_id = fields.Many2one('account.account',string='Account Retur Pembelian Discount lainnya Customer')
  
    wtc_retur_penjualan_journal_unit_id = fields.Many2one('account.journal', string='Jurnal Retur Penjualan Unit',help='Journal pembentukan invoice Retur Penjualan Unit')
    wtc_retur_penjualan_journal_sparepart_id = fields.Many2one('account.journal', string='Jurnal Retur Penjualan Sparepart',help='Journal pembentukan invoiceRetur Penjualan Sparepar')
    wtc_retur_penjualan_account_discount_cash_id = fields.Many2one('account.account',string='Account Retur Penjualan Discount Cash Customer')
    wtc_retur_penjualan_account_discount_program_id = fields.Many2one('account.account',string='Account Retur Penjualan Discount Program Customer')
    wtc_retur_penjualan_account_discount_lainnya_id = fields.Many2one('account.account',string='Account Retur Penjualan Discount lainnya Customer')
  