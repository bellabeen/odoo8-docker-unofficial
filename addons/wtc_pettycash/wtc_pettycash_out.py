import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.osv import orm

class wtc_pettycash(models.Model):
    _name = "wtc.pettycash"
    _description ="Petty Cash"
    _order = "date desc"
    
    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('waiting_for_approval','Waiting Approval'),
        ('confirmed', 'Waiting Approval'),
        ('approved', 'Approved'),
        ('posted', 'Posted'),
        ('reimbursed', 'Reimbursed'),
        ('cancel', 'Cancelled'),
    ]   
    
    @api.cr_uid_ids_context
    @api.depends('period_id')
    def _get_period(self, cr, uid, ids,context=None):
        if context is None: context = {}
        if context.get('period_id', False):
            return context.get('period_id')
        periods = self.pool.get('account.period').find(cr, uid, dt=self._get_default_date(cr,uid,ids,context=context).date(),context=context)
        return periods and periods[0] or False

    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 

    @api.one
    @api.depends('line_ids.amount_real')
    def _compute_amount(self):
        self.amount_real = sum(line.amount_real for line in self.line_ids)
             
    @api.multi
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date()
    
    @api.multi
    def _check_amount_real(self):
        if round(self.amount_real)<0:
            return False
        return True
                        
    name = fields.Char(string="Name",readonly=True,default='')
    branch_id = fields.Many2one('wtc.branch', string='Branch', required=True, default=_get_default_branch)
    user_id = fields.Many2one('res.users', string='Responsible')
    division = fields.Selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum'),('Finance','Finance')], string='Division',default='Unit', change_default=True, select=True)
    amount = fields.Float('Paid Amount')
    branch_destination_id =  fields.Many2one('wtc.branch', string='Branch Destination', required=True)
    journal_id = fields.Many2one('account.journal',string="Payment Method",domain="[('branch_id','=',branch_id),('type','=','pettycash')]")
    line_ids = fields.One2many('wtc.pettycash.line','pettycash_id',string="PettyCash Line")
    state= fields.Selection(STATE_SELECTION, string='State', readonly=True,default='draft')
    date = fields.Date(string="Date",required=True,readonly=True,default=_get_default_date)
    move_id = fields.Many2one('account.move', string='Account Entry', copy=False)
    move_ids = fields.One2many('account.move.line',related='move_id.line_id',string='Journal Items', readonly=True)    
    period_id = fields.Many2one('account.period',string="Period",required=True, readonly=True,default=_get_period)
