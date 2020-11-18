import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp import SUPERUSER_ID
from openerp import tools
import pytz

class wtc_bank_transfer(models.Model):
    _name = 'wtc.bank.transfer'
    _description = 'Bank Transfer'
    _order = 'date desc'
       
    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('waiting_for_approval','Waiting For Approval'),
        ('confirmed', 'Waiting Approval'),
        ('app_approve', 'Approved'),
        ('approved','Posted'),
        ('cancel','Cancelled')
    ]
    @api.one
    @api.depends('line_ids.amount','bank_fee')
    def _compute_amount(self):
        self.amount_total = sum(line.amount for line in self.line_ids) + self.bank_fee

    @api.cr_uid_ids_context
    @api.depends('period_id')
    def _get_period(self, cr, uid, ids,context=None):
        if context is None: context = {}
        if context.get('period_id', False):
            return context.get('period_id')
        periods = self.pool.get('account.period').find(cr, uid,dt=self._get_default_date(cr,uid,ids,context=context).date(), context=context)
        return periods and periods[0] or False

    @api.cr_uid_ids_context
    def _check_amount(self, cr, uid, ids, context=None):
      bank = self.browse(cr, uid, ids, context=context)[0]
      if round(bank.amount_total,2) != round(bank.amount,2):           
          return False
      return True
    
    @api.cr_uid_ids_context
    def change_amount(self,cr,uid,ids,bank,context=None):
        value = {}
        if bank :
            journal = self.pool.get('account.journal')
            journal_srch = journal.search(cr,uid,[('id','=',bank)])
            journal_brw = journal.browse(cr,uid,journal_srch)
            if journal_brw.type == 'cash' : 
                value = {
                         'amount_show':journal_brw.default_debit_account_id.balance
                         }
            else :
                value = {
                    'amount_show':False,
                    'reconcile_ids':False,
                }
        return {'value':value}
    
    @api.cr_uid_ids_context
    def change_amount_show(self,cr,uid,ids,amount,context=None):
        value = {}
        if amount :
            value = {
                     'amount':amount
                     }   
        else :
            value = {
                     'amount':False
                     }  
        return {'value':value}    
    
    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
            
    @api.multi
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date()
             
       
    name = fields.Char(string="Name",readonly=True,default='')
    branch_id = fields.Many2one('wtc.branch', string='Branch', required=True, default=_get_default_branch)
    amount = fields.Float('Amount')
    state= fields.Selection(STATE_SELECTION, string='State', readonly=True,default='draft')
    date = fields.Date(string="Date",required=True,readonly=True,default=_get_default_date)
    payment_from_id = fields.Many2one('account.journal',string="Bank",domain="[('branch_id','=',branch_id),'|',('type','=','cash'),('type','=','bank')]")
    description = fields.Char(string="Description")
    move_id = fields.Many2one('account.move', string='Account Entry', copy=False)
    move_ids = fields.One2many('account.move.line',related='move_id.line_id',string='Journal Items', readonly=True)    
    line_ids = fields.One2many('wtc.bank.transfer.line','bank_transfer_id',string="Bank Transfer Line")
    bank_fee = fields.Float(string='Bank Transfer Fee',digits=dp.get_precision('Account'))
    amount_total = fields.Float(string='Total Amount',digits=dp.get_precision('Account'), store=True, readonly=True, compute='_compute_amount',)
    period_id = fields.Many2one('account.period',string="Period",required=True, readonly=True,default=_get_period)
    note = fields.Text(string="Note")
    division = fields.Selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum'),('Finance','Finance')], string='Division',default='Unit', required=True,change_default=True, select=True)
    journal_type = fields.Selection(related='payment_from_id.type',string="Journal Type")
    account_id = fields.Many2one(related='payment_from_id.default_debit_account_id',string='Account')
    amount_show = fields.Float(related='amount',string='Amount')
    confirm_uid = fields.Many2one('res.users',string="Posted by")
    confirm_date = fields.Datetime('Posted on')
    cancel_uid = fields.Many2one('res.users',string="Cancelled by")
    cancel_date = fields.Datetime('Cancelled on')
    reconcile_ids = fields.One2many('wtc.bank.transfer.reconcile.line','bank_transfer_id',string="Reconcile Items")
    reconcile_id = fields.Many2one('wtc.bank.reconcile',string="Bank Reconcile")
    is_payment = fields.Boolean('Klik BCA ?')
    payment_klik_uid = fields.Many2one('res.users','Payment Klik by')
    payment_klik_date = fields.Datetime('Payment Klik on')

    _constraints = [
        (_check_amount, 'Total Amount tidak sesuai, mohon cek kembali data Anda.', ['amount_total','amount']),
    ]  

    @api.cr_uid_ids_context
    def button_dummy(self, cr, uid, ids, context=None):
        return True
        
    @api.model
    def create(self,vals,context=None):
        if not vals['line_ids'] :
            raise osv.except_osv(('Perhatian !'), ("Detail belum diisi. Data tidak bisa di save."))

        journal = self.pool.get('account.journal').browse(self._cr, self._uid, vals['payment_from_id'])
