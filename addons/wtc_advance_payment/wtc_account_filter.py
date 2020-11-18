from openerp import netsvc
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
import time
from datetime import datetime
import logging
from openerp.osv import orm

class AccountFilter(orm.Model):
    _inherit = "wtc.account.filter"
 
    def _register_hook(self, cr):
        selection = self._columns['name'].selection
        if ('advance_payment','Advance Payment') not in selection:         
            self._columns['name'].selection.append(
                ('advance_payment', 'Advance Payment'))
        return super(AccountFilter, self)._register_hook(cr)