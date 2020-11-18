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

class wtc_report_workshop(osv.osv_memory):
    _name = "wtc.report.workshop.wizard"
    _description = "Workshop Report"

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
    
    def _get_categ_ids(self, cr, uid, division, context=None):
        obj_categ = self.pool.get('product.category')
        all_categ_ids = obj_categ.search(cr, uid, [])
        categ_ids = obj_categ.get_child_ids(cr, uid, all_categ_ids, division)
        return categ_ids
        
    _columns = {
        'state_x': fields.selection( ( ('choose','choose'),('get','get'))), #xls
        'data_x': fields.binary('File', readonly=True),
        'name': fields.char('Filename', 100, readonly=True), 
        'options': fields.selection([('detail','Detail'),('unit_entry','Unit Entry'),('unit_entry_by_reason','Unit Entry By Reason')], 'Options', required=True, change_default=True, select=True),
        'wo_categ': fields.selection([('Sparepart','Sparepart'),('Service','Service')], 'Workshop Category'),
        'product_ids': fields.many2many('product.product', 'wtc_report_workshop_product_rel', 'wtc_report_workshop_wizard_id',
            'product_id', 'Products'),
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'state': fields.selection([('all', 'All'), ('open','Outstanding'), ('done','Paid'), ('open_done','Outstanding & Paid'), ('open_done_cancel', 'Outstanding, Paid & Cancelled'), ('cancel', 'Cancel'), ('unused', 'Unused')], 'Customer AR State', required=True, change_default=True, select=True),
        'branch_ids': fields.many2many('wtc.branch', 'wtc_report_workshop_branch_rel', 'wtc_report_workshop_wizard_id',
            'branch_id', 'Branches', copy=False),
        'partner_ids': fields.many2many('res.partner', 'wtc_report_workshop_partner_rel', 'wtc_report_workshop_wizard_id',
            'partner_id', 'Customers', copy=False, domain=[('customer','=',True)]),       
    }

    _defaults = {
        'state_x': lambda *a: 'choose',
        'options': 'detail',
        'state': 'open_done_cancel',
    }
    
    def wo_categ_change(self, cr, uid, ids, wo_categ, context=None):
        value = {}
        domain = {}
        value['product_ids'] = False
        obj_categ = self.pool.get('product.category')
        all_categ = obj_categ.search(cr,uid,[])
        categ_ids = obj_categ.get_child_ids(cr, uid, all_categ, wo_categ)
        domain['product_ids'] = [('categ_id','in',categ_ids)]
        return {'value':value, 'domain':domain}
    
    
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
        
        self.wbf['content_datetime_12_hr'] = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm AM/PM'})
        self.wbf['content_datetime_12_hr'].set_left()
        self.wbf['content_datetime_12_hr'].set_right()        
                
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
            
        if data['options'] == 'detail' : 
            return self._print_excel_report(cr, uid, ids, data, context=context)
        elif data['options'] == 'unit_entry':
            return self._print_excel_report_unit_entry(cr, uid, ids, data, context=context)
        else:
            return self._print_excel_report_unit_entry_by_reason(cr, uid, ids, data, context=context)

        # return self._print_excel_report_prestasi_mekanik(cr, uid, ids, data, context=context)


    def _print_excel_report(self, cr, uid, ids, data, context=None):        
        
        wo_categ = data['wo_categ']
        product_ids = data['product_ids']
        start_date = data['start_date']
        end_date = data['end_date']
        state = data['state']
        branch_ids = data['branch_ids']
        partner_ids = data['partner_ids']    
              
        tz = '7 hours'
        
        # query_where = " WHERE 1=1 "
        # query_where_wo=""
        # query_where_cancel=""
        # if product_ids :
        #     query_where += " AND wol.product_id in %s" % str(tuple(product_ids)).replace(',)', ')')
        # if wo_categ :
        #     query_where += " AND wol.categ_id = '%s'" % str(wo_categ)
        # if start_date :
        #     query_where_wo += " AND wo.date >= '%s'" % str(start_date)
        #     query_where_cancel += " AND woc.date >= '%s'" % str(start_date)
        # if end_date :
        #     end_date = end_date + ' 23:59:59'
        #     query_where_wo += " AND wo.date <= '%s'" % (end_date)
        #     query_where_cancel += " AND woc.date <= '%s'" % str(end_date)
        # if state in ['open','done','cancel','unused'] :
        #     query_where += " AND wo.state = '%s'" % str(state)
        # elif state == 'open_done' :
        #     query_where += " AND wo.state IN ('open','done')"
        # elif state == 'open_done_cancel' :
        #     query_where += " AND wo.state in ('open','done','cancel')"
        # if branch_ids :
        #     query_where += " AND wo.branch_id in %s" % str(tuple(branch_ids)).replace(',)', ')')
        # if partner_ids :
        #     query_where += " AND wo.customer_id in %s" % str(tuple(partner_ids)).replace(',)', ')')
              
        # query_order = "order by b.code, wo.date"

        query_where_wo = " WHERE 1=1"
        query_where_cancel = " WHERE woc.state = 'confirmed' "
        query_where_union = " WHERE 1=1"
        if product_ids:
            query_where_wo += " AND wol.product_id IN %s" % str(tuple(product_ids)).replace(',)', ')')
        if wo_categ:
            query_where_wo += " AND wol.categ_id = '%s'" % str(wo_categ)
        if start_date:
            query_where_wo += " AND wo.date_confirm  >= '%s'" % str(start_date)
            query_where_cancel += " AND woc.date >= '%s'" % str(start_date)
        if end_date:
            query_where_wo += " AND wo.date_confirm  <= '%s'" % str(end_date)
            query_where_cancel += " AND woc.date <= '%s'" % str(end_date)
        if state in ['open','done','cancel','unused']:
            query_where_wo += " AND wo.state = '%s'" % str(state)
        if state == 'open_done':
            query_where_wo += " AND wo.state IN ('open','done')"
        if state == 'open_done_cancel':
            query_where_wo += " AND wo.state IN ('open','done','cancel')"
        if branch_ids:
            query_where_wo += " AND wo.branch_id IN %s" % str(tuple(branch_ids)).replace(',)', ')')
            query_where_union += " AND branch_id IN %s" % str(tuple(branch_ids)).replace(',)', ')')
            query_where_cancel += " AND woc.branch_id IN %s" % str(tuple(branch_ids)).replace(',)', ')')
        if partner_ids :
            query_where_wo += " AND wo.customer_id IN %s" % str(tuple(partner_ids)).replace(',)', ')')
            query_where_union += " AND customer_id IN %s" % str(tuple(partner_ids)).replace(',)', ')')
            query_where_cancel += " AND wo.customer_id IN %s" % str(tuple(partner_ids)).replace(',)', ')')
        
        query_wo = """
                        SELECT b.code AS branch_code
                            , b.id AS branch_id  
                            , b.name AS branch_name 
                            , wo.name AS wo_name  
                            , wo.state AS wo_state  
                            , wo.date_confirm  AS wo_date  
                            , wo.type AS wo_type  
                            , inv.default_code AS main_dealer 
                            , users.login AS login  
                            , mechanic.name AS mechanic 
                            , lot.no_polisi AS nopol  
                            , customer.default_code AS cust_code  
                            , customer.name AS cust_name
                            , customer.id AS customer_id  
                            , wo.mobile AS cust_mobile  
                            , unit.name_template AS unit_name 
                            , lot.name as engine  
                            , lot.chassis_no as chassis 
                            , wol.categ_id as wo_categ  
                            , prod_category.name as prod_categ_name 
                            , product.name_template as prod_name  
                            , product.default_code as prod_code 
                            , CASE WHEN wol.categ_id = 'Sparepart' THEN wol.supply_qty ELSE COALESCE(wol.product_qty,0) END as qty  
                            , COALESCE(wol.price_unit,0) as het 
                            , COALESCE(NULLIF(wol.discount,0),0) as discount  
                            , COALESCE(wol.price_unit,0) * (1 - COALESCE(NULLIF(wol.discount,0),0) / 100) * CASE WHEN wol.categ_id = 'Sparepart' THEN wol.supply_qty ELSE COALESCE(wol.product_qty,0) END as total_piutang  
                            , COALESCE(wol.price_unit,0) / 1.1 * CASE WHEN wol.categ_id = 'Sparepart' THEN wol.supply_qty ELSE COALESCE(wol.product_qty,0) END as gross_sales 
                            , COALESCE(wol.price_unit,0) * (COALESCE(NULLIF(wol.discount,0),0) / 100) / 1.1 * CASE WHEN wol.categ_id = 'Sparepart' THEN wol.supply_qty ELSE COALESCE(wol.product_qty,0) END as discount_amount  
                            , COALESCE(wol.price_unit,0) * (1 - COALESCE(NULLIF(wol.discount,0),0) / 100) / 1.1 * CASE WHEN wol.categ_id = 'Sparepart' THEN wol.supply_qty ELSE COALESCE(wol.product_qty,0) END as dpp  
                            , COALESCE(wol.price_unit,0) * (1 - COALESCE(NULLIF(wol.discount,0),0) / 100) / 1.1 * 0.1 * CASE WHEN wol.categ_id = 'Sparepart' THEN wol.supply_qty ELSE COALESCE(wol.product_qty,0) END as ppn  
                            , COALESCE(ail.force_cogs / COALESCE(NULLIF(ail.quantity,0),1) * wol.supply_qty,0) as hpp 
                            , COALESCE ( (wol.price_unit * (1 - COALESCE(NULLIF(wol.discount,0),0) / 100) / 1.1 * CASE WHEN wol.categ_id = 'Sparepart' THEN wol.supply_qty ELSE wol.product_qty END) - (ail.force_cogs / COALESCE(NULLIF(ail.quantity,0),1) * wol.supply_qty),0) as total_gp  
                            , COALESCE(fp.name,'') as faktur_pajak  
                            , customer.street as alamat_konsumen
                            , 0 as woc_id 
                            , '' as woc_name  
                            , NULL as woc_date  
                            , '' as woc_reason  
                            , kec.name as kecamatan
                            , pembawa.name pembawa
                            , wo.alasan_ke_ahass as alasan
                            , wo.dealer_sendiri as dealer_sendiri
                            , wo.tahun_perakitan as tahun_perakitan
                            , wo.create_date as create_date
                            , wo.km
                            , wo.nomor_sa
                        FROM wtc_work_order wo  
                        INNER JOIN account_invoice ai ON wo.id = ai.transaction_id AND ai.model_id IN (SELECT id FROM ir_model WHERE model = 'wtc.work.order') 
                        LEFT JOIN wtc_work_order_line wol ON wo.id = wol.work_order_id  
                        LEFT JOIN account_invoice_line ail ON ai.id = ail.invoice_id AND wol.product_id = ail.product_id  
                        LEFT JOIN res_partner inv ON ai.partner_id = inv.id   
                        LEFT JOIN wtc_branch b ON wo.branch_id = b.id 
                        LEFT JOIN res_users users ON wo.mekanik_id = users.id   
                        LEFT JOIN res_partner mechanic ON users.partner_id = mechanic.id  
                        LEFT JOIN res_partner customer ON wo.customer_id = customer.id  
                        LEFT JOIN wtc_faktur_pajak_out fp ON wo.faktur_pajak_id = fp.id   
                        LEFT JOIN stock_production_lot lot ON wo.lot_id = lot.id  
                        LEFT JOIN product_product unit ON wo.product_id = unit.id   
                        LEFT JOIN product_product product ON wol.product_id = product.id  
                        LEFT JOIN product_template prod_template ON product.product_tmpl_id = prod_template.id  
                        LEFT JOIN product_category prod_category ON prod_template.categ_id = prod_category.id   
                        LEFT JOIN wtc_kecamatan kec on customer.kecamatan_id=kec.id  
                        LEFT JOIN res_partner pembawa on wo.driver_id = pembawa.id
                        %s  
        """ % (query_where_wo)

        query_cancel = """
                            SELECT b.code AS branch_code
                                , b.id AS branch_id
                                , b.name AS branch_name
                                , wo.name AS wo_name
                                , wo.state AS wo_state
                                , wo.date_confirm AS wo_date
                                , wo.type AS wo_type
                                , inv.default_code AS main_dealer
                                , users.login AS login
                                , mechanic.name AS mechanic
                                , lot.no_polisi AS nopol
                                , customer.default_code AS cust_code
                                , customer.name AS cust_name
                                , customer.id AS customer_id
                                , wo.mobile AS cust_mobile
                                , unit.name_template AS unit_name
                                , lot.name as engine
                                , lot.chassis_no as chassis
                                , wol.categ_id as wo_categ
                                , prod_category.name as prod_categ_name
                                , product.name_template as prod_name
                                , product.default_code as prod_code
                                , -1 * CASE WHEN wol.categ_id = 'Sparepart' THEN wol.supply_qty ELSE COALESCE(wol.product_qty,0) END as qty
                                , -1 * COALESCE(wol.price_unit,0) as het
                                , -1 * COALESCE(NULLIF(wol.discount,0),0) as discount
                                , -1 * COALESCE(wol.price_unit,0) * (1 - COALESCE(NULLIF(wol.discount,0),0) / 100) * CASE WHEN wol.categ_id = 'Sparepart' THEN wol.supply_qty ELSE COALESCE(wol.product_qty,0) END as total_piutang
                                , -1 * COALESCE(wol.price_unit,0) / 1.1 * CASE WHEN wol.categ_id = 'Sparepart' THEN wol.supply_qty ELSE COALESCE(wol.product_qty,0) END as gross_sales
                                , -1 * COALESCE(wol.price_unit,0) * (COALESCE(NULLIF(wol.discount,0),0) / 100) / 1.1 * CASE WHEN wol.categ_id = 'Sparepart' THEN wol.supply_qty ELSE COALESCE(wol.product_qty,0) END as discount_amount
                                , -1 * COALESCE(wol.price_unit,0) * (1 - COALESCE(NULLIF(wol.discount,0),0) / 100) / 1.1 * CASE WHEN wol.categ_id = 'Sparepart' THEN wol.supply_qty ELSE COALESCE(wol.product_qty,0) END as dpp
                                , -1 * COALESCE(wol.price_unit,0) * (1 - COALESCE(NULLIF(wol.discount,0),0) / 100) / 1.1 * 0.1 * CASE WHEN wol.categ_id = 'Sparepart' THEN wol.supply_qty ELSE COALESCE(wol.product_qty,0) END as ppn
                                , -1 * COALESCE(ail.force_cogs / COALESCE(NULLIF(ail.quantity,0),1) * wol.supply_qty,0) as hpp
                                , -1 * COALESCE ( (wol.price_unit * (1 - COALESCE(NULLIF(wol.discount,0),0) / 100) / 1.1 * CASE WHEN wol.categ_id = 'Sparepart' THEN wol.supply_qty ELSE wol.product_qty END) - (ail.force_cogs / COALESCE(NULLIF(ail.quantity,0),1) * wol.supply_qty),0) as total_gp
                                , COALESCE(fp.name,'') as faktur_pajak
                                , customer.street
                                , woc.id as woc_id
                                , woc.name as woc_name
                                , woc.date as woc_date
                                , regexp_replace(COALESCE(woc.reason, ''), '[\n\r]+', ' ', 'g') as woc_reason
                                , kec.name as kecamatan
                                , pembawa.name pembawa
                                , wo.alasan_ke_ahass as alasan
                                , wo.dealer_sendiri as dealer_sendiri
                                , wo.tahun_perakitan as tahun_perakitan
                                , wo.create_date as create_date
                                , wo.km
                                , wo.nomor_sa
                            FROM work_order_cancel woc 
                            INNER JOIN wtc_work_order wo ON woc.work_order_id = wo.id 
                            INNER JOIN account_invoice ai ON wo.id = ai.transaction_id AND ai.model_id IN (SELECT id FROM ir_model WHERE model = 'wtc.work.order')
                            LEFT JOIN wtc_work_order_line wol ON wo.id = wol.work_order_id
                            LEFT JOIN account_invoice_line ail ON ai.id = ail.invoice_id AND wol.product_id = ail.product_id
                            LEFT JOIN res_partner inv ON ai.partner_id = inv.id 
                            LEFT JOIN wtc_branch b ON wo.branch_id = b.id
                            LEFT JOIN res_users users ON wo.mekanik_id = users.id 
                            LEFT JOIN res_partner mechanic ON users.partner_id = mechanic."id"
                            LEFT JOIN res_partner customer ON wo.customer_id = customer.id 
                            LEFT JOIN wtc_faktur_pajak_out fp ON wo.faktur_pajak_id = fp.id 
                            LEFT JOIN stock_production_lot lot ON wo.lot_id = lot.id 
                            LEFT JOIN product_product unit ON wo.product_id = unit.id 
                            LEFT JOIN product_product product ON wol.product_id = product.id 
                            LEFT JOIN product_template prod_template ON product.product_tmpl_id = prod_template.id 
                            LEFT JOIN product_category prod_category ON prod_template.categ_id = prod_category.id 
                            LEFT JOIN wtc_kecamatan kec on customer.kecamatan_id=kec.id  
                            LEFT JOIN res_partner pembawa on wo.driver_id = pembawa.id

                            %s
                    """ % (query_where_cancel)

        if state in ['all','open_done_cancel']:
            query = """
                        SELECT * 
                        FROM ((%s) UNION ALL (%s)) a %s
                        ORDER BY branch_code
                """ % (query_wo, query_cancel, query_where_union)
        elif state == 'cancel':
            query = query_cancel
        else:
            query = query_wo
        # print query
        
        cr.execute (query)
        ress = cr.dictfetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Workshop')
        worksheet.set_column('B1:B1', 17)
        worksheet.set_column('C1:C1', 20)
        worksheet.set_column('D1:D1', 25)
        worksheet.set_column('E1:E1', 18)
        worksheet.set_column('F1:F1', 20)
        worksheet.set_column('G1:G1', 11)
        worksheet.set_column('H1:H1', 30)
        worksheet.set_column('I1:I1', 12)
        worksheet.set_column('J1:J1', 26)
        worksheet.set_column('K1:K1', 15)
        worksheet.set_column('L1:L1', 20)
        worksheet.set_column('M1:M1', 27)
        worksheet.set_column('N1:N1', 20)
        worksheet.set_column('O1:O1', 20)
        worksheet.set_column('P1:P1', 20)
        worksheet.set_column('Q1:Q1', 20)
        worksheet.set_column('R1:R1', 20)
        worksheet.set_column('S1:S1', 20)
        worksheet.set_column('T1:T1', 22)
        worksheet.set_column('U1:U1', 29)
        worksheet.set_column('V1:V1', 14)
        worksheet.set_column('W1:W1', 18)
        worksheet.set_column('X1:X1', 18)
        worksheet.set_column('Y1:Y1', 18)
        worksheet.set_column('Z1:Z1', 18)
        worksheet.set_column('AA1:AA1', 17)
        worksheet.set_column('AB1:AB1', 18)
        worksheet.set_column('AC1:AC1', 18)
        worksheet.set_column('AD1:AD1', 17)
        worksheet.set_column('AE1:AE1', 20)
        worksheet.set_column('AF1:AF1', 43) 
        worksheet.set_column('AG1:AG1', 23) 
        worksheet.set_column('AH1:AH1', 24)
        worksheet.set_column('AI1:AI1', 24)
        worksheet.set_column('AJ1:AJ1', 24)
        worksheet.set_column('AK1:AK1', 23)
        worksheet.set_column('AL1:AL1', 23)
        worksheet.set_column('AM1:AM1', 23)
        worksheet.set_column('AN1:AN1', 23)
        worksheet.set_column('AO1:AO1', 23)
        worksheet.set_column('AP1:AP1', 17)
        worksheet.set_column('AQ1:AQ1', 23)

                        
        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        filename = 'Report Workshop '+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report Workshop' , wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])
        row=3
        rowsaldo = row
        row+=1
        worksheet.write('A%s' % (row+1), 'No' , wbf['header'])
        worksheet.write('B%s' % (row+1), 'Branch Code' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'Branch Name' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'Workshop Number' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'State' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'Date Confirm' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'Type' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'Main Dealer' , wbf['header'])
        worksheet.write('I%s' % (row+1), 'Login' , wbf['header'])
        worksheet.write('J%s' % (row+1), 'Mechanic' , wbf['header'])
        worksheet.write('K%s' % (row+1), 'No Polisi' , wbf['header'])
        worksheet.write('L%s' % (row+1), 'Customer Code' , wbf['header'])
        worksheet.write('M%s' % (row+1), 'Customer Name' , wbf['header'])
        worksheet.write('N%s' % (row+1), 'Customer Mobile' , wbf['header'])
        worksheet.write('O%s' % (row+1), 'Unit Name' , wbf['header'])
        worksheet.write('P%s' % (row+1), 'Engine Number' , wbf['header'])                
        worksheet.write('Q%s' % (row+1), 'Cassis Number' , wbf['header'])
        worksheet.write('R%s' % (row+1), 'Workshop Category' , wbf['header'])
        worksheet.write('S%s' % (row+1), 'Category Name' , wbf['header'])
        worksheet.write('T%s' % (row+1), 'Product Name' , wbf['header'])
        worksheet.write('U%s' % (row+1), 'Product Code' , wbf['header'])
        worksheet.write('V%s' % (row+1), 'Quantity' , wbf['header'])
        worksheet.write('W%s' % (row+1), 'HET' , wbf['header'])
        worksheet.write('X%s' % (row+1), 'Discount' , wbf['header'])
        worksheet.write('Y%s' % (row+1), 'Discount Amount' , wbf['header'])
        worksheet.write('Z%s' % (row+1), 'DPP' , wbf['header'])
        worksheet.write('AA%s' % (row+1), 'PPN' , wbf['header'])
        worksheet.write('AB%s' % (row+1), 'Hpp' , wbf['header'])
        worksheet.write('AC%s' % (row+1), 'GP Total' , wbf['header'])
        worksheet.write('AD%s' % (row+1), 'Total' , wbf['header'])
        worksheet.write('AE%s' % (row+1), 'Total (dengan diskon)' , wbf['header'])
        worksheet.write('AF%s' % (row+1), 'Faktur Pajak' , wbf['header'])
        worksheet.write('AG%s' % (row+1), 'Alamat Konsumen' , wbf['header'])
        worksheet.write('AH%s' % (row+1), 'Nomor Batal' , wbf['header'])
        worksheet.write('AI%s' % (row+1), 'Alasan Batal' , wbf['header'])
        worksheet.write('AJ%s' % (row+1), 'Kecamatan' , wbf['header'])
        worksheet.write('AK%s' % (row+1), 'Pembawa' , wbf['header'])
        worksheet.write('AL%s' % (row+1), 'Alasan Ke Ahass' , wbf['header'])
        worksheet.write('AM%s' % (row+1), 'Dealer Sendiri' , wbf['header'])
        worksheet.write('AN%s' % (row+1), 'Tahun Perakitan' , wbf['header'])
        worksheet.write('AO%s' % (row+1), 'Create Date' , wbf['header'])
        worksheet.write('AP%s' % (row+1), 'Km' , wbf['header'])
        worksheet.write('AQ%s' % (row+1), 'No Service Advisor' , wbf['header'])

                       
        row+=2               
        no = 1     
        row1 = row
        
        total_qty = 0
        total_het = 0
        total_discount = 0
        
        total_hpp = 0
        total_dpp = 0
        total_ppn = 0
        total_discount_amount = 0
        total_total_gp = 0
        total_total=0
        total_total_new = 0
        for res in ress:
            
            branch_code = str(res.get('branch_code').encode('ascii','ignore').decode('ascii')) if res.get('branch_code') != None else ''
            branch_name = str(res.get('branch_name').encode('ascii','ignore').decode('ascii')) if res.get('branch_name') != None else ''
            name = str(res.get('wo_name').encode('ascii','ignore').decode('ascii')) if res.get('wo_name') != None else ''
            state = str(res.get('wo_state').encode('ascii','ignore').decode('ascii')) if res.get('wo_state') != None else ''
            date_order = datetime.strptime(res.get('wo_date'), "%Y-%m-%d") if res.get('wo_date') else ''
            wo_type = str(res.get('wo_type').encode('ascii','ignore').decode('ascii')) if res.get('wo_type') != None else ''
            main_dealer = str(res.get('main_dealer').encode('ascii','ignore').decode('ascii')) if res.get('main_dealer') != None else ''
            login = str(res.get('login').encode('ascii','ignore').decode('ascii')) if res.get('login') != None else ''
            mechanic = str(res.get('mechanic').encode('ascii','ignore').decode('ascii')) if res.get('mechanic') != None else ''
            nopol =str(res.get('nopol').encode('ascii','ignore').decode('ascii')) if res.get('nopol') != None else ''
        
            cust_code = str(res.get('cust_code').encode('ascii','ignore').decode('ascii')) if res.get('cust_code') != None else ''
            cust_name =str(res.get('cust_name').encode('ascii','ignore').decode('ascii')) if res.get('cust_name') != None else ''
            cust_mobile = str(res.get('cust_mobile').encode('ascii','ignore').decode('ascii')) if res.get('cust_mobile') != None else ''
            unit_name = str(res.get('unit_name').encode('ascii','ignore').decode('ascii')) if res.get('unit_name') != None else ''
            engine = str(res.get('engine').encode('ascii','ignore').decode('ascii')) if res.get('engine') != None else ''
            chassis = str(res.get('chassis').encode('ascii','ignore').decode('ascii')) if res.get('chassis') != None else ''
            wo_categ = str(res.get('wo_categ').encode('ascii','ignore').decode('ascii')) if res.get('wo_categ') != None else ''
            prod_categ_name = str(res.get('prod_categ_name').encode('ascii','ignore').decode('ascii')) if res.get('prod_categ_name') != None else ''
            prod_name = str(res.get('prod_name').encode('ascii','ignore').decode('ascii')) if res.get('prod_name') != None else ''
            prod_code = str(res.get('prod_code').encode('ascii','ignore').decode('ascii')) if res.get('prod_code') != None else ''
            qty = res.get('qty')
            het = res.get('het')
            discount = res.get('discount')
            hpp = res.get('hpp')
            dpp = res.get('dpp')
            ppn = res.get('ppn')
            discount_amount = res.get('discount_amount')
            total_gp = res.get('total_gp')
            faktur_pajak = str(res.get('faktur_pajak').encode('ascii','ignore').decode('ascii')) if res.get('faktur_pajak') != None else ''
            alamat_konsumen = str(res.get('alamat_konsumen').encode('ascii','ignore').decode('ascii')) if res.get('alamat_konsumen') != None else ''
            dsoc_name = str(res.get('woc_name').encode('ascii','ignore').decode('ascii')) if res.get('woc_name') != None else ''
            dsoc_reason = str(res.get('woc_reason').encode('ascii','ignore').decode('ascii')) if res.get('woc_reason') != None else ''
            kec = res.get('kecamatan')
            pembawa = res.get('pembawa')
            alasan = res.get('alasan')
            dealer_sendiri = res.get('dealer_sendiri')
            tahun_perakitan = res.get('tahun_perakitan')
            create_date = res.get('create_date')
            km = res.get('km')
            nomor_sa = res.get('nomor_sa')
            
            total=(qty*het)-discount_amount
            total_new = dpp + ppn
            worksheet.write('A%s' % row, no , wbf['content_number'])                    
            worksheet.write('B%s' % row, branch_code , wbf['content'])
            worksheet.write('C%s' % row, branch_name , wbf['content'])
            worksheet.write('D%s' % row, name , wbf['content'])
            worksheet.write('E%s' % row, state , wbf['content'])
            worksheet.write('F%s' % row, date_order , wbf['content_datetime_12_hr'])
            worksheet.write('G%s' % row, wo_type , wbf['content'])
            worksheet.write('H%s' % row, main_dealer , wbf['content']) 
            worksheet.write('I%s' % row, login, wbf['content'])  
            worksheet.write('J%s' % row, mechanic , wbf['content'])
            worksheet.write('K%s' % row, nopol , wbf['content_number'])
            worksheet.write('L%s' % row, cust_code , wbf['content_float'])
            worksheet.write('M%s' % row, cust_name , wbf['content'])
            worksheet.write('N%s' % row, cust_mobile , wbf['content'])
            worksheet.write('O%s' % row, unit_name , wbf['content'])
            worksheet.write('P%s' % row, engine , wbf['content'])
            worksheet.write('Q%s' % row, chassis, wbf['content'])
            worksheet.write('R%s' % row, wo_categ , wbf['content']) 
            worksheet.write('S%s' % row, prod_categ_name , wbf['content'])
            worksheet.write('T%s' % row, prod_name , wbf['content'])
            worksheet.write('U%s' % row, prod_code , wbf['content'])
            worksheet.write('V%s' % row, qty , wbf['content_float'])
            worksheet.write('W%s' % row, het , wbf['content_float'])
            worksheet.write('X%s' % row, discount , wbf['content_float'])     
            worksheet.write('Y%s' % row, discount_amount , wbf['content_float'])
            worksheet.write('Z%s' % row, dpp , wbf['content_float'])
            worksheet.write('AA%s' % row, ppn , wbf['content_float'])
            worksheet.write('AB%s' % row, hpp , wbf['content_float'])
            worksheet.write('AC%s' % row, total_gp , wbf['content_float'])
            worksheet.write('AD%s' % row, total , wbf['content_float'])
            worksheet.write('AE%s' % row, total_new , wbf['content_float'])
            worksheet.write('AF%s' % row, faktur_pajak , wbf['content'])
            worksheet.write('AG%s' % row, alamat_konsumen , wbf['content'])
            worksheet.write('AH%s' % row, dsoc_name , wbf['content'])
            worksheet.write('AI%s' % row, dsoc_reason , wbf['content'])
            worksheet.write('AJ%s' % row, kec , wbf['content'])
            worksheet.write('AK%s' % row, pembawa , wbf['content'])
            worksheet.write('AL%s' % row, alasan , wbf['content'])
            worksheet.write('AM%s' % row, dealer_sendiri , wbf['content'])
            worksheet.write('AN%s' % row, tahun_perakitan , wbf['content'])
            worksheet.write('AO%s' % row, create_date , wbf['content'])
            worksheet.write('AP%s' % row, km , wbf['content'])
            worksheet.write('AQ%s' % row, nomor_sa , wbf['content'])

            no+=1
            row+=1
            
            total_qty += qty
            total_het += het
            total_discount += discount
            
            total_hpp += hpp
            total_dpp += dpp
            total_ppn += ppn
            total_discount_amount += discount_amount
            total_total_gp += total_gp
            total_total+=total
            total_total_new+=total_new
            
        
        worksheet.autofilter('A5:AQ%s' % (row))  
        worksheet.freeze_panes(5, 3)
        
        #TOTAL
        worksheet.merge_range('A%s:C%s' % (row,row), 'Total', wbf['total'])    
        worksheet.merge_range('D%s:U%s' % (row,row), '', wbf['total'])
        worksheet.merge_range('AF%s:AQ%s' %(row,row), '', wbf['total'])

       
        
        formula_total_qty = '{=subtotal(9,V%s:V%s)}' % (row1, row-1) 
        formula_total_het = '{=subtotal(9,W%s:W%s)}' % (row1, row-1) 
        formula_total_discount = '{=subtotal(9,X%s:X%s)}' % (row1, row-1)
        formula_total_discount_amount = '{=subtotal(9,Y%s:Y%s)}' % (row1, row-1) 
        formula_total_dpp = '{=subtotal(9,Z%s:Z%s)}' % (row1, row-1) 
        formula_total_ppn = '{=subtotal(9,AA%s:AA%s)}' % (row1, row-1) 
        formula_total_hpp = '{=subtotal(9,AB%s:AB%s)}' % (row1, row-1) 
        formula_total_total_gp = '{=subtotal(9,AC%s:AC%s)}' % (row1, row-1) 
        formula_total = '{=subtotal(9,AD%s:AD%s)}' % (row1, row-1)
        formula_total_new = '{=subtotal(9,AE%s:AE%s)}' % (row1, row-1)


        worksheet.write_formula(row-1,21,formula_total_qty, wbf['total_float'], total_qty)                  
        worksheet.write_formula(row-1,22,formula_total_het, wbf['total_float'], total_het)
        worksheet.write_formula(row-1,23,formula_total_discount, wbf['total_float'],total_discount)
        worksheet.write_formula(row-1,24,formula_total_discount_amount, wbf['total_float'], total_discount_amount)
        worksheet.write_formula(row-1,25,formula_total_dpp, wbf['total_float'], total_dpp) 
        worksheet.write_formula(row-1,26,formula_total_ppn, wbf['total_float'], total_ppn)
        worksheet.write_formula(row-1,27,formula_total_hpp, wbf['total_float'], total_hpp)
        worksheet.write_formula(row-1,28,formula_total_total_gp, wbf['total_float'], total_total_gp)
        worksheet.write_formula(row-1,29,formula_total, wbf['total_float'], total_total)
        worksheet.write_formula(row-1,30,formula_total_new, wbf['total_float'], total_total_new)
        worksheet.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])  
                   
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_workshop', 'view_report_workshop_wizard')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.report.workshop.wizard',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }


    def _print_excel_report_unit_entry_by_reason(self, cr, uid, ids, data, context=None): 

        curr_date= self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)
        user = self.pool.get('res.users').browse(cr, uid, uid)
        company_name = user.company_id.name
        username = user.name
        # filename = 'Report Prestasi Mekanik Detil '+str(curr_date.strftime("%Y%m%d_%H%M%S"))+'.xlsx'
        wo_categ = data['wo_categ']
        product_ids = data['product_ids']
        start_date = data['start_date']
        end_date = data['end_date']
        state = data['state']
        branch_ids = data['branch_ids']
        partner_ids = data['partner_ids']        
        tz = '7 hours'
        query_where = " WHERE 1=1"
        query_where_wo_date = ""
        query_where_woc_date = ""


        query_where =" '%s' and '%s' "%(start_date,end_date)
        if not branch_ids :
            query_branch_id = " is not null "
        else:
            query_branch_id = " in %s " % str(tuple(branch_ids)).replace(',)', ')')

        query = """
                SELECT 
                wb.name as name
                ,reason.alasan_ke_ahass as alasan_ke_ahass
                ,cnt_unit.cnt_unit as cnt_unit
                ,jasa.amt_jasa as amt_jasa
                ,jasa.amt_oil as amt_oil
                ,jasa.amt_part as amt_part
                ,jasa.amt_total as amt_total
                ,jasa.qty_cla as qty_cla
                ,jasa.qty_cs as qty_cs
                ,jasa.qty_hr  as qty_hr
                ,jasa.qty_kpb  as qty_kpb
                ,jasa.qty_lr  as qty_lr
                ,jasa.qty_ls  as qty_ls
                ,jasa.qty_or  as qty_or
                ,jasa.qty_qs  as qty_qs
                ,kpb.cnt_inv  as cnt_inv
                ,kpb.cnt_cla  as cnt_cla
                ,kpb.cnt_kpb_1  as cnt_kpb_1
                ,kpb.cnt_kpb_2  as cnt_kpb_2
                ,kpb.cnt_kpb_3  as cnt_kpb_3
                ,kpb.cnt_kpb_4  as cnt_kpb_4
                from wtc_work_order reason
                LEFT JOIN (
                SELECT wo.alasan_ke_ahass
                , SUM(CASE WHEN wol.categ_id = 'Service' THEN COALESCE(wol.price_unit,0) * (1 - COALESCE(NULLIF(wol.discount,0),0) / 100)  * COALESCE(wol.product_qty,0) END) amt_jasa
                , SUM(CASE WHEN wol.categ_id = 'Sparepart' AND pc.name NOT IN ( 'OLI','OIL') THEN COALESCE(wol.price_unit,0) * (1 - COALESCE(NULLIF(wol.discount,0),0) / 100)  * wol.supply_qty END) amt_part
                , SUM(CASE WHEN wol.categ_id = 'Sparepart' AND pc.name = 'OIL' THEN COALESCE(wol.price_unit,0) * (1 - COALESCE(NULLIF(wol.discount,0),0) / 100)  * wol.supply_qty END) amt_oil
                , SUM(COALESCE(wol.price_unit,0) * (1 - COALESCE(NULLIF(wol.discount,0),0) / 100) / 1.1 * CASE WHEN wol.categ_id = 'Sparepart' THEN wol.supply_qty ELSE COALESCE(wol.product_qty,0) END) amt_total
                , SUM(CASE WHEN wol.categ_id = 'Service' AND pc2.name = 'KPB' THEN COALESCE(wol.product_qty,0) END) qty_kpb
                , SUM(CASE WHEN wol.categ_id = 'Service' AND pc.name = 'CS' THEN COALESCE(wol.product_qty,0) END) qty_cs
                , SUM(CASE WHEN wol.categ_id = 'Service' AND pc.name = 'LS' THEN COALESCE(wol.product_qty,0) END) qty_ls
                , SUM(CASE WHEN wol.categ_id = 'Service' AND pc.name = 'OR+' THEN COALESCE(wol.product_qty,0) END) qty_or
                , SUM(CASE WHEN wol.categ_id = 'Service' AND pc2.name = 'QS' THEN COALESCE(wol.product_qty,0) END) qty_qs
                , SUM(CASE WHEN wol.categ_id = 'Service' AND pc.name = 'LR' THEN COALESCE(wol.product_qty,0) END) qty_lr
                , SUM(CASE WHEN wol.categ_id = 'Service' AND pc.name = 'HR' THEN COALESCE(wol.product_qty,0) END) qty_hr
                , SUM(CASE WHEN wol.categ_id = 'Service' AND pc.name = 'CLA' THEN COALESCE(wol.product_qty,0) END) qty_cla
                , SUM(CASE WHEN wol.categ_id = 'Service' THEN COALESCE(wol.product_qty,0) END) qty_total
                FROM wtc_work_order wo
                INNER JOIN account_invoice ai ON wo.id = ai.transaction_id AND ai.model_id IN (SELECT id FROM ir_model WHERE model = 'wtc.work.order')
                INNER JOIN wtc_work_order_line wol ON wo.id = wol.work_order_id
                LEFT JOIN product_product p ON wol.product_id = p.id
                LEFT JOIN product_template pt ON p.product_tmpl_id = pt.id
                LEFT JOIN product_category pc ON pt.categ_id = pc.id
                LEFT JOIN product_category pc2 ON pc.parent_id = pc2.id
                WHERE wo.state IN ('open', 'done')
                AND wo.date_confirm BETWEEN   %s and wo.branch_id %s
                GROUP BY wo.alasan_ke_ahass
                )jasa on reason.alasan_ke_ahass=jasa.alasan_ke_ahass
                LEFT JOIN (
                SELECT kpb.alasan_ke_ahass,sum(kpb.cnt_inv)cnt_inv,sum(kpb.cnt_kpb_1)cnt_kpb_1,sum(kpb.cnt_kpb_2)cnt_kpb_2,sum(kpb.cnt_kpb_3)cnt_kpb_3,sum(kpb.cnt_kpb_4)cnt_kpb_4,sum(kpb.cnt_cla)cnt_cla from
                (SELECT COALESCE(wo.mekanik_id,0)mekanik_id,wo.alasan_ke_ahass
                , COUNT(wo.id) AS cnt_inv
                , COUNT(CASE WHEN wo.type = 'KPB' AND wo.kpb_ke = '1' THEN wo.id END) AS cnt_kpb_1
                , COUNT(CASE WHEN wo.type = 'KPB' AND wo.kpb_ke = '2' THEN wo.id END) AS cnt_kpb_2
                , COUNT(CASE WHEN wo.type = 'KPB' AND wo.kpb_ke = '3' THEN wo.id END) AS cnt_kpb_3
                , COUNT(CASE WHEN wo.type = 'KPB' AND wo.kpb_ke = '4' THEN wo.id END) AS cnt_kpb_4
                , COUNT(CASE WHEN wo.type = 'CLA' THEN wo.id END) AS cnt_cla
                FROM wtc_work_order wo
                INNER JOIN account_invoice ai ON wo.id = ai.transaction_id AND ai.model_id IN (SELECT id FROM ir_model WHERE model = 'wtc.work.order')
                WHERE wo.state IN ('open', 'done')
                AND wo.date_confirm between  %s and wo.branch_id  %s
                GROUP BY wo.mekanik_id,wo.alasan_ke_ahass)kpb
                GROUP BY kpb.alasan_ke_ahass
                )kpb on reason.alasan_ke_ahass=kpb.alasan_ke_ahass
                LEFT JOIN (
                select unit.alasan_ke_ahass,sum(unit.cnt_per_date)cnt_unit from 
                (SELECT wo.branch_id
                , wo.date_confirm
                ,COALESCE(wo.mekanik_id,0)mekanik_id
                ,wo.alasan_ke_ahass
                , COUNT(DISTINCT wo.lot_id) AS cnt_per_date
                FROM wtc_work_order wo
                INNER JOIN account_invoice ai ON wo.id = ai.transaction_id AND ai.model_id IN (SELECT id FROM ir_model WHERE model = 'wtc.work.order')
                WHERE wo.state IN ('open', 'done')
                AND wo.type <> 'WAR' AND wo.type <> 'SLS'
                AND wo.date_confirm BETWEEN %s and wo.branch_id  %s
                GROUP BY wo.branch_id, wo.date_confirm,COALESCE(wo.mekanik_id,0),wo.alasan_ke_ahass)unit
                GROUP BY unit.alasan_ke_ahass)cnt_unit on reason.alasan_ke_ahass=cnt_unit.alasan_ke_ahass
                LEFT JOIN 
                wtc_branch wb on reason.branch_id=wb.id 
                where reason.date_confirm BETWEEN %s and reason.branch_id  %s
                group by wb.name,reason.alasan_ke_ahass,jasa.amt_jasa,jasa.amt_oil,jasa.amt_part,jasa.amt_total,jasa.qty_cla
                ,jasa.qty_cs,jasa.qty_hr,jasa.qty_kpb,jasa.qty_lr,jasa.qty_ls,jasa.qty_or,jasa.qty_qs,kpb.cnt_inv
                ,kpb.cnt_cla,kpb.cnt_kpb_1,kpb.cnt_kpb_2,kpb.cnt_kpb_3,kpb.cnt_kpb_4,cnt_unit.cnt_unit
                
            """ % (
                    query_where
                    , query_branch_id
                    ,query_where
                    , query_branch_id
                    ,query_where
                    , query_branch_id
                    ,query_where
                    , query_branch_id
                )  
        cr.execute (query)
        ress = cr.dictfetchall()
  
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Unit Entry')
        worksheet.set_column('B1:B1', 16)
        worksheet.set_column('C1:C1', 26)
        worksheet.set_column('D1:D1', 13)
        worksheet.set_column('E1:E1', 18)
        worksheet.set_column('F1:F1', 18)
        worksheet.set_column('G1:G1', 18)
        worksheet.set_column('H1:H1', 18)
        worksheet.set_column('I1:I1', 20)
        worksheet.set_column('J1:J1', 15)
        worksheet.set_column('K1:K1', 15)
        worksheet.set_column('L1:L1', 15)
        worksheet.set_column('M1:M1', 15)
        worksheet.set_column('N1:N1', 15)
        worksheet.set_column('O1:O1', 15)
        worksheet.set_column('P1:P1', 15)
        worksheet.set_column('Q1:Q1', 15)
        worksheet.set_column('R1:R1', 15)
        worksheet.set_column('S1:S1', 15)
        worksheet.set_column('T1:T1', 15)
        worksheet.set_column('U1:U1', 15)
        worksheet.set_column('V1:V1', 17)
       
                        
        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        filename = 'Report Unit Entry by Reason '+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report Unit Entry' , wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])

        row = 4
        header_row = row

        col = 0 #branch_code
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'No', wbf['header'])
        col += 1 #branch_name
        worksheet.set_column(col, col, 35)
        worksheet.write_string(row, col, 'Branch Code', wbf['header']) 
        col += 1
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'Alasan ke AHASS', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'Unit', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'Invoice', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'Jasa', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'Part', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'Oil', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'Total', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'KPB1', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'KPB2', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'KPB3', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'KPB4', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'CLA', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'CS', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'LS', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'OR', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'LR', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'HR', wbf['header'])

        data_last_col = col

        row += 1
        data_first_row = row
        no = 0
        # print 'ress',query,ress
        # # sdf
        for res in ress :
            no +=1
            
            name    = res['name']
            nama    = res['alasan_ke_ahass']
            cnt_unit    = res['cnt_unit']
            amt_jasa    = res['amt_jasa']
            amt_oil = res['amt_oil']
            amt_part    = res['amt_part']
            amt_total   = res['amt_total']
            qty_cla = res['qty_cla']
            qty_cs  = res['qty_cs']
            qty_hr  = res['qty_hr']
            qty_kpb = res['qty_kpb']
            qty_lr  = res['qty_lr']
            qty_ls  = res['qty_ls']
            qty_or  = res['qty_or']
            qty_qs  =res['qty_qs']
            # qty_total   = res[15]
            cnt_inv = res['cnt_inv']
            cnt_cla = res['cnt_cla']
            cnt_kpb_1   = res['cnt_kpb_1']
            cnt_kpb_2   = res['cnt_kpb_2']
            cnt_kpb_3   = res['cnt_kpb_3']
            cnt_kpb_4   = res['cnt_kpb_4']
            
            col = 0 #branch_code
            worksheet.write(row, col, no, wbf['content'])
            col += 1 #branch_name
            worksheet.write_string(row, col, name, wbf['content'])
            col += 1 #dealer_code
            worksheet.write_string(row, col, nama, wbf['content'])
            col += 1 #dealer_code
            worksheet.write(row, col, cnt_unit, wbf['content'])            
            col += 1 #dealer_code
            worksheet.write(row, col, cnt_inv, wbf['content'])  
            col += 1 #dealer_code
            worksheet.write(row, col, amt_jasa, wbf['content'])  
            col += 1 #dealer_code
            worksheet.write(row, col, amt_part, wbf['content'])  
            col += 1 #dealer_code
            worksheet.write(row, col, amt_oil, wbf['content'])
            col += 1 #dealer_code
            worksheet.write(row, col, amt_total, wbf['content'])
            col += 1
            worksheet.write(row, col, cnt_kpb_1, wbf['content'])
            col += 1
            worksheet.write(row, col, cnt_kpb_2, wbf['content'])
            col += 1
            worksheet.write(row, col, cnt_kpb_3, wbf['content'])
            col += 1
            worksheet.write(row, col, cnt_kpb_4, wbf['content'])
            col += 1
            worksheet.write(row, col, cnt_cla, wbf['content'])
            col += 1
            worksheet.write(row, col, qty_cs, wbf['content'])
            col += 1
            worksheet.write(row, col, qty_ls, wbf['content'])
            col += 1
            worksheet.write(row, col, qty_or, wbf['content'])
            col += 1
            worksheet.write(row, col, qty_lr, wbf['content'])
            col += 1
            worksheet.write(row, col, qty_hr, wbf['content'])
#             col += 1
#             worksheet.write(row, col, tot_waktu, wbf['content'])
            
            row += 1
        worksheet.autofilter(header_row, 0, row, data_last_col)

        #Datecreate and Created
        # worksheet.write(row+2, 0, '%s %s' % (str(curr_date.strftime("%Y-%m-%d %H:%M:%S")),username) , wbf['footer'])  

        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_workshop', 'view_report_workshop_wizard')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.report.workshop.wizard',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }
wtc_report_workshop()