#         if journal.type == 'cash' :
#             if not vals['reconcile_ids'] :
#                 raise osv.except_osv(('Perhatian !'), ("Detail reconcile belum diisi. Data tidak bisa di save."))
#             self._check_double_entries(#self._cr, self._uid, 0,
#                 [x[2]['move_line_id'] for x in vals.get('reconcile_ids',[])])

        vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'BT') 
        vals['date'] = self._get_default_date()

        return super(wtc_bank_transfer, self).create(vals)

#     def write(self, cr, uid, ids, vals, context=None):
#         res = super(wtc_bank_transfer,self).write(cr,uid,ids,vals)
#         if ('payment_from_id' in vals) or ('reconcile_ids' in vals) :
#             values = self.browse(cr, uid, ids)
#             for value in values :
#                 if value.payment_from_id.type == 'cash' :
#                     self._check_double_entries(cr, uid, value.id,
#                         [line.move_line_id.id for line in value.reconcile_ids])
#         return res

    @api.cr_uid_ids
    def _check_double_entries(self, cr, uid, ids, move_line_ids):
        if ids == 0:
            ids = [0]
        elif not ids :
            ids = [0]
        elif isinstance(ids, (int,long)):
            ids = [ids]
        ids = str(tuple(ids)).replace(',)', ')')
        move_line_ids = str(tuple(move_line_ids)).replace(',)',')')
        query = """
            select btr.name, btr.amount_original, bt.name
            from wtc_bank_transfer bt 
            inner join wtc_bank_transfer_reconcile_line btr on bt.id = btr.bank_transfer_id
            where bt.state in ('draft', 'waiting_for_approval', 'confirmed', 'app_approve')
            and (bt.id not in (%s) or %s)
            and btr.move_line_id in %s
        """ % (ids, '1=1' if ids == [0] else '1=0', move_line_ids)
        cr.execute(query)
        data = cr.fetchall()
        if len(data) > 0:
            message = ""
            for x in data :
                message += "Detil %s (%s) sudah ditarik di nomor %s. \r\n" % (x[0], x[1], x[2])
            raise osv.except_osv('Perhatian !', message)
    
    @api.one
    def post_bank(self):
        ada=0
        message=''
        for inv in self.line_ids:
            inv.reimbursement_id
            if inv.reimbursement_id.state!='paid':
                self.write({'date':self._get_default_date(),'state':'approved','confirm_uid':self._uid,'confirm_date':datetime.now()})        
                if self.payment_from_id.type == 'cash' :
                    if round(self.amount,2) > round(self.payment_from_id.default_debit_account_id.balance,2) or round(self.amount_show,2) > round(self.payment_from_id.default_debit_account_id.balance,2) :
                        raise osv.except_osv(('Perhatian !'), ("Saldo kas tidak mencukupi !"))
        #             total_reconcile = sum([(reconcile_line.move_line_id.debit - reconcile_line.move_line_id.credit) for reconcile_line in self.reconcile_ids])
        #             if self.amount != total_reconcile :
        #                 raise osv.except_osv('Perhatian !', 'Detil reconcile item tidak sama (%d)' % total_reconcile)
        
                res = self.action_move_line_create()
                if self.payment_from_id.type == 'cash' :
                    self.payment_from_id.write({'is_pusted':True})
        #         if self.payment_from_id.type == 'cash' :
        #             self.action_reconcile_create(res[self.id])
                return True  
            else:
                message += "Nomor Reimburse %s sudah %s. \r\n" % (inv.reimbursement_id.name,inv.reimbursement_id.state)
                ada +=1
        if ada>0:
            raise osv.except_osv('Perhatian !', message)
        
    @api.one
    def action_reconcile_create(self, line_id):
        reconcile_ids = [line.move_line_id.id for line in self.reconcile_ids]
        reconcile_ids += [line_id]
        r_id = self.pool.get('wtc.bank.reconcile').create(self._cr, self._uid, {
            'type': 'cash',
            'line_ids': map(lambda x: (4, x, False), reconcile_ids),
        })
        self.write({'reconcile_id':r_id})
        return r_id
    
    @api.one
    def cancel_bank(self):
        self.write({'state':'cancel','cancel_uid':self._uid,'cancel_date':datetime.now()})
        return True    

    @api.cr_uid_ids_context
    def action_move_line_create(self, cr, uid, ids, context=None):
        res = {}
        if context is None:
            context = {}
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        periods = self.pool.get('account.period').find(cr, uid, self._get_default_date(cr,uid,ids,context=context).date(),context=context)
        for banktransfer in self.browse(cr, uid, ids, context=context):       
            banktransfer.write({'period_id':periods and periods[0]})
            name = banktransfer.name
            date = banktransfer.date
            journal_id = banktransfer.payment_from_id.id
            credit_account_id = banktransfer.payment_from_id.default_credit_account_id.id
            debit_account_id = banktransfer.payment_from_id.default_debit_account_id.id
            if not credit_account_id or not debit_account_id:
                raise osv.except_osv(('Perhatian !'), ("Account belum diisi dalam journal %s!")%(banktransfer.payment_from_id.name))
            amount = banktransfer.amount          
            period_id = banktransfer.period_id.id  
            
            config = self.pool.get('wtc.branch.config').search(cr,uid,[('branch_id','=',banktransfer.branch_id.id)])
           
            if config :
                config_browse = self.pool.get('wtc.branch.config').browse(cr,uid,config)
                bank_fee_account = config_browse.bank_transfer_fee_account_id.id                    
            elif not config :
                raise osv.except_osv(('Perhatian !'), ("Account Bank Transfer Fee belum diisi dalam setting branch !"))

                                   
            move = {
                'name': name,
                'ref':name,
                'journal_id': journal_id,
                'date': date,
                'period_id':period_id,
            }
            move_id = move_pool.create(cr, uid, move, context=None)
            move_line1 = {
                'name': banktransfer.description,
                'ref':name,
                'account_id': credit_account_id,
                'move_id': move_id,
                'journal_id': journal_id,
                'period_id': period_id,
                'date': date,
                'debit': 0.0,
                'credit': banktransfer.amount,
                'branch_id' : banktransfer.branch_id.id,
                'division' : banktransfer.division
            }           
            line_id = move_line_pool.create(cr, uid, move_line1, context)   
            res[banktransfer.id] = line_id
            if banktransfer.bank_fee > 0 :
                move_line3 = {
                    'name': 'Bank Transfer Fee',
                    'ref':name,
                    'account_id': bank_fee_account,
                    'move_id': move_id,
                    'journal_id': journal_id,
                    'period_id': period_id,
                    'date': date,
                    'debit': banktransfer.bank_fee,
                    'credit': 0.0,
                    'branch_id' : banktransfer.branch_id.id,
                    'division' : banktransfer.division                    
                }    
                line_id3 = move_line_pool.create(cr, uid, move_line3, context)                     
            for y in banktransfer.line_ids :
                branch_destination = self.pool.get('wtc.branch').search(cr,SUPERUSER_ID,[('code','=',y.branch_destination_id)])
                branch_dest = self.pool.get('wtc.branch').browse(cr,SUPERUSER_ID,branch_destination)
                
                move_line_2 = {
                    'name': y.description,
                    'ref':name,
                    'account_id': y.payment_to_id.default_debit_account_id.id,
                    'move_id': move_id,
                    'journal_id': journal_id,
                    'period_id': period_id,
                    'date': date,
                    'debit': y.amount,
                    'credit': 0.0,
                    'branch_id' : branch_dest.id,
                    'division' : banktransfer.division                    
                }           
                line_id2 = move_line_pool.create(cr, uid, move_line_2, context)
                if y.reimbursement_id :
                    y.reimbursement_id.write({'state':'paid'})
            self.create_intercompany_lines(cr,uid,ids,move_id,context=None) 
            if banktransfer.payment_from_id.entry_posted:
                posted = move_pool.post(cr, uid, [move_id], context=None)
            self.write(cr, uid, banktransfer.id, {'state': 'approved', 'move_id': move_id})
        return res
     
    @api.cr_uid_ids_context   
    def create_intercompany_lines(self,cr,uid,ids,move_id,context=None):
        ##############################################################
        ################# Add Inter Company Journal ##################
        ##############################################################
        
        
        branch_rekap = {}       
        branch_pool = self.pool.get('wtc.branch')        
        vals = self.browse(cr,uid,ids) 
        move_line = self.pool.get('account.move.line')
        move_line_srch = move_line.search(cr,SUPERUSER_ID,[('move_id','=',move_id)])
        move_line_brw = move_line.browse(cr,SUPERUSER_ID,move_line_srch)
        
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
                inter_branch_detail_account_id = key.inter_company_account_id.id                
                if not inter_branch_detail_account_id :
                    raise osv.except_osv(('Perhatian !'), ("Account Inter belum diisi dalam Master branch %s - %s!")%(key.code, key.name))

                balance = value['debit']-value['credit']
                debit = abs(balance) if balance < 0 else 0
                credit = balance if balance > 0 else 0
                
                if balance != 0:
                    move_line_create = {
                        'name': _('Interco Bank Transfer %s')%(key.name),
                        'ref':_('Interco Bank Transfer %s')%(key.name),
                        'account_id': inter_branch_header_account_id,
                        'move_id': move_id,
                        'journal_id': vals.payment_from_id.id,
                        'period_id': vals.period_id.id,
                        'date': vals.date,
                        'debit': debit,
                        'credit': credit,
                        'branch_id' : key.id,
                        'division' : vals.division                    
                    }    
                    inter_first_move = move_line.create(cr, uid, move_line_create, context)    
                             
                    move_line2_create = {
                        'name': _('Interco Bank Transfer %s')%(vals.branch_id.name),
                        'ref':_('Interco Bank Transfer %s')%(vals.branch_id.name),
                        'account_id': inter_branch_detail_account_id,
                        'move_id': move_id,
                        'journal_id': vals.payment_from_id.id,
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
                raise osv.except_osv(('Perhatian !'), ("Bank Transfer sudah diproses, data tidak bisa didelete !"))
        return super(wtc_bank_transfer, self).unlink(cr, uid, ids, context=context)     
    
    def branch_id_change(self, cr, uid, ids, branch_id, context=None):
        value = {}
        if branch_id :
            value['payment_from_id'] = False
        
        return {'value':value}


    def print_report_bank_transfer(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        datas = self.read(cr, uid, ids,context=context)[0]
        return self.pool['report'].get_action(cr, uid, [], 'wtc_bank_transfer.wtc_bank_transfer_report', data=datas, context=context)
  
    @api.multi
    def action_klik_payment(self):
        self.write({
            'is_payment':True,
            'payment_klik_uid':self._uid,
            'payment_klik_date':datetime.now(),
        })
            
class wtc_bank_transfer_line(models.Model): 
    _name = 'wtc.bank.transfer.line'
    _description = 'Bank Transfer Line'

    @api.model
    def _get_branch(self):
        branch_user = self.env['res.users'].browse(self._uid).branch_ids
        branch_ids = [x.id for x in branch_user]
        branch_total = self.env['wtc.branch'].sudo().search(['|',
                                                          ('branch_type','=','HO'),
                                                          ('id','in',branch_ids)
                                                          ],order='name')
        
        return [(branch.code,branch.name) for branch in branch_total]
    

    name = fields.Char(string="Name",readonly=True)
    branch_destination_id = fields.Selection('_get_branch', string='Branch Destination', required=True)   
    payment_to_id = fields.Many2one('account.journal',string="Bank",domain="[('branch_id.code','=',branch_destination_id),('type','in',('cash','bank','pettycash'))]")
    description = fields.Char(string="Description")
    amount = fields.Float('Amount')
    bank_transfer_id = fields.Many2one('wtc.bank.transfer',string="Bank Transfer")
    reimbursement_id = fields.Many2one('wtc.reimbursed',domain="[('state','=','approved')]", string="Reimbursed No")
    
    @api.model
    def create(self,vals):
        if vals.get('reimbursement_id',False):
            obj = self.env['wtc.reimbursed'].browse(vals['reimbursement_id'])
            vals['amount'] = obj.amount_total

        return super(wtc_bank_transfer_line,self).create(vals)

    @api.multi
    def write(self,vals):
        if vals.get('reimbursement_id',False):
            obj = self.env['wtc.reimbursed'].browse(vals['reimbursement_id'])
            vals['amount'] = obj.amount_total

        return super(wtc_bank_transfer_line,self).write(vals)


    @api.onchange('branch_destination_id')
    def branch_destination_change(self):
        if not self.bank_transfer_id.description or not self.bank_transfer_id.branch_id or not self.bank_transfer_id.payment_from_id :
                raise osv.except_osv(('Perhatian !'), ("Sebelum menambah detil transaksi,\n harap isi data header terlebih dahulu."))            
                 
        dom = {}
        rekap_journal_id = []
        journal_id = self.env['account.journal'].sudo().search([
                                                                ('branch_id.code','=',self.branch_destination_id),
                                                                ('type','in',('cash','bank','pettycash'))
                                                                ])
        if journal_id :
            for x in journal_id :
                rekap_journal_id.append(x.id)            
            dom['payment_to_id'] = [('id','in',(rekap_journal_id))]
        else :
            dom['payment_to_id'] = [('branch_id.code','=',self.branch_destination_id),('type','in',('cash','bank','pettycash'))]  
        self.description = self.bank_transfer_id.description
        if not self.reimbursement_id :
          self.payment_to_id = False
        return {'domain':dom}
   
    @api.onchange('reimbursement_id','branch_destination_id','amount')
    def change_reimbursement(self):
       if self.reimbursement_id :
           self.branch_destination_id = self.reimbursement_id.branch_id.code
           self.payment_to_id = self.reimbursement_id.journal_id.id
           self.amount = self.reimbursement_id.amount_total
   
    @api.onchange('amount')
    def change_amount(self):
        if self.amount and self.reimbursement_id :
            self.amount = self.reimbursement_id.amount_total

class wtc_bank_transfer_reconcile_line(models.Model): 
    _name = 'wtc.bank.transfer.reconcile.line'
    _description = 'Bank Transfer Reconciliation Line'

    @api.one
    @api.depends('move_line_id')
    def _compute_balance(self):
        res = {}
        move_line = self.move_line_id or False

        if not move_line:
            self.amount_original = 0.0
            self.name = ""
        else :
            self.amount_original = move_line.debit - move_line.credit
            self.name = move_line.name

    name = fields.Char(string="Name",readonly=True,store=True)
    bank_transfer_id = fields.Many2one('wtc.bank.transfer',string="Bank Transfer", required=True, select=1)
    move_line_id = fields.Many2one('account.move.line', string='Journal Item', required=True)   
    ref_original = fields.Char(related='move_line_id.ref', string='Ref', readonly=1)
    date_original = fields.Date(related='move_line_id.date', string='Date', readonly=1)
    amount_original = fields.Float(string='Original Amount', store=True, digits_compute=dp.get_precision('Account'), compute='_compute_balance')

    def onchange_move_line_id(self, cr, uid, ids, move_line_id, journal_id):
        values = {}
        warning = {}

        if not journal_id :
            warning = {
                'title': 'Perhatian !',
                'message': 'Harap lengkapi header terlebih dahulu.',
            }

        if move_line_id :
            move_line = self.pool.get('account.move.line').browse(cr, uid, move_line_id)
            values.update({
                'name': move_line.name,
                'ref_original': move_line.ref,
                'date_original': move_line.date,
                'amount_original': move_line.debit - move_line.credit
                })
        if warning :
            values.update({
                'name': False,
                'move_line_id': False,
                'ref_original': False,
                'name_original': False,
                'date_original': False,
                'amount_original': False,
                })
        return {
            'value': values,
            'warning': warning,
        }
