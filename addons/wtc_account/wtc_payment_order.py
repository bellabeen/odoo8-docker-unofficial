from openerp.osv import fields, osv
from datetime import datetime
import time

class payment_order(osv.osv):
    _inherit = 'payment.order'
    
    _columns = {
                'confirm_uid':fields.many2one('res.users',string="Confirmed by"),
                'confirm_date':fields.datetime('Confirmed on'),
                }
    
    def action_open(self, cr, uid, ids, *args):
        self.write(cr,uid,ids,{'confirm_uid':uid,'confirm_date':datetime.now()})        
        vals = super(payment_order,self).action_open(cr,uid,ids,*args)
        return vals     