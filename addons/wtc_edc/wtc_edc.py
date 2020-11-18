import time
from datetime import datetime
from openerp import models, fields, api
from openerp.osv import osv
from string import whitespace
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.osv import orm

class wtc_edc(models.Model):
    _inherit = "account.voucher"

    @api.one
    @api.depends('percentage','amount')
    def _compute_amount(self):
        self.amount_edc = self.amount *100/(100-self.percentage)

        
    @api.one
    @api.depends('journal_id')
    def _journal_type(self):
        self.journal_type = self.journal_id.type
        
    card_no = fields.Char(string="Card No")
    card_name = fields.Char(string="Card Name")
    percentage = fields.Float(string="Bank Charge (%)")
    amount_edc = fields.Float(string='Total Amount',digits=dp.get_precision('Account'), store=True, readonly=True, compute='_compute_amount',)
    approval_code = fields.Char(sting="Approval Code")
    journal_type = fields.Char(string="Journal Type",compute='_journal_type')
    
    @api.cr_uid_ids_context
    def first_move_line_get(self, cr, uid, voucher_id, move_id, company_currency, current_currency, context=None):
        move_line = super(wtc_edc, self).first_move_line_get(cr,uid,voucher_id, move_id, company_currency, current_currency, context=context)
        voucher = self.pool.get('account.voucher').browse(cr,uid,voucher_id,context)
        if voucher.journal_type == 'edc' :
            move_line['partner_id'] = voucher.journal_id.partner_id.id
        move_line['branch_id'] = voucher.branch_id.id
        move_line['division'] = voucher.division
        return move_line
        
class wtc_edc_journal(models.Model):
    _inherit = "account.journal"
                
    partner_id = fields.Many2one('res.partner',string="Partner") 
 
class wtc_edc_journal_type(orm.Model):
    _inherit = "account.journal"
 
    def _register_hook(self, cr):      
        selection = self._columns['type'].selection
        if ('edc','EDC') not in selection:
            self._columns['type'].selection.append(
                ('edc', 'EDC'))
        return super(wtc_edc_journal_type, self)._register_hook(cr)                            
