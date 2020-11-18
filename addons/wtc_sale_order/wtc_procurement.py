from openerp.osv import fields, osv
from openerp.tools.translate import _

from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp import SUPERUSER_ID
from dateutil.relativedelta import relativedelta
from datetime import datetime


class procurement_order(osv.osv):
    _inherit = "procurement.order"
    
    def _get_default_date(self,cr,uid,ids,context=None):
        return self.pool.get('wtc.branch').get_default_date(cr,uid,ids,context=context)
    
    def _get_default_location_delivery_sales(self,cr,uid,branch_id):
        default_location_id = {}
        obj_picking_type = self.pool.get('stock.picking.type')
        picking_type_id = obj_picking_type.search(cr,uid,[
                                                  ('branch_id','=',branch_id),
                                                  ('code','=','outgoing')
                                                  ])
        if picking_type_id:
            for pick_type in obj_picking_type.browse(cr,uid,picking_type_id[0]):
                if not pick_type.default_location_dest_id.id :
                     raise osv.except_osv(('Perhatian !'), ("Location destination Belum di Setting"))
                default_location_id.update({
                    'picking_type_id':pick_type.id,
                    'source':pick_type.default_location_src_id.id,
                    'destination': pick_type.default_location_dest_id.id,
                })
        else:
           raise osv.except_osv(('Error !'), ('Tidak ditemukan default lokasi untuk penjualan di konfigurasi cabang \'%s\'!') % (val.branch_id.name,)) 
        return default_location_id
    
    def _search_pricelist_ekspedisi(self,cr,uid,ids,product_id,branch_id):
        price_list_ekspedisi_def = self.pool.get('wtc.harga.ekspedisi').search(cr,uid,[('branch_id','=',branch_id),('default_ekspedisi','=',True)])
        if not price_list_ekspedisi_def:
            raise osv.except_osv(('Tidak ditemukan default harga ekspedisi!'), ('Tidak bisa confirm, silahkan setting dulu di pengaturan cabang!'))
        else:
            pricelist_ekspedisi = self.pool.get('wtc.harga.ekspedisi').browse(cr,uid,price_list_ekspedisi_def[0])
            pl_ekspedisi_line_active = self.pool.get('wtc.pricelist.expedition.line').search(cr,uid,[
                                                                                                     ('pricelist_expedition_id','=',pricelist_ekspedisi.harga_ekspedisi_id.id),
                                                                                                     ('active','=',True),
                                                                                                     ('start_date','<=',self._get_default_date(cr, uid, ids, context=None)),
                                                                                                     ('end_date','>=',self._get_default_date(cr, uid, ids, context=None)),
                                                                                                     ])
            if not pl_ekspedisi_line_active:
                raise osv.except_osv(('Tidak ditemukan harga ekspedisi yang aktif!'), ('Tidak bisa confirm, silahkan setting dulu di pengaturan cabang!'))
            else:
                pl_eks_det_obj = self.pool.get('wtc.pricelist.expedition.line.detail')
                pl_ekspedisi_product = pl_eks_det_obj.search(cr,uid,[
                                                                    ('pricelist_expedition_line_id','=',pl_ekspedisi_line_active[0]),
                                                                    ('product_template_id','=',product_id.product_tmpl_id.id),
                                                                    ])
                if not pl_ekspedisi_product:
                    raise osv.except_osv(('Tidak ditemukan harga ekspedisi product %s!') % (product_id.product_tmpl_id.name), ('Tidak bisa confirm, silahkan setting dulu di pengaturan cabang!'))
                else:
                    harga_ekspedisi_product = pl_eks_det_obj.browse(cr,uid,pl_ekspedisi_product[0])
                    return harga_ekspedisi_product.cost
            
    def _run_move_create(self, cr, uid, procurement, context=None):
        vals = super(procurement_order,self)._run_move_create(cr, uid, procurement, context=context)
        undelivered_value = 0
        if procurement.sale_line_id and procurement.sale_line_id.id:
            branch_id = procurement.sale_line_id.order_id.branch_id.id
            if procurement.product_id.product_tmpl_id.cost_method == 'real':
                pricelist_beli_md = procurement.sale_line_id.order_id.branch_id.pricelist_unit_purchase_id.id
                if not pricelist_beli_md:
                    raise osv.except_osv(('No Purchase Pricelist Defined!'), ('Tidak bisa confirm'))
                undelivered_value = round(self.pool.get('product.pricelist').price_get(cr, uid, [pricelist_beli_md], procurement.product_id.id, 1,0)[pricelist_beli_md]/1.1,2)
                harga_ekspedisi = self._search_pricelist_ekspedisi(cr, uid, procurement.id,procurement.product_id, branch_id)
                undelivered_value += harga_ekspedisi
                
            elif procurement.product_id.product_tmpl_id.cost_method == 'average':
                product_price_branch_obj = self.pool.get('product.price.branch')
                undelivered_value = product_price_branch_obj._get_price(cr, uid, procurement.sale_line_id.order_id.warehouse_id.id, procurement.product_id.id)    
            
            location = self._get_default_location_delivery_sales(cr,uid,branch_id)
            
            if procurement.sale_line_id.order_id.division=='Sparepart':
                location_id = procurement.sale_line_id.order_id.source_location_id.id
            else:
                location_id = location['source']
            vals.update({'branch_id':branch_id,'undelivered_value':undelivered_value,'picking_type_id': location['picking_type_id'],'location_dest_id': location['destination'],'location_id':location_id})
        
        return vals
    
class stock_move(osv.osv):
    _inherit = "stock.move"
    
    def _picking_assign(self, cr, uid, move_ids, procurement_group, location_from, location_to, context=None):
        pick_obj = self.pool.get("stock.picking")
        move = self.browse(cr,uid,move_ids[0])
        obj_model = self.pool.get('ir.model')
        obj_model_id = obj_model.search(cr,uid,[ ('model','=',move.procurement_id.sale_line_id.order_id.__class__.__name__) ])
        if move.branch_id:
            values = {
                'origin': move.origin,
                'company_id': move.company_id and move.company_id.id or False,
                'move_type': move.group_id and move.group_id.move_type or 'direct',
                'partner_id': move.partner_id.id or False,
                'picking_type_id': move.picking_type_id and move.picking_type_id.id or False,
                'group_id': procurement_group,
                'location_id':location_from,
                'location_dest_id': location_to,
                'branch_id': move.branch_id.id,
                'division': move.procurement_id.sale_line_id.order_id.division,
                'state': 'draft',
                'transaction_id': move.procurement_id.sale_line_id.order_id.id,
                'model_id': obj_model_id[0]
            }
            pick = pick_obj.create(cr, uid, values, context=context)
            self.write(cr, uid, move_ids, {'picking_id': pick}, context=context)            
        res = super(stock_move,self)._picking_assign(cr, uid, move_ids, procurement_group, location_from, location_to, context=context)
        pick_obj.force_assign(cr,uid,pick)
        return res 