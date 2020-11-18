import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp import SUPERUSER_ID
from lxml import etree

class wtc_disposal_asset(models.Model):
    _name = 'wtc.disposal.asset'
    _description = 'Disposal Asset'
    _order = 'date desc'
    
    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('waiting_for_approval','Waiting For Approval'),
        ('approved','Approved'),
        ('confirm','Confirmed'),
        ('cancel','Cancelled')
    ]
        
    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
    
    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()
            
    @api.one
    @api.depends('disposal_line.amount','disposal_line.amount_subtotal')
    def _compute_amount(self):
        taxes = 0.0
        untaxes = 0.0
        for x in self.disposal_line :
            if self.type  == 'sold' :
                tax = x.tax_id.compute_all(x.amount,1,x.product_id)

                taxes += tax['total_included'] - tax['total']
            untaxes += x.amount_subtotal
        self.amount_tax = taxes
        self.amount_untaxed = untaxes
        self.amount_total = untaxes + taxes
        
    name = fields.Char(string='No')
    branch_id = fields.Many2one('wtc.branch', string='Branch', required=True, default=_get_default_branch)
    date = fields.Date(string="Date",required=True,readonly=True,default=_get_default_date)
    division = fields.Selection([('Umum','Umum')], string='Division',default='Umum', required=True, select=True)
    state= fields.Selection(STATE_SELECTION, string='State', readonly=True,default='draft')
    confirm_uid = fields.Many2one('res.users',string="Confirmed by")
    confirm_date = fields.Datetime('Confirmed on')        
    move_id = fields.Many2one('account.move', string='Account Entry', copy=False)
    move_ids = fields.One2many('account.move.line',related='move_id.line_id',string='Journal Items', readonly=True)
    approval_ids = fields.One2many('wtc.approval.line','transaction_id',string="Table Approval",domain=[('form_id','=',_name)])
    approval_state =  fields.Selection([
                                        ('b','Belum Request'),
                                        ('rf','Request For Approval'),
                                        ('a','Approved'),
                                        ('r','Reject')
                                        ],'Approval State', readonly=True,default='b')
    type = fields.Selection([('sold','Sold'),('scrap','Scrap')],string="Type",default='scrap') 
    partner_id = fields.Many2one('res.partner',string='Partner')
    amount_total = fields.Float(string='Amount Total',digits=dp.get_precision('Account'), store=True,compute='_compute_amount')
    amount_tax = fields.Float(string='Amount Tax',digits=dp.get_precision('Account'), store=True,compute='_compute_amount')
    amount_untaxed = fields.Float(string='Untaxed Amount',digits=dp.get_precision('Account'), store=True,compute='_compute_amount')
    disposal_line = fields.One2many('wtc.disposal.asset.line','disposal_id',string='Disposal Line')
    invoice_number = fields.Char(string='Invoice Number')
    journal_id = fields.Many2one('account.journal',string='Journal')
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms',states={'draft': [('readonly', False)]})
    pajak_gabungan = fields.Boolean('Faktur Pajak Gabungan',copy=False)
    faktur_pajak_id = fields.Many2one('wtc.faktur.pajak.out',string='No Faktur Pajak',copy=False)
    due_date = fields.Date(string='Due Date')

    # Penambahan Tgl 14082020
    disposal_line_sold_ids = fields.One2many('wtc.disposal.asset.line','disposal_id',string='Disposal Sold Line',domain=[('type','=','sold')],context={'default_type':'sold'})
    disposal_line_scrap_ids = fields.One2many('wtc.disposal.asset.line','disposal_id',string='Disposal Scrap Line',domain=[('type','=','scrap')],context={'default_type':'scrap'})
    hl_ids = fields.One2many('teds.disposal.asset.hutang.lain','disposal_id','Hutang Lain')
                
    @api.model
    def create(self,vals,context=None):
            
        vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'DA') 
        vals['date'] = self._get_default_date()           
        if not vals.get('disposal_line_scrap_ids') and not vals.get('disposal_line_sold_ids'):
            raise osv.except_osv(('Perhatian !'), ("Disposal Detail harus diisi !"))   
        if vals.get('type'):
            if vals['type'] == 'sold' and not vals.get('hl_ids'):
                raise osv.except_osv(('Perhatian !'), ("Disposal Asset Type Sold harus mencantumkan Alokasi HL !"))
        return super(wtc_disposal_asset, self).create(vals)

    @api.onchange('type')
    def onchange_type(self):
        self.disposal_line_sold_ids = False
        self.disposal_line_scrap_ids = False
        self.hl_ids = False

    @api.multi
    def action_print_form(self):
        datas = self.read()[0]

        return self.env['report'].get_action(self,'wtc_purchase_asset.teds_disposal_asset_print_form_pdf', data=datas)

    
    def cek_hl(self):
        if self.type == 'sold':
            total_hl = 0
            if not self.hl_ids:
                raise osv.except_osv(('Perhatian !'), ("Disposal Asset Type Sold harus mencantumkan Alokasi HL !"))
            for hl in self.hl_ids:
                if hl.amount_hl_allocation > hl.amount_hl_balance:
                    raise osv.except_osv(('Perhatian !'),('Nilai Allocation melebihi HL Balance !'))
                if int(hl.amount_hl_allocation) <= 0:
                    raise osv.except_osv(('Perhatian !'),('Nilai Allocation tidak boleh 0 !'))
                total_hl += hl.amount_hl_allocation 

            if round(self.amount_total,2) != round(total_hl,2):
                raise osv.except_osv(('Perhatian !'),('Nilai HL tidak sama dengan Amount Total !'))

    @api.multi
    def request_approval(self):
        self.cek_hl()
        if not self.disposal_line:
            raise osv.except_osv(('Perhatian !'),('Disposal Detail harus diisi !'))

        obj_matrix = self.env["wtc.approval.matrixbiaya"]
        obj_matrix.request_by_value(self, self.amount_total)

        self.state = 'waiting_for_approval'
        self.approval_state = 'rf'
        branch_config_journal = self.env['wtc.branch.config'].search([
                                           ('branch_id','=',self.branch_id.id),
                                           ('journal_disposal_asset_id','!=',False)
                                           ])
        if not branch_config_journal :
            raise osv.except_osv(('Perhatian !'), ("Journal Disposal Asset belum diisi dalam master Branch Config !")) 
           
                
    @api.multi      
    def approve_approval(self):
        if not self.disposal_line :
            raise osv.except_osv(('Perhatian !'), ("Detail belum diisi. Data tidak bisa di save."))       
        approval_sts = self.env['wtc.approval.matrixbiaya'].approve(self)
        if approval_sts == 1:
            self.write({'date':self._get_default_date(),'approval_state':'a','state':'approved'})
        elif approval_sts == 0:
                raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group Approval")) 
           
    @api.multi
    def _fill_due_date(self,document_date, payment_term):
        pterm = self.env['account.payment.term'].browse(payment_term)
        pterm_list = pterm.compute(value=1, date_ref=document_date)[0]
        date_due = False
        if pterm_list:
            date_due =  max(line[0] for line in pterm_list)
        return date_due
               
    @api.multi
    def confirm_disposal(self):
        self.cek_hl()
        due_date = self._fill_due_date(self.date, self.payment_term_id.id)
        move_id,period_id,journal_id = self.action_create_account_move()
                
        self.write({'confirm_uid':self._uid,
                    'confirm_date':datetime.now(),
                    'date':self._get_default_date().date(),
                    'due_date' : due_date,
                    'move_id' : move_id,
                    'state' : 'confirm'
                    })
                
        if self.type == 'sold' :
            self.action_create_journal_sold(due_date,journal_id,period_id,move_id)
        elif self.type == 'scrap' :
            self.action_create_journal_scrap(due_date,journal_id,period_id,move_id)

        for x in self.disposal_line :
            x.asset_id.write({'disposal_id':self.id,'state':'disposed'})
            
        no_faktur = self.get_faktur_pajak(self)
        
    def get_faktur_pajak(self,cr,uid,ids,vals,context=None):
        no_faktur = False
        if vals.amount_tax and not vals.pajak_gabungan : 
            no_faktur = self.pool.get('wtc.faktur.pajak.out').get_no_faktur_pajak(cr,uid,ids,'wtc.disposal.asset')        
        return no_faktur
                    
    @api.multi
    def action_create_account_move(self):
        account_move = self.env['account.move']
        periods = self.env['account.period'].find(self._get_default_date().date())
        branch_config = self.env['wtc.branch.config'].search([('branch_id','=',self.branch_id.id)])              
        if not branch_config :
            raise osv.except_osv(('Perhatian !'), ("Branch Config %s tidak ditemukan !")%(self.branch_id.code))  
        
        journal_id = branch_config.journal_disposal_asset_id
        period_id =  periods and periods[0]
        if not journal_id:
            raise osv.except_osv(('Perhatian !'), ("Journal disposal asset belum diisi dalam master Branch Config %s !")%(self.branch_id.code))  
        
        #Create Account MOVE 
        move = {
            'name': self.name,
            'ref': self.name,
            'journal_id': journal_id.id,
            'date': self.date,
            'period_id':period_id.id,
        }
        move_id = account_move.create(move)
        
        return move_id.id,period_id.id,journal_id.id
            
    @api.multi
    def action_create_journal_sold(self,due_date,journal_id,period_id,move_id):
        account_move_line = self.env['account.move.line']
        aml_piutang_ids = []

        for asset in self.disposal_line :
            branch_config = self.env['wtc.branch.config'].search([('branch_id','=',asset.asset_id.branch_id.id)])
            journal_line_id = branch_config.journal_disposal_asset_id.id
            if not journal_line_id :
                raise osv.except_osv(('Perhatian !'), ("Journal Disposal Asset belum diisi dalam Branch Config %s")%(asset.asset_id.branch_id.name))
                        
            or_account_id = branch_config.journal_disposal_asset_id.default_debit_account_id.id
            if not or_account_id :
                raise osv.except_osv(('Perhatian !'), ("Debit Account Journal Disposal Asset belum diisi dalam Branch Config %s")%(asset.asset_id.branch_id.name))
                        
            akumulasi_account_id = asset.asset_id.category_id.account_depreciation_id.id
            if not akumulasi_account_id :
                raise osv.except_osv(('Perhatian !'), ("Depreciation Account belum diisi dalam category asset %s")%(asset.asset_id.category_id.name))
                        
            asset_account_id = asset.asset_id.category_id.account_asset_id.id
            if not asset_account_id :
                raise osv.except_osv(('Perhatian !'), ("Asset Account belum diisi dalam category asset %s")%(asset.asset_id.category_id.name))
            
            if asset.tax_id :         
                tax_account_id = asset.tax_id.account_collected_id.id
                if not tax_account_id :
                    raise osv.except_osv(('Perhatian !'), ("Tax Account belum diisi dalam Tax %s")%(asset.tax_id.name))
                        
            gain_loss_account_id = branch_config.gain_loss_account_id.id
            if not gain_loss_account_id :
                raise osv.except_osv(('Perhatian !'), ("Gain/Loss Account belum diisi dalam Branch Config %s")%(asset.asset_id.branch_id.name))            
            
            other_receivable_value = asset.amount
            acc_depreciation_value = asset.asset_id.real_purchase_value - asset.asset_id.value_residual
            fixed_asset_value = asset.asset_id.real_purchase_value
            taxes_value  = asset.amount - asset.amount_subtotal
            gain_loss_value = asset.amount_subtotal - asset.asset_id.value_residual
            #loss_value = asset.asset_id.value_residual - asset.amount_subtotal
            
            move_line_or = {
                'name': asset.asset_id.name + '-Other Receivable',
                'ref':self.name,
                'account_id': or_account_id,
                'move_id': move_id,
                'journal_id': journal_line_id,
                'period_id': period_id,
                'date': self.date,
                'debit': other_receivable_value,
                'credit': 0.0,
                'branch_id' : asset.asset_id.branch_id.id,
                'division' : self.division,
                'partner_id' : self.partner_id.id,
                'ref_asset_id': asset.asset_id.id, 
                'date_maturity' : due_date,                  
            }
             
            move_line_akumulasi = {
                'name': asset.asset_id.name + '-Accumulation',
                'ref':self.name,
                'account_id': akumulasi_account_id,
                'move_id': move_id,
                'journal_id': journal_line_id,
                'period_id': period_id,
                'date': self.date,
                'debit': acc_depreciation_value,
                'credit': 0.0,
                'branch_id' : asset.asset_id.branch_id.id,
                'division' : self.division,
                'partner_id' : self.partner_id.id,
                'ref_asset_id': asset.asset_id.id,   
                'date_maturity' : due_date,                 
            }
            
            move_line_asset = {
                'name': asset.asset_id.name + '-Asset',
                'ref':self.name,
                'account_id': asset_account_id,
                'move_id': move_id,
                'journal_id': journal_line_id,
                'period_id': period_id,
                'date': self.date,
                'debit': 0.0,
                'credit': fixed_asset_value,
                'branch_id' : asset.asset_id.branch_id.id,
                'division' : self.division,
                'partner_id' : self.partner_id.id,
                'ref_asset_id': asset.asset_id.id, 
                'date_maturity' : due_date,                   
            }                               

            move_line_ppn_out = {
                'name': asset.asset_id.name +'-PPN Out',
                'ref':self.name,
                'account_id': tax_account_id,
                'move_id': move_id,
                'journal_id': journal_line_id,
                'period_id': period_id,
                'date': self.date,
                'debit': 0.0,
                'credit': taxes_value,
                'branch_id' : asset.asset_id.branch_id.id,
                'division' : self.division,
                'partner_id' : self.partner_id.id,
                'ref_asset_id': asset.asset_id.id,   
                'date_maturity' : due_date,                 
            }
                  
            move_line_gain_loss = {
                'name': asset.asset_id.name + '-Gain/Loss',
                'ref':self.name,
                'account_id': gain_loss_account_id,
                'move_id': move_id,
                'journal_id': journal_line_id,
                'period_id': period_id,
                'date': self.date,
                'debit': abs(gain_loss_value) if gain_loss_value < 0.0 else 0.0,
                'credit': gain_loss_value if gain_loss_value > 0.0 else 0.0,
                'branch_id' : asset.asset_id.branch_id.id,
                'division' : self.division,
                'partner_id' : self.partner_id.id,
                'ref_asset_id': asset.asset_id.id,   
                'date_maturity' : due_date,                 
            }
                                                
            aml_piutang = account_move_line.create(move_line_or)
            aml_akumulasi = account_move_line.create(move_line_akumulasi)
            aml_asset = account_move_line.create(move_line_asset)
            aml_ppn_out = account_move_line.create(move_line_ppn_out)
            aml_gain_loss = account_move_line.create(move_line_gain_loss)
        
            aml_piutang_ids.append(aml_piutang)
        
        self.auto_journal_and_reconcile(aml_piutang_ids)

    @api.multi
    def auto_journal_and_reconcile(self,aml_piutang_ids):
        obj_account_move = self.env['account.move']
        obj_account_move_line = self.env['account.move.line']
        date = self._get_default_date()
        periods = self.env['account.period'].find(self._get_default_date().date())
        period_id =  periods and periods[0]
        total_hl = 0
        ids_to_reconcile = []
            
        if self.hl_ids:            
            obj_branch_config = self.env['wtc.branch.config'].search([('branch_id','=',self.branch_id.id)],limit=1)
            if not obj_branch_config.journal_disposal_asset_hl_id:
                raise osv.except_osv(('Perhatian !'), ("Konfigurasi Jurnal Reconcile HL belum disetting!"))
            
            # Create Jurnal AL untuk lawan HL
            create_acc_move = obj_account_move.create({
                'journal_id': obj_branch_config.journal_disposal_asset_hl_id.id,
                'line_id': [],
                'period_id': period_id.id,
                'date': date,
                'ref':  self.name,
                'name': self.env['ir.sequence'].get_per_branch(self.branch_id.id, 'AL')
            })

            for hl_line in self.hl_ids:
                total_hl += hl_line.amount_hl_allocation
                new_line_id = hl_line.hl_id.copy({
                    'move_id': create_acc_move.id,
                    'debit': hl_line.amount_hl_allocation,
                    'credit': 0,
                    'name': hl_line.hl_id.ref,
                    'ref': self.name,
                    'tax_amount': hl_line.hl_id.tax_amount * -1
                })
                if hl_line.hl_id.account_id.reconcile :
                    ids_to_reconcile.append([hl_line.hl_id.id,new_line_id.id])
        
        total_aml_piutang = 0
        for aml_piutang in aml_piutang_ids:    
            # Create AML Untuk Reconcile Piutang
            create_aml_piu = obj_account_move_line.create({
                    'move_id': create_acc_move.id,
                    'debit': 0,
                    'credit': aml_piutang.debit,
                    'name': self.name,
                    'ref': self.name,
                    'account_id': aml_piutang.account_id.id,
                    'partner_id': self.partner_id.id,
                    'branch_id': self.branch_id.id,
                    'division': self.division
            })
            ids_to_reconcile.append([aml_piutang.id,create_aml_piu.id])
            total_aml_piutang += aml_piutang.debit
        if total_aml_piutang > total_hl:
            raise Warning('Reconcile Amount Asset (%s) Melebihi Nilai Alokasi HL (%s) !'%(total_aml_piutang,total_hl))
        for to_reconcile in ids_to_reconcile :
            self.pool.get('account.move.line').reconcile_partial(self._cr, self._uid, to_reconcile)

    @api.multi
    def action_create_journal_scrap(self,due_date,journal_id,period_id,move_id):
        account_move_line = self.env['account.move.line']
                        
        for asset in self.disposal_line :
            branch_config = self.env['wtc.branch.config'].search([('branch_id','=',asset.asset_id.branch_id.id)])
            journal_line_id = branch_config.journal_disposal_asset_id.id
            if not journal_line_id :
                raise osv.except_osv(('Perhatian !'), ("Journal Disposal Asset belum diisi dalam Branch Config %s")%(asset.asset_id.branch_id.name))  
                                        
            akumulasi_account_id = asset.asset_id.category_id.account_depreciation_id.id
            if not akumulasi_account_id :
                raise osv.except_osv(('Perhatian !'), ("Depreciation Account belum diisi dalam category asset %s")%(asset.asset_id.category_id.name))  
                
            asset_account_id = asset.asset_id.category_id.account_asset_id.id
            if not asset_account_id :
                raise osv.except_osv(('Perhatian !'), ("Asset Account belum diisi dalam category asset %s")%(asset.asset_id.category_id.name))  
                            
            expense_asset_account_id = branch_config.expense_asset_account_id.id
            if not expense_asset_account_id :
                raise osv.except_osv(('Perhatian !'), ("Expense Account belum diisi dalam Branch Config %s")%(asset.asset_id.branch_id.name))
                        
            value_residual = asset.asset_id.value_residual
            gross_value = asset.asset_id.purchase_value
            akumulasi_value = gross_value - value_residual
            
            move_line_akumulasi = {
                'name': asset.asset_id.name + '-Accumulation',
                'ref':self.name,
                'account_id': akumulasi_account_id,
                'move_id': move_id,
                'journal_id': journal_line_id,
                'period_id': period_id,
                'date': self.date,
                'debit': akumulasi_value,
                'credit': 0.0,
                'branch_id' : asset.asset_id.branch_id.id,
                'division' : self.division,
                'partner_id' : self.partner_id.id,
                'ref_asset_id': asset.asset_id.id,  
                'date_maturity' : due_date,                  
            }

            move_line_asset = {
                'name': asset.asset_id.name + '-Asset',
                'ref':self.name,
                'account_id': asset_account_id,
                'move_id': move_id,
                'journal_id': journal_line_id,
                'period_id': period_id,
                'date': self.date,
                'debit': 0.0,
                'credit': gross_value,
                'branch_id' : asset.asset_id.branch_id.id,
                'division' : self.division,
                'partner_id' : self.partner_id.id,
                'ref_asset_id': asset.asset_id.id,    
                'date_maturity' : due_date,                
            }

            move_line_expense = {
                'name': asset.asset_id.name + '-Expense',
                'ref':self.name,
                'account_id': expense_asset_account_id,
                'move_id': move_id,
                'journal_id': journal_line_id,
                'period_id': period_id,
                'date': self.date,
                'debit': value_residual,
                'credit': 0.0,
                'branch_id' : asset.asset_id.branch_id.id,
                'division' : self.division,
                'partner_id' : self.partner_id.id,
                'ref_asset_id': asset.asset_id.id,     
                'date_maturity' : due_date,               
            }                               

            account_move_line.create(move_line_expense)
            account_move_line.create(move_line_akumulasi)
            account_move_line.create(move_line_asset)
                 
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Disposal Asset tidak bisa didelete dalam State selain 'draft' !"))
        return super(wtc_disposal_asset, self).unlink(cr, uid, ids, context=context)
                     
