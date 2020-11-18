import time
from operator import attrgetter
from openerp.osv import fields, osv
from datetime import date, datetime, timedelta



class purchase_order(osv.osv):
    _inherit = 'purchase.order'
    _columns = {
                'state': fields.selection([('draft', 'Draft PO'), ('sent', 'RFQ'), ('bid', 'Bid Received'), ('confirmed', 'Waiting Approval'),
                                           ('approved', 'Purchase Confirmed'), ('except_picking', 'Shipping Exception'), ('except_invoice', 'Invoice Exception'),
                                           ('done', 'Done'), ('close', 'Close'), ('cancel', 'Cancelled')], 'Status', readonly=True, select=True, copy=False),
    }
    
    def action_close(self, cr, uid, ids, context=None):
        for purchase in self.browse(cr, uid, ids, context=context):
            for pick in purchase.picking_ids:
                if pick.state != 'done':
                    self.pool.get('stock.picking').action_cancel(cr, uid, [pick.id], context=context)
        self.write(cr, uid, ids, {'state': 'close'}, context=context)
        self.set_order_line_status(cr, uid, ids, 'cancel', context=context)
        
        return True
