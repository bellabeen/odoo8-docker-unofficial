from openerp import models, fields, api
from datetime import datetime

class ApiButton(models.Model):
    _inherit = "teds.api.button"

    @api.multi
    def api_dms_account_invoice(self):
        self.env['account.invoice'].sudo().api_dms_account_invoice()
    