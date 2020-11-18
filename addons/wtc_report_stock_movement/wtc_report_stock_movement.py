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

class wtc_report_stock_movement_wizard(osv.osv_memory):
   
    _name = "wtc.report.stock.movement.wizard"
    _description = "Stock Movement Report"

    wbf = {}

    def _get_default(self,cr,uid,date=False,user=False,context=None):
        if date :
            return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)
        else :
            return self.pool.get('res.users').browse(cr, uid, uid)
    
    def _get_ids_branch(self, cr, uid, context=None):
        branch_ids_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
        branch_ids = [b.id for b in branch_ids_user]
        return branch_ids
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(wtc_report_stock_movement_wizard, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        branch_ids = self._get_ids_branch(cr, uid, context)
        doc = etree.XML(res['arch'])
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
        
        for node in nodes_branch :
            node.set('domain', '[("id", "in", '+ str(branch_ids)+')]')
        
        res['arch'] = etree.tostring(doc)
        return res
        
    def categ_ids_change(self, cr, uid, ids, categ_ids, context=None):
        value = {}
        domain = {}
        value['product_ids'] = False
        if categ_ids[0][2] :
            domain['product_ids'] = [('categ_id','in',categ_ids[0][2])]
        else :
            ids_all_product = self.pool.get('product.product').search(cr, uid, [])
            domain['product_ids'] = [('categ_id','in',ids_all_product)]
        return {'value':value, 'domain':domain}
            
    _columns = {
        'state_x': fields.selection( ( ('choose','choose'),('get','get'))), #xls
        'data_x': fields.binary('File', readonly=True),
        'name': fields.char('Filename', 100, readonly=True), 
        'options': fields.selection([('detail_movement','Detail Movement'), ('outstanding','Outstanding Movement')], 'Options', required=True, change_default=True, select=True),
        'division': fields.selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum')], 'Division', change_default=True, select=True),
        'picking_type_code': fields.selection([('all','All'),('in','In'),('out','Out'),('incoming','Receipts'),('outgoing','Delivery Orders'),('internal','Internal Transfers'),('interbranch_in','Interbranch Receipts'),('interbranch_out','Interbranch Deliveries')], 'Picking Type', change_default=True, select=True),
        'date_start_date': fields.date('Start Date'),
        'date_end_date': fields.date('End Date'),
        'min_date_start_date': fields.date('Start Date'),
        'min_date_end_date': fields.date('End Date'),
        'date_done_start_date': fields.date('Start Date'),
        'date_done_end_date': fields.date('End Date'),
        'branch_ids': fields.many2many('wtc.branch', 'wtc_report_stock_movement_branch_rel', 'wtc_report_stock_movement_wizard_id',
            'branch_id', 'Branches', copy=False),
        'categ_ids': fields.many2many('product.category', 'wtc_report_stock_movement_categ_rel', 'wtc_report_stock_movement_wizard_id',
            'categ_id', 'Categories', copy=False, domain=[('type','=','normal')]),
        'product_ids': fields.many2many('product.product', 'wtc_report_stock_movement_product_rel', 'wtc_report_stock_movement_wizard_id',
            'product_id', 'Products'),
        'partner_ids': fields.many2many('res.partner', 'wtc_report_stock_movement_partner_rel', 'wtc_report_stock_movement_wizard_id',
            'partner_id', 'Partners'),     
        'type_file': fields.selection([('excel','Excel'),('csv','CSV')],string="Format File"),
    }

    _defaults = {
        'state_x': lambda *a: 'choose',
        'options': 'detail_movement',
        'picking_type_code': 'all',
        'date_done_start_date':datetime.today(),
        'date_done_end_date':datetime.today(),        
        'type_file':'excel',
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
            data.update({'branch_ids': self._get_ids_branch(cr, uid, context)})
        if len(data['categ_ids']) == 0 :
            ids_categ = self.pool.get('product.category').search(cr, uid, [('type','=','normal')])
            data.update({'categ_ids': ids_categ})         
        return self._print_excel_report(cr, uid, ids, data, context=context)
    
    def _print_excel_report(self, cr, uid, ids, data, context=None):        
        options = data['options']
        division = data['division']
        picking_type_code = data['picking_type_code']
        date_start_date = data['date_start_date']
        date_end_date = data['date_end_date']
        min_date_start_date = data['min_date_start_date']
        min_date_end_date = data['min_date_end_date']
        date_done_start_date = data['date_done_start_date']
        date_done_end_date = data['date_done_end_date']
        branch_ids = data['branch_ids']
        categ_ids = data['categ_ids']
        product_ids = data['product_ids']
        partner_ids = data['partner_ids']
        type_file=data['type_file']
        
        if options == 'detail_movement':
            if picking_type_code=='internal':
                query="""
                    select 
                    b.code as branch_code
                    , b.name as branch_name
                    , spick.division
                    , spt.name as picking_type_name
                    , spick.name as picking_name
                    , '' as packing_name
                    , date(spick.date_done + interval '7 hours') as packing_date
                    , partner.default_code as partner_code
                    , partner.name as partner_name
                    , '' as ekspedisi_code
                    , '' as ekspedisi_name
                    , product.name_template as prod_tmpl
                    , pav.code as color
                    , spl.name as engine
                    , spl.chassis_no as chassis
                    , spl.tahun as tahun
                    , sm.product_qty as qty
                    , '' as packing_state
                    , spick.origin as picking_origin
                    , COALESCE(spick2.name,'') as backorder
                    , sloc_src.name as source_location
                    , sloc_dest.name as dest_location
                    , spl.no_ship_list as sl_ahm
                    , ''
                    , ai.number as pembelian
                    from stock_picking spick 
                    inner join stock_move sm on spick.id = sm.picking_id 
                    left join stock_production_lot spl on spl.id = sm.restrict_lot_id
                    left join account_invoice ai on ai.id = spl.supplier_invoice_id
                    left join stock_picking_type spt ON spt.id = spick.picking_type_id 
                    left join wtc_branch b on b.id = spick.branch_id 
                    left join res_partner partner on partner.id = spick.partner_id 
                    left join stock_picking spick2 ON spick2.id = spick.backorder_id 
                    left join product_product product on product.id = sm.product_id
                    left join product_attribute_value_product_product_rel pavpp ON product.id = pavpp.prod_id 
                    left join product_attribute_value pav ON pavpp.att_id = pav.id 
                    left join product_template prod_tmpl ON prod_tmpl.id = product.product_tmpl_id 
                    left join product_category prod_categ ON prod_categ.id = prod_tmpl.categ_id 
                    left join stock_location sloc_src ON sloc_src.id = sm.location_id
                    left join stock_location sloc_dest ON sloc_dest.id = sm.location_dest_id
                   
                    
                """
                if division =='Unit':
                    query_where = " WHERE sm.restrict_lot_id is not null and sm.product_qty > 0 and spick.state = 'done' "
                else:
                    query_where = " WHERE sm.restrict_lot_id is null and sm.product_qty > 0 and spick.state = 'done' "
                
            else:
                query = """
                select 
                b.code as branch_code
                , b.name as branch_name
                , spick.division
                , spt.name as picking_type_name
                , spick.name as picking_name
                , spack.name as packing_name
                , date(spick.date_done + interval '7 hours') as packing_date
                , partner.default_code as partner_code
                , partner.name as partner_name
                , expedisi.default_code as ekspedisi_code
                , expedisi.name as ekspedisi_name
                , product.name_template as prod_tmpl
                , pav.code as color
                , spl.name as engine
                , spl.chassis_no as chassis
                , spl.tahun as tahun
                , spo.product_qty as qty
                , spack.state as packing_state
                , spick.origin as picking_origin
                , COALESCE(spick2.name,'') as backorder
                , sloc_src.name as source_location
                , sloc_dest.name as dest_location
                , spl.no_ship_list as sl_ahm
                , spack.date_in as tgl_masuk_brg
                , ai.number as pembelian
                from stock_picking spick
                inner join stock_pack_operation spo on spick.id = spo.picking_id
                left join stock_production_lot spl on spl.id = spo.lot_id
                left join account_invoice ai on ai.id = spl.supplier_invoice_id
                left join stock_picking_type spt ON spt.id = spick.picking_type_id 
                left join wtc_stock_packing spack on spick.id = spack.picking_id and spack."state" = 'posted'
                left join wtc_branch b on b.id = spick.branch_id 
                left join res_partner partner on partner.id = spick.partner_id 
                left join res_partner expedisi on expedisi.id = spack.expedition_id
                left join stock_picking spick2 ON spick2.id = spick.backorder_id 
                left join product_product product on product.id = spo.product_id
                left join product_attribute_value_product_product_rel pavpp ON product.id = pavpp.prod_id 
                left join product_attribute_value pav ON pavpp.att_id = pav.id 
                left join product_template prod_tmpl ON prod_tmpl.id = product.product_tmpl_id 
                left join product_category prod_categ ON prod_categ.id = prod_tmpl.categ_id 
                left join stock_location sloc_src ON sloc_src.id = spo.location_id
                left join stock_location sloc_dest ON sloc_dest.id = spo.location_dest_id
                """ 
                
                if division =='Unit':
                    query_where = " WHERE spo.lot_id is not null and spo.product_qty > 0 and spick.state = 'done' "
                else:
                    query_where = " WHERE spo.lot_id is null and spo.product_qty > 0 and spick.state = 'done' "
                
            query_where += "  AND spick.division = '%s'" % str(division)
           
            if picking_type_code :
                if picking_type_code == 'all' :
                    query_where += "  AND spt.code in ('incoming','outgoing','interbranch_in','interbranch_out')"
                elif picking_type_code == 'in' :
                    query_where += "  AND spt.code in ('incoming','interbranch_in')"
                elif picking_type_code == 'out' :
                    query_where += "  AND spt.code in ('outgoing','interbranch_out')"
                else :
                    query_where += "  AND spt.code = '%s'" % str(picking_type_code)
            if date_done_start_date :
                query_where += "  AND date(spick.date_done + interval '7 hours') >= '%s'" % str(date_done_start_date)
            if date_done_end_date :
                query_where += "  AND date(spick.date_done + interval '7 hours') <= '%s'" % str(date_done_end_date)
            if branch_ids :
                query_where += "  AND spick.branch_id in %s" % str(tuple(branch_ids)).replace(',)', ')')
            if product_ids :
                query_where += "  AND product.id in %s" % str(tuple(product_ids)).replace(',)', ')')
            if partner_ids :
                query_where += "  AND spick.partner_id in %s" % str(tuple(partner_ids)).replace(',)', ')')
            if categ_ids :
                query_where += "  AND prod_categ.id in %s" % str(tuple(categ_ids)).replace(',)', ')')

            query_order = "ORDER BY branch_code"
            cr.execute (query+query_where+query_order)

        elif options == 'outstanding':
            query="""
                select 
                b.code as branch_code
                , b.name as branch_name
                , spick.division
                , spt.name as picking_type_name
                , spick.name as picking_name
                , '' as packing_name
                , date(spick.date + interval '7 hours') as packing_date
                , partner.default_code as partner_code
                , partner.name as partner_name
                , '' as ekspedisi_code
                , '' as ekspedisi_name
                , product.name_template as prod_tmpl
                , pav.code as color
                , spl.name as engine
                , spl.chassis_no as chassis
                , spl.tahun as tahun
                , sm.product_qty as qty
                , spick.state as packing_state
                , spick.origin as picking_origin
                , COALESCE(spick2.name,'') as backorder
                , sloc_src.name as source_location
                , sloc_dest.name as dest_location
                , spl.no_ship_list as sl_ahm
                , spack.date_in as tgl_masuk_brg
                , ai.number as pembelian
                from stock_picking spick 
                inner join stock_move sm on spick.id = sm.picking_id 
                left join stock_production_lot spl on spl.id = sm.restrict_lot_id
                left join account_invoice ai on ai.id = spl.supplier_invoice_id
                left join stock_picking_type spt ON spt.id = spick.picking_type_id 
                left join wtc_branch b on b.id = spick.branch_id 
                left join res_partner partner on partner.id = spick.partner_id 
                left join stock_picking spick2 ON spick2.id = spick.backorder_id 
                left join product_product product on product.id = sm.product_id
                left join product_attribute_value_product_product_rel pavpp ON product.id = pavpp.prod_id 
                left join product_attribute_value pav ON pavpp.att_id = pav.id 
                left join product_template prod_tmpl ON prod_tmpl.id = product.product_tmpl_id 
                left join product_category prod_categ ON prod_categ.id = prod_tmpl.categ_id 
                left join stock_location sloc_src ON sloc_src.id = sm.location_id
                left join stock_location sloc_dest ON sloc_dest.id = sm.location_dest_id
                left join wtc_stock_packing spack on spick.id = spack.picking_id
            """
            if division =='Unit':
                query_where = " WHERE sm.restrict_lot_id is not null and sm.product_qty > 0 and spick.state not in ('draft', 'cancel', 'done') "
            else:
                query_where = " WHERE sm.restrict_lot_id is null and sm.product_qty > 0 and spick.state not in ('draft', 'cancel', 'done') "
                
                
            query_where += "  AND spick.division = '%s'" % str(division)
           
            if picking_type_code :
                if picking_type_code == 'all' :
                    query_where += "  AND spt.code in ('incoming','outgoing','interbranch_in','interbranch_out')"
                elif picking_type_code == 'in' :
                    query_where += "  AND spt.code in ('incoming','interbranch_in')"
                elif picking_type_code == 'out' :
                    query_where += "  AND spt.code in ('outgoing','interbranch_out')"
                else :
                    query_where += "  AND spt.code = '%s'" % str(picking_type_code)
            if date_start_date :
                query_where += "  AND date(spick.date) >= '%s'" % str(date_start_date)
            if date_end_date :
                query_where += "  AND date(spick.date) <= '%s'" % str(date_end_date)
            if branch_ids :
                query_where += "  AND spick.branch_id in %s" % str(tuple(branch_ids)).replace(',)', ')')
            if product_ids :
                query_where += "  AND product.id in %s" % str(tuple(product_ids)).replace(',)', ')')
            if partner_ids :
                query_where += "  AND spick.partner_id in %s" % str(tuple(partner_ids)).replace(',)', ')')
            if categ_ids :
                query_where += "  AND prod_categ.id in %s" % str(tuple(categ_ids)).replace(',)', ')')

            query_order = "ORDER BY branch_code"
            cr.execute (query+query_where+query_order)

        ress = cr.fetchall()

        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        filename = ""

        if type_file == 'csv':
            content = "Branch Code,Branch Name,Division,Picking Type,Picking Number,Packing Number,"
            if options == 'detail_movement':
                content += 'Movement Date,'
                filename = 'Report Stock Movement '+str(date)+'.csv'
            elif options == 'outstanding':
                content += 'Order Date,'
                filename = 'Report Outstanding Movement '+str(date)+'.csv'
            content += "Partner Code,Partner Name,Expedition Code,Expedition Name,Type,Color,Engine Number,Chassis Number,Tahun Pembuatan,Qty,Source Location,Destination Location,Packing State,Source Document,Backorder,Shipping List AHM,Tgl Masuk Barang,Invoice Pembelian \r\n"
            for res in ress:
                branch_code = str(res[0].encode('ascii','ignore').decode('ascii')) if res[0] != None else ''
                branch_name = str(res[1].encode('ascii','ignore').decode('ascii')) if res[1] != None else ''
                division = str(res[2].encode('ascii','ignore').decode('ascii')) if res[2] != None else ''
                picking_type_name = str(res[3].encode('ascii','ignore').decode('ascii')) if res[3] != None else ''
                picking_name = str(res[4].encode('ascii','ignore').decode('ascii')) if res[4] != None else ''
                packing_name = str(res[5].encode('ascii','ignore').decode('ascii')) if res[5] != None else ''
                movement_date = str(res[6].encode('ascii','ignore').decode('ascii')) if res[6] != None else ''
                partner_code = str(res[7].encode('ascii','ignore').decode('ascii')) if res[7] != None else ''
                partner_name = str(res[8].encode('ascii','ignore').decode('ascii')) if res[8] != None else ''
                ekspedisi_code = str(res[9].encode('ascii','ignore').decode('ascii')) if res[9] != None else ''
                ekspedisi_name = str(res[10].encode('ascii','ignore').decode('ascii')) if res[10] != None else ''
                prod_tmpl = str(res[11].encode('ascii','ignore').decode('ascii')) if res[11] != None else ''
                color = str(res[12].encode('ascii','ignore').decode('ascii')) if res[12] != None else ''
                engine = str(res[13].encode('ascii','ignore').decode('ascii')) if res[13] != None else ''
                chassis = str(res[14].encode('ascii','ignore').decode('ascii')) if res[14] != None else ''
                tahun = str(res[15].encode('ascii','ignore').decode('ascii')) if res[15] != None else ''
                qty = res[16]
                packing_state = str(res[17].encode('ascii','ignore').decode('ascii')) if res[17] != None else ''
                picking_origin = str(res[18].encode('ascii','ignore').decode('ascii')) if res[18] != None else ''
                backorder = str(res[19].encode('ascii','ignore').decode('ascii')) if res[19] != None else ''
                source_location = str(res[20].encode('ascii','ignore').decode('ascii')) if res[20] != None else ''
                dest_location = str(res[21].encode('ascii','ignore').decode('ascii')) if res[21] != None else ''
                sl_ahm = str(res[22].encode('ascii','ignore').decode('ascii')) if res[22] != None else ''
                tgl_masuk_brg = res[23] if res[23] else ''
                invoice_number = str(res[24].encode('ascii','ignore').decode('ascii')) if res[24] != None else ''

                content += "%s," %branch_code
                content += "%s," %branch_name
                content += "%s," %division
                content += "%s," %picking_type_name
                content += "%s," %picking_name
                content += "%s," %packing_name
                content += "%s," %movement_date
                content += "%s," %partner_code
                content += "%s," %partner_name
                content += "%s," %ekspedisi_code
                content += "%s," %ekspedisi_name
                content += "%s," %prod_tmpl
                content += "%s," %color
                content += "%s," %engine
                content += "%s," %chassis
                content += "%s," %tahun
                content += "%s," %qty
                content += "%s," %source_location
                content += "%s," %dest_location
                content += "%s," %packing_state
                content += "%s," %picking_origin
                content += "%s," %backorder
                content += "%s," %sl_ahm
                content += "%s," %tgl_masuk_brg
                content += "%s \r\n" %invoice_number

            out = base64.encodestring(content)
        else:
            fp = StringIO()
            workbook = xlsxwriter.Workbook(fp)        
            workbook = self.add_workbook_format(cr, uid, workbook)
            wbf=self.wbf
            worksheet = workbook.add_worksheet('Stock Movement')
            worksheet.set_column('B1:B1', 13)
            worksheet.set_column('C1:C1', 21)
            worksheet.set_column('D1:D1', 11)
            worksheet.set_column('E1:E1', 20)
            worksheet.set_column('F1:F1', 20)
            worksheet.set_column('G1:G1', 20)
            worksheet.set_column('H1:H1', 11)
            worksheet.set_column('I1:I1', 22)
            worksheet.set_column('J1:J1', 20)
            worksheet.set_column('K1:K1', 15)
            worksheet.set_column('L1:L1', 15)
            worksheet.set_column('M1:M1', 17)
            worksheet.set_column('N1:N1', 9)
            worksheet.set_column('O1:O1', 17)
            worksheet.set_column('P1:P1', 20)
            worksheet.set_column('Q1:Q1', 20)
            worksheet.set_column('R1:R1', 20)
            worksheet.set_column('S1:S1', 20)
            worksheet.set_column('T1:T1', 26)
            worksheet.set_column('U1:U1', 20)
            worksheet.set_column('V1:V1', 20)
            worksheet.set_column('W1:W1', 24)
            worksheet.set_column('X1:X1', 20)
            worksheet.set_column('Y1:Y1', 15)
            worksheet.set_column('Z1:Z1', 20)
                            
            company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
            user = self._get_default(cr, uid, user=True, context=context).name
            
            worksheet.write('A1', company_name , wbf['company'])
            if options == 'detail_movement':
                filename = 'Report Stock Movement '+str(date)+'.xlsx'
                worksheet.write('A2', 'Report Stock Movement' , wbf['title_doc'])
            elif options == 'outstanding':
                filename = 'Report Outstanding Movement '+str(date)+'.xlsx'
                worksheet.write('A2', 'Report Outstanding Movement' , wbf['title_doc'])
            worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(date_done_start_date),str(date_done_end_date)) , wbf['company'])
            row=3
            rowsaldo = row
            row+=1
            worksheet.write('A%s' % (row+1), 'No' , wbf['header'])
            worksheet.write('B%s' % (row+1), 'Branch Code' , wbf['header'])
            worksheet.write('C%s' % (row+1), 'Branch Name' , wbf['header'])
            worksheet.write('D%s' % (row+1), 'Division' , wbf['header'])
            worksheet.write('E%s' % (row+1), 'Picking Type' , wbf['header'])
            worksheet.write('F%s' % (row+1), 'Picking Number' , wbf['header'])
            worksheet.write('G%s' % (row+1), 'Packing Number' , wbf['header'])
            if options == 'detail_movement':
                worksheet.write('H%s' % (row+1), 'Movement Date' , wbf['header'])
            elif options == 'outstanding':
                worksheet.write('H%s' % (row+1), 'Order Date' , wbf['header'])
            worksheet.write('I%s' % (row+1), 'Partner Code' , wbf['header'])
            worksheet.write('J%s' % (row+1), 'Partner Name' , wbf['header'])
            worksheet.write('K%s' % (row+1), 'Expedition Code' , wbf['header'])
            worksheet.write('L%s' % (row+1), 'Expedition Name' , wbf['header'])
            worksheet.write('M%s' % (row+1), 'Type' , wbf['header'])
            worksheet.write('N%s' % (row+1), 'Color' , wbf['header'])
            worksheet.write('O%s' % (row+1), 'Engine Number' , wbf['header'])
            worksheet.write('P%s' % (row+1), 'Chassis Number' , wbf['header'])                
            worksheet.write('Q%s' % (row+1), 'Tahun Pembuatan' , wbf['header'])
            worksheet.write('R%s' % (row+1), 'Qty' , wbf['header'])
            worksheet.write('S%s' % (row+1), 'Source Location' , wbf['header'])
            worksheet.write('T%s' % (row+1), 'Destination Location' , wbf['header'])
            worksheet.write('U%s' % (row+1), 'Packing State' , wbf['header'])
            worksheet.write('V%s' % (row+1), 'Source Document' , wbf['header'])
            worksheet.write('W%s' % (row+1), 'Backorder' , wbf['header'])
            worksheet.write('X%s' % (row+1), 'Shipping List AHM' , wbf['header'])
            worksheet.write('Y%s' % (row+1), 'Tgl Masuk Barang' , wbf['header'])
            worksheet.write('Z%s' % (row+1), 'Invoice Pembelian' , wbf['header'])
            row+=2 
                    
            no = 1
            total_qty = 0
            row1 = row
            
            for res in ress:
                
                branch_code = str(res[0].encode('ascii','ignore').decode('ascii')) if res[0] != None else ''
                branch_name = str(res[1].encode('ascii','ignore').decode('ascii')) if res[1] != None else ''
                division = str(res[2].encode('ascii','ignore').decode('ascii')) if res[2] != None else ''
                picking_type_name = str(res[3].encode('ascii','ignore').decode('ascii')) if res[3] != None else ''
                picking_name = str(res[4].encode('ascii','ignore').decode('ascii')) if res[4] != None else ''
                packing_name = str(res[5].encode('ascii','ignore').decode('ascii')) if res[5] != None else ''
                movement_date = str(res[6].encode('ascii','ignore').decode('ascii')) if res[6] != None else ''
                partner_code = str(res[7].encode('ascii','ignore').decode('ascii')) if res[7] != None else ''
                partner_name = str(res[8].encode('ascii','ignore').decode('ascii')) if res[8] != None else ''
                ekspedisi_code = str(res[9].encode('ascii','ignore').decode('ascii')) if res[9] != None else ''
                ekspedisi_name = str(res[10].encode('ascii','ignore').decode('ascii')) if res[10] != None else ''
                prod_tmpl = str(res[11].encode('ascii','ignore').decode('ascii')) if res[11] != None else ''
                color = str(res[12].encode('ascii','ignore').decode('ascii')) if res[12] != None else ''
                engine = str(res[13].encode('ascii','ignore').decode('ascii')) if res[13] != None else ''
                chassis = str(res[14].encode('ascii','ignore').decode('ascii')) if res[14] != None else ''
                tahun = str(res[15].encode('ascii','ignore').decode('ascii')) if res[15] != None else ''
                qty = res[16]
                packing_state = str(res[17].encode('ascii','ignore').decode('ascii')) if res[17] != None else ''
                picking_origin = str(res[18].encode('ascii','ignore').decode('ascii')) if res[18] != None else ''
                backorder = str(res[19].encode('ascii','ignore').decode('ascii')) if res[19] != None else ''
                source_location = str(res[20].encode('ascii','ignore').decode('ascii')) if res[20] != None else ''
                dest_location = str(res[21].encode('ascii','ignore').decode('ascii')) if res[21] != None else ''
                sl_ahm = str(res[22].encode('ascii','ignore').decode('ascii')) if res[22] != None else ''
                tgl_masuk_brg = res[23] if res[23] else ''
                invoice_number = str(res[24].encode('ascii','ignore').decode('ascii')) if res[24] != None else ''
                total_qty += qty
                                
                worksheet.write('A%s' % row, no , wbf['content_number'])                    
                worksheet.write('B%s' % row, branch_code , wbf['content'])
                worksheet.write('C%s' % row, branch_name , wbf['content'])
                worksheet.write('D%s' % row, division , wbf['content'])
                worksheet.write('E%s' % row, picking_type_name , wbf['content'])
                worksheet.write('F%s' % row, picking_name , wbf['content'])
                worksheet.write('G%s' % row, packing_name , wbf['content'])
                worksheet.write('H%s' % row, movement_date , wbf['content_date'])  
                worksheet.write('I%s' % row, partner_code , wbf['content'])
                worksheet.write('J%s' % row, partner_name , wbf['content'])
                worksheet.write('K%s' % row, ekspedisi_code , wbf['content'])
                worksheet.write('L%s' % row, ekspedisi_name , wbf['content'])
                worksheet.write('M%s' % row, prod_tmpl , wbf['content'])
                worksheet.write('N%s' % row, color , wbf['content_number'])
                worksheet.write('O%s' % row, engine , wbf['content_number'])
                worksheet.write('P%s' % row, chassis , wbf['content_number'])
                worksheet.write('Q%s' % row, tahun , wbf['content_float']) 
                worksheet.write('R%s' % row, qty , wbf['content_float'])
                worksheet.write('S%s' % row, source_location , wbf['content'])
                worksheet.write('T%s' % row, dest_location , wbf['content'])
                worksheet.write('U%s' % row, packing_state , wbf['content'])
                worksheet.write('V%s' % row, picking_origin , wbf['content'])
                worksheet.write('W%s' % row, backorder , wbf['content'])
                worksheet.write('X%s' % row, sl_ahm , wbf['content'])
                worksheet.write('Y%s' % row, tgl_masuk_brg , wbf['content'])
                worksheet.write('Z%s' % row, invoice_number , wbf['content'])
                no+=1
                row+=1
                
            worksheet.autofilter('A5:Z%s' % (row))  
            worksheet.freeze_panes(5, 3)
            
            #TOTAL
            worksheet.merge_range('A%s:C%s' % (row,row), 'Total', wbf['total'])    
            worksheet.merge_range('D%s:Q%s' % (row,row), '', wbf['total']) 
            worksheet.merge_range('S%s:Z%s' % (row,row), '', wbf['total']) 

            if row-1 >= row1 :
                worksheet.write_formula('R%s' % (row),'{=subtotal(9,R%s:R%s)}' % (row1, row-1), wbf['total_number'], total_qty)
            else :
                worksheet.write_blank('R%s' % (row), '', wbf['total_number'])
                                    
            worksheet.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])  
                       
            workbook.close()
            out=base64.encodestring(fp.getvalue())
            fp.close()
        
        self.write(cr, uid, ids, {'state_x': 'get', 'data_x':out, 'name': filename}, context=context)

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_stock_movement', 'view_report_stock_movement_wizard')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.report.stock.movement.wizard',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }

wtc_report_stock_movement_wizard()
