from openerp import tools
from openerp.osv import fields, osv
import time

class dealer_sale_order_analysis(osv.osv):
    _name = "dealer.sale.order.analysis"
    _description = "Dealer Sales Orders Statistics"
    _auto = False
    _rec_name = 'date_order'

    _columns = {
        'date_order': fields.date('Date Order', readonly=True),  # TDE FIXME master: rename into date_order
        'date_confirm': fields.date('Date Confirm', readonly=True),
        'branch_id': fields.many2one('wtc.branch','Branch',readonly=True),
        'product_id': fields.many2one('product.product', 'Product', readonly=True),
        'partner_id': fields.many2one('res.partner', 'Partner', readonly=True),
        'finco_id': fields.many2one('res.partner', 'Finco', readonly=True),
        'partner_komisi_id': fields.many2one('res.partner','Channel',readonly=True),
        'user_id': fields.many2one('res.users', 'Salesperson', readonly=True),
        'amount_total': fields.float('Amount Total', readonly=True),
        'beban_dealer': fields.float('Beban Diskon', readonly=True),
        'price_unit': fields.float('Unit Price', readonly=True),
        'categ_id': fields.many2one('product.category','Category of Product', readonly=True),
        'product_qty': fields.integer('# of Qty', readonly=True),
        
        'nbr': fields.integer('# of Lines', readonly=True),  # TDE FIXME master: rename into nbr_lines
        'state': fields.selection([
                         ('draft', 'Draft Quotation'),
                            ('waiting_for_approval','Waiting Approval'),
                            ('approved','Approved'),                                
                            ('progress', 'Sales Order'),
                            ('done', 'Done'),
            ], 'Status', readonly=True),
        'sales_source': fields.selection([('Walk In','Walk In'),('Kanvasing','Kanvasing'),('Pameran','Pameran'),('POS','POS'),('Lain-Lain','Lain-Lain')],'Sales Source',readonly=True),
        'section_id': fields.many2one('crm.case.section', 'Sales Team',readonly=True),
        'is_cod':fields.boolean('Is COD',readonly=True),
        'biro_jasa_id': fields.many2one('res.partner','Biro Jasa',readonly=True),
        'price_bbn': fields.float('Price BBN',readonly=True),
        'city_id': fields.many2one('wtc.city','City',readonly=True)

    }
    _order = 'date_order desc'

    def _select(self):
        select_str = """
             SELECT min(l.id) as id,
                    l.product_id as product_id,
                    l.biro_jasa_id as biro_jasa_id,
                    sum(l.product_qty) as product_qty,
                    sum(s.amount_total) as amount_total,
                    sum(l.price_unit) as price_unit,
                    sum(l.price_bbn) as price_bbn,
                    sum(d.amount_average) as beban_dealer,
                    count(*) as nbr,
                    s.date_order as date_order,
                    s.date_confirm as date_confirm,
                    s.partner_id as partner_id,
                    s.user_id as user_id,
                    s.finco_id as finco_id,
                    s.partner_komisi_id as partner_komisi_id,
                    t.categ_id as categ_id,
                    s.section_id as section_id,
                    s.sales_source as sales_source,
                    s.is_cod as is_cod,
                    s.state,
                    s.branch_id,
                    case rp.sama when True then rp.city_id when False then rp.city_tab_id end as city_id
        """
        return select_str

    def _from(self):

        from_str = """
             dealer_sale_order_line l
                      join dealer_sale_order s on (l.dealer_sale_order_line_id=s.id) 
                        left join product_product p on (l.product_id=p.id)
                            left join product_template t on (p.product_tmpl_id=t.id)
                            left join res_partner rp on (s.partner_id=rp.id)
                            left join wtc_city wc on (rp.city_id=wc.id or rp.city_tab_id=wc.id)
                            left join dealer_sale_order_summary_diskon d on (d.dealer_sale_order_id=s.id)
                    
        """
        return from_str
    
    def _where(self):
        where_str = """
        where d.dealer_sale_order_id = s.id
        """
        
        return where_str

    def _group_by(self):
        group_by_str = """
            GROUP BY l.product_id,
                    l.biro_jasa_id,
                    l.dealer_sale_order_line_id,
                    t.categ_id,
                    s.date_order,
                    s.date_confirm,
                    s.partner_id,
                    s.user_id,
                    s.state,
                    s.is_cod,
                    s.sales_source,
                    s.section_id,
                    s.finco_id,
                    s.partner_komisi_id,
                    s.branch_id,
                    case rp.sama when True then rp.city_id when False then rp.city_tab_id end
                  
        """
        return group_by_str

    def init(self, cr):
        # self._table = sale_report
        tools.drop_view_if_exists(cr, self._table)
        cr.execute("""CREATE or REPLACE VIEW %s as (
            %s
            FROM %s
            %s
            )""" % (self._table, self._select(), self._from(), self._group_by()))