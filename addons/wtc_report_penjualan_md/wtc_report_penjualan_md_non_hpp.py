import time
import cStringIO
import xlsxwriter
from cStringIO import StringIO
import base64
import tempfile
import os
from openerp.osv import fields, osv
from openerp.tools.translate import _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from xlsxwriter.utility import xl_rowcol_to_cell
import logging
import re
import pytz
_logger = logging.getLogger(__name__)
from lxml import etree

class wtc_report_penjualan_mo_non_hpp(osv.osv_memory):
    _inherit = "wtc.report.penjualan.md.wizard"


    def _print_excel_report_non_hpp(self, cr, uid, ids, data, context=None):      
        division = data['division']
        product_ids = data['product_ids']
        start_date = data['start_date']
        end_date = data['end_date']
        state = data['state']
        branch_ids = data['branch_ids']
        dealer_ids = data['dealer_ids']
        type_file = data['type_file']
              
        tz = '7 hours'
        
        query_where = " WHERE 1=1 "
        query_where_cancel = ""

        if product_ids :
            query_where += " AND sol.product_id in %s" % str(tuple(product_ids)).replace(',)', ')')
        if division :
            query_where += " AND so.division = '%s'" % str(division)
        if start_date :
            query_where += " AND so.date_order >= '%s'" % str(start_date)
            query_where_cancel += " AND soc.date >= '%s'" % str(start_date)
        if end_date :
            query_where_cancel += " AND soc.date <= '%s'" % str(end_date)
            end_date = end_date + ' 23:59:59'
            query_where += " AND so.date_order <= to_timestamp('%s', 'YYYY-MM-DD HH24:MI:SS') + interval '%s'" % (end_date,tz)
        if state in ['progress','done','cancel','unused'] :
            query_where += " AND so.state = '%s'" % str(state)
        elif state == 'all' :
            query_where += " AND so.state in ('progress', 'done', 'cancel')"
        else :
            query_where += " AND so.state in ('progress','done')"
        if branch_ids :
            query_where += " AND so.branch_id in %s" % str(tuple(branch_ids)).replace(',)', ')')
        if dealer_ids :
            query_where += " AND so.partner_id in %s" % str(tuple(dealer_ids)).replace(',)', ')')
        
        query_where += " AND so.confirm_date is not null"
        
        query_order = "order by b.code"

        query_sales = ""
        query_cancel = ""

        if division == 'Unit' :
            query_sales = """
                select 
                b.code as branch_code, 
                b.name as branch_name, 
                so.name as name, 
                CASE WHEN so.state = 'progress' THEN 'Sales Order' 
                     WHEN so.state = 'done' THEN 'Done' 
                     WHEN so.state = 'unused' THEN 'Unused'
                     WHEN so.state IS NULL THEN '' 
                ELSE so.state END as state, 
                to_char(so.date_order + interval '%s', 'YYYY-MM-DD HH12:MI') as date_order, 
                customer.default_code as cust_code, 
                customer.name as cust_name, 
                product.name_template as type, 
                pav.code as warna, 
                sol.product_uom_qty as qty,
                COALESCE(inv.force_cogs,0) / sol.product_uom_qty as hpp,
                sol.price_unit as harga_jual, 
                sol.discount as disc,
                sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 as harga_jual_excl_tax,
                COALESCE(inv.force_cogs,0) as total_hpp,
                invs.number as no_invoice,                
                sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty as nett_sales,
                COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty as discount_cash_avg,
                COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty as discount_lain_avg,
                COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty as discount_program_avg,
                (sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty) - (COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty) as dpp,
                ((sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty) - (COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty)) * 0.1 as tax,
                ((sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty) - (COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty)) * 1.1 as total,
                ((sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty) - (COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty)) - COALESCE(inv.force_cogs,0) as gp,
                (((sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty) - (COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty)) - COALESCE(inv.force_cogs,0)) / sol.product_uom_qty as gp_avg,
                COALESCE(prod_category.name,'') as categ_name,
                COALESCE(prod_category2.name,'') as categ2_name,
                COALESCE(prod_template.series,'') as prod_series,
                COALESCE(fp.name,'') as faktur_pajak, 
                0 as soc_id
                from sale_order so
                inner join sale_order_line sol on so.id = sol.order_id
                LEFT JOIN account_invoice as invs
                ON invs.origin=so.name and invs.state != 'draft' and invs.type = 'out_invoice'
                inner join (select tent_so.id, COALESCE(sum(tent_sol.product_uom_qty),0) as total_qty from sale_order tent_so inner join sale_order_line tent_sol on tent_so.id = tent_sol.order_id group by tent_so.id) tent on so.id = tent.id
                left join wtc_branch b on so.branch_id = b.id
                left join res_partner customer on so.partner_id = customer.id
                left join product_product product on sol.product_id = product.id
                left join product_template prod_template ON product.product_tmpl_id = prod_template.id
                left join product_category prod_category ON prod_template.categ_id = prod_category.id
                left join product_category prod_category2 ON prod_category.parent_id = prod_category2.id
                left join wtc_faktur_pajak_out fp ON so.faktur_pajak_id = fp.id
                left join product_attribute_value_product_product_rel pavpp on pavpp.prod_id = product.id
                left join product_attribute_value pav on pavpp.att_id = pav.id
                left join (select ai.origin, ail.product_id, ail.force_cogs from account_invoice ai
                inner join account_invoice_line ail on ai.id = ail.invoice_id and ai.type = 'out_invoice' and ai.state != 'draft' where ail.product_id is not null) inv on inv.origin = so.name and inv.product_id = sol.product_id 
                %s %s
            """ % (tz,query_where,query_order) 
        else :
            query_sales = """
                select 
                b.code as branch_code, 
                b.name as branch_name, 
                so.name as name, 
                CASE WHEN so.state = 'progress' THEN 'Sales Order' 
                     WHEN so.state = 'done' THEN 'Done' 
                     WHEN so.state = 'unused' THEN 'Unused'
                     WHEN so.state IS NULL THEN '' 
                ELSE so.state END as state, 
                to_char(so.date_order + interval '%s', 'YYYY-MM-DD HH12:MI') as date_order, 
                customer.default_code as cust_code, 
                customer.name as cust_name, 
                product.name_template as type, 
                '' as warna, 
                sol.product_uom_qty as qty,
                COALESCE(inv.force_cogs,0) / sol.product_uom_qty as hpp,
                sol.price_unit as harga_jual, 
                sol.discount as disc,
                sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 as harga_jual_excl_tax,
                COALESCE(inv.force_cogs,0) as total_hpp,
                invs.number as no_invoice,
                sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty as nett_sales,
                COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty as discount_cash_avg,
                COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty as discount_lain_avg,
                COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty as discount_program_avg,
                (sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty) - (COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty) as dpp,
                ((sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty) - (COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty)) * 0.1 as tax,
                ((sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty) - (COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty)) * 1.1 as total,
                ((sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty) - (COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty)) - COALESCE(inv.force_cogs,0) as gp,
                (((sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty) - (COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty)) - COALESCE(inv.force_cogs,0)) / sol.product_uom_qty as gp_avg,
                COALESCE(prod_category.name,'') as categ_name,
                COALESCE(prod_category2.name,'') as categ2_name,
                COALESCE(prod_template.series,'') as prod_series,
                COALESCE(fp.name,'') as faktur_pajak,
                0 as soc_id
                from sale_order so
                inner join sale_order_line sol on so.id = sol.order_id
                LEFT JOIN account_invoice as invs
                ON invs.origin=so.name and invs.state != 'draft' and invs.type = 'out_invoice'
                inner join (select tent_so.id, COALESCE(sum(tent_sol.product_uom_qty),0) as total_qty from sale_order tent_so inner join sale_order_line tent_sol on tent_so.id = tent_sol.order_id group by tent_so.id) tent on so.id = tent.id
                left join wtc_branch b on so.branch_id = b.id
                left join res_partner customer on so.partner_id = customer.id
                left join product_product product on sol.product_id = product.id
                left join product_template prod_template ON product.product_tmpl_id = prod_template.id
                left join product_category prod_category ON prod_template.categ_id = prod_category.id
                left join product_category prod_category2 ON prod_category.parent_id = prod_category2.id
                left join wtc_faktur_pajak_out fp ON so.faktur_pajak_id = fp.id
                left join (select ai.origin, ail.product_id, ail.force_cogs from account_invoice ai
                inner join account_invoice_line ail on ai.id = ail.invoice_id and ai.type = 'out_invoice' and ai.state != 'draft' where ail.product_id is not null) inv on inv.origin = so.name and inv.product_id = sol.product_id
                %s %s
            """ % (tz,query_where,query_order)                     

        if state in ('all', 'cancel') :
            if division == 'Unit' :
                query_cancel = """
                    select 
                    b.code as branch_code, 
                    b.name as branch_name, 
                    so.name as name, 
                    CASE WHEN so.state = 'progress' THEN 'Sales Order' 
                         WHEN so.state = 'done' THEN 'Done' 
                        WHEN so.state = 'unused' THEN 'Unused'
                         WHEN so.state IS NULL THEN '' 
                    ELSE so.state END as state, 
                    to_char(so.date_order + interval '%s', 'YYYY-MM-DD HH12:MI') as date_order, 
                    customer.default_code as cust_code, 
                    customer.name as cust_name, 
                    product.name_template as type, 
                    pav.code as warna, 
                    sol.product_uom_qty as qty,
                    COALESCE(inv.force_cogs,0) / sol.product_uom_qty as hpp,
                    sol.price_unit as harga_jual, 
                    sol.discount as disc,
                    sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 as harga_jual_excl_tax,
                    COALESCE(inv.force_cogs,0) as total_hpp,
                    invs.number as no_invoice,                
                    sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty as nett_sales,
                    COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty as discount_cash_avg,
                    COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty as discount_lain_avg,
                    COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty as discount_program_avg,
                    (sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty) - (COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty) as dpp,
                    ((sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty) - (COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty)) * 0.1 as tax,
                    ((sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty) - (COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty)) * 1.1 as total,
                    ((sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty) - (COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty)) - COALESCE(inv.force_cogs,0) as gp,
                    (((sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty) - (COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty)) - COALESCE(inv.force_cogs,0)) / sol.product_uom_qty as gp_avg,
                    COALESCE(prod_category.name,'') as categ_name,
                    COALESCE(prod_category2.name,'') as categ2_name,
                    COALESCE(prod_template.series,'') as prod_series,
                    COALESCE(fp.name,'') as faktur_pajak, 
                    coalesce(soc.id,0) as soc_id
                    from sale_order_cancel soc 
                    inner join sale_order so on soc.sale_order_id = so.id and soc.state = 'confirmed' %s
                    inner join sale_order_line sol on so.id = sol.order_id
                    LEFT JOIN account_invoice as invs
                    ON invs.origin=so.name and invs.state != 'draft' and invs.type = 'out_invoice'
                    inner join (select tent_so.id, COALESCE(sum(tent_sol.product_uom_qty),0) as total_qty from sale_order tent_so inner join sale_order_line tent_sol on tent_so.id = tent_sol.order_id group by tent_so.id) tent on so.id = tent.id
                    left join wtc_branch b on so.branch_id = b.id
                    left join res_partner customer on so.partner_id = customer.id
                    left join product_product product on sol.product_id = product.id
                    left join product_template prod_template ON product.product_tmpl_id = prod_template.id
                    left join product_category prod_category ON prod_template.categ_id = prod_category.id
                    left join product_category prod_category2 ON prod_category.parent_id = prod_category2.id
                    left join wtc_faktur_pajak_out fp ON so.faktur_pajak_id = fp.id
                    left join product_attribute_value_product_product_rel pavpp on pavpp.prod_id = product.id
                    left join product_attribute_value pav on pavpp.att_id = pav.id
                    left join (select ai.origin, ail.product_id, ail.force_cogs from account_invoice ai
                    inner join account_invoice_line ail on ai.id = ail.invoice_id and ai.type = 'out_invoice' and ai.state != 'draft' where ail.product_id is not null) inv on inv.origin = so.name and inv.product_id = sol.product_id 
                    %s %s
                """ % (tz,query_where_cancel,query_where,query_order) 
            else :
                query_cancel = """
                    select 
                    b.code as branch_code, 
                    b.name as branch_name, 
                    so.name as name, 
                    CASE WHEN so.state = 'progress' THEN 'Sales Order' 
                         WHEN so.state = 'done' THEN 'Done' 
                        WHEN so.state = 'unused' THEN 'Unused'
                         WHEN so.state IS NULL THEN '' 
                    ELSE so.state END as state, 
                    to_char(so.date_order + interval '%s', 'YYYY-MM-DD HH12:MI') as date_order, 

                    customer.default_code as cust_code, 
                    customer.name as cust_name, 
                    product.name_template as type, 
                    '' as warna, 
                    sol.product_uom_qty as qty,
                    COALESCE(inv.force_cogs,0) / sol.product_uom_qty as hpp,
                    sol.price_unit as harga_jual, 
                    sol.discount as disc,
                    sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 as harga_jual_excl_tax,
                    COALESCE(inv.force_cogs,0) as total_hpp,
                    invs.number as no_invoice,
                    sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty as nett_sales,
                    COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty as discount_cash_avg,
                    COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty as discount_lain_avg,
                    COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty as discount_program_avg,
                    (sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty) - (COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty) as dpp,
                    ((sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty) - (COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty)) * 0.1 as tax,
                    ((sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty) - (COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty)) * 1.1 as total,
                    ((sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty) - (COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty)) - COALESCE(inv.force_cogs,0) as gp,
                    (((sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty) - (COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty)) - COALESCE(inv.force_cogs,0)) / sol.product_uom_qty as gp_avg,
                    COALESCE(prod_category.name,'') as categ_name,
                    COALESCE(prod_category2.name,'') as categ2_name,
                    COALESCE(prod_template.series,'') as prod_series,
                    COALESCE(fp.name,'') as faktur_pajak,
                    coalesce(soc.id,0) as soc_id
                    from sale_order_cancel soc
                    inner join sale_order so on soc.sale_order_id = so.id and soc.state = 'confirmed' %s
                    inner join sale_order_line sol on so.id = sol.order_id
                    LEFT JOIN account_invoice as invs
                    ON invs.origin=so.name and invs.state != 'draft' and invs.type = 'out_invoice'
                    inner join (select tent_so.id, COALESCE(sum(tent_sol.product_uom_qty),0) as total_qty from sale_order tent_so inner join sale_order_line tent_sol on tent_so.id = tent_sol.order_id group by tent_so.id) tent on so.id = tent.id
                    left join wtc_branch b on so.branch_id = b.id
                    left join res_partner customer on so.partner_id = customer.id
                    left join product_product product on sol.product_id = product.id
                    left join product_template prod_template ON product.product_tmpl_id = prod_template.id
                    left join product_category prod_category ON prod_template.categ_id = prod_category.id
                    left join product_category prod_category2 ON prod_category.parent_id = prod_category2.id
                    left join wtc_faktur_pajak_out fp ON so.faktur_pajak_id = fp.id
                    left join (select ai.origin, ail.product_id, ail.force_cogs from account_invoice ai
                    inner join account_invoice_line ail on ai.id = ail.invoice_id and ai.type = 'out_invoice' and ai.state != 'draft' where ail.product_id is not null) inv on inv.origin = so.name and inv.product_id = sol.product_id
                    %s %s
                """ % (tz,query_where_cancel,query_where,query_order)

        if state == 'cancel' :
            query = query_cancel
        elif state == 'all' :
            query = """
                SELECT * 
                FROM ((%s) UNION (%s)) a
                ORDER BY branch_code, date_order
                """ % (query_sales, query_cancel)
        else :
            query = query_sales

        cr.execute (query)
        ress = cr.fetchall()

        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")

        if type_file == 'csv':
            content = "Branch Code,Branch Name,SO Number,State,Date,Customer Code,Customer Name,Type,Color,Qty,Harga Jual,Disc (%),Harga Jual Excl Tax,Sales,Disc Cash (Avg),Disc Lain (Avg),Disc Program (Avg),DPP,Tax,Total Piutang,Category Name,Parent Category Name,Sales,No Invoice,Faktur Pajak \r\n"
            for res in ress:
                branch_code = str(res[0].encode('ascii','ignore').decode('ascii')) if res[0] != None else ''
                branch_name = str(res[1].encode('ascii','ignore').decode('ascii')) if res[1] != None else ''
                name = str(res[2].encode('ascii','ignore').decode('ascii')) if res[2] != None else ''
                state = str(res[3].encode('ascii','ignore').decode('ascii')) if res[3] != None else ''
                date_order = str(res[4].encode('ascii','ignore').decode('ascii')) if res[4] != None else ''
                # date_order = datetime.strptime(res[4][0:22], "%Y-%m-%d %I:%M %p") if res[4] else ''
                cust_code = str(res[5].encode('ascii','ignore').decode('ascii')) if res[5] != None else ''
                cust_name = str(res[6].encode('ascii','ignore').decode('ascii')) if res[6] != None else ''
                type = str(res[7].encode('ascii','ignore').decode('ascii')) if res[7] != None else ''
                warna = str(res[8].encode('ascii','ignore').decode('ascii')) if res[8] != None else ''
                qty = res[9]
                hpp = res[10]
                harga_jual = res[11]
                disc = res[12]
                harga_jual_excl_tax = res[13]
                total_hpp = res[14]
                no_invoice = str(res[15].encode('ascii','ignore').decode('ascii')) if res[15] != None else ''            
                nett_sales = res[16]
                discount_cash_avg = res[17]
                discount_lain_avg = res[18]
                discount_program_avg = res[19]
                dpp = res[20]
                tax = res[21]
                total = res[22]
                gp = res[23]
                gp_avg = res[24]
                categ_name = str(res[25].encode('ascii','ignore').decode('ascii')) if res[25] != None else ''
                categ2_name = str(res[26].encode('ascii','ignore').decode('ascii')) if res[26] != None else ''
                prod_series = str(res[27].encode('ascii','ignore').decode('ascii')) if res[27] != None else ''
                faktur_pajak = str(res[28].encode('ascii','ignore').decode('ascii')) if res[28] != None else ''
                soc_id = res[29]

                if soc_id > 0 :
                    qty = -qty
                    hpp = -hpp
                    harga_jual = -harga_jual
                    disc = -disc
                    harga_jual_excl_tax = -harga_jual_excl_tax
                    total_hpp = -total_hpp
                    nett_sales = -nett_sales
                    discount_cash_avg = -discount_cash_avg
                    discount_lain_avg = -discount_lain_avg
                    discount_program_avg = -discount_program_avg
                    dpp = -dpp
                    tax = -tax
                    total = -total
                    gp = -gp
                    gp_avg = -gp_avg

                content += "%s," %branch_code
                content += "%s," %branch_name
                content += "%s," %name
                content += "%s," %state
                content += "%s," %date_order
                content += "%s," %cust_code
                content += "%s," %cust_name
                content += "%s," %type
                content += "%s," %warna
                content += "%s," %qty
                content += "%s," %harga_jual
                content += "%s," %disc
                content += "%s," %harga_jual_excl_tax
                content += "%s," %nett_sales
                content += "%s," %discount_cash_avg
                content += "%s," %discount_lain_avg
                content += "%s," %discount_program_avg
                content += "%s," %dpp
                content += "%s," %tax
                content += "%s," %total
                content += "%s," %categ_name
                content += "%s," %categ2_name
                content += "%s," %prod_series
                content += "%s," %no_invoice
                content += "%s \r\n" %faktur_pajak

            filename = 'Report Penjualan MD '+str(date)+'.csv'
            out = base64.encodestring(content)

        else:
            fp = StringIO()
            workbook = xlsxwriter.Workbook(fp)        
            workbook = self.add_workbook_format(cr, uid, workbook)
            wbf=self.wbf
            worksheet = workbook.add_worksheet('Penjualan MD')
            worksheet.set_column('B1:B1', 13)
            worksheet.set_column('C1:C1', 21)
            worksheet.set_column('D1:D1', 25)
            worksheet.set_column('E1:E1', 18)
            worksheet.set_column('F1:F1', 20)
            worksheet.set_column('G1:G1', 11)
            worksheet.set_column('H1:H1', 30)
            worksheet.set_column('I1:I1', 11)
            worksheet.set_column('J1:J1', 18)
            worksheet.set_column('K1:K1', 15)
            worksheet.set_column('L1:L1', 20)
            worksheet.set_column('M1:M1', 20)
            worksheet.set_column('N1:N1', 20)
            worksheet.set_column('O1:O1', 20)
            worksheet.set_column('P1:P1', 20)
            worksheet.set_column('Q1:Q1', 20)
            worksheet.set_column('R1:R1', 20)
            worksheet.set_column('S1:S1', 20)
            worksheet.set_column('T1:T1', 20)
            worksheet.set_column('U1:U1', 20)
            worksheet.set_column('V1:V1', 20)
            worksheet.set_column('W1:W1', 20)
            worksheet.set_column('X1:X1', 20)
            worksheet.set_column('Y1:Y1', 20)
            worksheet.set_column('Z1:Z1', 20)
            worksheet.set_column('AA1:AA1', 8)
            worksheet.set_column('AB1:AB1', 8)
            worksheet.set_column('AC1:AC1', 20)
            worksheet.set_column('AD1:AD1', 20)      
                            
            company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
            user = self._get_default(cr, uid, user=True, context=context).name
            
            filename = 'Report Penjualan MD Non HPP '+str(date)+'.xlsx'        
            worksheet.write('A1', company_name , wbf['company'])
            worksheet.write('A2', 'Report Penjualan MD Non HPP' , wbf['title_doc'])
            worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])
            row=3
            rowsaldo = row
            row+=1
            worksheet.write('A%s' % (row+1), 'No' , wbf['header'])
            worksheet.write('B%s' % (row+1), 'Branch Code' , wbf['header'])
            worksheet.write('C%s' % (row+1), 'Branch Name' , wbf['header'])
            worksheet.write('D%s' % (row+1), 'SO Number' , wbf['header'])
            worksheet.write('E%s' % (row+1), 'State' , wbf['header'])
            worksheet.write('F%s' % (row+1), 'Date' , wbf['header'])
            worksheet.write('G%s' % (row+1), 'Customer Code' , wbf['header'])
            worksheet.write('H%s' % (row+1), 'Customer Name' , wbf['header'])
            worksheet.write('I%s' % (row+1), 'Type' , wbf['header'])
            worksheet.write('J%s' % (row+1), 'Color' , wbf['header'])
            worksheet.write('K%s' % (row+1), 'Qty' , wbf['header'])
            # worksheet.write('L%s' % (row+1), 'HPP' , wbf['header'])
            worksheet.write('L%s' % (row+1), 'Harga Jual' , wbf['header'])
            worksheet.write('M%s' % (row+1), 'Disc (%)' , wbf['header'])
            worksheet.write('N%s' % (row+1), 'Harga Jual Excl Tax' , wbf['header'])
            worksheet.write('O%s' % (row+1), 'Sales' , wbf['header'])
            worksheet.write('P%s' % (row+1), 'Disc Cash (Avg)' , wbf['header'])
            worksheet.write('Q%s' % (row+1), 'Disc Lain (Avg)' , wbf['header'])
            worksheet.write('R%s' % (row+1), 'Disc Program (Avg)' , wbf['header'])
            worksheet.write('S%s' % (row+1), 'DPP' , wbf['header'])
            worksheet.write('T%s' % (row+1), 'Tax' , wbf['header'])
            worksheet.write('U%s' % (row+1), 'Total Piutang' , wbf['header'])
            worksheet.write('V%s' % (row+1), 'Category Name' , wbf['header'])
            worksheet.write('W%s' % (row+1), 'Parent Category Name' , wbf['header'])
            worksheet.write('X%s' % (row+1), 'Sales' , wbf['header'])
            worksheet.write('Y%s' % (row+1), 'No Invoice' , wbf['header'])
            worksheet.write('Z%s' % (row+1), 'Faktur Pajak' , wbf['header'])

                           
            row+=2               
            no = 1     
            row1 = row
            
            total_qty = 0
            total_hpp = 0
            total_harga_jual = 0
            total_disc = 0
            total_harga_jual_excl_tax = 0
            total_total_hpp = 0
            total_sales = 0
            total_disc_cash = 0
            total_disc_lain = 0
            total_disc_program = 0
            total_dpp = 0
            total_tax = 0
            total_total_piutang = 0
            total_gross_profit = 0
            total_gross_profit_avg = 0
            
            for res in ress:
                branch_code = str(res[0].encode('ascii','ignore').decode('ascii')) if res[0] != None else ''
                branch_name = str(res[1].encode('ascii','ignore').decode('ascii')) if res[1] != None else ''
                name = str(res[2].encode('ascii','ignore').decode('ascii')) if res[2] != None else ''
                state = str(res[3].encode('ascii','ignore').decode('ascii')) if res[3] != None else ''
                date_order = str(res[4].encode('ascii','ignore').decode('ascii')) if res[4] != None else ''
                # date_order = datetime.strptime(res[4][0:22], "%Y-%m-%d %I:%M %p") if res[4] else ''
                cust_code = str(res[5].encode('ascii','ignore').decode('ascii')) if res[5] != None else ''
                cust_name = str(res[6].encode('ascii','ignore').decode('ascii')) if res[6] != None else ''
                type = str(res[7].encode('ascii','ignore').decode('ascii')) if res[7] != None else ''
                warna = str(res[8].encode('ascii','ignore').decode('ascii')) if res[8] != None else ''
                qty = res[9]
                hpp = res[10]
                harga_jual = res[11]
                disc = res[12]
                harga_jual_excl_tax = res[13]
                total_hpp = res[14]
                no_invoice = str(res[15].encode('ascii','ignore').decode('ascii')) if res[15] != None else ''            
                nett_sales = res[16]
                discount_cash_avg = res[17]
                discount_lain_avg = res[18]
                discount_program_avg = res[19]
                dpp = res[20]
                tax = res[21]
                total = res[22]
                gp = res[23]
                gp_avg = res[24]
                categ_name = str(res[25].encode('ascii','ignore').decode('ascii')) if res[25] != None else ''
                categ2_name = str(res[26].encode('ascii','ignore').decode('ascii')) if res[26] != None else ''
                prod_series = str(res[27].encode('ascii','ignore').decode('ascii')) if res[27] != None else ''
                faktur_pajak = str(res[28].encode('ascii','ignore').decode('ascii')) if res[28] != None else ''
                soc_id = res[29]

                if soc_id > 0 :
                    qty = -qty
                    hpp = -hpp
                    harga_jual = -harga_jual
                    disc = -disc
                    harga_jual_excl_tax = -harga_jual_excl_tax
                    total_hpp = -total_hpp
                    nett_sales = -nett_sales
                    discount_cash_avg = -discount_cash_avg
                    discount_lain_avg = -discount_lain_avg
                    discount_program_avg = -discount_program_avg
                    dpp = -dpp
                    tax = -tax
                    total = -total
                    gp = -gp
                    gp_avg = -gp_avg
                
                worksheet.write('A%s' % row, no , wbf['content_number'])                    
                worksheet.write('B%s' % row, branch_code , wbf['content'])
                worksheet.write('C%s' % row, branch_name , wbf['content'])
                worksheet.write('D%s' % row, name , wbf['content'])
                worksheet.write('E%s' % row, state , wbf['content'])
                worksheet.write('F%s' % row, date_order , wbf['content_datetime_12_hr'])
                worksheet.write('G%s' % row, cust_code , wbf['content'])
                worksheet.write('H%s' % row, cust_name , wbf['content']) 
                worksheet.write('I%s' % row, type, wbf['content'])  
                worksheet.write('J%s' % row, warna , wbf['content'])
                worksheet.write('K%s' % row, qty , wbf['content_number'])
                # worksheet.write('L%s' % row, hpp , wbf['content_float'])
                worksheet.write('L%s' % row, harga_jual , wbf['content_float'])
                worksheet.write('M%s' % row, disc , wbf['content_float'])
                worksheet.write('N%s' % row, harga_jual_excl_tax , wbf['content_float'])
                worksheet.write('O%s' % row, nett_sales, wbf['content_float'])
                worksheet.write('P%s' % row, discount_cash_avg , wbf['content_float']) 
                worksheet.write('Q%s' % row, discount_lain_avg , wbf['content_float'])
                worksheet.write('R%s' % row, discount_program_avg , wbf['content_float'])
                worksheet.write('S%s' % row, dpp , wbf['content_float'])
                worksheet.write('T%s' % row, tax , wbf['content_float'])
                worksheet.write('U%s' % row, total , wbf['content_float'])
                worksheet.write('V%s' % row, categ_name , wbf['content'])
                worksheet.write('W%s' % row, categ2_name , wbf['content'])
                worksheet.write('X%s' % row, prod_series , wbf['content'])
                worksheet.write('Y%s' % row, no_invoice , wbf['content'])
                worksheet.write('Z%s' % row, faktur_pajak , wbf['content'])
                no+=1
                row+=1
                
                total_qty += qty
                total_hpp += hpp
                total_harga_jual += harga_jual
                total_disc += disc
                total_harga_jual_excl_tax += harga_jual_excl_tax
                total_total_hpp += total_hpp
                total_sales += nett_sales
                total_disc_cash += discount_cash_avg
                total_disc_lain += discount_lain_avg
                total_disc_program += discount_program_avg
                total_dpp += dpp
                total_tax += tax
                total_total_piutang += total
                total_gross_profit += gp
                total_gross_profit_avg += gp_avg
            
            worksheet.autofilter('A5:Z%s' % (row))  
            worksheet.freeze_panes(5, 3)
            
            #TOTAL
            worksheet.merge_range('A%s:C%s' % (row,row), 'Total', wbf['total'])    
            worksheet.merge_range('D%s:J%s' % (row,row), '', wbf['total'])
            worksheet.merge_range('V%s:Z%s' % (row,row), '', wbf['total']) 
            
            formula_total_qty = '{=subtotal(9,K%s:K%s)}' % (row1, row-1) 
            # formula_total_hpp = '{=subtotal(9,L%s:L%s)}' % (row1, row-1) 
            formula_total_harga_jual = '{=subtotal(9,L%s:L%s)}' % (row1, row-1) 
            formula_total_disc = '{=subtotal(9,M%s:M%s)}' % (row1, row-1) 
            formula_total_harga_jual_excl_tax = '{=subtotal(9,N%s:N%s)}' % (row1, row-1) 
            formula_total_formula_total_hpp = '{=subtotal(9,O%s:O%s)}' % (row1, row-1) 
            formula_total_sales = '{=subtotal(9,P%s:P%s)}' % (row1, row-1) 
            formula_total_disc_cash = '{=subtotal(9,Q%s:Q%s)}' % (row1, row-1) 
            formula_total_disc_lain = '{=subtotal(9,R%s:R%s)}' % (row1, row-1) 
            formula_total_disc_program = '{=subtotal(9,S%s:S%s)}' % (row1, row-1) 
            formula_total_tax = '{=subtotal(9,T%s:T%s)}' % (row1, row-1) 
            formula_total_formula_total_piutang = '{=subtotal(9,U%s:U%s)}' % (row1, row-1) 

            worksheet.write_formula(row-1,10,formula_total_qty, wbf['total_number'], total_qty)                  
            # worksheet.write_formula(row-1,11,formula_total_hpp, wbf['total_float'], total_hpp)
            worksheet.write_formula(row-1,11,formula_total_harga_jual, wbf['total_float'],total_harga_jual)
            worksheet.write_formula(row-1,12,formula_total_disc, wbf['total_float'], total_disc)
            worksheet.write_formula(row-1,13,formula_total_harga_jual_excl_tax, wbf['total_float'], total_harga_jual_excl_tax) 
            worksheet.write_formula(row-1,14,formula_total_formula_total_hpp, wbf['total_float'], total_total_hpp)
            worksheet.write_formula(row-1,15,formula_total_sales, wbf['total_float'], total_sales)
            worksheet.write_formula(row-1,16,formula_total_disc_cash, wbf['total_float'], total_disc_cash)
            worksheet.write_formula(row-1,17,formula_total_disc_lain, wbf['total_float'], total_disc_lain)
            worksheet.write_formula(row-1,18,formula_total_disc_program, wbf['total_float'], total_disc_program)
            worksheet.write_formula(row-1,19,formula_total_tax, wbf['total_float'], total_tax)
            worksheet.write_formula(row-1,20,formula_total_formula_total_piutang, wbf['total_float'], total_total_piutang)
            worksheet.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])  
                       
            workbook.close()
            out=base64.encodestring(fp.getvalue())
            fp.close()
        
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_penjualan_md', 'view_report_penjualan_md_wizard')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.report.penjualan.md.wizard',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }

