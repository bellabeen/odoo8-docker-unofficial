import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp import SUPERUSER_ID
from openerp import tools
import pytz
from lxml import etree
from openerp.exceptions import except_orm, Warning, RedirectWarning

class wtc_dn_nc(models.Model):
    _name = 'wtc.dn.nc'
    _description = 'Debit and Credit Note Custom'
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
        if self._context.get('type') == 'DN' :
            name = 'customer'
        self.partner_type = name
            
    @api.one
    def _get_company(self):
        company = self.env['res.company']._company_default_get(self._cr, self._uid, 'account.voucher')
        return company
                    
    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
        
                        
#     @api.multi
#     @api.depends('line_ids.amount','line.tax_id')
#     def _compute_amount(self):
#         amount_total = 0.0
#         untaxes = 0.0
#         taxes = 0.0 
#         if self.line_ids :
#             for x in self.line_ids :
#                 tax = x.tax_id.compute_all(x.amount,1)
#                 taxes += tax['total_included'] - tax['total']
#                 untaxes += x.amount
#                 amount_total += taxes + untaxes
#         self.untaxed_amount = untaxes
#         self.tax_amount = taxes
#         self.amount = amount_total
            
                           
    @api.one
    @api.depends('journal_id')
    def _journal_type(self):
        self.journal_type = self.journal_id.type
