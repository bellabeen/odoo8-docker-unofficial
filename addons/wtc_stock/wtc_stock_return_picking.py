from __future__ import division
from openerp.osv import fields, osv
from openerp.tools.translate import _

class wtc_stock_return_picking(osv.osv_memory):
    _inherit = 'stock.return.picking'
    _columns = {
        'picking_id': fields.many2one('stock.picking', 'Picking')
        }
    
    def default_get(self, cr, uid, fields, context=None):
        """
         To get default values for the object.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param fields: List of fields for which we want default values
         @param context: A standard dictionary
         @return: A dictionary with default values for all field in ``fields``
        """
        result1 = []
        if context is None:
            context = {}
        res = super(wtc_stock_return_picking, self).default_get(cr, uid, fields, context=context)
        record_id = context and context.get('active_id', False) or False
        uom_obj = self.pool.get('product.uom')
        move_obj = self.pool.get('stock.move')
        pick_obj = self.pool.get('stock.picking')
        pick = pick_obj.browse(cr, uid, record_id, context=context)
        quant_obj = self.pool.get("stock.quant")
        chained_move_exist = False
        if pick:
            if pick.state != 'done':
                raise osv.except_osv(_('Warning!'), _("You may only return pickings that are Done!"))

            for move in pick.move_lines:
                if move.move_dest_id:
                    chained_move_exist = True
                #Sum the quants in that location that can be returned (they should have been moved by the moves that were included in the returned picking)
                lots = []
                qty = 0
                quant_search = quant_obj.search(cr, uid, [('product_id', '=', move.product_id.id), ('history_ids', 'in', move.id), ('qty', '>', 0.0), ('location_id', 'child_of', move.location_dest_id.id)], context=context)
                for quant in quant_obj.browse(cr, uid, quant_search, context=context):
                    lots.append(quant.lot_id.id)
                    if not quant.reservation_id or quant.reservation_id.origin_returned_move_id.id != move.id:
                        qty += quant.qty
                if move.product_id.categ_id.isParentName('Unit'):
                    for quantity in range(int(qty)):
                        result1.append({'product_id': move.product_id.id, 'quantity': 1, 'move_id': move.id, 'lot_id':lots[0]})
                        lots.remove(lots[0])
                else :
                    move_search = move_obj.search(cr, uid, [('origin_returned_move_id', '=', move.id), ('product_uom_qty', '>', 0.0), ('state', '=', 'done')], context=context)
                    for move_id in move_obj.browse(cr, uid, move_search, context=context):
                        qty -= move_id.product_uom_qty
                    if qty > 0 :
                        result1.append({'product_id': move.product_id.id, 'quantity': qty, 'move_id': move.id})

            if len(result1) == 0:
                raise osv.except_osv(_('Warning!'), _("No products to return (only lines in Done state and not fully returned yet can be returned)!"))
            if 'product_return_moves' in fields:
                res.update({'product_return_moves': result1, 'picking_id': record_id, 'invoice_state':'none'})
            if 'move_dest_exists' in fields:
                res.update({'move_dest_exists': chained_move_exist})
        return res
    
    def _check_quantity(self, cr, uid, ids, context=None):
        stock_return_id = self.browse(cr, uid, ids, context=context)
        obj_stock_move = self.pool.get('stock.move')
        return_qty = stock_return_id.picking_id.get_seharusnya()
        move_ids = stock_return_id.picking_id.get_ids_move()
        lots_reversed = []
        ids_move_reversed = stock_return_id.picking_id.get_ids_move_reversed()
        move_reversed_ids = obj_stock_move.browse(cr, uid, ids_move_reversed)
        #move line qty dikurang move line qty yg sudah direverse sebelumnya
        for move_id_reversed in move_reversed_ids :
            lots_reversed.append(move_id_reversed.restrict_lot_id.id)
            return_qty[move_id_reversed.product_id] = return_qty.get(move_id_reversed.product_id,0) - move_id_reversed.product_uom_qty
        #sisa move line qty yg sudah direverse dikurang current return qty
        for return_move in stock_return_id.product_return_moves :
            if return_move.product_id.categ_id.isParentName('Unit') and return_move.lot_id.id in lots_reversed :
                raise osv.except_osv(('Perhatian !'), ("Produk '%s' dengan serial number '%s' sudah di reverse sebelumnya" %(return_move.product_id.name,return_move.lot_id.name)))
            return_qty[return_move.product_id] = return_qty.get(return_move.product_id,0) - return_move.quantity
            if return_qty[return_move.product_id] < 0 :
                product_name = return_move.product_id.name
                if return_move.product_id.categ_id.isParentName('Unit') :
                    product_name = return_move.product_id.name + " warna " + return_move.product_id.attribute_value_ids.name
                raise osv.except_osv(('Perhatian !'), ("Quantity produk '%s' melebihi quantity yg ditransfer,\nproduk ini mungkin pernah di reverse sebelumnya" %product_name))
        return True
    
    def _create_returns(self, cr, uid, ids, context=None):
        self._check_quantity(cr, uid, ids, context)
        if context is None:
            context = {}
        record_id = context and context.get('active_id', False) or False
        move_obj = self.pool.get('stock.move')
        pick_obj = self.pool.get('stock.picking')
        uom_obj = self.pool.get('product.uom')
        data_obj = self.pool.get('stock.return.picking.line')
        pick = pick_obj.browse(cr, uid, record_id, context=context)
        data = self.read(cr, uid, ids[0], context=context)
        returned_lines = 0

        # Cancel assignment of existing chained assigned moves
        moves_to_unreserve = []
        for move in pick.move_lines:
            if move.move_dest_id :
                to_check_moves = [move.move_dest_id]
                while to_check_moves:
                    current_move = to_check_moves.pop()
                    if current_move.state not in ('done', 'cancel') and current_move.reserved_quant_ids:
                        moves_to_unreserve.append(current_move.id)
                    split_move_ids = move_obj.search(cr, uid, [('split_from', '=', current_move.id)], context=context)
                    if split_move_ids:
                        to_check_moves += move_obj.browse(cr, uid, split_move_ids, context=context)

        if moves_to_unreserve:
            move_obj.do_unreserve(cr, uid, moves_to_unreserve, context=context)
            #break the link between moves in order to be able to fix them later if needed
            move_obj.write(cr, uid, moves_to_unreserve, {'move_orig_ids': False}, context=context)

        #Create new picking for returned products
        pick_type_id = pick.picking_type_id.return_picking_type_id and pick.picking_type_id.return_picking_type_id.id or pick.picking_type_id.id
        new_picking = pick_obj.copy(cr, uid, pick.id, {
            'move_lines': [],
            'picking_type_id': pick_type_id,
            'state': 'draft',
            'origin': pick.name,
        }, context=context)

        for data_get in data_obj.browse(cr, uid, data['product_return_moves'], context=context):
            move = data_get.move_id
            if not move:
                raise osv.except_osv(_('Warning !'), _("You have manually created product lines, please delete them to proceed"))
            new_qty = data_get.quantity
            if new_qty:
                returned_lines += 1
                move_obj.copy(cr, uid, move.id, {
                    'product_id': data_get.product_id.id,
                    'product_uom_qty': new_qty,
                    'product_uos_qty': uom_obj._compute_qty(cr, uid, move.product_uom.id, new_qty, move.product_uos.id),
                    'picking_id': new_picking,
                    'state': 'draft',
                    'location_id': move.location_dest_id.id,
                    'location_dest_id': move.location_id.id,
                    'origin_returned_move_id': move.id,
                    'procure_method': 'make_to_stock',
                    'restrict_lot_id': data_get.lot_id.id,
                })

        if not returned_lines:
            raise osv.except_osv(_('Warning!'), _("Please specify at least one non-zero quantity."))

        pick_obj.action_confirm(cr, uid, [new_picking], context=context)
        pick_obj.action_assign(cr, uid, [new_picking], context)
        return new_picking, pick_type_id
    
class wtc_stock_return_picking_line(osv.osv_memory):
    _inherit = "stock.return.picking.line"
    
    _sql_constraints = [
        ('unique_lot_id', 'unique(wizard_id,lot_id)', 'Ditemukan Serial Number duplicate, silahkan cek kembali')
        ]
    
    def quantity_change(self, cr, uid, ids, id_product, quantity, context=None):
        value = {}
        warning = {}
        product_id = self.pool.get('product.product').browse(cr, uid, id_product)
        if product_id.categ_id.isParentName('Unit') :
            value['quantity'] = 1
        if quantity <= 0 :
            value['quantity'] = 1
            return {'value':value,'warning':{'title':'Perhatian !', 'message':'Quantity tidak boleh kurang dari 1'}}
        return {'value':value}
    