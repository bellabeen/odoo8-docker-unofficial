from openerp import models, fields, api

class wtc_account_move_line(models.Model):
    _inherit = 'account.move.line'

    def _report_xls_advance_payment_fields(self, cr, uid, context=None):
        return [
            'no',\
            'branch_code',\
            'no_rek',\
            'date',\
            'no_bukti',\
            'sts',\
            'keterangan',\
            'partner',\
            'total',\
            'user',\
            'due_date',\
        ]
        
    def _report_xls_advance_payment_detail_fields(self, cr, uid, context=None):
        return [
            'total_perbranch',\
        ]        