from openerp.osv import fields, osv
from lxml import etree
from openerp.osv.orm import setup_modifiers
from openerp import SUPERUSER_ID

class wtc_product_pricelist_item (osv.osv):
    _inherit = "product.pricelist.item"
    
    def product_id_change(self, cr, uid, ids, product_id, product_tmpl_id, categ_id, context=None):
        value = {}
        value['name'] = False
        if product_id :
            prod = self.pool.get('product.product').browse(cr, uid, product_id)
            value['name'] = prod.name_get().pop()[1]
        elif product_tmpl_id :
            prod_tmpl = self.pool.get('product.template').browse(cr, uid, product_tmpl_id)
            value['name'] = prod_tmpl.name_get().pop()[1]
        elif categ_id :
            categ = self.pool.get('product.category').browse(cr, uid, categ_id)
            value['name'] = categ.name_get().pop()[1]
        return {'value':value}
    
class wtc_pricelist (osv.osv):
    _name = "wtc.pricelist"
    
    def _get_branch_id(self, cr, uid, context=None):
        obj_branch = self.pool.get('wtc.branch')
        ids_branch = obj_branch.search(cr, SUPERUSER_ID, [], order='name')
        branches = obj_branch.read(cr, SUPERUSER_ID, ids_branch, ['id','name'], context=context)
        res = []
        for branch in branches :
            res.append((branch['id'],branch['name']))
        return res
    
    _columns = {
                'product_id': fields.many2one('product.product', 'Product'),
                'branch_id': fields.many2one('wtc.branch', 'Branch'),
                'name': fields.char('Name'),
                'categ_id': fields.many2one('product.category','Category'),
                'pricelist_unit_purchase_id' : fields.many2one('product.pricelist', string='Price List Beli Unit', domain=[('type','=','purchase')]),
                'pricelist_unit_sales_id' : fields.many2one('product.pricelist', string='Price List Jual Unit', domain=[('type','=','sale')]),
                'pricelist_part_purchase_id' : fields.many2one('product.pricelist', string='Price List Beli Sparepart', domain=[('type','=','purchase')]),
                'pricelist_part_sales_id' : fields.many2one('product.pricelist', string='Price List Jual Sparepart', domain=[('type','=','sale')]),
                'pricelist_bbn_hitam_id' : fields.many2one('product.pricelist', string='Price List Jual BBN Plat Hitam', domain=[('type','=','sale_bbn_hitam')]),
                'pricelist_bbn_merah_id' : fields.many2one('product.pricelist', string='Price List Jual BBN Plat Merah', domain=[('type','=','sale_bbn_merah')]),
                'harga_beli': fields.float('Harga Beli'),
                'harga_jual': fields.float('Harga Jual'),
                'harga_jual_bbn_hitam': fields.float('Harga Jual BBN Hitam'),
                'harga_jual_bbn_merah': fields.float('Harga Jual BBN Merah'),
                'total_stock': fields.float('Total Stock'),
                'stock_intransit': fields.float('Stock Intransit'),
                'stock_available': fields.float('Stock Available'),
                'stock_reserved': fields.float('Stock Reserved (All)'),
                'other_branch_prize_ids': fields.one2many('wtc.pricelist.branch.other','pricelist_id', readonly=True, copy=True),
                }
    
    def create(self, cr, uid, vals, context=None):
        raise osv.except_osv(('Perhatian !'), ("Tidak bisa disimpan, form ini hanya untuk Pengecekan"))
        return False
    
    def pricelist_change(self, cr, uid, ids, product_id, branch_id, context=None):
        value = {}
        warning = {}
        
        value['name'] = False
        value['categ_id'] = False
        value['pricelist_unit_sales_id'] = False
        value['pricelist_unit_purchase_id'] = False
        value['pricelist_bbn_hitam_id'] = False
        value['pricelist_bbn_merah_id'] = False
        value['harga_beli'] = False
        value['harga_jual'] = False
        value['harga_jual_bbn_hitam'] = False
        value['harga_jual_bbn_merah'] = False
        value['total_stock'] = False
        value['stock_available'] = False
        value['stock_reserved'] = False
        value['other_branch_prize_ids'] = False
        
        if product_id and branch_id :
            prod = self.pool.get('product.product').browse(cr, SUPERUSER_ID, product_id)
            branch = self.pool.get('wtc.branch').browse(cr, SUPERUSER_ID, branch_id)
            
            value['name'] = prod.description
            value['categ_id'] = prod.categ_id
            value['pricelist_unit_purchase_id'] = branch.pricelist_unit_purchase_id
            value['pricelist_unit_sales_id'] = branch.pricelist_unit_sales_id
            value['pricelist_part_purchase_id'] = branch.pricelist_part_purchase_id
            value['pricelist_part_sales_id'] = branch.pricelist_part_sales_id
            value['pricelist_bbn_hitam_id'] = branch.pricelist_bbn_hitam_id
            value['pricelist_bbn_merah_id'] = branch.pricelist_bbn_merah_id
            
            if prod.categ_id.isParentName('Unit') :
                # pricelist beli unit
                if branch.pricelist_unit_purchase_id :
                    value['harga_beli'] = self.pool.get('product.pricelist').price_get(cr, uid, [branch.pricelist_unit_purchase_id.id], product_id, 1,0)[branch.pricelist_unit_purchase_id.id]
                
                # pricelist jual unit
                if branch.pricelist_unit_sales_id :
                    value['harga_jual'] = self.pool.get('product.pricelist').price_get(cr, uid, [branch.pricelist_unit_sales_id.id], product_id, 1,0)[branch.pricelist_unit_sales_id.id]
                
                # pricelist jual bbn hitam
                if branch.pricelist_bbn_hitam_id :
                    value['harga_jual_bbn_hitam'] = self.pool.get('product.pricelist').price_get(cr, uid, [branch.pricelist_bbn_hitam_id.id], product_id, 1,0)[branch.pricelist_bbn_hitam_id.id]
                    
                # pricelist jual bbn merah
                if branch.pricelist_bbn_merah_id :
                    value['harga_jual_bbn_merah'] = self.pool.get('product.pricelist').price_get(cr, uid, [branch.pricelist_bbn_merah_id.id], product_id, 1,0)[branch.pricelist_bbn_merah_id.id]
                
                cr.execute("""SELECT
                    q.product_id, l.branch_id, q.reservation_id, q.consolidated_date, s.state, sum(q.qty)
                FROM
                    stock_quant q
                JOIN
                    stock_location l on q.location_id = l.id
                JOIN
                    stock_production_lot s on q.lot_id = s.id
                WHERE
                    q.product_id = %s and l.branch_id = %s and l.usage in ('internal','transit')
                GROUP BY
                    q.product_id, l.branch_id, q.reservation_id, q.consolidated_date, s.state
                """,(product_id,branch_id))

                unit_intransit = 0
                unit_available = 0
                unit_reserved = 0
                
                for x in cr.fetchall() :
                    if x[2] == None and (x[4] == 'intransit' or x[3] == None) :
                        unit_intransit += x[5]
                    elif x[2] == None and x[4] == 'stock' :
                        unit_available += x[5]
                    elif x[2] <> None or x[4] == 'reserved' :
                        unit_reserved += x[5]
                
                unit_tot_qty = unit_intransit + unit_available + unit_reserved
                
                value['stock_intransit'] = unit_intransit
                value['stock_available'] = unit_available
                value['stock_reserved'] = unit_reserved
                value['total_stock'] = unit_tot_qty

            else :
                # pricelist beli sparepart
                if branch.pricelist_part_purchase_id :
                    value['harga_beli'] = self.pool.get('product.pricelist').price_get(cr, uid, [branch.pricelist_part_purchase_id.id], product_id, 1,0)[branch.pricelist_part_purchase_id.id]
                
                # pricelist jual sparepart
                if branch.pricelist_part_sales_id :
                    value['harga_jual'] = self.pool.get('product.pricelist').price_get(cr, uid, [branch.pricelist_part_sales_id.id], product_id, 1,0)[branch.pricelist_part_sales_id.id]

                cr.execute("""select l.branch_id
                        , p.default_code
                        , t.name as product_name
                        , q.product_id
                        , q.location_id
                        , sum(case when q.consolidated_date IS NULL THEN q.qty ELSE 0 END) as qty_titipan
                        , sum(case when q.consolidated_date IS NOT NULL THEN q.qty ELSE 0 END) as qty_stock
                        , case WHEN l.usage='internal' then COALESCE(
                            (select sum(product_uom_qty) from stock_move sm 
                                left join stock_picking sp on sm.picking_id=sp.id 
                                left join stock_picking_type spt on sp.picking_type_id=spt.id
                                left join stock_location stl on sm.location_dest_id=stl.id 
                                where spt.code in ('outgoing','interbranch_out') 
                                    and sp.branch_id=l.branch_id 
                                    and sp.state not in ('draft','cancel','done') 
                                    and sp.division='Sparepart' 
                                    and sm.product_id=q.product_id
                                    and sm.location_id=q.location_id
                            ),0
                        ) 
                        else 0 end as qty_reserved_end
                        from stock_quant q
                        INNER JOIN stock_location l ON q.location_id = l.id AND l.usage = 'internal'
                        LEFT JOIN product_product p ON q.product_id = p.id
                        LEFT JOIN product_template t ON p.product_tmpl_id = t.id
                        LEFT JOIN product_category c ON t.categ_id = c.id 
                        LEFT JOIN product_category c2 ON c.parent_id = c2.id 
                        WHERE (c.name = 'Sparepart' or c2.name = 'Sparepart')  and q.product_id = %s and l.branch_id = %s
                        group by l.branch_id, l.warehouse_id, l.complete_name, l.usage, p.default_code, t.name, q.product_id, q.location_id
                """,(product_id,branch_id))

                qty_intransit = 0
                qty_reserved = 0
                qty_stok = 0

                for x in cr.fetchall() :
                    qty_intransit += x[5]
                    qty_reserved += x[7]
                    qty_stok += x[6]

                total_available = qty_stok - qty_reserved
                
                value['stock_intransit'] = qty_intransit
                value['stock_available'] = total_available
                value['stock_reserved'] = qty_reserved
                value['total_stock'] = qty_stok + qty_intransit

            other_branch_list=[]
            # obj_branch = self.pool.get('wtc.branch')
            # ids_branch = obj_branch.search(cr, SUPERUSER_ID, [], order='name')
            # branches = obj_branch.read(cr, SUPERUSER_ID, ids_branch, ['id','code','name'], context=context)
                   
            if prod.categ_id.isParentName('Unit') :
                query = """
                    SELECT
                    l.branch_id, b.code, b.name, q.product_id,sum(q.qty)
                FROM
                    stock_quant q
                    JOIN
                    stock_location l on q.location_id = l.id
                    JOIN
                    stock_production_lot s on q.lot_id = s.id
                    JOIN
                    wtc_branch b on l.branch_id = b.id AND b.branch_type = 'DL'
                WHERE
                    q.product_id = %s and 
                    l.usage in ('internal','transit') and
                    s.state = 'stock' and
                    q.reservation_id IS NULL and  
                    q.consolidated_date IS NOT NULL and
                    l.branch_id != %s
                GROUP BY
                    l.branch_id,b.code,b.name,q.product_id
                ORDER BY
                    b.code
                """
                    
            else :
      
                query = """
                    SELECT
                    l.branch_id, b.code, b.name, q.product_id,sum(q.qty)
                FROM
                    stock_quant q
                    JOIN
                    stock_location l on q.location_id = l.id
                    JOIN
                    wtc_branch b on l.branch_id = b.id
                WHERE
                    q.product_id = %s and 
                    l.usage in ('internal','transit') and 
                    q.reservation_id IS NULL and 
                    q.consolidated_date IS NOT NULL and
                    l.branch_id != %s
                GROUP BY
                    l.branch_id,b.code,b.name,q.product_id
                ORDER BY
                    b.code
                """

            
            cr.execute(query,(product_id,branch_id))    
                    
            ress = cr.fetchall()
            #print ress,"Resss<<<<<<<<<"
            for res in ress :
                other_branch_list.append([0,0,{
                    'branch_code':res[1],
                    'branch_name':res[2],
                    'stock_available':res[4],
                }])

            value['other_branch_prize_ids'] = other_branch_list
        
        return {'value':value}
    
    def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
        if context is None:context = {}
        res = super(wtc_pricelist, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=False)
        doc = etree.XML(res['arch'])
        nodes = doc.xpath("//field[@name='product_id']")   
        parent_categ_id = str(context.get('default_categ_id'))

        for node in nodes:
            domain ="[('type','!=','view'),('categ_id','child_of',"+parent_categ_id+")]"
            node.set('domain', domain)
            setup_modifiers(node, res['fields']['product_id'])
        res['arch'] = etree.tostring(doc)            
        return res

class wtc_pricelist_branch_other(osv.osv):
    _name = 'wtc.pricelist.branch.other'
    _rec_name = 'pricelist_id'
    _columns = {
        'pricelist_id':fields.many2one('wtc.pricelist', 'Pricelist', required=1, ondelete='cascade'),
        'branch_code':fields.char('Branch Code'),
        'branch_name':fields.char('Branch Name'),
        'stock_available':fields.float('Stock Available'),
    }