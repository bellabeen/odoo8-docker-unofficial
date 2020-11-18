import time
import pytz
from openerp import SUPERUSER_ID
from datetime import datetime
from dateutil.relativedelta import relativedelta

from openerp.osv import fields, osv
from openerp import netsvc
from openerp import pooler
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.osv.orm import browse_record, browse_null
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP


class wtc_purchase_requisition(osv.osv):
    _inherit="purchase.requisition"
    
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
        
    def _get_default_date(self,cr,uid,context=None):
        return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)
            
    _columns={
              'branch_id':fields.many2one('wtc.branch','Branch'),
              'division':fields.selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum')], 'Division', change_default=True, select=True),
              'department_id':fields.many2one('hr.department','Department'),
              'date':fields.date('Date'),
              'confirm_uid':fields.many2one('res.users',string="Confirmed by"),
              'confirm_date':fields.datetime('Confirmed on'),
              'cancel_uid':fields.many2one('res.users',string="Cancelled by"),
              'cancel_date':fields.datetime('Cancelled on'),              
              }
           
    _defaults = {
                'name': '/',
                'branch_id': _get_default_branch,
                'date':_get_default_date
    }

    def create(self, cr, uid, vals, context=None):
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'PR')
        vals['date'] = self._get_default_date(cr, uid, context) 
        return super(wtc_purchase_requisition, self).create(cr, uid, vals, context=context)
    
    def tender_open(self, cr, uid, ids, context=None):
        obj_me = self.browse(cr, uid, ids)
        if not obj_me.purchase_ids :
            raise osv.except_osv(_('Perhatian !'), _('Tidak bisa diclose, Anda belum membuat RFQ !'))
        return self.write(cr, uid, ids, {'state': 'open'}, context=context)
    
    def _prepare_purchase_order(self, cr, uid, requisition, supplier, type_id, start, end, context=None):
        if requisition.division == 'Unit' :
            if not requisition.branch_id.pricelist_unit_purchase_id :
                raise osv.except_osv(_('Perhatian !'), _('Silahkan setting Pricelist Beli Unit di Branch terlebih dahulu !'))
            else :
                pricelist = requisition.branch_id.pricelist_unit_purchase_id.id
        else :
            if not requisition.branch_id.pricelist_part_purchase_id :
                raise osv.except_osv(_('Perhatian !'), _('Silahkan setting Pricelist Beli Sparepart di Branch terlebih dahulu !'))
            else :
                pricelist = requisition.branch_id.pricelist_part_purchase_id.id
        picking_type_in = self.pool.get("purchase.order")._get_picking_in(cr, uid, context=context)
        payment_term = False
        if supplier.property_supplier_payment_term:
            payment_term = supplier.property_supplier_payment_term.id
        return {
            'origin': requisition.name,
            'date_order': requisition.date_end or self._get_default_date(cr, uid, context),
            'partner_id': supplier.id,
            'pricelist_id': pricelist,
            'location_id': requisition.picking_type_id.default_location_dest_id.id,
            'company_id': requisition.company_id.id,
            'fiscal_position': supplier.property_account_position and supplier.property_account_position.id or False,
            'requisition_id': requisition.id,
            'notes': requisition.description,
            'picking_type_id': picking_type_in,
            'branch_id': requisition.branch_id.id,
            'division' : requisition.division,
            'purchase_order_type_id': type_id,
            'start_date': start,
            'end_date': end,
            'payment_term_id' : payment_term,
        }

    def _prepare_purchase_order_line(self, cr, uid, requisition, requisition_line, purchase_id, supplier, context=None):
        if context is None:
            context = {}
        po_line_obj = self.pool.get('purchase.order.line')
        product_uom = self.pool.get('product.uom')
        product = requisition_line.product_id
        categ = requisition_line.categ_id 
        default_uom_po_id = product.uom_po_id.id
        ctx = context.copy()
        ctx['tz'] = requisition.user_id.tz
        date_order = requisition.ordering_date and fields.date.date_to_datetime(self, cr, uid, requisition.ordering_date, context=ctx) or self._get_default_date(cr, uid, context=ctx)
        qty = product_uom._compute_qty(cr, uid, requisition_line.product_uom_id.id, requisition_line.product_qty, default_uom_po_id)
        if requisition.division == 'Unit' :
            if not requisition.branch_id.pricelist_unit_purchase_id :
                raise osv.except_osv(_('Perhatian !'), _('Silahkan setting Pricelist Beli Unit di Branch terlebih dahulu !'))
            else :
                pricelist = requisition.branch_id.pricelist_unit_purchase_id.id
        elif requisition.division == 'Sparepart' : 
            if not requisition.branch_id.pricelist_part_purchase_id :
                raise osv.except_osv(_('Perhatian !'), _('Silahkan setting Pricelist Beli Sparepart di Branch terlebih dahulu !'))
            else :
                pricelist = requisition.branch_id.pricelist_part_purchase_id.id
        else :
            if not supplier.property_product_pricelist_purchase :
                raise osv.except_osv(_('Perhatian !'), _('Silahkan setting Purchae Pricelist Beli dalam supplier %s !')%(supplier.name))
            else :
                pricelist = supplier.property_product_pricelist_purchase.id        
        vals = po_line_obj.onchange_product_id(
            cr, uid, [], pricelist, product.id, qty, default_uom_po_id,
            supplier.id, date_order=date_order,
            fiscal_position_id=supplier.property_account_position,
            date_planned=requisition_line.schedule_date,
            name=False, price_unit=False, state='draft', context=context)['value']
        vals.update({
            'order_id': purchase_id,
            'product_id': product.id,
            'categ_id': categ.id,
            'account_analytic_id': requisition_line.account_analytic_id.id,
        })
        return vals
    
    def make_purchase_order(self, cr, uid, ids, partner_id, type_id, start, end, context=None):
        """
        Create New RFQ for Supplier
        """
        context = dict(context or {})
        assert partner_id, 'Supplier should be specified'
        purchase_order = self.pool.get('purchase.order')
        purchase_order_line = self.pool.get('purchase.order.line')
        res_partner = self.pool.get('res.partner')
        supplier = res_partner.browse(cr, uid, partner_id, context=context)
        res = {}
        for requisition in self.browse(cr, uid, ids, context=context):
            if not requisition.multiple_rfq_per_supplier and supplier.id in filter(lambda x: x, [rfq.state != 'cancel' and rfq.partner_id.id or None for rfq in requisition.purchase_ids]):
                raise osv.except_osv(_('Warning!'), _('You have already one %s purchase order for this partner, you must cancel this purchase order to create a new quotation.') % rfq.state)
            context.update({'mail_create_nolog': True})
            purchase_id = purchase_order.create(cr, uid, self._prepare_purchase_order(cr, uid, requisition, supplier, type_id, start, end, context=context), context=context)
            purchase_order.message_post(cr, uid, [purchase_id], body=_("RFQ created"), context=context)
            res[requisition.id] = purchase_id
            for line in requisition.line_ids:
                purchase_order_line.create(cr, uid, self._prepare_purchase_order_line(cr, uid, requisition, line, purchase_id, supplier, context=context), context=context)
        return res

    def tender_in_progress(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'date':self._get_default_date(cr, uid, context),'state': 'in_progress','confirm_uid':uid,'confirm_date':datetime.now()}, context=context)

    def tender_cancel(self, cr, uid, ids, context=None):
        vals = super(wtc_purchase_requisition, self).tender_cancel(cr, uid, ids, context=context)
        self.write(cr, uid, ids, {'cancel_uid':uid,'cancel_date':datetime.now()})
        return vals
        
