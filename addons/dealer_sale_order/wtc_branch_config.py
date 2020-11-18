from openerp import models, fields, api, _

class wtc_branch_config(models.Model):
    _inherit = 'wtc.branch.config'
   
    dealer_so_journal_pelunasan_id = fields.Many2one('account.journal', string='Jurnal Pelunasan SO',help='Journal D')
    dealer_so_journal_dp_id = fields.Many2one('account.journal', string='Jurnal DP')
    dealer_so_account_potongan_langsung_id = fields.Many2one('account.account', string='Account Potongan Langsung')
    dealer_so_account_potongan_subsidi_id = fields.Many2one('account.account', string='Account Potongan Subsidi')
    dealer_so_journal_psmd_id = fields.Many2one('account.journal', string='Jurnal PS MD')
    dealer_so_journal_psfinco_id = fields.Many2one('account.journal', string='Jurnal PS Finco')
    dealer_so_journal_bbnbeli_id = fields.Many2one('account.journal', string='Jurnal BBN Beli')
    dealer_so_journal_insentive_finco_id = fields.Many2one('account.journal', string='Jurnal Insentive Finco')
    dealer_so_account_bbn_jual_id = fields.Many2one('account.account', string='Account BBN Jual')
    dealer_so_journal_bbmd_id = fields.Many2one('account.journal', string='Jurnal BB MD')
    dealer_so_journal_bbfinco_id = fields.Many2one('account.journal', string='Jurnal BB Finco')
    dealer_so_journal_hc_id = fields.Many2one('account.journal', string='Jurnal Hutang Komisi')
    dealer_so_account_sisa_subsidi_id = fields.Many2one('account.account', string='Account Sisa Program Subsidi')
    dealer_so_journal_hl_id = fields.Many2one('account.journal', string='Jurnal Hutang Lain Reconcile')

    dealer_so_journal_accrue_ekspedisi_id = fields.Many2one('account.journal','Jurnal Accrue Dana Ongkos Angkut')
    dealer_so_journal_accrue_proses_bbn_id = fields.Many2one('account.journal','Jurnal Accrue Biaya Proses BBN')


class Branch(models.Model):
    _inherit = "wtc.branch"

    accrue_ekspedisi = fields.Float('Accrue Dana Ongkos Angkut')
    accrue_proses_bbn = fields.Float('Accrue Biaya Proses BBN')