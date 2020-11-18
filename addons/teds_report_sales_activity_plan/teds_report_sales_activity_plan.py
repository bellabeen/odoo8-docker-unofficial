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


class teds_report_sales_activity_plan(osv.osv_memory):
    _name='teds.report.sales.activity.plan'
    
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
        'start_date':fields.date('Start Date'),
        'end_date':fields.date('End Date'),
        'branch_ids': fields.many2many('wtc.branch', 'wtc_report_sales_activity_plan', 'wtc_report_sales_activity_plan_wizard_id','branch_id', 'Branches', copy=False),
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

        self._print_excel_report_sales_acativity_plan(cr, uid,ids,data,context=context)

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'teds_report_sales_activity_plan', 'teds_report_sales_activity_plan_form')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.report.sales.activity.plan',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }
    
    def _print_excel_report_sales_acativity_plan(self, cr, uid, ids, data, context=None):        
        start_date = data['start_date']
        end_date = data['end_date']
        branch_ids = data['branch_ids']
        
        tz = '7 hours'
        query_where = ""
        query_saldo_where = ""

        if branch_ids :
            query_where += " AND wb.id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        if start_date :
            query_where += " AND slspl.start_date >= '%s' " % (start_date)
        if end_date :
            query_where += " AND slspl.end_date <= '%s' "  % (end_date)

        query="""
            select 
            wb.code,
            wb.name dealer,
            slspl.start_date,
            slspl.end_date,
            kec.name kecamatan,
            kel.name kelurahan,
            tk.category kategori_keramain,
            tk.name titik_keramaian,
            mr.name ring_id,
            tk.dealer_kompetitor dealer_kompetitor,
            tk.profil_konsumen profil_konsumen,
            hr.name_related pic,
            slspl.target_unit target_unit,
            slspl.target_data_cust,
            slspl.estimasi_biaya estimasi_biaya,
            mat.code,
            mat.name
            from sales_plan slsp
            LEFT JOIN sales_plan_line slspl on slsp.id=slspl.sales_activity_id
            LEFT JOIN master_act_type mat on mat.id=slspl.act_type_id
            LEFT JOIN wtc_branch wb on slsp.branch_id=wb.id 
            LEFT JOIN wtc_kecamatan kec on slspl.kecamatan_id=kec.id 
            LEFT JOIN titik_keramaian tk on slspl.titik_keramaian_id=tk.id 
            LEFT JOIN wtc_kelurahan kel on kel.id=tk.kelurahan_id
            LEFT JOIN master_ring mr on slspl.ring_id=mr.id 
            LEFT JOIN hr_employee hr on slspl.pic_id=hr.id
            where 1=1 %s
            """ % (query_where)

        cr.execute (query)
        ress = cr.fetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Sales Activity Plan ')
        col=1 
        worksheet.set_column(col,col, 10)
        col+=1
        worksheet.set_column(col,col, 10)
        col+=1
        worksheet.set_column(col,col, 20)
        col+=1
        worksheet.set_column(col,col, 20)
        col+=1
        worksheet.set_column(col,col, 20)
        col+=1
        worksheet.set_column(col,col, 20)
        col+=1
        worksheet.set_column(col,col, 30)
        col+=1
        worksheet.set_column(col,col, 20)
        col+=1
        worksheet.set_column(col,col, 20)
        col+=1
        worksheet.set_column(col,col, 30)
        col+=1
        worksheet.set_column(col,col, 15)
        col+=1
        worksheet.set_column(col,col, 15)
        col+=1
        worksheet.set_column(col,col, 30)
        col+=1
        worksheet.set_column(col,col, 20)
        col+=1
        worksheet.set_column(col,col, 20)
        col+=1
        worksheet.set_column(col,col, 20)
        col+=1
        worksheet.set_column(col,col, 20)
        col+=1
        worksheet.set_column(col,col, 20)
        
        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        filename = 'Report Sales Activity Plan '+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report Sales Activity Plan', wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])

        row=4
        col=0
        worksheet.write(row+1, col, 'No' , wbf['header'])
        col+=1
        worksheet.write(row+1, col, 'Code', wbf['header'])
        col+=1
        worksheet.write(row+1, col, 'Branch', wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Start Date', wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'End Date', wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Kecamatan' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Kelurahan' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Kategori Titik Keramaian' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Titik Keramaian' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Ring' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Dealer Kompetitor' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Profile Konsumen' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'PIC' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Target Unit' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Target Data Customer' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Estimasi Biaya' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Activity Code' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Activity Type' , wbf['header'])

        row+=2               
        no = 1     
        row1 = row
        
        for res in ress:
            code = res[0]
            dealer = res[1]
            start_date = res[2]
            end_date = res[3]
            kecamatan = res[4]
            kelurahan = res[5]
            kategori_keramain = res[6]
            titik_keramaian = res[7]
            ring_id = res[8]
            dealer_kompetitor = res[9]
            profil_konsumen = res[10]
            pic = res[11]
            target_unit = res[12]
            target_data_cust = res[13]
            estimasi_biaya = res[14]
            act_code = res[15]
            act_type = res[16]


            col=0
            worksheet.write(row, col, no , wbf['content_number'])
            col+=1
            worksheet.write(row, col, code , wbf['content'])
            col+=1
            worksheet.write(row, col, dealer , wbf['content'])
            col+=1
            worksheet.write(row, col, start_date , wbf['content'])
            col+=1
            worksheet.write(row, col, end_date , wbf['content'])
            col+=1
            worksheet.write(row, col, kecamatan , wbf['content'])
            col+=1
            worksheet.write(row, col, kelurahan , wbf['content_date'])
            col+=1
            worksheet.write(row, col, kategori_keramain, wbf['content'])
            col+=1
            worksheet.write(row, col, titik_keramaian, wbf['content'])
            col+=1
            worksheet.write(row, col, ring_id, wbf['content'])
            col+=1
            worksheet.write(row, col, dealer_kompetitor, wbf['content'])
            col+=1
            worksheet.write(row, col, profil_konsumen, wbf['content'])
            col+=1
            worksheet.write(row, col, pic, wbf['content'])
            col+=1
            worksheet.write(row, col, target_unit, wbf['content'])
            col+=1
            worksheet.write(row, col, target_data_cust, wbf['content'])
            col+=1
            worksheet.write(row, col, estimasi_biaya, wbf['content'])
            col+=1
            worksheet.write(row, col, act_code, wbf['content'])
            col+=1
            worksheet.write(row, col, act_type, wbf['content'])

            no+=1
            row+=1
                
        worksheet.autofilter('A6:Q%s' % (row))  
        worksheet.freeze_panes(6, 3)
        worksheet.write('A%s'%(row+2), 'Create By: %s %s' % (user,str(date)) , wbf['footer'])  

        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        # return true

# teds_report_performance_expedisi()