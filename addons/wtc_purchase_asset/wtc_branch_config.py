import time
from datetime import datetime
from openerp import models, fields, api

class wtc_branch_config_purchase_asset(models.Model):
    _inherit = "wtc.branch.config"
    
    purchase_asset_journal_id = fields.Many2one('account.journal',string="Journal Purchase Asset",domain="[('type','!=','view')]",help="Journal ini dibutuhkan saat proses Purchase Asset.")
    prepaid_account_id = fields.Many2one('account.account',string='Prepaid Account')
    accrue_account_id = fields.Many2one('account.account',string='Accrue Account')
    receipt_asset_journal_id = fields.Many2one('account.journal',string="Journal Receipt Asset",domain="[('type','!=','view')]",help="Journal ini dibutuhkan saat proses Receipt Asset.")
    journal_asset_adjustment_id = fields.Many2one('account.journal',string="Journal Asset Adjustment",domain="[('type','!=','view')]",help="Journal ini dibutuhkan saat proses Asset Adjustment.")
    journal_disposal_asset_id = fields.Many2one('account.journal',string="Journal Disposal Asset",domain="[('type','!=','view')]",help="Journal ini dibutuhkan saat proses Disposal Asset.")
    gain_loss_account_id = fields.Many2one('account.account',string='Gain/Loss Account')
    expense_asset_account_id = fields.Many2one('account.account',string='Expense Asset Account')
    journal_disposal_asset_hl_id = fields.Many2one('account.journal',string="Journal Hutang Lain Reconcile",domain="[('type','!=','view')]",help="Journal ini dibutuhkan saat Reconcile HL Disposal Asset Sold.")