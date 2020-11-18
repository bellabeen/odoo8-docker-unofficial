from openerp.osv import osv, fields
from openerp import SUPERUSER_ID, api
from openerp.tools.translate import _
import code
from datetime import datetime
import time
from dateutil.relativedelta import relativedelta

class wtc_warehouse(osv.osv):
    _inherit = 'stock.warehouse'
    
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
        
    def _get_default_date(self,cr,uid,context):
        return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)    
        
    _columns = {
                'branch_id': fields.many2one('wtc.branch', 'Branch'),
                'rel_code': fields.related('code', string='Short Name', type="char", readonly="True"),
                'interbranch_in_type_id': fields.many2one('stock.picking.type', 'Interbranch In Type', ondelete='restrict'),
                'interbranch_out_type_id': fields.many2one('stock.picking.type', 'Interbranch Out Type', ondelete='restrict'),
                'in_type_id': fields.many2one('stock.picking.type', 'In Type', ondelete='restrict'),
                'out_type_id': fields.many2one('stock.picking.type', 'Out Type', ondelete='restrict'),
                'int_type_id': fields.many2one('stock.picking.type', 'Internal Type', ondelete='restrict'),
                }

    _defaults = {
        'branch_id': _get_default_branch,
    }    
    
    def create_sequences_and_picking_types(self, cr, uid, warehouse, context=None):
        seq_obj = self.pool.get('ir.sequence')
        picking_type_obj = self.pool.get('stock.picking.type')
        data_obj = self.pool.get('ir.model.data')
        obj_loc = self.pool.get('stock.location')
        #create new sequences
        in_seq_id = seq_obj.create(cr, uid, values={'name': warehouse.name + _(' Sequence in'), 'prefix': 'GRN/' + warehouse.code + '/%(y)s/%(month)s/', 'padding': 5}, context=context)
        out_seq_id = seq_obj.create(cr, uid, values={'name': warehouse.name + _(' Sequence out'), 'prefix': 'SJ/' + warehouse.code + '/%(y)s/%(month)s/', 'padding': 5}, context=context)
        pack_seq_id = seq_obj.create(cr, uid, values={'name': warehouse.name + _(' Sequence packing'), 'prefix': 'PACK/' + warehouse.code + '/%(y)s/%(month)s/', 'padding': 5}, context=context)
        pick_seq_id = seq_obj.create(cr, uid, values={'name': warehouse.name + _(' Sequence picking'), 'prefix': 'PICK/' + warehouse.code + '/%(y)s/%(month)s/', 'padding': 5}, context=context)
        int_seq_id = seq_obj.create(cr, uid, values={'name': warehouse.name + _(' Sequence internal'), 'prefix': 'MU/' + warehouse.code + '/%(y)s/%(month)s/', 'padding': 5}, context=context)
        inter_in_seq_id = seq_obj.create(cr, uid, values={'name': warehouse.name + _(' Sequence interbranch in'), 'prefix': 'STM/' + warehouse.code + '/%(y)s/%(month)s/', 'padding': 5}, context=context)
        inter_out_seq_id = seq_obj.create(cr, uid, values={'name': warehouse.name + _(' Sequence interbranch out'), 'prefix': 'SJM/' + warehouse.code + '/%(y)s/%(month)s/', 'padding': 5}, context=context)

        wh_stock_loc = warehouse.lot_stock_id
        now = self._get_default_date(cr, uid, context)
        wh_stock_loc.write({
                            'branch_id': warehouse.branch_id.id,
                            'warehouse_id': warehouse.id,
                            'end_date': datetime(now.year+2, now.month, now.day),
                            'maximum_qty': -1})
        wh_input_stock_loc = warehouse.wh_input_stock_loc_id
        wh_output_stock_loc = warehouse.wh_output_stock_loc_id
        wh_pack_stock_loc = warehouse.wh_pack_stock_loc_id

        #fetch customer and supplier locations, for references
        customer_loc, supplier_loc = self._get_partner_locations(cr, uid, warehouse.id, context=context)
        customer_loc_id = obj_loc.search(cr, uid, [
                                                  ('location_id','=',customer_loc.id),
                                                  ('branch_id','=',warehouse.branch_id.id)
                                                  ])[0]
        supplier_loc_id = obj_loc.search(cr, uid, [
                                                  ('location_id','=',supplier_loc.id),
                                                  ('branch_id','=',warehouse.branch_id.id)
                                                  ])[0]
        transit_loc_id = obj_loc.search(cr, uid, [
                                                  ('location_id','=',data_obj.get_object_reference(cr, uid, 'stock', 'stock_location_inter_wh')[1]),
                                                  ('branch_id','=',warehouse.branch_id.id),
                                                  ('usage','=','transit')
                                                  ])[0]

        #create in, out, internal picking types for warehouse
        input_loc = wh_input_stock_loc
        if warehouse.reception_steps == 'one_step':
            input_loc = wh_stock_loc
        output_loc = wh_output_stock_loc
        if warehouse.delivery_steps == 'ship_only':
            output_loc = wh_stock_loc

        #choose the next available color for the picking types of this warehouse
        color = 0
        available_colors = [c%9 for c in range(3, 12)]  # put flashy colors first
        all_used_colors = self.pool.get('stock.picking.type').search_read(cr, uid, [('warehouse_id', '!=', False), ('color', '!=', False)], ['color'], order='color')
        #don't use sets to preserve the list order
        for x in all_used_colors:
            if x['color'] in available_colors:
                available_colors.remove(x['color'])
        if available_colors:
            color = available_colors[0]

        #order the picking types with a sequence allowing to have the following suit for each warehouse: reception, internal, pick, pack, ship. 
        max_sequence = self.pool.get('stock.picking.type').search_read(cr, uid, [], ['sequence'], order='sequence desc')
        max_sequence = max_sequence and max_sequence[0]['sequence'] or 0

        in_type_id = picking_type_obj.create(cr, uid, vals={
            'name': _('Receipts'),
            'branch_id': warehouse.branch_id.id,
            'warehouse_id': warehouse.id,
            'code': 'incoming',
            'sequence_id': in_seq_id,
            'default_location_src_id': supplier_loc_id,
            'default_location_dest_id': input_loc.id,
            'sequence': max_sequence + 1,
            'color': color}, context=context)
        seq_obj.browse(cr, uid, in_seq_id).write({'picking_type_id':in_type_id})
        out_type_id = picking_type_obj.create(cr, uid, vals={
            'name': _('Delivery Orders'),
            'branch_id': warehouse.branch_id.id,
            'warehouse_id': warehouse.id,
            'code': 'outgoing',
            'sequence_id': out_seq_id,
            'return_picking_type_id': in_type_id,
            'default_location_src_id': output_loc.id,
            'default_location_dest_id': customer_loc_id,
            'sequence': max_sequence + 4,
            'color': color}, context=context)
        seq_obj.browse(cr, uid, out_seq_id).write({'picking_type_id':out_type_id})
        picking_type_obj.write(cr, uid, [in_type_id], {'return_picking_type_id': out_type_id}, context=context)
        int_type_id = picking_type_obj.create(cr, uid, vals={
            'name': _('Internal Transfers'),
            'branch_id': warehouse.branch_id.id,
            'warehouse_id': warehouse.id,
            'code': 'internal',
            'sequence_id': int_seq_id,
            'default_location_src_id': wh_stock_loc.id,
            'default_location_dest_id': wh_stock_loc.id,
            'active': True,
            'sequence': max_sequence + 2,
            'color': color}, context=context)
        seq_obj.browse(cr, uid, int_seq_id).write({'picking_type_id':int_type_id})
        pack_type_id = picking_type_obj.create(cr, uid, vals={
            'name': _('Pack'),
            'branch_id': warehouse.branch_id.id,
            'warehouse_id': warehouse.id,
            'code': 'internal',
            'sequence_id': pack_seq_id,
            'default_location_src_id': wh_pack_stock_loc.id,
            'default_location_dest_id': output_loc.id,
            'active': warehouse.delivery_steps == 'pick_pack_ship',
            'sequence': max_sequence + 3,
            'color': color}, context=context)
        seq_obj.browse(cr, uid, pack_seq_id).write({'picking_type_id':pack_type_id})
        pick_type_id = picking_type_obj.create(cr, uid, vals={
            'name': _('Pick'),
            'branch_id': warehouse.branch_id.id,
            'warehouse_id': warehouse.id,
            'code': 'internal',
            'sequence_id': pick_seq_id,
            'default_location_src_id': wh_stock_loc.id,
            'default_location_dest_id': wh_pack_stock_loc.id,
            'active': warehouse.delivery_steps != 'ship_only',
            'sequence': max_sequence + 2,
            'color': color}, context=context)
        seq_obj.browse(cr, uid, pick_seq_id).write({'picking_type_id':pick_type_id})
        interbranch_in_type_id = picking_type_obj.create(cr, uid, vals={
            'name': _('Interbranch Receipts'),
            'branch_id': warehouse.branch_id.id,
            'warehouse_id': warehouse.id,
            'code': 'interbranch_in',
            'sequence_id': inter_in_seq_id,
            'default_location_src_id': transit_loc_id,
            'default_location_dest_id': wh_stock_loc.id,
            'active': True,
            'sequence': max_sequence + 2,
            'color': color}, context=context)
        seq_obj.browse(cr, uid, inter_in_seq_id).write({'picking_type_id':interbranch_in_type_id})
        interbranch_out_type_id = picking_type_obj.create(cr, uid, vals={
            'name': _('Interbranch Deliveries'),
            'branch_id': warehouse.branch_id.id,
            'warehouse_id': warehouse.id,
            'code': 'interbranch_out',
            'sequence_id': inter_out_seq_id,
            'default_location_src_id': wh_stock_loc.id,
            'default_location_dest_id': transit_loc_id,
            'active': True,
            'sequence': max_sequence + 2,
            'color': color}, context=context)
        seq_obj.browse(cr, uid, inter_out_seq_id).write({'picking_type_id':interbranch_out_type_id})

        #write picking types on WH
        vals = {
            'in_type_id': in_type_id,
            'out_type_id': out_type_id,
            'pack_type_id': pack_type_id,
            'pick_type_id': pick_type_id,
            'int_type_id': int_type_id,
            'interbranch_in_type_id': interbranch_in_type_id,
            'interbranch_out_type_id': interbranch_out_type_id,
        }
        obj_branch = self.pool.get('wtc.branch').browse(cr, uid, warehouse.branch_id.id)
        if not obj_branch.warehouse_id :
            obj_branch.write({'warehouse_id':warehouse.id})
        return super(wtc_warehouse, self).write(cr, uid, warehouse.id, vals=vals, context=context)
        
    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        if vals is None:
            vals = {}
        
        data_obj = self.pool.get('ir.model.data')
        location_obj = self.pool.get('stock.location')
        obj_branch = self.pool.get('wtc.branch').browse(cr, uid, vals['branch_id'])

        partner_locations = [
            {'name': _(vals.get('code')) + _('-Customers'), 'usage': 'customer', 'field': 'lot_stock_id', 'location_id': data_obj.get_object_reference(cr, uid, 'stock', 'stock_location_customers')[1]},
            {'name': _(vals.get('code')) + _('-Suppliers'), 'usage': 'supplier', 'field': 'lot_stock_id', 'location_id': data_obj.get_object_reference(cr, uid, 'stock', 'stock_location_suppliers')[1]},
            {'name': _(vals.get('code')) + _('-Transit'), 'usage': 'transit', 'field': 'lot_stock_id', 'location_id': data_obj.get_object_reference(cr, uid, 'stock', 'stock_location_inter_wh')[1]},
            {'name': _(vals.get('code')) + _('-Inventory Loss'), 'usage': 'inventory', 'field': 'lot_stock_id', 'location_id': data_obj.get_object_reference(cr, uid, 'stock', 'location_inventory')[1]},
            {'name': _(vals.get('code')) + _('-Scrapped'), 'usage': 'inventory', 'field': 'lot_stock_id', 'location_id': data_obj.get_object_reference(cr, uid, 'stock', 'stock_location_scrapped')[1]},
        ]
        loc_ids = []
        for values in partner_locations:
            part_vals = {
                'name': values['name'],
                'branch_id': _(vals.get('branch_id')),
                'usage': values['usage'],
                'location_id': values['location_id'],
                'active': True,
                'warehouse_id': _(vals.get('id')),
                'maximum_qty': -1,
                'start_date': self._get_default_date(cr, uid, context),
                'end_date': self._get_default_date(cr, uid, context) + relativedelta(years=2),
            }
            if vals.get('company_id'):
                part_vals['company_id'] = vals.get('company_id')
            location_id = location_obj.create(cr, uid, part_vals, context=context)
            loc_ids.append(location_id)
        
        result = super(wtc_warehouse, self).create(cr, uid, vals, context=context)
        loc_stock_id = location_obj.search(cr, uid, [('name','=',vals['code'])])
        if len(loc_stock_id) > 1 :
            try :
                for x in loc_stock_id :
                    loc_stock = location_obj.browse(cr, uid, x)
                    if not loc_stock.branch_id :
                        loc_stock.write({'branch_id':_(vals.get('branch_id')), 'maximum_qty': -1, 'end_date': self._get_default_date(cr, uid, context) + relativedelta(years=2)})
                    else :
                        loc_stock.unlink()
            except :
                cr.commit()
        else :
            loc_stock = location_obj.browse(cr, uid, loc_stock_id)
            loc_stock.write({'branch_id':_(vals.get('branch_id')), 'maximum_qty': -1, 'end_date':self._get_default_date(cr, uid, context) + relativedelta(years=2)})
        for x in loc_ids :
            location_obj.write(cr, uid, x, {'warehouse_id':result})
        return result
        
    def upper_change(self, cr, uid, ids, name, code, context=None):
        value = {}
        if name :
            value['name'] = name.upper()
        if code :
            value['code'] = code.upper()
        return {'value':value}
        
    def write(self, cr, uid, ids, vals, context=None):
        result = super(wtc_warehouse, self).write(cr, uid, ids, vals=vals, context=context)
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        seq_obj = self.pool.get('ir.sequence')
        context_with_inactive = context.copy()
        context_with_inactive['active_test'] = False
        for warehouse in self.browse(cr, uid, ids, context=context_with_inactive):
            if vals.get('code') or vals.get('name'):
                name = warehouse.name
                #rename sequence
                if vals.get('name'):
                    name = vals.get('name', warehouse.name)
                if warehouse.in_type_id:
                    seq_obj.write(cr, uid, warehouse.in_type_id.sequence_id.id, {'name': warehouse.name + _(' Sequence in'), 'prefix': 'GRN/' + warehouse.code + '/%(y)s/%(month)s/', 'padding': 5}, context=context)
                    seq_obj.write(cr, uid, warehouse.out_type_id.sequence_id.id, {'name': warehouse.name + _(' Sequence out'), 'prefix': 'SJ/' + warehouse.code + '/%(y)s/%(month)s/', 'padding': 5}, context=context)
                    seq_obj.write(cr, uid, warehouse.pack_type_id.sequence_id.id, {'name': warehouse.name + _(' Sequence packing'), 'prefix': 'PACK/' + warehouse.code + '/%(y)s/%(month)s/', 'padding': 5}, context=context)
                    seq_obj.write(cr, uid, warehouse.pick_type_id.sequence_id.id, {'name': warehouse.name + _(' Sequence picking'), 'prefix': 'PICK/' + warehouse.code + '/%(y)s/%(month)s/', 'padding': 5}, context=context)
                    seq_obj.write(cr, uid, warehouse.int_type_id.sequence_id.id, {'name': warehouse.name + _(' Sequence internal'), 'prefix': 'MU/' + warehouse.code + '/%(y)s/%(month)s/', 'padding': 5}, context=context)
                    seq_obj.write(cr, uid, warehouse.interbranch_in_type_id.sequence_id.id, {'name': warehouse.name + _(' Sequence interbranch in'), 'prefix': 'STM/' + warehouse.code + '/%(y)s/%(month)s/', 'padding': 5}, context=context)
                    seq_obj.write(cr, uid, warehouse.interbranch_out_type_id.sequence_id.id, {'name': warehouse.name + _(' Sequence interbranch out'), 'prefix': 'SJM/' + warehouse.code + '/%(y)s/%(month)s/', 'padding': 5}, context=context)

        return result
    
    """
    update stock_location set maximum_qty = -1 where usage = 'internal' and maximum_qty is Null;
    update stock_location set end_date = start_date + interval '2 years' where start_date is not Null;
    update stock_picking_type set code = 'interbranch_in' where name = 'Interbranch Receipts';
    update stock_picking_type set code = 'interbranch_out' where name = 'Interbranch Deliveries';
    """
    
class wtc_warehouse_location(osv.osv):
    _inherit = 'stock.location'
    _columns = {
                'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', ondelete='cascade'),
                }
    
class wtc_warehouse_ir_sequence(osv.osv):
    _inherit = 'ir.sequence'
    _columns = {
                'picking_type_id': fields.many2one('stock.picking.type', 'Picking Type', ondelete='cascade'),
                }
     
class wtc_warehouse_stock_picking_type(osv.osv):
    _inherit = 'stock.picking.type'
    _columns = {
                'default_location_src_id': fields.many2one('stock.location', 'Default Source Location', ondelete="restrict"),
                'default_location_dest_id': fields.many2one('stock.location', 'Default Destination Location', ondelete="restrict"),
                }
    