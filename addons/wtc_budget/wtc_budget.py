import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _

class wtc_crossovered_budget(osv.osv):
    _inherit = 'crossovered.budget'
    
    _columns = {
                'confirm_uid':fields.many2one('res.users',string="Confirmed by"),
                'confirm_date':fields.datetime('Confirmed on'),
                'cancel_uid':fields.many2one('res.users',string="Cancelled by"),
                'cancel_date':fields.datetime('Cancelled on'),
                }
    
    def budget_confirm(self, cr, uid, ids, *args):
        vals = super(wtc_crossovered_budget,self).budget_confirm(cr,uid,ids,*args)
        self.write(cr, uid, ids, {
            'confirm_uid': uid,'confirm_date':datetime.now()
        })
        return vals 
  
    def budget_cancel(self, cr, uid, ids, *args):
        vals = super(wtc_crossovered_budget,self).budget_cancel(cr,uid,ids,*args)
        self.write(cr, uid, ids, {
            'cancel_uid': uid,'cancel_date':datetime.now()
        })
        return vals    