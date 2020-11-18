from datetime import datetime
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm, Warning, ValidationError

class teds_dn_nc(models.Model):
    _inherit = "wtc.dn.nc"

    # 
    @api.depends('proposal_id.state','proposal_id.approval_state','amount_limit','amount')
    def _compute_proposal_state(self):
        if self.proposal_id:
            if self.proposal_id.approval_state == 'r' and self.state in ['draft','waiting_for_approval','approved']:
                self.proposal_state = 'reject'
            elif self.proposal_id.state == 'close' and self.state in ['draft','waiting_for_approval','approved']:
                self.proposal_state = 'close'
            else:
                if self.amount_limit and self.amount:
                    if self.amount < self.amount_limit:
                        self.proposal_state = 'under'
                    elif self.amount == self.amount_limit:
                        self.proposal_state = 'on'
                    elif self.amount > self.amount_limit:
                        self.proposal_state = 'over'

    proposal_id = fields.Many2one('teds.proposal', string='Nomor Proposal')
    amount_limit = fields.Float(string='Limit Proposal', digits=dp.get_precision('Product Price'))
    proposal_state = fields.Selection([
        ('under','UNDER BUDGET'),
        ('on','ON BUDGET'),
        ('over','OVER BUDGET'),
        ('reject','REJECTED'),
        ('close','CLOSED')
    ], string='Status Proposal', compute='_compute_proposal_state')

    MIN_LIMIT = 10000000 # COO

    @api.constrains('amount')
    def _check_proposal_amount(self):
        if self.proposal_id and self.amount > self.amount_limit:
            raise ValidationError('Total amount tidak boleh melebihi limit proposal.')

    def _check_proposal_state(self):
        if self.proposal_id.state == 'reject':
            raise Warning('Status %s REJECTED' % (self.proposal_id.name))
        elif self.proposal_id.state == 'close':
            raise Warning('Status %s CLOSED' % (self.proposal_id.name))

    # rewrite branch_onchange_payment_request() menggunakan new API
    # BACKGROUND: on_change .xml menghalangi jalannya onchange dari .py
    # EXAMPLE: domain dan value proposal_id tidak berubah ketika onchange branch_id
    # TESTING done, RESULT OK
    @api.multi
    @api.onchange('branch_id')
    def branch_onchange_payment_request(self):
        if self.branch_id:
            branch_config =self.env['wtc.branch.config'].search([('branch_id','=',self.branch_id.id)])
            # branch_config_browse = self.env['wtc.branch.config'].browse(branch_config)
            journal_id = branch_config.wtc_payment_request_account_id
            account_id = branch_config.wtc_payment_request_account_id.default_credit_account_id.id
            if not journal_id:
                raise except_orm('Warning!', 'Konfigurasi jurnal cabang belum dibuat, silahkan setting dulu!')
            if not account_id :
                raise except_orm('Warning!', 'Konfigurasi jurnal account cabang belum dibuat, silahkan setting dulu!')
            if journal_id.currency:
                currency_id = journal_id.currency.id
            else:
                currency_id = journal_id.company_id.currency_id.id
                
            today = self._get_default_date()
            period_id = self.env['account.period'].find(today)
            self.account_id = account_id
            self.journal_id = journal_id.id if journal_id else journal_id       
            self.period_id = period_id.id if period_id else False
            self.currency_id = currency_id 
            self.company_id = journal_id.company_id.id

    @api.multi
    @api.onchange('transaksi')
    def transaksi_change(self):
        self.jenis_transaksi_id = False
        self.proposal_id = False

    @api.onchange('branch_id','division','partner_id')
    def _reset_line(self):
        self.line_dr_ids = []

    @api.onchange('branch_id','division')
    def _onchange_proposal_id(self):
        # print "_ONCHANGE_PROPOSAL_ID"
        # print "branch_id >>>>>>> ", self.branch_id.id
        # print "division >>>>>>> ", self.division
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
    def _onchange_name_and_limit(self):
        self.line_dr_ids = []
        self.name = False
        self.amount_limit = 0
        if self.proposal_id:
            self.name = self.proposal_id.event
            self.update_proposal_limit()

    @api.multi
    def request_approval(self):
        # import ipdb
        # ipdb.set_trace()
        if self.proposal_id:
            self._check_proposal_state()
            # check latest limit proposal
            self.update_proposal_limit()
            self._check_proposal_amount()
            # setup item proposal
            item_update = []
            for x in self.line_dr_ids:
                amount_reserved = x.proposal_line_id.suspend_security().amount_reserved
                item_update.append([1, x.proposal_line_id.id, {
                    'amount_reserved': amount_reserved + x.amount,
                }])
            # update proposal
            try:
                self.proposal_id.suspend_security().write({'item_ids': item_update})
            except Exception:
                self._cr.rollback()
                raise Warning('Terjadi kesalahan saat update proposal %s.' % (self.proposal_id.suspend_security().name))
        return super(teds_dn_nc, self).request_approval()

    @api.multi
    def proforma_voucher(self):
        confirm_nc = super(teds_dn_nc, self).proforma_voucher()
        if confirm_nc and self.proposal_id:
            self._check_proposal_state()
            # import ipdb
            # ipdb.set_trace()
            try:
                # create listing pembayaran
                self.env['teds.proposal.payment'].suspend_security().create({
                    'proposal_id': self.proposal_id.id,
                    'payment_num': str(self.number),
                    'payment_model_id': self.env['ir.model'].suspend_security().search([('model','=',str(self.__class__.__name__))]).id,
                    'payment_transaction_id': self.id,
                    'payment_date': self.date,
                    'payment_amount': self.amount
                })
                # update item proposal
                item_update = []
                for x in self.line_dr_ids:
                    amount_reserved = x.proposal_line_id.suspend_security().amount_reserved
                    amount_paid = x.proposal_line_id.suspend_security().amount_paid
                    item_update.append([1, x.proposal_line_id.id, {
                        'amount_reserved': amount_reserved - x.amount,
                        'amount_paid': amount_paid + x.amount,
                        'payment_ids': [[0, 0, {
                            'name': x.voucher_id.number,
                            'supplier_id': x.voucher_id.partner_id.id,
                            'jenis_pembayaran': 'T',
                            'amount_paid': x.amount,
                        }]]
                    }])
                try:
                    self.proposal_id.suspend_security().write({'item_ids': item_update})
                except Exception:
                    self._cr.rollback()
                    raise Warning('Terjadi kesalahan saat update proposal %s.' % (self.proposal_id.suspend_security().name))
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

    @api.multi
    def action_cancel_rfa_form(self):
        form_id = self.env.ref('teds_proposal.view_teds_dn_nc_cancel_rfa_form').id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'teds.dn.nc.cancel.rfa',
            'name': 'Cancel RFA Payment Request',
            'views': [(form_id, 'form')],
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': False,
            'target': 'new',
            'context': {'default_dn_nc_id': self.id}
        }

    @api.multi
    def action_reject_form(self):
        form_id = self.env.ref('teds_proposal.view_teds_dn_nc_reject_form').id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'teds.dn.nc.reject',
            'name': 'Reject Payment Request',
            'views': [(form_id, 'form')],
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': False,
            'target': 'new',
            'context': {'default_dn_nc_id': self.id}
        }

    @api.multi
    def action_cancel_approval_form(self):
        form_id = self.env.ref('teds_proposal.view_teds_dn_nc_cancel_approval_form').id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'teds.dn.nc.cancel.approval',
            'name': 'Cancel Approval Payment Request',
            'views': [(form_id, 'form')],
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': False,
            'target': 'new',
            'context': {'default_dn_nc_id': self.id}
        }

