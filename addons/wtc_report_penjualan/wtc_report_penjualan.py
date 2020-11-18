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

class wtc_report_penjualan(osv.osv_memory):
   
    _name = "wtc.report.penjualan.wizard"
    _description = "Penjualan Report"

    wbf = {}

    def _get_default(self,cr,uid,date=False,user=False,context=None):
        if date :
            return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)
        else :
            return self.pool.get('res.users').browse(cr, uid, uid)
        
    def _get_branch_ids(self, cr, uid, context=None):
        branch_ids_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
        branch_ids = [b.id for b in branch_ids_user]
        return branch_ids
    
    def _get_categ_ids(self, cr, uid, context=None):
        obj_categ = self.pool.get('product.category')
        all_categ_ids = obj_categ.search(cr, uid, [])
        categ_ids = obj_categ.get_child_ids(cr, uid, all_categ_ids, 'Unit')
        return categ_ids
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(wtc_report_penjualan, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        branch_ids = self._get_branch_ids(cr, uid, context)
        categ_ids = self._get_categ_ids(cr, uid, context)
        
        doc = etree.XML(res['arch'])
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
        nodes_product = doc.xpath("//field[@name='product_ids']")
        
        for node in nodes_branch :
            node.set('domain', '[("id", "in", '+ str(branch_ids)+')]')
        for node in nodes_product :
            node.set('domain', '[("categ_id", "in", '+ str(categ_ids)+')]')
        
        res['arch'] = etree.tostring(doc)
        return res
        
    _columns = {
        'state_x': fields.selection( ( ('choose','choose'),('get','get'))), #xls
        'data_x': fields.binary('File', readonly=True),
        'name': fields.char('Filename', 100, readonly=True), 
        'options': fields.selection([('detail_per_chassis_engine','Detail Per Chassis & Engine'),('direct_gift','Direct Gift')], 'Options', required=True, change_default=True, select=True),
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
        'sales_koordinator_id': fields.many2one('res.users','Sales Koordinator'),
        'user_id': fields.many2one('res.users', 'Sales Person'),
        'product_ids': fields.many2many('product.product', 'wtc_report_penjualan_product_rel', 'wtc_report_penjualan_wizard_id',
            'product_id', 'Products'),
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'state': fields.selection([('all','All'), ('progress','Outstanding'), ('done','Paid'), ('progress_done','Outstanding & Paid'), ('progress_done_cancelled', 'Outstanding, Paid & Cancelled'), ('cancelled','Cancelled'),('unused', 'Unused')], 'State', required=True, change_default=True, select=True),
        'branch_ids': fields.many2many('wtc.branch', 'wtc_report_penjualan_branch_rel', 'wtc_report_penjualan_wizard_id',
            'branch_id', 'Branches', copy=False),
        'finco_ids': fields.many2many('res.partner', 'wtc_report_penjualan_partner_rel', 'wtc_report_penjualan_wizard_id',
            'finco_id', 'Finco', copy=False, domain=[('finance_company','=',True)]),        
    }

    _defaults = {
        'state_x': lambda *a: 'choose',
        'state': 'progress_done_cancelled',
        'start_date':datetime.today(),
        'end_date':datetime.today(),
        'options': 'detail_per_chassis_engine',
    }
    
    def add_workbook_format(self, cr, uid, workbook):      
        self.wbf['header'] = workbook.add_format({'bold': 1,'align': 'center','bg_color': '#FFFFDB','font_color': '#000000'})
        self.wbf['header'].set_border()

        self.wbf['header_no'] = workbook.add_format({'bold': 1,'align': 'center','bg_color': '#FFFFDB','font_color': '#000000'})
        self.wbf['header_no'].set_border()
        self.wbf['header_no'].set_align('vcenter')
                
        self.wbf['footer'] = workbook.add_format({'align':'left'})
        
        self.wbf['content_datetime'] = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss'})
        self.wbf['content_datetime'].set_left()
        self.wbf['content_datetime'].set_right()
                
        self.wbf['content_date'] = workbook.add_format({'num_format': 'yyyy-mm-dd'})
        self.wbf['content_date'].set_left()
        self.wbf['content_date'].set_right() 
        
        self.wbf['title_doc'] = workbook.add_format({'bold': 1,'align': 'left'})
        self.wbf['title_doc'].set_font_size(12)
        
        self.wbf['company'] = workbook.add_format({'align': 'left'})
        self.wbf['company'].set_font_size(11)
        
        self.wbf['content'] = workbook.add_format()
        self.wbf['content'].set_left()
        self.wbf['content'].set_right() 
        
        self.wbf['content_float'] = workbook.add_format({'align': 'right','num_format': '#,##0.00'})
        self.wbf['content_float'].set_right() 
        self.wbf['content_float'].set_left()

        self.wbf['content_center'] = workbook.add_format({'align': 'centre'})
        
        self.wbf['content_number'] = workbook.add_format({'align': 'right'})
        self.wbf['content_number'].set_right() 
        self.wbf['content_number'].set_left() 
                
        self.wbf['content_percent'] = workbook.add_format({'align': 'right','num_format': '0.00%'})
        self.wbf['content_percent'].set_right() 
        self.wbf['content_percent'].set_left() 
                
        self.wbf['total_float'] = workbook.add_format({'bold':1,'bg_color': '#FFFFDB','align': 'right','num_format': '#,##0.00'})
        self.wbf['total_float'].set_top()
        self.wbf['total_float'].set_bottom()            
        self.wbf['total_float'].set_left()
        self.wbf['total_float'].set_right()         
        
        self.wbf['total_number'] = workbook.add_format({'align':'right','bg_color': '#FFFFDB','bold':1})
        self.wbf['total_number'].set_top()
        self.wbf['total_number'].set_bottom()            
        self.wbf['total_number'].set_left()
        self.wbf['total_number'].set_right()
        
        self.wbf['total'] = workbook.add_format({'bold':1,'bg_color': '#FFFFDB','align':'center'})
        self.wbf['total'].set_left()
        self.wbf['total'].set_right()
        self.wbf['total'].set_top()
        self.wbf['total'].set_bottom()
        
        return workbook
        

    def excel_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
            
        data = self.read(cr, uid, ids,context=context)[0]
        if len(data['branch_ids']) == 0 :
            data.update({'branch_ids': self._get_branch_ids(cr, uid, context)})

        if data['options']== 'detail_per_chassis_engine':
            self._print_excel_report(cr, uid, ids, data, context=context)
        else:
            self._print_excel_report_direct_gift(cr, uid, ids, data, context=context)

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_penjualan', 'view_report_penjualan_wizard')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.report.penjualan.wizard',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }

    def _print_excel_report(self, cr, uid, ids, data, context=None):        
        #section_id = data['section_id'][0] if data['section_id'] else False
        sales_koordinator_id = data['sales_koordinator_id'][0] if data['sales_koordinator_id'] else False
        user_id = data['user_id'][0] if data['user_id'] else False
        product_ids = data['product_ids']
        start_date = data['start_date']
        end_date = data['end_date']
        state = data['state']
        branch_ids = data['branch_ids']
        finco_ids = data['finco_ids']       

        query_where_sales = ""
        query_where_cancel = ""
        query_where = " WHERE 1=1  "

        #if section_id :
        #    query_where += " AND dso.section_id = '%s'" % str(section_id)
        if sales_koordinator_id :
            query_where += " AND dso.sales_koordinator_id = '%s'" % str(sales_koordinator_id)
        if user_id :
            query_where += " AND dso.user_id = '%s'" % str(user_id)
        if product_ids :
            query_where += " AND dsol.product_id in %s" % str(
                tuple(product_ids)).replace(',)', ')')
        if start_date :
            query_where_sales += " AND dso.date_order >= '%s'" % str(start_date)
            query_where_cancel += " AND dsoc.date >= '%s'" % str(start_date)
        if end_date :
            query_where_sales += " AND dso.date_order <= '%s'" % str(end_date)
            query_where_cancel += "  AND dsoc.date <= '%s'" % str(end_date)
        if state in ['progress','done','cancelled', 'unused'] :
            query_where += " AND dso.state = '%s'" % str(state)
        elif state == 'progress_done_cancelled' :
            query_where += " AND dso.state in ('progress', 'done', 'cancelled')"
        elif state == 'progress_done' :
            query_where += " AND dso.state in ('progress','done')"
        if branch_ids :
            query_where += " AND dso.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        if finco_ids :
            query_where += " AND dso.finco_id in %s" % str(
                tuple(finco_ids)).replace(',)', ')')

        query_sales = """
            SELECT
            COALESCE(b.code,'') as branch_code, 
            COALESCE(b.name,'') as branch_name, 
            COALESCE(md.default_code,'') as md_code, 
            COALESCE(dso.name,'') as name, 
            CASE WHEN dso.state = 'progress' THEN 'Sales Order' 
                WHEN dso.state = 'done' THEN 'Done' 
                WHEN dso.state = 'cancelled' THEN 'Cancelled'
                WHEN dso.state IS NULL THEN '' 
                ELSE dso.state 
            END as state, 
            dso.date_order as date_order, 
            COALESCE(finco.default_code,'Cash') as finco_code, 
            CASE WHEN dso.is_cod = TRUE THEN 'COD' 
                ELSE 'Reguler' 
            END as is_cod, 
            COALESCE(sales_koor.name,'') as sales_koor_name, 
            COALESCE(hr_sales.nip,'') as sales_nip, 
            COALESCE(sales.name,'') as sales_name, 
            COALESCE(job.name,'') as job_name, 
            COALESCE(cust.default_code,'') as cust_code, 
            COALESCE(cust.name,'') as cust_name,  
            COALESCE(product.name_template,'') as product_name, COALESCE(pav.code,'') as pav_code, COALESCE(dsol.product_qty,0) as product_qty, 
            COALESCE(lot.name,'') as lot_name, COALESCE(lot.chassis_no,'') as lot_chassis, 
            COALESCE(dsol.price_unit,0) as price_unit, 
            COALESCE(dsol.discount_po,0) as discount_po, COALESCE(dsol_disc.ps_dealer,0) as ps_dealer, COALESCE(dsol_disc.ps_ahm,0) as ps_ahm, COALESCE(dsol_disc.ps_md,0) as ps_md, COALESCE(dsol_disc.ps_finco,0) as ps_finco, 
            COALESCE(dsol_disc.ps_dealer,0)+COALESCE(dsol_disc.ps_ahm,0)+COALESCE(dsol_disc.ps_md,0)+COALESCE(dsol_disc.ps_finco,0) as ps_total, 
            COALESCE(dsol.price_unit/1.1,0) as sales, 
            COALESCE(dsol.discount_po/1.1,0) as disc_reg, COALESCE(dsol_disc.discount_pelanggan/1.1,0) as disc_quo, 
            COALESCE(dsol.discount_po/1.1,0)+COALESCE(dsol_disc.discount_pelanggan/1.1,0) as disc_total, 
            COALESCE(dsol.price_subtotal,0) as price_subtotal, round(COALESCE(dsol.price_subtotal,0)*0.1,2) as PPN, COALESCE(dsol.force_cogs,0) as force_cogs, 
            COALESCE(dso.customer_dp,0) as piutang_dp, COALESCE(dso.amount_total,0)-COALESCE(dso.customer_dp,0) as piutang, 
            COALESCE(dsol.price_subtotal,0)-COALESCE(dsol.force_cogs,0)+COALESCE(dsol_disc.ps_ahm,0)+COALESCE(dsol_disc.ps_md,0)+COALESCE(dsol_disc.ps_finco,0) as gp_unit, 
            COALESCE(dsol.price_bbn,0) as price_bbn, COALESCE(dsol.price_bbn_beli,0) as price_bbn_beli, COALESCE(dsol.price_bbn,0)-COALESCE(dsol.price_bbn_beli,0) as gp_bbn, 
            (COALESCE(dsol.price_subtotal,0)-COALESCE(dsol.force_cogs,0)+COALESCE(dsol_disc.ps_ahm,0)+COALESCE(dsol_disc.ps_md,0)+COALESCE(dsol_disc.ps_finco,0))+(COALESCE(dsol.price_bbn,0)-COALESCE(dsol.price_bbn_beli,0)) as gp_total, 
            COALESCE(dsol.amount_hutang_komisi,0) as amount_hutang_komisi, 
            COALESCE(dsol.insentif_finco/1.1,0) as insentif_finco, COALESCE(insentif_finco,0) as dpp_insentif_finco, 
            COALESCE(dsol.discount_po/1.1,0)+COALESCE(dsol_disc.ps_dealer/1.1,0)+COALESCE(amount_hutang_komisi,0) as beban_cabang, 
            COALESCE(prod_category.name,'') as categ_name, 
            COALESCE(prod_category2.name,'') as categ2_name, 
            COALESCE(prod_template.series,'') as prod_series, 
            COALESCE(fp.name,'') as faktur_pajak, 
            dso.date_order - lot.receive_date as aging_stock, 
            stnk.kecamatan as kecamatan,
            '' as dsoc_name, 
            Null as dsoc_date,
            '' as dsoc_reason,
            0 as dsoc_id,
            kec.code as kode_kecamatan,
            dso.sales_source,
            source_loc.name as source_sales_location,
            COALESCE(hr_sales_koor.nip,'') as sales_koor_nip,
            COALESCE(cust.mobile,'') as cust_mobile,
            dsol.finco_tenor as tenor,
            mr.name
            , COALESCE(dsol_brg_bonus.total_brg_bonus,0) as price_total_brg_bonus,
            dsol.finco_no_po as no_po,
            loc_stock.name as location_line,
            dsol.price_bbn_notice,
            dsol.price_bbn_proses,
            dsol.price_bbn_jasa,
            dsol.price_bbn_jasa_area,
            dsol.price_bbn_fee_pusat,
			city.code as kode_city,
            city.name as name_city,
            dso.jaringan_penjualan,
            sp.name as sumber_penjualan,
            tk.name as titik_keramaian,
            loc_tk.name as location_tk,
            src_pos.name as source_pos_location,
            COALESCE(cust.no_ktp,'') as ktp_customer,
            COALESCE(stnk.no_ktp,'') as ktp_stnk
            FROM dealer_sale_order dso 
            LEFT JOIN dealer_sale_order_line dsol on dsol.dealer_sale_order_line_id = dso.id 
            LEFT JOIN wtc_branch b ON dso.branch_id = b.id 
            LEFT JOIN res_partner md ON b.default_supplier_id = md.id 
            LEFT JOIN res_partner finco ON dso.finco_id = finco.id 
            --left join res_users users ON dso.user_id = users.id 
            LEFT JOIN resource_resource sales ON dso.user_id = sales.user_id 
            LEFT JOIN hr_employee hr_sales ON sales.id = hr_sales.resource_id 
            LEFT JOIN hr_job job ON hr_sales.job_id = job.id 
            --left join crm_case_section sales_team ON dso.section_id = sales_team.id 
            LEFT JOIN resource_resource sales_koor ON dso.sales_koordinator_id = sales_koor.user_id 
            LEFT JOIN hr_employee hr_sales_koor ON sales_koor.id = hr_sales_koor.resource_id
            LEFT JOIN res_partner cust ON dso.partner_id = cust.id 
            LEFT JOIN product_product product ON dsol.product_id = product.id 
            LEFT JOIN product_attribute_value_product_product_rel pavpp ON product.id = pavpp.prod_id 
            LEFT JOIN product_attribute_value pav ON pavpp.att_id = pav.id 
            LEFT JOIN product_template prod_template ON product.product_tmpl_id = prod_template.id 
            LEFT JOIN product_category prod_category ON prod_template.categ_id = prod_category.id 
            LEFT JOIN product_category prod_category2 ON prod_category.parent_id = prod_category2.id 
            LEFT JOIN stock_production_lot lot ON dsol.lot_id = lot.id 
            LEFT JOIN res_partner stnk ON lot.customer_stnk = stnk.id
            LEFT JOIN wtc_city city ON stnk.city_id = city.id
            LEFT JOIN wtc_kecamatan kec ON stnk.kecamatan_id = kec.id
            LEFT JOIN wtc_faktur_pajak_out fp ON dso.faktur_pajak_id = fp.id 
            LEFT JOIN stock_location source_loc ON source_loc.id = dso.sales_source_location
            LEFT JOIN ( 
            SELECT dealer_sale_order_line_discount_line_id, sum(ps_finco) as ps_finco, sum(ps_ahm) as ps_ahm, sum(ps_md) as ps_md, sum(ps_dealer) as ps_dealer, sum(ps_others) as ps_others, 
            sum(discount) as discount, sum(discount_pelanggan) as discount_pelanggan 
            FROM dealer_sale_order_line_discount_line 
            GROUP BY dealer_sale_order_line_discount_line_id 
            ) dsol_disc ON dsol_disc.dealer_sale_order_line_discount_line_id = dsol.id
            LEFT JOIN (
            SELECT head.branch_id,line.ring_id,line.kecamatan_id FROM ring_kecamatan_line line LEFT JOIN ring_kecamatan head ON head.id=line.ring_kecamatan_id
            ) ring ON ring.branch_id=b.id and ring.kecamatan_id=kec.id
            LEFT JOIN master_ring mr ON ring.ring_id=mr.id
            
            LEFT JOIN (
            SELECT dealer_sale_order_line_brgbonus_line_id, sum(price_barang) as total_brg_bonus
            FROM dealer_sale_order_line_brgbonus_line 
            GROUP BY dealer_sale_order_line_brgbonus_line_id 
            ) dsol_brg_bonus ON dsol_brg_bonus.dealer_sale_order_line_brgbonus_line_id = dsol.id
            
            LEFT JOIN stock_location loc_stock ON loc_stock.id = dsol.location_id
            LEFT JOIN teds_act_type_sumber_penjualan sp ON sp.id = dso.sumber_penjualan_id
            LEFT JOIN teds_sales_plan_activity_line spal ON spal.id = dso.activity_plan_id 
            LEFT JOIN stock_location loc_tk ON loc_tk.id = spal.location_id
            LEFT JOIN titik_keramaian tk ON tk.id = dso.titik_keramaian_id
            LEFT JOIN stock_location src_pos ON src_pos.id = spal.source_pos_location_id
            %s %s
            ORDER BY b.code, dso.date_order
            """ % (query_where, query_where_sales)
        
        
        if state in ('all', 'cancelled', 'progress_done_cancelled') :
            query_cancel = """
                SELECT
                COALESCE(b.code,'') as branch_code, 
                COALESCE(b.name,'') as branch_name, 
                COALESCE(md.default_code,'') as md_code, 
                COALESCE(dso.name,'') as name, 
                CASE WHEN dso.state = 'progress' THEN 'Sales Order' 
                    WHEN dso.state = 'done' THEN 'Done' 
                    WHEN dso.state = 'cancelled' THEN 'Cancelled'
                    WHEN dso.state IS NULL THEN '' 
                    ELSE dso.state 
                END as state, 
                dso.date_order as date_order, 
                COALESCE(finco.default_code,'Cash') as finco_code, 
                CASE WHEN dso.is_cod = TRUE THEN 'COD' 
                    ELSE 'Reguler' 
                END as is_cod, 
                COALESCE(sales_koor.name,'') as sales_koor_name, 
                COALESCE(hr_sales.nip,'') as sales_nip, 
                COALESCE(sales.name,'') as sales_name, 
                COALESCE(job.name,'') as job_name, 
                COALESCE(cust.default_code,'') as cust_code, 
                COALESCE(cust.name,'') as cust_name,
                COALESCE(product.name_template,'') as product_name, COALESCE(pav.code,'') as pav_code, COALESCE(dsol.product_qty,0) as product_qty, 
                COALESCE(lot.name,'') as lot_name, COALESCE(lot.chassis_no,'') as lot_chassis, 
                COALESCE(dsol.price_unit,0) as price_unit, 
                COALESCE(dsol.discount_po,0) as discount_po, COALESCE(dsol_disc.ps_dealer,0) as ps_dealer, COALESCE(dsol_disc.ps_ahm,0) as ps_ahm, COALESCE(dsol_disc.ps_md,0) as ps_md, COALESCE(dsol_disc.ps_finco,0) as ps_finco, 
                COALESCE(dsol_disc.ps_dealer,0)+COALESCE(dsol_disc.ps_ahm,0)+COALESCE(dsol_disc.ps_md,0)+COALESCE(dsol_disc.ps_finco,0) as ps_total, 
                COALESCE(dsol.price_unit/1.1,0) as sales, 
                COALESCE(dsol.discount_po/1.1,0) as disc_reg, COALESCE(dsol_disc.discount_pelanggan/1.1,0) as disc_quo, 
                COALESCE(dsol.discount_po/1.1,0)+COALESCE(dsol_disc.discount_pelanggan/1.1,0) as disc_total, 
                COALESCE(dsol.price_subtotal,0) as price_subtotal, round(COALESCE(dsol.price_subtotal,0)*0.1,2) as PPN, COALESCE(dsol.force_cogs,0) as force_cogs, 
                COALESCE(dso.customer_dp,0) as piutang_dp, COALESCE(dso.amount_total,0)-COALESCE(dso.customer_dp,0) as piutang, 
                COALESCE(dsol.price_subtotal,0)-COALESCE(dsol.force_cogs,0)+COALESCE(dsol_disc.ps_ahm,0)+COALESCE(dsol_disc.ps_md,0)+COALESCE(dsol_disc.ps_finco,0) as gp_unit, 
                COALESCE(dsol.price_bbn,0) as price_bbn, COALESCE(dsol.price_bbn_beli,0) as price_bbn_beli, COALESCE(dsol.price_bbn,0)-COALESCE(dsol.price_bbn_beli,0) as gp_bbn, 
                (COALESCE(dsol.price_subtotal,0)-COALESCE(dsol.force_cogs,0)+COALESCE(dsol_disc.ps_ahm,0)+COALESCE(dsol_disc.ps_md,0)+COALESCE(dsol_disc.ps_finco,0))+(COALESCE(dsol.price_bbn,0)-COALESCE(dsol.price_bbn_beli,0)) as gp_total, 
                COALESCE(dsol.amount_hutang_komisi,0) as amount_hutang_komisi, 
                COALESCE(dsol.insentif_finco/1.1,0) as insentif_finco, COALESCE(insentif_finco,0) as dpp_insentif_finco, 
                COALESCE(dsol.discount_po/1.1,0)+COALESCE(dsol_disc.ps_dealer/1.1,0)+COALESCE(amount_hutang_komisi,0) as beban_cabang, 
                COALESCE(prod_category.name,'') as categ_name, 
                COALESCE(prod_category2.name,'') as categ2_name, 
                COALESCE(prod_template.series,'') as prod_series, 
                COALESCE(fp.name,'') as faktur_pajak, 
                dso.date_order - lot.receive_date as aging_stock, 
                stnk.kecamatan as kecamatan,
                dsoc.name as dsoc_name, 
                dsoc.date as dsoc_date,
                regexp_replace(coalesce(dsoc.reason, ''), '[\n\r]+', ' ', 'g') as dsoc_reason,
                coalesce(dsoc.id,0) as dsoc_id,
                kec.code as kode_kecamatan,
                dso.sales_source,
                source_loc.name as source_sales_location,
                COALESCE(hr_sales_koor.nip,'') as sales_koor_nip,
                COALESCE(cust.mobile,'') as cust_mobile,
                dsol.finco_tenor as tenor,
                mr.name   
                , COALESCE(dsol_brg_bonus.total_brg_bonus,0) as price_total_brg_bonus,
                dsol.finco_no_po as no_po,
                loc_stock.name as location_line,
                dsol.price_bbn_notice,
                dsol.price_bbn_proses,
                dsol.price_bbn_jasa,
                dsol.price_bbn_jasa_area,
                dsol.price_bbn_fee_pusat,
				city.code as kode_city,
            	city.name as name_city,
                dso.jaringan_penjualan,
                sp.name sumber_penjualan,
                tk.name titik_keramaian,
                loc_tk.name,
                src_pos.name as source_pos_location,
                COALESCE(cust.no_ktp,'') as ktp_customer,
                COALESCE(stnk.no_ktp,'') as ktp_stnk
                FROM dealer_sales_order_cancel dsoc
                INNER JOIN dealer_sale_order dso on dsoc.dealer_sales_order_id = dso.id and dsoc.state = 'confirmed' %s
                INNER JOIN dealer_sale_order_line dsol on dsol.dealer_sale_order_line_id = dso.id 
                LEFT JOIN wtc_branch b ON dso.branch_id = b.id 
                LEFT JOIN res_partner md ON b.default_supplier_id = md.id 
                LEFT JOIN res_partner finco ON dso.finco_id = finco.id 
                --left join res_users users ON dso.user_id = users.id 
                LEFT JOIN resource_resource sales ON dso.user_id = sales.user_id 
                LEFT JOIN hr_employee hr_sales ON sales.id = hr_sales.resource_id 
                LEFT JOIN hr_job job ON hr_sales.job_id = job.id 
                --left join crm_case_section sales_team ON dso.section_id = sales_team.id 
                LEFT JOIN resource_resource sales_koor ON dso.sales_koordinator_id = sales_koor.user_id 
                LEFT JOIN hr_employee hr_sales_koor ON sales_koor.id = hr_sales_koor.resource_id
                LEFT JOIN res_partner cust ON dso.partner_id = cust.id 
                LEFT JOIN product_product product ON dsol.product_id = product.id 
                LEFT JOIN product_attribute_value_product_product_rel pavpp ON product.id = pavpp.prod_id 
                LEFT JOIN product_attribute_value pav ON pavpp.att_id = pav.id 
                LEFT JOIN product_template prod_template ON product.product_tmpl_id = prod_template.id 
                LEFT JOIN product_category prod_category ON prod_template.categ_id = prod_category.id 
                LEFT JOIN product_category prod_category2 ON prod_category.parent_id = prod_category2.id 
                LEFT JOIN stock_production_lot lot ON dsol.lot_id = lot.id 
                LEFT JOIN res_partner stnk ON lot.customer_stnk = stnk.id
                LEFT JOIN wtc_city city ON stnk.city_id = city.id
                LEFT JOIN wtc_kecamatan kec ON stnk.kecamatan_id = kec.id
                LEFT JOIN wtc_faktur_pajak_out fp ON dso.faktur_pajak_id = fp.id 
                LEFT JOIN stock_location source_loc ON source_loc.id = dso.sales_source_location
                LEFT JOIN ( 
                SELECT dealer_sale_order_line_discount_line_id, sum(ps_finco) as ps_finco, sum(ps_ahm) as ps_ahm, sum(ps_md) as ps_md, sum(ps_dealer) as ps_dealer, sum(ps_others) as ps_others, 
                sum(discount) as discount, sum(discount_pelanggan) as discount_pelanggan 
                FROM dealer_sale_order_line_discount_line 
                GROUP BY dealer_sale_order_line_discount_line_id 
                ) dsol_disc ON dsol_disc.dealer_sale_order_line_discount_line_id = dsol.id
                LEFT JOIN (
                SELECT head.branch_id,line.ring_id,line.kecamatan_id FROM ring_kecamatan_line line LEFT JOIN ring_kecamatan head on head.id=line.ring_kecamatan_id
                ) ring on ring.branch_id=b.id and ring.kecamatan_id=kec.id
                LEFT JOIN master_ring mr on ring.ring_id=mr.id
                
                LEFT JOIN (
                SELECT dealer_sale_order_line_brgbonus_line_id, sum(price_barang) as total_brg_bonus
                FROM dealer_sale_order_line_brgbonus_line 
                GROUP BY dealer_sale_order_line_brgbonus_line_id 
                ) dsol_brg_bonus ON dsol_brg_bonus.dealer_sale_order_line_brgbonus_line_id = dsol.id
            
                LEFT JOIN stock_location loc_stock ON loc_stock.id = dsol.location_id
                LEFT JOIN teds_act_type_sumber_penjualan sp ON sp.id = dso.sumber_penjualan_id
                LEFT JOIN teds_sales_plan_activity_line spal ON spal.id = dso.activity_plan_id 
                LEFT JOIN stock_location loc_tk ON loc_tk.id = spal.location_id
                LEFT JOIN titik_keramaian tk ON tk.id = dso.titik_keramaian_id
                LEFT JOIN stock_location src_pos ON src_pos.id = spal.source_pos_location_id
                %s
                ORDER BY b.code, dso.date_order            
            """ % (query_where_cancel, query_where)
           
        

        if state == 'cancelled' :
            query = query_cancel
        elif state in ('all','progress_done_cancelled') : 
            query = """
                SELECT * 
                FROM ((%s) UNION (%s)) a
                ORDER BY branch_code, date_order
                """ % (query_sales, query_cancel)
        else :
            query = query_sales
            
        
        cr.execute (query)
        ress = cr.fetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Penjualan')
        worksheet.set_column('B1:B1', 13)
        worksheet.set_column('C1:C1', 21)
        worksheet.set_column('D1:D1', 25)
        worksheet.set_column('E1:E1', 18)
        worksheet.set_column('F1:F1', 11)
        worksheet.set_column('G1:G1', 11)
        worksheet.set_column('H1:H1', 11)
        worksheet.set_column('I1:I1', 11)
        worksheet.set_column('J1:J1', 18)
        worksheet.set_column('K1:K1', 15)
        worksheet.set_column('L1:L1', 30)
        worksheet.set_column('M1:M1', 17)
        worksheet.set_column('N1:N1', 16)
        worksheet.set_column('O1:O1', 22)
        worksheet.set_column('P1:P1', 8)
        worksheet.set_column('Q1:Q1', 8)
        worksheet.set_column('R1:R1', 10)
        worksheet.set_column('S1:S1', 20)
        worksheet.set_column('T1:T1', 20)
        worksheet.set_column('U1:U1', 20)
        worksheet.set_column('V1:V1', 20)
        worksheet.set_column('W1:W1', 20)
        worksheet.set_column('X1:X1', 20)
        worksheet.set_column('Y1:Y1', 20)
        worksheet.set_column('Z1:Z1', 20)
        worksheet.set_column('AA1:AA1', 20)
        worksheet.set_column('AB1:AB1', 20)
        worksheet.set_column('AC1:AC1', 20)
        worksheet.set_column('AD1:AD1', 20)
        worksheet.set_column('AE1:AE1', 20)
        worksheet.set_column('AF1:AF1', 20)
        worksheet.set_column('AG1:AG1', 20)
        worksheet.set_column('AH1:AH1', 20)
        worksheet.set_column('AI1:AI1', 20)
        worksheet.set_column('AJ1:AJ1', 20)
        worksheet.set_column('AK1:AK1', 20)
        worksheet.set_column('AL1:AL1', 20)
        worksheet.set_column('AM1:AM1', 20)
        worksheet.set_column('AN1:AN1', 20)
        worksheet.set_column('AO1:AO1', 20)
        worksheet.set_column('AP1:AP1', 20)
        worksheet.set_column('AQ1:AQ1', 20)
        worksheet.set_column('AR1:AR1', 20)
        worksheet.set_column('AS1:AS1', 20)
        worksheet.set_column('AT1:AT1', 20)
        worksheet.set_column('AU1:AU1', 20)
        worksheet.set_column('AV1:AV1', 16)        
        worksheet.set_column('AW1:AW1', 17)        
        worksheet.set_column('AX1:AX1', 20)
        worksheet.set_column('AY1:AY1', 15)
        worksheet.set_column('AZ1:AZ1', 22)
        worksheet.set_column('BA1:BA1', 15)
        worksheet.set_column('BB1:BA1', 20)
        worksheet.set_column('BC1:BA1', 20)
        worksheet.set_column('BD1:BA1', 40)
        worksheet.set_column('BE1:BE1', 20)
        worksheet.set_column('BF1:BF1', 15)
        worksheet.set_column('BG1:BG1', 25)
        worksheet.set_column('BH1:BH1', 20)
        worksheet.set_column('BI1:BI1', 20)
        worksheet.set_column('BJ1:BJ1', 15)
        worksheet.set_column('BK1:BK1', 10)
        worksheet.set_column('BL1:BL1', 20)
        worksheet.set_column('BM1:BM1', 30)
        worksheet.set_column('BN1:BN1', 20)
        worksheet.set_column('BO1:BO1', 20)
        worksheet.set_column('BP1:BP1', 20)
        worksheet.set_column('BQ1:BQ1', 20)
        worksheet.set_column('BR1:BR1', 20)
        worksheet.set_column('BS1:BS1', 25)
        worksheet.set_column('BT1:BT1', 25)
        worksheet.set_column('BU1:BU1', 25)
        worksheet.set_column('BV1:BV1', 30)
        worksheet.set_column('BW1:BW1', 30)

                        
        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        filename = 'Report Penjualan '+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report Penjualan' , wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date),str(end_date)) , wbf['company'])
        row=4
        rowsaldo = row
        row+=1
        worksheet.write('A%s' % (row+1), 'No' , wbf['header'])
        worksheet.write('B%s' % (row+1), 'Branch Code' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'Branch Name' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'Main Dealer' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'SO Number' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'State' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'Date' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'Sales Type' , wbf['header'])
        worksheet.write('I%s' % (row+1), 'Payment Type' , wbf['header'])
        worksheet.write('J%s' % (row+1), 'Sales Coord Name' , wbf['header'])
        worksheet.write('K%s' % (row+1), 'Sales NIP' , wbf['header'])
        worksheet.write('L%s' % (row+1), 'Sales Name' , wbf['header'])
        worksheet.write('M%s' % (row+1), 'Job Name' , wbf['header'])
        worksheet.write('N%s' % (row+1), 'Customer Code' , wbf['header'])
        worksheet.write('O%s' % (row+1), 'Customer Name' , wbf['header'])
        worksheet.write('P%s' % (row+1), 'Type' , wbf['header'])                
        worksheet.write('Q%s' % (row+1), 'Color' , wbf['header'])
        worksheet.write('R%s' % (row+1), 'Qty' , wbf['header'])
        worksheet.write('S%s' % (row+1), 'Engine Number' , wbf['header'])
        worksheet.write('T%s' % (row+1), 'Chassis Number' , wbf['header'])
        worksheet.write('U%s' % (row), 'A' , wbf['content_center'])
        worksheet.write('U%s' % (row+1), 'Off The Road' , wbf['header'])
        worksheet.write('V%s' % (row), 'B' , wbf['content_center'])
        worksheet.write('V%s' % (row+1), 'Discount PO' , wbf['header'])
        worksheet.write('W%s' % (row), 'C' , wbf['content_center'])
        worksheet.write('W%s' % (row+1), 'PS Dealer' , wbf['header'])
        worksheet.write('X%s' % (row), 'D' , wbf['content_center'])
        worksheet.write('X%s' % (row+1), 'PS AHM' , wbf['header'])
        worksheet.write('Y%s' % (row), 'E' , wbf['content_center'])
        worksheet.write('Y%s' % (row+1), 'PS MD' , wbf['header'])
        worksheet.write('Z%s' % (row), 'F' , wbf['content_center'])
        worksheet.write('Z%s' % (row+1), 'PS Finco' , wbf['header'])
        worksheet.write('AA%s' % (row), 'G = C + D + E + F' , wbf['content_center'])
        worksheet.write('AA%s' % (row+1), 'PS Total' , wbf['header'])
        worksheet.write('AB%s' % (row), 'H = A / 1.1' , wbf['content_center'])
        worksheet.write('AB%s' % (row+1), 'Nett Sales' , wbf['header'])
        worksheet.write('AC%s' % (row), 'I = B / 1.1' , wbf['content_center'])
        worksheet.write('AC%s' % (row+1), 'Total Disc Reg (Nett)' , wbf['header'])
        worksheet.write('AD%s' % (row), 'J' , wbf['content_center'])
        worksheet.write('AD%s' % (row+1), 'Total Disc PS (Nett)' , wbf['header'])
        worksheet.write('AE%s' % (row), 'K = I + J' , wbf['content_center'])
        worksheet.write('AE%s' % (row+1), 'Total Disc' , wbf['header'])
        worksheet.write('AF%s' % (row), 'L = H - K' , wbf['content_center'])
        worksheet.write('AF%s' % (row+1), 'DPP' , wbf['header'])
        worksheet.write('AG%s' % (row), 'M = L / 1.1' , wbf['content_center'])
        worksheet.write('AG%s' % (row+1), 'PPN' , wbf['header'])
        worksheet.write('AH%s' % (row), 'N' , wbf['content_center'])
        worksheet.write('AH%s' % (row+1), 'HPP' , wbf['header'])
        worksheet.write('AI%s' % (row), 'O' , wbf['content_center'])
        worksheet.write('AI%s' % (row+1), 'Piutang DP' , wbf['header'])
        worksheet.write('AJ%s' % (row), 'P = L + M - O' , wbf['content_center'])
        worksheet.write('AJ%s' % (row+1), 'Piutang' , wbf['header'])
        worksheet.write('AK%s' % (row), 'Q = L - N' , wbf['content_center'])
        worksheet.write('AK%s' % (row+1), 'GP Unit' , wbf['header'])
        worksheet.write('AL%s' % (row), 'R' , wbf['content_center'])
        worksheet.write('AL%s' % (row+1), 'Sales BBN' , wbf['header'])
        worksheet.write('AM%s' % (row), 'S' , wbf['content_center'])
        worksheet.write('AM%s' % (row+1), 'HPP BBN' , wbf['header'])
        worksheet.write('AN%s' % (row), 'T = R - S' , wbf['content_center'])
        worksheet.write('AN%s' % (row+1), 'GP BBN' , wbf['header'])
        worksheet.write('AO%s' % (row), 'U = Q + T' , wbf['content_center'])
        worksheet.write('AO%s' % (row+1), 'Total GP' , wbf['header'])
        worksheet.write('AP%s' % (row), 'V' , wbf['content_center'])
        worksheet.write('AP%s' % (row+1), 'Hutang Komisi' , wbf['header']) 
        worksheet.write('AQ%s' % (row), 'W' , wbf['content_center'])               
        worksheet.write('AQ%s' % (row+1), 'DPP Insentif Finco' , wbf['header'])
        worksheet.write('AR%s' % (row), 'X' , wbf['content_center'])
        worksheet.write('AR%s' % (row+1), 'Beban Cabang' , wbf['header'])
        worksheet.write('AS%s' % (row+1), 'Total Barang Bonus' , wbf['header'])
        
        
        
        worksheet.write('AT%s' % (row+1), 'Category Name' , wbf['header'])
        worksheet.write('AU%s' % (row+1), 'Parent Category Name' , wbf['header'])
        worksheet.write('AV%s' % (row+1), 'Series' , wbf['header'])
        worksheet.write('AW%s' % (row+1), 'Faktur Pajak' , wbf['header'])
        worksheet.write('AX%s' % (row+1), 'Umur Stock' , wbf['header'])
        worksheet.write('AY%s' % (row+1), 'Kode Kabupaten' , wbf['header'])
        worksheet.write('AZ%s' % (row+1), 'Kabupaten' , wbf['header'])
        worksheet.write('BA%s' % (row+1), 'Kode Kecamatan' , wbf['header'])
        
        worksheet.write('BB%s' % (row+1), 'Kecamatan' , wbf['header'])
        # worksheet.write('BC%s' % (row+1), 'Sales Source' , wbf['header'])
        # worksheet.write('BD%s' % (row+1), 'Sales Source Location' , wbf['header'])
        worksheet.write('BC%s' % (row+1), 'Jaringan Penjualan', wbf['header'])
        worksheet.write('BD%s' % (row+1), 'Sumber Penjualan', wbf['header'])
        worksheet.write('BE%s' % (row+1), 'Titik Keramaian', wbf['header'])
        worksheet.write('BF%s' % (row+1), 'Source Location', wbf['header'])
        worksheet.write('BG%s' % (row+1), 'Source POS Location', wbf['header'])

        
        worksheet.write('BH%s' % (row+1), 'Nomor Batal' , wbf['header'])
        worksheet.write('BI%s' % (row+1), 'Tanggal Batal' , wbf['header'])
        worksheet.write('BJ%s' % (row+1), 'Alasan Batal' , wbf['header'])

        worksheet.write('BK%s' % (row+1), 'Sales Coord NIP', wbf['header'])
        worksheet.write('BL%s' % (row+1), 'Customer Mobile', wbf['header'])
        worksheet.write('BM%s' % (row+1), 'Tenor', wbf['header'])
        worksheet.write('BN%s' % (row+1), 'Ring', wbf['header'])
        worksheet.write('BO%s' % (row+1), 'No PO', wbf['header'])
        worksheet.write('BP%s' % (row+1), 'Stock Location', wbf['header'])
        worksheet.write('BQ%s' % (row+1), 'Price BBN Notice', wbf['header'])
        worksheet.write('BR%s' % (row+1), 'Price BBN Proses', wbf['header'])
        worksheet.write('BS%s' % (row+1), 'Price BBN Jasa', wbf['header'])
        worksheet.write('BT%s' % (row+1), 'Price BBN Jasa Area', wbf['header'])
        worksheet.write('BU%s' % (row+1), 'Price BBN Fee Pusat', wbf['header'])
        worksheet.write('BV%s' % (row+1), 'KTP Customer', wbf['header'])
        worksheet.write('BW%s' % (row+1), 'KTP Customer STNK', wbf['header'])
        # worksheet.write('BS%s' % (row+1), 'Jaringan Penjualan', wbf['header'])
        # worksheet.write('BT%s' % (row+1), 'Sumber Penjualan', wbf['header'])
        # worksheet.write('BU%s' % (row+1), 'Titik Keramaian', wbf['header'])
        # worksheet.write('BV%s' % (row+1), 'Source Location', wbf['header'])
        # worksheet.write('BW%s' % (row+1), 'Source POS Location', wbf['header'])

                       
        row+=2               
        no = 1     
        row1 = row
        
        total_qty = 0
        total_off_the_road = 0
        total_discount_po = 0
        total_ps_dealer = 0
        total_ps_ahm = 0
        total_ps_md = 0
        total_ps_finco = 0
        total_ps_total = 0
        total_nett_sales = 0
        total_total_disc_reg = 0
        total_total_disc_ps = 0
        total_total_disc = 0
        total_dpp = 0
        total_ppn = 0
        total_hpp = 0
        total_piutang_dp = 0
        total_piutang = 0
        total_gp_unit = 0
        total_sales_bbn = 0
        total_hpp_bbn = 0
        total_gp_bbn = 0
        total_total_gp = 0
        total_hutang_komisi = 0
        total_dpp_insentif_finco = 0
        total_beban_cabang = 0
        total_barang_bonus = 0
        
        for res in ress:
            
            branch_code =  str(res[0].encode('ascii','ignore').decode('ascii')) if res[0] != None else ''
            branch_name =  str(res[1].encode('ascii','ignore').decode('ascii')) if res[1] != None else ''
            md_code =  str(res[2].encode('ascii','ignore').decode('ascii')) if res[2] != None else ''
            name =  str(res[3].encode('ascii','ignore').decode('ascii')) if res[3] != None else ''
            state =  str(res[4].encode('ascii','ignore').decode('ascii')) if res[4] != None else ''
            date_order =  datetime.strptime(res[5], "%Y-%m-%d").date() if res[5] else ''
            finco_code =  str(res[6].encode('ascii','ignore').decode('ascii')) if res[6] != None else ''
            is_cod =  str(res[7].encode('ascii','ignore').decode('ascii')) if res[7] != None else ''
            sales_koor_name =  str(res[8].encode('ascii','ignore').decode('ascii')) if res[8] != None else ''
            sales_nip =  str(res[9].encode('ascii','ignore').decode('ascii')) if res[9] != None else ''
            sales_name =  str(res[10].encode('ascii','ignore').decode('ascii')) if res[10] != None else ''
            job_name =  str(res[11].encode('ascii','ignore').decode('ascii')) if res[11] != None else ''
            cust_code =  str(res[12].encode('ascii','ignore').decode('ascii')) if res[12] != None else ''
            cust_name =  str(res[13].encode('ascii','ignore').decode('ascii')) if res[13] != None else ''
            product_name =  str(res[14].encode('ascii','ignore').decode('ascii')) if res[14] != None else ''
            pav_code =  str(res[15].encode('ascii','ignore').decode('ascii')) if res[15] != None else ''
            product_qty =  res[16]
            lot_name =  str(res[17].encode('ascii','ignore').decode('ascii')) if res[17] != None else ''
            lot_chassis =  str(res[18].encode('ascii','ignore').decode('ascii')) if res[18] != None else ''
            price_unit =  res[19]
            discount_po =  res[20]
            ps_dealer =  res[21]
            ps_ahm =  res[22]
            ps_md =  res[23]
            ps_finco =  res[24]
            ps_total =  res[25]
            sales =  res[26] if res[26] != 0 else 0
            disc_reg =  res[27] if res[27] != 0 else 0
            disc_quo =  res[28] if res[28] != 0 else 0
            disc_total =  res[29] if res[29] != 0 else 0
            price_subtotal =  res[30]
            PPN =  res[31] if res[31] != None else 0
            force_cogs =  res[32]
            piutang_dp =  res[33]
            piutang =  res[34]
            gp_unit =  res[35]
            price_bbn =  res[36]
            price_bbn_beli =  res[37]        
            gp_bbn =  res[38]    
            gp_total =  res[39]                        
            amount_hutang_komisi =  res[40]
            insentif_finco = res[41]
            dpp_insentif_finco =  res[42] if res[42] != 0 else 0
            beban_cabang =  res[43]
            categ_name =  res[44]
            categ2_name =  res[45] 
            prod_series =  str(res[46].encode('ascii','ignore').decode('ascii')) if res[46] != None else ''
            faktur_pajak =  str(res[47].encode('ascii','ignore').decode('ascii')) if res[47] != None else ''
            umur_stock = res[48]
            kecamatan = str(res[49].encode('ascii','ignore').decode('ascii')) if res[49] != None else ''
            dsoc_name = str(res[50].encode('ascii','ignore').decode('ascii')) if res[50] != None else ''
            dsoc_date = datetime.strptime(res[51], "%Y-%m-%d").date() if res[51] else ''
            dsoc_reason = str(res[52].encode('ascii','ignore').decode('ascii')) if res[52] != None else ''
            dsoc_id = res[53]
            kode_kecamatan = str(res[54].encode('ascii','ignore').decode('ascii')) if res[54] != None else ''
            sales_source = str(res[55].encode('ascii','ignore').decode('ascii')) if res[55] != None else ''
            sales_source_location = str(res[56].encode('ascii','ignore').decode('ascii')) if res[56] != None else ''
            sales_koor_nip =  str(res[57].encode('ascii','ignore').decode('ascii')) if res[57] != None else ''
            cust_mobile =  str(res[58].encode('ascii','ignore').decode('ascii')) if res[58] != None else ''
            tenor =  str(res[59])+ ' Bulan' if res[59] != None else '0 Bulan'
            ring =  str(res[60].encode('ascii','ignore').decode('ascii')) if res[60] != None else ''
            amount_barang_bonus = res[61] if res[61] != 0 else 0
            no_po = res[62]
            location_line = res[63]
            price_bbn_notice = res[64]
            price_bbn_proses = res[65]
            price_bbn_jasa = res[66]
            price_bbn_jasa_area = res[67]
            price_bbn_fee_pusat = res[68]
            city_code = res[69]
            city = res[70]
            jaringan_penjualan = res[71]
            sumber_penjualan = res[72]
            titik_keramaian = res[73]
            location_tk = res[74]
            source_pos_location = res[75]
            ktp_customer = res[76]
            ktp_stnk = res[77]

            if dsoc_id > 0 :
                product_qty = -product_qty
                price_unit = -price_unit
                discount_po = -discount_po
                ps_dealer =  -ps_dealer
                ps_ahm = -ps_ahm
                ps_md = -ps_md
                ps_finco = -ps_finco
                ps_total = -ps_total
                sales = -sales
                disc_reg = -disc_reg
                disc_quo = -disc_quo
                disc_total = -disc_total
                price_subtotal = -price_subtotal
                PPN = -PPN
                force_cogs = -force_cogs
                piutang_dp = -piutang_dp
                piutang = -piutang
                gp_unit = -gp_unit
                price_bbn = -price_bbn
                price_bbn_beli = -price_bbn_beli
                gp_bbn = -gp_bbn
                gp_total = -gp_total
                amount_hutang_komisi = -amount_hutang_komisi
                insentif_finco = -insentif_finco
                dpp_insentif_finco = -dpp_insentif_finco
                beban_cabang = -beban_cabang

            if context.get('column_filter') :
                disc_reg = 0
                disc_quo = 0
                disc_total = 0
                price_subtotal = 0
                PPN = 0
                force_cogs = 0
                gp_unit = 0
                price_bbn_beli = 0
                gp_bbn = 0
                gp_total = 0
                dpp_insentif_finco = 0
                beban_cabang = 0
            
            worksheet.write('A%s' % row, no , wbf['content_number'])                    
            worksheet.write('B%s' % row, branch_code , wbf['content'])
            worksheet.write('C%s' % row, branch_name , wbf['content'])
            worksheet.write('D%s' % row, md_code , wbf['content'])
            worksheet.write('E%s' % row, name , wbf['content'])
            worksheet.write('F%s' % row, state , wbf['content'])
            worksheet.write('G%s' % row, date_order , wbf['content_date'])
            worksheet.write('H%s' % row, finco_code , wbf['content']) 
            worksheet.write('I%s' % row, is_cod , wbf['content'])  
            worksheet.write('J%s' % row, sales_koor_name , wbf['content'])
            worksheet.write('K%s' % row, sales_nip , wbf['content'])
            worksheet.write('L%s' % row, sales_name , wbf['content'])
            worksheet.write('M%s' % row, job_name , wbf['content'])
            worksheet.write('N%s' % row, cust_code , wbf['content'])
            worksheet.write('O%s' % row, cust_name , wbf['content'])
            worksheet.write('P%s' % row, product_name , wbf['content'])
            worksheet.write('Q%s' % row, pav_code , wbf['content'])
            worksheet.write('R%s' % row, product_qty , wbf['content_number']) 
            worksheet.write('S%s' % row, lot_name , wbf['content'])
            worksheet.write('T%s' % row, lot_chassis , wbf['content'])
            worksheet.write('U%s' % row, price_unit , wbf['content_float'])
            worksheet.write('V%s' % row, discount_po , wbf['content_float'])
            worksheet.write('W%s' % row, ps_dealer , wbf['content_float'])
            worksheet.write('X%s' % row, ps_ahm , wbf['content_float'])     
            worksheet.write('Y%s' % row, ps_md , wbf['content_float'])
            worksheet.write('Z%s' % row, ps_finco , wbf['content_float'])
            worksheet.write('AA%s' % row, ps_total , wbf['content_float'])
            worksheet.write('AB%s' % row, sales , wbf['content_float'])
            worksheet.write('AC%s' % row, disc_reg , wbf['content_float'])
            worksheet.write('AD%s' % row, disc_quo , wbf['content_float'])
            worksheet.write('AE%s' % row, disc_total , wbf['content_float'])
            worksheet.write('AF%s' % row, price_subtotal , wbf['content_float'])
            worksheet.write('AG%s' % row, PPN , wbf['content_float'])
            worksheet.write('AH%s' % row, force_cogs , wbf['content_float'])
            worksheet.write('AI%s' % row, piutang_dp , wbf['content_float'])  
            worksheet.write('AJ%s' % row, piutang , wbf['content_float'])
            worksheet.write('AK%s' % row, gp_unit , wbf['content_float'])
            worksheet.write('AL%s' % row, price_bbn , wbf['content_float'])
            worksheet.write('AM%s' % row, price_bbn_beli , wbf['content_float'])
            worksheet.write('AN%s' % row, gp_bbn , wbf['content_float'])
            worksheet.write('AO%s' % row, gp_total , wbf['content_float'])
            worksheet.write('AP%s' % row, amount_hutang_komisi , wbf['content_float'])
            worksheet.write('AQ%s' % row, dpp_insentif_finco , wbf['content_float'])
            worksheet.write('AR%s' % row, beban_cabang , wbf['content_float']) 
            
            worksheet.write('AS%s' % row, amount_barang_bonus , wbf['content_float']) 
             
            worksheet.write('AT%s' % row, categ_name , wbf['content'])
            worksheet.write('AU%s' % row, categ2_name , wbf['content'])
            worksheet.write('AV%s' % row, prod_series , wbf['content'])
            worksheet.write('AW%s' % row, faktur_pajak , wbf['content'])
            worksheet.write('AX%s' % row, umur_stock , wbf['content'])
            worksheet.write('AY%s' % row, city_code , wbf['content'])
            
            worksheet.write('AZ%s' % row, city , wbf['content'])
            worksheet.write('BA%s' % row, kode_kecamatan , wbf['content'])
        
            worksheet.write('BB%s' % row, kecamatan , wbf['content'])
            # worksheet.write('BC%s' % row, sales_source , wbf['content'])
            # worksheet.write('BD%s' % row, sales_source_location , wbf['content'])
            worksheet.write('BC%s' % row, jaringan_penjualan, wbf['content'])
            worksheet.write('BD%s' % row, sumber_penjualan, wbf['content'])
            worksheet.write('BE%s' % row, titik_keramaian, wbf['content'])
            worksheet.write('BF%s' % row, location_tk, wbf['content'])
            worksheet.write('BG%s' % row, source_pos_location if source_pos_location else sales_source_location, wbf['content'])


            worksheet.write('BH%s' % row, dsoc_name , wbf['content'])
            worksheet.write('BI%s' % row, dsoc_date , wbf['content_date'])
            worksheet.write('BJ%s' % row, dsoc_reason , wbf['content'])

            worksheet.write('BK%s' % row, sales_koor_nip, wbf['content'])
            worksheet.write('BL%s' % row, cust_mobile, wbf['content'])
            worksheet.write('BM%s' % row, tenor, wbf['content'])
            worksheet.write('BN%s' % row, ring, wbf['content'])
            worksheet.write('BO%s' % row, no_po, wbf['content'])
            worksheet.write('BP%s' % row, location_line, wbf['content'])
            worksheet.write('BQ%s' % row, price_bbn_notice, wbf['content'])
            worksheet.write('BR%s' % row, price_bbn_proses, wbf['content'])
            worksheet.write('BS%s' % row, price_bbn_jasa, wbf['content'])
            worksheet.write('BT%s' % row, price_bbn_jasa_area, wbf['content'])
            worksheet.write('BU%s' % row, price_bbn_fee_pusat, wbf['content'])
            worksheet.write('BV%s' % row, ktp_customer, wbf['content'])
            worksheet.write('BW%s' % row, ktp_stnk, wbf['content'])
            # worksheet.write('BS%s' % row, jaringan_penjualan, wbf['content'])
            # worksheet.write('BT%s' % row, sumber_penjualan, wbf['content'])
            # worksheet.write('BU%s' % row, titik_keramaian, wbf['content'])
            # worksheet.write('BV%s' % row, location_tk, wbf['content'])
            # worksheet.write('BW%s' % row, source_pos_location, wbf['content'])


            no+=1
            row+=1
            
            total_qty += product_qty
            total_off_the_road += price_unit
            total_discount_po += discount_po
            total_ps_dealer += ps_dealer
            total_ps_ahm += ps_ahm
            total_ps_md += ps_md
            total_ps_finco += ps_md
            total_ps_total += ps_total
            total_nett_sales += sales
            total_total_disc_reg += disc_reg
            total_total_disc_ps +=disc_quo
            total_total_disc += disc_total
            total_dpp += price_subtotal
            total_ppn += PPN
            total_hpp += force_cogs
            total_piutang_dp += piutang_dp
            total_piutang += piutang
            total_gp_unit += gp_unit
            total_sales_bbn += price_bbn
            total_hpp_bbn += price_bbn_beli
            total_gp_bbn += gp_bbn
            total_total_gp += gp_total
            total_hutang_komisi += amount_hutang_komisi
            total_dpp_insentif_finco += dpp_insentif_finco
            total_beban_cabang += beban_cabang
            total_barang_bonus += amount_barang_bonus
        
        worksheet.autofilter('A6:BW%s' % (row))  
        worksheet.freeze_panes(6, 3)
        
        #TOTAL
        worksheet.merge_range('A%s:C%s' % (row,row), 'Total', wbf['total'])    
        worksheet.merge_range('D%s:Q%s' % (row,row), '', wbf['total'])
        worksheet.merge_range('S%s:T%s' % (row,row), '', wbf['total']) 
        worksheet.merge_range('AT%s:BW%s' % (row,row), '', wbf['total']) 
        
        formula_total_qty =  '{=subtotal(9,R%s:R%s)}' % (row1, row-1)                      
        formula_total_off_the_road =  '{=subtotal(9,U%s:U%s)}' % (row1, row-1)
        formula_total_discount_po =  '{=subtotal(9,V%s:V%s)}' % (row1, row-1)
        formula_total_ps_dealer =   '{=subtotal(9,W%s:W%s)}' % (row1, row-1)
        formula_total_ps_ahm = '{=subtotal(9,X%s:X%s)}' % (row1, row-1)
        formula_total_ps_md =   '{=subtotal(9,Y%s:Y%s)}' % (row1, row-1)
        formula_total_ps_finco = '{=subtotal(9,Z%s:Z%s)}' % (row1, row-1)
        formula_total_ps_total =  '{=subtotal(9,AA%s:AA%s)}' % (row1, row-1)
        formula_total_nett_sales =  '{=subtotal(9,AB%s:AB%s)}' % (row1, row-1)
        formula_total_total_disc_reg =  '{=subtotal(9,AC%s:AC%s)}' % (row1, row-1)
        formula_total_total_disc_ps =  '{=subtotal(9,AD%s:AD%s)}' % (row1, row-1)
        formula_total_total_disc =  '{=subtotal(9,AE%s:AE%s)}' % (row1, row-1)
        formula_total_dpp =  '{=subtotal(9,AF%s:AF%s)}' % (row1, row-1) 
        formula_total_ppn =  '{=subtotal(9,AG%s:AG%s)}' % (row1, row-1)
        formula_total_hpp =  '{=subtotal(9,AH%s:AH%s)}' % (row1, row-1)
        formula_total_piutang_dp =   '{=subtotal(9,AI%s:AI%s)}' % (row1, row-1)
        formula_total_piutang = '{=subtotal(9,AJ%s:AJ%s)}' % (row1, row-1)
        formula_total_gp_unit =   '{=subtotal(9,AK%s:AK%s)}' % (row1, row-1)
        formula_total_sales_bbn = '{=subtotal(9,AL%s:AL%s)}' % (row1, row-1)
        formula_total_hpp_bbn =  '{=subtotal(9,AM%s:AM%s)}' % (row1, row-1)
        formula_total_gp_bbn =  '{=subtotal(9,AN%s:AN%s)}' % (row1, row-1)
        formula_total_total_gp =  '{=subtotal(9,AO%s:AO%s)}' % (row1, row-1)
        formula_total_hutang_komisi =  '{=subtotal(9,AP%s:AP%s)}' % (row1, row-1)
        formula_total_dpp_insentif_finco =  '{=subtotal(9,AQ%s:AQ%s)}' % (row1, row-1)
        formula_total_beban_cabang =  '{=subtotal(9,AR%s:AR%s)}' % (row1, row-1)    
        formula_total_barang_bonus =  '{=subtotal(9,AS%s:AS%s)}' % (row1, row-1)    

        worksheet.write_formula(row-1,17,formula_total_qty, wbf['total_number'], total_qty)                  
        worksheet.write_formula(row-1,20,formula_total_off_the_road, wbf['total_float'], total_off_the_road)
        worksheet.write_formula(row-1,21,formula_total_discount_po, wbf['total_float'], total_discount_po)
        worksheet.write_formula(row-1,22,formula_total_ps_dealer, wbf['total_float'], total_ps_dealer)
        worksheet.write_formula(row-1,23,formula_total_ps_ahm, wbf['total_float'], total_ps_ahm) 
        worksheet.write_formula(row-1,24,formula_total_ps_md, wbf['total_float'], total_ps_md)
        worksheet.write_formula(row-1,25,formula_total_ps_finco, wbf['total_float'], total_ps_finco)
        worksheet.write_formula(row-1,26,formula_total_ps_total, wbf['total_float'], total_ps_total)
        worksheet.write_formula(row-1,27,formula_total_nett_sales, wbf['total_float'], total_nett_sales)
        worksheet.write_formula(row-1,28,formula_total_total_disc_reg, wbf['total_float'], total_total_disc_reg)
        worksheet.write_formula(row-1,29,formula_total_total_disc_ps, wbf['total_float'], total_total_disc_ps)
        worksheet.write_formula(row-1,30,formula_total_total_disc, wbf['total_float'], total_total_disc)
        worksheet.write_formula(row-1,31,formula_total_dpp, wbf['total_float'], total_dpp)
        worksheet.write_formula(row-1,32,formula_total_ppn, wbf['total_float'], total_ppn)
        worksheet.write_formula(row-1,33,formula_total_hpp, wbf['total_float'], total_hpp)
        worksheet.write_formula(row-1,34,formula_total_piutang_dp, wbf['total_float'], total_piutang_dp)
        worksheet.write_formula(row-1,35,formula_total_piutang, wbf['total_float'], total_piutang) 
        worksheet.write_formula(row-1,36,formula_total_gp_unit, wbf['total_float'], total_gp_unit)
        worksheet.write_formula(row-1,37,formula_total_sales_bbn, wbf['total_float'], total_sales_bbn)
        worksheet.write_formula(row-1,38,formula_total_hpp_bbn, wbf['total_float'], total_hpp_bbn)
        worksheet.write_formula(row-1,39,formula_total_gp_bbn, wbf['total_float'], total_gp_bbn)
        worksheet.write_formula(row-1,40,formula_total_total_gp, wbf['total_float'], total_total_gp)
        worksheet.write_formula(row-1,41,formula_total_hutang_komisi, wbf['total_float'], total_hutang_komisi)
        worksheet.write_formula(row-1,42,formula_total_dpp_insentif_finco, wbf['total_float'], total_dpp_insentif_finco)
        worksheet.write_formula(row-1,43,formula_total_beban_cabang, wbf['total_float'], total_beban_cabang)
        worksheet.write_formula(row-1,44,formula_total_barang_bonus, wbf['total_float'], total_barang_bonus)
                                                                
        worksheet.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])  
                   
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        
        return fp

wtc_report_penjualan()
