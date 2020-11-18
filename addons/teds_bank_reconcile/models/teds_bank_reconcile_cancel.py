from openerp import api, fields, models
from openerp.exceptions import Warning
from datetime import date, datetime, timedelta

class BankReconcileCancel(models.Model):
    _name = "teds.bank.reconcile.cancel"

    def _get_default_branch(self):
        branch_ids = False
        branch_ids = self.env.user.branch_ids
        if branch_ids and len(branch_ids) == 1 :
            return branch_ids[0].id
        return False

    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()
    
    def _get_default_datetime(self):
        return self.env['wtc.branch'].get_default_datetime_model()

    name = fields.Char('Neme')
    branch_id = fields.Many2one('wtc.branch','Branch',default=_get_default_branch)
    bank_reconcile_id = fields.Many2one('teds.bank.reconcile','Bank Reconcile')
    date = fields.Date('Date',default=_get_default_date)
    state = fields.Selection([
        ('draft','Draft'),
        ('waiting_for_approval','Waiting For Approval'),
        ('approved','Approved'),
        ('confirmed','Confirmed')],default="draft")
    reason = fields.Text('Reason')
    approve_uid = fields.Many2one('res.users','Approved by')
    approve_date = fields.Datetime('Approved on')
    confirm_uid = fields.Many2one('res.users','Confirmed by')
    confirm_date = fields.Datetime('Confirmed on')

    @api.model
    def create(self,vals):
        if vals.get('bank_reconcile_id'):
            bank_reconcile = self.env['teds.bank.reconcile'].browse(vals['bank_reconcile_id'])
            vals['name'] = 'X%s'%(bank_reconcile.name)
        return super(BankReconcileCancel,self).create(vals)

    def cek_bank_mutation(self):
        if self.bank_reconcile_id.state not in ('posted','Auto Reconcile'):
            raise Warning('Bank Reconcile tidak bisa dicancel, State %s !'%(self.bank_reconcile_id.state))

    @api.multi
    def action_rfa(self):
        self.cek_bank_mutation()
        self.write({'state':'waiting_for_approval'})

    @api.multi
    def action_cancel_approved(self):
        if self.state == 'confirmed':
            raise Warning('Sudah tidak bisa di cancel approve !')
        self.write({
            'state':'draft',
            'approve_date':False,
            'approve_uid':False,
        })
    
    @api.multi
    def action_approved(self):
        self.cek_bank_mutation()
        self.write({
            'state':'approved',
            'approve_uid':self._uid,
            'approve_date':self._get_default_datetime(),
        })


    @api.multi
    def action_confirm(self):
        self.cek_bank_mutation()
        for bm in self.bank_reconcile_id.bank_mutasi_ids:
            print "bm>>>>>>>>>>>",bm
           
            bm.write({
                'state':'Outstanding',
                'reconciled':False,
                'bank_reconcile_id':False,
                'effective_date_reconcile':False,
            })
        for ml in self.bank_reconcile_id.move_line_ids:
            print "ml>>>>>>>>>>>",ml
            ml.write({
                'teds_reconciled_rk':False,
                'teds_bank_reconcile_id':False,
                'effective_date_reconcile':False,
            })
        self.bank_reconcile_id.write({
            'cancel_uid':self._uid,
            'cancel_date':self._get_default_datetime(),
            'state':'cancel'    
        })
        self.write({
            'state':'confirmed',
            'confirm_uid':self._uid,
            'confirm_date':self._get_default_datetime(),    
        })