class teds_dn_nc_line(models.Model):
    _inherit = "wtc.dn.nc.line"

    proposal_line_id = fields.Many2one('teds.proposal.line', string='Item Proposal', ondelete='restrict')

    _sql_constraints = [
        ('proposal_line_id_uniq', 'unique(voucher_id, proposal_line_id)', "Item proposal tidak boleh duplikat.")]

    @api.constrains('amount')
    def _check_amount(self):
        for record in self:
            if record.amount <= 0:
                raise ValidationError("Nilai bill tidak boleh 0.")

    @api.onchange('proposal_line_id')
    def _onchange_name_and_amount(self):
        self.name = False
        self.amount = 0
        if self.proposal_line_id:
            self.name = self.proposal_line_id.description
            self.amount = self.proposal_line_id.amount_total - (self.proposal_line_id.amount_reserved + self.proposal_line_id.amount_paid)
            if self.amount <= 0:
                self.amount = 0

class teds_dn_nc_cancel_rfa(models.TransientModel):
    _name = "teds.dn.nc.cancel.rfa"
    
    dn_nc_id = fields.Many2one('wtc.dn.nc', string='ID Payment Request', ondelete='cascade')
    cancel_rfa_reason = fields.Text(string='Alasan Cancel')

    @api.multi
    def action_cancel_rfa(self):
        # import ipdb
        # ipdb.set_trace()
        if self.env['wtc.approval.matrixbiaya'].suspend_security().cancel_approval(self.dn_nc_id, self.cancel_rfa_reason):
            try:
                self.dn_nc_id.suspend_security().write({'state': 'draft','approval_state':'b'})
            except Exception:
                self._cr.rollback()
                raise Warning('Terjadi kesalahan saat update Payment Request %s.' % (self.dn_nc_id.suspend_security().number))
            if self.dn_nc_id.proposal_id:
                item_update = []
                for x in self.dn_nc_id.line_dr_ids:
                    amount_reserved = x.proposal_line_id.suspend_security().amount_reserved
                    item_update.append([1, x.proposal_line_id.id, {
                        'amount_reserved': amount_reserved - x.amount,
                    }])
                try:
                    self.dn_nc_id.proposal_id.suspend_security().write({'item_ids': item_update})
                except Exception:
                    self._cr.rollback()
                    raise Warning('Terjadi kesalahan saat update proposal %s.' % (self.dn_nc_id.proposal_id.suspend_security().name))
        else:
            raise Warning("User tidak termasuk group approval.")
        return True

