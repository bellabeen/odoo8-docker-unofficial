from openerp import models, fields, api

class wtc_account_move_line(models.Model):
    _inherit = 'account.move.line'

    def _report_xls_trial_balance_fields(self, cr, uid, context=None):
        return [
            'no',\
            'account_code',\
            'branch_name',\
            'account_sap',\
            'account_name',\
            'saldo_awal_debit',\
            'saldo_awal_credit',\
            'mutasi_debit',\
            'mutasi_credit',\
            'debit_neraca',\
            'credit_neraca',\

        ]

    def _report_xls_import_trial_balance_fields(self, cr, uid, context=None):
        return [
            'no',\
            'account_code',\
            'branch_name',\
            'account',\
            'profit_centre',\
            'div',\
            'dept',\
            'class',\
            'type',\
            'account_name',\
            'mutasi_debit',\
            'mutasi_credit',\

        ]
        
    def _report_xls_trial_balance_import_sun_fields(self, cr, uid, context=None):
        return [
            'no',\
            'branch_code',\
            'account_code',\
            'account',\
            'profit_centre',\
            'div',\
            'dept',\
            'class',\
            'type',\
            'account_name',\
            'transaction_amount',\
            'date_stop',\
            'trans_reference',\
            'memo_amount',\
            'debit',\
            'credit',\

        ]
                 
    # override list in custom module to add/drop columns
    # or change order of the partner summary table
    def _report_xls_arap_details_fields(self, cr, uid, context=None):
        return [
            'document', 'date', 'date_maturity', 'account', 'description',
            'rec_or_rec_part', 'debit', 'credit', 'balance',
            # 'partner_id',
        ]
 
    # Change/Add Template entries
    def _report_xls_arap_overview_template(self, cr, uid, context=None):
        """
        Template updates, e.g.
 
        my_change = {
            'partner_id':{
                'header': [1, 20, 'text', _('Move Line ID')],
                'lines': [1, 0, 'text', _render("p['id_aml']")],
                'totals': [1, 0, 'text', None]},
        }
        return my_change
        """
        return {}
 
    # Change/Add Template entries
    def _report_xls_arap_details_template(self, cr, uid, context=None):
        """
        Template updates, e.g.
 
        my_change = {
            'partner_id':{
                'header': [1, 20, 'text', _('Move Line ID')],
                'lines': [1, 0, 'text', _render("p['id_aml']")],
                'totals': [1, 0, 'text', None]},
        }
        return my_change
        """
        return {}
     