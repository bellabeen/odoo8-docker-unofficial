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

class wtc_report_so_undelivered(osv.osv_memory):
   
    _name = "wtc.report.so.undelivered"
    _description = "SO Undelivered Report"

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
        res = super(wtc_report_so_undelivered, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        branch_ids_user=self.pool.get('res.users').browse(cr,uid,uid).branch_ids
        branch_ids=[b.id for b in branch_ids_user]
        
        doc = etree.XML(res['arch'])      
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
        for node in nodes_branch:
            node.set('domain', '[("id", "in", '+ str(branch_ids)+')]')
        res['arch'] = etree.tostring(doc)
        return res
    
    _columns = {
        'state_x': fields.selection( ( ('choose','choose'),('get','get'))), #xls
        'data_x': fields.binary('File', readonly=True),
        'name': fields.char('Filename', 100, readonly=True), 
        'options': fields.selection([('detail','Detail per Sales')], 'Options', change_default=True, select=True), 
        'division': fields.selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum')], 'Division', change_default=True, select=True),         
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'branch_ids': fields.many2many('wtc.branch', 'wtc_report_so_undelivered_branch_rel', 'wtc_report_so_undelivered',
                                        'branch_id', 'Branch', copy=False),
        'partner_ids': fields.many2many('res.partner', 'wtc_report_so_undelivered_partner_rel', 'wtc_report_so_undelivered',
                                        'partner_id', 'Partner', copy=False),         
    }

    _defaults = {
        'state_x': lambda *a: 'choose',
        'start_date':datetime.today(),
        'end_date':datetime.today(),
        'options':'detail'        
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
            data.update({'branch_ids': self._get_branch_ids(cr, uid, context)})
        return self._print_excel_report(cr, uid, ids, data, context=context)
    
    def _print_excel_report(self, cr, uid, ids, data, context=None):
        
        branch_ids = data['branch_ids']
        partner_ids = data['partner_ids']
        division = data['division']
        start_date = data['start_date']
        end_date = data['end_date']          
        
        query = """
            select b.code
            , so.name
            , so.division
            , so.date_order + interval '7 hours' as date_order
            , so.state
            , partner.default_code
            , partner.name as partner_name
            , prod.name_template
            , sol.name as description
            , sol.product_uom_qty
            , sol.price_unit
            , sol.price_unit / 1.1 as nett_sales
            , sol.discount
            , (sol.price_unit * (1 - coalesce(sol.discount,0) / 100)) / 1.1 as dpp
            , (sol.price_unit * (1 - coalesce(sol.discount,0) / 100)) / 1.1 * sol.product_uom_qty as subtotal
            , sol.force_cogs
            , coalesce(picking.qty,0) as delivered_qty
            , coalesce(picking.delivered_value,0) as delivered_value
            , coalesce(picking.total_hpp,0) as total_hpp
            , sol.product_uom_qty - coalesce(picking.qty,0) as qty_undelivered
            , sol.force_cogs - coalesce(picking.delivered_value,0) as stock_undelivered
            from sale_order so
            inner join sale_order_line sol on so.id = sol.order_id
            inner join wtc_branch b on b.id = so.branch_id
            left join res_partner partner on partner.id = so.partner_id
            left join product_product prod on prod.id = sol.product_id
            left join
            (select pick.transaction_id
            , move.product_id, sum(move.product_qty) qty
            , sum(coalesce(move.product_qty,0) * coalesce(move.undelivered_value,0)) as delivered_value
            , sum(coalesce(move.product_qty,0) * coalesce(move.real_hpp,0)) as total_hpp
            from stock_picking pick
            inner join stock_move move on pick.id = move.picking_id
            where pick.state = 'done'
            and pick.model_id = 348 --sale.order
            group by pick.transaction_id, move.product_id
            ) picking on picking.transaction_id = so.id and picking.product_id = sol.product_id       
            """
            
        query_where = """ 
            where so.state in ('progress', 'done')
            and (sol.product_uom_qty != picking.qty or picking.qty is null) 
            """
                        
        if branch_ids :
            query_where += " and b.id in %s " % str(tuple(branch_ids)).replace(',)', ')')               
        if partner_ids :
            query_where += " and partner.id  in %s " % str(tuple(partner_ids)).replace(',)', ')')
        if division :
            query_where += " and so.division = '%s' " % division                             
        if start_date :
            query_where += " and so.date_order >= '%s' " % start_date
        if end_date :
            query_where += " and so.date_order <= '%s' " % end_date 
                   
        query_order = " order by b.code, so.date_order, so.name, prod.name_template  "
        
        cr.execute (query+query_where+query_order)
        ress = cr.fetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('SO Undelivered')
        worksheet.set_column('B1:B1', 13)
        worksheet.set_column('C1:C1', 21)
        worksheet.set_column('D1:D1', 9)
        worksheet.set_column('E1:E1', 19)
        worksheet.set_column('F1:F1', 8)
        worksheet.set_column('G1:G1', 21)
        worksheet.set_column('H1:H1', 25)
        worksheet.set_column('I1:I1', 12)
        worksheet.set_column('J1:J1', 25)
        worksheet.set_column('K1:K1', 12)
        worksheet.set_column('L1:L1', 20)
        worksheet.set_column('M1:M1', 20)
        worksheet.set_column('N1:N1', 12)
        worksheet.set_column('O1:O1', 20)
        worksheet.set_column('P1:P1', 20)
        worksheet.set_column('Q1:Q1', 20)
        worksheet.set_column('R1:R1', 20)
        worksheet.set_column('S1:S1', 20)
        worksheet.set_column('T1:T1', 20)
        worksheet.set_column('U1:U1', 20)
        worksheet.set_column('V1:V1', 20)
                
        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        filename = 'Report SO Undelivered '+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report SO Undelivered' , wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date),str(end_date)) , wbf['company'])
        row=4
        rowsaldo = row
        row+=1
        worksheet.merge_range('A%s:A%s' % (row,(row+1)), 'No' , wbf['header_no'])
        worksheet.merge_range('B%s:H%s' % (row,row), 'Sales Order' , wbf['header'])        
        worksheet.write('B%s' % (row+1), 'Branch' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'Number' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'Division' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'Date Order' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'State' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'Partner Code' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'Partner Name' , wbf['header'])
        worksheet.merge_range('I%s:Q%s' % (row,row), 'Lines' , wbf['header'])         
        worksheet.write('I%s' % (row+1), 'Product Code' , wbf['header'])
        worksheet.write('J%s' % (row+1), 'Description' , wbf['header'])
        worksheet.write('K%s' % (row+1), 'Product Qty' , wbf['header'])
        worksheet.write('L%s' % (row+1), 'Price Unit' , wbf['header'])
        worksheet.write('M%s' % (row+1), 'Nett Sales' , wbf['header'])
        worksheet.write('N%s' % (row+1), 'Discount' , wbf['header'])
        worksheet.write('O%s' % (row+1), 'DPP' , wbf['header'])                
        worksheet.write('P%s' % (row+1), 'Sub Total' , wbf['header'])
        worksheet.write('Q%s' % (row+1), 'Force COGS' , wbf['header'])
        worksheet.merge_range('R%s:V%s' % (row,row), 'Delivered/Undelivered' , wbf['header'])   
        worksheet.write('R%s' % (row+1), 'Delivered Qty' , wbf['header'])
        worksheet.write('S%s' % (row+1), 'Delivered Value' , wbf['header'])
        worksheet.write('T%s' % (row+1), 'Total HPP' , wbf['header'])
        worksheet.write('U%s' % (row+1), 'Qty Undelivered' , wbf['header'])
        worksheet.write('V%s' % (row+1), 'Stock Undelivered' , wbf['header'])
        row+=2 
                
        no = 1
        total_net_sales =0
        total_subtotal = 0
        total_delivered_qty = 0
        total_total_hpp = 0        
        total_undelivered_qty = 0
        row1 = row
        branch_code = False
        
        user = self.pool.get('res.users').browse(cr, uid, uid)
        tz = pytz.timezone(user.tz) if user.tz else pytz.utc
                
        for res in ress:
#             if branch_code != res[0] :
#                 worksheet.write('B%s' % row, "SUBTOTAL %s" % branch_code , wbf['lr'])
#                 row += 2
#                 no = 1
            
            branch_code = res[0]
            so_number = res[1]
            division = res[2]                
            date_order = datetime.strptime(res[3][0:19], "%Y-%m-%d %H:%M:%S") if res[3] else ''   
            state = res[4]
            partner_code = res[5]
            partner_name = res[6]
            product_code = res[7]
            product_desc = res[8]
            product_qty = res[9]
            price_unit = res[10]
            nett_sales = res[11]
            discount = res[12] / 100 if res[12] else 0
            dpp = res[13]
            subtotal = res[14]
            force_cogs = res[15]
            delivered_qty = res[16]
            delivered_value = res[17]
            total_hpp = res[18]
            qty_undelivered = res[19]
            stock_undelivered = res[20]
            
            total_net_sales += total_net_sales
            total_subtotal += total_subtotal
            total_delivered_qty += delivered_qty
            total_total_hpp += total_hpp       
            total_undelivered_qty += qty_undelivered
                            
            worksheet.write('A%s' % row, no , wbf['content_number'])                    
            worksheet.write('B%s' % row, branch_code , wbf['content'])
            worksheet.write('C%s' % row, so_number , wbf['content'])
            worksheet.write('D%s' % row, division , wbf['content'])
            worksheet.write('E%s' % row, date_order , wbf['content_datetime'])
            worksheet.write('F%s' % row, state , wbf['content'])
            worksheet.write('G%s' % row, partner_code , wbf['content'])
            worksheet.write('H%s' % row, partner_name , wbf['content'])  
            worksheet.write('I%s' % row, product_code , wbf['content'])
            worksheet.write('J%s' % row, product_desc , wbf['content'])
            worksheet.write('K%s' % row, product_qty , wbf['content_number'])
            worksheet.write('L%s' % row, price_unit , wbf['content_float'])
            worksheet.write('M%s' % row, nett_sales , wbf['content_float'])
            worksheet.write('N%s' % row, discount , wbf['content_percent'])
            worksheet.write('O%s' % row, dpp , wbf['content_float'])
            worksheet.write('P%s' % row, subtotal , wbf['content_float'])
            worksheet.write('Q%s' % row, force_cogs , wbf['content_float']) 
            worksheet.write('R%s' % row, delivered_qty , wbf['content_number'])
            worksheet.write('S%s' % row, delivered_value , wbf['content_float'])
            worksheet.write('T%s' % row, total_hpp , wbf['content_float'])
            worksheet.write('U%s' % row, qty_undelivered , wbf['content_number'])
            worksheet.write('V%s' % row, stock_undelivered , wbf['content_float'])
            no+=1
            row+=1
            
        worksheet.autofilter('A6:Q%s' % (row))  
        worksheet.freeze_panes(6, 3)
        
        #TOTAL
        worksheet.merge_range('A%s:C%s' % (row,row), 'Total', wbf['total'])    
        worksheet.merge_range('D%s:L%s' % (row,row), '', wbf['total']) 
        worksheet.merge_range('N%s:O%s' % (row,row), '', wbf['total'])
                      
        formula_nett_sales = '{=subtotal(9,M%s:M%s)}' % (row1, row-1)
        formula_subtotal = '{=subtotal(9,P%s:P%s)}' % (row1, row-1)
        formula_delivered_qty = '{=subtotal(9,R%s:R%s)}' % (row1, row-1)
        formula_total_hpp = '{=subtotal(9,T%s:T%s)}' % (row1, row-1)
        formula_undelivered_qty = '{=subtotal(9,U%s:U%s)}' % (row1, row-1)
                  
        worksheet.write_formula(row-1,12,formula_nett_sales, wbf['total_float'], total_net_sales)
        worksheet.write_formula(row-1,15,formula_subtotal, wbf['total_float'], total_subtotal)
        worksheet.write('Q%s'%(row), '', wbf['total_float']) 
        worksheet.write_formula(row-1,17,formula_delivered_qty, wbf['total_number'], total_delivered_qty)
        worksheet.write('S%s'%(row), '', wbf['total_float']) 
        worksheet.write_formula(row-1,19,formula_total_hpp, wbf['total_float'], total_total_hpp) 
        worksheet.write_formula(row-1,20,formula_undelivered_qty, wbf['total_number'], total_undelivered_qty) 
        worksheet.write('V%s'%(row), '', wbf['total_float'])    
        worksheet.write('A%s'%(row+2), '%s %s' % (str(date),user.name) , wbf['footer'])  
                   
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_so_undelivered', 'view_report_so_undelivered')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.report.so.undelivered',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }

wtc_report_so_undelivered()