class teds_dn_nc_reject(models.TransientModel):
    _name = "teds.dn.nc.reject"
    
    dn_nc_id = fields.Many2one('wtc.dn.nc', string='ID Payment Request', ondelete='cascade')
    reject_reason = fields.Text(string='Alasan Reject')

    @api.multi
    def action_reject(self):
        # import ipdb
        # ipdb.set_trace()
        if self.env['wtc.approval.matrixbiaya'].suspend_security().reject(self.dn_nc_id, self.reject_reason):
            try:
                self.dn_nc_id.suspend_security().write({'state': 'draft','approval_state':'r'})
            except Exception:
                self._cr.rollback()
                raise Warning('Terjadi kesalahan saat update Payment Request %s.' % (self.dn_nc_id.suspend_security().number))
            if self.dn_nc_id.proposal_id:
                item_update = []
                for x in self.dn_nc_id.line_dr_ids:
                    amount_reserved = x.proposal_line_id.suspend_security().amount_reserved
                    item_update.append([1, x.proposal_line_id.id, {
                        'amount_reserved': amount_reserved - x.amount,
                    }])
                try:
                    self.dn_nc_id.proposal_id.suspend_security().write({'item_ids': item_update})
                except Exception:
                    self._cr.rollback()
                    raise Warning('Terjadi kesalahan saat update proposal %s.' % (self.dn_nc_id.proposal_id.suspend_security().name))
        else:
            raise Warning("User tidak termasuk group approval.")
        return True

class teds_dn_nc_cancel_approval(models.TransientModel):
    _name = "teds.dn.nc.cancel.approval"

    dn_nc_id = fields.Many2one('wtc.dn.nc', string='ID Payment Request', ondelete='cascade')
    cancel_approval_reason = fields.Text(string='Alasan Cancel')

    @api.multi
    def action_cancel_approval(self):
        # import ipdb
        # ipdb.set_trace()
        # Copy logic of
        # wtc.approval.cancel.after.approve wtc_cancel_approval()
        reason = "batal approve: " + self.cancel_approval_reason
        form_id = self.env['ir.model'].suspend_security().search([('model','=', self.dn_nc_id.__class__.__name__)]).id
        try:
            for approval_line in self.dn_nc_id.approval_ids:
                approval_line.write({'sts':'4'})
            self.env['wtc.approval.line'].suspend_security().create({
                'form_id': form_id,
                'sts':'4', 
                'transaction_id': self.dn_nc_id.id, 
                'pelaksana_id': self._uid, 
                'reason': reason,
                'tanggal': datetime.now(),
                'division': self.dn_nc_id.division,
                'branch_id': self.dn_nc_id.branch_id.id
            })
            self.dn_nc_id.suspend_security().write({'state': 'draft','approval_state':'b'})
        except Exception:
            self._cr.rollback()
            raise Warning('Terjadi kesalahan saat update Payment Request %s.' % (self.dn_nc_id.suspend_security().number))
        if self.dn_nc_id.proposal_id:
            item_update = []
            for x in self.dn_nc_id.line_dr_ids:
                amount_reserved = x.proposal_line_id.suspend_security().amount_reserved
                item_update.append([1, x.proposal_line_id.id, {
                    'amount_reserved': amount_reserved - x.amount,
                }])
            try:
                self.dn_nc_id.proposal_id.suspend_security().write({'item_ids': item_update})
            except Exception:
                self._cr.rollback()
                raise Warning('Terjadi kesalahan saat update proposal %s.' % (self.dn_nc_id.proposal_id.suspend_security().name))
        return True
