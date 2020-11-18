from openerp import models, fields, api
from datetime import datetime
from openerp.osv import osv
    
class birojasa_cancel(models.Model):
    _name = "birojasa.cancel"
    _description = "Birojasa Cancel"
    
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
    birojasa_id = fields.Many2one('wtc.proses.birojasa', 'Tagihan Birojasa')
    division = fields.Selection([('Unit','Unit')], 'Division',default='Unit')
    date = fields.Date('Date',default=_get_default_date)
    confirm_uid = fields.Many2one('res.users', string="Confirmed by")
    confirm_date = fields.Datetime('Confirmed on')
    approval_ids = fields.One2many('wtc.approval.line', 'transaction_id', string="Approval", domain=[('form_id','=','birojasa.cancel')])
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
        ('unique_birojasa_id', 'unique(birojasa_id)', 'Birojasa pernah diinput sebelumnya !')
        ]
    
    @api.model
    def create(self, values, context=None):
        birojasa_id = self.env['wtc.proses.birojasa'].search([('id','=',values['birojasa_id'])])
        values['name'] = "X" + birojasa_id.name
        values['date'] = self._get_default_date_model()
        values['period_id'] = self.env['account.period'].find(dt=self._get_default_date_model().date()).id
        return super(birojasa_cancel, self).create(values)
    
    def unlink(self, cr, uid, ids, context=None):
        birojasa_cancel_id = self.browse(cr, uid, ids, context=context)
        if birojasa_cancel_id.state != 'draft':
            raise osv.except_osv(('Invalid action !'), ('Tidak bisa dihapus jika state bukan Draft !'))
        return super(birojasa_cancel, self).unlink(cr, uid, ids, context=context)
    
    @api.multi
    def create_account_move_line(self, move_id):
        ids_to_reconcile = []
        invoice_bbn = []
        invoice_pp = []
        obj_invoice = self.env['account.invoice']
        obj_reconcile = self.env['account.move.reconcile']
        obj_move_line = self.env['account.move.line']
        invoice_ids = []
        
        invoice_tagihan_ids = obj_invoice.search([
                                          ('origin','=',self.birojasa_id.name),
                                          ('type','=','in_invoice')
                                          ])
        if not invoice_tagihan_ids :
            raise osv.except_osv(("Perhatian !"), ("Invoice Tagihan birojasa tidak ditemukan !"))
        invoice_ids.append(invoice_tagihan_ids)
        
        for line in self.birojasa_id.proses_birojasa_line :
            if line.name.invoice_bbn :
                invoice_bbn.append(line.name.invoice_bbn)
            # if line.name.inv_pajak_progressive_id :
            #     if line.name.inv_pajak_progressive_id not in invoice_ids :
            #         invoice_ids.append(line.name.inv_pajak_progressive_id)
                
        if invoice_bbn :      
            for invoice_id in invoice_bbn :
                for line_id in invoice_id.move_id.line_id :
                    move_lines = []
                    if line_id.reconcile_id :
                        move_lines = [move_line.id for move_line in line_id.reconcile_id.line_id]
                        line_id.reconcile_id.unlink()
                    elif line_id.reconcile_partial_id :
                        move_lines = [move_line.id for move_line in line_id.reconcile_partial_id.line_partial_ids]
                        line_id.reconcile_partial_id.unlink()
                    if move_lines :
                        move_lines.remove(line_id.id)
                        
        if invoice_ids :      
            for invoice_id in invoice_ids :
                for line_id in invoice_id.move_id.line_id :
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
    def cek_penyerahan_stnk_bpkb(self):
        for line in self.birojasa_id.proses_birojasa_line :
            if line.name.penyerahan_stnk_id or line.name.penyerahan_notice_id or line.name.penyerahan_polisi_id :
                raise osv.except_osv(('Perhatian !'), ("Engine %s sudah ditarik dalam penerimaan STNK, silahkan cancel terlebih dahulu!")%(line.name.name))
            if line.name.penyerahan_bpkb_id :
                raise osv.except_osv(('Perhatian !'), ("Engine %s sudah ditarik dalam penerimaan BPKB, silahkan cancel terlebih dahulu!")%(line.name.name))   
    
    @api.multi
    def cek_supplier_invoice(self):
        invoice = self.env['account.invoice']
        invoice_ids = invoice.search([
                             ('name','=',self.birojasa_id.name),
                             ('type','=','in_invoice')
                             ])    
        if not invoice_ids :
            raise osv.except_osv(('Perhatian !'), ("Invoice tidak ditemukan"))
        message = ""
        for invoice_id in invoice_ids :
                if invoice_id.state == 'paid' :
                    message += invoice_id.number + ", "
        if message :
            raise osv.except_osv(("Perhatian !"), ("Invoice Birojasa " + message + "sudah dibayar, silahkan lakukan pembatalan Customer/Supplier Payment terlebih dahulu !"))        
         
    @api.multi
    def cek_invoice_pajak_progressive(self):
        invoice = self.env['account.invoice']
        invoice_ids = invoice.search([
                                     ('origin','=',self.birojasa_id.name),
                                     ('type','=','out_invoice'),
                                     # ('state','!=','paid')
                                     ])
        if invoice_ids :
            message = ""
            for invoice_id in invoice_ids :
                for line_id in invoice_id.move_id.line_id :
                    if line_id.reconcile_id or line_id.reconcile_partial_id :
                        message += invoice_id.number + ", "
            if message :
                raise osv.except_osv(("Perhatian !"), ("Invoice Progressive" + message + "sudah dibayar, silahkan lakukan pembatalan Customer/Supplier Payment terlebih dahulu !"))        
        
    @api.multi
    def validity_check(self):
        #Note : Approve dalam tagihan birojasa adalah 'Process Conf
        if self.birojasa_id.state not in ('approved','done') :
            raise osv.except_osv(('Perhatian !'), ("Tidak bisa cancel, status Birojasa selain 'Done' dan 'Process Confirm' !"))
        self.cek_penyerahan_stnk_bpkb()
        self.cek_invoice_pajak_progressive()
        self.cek_supplier_invoice()
        
    @api.multi
    def confirm(self):
        if self.state == 'approved' :
            self.validity_check()
            self.write({'state':'confirmed', 'date':self._get_default_date(), 'confirm_uid':self._uid, 'confirm_date':datetime.now(), 'period_id':self.env['account.period'].find(dt=self._get_default_date().date()).id})
            self.birojasa_id.is_cancelled = True
            obj_acc_move = self.env['account.move']
            acc_move_line_obj = self.env['account.move.line']
            branch_config_id = self.env['wtc.branch.config'].search([('branch_id','=',self.branch_id.id)])
            journal_id = branch_config_id.birojasa_cancel_journal_id
            if not journal_id :
                raise osv.except_osv(("Perhatian !"), ("Tidak ditemukan Journal Pembatalan Tagihan Birojasa di Branch Config, silahkan konfigurasi ulang !"))
            move_id = obj_acc_move.create({
                'name': self.name,
                'journal_id': journal_id.id,
                'line_id': [],
                'period_id': self.period_id.id,
                'date': self._get_default_date(),
                'ref': self.birojasa_id.name,
                })
            to_reconcile_ids = self.create_account_move_line(move_id)
            for to_reconcile in to_reconcile_ids :
                self.reconcile_move(to_reconcile)
            self.write({'move_id':move_id.id})
            if journal_id.entry_posted :
                move_id.button_validate()
            self.birojasa_id.signal_workflow('birojasa_cancel')

        return True    
    
    def reconcile_move(self,cr,uid,ids,to_reconcile,context=None):
        if to_reconcile :
            self.pool.get('account.move.line').reconcile(cr,uid,to_reconcile)
        return True