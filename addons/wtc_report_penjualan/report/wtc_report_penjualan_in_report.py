from openerp.osv import fields,osv
from openerp import tools

class wtc_report_penjualan_report(osv.osv):
    _name = "wtc.report.penjualan.report"
    _description = "Report Penjualan"
    _auto = False
    _columns = {
        'date': fields.date('Order Date', readonly=True,),
        'product_id':fields.many2one('product.product', 'Product', readonly=True),
        'categ_id': fields.many2one('product.category','Category of Product', readonly=True),
        'branch_id':fields.many2one('wtc.branch','Branch',required=True), 
        'partner_id': fields.many2one('res.partner','Customer',domain=[('customer','=',True)],required=True),
        'finco_id': fields.many2one('res.partner','Finco',domain=[('finance_company','=',True)]),
        'user_id': fields.many2one('res.users', 'Salesperson', readonly=True),
        'section_id': fields.many2one('crm.case.section', 'Sales Team',readonly=True),
        'state': fields.selection([
                         ('draft', 'Draft Quotation'),
                            ('waiting_for_approval','Waiting Approval'),
                            ('approved','Approved'),                                
                            ('progress', 'Sales Order'),
                            ('done', 'Done'),
            ], 'Status', readonly=True),
        'job_id': fields.many2one('hr.job', 'Job Title'),
        'product_qty': fields.integer('# of Qty', readonly=True),
        'price_unit': fields.float('Unit Price', readonly=True),
        'lot_id': fields.many2one('stock.production.lot', 'Engine', readonly=True),
        'discount_po': fields.float('Discount PO', readonly=True),
        'ps_dealer': fields.float('PS Dealer', readonly=True),
        
        'ps_ahm': fields.float('PS AHM', readonly=True),
        'ps_md': fields.float('PS MD', readonly=True),
        'ps_finco': fields.float('PS Finco', readonly=True),
        'ps_total': fields.float('PS Total', readonly=True),
        'sales': fields.float('Sales', readonly=True),
        'disc_reg': fields.float('Discount Reguler', readonly=True),
        'disc_quo': fields.float('Discount Quo', readonly=True),
        'disc_total': fields.float('Discount Total', readonly=True),
        'price_subtotal': fields.float('Price Subtotal', readonly=True),
        'ppn': fields.float('PPN', readonly=True),
        
        'force_cogs': fields.float('Force Cogs', readonly=True),
        'piutang_dp': fields.float('piutang DP', readonly=True),
        'piutang': fields.float('piutang', readonly=True),
        'gp_unit': fields.float('GP Unit', readonly=True),
        'price_bbn': fields.float('Price BBN', readonly=True),
        'price_bbn_beli': fields.float('Price BBN Beli', readonly=True),
        'gp_bbn': fields.float('GP BBN', readonly=True),
        'gp_total': fields.float('GP Total', readonly=True),
        'amount_hutang_komisi': fields.float('Amount Hutang Komisi', readonly=True),
        'dpp_insentif_finco': fields.float('DPP Insentif Finco', readonly=True),
        'beban_cabang': fields.float('Beban Cabang', readonly=True),

        
        
        
    }
    
    
    
    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, 'wtc_report_penjualan_report')
        cr.execute("""
            create or replace view wtc_report_penjualan_report as (
                select min(dso.id) as id,  
            dso.branch_id as branch_id,  
            dso.name,  
            CASE WHEN dso.state = 'progress' THEN 'Sales Order'  
                WHEN dso.state = 'done' THEN 'Done'  
                WHEN dso.state IS NULL THEN ''  
                ELSE dso.state  
            END as state,  
            dso.date_order as date,  
            dso.finco_id,  
            CASE WHEN dso.is_cod = TRUE THEN 'COD'  
                ELSE 'Reguler'  
            END as is_cod,  
            COALESCE(sales_koor.name,'') as sales_koor_name,  
            dso.user_id,  
            dso.section_id as section_id ,
            hr_sales.job_id,  
            dso.partner_id,
            dsol.product_id ,
            COALESCE(pav.code,'') as pav_code, 
            COALESCE(dsol.product_qty,0) as product_qty,  
            dsol.lot_id , 
            COALESCE(lot.chassis_no,'') as lot_chassis,  
            COALESCE(dsol.price_unit,0) as price_unit,  
            COALESCE(dsol.discount_po,0) as discount_po, 
            COALESCE(dsol_disc.ps_dealer,0) as ps_dealer,
             COALESCE(dsol_disc.ps_ahm,0) as ps_ahm, 
             COALESCE(dsol_disc.ps_md,0) as ps_md, 
             COALESCE(dsol_disc.ps_finco,0) as ps_finco,  
            COALESCE(dsol_disc.ps_dealer,0)+COALESCE(dsol_disc.ps_ahm,0)+COALESCE(dsol_disc.ps_md,0)+COALESCE(dsol_disc.ps_finco,0) as ps_total,  
            COALESCE(dsol.price_unit/1.1,0) as sales,  
            COALESCE(dsol.discount_po/1.1,0) as disc_reg,
             COALESCE(dsol_disc.discount_pelanggan/1.1,0) as disc_quo,  
            COALESCE(dsol.discount_po/1.1,0)+COALESCE(dsol_disc.discount_pelanggan/1.1,0) as disc_total,  
            COALESCE(dsol.price_subtotal,0) as price_subtotal, 
            round(dsol.price_subtotal*0.1,2) as PPN, 
            COALESCE(dsol.force_cogs,0) as force_cogs,  
            COALESCE(dso.customer_dp,0) as piutang_dp, 
            COALESCE(dso.amount_total,0)-COALESCE(dso.customer_dp,0) as piutang,  
            COALESCE(dsol.price_subtotal,0)-COALESCE(dsol.force_cogs,0)+COALESCE(dsol_disc.ps_ahm,0)+COALESCE(dsol_disc.ps_md,0)+COALESCE(dsol_disc.ps_finco,0) as gp_unit,  
            COALESCE(dsol.price_bbn,0) as price_bbn, 
            COALESCE(dsol.price_bbn_beli,0) as price_bbn_beli, 
            COALESCE(dsol.price_bbn,0)-COALESCE(dsol.price_bbn_beli,0) as gp_bbn,  
            (COALESCE(dsol.price_subtotal,0)-COALESCE(dsol.force_cogs,0)+COALESCE(dsol_disc.ps_ahm,0)+COALESCE(dsol_disc.ps_md,0)+COALESCE(dsol_disc.ps_finco,0))+(COALESCE(dsol.price_bbn,0)-COALESCE(dsol.price_bbn_beli,0)) as gp_total,  
            COALESCE(dsol.amount_hutang_komisi,0) as amount_hutang_komisi,  
            COALESCE(dsol.insentif_finco/1.1,0) as insentif_finco, insentif_finco as dpp_insentif_finco,  
            COALESCE(dsol.discount_po/1.1,0)+COALESCE(dsol_disc.ps_dealer/1.1,0)+COALESCE(amount_hutang_komisi,0) as beban_cabang,  
            prod_template.categ_id as categ_id ,  
            COALESCE(prod_category2.name,'') as categ2_name,  
            COALESCE(prod_template.series,'') as prod_series,  
            COALESCE(fp.name,'') as faktur_pajak  
            from dealer_sale_order dso  
            inner join dealer_sale_order_line dsol on dsol.dealer_sale_order_line_id = dso.id  
            left join wtc_branch b ON dso.branch_id = b.id  
            left join res_partner md ON b.default_supplier_id = md.id  
            left join res_partner finco ON dso.finco_id = finco.id  
            left join res_users users ON dso.user_id = users.id  
            left join resource_resource sales ON users.id = sales.user_id  
            left join hr_employee hr_sales ON sales.id = hr_sales.resource_id  
            left join hr_job job ON hr_sales.job_id = job.id  
            left join crm_case_section sales_team ON dso.section_id = sales_team.id  
            left join resource_resource sales_koor ON sales_team.user_id = sales_koor.user_id  
            left join res_partner cust ON dso.partner_id = cust.id  
            left join product_product product ON dsol.product_id = product.id  
            left join product_attribute_value_product_product_rel pavpp ON product.id = pavpp.prod_id  
            left join product_attribute_value pav ON pavpp.att_id = pav.id  
            left join product_template prod_template ON product.product_tmpl_id = prod_template.id  
            left join product_category prod_category ON prod_template.categ_id = prod_category.id  
            left join product_category prod_category2 ON prod_category.parent_id = prod_category2.id  
            left join stock_production_lot lot ON dsol.lot_id = lot.id  
            left join wtc_faktur_pajak_out fp ON dso.faktur_pajak_id = fp.id  
            left join ( 
            select dealer_sale_order_line_discount_line_id, sum(ps_finco) as ps_finco, sum(ps_ahm) as ps_ahm, sum(ps_md) as ps_md, sum(ps_dealer) as ps_dealer, sum(ps_others) as ps_others,  
            sum(discount) as discount, sum(discount_pelanggan) as discount_pelanggan  
            from dealer_sale_order_line_discount_line  
            group by dealer_sale_order_line_discount_line_id  
            ) dsol_disc ON dsol_disc.dealer_sale_order_line_discount_line_id = dsol.id 
            WHERE  1=1 
            
            group by
            dso.branch_id,
            dso.name,
            dso.state ,
            dso.date_order,
            dso.finco_id,
            dso.is_cod,
            sales_koor.name,
            dso.user_id,
            dso.section_id,
            hr_sales.job_id,
            dso.partner_id,
            dsol.product_id,
            dsol.lot_id,
            pav.code,
            dsol.product_qty,
            lot.chassis_no,
            dsol.price_unit,
            dsol.discount_po,
            dsol_disc.ps_dealer,
            dsol_disc.ps_ahm,
            dsol_disc.ps_md,
            dsol_disc.ps_finco,
            dsol_disc.discount_pelanggan,
            dsol.price_subtotal,
            dsol.force_cogs,
            dso.customer_dp,
            dso.amount_total,
            dsol.price_bbn,
            dsol.price_bbn_beli,
            dsol.amount_hutang_komisi,
            dsol.insentif_finco,
            prod_template.categ_id,
            prod_category2.name,
            prod_template.series,
            fp.name,
            b.code
            
            
            
            

     
            )
        """)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
