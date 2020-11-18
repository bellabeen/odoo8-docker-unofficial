# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#
#    Copyright (c) 2014-now Noviat nv/sa (www.noviat.com).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import orm, osv, fields
from datetime import datetime
# from openerp.addons.report_xls.utils import _render
# from openerp.tools.translate import _


class wtc_stock_quant(orm.Model):
    _inherit = 'stock.quant'
    
    def _check_location(self, cr, uid, location, context=None):
        result = super(wtc_stock_quant, self)._check_location(cr, uid, location, context=context)
        if location.usage == 'internal' :
            if datetime.strptime(location.start_date, "%Y-%m-%d").date() > datetime.today().date() or datetime.strptime(location.end_date, "%Y-%m-%d").date() < datetime.today().date() :
                raise osv.except_osv(('Perhatian !'), ("Effective Date utk lokasi '%s' sudah habis !" %location.name)) 
            if location.maximum_qty == -1:
                return result
            else:
                cr.execute("""
                SELECT
                    sum(qty) as quantity
                FROM
                    stock_quant
                WHERE lot_id is not NULL  AND 
                    location_id = %s
                """,([location.id]))
                current_qty = cr.fetchall()[0][0]
                if current_qty > location.maximum_qty :
                    raise osv.except_osv(('Perhatian !'), ("Quantity produk melebihi jumlah maksimum lokasi '%s' !" %location.name))
            
        return result
    
    def _teds_check_location(self, cr, uid, location, move, context=None):
        if location.usage == 'internal' :
            if datetime.strptime(location.start_date, "%Y-%m-%d").date() > datetime.today().date() or datetime.strptime(location.end_date, "%Y-%m-%d").date() < datetime.today().date() :
                raise osv.except_osv(('Perhatian !'), ("Effective Date utk lokasi '%s' sudah habis !" %location.name)) 
            if location.maximum_qty == -1:
                return True
            else:
                cr.execute("""
                SELECT
                    sum(qty) as quantity
                FROM
                    stock_quant
                WHERE lot_id is not NULL AND
                    location_id = %s
                """,([location.id]))
                current_qty = cr.fetchall()[0][0]
                if not current_qty:
                    current_qty=0
                if current_qty+int(move.product_uom_qty) > location.maximum_qty :
                    raise osv.except_osv(('Perhatian !'), ("Quantity produk melebihi jumlah maksimum lokasi '%s' !" %location.name))

    def quants_get(self, cr, uid, location, product, qty, domain=None, restrict_lot_id=False, restrict_partner_id=False, context=None):
        if domain is None:
            domain = []
        if product.categ_id.isParentName('Extras') :
            return super(wtc_stock_quant, self).quants_get(cr, uid, location, product, qty, domain, restrict_lot_id, restrict_partner_id, context)
        if context.get('unconsolidated_reverse',False):
            domain += [('consolidated_date', '=', False)]
            if ('consolidated_date', '!=', False) in domain:
                domain.remove(('consolidated_date', '!=', False))
        else :
            domain += [('consolidated_date', '!=', False)]
        
        return super(wtc_stock_quant, self).quants_get(cr, uid, location, product, qty, domain, restrict_lot_id, restrict_partner_id, context)
    
    def quants_move(self, cr, uid, quants, move, location_to, location_from=False, lot_id=False, owner_id=False, src_package_id=False, dest_package_id=False, context=None):
        self._teds_check_location(cr, uid, location_to, move, context=context)
        return super(wtc_stock_quant, self).quants_move(cr, uid, quants, move, location_to, location_from, lot_id, owner_id, src_package_id, dest_package_id, context)
    
    
