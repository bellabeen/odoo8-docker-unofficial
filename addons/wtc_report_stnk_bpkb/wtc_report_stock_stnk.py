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

    def _print_excel_report_stock_stnk(self, cr, uid, ids, data, context=None):
        
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
                    stnk.name as no_penerimaan,
                    lokasi_stnk.name as lokasi_stnk,
                    lot.tgl_terima_stnk as tgl_terima_stnk,
                    lot.tgl_stnk as tgl_stnk,
                    lot.name as engine,
                    lot.no_notice as notice,
                    lot.no_polisi as nopol,
                    lot.no_stnk as no_stnk,
                    partner.default_code as code_customer,
                    so.name as no_so,
                    partner.mobile as mobile,
                    partner2.name as pemohon_name,
                    age(tgl_terima_stnk)::text as umur,
                    sls.name_related as salesman,
                    lsng.name as finco
                    FROM stock_production_lot as lot             
                    LEFT JOIN res_partner as partner ON partner.id=lot.customer_stnk
                    LEFT JOIN wtc_penerimaan_stnk as stnk ON stnk.id=lot.penerimaan_stnk_id
                    LEFT JOIN wtc_lokasi_stnk as lokasi_stnk ON lokasi_stnk.id=lot.lokasi_stnk_id
                    LEFT JOIN dealer_sale_order as so ON so.id=lot.dealer_sale_order_id
                    LEFT JOIN wtc_branch as branch ON branch.id=lokasi_stnk.branch_id
                    LEFT JOIN res_partner as partner2 ON partner2.id = lot.customer_id 
                    LEFT JOIN res_users u_sls ON u_sls.id = so.user_id
                    LEFT JOIN resource_resource rr ON rr.user_id = u_sls.id
                    LEFT JOIN hr_employee sls ON sls.resource_id = rr.id
                    LEFT JOIN res_partner lsng ON lsng.id = so.finco_id
                    where (penerimaan_stnk_id IS NOT NULL or tgl_terima_stnk is not null)
                    AND (penyerahan_stnk_id IS NULL and tgl_penyerahan_stnk is null)

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
            query_where +=" AND  lokasi_stnk.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        if loc_stnk_ids :
            query_where+=" AND  lot.lokasi_stnk_id  in %s" % str(
                tuple(loc_stnk_ids)).replace(',)', ')')
        query_order=" order by lot.name"

        cr.execute (query+query_where+query_order)
        ress = cr.fetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        
        #WKS 1
        worksheet = workbook.add_worksheet('STOCK STNK')
        worksheet.set_column('B1:B1', 13)
        worksheet.set_column('C1:C1', 21)
        worksheet.set_column('D1:D1', 30)
        worksheet.set_column('E1:E1', 20)
        worksheet.set_column('F1:F1', 20)
        worksheet.set_column('G1:G1', 20)
        worksheet.set_column('H1:H1', 20)
        worksheet.set_column('I1:I1', 20)
        worksheet.set_column('J1:J1', 18)
        worksheet.set_column('K1:K1', 15)
        worksheet.set_column('L1:L1', 20)
        worksheet.set_column('M1:M1', 20)
        worksheet.set_column('N1:N1', 45)
        worksheet.set_column('O1:O1', 45)
        worksheet.set_column('P1:P1', 25)
        worksheet.set_column('Q1:Q1', 28)
                             
        get_date = self._get_default(cr, uid, date=True, context=context)
        date = get_date.strftime("%Y-%m-%d %H:%M:%S")
        date_date = get_date.strftime("%Y-%m-%d")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        filename = 'Report Stock STNK '+str(date)+'.xlsx'  
        
        #WKS 1      
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report Stock STNK' , wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s'%(str(date)) , wbf['company'])
        
        row=3   
        rowsaldo = row
        row+=1
        
        worksheet.write('A%s' % (row+1), 'No' , wbf['header'])
        worksheet.write('B%s' % (row+1), 'Branch Code' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'Branch Name' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'Nama STNK' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'Code Customer' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'No Sale Order' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'No Penerimaan' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'Tanggal Penerimaan' , wbf['header'])
        worksheet.write('I%s' % (row+1), 'Lokasi STNK' , wbf['header'])
        worksheet.write('J%s' % (row+1), 'No Engine' , wbf['header'])
        # worksheet.write('K%s' % (row+1), 'No Notice' , wbf['header'])
        # worksheet.write('L%s' % (row+1), 'No STNK' , wbf['header'])
        worksheet.write('K%s' % (row+1), 'Tgl Jadi STNK' , wbf['header'])
        worksheet.write('L%s' % (row+1), 'No Polisi' , wbf['header'])
        worksheet.write('M%s' % (row+1), 'Mobile' , wbf['header'])
        worksheet.write('N%s' % (row+1), 'Pemohon Name' , wbf['header'])
        worksheet.write('O%s' % (row+1), 'Umur' , wbf['header'])
        worksheet.write('P%s' % (row+1), 'Salesman' , wbf['header'])
        worksheet.write('Q%s' % (row+1), 'Finance Company' , wbf['header'])
            
        row+=2         
        no = 0
        row1 = row
          
        for res in ress:
            branch_code = str(res[0].encode('ascii','ignore').decode('ascii')) if res[0] != None else ''
            branch_name = str(res[1].encode('ascii','ignore').decode('ascii')) if res[1] != None else ''
            nama_stnk = str(res[2].encode('ascii','ignore').decode('ascii')) if res[2] != None else ''
            no_penerimaan = str(res[3].encode('ascii','ignore').decode('ascii')) if res[3] != None else ''
            lokasi_stnk = str(res[4].encode('ascii','ignore').decode('ascii')) if res[4] != None else ''
            tgl_penerimaan = datetime.strptime(res[5][0:22], "%Y-%m-%d") if res[5] else ''
            tgl_stnk = datetime.strptime(res[6][0:22], "%Y-%m-%d") if res[6] else ''
            no_engine = str(res[7].encode('ascii','ignore').decode('ascii')) if res[7] != None else ''
            no_notice = str(res[8].encode('ascii','ignore').decode('ascii')) if res[8] != None else ''
            no_polisi = str(res[9].encode('ascii','ignore').decode('ascii')) if res[9] != None else ''
            no_stnk = str(res[10].encode('ascii','ignore').decode('ascii')) if res[10] != None else ''
            code_customer = str(res[11].encode('ascii','ignore').decode('ascii')) if res[11] != None else ''
            no_so = str(res[12].encode('ascii','ignore').decode('ascii')) if res[12] != None else ''
            mobile = res[13]
            pemohon_name = res[14]
            umur = res[15]
            salesman = res[16]
            finco = res[17]
            
            no += 1  
            worksheet.write('A%s' % row, no , wbf['content_number'])                    
            worksheet.write('B%s' % row, branch_code , wbf['content'])
            worksheet.write('C%s' % row, branch_name , wbf['content'])
            worksheet.write('D%s' % row, nama_stnk , wbf['content'])
            worksheet.write('E%s' % row, code_customer , wbf['content'])
            worksheet.write('F%s' % row, no_so , wbf['content'])
            worksheet.write('G%s' % row, no_penerimaan , wbf['content'])
            worksheet.write('H%s' % row, tgl_penerimaan , wbf['content_date'])
            worksheet.write('I%s' % row, lokasi_stnk , wbf['content'])
            worksheet.write('J%s' % row, no_engine , wbf['content'])
            # worksheet.write('K%s' % row, no_notice , wbf['content'])
            # worksheet.write('L%s' % row, no_stnk , wbf['content']) 
            worksheet.write('K%s' % row, tgl_stnk, wbf['content_date'])  
            worksheet.write('L%s' % row, no_polisi , wbf['content'])       
            worksheet.write('M%s' % row, mobile , wbf['content'])   
            worksheet.write('N%s' % row, pemohon_name , wbf['content'])        
            worksheet.write('O%s' % row, umur , wbf['content'])        
            worksheet.write('P%s' % row, salesman , wbf['content'])        
            worksheet.write('Q%s' % row, finco , wbf['content'])        
            row+=1
            
        worksheet.autofilter('A5:Q%s' % (row))  
        worksheet.freeze_panes(5, 3)
        
        #TOTAL
        worksheet.merge_range('A%s:Q%s' % (row,row), '', wbf['total'])    
        
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