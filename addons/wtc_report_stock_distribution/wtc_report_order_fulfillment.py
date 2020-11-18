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

class wtc_report_order_fulfillment(osv.osv_memory):
    _name = "wtc.report.order.fulfillment.wizard"
    _description = "Report Order Fulfillment"

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

    _columns = {
        'state_x': fields.selection( ( ('choose','choose'),('get','get'))),
        'data_x': fields.binary('File', readonly=True),
        'name': fields.char('Filename', 100, readonly=True),
        'options': fields.selection([('outstanding','Outstanding')], 'Options', change_default=True, select=True),
        'trx_type': fields.selection([('all','All'),('mutation','Mutation Order'),('sales','Sales Order')], 'Transaction Type'),
        'division': fields.selection([('Unit','Unit'),('Sparepart','Sparepart')], 'Division'),
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'branch_ids': fields.many2many('wtc.branch', 'wtc_report_stock_distribution_branch_rel', 'wtc_report_stock_distribution', 'branch_id', 'Branches', copy=False),
    }

    _defaults = {
        'state_x': lambda *a: 'choose',
        'start_date':datetime.today(),
        'end_date':datetime.today(),
        'options':'outstanding',
        
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
        return self._print_excel_report(cr, uid, ids, data, context=context)
    
    def _print_excel_report(self, cr, uid, ids, data, context=None):        
        start_date = data['start_date']
        end_date = data['end_date']
        branch_ids = data['branch_ids']
        options = data['options']
        trx_type = data['trx_type']
        division = data['division']
       
        tz = '7 hours'
        query_where_so = " "
        query_where_mo = " "
        
        if division :
            query_where_so += " AND so.division = '%s'" % str(division)
            query_where_mo += " AND so.division = '%s'" % str(division)
        if start_date :
            query_where_so += " AND so.date_order >= '%s 00:00:00'" % str(start_date)
            query_where_mo += " AND so.date >= '%s'" % str(start_date)
        if end_date :
            query_where_so += " AND so.date_order <= to_timestamp('%s 23:59:59', 'YYYY-MM-DD HH24:MI:SS') + interval '7 hours'" % (end_date)
            query_where_mo += " AND so.date <= '%s'" % (end_date)
        if branch_ids :
            query_where_so += " AND so.branch_id in %s" % str(tuple(branch_ids)).replace(',)', ')')
            query_where_mo += " AND so.branch_id in %s" % str(tuple(branch_ids)).replace(',)', ')')
        
        query_order = " order by b.code, date, so.name, prod.name_template"
                                       
  
        query_sales = """
                   select b.code
            , so.name
            , so.division
            , so.date_order + interval '7 hours' as date
            , so.state
            , partner.default_code
            , partner.name as partner_name
            , prod.name_template
            , pav.code as color
            , sol.name as description
            , sol.product_uom_qty
            , coalesce(picking.qty,0) as delivered_qty
            , sol.product_uom_qty - coalesce(picking.qty,0) as qty_undelivered
            from sale_order so
            inner join sale_order_line sol on so.id = sol.order_id
            inner join wtc_branch b on b.id = so.branch_id
            left join res_partner partner on partner.id = so.partner_id
            left join product_product prod on prod.id = sol.product_id
            left join product_attribute_value_product_product_rel pavpp ON prod.id = pavpp.prod_id 
            left join product_attribute_value pav ON pavpp.att_id = pav.id 
            left join
            (select pick.transaction_id
            , move.product_id, sum(case spt.code when 'incoming' then -1 else 1 end * move.product_qty) qty
            from stock_picking pick
            inner join stock_move move on pick.id = move.picking_id
            inner join stock_picking_type spt on pick.picking_type_id = spt.id
            where pick.state = 'done'
            and pick.model_id in (select id from ir_model where model = 'sale.order')
            group by pick.transaction_id, move.product_id
            ) picking on picking.transaction_id = so.id and picking.product_id = sol.product_id
            where so.state in ('progress', 'done')
            and (sol.product_uom_qty != picking.qty or picking.qty is null) 
            %s %s
            """ % (query_where_so,query_order)    
            
         
        query_mo = """
                    select b.code
        , so.name
        , so.division
        , so.date as date
        , so.state
        , partner.code as default_code
        , partner.name as partner_name
        , prod.name_template
        , pav.code as color
        , sol.description as description
        , sol.qty
        , coalesce(picking.qty,0) as delivered_qty
        , sol.qty - coalesce(picking.qty,0) as qty_undelivered
        from wtc_mutation_order so
        inner join wtc_mutation_order_line sol on so.id = sol.order_id
        inner join wtc_branch b on b.id = so.branch_id
        left join wtc_branch partner on partner.id = so.branch_requester_id
        left join product_product prod on prod.id = sol.product_id
        left join product_attribute_value_product_product_rel pavpp ON prod.id = pavpp.prod_id 
        left join product_attribute_value pav ON pavpp.att_id = pav.id 
        left join
        (select pick.transaction_id
        , move.product_id, sum(move.product_qty) qty
        from stock_picking pick
        inner join stock_move move on pick.id = move.picking_id
        inner join stock_picking_type spt on pick.picking_type_id = spt.id
        where pick.state = 'done'
        and spt.code = 'interbranch_out'
        and pick.model_id in (select id from ir_model where model = 'wtc.mutation.order')
        group by pick.transaction_id, move.product_id
        ) picking on picking.transaction_id = so.id and picking.product_id = sol.product_id
        where so.state in ('confirm', 'done')
        and sol.qty > 0 and (sol.qty != picking.qty or picking.qty is null) 
            %s %s
            """ % (query_where_mo,query_order)
            
            
        query_all = """
            SELECT * 
           FROM ((%s) UNION (%s)) a
            ORDER BY code, date, name, name_template
            """ % (query_sales, query_mo)
            
        
                 
                
              
        if trx_type == 'sales'  :         
            cr.execute (query_sales)
        elif trx_type == 'mutation'  :    
            cr.execute (query_mo)  
        elif trx_type == 'all'  :    
            cr.execute (query_all) 
        ress = cr.fetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Order Fulfillment')
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
                        
        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        filename = 'Report Order Fulfillment '+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report Order Fulfillment' , wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])
        row=3
        rowsaldo = row
        row+=1
        worksheet.write('A%s' % (row+1), 'No' , wbf['header'])
        worksheet.write('B%s' % (row+1), 'Branch Code' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'No Transaksi' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'Division' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'Tanggal' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'State' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'Kode Dealer' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'Nama Dealer' , wbf['header'])
        worksheet.write('I%s' % (row+1), 'Kode Type' , wbf['header'])
        worksheet.write('J%s' % (row+1), 'Kode Warna' , wbf['header'])
        worksheet.write('K%s' % (row+1), 'Desc Type' , wbf['header'])
        worksheet.write('L%s' % (row+1), 'Qty' , wbf['header'])
        worksheet.write('M%s' % (row+1), 'Qty Delivered' , wbf['header'])
        worksheet.write('N%s' % (row+1), 'Qty Undelivered' , wbf['header'])
        
        
        

                       
        row+=2               
        no = 1     
        row1 = row
        
        total_qty = 0
        total_qty_delivered = 0
        total_qty_undelivered = 0
        
        
        for res in ress:
            
            branch_code = str(res[0].encode('ascii','ignore').decode('ascii')) if res[0] != None else ''
            no_transaksi = str(res[1].encode('ascii','ignore').decode('ascii')) if res[1] != None else ''
            division = str(res[2].encode('ascii','ignore').decode('ascii')) if res[2] != None else ''
            date_order =res[3]
            state = str(res[4].encode('ascii','ignore').decode('ascii')) if res[4] != None else ''
            
            kode_dealer = str(res[5].encode('ascii','ignore').decode('ascii')) if res[5] != None else ''
            nama_dealer = str(res[6].encode('ascii','ignore').decode('ascii')) if res[6] != None else ''
            kode_type = str(res[7].encode('ascii','ignore').decode('ascii')) if res[7] != None else ''
            kode_color = str(res[8].encode('ascii','ignore').decode('ascii')) if res[8] != None else ''
            desc_type =str(res[9].encode('ascii','ignore').decode('ascii')) if res[9] != None else ''
            
            
            qty = res[10]
            qty_delivered =res[11]
            qty_undelivered = res[12]

            worksheet.write('A%s' % row, no , wbf['content_number'])                    
            worksheet.write('B%s' % row, branch_code , wbf['content'])
            worksheet.write('C%s' % row, no_transaksi , wbf['content'])
            worksheet.write('D%s' % row, division , wbf['content'])
            worksheet.write('E%s' % row, date_order , wbf['content_date'])
            worksheet.write('F%s' % row, state , wbf['content'])
            worksheet.write('G%s' % row, kode_dealer , wbf['content'])
            worksheet.write('H%s' % row, nama_dealer , wbf['content']) 
            worksheet.write('I%s' % row, kode_type, wbf['content'])  
            worksheet.write('J%s' % row, kode_color , wbf['content'])
            worksheet.write('K%s' % row, desc_type , wbf['content_number'])
            worksheet.write('L%s' % row, qty , wbf['content_float'])
            worksheet.write('M%s' % row, qty_delivered , wbf['content_float'])
            worksheet.write('N%s' % row, qty_undelivered , wbf['content_float'])
            
            no+=1
            row+=1
            
            total_qty += qty
            total_qty_delivered += qty_delivered
            total_qty_undelivered += qty_undelivered

            
        
        worksheet.autofilter('A5:N%s' % (row))  
        worksheet.freeze_panes(5, 3)
        
        #TOTAL
#         worksheet.merge_range('A%s:C%s' % (row,row), 'Total', wbf['total'])    
#         worksheet.merge_range('D%s:N%s' % (row,row), '', wbf['total'])
       
        
#         formula_total_qty = '{=subtotal(9,V%s:V%s)}' % (row1, row-1) 
#         formula_total_het = '{=subtotal(9,W%s:W%s)}' % (row1, row-1) 
#         formula_total_discount = '{=subtotal(9,X%s:X%s)}' % (row1, row-1) 
#         formula_total_hpp = '{=subtotal(9,Y%s:Y%s)}' % (row1, row-1) 
#         formula_total_dpp = '{=subtotal(9,Z%s:Z%s)}' % (row1, row-1) 
#         formula_total_ppn = '{=subtotal(9,AA%s:AA%s)}' % (row1, row-1) 
#         formula_total_total = '{=subtotal(9,AB%s:AB%s)}' % (row1, row-1) 
#         formula_total_total_gp = '{=subtotal(9,AC%s:AC%s)}' % (row1, row-1) 
# 
# 
#         worksheet.write_formula(row-1,21,formula_total_qty, wbf['total_float'], total_qty)                  
#         worksheet.write_formula(row-1,22,formula_total_het, wbf['total_float'], total_het)
#         worksheet.write_formula(row-1,23,formula_total_discount, wbf['total_float'],total_discount)
#         worksheet.write_formula(row-1,24,formula_total_hpp, wbf['total_float'], total_hpp)
#         worksheet.write_formula(row-1,25,formula_total_dpp, wbf['total_float'], total_dpp) 
#         worksheet.write_formula(row-1,26,formula_total_ppn, wbf['total_float'], total_ppn)
#         worksheet.write_formula(row-1,27,formula_total_total, wbf['total_float'], total_total)
#         worksheet.write_formula(row-1,28,formula_total_total_gp, wbf['total_float'], total_total_gp)
#         worksheet.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])  
                   
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_stock_distribution', 'view_report_order_fulfillment_wizard')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.report.order.fulfillment.wizard',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }

wtc_report_order_fulfillment()
