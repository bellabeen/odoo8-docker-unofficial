from openerp import models, fields, api
from datetime import datetime
from openerp.osv import osv
from openerp import workflow

class wtc_cancel_bank_transfer(models.Model):
    _name = "wtc.cancel.bank.transfer"
    _description = "Bank Transfer Cancel"
    
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
    bank_transfer_id = fields.Many2one('wtc.bank.transfer', 'Bank Transfer')
    division = fields.Selection([
                                 ('Unit','Unit'),
                                 ('Sparepart','Sparepart'),
                                 ('Umum','Umum'),
                                  ('Finance','Finance')
                                 ],required=True,string='Division')
    date = fields.Date('Date',default=_get_default_date)
    confirm_uid = fields.Many2one('res.users', string="Confirmed by")
    confirm_date = fields.Datetime('Confirmed on')
    approval_ids = fields.One2many('wtc.approval.line', 'transaction_id', string="Approval", domain=[('form_id','=','wtc.cancel.bank.transfer')])
    approval_state = fields.Selection([
        ('b','Belum Request'),
        ('rf','Request For Approval'),
        ('a','Approved'),
        ('r','Rejected')
        ], 'Approval State', readonly=True, default='b')
    move_id = fields.Many2one('account.move', string='Account Entry', copy=False)
    move_ids = fields.One2many('account.move.line', related='move_id.line_id', string='Journal Items', readonly=True)
    period_id = fields.Many2one('account.period', string="Period")
    reason = fields.Text('Reason',required=True)
    
    _sql_constraints = [
        ('unique_bank_transfer_id', 'unique(bank_transfer_id)', 'Bank Transfer pernah diinput sebelumnya !')
        ]
    
    @api.model
    def create(self, values, context=None):
        settlement_id = self.env['wtc.bank.transfer'].search([('id','=',values['bank_transfer_id'])])
        values['name'] = "X" + settlement_id.name
        values['date'] = self._get_default_date_model()
        return super(wtc_cancel_bank_transfer, self).create(values)
    
    def unlink(self, cr, uid, ids, context=None):
        bt_cancel_id = self.browse(cr, uid, ids, context=context)
        if bt_cancel_id.state != 'draft':
            raise osv.except_osv(('Invalid action !'), ('Tidak bisa dihapus jika state bukan Draft !'))
        return super(wtc_cancel_bank_transfer, self).unlink(cr, uid, ids, context=context)
    
    @api.multi
    def validity_check(self):
        if self.bank_transfer_id.state=='cancel':
            raise osv.except_osv(('Perhatian !'), ('Settlement %s sudah dibatalkan !') % (self.bank_transfer_id.name))
    
    @api.multi
    def create_account_move_line(self, move_id):
        for line_id in self.bank_transfer_id.move_id.line_id :
            new_line_id = line_id.copy({
                'move_id': move_id.id,
                'debit': line_id.credit,
                'credit': line_id.debit,
                'name': self.name,
                'ref': line_id.ref,
                'tax_amount': line_id.tax_amount * -1,
                'bank_reconcile_id': line_id.bank_reconcile_id.id
                })
    
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
    def confirm(self):
        if self.state == 'approved' :
            self.write({'state':'confirmed', 'date':self._get_default_date(), 'confirm_uid':self._uid, 'confirm_date':datetime.now(), 'period_id':self.env['account.period'].find(dt=self._get_default_date().date()).id})
            self.validity_check()
            obj_acc_move = self.env['account.move']
            acc_move_line_obj = self.pool.get('account.move.line')
            branch_config_id = self.env['wtc.branch.config'].search([('branch_id','=',self.branch_id.id)])
            journal_id = branch_config_id.bank_transfer_cancel_journal_id
            if not journal_id :
                raise osv.except_osv(("Perhatian !"), ("Tidak ditemukan Journal Pembatalan Settlement di Branch Config, silahkan konfigurasi ulang !"))
            
            if self.bank_transfer_id.move_id:
                move_id = obj_acc_move.create({
                    'name': self.name,
                    'journal_id': journal_id.id,
                    'line_id': [],
                    'period_id': self.period_id.id,
                    'date': self._get_default_date(),
                    'ref': self.bank_transfer_id.name
                    })
                to_reconcile_ids = self.create_account_move_line(move_id)
                self.write({'move_id':move_id.id})
                if journal_id.entry_posted :
                    move_id.button_validate()
            if self.bank_transfer_id.reconcile_ids:
                for item in self.bank_transfer_id.reconcile_ids:
                    item.move_line_id.write({'bank_reconcile_id':False})
                    
            for line in self.bank_transfer_id.line_ids:
                if line.reimbursement_id:
                    line.reimbursement_id.write({'state':'approved'})
            self.bank_transfer_id.write({
                'state':'cancel',
                'cancel_uid': self._uid,
                'cancel_date': datetime.now(),
            })
            
         
            #print self.settlement_id.signal_workflow('settlement_cancel')
            #nyeahhh
        #return workflow.trg_validate(self._uid, 'wtc.settlement', self.settlement_id.id, 'settlement_cancel', self._cr) 
    #self.settlement_id.signal_workflow('settlement_cancel')