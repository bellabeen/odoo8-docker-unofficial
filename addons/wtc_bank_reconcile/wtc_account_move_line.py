from openerp.osv import fields, osv

class wtc_account_move_line(osv.osv):
    _inherit = "account.move.line"

    _columns = {
        'bank_reconcile_id':fields.many2one('wtc.bank.reconcile', 'Bank Reconcile', copy=False),
    }