class wtc_disposal_asset_line(models.Model):
    _name = 'wtc.disposal.asset.line'
    _description = 'Disposal Asset Line'
    
    @api.one
    @api.depends('amount','tax_id')
    def _amount_line(self):
        taxes = False
        if self.tax_id and self.disposal_id.type == 'sold':
            taxes = self.tax_id.compute_all(self.amount,1,self.product_id)
        self.amount_subtotal = taxes['total'] if taxes else self.amount

    @api.multi
    @api.depends('asset_id')
    def compute_asset_data(self):
        for  me in self:
            if me.asset_id:
                me.nilai_asset = me.asset_id.purchase_value
                me.nilai_penyusutan = me.asset_id.purchase_value / (me.asset_id.method_number or 60)
                me.akumulasi_penyusutan = me.asset_id.purchase_value - me.asset_id.value_residual
                me.nilai_buku = me.asset_id.value_residual
                    
    name = fields.Char(string='Description')
    branch_id = fields.Many2one('wtc.branch',string='Branch')
    asset_id = fields.Many2one('account.asset.asset',string='Asset No',domain="[('branch_id','=',parent.branch_id),('state','in',['open','close']),('category_id.type','=','fixed')]")
    amount = fields.Float(string='Harga Jual')
    tax_id =  fields.Many2many('account.tax', 'wtc_disposal_asset_line_tax', 'wtc_disposal_asset_line_id', 'tax_id', 'Taxes',domain=[('type_tax_use','=','sale')])
    amount_subtotal = fields.Float(compute='_amount_line', string='Subtotal', digits_compute= dp.get_precision('Account'),store=True)
    disposal_id = fields.Many2one('wtc.disposal.asset',string='Disposal No')
    category_id = fields.Many2one(related='asset_id.category_id',string='Category',store=True)
    product_id = fields.Many2one(related='asset_id.product_id',string='Product')
    
    # Penambahan Type Scarp / Sold Tgl 14082020
    type = fields.Selection([('sold','Sold'),('scrap','Scrap')],string="Type")
    nilai_penyusutan = fields.Float('Penyusutan Per Bln',compute='compute_asset_data')
    akumulasi_penyusutan = fields.Float('Akumulasi Penyusutan',compute='compute_asset_data')
    nilai_buku = fields.Float('Nilai Buku',compute='compute_asset_data')
    nilai_asset = fields.Float('Harga Beli',compute='compute_asset_data')
    
    @api.onchange('asset_id')
    def change_asset(self):
        if self.asset_id :
            self.category_id = self.asset_id.category_id.id
            self.product_id = self.asset_id.product_id.id
            if self.disposal_id.type == 'scrap' :
                self.amount = self.asset_id.purchase_value

    @api.onchange('tax_id')
    def change_taxes(self):
        if self.tax_id and self.disposal_id.type == 'scrap' :
            self.tax_id = [(6,0,[])]

