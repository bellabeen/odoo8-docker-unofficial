from datetime import datetime, timedelta
from openerp.osv import osv, fields

class bank_statement(osv.osv):
    _inherit = 'account.bank.statement'
    
    _columns = {
                'confirm_uid':fields.many2one('res.users',string="Closed by"),
                'confirm_date':fields.datetime('Closed on'),
                'cancel_uid':fields.many2one('res.users',string="Cancelled by"),
                'cancel_date':fields.datetime('Cancelled on'),                
                }
    
    def _get_default_date(self,cr,uid,context=None):
        return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)
        
    def create(self,cr,uid,vals,context=None):
        vals['date'] = self._get_default_date(cr,uid,context=context)
        res = super(bank_statement,self).create(cr,uid,vals,context=None)
        return res
    
    def button_confirm_bank(self, cr, uid, ids, context=None):
        self.write(cr,uid,ids,{'date':self._get_default_date(cr,uid,context=context),'confirm_uid':uid,'confirm_date':datetime.now()})        
        vals = super(bank_statement,self).button_confirm_bank(cr,uid,ids,context=None)
        return vals
    
    def button_cancel(self, cr, uid, ids, context=None):
        vals = super(bank_statement,self).button_confirm_bank(cr,uid,ids,context=None)
        self.write(cr,uid,ids,{'cancel_uid':uid,'cancel_date':datetime.now()})
        return vals  
      
    def button_confirm_cash(self, cr, uid, ids, context=None): 
        vals = super(bank_statement,self).button_confirm_cash(cr,uid,ids,context=None)
        self.write(cr,uid,ids,{'date':self._get_default_date(cr, uid, context=context),'confirm_uid':uid,'confirm_date':datetime.now()})
        return vals            