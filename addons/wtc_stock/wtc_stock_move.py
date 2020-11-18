from openerp.osv import fields, osv
from datetime import datetime

class wtc_stock_move(osv.osv):
    _inherit = 'stock.move'
    
    def _get_division(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for x in self.browse(cr, uid, ids, context=context) :
            result[x.id] = self.pool.get('product.category').get_root_name(cr, uid, x.categ_id.id)
        return result

    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids
        
    _columns = {
                'branch_id': fields.many2one('wtc.branch', string='Branch'),
                'categ_id': fields.many2one('product.category', 'Category'),
                'func_division': fields.function(_get_division, string="Division", type="char"),
                'stock_available': fields.float('Stock Available', digits=(10,0)),
                'rel_stock_available': fields.related('stock_available', string='Stock Available', digits=(10,0)),
                'confirm_uid':fields.many2one('res.users',string="Confirmed by"),
                'confirm_date':fields.datetime('Confirmed on'),
                'cancel_uid':fields.many2one('res.users',string="Cancelled by"),
                'cancel_date':fields.datetime('Cancelled on'),
                'undelivered_value': fields.float('Undelivered Value'),
                'real_hpp': fields.float('Real HPP'),
                'is_rfs': fields.boolean('RFS?')                
                }
    
    _sql_constraints = [
                        ('unique_lot', 'unique(picking_id,restrict_lot_id)', 'Ditemukan Lot duplicate, Silahkan cek kembali !'),
                        ]
    
    _defaults = {
                 'branch_id': _get_default_branch,
                 }
    
    def lot_qty_change(self, cr, uid, ids, product_uom_qty, product_uom, restrict_lot_id, context=None) :
        value = {}
        value['product_uos'] = product_uom
        if restrict_lot_id :
            value['product_uom_qty'] = 1
            value['product_uos_qty'] = 1
            
            lot_browse = self.pool.get('stock.production.lot').browse(cr,uid,restrict_lot_id)
            if lot_browse.ready_for_sale=='good':
                value['is_rfs']=True
            else:
                value['is_rfs']=False
        else :
            value['product_uos_qty'] = product_uom_qty
        return {'value':value}
    
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
            and (q.lot_id is Null or l.state = 'stock')
        """,(id_product,id_location))
        return cr.fetchall()[0][0]
    
    def get_lot_available(self, cr, uid, ids, id_product, id_location, context=None):
        ids_lot_available = []
        cr.execute("""
        SELECT
            l.id
        FROM
            stock_quant q
        JOIN
            stock_production_lot l on l.id = q.lot_id
        WHERE
            q.product_id = %s and q.location_id = %s and l.state = 'stock' and q.reservation_id is Null and q.consolidated_date is not Null
        """,(id_product,id_location))
        for id_lot in cr.fetchall() :
            ids_lot_available.append(id_lot[0])
        return ids_lot_available
    
    def categ_id_change(self, cr, uid, ids, branch_id, division, categ_id, source, context=None):
        val = {}
        dom = {}
        war = {}
        obj_categ = self.pool.get('product.category')
        val['product_id'] = False
        val['restrict_lot_id'] = False
        
        if categ_id and not source :
            val['categ_id'] = False
            war = {'title':'Perhatian !', 'message':'Silahkan isi Source Location terlebih dahulu'}
            return {'warning':war, 'value':val}
        elif categ_id and not branch_id :
            val['categ_id'] = False
            war = {'title':'Perhatian !', 'message':'Silahkan isi Branch terlebih dahulu'}
            return {'warning':war, 'value':val}
        elif categ_id and source :
            val['func_division'] = obj_categ.get_root_name(cr, uid, categ_id)
            
            cr.execute("""SELECT
                q.product_id
            FROM
                stock_quant q
            LEFT JOIN
                product_product p on (p.id=q.product_id)
            LEFT JOIN
                stock_location l on (l.id=q.location_id)
            LEFT JOIN
                wtc_branch b on (b.id=l.branch_id)
            WHERE
                q.location_id=%s and l.branch_id=%s""",(source,branch_id))
            result = cr.fetchall()
            dom['product_id'] = [('categ_id','=',categ_id),('id','in',result)]
            
        return {'domain':dom, 'value':val, 'warning':war}
    
    def picking_branch_id_change(self, cr, uid, ids, categ_id, branch_id, division, type, source, destination, context=None):
        if not type :
            raise osv.except_osv(('Data header belum lengkap !'), ('Sebelum menambah detil harap isi data header terlebih dahulu'))
        elif not branch_id or not division :
            raise osv.except_osv(('Data header belum lengkap !'), ('Sebelum menambah detil harap isi data header terlebih dahulu'))
        val = {}
        dom = {}
        obj_categ = self.pool.get('product.category')
        picking_type_id = self.pool.get('stock.picking.type').browse(cr, uid, type)
        
        cr.execute("""SELECT
            q.product_id
        FROM
            stock_quant q
        LEFT JOIN
            product_product p on (p.id=q.product_id)
        LEFT JOIN
            stock_location l on (l.id=q.location_id)
        LEFT JOIN
            wtc_branch b on (b.id=l.branch_id)
        WHERE
            q.location_id=%s and l.branch_id=%s""",(picking_type_id.default_location_src_id.id,branch_id))
        result = cr.fetchall()
        
        categ_ids = obj_categ.get_child_ids(cr, uid, ids, division)
        dom['product_id'] = [('categ_id','in',categ_ids),('id','in',result)]
        
        val['branch_id'] = branch_id
        val['restrict_lot_id'] = False
        val['func_division'] = division
        val['location_id'] = picking_type_id.default_location_src_id.id
        val['location_dest_id'] = picking_type_id.default_location_dest_id.id
        
        return {'domain':dom, 'value':val}
    
    def internal_stock_available_change(self, cr, uid, ids, stock_available, context=None):
        value = {}
        value['rel_stock_available'] = stock_available
        return {'value':value}
    
    def internal_product_qty_change(self, cr, uid, ids, stock_available, id_branch, division, id_product, qty, id_picking_type, source, destination, restrict_lot_id, context=None):
        if not id_branch or not division or not id_picking_type or not source or not destination :
            raise osv.except_osv(('Data header belum lengkap !'), ('Sebelum menambah detil harap isi data header terlebih dahulu'))
        val = {}
        war = {}
        dom = {}
        obj_categ = self.pool.get('product.category')
        product_id = self.pool.get('product.product').browse(cr, uid, id_product)
        obj_pu = self.pool.get('product.uom')
        if id_product :
            if restrict_lot_id not in self.get_lot_available(cr, uid, ids, id_product, source, context) :
                val['restrict_lot_id'] = False
            dom['restrict_lot_id'] = [('id','in',self.get_lot_available(cr, uid, ids, id_product, source, context))]
            val['stock_available'] = self.get_stock_available(cr, uid, ids, id_product, source, context)
        
        cr.execute("""
        SELECT
            q.product_id
        FROM
            stock_quant q
        LEFT JOIN
            stock_production_lot l on l.id = q.lot_id
        WHERE
            q.location_id = %s and q.reservation_id is Null and q.consolidated_date is not Null
            and (q.lot_id is Null or l.state = 'stock')
        """,(source,))
        
        result = cr.fetchall()
        categ_ids = obj_categ.get_child_ids(cr, uid, ids, division)
        dom['product_id'] = [('categ_id','in',categ_ids),('id','in',result)]
        
        val['branch_id'] = id_branch
        val['func_division'] = division
        
        id_pu = obj_pu.search(cr, uid, [('name','like','Unit')])
        if len(id_pu)>0:
            id_pu=id_pu[0]
        val['product_uom'] = id_pu
        val['product_uos'] = id_pu
        val['picking_type_id'] = id_picking_type
        val['location_id'] = source
        val['location_dest_id'] = destination
        if product_id :
            val['name'] = product_id.description
            val['categ_id'] = product_id.categ_id.id
        val['product_uos_qty'] = qty
        if qty :
            if qty < 0 :
                val['product_uom_qty'] = stock_available
                val['product_uos_qty'] = stock_available
                war = {'title':'Perhatian !', 'message':'Quantity tidak boleh kurang dari nol'}
            elif division <> 'Unit' and qty > stock_available and id_product:
                val['product_uom_qty'] = stock_available
                val['product_uos_qty'] = stock_available
                war = {'title':'Perhatian !', 'message':'Quantity tidak boleh lebih dari stock available'}
        
        if division == 'Unit' :
            val['product_uom_qty'] = 1
            val['product_uos_qty'] = 1
        
        return {'value':val, 'warning':war, 'domain':dom}
    
    def onchange_product_id(self, cr, uid, ids, prod_id=False, loc_id=False, loc_dest_id=False, partner_id=False):
        result = super(wtc_stock_move,self).onchange_product_id(cr, uid, ids, prod_id=prod_id, loc_id=loc_id, loc_dest_id=loc_dest_id, partner_id=partner_id)
        if prod_id :
            id_categ = self.pool.get('product.product').browse(cr, uid, prod_id).categ_id.id
            result['value'].update({'categ_id': id_categ})
            result['value'].update({'restrict_lot_id': False})
        return result
    
    def action_done(self, cr, uid, ids, context=None):  
        self.write(cr,uid,ids,{'confirm_uid':uid,'confirm_date':datetime.now()})        
        vals = super(wtc_stock_move,self).action_done(cr,uid,ids,context=context)  
        return vals
    
    def action_cancel(self, cr, uid, ids, context=None):
        self.write(cr,uid,ids,{'cancel_uid':uid,'cancel_date':datetime.now()})        
        vals = super(wtc_stock_move,self).action_cancel(cr,uid,ids,context=context)  
        return vals
    
    def action_assign(self, cr, uid, ids, context=None):
        """ Checks the product type and accordingly writes the state.
        """
        context = context or {}
        quant_obj = self.pool.get("stock.quant")
        to_assign_moves = []
        main_domain = {}
        todo_moves = []
        operations = set()
        for move in self.browse(cr, uid, ids, context=context):
            if move.state not in ('confirmed', 'waiting', 'assigned'):
                continue
            if move.location_id.usage in ('supplier', 'inventory', 'production') or (move.sudo().branch_id.branch_type == 'MD' and move.picking_id.division == 'Unit' and move.picking_id.picking_type_id.code == 'outgoing' and not move.picking_id.is_reverse) or (move.picking_id.division == 'Unit' and move.picking_id.picking_type_id.code == 'interbranch_out' and not move.picking_id.is_reverse):
                to_assign_moves.append(move.id)
                #in case the move is returned, we want to try to find quants before forcing the assignment
                if not move.origin_returned_move_id:
                    continue
            if move.product_id.type == 'consu':
                to_assign_moves.append(move.id)
                continue
            else:
                todo_moves.append(move)

                #we always keep the quants already assigned and try to find the remaining quantity on quants not assigned only
                main_domain[move.id] = [('reservation_id', '=', False), ('qty', '>', 0)]
                
#                 if move.picking_id.is_unconsolidated_reverse:
#                     context.update({'is_unconsolidated_reverse': True})

                #if the move is preceeded, restrict the choice of quants in the ones moved previously in original move
                ancestors = self.find_move_ancestors(cr, uid, move, context=context)
                if move.state == 'waiting' and not ancestors:
                    #if the waiting move hasn't yet any ancestor (PO/MO not confirmed yet), don't find any quant available in stock
                    main_domain[move.id] += [('id', '=', False)]
                elif ancestors:
                    main_domain[move.id] += [('history_ids', 'in', ancestors)]

                #if the move is returned from another, restrict the choice of quants to the ones that follow the returned move
                if move.origin_returned_move_id:
                    main_domain[move.id] += [('history_ids', 'in', move.origin_returned_move_id.id)]
                for link in move.linked_move_operation_ids:
                    operations.add(link.operation_id)
        # Check all ops and sort them: we want to process first the packages, then operations with lot then the rest
        operations = list(operations)
        operations.sort(key=lambda x: ((x.package_id and not x.product_id) and -4 or 0) + (x.package_id and -2 or 0) + (x.lot_id and -1 or 0))
        for ops in operations:
            #first try to find quants based on specific domains given by linked operations
            for record in ops.linked_move_operation_ids:
                move = record.move_id
                if move.id in main_domain:
                    domain = main_domain[move.id] + self.pool.get('stock.move.operation.link').get_specific_domain(cr, uid, record, context=context)
                    qty = record.qty
                    if qty:
                        quants = quant_obj.quants_get_prefered_domain(cr, uid, ops.location_id, move.product_id, qty, domain=domain, prefered_domain_list=[], restrict_lot_id=move.restrict_lot_id.id, restrict_partner_id=move.restrict_partner_id.id, context=context)
                        quant_obj.quants_reserve(cr, uid, quants, move, record, context=context)
        for move in todo_moves:
            if move.linked_move_operation_ids:
                continue
            move.refresh()
            #then if the move isn't totally assigned, try to find quants without any specific domain
            if move.state != 'assigned':
                qty_already_assigned = move.reserved_availability
                qty = move.product_qty - qty_already_assigned
                if move.picking_id.is_unconsolidated_reverse:
                    context_unconsolidated_reverse = context.copy()
                    context_unconsolidated_reverse['unconsolidated_reverse']=True
                    quants = quant_obj.quants_get_prefered_domain(cr, uid, move.location_id, move.product_id, qty, domain=main_domain[move.id], prefered_domain_list=[], restrict_lot_id=move.restrict_lot_id.id, restrict_partner_id=move.restrict_partner_id.id, context=context_unconsolidated_reverse)
                else:
                    quants = quant_obj.quants_get_prefered_domain(cr, uid, move.location_id, move.product_id, qty, domain=main_domain[move.id], prefered_domain_list=[], restrict_lot_id=move.restrict_lot_id.id, restrict_partner_id=move.restrict_partner_id.id, context=context)
                quant_obj.quants_reserve(cr, uid, quants, move, context=context)
        
        #force assignation of consumable products and incoming from supplier/inventory/production
        if to_assign_moves:
            self.force_assign(cr, uid, to_assign_moves, context=context)
    
class wtc_stock_move_operation_link(osv.osv):
    _inherit = "stock.move.operation.link"

    def get_specific_domain(self, cr, uid, record, context=None):
        domain = super(wtc_stock_move_operation_link, self).get_specific_domain(cr, uid, record, context)
        #domain.append(('consolidated_date', '!=', False))
        return domain
