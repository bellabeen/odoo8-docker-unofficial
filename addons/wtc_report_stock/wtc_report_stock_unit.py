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

class wtc_report_stock_unit(osv.osv_memory):
    _name = "wtc.report.stock.unit.wizard"
    _description = "Report Stock Unit"

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
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(wtc_report_stock_unit, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        categ_ids = self.pool.get('product.category').get_child_ids(cr,uid,view_id,'Unit')
        branch_ids_user=self.pool.get('res.users').browse(cr,uid,uid).branch_ids
        branch_ids=[b.id for b in branch_ids_user]
        
        doc = etree.XML(res['arch'])
        nodes = doc.xpath("//field[@name='product_ids']")
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
        nodes_location = doc.xpath("//field[@name='location_ids']")
        for node in nodes:
            node.set('domain', '[("categ_id", "in", '+ str(categ_ids)+')]')
        for node in nodes_branch:
            node.set('domain', '[("id", "in", '+ str(branch_ids)+')]')
        for node in nodes_location:
            node.set('domain', '[("branch_id", "in", '+ str(branch_ids)+')]')
        res['arch'] = etree.tostring(doc)
        return res
        
    _columns = {
        'state_x': fields.selection( ( ('choose','choose'),('get','get'))), #xls
        'data_x': fields.binary('File', readonly=True),
        'name': fields.char('Filename', 100, readonly=True), 
        'options': fields.selection([('detail','Detail Per Engine'), ('type_warna','Per Type Warna'), ('location','Per Location')], 'Options', required=True, change_default=True, select=True),       
        'branch_ids': fields.many2many('wtc.branch', 'wtc_report_stock_unit_invoice_rel', 'wtc_report_stock_unit_wizard_id',
                                        'branch_id', 'Branch', copy=False),
        'product_ids': fields.many2many('product.product', 'wtc_report_stock_unit_product_rel', 'wtc_report_stock_unit_wizard_id',
                                        'product_id', 'Product', copy=False, ),
        'location_ids': fields.many2many('stock.location', 'wtc_report_stock_unit_location_rel', 'wtc_report_stock_unitwizard_id',
                                        'location_id', 'Location', copy=False, domain=[('usage','=','internal')]),
        'company_id': fields.many2one('res.company', 'Company', readonly=True)
    }

    _defaults = {
        'state_x': lambda *a: 'choose',

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
        elif data['options'] == 'location':
            return self._print_excel_report_location(cr, uid, ids, data, context=context)
        else :          
            return self._print_excel_report_warna(cr, uid, ids, data, context=context)
    
    def _query_report_detail(self, cr, uid, ids, data, context=None):  
        product_ids = data['product_ids']
        branch_ids = data['branch_ids'] 
        location_ids = data['location_ids']
        # options = data['options']
        
        tz = '7 hours'
        
        query_where = " "
    
        if branch_ids :
            branch_name = [str(b.code) for b in self.pool.get('wtc.branch').browse(cr, uid, branch_ids)]
            query_where +=" AND  branch_code in %s" % str(
                tuple(branch_name)).replace(',)', ')')
        if product_ids :
            tipe = [str(p.name) for p in self.pool.get('product.product').browse(cr, uid, product_ids)]
            warna = [str(p.attribute_value_ids.name) for p in self.pool.get('product.product').browse(cr, uid, product_ids)]
            query_where+="AND tipe in %s AND warna in %s" % (str(tuple(tipe)).replace(',)', ')'),str(tuple(warna)).replace(',)', ')'))
        if location_ids :
            loc_name = [str(l.complete_name) for l in self.pool.get('stock.location').browse(cr, uid, location_ids)]
            query_where+="AND complete_name in %s" % str(
                tuple(loc_name)).replace(',)', ')')

        query_order="order by branch_code, lot_state, complete_name, tipe, warna  "
                                                     
        query2=query_where+query_order
        
        query = """
                 select branch_name, branch_code, profit_centre, tipe, warna, in_date+ INTERVAL '7 hours' as in_date, AGE(CURRENT_TIMESTAMP, in_date+ INTERVAL '7 hours') as umur_stock, complete_name, AGE(CURRENT_TIMESTAMP, pick_date+ INTERVAL '7 hours') as umur_movement, 
            engine_no, chassis_no, lot_state, tahun, qty, cost, hpp as hpp_unit, freight_cost, last_movement, last_transaction, branch_destination, cat2_name, cat_name, series, scrap_location, in_date_mutation
            from
            ((select b.name as branch_name, b.code as branch_code, b.profit_centre, prod.name_template as tipe, pav.name as warna, lot.name as engine_no, lot.chassis_no,
            CASE
            WHEN loc.usage = 'transit' THEN 'Intransit Mutasi'
            WHEN lot.state = 'intransit' THEN 'Intransit Beli'
            WHEN lot.state = 'stock' and lot.ready_for_sale = 'not_good' THEN 'Stock NRFS'
            WHEN lot.state = 'stock' THEN 'Stock RFS'
            WHEN lot.state = 'reserved' THEN 'Stock Reserved'
            WHEN lot.state = 'workshop' THEN 'Workshop'
            WHEN lot.state ilike 'paid%' or lot.state ilike 'sold%' THEN 'Undelivered'
            END lot_state,
            lot.tahun, quant.qty, quant.cost, coalesce(lot.hpp,0) hpp, coalesce(lot.freight_cost,0) as freight_cost, loc.complete_name, cat2.name as cat2_name, cat.name as cat_name, loc.scrap_location, quant.in_date, coalesce(pick.date_done, quant.in_date) as pick_date,
            pt.series, pick.name as last_movement,
            CASE
            WHEN lot.state ilike 'paid%' or lot.state ilike 'sold%' THEN dso.name
            WHEN lot.state = 'reserved' THEN dsor.name
            WHEN lot.state = 'intransit' THEN po.name
            WHEN loc.usage = 'transit' THEN mo.name
            ELSE pick.origin END last_transaction, 
            coalesce(b_dest.code, '') as branch_destination,
            lot.in_date as in_date_mutation
            from stock_quant quant
            inner join stock_production_lot lot on quant.lot_id = lot.id
            inner join product_product prod on quant.product_id = prod.id
            inner join stock_location loc on quant.location_id = loc.id
            
            left join wtc_branch b on loc.branch_id = b.id
            
            left join product_template pt on prod.product_tmpl_id = pt.id
            left join product_category cat on pt.categ_id = cat.id
            left join product_category cat2 on cat.parent_id = cat2.id
            left join product_category cat3 on cat2.parent_id = cat3.id
            
            left join product_attribute_value_product_product_rel pavpp on prod.id = pavpp.prod_id
            left join product_attribute_value pav on pavpp.att_id = pav.id
            
            left join stock_picking pick on pick.id = lot.picking_id
            left join wtc_mutation_order mo on pick.origin = mo.name and pick.branch_id = mo.branch_id
            left join wtc_branch b_dest on b_dest.id = mo.branch_requester_id
            
            left join dealer_sale_order dso on lot.dealer_sale_order_id = dso.id
            left join dealer_sale_order dsor on lot.sale_order_reserved = dsor.id and lot.state = 'reserved'
            left join purchase_order po on po.id = lot.purchase_order_id
            
            where cat3.name = 'Unit' and (loc.usage = 'internal' or loc.usage = 'transit' or loc.usage = 'nrfs'))-- and quant.consolidated_date is not null)
            UNION
            (select b.name as branch_name, b.code as branch_code, b.profit_centre, prod.name_template as tipe, pav.name as warna, lot.name as engine_no, lot.chassis_no, 'Intransit AHM' as lot_state, lot.tahun, 1 as qty,
            (lot.hpp + coalesce(lot.freight_cost,0)) as cost, lot.hpp, coalesce(lot.freight_cost, 0) as freight_cost, loc.complete_name,
            cat2.name as cat2_name, cat.name as cat_name, loc.scrap_location, lot.create_date as in_date, lot.create_date as pick_date, pt.series, lot.no_ship_list as last_movement, po.name as last_transaction, '' as branch_destination, lot.in_date as in_date_mutation
            from stock_production_lot lot
            inner join product_product prod on lot.product_id = prod.id
            
            left join wtc_branch b on lot.branch_id = b.id
            left join stock_location loc on lot.location_id = loc.id
            
            left join product_template pt on prod.product_tmpl_id = pt.id
            left join product_category cat on pt.categ_id = cat.id
            left join product_category cat2 on cat.parent_id = cat2.id
            left join product_category cat3 on cat2.parent_id = cat3.id
            
            left join product_attribute_value_product_product_rel pavpp on prod.id = pavpp.prod_id
            left join product_attribute_value pav on pavpp.att_id = pav.id
            
            left join purchase_order po on po.id = lot.purchase_order_id
            
            where lot.state = 'intransit' and b.branch_type = 'MD')) a
            where 1=1
            """+query2+"""
            
            """ 
            
        cr.execute (query)
        ress = cr.fetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Stock Unit')
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
        worksheet.set_column('AE1:AE1', 30)     
                        
        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report Stock Unit' , wbf['title_doc'])
        worksheet.write('A3', ' ' , wbf['company'])
        row=3
        rowsaldo = row
        row+=1
        worksheet.write('A%s' % (row+1), 'No' , wbf['header'])
        worksheet.write('B%s' % (row+1), 'Branch Code' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'Branch Name' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'Profit Center' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'Product Type' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'Color' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'Incoming Date' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'Stock Aging' , wbf['header'])
        worksheet.write('I%s' % (row+1), 'Location' , wbf['header'])
        worksheet.write('J%s' % (row+1), 'Movement Aging' , wbf['header'])
        worksheet.write('K%s' % (row+1), 'Engine Number' , wbf['header'])
        worksheet.write('L%s' % (row+1), 'Chassis Number' , wbf['header'])
        worksheet.write('M%s' % (row+1), 'Engine State' , wbf['header'])
        worksheet.write('N%s' % (row+1), 'Year' , wbf['header'])
        worksheet.write('O%s' % (row+1), 'Quantity' , wbf['header'])
        worksheet.write('P%s' % (row+1), 'Cost' , wbf['header'])
        worksheet.write('Q%s' % (row+1), 'Freight Cost' , wbf['header'])
        worksheet.write('R%s' % (row+1), 'Last Movement' , wbf['header'])
        worksheet.write('S%s' % (row+1), 'Last Transaction' , wbf['header'])
        worksheet.write('T%s' % (row+1), 'Branch Destination' , wbf['header'])
        worksheet.write('U%s' % (row+1), 'Parent Category' , wbf['header'])
        worksheet.write('V%s' % (row+1), 'Category Name' , wbf['header'])
        worksheet.write('W%s' % (row+1), 'Series' , wbf['header'])
        worksheet.write('X%s' % (row+1), 'Incoming Date Mutation' , wbf['header'])
    
        row+=2               
        no = 1     
        row1 = row
        
        total_qty = 0     
        total_cost = 0
        total_freight_cost = 0         
        for res in ress:
            
            branch_name = str(res[0].encode('ascii','ignore').decode('ascii')) if res[0] != None else ''
            branch_code  = str(res[1].encode('ascii','ignore').decode('ascii')) if res[1] != None else ''
            profit_centre = str(res[2].encode('ascii','ignore').decode('ascii')) if res[2] != None else ''
            tipe = str(res[3].encode('ascii','ignore').decode('ascii')) if res[3] != None else ''
            warna = str(res[4].encode('ascii','ignore').decode('ascii')) if res[4] != None else ''
            in_date = str(res[5].encode('ascii','ignore').decode('ascii')) if res[5] != None else ''
            umur_stock = str(res[6])
            location = str(res[7].encode('ascii','ignore').decode('ascii')) if res[7] != None else ''
            umur_movement = str(res[8])
            engine_no = str(res[9].encode('ascii','ignore').decode('ascii')) if res[9] != None else ''
            chassis_no = str(res[10].encode('ascii','ignore').decode('ascii')) if res[10] != None else ''
            lot_state = str(res[11].encode('ascii','ignore').decode('ascii')) if res[11] != None else ''
            tahun = str(res[12].encode('ascii','ignore').decode('ascii')) if res[12] != None else ''
            qty = res[13]
            cost = res[14]
            freight_cost =  res[16]

            last_movement = str(res[17].encode('ascii','ignore').decode('ascii')) if res[17] != None else ''
            last_transaction = str(res[18].encode('ascii','ignore').decode('ascii')) if res[18] != None else ''
            branch_destination = str(res[19].encode('ascii','ignore').decode('ascii')) if res[19] != None else ''
            cat2_name = str(res[20].encode('ascii','ignore').decode('ascii')) if res[20] != None else ''
            cat_name = str(res[21].encode('ascii','ignore').decode('ascii')) if res[21] != None else ''
            series = str(res[22].encode('ascii','ignore').decode('ascii')) if res[22] != None else ''
            in_date_mutation = str(res[24]) if res[24] != None else ''
            
            worksheet.write('A%s' % row, no , wbf['content_number'])                    
            worksheet.write('B%s' % row, branch_code , wbf['content'])
            worksheet.write('C%s' % row, branch_name , wbf['content'])
            worksheet.write('D%s' % row, profit_centre , wbf['content'])
            worksheet.write('E%s' % row, tipe , wbf['content'])
            worksheet.write('F%s' % row, warna , wbf['content'])
            worksheet.write('G%s' % row, in_date , wbf['content'])
            worksheet.write('H%s' % row, umur_stock , wbf['content'])
            worksheet.write('I%s' % row, location , wbf['content']) 
            worksheet.write('J%s' % row, umur_movement, wbf['content'])  
            worksheet.write('K%s' % row, engine_no , wbf['content'])
            worksheet.write('L%s' % row, chassis_no , wbf['content'])
            worksheet.write('M%s' % row, lot_state   , wbf['content'])
            worksheet.write('N%s' % row, tahun , wbf['content'])
            worksheet.write('O%s' % row, qty , wbf['content_float'])
            worksheet.write('P%s' % row, cost , wbf['content_float'])
            worksheet.write('Q%s' % row, freight_cost , wbf['content_float'])
            worksheet.write('R%s' % row, last_movement, wbf['content_float'])
            worksheet.write('S%s' % row, last_transaction , wbf['content']) 
            worksheet.write('T%s' % row, branch_destination , wbf['content_float'])
            worksheet.write('U%s' % row, cat2_name , wbf['content_float'])
            worksheet.write('V%s' % row, cat_name , wbf['content_float'])
            worksheet.write('W%s' % row, series , wbf['content_float'])
            worksheet.write('X%s' % row, in_date_mutation , wbf['content_date'])
           
            no+=1
            row+=1
            
            total_qty += qty        
            total_cost += cost    
            total_freight_cost += freight_cost        
        
        worksheet.autofilter('A5:X%s' % (row))  
        worksheet.freeze_panes(5, 3)
        
        #TOTAL
        worksheet.merge_range('A%s:C%s' % (row,row), 'Total', wbf['total'])    
        worksheet.merge_range('D%s:N%s' % (row,row), '', wbf['total'])
        worksheet.merge_range('R%s:X%s' % (row,row), '', wbf['total'])
      
       
        formula_total_qty = '{=subtotal(9,O%s:O%s)}' % (row1, row-1) 
        formula_total_cost = '{=subtotal(9,P%s:P%s)}' % (row1, row-1) 
        formula_total_freight_cost = '{=subtotal(9,Q%s:Q%s)}' % (row1, row-1) 
        
        worksheet.write_formula(row-1,14,formula_total_qty, wbf['total_float'], total_qty)       
        worksheet.write_formula(row-1,15,formula_total_cost, wbf['total_float'], total_cost)  
        worksheet.write_formula(row-1,16,formula_total_freight_cost, wbf['total_float'], total_freight_cost)             
        worksheet.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])  
                   
        workbook.close()

        return fp
    
    def _print_excel_report(self, cr, uid, ids, data, context=None):   
        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")     
        filename = 'Report Stock Unit '+str(date)+'.xlsx'        
        fp = self._query_report_detail(cr, uid, ids, data, context=context)

        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_stock', 'view_wtc_report_stock_unit_wizard')


        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.report.stock.unit.wizard',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }

    def excel_report_daily_mml(self, cr, uid, ids, data, context=None):
        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")     
        filename = 'Report Stock Unit '+str(date)+'.xlsx'        
        data = {
            'product_ids': [],
            'location_ids': [], 
            'branch_ids': [40],
        }
        fp = self._query_report_detail(cr, uid, ids, data, context=context)
        path = '/opt/odoo/TDM/units_daily/'
        file = open(path+filename, 'w+b')
        file.write(fp.getvalue())
        fp.close()

wtc_report_stock_unit()
