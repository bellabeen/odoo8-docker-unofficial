# 1 : imports of python lib
import calendar
from datetime import datetime
# 2 :  imports of odoo
from openerp import api, fields, models
from openerp import SUPERUSER_ID
from openerp.exceptions import Warning
# 3 :  imports from odoo modules

class TedsCollecting(models.Model):
    # Private attributes
    _name = "teds.collecting"
    _description = 'Collecting AR/AP'

    STATE_SELECTION = [
        ('draft', 'Draft'),
        #('waiting_for_approval','Waiting For Approval'),
        ('confirm','Confirmed'),
        ('cancel','Cancelled')
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

    def _get_default_date_start(self):
        now = self._get_default_date()
        return datetime(now.year, now.month, 1)

    def _get_default_date_end(self):
        now = self._get_default_date()
        return datetime(now.year, now.month, calendar.monthrange(now.year, now.month)[1])

    # Fields declaration
    name = fields.Char(string='Name', readonly=True)
    date = fields.Date(string='Date', readonly=True, default=_get_default_date)
    branch_id = fields.Many2one('wtc.branch', string='Branch', required=True, default=_get_default_branch)
    division = fields.Selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum')], string='Division', default='Unit', required=True)
    state = fields.Selection(STATE_SELECTION, string='State', readonly=True, default='draft')
    partner_id = fields.Many2one('res.partner', string='Partner', required=True, domain=['|',('customer','=',True),('supplier','=',True)])
    type = fields.Selection([('receivable','Receivable'),('payable','Payable')], string='Type', default='receivable', required=True)
    account_id = fields.Many2one('account.account', string='Account', required=True)
    journal_id = fields.Many2one('account.journal', string='Journal')
    date_start = fields.Date(string='Effective Date', required=True, default=_get_default_date_start)
    date_end = fields.Date(string='Date End', required=True, default=_get_default_date_end)
    date_maturity = fields.Date(string='Due Date')
    move_id = fields.Many2one('account.move', string='Journal Entries')
    move_line_id = fields.Many2one('account.move.line', string='Journal Items')
    move_line_ids = fields.Many2many('account.move.line', 'wtc_collecting_move_line_rel', 'collecting_id', 'move_line_id', string='Move Lines')
    description = fields.Char(string='Description', required=True)
    amount = fields.Float(string='Amount')
    confirm_uid = fields.Many2one('res.users', string="Confirmed by")
    confirm_date = fields.Datetime('Confirmed on')
    cancel_uid = fields.Many2one('res.users', string="Cancelled by")
    cancel_date = fields.Datetime('Cancelled on')

    # compute and search fields, in the same order that fields declaration

    # Constraints and onchanges
    #TODO: add contraint on teds_collecting_move_line_rel, move_line_id ga boleh duplikat

    @api.onchange('branch_id', 'division', 'partner_id', 'date', 'date_start', 'date_end', 'type', 'account_id', 'journal_id')
    def _onchange_branch_division_partner_date_account_journal(self):
        self.move_line_ids = False
        self.amount = 0.0

    @api.onchange('type')
    def _onchange_type(self):
        self.account_id = False

    # CRUD methods
    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].get_per_branch(values['branch_id'], 'CL')
        values['date'] = self._get_default_date()

        return super(TedsCollecting, self).create(values)

    @api.multi
    def write(self, values):
        # set move_line_ids to empty if there's any changes on selected fields.
        if 'move_line_ids' not in values :
            for key in values :
                if key in ('branch_id', 'division', 'partner_id', 'date_start', 'date_end', 'account_id', 'journal_id') :
                    values.update({'move_line_ids': [(5,0)], 'amount': 0})
                    break
        return super(TedsCollecting, self).write(values)

    @api.multi
    def unlink(self, context=None):
        for tc in self :
            if tc.state != 'draft' :
                raise Warning('Transaksi yang berstatus selain Draft tidak bisa dihapus.')
        return super(TedsCollecting, self).unlink()

    @api.model
    def copy(self):
        raise Warning('Transaksi ini tidak dapat diduplikat.')
        return super(TedsCollecting, self).copy()

    # Action methods
    @api.multi
    def action_get_detail(self):
        self.ensure_one()
        criteria = [
            ('branch_id','=',self.branch_id.id),
            ('division','=',self.division),
            ('partner_id','=',self.partner_id.id),
            ('account_id','=',self.account_id.id), 
            ('date','>=',self.date_start),
            ('date','<=',self.date_end),
            ('reconcile_id','=',False),
            ('reconcile_partial_id','=',False)]
        if self.journal_id :
            criteria.append(('journal_id','=',self.journal_id.id))
        obj_ids = self.env['account.move.line'].search(criteria)

        amount = 0.0
        ids = [x.id for x in obj_ids]
        for x in obj_ids :
            amount += x.debit + x.credit
        self.write({'move_line_ids': [(6,0,ids)],
            'amount': amount,
            'date': self._get_default_date()})

    @api.multi
    def action_confirm(self):
        self.ensure_one()

        if self.amount <= 0.0 :
            raise Warning('Nilai total AR/AP kurang dari 0!')
        if len(self.move_line_ids) < 1 :
            raise Warning('Klik button Get Detail terlebih dahulu.')

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
            'ref': self.name
            })

        ids_to_rec = []
        amt = 0.0
        warning = ""
        for move_line in self.move_line_ids :
            if move_line.reconcile_id or move_line.reconcile_partial_id :
                warning += "- %s \r\n" % move_line.name
            amt += move_line.debit - move_line.credit
            new_line_id = move_line.sudo().copy({
                'move_id': move_id.id,
                'debit': move_line.credit,
                'credit': move_line.debit,
                'name': self.description,
                'ref': self.name,
                'tax_amount': -1 * move_line.tax_amount,
                'date_created': today,
                'date_maturity': today,
                })
            ids_to_rec.append([move_line.id, new_line_id.id])
        if warning != "" :
            raise Warning("Transaksi berikut sudah di reconcile (sebagian / penuh):\r\n %s " % warning)

        new_col = self.env['account.move.line'].sudo().create({
            'move_id': move_id.id,
            'debit': amt if amt > 0 else 0,
            'credit': abs(amt) if amt < 0 else 0,
            'name': self.description,
            'ref': self.name,
            'account_id': self.account_id.id,
            'partner_id': self.partner_id.id,
            'branch_id': self.branch_id.id,
            'division': self.division,
            'date_maturity': self.date_maturity if self.date_maturity else today,
            })

        for id_to_rec in ids_to_rec :
            self.pool.get('account.move.line').reconcile(self._cr, SUPERUSER_ID, id_to_rec)

        self.write({
            'move_id': move_id.id,
            'move_line_id': new_col.id,
            'date': today,
            'state': 'confirm',
            'confirm_date': today,
            'confirm_uid': self._uid,
            })

    # Business methods