class wtc_purchase_requisition_line(osv.osv):
    _inherit = 'purchase.requisition.line'
    _columns = {
                'categ_id':fields.many2one('product.category','Category',required=True),
                }
    
    _sql_constraints = [('product_id_unique', 'unique(requisition_id,product_id)', 'Tidak boleh ada product yg sama dalam satu transaksi !')]
    
    def category_change(self, cr, uid, ids, categ_id, branch_id, division):
        if not branch_id or not division:
            raise osv.except_osv(('No Branch Defined!'), ('Sebelum menambah detil transaksi,\n harap isi branch dan division terlebih dahulu.'))
        dom = {}
        if categ_id:
            categ_ids = self.pool.get('product.category').get_child_by_ids(cr,uid,categ_id)
            dom['product_id']=[('categ_id','in',categ_ids)]
        return {'domain':dom}
    
class wtc_purchase_requisition_partner(osv.osv_memory):
    _inherit = 'purchase.requisition.partner'
    _columns = {
                'division':fields.selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum')], 'Division', change_default=True, select=True, required=True),
                'purchase_order_type_id':fields.many2one('wtc.purchase.order.type','Type',required=True),
                'start_date':fields.date('Start Date'),
                'end_date':fields.date('End Date')
                }
    
    def _get_division(self, cr, uid, context=None):
        active_ids = context and context.get('active_ids', [])
        if active_ids :
            pr = self.pool.get('purchase.requisition').browse(cr, uid, active_ids)
            return pr.division
        return False
    
    _defaults = {
                 'division':_get_division,
                 }
    
    def purchase_order_type_id_change(self, cr, uid, ids, purchase_order_type_id):
        po_type = self.pool.get('wtc.purchase.order.type').browse(cr, uid, purchase_order_type_id)
        res={}
        res['start_date']=False
        res['end_date']=False
        if po_type:
            res['start_date'] = po_type.get_date(po_type.date_start)
            res['end_date'] = po_type.get_date(po_type.date_end)
        return {'value':res}
    
    def onchange_division(self, cr, uid, vals, division):
        res={}
        res['purchase_order_type_id']=False
        return {'value':res}
    
    def create_order(self, cr, uid, ids, context=None):
        active_ids = context and context.get('active_ids', [])
        data = self.browse(cr, uid, ids, context=context)[0]
        self.pool.get('purchase.requisition').make_purchase_order(cr, uid, active_ids, data.partner_id.id, data.purchase_order_type_id.id, data.start_date, data.end_date, context=context)
        return {'type': 'ir.actions.act_window_close'}
    