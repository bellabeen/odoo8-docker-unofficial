import time
from datetime import datetime
from openerp.osv import fields, osv
  
class wtc_questionnaire(osv.osv):
    _name = 'wtc.questionnaire'

    _columns = {
                'type' : fields.char('Type'),
                'name' : fields.char('Question'),
                'value' : fields.char('Value'),
                'position' : fields.integer('Position'),

    }
        
    def unlink(self, cr, uid, ids, context=None):
        if ids :
                raise osv.except_osv(('Perhatian !'), ("Master Questionnaire tidak bisa didelete !"))
        return super(wtc_questionnaire, self).unlink(cr, uid, ids, context=context)