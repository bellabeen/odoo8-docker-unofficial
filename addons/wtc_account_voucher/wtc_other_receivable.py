import time
from lxml import etree
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import openerp.addons.decimal_precision as dp
from openerp.osv import orm

class account_voucher_or(models.Model):
    _inherit = 'account.voucher'
    
    user_id = fields.Many2one('res.users', string='Responsible', change_default=True,
        readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='always')
    kwitansi = fields.Boolean('Yg Sudah Print Kwitansi')
    
    @api.onchange('kwitansi')
    def change_kwitansi(self):
        if self.kwitansi :
            self.line_cr_ids = False
            self.line_dr_ids = False
            
    @api.multi
    def branch_id_onchange(self,branch_id):
        dom={}
        edi_doc_list = ['&', ('active','=',True), ('type','!=','view')]
        dict=self.env['wtc.account.filter'].get_domain_account('other_receivable_header')
        edi_doc_list.extend(dict)      
        dom['account_id'] = edi_doc_list
        return {'domain':dom,'value': {'journal_id': 1}} 
            
class account_voucher_line(models.Model):
    _inherit = 'account.voucher.line'

    kwitansi = fields.Boolean(related='voucher_id.kwitansi',string='Yg Sudah Print Kwitansi')
    
    @api.multi
    def account_id_onchange(self,account_id,branch_id,division):
        if not branch_id or not division:
            raise except_orm(_('No Branch Defined!'), _('Sebelum menambah detil transaksi,\n harap isi branch dan division terlebih dahulu.'))
        dom2={}
        edi_doc_list2 = ['&', ('active','=',True), ('type','!=','view')]
        dict=self.env['wtc.account.filter'].get_domain_account('other_receivable_detail')
        edi_doc_list2.extend(dict)      
        dom2['account_id'] = edi_doc_list2
        return {'domain':dom2}  
    
class AccountFilter(orm.Model):
    _inherit = "wtc.account.filter"

    def _register_hook(self, cr):
        selection = self._columns['name'].selection
        if ('other_receivable_header','Other Receivable Header') not in selection: 
            self._columns['name'].selection.append(
                ('other_receivable_header', 'Other Receivable Header'))
        return super(AccountFilter, self)._register_hook(cr)    
    
   
    
