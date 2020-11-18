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

class wtc_report_surat_jalan(osv.osv_memory):
    _name='wtc.report.surat.jalan'
    
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
        'division':fields.selection([('Sparepart','Sparepart'),('Unit','Unit'),('Umum','Umum')]),
        'options':fields.selection([('sjo','Surat Jalan Keluar'),
                                    ('sji','Surat Jalan Masuk'),
                                    ('sja','Surat Jalan Mutasi'),
                                    ]),
        'state': fields.selection([('done','Transfered')], 'State', change_default=True, select=True),
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'branch_ids': fields.many2many('wtc.branch', 'wtc_report_surat_jalan_rel', 'wtc_report_surat_jalan_wizard_id','branch_id', 'Branch', copy=False),
    
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
        
        return self._print_excel_report_surat_jalan(cr, uid,ids,data,context=context)

    def _print_excel_report_surat_jalan(self, cr, uid, ids, data, context=None):        
        start_date = data['start_date']
        end_date = data['end_date']
        branch_ids = data['branch_ids']
        division=data['division']
        
        query_code = ""
        branch2_code=""
        branch2_name=""
        
        if data['options']=='sjo':
            branch2_code='Branch Req Code'
            branch2_name='Branch Req Name'
            query_code += " and spt.code in ('interbranch_out','outgoing')"
        elif data['options']=='sji':
            branch2_code='Branch Sender Code'
            branch2_name='Branch Sender Name'
            query_code += " and spt.code in ('interbranch_in','incoming')"
        else :
            branch2_code='Branch Req Code'
            branch2_name='Branch Req Name'
            query_code += " and spt.code ='internal' "
        
        tz = '7 hours'
        query_where = ""
        if branch_ids :
            query_where += " sp.branch_id in %s " % str(tuple(branch_ids)).replace(',)', ')')
        if start_date:
            query_where += " and sp.date_done + interval '7 hours' >='%s'" %(start_date) 
        if end_date :
            query_where += " and sp.date_done + interval '7 hours' <='%s'" %(end_date)

        if division=='Unit':
            query_division = " and sp.division ='%s' and pc2.name in ('AT','CUB','SPORT') " %(division)
        elif division=='Sparepart':
            query_division = " and sp.division ='%s' " %(division)
        else :
            query_division = " and sp.division ='%s' " %(division)
            
            
        query="""
            select 
            wb.code as branch_code,
            wb.name as branch_name,
            sp.origin as origin,
            COALESCE(rp.default_code, COALESCE(wb2.code, rp2.default_code)) as branch_req_code,
            COALESCE(rp.name,COALESCE(wb2.name,rp2.name)) as branch_req_name,
            sp.name as no_picking,
            sp.date_done + interval '7 hours' as tanggal,
            sp.state as status,
            sp.division as division,
            spt.name as jenis_transaksi,
            wsp.name as surat_jalan,
            spl.name as engine_no,
            spl.chassis_no,
            pp.name_template as model_tipe,
            pav.code as model_warna,
            wdl.driver as driver
            from stock_picking sp 
            left join stock_pack_operation spo on sp.id=spo.picking_id
            left join stock_picking_type spt on sp.picking_type_id=spt.id
            left join stock_production_lot spl on spo.lot_id=spl.id
            left join wtc_stock_packing wsp on sp.id=wsp.picking_id
            left join wtc_driver_line wdl on wsp.driver_id=wdl.id
            left join product_product pp on spo.product_id=pp.id 
            left join product_attribute_value_product_product_rel pavp on pp.id=pavp.prod_id
            left join product_attribute_value pav on pavp.att_id=pav.id 
            left join product_template pt on pp.product_tmpl_id=pt.id 
            left join product_category pc on pt.categ_id=pc.id 
            left join product_category pc2 on pc.parent_id=pc2.id 
            left join dealer_sale_order dso on sp.origin=dso.name
            left join wtc_mutation_order wmo on sp.origin=wmo.name
            left join wtc_branch wb on sp.branch_id=wb.id
            left join wtc_branch wb2 on wmo.branch_requester_id=wb2.id
            left join res_partner rp on sp.partner_id=rp.id
            left join res_partner rp2 on dso.partner_id=rp2.id
            WHERE
            %s %s %s
            """ % (query_where,query_division,query_code,)
            
        cr.execute (query)
        ress = cr.fetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('%s' %(division)) 
        worksheet.set_column('B1:B1', 15)
        worksheet.set_column('C1:C1', 25)
        worksheet.set_column('D1:D1', 20)
        worksheet.set_column('E1:E1', 20)
        worksheet.set_column('F1:F1', 50)
        worksheet.set_column('G1:G1', 30)
        worksheet.set_column('H1:H1', 20)
        worksheet.set_column('I1:I1', 10)
        worksheet.set_column('J1:J1', 13)
        worksheet.set_column('K1:K1', 20)
        worksheet.set_column('L1:L1', 20)
        worksheet.set_column('M1:M1', 25)
        worksheet.set_column('N1:N1', 25)
        worksheet.set_column('O1:O1', 25)
        worksheet.set_column('P1:P1', 25)
        worksheet.set_column('Q1:Q1', 25)
        
        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        filename = 'Report Surat Jalan '+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report Surat Jalan (%s)' %(division) , wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])
            
        row=3
        col=0
        worksheet.write(row+1,col, 'No' , wbf['header'])
        col+=1
        worksheet.write(row+1,col,  'Branch Code' , wbf['header'])
        col+=1
        worksheet.write(row+1,col, 'Branch Name' , wbf['header'])
        col+=1
        worksheet.write(row+1,col,  'Origin' , wbf['header'])
        col+=1
        worksheet.write(row+1,col, '%s' %(branch2_code) , wbf['header'])
        col+=1
        worksheet.write(row+1,col, '%s' %(branch2_name) , wbf['header'])
        col+=1
        worksheet.write(row+1,col,  'No Picking' , wbf['header'])
        col+=1
        worksheet.write(row+1,col,  'Date' , wbf['header'])
        col+=1
        worksheet.write(row+1,col,  'Status' , wbf['header'])
        col+=1
        worksheet.write(row+1,col,  'Division' , wbf['header'])
        col+=1
        worksheet.write(row+1,col,  'Jenis Transaksi' , wbf['header'])
        col+=1
        worksheet.write(row+1,col,  'Surat Jalan' , wbf['header'])
        col+=1
        worksheet.write(row+1,col,  'Engine No' , wbf['header'])
        col+=1
        worksheet.write(row+1,col,  'Chassis No' , wbf['header'])
        col+=1
        worksheet.write(row+1,col,  'Model Tipe' , wbf['header'])
        col+=1
        worksheet.write(row+1,col,  'Model Warna' , wbf['header'])
        col+=1
        worksheet.write(row+1,col,  'Driver' , wbf['header'])
        
        row+=1               
        no = 1     
        row1 = row
        branch_req_code=""
        branch_req_name=""
        for res in ress:
            branch_code=res[0]
            branch_name = res[1]
            origin=res[2]      
            branch_req_code=res[3]
            branch_req_name=res[4]         
            no_picking=res[5]
            date =  res[6].encode('ascii','ignore').decode('ascii')
            status=res[7]
            division=res[8]
            transaksi=res[9]
            surat_jalan=res[10]
            engine=res[11]
            chassis=res[12]
            tipe=res[13]
            warna=res[14]
            driver=res[15]
            
            col=0
            worksheet.write(row+1,col, no , wbf['content_number'])
            col+=1
            worksheet.write(row+1,col, branch_code , wbf['content'])
            col+=1
            worksheet.write(row+1,col, branch_name , wbf['content'])
            col+=1
            worksheet.write(row+1,col, origin , wbf['content'])                
            col+=1
            worksheet.write(row+1,col, branch_req_code , wbf['content'])
            col+=1
            worksheet.write(row+1,col, branch_req_name , wbf['content'])
            col+=1
            worksheet.write(row+1,col, no_picking , wbf['content'])
            col+=1
            worksheet.write(row+1,col, date , wbf['content'])
            col+=1
            worksheet.write(row+1,col, status , wbf['content'])
            col+=1
            worksheet.write(row+1,col, division , wbf['content_date'])
            col+=1
            worksheet.write(row+1,col, transaksi , wbf['content'])
            col+=1
            worksheet.write(row+1,col, surat_jalan, wbf['content'])
            col+=1
            worksheet.write(row+1,col, engine , wbf['content'])
            col+=1
            worksheet.write(row+1,col, chassis , wbf['content'])
            col+=1
            worksheet.write(row+1,col, tipe , wbf['content'])
            col+=1
            worksheet.write(row+1,col, warna , wbf['content'])
            col+=1
            worksheet.write(row+1,col, driver , wbf['content'])
            
            no+=1
            row+=1
            
        worksheet.autofilter('A5:Q%s' % (row))  
        worksheet.freeze_panes(5, 3)
        worksheet.write('A%s'%(row+3), 'Create By: %s %s' % (user,str(date)) , wbf['footer'])  

        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_surat_jalan', 'report_surat_jalan_form')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.report.surat.jalan',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }

        return true



wtc_report_surat_jalan()
    