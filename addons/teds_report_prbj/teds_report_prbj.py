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


class teds_report_prbj(osv.osv_memory):
    _name='teds.report.prbj'
    
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
        'partner_id':fields.many2one('res.partner', 'Birojasa', copy=False),
        'start_date':fields.date('Start Date'),
        'end_date':fields.date('End Date'),
        'branch_ids': fields.many2many('wtc.branch', 'wtc_report_prbj_rel', 'wtc_report_prbj_wizard_id','branch_id', 'Branch', copy=False),
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

        self._print_excel_report_prbj(cr, uid,ids,data,context=context)

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'teds_report_prbj', 'teds_report_prbj_form')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.report.prbj',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }
    
    def _print_excel_report_prbj(self, cr, uid, ids, data, context=None):        
        start_date = data['start_date']
        end_date = data['end_date']
        branch_ids = data['branch_ids']
        birojasa = ''
        partner_id = data.get('partner_id',False)
        if partner_id:
            birojasa = partner_id[1]
        tz = '7 hours'
        query_where = ""
        query_saldo_where = ""

        if branch_ids :
            query_where += " AND b.id in %s " % str(tuple(branch_ids)).replace(',)', ')') 
        if start_date :
            query_where += " AND pb.tanggal >= '%s' " % (start_date)
        if end_date :
            query_where += " AND pb.tanggal <= '%s' "  % (end_date)
        if partner_id :
            query_where += " AND rp.id = %s "  % (partner_id[0])


        query = """
                select 
                b.code, 
                b.name, 
                pb.name, 
                pb.tanggal, 
                pb.state, 
                rp.default_code, 
                rp.name, 
                pb.type, 
                pb.no_dok, 
                pb.description, 
                lot.name, 
                lot.chassis_no, 
                cust.default_code, 
                cust.name, 
                pbl.no_notice_copy, 
                pbl.tgl_notice_copy, 
                pbl.total_estimasi, 
                pbl.pajak_progressive, 
                pbl.total_tagihan, 
                pbl.koreksi
                from wtc_proses_birojasa pb 
                inner join wtc_proses_birojasa_line pbl on pb.id = pbl.proses_biro_jasa_id
                left join wtc_branch b on pb.branch_id = b.id 
                left join res_partner rp on pb.partner_id = rp.id 
                left join stock_production_lot lot on pbl.name = lot.id 
                left join res_partner cust on lot.customer_stnk = cust.id 
                where pb.state in ('done', 'approved')
                %s
                order by pb.tanggal, pb.id 
                """ % (query_where)

        cr.execute (query)
        ress = cr.fetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Report PRBJ') 
        worksheet.set_column('B1:B1', 5)
        worksheet.set_column('C1:C1', 20)
        worksheet.set_column('D1:D1', 20)
        worksheet.set_column('E1:E1', 10)
        worksheet.set_column('F1:F1', 5)
        worksheet.set_column('G1:G1', 15)
        worksheet.set_column('H1:H1', 15)
        worksheet.set_column('I1:I1', 5)
        worksheet.set_column('J1:J1', 10)
        worksheet.set_column('K1:K1', 30)
        worksheet.set_column('L1:L1', 15)
        worksheet.set_column('M1:M1', 15)
        worksheet.set_column('N1:N1', 15)
        worksheet.set_column('O1:O1', 20)
        worksheet.set_column('P1:P1', 20)
        worksheet.set_column('Q1:Q1', 20)
        worksheet.set_column('R1:R1', 15)
        worksheet.set_column('S1:S1', 20)
        worksheet.set_column('T1:T1', 15)
        worksheet.set_column('U1:U1', 15)



        
        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        filename = 'Report PRBJ %s '%(birojasa)+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report PRBJ %s'%(birojasa), wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])

        row=4
        col=0
        worksheet.write(row+1, col, 'No' , wbf['header'])
        col+=1
        worksheet.write(row+1, col, 'Code', wbf['header'])
        col+=1
        worksheet.write(row+1, col, 'Branch', wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'No Transaksi', wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Tanggal' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'State' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'BJ Code' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'BJ Name' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Type' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'No Doc' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Description' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Engine No' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Chassis No' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Cust. Code' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Cust. Name' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'No Notice' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Tgl Notice' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Total Estimasi' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Tax Progressive' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Total Tagihan' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Koreksi' , wbf['header'])

        row+=2               
        no = 1     
        row1 = row
        
        for res in ress:
            code = res[0]
            name = res[1]
            no_transaksi = res[2]
            tanggal = res[3]
            state = res[4]
            bjcode = res[5]
            bjname = res[6]
            tipe = res[7]
            no_dok = res[8]
            description = res[9] 
            engine_no = res[10]
            chassis_no = res[11]
            cust_code = res[12]
            cust_name = res[13]
            no_notice_copy = res[14]
            tgl_notice_copy = res[15]
            total_estimasi = res[16]
            pajak_progressive = res[17]
            total_tagihan = res[18]
            koreksi = res[19]

            col=0
            worksheet.write(row, col, no , wbf['content_number'])
            col+=1
            worksheet.write(row, col, code , wbf['content'])
            col+=1
            worksheet.write(row, col, name , wbf['content'])
            col+=1
            worksheet.write(row, col, no_transaksi , wbf['content'])
            col+=1
            worksheet.write(row, col, tanggal , wbf['content'])
            col+=1
            worksheet.write(row, col, state , wbf['content'])
            col+=1
            worksheet.write(row, col, bjcode , wbf['content_date'])
            col+=1
            worksheet.write(row, col, bjname , wbf['content'])
            col+=1
            worksheet.write(row, col, tipe, wbf['content'])
            col+=1
            worksheet.write(row, col, no_dok , wbf['content'])
            col+=1
            worksheet.write(row, col, description , wbf['content'])
            col+=1
            worksheet.write(row, col, engine_no , wbf['content_date'])
            col+=1
            worksheet.write(row, col, chassis_no , wbf['content'])
            col+=1
            worksheet.write(row, col, cust_code, wbf['content'])
            col+=1
            worksheet.write(row, col, cust_name , wbf['content'])
            col+=1
            worksheet.write(row, col, no_notice_copy , wbf['content_date'])
            col+=1
            worksheet.write(row, col, tgl_notice_copy , wbf['content'])
            col+=1
            worksheet.write(row, col, total_estimasi, wbf['content'])
            col+=1
            worksheet.write(row, col, pajak_progressive , wbf['content'])
            col+=1
            worksheet.write(row, col, total_tagihan, wbf['content'])
            col+=1
            worksheet.write(row, col, koreksi, wbf['content'])

            no+=1
            row+=1
                
        worksheet.autofilter('A6:U%s' % (row))  
        worksheet.freeze_panes(6, 3)
        worksheet.write('A%s'%(row+2), 'Create By: %s %s' % (user,str(date)) , wbf['footer'])  

        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        # return true

teds_report_prbj()