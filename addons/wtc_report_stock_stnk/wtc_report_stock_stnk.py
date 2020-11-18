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

class wtc_report_stock_stnk(osv.osv_memory):
   
    _name = "wtc.report.stock.stnk.wizard"
    _description = "Report Stock STNK"

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
        res = super(wtc_report_stock_stnk, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        branch_ids_user=self.pool.get('res.users').browse(cr,uid,uid).branch_ids
        branch_ids=[b.id for b in branch_ids_user]
        
        doc = etree.XML(res['arch'])
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
        nodes_location = doc.xpath("//field[@name='location_ids']")
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
        'branch_ids': fields.many2many('wtc.branch', 'wtc_report_stock_stnk_rel', 'wtc_report_stock_stnk_wizard_id',
            'branch_id', 'Branches', copy=False),
        'lokasi_stnk_ids': fields.many2many('wtc.lokasi.stnk', 'wtc_report_stock_stnk_location_stnk_rel', 'wtc_report_stock_stnk_wizard_id',
                                        'lokasi_stnk_id', 'Location', copy=False),
    
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
        return self._print_excel_report(cr, uid, ids, data, context=context)
    
    def _print_excel_report(self, cr, uid, ids, data, context=None):        
        
       
        branch_ids = data['branch_ids']
        lokasi_stnk_ids = data['lokasi_stnk_ids']
    
              
        tz = '7 hours'
        
        query_where = ""
        query_where_cancel = ""
        if branch_ids :
            query_where += " AND a.branch_id in %s" % str(tuple(branch_ids)).replace(',)', ')') 
        if lokasi_stnk_ids :
            query_where += " AND a.lokasi_stnk_id in %s" % str(tuple(lokasi_stnk_ids)).replace(',)', ')') 
        
              
        query_order = "order by a.name"

        query_sales = ""
        query_cancel = ""

       
        query = """
           SELECT 
            c.code,
            c.name as branc_code,
            a.name as no_penerimaan,
            a.tgl_terima,
            d.name as no_engine,
            b.no_notice,
            b.no_stnk,
            b.tgl_notice,
            b.no_polisi,
            e.name as customer_stnk
            
            from wtc_penerimaan_stnk as a
            LEFT JOIN wtc_penerimaan_stnk_line as b
            ON a.id=b.penerimaan_notice_id
            LEFT JOIN wtc_branch as c
            ON a.branch_id=c.id
            LEFT JOIN stock_production_lot as d
            ON d.id=b.name
            LEFT JOIN res_partner as e
            ON e.id=d.customer_stnk
            where a.state='posted'
            %s limit 100
            """ % (query_where) 
        
        cr.execute (query)
        ress = cr.fetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('STOCK STNK')
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
                        
        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        filename = 'Report Stock STNK '+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report Stock STNK' , wbf['title_doc'])
#         worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])
        row=3
        rowsaldo = row
        row+=1
        worksheet.write('A%s' % (row+1), 'No' , wbf['header'])
        worksheet.write('B%s' % (row+1), 'Branch Code' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'Branch Name' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'Nama STNK' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'No Penerimaan' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'Tanggal Penerimaan' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'No Engine' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'No Notice' , wbf['header'])
        worksheet.write('I%s' % (row+1), 'No STNK' , wbf['header'])
        worksheet.write('J%s' % (row+1), 'TGL JTP STNK' , wbf['header'])
        worksheet.write('K%s' % (row+1), 'No Polisi' , wbf['header'])
        row+=2               
        no = 1     
        row1 = row
        
      
        
        for res in ress:
            
            branch_code = str(res[0].encode('ascii','ignore').decode('ascii')) if res[0] != None else ''
            branch_name = str(res[1].encode('ascii','ignore').decode('ascii')) if res[1] != None else ''
            no_penerimaan = str(res[2].encode('ascii','ignore').decode('ascii')) if res[2] != None else ''
            tgl_penerimaan = datetime.strptime(res[3][0:22], "%Y-%m-%d") if res[3] else ''
            no_engine = str(res[4].encode('ascii','ignore').decode('ascii')) if res[4] != None else ''
            no_notice = str(res[5].encode('ascii','ignore').decode('ascii')) if res[5] != None else ''
            no_stnk = str(res[6].encode('ascii','ignore').decode('ascii')) if res[6] != None else ''
            tgl_jtp_notice = datetime.strptime(res[7][0:22], "%Y-%m-%d") if res[7] else ''
            no_polisi = str(res[8].encode('ascii','ignore').decode('ascii')) if res[8] != None else ''
            nama_stnk = str(res[9].encode('ascii','ignore').decode('ascii')) if res[9] != None else ''
           
            worksheet.write('A%s' % row, no , wbf['content_number'])                    
            worksheet.write('B%s' % row, branch_code , wbf['content'])
            worksheet.write('C%s' % row, branch_name , wbf['content'])
            worksheet.write('D%s' % row, nama_stnk , wbf['content'])
            worksheet.write('E%s' % row, no_penerimaan , wbf['content'])
            worksheet.write('F%s' % row, tgl_penerimaan , wbf['content_datetime_12_hr'])
            worksheet.write('G%s' % row, no_engine , wbf['content'])
            worksheet.write('H%s' % row, no_notice , wbf['content'])
            worksheet.write('I%s' % row, no_stnk , wbf['content']) 
            worksheet.write('J%s' % row, tgl_jtp_notice, wbf['content_datetime_12_hr'])  
            worksheet.write('K%s' % row, no_polisi , wbf['content'])
            no+=1
            row+=1
            
    
        worksheet.autofilter('A5:K%s' % (row))  
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
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_stock_stnk', 'view_wtc_report_stock_stnk_wizard')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.report.stock.stnk.wizard',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }

wtc_report_stock_stnk()
