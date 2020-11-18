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

class report_supplier(osv.osv_memory):
   
    _name = "report.supplier"
    _description = "Report Supplier"

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
    
    # def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
    #     if not context: context = {}
    #     res = super(report_stnk_bpkb, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
    #     categ_ids = self.pool.get('product.category').get_child_ids(cr,uid,view_id,'Unit')
    #     branch_ids_user=self.pool.get('res.users').browse(cr,uid,uid).branch_ids
    #     branch_ids=[b.id for b in branch_ids_user]
        
    #     doc = etree.XML(res['arch'])
    #     nodes_stnk_loc = doc.xpath("//field[@name='loc_stnk_ids']")
    #     nodes_bpkb_loc = doc.xpath("//field[@name='loc_bpkb_ids']")       
    #     nodes_branch = doc.xpath("//field[@name='branch_ids']")
    #     for node in nodes_stnk_loc:
    #         node.set('domain', '[("branch_id", "=", '+ str(branch_ids)+')]')
    #     for node in nodes_branch:
    #         node.set('domain', '[("id", "=", '+ str(branch_ids)+')]')
    #     for node in nodes_bpkb_loc:
    #         node.set('domain', '[("branch_id", "=", '+ str(branch_ids)+')]')
    #     res['arch'] = etree.tostring(doc)
    #     return res
        
    _columns = {
        'state_x': fields.selection( ( ('choose','choose'),('get','get'))), #xls
        'data_x': fields.binary('File', readonly=True),
        'name': fields.char('Filename', 100, readonly=True),

        'option': fields.selection([
                                    ('principle','Principle'),
                                    ('biro_jasa','Biro Jasa'),
                                    ('forwarder','Forwarder'),
                                    ('supplier','Supplier'),
                                    ('showroom','Showroom'),
                                    ('ahass','Ahass'),
                                    ('dealer','Dealer'),
                                    ('finance_company','Finance Company')
                                    ], 'Type Supplier', change_default=True, select=True, required=True),
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'), 

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
        
        self.wbf['header_detail_space'] = workbook.add_format({})
        self.wbf['header_detail_space'].set_left()
        self.wbf['header_detail_space'].set_right()
        self.wbf['header_detail_space'].set_top()
        self.wbf['header_detail_space'].set_bottom()
                
        self.wbf['header_detail'] = workbook.add_format({'bg_color': '#E0FFC2'})
        self.wbf['header_detail'].set_left()
        self.wbf['header_detail'].set_right()
        self.wbf['header_detail'].set_top()
        self.wbf['header_detail'].set_bottom()
                        
        return workbook
        

    def excel_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
            
        data = self.read(cr, uid, ids,context=context)[0]

        if data['option']  == 'principle' :
            return self._print_excel_report_principle(cr, uid, ids, data, context=context)

        if data['option'] == 'biro_jasa' :
            return self._print_excel_report_biro_jasa(cr, uid, ids, data, context=context)

        if data['option'] == 'forwarder' :
            return self._print_excel_report_forwarder(cr, uid, ids, data, context=context)

        if data['option'] == 'supplier' :
            return self._print_excel_report_supplier(cr, uid, ids, data, context=context)

        if data['option'] == 'showroom' :
            return self._print_excel_report_showroom(cr, uid,ids,data,context=context)

        if data['option'] == 'ahass' :
            return self._print_excel_report_ahass(cr, uid,ids,data,context=context)
            
        if data['option'] == 'dealer' :
            return self._print_excel_report_dealer(cr, uid,ids,data,context=context)
            
        if data['option'] == 'finance_company' :
            return self._print_excel_report_finance_company(cr, uid,ids,data,context=context)
               
    
    def _print_excel_report_supplier(self, cr, uid, ids, data, context=None):
        
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
        
        where = "WHERE s.supplier = true AND " + where_start_date + " AND "+ where_end_date 
        order = "order by s.name, s.id"

        cr.execute(query + where + order)
        all_lines = cr.fetchall()
        # print "ffdffd",(query + where + order)

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
        filename = 'Report Supplier '+str(date)+'.xlsx'  
        
        #WKS 1      
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report Supplier' , wbf['title_doc'])
        # worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])
         
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
report_supplier()
