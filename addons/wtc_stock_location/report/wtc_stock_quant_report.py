from openerp.osv import fields,osv
from openerp import tools

class wtc_stock_quat_report(osv.osv):
    _name = "wtc.stock.quant.report"
    _description = "Stock Quant Report"
    _auto = False
    
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False 
        return branch_ids 
    
    
    _columns = {
                
        'branch_id':fields.many2one('wtc.branch', 'Branch', readonly=True),
        'product_id': fields.many2one('product.product','Product',required=True),
        'categ_id': fields.many2one('product.product','Category',required=True),
        'qty': fields.float('Qty', required=True ),
        'location_id': fields.many2one('stock.location', 'Location', select=True),
        'cost': fields.float('Unit Cost'),
    }
    _order = 'branch_id desc'
    
    _defaults = {
        'branch_id': _get_default_branch,
    }
    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, 'wtc_stock_quant_report')
        cr.execute("""
            create or replace view wtc_stock_quant_report as (
                select
                    min(s.id) as id,
                    l.branch_id, 
                    s.product_id,
                    t.categ_id,
                    s.qty,
                    s.location_id,
                    s.cost
                    
                    
                from stock_quant s
                    join stock_location l on (s.location_id=l.id)
                        left join wtc_branch b on (l.branch_id=l.id)
                            left join product_product p on (s.product_id=p.id)
                                left join product_template t on (p.product_tmpl_id=t.id)
                                    left join product_category c on (t.categ_id=p.id)
                
                where l.usage='internal'
                
                group by
                l.branch_id,
                s.product_id,
                t.categ_id,
                s.location_id,
                s.qty,
                s.cost
                
                      
            )
        """)
    
    
    
    
    
    
  


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
