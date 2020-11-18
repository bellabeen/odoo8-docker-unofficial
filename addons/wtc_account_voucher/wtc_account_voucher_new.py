import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp import SUPERUSER_ID
from openerp import tools
import pytz
from lxml import etree

class wtc_account_voucher_new(models.Model):
    _name = 'wtc.account.voucher'
    _description = 'Account Voucher Custom'
    _order = 'date desc, id desc'
    _rec_name = 'number'
    
    @api.one
    def _get_period(self):
        if self._context.get('period_id', False):
            return self._context.get('period_id')
        periods = self.pool.get('account.period').find(self._cr,self._uid,self._get_default_date().date())
        return periods and periods[0] or False
        
    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()
    
    @api.one        
    def _get_partner_type(self):
        name = 'supplier'
        if self._context is None: self._context = {}        
        if self._context.get('type') in ('receipt','hutang_lain') :
            name = 'customer'
        self.partner_type = name
            
    @api.one
    def _get_company(self):
        company = self.env['res.company']._company_default_get(self._cr, self._uid, 'account.voucher')
        return company
            
    @api.one
    @api.depends('line_dr_ids','total_debit')
    def _total_debit(self):
        res = {}
        value =  0.0
        for line in self.line_dr_ids:
            value += line.amount
        self.total_debit = value
             
    @api.one
    @api.depends('line_dr_ids','line_cr_ids','line_wo_ids','writeoff_amount')
    def _get_writeoff_amount(self):
        currency_obj = self.env['res.currency']
        res = {}
        debit = credit = writeoff = 0.0
        sign = self.type == 'payment' and -1 or 1
        for l in self.line_dr_ids:
            debit += l.amount
        for l in self.line_cr_ids:
            credit += l.amount
        for l in self.line_wo_ids :
            writeoff += l.amount
        self.writeoff_amount = self.amount - sign * (credit - debit) - writeoff

    def _compute_writeoff_amount(self, cr, uid, line_dr_ids, line_cr_ids, line_wo_ids, amount, type):
        debit = credit = writeoff = 0.0
        sign = type == 'payment' and -1 or 1
        for l in line_dr_ids:
            if isinstance(l, dict):
                debit += l['amount']
        for l in line_cr_ids:
            if isinstance(l, dict):
                credit += l['amount']
        for l in line_wo_ids:
            if isinstance(l, dict):
                writeoff += l['amount']                
        return amount - sign * (credit - debit) - writeoff
                
    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
                  
    @api.one
    @api.depends('percentage','amount')
    def _compute_amount(self):
        self.amount_edc = self.amount *100/(100-self.percentage)

    @api.one
    @api.depends('journal_id')
    def _journal_type(self):
        self.journal_type = self.journal_id.type
                                
    type = fields.Selection([
                            ('hutang_lain','Hutang Lain'),
                            ('payment','Payment'),
                            ('receipt','Receipt'),
                            ],'Default Type', readonly=True, states={'draft':[('readonly',False)]})
    name = fields.Char('Memo', readonly=True, states={'draft':[('readonly',False)]},default='')
    journal_id = fields.Many2one('account.journal', 'Journal', required=True, readonly=True, states={'draft':[('readonly',False)]})
    account_id = fields.Many2one('account.account', 'Account', required=True, readonly=True, states={'draft':[('readonly',False)]})
    line_ids = fields.One2many('wtc.account.voucher.line', 'voucher_id', 'Voucher Lines',
                               readonly=True, copy=True,
                               states={'draft':[('readonly',False)]})
    line_cr_ids = fields.One2many('wtc.account.voucher.line','voucher_id','Credits',domain=[('type','=','cr')], context={'default_type':'cr'}, readonly=True, states={'draft':[('readonly',False)]})
    line_dr_ids = fields.One2many('wtc.account.voucher.line','voucher_id','Debits',domain=[('type','=','dr')], context={'default_type':'dr'}, readonly=True, states={'draft':[('readonly',False)]})
    line_wo_ids = fields.One2many('wtc.account.voucher.line','voucher_id','Writeoff',domain=[('type','=','wo')], context={'default_type':'wo'}, readonly=True, states={'draft':[('readonly',False)]})    
    period_id = fields.Many2one('account.period', 'Period', required=True, readonly=True, 
                                states={'draft':[('readonly',False)]},default=_get_period)
    narration = fields.Text('Notes', readonly=True, states={'draft':[('readonly',False)]})
    company_id = fields.Many2one('res.company', 'Company', required=True, readonly=True, states={'draft':[('readonly',False)]},default=_get_company)
    state = fields.Selection(
                            [
                            ('draft','Draft'),
                            ('waiting_for_approval','Waiting Approval'),
                            ('confirmed', 'Waiting Approval'),
                            ('request_approval','RFA'), 
                            ('approved','Approve'), 
                            ('cancel','Cancelled'),
                            ('proforma','Pro-forma'),
                            ('posted','Posted')                             
                            ], 'Status', readonly=True, copy=False, default = 'draft')
    amount = fields.Float('Total', store=True,digits_compute=dp.get_precision('Account'), required=True, readonly=True, states={'draft':[('readonly',False)]})
    #TODO: delete
    tax_amount = fields.Float('Tax Amount', digits_compute=dp.get_precision('Account'), readonly=True)
    number = fields.Char('Number', readonly=True, copy=False)
    move_id = fields.Many2one('account.move', 'Account Entry', copy=False)
    move_ids = fields.One2many(related='move_id.line_id', string='Journal Items', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Partner', change_default=1, readonly=True, states={'draft':[('readonly',False)]})
    #TODO: delete
    tax_id = fields.Many2one('account.tax', 'Tax', readonly=True, states={'draft':[('readonly',False)]}, domain=[('price_include','=', False)])
    date_due = fields.Date('Due Date', readonly=True, select=True, states={'draft':[('readonly',False)]})
    writeoff_amount = fields.Float(compute =_get_writeoff_amount, string='Difference Amount', readonly=True,store=True)
        
    branch_id = fields.Many2one('wtc.branch', string='Branch', default = _get_default_branch)
    division = fields.Selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum'),('Finance','Finance')], 'Division', change_default=True, select=True)
    inter_branch_id = fields.Many2one('wtc.branch',string='Inter Branch')
    kwitansi_id = fields.Many2one('wtc.register.kwitansi.line', string='Kwitansi')
    reason_cancel_kwitansi = fields.Char('Reason')
    confirm_uid = fields.Many2one('res.users',string="Validated by")
    confirm_date = fields.Datetime('Validated on')
    cancel_uid = fields.Many2one('res.users',string="Cancelled by")
    cancel_date = fields.Datetime('Cancelled on')
    date = fields.Date('Date',default=_get_default_date)
    cetak_ke = fields.Integer('Cetak Kwitansi Ke')
    pajak_gabungan = fields.Boolean('Faktur Pajak Gabungan',copy=False)
    faktur_pajak_id = fields.Many2one('wtc.faktur.pajak.out',string='No Faktur Pajak',copy=False)
    no_faktur_pajak =  fields.Char('No Faktur Pajak',copy=False)
    tgl_faktur_pajak =  fields.Date('Tgl Faktur Pajak',copy=False)
    partner_type = fields.Selection([('principle','Principle'),('biro_jasa','Biro Jasa'),('forwarder','Forwarder'),\
                                      ('supplier','General Supplier'),('finance_company','Finance Company'),\
                                      ('customer','Customer'),('dealer','Dealer'),('ahass','Ahass')], 'Partner Type', default=_get_partner_type)
    user_id =  fields.Many2one('res.users', string='Responsible', change_default=True,readonly=True, states={'draft': [('readonly', False)]})
    transaksi =  fields.Selection([
                                ('rutin','Rutin'),
                                ('tidak_rutin','Tidak Rutin'),
                                ], string='Transaksi',  index=True, change_default=True)
    jenis_transaksi_id =  fields.Many2one('wtc.payments.request.type', string='Tipe Transaksi',readonly=True, states={'draft': [('readonly', False)]})
    no_document =  fields.Char(string='No Document', index=True)
    tgl_document =  fields.Date(string='Tgl Document', readonly=True, states={'draft': [('readonly', False)]}, index=True, copy=False)
    payments_request_ids =  fields.One2many('wtc.account.voucher.line', 'voucher_id',readonly=True, copy=True)
    paid_amount =  fields.Float(string='Paid Amount')
    
    approval_ids = fields.One2many('wtc.approval.line','transaction_id',string="Table Approval",domain=[('form_id','=',_name)])
    approval_state = fields.Selection([('b','Belum Request'),('rf','Request For Approval'),('a','Approved'),('r','Reject')],'Approval State', default='b', readonly=True)
    total_debit = fields.Float(compute = _total_debit, digits_compute=dp.get_precision('Account'), string='Total Debit', store=True)
    kwitansi =  fields.Boolean(string='Yg Sudah Print Kwitansi')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True)
    
    #edc
    card_no = fields.Char(string="Card No")
    card_name = fields.Char(string="Card Name")
    percentage = fields.Float(string="Bank Charge (%)")
    amount_edc = fields.Float(string='Total Amount',digits=dp.get_precision('Account'), store=True, readonly=True, compute='_compute_amount',)
    approval_code = fields.Char(sting="Approval Code")
    journal_type = fields.Char(string="Journal Type",compute='_journal_type')
        
    pembulatan = fields.Boolean(string='Pembulatan')
    no_rekening_tujuan = fields.Char('No Rekening Tujuan')
    is_payment = fields.Boolean('Klik BCA ?')
    payment_klik_uid = fields.Many2one('res.users','Payment Klik by')
    payment_klik_date = fields.Datetime('Payment Klik on')

    def onchange_journal_id(self, cr, uid, ids, journal_id, context=None):
        if context is None:
            context = {}
        if not journal_id:
            return False
        journal = self.pool.get('account.journal').browse(cr, uid, journal_id, context=context)
        account_id = journal.default_credit_account_id or journal.default_debit_account_id
        if not account_id :
            raise except_orm('Perhatian !', 'Konfigurasi jurnal account belum dibuat, silahkan setting dulu !')
        company_id = journal.company_id
        currency_id = False
        vals = {}
        if journal.currency:
            currency_id = journal.currency.id
        else:
            currency_id = journal.company_id.currency_id.id
        if currency_id :
            vals['currency_id'] = currency_id        
        if account_id :
            vals['account_id'] = account_id.id
        if company_id :
            vals['company_id'] = company_id.id
        #vals['date_due'] = self._get_default_date(cr,uid).date()
        vals['period_id'] = self.pool['account.period'].find(cr, uid,dt=self._get_default_date(cr,uid).date(), context=context)[0]
        return {'value':vals}
        
    def onchange_division(self,cr,uid,ids,division,context=None):
        value = {}
        if division :
            value['line_cr_ids'] = []
            value['line_ids'] = []
            value['line_wo_ids'] = []
            value['line_dr_ids'] = []
        return {'value':value}
    
    def onchange_partner_type(self,cr,uid,ids,partner_type,context=None):
        dom={}        
        val={}
        if partner_type :
            val['partner_id'] = False
            if partner_type == 'biro_jasa' :
                dom['partner_id'] = [('biro_jasa','!=',False)]
            elif partner_type == 'forwarder' :
                dom['partner_id'] = [('forwarder','!=',False)]                
            elif partner_type == 'supplier' :
                dom['partner_id'] = [('supplier','!=',False)]                
            elif partner_type == 'finance_company' :
                dom['partner_id'] = [('finance_company','!=',False)]                
            elif partner_type == 'customer' :
                dom['partner_id'] = [('customer','!=',False)]                
            elif partner_type == 'dealer' :
                dom['partner_id'] = [('dealer','!=',False)] 
            elif partner_type == 'ahass' :
                dom['partner_id'] = [('ahass','!=',False)]     
            elif partner_type == 'principle' :
                dom['partner_id'] = [('principle','!=',False)]                                   
        return {'domain':dom,'value':val}

    def onchange_partner_id(self, cr, uid, ids, partner_id, context=None):
        res = {'value':{}}
        if partner_id :
            res['value']['line_ids'] = []
            res['value']['line_dr_ids'] = []
            res['value']['line_cr_ids'] = []  
        return res
    
    def onchange_branch(self, cr, uid, ids, branch, context=None):
        value = {}
        domain = {}
        if branch :
            value['inter_branch_id'] = branch
            domain['journal_id'] = [('branch_id','=',branch),('type','in',['bank','cash','edc']),('is_pusted','=',True)]
            value['journal_id'] = False
            value['line_ids'] = []
            value['line_cr_ids'] = []
            value['line_dr_ids'] = []
            value['line_wo_ids'] = []
        return {'value':value, 'domain':domain}
        
    def onchange_inter_branch(self, cr, uid, ids, inter_branch, context=None):
        value = {}
        if inter_branch :
            value['line_ids'] = []
            value['line_cr_ids'] = []
            value['line_dr_ids'] = []        
            value['line_wo_ids'] = []            
        return {'value':value}    
                        
    def print_wizard_kwitansi(self,cr,uid,ids,context=None):  
        obj_claim_kpb = self.browse(cr,uid,ids)
        obj_ir_view = self.pool.get("ir.ui.view")
        obj_ir_view_search= obj_ir_view.search(cr,uid,[("name", "=", 'wtc.kwitansi.wizard.customer.payment'), ("model", "=", 'wtc.account.voucher'),])
        obj_ir_view_browse = obj_ir_view.browse(cr,uid,obj_ir_view_search)
        return {
            'name': 'Kwitansi',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.account.voucher',
            'type': 'ir.actions.act_window',
            'view_id' : obj_ir_view_browse.id,
            'target': 'new',
            'nodestroy': True,
            'res_id': obj_claim_kpb.id,
            'context': context
            }
        
    #def reg_kwitansi(self, cr, uid, ids, vals, context=None):
    #    res = super(wtc_account_voucher_new, self).write(cr, uid, ids, vals, context=context)
    #    return res
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(wtc_account_voucher_new, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        obj_active = self.browse(cr,uid,context.get('active_ids',[]))
        if not context.get('portal') :
            branch_id = obj_active.branch_id.id
            kwitansi=obj_active.kwitansi_id.id
            doc = etree.XML(res['arch'])
            nodes = doc.xpath("//field[@name='kwitansi_id']")
            for node in nodes:
                node.set('domain', '[("new_payment_id","=",False),("payment_id","=",False),("dn_nc_id","=",False),("branch_id", "=", '+ str(branch_id)+'),("state","=","open")]')
            res['arch'] = etree.tostring(doc)
        return res
        
    def generate_sequence(self,cr,uid,vals,context=None):
        name = '/'
        if vals.get('type') == 'payment' :
            name = self.pool.get('ir.sequence').get_per_branch(cr,uid,vals.get('branch_id'),'PV') 
        elif vals.get('type') == 'receipt' :
            name = self.pool.get('ir.sequence').get_per_branch(cr,uid,vals.get('branch_id'),'AR')
        elif vals.get('type') == 'hutang_lain' :
            name = self.pool.get('ir.sequence').get_per_branch(cr,uid,vals.get('branch_id'),'HL')                                
        return name 

    def create(self,cr,uid,vals,context=None):
	if ('line_dr_ids' in vals) :
            for x in vals['line_dr_ids'] :
            	if x[2].get('date_due') :
                    x[2].pop('date_due')
            	if x[2].get('date_original') :
                    x[2].pop('date_original')
        if ('line_cr_ids' in vals) :
	    for x in vals['line_cr_ids'] :
            	if x[2].get('date_due') :
                    x[2].pop('date_due')
                if x[2].get('date_original') :
    	            x[2].pop('date_original')
        vals.update({'amount': vals.get('amount',0.0)}) 
        if vals.get('amount') < 0.0  :
            raise osv.except_osv(('Perhatian !'), ("Paid Amount tidak boleh minus"))
        if not all(x[2]['amount'] > 0.0 for x in vals.get('line_dr_ids',[])) or not all(x[2]['amount'] > 0.0 for x in vals.get('line_cr_ids',[])) :
            raise osv.except_osv('Perhatian !', "Amount detil harus lebih besar atau sama dengan 0.0.")

        amount_dr = sum(x[2]['amount'] for x in vals.get('line_dr_ids',[]))

        journal_type = self.pool.get('account.journal').read(cr, uid, vals.get('journal_id'), ['type'])
        self._check_on_create_and_write(cr, uid, 0, 
            vals['branch_id'], 
            vals['type'], 
            journal_type and str(journal_type['type']), 
            vals['amount'], 
            sum(x[2]['amount'] for x in vals.get('line_cr_ids',[])), 
            amount_dr, 
            sum(x[2]['amount'] for x in vals.get('line_wo_ids',[])), 
            vals.get('writeoff_amount'), 
            vals.get('pembulatan'),  
            context=context)
	if vals.get('type') in ('payment', 'receipt') :
            self._check_double_entries(cr, uid, 0,
                vals.get('type'),
                [x[2]['move_line_id'] for x in vals.get('line_dr_ids',[])],
                [x[2]['move_line_id'] for x in vals.get('line_cr_ids',[])])

        vals['date'] = self._get_default_date(cr, uid, context=context)
        vals.update({'period_id':self.pool['account.period'].find(cr, uid,dt=vals['date'], context=context)[0]})
        vals['number'] = self.generate_sequence(cr, uid, vals, context=context)

        res = super(wtc_account_voucher_new,self).create(cr,uid,vals,context=context)
        #value = self.browse(cr,uid,res)
        #if value.type == 'hutang_lain' :
        #    self.compute_tax(cr,uid,value.id,context)
        #    if amount_wo == 0.0 :
        #        self.cek_amount_total_per_detail(cr, uid, value.id, value, amount, context=context)         
        return res

    def write(self,cr,uid,ids,vals,context=None):
        if ('line_dr_ids' in vals) :
            for x in vals['line_dr_ids'] :
		if x[2]:
                    if x[2].get('date_due') :
                    	x[2].pop('date_due')
       		    if x[2].get('date_original') :
                	x[2].pop('date_original')
        if ('line_cr_ids' in vals) :
            for x in vals['line_cr_ids'] :
                if x[2]:
		    if x[2].get('date_due') :
                    	x[2].pop('date_due')
                    if x[2].get('date_original') :
                    	x[2].pop('date_original')
        vals.update({'period_id':self.pool['account.period'].find(cr, uid,dt=self._get_default_date(cr, uid, context=context).date(), context=context)[0]})
        res = super(wtc_account_voucher_new,self).write(cr,uid,ids,vals)
        #check monitored values to extra checking
        if ('branch_id' in vals) or ('type' in vals) or ('journal_id' in vals) or ('amount' in vals) or ('line_cr_ids' in vals) or ('line_dr_ids' in vals) or ('line_wo_ids' in vals) or ('pembulatan' in vals) :
            value = self.browse(cr,uid,ids)
            if value.amount < 0.0 :
                raise osv.except_osv(('Perhatian !'), ("Paid Amount tidak boleh minus"))
            if not all(line_dr.amount > 0.0 for line_dr in value.line_dr_ids) or not all(line_cr.amount > 0.0 for line_cr in value.line_cr_ids) :
                raise osv.except_osv('Perhatian !', "Amount detil harus lebih besar atau sama dengan 0.0.")
            self._check_on_create_and_write(cr, uid, ids, 
                value.branch_id.id, 
                value.type, 
                value.journal_type, 
                value.amount, 
                sum(line_cr.amount for line_cr in value.line_cr_ids), 
                sum(line_dr.amount for line_dr in value.line_dr_ids), 
                sum(line_wo.amount for line_wo in value.line_wo_ids), 
                value.writeoff_amount, 
                value.pembulatan, 
                context=context)
            if value.type in ('payment', 'receipt') and (('line_dr_ids' in vals) or ('line_cr_ids' in vals)) :
                self._check_double_entries(cr, uid, ids,
                    value.type,
                    [line_dr.move_line_id.id for line_dr in value.line_dr_ids],
                    [line_cr.move_line_id.id for line_cr in value.line_cr_ids])
        return res

    def _get_pembulatan_config(self, cr, uid, branch_id, context=None) :
        branch_config_id = self.pool.get('wtc.branch.config').search(cr,uid,[
                                                                             ('branch_id','=',branch_id),
                                                                             ])
        if not branch_config_id :
            raise osv.except_osv('Error!',"Branch Config tidak ditemukan")
        
        branch_config = self.pool.get('wtc.branch.config').browse(cr,uid,branch_config_id)
        
        if not branch_config.wtc_account_voucher_pembulatan_account_id :
            raise osv.except_osv('Error!',"Account Pembulatan belum diisi dalam branch config")
        
        if not branch_config.nilai_pembulatan :
            raise osv.except_osv('Error!',"Nilai pembulatan belum diisi dalam branch config")
        
        account_id = branch_config.wtc_account_voucher_pembulatan_account_id.id
        nilai_pembulatan = branch_config.nilai_pembulatan

        return (account_id, nilai_pembulatan)

    def _check_on_create_and_write(self, cr, uid, ids, branch_id, vtype, jtype, amount, total_cr, total_dr, total_wo, diff, pembulatan, context=None):
        sign = vtype == 'payment' and -1 or 1
        diff = amount - sign * (total_cr - total_dr) - total_wo

        acc, max_pembulatan = self._get_pembulatan_config(cr, uid, branch_id)

        if pembulatan and abs(diff) > max_pembulatan :
            raise osv.except_osv('Perhatian !', 'Maksimal nilai pembulatan adalah +/- Rp. %s' % max_pembulatan)

        if vtype in ('payment') :
            if jtype == 'bank' and amount > 0.0 and total_cr + total_dr == 0.0 and total_wo != 0.0 and diff == 0.0 :
                #input biaya bank
                return True
            if amount > 0.0 and total_dr > 0 and total_cr == 0.0 and (diff != 0.0 and pembulatan or diff == 0.0) :
                #input pembayaran hutang
                return True

            branch = self.pool.get('wtc.branch').browse(cr,uid,branch_id)
            branch_type = branch and branch.branch_type

            if branch_type == 'HO' and amount > 0.0 and total_dr > 0.0 and total_cr > 0.0 and (diff != 0.0 and pembulatan or diff == 0.0) :
                #input pembayaran hutang dengan DP
                return True
            if branch_type == 'HO' and amount > 0.0 and total_cr + total_dr == 0.0 and total_wo == 0.0 and diff > 0.0 and not pembulatan :
                #input pembayaran DP
                return True

            if jtype != 'bank' and amount > 0.0 and total_cr + total_dr == 0.0 and total_wo != 0.0 and diff == 0.0 :
                raise osv.except_osv('Perhatian !', 'Inputan ini hanya untuk Payment Method bank.')
            if diff != 0.0 and not pembulatan :
                raise osv.except_osv('Perhatian !', 'Difference Amount: Rp %s. Selain pembualatan harus Rp 0.' % diff)
            if branch_type != 'HO' and total_cr > 0.0 :
                raise osv.except_osv('Perhatian !', 'Transaksi dengan Credits hanya bisa dilakukan oleh Head Office.')
            raise osv.except_osv('Perhatian !', 'Cek kembali inputan Anda.')
        elif vtype in ('receipt') :
            if amount == 0.0 and total_dr > 0.0 and total_cr > 0.0 and (diff != 0.0 and pembulatan or diff == 0.0) :
                #input net off (AR vs AP)
                return True
            if amount > 0.0 and total_cr > 0.0 and (diff != 0.0 and pembulatan or diff == 0.0) :
                #input penerimaan AR (optional AP & write off)
                return True
            if amount > 0.0 and total_cr + total_dr == 0.0 and total_wo != 0.0 and diff == 0.0 :
                #input pendapatan
                return True

            if round(diff,2) != 0.00 and not pembulatan :
                raise osv.except_osv('Perhatian !', 'Difference Amount: Rp %s. Selain pembulatan harus Rp 0.' % diff)
            elif total_cr == 0.0 and total_dr > 0.0 :
                raise osv.except_osv('Perhatian !', 'Harus ada detil Credits.')
            raise osv.except_osv('Perhatian !', 'Cek kembali inputan Anda.')
        elif vtype in ('hutang_lain') :
            if amount > 0.0 and total_cr > 0.0 and amount == total_cr and total_dr == 0.0 and total_wo == 0.0 and diff == 0.0 :
                #input HL
                return True
            if amount != total_cr :
                raise osv.except_osv('Perhatian !', 'Total penerimaan uang dan detil harus sama.')
            raise osv.except_osv('Perhatian !', 'Cek kembali inputan Anda.')
        else :
            raise osv.except_osv('ERROR !', 'ERR0143: Harap menghubungi IT')

        return True

    def _check_double_entries(self, cr, uid, ids, vtype, move_line_dr, move_line_cr, context=None):
        if ids == 0 :
            ids = [0]
        ids = str(tuple(ids)).replace(',)', ')')
        if len(move_line_dr) > 0 and vtype == 'payment' :
            move_line_dr = str(tuple(move_line_dr)).replace(',)', ')')
        else :
            move_line_dr = '(0)'
        if len(move_line_cr) > 0 :
            move_line_cr = str(tuple(move_line_cr)).replace(',)', ')')
        else :
            move_line_cr = '(0)'
        query = """
        select avl.move_line_id, aml.name, aml.ref, av.number, av.state
        from wtc_account_voucher av
        inner join wtc_account_voucher_line avl on av.id = avl.voucher_id
        inner join account_move_line aml on avl.move_line_id = aml.id
        where av.state in ('draft','waiting_for_approval','approved','request_approval','confirmed')
        and (av.id not in (%s) or %s)
        and ((avl.type = '%s' and avl.move_line_id in %s)
        or (avl.type = '%s' and avl.move_line_id in %s))
        """ % (ids, '1=1' if ids == [0] else '1=0','dr',move_line_dr,'cr',move_line_cr)
        cr.execute(query)
        data = cr.fetchall()
        if len(data) > 0 :
            message = ""
            for x in data :                 
                message += "Detil %s %s sudah ditarik di nomor %s (%s). \r\n "%(x[1],x[2],x[3],x[4])
            raise osv.except_osv(('Perhatian !'), (message))
                    
    def default_get(self, cr, user, fields_list, context=None):
        if context is None:
            context = {}
        values = super(wtc_account_voucher_new, self).default_get(cr, user, fields_list, context=context)
        values.update({'partner_type': 'customer' if context.get('type') == 'receipt' else 'supplier',
                       'type' : 'receipt' if context.get('type') == 'receipt' else 'payment' if context.get('type') == 'payment' else 'hutang_lain' 
                       })
        return values
                  
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        args = args or []
        if name :
            ids = self.search(cr, uid, [('number', operator, name)] + args, limit=limit, context=context or {})
            if not ids:
                ids = self.search(cr, uid, [('name', operator, name)] + args, limit=limit, context=context or {})
        else :
            ids = self.search(cr, uid, args, limit=limit, context=context or {})
        return self.name_get(cr, uid, ids, context or {})

    def proforma_voucher(self, cr, uid, ids, context=None):
        _date = self._get_default_date(cr, uid, context=context).date()
        self.write(cr, uid, ids, {
            'date':_date,
            'period_id': self.pool.get('account.period').find(cr,uid,_date)[0]
        })

        self.action_move_line_create(cr, uid, ids, context=context)
        return True
    
    def action_cancel_draft(self, cr, uid, ids, context=None):
        self.create_workflow(cr, uid, ids)
        self.write(cr, uid, ids, {'state':'draft'})
        return True

    def cancel_voucher(self, cr, uid, ids, context=None):
        if context == None :
            context = {}
        reconcile_pool = self.pool.get('account.move.reconcile')
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        for voucher in self.browse(cr, uid, ids, context=context):
            # refresh to make sure you don't unlink an already removed move
            voucher.refresh()
            for line in voucher.move_ids:
                # refresh to make sure you don't unreconcile an already unreconciled entry
                line.refresh()
                values = {}
                if line.reconcile_id:
                    move_lines = [move_line.id for move_line in line.reconcile_id.line_id]
                    new_move_line_id = self.create_new_move(cr, uid, ids, line.move_id.id, context)
                    move_lines.append(new_move_line_id)
                    reconcile_pool.unlink(cr, uid, [line.reconcile_id.id])
                    if len(move_lines) >= 2:
                        move_line_pool.reconcile_partial(cr, uid, move_lines, 'auto',context=context)
                elif line.reconcile_partial_id :
                    move_lines = [move_line.id for move_line in line.reconcile_partial_id.line_partial_ids]
                    new_move_line_id = self.create_new_move(cr, uid, ids, line.move_id.id, context)
                    move_lines.append(new_move_line_id)
                    reconcile_pool.unlink(cr, uid, [line.reconcile_partial_id.id])
                    if len(move_lines) >= 2:
                        move_line_pool.reconcile_partial(cr, uid, move_lines, 'auto',context=context)
                    
            if voucher.move_id:
                move_pool.button_cancel(cr, uid, [voucher.move_id.id])
        
        res = {
            'state':'cancel',
            'move_id':False,
            'cancel_uid':uid,
            'cancel_date':datetime.now()
        }
        self.write(cr, uid, ids, res)
        return True
                
    def create_new_move(self, cr, uid, ids, id_old_move, context=None):
        move_pool = self.pool.get('account.move')
        new_move_line_id = False
        new_id_move = move_pool.copy(cr, uid, id_old_move)
        new_move_id = move_pool.browse(cr, uid, new_id_move)
        for line in new_move_id.line_id :
            if line.account_id.type in ('payable','receivable') :
                new_move_line_id = line.id
            credit = line.debit
            debit = line.credit
            line.write({'debit':debit,'credit':credit})
            
        return new_move_line_id                
                
    def unlink(self, cr, uid, ids, context=None):
        for t in self.read(cr, uid, ids, ['state'], context=context):
            if t['state'] not in ('draft'):
                raise osv.except_osv(_('Invalid Action!'), _('Cannot delete voucher(s) which are already opened or paid.'))
        return super(wtc_account_voucher_new, self).unlink(cr, uid, ids, context=context)

    def onchange_kwitansi(self,cr,uid,ids,kwitansi,context=None):
        vals = {}
        if kwitansi :
            vals['line_cr_ids'] = False
            vals['line_dr_ids'] = False
            vals['line_wo_ids'] = False
        return {'value':vals}
    
    def first_move_line_get(self, cr, uid, voucher, move_id, company_currency, current_currency, context=None):
        debit = credit = 0.0

        if voucher.type == 'payment':
            credit = voucher.amount
        elif voucher.type in ('receipt','hutang_lain'):
            debit = voucher.amount
        if debit < 0: credit = -debit; debit = 0.0
        if credit < 0: debit = -credit; credit = 0.0
        sign = debit - credit < 0 and -1 or 1
        #set the first line of the voucher
        move_line = {
                'branch_id' : voucher.branch_id.id,
                'division' : voucher.division,
                'name': voucher.name or voucher.number or '/',
                'debit': debit,
                'credit': credit,
                'account_id': voucher.account_id.id,
                'move_id': move_id,
                'journal_id': voucher.journal_id.id,
                'period_id': voucher.period_id.id,
                'partner_id': voucher.partner_id.id,
                'currency_id': company_currency <> current_currency and  current_currency or False,
                'amount_currency': (sign * abs(voucher.amount) # amount < 0 for refunds
                    if company_currency != current_currency else 0.0),
                'date': voucher.date,
                #'date_maturity': voucher.date_due
            }
        if voucher.journal_type == 'edc' :
            move_line['partner_id'] = voucher.journal_id.partner_id.id   
        return move_line
        
    def account_move_get(self, cr, uid, voucher, context=None):
        seq_obj = self.pool.get('ir.sequence')
        if voucher.number:
            name = voucher.number
        elif voucher.journal_id.sequence_id:
            if not voucher.journal_id.sequence_id.active:
                raise osv.except_osv(_('Configuration Error !'),
                    _('Please activate the sequence of selected journal !'))
            c = dict(context)
            c.update({'fiscalyear_id': voucher.period_id.fiscalyear_id.id})
            name = seq_obj.next_by_id(cr, uid, voucher.journal_id.sequence_id.id, context=c)
        else:
            raise osv.except_osv(_('Error!'),
                        _('Please define a sequence on the journal.'))
        move = {
            'name': name,
            'journal_id': voucher.journal_id.id,
            'narration': voucher.narration,
            'date': voucher.date,
            'ref': name,
            'period_id': voucher.period_id.id,
        }
        return move
            
    def voucher_move_line_create(self, cr, uid, voucher, line_total, move_id, company_currency, current_currency, context=None):
        if context is None:
            context = {}
        move_line_obj = self.pool.get('account.move.line')
        currency_obj = self.pool.get('res.currency')
        tax_obj = self.pool.get('account.tax')
        tot_line = line_total
        rec_lst_ids = []
        voucher_currency = voucher.journal_id.currency or voucher.company_id.currency_id
        prec = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')

        if voucher.inter_branch_id :
            branch_id = voucher.inter_branch_id.id
        else :
            branch_id = voucher.branch_id.id 
                             
        for line in voucher.line_ids:
            if line.type == 'wo' or not line.amount and not (line.move_line_id and not float_compare(line.move_line_id.debit, line.move_line_id.credit, precision_digits=prec) and not float_compare(line.move_line_id.debit, 0.0, precision_digits=prec)):
                continue
            if voucher.type == 'receipt' :
                if line.type == 'cr' :
                    branch_id = voucher.inter_branch_id.id
                elif line.type == 'dr' :
                    branch_id = voucher.branch_id.id 
            else :
                if line.type == 'dr' :
                    branch_id = voucher.inter_branch_id.id
                elif line.type == 'cr' :
                    branch_id = voucher.branch_id.id 

            amount = line.amount
            if line.amount == line.amount_unreconciled:
                if not line.move_line_id:
                    raise osv.except_osv(_('Wrong voucher line'),_("The invoice you are willing to pay is not valid anymore."))
                sign = line.type =='dr' and -1 or 1
                
            move_line = {
                'branch_id' : branch_id,
                'division' : voucher.division,
                'journal_id': voucher.journal_id.id,
                'period_id': voucher.period_id.id,
                'name': line.name or '/',
                'account_id': line.account_id.id,
                'move_id': move_id,
                'partner_id': voucher.partner_id.id,
                'currency_id': line.move_line_id and (company_currency <> line.move_line_id.currency_id.id and line.move_line_id.currency_id.id) or False,
                'quantity': 1,
                'credit': 0.0,
                'debit': 0.0,
                'date': voucher.date
            }
            if amount < 0:
                amount = -amount
                if line.type == 'dr':
                    line.type = 'cr'
                elif line.type == 'cr':
                    line.type = 'dr'

            if (line.type=='dr'):
                tot_line += amount
                move_line['debit'] = amount
            elif (line.type=='cr'):
                tot_line -= amount
                move_line['credit'] = amount

            voucher_line = move_line_obj.create(cr, uid, move_line, context=context)
            rec_ids = [voucher_line, line.move_line_id.id]
            
            if line.move_line_id.id:
                rec_lst_ids.append(rec_ids)
        return (tot_line, rec_lst_ids)
                
                       
    def writeoff_move_line_get(self, cr, uid, voucher, line_total, move_id, name, company_currency, current_currency, context=None):
        currency_obj = self.pool.get('res.currency')
        move_line = {}
        current_currency_obj = voucher.currency_id or voucher.journal_id.company_id.currency_id
        amount_wo = 0.0
        
        if not currency_obj.is_zero(cr, uid, current_currency_obj, line_total):
            account_id = False
            write_off_name = ''
            sign = voucher.type == 'payment' and -1 or 1

            if voucher.line_wo_ids :
                for line in voucher.line_wo_ids :
                    account_id = line.account_id.id
                    write_off_name = line.name
                    ####amount
                    amount_wo += line.amount
                    amount = sign * line.amount
                    move_line = {
                        'branch_id' : voucher.inter_branch_id.id,
                        'division' : voucher.division,
                        'name': write_off_name or name,
                        'account_id': account_id,
                        'move_id': move_id,
                        'partner_id': voucher.partner_id.id,
                        'date': voucher.date,
                        'credit': amount if amount > 0 else 0.0,
                        'debit': -amount if amount < 0 else 0.0,
                        'amount_currency': company_currency <> current_currency and (sign * -1 * line.amount) or 0.0,
                        'currency_id': company_currency <> current_currency and current_currency or False,
                    }   
                    self.pool.get('account.move.line').create(cr, uid, move_line, context=context)
            
            diff = line_total - sign * amount_wo 

            if diff:
                diff_name = False
                if voucher.pembulatan :
                    branch_config_id = self.pool.get('wtc.branch.config').search(cr,uid,[
                                                                                         ('branch_id','=',voucher.branch_id.id),
                                                                                         ])
                    if not branch_config_id :
                        raise osv.except_osv('Error!',"Branch Config tidak ditemukan")
                    
                    branch_config_id = self.pool.get('wtc.branch.config').browse(cr,uid,branch_config_id)
                    
                    if not branch_config_id.wtc_account_voucher_pembulatan_account_id :
                        raise osv.except_osv('Error!',"Account Pembulatan belum diisi dalam branch config")
                    
                    if not branch_config_id.nilai_pembulatan :
                        raise osv.except_osv('Error!',"Nilai pembulatan belum diisi dalam branch config")
                    
                    account_id = branch_config_id.wtc_account_voucher_pembulatan_account_id.id
                    nilai_pembulatan = branch_config_id.nilai_pembulatan

                    diff_name = '%s (Pembulatan)' % name
                    
                    if abs(diff) > nilai_pembulatan :
                        raise osv.except_osv('Error!',"Nilai different amount tidak boleh melebihi batas pembulatan")
                    
                elif voucher.type == 'payment':
                    account_id = voucher.partner_id.property_account_receivable.id
                else:
                    account_id = voucher.partner_id.property_account_payable.id
                move_line = {
                    'branch_id' : voucher.branch_id.id,
                    'division' : voucher.division,
                    'name': diff_name or name,
                    'account_id': account_id,
                    'move_id': move_id,
                    'partner_id': voucher.partner_id.id,
                    'date': voucher.date,
                    'credit': diff > 0 and diff or 0.0,
                    'debit': diff < 0 and -diff or 0.0,
                    'amount_currency': company_currency <> current_currency and (sign * -1 * voucher.writeoff_amount) or 0.0,
                    'currency_id': company_currency <> current_currency and current_currency or False,
                }
                self.pool.get('account.move.line').create(cr, uid, move_line, context=context)

        return move_line
                
    def _get_company_currency(self, cr, uid, voucher_id, context=None):
        return self.pool.get('wtc.account.voucher').browse(cr,uid,voucher_id,context).journal_id.company_id.currency_id.id
                 
    def _get_current_currency(self, cr, uid, voucher_id, context=None):
        voucher = self.pool.get('wtc.account.voucher').browse(cr,uid,voucher_id,context)
        return voucher.currency_id.id or self._get_company_currency(cr,uid,voucher.id,context)
                
    def _sel_context(self, cr, uid, voucher, context=None):
        company_currency = self._get_company_currency(cr, uid, voucher.id, context)
        current_currency = self._get_current_currency(cr, uid, voucher.id, context)
        if current_currency <> company_currency:
            context_multi_currency = context.copy()
            context_multi_currency.update({'date': voucher.date})
            return context_multi_currency
        return context
                            
    def action_move_line_create(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        for voucher in self.browse(cr, uid, ids, context=context):
            if not voucher.amount and voucher.journal_id.type == 'edc'  :
                raise osv.except_osv('Perhatian !', "'Paid Amount' harus diisi untuk pembayaran menggunakan EDC.")
            if voucher.journal_id.branch_id != voucher.branch_id :
                raise osv.except_osv('Perhatian !', 'Branch & Payment Method nya tidak sesuai.')

            account_id = voucher.journal_id.default_credit_account_id or voucher.journal_id.default_debit_account_id
            if voucher.journal_id.type == 'cash' and voucher.type=='payment':
                if voucher.amount > voucher.journal_id.default_debit_account_id.balance :
                        raise osv.except_osv(('Perhatian !'), ("Saldo kas tidak mencukupi !"))
                  
            if voucher.account_id.id != account_id.id :
                self.write(cr, uid, voucher.id, {'account_id' : account_id.id})

            local_context = dict(context, force_company=voucher.journal_id.company_id.id)
            if voucher.move_id:
                continue
            company_currency = voucher.journal_id.company_id.currency_id.id
            current_currency = voucher.currency_id.id or company_currency
            ctx = context.copy()
            if current_currency <> company_currency :
                ctx.update({'date': voucher.date})

            move_vals = self.account_move_get(cr, uid, voucher, context=context)
            move_id = move_pool.create(cr, uid, move_vals, context=context)
            name = move_vals['name']
            
            ctx = local_context.copy()
            ctx['novalidate'] = True

            move_line_id = move_line_pool.create(cr, uid, self.first_move_line_get(cr,uid,voucher, move_id, company_currency, current_currency, local_context), ctx)
            move_line_brw = move_line_pool.browse(cr, uid, move_line_id, context=context)
            line_total = move_line_brw.debit - move_line_brw.credit
            rec_list_ids = []
            line_total, rec_list_ids = self.voucher_move_line_create(cr, uid, voucher, line_total, move_id, company_currency, current_currency, ctx)

            ml_writeoff = self.writeoff_move_line_get(cr, uid, voucher, line_total, move_id, name, company_currency, current_currency, ctx)

            # We post the voucher.
            self.write(cr, uid, [voucher.id], {
                'move_id': move_id,
                'state': 'posted',
                'confirm_uid':uid,
                'confirm_date':datetime.now(),
            })
            if voucher.journal_id.entry_posted:
                move_pool.post(cr, uid, [move_id], context={})
            else :
                move_pool.validate(cr, uid, [move_id], context={})
            reconcile = False
            for rec_ids in rec_list_ids:
                if len(rec_ids) >= 2:
                    reconcile = move_line_pool.reconcile_partial(cr, uid, rec_ids)
        return True
                    
    def validate_or_rfa(self,cr,uid,ids,context=None):
        obj_av = self.browse(cr, uid, ids, context=context)
        if obj_av.total_debit > 0 or obj_av.type == 'hutang_lain':
            self.request_approval(cr, uid, ids, context)
        else :
            self.proforma_voucher(cr, uid, ids, context)
        return True

    def request_approval(self, cr, uid, ids,context=None):
        obj_av = self.browse(cr, uid, ids, context=context)
        obj_matrix = self.pool.get("wtc.approval.matrixbiaya")
        total = 0.0
        jenis_trx = 'HC'
        for x in obj_av.line_dr_ids :
            total += x.amount
            if x.name:
                split_trx = x.name.split('/')
                if split_trx[0] != 'HC':
                    jenis_trx = ''

        type = obj_av.type
        if type == 'payment' :
            view_name = 'wtc.account.voucher.payment.form'
            if jenis_trx != 'HC':
                total = max(total, 2000001)

        elif type == 'receipt' :
            view_name = 'wtc.account.voucher.receipt.form'
            total_cr = sum([x.amount for x in obj_av.line_cr_ids])
            selisih = total_cr - total
            if selisih == 0:
                total = 1

        elif type == 'hutang_lain':
            view_name = 'wtc.account.voucher.other.payable.form'
            type = 'purchase'
            total = 0.0
            for x in obj_av.line_cr_ids:
                total += x.amount
        obj_matrix.request_by_value(cr, uid, ids, obj_av, total,type,view_name)
        self.write(cr, uid, ids, {'state': 'waiting_for_approval','approval_state':'rf'})
        return True        
    
    def approval_approve(self, cr, uid, ids, context=None):
        obj_av = self.browse(cr, uid, ids, context=context) 
        approval_sts = self.pool.get("wtc.approval.matrixbiaya").approve(cr, uid, ids, obj_av)
        if approval_sts == 1:
            self.write(cr, uid, ids, {'approval_state':'a','state':'approved'})
        elif approval_sts == 0:
            raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group approval"))
        return True

    @api.multi
    def action_klik_payment(self):
        self.write({
            'is_payment':True,
            'payment_klik_uid':self._uid,
            'payment_klik_date':datetime.now(),
        })
                                                                                        
class wtc_account_voucher_new_line(models.Model):
    _name = 'wtc.account.voucher.line'
    _description = 'Account Voucher Line Custom'
    
    @api.one
    @api.depends('move_line_id')
    def _compute_balance(self):
        res = {}
        move_line = self.move_line_id or False
        company_currency = self.voucher_id.journal_id.company_id.currency_id.id
        voucher_currency = self.voucher_id.currency_id and self.voucher_id.currency_id.id or company_currency
                    
        if not move_line:
            self.amount_original = 0.0
            self.amount_unreconciled = 0.0
        elif move_line.currency_id and voucher_currency == move_line.currency_id.id:
            self.amount_original = abs(move_line.amount_currency)
            self.amount_unreconciled = abs(move_line.amount_residual_currency)
        else :
            self.amount_original = self.pool.get('res.currency').compute(self._cr, self._uid, company_currency, voucher_currency, move_line.credit or move_line.debit or 0.0)
            self.amount_unreconciled = self.pool.get('res.currency').compute(self._cr, self._uid, company_currency, voucher_currency, abs(move_line.amount_residual))
            
            
    @api.one
    @api.depends('currency_id')            
    def _get_currency_id(self):
        res = {}
        move_line = self.move_line_id
        if move_line:
            currency_id =  move_line.currency_id and move_line.currency_id.id or move_line.company_id.currency_id.id
        else:
            currency_id =  self.voucher_id.currency_id and self.voucher_id.currency_id.id or self.voucher_id.company_id.currency_id.id
        return currency_id
            
            
    voucher_id = fields.Many2one('wtc.account.voucher', 'Voucher', required=1, ondelete='cascade')
    name = fields.Char('Description',)
    account_id = fields.Many2one('account.account','Account', required=True)
    partner_id = fields.Many2one(related='voucher_id.partner_id', string='Partner', store=True)
    untax_amount = fields.Float('Untax Amount')
    amount = fields.Float('Amount', digits_compute=dp.get_precision('Account'))
    reconcile = fields.Boolean('Full Reconcile')
    type = fields.Selection([('dr','Debit'),('cr','Credit'),('wo','Writeoff')], 'Dr/Cr/Wo')
    move_line_id = fields.Many2one('account.move.line', 'Journal Item', copy=False)
    date_original =  fields.Date(related='move_line_id.date', string='Date', readonly=1)
    date_due =  fields.Date(related='move_line_id.date_maturity', string='Due Date', readonly=1)
    amount_original = fields.Float(string='Original Amount', store=True, digits_compute=dp.get_precision('Account'), compute='_compute_balance')
    amount_unreconciled = fields.Float(string='Open Balance', store=True, digits_compute=dp.get_precision('Account'), compute='_compute_balance')
    company_id = fields.Many2one(related='voucher_id.company_id', relation='res.company',string='Company', store=True, readonly=True)
    kwitansi = fields.Boolean(related='voucher_id.kwitansi',string='Yg Sudah Print Kwitansi')
    branch_id = fields.Many2one('wtc.branch',string='Branch')        
    currency_id = fields.Many2one('res.currency', string='Currency',readonly=True,store=True, compute='_get_currency_id')
         
    def onchange_reconcile(self, cr, uid, ids, reconcile, amount, amount_unreconciled, context=None):
        vals = {}
        if reconcile:
            vals = { 'amount': amount_unreconciled}
        return {'value': vals}

    def onchange_amount(self, cr, uid, ids, amount, amount_unreconciled, context=None):
        vals = {}
        warning = {}
        if amount :
            vals['reconcile'] = (amount == amount_unreconciled)
            
        if amount > amount_unreconciled :
            warning = {
                        'title': ('Perhatian !'),
                        'message': ("Nilai allocation tidak boleh lebih dari open balance !"),
                    }  
            vals['amount'] = amount_unreconciled

        if amount < 0 :
            warning = {
                'title': 'Perhatian !',
                'message': 'Nilai allocation tidak boleh lebih kecil dari 0 !',
            }
            vals['amount'] = 0

        return {'value': vals,'warning':warning}

    def onchange_move_line_id(self, cr, user, ids, move_line_id, amount,currency_id,journal, context=None):
        res = {}
        Warning = {}
        
        move_line_pool = self.pool.get('account.move.line')
        currency_pool = self.pool.get('res.currency')  
        
        if not journal :
            Warning = {
                        'title': ('Perhatian !'),
                        'message': ("Harap isi Payment Method terbelih dahulu !"),
                    }
        if move_line_id : 
            move_line = move_line_pool.browse(cr, user, move_line_id, context=context)
            if move_line.credit:
                ttype = 'dr'
            else:
                ttype = 'cr'

            remaining_amount = amount
            journal_brw = self.pool.get('account.journal').browse(cr,user,journal)
            move_line_brw = move_line_pool.browse(cr,user,move_line_id)
            currency_id = currency_id or journal_brw.company_id.currency_id.id
            company_currency = journal_brw.company_id.currency_id.id
            
            if move_line_brw.currency_id and currency_id == move_line_brw.currency_id.id:
                amount_original = abs(move_line_brw.amount_currency)
                amount_unreconciled = abs(move_line_brw.amount_residual_currency)
            else:
                #always use the amount booked in the company currency as the basis of the conversion into the voucher currency
                amount_original = currency_pool.compute(cr, user, company_currency, currency_id, move_line_brw.credit or move_line_brw.debit or 0.0, context=context)
                amount_unreconciled = currency_pool.compute(cr, user, company_currency, currency_id, abs(move_line_brw.amount_residual), context=context)
            res.update({
                                'name':move_line_brw.move_id.name,
                                'move_line_id':move_line_brw.id,                
                                'amount_original': amount_original,
                                'amount': move_line_id and min(abs(remaining_amount), amount_unreconciled) or 0.0,
                                'date_original':move_line_brw.date,
                                'date_due':move_line_brw.date_maturity,
                                'amount_unreconciled': amount_unreconciled,
                                'account_id': move_line.account_id.id,
                                'type': ttype,
                                'currency_id': move_line.currency_id and move_line.currency_id.id or move_line.company_id.currency_id.id,                             
                    })
            
            ####################### CEK CONSOLIDATE INVOICE ###############################
            if not move_line_brw.invoice.asset :
                if move_line_brw.invoice.type == 'in_invoice' and move_line_brw.invoice.tipe == 'purchase' and not move_line_brw.invoice.consolidated :
                    Warning = {
                                'title': ('Perhatian !'),
                                'message': ("Penerimaan atas Invoice '%s' belum lengkap, mohon lakukan consolidate invoice !")%(move_line_brw.invoice.number),
                            }
                    res = {}
                    res['move_line_id'] = False
        if Warning :
            res.update({
                        'name':False,
                        'move_line_id':False,                
                        'amount_original': False,
                        'amount': False,
                        'date_original':False,
                        'date_due':False,
                        'amount_unreconciled': False,
                        'account_id': False,
                        'type': False,
                        'currency_id': False,                             
                    })
        return {
            'value':res,
            'warning':Warning
        }

    def default_get(self, cr, user, fields_list, context=None):
        if context is None:
            context = {}
        journal_id = context.get('journal_id', False)
        partner_id = context.get('partner_id', False)
        journal_pool = self.pool.get('account.journal')
        partner_pool = self.pool.get('res.partner')
        values = super(wtc_account_voucher_new_line, self).default_get(cr, user, fields_list, context=context)
        if (not journal_id) or ('account_id' not in fields_list):
            return values
        journal = journal_pool.browse(cr, user, journal_id, context=context)
        account_id = False
        ttype = 'cr'
        if journal.type in ('sale', 'sale_refund'):
            account_id = journal.default_credit_account_id and journal.default_credit_account_id.id or False
            ttype = 'cr'
        elif journal.type in ('purchase', 'expense', 'purchase_refund'):
            account_id = journal.default_debit_account_id and journal.default_debit_account_id.id or False
            ttype = 'dr'
        elif partner_id:
            partner = partner_pool.browse(cr, user, partner_id, context=context)
            if context.get('type') == 'payment':
                ttype = 'dr'
                account_id = partner.property_account_payable.id
            elif context.get('type') == 'receipt':
                account_id = partner.property_account_receivable.id

        values.update({
            'account_id':account_id,
            'type':ttype
        })
        return values
                
    def name_payable_onchange(self,cr,uid,ids,account_id,branch_id,division,context=None):
        if not branch_id or not division:
            raise except_orm(_('No Branch Defined!'), _('Sebelum menambah detil transaksi,\n harap isi branch dan division terlebih dahulu.'))
        dom2={}
        vals={}
        edi_doc_list2 = ['&', ('active','=',True), ('type','=','payable')]
        dict=self.pool.get('wtc.account.filter').get_domain_account(cr,uid,ids,'other_payable',context=None)
        edi_doc_list2.extend(dict)      
        dom2['account_id'] = edi_doc_list2

        
        return {'domain':dom2,'value':vals}
    
    def writeoff_account_onchange(self,cr,uid,ids,account_id,branch_id,division,context=None):
        if not branch_id or not division:
            raise osv.except_osv(_('No Branch Defined!'), _('Sebelum menambah detil transaksi,\n harap isi branch dan division terlebih dahulu.'))
        dom2={}
        vals={}
        dict=self.pool.get('wtc.account.filter').get_domain_account(cr,uid,ids,'payments',context=None)
        dom2['account_id'] = dict

        
        return {'domain':dom2,'value':vals}

                    
class wtc_register_kwitansi(models.Model):
    _inherit = 'wtc.register.kwitansi.line'
    
    new_payment_id = fields.Many2one('wtc.account.voucher',string= 'Payment No.')
    
