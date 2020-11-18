import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp import netsvc

class wtc_purchase_order(osv.osv):
    _inherit = "purchase.order"
    STATE_SELECTION = [
        ('draft', 'Draft PO'),
        ('waiting_for_approval','Waiting Approval'),
        ('sent', 'RFQ'),
        ('bid', 'Bid Received'),
        ('confirmed', 'Waiting Approval'),
        ('approved', 'Purchase Confirmed'),
        ('except_picking', 'Shipping Exception'),
        ('except_invoice', 'Invoice Exception'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
        ('close', 'Close')
    ]
    _columns = {
                'approval_ids': fields.one2many('wtc.approval.line','transaction_id',string="Table Approval",domain=[('form_id','=',_inherit)]),
                'approval_state': fields.selection([('b','Belum Request'),('rf','Request For Approval'),('a','Approved'),('r','Reject')],'Approval State', readonly=True),
                'partner_ref': fields.char('Supplier Reference', states={'waiting_for_approval':[('readonly',True)],'confirmed':[('readonly',True)],'approved':[('readonly',True)],'done':[('readonly',True)]}, copy=False, ),
                'date_order':fields.datetime('Order Date', required=True, states={'waiting_for_approval':[('readonly',True)],'confirmed':[('readonly',True)],'approved':[('readonly',True)]}, select=True,copy=False),
                'partner_id':fields.many2one('res.partner', 'Supplier', required=True, states={'waiting_for_approval':[('readonly',True)],'confirmed':[('readonly',True)], 'approved':[('readonly',True)],'done':[('readonly',True)]},change_default=True, track_visibility='always'),
                'dest_address_id':fields.many2one('res.partner', 'Customer Address (Direct Delivery)',states={'waiting_for_approval':[('readonly',True)],'confirmed':[('readonly',True)], 'approved':[('readonly',True)],'done':[('readonly',True)]}, ),
                'location_id': fields.many2one('stock.location', 'Destination', required=True, domain=[('usage','<>','view')], states={'waiting_for_approval':[('readonly',True)],'confirmed':[('readonly',True)], 'approved':[('readonly',True)],'done':[('readonly',True)]} ),
                'pricelist_id':fields.many2one('product.pricelist', 'Pricelist', required=True, states={'waiting_for_approval':[('readonly',True)],'confirmed':[('readonly',True)], 'approved':[('readonly',True)],'done':[('readonly',True)]}, help="The pricelist sets the currency used for this purchase order. It also computes the supplier price for the selected products/quantities."),
                'currency_id': fields.many2one('res.currency','Currency', readonly=True, required=True,states={'waiting_for_approval':[('readonly',True)],'draft': [('readonly', False)],'sent': [('readonly', False)]}),
                'company_id': fields.many2one('res.company', 'Company', required=True, select=1, states={'waiting_for_approval':[('readonly',True)],'confirmed': [('readonly', True)], 'approved': [('readonly', True)]}),
                'picking_type_id': fields.many2one('stock.picking.type', 'Deliver To', required=True,states={'waiting_for_approval':[('readonly',True)],'confirmed': [('readonly', True)], 'approved': [('readonly', True)], 'done': [('readonly', True)]}),
                'state': fields.selection(STATE_SELECTION, 'Status', readonly=True, select=True, copy=False),
                'order_line': fields.one2many('purchase.order.line', 'order_id', 'Order Lines',states={'waiting_for_approval':[('readonly',True)],'approved':[('readonly',True)], 'done':[('readonly',True)]},copy=True),   
    }
    
    _defaults ={
                'approval_state':'b'
                }
    
    def wkf_request_approval(self, cr, uid, ids, context=None):
        obj_po = self.browse(cr, uid, ids, context=context)
        obj_matrix = self.pool.get("wtc.approval.matrixbiaya")
        if not obj_po.order_line:
            raise osv.except_osv(('Perhatian !'), ("Produk belum diisi"))
        for line in obj_po.order_line :
            if line.price_unit < 1 :
                raise osv.except_osv(('Perhatian !'), ("Unit Price Product '%s' tidak boleh '%s'" %(line.product_id.name,line.price_unit)))
        obj_matrix.request(cr, uid, ids, obj_po, 'amount_total')
        self.write(cr, uid, ids, {'state': 'waiting_for_approval','approval_state':'rf'})
        return True
        
    def wkf_approval(self, cr, uid, ids, context=None):
        obj_po = self.browse(cr, uid, ids, context=context)
        if not obj_po.order_line:
            raise osv.except_osv(('Perhatian !'), ("Produk belum diisi"))
        approval_sts = self.pool.get("wtc.approval.matrixbiaya").approve(cr, uid, ids, obj_po)
        if approval_sts == 1:
            self.write(cr, uid, ids, {'approval_state':'a'})
        elif approval_sts == 0:
            raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group approval"))
   
        return True

    def has_approved(self, cr, uid, ids, *args):
        obj_po = self.browse(cr, uid, ids)
        return obj_po.approval_state == 'a'

    def has_rejected(self, cr, uid, ids, *args):
        obj_po = self.browse(cr, uid, ids)
        if obj_po.approval_state == 'r':
            self.write(cr, uid, ids, {'state':'draft'})
            return True
        return False

    def wkf_set_to_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'r'})
        
    def wkf_set_to_draft_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'b'})        