class stock_quant_history(osv.osv):
    
    _name = "stock.quant.history"
    _description = "Stock Quant History"
    
    def _get_default_date(self,cr,uid,context):
        return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)  
    
    def _get_quant_name(self, cr, uid, ids, name, args, context=None):
        """ Forms complete name of location from parent location to child location.
        @return: Dictionary of values
        """
        res = {}
        for q in self.browse(cr, uid, ids, context=context):

            res[q.id] = q.product_id.code or ''
            if q.lot_id:
                res[q.id] = q.lot_id.name
            res[q.id] += ': ' + str(q.qty) + q.product_id.uom_id.name
        return res

    def _calc_inventory_value(self, cr, uid, ids, name, attr, context=None):
        context = dict(context or {})
        res = {}
        uid_company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        for quant in self.browse(cr, uid, ids, context=context):
            context.pop('force_company', None)
            if quant.company_id.id != uid_company_id:
                #if the company of the quant is different than the current user company, force the company in the context
                #then re-do a browse to read the property fields for the good company.
                context['force_company'] = quant.company_id.id
                quant = self.browse(cr, uid, quant.id, context=context)
            res[quant.id] = self._get_inventory_value(cr, uid, quant, context=context)
        return res

    def _get_inventory_value(self, cr, uid, quant, context=None):
        return quant.product_id.standard_price * quant.qty
    
    _columns = {
        'name': fields.function(_get_quant_name, type='char', string='Identifier'),
        'product_id': fields.many2one('product.product', 'Product', required=True, ondelete="restrict", readonly=True, select=True),
        'location_id': fields.many2one('stock.location', 'Location', required=True, ondelete="restrict", readonly=True, select=True),
        'qty': fields.float('Quantity', required=True, help="Quantity of products in this quant, in the default unit of measure of the product", readonly=True, select=True),
        'package_id': fields.many2one('stock.quant.package', string='Package', help="The package containing this quant", readonly=True, select=True),
        'packaging_type_id': fields.related('package_id', 'packaging_id', type='many2one', relation='product.packaging', string='Type of packaging', readonly=True, store=True),
        'reservation_id': fields.many2one('stock.move', 'Reserved for Move', help="The move the quant is reserved for", readonly=True, select=True),
        'lot_id': fields.many2one('stock.production.lot', 'Lot', readonly=True, select=True),
        'cost': fields.float('Unit Cost'),
        'owner_id': fields.many2one('res.partner', 'Owner', help="This is the owner of the quant", readonly=True, select=True),

        'create_date': fields.datetime('Creation Date', readonly=True),
        'in_date': fields.datetime('Incoming Date', readonly=True, select=True),

        'history_ids': fields.many2many('stock.move', 'stock_quant_move_rel', 'quant_id', 'move_id', 'Moves', help='Moves that operate(d) on this quant'),
        'company_id': fields.many2one('res.company', 'Company', help="The company to which the quants belong", required=True, readonly=True, select=True),
        'inventory_value': fields.function(_calc_inventory_value, string="Inventory Value", type='float', readonly=True),

        # Used for negative quants to reconcile after compensated by a new positive one
        'propagated_from_id': fields.many2one('stock.quant', 'Linked Quant', help='The negative quant this is coming from', readonly=True, select=True),
        'negative_move_id': fields.many2one('stock.move', 'Move Negative Quant', help='If this is a negative quant, this will be the move that caused this negative quant.', readonly=True),
        'negative_dest_location_id': fields.related('negative_move_id', 'location_dest_id', type='many2one', relation='stock.location', string="Negative Destination Location", readonly=True, 
                                                    help="Technical field used to record the destination location of a move that created a negative quant"),
        'date': fields.datetime('Stock Date')
    }
    
    def copy_stock_quant(self,cr,uid,ids,context=None):
        cr.execute("insert into stock_quant_history(id,write_uid,date,product_id,location_id,qty,package_id,packaging_type_id,reservation_id,lot_id,cost,owner_id,create_date,in_date,company_id,propagated_from_id,negative_move_id ) select id,write_uid,%s,product_id,location_id,qty,package_id,packaging_type_id,reservation_id,lot_id,cost,owner_id,create_date,in_date,company_id,propagated_from_id,negative_move_id from stock_quant" % (self._get_default_date(cr, uid, context)) )
    
        
        
