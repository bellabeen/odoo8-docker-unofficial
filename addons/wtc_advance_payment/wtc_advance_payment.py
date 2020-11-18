import itertools
from lxml import etree
from datetime import datetime, timedelta
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import openerp.addons.decimal_precision as dp
from openerp.osv import osv

class wtc_advance_payment(models.Model):
    _name = "wtc.advance.payment"
    _description = "Advance Payment"
    _order = "id asc"
    
    #===========================================================================
    # @api.one
    # @api.depends('advance_payment_line.amount')
    # def _compute_amount(self):
    #     self.amount_total = sum(line.amount for line in self.advance_payment_line)
    #===========================================================================

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
            
    @api.model
    def _get_default_date_model(self):
        return self.env['wtc.branch'].get_default_date_model()
                
    name = fields.Char(string='Advance Payment')
    user_id = fields.Many2one('res.users',string='Employee',required=True)
    employee_id = fields.Many2one('hr.employee',string='Employee')
    branch_id = fields.Many2one('wtc.branch', string='Branch',required=True, default=_get_default_branch)
    date = fields.Date(string='Date',default=_get_default_date)
    account_avp_id = fields.Many2one('account.account',string='Account Advance Payment')
    payment_method = fields.Many2one('account.journal',string='Payment Method',required=True)
    division = fields.Selection([
                                 ('Unit','Unit'),
                                 ('Sparepart','Sparepart'),
                                 ('Umum','Umum')
                                 ],required=True,string='Division')
    amount = fields.Float(string='Total',required=True)
    
    state = fields.Selection([
            ('draft','Draft'),
            ('waiting_for_approval','Waiting Approval'),
            ('approved','Approved'),
            ('confirmed','Confirmed'),
            ('done','Done')
        ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False,)
    description = fields.Text(string='Description')
    user_balance = fields.Float(string='Balance',compute='onchange_user_id')
    account_move_id = fields.Many2one('account.move')
    confirm_uid = fields.Many2one('res.users',string="Confirmed by")
    confirm_date = fields.Datetime('Confirmed on')
    date_due = fields.Date(string='Due Date')
    no_rekening_tujuan = fields.Char('No Rekening Tujuan')
    is_payment = fields.Boolean('Klik BCA ?')
    payment_klik_uid = fields.Many2one('res.users','Payment Klik by')
    payment_klik_date = fields.Datetime('Payment Klik on')

    @api.multi
    def get_sequence(self,branch_id,context=None):
        doc_code = self.env['wtc.branch'].browse(branch_id).doc_code
        seq_name = 'AVP/{0}'.format(doc_code)
        seq = self.env['ir.sequence']
        ids = seq.sudo().search([('name','=',seq_name)])
        if not ids:
            prefix = '/%(y)s/%(month)s/'
            prefix = seq_name + prefix
            ids = seq.create({'name':seq_name,
                                 'implementation':'no_gap',
                                 'prefix':prefix,
                                 'padding':5})
        
        return seq.get_id(ids.id)
    
    @api.model
    def create(self,values,context=None):
        values['name'] = self.get_sequence(values['branch_id'],context)
        obj_branch_config = self.env['wtc.branch.config'].search([('branch_id','=',values['branch_id'])])
        if not obj_branch_config:
            raise Warning("Konfigurasi jurnal cabang belum dibuat, silahkan setting dulu")
        else:
            if not(obj_branch_config.wtc_advance_payment_account_id):
                raise Warning("Konfigurasi cabang jurnal Advance Payment belum dibuat, silahkan setting dulu")
            
        values['account_avp_id'] = obj_branch_config.wtc_advance_payment_account_id.id    
        advance_payment = super(wtc_advance_payment,self).create(values)
        advance_payment.write({'date' : self._get_default_date()})
        return advance_payment
    
    @api.multi
    def wkf_action_confirm(self):
        if self.state=='done':
            self.write({'state':'confirmed'})
            return True
        self.write({'date':self._get_default_date(),'state':'confirmed','confirm_uid':self._uid,'confirm_date':datetime.now()})        
        period_ids = self.env['account.period'].find(dt=self._get_default_date())
        obj_branch_config = self.env['wtc.branch.config'].search([('branch_id','=',self.branch_id.id)])
        if not obj_branch_config:
            raise Warning("Konfigurasi jurnal cabang belum dibuat, silahkan setting dulu")
        else:
            if not(obj_branch_config.wtc_advance_payment_account_id):
                raise Warning("Konfigurasi cabang jurnal Advance Payment belum dibuat, silahkan setting dulu")
        move_line = []
        move_journal = {
                        'name': self.name,
                        'ref': self.name,
                        'journal_id': self.payment_method.id,
                        'date': self._get_default_date(),
                        'period_id':period_ids.id,
                        }
        
        account_id = self.payment_method.default_credit_account_id.id or self.payment_method.default_debit_account_id.id
        
        move_line.append([0,False,{
                    'name': self.description or 'Payment Amount',
                    'partner_id': self.user_id.partner_id.id,
                    'account_id': account_id,
                    'period_id': period_ids.id,
                    'date': self._get_default_date(),
                    'debit': 0.0,
                    'credit': self.amount,
                    'branch_id': self.branch_id.id,
                    'division': self.division,
                    'date_maturity': self.date_due
                     }])
       
        move_line.append([0,False,{
                    'name': self.description or 'Advance Payment',
                    'partner_id': self.user_id.partner_id.id,
                    'account_id': obj_branch_config.wtc_advance_payment_account_id.id,
                    'period_id': period_ids.id,
                    'date': self._get_default_date(),
                    'debit': self.amount,
                    'credit': 0.0,
                    'branch_id': self.branch_id.id,
                    'division': self.division,
                    'date_maturity': self.date_due
                     }])
        
        move_journal['line_id']=move_line
        
        move_obj = self.env['account.move']
        create_journal = move_obj.create(move_journal)
        if self.payment_method.entry_posted:
            create_journal.post()
        self.write({'account_move_id':create_journal.id})
        #wkwkwk
        return True
    
    @api.onchange('user_id','amount')
    def onchange_user_id(self):
        if self.amount < 0:
            self.amount = 0.0
            return {'warning':{'title':'Perhatian !','message':'Tidak boleh input nilai negatif!'}}
            #raise Warning( ("Total tidak boleh negatif!"))
        
        advance_payment = self.search([('user_id','=',self.user_id.id),('state','=','confirmed')])
        if self.user_id :
            obj_search_empl=self.env['hr.employee'].search([('user_id','=',self.user_id.id)])
            self.employee_id=obj_search_empl.id
        balance = 0.0
        for avp in advance_payment:
            balance+=avp.amount
        
        self.user_balance = balance
        
    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Advance Payment sudah diproses, data tidak bisa dihapus !"))
        return super(wtc_advance_payment, self).unlink(cr, uid, ids, context=context)

    @api.multi
    def action_print_advance_payment(self):
        active_ids = self.env.context.get('active_ids', [])
        user = self.env['res.users'].suspend_security().browse(self._uid).name
        datas = {
             'ids': active_ids,
             'model': 'wtc.advance.payment',
             'form': self.read()[0],
             'user': user
        }
        return self.env['report'].suspend_security().get_action(self, 'wtc_advance_payment.teds_advance_payment', data=datas)        
    
    @api.multi
    def action_klik_payment(self):
        self.write({
            'is_payment':True,
            'payment_klik_uid':self._uid,
            'payment_klik_date':datetime.now(),
        })
