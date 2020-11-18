import time
from datetime import datetime
import string 
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import api
from openerp.osv.expression import get_unaccent_wrapper


class res_partner(osv.osv):
    _inherit = 'res.partner'
    
    _columns = {
                'credit_limit_unit': fields.float('Credit Limit Unit'),
                'credit_limit_sparepart': fields.float('Credit Limit Sparepart'),
                }
    