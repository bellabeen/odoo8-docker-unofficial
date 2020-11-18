from datetime import datetime, timedelta
import time
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import openerp.addons.decimal_precision as dp
from openerp import workflow
import pytz 

class dealer_sale_order(osv.osv):
    _inherit = 'dealer.sale.order'

    def get_faktur_pajak_for_so(self,cr,uid,ids):
        dso_ids = self.search(cr,uid,[('state','in',('progress','done')),('faktur_pajak_id','=',False),('pajak_gabungan','=',False)],limit=30)
        if not dso_ids:
            return False
        for id in dso_ids:
            self.pool.get('wtc.faktur.pajak.out').get_no_faktur_pajak(cr,uid,id,'dealer.sale.order')
            
        return True
    
    def set_done_for_dsp(self,cr,uid,ids,tgl_awal,tgl_akhir,context=None):
        dso_ids = self.search(cr,uid,[('state','=','progress'),('date_order','>=',tgl_awal),('date_order','<=',tgl_akhir)],order="id asc")
        if not dso_ids:
            return False
        for id in dso_ids:
            dso_id = self.browse(cr, uid, id, context=context)
            inv_done = False
            picking_done = self.test_moves_done(cr, uid, id, context)
            reverse = self.reverse(cr, uid, id, context)
            inv_ids = self._get_invoice_ids(cr, uid, id, context)
            for inv in inv_ids :
                if inv.tipe in ('customer','finco') and inv.state == 'paid' :
                    inv_done = True
            if inv_done and not dso_id.is_cancelled and picking_done and not reverse :
                self.write(cr,uid,id,{'state':'done'})
        return True
