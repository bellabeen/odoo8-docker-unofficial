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


class teds_report_performance_expedisi(osv.osv_memory):
    _name='teds.report.performance.expedisi'
    
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
        'branch_id': fields.many2one('wtc.branch', 'Branch', copy=False),
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
        # if len(data['branch_id']) == 0 :
        #     data.update({'branch_id': self._get_branch_ids(cr, uid, context)})

        self._print_excel_report_performnace_expedisi(cr, uid,ids,data,context=context)

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'teds_report_performance_expedisi', 'teds_report_performance_expedisi_form')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.report.performance.expedisi',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }
    
    def _print_excel_report_performnace_expedisi(self, cr, uid, ids, data, context=None):        
        start_date = data['start_date']
        end_date = data['end_date']
        branch_id = data['branch_id'][0]
        division = data['division']
        
        tz = '7 hours'
        query_where = ""
        query_saldo_where = ""

        if branch_id :
            query_where += " AND pick.branch_id = %s " % (branch_id)
        if start_date :
            query_where += " AND pick.date_done >= '%s' " % (start_date)
        if end_date :
            query_where += " AND pick.date_done <= '%s' "  % (end_date)

        if division == 'Unit':
            code = 'Engine No'
            name = 'Chassis No'
            sl_ps = 'No Shipping List'
            tgl_sl_ps = 'Tgl Shipping List'

            query="""
                select 
                lot.name engineNo,
                lot.chassis_no chassisNo,
                lot.no_ship_list noSL,
                lot.tgl_ship_list,
                pack.name noPacking,
                date(pick.date_done) tglDone,
                exs.name exspedisi,
                age(date(pick.date_done),date(lot.tgl_ship_list)) expedisi_sla
                from stock_picking pick
                LEFT JOIN wtc_stock_packing pack on pick.id=pack.picking_id
                LEFT JOIN wtc_stock_packing_line pack_line on pack.id=pack_line.packing_id
                LEFT JOIN stock_production_lot lot on pack_line.serial_number_id=lot.id
                LEFT JOIN res_partner exs on lot.expedisi_id=exs.id
                where 1=1 %s
                """ % (query_where)
        else:
            code = 'Code Sparepart'
            name = 'Description'
            sl_ps = 'No Packing Sheet'
            tgl_sl_ps = 'Tgl Packing Sheet'

            query="""
                select 
                pp.default_code,
                pp.name_template, 
                pick.origin,
                ps.tanggal_ps,
                pick.name,
                pick.date_done,
                partner.name,
                age(date(pick.date_done),date(ps.tanggal_ps))
                from stock_picking pick 
                LEFT JOIN wtc_stock_packing pack on pick.origin=pack.rel_origin
                LEFT JOIN wtc_stock_packing_line pack_line on pack.id=pack_line.packing_id
                LEFT JOIN b2b_file_ps ps on pick.origin=ps.kode_ps
                LEFT JOIN product_product pp on pack_line.product_id=pp.id 
                LEFT JOIN res_partner partner on pack.expedition_id=partner.id
                where 1=1 and pick.division='Sparepart' and pick.partner_id=24 %s
                """ % (query_where)

        cr.execute (query)
        ress = cr.fetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Performance Expedisi %s'%(division)) 
        worksheet.set_column('B1:B1', 15)
        worksheet.set_column('C1:C1', 20)
        worksheet.set_column('D1:D1', 20)
        worksheet.set_column('E1:E1', 20)
        worksheet.set_column('F1:F1', 25)
        worksheet.set_column('G1:G1', 10)
        worksheet.set_column('H1:H1', 30)
        worksheet.set_column('I1:I1', 10)

        
        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        filename = 'Report Performance Expedisi %s '%(division)+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report Performance Expedisi %s'%(division), wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])

        row=4
        col=0
        worksheet.write(row+1, col, 'No' , wbf['header'])
        col+=1
        worksheet.write(row+1, col, '%s' %(code), wbf['header'])
        col+=1
        worksheet.write(row+1, col, '%s' %(name) , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  '%s' %(sl_ps) , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  '%s' %(tgl_sl_ps) , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'No Packing' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Tgl Packing' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Expedisi' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Perfmance' , wbf['header'])

        row+=2               
        no = 1     
        row1 = row
        
        for res in ress:
            engine=res[0]
            chassis=res[1]
            nosl=res[2]
            tglsl=res[3]
            nopacking=res[4]
            tglpacking=res[5]
            expedisi=res[6]
            performance=res[7]

            col=0
            worksheet.write(row, col, no , wbf['content_number'])
            col+=1
            worksheet.write(row, col, engine , wbf['content'])
            col+=1
            worksheet.write(row, col, chassis , wbf['content'])
            col+=1
            worksheet.write(row, col, nosl , wbf['content'])
            col+=1
            worksheet.write(row, col, tglsl , wbf['content'])
            col+=1
            worksheet.write(row, col, nopacking , wbf['content'])
            col+=1
            worksheet.write(row, col, tglpacking , wbf['content_date'])
            col+=1
            worksheet.write(row, col, expedisi , wbf['content'])
            col+=1
            worksheet.write(row, col, performance, wbf['content'])

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

teds_report_performance_expedisi()