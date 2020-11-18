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

class wtc_report_stnk_bpkb(osv.osv_memory):
   
    _inherit = "report.stnk.bpkb"

    wbf = {}

    def _print_excel_report_stock_bpkb(self, cr, uid, ids, data, context=None):
        
        branch_ids = data['branch_ids']
        partner_ids = data['partner_ids']
        loc_stnk_ids = data['loc_stnk_ids']
        loc_bpkb_ids = data['loc_bpkb_ids']
        lot_ids = data['lot_ids']
        birojasa_ids = data['birojasa_ids']
        finco_ids = data['finco_ids']
            
        query = """
                    SELECT 
                    branch.code,
                    branch.name as branch_name,
                    partner.name as customer_stnk,
                    bpkb.name as no_penerimaan,
                    lokasi_bpkb.name as lokasi_bpkb,
                    lot.tgl_terima_bpkb as tgl_terima_bpkb,
                    lot.tgl_bpkb as tgl_bpkb,
                    lot.name as engine,
                    lot.no_bpkb as no_bpkb,
                    invoice.number as invoice_bbn, 
                    partner.mobile as mobile,
                    finco.name as finco_name,
                    so.user_id as sales_id,
                    resource.name as sales,
                    partner2.name as pemohon_name,
                    age(tgl_terima_bpkb)::text as umur,
                    EXTRACT(day from now() - lot.tgl_terima_bpkb) as over_due
                    from stock_production_lot as lot

                    LEFT JOIN res_partner finco ON finco.id =lot.finco_id 
                    LEFT JOIN account_invoice invoice ON invoice.id = lot.invoice_bbn
                    LEFT JOIN dealer_sale_order so ON so.id = lot.dealer_sale_order_id                               
                    LEFT JOIN resource_resource resource ON so.user_id = resource.user_id
                    
                    LEFT JOIN res_partner as partner ON partner.id=lot.customer_stnk
                    LEFT JOIN wtc_penerimaan_bpkb as bpkb ON bpkb.id=lot.penerimaan_bpkb_id
                    LEFT JOIN wtc_lokasi_bpkb as lokasi_bpkb ON lokasi_bpkb.id=lot.lokasi_bpkb_id
                    LEFT JOIN wtc_branch as branch ON branch.id=lokasi_bpkb.branch_id

                    LEFT JOIN res_partner as partner2 ON partner2.id=lot.customer_id

                    where (penerimaan_bpkb_id IS NOT NULL or  tgl_terima_bpkb is not null)
                    AND (penyerahan_bpkb_id IS NULL and tgl_penyerahan_bpkb is null)

            """
             
        
        query_where = " "
        if lot_ids :
            query_where +=" AND  lot.id in %s" % str(
                tuple(lot_ids)).replace(',)', ')')   
        if birojasa_ids :
            query_where+=" AND  lot.biro_jasa_id  in %s" % str(
                tuple(birojasa_ids)).replace(',)', ')')    
        if finco_ids :
            query_where+=" AND  lot.finco_id  in %s" % str(
                tuple(finco_ids)).replace(',)', ')')            
        if branch_ids :
            query_where +=" AND  lokasi_bpkb.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        if loc_bpkb_ids :
            query_where+=" AND  lot.lokasi_bpkb_id  in %s" % str(
                tuple(loc_bpkb_ids)).replace(',)', ')')
        query_order=" order by lot.name"
        cr.execute (query+query_where+query_order)
        ress = cr.fetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        
        #WKS 1
        worksheet = workbook.add_worksheet('STOCK BPKB')
        worksheet.set_column('B1:B1', 13)
        worksheet.set_column('C1:C1', 21)
        worksheet.set_column('D1:D1', 25)
        worksheet.set_column('E1:E1', 25)
        worksheet.set_column('F1:F1', 20)
        worksheet.set_column('G1:G1', 15)
        worksheet.set_column('H1:H1', 20)
        worksheet.set_column('I1:I1', 25)
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
                             
        get_date = self._get_default(cr, uid, date=True, context=context)
        date = get_date.strftime("%Y-%m-%d %H:%M:%S")
        date_date = get_date.strftime("%Y-%m-%d")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        filename = 'Report Stock BPKB '+str(date)+'.xlsx'  
        
        #WKS 1      
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report Stock BPKB' , wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s'%(str(date)) , wbf['company'])
        
        row=3   
        rowsaldo = row
        row+=1
        
        worksheet.write('A%s' % (row+1), 'No' , wbf['header'])
        worksheet.write('B%s' % (row+1), 'Branch Code' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'Branch Name' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'Nama STNK' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'Nama Pemohon' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'No Penerimaan' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'Tanggal Penerimaan' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'Lokasi BPKB' , wbf['header'])
        worksheet.write('I%s' % (row+1), 'No Engine' , wbf['header'])
        worksheet.write('J%s' % (row+1), 'No BPKB' , wbf['header'])
        worksheet.write('K%s' % (row+1), 'TGL Jadi BPKB' , wbf['header'])
        worksheet.write('L%s' % (row+1), 'Finance Company' , wbf['header'])
        worksheet.write('M%s' % (row+1), 'No Invoice' , wbf['header'])
        worksheet.write('N%s' % (row+1), 'No Telp Konsumen' , wbf['header'])
        worksheet.write('O%s' % (row+1), 'Nama Sales' , wbf['header'])
        worksheet.write('P%s' % (row+1), 'Pemohon Name' , wbf['header'])
        worksheet.write('Q%s' % (row+1), 'Umur' , wbf['header'])
        worksheet.write('R%s' % (row+1), 'Over Due (Hari)' , wbf['header'])

                                            
        row+=2         
        no = 0
        row1 = row
          
        for res in ress:
            branch_code = str(res[0].encode('ascii','ignore').decode('ascii')) if res[0] != None else ''
            branch_name = str(res[1].encode('ascii','ignore').decode('ascii')) if res[1] != None else ''
            nama_stnk = str(res[2].encode('ascii','ignore').decode('ascii')) if res[2] != None else ''
            nama_pemohon = str(res[14].encode('ascii','ignore').decode('ascii')) if res[2] != None else ''
            no_penerimaan = str(res[3].encode('ascii','ignore').decode('ascii')) if res[3] != None else ''
            lokasi_bpkb = str(res[4].encode('ascii','ignore').decode('ascii')) if res[4] != None else ''
            tgl_penerimaan = datetime.strptime(res[5][0:22], "%Y-%m-%d") if res[5] else ''
            tgl_bpkb = datetime.strptime(res[6][0:22], "%Y-%m-%d") if res[6] else ''
            no_engine = str(res[7].encode('ascii','ignore').decode('ascii')) if res[7] != None else ''
            no_bpkb = str(res[8].encode('ascii','ignore').decode('ascii')) if res[8] != None else ''
            invoice_bbn = res[9]
            mobile = res[10]
            finco_name = res[11]
            sales_id = res[12]
            sales = res[13]
            pemohon_name = res[14]
            umur = res[15]
            over_due = "-"
            if res[16] and res[16] > 360:
                over_due =  res[16] - 360

            no += 1  
            worksheet.write('A%s' % row, no , wbf['content_number'])                    
            worksheet.write('B%s' % row, branch_code , wbf['content'])
            worksheet.write('C%s' % row, branch_name , wbf['content'])
            worksheet.write('D%s' % row, nama_stnk , wbf['content'])
            worksheet.write('E%s' % row, nama_pemohon , wbf['content'])
            worksheet.write('F%s' % row, no_penerimaan , wbf['content'])
            worksheet.write('G%s' % row, tgl_penerimaan , wbf['content_date'])
            worksheet.write('H%s' % row, lokasi_bpkb , wbf['content'])
            worksheet.write('I%s' % row, no_engine , wbf['content'])
            worksheet.write('J%s' % row, no_bpkb , wbf['content'])
            worksheet.write('K%s' % row, tgl_bpkb , wbf['content_date']) 
            worksheet.write('L%s' % row, finco_name , wbf['content']) 
            worksheet.write('M%s' % row, invoice_bbn, wbf['content']) 
            worksheet.write('N%s' % row, mobile , wbf['content']) 
            worksheet.write('O%s' % row, sales , wbf['content']) 
            worksheet.write('P%s' % row, pemohon_name , wbf['content']) 
            worksheet.write('Q%s' % row, umur , wbf['content']) 
            worksheet.write('R%s' % row, over_due , wbf['content']) 

     
            row+=1
            
        worksheet.autofilter('A5:Q%s' % (row))  
        worksheet.freeze_panes(5, 3)
        
        #TOTAL
        worksheet.merge_range('A%s:C%s' % (row,row), '', wbf['total'])    
        worksheet.merge_range('D%s:J%s' % (row,row), '', wbf['total'])
        worksheet.merge_range('Z%s:AD%s' % (row,row), '', wbf['total']) 

        worksheet.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])  
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_stnk_bpkb', 'view_report_stnk_bpkb')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'report.stnk.bpkb',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }