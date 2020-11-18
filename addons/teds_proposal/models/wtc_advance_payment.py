from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm, Warning, ValidationError

class teds_advance_payment(models.Model):
    _inherit = "wtc.advance.payment"

    @api.depends('proposal_item_ids.amount_total')
    def _compute_amount(self):
        self.amount_total = sum(x.amount_total for x in self.proposal_item_ids)

    # 
    @api.depends('proposal_id.state','amount_limit','amount_total')
    def _compute_proposal_state(self):
        if self.proposal_id:
            if self.proposal_id.approval_state == 'r' and self.state in ['draft','waiting_for_approval','approved']:
                self.proposal_state = 'reject'
            elif self.proposal_id.state == 'close' and self.state in ['draft','waiting_for_approval','approved']:
                self.proposal_state = 'close'
            else:
                if self.amount_limit and self.amount_total:
                    if self.amount_total < self.amount_limit:
                        self.proposal_state = 'under'
                    elif self.amount_total == self.amount_limit:
                        self.proposal_state = 'on'
                    elif self.amount_total > self.amount_limit:
                        self.proposal_state = 'over'

    proposal_id = fields.Many2one('teds.proposal', string='Nomor Proposal', ondelete='restrict')
    amount_limit = fields.Float(string='Limit Proposal', digits=dp.get_precision('Product Price'))
    amount_total = fields.Float(string='Total', digits=dp.get_precision('Product Price'), compute='_compute_amount', store=True)
    proposal_state = fields.Selection([
        ('under','UNDER BUDGET'),
        ('on','ON BUDGET'),
        ('over','OVER BUDGET'),
        ('reject','REJECTED'),
        ('close','CLOSED')
    ], string='Status Budget', compute='_compute_proposal_state')
    proposal_item_ids = fields.One2many('teds.advance.payment.proposal', 'avp_id', string='Detail Proposal')

    MIN_LIMIT = 10000000 # COO

    @api.onchange('branch_id','division')
    def _onchange_proposal_id(self):
        self.proposal_id = False
        domain = {'proposal_id': [('id','=',0)]}
        if self.branch_id and self.division:
            proposal_model_id = self.env['ir.model'].suspend_security().search([('model','=','teds.proposal')]).id
            get_proposal_query = """
                SELECT DISTINCT
                    prop.id
                FROM teds_proposal prop
                JOIN wtc_approval_line al ON al.transaction_id = prop.id AND al.form_id = %d
                WHERE prop.branch_id = %d
                AND prop.division = '%s'
                AND (
                    prop.state = 'approved' 
                    OR (prop.state = 'rfa' AND prop.amount_approved >= %d AND prop.is_penyimpangan = True)
                )
            """ % (proposal_model_id, self.branch_id.id, self.division, self.MIN_LIMIT)
            self._cr.execute(get_proposal_query)
            proposal_ress = self._cr.fetchall()
            domain = {'proposal_id': [('id','in',[p[0] for p in proposal_ress])]}            
        return {'domain': domain}

    # NOTE: REPLACED WITH amount_approved
    # def _get_proposal_limit(self):
    #     proposal_model_id = self.env['ir.model'].suspend_security().search([('model','=','teds.proposal')]).id
    #     get_proposal_limit_query = """
    #         SELECT MAX(al.limit)
    #         FROM teds_proposal prop
    #         JOIN wtc_approval_line al ON al.transaction_id = prop.id AND al.form_id = %d
    #         WHERE prop.id = %d
    #         AND al.sts = '2'
    #     """ % (proposal_model_id, self.proposal_id.id)
    #     self._cr.execute(get_proposal_limit_query)
    #     limit_ress = self._cr.fetchone()
    #     return limit_ress

    @api.multi
    def update_proposal_limit(self):
        # limit = self._get_proposal_limit()[0]
        if self.proposal_id.state == 'approved':
            self.amount_limit = self.proposal_id.amount_total - (self.proposal_id.amount_paid + self.proposal_id.amount_reserved)
        elif self.proposal_id.state == 'rfa':
            self.amount_limit = self.proposal_id.amount_approved - (self.proposal_id.amount_paid + self.proposal_id.amount_reserved)

    @api.onchange('proposal_id')
    def _onchange_description_and_limit(self):
        self.description = False
        self.amount = 0
        self.amount_limit = 0
        self.proposal_item_ids = []
        if self.proposal_id:
            self.description = self.proposal_id.event
            self.update_proposal_limit()

    @api.constrains('amount')
    def _check_amount(self):
        # Reason: AVP dengan nomor proposal tidak otomatis update amount_total (juga amount).
        if not self.proposal_id and self.amount <= 0:
            raise ValidationError('Total amount harus lebih dari 0.')

    def _check_proposal_amount(self, state, amount, limit):
        if amount <= 0:
            raise Warning('Total amount proposal harus lebih dari 0.')    
        if state == 'rfa' and amount > limit:
            raise Warning('Total amount proposal tidak boleh melebihi limit proposal.')
    
    def _check_proposal_state(self):
        if self.proposal_id.state == 'reject':
            raise Warning('Status %s REJECTED' % (self.proposal_id.name))
        elif self.proposal_id.state == 'close':
            raise Warning('Status %s CLOSED' % (self.proposal_id.name))

    @api.constrains('proposal_item_ids')
    def _check_empty_proposal_line(self):
        if self.proposal_id and len(self.proposal_item_ids) <= 0:
            raise ValidationError('Detail Proposal harus diisi.')
    
    @api.model
    def create(self, values):
        if values.get('proposal_id', False):
            amount = 0
            for x in values['proposal_item_ids']:
                if x[2]: # 0 Create
                    amount += x[2]['amount_total']
            proposal_state = self.env['teds.proposal'].suspend_security().browse(values['proposal_id']).state
            self._check_proposal_amount(proposal_state, amount, values.get('amount_limit',0))
            values['amount'] = amount
        return super(teds_advance_payment, self).create(values)
    
    @api.multi
    def write(self, values):
        if values.get('proposal_item_ids', False):
            amount = 0
            amount_total = 0
            for x in values['proposal_item_ids']:
                if x[0] == 0: # 0 Create
                    amount_total = x[2]['amount_total']
                elif x[0] in [1,4]:
                    item_obj = self.proposal_item_ids.suspend_security().browse(x[1])
                    if x[2]:
                        amount_total = x[2]['amount_total'] if x[2].get('amount_total', False) else item_obj.amount_total
                    else:
                        amount_total = item_obj.amount_total
                amount +=  amount_total
            # Nomor proposal tidak bisa update lagi setelah save, sehingga self.proposal_state & self.amount_limit
            self._check_proposal_amount(self.proposal_id.state, amount, self.amount_limit)
            values['amount'] = amount
        return super(teds_advance_payment, self).write(values)

    @api.multi
    def wkf_request_approval(self):
        # import ipdb
        # ipdb.set_trace()
        # check latest limit proposal
        if self.proposal_id:
            self._check_proposal_state()
            self.update_proposal_limit()
            self._check_proposal_amount(self.proposal_id.state, self.amount, self.amount_limit)
            # setup item proposal
            item_update = []
            for x in self.proposal_item_ids:
                amount_reserved = x.proposal_line_id.suspend_security().amount_reserved
                item_update.append([1, x.proposal_line_id.id, {
                    'amount_reserved': amount_reserved + x.amount_total,
                }])
            # update proposal
            try:
                self.proposal_id.suspend_security().write({'item_ids': item_update})
            except Exception:
                self._cr.rollback()
                raise Warning('Terjadi kesalahan saat update proposal %s.' % (self.proposal_id.suspend_security().name))
        return super(teds_advance_payment, self).wkf_request_approval()

    def _unset_amount_reserved(self):
        item_update = []
        for x in self.proposal_item_ids:
            amount_reserved = x.proposal_line_id.suspend_security().amount_reserved
            item_update.append([1, x.proposal_line_id.id, {
                'amount_reserved': amount_reserved - x.amount_total,
            }])
        try:
            self.proposal_id.suspend_security().write({'item_ids': item_update})
        except Exception:
            self._cr.rollback()
            raise Warning('Terjadi kesalahan saat update proposal %s.' % (self.proposal_id.suspend_security().name))

    @api.one
    def wkf_set_to_draft(self):
        # import ipdb
        # ipdb.set_trace()
        write_avp = super(teds_advance_payment, self).wkf_set_to_draft()
        if write_avp and self.proposal_id:
            self._unset_amount_reserved()

    @api.multi
    def wkf_action_confirm(self):
        confirm_avp = super(teds_advance_payment, self).wkf_action_confirm()
        if confirm_avp and self.proposal_id:
            self._check_proposal_state()
            # import ipdb
            # ipdb.set_trace()
            try:
                # create listing pembayaran
                self.env['teds.proposal.payment'].suspend_security().create({
                    'proposal_id': self.proposal_id.id,
                    'payment_num': str(self.name),
                    'payment_model_id': self.env['ir.model'].suspend_security().search([('model','=',str(self.__class__.__name__))]).id,
                    'payment_transaction_id': self.id,
                    'payment_date': self.date,
                    'payment_amount': self.amount
                })
                # setup item proposal
                item_update = []
                for x in self.proposal_item_ids:
                    amount_reserved = x.proposal_line_id.suspend_security().amount_reserved
                    amount_paid = x.proposal_line_id.suspend_security().amount_paid
                    item_update.append([1, x.proposal_line_id.id, {
                        'amount_reserved': amount_reserved - x.amount_total,
                        'amount_paid': amount_paid + x.amount_total,
                        'payment_ids': [[0, 0, {
                            'name': x.avp_id.name,
                            'supplier_id': False,
                            'jenis_pembayaran': 'C',
                            'amount_paid': x.amount_total,
                        }]]
                    }])
                # update proposal
                try:
                    self.proposal_id.suspend_security().write({'item_ids': item_update})
                except Exception:
                    self._cr.rollback()
                    raise Warning('Terjadi kesalahan saat update item Proposal %s.' % self.proposal_id.name)
                # NOTE: NO BUDGET
                # budget_amount_avb = self.proposal_id.act_budget_id.suspend_security().amount_avb
                # try:
                #     self.proposal_id.act_budget_id.suspend_security().write({'amount_avb': budget_amount_avb - self.amount})
                # except Exception:
                #     self._cr.rollback()
                #     raise Warning('Terjadi kesalahan saat update Master Budget %s.' % self.proposal_id.act_budget_id.suspend_security().name)
            except Exception:
                self._cr.rollback()
                raise Warning('Terjadi kesalahan saat create Listing Pembayaran di Proposal %s.' % self.proposal_id.name)
        return True

    @api.one
    def wkf_set_to_draft_cancel(self):
        # import ipdb
        # ipdb.set_trace()
        write_avp = super(teds_advance_payment, self).wkf_set_to_draft_cancel()
        if write_avp and self.proposal_id:
            self._unset_amount_reserved()

    @api.multi
    def copy(self):
        raise Warning('Tidak bisa duplikat data.')

class teds_advance_payment_proposal(models.Model):
    _name = "teds.advance.payment.proposal"
    _description = "Advance Payment - Proposal"

    avp_id = fields.Many2one('wtc.advance.payment', string="ID Payment", ondelete='cascade')
    proposal_line_id = fields.Many2one('teds.proposal.line', string='Item Proposal', ondelete='restrict')
    amount_total = fields.Float(string='Amount', digits=dp.get_precision('Product Price'))

    _sql_constraints = [
        ('proposal_line_id_uniq', 'unique(avp_id, proposal_line_id)', "Item proposal tidak boleh duplikat.")]

    @api.constrains('amount_total')
    def _check_amount(self):
        for record in self:
            if record.amount_total <= 0:
                raise ValidationError("Amount %s tidak boleh 0." % (self.proposal_line_id.description))

    @api.onchange('proposal_line_id')
    def _onchange_amount_total(self):
        self.amount_total = 0
        if self.proposal_line_id:
            self.amount_total = self.proposal_line_id.amount_total - (self.proposal_line_id.amount_reserved + self.proposal_line_id.amount_paid)
            if self.amount_total < 0:
                self.amount_total = 0