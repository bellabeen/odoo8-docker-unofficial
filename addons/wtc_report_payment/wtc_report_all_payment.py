from openerp import models, fields, api

class wtc_account_voucher(models.Model):
    _inherit = 'account.voucher'

    def _report_xls_arap_overview_fields(self, cr, uid, context=None):
        return [
            'partner', 'partner_ref', 'debit', 'credit', 'balance',
            # 'partner_id'
        ]

    def _report_xls_arap_details_fields(self, cr, uid, context=None):
        return [
            'document','nama_cabang','terima_untuk','nama_cabang_untuk','number','status','payment_method','account2',
            'paid_amount','partner','nama_partner','no_transksi','cr','dr','dif', 
        ]

    def _report_xls_arap_overview_template(self, cr, uid, context=None):
        """
        Template updates, e.g.

        my_change = {
            'partner_id':{
                'header': [1, 20, 'text', _('Partner ID')],
                'lines': [1, 0, 'text', _render("p['p_id']")],
                'totals': [1, 0, 'text', None]},
        }
        return my_change
        """
        return {}

    def _report_xls_arap_details_template(self, cr, uid, context=None):
        """
        Template updates, e.g.

        my_change = {
            'partner_id':{
                'header': [1, 20, 'text', _('Partner ID')],
                'lines': [1, 0, 'text', _render("p['p_id']")],
                'totals': [1, 0, 'text', None]},
        }
        return my_change
        """
