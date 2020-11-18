# 1 : imports of python lib
import calendar
from datetime import datetime
# 2 :  imports of odoo
from openerp import api, fields, models
from openerp import SUPERUSER_ID
from openerp.exceptions import Warning
# 3 :  imports from odoo modules

class TedsCollectingCancel(models.Model):
    # Private attributes
    _name = "teds.collecting.cancel"
    _description = 'Collecting AR/AP Cancel'

    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('waiting_for_approval','Waiting For Approval'),
        ('approved','Approved'),
        ('confirm','Confirmed'),
        #('cancel','Cancelled')
    ]

    APPROVAL_STATE_SELECTION = [
        ('b', 'Belum Request'),
        ('rf', 'Request For Approval'),
        ('a', 'Approved'),
        ('r', 'Rejected')
    ]

    # Default methods
    def _get_default_branch(self):
        branch_ids = False
        branch_ids = self.env.user.branch_ids
        if branch_ids and len(branch_ids) == 1 :
            return branch_ids[0].id
        return False

    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()

    # Fields declaration
    name = fields.Char(string='Name', readonly=True)
    date = fields.Date(string='Date', readonly=True, default=_get_default_date)
    branch_id = fields.Many2one('wtc.branch', string='Branch', required=True, default=_get_default_branch)
    division = fields.Selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum')], string='Division', default='Unit', required=True)
    state = fields.Selection(STATE_SELECTION, string='State', readonly=True, default='draft')
    approval_state = fields.Selection(APPROVAL_STATE_SELECTION, string='Approval State', readonly=True, default='b')
    approval_ids = fields.One2many('wtc.approval.line', 'transaction_id', string='Approval', domain=[('form_id','=','teds.collecting.cancel')])
    collecting_id = fields.Many2one('teds.collecting', string='Collecting', required=True)
    move_id = fields.Many2one('account.move', string='Journal Entries')
    reason = fields.Text(string='Reason', required=True)
    confirm_uid = fields.Many2one('res.users', string="Confirmed by")
    confirm_date = fields.Datetime('Confirmed on')

    # compute and search fields, in the same order that fields declaration

    # Constraints and onchanges
    _sql_constraint = [
        ('unique_teds_collecting_cancel_id', 'unique(collecting_id)', 'Collecting pernah diinput sebelumnya !')
    ]

    # CRUD methods
    @api.model
    def create(self, values):
        collecting = self.env['teds.collecting'].browse(values['collecting_id'])
        values['name'] = 'X' + collecting.name 
        values['date'] = self._get_default_date()

        return super(TedsCollectingCancel, self).create(values)

    @api.multi
    def unlink(self, context=None):
        for tc in self :
            if tc.state != 'Draft' :
                raise Warning('Transaksi yang berstatus selain Draft tidak bisa dihapus.')
        return super(TedsCollectingCancel, self).unlink()

    @api.model
    def copy(self):
        raise Warning('Transaksi ini tidak dapat diduplikat.')
        return super(TedsCollectingCancel, self).copy()

    # Action methods
    @api.multi
    def action_request_approval(self):
        self.validity_check()
        self.env['wtc.approval.matrixbiaya'].request_by_value(self, 5)
        self.write({'state':'waiting_for_approval', 'approval_state':'rf'})

    @api.multi
    def action_approve(self):
        approval_sts = self.env['wtc.approval.matrixbiaya'].approve(self)
        if approval_sts == 1 :
            self.write({'approval_state':'a', 'state':'approved'})
        elif approval_sts == 0 :
            raise Warning('User tidak termasuk group Approval !')

    @api.multi
    def action_confirm(self):
        self.ensure_one()

        if self.state != 'approved' :
            raise Warning ('Silahkan approve transaksi terlebih dahulu.')

        self.validity_check()

        branch_config = self.env['wtc.branch.config'].search([
            ('branch_id','=',self.branch_id.id)
            ])
        if not branch_config :
            raise Warning('Tidak ditemukan konfigurasi jurnal cabang, silahkan konfigurasi terlebih dahulu.')
        if not branch_config.journal_collecting_id :
            raise Warning('Konfigurasi jurnal collecting belum lengkap, silahkan konfigurasi terlebih dahulu.')
        journal_id = branch_config.journal_collecting_id.id

        today = self._get_default_date()
        period_id = self.env['account.period'].find(today).id

        move_id = self.env['account.move'].sudo().create({
            'journal_id': journal_id,
            'line_id': [],
            'period_id': period_id,
            'date': today,
            'name': self.name,
            'ref': self.collecting_id.name
            })

        ids_to_rec = []

        for move_line in self.collecting_id.move_id.line_id :
            new_line_id = move_line.sudo().copy({
                'move_id': move_id.id,
                'debit': move_line.credit,
                'credit': move_line.debit,
                'name': self.name,
                'ref': self.collecting_id.name,
                'tax_amount': -1 * move_line.tax_amount,
                'date_created': today,
                'date_maturity': today,
                })
            ids_to_rec.append([move_line.id, new_line_id.id])

            move_line.reconcile_id.unlink()

        if branch_config.journal_collecting_id.entry_posted :
            move_id.post()
        else :
            move_id.validate()
        for id_to_rec in ids_to_rec :
            self.pool.get('account.move.line').reconcile(self._cr,self._uid,id_to_rec)

        self.write({
            'move_id': move_id.id,
            'date': today,
            'state': 'confirm',
            'confirm_date': today,
            'confirm_uid': self._uid,
            })

        self.collecting_id.sudo().write({
            'state': 'cancel',
            'cancel_uid': self._uid,
            'cancel_date': today,
            })

    # Business methods
    def validity_check(self):
        if self.collecting_id.state != 'confirm' :
            raise Warning('Tidak bisa cancel, status Collecting bukan Confirmed !')

        if self.collecting_id.move_line_id.reconcile_id or self.collecting_id.move_line_id.reconcile_partial_id :
            raise Warning('Tidak bisa cancel, collecting sudah di reconcile !')

