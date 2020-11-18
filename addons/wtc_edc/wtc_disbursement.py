import time
from datetime import datetime
from openerp import models, fields, api
from openerp.osv import osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

class wtc_disbursement(models.Model):
    _name = "wtc.disbursement"
    _description = "Disbursement EDC"
    
    @api.one
    @api.depends('disbursement_line.debit','amount')
    def _compute_amount(self):
        debit_amount = 0.00
        for x in self.disbursement_line :
            debit_amount += x.debit
        
        self.diff_amount = self.amount - debit_amount 

    @api.cr_uid_ids_context
    @api.depends('period_id')
    def _get_period(self, cr, uid, ids,context=None):
        if context is None: context = {}
        if context.get('period_id', False):
            return context.get('period_id')
        periods = self.pool.get('account.period').find(cr, uid, dt=self._get_default_date(cr,uid,ids,context=None).date(),context=context)
        return periods and periods[0] or False

    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
    
    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('posted','Posted'),
        ('cancel','Cancelled')
    ]
   
    @api.multi
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date()
        
    name = fields.Char(string="Name",readonly=True,default='')
    branch_id = fields.Many2one('wtc.branch', string='Branch', required=True, default=_get_default_branch)
    division = fields.Selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum'),('Finance','Finance')], string='Division',default='Unit', required=True,change_default=True, select=True)
    journal_id = fields.Many2one('account.journal',string="Payment Method",domain="[('branch_id','=',branch_id),('type','in',['cash','bank'])]")
    edc_journal_id = fields.Many2one('account.journal',string="EDC",domain="[('type','=','edc'),('branch_id','=',branch_id)]")    
    move_id = fields.Many2one('account.move', string='Account Entry', copy=False)
    move_ids = fields.One2many('account.move.line',related='move_id.line_id',string='Journal Items', readonly=True)    
    disbursement_line = fields.One2many('wtc.disbursement.line','disbursement_id')
    amount = fields.Float(string="Paid Amount")
    diff_amount = fields.Float(string='Difference Amount',digits=dp.get_precision('Account'), store=True, readonly=True, compute='_compute_amount',)
    state= fields.Selection(STATE_SELECTION, string='State', readonly=True,default='draft')
    date = fields.Date(string="Date",required=True,readonly=True,default=_get_default_date)
    description = fields.Text(string="Note")
    period_id = fields.Many2one('account.period',string="Period",required=True, readonly=True,default=_get_period)
    confirm_uid = fields.Many2one('res.users',string="Posted by")
    confirm_date = fields.Datetime('Posted on')
    cancel_uid = fields.Many2one('res.users',string="Cancelled by")
    cancel_date = fields.Datetime('Cancelled on')
    memo = fields.Char(string="Memo")
                    
    @api.model
    def create(self,vals,context=None):
        if vals['amount'] <= 0 :
            raise osv.except_osv(('Perhatian !'), ("Paid Amount tidak boleh kurang dari Rp.1 "))
        if not vals['disbursement_line'] :
            raise osv.except_osv(('Perhatian !'), ("Detail belum diisi. Data tidak bisa di save."))
#         move_pop = []   
#         for x in vals['disbursement_line']:
#             move_pop.append(x.pop(2))      
              
        vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'EDC')                               
        vals['date'] = self._get_default_date()
#         del[vals['disbursement_line']]     
        
        disbursement_id = super(wtc_disbursement, self).create(vals)
#         if disbursement_id :         
#             for x in move_pop :
#                 disbursement = self.env['wtc.disbursement.line']
#                 disbursement.create({
#                                      'name':x['name'],                               
#                                      'move_line_id':x['move_line_id'],
#                                      'partner_id':x['partner_id'],
#                                      'debit':x['debit'],
#                                      'ref':x['ref'],
#                                      'account_id':x['account_id'],
#                                      'disbursement_id':disbursement_id.id
#                                                     })   
#                             
#         else :
#             return False           
        return disbursement_id
    
