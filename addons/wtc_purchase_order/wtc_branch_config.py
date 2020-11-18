from openerp import models, fields, api, _

class wtc_branch_config(models.Model):
    _inherit = 'wtc.branch.config'
   
    wtc_po_journal_unit_id = fields.Many2one('account.journal', string='Jurnal Purchase Unit',help='Journal pembentukan invoice pembelian unit')
    wtc_po_journal_sparepart_id = fields.Many2one('account.journal', string='Jurnal Purchase Sparepart',help='Journal pembentukan invoice pembelian sparepart')
    wtc_po_journal_umum_id = fields.Many2one('account.journal', string='Jurnal Purchase Umum',help='Journal pembentukan invoice pembelian umum')
    wtc_po_account_discount_cash_id = fields.Many2one('account.account',string='Account Discount Cash Supplier')
    wtc_po_account_discount_program_id = fields.Many2one('account.account',string='Account Discount Program Supplier')
    wtc_po_account_discount_lainnya_id = fields.Many2one('account.account',string='Account Discount lainnya Supplier')
    wtc_po_journal_blind_bonus_beli_id = fields.Many2one('account.journal', string='Journal Blind Bonus Beli',help='Journal blind bonus beli unit')
    wtc_po_account_blind_bonus_beli_dr_id = fields.Many2one('account.account', string='Account Blind Bonus Beli (Dr)',help='Account blind bonus beli unit (Dr)')
    wtc_po_account_blind_bonus_beli_cr_id = fields.Many2one('account.account', string='Account Blind Bonus Beli (Cr)',help='Account blind bonus beli unit (Cr)')
    wtc_po_account_blind_bonus_performance_dr_id = fields.Many2one('account.account', string='Account Blind Bonus Performance Beli (Dr)',help='Account blind bonus performance beli unit (Dr)')
    wtc_po_account_blind_bonus_performance_cr_id = fields.Many2one('account.account', string='Account Blind Bonus Performance Beli (Cr)',help='Account blind bonus performance beli unit (Cr)')
    wtc_po_account_discount_all_workshop_id = fields.Many2one('account.account',string='Account Discount Workshop Supplier')
    
      