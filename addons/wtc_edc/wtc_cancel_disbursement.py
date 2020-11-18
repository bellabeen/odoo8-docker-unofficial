from openerp import models, fields, api
from datetime import datetime
from openerp.osv import osv
from openerp import workflow

class wtc_cancel_disbursement(models.Model):
    _name = "wtc.cancel.disbursement"
    _description = "Disbursment EDC Cancel"
    
    @api.multi
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date()
    
    @api.model
    def _get_default_date_model(self):
        return self.env['wtc.branch'].get_default_date_model()
    
    name = fields.Char('Name')
    state = fields.Selection([
        ('draft','Draft'),
        ('waiting_for_approval','Waiting For Approval'),
        ('approved','Approved'),
        ('confirmed','Confirmed'),
        ], 'State', default='draft')
    branch_id = fields.Many2one('wtc.branch', 'Branch')
    disbursement_id = fields.Many2one('wtc.disbursement', 'Disbursement EDC')
    division = fields.Selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum')], 'Division')
    date = fields.Date('Date',default=_get_default_date)
    confirm_uid = fields.Many2one('res.users', string="Confirmed by")
    confirm_date = fields.Datetime('Confirmed on')
    approval_ids = fields.One2many('wtc.approval.line', 'transaction_id', string="Approval", domain=[('form_id','=','wtc.cancel.disbursement')])
    approval_state = fields.Selection([
        ('b','Belum Request'),
        ('rf','Request For Approval'),
        ('a','Approved'),
        ('r','Rejected')
        ], 'Approval State', readonly=True, default='b')
    move_id = fields.Many2one('account.move', string='Account Entry', copy=False)
    move_ids = fields.One2many('account.move.line', related='move_id.line_id', string='Journal Items', readonly=True)
    period_id = fields.Many2one('account.period', string="Period")
    reason = fields.Text('Reason')
    
    _sql_constraints = [
        ('unique_disbursment_id', 'unique(disbursement_id)', 'Transaksi ini sudah pernah diinput sebelumnya !')
        ]
    
    @api.model
    def create(self, values, context=None):
        disbursement_id = self.env['wtc.disbursement'].search([('id','=',values['disbursement_id'])])
        values['name'] = "X" + disbursement_id.name
        values['date'] = self._get_default_date_model()
        values['period_id'] = self.env['account.period'].find(dt=self._get_default_date_model().date()).id
        res = super(wtc_cancel_disbursement, self).create(values)
        return res

    
    def unlink(self, cr, uid, ids, context=None):
        disbursement_id = self.browse(cr, uid, ids, context=context)
        if disbursement_id.state != 'draft':
            raise osv.except_osv(('Invalid action !'), ('Tidak bisa dihapus jika state bukan Draft !'))
        return super(wtc_cancel_disbursement, self).unlink(cr, uid, ids, context=context)

    @api.multi
    def create_account_move_line(self, move_id):
        ids_to_reconcile = []
        obj_reconcile = self.env['account.move.reconcile']
        obj_move_line = self.env['account.move.line']

        for line_id in self.disbursement_id.move_ids :
            new_line_id = line_id.copy({
                'move_id': move_id.id,
                'debit': line_id.credit,
                'credit': line_id.debit,
                'name': self.name,
                'ref': line_id.ref,
                'tax_amount': line_id.tax_amount * -1
                })
            if line_id.account_id.reconcile :
                ids_to_reconcile.append([line_id.id,new_line_id.id])
            move_lines = []
            if line_id.reconcile_id :
                move_lines = [move_line.id for move_line in line_id.reconcile_id.line_id]
                line_id.reconcile_id.unlink()
            elif line_id.reconcile_partial_id :
                move_lines = [move_line.id for move_line in line_id.reconcile_partial_id.line_partial_ids]
                line_id.reconcile_partial_id.unlink()
            if move_lines :
                move_lines.remove(line_id.id)
            if len(move_lines) >= 2 :
                obj_move_line.browse(move_lines).reconcile_partial('auto')
#                 obj_move_line.reconcile_partial(self._cr, self._uid, move_lines, type='auto', context=self._context)
        return ids_to_reconcile
    
    @api.multi
    def request_approval(self):
        self.validity_check()
        obj_matrix = self.env['wtc.approval.matrixbiaya']
        obj_matrix.request_by_value(self, 5)
        self.write({'state':'waiting_for_approval', 'approval_state':'rf'})
    
    @api.multi
    def approve(self):
        approval_sts = self.env['wtc.approval.matrixbiaya'].approve(self)
        if approval_sts == 1 :
            self.write({'approval_state':'a','state':'approved'})
        elif approval_sts == 0 :
            raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group Approval !"))
    
    @api.multi
    def validity_check(self):
        if self.disbursement_id.id :
            if self.disbursement_id.state != 'posted' :
                raise osv.except_osv(('Perhatian !'), ("Tidak bisa cancel, status Disbursement bukan Posted !"))
            elif self.disbursement_id.state == 'cancel' :
                raise osv.except_osv(('Perhatian !'), ("Disbursement sudah dibatalkan!"))
            
        
    @api.multi
    def confirm(self):
        if self.state == 'approved' :
            self.validity_check()
            self.write({'state':'confirmed', 'date':self._get_default_date(), 'confirm_uid':self._uid, 'confirm_date':datetime.now(), 'period_id':self.env['account.period'].find(dt=self._get_default_date().date()).id})
            obj_acc_move = self.env['account.move']
            acc_move_line_obj = self.pool.get('account.move.line')
            journal_id = False
            branch_config_id = self.env['wtc.branch.config'].search([('branch_id','=',self.branch_id.id)])
            journal_id = branch_config_id.disbursement_cancel_journal_id
            if not journal_id :
                raise osv.except_osv(("Perhatian !"), ("Tidak ditemukan Journal Pembatalan Disbursement EDC di Branch Config, silahkan konfigurasi ulang !"))
            if self.disbursement_id.move_ids:
                move_id = obj_acc_move.create({
                    'name': self.name,
                    'journal_id': journal_id.id,
                    'line_id': [],
                    'period_id': self.period_id.id,
                    'date': self._get_default_date(),
                    'ref': self.disbursement_id.name
                    })
                to_reconcile_ids = self.create_account_move_line(move_id)
                for to_reconcile in to_reconcile_ids :
                    acc_move_line_obj.reconcile(self._cr, self._uid, to_reconcile)
                self.write({'move_id':move_id.id})
                if journal_id.entry_posted :
                    move_id.button_validate()
                self.disbursement_id.write({'state':'cancel','cancel_uid':self._uid,'cancel_date':datetime.now()})
                
        return True