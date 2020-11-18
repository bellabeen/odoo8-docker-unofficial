from datetime import datetime, timedelta
import time
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import openerp.addons.decimal_precision as dp
from openerp import workflow
import pytz 

class wtc_work_order(osv.osv):
    _inherit = 'wtc.work.order'

    def get_faktur_pajak_for_wo(self,cr,uid,ids):
        dso_ids = self.search(cr,uid,[('state','in',('open','done')),('faktur_pajak_id','=',False),('pajak_gabungan','=',False)],limit=30)
        if not dso_ids:
            return False
        for id in dso_ids:
            self.pool.get('wtc.faktur.pajak.out').get_no_faktur_pajak(cr,uid,id,'wtc.work.order')
            
        return True
