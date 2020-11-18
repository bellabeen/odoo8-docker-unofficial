import time
from datetime import datetime
from openerp import models, fields, api

class wtc_branch_config(models.Model):
    _inherit = "wtc.branch.config"
    
    disburesement_pl_account_id = fields.Many2one('account.account',string="Account PL Disbursement",domain=[('type','=','other')],help="Account ini prefix(799)")
    disbursement_cancel_journal_id = fields.Many2one('account.journal',string="Jorunal Pembatalan Disbursement EDC")
    