#     @api.onchange('edc_journal_id')
#     def onchange_reimbursement(self):          
#         if self.edc_journal_id :
#             move_line = self.env['account.move.line']
#             move_line_search = move_line.search([
#                                         ('journal_id','=',self.edc_journal_id.id),
#                                         ('reconcile_id','=',False),
#                                         ('debit','>',0),
#                                         ('partner_id','=',self.edc_journal_id.partner_id.id)
#                                         ])
#             move = []
#             if not move_line_search :
#                 raise osv.except_osv(('Perhatian !'), ("Transaksi menggunakan EDC %s tidak ditemukan!")%(self.edc_journal_id.name))
#                 move = []
#             elif move_line_search :
#                 for x in move_line_search :
#                     move.append([0,0,{
#                                      'name':x.name,                               
#                                      'move_line_id':x.id,
#                                      'partner_id':x.partner_id.id,
#                                      'debit':x.debit,
#                                      'ref':x.ref,
#                                      'account_id':x.account_id
#                     }])   
#             self.disbursement_line = move

    @api.one
    def post_disbursement(self):
        self.write({'date':self._get_default_date(),'state':'posted','confirm_uid':self._uid,'confirm_date':datetime.now()})        
        self.action_move_line_create()
        return True 

    @api.one
    def cancel_disbursement(self):
        self.write({'state':'cancel','cancel_uid':self._uid,'cancel_date':datetime.now()})
        return True  
    
    @api.cr_uid_ids_context
    def action_move_line_create(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        periods = self.pool.get('account.period').find(cr, uid, dt=self._get_default_date(cr,uid,ids,context=context).date(),context=context)
        move_line_rec = [] 
        disbursement = self.browse(cr, uid, ids, context=context)
        disbursement.write({'period_id':periods and periods[0]})
        
        name = disbursement.name
        date = disbursement.date
        journal_id = disbursement.journal_id.id
        journal_edc_id = disbursement.edc_journal_id.id
        debit_account_id = disbursement.journal_id.default_debit_account_id.id
        if not debit_account_id:
            raise osv.except_osv(('Perhatian !'), ("Account belum diisi dalam journal %s!")%(disbursement.journal_id.name))
        amount = disbursement.amount          
        period_id = disbursement.period_id.id
        diff_amount = disbursement.diff_amount

        config = self.pool.get('wtc.branch.config').search(cr,uid,[('branch_id','=',disbursement.branch_id.id)])
        if config :
            config_browse = self.pool.get('wtc.branch.config').browse(cr,uid,config)
            pl_account = config_browse.disburesement_pl_account_id.id
            if not pl_account :
                raise osv.except_osv(('Perhatian !'), ("Account Disbursement EDC belum diisi dalam setting branch !"))
                
        elif not config :
            raise osv.except_osv(('Perhatian !'), ("Account Disbursement EDC belum diisi dalam setting branch !"))
                     
        move = {
            'name': name,
            'journal_id': journal_id,
            'date': date,
            'ref':name,
            'period_id':period_id,
        }
        move_id = move_pool.create(cr, uid, move, context=None)
        move_line1 = {
            'name': _('%s')%(disbursement.journal_id.name),
            'ref':name,
            'account_id': debit_account_id,
            'move_id': move_id,
            'journal_id': journal_id,
            'period_id': period_id,
            'date': date,
            'debit': amount,
            'credit': 0.0,
            'partner_id':disbursement.edc_journal_id.partner_id.id,
            'branch_id': disbursement.branch_id.id,
            'division': disbursement.division,
        }   
        line_id = move_line_pool.create(cr, uid, move_line1, context)
        if diff_amount < 0 :
            diff_amount = abs(diff_amount)
            move_line = {
                'name': _('Shortage Pencairan'),
                'ref':name,
                'account_id': pl_account,
                'move_id': move_id,
                'journal_id': journal_id,
                'period_id': period_id,
                'date': date,
                'debit': diff_amount,
                'credit': 0.0,
                'partner_id':disbursement.edc_journal_id.partner_id.id,
                'branch_id': disbursement.branch_id.id,
                'division': disbursement.division,
            }    
            line_id = move_line_pool.create(cr, uid, move_line, context) 
            
        elif diff_amount > 0 :
            move_line4 = {
                'name': _('Excess Disbursement'),
                'ref':name,
                'account_id': pl_account,
                'move_id': move_id,
                'journal_id': journal_id,
                'period_id': period_id,
                'date': date,
                'debit': 0.0,
                'credit': diff_amount,
                'partner_id':disbursement.edc_journal_id.partner_id.id,
                'branch_id': disbursement.branch_id.id,
                'division': disbursement.division,
            }    
            line_id4 = move_line_pool.create(cr, uid, move_line4, context)  
            
        reconcile_by_account = {}                                      
        for y in disbursement.disbursement_line :
            move_line_rec = []
            move_line_2 = {
                'name': _('Disbursement %s')%(y.ref),
                'ref':name,
                'account_id': y.account_id.id,
                'move_id': move_id,
                'journal_id': journal_id,
                'period_id': period_id,
                'date': date,
                'debit': 0.0,
                'credit': y.debit,
                'partner_id':y.partner_id.id,
                'branch_id': disbursement.branch_id.id,
                'division': disbursement.division,
            }     
                   
            line_id2 = move_line_pool.create(cr, uid, move_line_2, context)
            curr_move_line = []
            if reconcile_by_account.get(y.account_id.id,0) != 0 :
                curr_move_line = reconcile_by_account[y.account_id.id]
            curr_move_line.append(line_id2)
            curr_move_line.append(y.move_line_id.id)    
            reconcile_by_account[y.account_id.id] = curr_move_line
            
        for key,value in reconcile_by_account.items() :
            self.pool.get('account.move.line').reconcile(cr, uid,  value)
        if disbursement.journal_id.entry_posted:
            posted = move_pool.post(cr, uid, [move_id], context=None)
        self.write(cr, uid, disbursement.id, {'move_id': move_id})
        return True      

    
    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Reimbursement EDC sudah diproses, data tidak bisa didelete !"))
        return super(wtc_disbursement, self).unlink(cr, uid, ids, context=context)     
                
class wtc_disbursement_line(models.Model):
    _name = 'wtc.disbursement.line'

    name = fields.Char(string="Name",readonly=True,default='')
    disbursement_id = fields.Many2one('wtc.disbursement')
    move_line_id = fields.Many2one('account.move.line')
    partner_id = fields.Many2one('res.partner',string="Partner")
    debit = fields.Float(string="Amount")
    ref = fields.Char(string="Reference")
    account_id = fields.Many2one('account.account',string="Account")
                   
    _sql_constraints = [
    ('unique_name_move_line_id', 'unique(disbursement_id,move_line_id)', 'Tidak boleh ada detail yang sama  !'),
] 
                         
    @api.onchange('move_line_id')
    def onchange_move_line(self):
        dom = {}        
        dom['move_line_id'] = '[("debit",">",0),("journal_id","=",'+str(self.disbursement_id.edc_journal_id.id)+'),("partner_id","=",'+str(self.disbursement_id.edc_journal_id.partner_id.id)+'),("reconcile_id","=",False)]'
         
        if self.move_line_id :
            self.partner_id = self.move_line_id.partner_id.id
            self.account_id = self.move_line_id.account_id.id            
            self.debit = self.move_line_id.debit
            self.ref = self.move_line_id.ref
        return {'domain':dom} 

            
#                                         ('journal_id','=',self.edc_journal_id.id),
#                                         ('reconcile_id','=',False),
#                                         ('debit','>',0),
#                                         ('partner_id','=',self.edc_journal_id.partner_id.id)            