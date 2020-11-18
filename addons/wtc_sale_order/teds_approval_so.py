import time
from datetime import datetime
from openerp.osv import fields, osv

class wtc_purchase_order(osv.osv):
    _inherit = 'sale.order'

    # ('draft', 'Draft PO'),
    # ('waiting_for_approval','Waiting Approval'),
    # ('sent', 'RFQ'),
    # ('bid', 'Bid Received'),
    # ('confirmed', 'Waiting Approval'),
    # ('approved', 'Purchase Confirmed'),
    # ('except_picking', 'Shipping Exception'),
    # ('except_invoice', 'Invoice Exception'),
    # ('done', 'Done'),
    # ('cancel', 'Cancelled'),
    # ('close', 'Close')

    STATE_SELECTION = [
        ('draft', 'Draft Quotation'),
        ('waiting_for_approval','Waiting Approval'),
        ('sent', 'Quotation Sent'),
        ('cancel', 'Cancelled'),
        ('approved', 'Approved'),
        ('waiting_date', 'Waiting Schedule'),
        ('progress', 'Sales Order'),
        ('manual', 'Sale to Invoice'),
        ('shipping_except', 'Shipping Exception'),
        ('invoice_except', 'Invoice Exception'),
        ('done', 'Done'),
    ]
    _columns = {
        'state': fields.selection(STATE_SELECTION, 'Status', readonly=True, select=True, copy=False),
        'approval_ids': fields.one2many('wtc.approval.line','transaction_id',string="Table Approval",domain=[('form_id','=',_inherit)]),
        'approval_state': fields.selection([('b','Belum Request'),('rf','Request For Approval'),('a','Approved'),('r','Reject')],'Approval State', readonly=True),
        'amount_approval': fields.float('Amount Approval', readonly=True)
    }

    def wkf_request_approval(self, cr, uid, ids, context=None):
        obj_po = self.browse(cr, uid, ids, context=context)
        obj_matrix = self.pool.get("wtc.approval.matrixbiaya")
        obj_picking = self.pool.get("stock.picking")
        if not obj_po.order_line:
            raise osv.except_osv(('Perhatian!'), ("Produk belum diisi"))
        amount = 0
        value = 0
        for line in obj_po.order_line :
            if line.price_unit < 1 :
                raise osv.except_osv(('Perhatian !'), ("Unit Price Product '%s' tidak boleh '%s'" %(line.product_id.name,line.price_unit)))
            if obj_po.division=='Sparepart':
                obj_picking.compare_sale_rfa_approved_stock(cr, uid, obj_po.branch_id.id, obj_po.division, line.product_id.id, line.product_uom_qty)
                if line.force_cogs:
                    hpp_average = line.force_cogs
                else:
                    hpp_average = self.pool.get('product.price.branch')._get_price(cr,uid,line.order_id.warehouse_id.id,line.product_id.id)
                if line.product_uom_qty > 0:
                    bawah = ((line.price_unit/1.1)*line.product_uom_qty)-(hpp_average*line.product_uom_qty)
                    if bawah == 0:
                        bawah = 0.001
                    value = (1 - ((line.price_subtotal-(hpp_average*line.product_uom_qty))/(bawah)))*100
                    if amount<value:
                        amount=value
                    amount = round(amount, 2)
            elif obj_po.division=='Unit':
                value += line.product_uom_qty
                amount = value
        obj_matrix.request_by_value(cr, uid, ids, obj_po, amount)
        self.write(cr, uid, ids, {'state': 'waiting_for_approval','approval_state':'rf','amount_approval':amount})
        return True
        
    def wkf_approval(self, cr, uid, ids, context=None):
        obj_po = self.browse(cr, uid, ids, context=context)
        if not obj_po.order_line:
            raise osv.except_osv(('Perhatian !'), ("Produk belum diisi"))
        approval_sts = self.pool.get("wtc.approval.matrixbiaya").approve(cr, uid, ids, obj_po)
        # print ">>>>>>>>>>>>>>>>>>>>>>",approval_sts
        # wkwkwk
        if approval_sts == 1:
            self.write(cr, uid, ids, {'state': 'approved','approval_state':'a'})
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

    def wkf_reject(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'r'})
        
    def wkf_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'b'})

    def renew_available(self, cr, uid, ids, context=None):
        obj_picking = self.pool.get("stock.picking")
        obj_me = self.browse(cr, uid, ids, context=context)
        for so_line in obj_me.order_line:
            if obj_me.division == 'Sparepart':
                qty_available = obj_picking._get_qty_quant(cr, uid, obj_me.branch_id.id, so_line.product_id.id) - (obj_picking._get_qty_picking(cr, uid, obj_me.branch_id.id, obj_me.division, so_line.product_id.id) + obj_picking._get_qty_rfa_approved(cr, uid, obj_me.branch_id.id, obj_me.division, so_line.product_id.id))
            so_line.write({'qty_available': qty_available})