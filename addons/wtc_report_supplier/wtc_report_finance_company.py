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

class wtc_report_finance_company(osv.osv_memory):
   
    _inherit = "report.supplier"

    wbf = {}

    def _print_excel_report_finance_company(self, cr, uid, ids, data, context=None):
        
        start_date = data['start_date']
        end_date = data['end_date']
      
        
        where_start_date = " 1=1 "
        if start_date :
            where_start_date = " s.tgl_kukuh >= '%s'" % str(start_date)
            
        where_end_date = " 1=1 "
        if end_date :
            where_end_date = " s.tgl_kukuh<= '%s'" % str(end_date)

      
        query = """
            select 
            s.name as nama_supplier,
            s.street as street,
            c.name as city,
            co.name as state,
            s.kecamatan,
            s.kelurahan,
            s.alamat_pkp as alamat_pkp,
            s.tgl_kukuh as tgl_kukuh
            from res_partner s
            left join wtc_city c ON c.id = s.city_id
            left join res_country_state co ON co.id = s.state_id
        
            """
        
        where = "WHERE s.finance_company = true AND " + where_start_date + " AND "+ where_end_date 
        order = "order by s.name, s.id"

        cr.execute(query + where + order)
        all_lines = cr.fetchall()
        # print ">>>>>>>>>>>>>>>>>>",(query + where + order)

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        
        #WKS 1
        worksheet = workbook.add_worksheet('Laporan Supplier')
        worksheet.set_column('B1:B1', 20)
        worksheet.set_column('C1:C1', 20)
        worksheet.set_column('D1:D1', 20)
        worksheet.set_column('E1:E1', 20)
        worksheet.set_column('F1:F1', 20)
        worksheet.set_column('G1:G1', 20)
        worksheet.set_column('H1:H1', 20)
        worksheet.set_column('I1:I1', 20)
       
                             
        get_date = self._get_default(cr, uid, date=True, context=context)
        date = get_date.strftime("%Y-%m-%d %H:%M:%S")
        date_date = get_date.strftime("%Y-%m-%d")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        filename = 'Report Supplier Finence Company '+str(date)+'.xlsx'  
        
        #WKS 1      
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report Supplier' , wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])
         
        row=3   
        rowsaldo = row
        row+=1
        
        worksheet.write('A%s' % (row+1), 'No' , wbf['header_no'])
        worksheet.write('B%s' % (row+1), 'Nama' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'Alamat' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'Prov' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'Kota' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'Kecamatan' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'Kelurahan' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'Alamat PKP' , wbf['header'])
        worksheet.write('I%s' % (row+1), 'Tanggal PKP' , wbf['header'])
       
        row+=2         
        no = 0
        row1 = row
          
        for res in all_lines:
            nama_supplier = str(res[0].encode('ascii','ignore').decode('ascii')) if res[0] != None else ''
            street = str(res[1].encode('ascii','ignore').decode('ascii')) if res[1] != None else ''
            city = str(res[2].encode('ascii','ignore').decode('ascii')) if res[2] != None else ''
            state = str(res[3].encode('ascii','ignore').decode('ascii')) if res[3] != None else ''                        
            kecamatan = str(res[4].encode('ascii','ignore').decode('ascii')) if res[4] != None else ''
            kelurahan = str(res[5].encode('ascii','ignore').decode('ascii')) if res[5] != None else ''
            alamat_pkp = str(res[6].encode('ascii','ignore').decode('ascii')) if res[6] != None else ''
            tgl_kukuh = str(res[7].encode('ascii','ignore').decode('ascii')) if res[7] != None else ''
           
            no += 1         
          
            worksheet.write('A%s' % row, no , wbf['content_number'])                    
            worksheet.write('B%s' % row, nama_supplier , wbf['content'])
            worksheet.write('C%s' % row, street , wbf['content'])
            worksheet.write('D%s' % row, city , wbf['content'])
            worksheet.write('E%s' % row, state , wbf['content'])
            worksheet.write('F%s' % row, kecamatan , wbf['content'])
            worksheet.write('G%s' % row, kelurahan , wbf['content'])
            worksheet.write('H%s' % row, alamat_pkp , wbf['content'])  
            worksheet.write('I%s' % row, tgl_kukuh, wbf['content'])
          
          
            row+=1
            
        # worksheet.autofilter('A5:BF%s' % (row))  
        worksheet.freeze_panes(5, 3)
        
        #TOTAL      
        worksheet.merge_range('A%s:I%s' % (row,row), '', wbf['total'])            
        worksheet.write('A%s'%(row+1), '%s %s' % (str(date),user) , wbf['footer'])  
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_supplier', 'view_report_supplier')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'report.supplier',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }
