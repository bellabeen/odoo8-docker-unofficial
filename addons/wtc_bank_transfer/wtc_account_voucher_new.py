import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp import SUPERUSER_ID
from openerp import tools
import pytz
from lxml import etree

class wtc_account_voucher_new(models.Model):
    _inherit = 'wtc.account.voucher'
   
   
#     def onchange_journal_id(self, cr, uid, ids, journal_id, context=None):
#         journal = self.pool.get('account.journal').browse(cr,uid,journal_id) 
#         if journal.type=='cash' and not journal.is_pusted:
#             return {'value':{'journal_id':False},'warning':{'title':'Perhatian !','message':'Kas belum di PUST, silahkan lakukan PUST terlebih dahulu !'}}
#         res = super(wtc_account_voucher_new,self).onchange_journal_id(cr,uid,ids,journal_id,context=context)
#         return res