from openerp import api, SUPERUSER_ID, exceptions
from openerp.osv import fields, osv
from openerp.tools.float_utils import float_compare, float_round
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
import time
from datetime import datetime
import code

class wtc_stock_picking(osv.osv):
    _inherit = 'stock.picking'

    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids
    
    def _get_is_effective_date(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for picking in self.browse(cr, uid, ids, context=context):
            if not picking.start_date and not picking.end_date :
                res[picking.id] = True
            elif picking.start_date and picking.end_date and datetime.strptime(picking.start_date, "%Y-%m-%d").date() <= self._get_default_date(cr, uid, context).date() and datetime.strptime(picking.end_date, "%Y-%m-%d").date() >= datetime.today().date() :
                res[picking.id] = True
            else :
                res[picking.id] = False
        return res
    
    def _get_is_reverse(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for picking in self.browse(cr, uid, ids, context=context):
            reverse_incoming = picking.picking_type_code == 'outgoing' and picking.location_dest_id.usage == 'supplier'
            reverse_outgoing = picking.picking_type_code == 'incoming' and picking.location_id.usage == 'customer'
            res[picking.id] = reverse_incoming or reverse_outgoing
        return res
    
    def _get_default_date(self,cr,uid,context=None):
        return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=None) 
        
    _columns = {
                'branch_id': fields.many2one('wtc.branch', string='Branch', required=True),
                'division': fields.selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum')], 'Division', change_default=True, select=True, required=True),
                'transaction_id': fields.integer('Transaction ID'),
                'model_id': fields.many2one('ir.model','Model'),
                'internal_location_id': fields.many2one('stock.location', string='Source Location'),
                'internal_location_dest_id': fields.many2one('stock.location', string='Destination Location', help='Destination Location filtered by effective date.'),
                'start_date': fields.date('Start Date'),
                'end_date': fields.date('End Date'),
                'is_effective_date': fields.function(_get_is_effective_date, string='Is Effective Date', type='boolean', copy=False),
                'is_reverse': fields.function(_get_is_reverse, string='Is Reverse', type='boolean', copy=False),
                'rel_branch_type' : fields.related('branch_id', 'branch_type', string='Branch Type', type='selection', selection=[('HO','Head Office'), ('MD','Main Dealer'), ('DL','Dealer')]),
                'confirm_uid':fields.many2one('res.users', string="Transfered by", copy=False),
                'confirm_date':fields.datetime('Transfered on', copy=False),
                'is_unconsolidated_reverse':fields.boolean('Cancelled'),
                }
    
    def print_wizard(self,cr,uid,ids,context=None):
        obj_claim_kpb = self.browse(cr,uid,ids)
        obj_ir_view = self.pool.get("ir.ui.view")
        obj_ir_view_search= obj_ir_view.search(cr,uid,[("name", "=", 'stock.picking.wizard.print'), ("model", "=", 'stock.picking'),])
        obj_ir_view_browse = obj_ir_view.browse(cr,uid,obj_ir_view_search)
        return {
            'name': 'Print',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
            'view_id' : obj_ir_view_browse.id,
            'nodestroy': True,
            'target': 'new',
            'res_id': obj_claim_kpb.id
            }
    
    _defaults = {
                 'picking_type_id': False,
                 'name': False,
                 'branch_id': _get_default_branch,
                 }
    
    def create(self, cr, uid, vals, context=None):
        ptype_id = vals.get('picking_type_id', False)
        code = self.pool.get('stock.picking.type').browse(cr, uid, ptype_id, context=context).code
        if code in ('incoming','interbranch_in') :
            prefix = 'WHI'
        elif code in ('outgoing','interbranch_out') :
            prefix = 'WHO'
        else :
            return super(wtc_stock_picking, self).create(cr, uid, vals, context=context)
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, SUPERUSER_ID, vals['branch_id'], prefix)
        return super(wtc_stock_picking, self).create(cr, uid, vals, context=context)
    
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Tidak bisa dihapus jika status bukan 'Draft' !"))
        return super(wtc_stock_picking, self).unlink(cr, uid, ids, context=context)
    
    def renew_available(self, cr, uid, ids, context=None):
        picking_id = self.browse(cr, uid, ids, context=None)
        obj_move = self.pool.get('stock.move')
        for move in picking_id.move_lines :
            current_available = obj_move.get_stock_available(cr, uid, ids, move.product_id.id, picking_id.internal_location_id.id, context)
            move.write({'stock_available':current_available})
        return True
    
    def _check_location(self, cr, uid, ids, source_location, destination_location, context=None):
        if source_location == destination_location :
            raise osv.except_osv(('Perhatian !'), ("Source Location dan Destination Location tidak boleh sama !"))
        return True
    
    def action_confirm(self, cr, uid, ids, context=None):
        koreksi = self.browse(cr, uid, ids).internal_location_dest_id.name

        if koreksi:
            if "KOREKSI" in str(koreksi.encode('ascii','ignore').decode('ascii')).replace('\xa0',' ').upper():
                group_in =" in ('Manager Administration','GM Finance Accounting')"
                cek_groups = """ 
                            select * from res_groups_users_rel rel
                            LEFT JOIN res_groups grps on rel.gid=grps.id
                            where grps.name  %s and rel.uid=%s
                """ %(group_in,uid)
                cr.execute (cek_groups)
                ress = cr.fetchall()
                if not ress:
                    raise osv.except_osv(('Perhatian !'), ("Tidak ada Wewenang mutasi ke Warehouse Koreksi"))

        todo = []
        todo_force_assign = []
        for picking in self.browse(cr, uid, ids, context=context):
            if picking.location_id.usage in ('supplier', 'inventory', 'production') or (picking.branch_id.branch_type == 'MD' and picking.division == 'Unit' and picking.picking_type_id.code == 'outgoing' and not picking.is_reverse) or (picking.division == 'Unit' and picking.picking_type_id.code == 'interbranch_out' and not picking.is_reverse):
                todo_force_assign.append(picking.id)
            for r in picking.move_lines:
                if r.state == 'draft':
                    todo.append(r.id)
        if len(todo):
            self.pool.get('stock.move').action_confirm(cr, uid, todo, context=context)

        if todo_force_assign:
            self.force_assign(cr, uid, todo_force_assign, context=context)
        
        #Custom
        picking_id = self.browse(cr, uid, ids, context=context)
        if picking_id.state == 'confirmed' :
            if picking_id.picking_type_id.code == 'internal' :
                self._check_location(cr, uid, ids, picking_id.internal_location_id, picking_id.internal_location_dest_id, context)
                self.renew_available(cr, uid, ids, context)
                internal_move = {}
                for move in picking_id.move_lines :
                    internal_move[move.product_id] = internal_move.get(move.product_id,0) + move.product_uom_qty
                    if internal_move[move.product_id] > move.stock_available :
                        raise osv.except_osv(('Perhatian !'), ("Quantity product '%s' melebihi stock available" %move.product_id.name))
                self.action_assign(cr, uid, [picking_id.id])
        return True
    
    def write(self, cr, uid, ids, vals, context=None):
        vals.get('move_lines', []).sort(reverse=True)
        return super(wtc_stock_picking, self).write(cr, uid, ids, vals, context=context)
    
    def internal_location_change(self, cr, uid, ids, context=None):
        value = {'move_lines': False}
        return {'value':value}
    
    @api.cr_uid_ids_context
    def wtc_do_enter_transfer_details(self, cr, uid, picking, context=None):
        if not context:
            context = {}
            
        context.update({
            'active_model': self._name,
            'active_ids': picking,
            'active_id': len(picking) and picking[0] or False
        })
        
        created_id = self.pool['stock.wtc_transfer_details'].create(cr, uid, {'picking_id': len(picking) and picking[0] or False}, context)
        return self.pool['stock.wtc_transfer_details'].wizard_view(cr, uid, created_id, context)
    
    def type_change(self, cr, uid, ids, type, context=None):
        value = {'internal_location_id': False, 'internal_location_dest_id': False}
        if type :
            obj_type = self.pool.get('stock.picking.type').browse(cr, uid, type)
            value['internal_location_id'] = obj_type.default_location_src_id
        return {'value':value}
    
    def get_ids_move(self, cr, uid, ids, context=None):
        ids_move = []
        picking_id = self.browse(cr, uid, ids)
        for move in picking_id.move_lines :
            ids_move.append(move.id)
        return ids_move
    
    def filter_ids_move(self, cr, uid, ids, context=None):
        product_move = {}
        picking_id = self.browse(cr, uid, ids)
        for move in picking_id.move_lines :
            product_move[move.product_id.id] = []
        for move in picking_id.move_lines :
            product_move[move.product_id.id].append(move.id)
        return product_move
    
    def get_restrict_lot_ids(self, cr, uid, ids, context=None):
        ids_restrict_lot = []
        picking_id = self.browse(cr, uid, ids)
        for move in picking_id.move_lines :
            ids_restrict_lot.append(move.restrict_lot_id.id)
        return ids_restrict_lot
    
    def get_lot_ids_from_pack(self, cr, uid, ids, context=None):
        ids_lot = []
        picking_id = self.browse(cr, uid, ids)
        for pack in picking_id.pack_operation_ids :
            ids_lot.append(pack.lot_id.id)
        return ids_lot
    
    def get_reserve_lot_quant_ids(self, cr, uid, ids, context=None):
        ids_lot_quant = []
        picking_id = self.browse(cr, uid, ids)
        for move in picking_id.move_lines :
            for quant in move.reserved_quant_ids :
                ids_lot_quant.append(quant.lot_id.id)
        return ids_lot_quant
    
    def filter_restrict_lot_ids(self, cr, uid, ids, context=None):
        product_restrict_lot = {}
        picking_id = self.browse(cr, uid, ids)
        for move in picking_id.move_lines :
            if not product_restrict_lot.get(move.product_id):
                product_restrict_lot[move.product_id] = []
            product_restrict_lot[move.product_id].append(move.restrict_lot_id.id)
        return product_restrict_lot
    
    def get_seharusnya(self, cr, uid, ids, context=None):
        qty_seharusnya = {}
        picking_id = self.browse(cr, uid, ids)
        for move in picking_id.move_lines :
            qty_seharusnya[move.product_id] = qty_seharusnya.get(move.product_id,0) + move.product_uom_qty
        return qty_seharusnya
    
    def get_ids_move_reversed(self, cr, uid, ids, context=None):
        ids_move = self.get_ids_move(cr, uid, ids, context)
        return self.pool.get('stock.move').search(cr, uid, [('origin_returned_move_id','in',ids_move),('state','!=','cancel')])
    
    def get_origin_returned_move_id(self, cr, uid, ids, context=None):
        move_origin = {}
        picking_id = self.browse(cr, uid, ids, context=context)
        for move in picking_id.move_lines :
            move_origin[move.product_id] = []
        for move in picking_id.move_lines :
            for qty in range(int(move.product_uom_qty)):
                move_origin[move.product_id].append(move.id)
        ids_move_reversed = self.get_ids_move_reversed(cr, uid, ids, context)
        if ids_move_reversed :
            for move_reversed_id in self.pool.get('stock.move').browse(cr, uid, ids_move_reversed):
                for qty_reversed in range(int(move_reversed_id.product_uom_qty)):
                    move_origin[move_reversed_id.product_id].remove(move_reversed_id.origin_returned_move_id.id)
        return move_origin
    
    def get_product_ids(self, cr, uid, ids, context=None):
        result = []
        if isinstance(ids,(int,long)):
            ids = [ids]
        for id in ids :
            picking_obj = self.browse(cr,uid,id)
            if picking_obj.move_lines :
                for move_obj in picking_obj.move_lines :
                    result.append(move_obj.product_id.id)
        return result
    
    def get_qty(self, cr, uid, ids, picking_id, product_id, move_qty, context=None):
        qty = 0
        if product_id.categ_id.isParentName('Unit'):
            qty = 1
        elif picking_id.is_reverse :
            qty = move_qty
        return qty
    
    def convert_rfs(self, cr, uid, ids, rfs, context=None):
        result = False
        if rfs == 'good' :
            result = True
        elif rfs == True :
            result = 'good'
        elif rfs == False :
            result = 'not_good'
        return result

    def _create_extras_order(self, cr, uid, picking, context=None):
        extras = {}

        move_id_unit = -1

        if not picking.move_lines:
            return False
        for move in picking.move_lines:
            if move.product_id.categ_id.isParentName('Unit'):
                if move_id_unit < 0:
                    move_id_unit = move.id
                for x in move.product_id.product_tmpl_id.extras_line:
                    extras[x.product_id] = extras.get(x.product_id,0)+(move.product_uom_qty*x.quantity)
        
        if extras:
            """
                Create backoder for extras
            """
            extras_order_id = self.copy(cr, uid, picking.id, {
                    'name':'/',
                    'division':'Umum',
                    'move_lines':[],
                    'pack_operation_ids':[],
                    'backorder_id':picking.id,
                    'move_type':'direct',
                    'invoice_state':'none',
                })
            extras_order = self.browse(cr, uid, extras_order_id, context=context)
            self.message_post(cr, uid, picking.id, body=_("Extras Order <em>%s</em> <b>created</b>.") % (extras_order.name), context=context)
            stock_move_obj = self.pool.get('stock.move')
            for key, value in extras.items():
                uos_id = key.uos_id and key.uos_id.id or False
                move = stock_move_obj.copy(cr, uid, move_id_unit, {
                        'picking_id':extras_order_id,
                        'categ_id': key.categ_id.id,
                        'product_id':key.id,
                        'name': key.partner_ref,
                        'product_uom': key.uom_id.id,
                        'product_uos': uos_id,
                        'product_uom_qty':value,
                        'product_uos_qty':value,
                        'price_unit': 0,
                        'undelivered_value': 0,
                    })
            self.action_confirm(cr, uid, [extras_order_id], context=context)
            return extras_order_id
        return False
    
    def _create_interbranch_in(self, cr, uid, picking, context=None):
        if not picking.move_lines :
            return False
        
        obj_mo_id = self.pool.get('wtc.mutation.order').browse(cr, uid, picking.transaction_id)
        branch_id = obj_mo_id.sudo().branch_requester_id
        warehouse_id = branch_id.warehouse_id
        picking_type_id = warehouse_id.interbranch_in_type_id
        ids_partner = self.pool.get('res.partner').search(cr, SUPERUSER_ID, [('branch_id','=',picking.branch_id.id),('default_code','=',picking.branch_id.code)])
        id_partner = False
        if ids_partner :
            id_partner = ids_partner[0]
        
        picking_vals = {
                        'branch_id': branch_id.id,
                        'division': picking.division,
                        'date': self._get_default_date(cr, uid, context),
                        'partner_id': id_partner,
                        'start_date': picking.start_date,
                        'end_date': picking.end_date,
                        'origin': picking.origin,
                        'transaction_id': picking.transaction_id,
                        'model_id': picking.model_id.id,
                        'picking_type_id': picking_type_id.id
                        }
        mutation_order_id = self.create(cr, SUPERUSER_ID, picking_vals, context=context)
        stock_move_obj = self.pool.get('stock.move')
        todo_moves = []
        for move in picking.pack_operation_ids :
            total_hpp = 0
            total_qty = 0
            for smol in move.linked_move_operation_ids :
               total_hpp = total_hpp + smol.move_id.real_hpp * smol.qty
               total_qty = total_qty + smol.qty
               real_hpp = total_hpp / total_qty
            moves = {
                    'branch_id': picking.branch_id.id,
                    'categ_id': move.product_id.categ_id.id,
                    'picking_id': mutation_order_id,
                    'product_id': move.product_id.id,
                    'product_uom': move.product_id.uom_id.id,
                    'product_uos': move.product_id.uom_id.id,
                    'name': move.product_id.partner_ref,
                    'product_uom': move.product_id.uom_id.id,
                    'product_uos': move.product_id.uom_id.id,
                    'restrict_lot_id': move.lot_id.id,
                    'date': self._get_default_date(cr, uid, context),
                    'product_uom_qty': move.product_qty,
                    'product_uos_qty': move.product_qty,
                    'location_id': picking.picking_type_id.default_location_dest_id.id,
                    'location_dest_id': picking_type_id.default_location_dest_id.id,
                    'state': 'draft',
                    'picking_type_id': picking_type_id.id,
                    'procurement_id': False,
                    'origin': picking.origin,
                    'warehouse_id': warehouse_id.id,
                    'price_unit': real_hpp*1.1
                    }
            move_create = stock_move_obj.create(cr, uid, moves, context=context)
            todo_moves.append(move_create)
            
        self.action_confirm(cr, uid, [mutation_order_id], context=context)
        self.action_assign(cr, uid, [mutation_order_id], context=context)
        #  if picking.division == 'Unit' :
        #  self.force_assign(cr, uid, [mutation_order_id], context=context)
        return mutation_order_id

    def transfer(self, cr, uid, picking, context=None):
        self.write(cr,uid,picking.id,{'confirm_uid':uid,'confirm_date':datetime.now()})
        return True

    def _create_nrfs(self, cr, uid, picking_obj, context=None):
        pass
    
    def write_serial_number(self, cr, uid, picking, context=None):
        if picking.picking_type_id.code == 'internal' and picking.division == 'Unit' :
            for move in picking.move_lines :
                if move.restrict_lot_id.id and move.restrict_lot_id.state!='stock':
                    raise osv.except_osv(('Perhatian !'), ("No Mesin '%s' sudah terjual!" %move.restrict_lot_id.name))
                is_rfs = 'good'
                if not move.is_rfs:
                    is_rfs = 'not_good'
                    if picking.rel_branch_type == 'MD':
                        self._create_nrfs(cr, uid, move, context=context)
                self.pool.get('stock.production.lot').write(cr, uid, move.restrict_lot_id.id, {'location_id':picking.internal_location_dest_id.id, 'picking_id':picking.id, 'ready_for_sale':is_rfs})
    
    @api.cr_uid_ids_context
    def do_transfer(self, cr, uid, picking_ids, context=None):
        
        for picking in self.browse(cr, uid, picking_ids, context=context):
            if picking.picking_type_code == 'internal' :
                if picking.state=='done':
                    raise osv.except_osv(('Perhatian !'), ("Transaksi sudah di Post oleh user lain!"))
        cr.execute("""
            update stock_move
            set date = (now() at time zone 'UTC'),
            write_uid = %s,
            write_date = (now() at time zone 'UTC')
            where picking_id in %s
            """, (uid, tuple(picking_ids)))
        res = super(wtc_stock_picking, self).do_transfer(cr, uid, picking_ids, context=context)
        """
            If receiving Motorcycle from supplier, do generate picking for Extras
        """
        for picking in self.browse(cr, uid, picking_ids, context=context):
            if (picking.picking_type_code in ('incoming','interbranch_out') or (picking.picking_type_code == 'outgoing' and picking.rel_branch_type == 'MD')) and picking.division == 'Unit' and not picking.is_reverse :
                self._create_extras_order(cr, uid, picking, context=context)
            if picking.picking_type_code == 'interbranch_out' :
                self._create_interbranch_in(cr, SUPERUSER_ID, picking, context=context)
            if picking.picking_type_code == 'internal' :
                picking.date_done = datetime.now()
            self.transfer(cr, SUPERUSER_ID, picking, context=context)
            self.write_serial_number(cr, uid, picking, context)
        return True

    @api.cr_uid_ids_context
    def do_unreserve(self, cr, uid, picking_ids, context=None):
        """
          Will remove all quants for picking in picking_ids
          except reservation from Dealer Sale Order Module
        """
        moves_to_unreserve = []
        pack_line_to_unreserve = []
        for picking in self.browse(cr, uid, picking_ids, context=context):
            moves_to_unreserve += [m.id for m in picking.move_lines if m.state not in ('done', 'cancel') and not m.product_id.categ_id.isParentName('Unit') and not m.picking_id.branch_id.branch_type == 'DL']
            pack_line_to_unreserve += [p.id for p in picking.pack_operation_ids]
        if moves_to_unreserve:
            if pack_line_to_unreserve:
                self.pool.get('stock.pack.operation').unlink(cr, uid, pack_line_to_unreserve, context=context)
            self.pool.get('stock.move').do_unreserve(cr, uid, moves_to_unreserve, context=context)
            
    def branch_id_change(self, cr, uid, ids, id_branch, context=None):
        val = {}
        if id_branch :
            obj_picking_type = self.pool.get('stock.picking.type')
            id_picking_type = obj_picking_type.search(cr, uid, [
                                                                ('code','=','internal'),
                                                                ('branch_id','=',id_branch)
                                                                ])[0]
            val['picking_type_id'] = id_picking_type
        return {'value':val}
    
    def get_current_reserved(self, cr, uid, ids, id_product, id_location, ids_move, context=None):
        ids_move = tuple(ids_move)
        cr.execute("""
        SELECT
            sum(q.qty) as quantity
        FROM
            stock_quant q
        LEFT JOIN
            stock_production_lot l on l.id = q.lot_id
        WHERE
            q.product_id = %s and q.location_id = %s and q.reservation_id in %s
        """,(id_product,id_location,ids_move))
        return cr.fetchall()[0][0]
    
    def get_stock_available(self, cr, uid, ids, id_product, id_location, context=None):
        cr.execute("""
        SELECT
            sum(q.qty) as quantity
        FROM
            stock_quant q
        LEFT JOIN
            stock_production_lot l on l.id = q.lot_id
        WHERE
            q.product_id = %s and q.location_id = %s and q.reservation_id is Null and q.consolidated_date is not Null
            and (q.lot_id is Null or (l.state = 'stock' and l.ready_for_sale='good'))
        """,(id_product,id_location))
        return cr.fetchall()[0][0]
    
    def get_stock_available_unconsolidated(self, cr, uid, ids, id_product, id_location, context=None):
        cr.execute("""
        SELECT
            sum(q.qty) as quantity
        FROM
            stock_quant q
        LEFT JOIN
            stock_production_lot l on l.id = q.lot_id
        WHERE
            q.product_id = %s and q.location_id = %s and q.reservation_id is Null and q.consolidated_date is Null
            and (q.lot_id is Null or l.state = 'stock')
        """,(id_product,id_location))
        return cr.fetchall()[0][0]
    
    def get_stock_available_extras(self, cr, uid, ids, id_product, id_location, context=None):
        cr.execute("""
        SELECT
            sum(q.qty) as quantity
        FROM
            stock_quant q
        LEFT JOIN
            stock_production_lot l on l.id = q.lot_id
        WHERE
            q.product_id = %s and q.location_id = %s and q.reservation_id is Null
            and (q.lot_id is Null or l.state = 'stock')
        """,(id_product,id_location))
        return cr.fetchall()[0][0]
    
    def create_packing(self, cr, uid, ids, context=None):
        picking_id = self.browse(cr, uid, ids, context=context)
        if picking_id.branch_id.branch_type == 'MD' and picking_id.division == 'Unit' and picking_id.picking_type_code == 'incoming' and not picking_id.is_reverse and picking_id.state != 'done' :
            raise osv.except_osv(('Perhatian !'), ("Untuk penerimaan Unit MD silahkan create di menu Showroom > Good Receipt Note MD"))
        packing_draft = self.pool.get('wtc.stock.packing').search(cr, uid, [
                                                                            ('picking_id','=',picking_id.id),
                                                                            ('state','in',['draft','surat_jalan'])
                                                                            ])
        if picking_id.state == 'done' or packing_draft :
            return self.view_packing(cr,uid,ids,context)
        
        obj_packing = self.pool.get('wtc.stock.packing')
        obj_packing_line = self.pool.get('wtc.stock.packing.line')
        branch_sender_id = False
        
        if picking_id.picking_type_code == 'interbranch_in' :
            branch_sender_id = picking_id.location_id.branch_id.id
        packing_vals = {
                        'picking_id': picking_id.id,
                        'branch_sender_id': branch_sender_id,
                        'rel_branch_id': picking_id.picking_type_id.branch_id.id,
                        'rel_source_location_id': picking_id.location_id.id,
                        'rel_picking_type_id': picking_id.picking_type_id.id,
                        'rel_destination_location_id': picking_id.location_dest_id.id,
                        'rel_origin': picking_id.origin,
                        'rel_partner_id': picking_id.partner_id.id,
                        'rel_division': picking_id.division,
                        'rel_code': picking_id.picking_type_id.code,
                        'rel_branch_type': picking_id.branch_id.branch_type,
                        }
        
        id_packing = obj_packing.create(cr, uid, packing_vals, context=context)
        
        if (picking_id.picking_type_code == 'outgoing' and picking_id.rel_branch_type == 'DL') or picking_id.division == 'Umum' or picking_id.is_reverse :
            ids_move = self.get_ids_move(cr, uid, ids, context)
            for move in picking_id.move_lines :
                if picking_id.picking_type_code == 'incoming' and not picking_id.is_reverse :
                    current_reserved = 0
                    stock_available = self.get_seharusnya(cr, uid, ids, context)[move.product_id]
                elif picking_id.is_reverse and not picking_id.is_unconsolidated_reverse:
                    current_reserved = self.get_current_reserved(cr, uid, ids, move.product_id.id, move.location_id.id, ids_move, context)
                    stock_available = 0
                elif picking_id.is_unconsolidated_reverse:
                    current_reserved = self.get_current_reserved(cr, uid, ids, move.product_id.id, move.location_id.id, ids_move, context)
                    stock_available = self.get_stock_available_unconsolidated(cr, uid, ids, move.product_id.id, move.location_id.id, context)   
                elif move.product_id.categ_id.isParentName('Extras') :
                    current_reserved = self.get_current_reserved(cr, uid, ids, move.product_id.id, move.location_id.id, ids_move, context)
                    stock_available = self.get_stock_available_extras(cr, uid, ids, move.product_id.id, move.location_id.id, context)
                else :
                    current_reserved = self.get_current_reserved(cr, uid, ids, move.product_id.id, move.location_id.id, ids_move, context)
                    stock_available = self.get_stock_available(cr, uid, ids, move.product_id.id, move.location_id.id, context)
                
                packing_line_vals = {
                                     'packing_id': id_packing,
                                     'product_id': move.product_id.id,
                                     'quantity': self.get_qty(cr, uid, ids, picking_id, move.product_id, move.product_uom_qty, context),
                                     'seharusnya': self.get_seharusnya(cr, uid, ids, context)[move.product_id],
                                     'serial_number_id': move.restrict_lot_id.id,
                                     'engine_number': move.restrict_lot_id.name,
                                     'chassis_number': move.restrict_lot_id.chassis_no,
                                     'source_location_id': move.location_id.id,
                                     'destination_location_id': move.location_dest_id.id,
                                     'tahun_pembuatan': move.restrict_lot_id.tahun,
                                     'ready_for_sale': self.convert_rfs(cr, uid, ids, move.restrict_lot_id.ready_for_sale, context),
                                     'current_reserved': current_reserved,
                                     'stock_available': stock_available
                                     }
                obj_packing_line.create(cr, uid, packing_line_vals, context=context)
        return self.view_packing(cr, uid, ids, context)
    
    def view_packing(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        mod_obj = self.pool.get('ir.model.data')
        dummy, action_id = tuple(mod_obj.get_object_reference(cr, uid, 'wtc_stock', 'wtc_stock_packing_action'))
        action = self.pool.get('ir.actions.act_window').read(cr, uid, action_id, context=context)
        packing_ids = []
        picking_id = self.browse(cr, uid, ids, context=context)
        for packing in self.pool.get('wtc.stock.packing').search(cr, uid, [('picking_id','=',picking_id.id)]):
            packing_ids.append(packing)
        if not packing_ids :
            raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan Stock Packing untuk Picking '%s'" %picking_id.name))
        action['context'] = {}
        if len(packing_ids) > 1:
            action['domain'] = "[('id','in',[" + ','.join(map(str, packing_ids)) + "])]"
        else:
            if picking_id.division=='Unit' and picking_id.branch_id.branch_type=='DL' and picking_id.picking_type_code in ('outgoing','interbranch_out','interbranch_in'):
                res = mod_obj.get_object_reference(cr, uid, 'wtc_stock', 'wtc_stock_packing_out_dl_unit_form_view')
            elif picking_id.division in ('Sparepart','Umum') and picking_id.picking_type_code in ('outgoing','interbranch_out','interbranch_in'):
                res = mod_obj.get_object_reference(cr, uid, 'wtc_stock', 'wtc_stock_packing_out_ws_umum_form_view')
            elif picking_id.division in ('Sparepart','Umum') and picking_id.picking_type_code in ('incoming'):
                res = mod_obj.get_object_reference(cr, uid, 'wtc_stock', 'wtc_stock_packing_in_ws_umum_form_view')
            elif picking_id.division in ('Unit') and picking_id.branch_id.branch_type=='DL' and picking_id.picking_type_code in ('incoming'):
                res = mod_obj.get_object_reference(cr, uid, 'wtc_stock', 'wtc_stock_packing_in_dl_unit_form_view')
            elif picking_id.division=='Unit' and picking_id.branch_id.branch_type=='MD' and picking_id.picking_type_code in ('outgoing','interbranch_out','interbranch_in'):
                res = mod_obj.get_object_reference(cr, uid, 'wtc_stock', 'wtc_stock_packing_out_md_unit_form_view')
            else:
                res = mod_obj.get_object_reference(cr, uid, 'wtc_stock', 'wtc_stock_packing_form_view')
            action['views'] = [(res and res[1] or False, 'form')]
            action['res_id'] = packing_ids and packing_ids[0] or False 
        return action
    
    def _get_picking_type(self,cr,uid,branch_id):
        picking_type_ids = self.pool.get('stock.picking.type').search(cr,uid,[('branch_id','=',branch_id),('code','in',['outgoing','interbranch_out'])])
        if not picking_type_ids:
            return False
        return picking_type_ids
    
    def _get_location(self,cr,uid,branch_id):
        location_ids = self.pool.get('stock.location').search(cr,uid,[('branch_id','=',branch_id),('usage','=','internal')])
        if not location_ids:
            return False
        return location_ids
    
    def _get_qty_rfa_approved(self, cr, uid, branch_id, division, product_id):
        return 0

    def _get_qty_picking(self,cr,uid,branch_id,division,product_id):
        qty_picking_product = 0
        obj_picking = self.pool.get('stock.picking')
        obj_move = self.pool.get('stock.move')
        picking_type = self._get_picking_type(cr, uid, branch_id)
        if picking_type:
            picking_ids = obj_picking.search(cr,uid,
                                            [('branch_id','=',branch_id),
                                             ('division','=',division),
                                             ('picking_type_id','in',picking_type),
                                             ('state','not in',('draft','cancel','done'))
                                             ])
            if picking_ids:
                move_ids = obj_move.search(cr,uid,[('picking_id','in',picking_ids),('product_id','=',product_id)])
                if move_ids:
                    for move in obj_move.browse(cr,uid,move_ids):
                        qty_picking_product+=move.product_uom_qty
        return qty_picking_product
    
    def _get_qty_lot(self,cr,uid,branch_id,product_id):
        qty_lot_product = 0
        obj_lot = self.pool.get('stock.production.lot')
        lot_ids = obj_lot.search(cr,uid,
                                [('branch_id','=',branch_id),
                                ('product_id','=',product_id),
                                ('state','in',['intransit', 'stock','sold','sold_offtr','paid','paid_offtr']),
                                ('location_id.usage','=','internal'),
                                ('ready_for_sale','=','good'),
                                ])
        return len(lot_ids)
    
    def _get_qty_quant(self,cr,uid,branch_id,product_id):
        qty_in_quant = 0
        obj_quant = self.pool.get('stock.quant')
        location_ids = self._get_location(cr, uid, branch_id)
        if location_ids:
            quant_ids = obj_quant.search(cr,uid,
                                         [('location_id','in',location_ids),
                                          ('product_id','=',product_id),
                                          ('consolidated_date','!=',False)
                                          ])
     
            if quant_ids:
                for quant in obj_quant.browse(cr,uid,quant_ids):
                    qty_in_quant+=quant.qty
        return qty_in_quant
    
    def compare_sale_stock(self,cr,uid,branch_id,division,product_id,qty):
        """ membandingkan qty per product di sale order/mutation order MD + confirmed sale order/mutation dengan stock RFS
        jika qty penjumlahan tsb melebihi stock maka tidak bisa continue
        """
        picking_obj = self.pool.get('stock.picking')
        move_obj = self.pool.get('stock.move')
        if division=='Unit':
            qty_in_picking = self._get_qty_picking(cr,uid,branch_id,division,product_id)
            qty_in_lot = self._get_qty_lot(cr, uid, branch_id, product_id)
            if (qty_in_picking+qty)>qty_in_lot:
                raise osv.except_osv(('Tidak Bisa Confirm !'), 
                 ("Stock product %s tidak mencukupi Jumlah Stock yang ada %s, Stock yang sedang dalam proses %s , Qty di SO %s" % (self.pool.get('product.product').browse(cr,uid,product_id)['name'],qty_in_lot,qty_in_picking,qty) ))
        elif division=='Sparepart':
            qty_in_picking = self._get_qty_picking(cr,uid,branch_id,division,product_id)
            qty_in_quant = self._get_qty_quant(cr, uid, branch_id, product_id)
            if (qty_in_picking+qty)>qty_in_quant:
                raise osv.except_osv(('Tidak Bisa Confirm !'), ("Stock product %s tidak mencukupi Jumlah Stock yang ada %s, Stock yang sedang dalam proses %s , Qty di SO %s" % (self.pool.get('product.product').browse(cr,uid,product_id)['name'],qty_in_quant,qty_in_picking,qty) ))
        return True
    
    def compare_sale_rfa_approved_stock(self, cr, uid, branch_id, division, product_id, qty):
        self.compare_sale_stock(branch_id, division, product_id, qty)

    def get_purchase_line_id(self, cr, uid, ids, id_product, context=None):
        picking_id = self.browse(cr, uid, ids, context=context)
        id_purchase_line = 0
        for move in picking_id.move_lines :
            if move.product_id.id == id_product :
                id_purchase_line = move.purchase_line_id.id
        return id_purchase_line
    