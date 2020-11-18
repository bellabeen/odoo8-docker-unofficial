import time
from openerp import SUPERUSER_ID, workflow
from openerp.osv import fields, osv
from openerp.tools.translate import _
from datetime import datetime, timedelta
import openerp.addons.decimal_precision as dp
from dateutil.relativedelta import relativedelta

class wtc_mutation_order(osv.osv):
    _name = "wtc.mutation.order"
    _description = "Mutation Order"
    _order = 'date desc'
    
    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('wtc.mutation.order.line').browse(cr, uid, ids, context=context):
            result[line.order_id.id] = True
        return result.keys()
    
    def _compute_amount(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                             'amount_total': 0.0,
                             }
            val = 0.0
            for line in order.order_line :
                val += line.sub_total
            res[order.id] = {
                             'amount_total': val
                             }
        return res

    def _get_picking_ids(self, cr, uid, ids, field_names, args, context=None):
        res = {}
        for po_id in ids:
            res[po_id] = []
        query = """
        SELECT p.id, po.id FROM stock_picking p, wtc_mutation_order po
            WHERE po.id in %s and p.origin = po.name
            GROUP BY p.id, po.id
        """
        cr.execute(query, (tuple(ids), ))
        picks = cr.fetchall()
        for pick_id, po_id in picks:
            res[po_id].append(pick_id)
        return res

    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
        
    def _get_default_date(self,cr,uid,context=None):
        return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)
            
    _columns = {
                'name' : fields.char('Mutation Order'),
                'state' : fields.selection([
                                          ('draft','Draft'),
                                          ('confirm','Confirmed'),
                                          ('done','Done'),
                                          ('cancelled','Cancelled'),
                                          ], 'State'),
                'date' : fields.date('Date'),
                'branch_id' : fields.many2one('wtc.branch', 'Branch Sender'),
                'branch_requester_id' : fields.many2one('wtc.branch', 'Branch Requester'),
                'division' : fields.selection([
                                             ('Unit','Unit'),
                                             ('Sparepart','Sparepart'),
                                             ('Umum','Umum')
                                             ], 'Division'),
                'user_id' : fields.many2one('res.users', 'Responsible'),
                'description' : fields.text('Description'),
                'order_line' : fields.one2many('wtc.mutation.order.line', 'order_id', 'Mutation Line'),
                'amount_total' : fields.function(_compute_amount, string='Total', digits_compute=dp.get_precision('Account'),
                                                 store={
                                                        'wtc.mutation.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                                                        'wtc.mutation.order.line': (_get_order, ['unit_price', 'qty', 'subtotal'], 10),
                                                        },
                                                 multi='sums', help="The total amount."),
                'start_date' : fields.date('Start Date'),
                'end_date' : fields.date('End Date'),
                'distribution_id' : fields.many2one('wtc.stock.distribution', 'Stock Distribution', required=True, ondelete='restrict'),
                'picking_ids': fields.function(_get_picking_ids, method=True, type='one2many', relation='stock.picking', string='Picking List'),
                'confirm_uid':fields.many2one('res.users',string="Confirmed by", copy=False),
                'confirm_date':fields.datetime('Confirmed on', copy=False),
                'cancelled_uid':fields.many2one('res.users', string="Cancelled by", copy=False),
                'cancelled_date':fields.datetime('Cancelled on', copy=False),
                'location_id': fields.many2one('stock.location','Location',domain="[('branch_id','=',branch_id),('usage','=','internal')]")
                }
    
    _defaults = {
        'branch_id': _get_default_branch,
        'date':_get_default_date
    }    
    
    def create(self, cr, uid, vals, context=None):
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'MO')
        vals['date'] = self._get_default_date(cr, uid, context)
        return super(wtc_mutation_order, self).create(cr, uid, vals, context=context)
    
    def _prepare_order_line_move(self, cr, uid, order, order_line, picking_id, context=None):
        res = []
        undelivered_value = 0
        warehouse = self.pool.get('wtc.branch').browse(cr, uid, order.branch_id.id).warehouse_id
        if warehouse :
            picking_type_id = warehouse.interbranch_out_type_id.id
            if warehouse.interbranch_out_type_id.branch_id == order.branch_id :
                if warehouse.interbranch_out_type_id.default_location_dest_id.usage == 'transit' :
                    if order.location_id and order.division=='Sparepart':
                        location_id = order.location_id.id
                    else:
                        location_id = warehouse.interbranch_out_type_id.default_location_src_id.id
                    location_dest_id = warehouse.interbranch_out_type_id.default_location_dest_id.id
                else :
                    raise osv.except_osv(('Perhatian !'), ("Type destinaton location '%s' bukan 'Transit Location'" %warehouse.interbranch_out_type_id.default_location_dest_id.name))
            else :
                raise osv.except_osv(('Perhatian !'), ("Type picking '%s' bukan untuk branch '%s'" %(warehouse.interbranch_out_type_id.name,order.branch_id.name)))
        else :
            raise osv.except_osv(('Perhatian !'), ("Silahkan setting warehouse untuk branch '%s' terlebih dahulu" %order.branch_id.name))
        
        if order_line.product_id.cost_method == 'average':
            obj_product_price = self.pool.get('product.price.branch')
            undelivered_value = obj_product_price._get_price(cr, uid, warehouse.id, order_line.product_id.id)
            
        move_template = {
            'name': order_line.description or '',
            'product_id': order_line.product_id.id,
            'product_uom': order_line.product_id.uom_id.id,
            'product_uos': order_line.product_id.uom_id.id,
            'product_uom_qty': order_line.qty,
            'product_uos_qty': order_line.qty,
            'date':self._get_default_date(cr, uid, context),
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'picking_id': picking_id,
            'move_dest_id': False,
            'state': 'draft',
            'price_unit': order_line.unit_price,
            'picking_type_id': picking_type_id,
            'procurement_id': False,
            'origin': order.name,
            'warehouse_id': warehouse.id,
            'branch_id': order.branch_id.id,
            'categ_id': order_line.product_id.categ_id.id,
            'undelivered_value': undelivered_value
        }
        res.append(move_template)
        return res
    
    def _create_stock_moves(self, cr, uid, order, order_lines, picking_id=False, context=None):
        stock_move = self.pool.get('stock.move')
        todo_moves = []

        for order_line in order_lines:
            if not order_line.product_id:
                continue

            if order_line.product_id.type in ('product', 'consu'):
                for vals in self._prepare_order_line_move(cr, uid, order, order_line, picking_id, context=context):
                    if vals['product_uom_qty'] > 0 :
                        move = stock_move.create(cr, uid, vals, context=context)
                        todo_moves.append(move)
        stock_move.action_confirm(cr, uid, todo_moves)
        
    def action_picking_create(self, cr, uid, ids, context=None):
        obj_me = self.browse(cr, uid, ids)
        obj_picking = self.pool.get('stock.picking')
        obj_partner = self.pool.get('res.partner')
        ids_partner = obj_partner.search(cr, SUPERUSER_ID, [('branch_id','=',obj_me.sudo().branch_requester_id.id),('default_code','=',obj_me.sudo().branch_requester_id.code)])
        id_partner = False
        if ids_partner :
            id_partner = ids_partner[0]
        warehouse = self.pool.get('wtc.branch').browse(cr, uid, obj_me.branch_id.id).warehouse_id
        if warehouse :
            picking_type_id = warehouse.interbranch_out_type_id.id
        else :
            raise osv.except_osv(('Perhatian !'), ("Silahkan setting warehouse untuk branch '%s' terlebih dahulu" %obj_me.branch_id.name))
        for order in obj_me :
            picking_vals = {
                'branch_id': order.branch_id.id,
                'division': order.division,
                'date': order.date,
                'partner_id': id_partner,
                'start_date': order.start_date,
                'end_date': order.end_date,
                'origin': order.name,
                'transaction_id': order.id,
                'model_id': self.pool.get('ir.model').search(cr, uid, [('model','=',order.__class__.__name__)])[0],
                'picking_type_id': picking_type_id,
                'min_date': order.end_date
            }
            picking_id = obj_picking.create(cr, uid, picking_vals, context=context)
            self._create_stock_moves(cr, uid, order, order.order_line, picking_id, context=context)
            obj_picking.force_assign(cr, uid, [picking_id])
        
    def _write_performance_hpp(self, cr, uid, ids, context=None):
        mutation_order_id = self.browse(cr, uid, ids, context=context)
        if mutation_order_id.division == 'Unit' and mutation_order_id.branch_id.branch_type == 'MD' :
            pricelist_unit_sales_id = mutation_order_id.branch_id.pricelist_unit_sales_id
            if not pricelist_unit_sales_id :
                raise osv.except_osv(('Perhatian !'), ("Silahkan isi Price List Jual Unit untuk Main Dealer !"))
            for mo_line in mutation_order_id.order_line :
                price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist_unit_sales_id.id], mo_line.product_id.id, 1,0)[pricelist_unit_sales_id.id]
                mo_line.write({'performance_hpp': price})
                if mo_line.performance_hpp < 1 :
                    raise osv.except_osv(('Perhatian !'), ("Silahkan setting Harga untuk product '%s' di Pricelist '%s' !" %(mo_line.product_id.name,pricelist_unit_sales_id.name)))
        return True
        
    def get_stock_available(self, cr, uid, ids, id_product, id_branch, context=None):
        obj_location = self.pool.get('stock.location')
        ids_location = obj_location.search(cr, uid, [('branch_id','=',id_branch),('usage','=','internal')])
        cr.execute("""
        SELECT
            COALESCE(SUM(q.qty),0) as quantity
        FROM
            stock_quant q
        LEFT JOIN
            stock_production_lot l on l.id = q.lot_id
        WHERE
            q.product_id = %s and q.location_id in %s and q.reservation_id is Null and q.consolidated_date is not Null
            and (q.lot_id is Null or l.state = 'stock')
        """,(id_product,tuple(ids_location)))
        return cr.fetchall()[0][0]
    
    def renew_available(self, cr, uid, ids, context=None):
        obj_me = self.browse(cr, uid, ids, context=context)
        for mo_line in obj_me.order_line :
            qty_available = self.get_stock_available(cr, uid, ids, mo_line.product_id.id, obj_me.branch_id.id, context=context)
            if obj_me.division == 'Sparepart':
                obj_picking = self.pool.get('stock.picking')
                qty_available = obj_picking._get_qty_quant(cr, uid, obj_me.branch_id.id, mo_line.product_id.id) - (obj_picking._get_qty_picking(cr, uid, obj_me.branch_id.id, obj_me.division, mo_line.product_id.id) + obj_picking._get_qty_rfa_approved(cr, uid, obj_me.branch_id.id, obj_me.division, mo_line.product_id.id))
            mo_line.write({'qty_available':qty_available})
    
    def confirm(self, cr, uid, ids, context=None):
        obj_picking = self.pool.get('stock.picking')
        self.write(cr, uid, ids, {'confirm_uid':uid,'confirm_date':datetime.now(),'date':self._get_default_date(cr, uid, context)})        
        self.renew_available(cr, uid, ids, context)
        self._write_performance_hpp(cr, uid, ids, context)
        qty = {}
        approved_qty = {}
        obj_me = self.browse(cr, uid, ids, context=context)
        if obj_me.state == 'draft' :
            for x in obj_me.order_line :
                if obj_me.division == 'Sparepart':
                    obj_picking.compare_sale_rfa_approved_stock(cr, uid, obj_me.branch_id.id, obj_me.division, x.product_id.id, x.qty)
                else:
                    obj_picking.compare_sale_stock(cr, uid, obj_me.branch_id.id, obj_me.division, x.product_id.id, x.qty)
                if x.qty > x.qty_available :
                    raise osv.except_osv(('Perhatian !'), ("Quantity tidak boleh melebihi qty available,\n qty available mungkin telah berubah silahkan Renew Available !"))
                qty[x.product_id] = qty.get(x.product_id,0) + x.qty
            for x in obj_me.distribution_id.distribution_line :
                qty[x.product_id] = qty.get(x.product_id,0) + x.qty
                approved_qty[x.product_id] = approved_qty.get(x.product_id,0) + x.approved_qty
                if (approved_qty[x.product_id] - qty[x.product_id]) >= 0 :
                    x.write({'qty':qty[x.product_id]})
                else :
                    raise osv.except_osv(('Perhatian !'), ("Quantity melebihi Approved Qty"))
            self.write(cr, uid, ids, {'state':'confirm'})
            self.action_picking_create(cr, uid, ids, context)
        return True
        
    def view_picking(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        mod_obj = self.pool.get('ir.model.data')
        dummy, action_id = tuple(mod_obj.get_object_reference(cr, uid, 'stock', 'action_picking_tree'))
        action = self.pool.get('ir.actions.act_window').read(cr, uid, action_id, context=context)
        pick_ids = []
        mutation_order_id = self.browse(cr, uid, ids, context=context)
        for picking in self.pool.get('stock.picking').search(cr, SUPERUSER_ID, [
                                                                                ('origin','=',str(mutation_order_id.name)),
                                                                                ('picking_type_code','=','interbranch_out'),
                                                                                ]):
            pick_ids.append(picking)
        action['context'] = {}
        if len(pick_ids) > 1:
            action['domain'] = "[('id','in',[" + ','.join(map(str, pick_ids)) + "])]"
        else:
            res = mod_obj.get_object_reference(cr, uid, 'stock', 'view_picking_form')
            action['views'] = [(res and res[1] or False, 'form')]
            action['res_id'] = pick_ids and pick_ids[0] or False 
        return action
    
    def is_done(self, cr, uid, ids, context=None):
        obj_me = self.browse(cr, uid, ids, context=context)
        qty = 0
        supply_qty = 0
        for x in obj_me.order_line :
            qty += x.qty
            supply_qty += x.supply_qty
        if qty - supply_qty == 0 :
            obj_me.write({'state':'done'})
        obj_me.distribution_id.is_done()
        return True
    
    def unlink(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids, context={})[0]
        if val.state != 'draft':
            raise osv.except_osv(('Invalid action !'), ('Cannot delete a Mutation Order which is in state \'%s\'!') % (val.state))
        return super(wtc_mutation_order, self).unlink(cr, uid, ids, context=context)
    
    def _get_ids_picking(self, cr, uid, ids, context=None):
        mo_id = self.browse(cr, uid, ids, context=context)
        obj_picking = self.pool.get('stock.picking')
        obj_model = self.pool.get('ir.model')
        id_model = obj_model.search(cr, uid, [('model','=',mo_id.__class__.__name__)])[0]
        ids_picking = obj_picking.search(cr, uid, [
            ('model_id','=',id_model),
            ('transaction_id','=',mo_id.id),
            ('state','!=','cancel')
            ])
        return ids_picking
    
    def action_cancel(self, cr, uid, ids, context=None):
        mo_id = self.browse(cr, uid, ids, context=None)
        self.write(cr, uid, ids, {'state':'cancelled','cancelled_uid':uid,'cancelled_date':datetime.now()})
        product_qty = {}
        for mo_line in mo_id.order_line :
            product_qty[mo_line.product_id] = product_qty.get(mo_line.product_id,0) + mo_line.qty
        for sd_line in mo_id.distribution_id.distribution_line :
            sd_line.write({'qty':sd_line.qty - product_qty[sd_line.product_id] if sd_line.product_id in product_qty else 0})
    
class wtc_mutation_order_line(osv.osv):
    _name = "wtc.mutation.order.line"
    
    def _get_price(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for price in self.browse(cr, uid, ids, context=context):
            unit_price_show=price.unit_price
            res[price.id]=unit_price_show
        return res
    
    def _compute_price(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        sub_total = 0
        for line in self.browse(cr, uid, ids, context=context):
            sub_total = line.qty * line.unit_price
            res[line.id] = sub_total
        return res
    
    _columns = {
                'order_id' : fields.many2one('wtc.mutation.order', 'Mutation'),
                'product_id' : fields.many2one('product.product', 'Product'),
                'description' : fields.text('Description'),
                'qty' : fields.float('Qty', digits=(10,0)),
                'qty_available' : fields.float('Qty Available', digits=(10,0)),
                'supply_qty' : fields.float('Supply Qty', digits=(10,0)),
                'unit_price' : fields.float('Unit Price'),
                'unit_price_show' : fields.function(_get_price, string='Unit Price'),
                'sub_total': fields.function(_compute_price, string='Subtotal', digits_compute=dp.get_precision('Account')),
                'rel_state' : fields.related('order_id', 'state', string='State', type='selection', selection=[('draft','Draft'), ('confirm','Confirmed'), ('done','Done')]),
                'rel_distribution_id' : fields.related('order_id', 'distribution_id', string='Stock Distribution', type='many2one', relation='wtc.stock.distribution'),
                'performance_hpp': fields.float('Performance HPP', digits=(10,0)),
                }
    
    def qty_change(self, cr, uid, ids, qty, product_id, distribution, context=None):
        warning = {}
        value = {}
        quantity = {}
        distribution_id = self.pool.get('wtc.stock.distribution').browse(cr, uid, distribution)
        obj_me = self.browse(cr, uid, ids, context=context)
        for x in distribution_id.distribution_line :
            if product_id == x.product_id.id :
                quantity[x.product_id] = quantity.get(x.product_id,0) + (x.approved_qty - x.qty - qty)
                if qty < 0 :
                    value = {'qty': 0}
                    warning = {'title':'Perhatian !', 'message':'Quantity tidak boleh kurang dari nol'}
                elif qty > obj_me.qty_available :
                    value = {'qty': 0}
                    warning = {'title':'Perhatian !', 'message':'Quantity tidak boleh melebihi qty available'}
                elif quantity[x.product_id] < 0 :
                    value = {'qty': 0}
                    approved_qty = x.approved_qty - x.qty
                    warning = {'title':'Perhatian !', 'message':"Quantity tidak boleh lebih dari approved qty '%s'" %approved_qty}
        return {'value':value, 'warning':warning}
