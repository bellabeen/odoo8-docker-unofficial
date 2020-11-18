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

class wtc_report_consolidate_invoice(osv.osv_memory):
   
    _inherit = "wtc.report.pembelian.wizard"

    wbf = {}

    def _print_excel_report_consolidate_invoice(self, cr, uid, ids, data, context=None):        
        
        division = data['division']
        branch_ids = data['branch_ids']
        start_date = data['start_date']
        end_date = data['end_date']
        product_ids = data['product_ids']
        partner_ids = data['partner_ids']
        options = data['options']
                        
        query = """
                select b.code
                , ci.name
                , ci.division
                , ci.date
                , partner.default_code as partner_code
                , partner.name as partner_name
                , ai.number
                , ai.date_invoice
                , ai.origin as origin                
                , pick.name as pick_name
                , pick.date_done + interval '7 hours' as date_done
                , prod.name_template as tipe
                , COALESCE(pav.code, '') as warna
                , cil.product_qty
                , cil.price_unit
                , COALESCE(lot.name,'') as engine_no
                , COALESCE(lot.chassis_no,'') as chassis_no
                
                from consolidate_invoice ci
                inner join wtc_branch b on b.id = ci.branch_id
                inner join res_partner partner on partner.id = ci.partner_id
                inner join account_invoice ai on ai.id = ci.invoice_id
                inner join consolidate_invoice_line cil on cil.consolidate_id = ci.id
                inner join product_product prod on prod.id = cil.product_id
                inner join stock_picking pick on pick.id = ci.picking_id
                left join product_attribute_value_product_product_rel pavpp on pavpp.prod_id = prod.id
                left join product_attribute_value pav on pav.id = pavpp.att_id
                left join stock_production_lot lot on lot.id = cil.name
                """
                
        query_where = " where ci.state = 'done' "
        if division :
            query_where += " AND ci.division = '%s'" % str(division)
        if start_date :
            query_where += " AND ci.date >= '%s'" % str(start_date)
        if end_date :
            query_where += " AND ci.date <= '%s'" % str(end_date)
        if branch_ids :
            query_where += " AND ci.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        if product_ids :
            query_where += " AND prod.id in %s" % str(
                tuple(product_ids)).replace(',)', ')')
        if partner_ids :
            query_where += " AND partner.id in %s" % str(
                tuple(partner_ids)).replace(',)', ')')
        query_order = " order by b.code, ai.number, pick.name, partner_name, tipe, warna "
        
        cr.execute (query+query_where+query_order)
        ress = cr.fetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Consolidate Invoice')
        worksheet.set_column('B1:B1', 13)
        worksheet.set_column('C1:C1', 21)
        worksheet.set_column('D1:D1', 9)
        worksheet.set_column('E1:E1', 11)
        worksheet.set_column('F1:F1', 20)
        worksheet.set_column('G1:G1', 21)
        worksheet.set_column('H1:H1', 21)
        worksheet.set_column('I1:I1', 9)
        worksheet.set_column('J1:J1', 21)
        worksheet.set_column('K1:K1', 21)
        worksheet.set_column('L1:L1', 19)
        worksheet.set_column('M1:M1', 17)
        worksheet.set_column('N1:N1', 12)
        worksheet.set_column('O1:O1', 6)
        worksheet.set_column('P1:P1', 20)
        worksheet.set_column('Q1:Q1', 20)
        worksheet.set_column('R1:R1', 20)
                        
        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        filename = 'Report Consolidate Invoice '+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report Consolidate Invoice' , wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date),str(end_date)) , wbf['company'])
        row=4
        rowsaldo = row
        row+=1
        worksheet.merge_range('A%s:A%s' % (row,(row+1)), 'No' , wbf['header_no'])
        worksheet.merge_range('B%s:G%s' % (row,row), 'Consolidate Invoice' , wbf['header'])         
        worksheet.write('B%s' % (row+1), 'Branch Code' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'Number' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'Division' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'Date' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'Partner Code' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'Partner Name' , wbf['header'])
        worksheet.merge_range('H%s:J%s' % (row,row), 'Supplier Invoice' , wbf['header'])                 
        worksheet.write('H%s' % (row+1), 'Number' , wbf['header'])
        worksheet.write('I%s' % (row+1), 'Date' , wbf['header'])
        worksheet.write('J%s' % (row+1), 'Origin' , wbf['header'])        
        worksheet.merge_range('K%s:L%s' % (row,row), 'Picking' , wbf['header']) 
        worksheet.write('K%s' % (row+1), 'Number' , wbf['header'])
        worksheet.write('L%s' % (row+1), 'Date Done' , wbf['header'])
        worksheet.merge_range('M%s:R%s' % (row,row), 'Lines' , wbf['header']) 
        worksheet.write('M%s' % (row+1), 'Type' , wbf['header'])
        worksheet.write('N%s' % (row+1), 'Color' , wbf['header'])
        worksheet.write('O%s' % (row+1), 'Qty' , wbf['header'])
        worksheet.write('P%s' % (row+1), 'Price' , wbf['header'])
        worksheet.write('Q%s' % (row+1), 'Engine No' , wbf['header'])                
        worksheet.write('R%s' % (row+1), 'Chassis No' , wbf['header'])        
        row+=2 
                
        no = 1    
        row1 = row
        total_qty = 0
        
        for res in ress:
            
            branch_code = str(res[0].encode('ascii','ignore').decode('ascii')) if res[0] != None else ''
            ci_number = str(res[1].encode('ascii','ignore').decode('ascii')) if res[1] != None else ''
            division = str(res[2].encode('ascii','ignore').decode('ascii')) if res[2] != None else ''
            date = datetime.strptime(res[3], "%Y-%m-%d").date() if res[3] != None else ''
            partner_code = str(res[4].encode('ascii','ignore').decode('ascii')) if res[4] != None else ''
            partner_name = str(res[5].encode('ascii','ignore').decode('ascii')) if res[5] != None else ''
            inv_number =  str(res[6].encode('ascii','ignore').decode('ascii')) if res[6] != None else ''
            date_invoice = datetime.strptime(res[7], "%Y-%m-%d").date() if res[7] != None else ''
            origin = str(res[8].encode('ascii','ignore').decode('ascii')) if res[8] != None else ''
            pick_name = str(res[9].encode('ascii','ignore').decode('ascii')) if res[9] != None else ''
            pick_date_done = datetime.strptime(res[10][0:19], "%Y-%m-%d %H:%M:%S") if res[10] else ''
            type = str(res[11].encode('ascii','ignore').decode('ascii')) if res[11] != None else ''
            color = res[12] if res[12] else 0
            qty = res[13] if res[13] else 0
            price = res[14] if res[14] else 0
            engine_no = res[15] if res[15] else 0
            chassis_no = res[16] if res[16] else 0
            
            total_qty += qty
                            
            worksheet.write('A%s' % row, no , wbf['content_number'])                    
            worksheet.write('B%s' % row, branch_code , wbf['content'])
            worksheet.write('C%s' % row, ci_number , wbf['content'])
            worksheet.write('D%s' % row, division , wbf['content'])
            worksheet.write('E%s' % row, date , wbf['content_date'])
            worksheet.write('F%s' % row, partner_code , wbf['content'])
            worksheet.write('G%s' % row, partner_name , wbf['content'])
            worksheet.write('H%s' % row, inv_number , wbf['content'])  
            worksheet.write('I%s' % row, date_invoice , wbf['content_date'])
            worksheet.write('J%s' % row, origin , wbf['content'])
            worksheet.write('K%s' % row, pick_name , wbf['content'])
            worksheet.write('L%s' % row, pick_date_done , wbf['content_datetime'])
            worksheet.write('M%s' % row, type , wbf['content'])
            worksheet.write('N%s' % row, color , wbf['content'])
            worksheet.write('O%s' % row, qty , wbf['content_number'])
            worksheet.write('P%s' % row, price , wbf['content_float'])
            worksheet.write('Q%s' % row, engine_no , wbf['content'])
            worksheet.write('R%s' % row, chassis_no , wbf['content'])                               
            no+=1
            row+=1
            
        worksheet.autofilter('A6:R%s' % (row))  
        worksheet.freeze_panes(6, 3)
        
        #TOTAL
        worksheet.merge_range('A%s:C%s' % (row,row), 'Total', wbf['total'])    
        worksheet.merge_range('D%s:N%s' % (row,row), '', wbf['total']) 
        worksheet.merge_range('P%s:R%s' % (row,row), '', wbf['total']) 
                      
        formula_total_qty =  '{=subtotal(9,O%s:O%s)}' % (row1, row-1)
                  
        worksheet.write_formula(row-1,14,formula_total_qty, wbf['total_number'], total_qty)
        worksheet.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])  
                   
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_pembelian', 'view_report_pembelian_wizard')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.report.pembelian.wizard',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }