import time
from datetime import datetime
from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp.osv import orm

class wtc_account_voucher_approval(osv.osv):
    _inherit = "account.voucher"
    STATE_SELECTION = [ ('draft','Draft'),
                        ('waiting_for_approval','Waiting Approval'),
                        ('confirmed', 'Waiting Approval'),
                        ('request_approval','RFA'), 
                        ('approved','Approve'), 
                        ('cancel','Cancelled'),
                        ('proforma','Pro-forma'),
                        ('posted','Posted') ]
    
    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('account.voucher.line').browse(cr, uid, ids, context=context):
            result[line.voucher_id.id] = True
        return result.keys()
    
    def _total_debit(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for voucher in self.browse(cr, uid, ids, context=context):
            res[voucher.id] = {
                'total_debit': 0.0,
            }
            value =  0.0
           
            for line in voucher.line_dr_ids:
                value += line.amount
            res[voucher.id]['total_debit'] = value

        return res
    
     
    _columns = {
                'approval_ids': fields.one2many('wtc.approval.line','transaction_id',string="Table Approval",domain=[('form_id','=',_inherit)],),
                'state':fields.selection(STATE_SELECTION, 'Status', readonly=True, track_visibility='onchange', copy=False,
                    help=' * The \'Draft\' status is used when a user is encoding a new and unconfirmed Voucher. \
                                \n* The \'Pro-forma\' when voucher is in Pro-forma status,voucher does not have an voucher number. \
                                \n* The \'Posted\' status is used when user create voucher,a voucher number is generated and voucher entries are created in account \
                                \n* The \'Cancelled\' status is used when user cancel voucher.'),
                'approval_state': fields.selection([('b','Belum Request'),('rf','Request For Approval'),('a','Approved'),('r','Reject')],'Approval State', readonly=True),
                'type':fields.selection([
                    ('sale','Sale'),
                    ('purchase','Purchase'),
                    ('payment','Payment'),
                    ('receipt','Receipt'),
                ],'Default Type', readonly=True, states={'request_approval':[('readonly',True)],'draft':[('readonly',False)]}),
                'name':fields.char('Memo', readonly=True, states={'request_approval':[('readonly',True)],'draft':[('readonly',False)]}),
                'date':fields.date('Date', readonly=True, select=True, states={'request_approval':[('readonly',True)],'draft':[('readonly',False)]},
                                   help="Effective date for accounting entries", copy=False),
                'journal_id':fields.many2one('account.journal', 'Journal', required=True, readonly=True, states={'request_approval':[('readonly',True)],'draft':[('readonly',False)]}),
                'account_id':fields.many2one('account.account', 'Account', required=True, readonly=True, states={'request_approval':[('readonly',True)],'draft':[('readonly',False)]}),
                'line_ids':fields.one2many('account.voucher.line', 'voucher_id', 'Voucher Lines',
                                           readonly=True, copy=True,
                                           states={'request_approval':[('readonly',True)],'draft':[('readonly',False)]}),
                'line_cr_ids':fields.one2many('account.voucher.line','voucher_id','Credits',
                    domain=[('type','=','cr')], context={'default_type':'cr'}, readonly=True, states={'request_approval':[('readonly',True)],'draft':[('readonly',False)]}),
                'line_dr_ids':fields.one2many('account.voucher.line','voucher_id','Debits',
                    domain=[('type','=','dr')], context={'default_type':'dr'}, readonly=True, states={'request_approval':[('readonly',True)],'draft':[('readonly',False)]}),
                'period_id': fields.many2one('account.period', 'Period', required=True, readonly=True, states={'request_approval':[('readonly',True)],'draft':[('readonly',False)]}),
                'narration':fields.text('Notes', readonly=True, states={'request_approval':[('readonly',True)],'draft':[('readonly',False)]}),
                'company_id': fields.many2one('res.company', 'Company', required=True, readonly=True, states={'request_approval':[('readonly',True)],'draft':[('readonly',False)]}),
                'amount': fields.float('Total', digits_compute=dp.get_precision('Account'), required=True, readonly=True, states={'request_approval':[('readonly',True)],'draft':[('readonly',False)]}),
                'reference': fields.char('Ref #', readonly=True, states={'request_approval':[('readonly',True)],'draft':[('readonly',False)]},
                                         help="Transaction reference number.", copy=False),
                'partner_id':fields.many2one('res.partner', 'Partner', change_default=1, readonly=True, states={'request_approval':[('readonly',True)],'draft':[('readonly',False)]}),
                'pay_now':fields.selection([
                    ('pay_now','Pay Directly'),
                    ('pay_later','Pay Later or Group Funds'),
                ],'Payment', select=True, readonly=True, states={'request_approval':[('readonly',True)],'draft':[('readonly',False)]}),
                'tax_id': fields.many2one('account.tax', 'Tax', readonly=True, states={'request_approval':[('readonly',True)],'draft':[('readonly',False)]}, domain=[('price_include','=', False)], help="Only for tax excluded from price"),
                'date_due': fields.date('Due Date', readonly=True, select=True, states={'request_approval':[('readonly',True)],'draft':[('readonly',False)]}),
                'payment_option':fields.selection([
                                                   ('without_writeoff', 'Keep Open'),
                                                   ('with_writeoff', 'Reconcile Payment Balance'),
                                                   ], 'Payment Difference', required=True, readonly=True, states={'request_approval':[('readonly',True)],'draft': [('readonly', False)]}, help="This field helps you to choose what you want to do with the eventual difference between the paid amount and the sum of allocated amounts. You can either choose to keep open this difference on the partner's account, or reconcile it with the payment(s)"),
                'writeoff_acc_id': fields.many2one('account.account', 'Counterpart Account', readonly=True, states={'request_approval':[('readonly',True)],'draft': [('readonly', False)]}),
                'comment': fields.char('Counterpart Comment', required=True, readonly=True, states={'request_approval':[('readonly',True)],'draft': [('readonly', False)]}),
                'analytic_id': fields.many2one('account.analytic.account','Write-Off Analytic Account', readonly=True, states={'request_approval':[('readonly',True)],'draft': [('readonly', False)]}),
                'payment_rate_currency_id': fields.many2one('res.currency', 'Payment Rate Currency', required=True, readonly=True, states={'draft':[('readonly',False)]}),
                'payment_rate': fields.float('Exchange Rate', digits=(12,6), required=True, readonly=True, states={'request_approval':[('readonly',True)],'draft': [('readonly', False)]},
                    help='The specific rate that will be used, in this voucher, between the selected currency (in \'Payment Rate Currency\' field)  and the voucher currency.'),
                'total_debit': fields.function(_total_debit, digits_compute=dp.get_precision('Account'), string='Total Debit',
#                     store={
#                         'account.voucher': (lambda self, cr, uid, ids, c={}: ids, ['line_dr_ids'], 10),
#                         'account.voucher.line': (_get_order, ['amount','voucher_id'], 10),
#                     },                   
                    multi='sums', help="Line Debit"),            
    }

    
    _defaults ={
                'approval_state':'b'
                }
    
    def wkf_cancel_approval_av(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'b'})
        return True 
            
    def validate_or_rfa(self,cr,uid,ids,context=None):
        obj_av = self.browse(cr, uid, ids, context=context)
        if obj_av.total_debit > 0 :
            self.signal_workflow(cr, uid, ids, 'approval_request')
        else :
            self.signal_workflow(cr, uid, ids, 'proforma_voucher')
        return True
    
    def wkf_request_approval(self, cr, uid, ids, context=None):
        obj_av = self.browse(cr, uid, ids, context=context)

        obj_matrix = self.pool.get("wtc.approval.matrixbiaya")
        total = 0.0
        for x in obj_av.line_dr_ids :
            total += x.amount
        type = obj_av.type
        if type == 'payment' :
            view_name = 'account.voucher.payment.form'
        elif type == 'purchase' :
            view_name = 'account.voucher.purchase.form'
        elif type == 'receipt' :
            view_name = 'account.voucher.receipt.form'
        obj_matrix.request_by_value(cr, uid, ids, obj_av, total,type,view_name)
        self.write(cr, uid, ids, {'state': 'waiting_for_approval','approval_state':'rf'})
        return True        
    
    def wkf_approval(self, cr, uid, ids, context=None):
        obj_av = self.browse(cr, uid, ids, context=context) 
        approval_sts = self.pool.get("wtc.approval.matrixbiaya").approve(cr, uid, ids, obj_av)
        if approval_sts == 1:
            self.write(cr, uid, ids, {'approval_state':'a'})
        elif approval_sts == 0:
            raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group approval"))
   
        return True

    def has_approved(self, cr, uid, ids, *args):
        obj_av = self.browse(cr, uid, ids)
        return obj_av.approval_state == 'a'

    def is_payment(self, cr, uid, ids, *args):
        obj_av = self.browse(cr, uid, ids)
        if not obj_av.type :
            return False
        return True
        
    def has_rejected(self, cr, uid, ids, *args):
        obj_av = self.browse(cr, uid, ids)
        if obj_av.approval_state == 'r':
            self.write(cr, uid, ids, {'state':'draft'})
            return True
        return False

    def wkf_set_to_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'r'}) 

    def wkf_set_to_draft_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'b'})
   
