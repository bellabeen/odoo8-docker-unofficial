from openerp.osv import fields, osv
from openerp import SUPERUSER_ID
from datetime import datetime
from openerp.tools.translate import _
import base64

class wtc_stock_inventory(osv.osv):
    _inherit = 'stock.inventory'
    
    INVENTORY_STATE_SELECTION = [
        ('draft', 'Draft'),
        ('cancel', 'Cancelled'),
        ('confirm', 'Confirmed'),
        ('closed','Closed'),
        ('done', 'Validated'),
    ]
    
    def _get_dev_min(self, cr, uid, ids, field_name, arg, context=None):
        mine_id = self.browse(cr, uid, ids, context=context)
        dev_min = 0
        if mine_id :
            for line in mine_id.line_ids :
                deviation = line.product_qty - line.theoretical_qty
                if deviation < 0 :
                    dev_min += deviation
        return {mine_id.id:dev_min}
    
    def _get_dev_plus(self, cr, uid, ids, field_name, arg, context=None):
        mine_id = self.browse(cr, uid, ids, context=context)
        dev_plus = 0
        if mine_id :
            for line in mine_id.line_ids :
                deviation = line.product_qty - line.theoretical_qty
                if deviation > 0 :
                    dev_plus += deviation
        return {mine_id.id:dev_plus}
    
    def _get_theoretical_qty(self, cr, uid, ids, field_name, arg, context=None):
        mine_id = self.browse(cr, uid, ids, context=context)
        theoretical_qty = 0
        if mine_id :
            for line in mine_id.line_ids :
                theoretical_qty += line.theoretical_qty
        return {mine_id.id:theoretical_qty}
    
    def _get_prod_qty(self, cr, uid, ids, field_name, arg, context=None):
        mine_id = self.browse(cr, uid, ids, context=context)
        prod_qty = 0
        if mine_id :
            for line in mine_id.line_ids :
                prod_qty += line.product_qty
        return {mine_id.id:prod_qty}
    
    def _get_amount_total(self, cr, uid, ids, field_name, arg, context=None):
        mine_id = self.browse(cr, uid, ids, context=context)
        amount = 0
        if mine_id :
            for line in mine_id.line_ids :
                amount += line.price_unit * line.deviation
        return {mine_id.id:amount}
    
    def _get_default_date(self,cr,uid,context):
        return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)
    
    _columns = {
        'confirm_uid': fields.many2one('res.users', string="Validated by"),
        'confirm_date': fields.datetime('Validated on'),
        'cancel_uid': fields.many2one('res.users', string="Cancelled by"),
        'cancel_date': fields.datetime('Cancelled on'),
        'close_uid': fields.many2one('res.users', string="Closed by"),
        'close_date': fields.datetime('Closed on'),
        'state': fields.selection(INVENTORY_STATE_SELECTION, 'Status', readonly=True, select=True, copy=False),
        'division': fields.selection([('Unit','Unit'),('Sparepart','Sparepart'),('Extras','Extras'),('Umum','Umum')], string='Division'),
        'start_date': fields.datetime('Start Date'),
        'end_date': fields.datetime('End Date'),
        'remark': fields.text('Remark'),
        'all_location': fields.boolean('All Location'),
        'total_deviation_minus': fields.function(_get_dev_min, string='Total Deviation (-)'),
        'total_deviation_plus': fields.function(_get_dev_plus, string='Total Deviation (+)'),
        'total_theoretical_qty': fields.function(_get_theoretical_qty, string='Total Theoretical Qty'),
        'total_product_qty': fields.function(_get_prod_qty, string='Total Real Qty'),
        'amount_total': fields.function(_get_amount_total, string='Amount Total'),
        'is_scrap': fields.boolean('Is Scrap', default=False),
        'data_x': fields.binary('File', readonly=True),
        'import_file': fields.binary('Import'),
        }
    
    _sql_constraints = [
        ('unique_name', 'unique(name)', 'Nama Inventory Adjustment sudah pernah ada !'),
        ]
    
    def default_get(self, cr, uid, fields, context=None):
         context = context or {}
         res = super(wtc_stock_inventory, self).default_get(cr, uid, fields, context=context)
         if 'location_id' in fields :
             res.update({'location_id': False})
         return res
    
    def create(self, cr, uid, vals, context=None):
        location_id = self.pool.get('stock.location').browse(cr, uid, vals['location_id'])
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, location_id.branch_id.id, 'IT')
        return super(wtc_stock_inventory, self).create(cr, uid, vals, context=context)
    
    def unlink(self, cr, uid, ids, context=None):
        stock_inventory_id = self.browse(cr, uid, ids, context=context)
        if stock_inventory_id.state != 'draft' :
            raise osv.except_osv(('Perhatian !'), ('Tidak bisa dihapus jika state bukan Draft!'))
        return super(wtc_stock_inventory, self).unlink(cr, uid, ids, context=context)
    
    def prepare_inventory(self, cr, uid, ids, context=None):
        vals = super(wtc_stock_inventory, self).prepare_inventory(cr, uid, ids, context=context)
        self.write(cr, uid, ids, {'start_date':datetime.now()})
        scrap_ids = []
        hrt_ids = []
        for inventory in self.browse(cr, uid, ids, context=context):
            if inventory.is_scrap :
                scrap_ids.append(inventory.id)
            if inventory.division == 'Sparepart' or inventory.division == 'Umum' :
                hrt_ids.append(inventory.id)

        if len(scrap_ids)>0 :
            cr.execute('''
                update stock_inventory_line set product_qty = theoretical_qty where inventory_id in %s
            ''', (tuple(scrap_ids),))

        if len(hrt_ids)>0:
            cr.execute('''
                update stock_inventory_line sil set price_unit = ppb.cost
                from product_price_branch ppb, stock_location loc
                where sil.location_id = loc.id
                and sil.product_id = ppb.product_id
                and loc.warehouse_id = ppb.warehouse_id
                and sil.inventory_id in %s
            ''', (tuple(hrt_ids),))

        return vals
    
    def action_cancel_inventory(self, cr, uid, ids, context=None):
        for inv in self.browse(cr, uid, ids, context=context):
            self.pool.get('stock.move').action_cancel(cr, uid, [x.id for x in inv.move_ids], context=context)
            self.write(cr, uid, [inv.id], {'state': 'cancel'}, context=context)
        self.write(cr, uid, ids, {'cancel_uid':uid, 'cancel_date':datetime.now()})
        return True
    
    def write_price_unit(self, cr, uid, ids, context=None):
        inventory_id = self.browse(cr, uid, ids, context=context)
        for line in inventory_id.line_ids :
            if line.deviation < 0 :
                price_unit = line.get_price_unit()
                line.write({'price_unit':price_unit})
        inventory_id.refresh()
        return True
    
    def action_done(self, cr, uid, ids, context=None):
        self.write_price_unit(cr, uid, ids, context)
        vals = super(wtc_stock_inventory, self).action_done(cr, uid, ids, context=context)
        self.write(cr, uid, ids, {'confirm_uid':uid, 'confirm_date':datetime.now()})
        return vals
    
    def action_close(self, cr, uid, ids, context=None):
        for inventory in self.browse(cr, uid, ids, context=context):
            for line in inventory.line_ids :
                if line.product_qty > line.theoretical_qty and line.price_unit <= 0 and inventory.division != 'Extras':
                    raise osv.except_osv(('Perhatian'), ('Unit Price untuk koreksi plus tidak boleh 0:\n\t%s - Deviation: %s' % (line.product_id.name, line.deviation)))
        self.write(cr, uid, ids, {'close_uid':uid, 'close_date':datetime.now(), 'end_date':datetime.now(), 'state':'closed'})
        return True
    
    def action_open(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'confirm'})
        return True
    
    def _get_inventory_lines(self, cr, uid, inventory, context=None):
        location_obj = self.pool.get('stock.location')
        product_obj = self.pool.get('product.product')
        location_ids = [inventory.location_id.id]
        if inventory.all_location :
            location_ids = location_obj.search(cr, uid, [('id', 'child_of', [inventory.location_id.id])], context=context)
        domain = ' location_id in %s'
        args = (tuple(location_ids),)
        if inventory.partner_id:
            domain += ' and owner_id = %s'
            args += (inventory.partner_id.id,)
        if inventory.lot_id:
            domain += ' and lot_id = %s'
            args += (inventory.lot_id.id,)
        if inventory.product_id:
            domain += ' and product_id = %s'
            args += (inventory.product_id.id,)
        elif inventory.division :
            domain += ' and product_id in %s'
            ids_categ = self.pool.get('product.category').get_child_ids(cr, uid, [], inventory.division)
            ids_product = self.pool.get('product.product').search(cr, uid, [('categ_id','in',ids_categ)])
            args += (tuple(ids_product),)
        if inventory.package_id:
            domain += ' and package_id = %s'
            args += (inventory.package_id.id,)

        cr.execute('''
           SELECT product_id, sum(qty) as theoretical_qty, location_id, lot_id as prod_lot_id, package_id, owner_id as partner_id
           FROM stock_quant WHERE''' + domain + '''
           GROUP BY product_id, location_id, lot_id, package_id, partner_id
        ''', args)
        vals = []
        for product_line in cr.dictfetchall():
            #replace the None the dictionary by False, because falsy values are tested later on
            for key, value in product_line.items():
                if not value:
                    product_line[key] = False
            product_line['inventory_id'] = inventory.id
            product_line['theoretical_qty']
            product_line['product_qty'] = 0
            if product_line['product_id']:
                product = product_obj.browse(cr, uid, product_line['product_id'], context=context)
                product_line['product_uom_id'] = product.uom_id.id
            vals.append(product_line)
        return vals
    
    def action_picking_create(self, cr, uid, ids, context=None):
        obj_me = self.browse(cr, uid, ids)
        obj_picking = self.pool.get('stock.picking')
        for inventory in obj_me :
            picking_in_new = obj_picking.search(cr,uid,[('transaction_id','=',inventory.id),
                                           ('model_id','=',self.pool.get('ir.model').search(cr, uid, [('model','=',inventory.__class__.__name__)])[0]),
                                           ('picking_type_id','=',inventory.location_id.warehouse_id.in_type_id.id or inventory.location_id.branch_id.warehouse_id.in_type_id.id)
                                           ])
            picking_out_new = obj_picking.search(cr,uid,[('transaction_id','=',inventory.id),
                                           ('model_id','=',self.pool.get('ir.model').search(cr, uid, [('model','=',inventory.__class__.__name__)])[0]),
                                           ('picking_type_id','=',inventory.location_id.warehouse_id.out_type_id.id or inventory.location_id.branch_id.warehouse_id.out_type_id.id,)
                                           ])
            if picking_in_new and picking_out_new:
                return (picking_in_new[0], picking_out_new[0])
                
            picking_in = {
                'branch_id': inventory.location_id.branch_id.id,
                'division': inventory.division if inventory.division != 'Extras' else 'Umum',
                'date': inventory.date,
                'start_date': inventory.start_date,
                'end_date': inventory.end_date,
                'origin': inventory.name,
                'transaction_id': inventory.id,
                'model_id': self.pool.get('ir.model').search(cr, uid, [('model','=',inventory.__class__.__name__)])[0],
                'picking_type_id': inventory.location_id.warehouse_id.in_type_id.id or inventory.location_id.branch_id.warehouse_id.in_type_id.id,
                'min_date': inventory.end_date
            }
            picking_out = {
                'branch_id': inventory.location_id.branch_id.id,
                'division': inventory.division if inventory.division != 'Extras' else 'Umum',
                'date': inventory.date,
                'start_date': inventory.start_date,
                'end_date': inventory.end_date,
                'origin': inventory.name,
                'transaction_id': inventory.id,
                'model_id': self.pool.get('ir.model').search(cr, uid, [('model','=',inventory.__class__.__name__)])[0],
                'picking_type_id': inventory.location_id.warehouse_id.out_type_id.id or inventory.location_id.branch_id.warehouse_id.out_type_id.id,
                'min_date': inventory.end_date
            }
            picking_in_id = obj_picking.create(cr, uid, picking_in, context=context)
            picking_out_id = obj_picking.create(cr, uid, picking_out, context=context)
        return (picking_in_id, picking_out_id)
    
    def import_wizard(self,cr,uid,ids,context=None):
        data = self.browse(cr,uid,ids)
        obj_ir_view = self.pool.get("ir.ui.view")
        obj_ir_view_search= obj_ir_view.search(cr,uid,[("name", "=", 'wtc.stock.inventory.import.wizard'), ("model", "=", 'stock.inventory'),])
        obj_ir_view_browse = obj_ir_view.browse(cr,uid,obj_ir_view_search)
        return {
            'name': 'Import Inventory Adjustment',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.inventory',
            'type': 'ir.actions.act_window',
            'view_id' : obj_ir_view_browse.id,
            'nodestroy': True,
            'target': 'new',
            'res_id': data.id
            } 
        
    def action_import(self,cr,uid,ids,context=None):
        data = self.browse(cr,uid,ids)
        if not data.import_file:
            raise osv.except_osv(('Perhatian !'), ("Silahkan pilih file yang akan diimport terlebih dahulu!"))
        
        file=base64.decodestring(data.import_file)
        ct = file.splitlines()
        obj_sil = self.pool.get('stock.inventory.line')
        for n in ct:
            line = n.split(',')
            sil = obj_sil.search(cr,uid,[('id','=',line[0]),('inventory_id','=',data.id)])

            if not sil:
                raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan detil inventory adjustment dengan id %s inventory adjustment %s!") %(line[0],data.name))
            else:
                obj_sil.write(cr,uid,sil,{'product_qty':line[1]})
        
    def post_inventory(self, cr, uid, inv, context=None):
        date = self._get_default_date(cr, uid, context)
        period_id = self.pool.get('account.period').find(cr,uid,date)[0]
        inv.write({'period_id':period_id})
        post=super(wtc_stock_inventory, self).post_inventory(cr, uid, inv, context=context)
        picking_ids = []
        for line in inv.move_ids:
            #create pack ops for report requirement
            pack_datas = {
                    'product_id': line.product_id.id,
                    'product_uom_id': line.product_uom.id,
                    'product_qty': line.product_uom_qty,
                    'lot_id': line.restrict_lot_id.id if line.restrict_lot_id else False,
                    'location_id': line.location_id.id,
                    'location_dest_id': line.location_dest_id.id,
                    'date': date,
                    'owner_id': line.picking_id.owner_id.id,
                    'picking_id': line.picking_id.id
                }
            self.pool.get('stock.pack.operation').create(cr,uid,pack_datas)
            if line.picking_id.id not in picking_ids:
                picking_ids.append(line.picking_id.id)
            if line.location_dest_id.usage=='internal':
                for quant in line.quant_ids:
                    quant.sudo().write({'consolidated_date':date})
                    
        update_pick = self.pool.get('stock.picking').write(cr,uid,picking_ids,{'date_done':datetime.now()})
        
            
