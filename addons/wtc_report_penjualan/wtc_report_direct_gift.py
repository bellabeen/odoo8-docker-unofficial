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
   
    _inherit = "wtc.report.penjualan.wizard"

    def _print_excel_report_direct_gift(self, cr, uid, ids, data, context=None):
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
            select wb.code, wb.name,dso.name no_so,dso.state,dso.date_order,rr.name flp_name,job.name flp_job,
            rps.default_code,rps.name customer,pt.name tipe,pt.description descp,dsol.product_qty unit_qty,
            lot.name engine,lot.chassis_no chassis,subar.name kode_barang,subprod.name_template barang_desc,bb.barang_qty,bb.price_barang
            from dealer_sale_order dso
            LEFT JOIN dealer_sale_order_line dsol on dsol.dealer_sale_order_line_id=dso.id 
            LEFT JOIN dealer_sale_order_line_brgbonus_line bb on bb.dealer_sale_order_line_brgbonus_line_id=dsol.id
            LEFT JOIN wtc_branch wb on dso.branch_id=wb.id
            LEFT JOIN resource_resource rr on dso.user_id=rr.user_id
            LEFT JOIN hr_employee hre on hre.resource_id=rr.id
            LEFT JOIN hr_job job on hre.job_id=job.id
            LEFT JOIN res_partner rps on dso.partner_id=rps.id
            LEFT JOIN product_product pp on dsol.product_id=pp.id
            LEFT JOIN product_template pt on pp.product_tmpl_id=pt.id
            LEFT JOIN stock_production_lot lot on dsol.lot_id=lot.id
            LEFT JOIN wtc_subsidi_barang subar on bb.barang_subsidi_id=subar.id
            LEFT JOIN product_product subprod on bb.product_subsidi_id=subprod.id
            %s %s
            """ %(query_where,query_where_sales)

        cr.execute (query_sales)
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
                                
        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        filename = 'Report Direct Gift By Sale Order '+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report Direct Gift By Sale Order' , wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date),str(end_date)) , wbf['company'])
        row=4
        rowsaldo = row
        row+=1
        worksheet.write('A%s' % (row+1), 'No' , wbf['header'])
        worksheet.write('B%s' % (row+1), 'Branch Code' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'Branch Name' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'No Sale Order' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'State' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'Date' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'Flp Type' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'Flp Name' , wbf['header'])
        worksheet.write('I%s' % (row+1), 'Customer Code' , wbf['header'])
        worksheet.write('J%s' % (row+1), 'Customer Name' , wbf['header'])
        worksheet.write('K%s' % (row+1), 'Model Type' , wbf['header'])
        worksheet.write('L%s' % (row+1), 'Model Descp' , wbf['header'])
        worksheet.write('M%s' % (row+1), 'Unit Qty' , wbf['header'])
        worksheet.write('N%s' % (row+1), 'Engine' , wbf['header'])
        worksheet.write('O%s' % (row+1), 'Chassis' , wbf['header'])
        worksheet.write('P%s' % (row+1), 'Direct Gift Code' , wbf['header'])                
        worksheet.write('Q%s' % (row+1), 'Direct Gift Name' , wbf['header'])
        worksheet.write('R%s' % (row+1), 'Qty' , wbf['header'])
        worksheet.write('S%s' % (row+1), 'Harga' , wbf['header'])

        row+=2               
        no = 1     
        row1 = row
        
        for res in ress:
            
            branch_code =  str(res[0].encode('ascii','ignore').decode('ascii')) if res[0] != None else ''
            branch_name =  str(res[1].encode('ascii','ignore').decode('ascii')) if res[1] != None else ''
            no_so =  str(res[2].encode('ascii','ignore').decode('ascii')) if res[2] != None else ''
            state =  str(res[3].encode('ascii','ignore').decode('ascii')) if res[3] != None else ''
            date =  str(res[4].encode('ascii','ignore').decode('ascii')) if res[4] != None else ''
            flp_type =  str(res[5].encode('ascii','ignore').decode('ascii')) if res[5] != None else ''
            flp_name =  str(res[6].encode('ascii','ignore').decode('ascii')) if res[6] != None else ''
            cust_code =  str(res[7].encode('ascii','ignore').decode('ascii')) if res[7] != None else ''
            cust_name =  str(res[8].encode('ascii','ignore').decode('ascii')) if res[8] != None else ''
            model_type =  str(res[9].encode('ascii','ignore').decode('ascii')) if res[9] != None else ''
            model_descp =  str(res[10].encode('ascii','ignore').decode('ascii')) if res[10] != None else ''
            unit_qty =  res[11] if res[11] != None else ''
            engine =  str(res[12].encode('ascii','ignore').decode('ascii')) if res[12] != None else ''
            chassis =  str(res[13].encode('ascii','ignore').decode('ascii')) if res[13] != None else ''
            gift_code =  str(res[14].encode('ascii','ignore').decode('ascii')) if res[14] != None else ''
            gift_name =  str(res[15].encode('ascii','ignore').decode('ascii')) if res[15] != None else ''
            gift_qty =  res[16] if res[16] != None else ''
            harga =  res[17] if res[17] != None else ''


            worksheet.write('A%s' % row, no , wbf['content_number'])                    
            worksheet.write('B%s' % row, branch_code , wbf['content'])
            worksheet.write('C%s' % row, branch_name , wbf['content'])
            worksheet.write('D%s' % row, no_so , wbf['content'])
            worksheet.write('E%s' % row, state , wbf['content'])
            worksheet.write('F%s' % row, date , wbf['content'])
            worksheet.write('G%s' % row, flp_type , wbf['content_date'])
            worksheet.write('H%s' % row, flp_name , wbf['content']) 
            worksheet.write('I%s' % row, cust_code , wbf['content'])  
            worksheet.write('J%s' % row, cust_name , wbf['content'])
            worksheet.write('K%s' % row, model_type , wbf['content'])
            worksheet.write('L%s' % row, model_descp , wbf['content'])
            worksheet.write('M%s' % row, unit_qty , wbf['content'])
            worksheet.write('N%s' % row, engine , wbf['content'])
            worksheet.write('O%s' % row, chassis , wbf['content'])
            worksheet.write('P%s' % row, gift_code , wbf['content'])
            worksheet.write('Q%s' % row, gift_name , wbf['content'])
            worksheet.write('R%s' % row, gift_qty , wbf['content'])
            worksheet.write('S%s' % row, harga , wbf['content_number']) 
            no+=1
            row+=1

        worksheet.autofilter('A6:S%s' % (row))  
        worksheet.freeze_panes(6, 3)

        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

#         ir_model_data = self.pool.get('ir.model.data')
#         form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_penjualan', 'view_report_penjualan_wizard')

#         form_id = form_res and form_res[1] or False
#         return {
#             'name': _('Download XLS'),
#             'view_type': 'form',
#             'view_mode': 'form',
#             'res_model': 'wtc.report.penjualan.wizard',
#             'res_id': ids[0],
#             'view_id': False,
#             'views': [(form_id, 'form')],
#             'type': 'ir.actions.act_window',
#             'target': 'current'
#         }

# wtc_report_penjualan()



