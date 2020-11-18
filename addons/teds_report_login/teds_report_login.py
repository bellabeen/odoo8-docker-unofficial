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


class teds_report_login (osv.osv_memory):
    _name='teds.report.login'
    _description='Report Login'
    

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
        'branch_id':fields.many2one('wtc.branch','Branch',required=True),
        'resource_ids':fields.many2many('hr.employee','teds_report_login_partner_rel', 'teds_report_login', 'id', 'Employee', copy=False),
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
        if len(data['branch_id']) == 0 :
            data.update({'branch_id': self._get_branch_id(cr, uid, context)})

        self._print_excel_report_login(cr, uid,ids,data,context=context)

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'teds_report_login', 'view_report_login')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.report.login',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }
    
    def _print_excel_report_login(self, cr, uid, ids, data, context=None):        
        start_date = data['start_date']
        end_date = data['end_date']
        branch_id = data['branch_id']
        resource_ids = data['resource_ids']


        tz = '7 hours'
        query_where = ""
        query_saldo_where = ""
        if branch_id :
            query_where += " AND hr_sales.branch_id = '%s' " % (branch_id[0])
        if start_date :
            query_where += " AND users.login_date >= '%s' " % (start_date)
        if end_date :
            query_where += " AND users.login_date <= '%s' "  % (end_date)
        if resource_ids :
            query_where += " AND hr_sales.resource_id in %s " % str(tuple(resource_ids)) 

        

        query="""
                select branch.name as branch,
                users.login as login,
                hr_sales.name_related as nama, 
                job.name as job,
                users.login_date as date
                from res_users as users
                LEFT JOIN resource_resource sales ON users.id = sales.user_id 
                LEFT JOIN hr_employee hr_sales ON sales.id = hr_sales.resource_id
                LEFT JOIN wtc_branch as branch ON branch.id=hr_sales.branch_id
                LEFT JOIN hr_job job ON hr_sales.job_id = job.id
                where '1' %s
            """ %(query_where)
            

        cr.execute (query)
        ress = cr.fetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Report Login') 
        worksheet.set_column('B1:B1', 25)
        worksheet.set_column('C1:C1', 20)
        worksheet.set_column('D1:D1', 20)
        worksheet.set_column('E1:E1', 20)
        worksheet.set_column('F1:F1', 15)

      
        
        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        
        filename = 'Report Login  '+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report Login  '+str(date) , wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])

        row=4
        rowsaldo = row
        row+=1
        worksheet.write('A%s' % (row+1), 'No' , wbf['header']) 
        worksheet.write('B%s' % (row+1), 'Branch' , wbf['header'])      
        worksheet.write('C%s' % (row+1), 'Login' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'Nama' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'Job', wbf['header'])
        worksheet.write('F%s' % (row+1), 'Date', wbf['header'])

       
        row+=2 
        row1 = row        
        no = 1   

        for res in ress:
            branch = res[0]
            login = res[1]
            nama = res[2]
            job = res[3]
            date = res[4]
           
            
            worksheet.write('A%s' % row, no , wbf['content_number'])       
            worksheet.write('B%s' % row, branch , wbf['content'])             
            worksheet.write('C%s' % row, login , wbf['content'])
            worksheet.write('D%s' % row, nama , wbf['content'])
            worksheet.write('E%s' % row, job , wbf['content'])
            worksheet.write('F%s' % row, date , wbf['content_date'])
           
            no+=1
            row+=1
                
        worksheet.autofilter('A6:F%s' % (row))  
        worksheet.freeze_panes(6, 3)

        #TOTAL
        worksheet.merge_range('A%s:F%s' % (row,row), '', wbf['total'])    

        worksheet.write('A%s'%(row+2), 'Create By: %s %s' % (user,str(date)) , wbf['footer'])  

        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

#         return true

teds_report_login()