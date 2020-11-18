import time
from datetime import datetime
from openerp import models, fields, api

class wtc_branch_config_proses_birojasa(models.Model):
    _inherit = "wtc.branch.config"
    
    tagihan_birojasa_progressive_journal_id = fields.Many2one('account.journal',string="Journal Pajak Progressive",domain="[('type','!=','view')]",help="Journal ini dibutuhkan saat proses Tagihan Biro Jasa, jika Unitnya memiliki pajak progressive.")
    tagihan_birojasa_bbn_journal_id = fields.Many2one('account.journal',string="Journal BBN Beli",domain="[('type','!=','view')]",help="Journal ini dibutuhkan saat proses Tagihan Biro Jasa, Nilai yang dikeluarkan adalah Nilai BBN Beli / Tagihan dari Biro Jasa.")
    