class stock_inventory_line(osv.osv):
    _inherit = 'stock.inventory.line'
    
    def _get_selisih(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for line in self.browse(cr, uid, ids, context=context):
            result[line.id] = line.product_qty - line.theoretical_qty
        return result
    
    _columns = {
        'deviation': fields.function(_get_selisih, string='Deviation'),
        'price_unit': fields.float('Unit Price'),
        }
    
    def _resolve_inventory_line(self, cr, uid, inventory_line, context=None):
        picking_in, picking_out = inventory_line.inventory_id.action_picking_create()
        stock_move_obj = self.pool.get('stock.move')
        picking_obj = self.pool.get('stock.picking')
        diff = inventory_line.theoretical_qty - inventory_line.product_qty
        if not diff:
            return
        #each theorical_lines where difference between theoretical and checked quantities is not 0 is a line for which we need to create a stock move
        vals = {
            'name': _('INV:') + (inventory_line.inventory_id.name or ''),
            'product_id': inventory_line.product_id.id,
            'product_uom': inventory_line.product_uom_id.id,
            'date': inventory_line.inventory_id.date,
            'company_id': inventory_line.inventory_id.company_id.id,
            'inventory_id': inventory_line.inventory_id.id,
            'state': 'confirmed',
            'restrict_lot_id': inventory_line.prod_lot_id.id,
            'restrict_partner_id': inventory_line.partner_id.id,
            'branch_id': inventory_line.location_id.branch_id.id,
         }
        inventory_location_ids = self.pool.get('stock.location').search(cr, SUPERUSER_ID, [
            ('branch_id','=',inventory_line.location_id.branch_id.id),
            ('usage','=','inventory'),
            ('name','like','%Inventory Loss')
            ])
        if not inventory_location_ids :
            raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan lokasi inventory loss untuk cabang '%s'!"%inventory_line.location_id.branch_id.name))
        if diff < 0:
            #found more than expected
            vals['location_id'] = inventory_location_ids[0]
            vals['location_dest_id'] = inventory_line.location_id.id
            vals['product_uom_qty'] = -diff
            vals['price_unit'] = inventory_line.price_unit * 1.1
            vals['real_hpp'] = 0
            vals['picking_id'] = picking_in
            vals['picking_type_id'] = picking_obj.browse(cr, uid, picking_in).picking_type_id.id
        else:
            self.check_qty(cr, uid, inventory_line.id, inventory_line.location_id, inventory_line.product_id, diff, context)
            #found less than expected
            vals['location_id'] = inventory_line.location_id.id
            vals['location_dest_id'] = inventory_location_ids[0]
            vals['product_uom_qty'] = diff
            vals['price_unit'] = 0
            vals['real_hpp'] = inventory_line.price_unit
            vals['picking_id'] = picking_out
            vals['picking_type_id'] = picking_obj.browse(cr, uid, picking_out).picking_type_id.id
        return stock_move_obj.create(cr, uid, vals, context=context)
    
    def check_qty(self, cr, uid, ids, location_id, product_id, diff, context=None):
        warning = {}
        tot_qty = 0
        obj_quant = self.pool.get('stock.quant')
        ids_quant = obj_quant.search(cr, SUPERUSER_ID, [
            ('product_id','=',product_id.id),
            ('location_id','=',location_id.id)
            ])
        if not ids_quant :
            raise osv.except_osv(('Perhatian !'), ("Produk '%s' di lokasi '%s' tidak mencukupi, Theoretical Quantity mungkin sudah berubah !" %(product_id.name_template,location_id.name)))
        quant_ids = obj_quant.browse(cr, SUPERUSER_ID, ids_quant)
        for quant_id in quant_ids :
            tot_qty += quant_id.qty
        if tot_qty < diff :
            raise osv.except_osv(('Perhatian !'), ("Produk '%s' di lokasi '%s' tidak mencukupi, Theoretical Quantity mungkin sudah berubah !" %(product_id.name_template,location_id.name)))
        return {'warning':warning}
    
    def get_price_unit(self, cr, uid, ids, context=None):
        cost = 0
        line = self.browse(cr, uid, ids, context)
        diff = line.product_qty - line.theoretical_qty
        if diff < 0 :
            location_id = self.pool.get('stock.location').browse(cr, uid, line.location_id.id)
            id_warehouse = location_id.warehouse_id.id or location_id.branch_id.warehouse_id.id
            id_product_price_branch = self.pool.get('product.price.branch').search(cr, uid, [('product_id','=',line.product_id.id),('warehouse_id','=',id_warehouse)])
            product_price_branch_id = self.pool.get('product.price.branch').browse(cr, uid, id_product_price_branch)
            cost = product_price_branch_id.cost
        return cost
    
    def price_unit_change(self, cr, uid, ids, price_unit, theoretical_qty, product_qty, id_location, id_product, context=None):
        value = {}
        diff = product_qty - theoretical_qty
        if diff < 0 :
            location_id = self.pool.get('stock.location').browse(cr, uid, id_location)
            id_warehouse = location_id.warehouse_id.id or location_id.branch_id.warehouse_id.id
            id_product_price_branch = self.pool.get('product.price.branch').search(cr, uid, [('product_id','=',id_product),('warehouse_id','=',id_warehouse)])
            product_price_branch_id = self.pool.get('product.price.branch').browse(cr, uid, id_product_price_branch)
            value['price_unit'] = product_price_branch_id.cost
        return {'value':value}
    
    def product_qty_change(self, cr, uid, ids, price_unit, theoretical_qty, product_qty, id_location, id_product, context=None):
        value = {}
        diff = product_qty - theoretical_qty
        if diff < 0 :
            location_id = self.pool.get('stock.location').browse(cr, uid, id_location)
            id_warehouse = location_id.warehouse_id.id or location_id.branch_id.warehouse_id.id
            id_product_price_branch = self.pool.get('product.price.branch').search(cr, uid, [('product_id','=',id_product),('warehouse_id','=',id_warehouse)])
            product_price_branch_id = self.pool.get('product.price.branch').browse(cr, uid, id_product_price_branch)
            value['price_unit'] = product_price_branch_id.cost
        else :
            value['price_unit'] = 0
        return {'value':value}
    
            
        
        
    
    
    