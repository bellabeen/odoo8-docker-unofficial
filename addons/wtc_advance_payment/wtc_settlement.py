import itertools
from lxml import etree
from datetime import datetime, timedelta
from openerp import models, exceptions, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import openerp.addons.decimal_precision as dp
from Tkconstants import CASCADE
from openerp import workflow
from openerp.osv import osv

class wtc_settlement(models.Model):
    _name = "wtc.settlement"
    _description = "Settlement"
    _order = "id asc"
    
    @api.one
    @api.depends('amount_avp','settlement_line.amount')
    def _compute_amount(self):
        self.amount_total = sum(line.amount for line in self.settlement_line)
        if self.type:
            if self.type=='kembali':
                self.amount_gap = self.amount_avp - self.amount_total
            else:
                self.amount_gap = self.amount_total - self.amount_avp
        else:
            self.amount_gap = 0

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


    def print_x(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = self.read(cr, uid, ids,context=context)[0]
        
        return self.pool['report'].get_action(cr, uid, [], 'wtc_advance_payment.settlement_done', data=data, context=context)

    def print_y(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = self.read(cr, uid, ids,context=context)[0]
        
        return self.pool['report'].get_action(cr, uid, [], 'wtc_advance_payment.settlement_draft', data=data, context=context)

    @api.model
    def _get_default_date_model(self):
        return self.env['wtc.branch'].get_default_date_model()
            
    name = fields.Char(string='Settlement')
    user_id = fields.Many2one('res.users',string='Employee',required=True)
    branch_id = fields.Many2one('wtc.branch', string='Branch',required=True, default=_get_default_branch)
    advance_payment_id = fields.Many2one('wtc.advance.payment',string='Advance Payment',required=True)
    amount_avp = fields.Float()
    amount_avp_show = fields.Float(string='Total Avp',related = 'amount_avp')
    date = fields.Date(string='Date',default=_get_default_date)
    division = fields.Selection([
                                 ('Unit','Unit'),
                                 ('Sparepart','Sparepart'),
                                 ('Umum','Umum')
                                 ],required=True,string='Division')
    state = fields.Selection([
            ('draft','Draft'),
            ('waiting_for_approval','Waiting Approval'),
            ('approved','Approved'),
            ('done','Done'),
            ('cancel','Cancelled')
        ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False,)
    description = fields.Text(string='Description')
    payment_method = fields.Many2one('account.journal',string='Payment Method',required=True)
    type = fields.Selection([
                             ('tambah','Tambah'),
                             ('kembali','Kembali')                             
                             ],string='Type Kas')
    amount_total = fields.Float(string='Total',digits=dp.get_precision('Account'), store=True, readonly=True, compute='_compute_amount',)
    amount_gap = fields.Float(string='Total Kembalian/Tambahan',digits=dp.get_precision('Account'), store=True, readonly=True, compute='_compute_amount',)
    settlement_line = fields.One2many('wtc.settlement.line','settlement_id',required=True)
    account_avp_id = fields.Many2one('account.account',string='Account Advance Payment')
    account_move_id = fields.Many2one('account.move')
    confirm_uid = fields.Many2one('res.users',string="Confirmed by")
    confirm_date = fields.Datetime('Confirmed on')
    cancel_uid = fields.Many2one('res.users',string="Cancelled by")
    cancel_date = fields.Datetime('Cancelled on')
    is_payment = fields.Boolean('Klik BCA ?')
    payment_klik_uid = fields.Many2one('res.users','Payment Klik by')
    payment_klik_date = fields.Datetime('Payment Klik on')
        
#     _sql_constraints = [
#     ('unique_advance_payment_id', 'unique(advance_payment_id)', 'Nomor Advance Payment sudah pernah di buat sudah ada !'),
#     ]
    
    @api.one
    @api.constrains('advance_payment_id', 'state')
    def _check_description(self):
        avp_id = self.search([('advance_payment_id','=',self.advance_payment_id.id)])
        if len(avp_id)>1:
            for avp in avp_id:
                if avp.state!='cancel' and avp.id!=self.id:
                    raise Warning("Nomor Advance Payment sudah pernah di buat di transaksi lain")
        
    @api.multi
    def get_sequence(self,branch_id,context=None):
        doc_code = self.env['wtc.branch'].browse(branch_id).doc_code
        seq_name = 'STL/{0}'.format(doc_code)
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
        obj_branch_config = self.env['wtc.branch.config'].search([('branch_id','=',values['branch_id'])])
        if not obj_branch_config:
            raise Warning("Konfigurasi jurnal cabang belum dibuat, silahkan setting dulu")
        else:
            if not(obj_branch_config.wtc_advance_payment_account_id):
                raise Warning("Konfigurasi cabang jurnal Advance Payment belum dibuat, silahkan setting dulu")
        values['name'] = self.get_sequence(values['branch_id'],context)
        values['date'] = self._get_default_date_model()
        settlement = super(wtc_settlement,self).create(values)
        return settlement
    
    @api.multi
    def onchange_avp_id(self,advance_payment_id):
        avp = self.env['wtc.advance.payment'].browse(advance_payment_id)
        result = {'value':{
                  'user_id':avp.user_id.id,
                  'branch_id': avp.branch_id.id,
                  'division': avp.division,
                  'amount_avp': avp.amount,
                  'account_avp_id': avp.account_avp_id.id
                  }}
        
        return result
    
    @api.multi
    def wkf_action_confirm(self,context=None):
        period_ids = self.env['account.period'].find(dt=self._get_default_date().date())
        self.write({'date':self._get_default_date(),'state':'done','confirm_uid':self._uid,'confirm_date':datetime.now()})        
        obj_branch_config = self.env['wtc.branch.config'].search([('branch_id','=',self.branch_id.id)])
        if not obj_branch_config:
            raise Warning("Konfigurasi jurnal cabang belum dibuat, silahkan setting dulu")
        else:
            if not(obj_branch_config.wtc_advance_payment_account_id):
                raise Warning("Konfigurasi cabang jurnal Advance Payment belum dibuat, silahkan setting dulu")
        
        account_id = self.payment_method.default_credit_account_id.id or self.payment_method.default_debit_account_id.id
        
        move_line = []
        move_journal = {
                        'name': self.name,
                        'ref': self.name,
                        'journal_id': self.payment_method.id,
                        'date': self._get_default_date(),
                        'period_id':period_ids.id,
                        }
        move_line.append([0,False,{
                    'name': self.description or 'Payment Amount',
                    'partner_id': self.user_id.partner_id.id,
                    'account_id': self.account_avp_id.id,
                    'period_id': period_ids.id,
                    'date': self._get_default_date(),
                    'debit': 0.0,
                    'credit': self.amount_avp,
                    'branch_id': self.branch_id.id,
                    'division': self.division
                     }])
        for line in self.settlement_line:
            move_line.append([0,False,{
                        'name': self.description or 'Advance Payment',
                        'partner_id': self.user_id.partner_id.id,
                        'account_id': line.account_id.id,
                        'period_id': period_ids.id,
                        'date': self._get_default_date(),
                        'debit': line.amount,
                        'credit': 0.0,
                        'branch_id': line.branch_id.id if line.branch_id else self.branch_id.id,
                        'division': self.division
                         }])
        
        if self.type == 'tambah':
            move_line.append([0,False,{
                    'name': self.description or 'Kekurangan Advance Payment',
                    'partner_id': self.user_id.partner_id.id,
                    'account_id': self.payment_method.default_credit_account_id.id or self.payment_method.default_debit_account_id.id,
                    'period_id': period_ids.id,
                    'date': self._get_default_date(),
                    'debit': 0.0,
                    'credit': self.amount_gap,
                    'branch_id': self.branch_id.id,
                    'division': self.division
                     }])
        elif self.type == 'kembali':
            move_line.append([0,False,{
                    'name': self.description or 'Kembalian Advance Payment',
                    'partner_id': self.user_id.partner_id.id,
                    'account_id': self.payment_method.default_debit_account_id.id or self.payment_method.default_credit_account_id.id,
                    'period_id': period_ids.id,
                    'date': self._get_default_date(),
                    'debit': self.amount_gap,
                    'credit': 0.0,
                    'branch_id': self.branch_id.id,
                    'division': self.division
                     }])                     
        
        move_journal['line_id']=move_line
        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        create_journal = move_obj.create(move_journal)
        if self.payment_method.entry_posted:
            create_journal.post() 
        move_line_avp = move_line_obj.search([('move_id','=',self.advance_payment_id.account_move_id.id),('account_id','=',self.account_avp_id.id)])
        move_line_stl = move_line_obj.search([('move_id','=',create_journal.id),('account_id','=',self.account_avp_id.id)])
        
        self.pool.get('account.move.line').reconcile(self._cr,self._uid, [move_line_avp.id,move_line_stl.id])
        
        self.write({'account_move_id':create_journal.id})
        create_journal.write({'narration':'refresh'}) #untuk mentrigger status move.line, karena jika ada intercompany statusnya unbalance. kalau di write maka berubah jadi balance. kalau unbalance jadi masalah saat mau cancel
        workflow.trg_validate(self._uid, 'wtc.advance.payment', self.advance_payment_id.id, 'avp_done', self._cr)
        if self.advance_payment_id.state != 'done' :
            self.advance_payment_id.state = 'done'
        return True

    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Settlement sudah diproses, data tidak bisa dihapus !"))
        return super(wtc_settlement, self).unlink(cr, uid, ids, context=context)
    
    @api.multi
    def action_cancel_settlement(self,context=None):
        self.write({'state':'cancel','cancel_uid':self._uid,'cancel_date':datetime.now()})
        self.advance_payment_id.write({'state':'confirmed'})
        self.advance_payment_id.signal_workflow('wkf_action_settlement_cancel')
    
    @api.multi
    def wkf_cancel_approval_settlement(self, context=None):
        self.write({'state':'draft','approval_state':'b'})
    
    @api.multi
    def action_klik_payment(self):
        self.write({
            'is_payment':True,
            'payment_klik_uid':self._uid,
            'payment_klik_date':datetime.now(),
        })
                
class wtc_settlement_line(models.Model):
    _name = 'wtc.settlement.line'

    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
    
    settlement_id = fields.Many2one('wtc.settlement',ondelete='cascade')
    account_id = fields.Many2one('account.account',string='Account',required=True)
    amount = fields.Float(string='Amount',required=True)
    branch_id = fields.Many2one('wtc.branch', string='Branch')
    
    @api.onchange('account_id')
    def name_change(self):
        dom = {}
        edi_doc_list = ['&', ('active','=',True), ('type','!=','view')] 
   
        filter = self.env['wtc.account.filter']         
        dict = filter.get_domain_account("advance_payment")
        edi_doc_list.extend(dict)
        dom['account_id']=edi_doc_list
             

        return {'domain':dom}
    
    @api.multi
    def onchange_amount(self,amount,type,total_avp):
        if amount:
            if amount < 0:
                raise exceptions.ValidationError('Tidak boleh input nilai negatif')
            
            if type == 'kembali':
                if amount >= total_avp:
                    #raise exceptions.ValidationError('Amount harus lebih kecil dari total AVP untuk tipe kembali')
                    return {'value':{'settlement_id':False,'account_id':False,'amount':0,'amount_total':0,'amount_gap':0},'warning':{'title':'Perhatian !','message':'Amount harus lebih kecil dari total AVP untuk tipe kembali'}}
            elif type == 'tambah':
                if amount <= total_avp:
                    #raise exceptions.ValidationError('Amount harus lebih besar dari total AVP untuk tipe tambah')
                    return {'value':{'settlement_id':False,'account_id':False,'amount':0},'warning':{'title':'Perhatian !','message':'Amount harus lebih besar dari total AVP untuk tipe tambah'}}
            else:
                if amount != total_avp:
                    return {'value':{'settlement_id':False,'account_id':False,'amount':0},'warning':{'title':'Perhatian !','message':'Amount harus sama dengan total AVP'}}
                    #raise exceptions.ValidationError('Amount harus sama dengan total AVP')
            