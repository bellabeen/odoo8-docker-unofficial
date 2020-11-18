import time
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from datetime import date, datetime, timedelta
from openerp import SUPERUSER_ID

class stock_production_lot(osv.osv):
    _inherit = 'stock.production.lot'
    _columns = {
                'hpp': fields.float('HPP', readonly=True, digits_compute=dp.get_precision('Product Price')),
                'performance_hpp': fields.float('Performance HPP', readonly=True, digits_compute=dp.get_precision('Product Price')),
                'consolidate_id': fields.many2one('consolidate.invoice', 'Consolidate Invoice', readonly=True),
                }

class wtc_hpp_account_invoice(osv.osv):
    _inherit = 'account.invoice'
    
    def _consolidated(self, cursor, user, ids, name, arg, context=None):
        res = {}
        for invoice in self.browse(cursor, user, ids, context=context):
            qty = {}
            for x in invoice.invoice_line :
                qty[x.product_id] = qty.get(x.product_id,0) + x.quantity - x.consolidated_qty
        res[invoice.id] = all(x[1] == 0 for x in qty.items())
        return res
    
    _columns = {
                'consolidated': fields.boolean('Invoice Consolidated')
                }

class wtc_hpp_account_invoice_line(osv.osv):
    _inherit = 'account.invoice.line'
    _columns = {
                'consolidated_qty': fields.float('Cnsldted Qty', digits=(5,0)),
                }
    
class wtc_hpp_stock_picking(osv.osv):
    _inherit = 'stock.picking'
    
    def _consolidated(self, cursor, user, ids, name, arg, context=None):
        res = {}
        for picking in self.browse(cursor, user, ids, context=context):
            qty = {}
            for x in picking.move_lines :
                qty[x.product_id] = qty.get(x.product_id,0) + x.quantity - x.consolidated_qty
        res[picking.id] = all(x[1] == 0 for x in qty.items())
        return res
    
    _columns = {
                'consolidated': fields.boolean('Picking Consolidated')
                }
    
class wtc_hpp_stock_move(osv.osv):
    _inherit = 'stock.move'
    _columns = {
                'consolidated_qty': fields.integer('Cnsldted Qty'),
                }
    
