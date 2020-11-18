from datetime import datetime
from openerp import models, fields, api
from openerp.osv import osv

class wtc_cancel_pajak_progressive(models.Model):
    _name = "wtc.cancel.pajak.progressive"

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

    branch_id = fields.Many2one('wtc.branch', 'Branch',domain=[('pajak_progressive','=',True)])
    pajak_id = fields.Many2one('wtc.pajak.progressive', 'Pajak Progressive', domain="[('state','=','confirmed'),('branch_id','=',branch_id),('division','=',division)]")
    pajak_line_ids = fields.Many2many('wtc.pajak.progressive.line','wtc_cancel_pajak_progressive_rel','cancel_pajak_progressive_id','pajak_line_id',domain="[('pajak_progressive_id','=',pajak_id),('status','=','confirmed')]",string="PPD")
    division = fields.Selection([('Unit','Unit')], 'Division', default='Unit')
    date = fields.Date('Date', default=_get_default_date)
    confirm_uid = fields.Many2one('res.users', string="Confirmed by")
    confirm_date = fields.Datetime('Confirmed on')
    approval_ids = fields.One2many('wtc.approval.line', 'transaction_id', string="Approval", domain=[('form_id','=','wtc.cancel.pajak.progressive')])
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

    @api.onchange('branch_id')
    def onchange_branch_id(self):
        self.pajak_id = False
        self.pajak_line_ids = False


    @api.model
    def create(self,values,context=None):
        pajak_id = self.env['wtc.pajak.progressive'].search([('id','=',values['pajak_id'])])
        values['name'] = "X" + pajak_id.name
        values['date'] = self._get_default_date_model()
        values['period_id'] = self.env['account.period'].find(dt=self._get_default_date_model().date()).id
        return super(wtc_cancel_pajak_progressive,self).create(values)
  
    @api.multi
    def unlink(self):
        if self.state != 'draft':
            raise osv.except_osv(('Invalid action !'),('Tidak bisa dihapus jika state bukan Draft !'))
        return super(wtc_cancel_pajak_progressive,self).unlink()   
    
    @api.multi
    def create_account_move_line(self,move_id,ppd_id):
        ids_to_reconcile = []
        invoice_pp = []
        obj_invoice = self.env['account.invoice']
        obj_reconcile = self.env['account.move.reconcile']
        obj_move_line = self.env['account.move.line']
        invoice_ids = []

        invoice_tagihan_ids = obj_invoice.search([
            ('origin','=',ppd_id.name),
            ('type','=','out_invoice'),
            ('state','!=','paid')
        ])
        if not invoice_tagihan_ids :
            raise osv.except_osv(("Perhatian !"),("Invoice Pajak Progressive tidak ditemukan !"))
        for invoice_tagihan_id in invoice_tagihan_ids:  
            invoice_ids.append(invoice_tagihan_id)
        print "account_inv :",invoice_ids
        if invoice_ids:
            for invoice_id in invoice_ids:
                for line_id in invoice_id.move_id.line_id:
                    print "line_name:", line_id.name
                    new_line_id = line_id.copy({
                        'move_id': move_id.id,
                        'debit': line_id.credit,
                        'credit': line_id.debit,
                        'name': self.name,
                        'ref': line_id.ref,
                        'tax_amount': line_id.tax_amount*-1
                        })
                    if line_id.account_id.reconcile:
                        ids_to_reconcile.append([line_id.id,new_line_id.id])
    
        return ids_to_reconcile
   
    @api.multi
    def request_approval(self):
        self.validity_check()
        obj_matrix = self.env['wtc.approval.matrixbiaya']
        obj_matrix.request_by_value(self,5)
        self.write({'state':'waiting_for_approval','approval_state':'rf'})
    
    @api.multi
    def approve(self):
        approval_sts = self.env['wtc.approval.matrixbiaya'].approve(self)
        if approval_sts == 1:
            self.write({'approval_state':'a','state':'approved'})
        elif approval_sts == 0:
            raise except_osv(("Perhatian !"),("User tidak termasuk group Approval !"))

    @api.multi
    def cek_invoice_pajak_progressive(self):
        for ppd_id in self.pajak_line_ids:
            invoice = self.env['account.invoice'].search([
                ('origin','=',ppd_id.name),
                ('type','=','out_invoice')
            ])
    
            if invoice:
                message =""
                for invoice_id in invoice:
                    for line_id in invoice_id.move_id.line_id:
                        if (line_id.reconcile_id or line_id.reconcile_partial_id):
                            message += invoice_id.number +","
                            
                if message:
                    raise osv.except_osv(("Perhatian !"),("Invoice Pajak Progressive sudah dibayar"))

    
    @api.multi
    def cek_stock_product_lot(self):
        for line in self.pajak_line_ids:
            lot_mesin = line.lot_id.name
            stock = self.env['stock.production.lot'].search([
                ('name','=',lot_mesin),
                ('inv_pajak_progressive_id','!=',False),
                ('tgl_proses_birojasa','=',False),
                ('proses_biro_jasa_id','=',False),

            ])
            if not stock:
                raise osv.except_osv(("Perhatian !"),("Engine %s tidak ditemukan, atau sudah melakukan proses biro jasa, cek data kembali")%(line.lot_id.name))

    @api.multi
    def cek_penyerahan_stnk_bpkb(self):
        for line in self.pajak_line_ids:
            if line.lot_id.penyerahan_stnk_id or line.lot_id.penyerahan_notice_id or line.lot_id.penyerahan_polisi_id :
                raise osv.except_osv(('Perhatian !'), ("Engine %s sudah ditarik dalam penerimaan STNK, silahkan cancel terlebih dahulu!")%(line.lot_id.name))
            if line.lot_id.penyerahan_bpkb_id :
                raise osv.except_osv(('Perhatian !'), ("Engine %s sudah ditarik dalam penerimaan BPKB, silahkan cancel terlebih dahulu!")%(line.lot_id.name))
     
 
        
    @api.multi
    def validity_check(self):
        if self.pajak_id.state not in ('confirmed'):
            raise osv.except_osv(('Perhatian !'),("Tidak bisa cancel, status Pajak Progressive selain 'Confirm' !"))
        self.cek_penyerahan_stnk_bpkb()
        self.cek_invoice_pajak_progressive()
        self.cek_stock_product_lot()


    @api.multi
    def confirm(self):
        if self.state == 'approved':
            self.validity_check()
            self.write({'state':'confirmed', 'date':self._get_default_date(),'confirm_uid':self._uid,'confirm_date':datetime.now(),'period_id':self.env['account.period'].find(dt=self._get_default_date().date()).id})
            obj_acc_move = self.env['account.move']
            acc_move_line_obj = self.env['account.move.line']
            branch_config_id = self.env['wtc.branch.config'].search([('branch_id','=',self.branch_id.id)])
            journal_id = branch_config_id.pajak_progressive_cancel_journal_id
            if not journal_id:
                raise osv.except_osv(("Perhatian !"),("Tidak ditemukan Journal Pembatalan Tagihan Birojasa di Branch Config, silahkan konfigurasi ulang !"))
            for ppd_id in self.pajak_line_ids:
                move_id = obj_acc_move.create({
                    'name': self.name,
                    'journal_id': journal_id.id,
                    'line_id':[],
                    'period_id': self.period_id.id,
                    'date': self._get_default_date(),
                    'ref': ppd_id.name,
                    })
                to_reconcile_ids = self.create_account_move_line(move_id,ppd_id)
                print "reconcile :",to_reconcile_ids
                for to_reconcile in to_reconcile_ids:
                    self.reconcile_move(to_reconcile)
                self.write({'move_id':move_id.id})
                if journal_id.entry_posted:
                    move_id.button_validate()
                # self.pajak_id.wkf_action_cancel()
                ppd_id.lot_id.write({'inv_pajak_progressive_id': False})
                ppd_id.write({'status':'cancelled','cancel_uid':self._uid,'cancel_date':datetime.now()})
        return True

    def reconcile_move(self,cr,uid,ids,to_reconcile,context=None):
        if to_reconcile:
            self.pool.get('account.move.line').reconcile(cr,uid,to_reconcile)
        return True