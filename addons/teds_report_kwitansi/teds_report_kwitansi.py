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


class teds_report_kwitansi (osv.osv_memory):
    _name='teds.report.kwitansi'
    _description='Report kwitansi'
    

    STATE_SELECTION = [
        ('open','Open'),
        ('printed','Printed'),
        ('cancel','Canceled')
    ]

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
        'state': fields.selection(STATE_SELECTION, 'State'),
        'start_date':fields.date('Start Date'),
        'end_date':fields.date('End Date'),
        'branch_ids': fields.many2many('wtc.branch', 'wtc_report_kwitansi_relation', 'wtc_report_kwitansi_wizard_id','branch_id', 'Branches', copy=False),
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

        self._print_excel_report_kwitansi(cr, uid,ids,data,context=context)

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'teds_report_kwitansi', 'view_report_kwitansi')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.report.kwitansi',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }
    
    def _print_excel_report_kwitansi(self, cr, uid, ids, data, context=None):        
        start_date = data['start_date']
        end_date = data['end_date']
        branch_ids = data['branch_ids']
        state = data['state']
       
  

        tz = '7 hours'
        query_where = " WHERE 1=1"
        query_saldo_where = ""
        if branch_ids :
            query_where += " AND rk.branch_id in %s " % str(tuple(branch_ids)).replace(',)', ')') 
        if start_date :
            query_where += " AND rk.date >= '%s' " % (start_date)
        if end_date :
            query_where += " AND rk.date <= '%s' "  % (end_date)
        if state :
            query_where += " AND rkl.state = '%s'" % str(state)
        
        # if division == '':
        #     query_where += " "
        # else:
        #     query_where += " and pa.division = '%s' " %(division)
        query="""
                select b.code as branch_code,
                av.number as no_transaksi,
                rkl.name as no_kwitansi,
                c.name as partner,
                av.name as keterangan,
                rk.date,
                fp.name as no_faktur_pajak,
                rkl.reason
                from wtc_register_kwitansi rk 
                left join wtc_register_kwitansi_line rkl on rk.id = rkl.register_kwitansi_id
                left join wtc_account_voucher av on rkl.new_payment_id = av.id
                left join wtc_faktur_pajak_out fp on av.faktur_pajak_id = fp.id
                left join wtc_branch b on rk.branch_id = b.id
                left join res_partner c on av.partner_id = c.id
                %s
            """ %(query_where)
            

        cr.execute (query)
        ress = cr.fetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Report Kwitansi') 
        worksheet.set_column('B1:B1', 15)
        worksheet.set_column('C1:C1', 25)
        worksheet.set_column('D1:D1', 10)
        worksheet.set_column('E1:E1', 25)
        worksheet.set_column('F1:F1', 25)
        worksheet.set_column('G1:G1', 25)
        worksheet.set_column('H1:H1', 30)
      
        
        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        
        filename = 'Report Kwitansi  '+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report Kwitansi  '+str(date) , wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])

        row=4
        rowsaldo = row
        row+=1
        worksheet.write('A%s' % (row+1), 'No' , wbf['header']) 
        worksheet.write('B%s' % (row+1), 'Branch' , wbf['header'])      
        worksheet.write('C%s' % (row+1), 'No Kwitansi' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'Date' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'No Transaksi', wbf['header'])
        worksheet.write('F%s' % (row+1), 'Partner', wbf['header'])
        worksheet.write('G%s' % (row+1), 'No Faktur' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'Keterangan' , wbf['header'])
        if state == 'cancel':
            worksheet.write('I%s' % (row+1), 'Reason' , wbf['header'])
       
       
        row+=2 
        row1 = row        
        no = 1   
       
        for res in ress:
            branch_code = res[0]
            no_transaksi = res[1]
            no_kwitansi = res[2]
            partner = res[3]
            keterangan = res[4]
            date = res[5]
            no_faktur_pajak = res[6]
            reason = res[7]
           
            

            worksheet.write('A%s' % row, no , wbf['content_number'])       
            worksheet.write('B%s' % row, branch_code , wbf['content'])             
            worksheet.write('C%s' % row, no_kwitansi , wbf['content'])
            worksheet.write('D%s' % row, date , wbf['content'])
            worksheet.write('E%s' % row, no_transaksi , wbf['content'])
            worksheet.write('F%s' % row, partner , wbf['content_date'])
            worksheet.write('G%s' % row, no_faktur_pajak, wbf['content'])
            worksheet.write('H%s' % row, keterangan , wbf['content'])
            if state == 'cancel':
                worksheet.write('I%s' % row, reason , wbf['content'])
                
            

            no+=1
            row+=1
        if state == 'cancel':
            worksheet.autofilter('A6:I%s' % (row))  
            worksheet.merge_range('A%s:I%s' % (row,row), '', wbf['total'])    

        else:
            worksheet.autofilter('A6:H%s' % (row))  
            worksheet.merge_range('A%s:H%s' % (row,row), '', wbf['total'])    

        worksheet.freeze_panes(6, 3)

        #TOTAL
        
        worksheet.write('A%s'%(row+2), 'Create By: %s %s' % (user,str(date)) , wbf['footer'])  

        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

#         return true

teds_report_kwitansi()