class consolidate_invoice(osv.osv):
    _name = "consolidate.invoice"
    
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
        
    def _get_default_date(self,cr,uid,context=None):
        return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)        
    _columns = {
        'branch_id':fields.many2one('wtc.branch','Branch', required=True),
        'division':fields.selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum')], 'Division', change_default=True, select=True, required=True),
        'name': fields.char('Consolidate Invoice', size=64, required=True, readonly=True, select=True, states={'draft': [('readonly', False)]}),
        'invoice_id': fields.many2one('account.invoice', 'Supplier Invoice', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'picking_id': fields.many2one('stock.picking', 'Receipt', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'date': fields.date('Date', readonly=True, select=True, states={'draft': [('readonly', False)]}),
        'state': fields.selection([('draft', 'Draft'), ('done', 'Done'), ('cancel', 'Cancel')], 'State', readonly=True, select=True),
        'consolidate_line': fields.one2many('consolidate.invoice.line', 'consolidate_id', 'Consolidate Lines', readonly=True, required=True, states={'draft': [('readonly', False)]}),
        'partner_id': fields.many2one('res.partner', 'Supplier'),
        'confirm_uid':fields.many2one('res.users',string="Approved by"),
        'confirm_date':fields.datetime('Approved on'),      
    }
    
    _defaults = {
        'name': '/',
        'date':_get_default_date,
        'state':'draft',
        'branch_id': _get_default_branch,
    }

    _order = 'name desc'
    
    def consolidate_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'draft'})
    
    def consolidate_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'cancel'})
    
    def create_move(self, cr, uid, ids, branch_id, consolidate_line):                             
        move_obj = self.pool.get('account.move')
        
        if not (consolidate_line.product_id.categ_id.property_stock_account_input_categ or consolidate_line.product_id.categ_id.property_stock_valuation_account_id or consolidate_line.product_id.categ_id.property_stock_journal):
            raise osv.except_osv(('Perhatian !'), ("Konfigurasi jurnal/account product belum lengkap!"))
        
        move_journal = {
                        'name': consolidate_line.consolidate_id.name,
                        'ref': consolidate_line.consolidate_id.invoice_id.number,
                        'journal_id': consolidate_line.product_id.categ_id.property_stock_journal.id,
                        'date': self._get_default_date(cr, uid, context=None).strftime('%Y-%m-%d'),
                        }
        
        move_line = [[0,False,{
                                'name': [str(name) for id, name in consolidate_line.product_id.name_get()][0],
                                'account_id': consolidate_line.product_id.categ_id.property_stock_account_input_categ.id,
                                'date': self._get_default_date(cr, uid, context=None).strftime('%Y-%m-%d'),
                                'debit': 0.0,
                                'credit': round(consolidate_line.price_unit*consolidate_line.product_qty,2),
                                'branch_id': branch_id,
                                'division': consolidate_line.consolidate_id.division
                               }]]
        
        move_line.append([0,False,{
                                'name': [name for id, name in consolidate_line.product_id.name_get()][0],
                                'account_id': consolidate_line.product_id.categ_id.property_stock_valuation_account_id.id,
                                'date': self._get_default_date(cr, uid, context=None).strftime('%Y-%m-%d'),
                                'debit': round(consolidate_line.price_unit*consolidate_line.product_qty,2),
                                'credit': 0.0,
                                'branch_id': branch_id,
                                'division': consolidate_line.consolidate_id.division
                               }])
        
        move_journal['line_id'] = move_line
        
        create_journal = move_obj.create(cr, uid, move_journal)
        return create_journal
    
    def write_invoice_line(self, cr, uid, ids, id_invoice, purchase_line_id, qty, context=None):
        consolidate_id = self.browse(cr, uid, ids, context)
        obj_inv_line = self.pool.get('account.invoice.line')
        id_inv_line = obj_inv_line.search(cr, uid, [('purchase_line_id','=',purchase_line_id.id),('invoice_id','=',id_invoice)])
        if not id_inv_line :
            raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan product '%s' untuk receipt '%s' di invoice yang dipilih\nPastikan Anda memilih invoice dan receipt untuk PO yang sama !" %(purchase_line_id.product_id.name,consolidate_id.invoice_id.number)))
        inv_line_id = obj_inv_line.browse(cr, uid, id_inv_line)
        qty_before = inv_line_id.consolidated_qty
        if qty_before + qty <= inv_line_id.quantity :
            inv_line_id.write({'consolidated_qty': qty_before + qty})
        else :
            product_name = inv_line_id.product_id.name
            if consolidate_id.division == 'Unit' :
                product_name += " warna " + inv_line_id.product_id.attribute_value_ids.name
            raise osv.except_osv(('Perhatian !'), ("Quantity product '%s' melebihi qty invoice untuk PO '%s',\nqty invoice '%s' qty yg sudah diconsolidate '%s' qty yg akan diconsolidate '%s' !" %(product_name,purchase_line_id.order_id.name,inv_line_id.quantity,inv_line_id.consolidated_qty,qty)))
        
    def write_move_line(self, cr, uid, ids, id_picking, purchase_line_id, qty, context=None):
        consolidate_id = self.browse(cr, uid, ids, context)
        obj_move = self.pool.get('stock.move')
        id_move = obj_move.search(cr, uid, [('purchase_line_id','=',purchase_line_id.id),('picking_id','=',id_picking)])
        move_id = obj_move.browse(cr, uid, id_move)
        qty_before = move_id.consolidated_qty
        if qty_before + qty <= move_id.product_uom_qty :
            move_id.write({'consolidated_qty': qty_before + qty})
        else :
            raise osv.except_osv(('Perhatian !'), ("Quantity product '%s' melebihi qty receipt untuk PO '%s' !" %(move_id.product_id.name,purchase_line_id.order_id.name)))
    
    def is_consolidated(self, cr, uid, ids, id_invoice, id_picking, context=None):
        obj_invoice = self.pool.get('account.invoice')
        obj_picking = self.pool.get('stock.picking')
        invoice_id = obj_invoice.browse(cr, uid, id_invoice)
        picking_id = obj_picking.browse(cr, uid, id_picking)
        if all(line.quantity == line.consolidated_qty for line in invoice_id.invoice_line) :
            invoice_id.write({'consolidated': True})
        else :
            invoice_id.write({'consolidated': False})
        
        if all(line.product_uom_qty == line.consolidated_qty for line in picking_id.move_lines) :
            picking_id.write({'consolidated': True})
        else :
            picking_id.write({'consolidated': False})
        
    def consolidate_confirm(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'date':self._get_default_date(cr, uid, context=context), 'state':'done', 'confirm_uid':uid, 'confirm_date':datetime.now()})        
        consolidate_id = self.browse(cr, uid, ids, context)
        obj_lot = self.pool.get('stock.production.lot')
        obj_quant = self.pool.get('stock.quant')
        product_price_obj = self.pool.get('product.price.branch')
        
        for line in consolidate_id.consolidate_line :
            create_move = self.create_move(cr, uid, ids, consolidate_id.branch_id.id, line)
            line.account_move_id = create_move
            new_std_price = 0
            if line.product_id.cost_method=='average':
                product_avail = self.pool.get('stock.quant')._get_stock_product_branch(cr, uid, line.move_id.location_dest_id.warehouse_id.id, line.product_id.id)
                average_price = product_price_obj._get_price(cr, uid, line.move_id.location_dest_id.warehouse_id.id, line.product_id.id)
                if product_avail <=0:
                    new_std_price = line.price_unit
                else:
                    new_std_price = ((average_price * product_avail) + (line.price_unit * line.product_qty)) / (product_avail + line.product_qty)
                self.pool.get('stock.move').update_price_branch(cr, uid, line.move_id.location_dest_id.warehouse_id.id, line.product_id.id, new_std_price)
        
        if consolidate_id.division == 'Unit' :
            for line in consolidate_id.consolidate_line :
                if not line.name :
                    raise osv.except_osv(('Perhatian !'), ("Lot tidak boleh kosong, silahkan cek kembali data Anda !"))
                obj_lot.write(cr, uid, [line.name.id], {'hpp': line.price_unit, 'state': 'stock', 'consolidate_id': consolidate_id.id, 'supplier_invoice_id': consolidate_id.invoice_id.id})
                id_quant = obj_quant.search(cr, SUPERUSER_ID, [('lot_id','=',line.name.id)])
                obj_quant.write(cr, SUPERUSER_ID, id_quant, {'cost':line.price_unit, 'consolidated_date': datetime.now()})
                self.write_invoice_line(cr, uid, ids, consolidate_id.invoice_id.id, line.purchase_line_id, line.product_qty)
                self.write_move_line(cr, uid, ids, consolidate_id.picking_id.id, line.purchase_line_id, line.product_qty)
        elif consolidate_id.division in ('Sparepart','Umum'):
            for line in consolidate_id.consolidate_line:
                id_quant = obj_quant.search(cr, SUPERUSER_ID, [('product_id','=',line.product_id.id),('history_ids','in',line.move_id.id),('consolidated_date','=',False)])
                
                for quant in obj_quant.browse(cr, SUPERUSER_ID, id_quant) :
                    if line.product_qty < quant.qty :
                        obj_quant._quant_split(cr, SUPERUSER_ID, quant, line.product_qty)
                    quant.write({'cost':line.price_unit * quant.qty, 'consolidated_date':datetime.now()})
                self.write_invoice_line(cr, uid, ids, consolidate_id.invoice_id.id, line.purchase_line_id, line.product_qty)
                self.write_move_line(cr, uid, ids, consolidate_id.picking_id.id, line.purchase_line_id, line.product_qty)
                
        self.is_consolidated(cr, uid, ids, consolidate_id.invoice_id.id, consolidate_id.picking_id.id)
    
    def create(self, cr, uid, vals, context=None):
        if not vals['consolidate_line'] :
            raise osv.except_osv(('Tidak bisa disimpan !'), ("Silahkan isi detil consolidate terlebih dahulu"))
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'CI')
        return super(consolidate_invoice, self).create(cr, uid, vals, context=context)
    
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Consolidate sudah di proses, data tidak bisa dihapus !"))
        return super(consolidate_invoice, self).unlink(cr, uid, ids, context=context)    
    
    def picking_id_change(self, cr, uid, ids, context=None):
        value = {}
        value['consolidate_line'] = False
        return {'value':value}
    
