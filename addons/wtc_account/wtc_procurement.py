from openerp.osv import fields, osv
from datetime import datetime
import time

class procurement(osv.osv):
    _inherit = 'procurement.order'
    
    _columns = {
                'confirm_uid':fields.many2one('res.users',string="Run by"),
                'confirm_date':fields.datetime('Run on'),
                'cancel_uid':fields.many2one('res.users',string="Cancelled by"),
                'cancel_date':fields.datetime('Cancelled on'),                
                }
    
    def run(self, cr, uid, ids, autocommit=False, context=None):
        self.write(cr,uid,ids,{'confirm_uid':uid,'confirm_date':datetime.now()})        
        vals = super(procurement,self).run(cr,uid,ids,autocommit=autocommit,context=context)
        return vals
        
    def cancel(self, cr, uid, ids, context=None):
        self.write(cr,uid,ids,{'cancel_uid':uid,'cancel_date':datetime.now()})        
        vals = super(procurement,self).cancel(cr,uid,ids,context=context)
        return vals    