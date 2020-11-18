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


class teds_tracking_quantity(osv.osv_memory):
    _name='tracking.quantity'
    
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
        'division':fields.selection([('Unit','Unit'),('Sparepart','Sparepart')]),
        'start_date':fields.date('Start Date'),
        'end_date':fields.date('End Date'),
        'branch_ids': fields.many2many('wtc.branch', 'tracking_quantity_rel', 'tracking_quantity_wizard_id','branch_id', 'Branch', copy=False),
    }
    
    _defaults = {
        'state_x': lambda *a: 'choose',
        'start_date':datetime.today(),
        'end_date':datetime.today(),
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

        self._print_excel_report_tracking_quantity(cr, uid,ids,data,context=context)

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'teds_report_tracking_quantity', 'teds_tracking_quantity_form')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tracking.quantity',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }
    
    def _print_excel_report_tracking_quantity(self, cr, uid, ids, data, context=None):        
        start_date = data['start_date']
        end_date = data['end_date']
        branch_ids = data['branch_ids']
        division = data['division']
        
        tz = '7 hours'
        query_where = ""
        query_saldo_where = ""

        if branch_ids :
            query_where += " AND wb.id in %s " % str(tuple(branch_ids)).replace(',)', ')') 
        if start_date :
            query_where += " AND a.date_order >= '%s' " % (start_date)
        if end_date :
            query_where += " AND a.date_order <= '%s' "  % (end_date)
        if division :
            query_where += " AND a.division ='%s' " % (division)


        query="""
            select 
            wb.name branch,
            a.name no_so,
            b.qty_so,
            c.number no_inv,
            c.qty_inv qty_inv,
            string_agg(d.no_sj,', ')no_sj,
            sum(d.qty_sj)qty_sj 
            from sale_order a 
            LEFT JOIN(
            SELECT soh.name,sum(sol.product_uom_qty) qty_so from sale_order soh 
            LEFT JOIN sale_order_line sol on sol.order_id=soh.id
            group by soh.name)b on b."name"=a."name"
            LEFT JOIN (
            select ai.origin,ai.number,sum(ail.quantity)qty_inv from account_invoice ai 
            LEFT JOIN account_invoice_line ail on ail.origin=ai.origin
            group by ai.origin,ai.number) c on a."name"=c.origin
            LEFT JOIN(
            SELECT wsp.rel_origin,wsp.name,wsp."name" no_sj,sum(wspl.quantity)qty_sj from wtc_stock_packing wsp 
            LEFT JOIN wtc_stock_packing_line wspl on wspl.packing_id=wsp.id
            group by wsp.rel_origin,wsp.name)d on a."name"=d.rel_origin
            LEFT JOIN wtc_branch wb on a.branch_id=wb.id
            where 1=1  %s
            group by wb.name,a.name,b.qty_so,c.number,c.qty_inv
            """ % (query_where)
            
        cr.execute (query)
        ress = cr.fetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Tracking Quantity %s'%(division)) 
        worksheet.set_column('B1:B1', 30)
        worksheet.set_column('C1:C1', 20)
        worksheet.set_column('D1:D1', 10)
        worksheet.set_column('E1:E1', 20)
        worksheet.set_column('F1:F1', 10)
        worksheet.set_column('G1:G1', 40)
        worksheet.set_column('H1:H1', 10)
        
        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        filename = 'Report Tracking Quantity %s '%(division)+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report Tracking Quantity %s'%(division), wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])

        row=4
        col=0
        worksheet.write(row+1, col, 'No' , wbf['header'])
        col+=1
        worksheet.write(row+1, col, 'Branch Name', wbf['header'])
        col+=1
        worksheet.write(row+1, col, 'No Sale Order', wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Qty SO', wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'No Invoice', wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Qty Inv' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'No Surat Jalan' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Qty SJ' , wbf['header'])

        row+=2               
        no = 1     
        row1 = row
        
        for res in ress:
            branch=res[0]
            so=res[1]
            qty_so=res[2]
            inv=res[3]
            qty_inv=res[4]
            sj=res[5]
            qty_sj=res[6]

            col=0
            worksheet.write(row, col, no , wbf['content_number'])
            col+=1
            worksheet.write(row, col, branch , wbf['content'])
            col+=1
            worksheet.write(row, col, so , wbf['content'])
            col+=1
            worksheet.write(row, col, qty_so , wbf['content'])
            col+=1
            worksheet.write(row, col, inv , wbf['content'])
            col+=1
            worksheet.write(row, col, qty_inv , wbf['content'])
            col+=1
            worksheet.write(row, col, sj , wbf['content_date'])
            col+=1
            worksheet.write(row, col, qty_sj , wbf['content'])

            no+=1
            row+=1
                
        worksheet.autofilter('A6:H%s' % (row))  
        worksheet.freeze_panes(6, 3)
        worksheet.write('A%s'%(row+2), 'Create By: %s %s' % (user,str(date)) , wbf['footer'])  

        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        # return true

teds_tracking_quantity()