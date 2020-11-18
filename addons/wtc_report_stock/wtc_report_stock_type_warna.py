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

class wtc_report_stock_unit_type_warna(osv.osv_memory):
   
    _inherit = "wtc.report.stock.unit.wizard"

    wbf = {}
    
    
    def _get_picking_type(self,cr,uid,branch_id):
        picking_type_ids = self.pool.get('stock.picking.type').search(cr,uid,[('branch_id','=',branch_id),('code','in',['outgoing','interbranch_out'])])
        if not picking_type_ids:
            return False
        return picking_type_ids
    
    
    def _get_qty_picking(self,cr,uid,branch_id,division,product_id):
        qty_picking_product = 0
        obj_picking = self.pool.get('stock.picking')
        obj_move = self.pool.get('stock.move')
        picking_type = self._get_picking_type(cr, uid, branch_id)
        if picking_type:
            picking_ids = obj_picking.search(cr,uid,
                                            [('branch_id','=',branch_id),
                                             ('division','=',division),
                                             ('picking_type_id','in',picking_type),
                                             ('state','not in',('draft','cancel','done'))
                                             ])
            if picking_ids:
                move_ids = obj_move.search(cr,uid,[('picking_id','in',picking_ids),('product_id','=',product_id)])
                if move_ids:
                    for move in obj_move.browse(cr,uid,move_ids):
                        qty_picking_product+=move.product_uom_qty
        return qty_picking_product
    

    def _print_excel_report_warna(self, cr, uid, ids, data, context=None):        
        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")     
        filename = 'Report Stock Unit '+str(date)+'.xlsx'        
        fp = self._query_report_type_warna(cr, uid, ids, data, context=context)

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
    def _query_report_type_warna(self, cr, uid, ids, data, context=None):
        product_ids = data['product_ids']
        branch_ids = data['branch_ids'] 
        location_ids = data['location_ids']
              
     
        query = """
            select a.product_id as p_id,
            b.branch_id as branch_id,  
            a.product_id  as product_id,  
            c.name as nama_branch,  
            c.code as code_branch, 
            e.name_template as p_kode_product,  
            g.code as p_warna, 
            x.description as description, 
            sum(a.qty) as jumlah  
            From  
            stock_quant a 
            LEFT JOIN stock_location b ON b.id = a.location_id 
            LEFT JOIN wtc_branch c ON c.id = b.branch_id 
            LEFT JOIN stock_production_lot d ON d.id = a.lot_id 
            LEFT JOIN product_product e ON e.id = a.product_id 
            LEFT JOIN product_template x ON x.id = e.product_tmpl_id 
            LEFT JOIN product_attribute_value_product_product_rel f ON f.prod_id = a.product_id 
            LEFT JOIN product_attribute_value g ON g.id = f.att_id 
            LEFT JOIN product_category h ON h.id = x.categ_id 
            where b.usage='internal' and d.ready_for_sale='good'   
            """
       
        
        categ_ids = self.pool.get('product.category').get_child_ids(cr,uid,ids,'Unit')  
        query +="and h.id in %s" % str(
            tuple(categ_ids)).replace(',)', ')')

        query_where=""
        if branch_ids :
            query_where +=" AND  b.branch_id in %s " % str(
                tuple(branch_ids)).replace(',)', ')')
        if product_ids :
            query_where+="AND  a.product_id  in %s" % str(
                tuple(product_ids)).replace(',)', ')')
        if location_ids :
            query_where+="AND  a.location_id  in %s" % str(
                tuple(location_ids)).replace(',)', ')')
                        
        query_order=" GROUP BY b.branch_id,a.product_id,c.name ,c.code,e.name_template,g.code,x.description ORDER by nama_branch,code_branch,p_kode_product,p_warna "
       
        cr.execute (query+query_where+query_order)
        ress = cr.fetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Stock Unit Per Type Warna')
        worksheet.set_column('B1:B1', 13)
        worksheet.set_column('C1:C1', 20)
        worksheet.set_column('D1:D1', 20)
        worksheet.set_column('E1:E1', 20)
        worksheet.set_column('F1:F1', 13)
        worksheet.set_column('G1:G1', 13)
        worksheet.set_column('H1:H1', 20)
        worksheet.set_column('I1:I1', 22)
        worksheet.set_column('J1:J1', 13)
        worksheet.set_column('K1:K1', 15)
        worksheet.set_column('L1:L1', 15)
        worksheet.set_column('M1:M1', 17)
        worksheet.set_column('N1:N1', 9)
        worksheet.set_column('O1:O1', 20)
        worksheet.set_column('P1:P1', 12)
        worksheet.set_column('Q1:Q1', 12)
        worksheet.set_column('R1:R1', 12)
        worksheet.set_column('S1:S1', 12)
        worksheet.set_column('T1:T1', 20)
        worksheet.set_column('U1:U1', 20)
                        
        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        filename = 'Stock Unit Per Type Warna '+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Stock Unit Per Type Warna' , wbf['title_doc'])
 
        row=3
        rowsaldo = row
        row+=1
        worksheet.write('A%s' % (row+1), 'No' , wbf['header'])
        worksheet.write('B%s' % (row+1), 'Cabang' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'Kode Cabang' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'Kode Product' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'Desctiption' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'Warna' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'Jumlah' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'Jumlah Picking' , wbf['header'])
        worksheet.write('I%s' % (row+1), 'STOCK AVB' , wbf['header'])

        row+=2 
                
        no = 1     
        row1 = row
        
        total_jumlah = 0
        total_jumlah_picking = 0
        total_stock_avb = 0
                
        for res in ress:
            
            qty_in_picking = self._get_qty_picking(cr,uid,res[1],'Unit',res[2])
            stock_avb= res[8]-qty_in_picking
    
            
            branch_code = str(res[3].encode('ascii','ignore').decode('ascii')) if res[3] != None else ''
            branch_name = str(res[4].encode('ascii','ignore').decode('ascii')) if res[4] != None else ''
            kode_product = str(res[5].encode('ascii','ignore').decode('ascii')) if res[5] != None else ''
            desc_product = str(res[7].encode('ascii','ignore').decode('ascii')) if res[7] != None else ''
            warna = str(res[6].encode('ascii','ignore').decode('ascii')) if res[6] != None else ''
            jumlah = res[8]
            jumlah_picking=qty_in_picking
            stock_avb= stock_avb
            
            worksheet.write('A%s' % row, no , wbf['content_number'])                    
            worksheet.write('B%s' % row, branch_code , wbf['content'])
            worksheet.write('C%s' % row, branch_name , wbf['content'])
            worksheet.write('D%s' % row, kode_product , wbf['content'])
            worksheet.write('E%s' % row, desc_product , wbf['content'])
            worksheet.write('F%s' % row, warna , wbf['content_date'])
            worksheet.write('G%s' % row, jumlah , wbf['content'])
            worksheet.write('H%s' % row, jumlah_picking , wbf['content']) 
            worksheet.write('I%s' % row, stock_avb , wbf['content'])  
                                  
            no+=1
            row+=1
            
            total_jumlah += jumlah 
            total_jumlah_picking += jumlah_picking 
            total_stock_avb += stock_avb 
                    
        worksheet.autofilter('A5:I%s' % (row))  
        worksheet.freeze_panes(5, 3)
        
        #TOTAL
        worksheet.merge_range('A%s:C%s' % (row,row), 'Total', wbf['total'])  
        worksheet.merge_range('D%s:F%s' % (row,row), 'Total', wbf['total'])    
 
                       
        formula_total_jumlah =  '{=subtotal(9,G%s:G%s)}' % (row1, row-1)
        formula_total_jumlah_picking =  '{=subtotal(9,H%s:H%s)}' % (row1, row-1)
        formula_total_stock_avb =  '{=subtotal(9,I%s:I%s)}' % (row1, row-1)
                  
        worksheet.write_formula(row-1,6,formula_total_jumlah, wbf['total_number'], total_jumlah)
        worksheet.write_formula(row-1,7,formula_total_jumlah_picking, wbf['total_number'], total_jumlah_picking)
        worksheet.write_formula(row-1,8,formula_total_stock_avb, wbf['total_number'], total_stock_avb)
        

        worksheet.write('S%s'%(row), '', wbf['total'])  
        worksheet.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])  
                   
        workbook.close()
        
        return fp