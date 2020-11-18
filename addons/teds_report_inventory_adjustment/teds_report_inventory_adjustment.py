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


class teds_report_inventory_adjustment (osv.osv_memory):
    _name='teds.report.inventory.adjustment'
    _description='Report Inventory Adjustment'
    


    wbf={}
    
    def _get_default(self,cr,uid,date=False,user=False,context=None):
        if date :
            return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)
        else :
            return self.pool.get('res.users').browse(cr, uid, uid)
    
    def _get_branch_ids(self, cr, uid, context=None):
        branch_ids_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
        branch_ids = [b.id for b in branch_ids_user]
        return branch_ids
    
    _columns={
        'state_x': fields.selection( ( ('choose','choose'),('get','get'))), #xls
        'data_x': fields.binary('File', readonly=True),
        'name': fields.char('Filename', 100, readonly=True), 

 
        'division':fields.selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum')],'Division',required=1),
        'start_date':fields.date('Start Date'),
        'end_date':fields.date('End Date'),
        'branch_ids': fields.many2many('wtc.branch', 'wtc_report_inventory_relation', 'wtc_report_inventory_wizard_id','branch_id', 'Branches', copy=False),
    }
    
    _defaults = {
        'state_x': lambda *a: 'choose',
        'start_date':datetime.today(),
        'end_date':datetime.today(),
        'division' : 'Sparepart'
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
        start_date = data['start_date']
        end_date = data['end_date']
        branch_ids = data['branch_ids']
        division = data['division']
        
 
        # tz = '7 hours'
        # query_where = ""
        # query_saldo_where = ""
        # if branch_ids :
        #     query_where += " AND b.id in %s " % str(tuple(branch_ids)).replace(',)', ')') 
        # if start_date :
        #     query_where += " AND si.confirm_date >= '%s' " % (start_date)
        # if end_date :
        #     query_where += " AND si.confirm_date <= '%s' "  % (end_date)
        # if division == '':
        #     query_where += " "
        # else:
        #     query_where += " and si.division = '%s' " %(division)

        query="""
                select b.code
                ,b.name as branch
                ,si.name
                ,loc.complete_name
                ,si.division
                ,si.state
                ,si.start_date + interval '7 hours' as cut_off_date
                ,si.confirm_date + interval '7 hours' as adjustment_date
                ,sil.product_name
                ,sil.product_code
                ,sil.location_name
                ,sil.theoretical_qty
                ,sil.product_qty
                ,sil.price_unit
                from stock_inventory si
                inner join stock_inventory_line sil on si.id = sil.inventory_id
                left join stock_location loc on si.location_id = loc.id
                left join wtc_branch b on b.id = loc.branch_id
            """ 

        query_where = " WHERE 1=1  "

        tz = '7 hours'

        if branch_ids :
            query_where += " AND b.id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')

        if division :
            query_where += " AND si.division = '%s'" % str(division)

        if start_date :
            query_where += " AND si.confirm_date >= '%s' " % start_date

        if end_date :
            end_date = end_date + ' 23:59:59'
            query_where += " AND si.confirm_date <= to_timestamp('%s', 'YYYY-MM-DD HH24:MI:SS') + interval '%s'" % (end_date,tz)


        query_order = "ORDER BY  si.confirm_date, si.name, sil.id"

        

        cr.execute (query+query_where+query_order)
        ress = cr.fetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('R Inventory Adjustment') 
        worksheet.set_column('B1:B1', 15)
        worksheet.set_column('C1:C1', 25)
        worksheet.set_column('D1:D1', 20)
        worksheet.set_column('E1:E1', 20)
        worksheet.set_column('F1:F1', 15)
        worksheet.set_column('G1:G1', 10)
        worksheet.set_column('H1:H1', 20)
        worksheet.set_column('I1:I1', 10)
        worksheet.set_column('J1:J1', 25)
        worksheet.set_column('K1:K1', 25)    
        worksheet.set_column('L1:L1', 25)    
        worksheet.set_column('M1:M1', 10)    
        worksheet.set_column('N1:N1', 10)    
        worksheet.set_column('O1:O1', 15)    

        
        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        
        user = self._get_default(cr, uid, user=True, context=context).name
        
        filename = 'Report Inventory Adjustment (%s) ' %(division)+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report Inventory Adjustment (%s) '%(division) , wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])

        row=3
        col=0
        worksheet.write(row+1, col, 'No' , wbf['header'])
        col+=1
        worksheet.write(row+1, col, 'Branch Code' , wbf['header'])
        col+=1
        worksheet.write(row+1, col, 'Branch Name' , wbf['header'])
        col+=1
        worksheet.write(row+1, col, 'Name' , wbf['header'])
        col+=1
        worksheet.write(row+1, col, 'Complate name' , wbf['header'])
        col+=1
        worksheet.write(row+1, col, 'Division' , wbf['header'])
        col+=1
        worksheet.write(row+1, col, 'State' , wbf['header'])
        col+=1
        worksheet.write(row+1, col, 'Cut Off Date' , wbf['header'])
        col+=1
        worksheet.write(row+1, col, 'Adjustment Date' , wbf['header'])
        col+=1
        worksheet.write(row+1, col, 'Product Name' , wbf['header'])
        col+=1
        worksheet.write(row+1, col, 'Product Kode' , wbf['header'])
        col+=1
        worksheet.write(row+1, col, 'Location Name' , wbf['header'])
        col+=1
        worksheet.write(row+1, col, 'Theoretical Qty' , wbf['header'])
        col+=1
        worksheet.write(row+1, col, 'Product Qty' , wbf['header'])
        col+=1
        worksheet.write(row+1, col, 'Price Unit' , wbf['header'])
     
         
        row+=2               
        no = 1   

        row1 = row
        # price_unit =0

        for res in ress:
            branch_code=res[0]
            branch_name=res[1]
            name=res[2]
            complete_name=res[3]
            division=res[4]
            state=res[5]
            start_date=res[6]
            confirm_date=res[7]
            product_name=res[8]
            product_code=res[9]
            location_name=res[10]
            theoretical_qty=res[11]
            product_qty=res[12]
            price_unit=res[13]
            
            # price_unit += price_unit
            
            col=0
            worksheet.write(row, col, no , wbf['content_number'])
            col+=1
            worksheet.write(row, col, branch_code , wbf['content'])
            col+=1
            worksheet.write(row, col, branch_name , wbf['content'])
            col+=1
            worksheet.write(row, col, name , wbf['content'])
            col+=1
            worksheet.write(row, col, complete_name , wbf['content'])
            col+=1
            worksheet.write(row, col, division , wbf['content'])
            col+=1
            worksheet.write(row, col, state , wbf['content'])
            col+=1
            worksheet.write(row, col, start_date , wbf['content_date'])
            col+=1
            worksheet.write(row, col, confirm_date, wbf['content'])
            col+=1
            worksheet.write(row, col, product_name , wbf['content'])
            col+=1
            worksheet.write(row, col, product_code , wbf['content'])
            col+=1
            worksheet.write(row, col, location_name , wbf['content'])
            col+=1
            worksheet.write(row, col, theoretical_qty , wbf['content_number'])
            col+=1
            worksheet.write(row, col, product_qty , wbf['content_number'])
            col+=1
            worksheet.write(row, col, price_unit , wbf['content_float'])
           
            
            no+=1
            row+=1
                
        worksheet.autofilter('A5:N%s' % (row))  
        worksheet.freeze_panes(5, 3)

        # worksheet.merge_range('A%s:O%s' % (row+1), 'Total', wbf['total'])    

        worksheet.write('A%s'%(row+2), 'Create By: %s %s' % (user,str(date)) , wbf['footer'])  

        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'teds_report_inventory_adjustment', 'teds_report_inventory_ajustment_view')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.report.inventory.adjustment',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }

#         return true

teds_report_inventory_adjustment()