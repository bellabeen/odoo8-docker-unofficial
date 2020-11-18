import itertools
import time
from lxml import etree
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import openerp.addons.decimal_precision as dp

class wtc_account_filter(models.Model):
    _name = "wtc.account.filter" 

    CODE_SELECTION = [('other_receivable_detail', 'Other Receivable Detail'),]

    name = fields.Selection(CODE_SELECTION, string='Reference/Description')
    #name = fields.Char(string='Reference/Description')
    #model_id = fields.Many2one('ir.model', string='Medel Id')
    type = fields.Selection([
            ('view', 'View'),
            ('other', 'Regular'),
            ('receivable', 'Receivable'),
            ('payable', 'Payable'),
            ('liquidity','Liquidity'),
            ('consolidation', 'Consolidation'),
            ('closed', 'Closed'),
        ], string='Internal Type')
    user_type = fields.Many2one('account.account.type', string='Account Type')
    prefix = fields.Char(string='Prefix')

    @api.multi
    def get_domain_account(self,name):
        dict = []
        account_filter = self.search([('name', '=',name)])
        if len(account_filter) > 1:
            for num in range(0, len(account_filter)-1):
                dict.append('|')
        for x in account_filter :
            if x.type and x.prefix and x.user_type :
                dict.append('&')
                dict.append('&')
            elif x.type and x.prefix :
                dict.append('&')
            elif x.type and x.user_type :
                dict.append('&')
            elif x.prefix and x.user_type :
                dict.append('&')
             
            if  x.type:
                dict.append(( 'type','=',str(x.type) ))
            if x.prefix:
                dict.append(( 'code','ilike',str(x.prefix+'%') ))
            if x.user_type:
                dict.append(( 'user_type','=',x.user_type.id ))
        return dict