#     company_id = fields.Many2one(related='journal_id.company_id',string='Company',store=True, readonly=True),
    account_id = fields.Many2one('account.account',string="Account")
    reimbursed_id = fields.Many2one('wtc.reimbursed')  
    confirm_uid = fields.Many2one('res.users',string="Posted by")
    confirm_date = fields.Datetime('Posted on')
    amount_real = fields.Float(string='Amount Real',digits=dp.get_precision('Account'), store=True, readonly=True, compute='_compute_amount',) 
    
    _constraints = [
        (_check_amount_real, 'Nilai Pettycash IN melebihi Pettycash OUT', ['amount_real']),
    ]
         
    @api.multi
    def get_equal_amount(self,amount,pettycash):
        total_amount = 0.0
        for x in pettycash :
            total_amount += x['amount']
        if total_amount != amount :
            raise osv.except_osv(('Perhatian !'), ("Total Amount tidak sesuai, mohon cek kembali data Anda."))
        return True
        
            
    @api.model
    def create(self,vals,context=None):
        if not vals['line_ids'] :
            raise osv.except_osv(('Perhatian !'), ("Detail belum diisi. Data tidak bisa di save."))
        pettycash = []
        for x in vals['line_ids']:
            pettycash.append(x.pop(2))        
        vals['date'] = self._get_default_date()
        
        if vals['journal_id'] :
            journal_obj = self.env['account.journal'].search([('id','=',vals['journal_id'])])
            vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'PCO')  
                 
        del[vals['line_ids']]
        equal_amount = self.get_equal_amount(vals['amount'],pettycash)
        
        pettycash_id = super(wtc_pettycash, self).create(vals)
        if pettycash_id :
            rekap = []
            for x in pettycash :
                if x['account_id'] not in rekap :
                    rekap.append(x['account_id'])
                elif x['account_id'] in rekap :
                    raise osv.except_osv(('Perhatian !'), ("Tidak boleh ada Account yang sama dalam detail transaksi"))
                     
                pettycash_pool = self.env['wtc.pettycash.line']
                pettycash_pool.create({
                    'pettycash_id':pettycash_id.id,
                    'type_id':x['type_id'],
                    'type_detail_id':x['type_detail_id'],
                    'note':x['note'],
                    'name':x['name'],
                    'account_id':x['account_id'],
                    'amount':x['amount']
                })  
                            
        else :
            return False    
        return pettycash_id
    
    @api.multi
    def write(self,vals,context=None):
        vals.get('line_ids',[]).sort(reverse=True)        
        line = vals.get('line_ids',False)
        if line:
            for x,item in enumerate(line) :
                petty_id = item[1]
                if item[0] == 1 or item[0] == 0:
                    value = item[2]
                    if value.get('account_id') :
                        for y in self.line_ids :
                            if y.account_id.id == value['account_id'] :
                                raise osv.except_osv(('Perhatian !'), ("Tidak boleh ada Account yang sama dalam detail transaksi"))
        res = super(wtc_pettycash,self).write(vals)
        self.get_equal_amount(self.amount,self.line_ids)            
        
        return res
        
    @api.onchange('branch_id')
    def onchange_branch(self):
        self.branch_destination_id = self.branch_id
            
    @api.multi
    def post_pettycash(self):
        #check saldo pettycash
        if (self.journal_id.default_credit_account_id.balance-self.amount)<0:
            raise osv.except_osv(('Perhatian !'), ("Saldo kas pettycash tidak mencukupi!"))
        periods = self.env['account.period'].find(dt=self._get_default_date())
        self.write({'period_id':periods.id,'date':self._get_default_date(),'state': 'posted', 'confirm_uid':self._uid,'confirm_date':datetime.now()})
        self.action_move_line_create()
        self.set_amount_real()
        return True
    
    @api.multi
    def set_amount_real(self):
        for x in self.line_ids :
            x.amount_real = x.amount
                    
    @api.multi
    def reimbursed_pettycash(self):
        self.state = 'reimbursed'
    
    @api.multi
    def cancel_pettycash(self):
        self.state = 'cancel'
     
    @api.cr_uid_ids_context
    def action_move_line_create(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        for pettycash in self.browse(cr, uid, ids, context=context):
            name = pettycash.name
            date = pettycash.date
            journal_id = pettycash.journal_id.id
            account_id = pettycash.journal_id.default_credit_account_id.id or pettycash.journal_id.default_debit_account_id.id
            amount = pettycash.amount          
            period_id = pettycash.period_id.id
            
            move = {
                'name': name,
                'journal_id': journal_id,
                'ref':name,
                'date': date,
                'period_id':period_id,
            }
            move_id = move_pool.create(cr, uid, move, context=None)
            move_line1 = {
                'name': _('Petty Cash'),
                'ref':name,
                'account_id': account_id,
                'move_id': move_id,
                'journal_id': journal_id,
                'period_id': period_id,
                'date': date,
                'debit': 0.0,
                'credit': pettycash.amount,
                'branch_id' : pettycash.branch_id.id,
                'division' : pettycash.division                
            }           
            line_id = move_line_pool.create(cr, uid, move_line1, context)            
            for y in pettycash.line_ids :
                default_name = y.name
                default_account_id = y.account_id.id

                if y.type_detail_id:
                    default_name = str(y.type_detail_id.name)
                    default_account_id = y.type_detail_id.account_id.id
                    if y.note:
                        default_name += ' '
                        default_name += y.note
                move_line_2 = {
                    'name': default_name,
                    'ref':name,
                    'account_id': default_account_id,
                    'move_id': move_id,
                    'journal_id': journal_id,
                    'period_id': period_id,
                    'date': date,
                    'debit': y.amount,
                    'credit': 0.0,
                    'branch_id' : pettycash.branch_destination_id.id,
                    'division' : pettycash.division                    
                }           
                line_id2 = move_line_pool.create(cr, uid, move_line_2, context)
                
            self.create_intercompany_lines(cr,uid,ids,move_id,context=None)      
            if  pettycash.journal_id.entry_posted :    
                posted = move_pool.post(cr, uid, [move_id], context=None)
            self.write(cr, uid, pettycash.id, {'move_id': move_id,'account_id':account_id})
        return True 

    @api.cr_uid_ids_context   
    def create_intercompany_lines(self,cr,uid,ids,move_id,context=None):
        ##############################################################
        ################# Add Inter Company Journal ##################
        ##############################################################
        
        
        branch_rekap = {}       
        branch_pool = self.pool.get('wtc.branch')        
        vals = self.browse(cr,uid,ids) 
        move_line = self.pool.get('account.move.line')
        move_line_srch = move_line.search(cr,uid,[('move_id','=',move_id)])
        move_line_brw = move_line.browse(cr,uid,move_line_srch)
        
        branch = branch_pool.search(cr,uid,[('id','=',vals.branch_id.id)])

        if branch :
            branch_browse = branch_pool.browse(cr,uid,branch)
            inter_branch_header_account_id = branch_browse.inter_company_account_id.id
            if not inter_branch_header_account_id :
                raise osv.except_osv(('Perhatian !'), ("Account Inter Company belum diisi dalam Master branch %s !")%(vals.branch_id.name))
        
        #Merge Credit and Debit by Branch                                
        for x in move_line_brw :
            if x.branch_id not in branch_rekap :
                branch_rekap[x.branch_id] = {}
                branch_rekap[x.branch_id]['debit'] = x.debit
                branch_rekap[x.branch_id]['credit'] = x.credit
            else :
                branch_rekap[x.branch_id]['debit'] += x.debit
                branch_rekap[x.branch_id]['credit'] += x.credit  
        
        #Make account move       
        for key,value in branch_rekap.items() :
            if key != vals.branch_id :
                config = branch_pool.search(cr,uid,[('id','=',key.id)])
        
                if config :
                    config_browse = branch_pool.browse(cr,uid,config)
                    inter_branch_detail_account_id = config_browse.inter_company_account_id.id                
                    if not inter_branch_detail_account_id :
                        raise osv.except_osv(('Perhatian !'), ("Account Inter belum diisi dalam Master branch %s - %s!")%(key.code, key.name))

                balance = value['debit']-value['credit']
                debit = abs(balance) if balance < 0 else 0
                credit = balance if balance > 0 else 0
                
                if balance != 0:
                    move_line_create = {
                        'name': _('Interco Petty Cash Out %s')%(key.name),
                        'ref':_('Interco Petty Cash Out %s')%(key.name),
                        'account_id': inter_branch_header_account_id,
                        'move_id': move_id,
                        'journal_id': vals.journal_id.id,
                        'period_id': vals.period_id.id,
                        'date': vals.date,
                        'debit': debit,
                        'credit': credit,
                        'branch_id' : key.id,
                        'division' : vals.division                    
                    }    
                    inter_first_move = move_line.create(cr, uid, move_line_create, context)    
                             
                    move_line2_create = {
                        'name': _('Interco Petty Cash Out %s')%(vals.branch_id.name),
                        'ref':_('Interco Petty Cash Out %s')%(vals.branch_id.name),
                        'account_id': inter_branch_detail_account_id,
                        'move_id': move_id,
                        'journal_id': vals.journal_id.id,
                        'period_id': vals.period_id.id,
                        'date': vals.date,
                        'debit': credit,
                        'credit': debit,
                        'branch_id' : vals.branch_id.id,
                        'division' : vals.division                    
                    }    
                    inter_second_move = move_line.create(cr, uid, move_line2_create, context)       
        return True
        
    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Petty Cash sudah diproses, data tidak bisa didelete !"))
        return super(wtc_pettycash, self).unlink(cr, uid, ids, context=context) 

    @api.onchange('amount')
    def amount_change(self):    
        warning = {}     
        if self.amount < 0 :
            self.amount = 0 
            warning = {
                'title': ('Perhatian !'),
                'message': (("Nilai amount tidak boleh kurang dari 0")),
            }                      
        return {'warning':warning}
                      
class wtc_pettycash_line(models.Model): 
    _name = "wtc.pettycash.line"
    _description = "Petty Cash Line"
             
    pettycash_id = fields.Many2one('wtc.pettycash',string="Petty Cash")
    name = fields.Char(string="Description", required = True)
    account_id = fields.Many2one('account.account',string="Account",domain="[('type','!=','view')]")
    amount = fields.Float(string="Amount")
    amount_real = fields.Float(string="Amount Real")

    # New Deplopment
    type_id = fields.Many2one('wtc.payments.request.type','Tipe Transaksi',domain="[('type','=','PCO')]")
    type_detail_id = fields.Many2one('teds.payments.request.type.line','Transaksi Detail',domain="[('type_id','=',type_id)]")
    account_show_id = fields.Many2one('account.account','Account',compute='compute_account_show')
    note = fields.Char('Note')
    name_show = fields.Char('Description',compute="compute_name_show")

    _sql_constraints = [
    ('unique_name_pettycash_id', 'unique(account_id,pettycash_id)', 'Detail account duplicate, mohon cek kembali !'),
] 
           
    @api.onchange('name')
    def name_change(self):
        dom = {}
        if not self.pettycash_id.branch_id or not self.pettycash_id.division or not self.pettycash_id.branch_destination_id:
            raise osv.except_osv(('Perhatian!'), ('Sebelum menambah detil transaksi,\n harap isi data header terlebih dahulu.'))
                
        edi_doc_list = ['&', ('active','=',True), ('type','!=','view')] 
   
        filter = self.env['wtc.account.filter']         
        dict = filter.get_domain_account("pettycash")
        edi_doc_list.extend(dict)
        dom['account_id']=edi_doc_list
             
        return {'domain':dom}

    @api.onchange('amount')
    def amount_change(self):    
        warning = {}     
        if self.amount < 0 :
            self.amount = 0 
            warning = {
                'title': ('Perhatian !'),
                'message': (("Nilai amount tidak boleh kurang dari 0")),
            }                      
        return {'warning':warning} 

    # New Deplopment
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

    @api.onchange('type_id')
    def onchange_type_detail(self):
        self.type_detail_id = False
    
    @api.onchange('type_detail_id')
    def onchange_type(self):
        self.account_id = False
        self.account_show_id = False
        if self.type_detail_id:
            self.account_id = self.type_detail_id.account_id.id
            self.account_show_id = self.type_detail_id.account_id.id

    @api.onchange('type_detail_id','note')
    def onchange_name(self):
        self.name = False
        if self.type_detail_id:
            name = str(self.type_detail_id.name)
            if self.note:
                self.note = self.note.upper()
                name += ' '
                name += self.note
            self.name = name.upper()

class AccountFilter(orm.Model):
    _inherit = "wtc.account.filter"

    def _register_hook(self, cr):
        selection = self._columns['name'].selection
        if ('pettycash','Petty Cash') not in selection:         
            self._columns['name'].selection.append(
                ('pettycash', 'Petty Cash'))
        return super(AccountFilter, self)._register_hook(cr)    
    

class wtc_pc_journal_type(orm.Model):
    _inherit = "account.journal"
 
    def _register_hook(self, cr):
        selection = self._columns['type'].selection
        if ('pettycash','Petty Cash') not in selection:         
            self._columns['type'].selection.append(
                ('pettycash', 'Petty Cash'))
        return super(wtc_pc_journal_type, self)._register_hook(cr)      
