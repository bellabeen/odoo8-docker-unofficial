import itertools
from lxml import etree
import time
from datetime import datetime, timedelta
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp.tools import float_compare
import openerp.addons.decimal_precision as dp
from openerp.osv import orm

class wtc_other_payable(models.Model):
    _inherit = 'account.voucher'               
    
    
    
