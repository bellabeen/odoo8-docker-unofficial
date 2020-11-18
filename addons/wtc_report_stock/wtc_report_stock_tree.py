from openerp.osv import fields,osv
from openerp import tools
from lxml import etree
class wtc_report_stock_tree(osv.osv):
    _name = "wtc.report.stock.tree"
    _description = "Report Stock Tree"
    _auto = False
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(wtc_report_stock_tree, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        categ_ids = self.pool.get('product.category').get_child_ids(cr,uid,view_id,'Unit')
        doc = etree.XML(res['arch'])
        nodes = doc.xpath("//field[@name='product_id']")
        for node in nodes:
            node.set('domain', '[("categ_id", "=", '+ str(categ_ids)+')]')
        res['arch'] = etree.tostring(doc)
        return res

    _columns = {       
        'branch_id':fields.many2one('wtc.branch', 'Branch', readonly=True),
        'product_id':fields.many2one('product.product', 'Product', readonly=True),
        'lot_id':fields.many2one('stock.production.lot', 'Engine', readonly=True),
        'qty':fields.float('Qty'),
        'cost':fields.float('Cost'),
        'umur':fields.char('Umur')
    }
    _order = 'branch_id  desc'
    
    
    def _from(self,cr):
        categ_ids = self.pool.get('product.category').get_child_ids('Unit')
        query_pr ="and h.id in %s" % str(
            tuple(categ_ids)).replace(',)', ')')
        return query_pr
    
    
    def init(self, cr):
        uid=self._from
        ids=self._from
        tools.sql.drop_view_if_exists(cr, 'wtc_report_stock_tree')
        cr.execute("""
            create or replace view wtc_report_stock_tree as (
                select 
            min(a.id) as id, 
            b.branch_id,  
            a.lot_id,
            a.product_id,
            a.qty,
            a.cost,
            AGE(CURRENT_DATE, a.in_date) as umur
            From   
            stock_quant a  
            LEFT JOIN stock_location b ON b.id = a.location_id  
            LEFT JOIN wtc_branch c ON c.id = b.branch_id  
            LEFT JOIN stock_production_lot d ON d.id = a.lot_id  
            LEFT JOIN product_product e ON e.id = a.product_id  
            LEFT JOIN product_template x ON x.id = e.product_tmpl_id  
            LEFT JOIN product_attribute_value_product_product_rel f ON f.prod_id = a.product_id  
            LEFT JOIN product_attribute_value g ON g.id = f.att_id  
            LEFT JOIN product_category h ON h.id = x.categ_id  
            where b.usage='internal' and a.lot_id is NOT NULL
             group by
                b.branch_id,
                a.lot_id,
                a.product_id,
                a.qty,
                a.cost  ,
                AGE(CURRENT_DATE, a.in_date) 
            limit 2000  
            )""")

    
    
    def list_branchs(self, cr, uid, context=None):
        branch_ids_user=self.pool.get('res.users').browse(cr,uid,uid).branch_ids
        branch_ids=[b.id for b in branch_ids_user]
        return self.pool.get('wtc.branch').name_get(cr, uid, branch_ids, context=context)