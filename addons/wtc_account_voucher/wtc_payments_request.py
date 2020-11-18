from lxml import etree
from datetime import datetime
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import openerp.addons.decimal_precision as dp
from openerp.osv import orm

class account_voucher_pr(models.Model):
    _inherit = 'account.voucher'

    @api.cr_uid_ids_context
    def jenis_transaksi_change(self, cr, uid, ids, jenis_transaksi_id,branch_id):
        payments_request_histrory=[]
        if jenis_transaksi_id : 
            pr_pool = self.pool.get('account.voucher')
            pr_search = pr_pool.search(cr,uid,[('jenis_transaksi_id','=',jenis_transaksi_id),('branch_id','=',branch_id),])
            pr_pool2 = self.pool.get('account.voucher.line')
            pr_search2 = pr_pool2.search(cr,uid,[('voucher_id','=',pr_search),])
            payments_request_histrory = []
            if not pr_search2 :
                payments_request_histrory = []
            elif pr_search2 :
                pr_browse = pr_pool2.browse(cr,uid,pr_search2)           
                for x in pr_browse :
                    payments_request_histrory.append([0,0,{
                                     'account_id':x.account_id,
                                     'name':x.name,
                                     'amount':x.amount,
                                     'account_analytic_id':x.account_analytic_id
                    }])
        return {'value':{'payments_request_ids': payments_request_histrory}}
    
    @api.onchange('branch_id')
    def branch_onchange(self):
        account_id=False
        journal_id=False
        if self.branch_id :
            branch_config =self.env['wtc.branch.config'].search([('branch_id','=',self.branch_id.id)])
            journal_id=branch_config.wtc_payment_request_account_id.id
            account_id=branch_config.wtc_payment_request_account_id.default_credit_account_id.id
            if not journal_id :
                    raise except_orm(_('Warning!'), _('Konfigurasi jurnal cabang belum dibuat, silahkan setting dulu !'))
            if not account_id :
                    raise except_orm(_('Warning!'), _('Konfigurasi jurnal account cabang belum dibuat, silahkan setting dulu !'))
        self.account_id = account_id
        self.journal_id = journal_id

    transaksi = fields.Selection([
            ('rutin','Rutin'),
            ('tidak_rutin','Tidak Rutin'),
        ], string='Transaksi',  index=True, change_default=True)
    jenis_transaksi_id = fields.Many2one('wtc.payments.request.type', string='Tipe Transaksi', change_default=True,
        readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='always')
    no_document = fields.Char(string='No Document', index=True)
    tgl_document = fields.Date(string='Tgl Document',
        readonly=True, states={'draft': [('readonly', False)]}, index=True,
        help="Keep empty to use the current date", copy=False)
    payments_request_ids = fields.One2many('account.voucher.line', 'voucher_id',
         readonly=True, copy=True)
    
    
    @api.multi
    def transaksi_change(self,transaksi,jenis_transaksi_id):
        if transaksi :
          return {'value':{'jenis_transaksi_id':False}}

class account_voucher_line(models.Model):
    _inherit = 'account.voucher.line'

    name = fields.Text(string='Description')

    @api.multi
    def name_onchange(self,name,branch_id,division):
        if not branch_id or not division:
            raise except_orm(_('No Branch Defined!'), _('Sebelum menambah detil transaksi,\n harap isi branch dan division terlebih dahulu.'))
        dom={}
        edi_doc_list = ['&', ('active','=',True), ('type','!=','view')]
        dict=self.env['wtc.account.filter'].get_domain_account('payments_request')
        edi_doc_list.extend(dict)      
        dom['account_id'] = edi_doc_list
        return {'domain':dom}     
    
class wtc_payments_request_type(models.Model):
    _name = "wtc.payments.request.type"  
    name = fields.Text(string='Description') 
    
    
class AccountFilter(orm.Model):
    _inherit = "wtc.account.filter"
 
    def _register_hook(self, cr):
        selection = self._columns['name'].selection
        if ('payments_request','Payments Request') not in selection:         
            self._columns['name'].selection.append(
                ('payments_request', 'Payments Request'))
        return super(AccountFilter, self)._register_hook(cr)