class consolidate_invoice_line(osv.osv):
    _name = 'consolidate.invoice.line' 
    _columns = {
                'consolidate_id': fields.many2one('consolidate.invoice', 'Consolidate Invoice', required=True, ondelete='cascade'),
                'name': fields.many2one('stock.production.lot', 'Lot'),
                'product_id': fields.many2one('product.product', 'Product', required=True),
                'product_qty': fields.integer('Product Qty'),
                'move_qty': fields.integer('Move Qty'),
                'move_qty_show': fields.related('move_qty',string='Move Qty'),
                'consolidated_qty': fields.integer('Consolidated Qty'),
                'move_id': fields.many2one('stock.move', 'Stock Move'),
                'purchase_line_id': fields.related('move_id', 'purchase_line_id', type='many2one', relation='purchase.order.line', string="PO Line"),
                'product_uom': fields.many2one('product.uom', 'UoM', required=True),
                'price_unit': fields.float('Unit Price', required=True, digits_compute= dp.get_precision('Product Price')),
                'account_move_id': fields.many2one('account.move', 'Account Move'),
                }
    
    _sql_constraints = [
                        ('unique_product_id', 'unique(consolidate_id,product_id,name)', 'Ditemukan Lot/Product duplicate, silahkan cek kembali'),
                        ]
    
    def _auto_init(self,cr,context=None):
        result = super(consolidate_invoice_line,self)._auto_init(cr,context=context)
        cr.execute("""
            DROP INDEX IF EXISTS consolidate_invoice_line_unique_product_id_action_index;
            CREATE UNIQUE INDEX consolidate_invoice_line_unique_product_id_action_index on consolidate_invoice_line (consolidate_id,product_id)
            WHERE name IS NULL;
        """)
        return result
    
    def create(self, cr, uid, vals, context=None):
        if vals['product_qty'] <= 0 or vals['price_unit'] <= 0 :
            raise osv.except_osv(('Tidak bisa disimpan !'), ("Product Qty dan Price Unit tidak boleh 0"))
        return super(consolidate_invoice_line, self).create(cr, uid, vals, context=context)
        
    def lot_change(self, cr, uid, ids, id_branch, division, id_lot, id_product, id_invoice, id_partner, id_picking):
        if not id_branch or not division or not id_invoice or not id_partner or not id_picking :
            raise osv.except_osv(('Warning'),('Silahkan lengkapi data header terlebih dahulu'))
        res = {}
        domain = {}
        products = []
        obj_invoice = self.pool.get('account.invoice')
        obj_invoice_line = self.pool.get('account.invoice.line')
        obj_lot = self.pool.get('stock.production.lot')
        obj_quant = self.pool.get('stock.quant')
        obj_picking = self.pool.get('stock.picking')
        obj_move = self.pool.get('stock.move')
        invoice_id = obj_invoice.browse(cr, uid, id_invoice)
        
        if id_lot :
            lot_id = obj_lot.browse(cr, uid, id_lot)
            id_move = obj_move.search(cr,uid,[('product_id','=',lot_id.product_id.id),('picking_id','=',id_picking),('state','=','done')])
            if len(id_move)>0:
                id_move=id_move[0]
            move_id = obj_move.browse(cr, uid, id_move)

            res['product_id'] = lot_id.product_id.id
            res['product_uom'] = lot_id.product_id.uom_id.id
            res['product_qty'] = 1
            res['move_qty'] = 1
            res['move_qty_show'] = 1
            res['move_id'] = id_move
            
            id_inv_line = obj_invoice_line.search(cr, uid,
                [('purchase_line_id','=',move_id.purchase_line_id.id),
                ('invoice_id','=',id_invoice),
                ])
            if id_inv_line :
                inv_line_id = obj_invoice_line.browse(cr, uid, id_inv_line)
                res['price_unit'] = inv_line_id.price_subtotal / inv_line_id.quantity
            else :
                return {'value':{'price_unit':False}, 'warning':{'title':'Perhatian!','message':"Tidak ditemukan product '%s' warna '%s' di invoice '%s' untuk receipt yang dipilih,\nPastikan Anda memilih invoice dan receipt untuk PO yang sama !" %(lot_id.product_id.name,lot_id.product_id.attribute_value_ids.name,invoice_id.number)}}
        elif id_product :
            id_move = obj_move.search(cr,uid,[('product_id','=',id_product),('picking_id','=',id_picking),('state','=','done')])
            if len(id_move)>0:
                id_move=id_move[0]
            move_id = obj_move.browse(cr, uid, id_move)
            if not move_id:
                return {'value':{'product_id':False},'warning':{'title':'Perhatian!','message':'Tidak ditemukan product yg dipilih dalam receipt !'}}
            
            id_quant = obj_quant.search(cr,SUPERUSER_ID,[('product_id','=',id_product),('history_ids','in',id_move),('consolidated_date','=',False)])
            
            if not id_quant:
                return {'value':{'product_id':False},'warning':{'title':'Perhatian!','message':'Tidak ditemukan product yg dipilih dalam receipt'}}
            quant_id = obj_quant.browse(cr,uid,id_quant[0])
            
            id_inv_line = self.pool.get('account.invoice.line').search(cr, uid,
                [('purchase_line_id','=',move_id.purchase_line_id.id),
                ('invoice_id','=',id_invoice),
                ])
            if id_inv_line :
                inv_line_id = obj_invoice_line.browse(cr, uid, id_inv_line)
                res['price_unit'] = inv_line_id.price_subtotal / inv_line_id.quantity
                res['product_qty'] = move_id.product_qty - move_id.consolidated_qty
                res['move_qty'] = move_id.product_qty - move_id.consolidated_qty
                res['move_qty_show'] = move_id.product_qty - move_id.consolidated_qty
                res['product_uom'] = move_id.product_uom.id
                res['move_id'] = id_move
            else :
                product_id = self.pool.get('product.product').browse(cr, uid, id_product)
                return {'value':{'price_unit':False}, 'warning':{'title':'Perhatian!','message':"Tidak ditemukan product '%s' di invoice '%s' untuk receipt yang dipilih,\nPastikan Anda memilih invoice dan receipt untuk PO yang sama !" %(product_id.name,invoice_id.number)}}
        
        picking_id = obj_picking.browse(cr, uid, id_picking)
        for move in picking_id.move_lines :
            products.append(move.product_id.id)
        domain['product_id']=[('id','in',products)]
        
        return {'value': res,'domain':domain}
    
    def product_qty_change(self, cr, uid, ids, product_qty, move_qty):
        if product_qty and move_qty :
            if product_qty < 0:
                return {'value':{'product_qty':move_qty},'warning':{'title':'Perhatian!','message':'Product Qty tidak boleh negatif'}}
            if product_qty > move_qty:
                return {'value':{'product_qty':move_qty},'warning':{'title':'Perhatian!','message':'Product Qty tidak boleh melebihi move qty'}}
        return True

class stock_quant(osv.osv):
    
    _inherit = 'stock.quant'
    
    _columns = {
                'consolidated_date' :fields.datetime('Consolidated Date')
                }
    