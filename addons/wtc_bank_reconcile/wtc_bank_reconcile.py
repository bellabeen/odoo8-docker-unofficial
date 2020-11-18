from openerp import models, fields, api

class wtc_bank_reconcile(models.Model):
    _name = "wtc.bank.reconcile"
    _description = "Bank Reconciliation"

    @api.one
    def _get_name(self):
        return self.pool.get('ir.sequence').get(self._cr, self._uid, 'wtc.bank.reconcile') or '/'

    name = fields.Char('Name', required=True,default=_get_name)
    type = fields.Char('Type', required=True)
    line_ids = fields.One2many('account.move.line', 'bank_reconcile_id', 'Entry Lines')

    @api.multi
    def _check_account(self):
        for recon in self :
        	if len(recon.line_ids) < 1 :
        		return False
        	first_account = recon.line_ids[0].account_id.id
        	if any([(line.account_id.type != 'liquidity' or line.account_id.id != first_account) for line in recon.line_ids]):
        		return False
        return True

    _constraints = [
    	(_check_account, 'You can only reconcile journal items with the same account!', ['line_ids']),
    ]
