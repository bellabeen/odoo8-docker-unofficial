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


class wtc_report_employee(osv.osv_memory):
    _name='wtc.report.employee'
    
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
        'status':fields.selection([('all','All'),('aktif','Aktif'),('non_aktif','Non Aktif')]),
        'start_date':fields.date('Start Date'),
        'end_date':fields.date('End Date'),
        'branch_ids': fields.many2many('wtc.branch', 'wtc_report_employee_rel', 'wtc_report_employee_wizard_id','branch_id', 'Branch', copy=False),
        'job_ids': fields.many2many('hr.job', 'wtc_report_employee_jobs_rel', 'wtc_report_employee_id','job_id', 'Job Title', copy=False),
    }
    
    _defaults = {
        'state_x': lambda *a: 'choose',
        'start_date':datetime.today(),
        'end_date':datetime.today(),
    }
    
    def _onchange_status(self,cr,uid,ids,status):
        values= {}
        if status != 'non_aktif':
            values['start_date'] = False
            values['end_date'] = False
        return {'value':values}
        


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

        self._print_excel_report_employee(cr, uid,ids,data,context=context)

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_employee', 'wtc_report_employee_view')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.report.employee',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }
    
    def _print_excel_report_employee(self, cr, uid, ids, data, context=None):        
        start_date = data['start_date']
        end_date = data['end_date']
        branch_ids = data['branch_ids']
        status = data['status']
        job_ids = data['job_ids']

        tz = '7 hours'
        where = " AND 1=1 "
        if status == 'aktif' :
            where += " AND employee.tgl_keluar IS NULL"
        elif status == 'non_aktif' :
            where += " AND employee.tgl_keluar >= '%s'" %str(start_date) + " AND employee.tgl_keluar <= '%s'" %str(end_date) + " AND employee.tgl_keluar IS NOT NULL" 

        # if status == 'active' :
        #     where_status = " and employee.tgl_masuk >= '%s'" % str(start_date) + " and (employee.tgl_keluar <= '%s'" % str(end_date) + " or employee.tgl_keluar is null)"
        # elif status == 'non_active' :
        #     where_status = "and employee.tgl_keluar >= '%s'" % str(start_date) + " and (employee.tgl_keluar <= '%s'" % str(end_date) + " or employee.tgl_keluar is null)"
        # where_branch_ids = " and 1=1 "
        if branch_ids :
            where += " AND b.id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        # where_job_ids = " and 1=1 "
        if job_ids :
            where += " AND job.id in %s" % str(
                tuple(job_ids)).replace(',)', ')')
        
        query="""
                SELECT 
                b.code as branch_code, 
                b.name as branch_name, 
                area.code as area_code, 
                area.description as area_desc, 
                employee.nip as employee_nip,
                resource.name as resource_name, 
                employee.street as employee_street, 
                employee.street2 as employee_street2, 
                employee.rt as rt, 
                employee.rw as rw, 
                province.name as province, 
                city.name as city, 
                employee.kecamatan as kecamatan, 
                employee.kelurahan as kelurahan,
                job.name as job_name, 
                groups.name as group_name, 
                employee.tgl_masuk as tgl_masuk, 
                employee.tgl_keluar as tgl_keluar, 
                create_partner.name as created_by, 
                employee.create_date as created_date, 
                update_partner.name as updated_by, 
                employee.write_date as updated_date,
                users."login", 
                users.login_date, 
                users.active as login_active,
                employee.bank as bank,
                employee.no_rekening as no_rekening
                FROM hr_employee employee INNER JOIN resource_resource resource ON employee.resource_id = resource.id
                LEFT JOIN res_users users ON resource.user_id = users.id
                LEFT JOIN wtc_branch b ON employee.branch_id = b.id
                LEFT JOIN wtc_area area ON employee.area_id = area.id
                LEFT JOIN res_country_state province ON employee.state_id = province.id
                LEFT JOIN wtc_city city ON employee.city_id = city.id
                LEFT JOIN hr_job job ON employee.job_id = job.id
                LEFT JOIN res_groups groups ON job.group_id = groups.id
                LEFT JOIN res_users create_by ON employee.create_uid = create_by.id
                LEFT JOIN res_partner create_partner ON create_by.partner_id = create_partner.id
                LEFT JOIN res_users update_by ON employee.write_uid = update_by.id
                LEFT JOIN res_partner update_partner ON update_by.partner_id = update_partner.id
                WHERE employee.nip is not null %s
                
                ORDER BY b.code, job.name, employee.nip
            """ %(where)
        cr.execute (query)
        ress = cr.fetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Pricelist Audit Trail') 
        worksheet.set_column('B1:B1', 15)
        worksheet.set_column('C1:C1', 30)
        worksheet.set_column('D1:D1', 40)
        worksheet.set_column('E1:E1', 20)
        worksheet.set_column('F1:F1', 20)
        worksheet.set_column('G1:G1', 20)
        worksheet.set_column('H1:H1', 20)
        worksheet.set_column('I1:I1', 20)
        worksheet.set_column('J1:J1', 20)
        worksheet.set_column('K1:K1', 15)    
        worksheet.set_column('L1:L1', 15)    
        worksheet.set_column('M1:M1', 25)    
        worksheet.set_column('N1:N1', 25)    
        worksheet.set_column('O1:O1', 30)
        worksheet.set_column('P1:P1', 40)
        worksheet.set_column('Q1:Q1', 20)
        worksheet.set_column('R1:R1', 20)
        worksheet.set_column('S1:S1', 20)
        worksheet.set_column('T1:T1', 20)
        worksheet.set_column('U1:U1', 20)
        worksheet.set_column('V1:V1', 20)
        worksheet.set_column('W1:W1', 15)    
        worksheet.set_column('X1:X1', 15)    
        worksheet.set_column('Y1:Y1', 25)    
        worksheet.set_column('Z1:Z1', 25)  
        worksheet.set_column('AA1:AA1', 15)  
        worksheet.set_column('AB1:AB1', 25)  
        
        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        filename = 'Report Employee '+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report Employee ' , wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])
        worksheet.write('C3', 'Status : %s' %(status) , wbf['company'])

        row=3
        col=0
        worksheet.write(row+1, col, 'No' , wbf['header'])
        col+=1
        worksheet.write(row+1, col, 'Branch Code' , wbf['header'])
        col+=1
        worksheet.write(row+1, col, 'Branch Name' , wbf['header'])
        col+=1
        worksheet.write(row+1, col, 'Area Code' , wbf['header'])
        col+=1
        worksheet.write(row+1, col, 'Area Descp' , wbf['header'])
        col+=1
        worksheet.write(row+1, col, 'Emplyee Nip' , wbf['header'])
        col+=1
        worksheet.write(row+1, col, 'Employee Name' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Employee Street' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Employee Street2' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'RT' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'RW' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Province' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'City' , wbf['header'])
        col+=1
        worksheet.write(row+1, col, 'Kecamatan' , wbf['header'])
        col+=1
        worksheet.write(row+1, col, 'kelurahan' , wbf['header'])
        col+=1
        worksheet.write(row+1, col, 'Job Name' , wbf['header'])
        col+=1
        worksheet.write(row+1, col, 'Group Name' , wbf['header'])
        col+=1
        worksheet.write(row+1, col, 'Tgl Masuk' , wbf['header'])
        col+=1
        worksheet.write(row+1, col, 'Tgl Keluar' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Created By' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Created Date' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Updated By' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Updated Date' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Login' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Login Date' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Login Active' , wbf['header'])    
        col+=1
        worksheet.write(row+1, col,  'Bank' , wbf['header'])    
        col+=1
        worksheet.write(row+1, col,  'No Rekening' , wbf['header'])    
        row+=2               
        no = 1     
        row1 = row
        
        for res in ress:
            branch_code=res[0]
            branch_name=res[1]
            area_code=res[2]
            area_descp=res[3]
            emp_nip=res[4]
            emp_name=res[5]
            emp_street=res[6]
            emp_street2=res[7]
            rt=res[8]
            rw=res[9]
            province=res[10]
            city=res[11]
            kecamatan=res[12]
            kelurahan=res[13]
            job_name=res[14]
            group_name=res[15]
            tgl_masuk=res[16]
            tgl_keluar=res[17]
            create_by=res[18]
            create_date=res[19]
            update_by=res[20]
            update_date=res[21]
            login=res[22]
            login_date=res[23]
            login_active=res[24]
            bank=res[25]
            no_rekening=res[26]
            
            col=0
            worksheet.write(row, col, no , wbf['content_number'])
            col+=1
            worksheet.write(row, col, branch_code , wbf['content'])
            col+=1
            worksheet.write(row, col, branch_name , wbf['content'])
            col+=1
            worksheet.write(row, col, area_code , wbf['content'])
            col+=1
            worksheet.write(row, col, area_descp, wbf['content'])
            col+=1
            worksheet.write(row, col, emp_nip , wbf['content'])
            col+=1
            worksheet.write(row, col, emp_name , wbf['content_date'])
            col+=1
            worksheet.write(row, col, emp_street , wbf['content'])
            col+=1
            worksheet.write(row, col, emp_street2, wbf['content'])
            col+=1
            worksheet.write(row, col, rt , wbf['content'])
            col+=1
            worksheet.write(row, col, rw , wbf['content'])
            col+=1
            worksheet.write(row, col, province , wbf['content'])
            col+=1
            worksheet.write(row, col, city , wbf['content'])
            col+=1
            worksheet.write(row, col, kecamatan , wbf['content'])
            col+=1
            worksheet.write(row, col, kelurahan , wbf['content'])
            col+=1
            worksheet.write(row, col, job_name , wbf['content'])
            col+=1
            worksheet.write(row, col, group_name, wbf['content'])
            col+=1
            worksheet.write(row, col, tgl_masuk , wbf['content'])
            col+=1
            worksheet.write(row, col, tgl_keluar , wbf['content_date'])
            col+=1
            worksheet.write(row, col, create_by , wbf['content'])
            col+=1
            worksheet.write(row, col, create_date, wbf['content'])
            col+=1
            worksheet.write(row, col, update_by , wbf['content'])
            col+=1
            worksheet.write(row, col, update_date , wbf['content'])
            col+=1
            worksheet.write(row, col, login , wbf['content'])
            col+=1
            worksheet.write(row, col, login_date , wbf['content'])
            col+=1
            worksheet.write(row, col, login_active , wbf['content'])
            col+=1
            worksheet.write(row, col, bank , wbf['content'])
            col+=1
            worksheet.write(row, col, no_rekening , wbf['content'])
            no+=1
            row+=1
                
        worksheet.autofilter('A5:AB%s' % (row))  
        worksheet.freeze_panes(5, 3)
        worksheet.write('A%s'%(row+2), 'Create By: %s %s' % (user,str(date)) , wbf['footer'])  

        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

wtc_report_employee()