import time
import cStringIO
import xlsxwriter
from cStringIO import StringIO
import base64
import tempfile
import os
from openerp import models, fields, api, _
#from openerp.tools.translate import _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from xlsxwriter.utility import xl_rowcol_to_cell
import logging
import re
import pytz
from lxml import etree

class b2b_file_ps_report_wizard(models.TransientModel):
    _name = "b2b.file.ps.report.wizard"

    wbf = {}

    @api.multi
    def _get_default_date(self):
        return datetime.now() - timedelta(hours=7)

    name = fields.Char('Filename', readonly=True)
    state_x = fields.Selection([('choose','choose'),('get','get')], default='choose')
    data_x = fields.Binary('File', readonly=True)
    options = fields.Selection([('report_ps','Report PS')], 'Options',default='report_ps', select=False) 
    status = fields.Selection([
                                ('packed at ahm','Packed at AHM'),
                                ('on intransit','On Intransit'),
                                ('outstanding','Outstanding'),
                                ('received by md','Received by MD'),
                            ],string='Status')
    start_date_time = fields.Date('Start Date', required=True)
    branch_id = fields.Many2one('wtc.branch','Branch', default=40, readonly=True)
    end_date_time = fields.Date('End Date', required=True)

    @api.multi
    def add_workbook_format(self, workbook):      
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

        self.wbf['content_number'] = workbook.add_format({'align': 'center'})
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

    @api.multi
    def excel_report(self):
        self.ensure_one()

        if self['options'] == 'report_ps' :
            return self._print_export_ps()
        

    def _print_export_ps(self):
        start_date = self.start_date_time
        end_date = self.end_date_time
        status = self.status
        query_where = " WHERE 1=1"
        if start_date:
            query_where += " AND ps.tanggal_ps >= '%s'" %str(start_date) 
        if end_date:
            query_where += " AND ps.tanggal_ps <= '%s'" %str(end_date) 
        if status :
            if (status == 'outstanding'):
                query_where += " AND ps.status = 'packed at ahm' OR ps.status = 'on intransit'"
            else:
                query_where += " AND ps.status = '%s'" %str(status) 
        query = """
                SELECT kode_ps
                , kode_sparepart
                , qty_po
                , qty_ps
                , status
                , kode_po_md
                FROM b2b_file_ps ps %s ORDER BY ps.tanggal_ps
                """ % (query_where)
       
        self.env.cr.execute(query)
        ress = self.env.cr.dictfetchall() 

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Report File PS')
        worksheet.set_column('B1:B1', 27)
        worksheet.set_column('C1:C1', 21)
        worksheet.set_column('D1:D1', 27)
        worksheet.set_column('E1:E1', 9)
        worksheet.set_column('F1:F1', 9)
        worksheet.set_column('G1:G1', 20)


        
        date = self._get_default_date()
        date = date.strftime("%d-%m-%Y %H:%M:%S")

        filename = 'Report File PS'+ str(date) +'.xlsx'
        worksheet.write('A1', self.branch_id.name , wbf['company'])
        worksheet.write('A3', 'Report File PS' , wbf['title_doc'])
        worksheet.write('A4', 'Periode : %s s/d %s'%(str(self.start_date_time),str(self.end_date_time)) , wbf['title_doc'])
        row=4
        row +=1
        worksheet.write('A%s' %(row+1), 'No', wbf['header_no'])
        worksheet.write('B%s' %(row+1), 'Kode PO', wbf['header_no'])
        worksheet.write('C%s' %(row+1), 'Kode PS', wbf['header_no'])
        worksheet.write('D%s' %(row+1), 'Kode Sparepart', wbf['header_no'])
        worksheet.write('E%s' %(row+1), 'Qty PO', wbf['header_no'])
        worksheet.write('F%s' %(row+1), 'Qty PS', wbf['header_no'])
        worksheet.write('G%s' %(row+1), 'Status PS', wbf['header_no'])
        row +=2
        
        no = 1
        row1 = row

        for res in ress:
            kode_ps = str(res.get('kode_ps').encode('ascii','ignore').decode('ascii')) if res.get('kode_ps') != None else ''
            kode_sparepart = str(res.get('kode_sparepart').encode('ascii','ignore').decode('ascii')) if res.get('kode_sparepart') != None else ''
            qty_ps = res.get('qty_ps') if res.get('qty_ps') != None else ''
            qty_po = res.get('qty_po') if res.get('qty_po') != None else ''
            status = str(res.get('status').encode('ascii','ignore').decode('ascii')) if res.get('status') != None else ''
            kode_po_md = str(res.get('kode_po_md').encode('ascii','ignore').decode('ascii')) if res.get('kode_po_md') != None else ''
            
            worksheet.write('A%s' % row, no , wbf['content_number'])  
            worksheet.write('B%s' % row, kode_po_md , wbf['content_number'])                    
            worksheet.write('C%s' % row, kode_ps , wbf['content_number'])
            worksheet.write('D%s' % row, kode_sparepart , wbf['content_number'])
            worksheet.write('E%s' % row, qty_po , wbf['content_number'])
            worksheet.write('F%s' % row, qty_ps , wbf['content_number']) 
            worksheet.write('G%s' % row, status , wbf['content_number'])

            no +=1
            row +=1                    
           
        
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write({'state_x':'get', 'data_x':out, 'name': filename})
        fp.close()

        res = self.env.ref('b2b_file.view_b2b_file_ps_report_wizard', False)
       

        form_id = res and res.id or False

        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'b2b.file.ps.report.wizard',
            'res_id': self.ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }

    
      
   