#                               
#     @api.one
#     @api.depends('line_ids','untaxed_amount')
#     def _total_untax(self):
#         value =  0.0
#         for line in self.line_ids:
#             value += line.amount_subtotal            
#         self.untaxed_amount = value
#         
#     @api.one
#     @api.depends('line_ids','tax_amount')
#     def _total_tax(self):
#         value =  0.0
#         for line in self.line_ids:
#             for x in line.tax_id :
#                 value += x.tax_amount
#         self.tax_amount = value
#         
#     @api.one
#     @api.depends('line_ids','amount')
#     def _total_amount(self):
#         value =  0.0
#         for line in self.line_ids:
#             value += line.amount      
#             for x in line.tax_id :
#                 tax = x.compute_all(line.amount,1)
#                 value += tax['total_included'] - tax['total']
#                                   
#         self.amount = value
        
    @api.one
    @api.depends('line_ids.amount','line_ids.tax_amount')
    def _compute_amount(self):
        self.untaxed_amount = sum(line.amount_subtotal for line in self.line_ids)
        self.tax_amount = sum(line.tax_amount for line in self.line_ids)
        self.amount = self.untaxed_amount + self.tax_amount
                                
                                        
    type = fields.Selection([
                            ('DN','DN'),
                            ('NC','NC'),
                            ],'Default Type', readonly=True, states={'draft':[('readonly',False)]})
    name = fields.Char('Memo', readonly=True, states={'draft':[('readonly',False)]},default='')
    journal_id = fields.Many2one('account.journal', 'Journal', required=True, readonly=True, states={'draft':[('readonly',False)]})
    account_id = fields.Many2one('account.account', 'Account', required=True, readonly=True, states={'draft':[('readonly',False)]})
    line_ids = fields.One2many('wtc.dn.nc.line', 'voucher_id', 'Voucher Lines',
                               readonly=True, copy=True,
                               states={'draft':[('readonly',False)]})
    line_cr_ids = fields.One2many('wtc.dn.nc.line','voucher_id','Credits',domain=[('type','=','cr')], context={'default_type':'cr'}, readonly=True, states={'draft':[('readonly',False)]})
    line_dr_ids = fields.One2many('wtc.dn.nc.line','voucher_id','Debits',domain=[('type','=','dr'),('is_rutin','=',False)], context={'default_type':'dr'}, readonly=True, states={'draft':[('readonly',False)]})
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
    number = fields.Char('Number', readonly=True, copy=False)
    move_id = fields.Many2one('account.move', 'Account Entry', copy=False)
    move_ids = fields.One2many(related='move_id.line_id', string='Journal Items', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Partner', change_default=1, readonly=True, states={'draft':[('readonly',False)]})
    tax_id = fields.Many2one('account.tax', 'Tax', readonly=True, states={'draft':[('readonly',False)]}, domain=[('price_include','=', False)])
    date_due = fields.Date('Due Date', readonly=True, select=True, states={'draft':[('readonly',False)]})        
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
    jenis_transaksi_id =  fields.Many2one('wtc.payments.request.type', string='Tipe Transaksi',readonly=True, states={'draft': [('readonly', False)]},domain="[('type','=','NC')]")
    no_document =  fields.Char(string='No Document', index=True)
    tgl_document =  fields.Date(string='Tgl Document', readonly=True, states={'draft': [('readonly', False)]}, index=True, copy=False)
    payments_request_ids =  fields.One2many('wtc.dn.nc.line', 'voucher_id',readonly=True, copy=True)
    paid_amount =  fields.Float(string='Paid Amount')
    
    approval_ids = fields.One2many('wtc.approval.line','transaction_id',string="Table Approval",domain=[('form_id','=',_name)])
    approval_state = fields.Selection([('b','Belum Request'),('rf','Request For Approval'),('a','Approved'),('r','Reject')],'Approval State', default='b', readonly=True)
    kwitansi =  fields.Boolean(string='Yg Sudah Print Kwitansi')
    currency_id = fields.Many2one('res.currency', string='Currency')
    amount = fields.Float(compute = '_compute_amount',string = 'Total', store=True,digits_compute=dp.get_precision('Account'))
    tax_amount = fields.Float(compute = '_compute_amount',string = 'Taxes', digits_compute=dp.get_precision('Account'),store=True)
    untaxed_amount = fields.Float(compute = '_compute_amount', digits_compute=dp.get_precision('Account'), string='Untaxed Amount', store=True)

    # New Deveplopment
    line_dr_rutin_ids = fields.One2many('wtc.dn.nc.line','voucher_id','Debits',domain=[('type','=','dr'),('is_rutin','=',True)], context={'default_type':'dr','default_is_rutin':True}, readonly=True, states={'draft':[('readonly',False)]})
    jml_history = fields.Integer('Jumlah History',compute="compute_history_rutin")

        
    # def jenis_transaksi_change(self, cr, uid, ids, jenis_transaksi_id,branch_id):
    #     payments_request_histrory=[]
    #     if jenis_transaksi_id : 
    #         pr_pool = self.pool.get('wtc.dn.nc')
    #         pr_search = pr_pool.search(cr,uid,[('jenis_transaksi_id','=',jenis_transaksi_id),('branch_id','=',branch_id),])
    #         pr_pool2 = self.pool.get('wtc.dn.nc.line')
    #         pr_search2 = pr_pool2.search(cr,uid,[('voucher_id','=',pr_search),])
    #         payments_request_histrory = []
    #         if not pr_search2 :
    #             payments_request_histrory = []
    #         elif pr_search2 :
    #             pr_browse = pr_pool2.browse(cr,uid,pr_search2)           
    #             for x in pr_browse :
    #                 payments_request_histrory.append([0,0,{
    #                                  'account_id':x.account_id,
    #                                  'name':x.name,
    #                                  'amount':x.amount,
    #                 }])
    #     return {'value':{'payments_request_ids': payments_request_histrory}}
                 
    def transaksi_change(self,cr,uid,ids,transaksi,context=None):
        val = {}
        if transaksi :
            val['jenis_transaksi_id'] = False
        return {'value':val}
        
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
    
    def branch_onchange_payment_request(self,cr,uid,ids,branch_id,context=None):     
        val ={}
        if branch_id :
            branch_config =self.pool.get('wtc.branch.config').search(cr,uid,[
                                                                             ('branch_id','=',branch_id)])
            branch_config_browse = self.pool.get('wtc.branch.config').browse(cr,uid,branch_config)
            journal_id=branch_config_browse.wtc_payment_request_account_id
            account_id=branch_config_browse.wtc_payment_request_account_id.default_credit_account_id.id
            if not journal_id :
                    raise except_orm('Warning!', 'Konfigurasi jurnal cabang belum dibuat, silahkan setting dulu !')
            if not account_id :
                    raise except_orm('Warning!', 'Konfigurasi jurnal account cabang belum dibuat, silahkan setting dulu !')
            if journal_id.currency:
                currency_id = journal_id.currency.id
            else:
                currency_id = journal_id.company_id.currency_id.id
                
            period_id = self.pool['account.period'].find(cr, uid, dt=self._get_default_date(cr,uid,context=context).date(),context=context)
            val['account_id'] = account_id
            val['journal_id'] = journal_id.id if journal_id else journal_id       
            val['period_id'] = period_id[0] if period_id else period_id
            val['currency_id'] = currency_id 
            val['company_id'] = journal_id.company_id.id        
        return {'value':val}
              
    def print_wizard_kwitansi(self,cr,uid,ids,context=None):  
        obj_claim_kpb = self.browse(cr,uid,ids)
        obj_ir_view = self.pool.get("ir.ui.view")
        obj_ir_view_search= obj_ir_view.search(cr,uid,[("name", "=", 'wtc.kwitansi.wizard.other.receivable.dn'), ("model", "=", 'wtc.dn.nc'),])
        obj_ir_view_browse = obj_ir_view.browse(cr,uid,obj_ir_view_search)
        return {
            'name': 'Kwitansi',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.dn.nc',
            'type': 'ir.actions.act_window',
            'view_id' : obj_ir_view_browse.id,
            'target': 'new',
            'nodestroy': True,
            'res_id': obj_claim_kpb.id,
            'context': context
            }
        
    def reg_kwitansi(self, cr, uid, ids, vals, context=None):
        res = super(wtc_dn_nc, self).write(cr, uid, ids, vals, context=context)
        return res
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(wtc_dn_nc, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        obj_active = self.browse(cr,uid,context.get('active_ids',[]))
        if not context.get('portal') :
            branch_id = obj_active.branch_id.id
            kwitansi=obj_active.kwitansi_id.id
            doc = etree.XML(res['arch'])
            nodes = doc.xpath("//field[@name='kwitansi_id']")
            for node in nodes:
                    node.set('domain', '[("payment_id","=",False),("dn_nc_id","=",False),("branch_id", "=", '+ str(branch_id)+'),("state","=","open")]')
            res['arch'] = etree.tostring(doc)
        return res
        
    def generate_sequence(self,cr,uid,vals,context=None):
        name = '/'
        if context.get('type') == 'NC' :
            name = self.pool.get('ir.sequence').get_per_branch(cr,uid,vals.get('branch_id'),'NC')
        elif context.get('type') == 'DN' :
            name = self.pool.get('ir.sequence').get_per_branch(cr,uid,vals.get('branch_id'),'DN')

        return name 
                    
    def faktur_pajak_change(self,cr,uid,ids,no_faktur_pajak,context=None):   
        value = {}
        warning = {}
        if no_faktur_pajak :
            cek = no_faktur_pajak.isdigit()
            if not cek :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('Nomor Faktur Pajak Hanya Boleh Angka ! ')),
                }
                value = {
                         'no_faktur_pajak':False
                         }     
        return {'warning':warning,'value':value} 
    
    def create(self,cr,uid,vals,context=None):
        vals['date'] = self._get_default_date(cr, uid, context=context)     
        vals['number'] = self.generate_sequence(cr, uid, vals, context=context)       
        amount = 0.0 
        if not vals.get('amount') :
            vals['amount'] = 0.0 
        if vals.get('amount') < 0.0  :
            raise osv.except_osv(('Perhatian !'), ("Paid Amount tidak boleh minus"))
        if not vals.get('period_id') :
            vals['period_id'] = self.pool['account.period'].find(cr, uid,dt=vals['date'], context=context)[0]
        if not vals.get('currency_id') :
            journal_id = self.pool.get('account.journal').browse(cr,uid,vals['journal_id'])
            vals['currency_id'] = journal_id.company_id.currency_id.id
        
        if vals.get('type') == 'NC' :
            if not vals.get('line_dr_ids',False) and not vals.get('line_dr_rutin_ids',False):
                raise osv.except_osv(('Perhatian !'), ("Detail harus diisi !"))
                      
        if vals.get('type') == 'DN' :
            if not vals.get('line_cr_ids',False) :
                raise osv.except_osv(('Perhatian !'), ("Detail harus diisi !"))                

        res = super(wtc_dn_nc,self).create(cr,uid,vals,context=context)
        return res

                        
    def compute_tax(self, cr, uid, ids, context=None):
        return True
                    
    def default_get(self, cr, user, fields_list, context=None):
        if context is None:
            context = {}
        values = super(wtc_dn_nc, self).default_get(cr, user, fields_list, context=context)
        values.update({'partner_type': 'customer' if context.get('type') == 'DN' else 'supplier','type':context.get('type')})
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
             
    def onchange_term_id(self, cr, uid, ids, term_id, amount):
        term_pool = self.pool.get('account.payment.term')
        terms = False
        due_date = False
        default = {'date_due':False}
        if term_id and amount:
            terms = term_pool.compute(cr, uid, term_id, amount)
        if terms:
            due_date = terms[-1][0]
            default.update({
                'date_due':due_date
            })
        return {'value':default}
    
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
        self.write(cr,uid,ids,{'cancel_uid':uid,'cancel_date':datetime.now()})
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
        return super(wtc_dn_nc, self).unlink(cr, uid, ids, context=context)
     

    def change_kwitansi(self,cr,uid,ids,kwitansi,context=None):
        vals = {}
        if kwitansi :
            vals['line_cr_ids'] = False
            vals['line_dr_ids'] = False
        return {'value':vals}
    
    def first_move_line_get(self, cr, uid, voucher, move_id, company_currency, current_currency, context=None):
        debit = credit = 0.0

        if voucher.type == 'NC':
            credit = voucher.amount
        else :
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
                'date': voucher.date,
                'date_maturity': voucher.date_due
            }
        if voucher.journal_id.type == 'edc' :
            move_line['partner_id'] = voucher.journal_id.partner_id.id   

        return move_line
        
    def account_move_get(self, cr, uid, voucher_id, context=None):
        seq_obj = self.pool.get('ir.sequence')
        voucher = self.pool.get('wtc.dn.nc').browse(cr,uid,voucher_id,context)
        if voucher.number:
            name = voucher.number
        elif voucher.journal_id.sequence_id:
            if not voucher.journal_id.sequence_id.active:
                raise osv.except_osv('Configuration Error !',
                    'Please activate the sequence of selected journal !')
            c = dict(context)
            c.update({'fiscalyear_id': voucher.period_id.fiscalyear_id.id})
            name = seq_obj.next_by_id(cr, uid, voucher.journal_id.sequence_id.id, context=c)
        else:
            raise osv.except_osv('Error!',
                        'Please define a sequence on the journal.')
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
                             
        for line in voucher.line_ids:
            if not line.amount : #and not (line.move_line_id and not float_compare(line.move_line_id.debit, line.move_line_id.credit, precision_digits=prec) and not float_compare(line.move_line_id.debit, 0.0, precision_digits=prec)):
                continue
            amount = line.amount
            default_name = line.name
            default_account_id = line.account_id.id
            if line.type_detail_id:
                default_name = str(line.type_detail_id.name)
                default_account_id = line.type_detail_id.account_id.id
                if line.note:
                    default_name += ' '
                    default_name += line.note

            move_line = {
                'branch_id' : line.branch_id.id,
                'division' : voucher.division,
                'journal_id': voucher.journal_id.id,
                'period_id': voucher.period_id.id,
                'name': default_name or '/',
                'account_id': default_account_id,
                'move_id': move_id,
                'partner_id': voucher.partner_id.id,
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

            move_line.update({
                'account_tax_id': line.tax_id[0].id if line.tax_id else False,
            })

            if move_line.get('account_tax_id', False):
                tax_data = tax_obj.browse(cr, uid, [move_line['account_tax_id']], context=context)[0]
                if not (tax_data.base_code_id and tax_data.tax_code_id):
                    raise osv.except_osv('No Account Base Code and Account Tax Code!',"You have to configure account base code and account tax code on the '%s' tax!" % (tax_data.name))
            voucher_line = move_line_obj.create(cr, uid, move_line, context=context, check=False)
            rec_ids = [voucher_line]
            
#             if line.move_line_id.id:
#                 rec_lst_ids.append(rec_ids)
        return (tot_line, rec_lst_ids)
                
                       
    def writeoff_move_line_get(self, cr, uid, voucher, line_total, move_id, name, company_currency, current_currency, context=None):
        currency_obj = self.pool.get('res.currency')
        move_line = {}
        current_currency_obj = voucher.currency_id or voucher.journal_id.company_id.currency_id

#         if not currency_obj.is_zero(cr, uid, current_currency_obj, line_total):
#             diff = line_total
#             account_id = False                    
#             if voucher.partner_id:
#                 if voucher.type == 'DN':
#                     account_id = voucher.partner_id.property_account_receivable.id
#                 else:
#                     account_id = voucher.partner_id.property_account_payable.id
#                 move_line = {
#                     'branch_id' : voucher.branch_id.id,
#                     'division' : voucher.division,
#                     'name': name,
#                     'account_id': account_id,
#                     'move_id': move_id,
#                     'partner_id': voucher.partner_id.id,
#                     'date': voucher.date,
#                     'credit': diff > 0 and diff or 0.0,
#                     'debit': diff < 0 and -diff or 0.0,
#                 }
#                 self.pool.get('account.move.line').create(cr, uid, move_line)
#                 print "moveline_writeoff 222",move_line       
        return move_line
                
    def _get_company_currency(self, cr, uid, voucher_id, context=None):
        return self.pool.get('wtc.dn.nc').browse(cr,uid,voucher_id,context).journal_id.company_id.currency_id.id
                 
    def _get_current_currency(self, cr, uid, voucher_id, context=None):
        voucher = self.pool.get('wtc.dn.nc').browse(cr,uid,voucher_id,context)
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
                raise osv.except_osv(('Perhatian !'), ("'Paid Amount' harus diisi untuk pembayaran menggunakan EDC"))
                    
            local_context = dict(context, force_company=voucher.journal_id.company_id.id)
            if voucher.move_id:
                continue
            company_currency = self._get_company_currency(cr, uid, voucher.id, context)
            current_currency = self._get_current_currency(cr, uid, voucher.id, context)
            context = self._sel_context(cr, uid, voucher, context)
            ctx = context.copy()
            ctx.update({'date': voucher.date})
            ctx['novalidate'] = True
            move_id = move_pool.create(cr, uid, self.account_move_get(cr, uid, voucher.id, context=context), context=context)
            name = move_pool.browse(cr, uid, move_id, context=context).name
            
            move_line_id = move_line_pool.create(cr, uid, self.first_move_line_get(cr,uid,voucher, move_id, company_currency, current_currency, local_context), ctx, check=False)
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

            move_line_ids = move_line_pool.search(cr,uid,[
                ('move_id', '=', move_id),
                ('branch_id', '=', False)])

            if move_line_ids :
                move_line_pool.write(cr, uid, move_line_ids, 
                    {'branch_id': voucher.branch_id.id,
                    'division': voucher.division,
                    }, context=ctx)

            if voucher.journal_id.entry_posted:
                move_pool.post(cr, uid, [move_id], context={})
            else :
                move_pool.validate(cr, uid, [move_id], context={})
            reconcile = False
            for rec_ids in rec_list_ids:
                if len(rec_ids) >= 2:
                    reconcile = move_line_pool.reconcile_partial(cr, uid, rec_ids)
            if voucher.type == 'DN' and not voucher.pajak_gabungan and voucher.tax_amount > 0 :
                no_pajak = self.pool.get('wtc.faktur.pajak.out').get_no_faktur_pajak(cr,uid,ids,'wtc.dn.nc',context=context)
        return True
                    
    def branch_id_onchange_other_receivable(self,cr,uid,ids,branch_id,context=None):
        dom={}
        val = {}
        edi_doc_list = ['&', ('active','=',True), ('type','!=','view')]
        dict=self.pool.get('wtc.account.filter').get_domain_account(cr,uid,ids,'other_receivable_header',context=None)
        edi_doc_list.extend(dict)      
        dom['account_id'] = edi_doc_list
        if branch_id :      
            period_id = self.pool['account.period'].find(cr, uid, dt=self._get_default_date(cr, uid, context=context),context=context)           
            branch_search = self.pool.get('wtc.branch').browse(cr,uid,branch_id)
            branch_config = self.pool.get('wtc.branch.config').search(cr,uid,[
                                                                              ('branch_id','=',branch_id)
                                                                              ])
            if not branch_config :
                raise osv.except_osv(('Perhatian !'), ("Belum ada branch config atas branch %s !")%(branch_search.code))
            else :
                branch_config_browse = self.pool.get('wtc.branch.config').browse(cr,uid,branch_config)
                journal_other_receivable =  branch_config_browse.wtc_other_receivable_account_id
                if not journal_other_receivable :
                    raise osv.except_osv(('Perhatian !'), ("Journal Other Receivable belum diisi dalam branch %s !")%(branch_search.code))
                val['journal_id'] = journal_other_receivable.id
                val['company_id'] = journal_other_receivable.company_id.id
                val['currency_id'] = journal_other_receivable.company_id.currency_id.id
            val['period_id']  = period_id and period_id[0]  
                  
        return {'domain':dom,'value': val} 
                        
    def validate_or_rfa(self,cr,uid,ids,context=None):
        obj_av = self.browse(cr, uid, ids, context=context)
        if obj_av.type == 'NC' :
            self.request_approval(cr, uid, ids, context)
        elif obj_av.type == 'DN':
            self.request_approval(cr, uid, ids, context)
        else :
            self.proforma_voucher(cr, uid, ids, context)
        return True
    
    def request_approval(self, cr, uid, ids,context=None):
        obj_av = self.browse(cr, uid, ids, context=context)
        obj_matrix = self.pool.get("wtc.approval.matrixbiaya")
        total = 0.0
        for x in obj_av.line_ids :
            if x.type == 'dr':
                total += x.amount
        type = obj_av.type
        
        if type == 'NC' :
            if not obj_av.line_dr_ids and not obj_av.line_dr_rutin_ids:
                raise Warning("Bill Information tidak boleh kosong !")
            type = 'purchase'
            view_name = 'account.voucher.receipt.form'
        elif type == 'DN' :
            if not obj_av.line_cr_ids:
                raise Warning("Sales Information tidak boleh kosong !")
            type = 'sale'
            view_name = 'wtc.dn.nc.sale.form'
            total = 0.0
            for x in obj_av.line_dr_ids :
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
    
    # New Deveploment
    @api.onchange('jenis_transaksi_id')
    def onchange_line(self):
        self.line_dr_rutin_ids = False
        self.line_dr_ids = False
        if self.jenis_transaksi_id:
            if not self.jenis_transaksi_id.payment_request_type_ids:
                raise Warning('Transaksi Detail  %s belum ada di master !'%self.jenis_transaksi_id.name)

    @api.one
    @api.depends('branch_id','jenis_transaksi_id','create_date')
    def compute_history_rutin(self):
        if self.branch_id and self.jenis_transaksi_id and self.create_date:
            obj = self.search([
                ('branch_id','=',self.branch_id.id),
                ('jenis_transaksi_id','=',self.jenis_transaksi_id.id),
                ('create_date','<',self.create_date)])
            self.jml_history = len(obj)

    @api.multi
    def action_view_history(self):
        self.ensure_one()
        tree_id = self.env.ref('wtc_dn_nc.wtc_payment_request_tree_view2').id
        form_id = self.env.ref('wtc_dn_nc.wtc_payment_request_form_view2').id
        domain = [
            ('id','!=',self.id),
            ('branch_id','=',self.branch_id.id),
            ('jenis_transaksi_id','=',self.jenis_transaksi_id.id),
            ('create_date','<',self.create_date)]
        
        return {
            'name': ('History Pembayaran'),
            'res_model': 'wtc.dn.nc',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'views': [(tree_id, 'tree'),(form_id,'form')],
            'view_type': 'form',
            'view_mode': 'tree,form',
            'domain':domain
        }

    @api.multi
    def action_print_payment_request(self):
        active_ids = self.env.context.get('active_ids', [])
        user = self.env['res.users'].suspend_security().browse(self._uid).name
        datas = {
             'ids': active_ids,
             'model': 'wtc.dn.nc',
             'form': self.read()[0],
             'user': user
        }
        return self.env['report'].suspend_security().get_action(self, 'wtc_dn_nc.teds_payment_request', data=datas)

class wtc_dn_nc_line(models.Model):
    _name = 'wtc.dn.nc.line'
    _description = 'Debit and Credit Note Line Custom'
            
    @api.one
    @api.depends('currency_id')            
    def _get_currency_id(self):
        res = {}
        currency_id =  self.voucher_id.currency_id and self.voucher_id.currency_id.id or self.voucher_id.company_id.currency_id.id
        return currency_id
    
    @api.one
    @api.depends('amount','tax_id')
    def _amount_line(self):
        taxes = 0.0
        amount_subtotal = 0.0
        if self.tax_id :
            for detail in self.tax_id :
                tax = detail.compute_all(self.amount,1)
                for x in tax['taxes'] :
                    taxes += x['amount']
                amount_subtotal += tax['total'] if tax else 0.0
            self.amount_subtotal = amount_subtotal
            self.tax_amount = taxes
        else :
            self.amount_subtotal = self.amount
            
    voucher_id = fields.Many2one('wtc.dn.nc', 'Voucher', required=1, ondelete='cascade')
    name = fields.Char('Description',)
    account_id = fields.Many2one('account.account','Account', required=True)
    partner_id = fields.Many2one(related='voucher_id.partner_id', string='Partner', store=True)
    untax_amount = fields.Float('Untax Amount')
    amount = fields.Float('Amount', digits_compute=dp.get_precision('Account'))
    type = fields.Selection([('dr','Debit'),('cr','Credit'),('wo','Writeoff')], 'Dr/Cr/Wo')
    company_id = fields.Many2one(related='voucher_id.company_id', relation='res.company',string='Company', store=True, readonly=True)
    kwitansi = fields.Boolean(related='voucher_id.kwitansi',string='Yg Sudah Print Kwitansi')
    branch_id = fields.Many2one('wtc.branch',string='Branch')        
    currency_id = fields.Many2one('res.currency', string='Currency',readonly=True,store=True, compute='_get_currency_id')
    tax_id = fields.Many2many('account.tax','dn_nc_tax', 'dn_cn_id', 'tax_id', 'Taxes')         
    amount_subtotal = fields.Float(compute='_amount_line', string='Subtotal', digits_compute= dp.get_precision('Account'),store=True)
    tax_amount = fields.Float(compute='_amount_line',string='Tax Amount', digits_compute= dp.get_precision('Account'),store=True)
    
    # New
    type_detail_id = fields.Many2one('teds.payments.request.type.line','Transaksi Detail')
    account_show_id = fields.Many2one('account.account','Account',compute='compute_account_show')
    name_show = fields.Char('Description',compute="compute_name_show")
    note = fields.Char('Note')
    is_rutin = fields.Boolean('Rutin ?')

    def name_payment_request_onchange(self,cr,uid,ids,account_id,branch_id,division,context=None):
        if not branch_id or not division:
            raise except_orm('No Branch Defined!', 'Sebelum menambah detil transaksi,\n harap isi branch dan division terlebih dahulu.')
        dom={}
        edi_doc_list = ['&', ('active','=',True), ('type','!=','view')]
        dict=self.pool.get('wtc.account.filter').get_domain_account(cr,uid,ids,'payments_request',context=None)
        edi_doc_list.extend(dict)      
        dom['account_id'] = edi_doc_list
        dom['tax_id'] = [('type_tax_use','in',('purchase','all'))]
        return {'domain':dom}
                   
    def name_other_receivable_onchange(self,cr,uid,ids,account_id,branch_id,division,context=None):
        if not branch_id or not division:
            raise except_orm('No Branch Defined!','Sebelum menambah detil transaksi,\n harap isi branch dan division terlebih dahulu.')
        dom2={}
        edi_doc_list2 = ['&', ('active','=',True), ('type','!=','view')]
        dict=self.pool.get('wtc.account.filter').get_domain_account(cr,uid,ids,'other_receivable_detail',context=context)
        edi_doc_list2.extend(dict)      
        dom2['tax_id'] = [('type_tax_use','in',('sale','all'))]
        dom2['account_id'] = edi_doc_list2

        return {'domain':dom2} 

    # New
    @api.one
    @api.depends('account_id')
    def compute_account_show(self):
        if self.account_id:
            self.account_show_id = self.account_id.id
    
    @api.one
    @api.depends('name')
    def compute_name_show(self):
        if self.name:
            self.name_show = self.name

    @api.onchange('type_detail_id')
    def onchange_account(self):
        self.account_id = False
        self.account_show_id = False
        if self.type_detail_id:
            self.account_id = self.type_detail_id.account_id.id
            self.account_show_id = self.type_detail_id.account_id.id


    @api.onchange('type_detail_id','note')
    def onchange_name(self):
        if not self.voucher_id.branch_id and not self.voucher_id.division:
            raise Warning('No Branch Defined! \n', 'Sebelum menambah detil transaksi,\n harap isi branch dan division terlebih dahulu.')
        self.name = False
        if self.type_detail_id:
            name = str(self.type_detail_id.name)
            if self.note:
                self.note = self.note.upper()
                name += ' '
                name += self.note
            self.name = name.upper()
                        
class wtc_register_kwitansi(models.Model):
    _inherit = 'wtc.register.kwitansi.line'
    
    dn_nc_id = fields.Many2one('wtc.dn.nc',string= 'Payment No.')
    
