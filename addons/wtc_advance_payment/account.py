from openerp import netsvc
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
import time
from datetime import datetime
import logging
from openerp.osv import orm

class wtc_adv_journal_type(orm.Model):
    _inherit = "account.journal"
 
    def _register_hook(self, cr):
        selection = self._columns['type'].selection
        if ('advance_payment','Advance Payment') not in selection:         
            self._columns['type'].selection.append(
                ('advance_payment', 'Advance Payment'))
        return super(wtc_adv_journal_type, self)._register_hook(cr)  
