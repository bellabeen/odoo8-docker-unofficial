from openerp.osv import fields,osv
from openerp import tools

class work_order_report(osv.osv):
    _name = "work.order.report"
    _description = "Work Order Report"
    _auto = False
    _columns = {
        'date': fields.date('Order Date', readonly=True, help="Date on which this document has been created"),  # TDE FIXME master: rename into date_order
        'state': fields.selection([('draft', 'Request for Quotation'),
                                     ('confirmed', 'Waiting Supplier Ack'),
                                      ('approved', 'Approved'),
                                      ('except_picking', 'Shipping Exception'),
                                      ('except_invoice', 'Invoice Exception'),
                                      ('done', 'Done'),
                                      ('cancel', 'Cancelled')],'Order Status', readonly=True),
        'product_id':fields.many2one('product.product', 'Product', readonly=True),
        'customer_id':fields.many2one('res.partner','Customer'),
        'type':fields.selection([('KPB','KPB'),('REG','Regular'),('WAR','Job Return'),('CLA','Claim'),('SLS','Part Sales')],'Type', change_default=True, select=True, readonly=True, required=True),
        'kpb_ke':fields.selection([('1','1'),('2','2'),('3','3'),('4','4')],'KPB Ke',change_default=True,select=True),
#         'price_average': fields.float('Average Price', readonly=True, group_operator="avg"),
        'quantity': fields.integer('Unit Quantity', readonly=True),
        'price_total': fields.float('Total Price', readonly=True),
        'user_id':fields.many2one('res.users', 'Responsible', readonly=True),
        'branch_id':fields.many2one('wtc.branch','Branch',required=True),
        'categ_id':fields.selection([('Sparepart','Sparepart'),('Service','Service')],'Category',required=True),
        'mekanik_id':fields.many2one('res.users', 'Mekanik', readonly=True),
    }
    _order = 'date desc ,price_total desc'
    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, 'work_order_report')
        cr.execute("""
            create or replace view work_order_report as (
                select
                    min(l.id) as id,
                    l.date,
                    l.state,
                    s.product_id,
                    l.customer_id,
                    l.type,
                    l.kpb_ke,
                    l.create_uid as user_id,
                    sum(s.product_qty) as quantity ,
                    sum(s.price_unit*s.product_qty)::decimal(16,2) as price_total,
                    l.branch_id,
                    s.categ_id,
                    l.mekanik_id
                    
                    
                from wtc_work_order_line s
                    join wtc_work_order l on (s.work_order_id=l.id)
                        left join product_product p on (l.product_id=p.id)
    
                group by
                    l.state,
                    s.product_id,
                    s.categ_id,
                    l.customer_id,
                    l.type,
                    l.kpb_ke,
                    l.create_uid,
                    l.date,
                    l.branch_id,
                    l.mekanik_id
                    


                    
            )
        """)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