class DisposalAssetHutangLain(models.Model):
    _name = "teds.disposal.asset.hutang.lain"

    @api.depends('amount_hl_original')
    def compute_amount_origin(self):
        for me in self:
            me.amount_hl_original_show = me.amount_hl_original
    
    @api.depends('amount_hl_balance')
    def compute_amount_balance(self):
        for me in self:
            me.amount_hl_balance_show = me.amount_hl_balance


    disposal_id = fields.Many2one('wtc.disposal.asset','Disposal Asset')
    hl_id = fields.Many2one('account.move.line','Hutang Lain')
    amount_hl_original = fields.Float('HL Original')
    amount_hl_balance = fields.Float('HL Balance')
    amount_hl_allocation = fields.Float('Allocation')
    amount_hl_original_show = fields.Float('HL Original',compute='compute_amount_origin')
    amount_hl_balance_show = fields.Float('HL Balance',compute='compute_amount_balance') 

    @api.onchange('hl_id')
    def onchage_hl(self):
        if not self.disposal_id.partner_id or not self.disposal_id.branch_id or not self.disposal_id.type:
            raise osv.except_osv(('Perhatian !'), ("Sialhakn lengkapi data header terlebih dahulu !"))
        self.amount_hl_allocation = False
        if self.hl_id:
            self.amount_hl_original = abs(self.hl_id.credit)
            self.amount_hl_original_show = abs(self.hl_id.credit)
            self.amount_hl_balance = abs(self.hl_id.amount_residual_currency)
            self.amount_hl_balance_show = abs(self.hl_id.amount_residual_currency)
            self.amount_hl_allocation = abs(self.hl_id.amount_residual_currency)
    
    @api.onchange('amount_hl_allocation')
    def onchage_amount_allocation(self):
        if self.amount_hl_allocation:
            if self.amount_hl_allocation > self.amount_hl_balance:
                warning = {'title':'Perhatian !','message':'Nilai Allocation melebihi HL Balance !'}
                self.hl_id = False

                return {'warning':warning}
           
            if int(self.amount_hl_allocation) <= 0:
                warning = {'title':'Perhatian !','message':'Nilai Allocation tidak boleh 0 !'}
                self.hl_id = False
                return {'warning':warning,'value':{'amount_hl_allocation':False}}
           
