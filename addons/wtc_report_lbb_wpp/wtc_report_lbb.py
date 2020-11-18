import time
import cStringIO
import xlsxwriter
from cStringIO import StringIO
import base64
import tempfile
import os
import time
import datetime
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
from dateutil.rrule import *

class wtc_report_lbb(osv.osv_memory):
   
    _name = "wtc.report.lbb.wizard"
    _description = "Report LBB Work Shop"

    wbf = {}

    def _get_default(self,cr,uid,date=False,user=False,context=None):
        if date :
            return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)
        else :
            return self.pool.get('res.users').browse(cr, uid, uid)
        
    def _get_branch_ids(self, cr, uid, context=None):
        branch_ids_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
        branch_ids = [b.id for b in branch_ids_user]
        return branch_ids
    
   
    _columns = {
        'state_x': fields.selection( ( ('choose','choose'),('get','get'))), #xls
        'data_x': fields.binary('File', readonly=True),
        'name': fields.char('Filename', 100, readonly=True),
        'start_date': fields.date('Start Date', required=True),
        'end_date': fields.date('End Date', required=True), 
        'branch_id':fields.many2one('wtc.branch','Branch'),
        'branch_ids': fields.many2many('wtc.branch', 'wtc_report_lbb_rel', 'wtc_report_lbb_wizard_id','branch_id', 'Branches', copy=False),
        'options' : fields.selection([('lbb','LBB'),('wpp','WPP'),('persentasi_mekanik','Prestasi Mekanik'),('detil_prestasi','Detil Prestasi Mekanik')],string='Options',required=True),
       
    
    }

    _defaults = {
        'state_x': lambda *a: 'choose',
        'options':'lbb',
    }
    
    def add_workbook_format(self, cr, uid, workbook):  
        self.wbf['title'] = workbook.add_format({'align': 'center','bold': 1})
        self.wbf['title'].set_font_size(12)
        self.wbf['title'].set_font_name('Arial')
        self.wbf['title'].set_underline()
       
        
        self.wbf['title_2'] = workbook.add_format({'align': 'left','bold': 1})
        self.wbf['title_2'].set_font_size(11)
        self.wbf['title_2'].set_font_name('Arial Narrow')
        
        self.wbf['content_center'] = workbook.add_format({'align': 'centre'})
        
        
        self.wbf['haeader_table_center'] = workbook.add_format({'align': 'centre','bold': 1})
        self.wbf['haeader_table_center'].set_font_size(12)
        self.wbf['haeader_table_center'].set_font_name('Arial Narrow')
        self.wbf['haeader_table_center'].set_italic()
        self.wbf['haeader_table_center'].set_top()
        self.wbf['haeader_table_center'].set_bottom()            
        self.wbf['haeader_table_center'].set_left()
        self.wbf['haeader_table_center'].set_right()  
        
        
        self.wbf['haeader_table_center_right'] = workbook.add_format({'align': 'right','bold': 1})
        self.wbf['haeader_table_center_right'].set_font_size(11)
        self.wbf['haeader_table_center_right'].set_font_name('Arial Narrow')
        self.wbf['haeader_table_center_right'].set_top()
        self.wbf['haeader_table_center_right'].set_bottom()            
        self.wbf['haeader_table_center_right'].set_left()
        self.wbf['haeader_table_center_right'].set_right() 
        
        
        
        self.wbf['content'] = workbook.add_format()
        self.wbf['content'].set_font_name('Arial Narrow')
        self.wbf['content'].set_font_size(11)
        self.wbf['content'].set_top()
        self.wbf['content'].set_bottom()            
        self.wbf['content'].set_left()
        self.wbf['content'].set_right()  
        
        self.wbf['content_wpp'] = workbook.add_format()
        self.wbf['content_wpp'].set_font_name('Arial Narrow')
        self.wbf['content_wpp'].set_font_size(11)
        self.wbf['content_wpp'].set_top()
        self.wbf['content_wpp'].set_bottom()            
        self.wbf['content_wpp'].set_left()
        self.wbf['content_wpp'].set_right()
        self.wbf['content_wpp'].set_align('vcenter') 
        
        
        self.wbf['content_float'] = workbook.add_format({'align': 'right','num_format': '#,##0.00'})
        self.wbf['content_float'].set_font_name('Arial Narrow')
        self.wbf['content_float'].set_font_size(11)
        self.wbf['content_float'].set_top()
        self.wbf['content_float'].set_bottom()            
        self.wbf['content_float'].set_left()
        self.wbf['content_float'].set_right()  
        
        self.wbf['content_float_bold'] = workbook.add_format({'align': 'right','num_format': '#,##0.00','bold': 1})
        self.wbf['content_float_bold'].set_font_name('Arial Narrow')
        self.wbf['content_float_bold'].set_font_size(11)
        self.wbf['content_float_bold'].set_top()
        self.wbf['content_float_bold'].set_bottom()            
        self.wbf['content_float_bold'].set_left()
        self.wbf['content_float_bold'].set_right() 
        
        self.wbf['content_float_bold_wpp'] = workbook.add_format({'align': 'center','num_format': '#,##0.00','bold': 1})
        self.wbf['content_float_bold_wpp'].set_font_name('Arial Narrow')
        self.wbf['content_float_bold_wpp'].set_font_size(11)
        self.wbf['content_float_bold_wpp'].set_top()
        self.wbf['content_float_bold_wpp'].set_bottom()            
        self.wbf['content_float_bold_wpp'].set_left()
        self.wbf['content_float_bold_wpp'].set_right() 
        self.wbf['content_float_bold_wpp'].set_align('vcenter') 
       
        
        self.wbf['center_content'] =workbook.add_format({'align': 'centre'})
        self.wbf['center_content'].set_font_name('Arial Narrow')
        self.wbf['center_content'].set_font_size(11)
        self.wbf['center_content'].set_top()
        self.wbf['center_content'].set_bottom()            
        self.wbf['center_content'].set_left()
        self.wbf['center_content'].set_right()

        self.wbf['content_total'] =workbook.add_format({'align': 'centre','bold': 1})
        self.wbf['content_total'].set_font_name('Arial Narrow')
        self.wbf['content_total'].set_font_size(11)
        self.wbf['content_total'].set_top()
        self.wbf['content_total'].set_bottom()            
        self.wbf['content_total'].set_left()
        self.wbf['content_total'].set_right()  
        
        self.wbf['content_grand_total'] =workbook.add_format({'align': 'centre','bold': 1})
        self.wbf['content_grand_total'].set_font_name('Arial Narrow')
        self.wbf['content_grand_total'].set_font_size(12)
        self.wbf['content_grand_total'].set_top()
        self.wbf['content_grand_total'].set_bottom()            
        self.wbf['content_grand_total'].set_left()
        self.wbf['content_grand_total'].set_right() 
        
        
        self.wbf['content_no'] = workbook.add_format({'align': 'center'})
        self.wbf['content_no'].set_top()
        self.wbf['content_no'].set_bottom()            
        self.wbf['content_no'].set_left()
        self.wbf['content_no'].set_right()  
        self.wbf['content_no'].set_font_size(10)
        
        
        self.wbf['header_table_v_bold']  =workbook.add_format({'bold': 1})
        self.wbf['header_table_v_bold'].set_font_name('Arial Narrow')
        self.wbf['header_table_v_bold'].set_font_size(11)
        self.wbf['header_table_v_bold'].set_border()
        self.wbf['header_table_v_bold'].set_align('vcenter')
        
        
        self.wbf['header_table_v_center']  =workbook.add_format({'align': 'centre'})
        self.wbf['header_table_v_center'].set_font_name('Arial Narrow')
        self.wbf['header_table_v_center'].set_font_size(11)
        self.wbf['header_table_v_center'].set_border()
        self.wbf['header_table_v_center'].set_align('vcenter')
        
        
        self.wbf['header_table_v_center_bold']  =workbook.add_format({'align': 'centre','bold': 1})
        self.wbf['header_table_v_center_bold'].set_font_name('Arial Narrow')
        self.wbf['header_table_v_center_bold'].set_font_size(11)
        self.wbf['header_table_v_center_bold'].set_border()
        self.wbf['header_table_v_center_bold'].set_align('vcenter')
       
       
        
        
            
        self.wbf['header'] = workbook.add_format({'bold': 1,'align': 'center','bg_color': '#FFFFDB','font_color': '#000000'})
        self.wbf['header'].set_border()

       
                
        self.wbf['footer'] = workbook.add_format({'align':'left'})
        
        self.wbf['content_datetime'] = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss'})
        self.wbf['content_datetime'].set_left()
        self.wbf['content_datetime'].set_right()
        
        self.wbf['content_datetime_12_hr'] = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm AM/PM'})
        self.wbf['content_datetime_12_hr'].set_left()
        self.wbf['content_datetime_12_hr'].set_right()        
                
        self.wbf['content_date'] = workbook.add_format({'num_format': 'yyyy-mm-dd'})
        self.wbf['content_date'].set_left()
        self.wbf['content_date'].set_right() 
        
        self.wbf['title_doc'] = workbook.add_format({'bold': 1,'align': 'left'})
        self.wbf['title_doc'].set_font_size(12)
        
        self.wbf['company'] = workbook.add_format({'align': 'left'})
        self.wbf['company'].set_font_size(11)
        
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
        
        if data['options'] == 'lbb' : 
            self._print_excel_report_lbb(cr, uid, ids, data, context=context)
        if data['options'] == 'wpp' : 
            self._print_excel_report_wpp(cr, uid, ids, data, context=context)
        if data['options'] == 'persentasi_mekanik' : 
            self._print_excel_report_prestasi_mekanik(cr, uid, ids, data, context=context)
        if data['options'] == 'detil_prestasi' :   
            self._print_excel_report_prestasi_mekanik_detil(cr, uid, ids, data, context=context)
        
        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_lbb_wpp', 'view_wtc_report_lbb_wizard')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.report.lbb.wizard',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }

    def _print_excel_report_lbb(self, cr, uid, ids, data, context=None): 
        val = self.browse(cr, uid, ids, context={})[0]
        branch_id = data['branch_id']  
        start_date = data['start_date']
        end_date = data['end_date']
        tz = '7 hours'
        
        query_sum="""
                   SELECT 
                    wo.branch_id
                    ,COALESCE(SUM(CASE WHEN wol.categ_id = 'Service'  AND pc2.name = 'KPB'  THEN wol.price_unit*(1-COALESCE(wol.discount,0)/100) END),0) total_kpb
                    ,COALESCE(SUM(CASE WHEN wol.categ_id = 'Service'  AND (pc2.name = 'QS' OR pc.name in ('LR', 'HR'))  THEN wol.price_unit*(1-COALESCE(wol.discount,0)/100) END),0  ) total_qs_lr_hr
                    ,COALESCE(SUM(CASE WHEN wol.categ_id = 'Service'  AND pc.name = 'CLA'  THEN wol.price_unit*(1-COALESCE(wol.discount,0)/100) END),0  ) total_claim, 0 AS total_lain
                    ,COALESCE(SUM(CASE WHEN wol.categ_id = 'Service' THEN wol.price_unit*(1-COALESCE(wol.discount,0)/100) END),0  ) amt_jasa
                    ,COALESCE(SUM(CASE WHEN wol.categ_id = 'Sparepart' AND pc.name NOT IN ( 'OLI','OIL','TIRE','TIRE1') THEN wol.price_unit*(1-COALESCE(wol.discount,0)/100) END),0  ) amt_part
                    ,COALESCE(SUM(CASE WHEN wol.categ_id = 'Sparepart' AND pc.name IN ( 'OLI','OIL') THEN wol.price_unit*(1-COALESCE(wol.discount,0)/100) END),0  ) amt_oil
                    ,COALESCE(SUM(CASE WHEN wol.categ_id = 'Sparepart' AND pc.name IN ('TIRE','TIRE1') THEN wol.price_unit*(1-COALESCE(wol.discount,0)/100) END),0  ) amt_tire
                    ,COALESCE( SUM(CASE   WHEN  pc.name in ('OLI','OIL')  and wol.categ_id='Sparepart' then wol.supply_qty END ) ,0 )as count_oli
                    ,COALESCE( SUM(CASE   WHEN  pc.name in ('TIRE','TIRE1')  and wol.categ_id='Sparepart' then wol.supply_qty END ),0  )as count_tire
                    FROM wtc_work_order wo
                    INNER JOIN wtc_work_order_line wol ON wo.id = wol.work_order_id
                    LEFT JOIN product_product p ON wol.product_id = p.id 
                    LEFT JOIN product_template pt ON p.product_tmpl_id = pt.id 
                    LEFT JOIN product_category pc ON pt.categ_id = pc.id 
                    LEFT JOIN product_category pc2 ON pc.parent_id = pc2.id
                    WHERE wo.date BETWEEN '%s'  AND '%s'
                    AND branch_id=%s
                    GROUP BY wo.branch_id
                """ %(start_date,end_date,val.branch_id.id)
            
        cr.execute (query_sum)
        picks = cr.dictfetchall()
        
        if picks :
            jasa_kpb =picks[0]['total_kpb']
            jasa_qs_lr_hr =picks[0]['total_qs_lr_hr']
            jasa_claim =picks[0]['total_claim']
            jasa_lain =picks[0]['total_lain']
            sparepart =picks[0]['amt_part']
            oli =picks[0]['amt_oil']
            tire =picks[0]['amt_tire']
            count_oli =picks[0]['count_oli']
            count_tire =picks[0]['count_tire']
        else :
            jasa_kpb =0
            jasa_qs_lr_hr =0
            jasa_claim =0
            jasa_lain =0
            sparepart =0
            oli =0
            tire =0
            count_oli =0
            count_tire =0
               
        query = """
                SELECT 
                wo_header.id_product_unit,
                wo_header.nama_unit,
                wo_header.code_unit,
                wo_header.categ,
                wo_header.categ_parent,
                COALESCE(wo_header.total_kpb_1,0) as total_kpb_1,
                COALESCE(wo_header.total_kpb_2,0) as total_kpb_2,
                COALESCE(wo_header.total_kpb_3,0) as total_kpb_3,
                COALESCE(wo_header.total_kpb_4,0) as total_kpb_4,
                COALESCE(wo_header.total_claim,0) as total_claim,
                COALESCE(wo_header.total_unit,0) as total_unit,
                COALESCE(wo_header.total_jr,0) as total_jr,
                COALESCE(wo_detail.total_cs,0) as total_cs,
                COALESCE(wo_detail.total_ls,0) as total_ls,
                COALESCE(wo_detail.total_or,0) as total_or,
                COALESCE(wo_detail.total_lr,0) as total_lr,
                COALESCE(wo_detail.total_hr,0) as total_hr,
                COALESCE(wo_detail.total_pekerjaan,0) as total_pekerjaan,
                COALESCE(wo_header.total_jr,0) as total_jr,
                COALESCE(wo_unit.unit_entry,0) as unit_entry
                from 
                (SELECT 
                prt_u.id as id_product_unit,
                prt_u.name as code_unit,
                prt_u.description as nama_unit,
                prc_u.name as categ,
                prc_u_parent.name as categ_parent,
                COUNT(CASE   WHEN wo.kpb_ke='1'  then wo.id END ) as total_kpb_1,
                COUNT(CASE   WHEN wo.kpb_ke='2'  then wo.id END ) as total_kpb_2,
                COUNT(CASE   WHEN wo.kpb_ke='3'  then wo.id END ) as total_kpb_3,
                COUNT(CASE   WHEN wo.kpb_ke='4'  then wo.id END ) as total_kpb_4,
                COUNT(CASE   WHEN wo.type='CLA'  then wo.id END ) as total_claim,
                COUNT(CASE   WHEN wo.type='WAR'  then wo.id END ) as total_jr,
                COUNT(wo.id ) as total_unit
                FROM wtc_work_order as wo
                LEFT JOIN product_product as pr_u ON pr_u.id=wo.product_id
                LEFT JOIN product_template as prt_u ON prt_u.id=pr_u.product_tmpl_id
                LEFT JOIN product_category as prc_u ON prc_u.id=prt_u.categ_id
                LEFT JOIN product_category as prc_u_parent ON prc_u.parent_id=prc_u_parent.id
                LEFT JOIN wtc_branch as branch_header ON branch_header.id=wo.branch_id
                where  wo.date>= '%s' """ % str(start_date) + """ and wo.date<= '%s'""" % str(end_date) +"""
                AND wo.branch_id= %s """ % str(val.branch_id.id) + """
                GROUP BY prt_u.id,prt_u.description,prc_u.name,prc_u_parent.name,prt_u.name) as wo_header ,
                (SELECT 
                prt_u_line.id as id_product_unit_line,
                prt_u_line.description as nama_unit_line,
                COUNT(CASE   WHEN prc.name in ('CS') and wo_line.categ_id='Service' then wo_detail_line.id END ) as total_cs,
                COUNT(CASE   WHEN prc.name in ('LS') and wo_line.categ_id='Service' then wo_detail_line.id END ) as total_ls,
                COUNT(CASE   WHEN prc.name in ('OR+') and wo_line.categ_id='Service' then wo_detail_line.id END ) as total_or,
                COUNT(CASE   WHEN prc.name in ('LR') and wo_line.categ_id='Service' then wo_detail_line.id END ) as total_lr,
                COUNT(CASE   WHEN prc.name in ('HR') and wo_line.categ_id='Service' then wo_detail_line.id END ) as total_hr,
                COUNT(wo_line.id ) as total_pekerjaan
                FROM wtc_work_order as wo_detail_line
                LEFT JOIN wtc_work_order_line as wo_line ON wo_detail_line.id=wo_line.work_order_id
                LEFT JOIN product_product as pr ON pr.id=wo_line.product_id
                LEFT JOIN product_template as prt ON prt.id=pr.product_tmpl_id
                LEFT JOIN product_category as prc ON prc.id=prt.categ_id
                LEFT JOIN product_product as pr_u_line ON pr_u_line.id=wo_detail_line.product_id
                LEFT JOIN product_template as prt_u_line  ON prt_u_line.id=pr_u_line.product_tmpl_id
                LEFT JOIN product_category as prc_u_line ON prc_u_line.id=prt_u_line.categ_id
                LEFT JOIN wtc_branch as branch_detail ON branch_detail.id=wo_detail_line.branch_id
                WHERE    wo_detail_line.date>= '%s' """ % str(start_date) + """ and wo_detail_line.date<= '%s'""" % str(end_date) +"""
                AND wo_detail_line.branch_id= %s """ % str(val.branch_id.id) + """
                GROUP BY prt_u_line.id,prt_u_line.description ) as wo_detail,
                (            
                SELECT 
                id_product_unit_entry, 
                code_unit_entry,
                nama_unit_entry,
                categ_entry,
                categ_parent_entry,
                SUM(cnt_per_date) AS unit_entry
                FROM (
                SELECT prt_u_entry.id as id_product_unit_entry,
                prt_u_entry.name as code_unit_entry,
                prt_u_entry.description as nama_unit_entry,
                prc_u_entry.name as categ_entry,
                prc_u_parent_entry.name as categ_parent_entry,
                wo_entry.date,
                COUNT(DISTINCT lot_id) AS cnt_per_date
                FROM wtc_work_order as wo_entry
                LEFT JOIN stock_production_lot as lot ON lot.id=wo_entry.lot_id
                LEFT JOIN product_product as pr_u_entry ON pr_u_entry.id=lot.product_id
                LEFT JOIN product_template as prt_u_entry ON prt_u_entry.id=pr_u_entry.product_tmpl_id
                LEFT JOIN product_category as prc_u_entry ON prc_u_entry.id=prt_u_entry.categ_id
                LEFT JOIN product_category as prc_u_parent_entry  ON prc_u_entry.parent_id=prc_u_parent_entry.id
                LEFT JOIN wtc_branch as branch_header_entry  ON branch_header_entry.id=wo_entry.branch_id
                WHERE wo_entry.type <> 'WAR' AND wo_entry.type <> 'SLS' 
                AND wo_entry.date>= '%s' """ % str(start_date) + """ and wo_entry.date<= '%s'""" % str(end_date) +"""
                AND wo_entry.branch_id= %s """ % str(val.branch_id.id) + """
                GROUP BY prt_u_entry.id,prt_u_entry.description,prc_u_entry.name,prc_u_parent_entry.name,prt_u_entry.name, wo_entry.date ) wo_per_date
                GROUP BY id_product_unit_entry, 
                code_unit_entry,
                nama_unit_entry,
                categ_entry,categ_parent_entry) as wo_unit
                where 1=1 and wo_header.id_product_unit=wo_detail.id_product_unit_line
                and wo_unit.id_product_unit_entry=wo_header.id_product_unit
                and wo_unit.id_product_unit_entry=wo_detail.id_product_unit_line
                

                 """
        
        cr.execute (query)
        ress= cr.fetchall()
        
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('LBB')
        worksheet.set_column('A1:A1', 2)
       
        worksheet.set_column('B1:B1', 2)
        worksheet.set_column('C1:C1', 2)
        worksheet.set_column('D1:D1', 5)
        worksheet.set_column('D7:D7', 2)
        worksheet.set_column('E1:E1', 10)
        worksheet.set_column('E7:E7', 15)
        worksheet.set_column('E16:E16', 18)
        worksheet.set_column('F1:F1', 2)
        worksheet.set_column('F18:F18', 5)
        worksheet.set_column('G1:G1', 10)
        worksheet.set_column('G7:G7', 5)
        worksheet.set_column('G18:G18', 5)
        worksheet.set_column('H1:H1', 2)
        worksheet.set_column('H7:H7', 15)
        worksheet.set_column('H8:H8', 15)
        worksheet.set_column('H9:H9', 15)
        worksheet.set_column('H10:H10', 15)
        worksheet.set_column('H18:H18', 5)
        worksheet.set_column('I1:I1', 2)
        worksheet.set_column('I18:I18', 5)
        worksheet.set_column('J1:J1', 8)
        worksheet.set_column('J16:J16', 5)
        worksheet.set_column('K1:K1', 15)
        worksheet.set_column('K11:K11', 2)
        worksheet.set_column('K17:K17', 5)
        worksheet.set_column('L1:L1', 2)
        worksheet.set_column('L7:L7', 10)
        worksheet.set_column('L17:L17', 5)
        worksheet.set_column('M1:M1', 5)
        worksheet.set_column('M7:M7', 15)
        worksheet.set_column('M17:M17', 5)
        worksheet.set_column('N1:N1', 2)
        worksheet.set_column('N17:N17', 5)
        worksheet.set_column('O1:O1', 2)
        worksheet.set_column('O4:O4', 15)
        worksheet.set_column('O7:O7', 2)
        worksheet.set_column('O17:O17', 5)
        worksheet.set_column('P1:P1', 2)
        worksheet.set_column('P16:P16', 1)
        worksheet.set_column('Q1:Q1', 2)
        worksheet.set_column('Q7:Q7', 15)
        worksheet.set_column('Q8:Q8', 15)
        worksheet.set_column('Q9:Q9', 8)
        worksheet.set_column('Q10:Q10', 6)
        worksheet.set_column('R1:R1', 2)
        worksheet.set_column('R16:R16', 6)
        worksheet.set_column('S1:S1', 2)
        worksheet.set_column('S8:S8', 15)
        worksheet.set_column('S9:S9', 8)
        worksheet.set_column('T1:T1', 20)
        worksheet.set_column('U1:U1', 20)
        worksheet.set_column('V1:V1', 20)
        worksheet.set_column('W1:W1', 20)
        worksheet.set_column('X1:X1', 20)
        worksheet.set_column('Y1:Y1', 20)
        worksheet.set_column('Z1:Z1', 20)
        worksheet.set_column('AA1:AA1', 8)
        worksheet.set_column('AB1:AB1', 8)
        worksheet.set_column('AC1:AC1', 20)
        worksheet.set_column('AD1:AD1', 20)      
                        
        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
       
        
        filename = 'Laporan LBB '+str(date)+'.xlsx'        
        worksheet.merge_range('D%s:S%s' % (1,1), 'LAPORAN BULANAN BENGKEL ( L.B.B )', wbf['title']) 
        
        worksheet.merge_range('D%s:E%s' % (2,2), 'No.AHASS', wbf['title_2']) 
        worksheet.write('F2', ':' , wbf['content_center'])
        worksheet.merge_range('G%s:J%s' % (2,2), val.branch_id.ahm_code, wbf['title_2']) 
        
        worksheet.merge_range('L%s:M%s' % (2,2), 'Laporan Bulan', wbf['title_2']) 
        worksheet.write('N2', ':' , wbf['content_center'])
        worksheet.merge_range('O%s:S%s' % (2,2), '%s s/d %s'%(str(start_date),str(end_date)), wbf['title_2']) 
        
        
        worksheet.merge_range('D%s:E%s' % (3,3), 'Nama AHASS', wbf['title_2']) 
        worksheet.write('F3', ':' , wbf['content_center'])
        worksheet.merge_range('G%s:J%s' % (3,3), val.branch_id.name, wbf['title_2']) 
        
        
        worksheet.merge_range('L%s:M%s' % (3,3), 'Dibuat Tanggal', wbf['title_2']) 
        worksheet.write('N3', ':' , wbf['content_center'])
        worksheet.merge_range('O%s:S%s' % (3,3), date, wbf['title_2']) 
        
        
        worksheet.merge_range('D%s:E%s' % (4,4), 'Kab/ Kota', wbf['title_2']) 
        worksheet.write('F4', ':' , wbf['content_center'])
        worksheet.merge_range('G%s:J%s' % (4,4), val.branch_id.city_id.name, wbf['title_2']) 
        
        
        worksheet.merge_range('L%s:M%s' % (4,4), 'Dibuat Oleh', wbf['title_2']) 
        worksheet.write('N4', ':' , wbf['content_center'])
        worksheet.merge_range('O%s:S%s' % (4,4), user, wbf['title_2']) 
        
        
        worksheet.merge_range('D%s:J%s' % (6,6), 'I. Pendapatan Jasa dan Reparasi', wbf['haeader_table_center']) 
        worksheet.merge_range('L%s:S%s' % (6,6), 'II. Pendapatan Penjualan Spare Parts', wbf['haeader_table_center']) 
        
        worksheet.write('D7', 'a' , wbf['content'])
        worksheet.write('E7', 'Jasa   KPB ( 1-4)' , wbf['content'])
        worksheet.write('F7', ':' , wbf['center_content'])
        worksheet.write('G7', 'Rp.' , wbf['content'])
        worksheet.merge_range('H%s:J%s' % (7,7),  jasa_kpb, wbf['content_float']) 
        
        worksheet.write('D8', 'b' , wbf['content'])
        worksheet.write('E8', 'Jasa  QS + LR + HR' , wbf['content'])
        worksheet.write('F8', ':' , wbf['center_content'])
        worksheet.write('G8', 'Rp.' , wbf['content'])
        worksheet.merge_range('H%s:J%s' % (8,8), jasa_qs_lr_hr, wbf['content_float']) 
        
        worksheet.write('D9', 'c' , wbf['content'])
        worksheet.write('E9', 'Jasa Claim (C2)' , wbf['content'])
        worksheet.write('F9', ':' , wbf['center_content'])
        worksheet.write('G9', 'Rp.' , wbf['content'])
        worksheet.merge_range('H%s:J%s' % (9,9), jasa_claim, wbf['content_float']) 
        
        worksheet.write('D10', 'd' , wbf['content'])
        worksheet.write('E10', 'Lain Lain' , wbf['content'])
        worksheet.write('F10', ':' , wbf['center_content'])
        worksheet.write('G10', 'Rp.' , wbf['content'])
        worksheet.merge_range('H%s:J%s' % (10,10), jasa_lain, wbf['content_float']) 
        
        worksheet.merge_range('D%s:F%s' % (11,11), 'T  O  T  A  L   J A S A', wbf['content_total']) 
        worksheet.merge_range('G%s:J%s' % (11,11), jasa_kpb+jasa_qs_lr_hr+jasa_claim+jasa_lain , wbf['content_float_bold']) 
        
        worksheet.merge_range('L%s:M%s' % (7,7), 'a Spare Parts', wbf['content']) 
        worksheet.write('N7', ':  Rp.' , wbf['center_content'])
        worksheet.merge_range('O%s:S%s' % (7,7), sparepart, wbf['content_float']) 
       
 
        worksheet.merge_range('L%s:M%s' % (8,8), 'b Oli (Amount & Botol)', wbf['content']) 
        worksheet.write('N8', ':  Rp.' , wbf['center_content'])
        worksheet.merge_range('O%s:Q%s' % (8,8), oli, wbf['content_float']) 
        worksheet.write('R8', 'Qty :' , wbf['content'])
        worksheet.write('S8', count_oli , wbf['content_float'])

        worksheet.merge_range('L%s:M%s' % (9,9), 'c Tire (Amount & Qty)', wbf['content']) 
        worksheet.write('N9', ':  Rp.' , wbf['center_content'])
        worksheet.merge_range('O%s:Q%s' % (9,9), tire, wbf['content_float']) 
        worksheet.write('R9', 'Qty :' , wbf['content'])
        worksheet.write('S9', count_tire , wbf['content_float'])
        

        worksheet.merge_range('L%s:M%s' % (10,10), 'd Lain - Lain', wbf['content']) 
        worksheet.write('N10', ':  Rp.' , wbf['center_content'])
        worksheet.merge_range('O%s:S%s' % (10,10), '', wbf['content']) 
      
        
        worksheet.merge_range('L%s:P%s' % (11,11), 'T  O  T  A  L    P A R T S', wbf['content_total']) 
        worksheet.merge_range('Q%s:S%s' % (11,11), sparepart+oli+tire, wbf['content_float_bold']) 
        
        
        worksheet.merge_range('D%s:J%s' % (13,13), 'Penghasilan Bengkel  ( Jasa + Penjualan Spare Parts )', wbf['content_grand_total']) 
        worksheet.write('K13', ':' , wbf['center_content'])
        worksheet.merge_range('L%s:S%s' % (13,13), jasa_kpb+jasa_qs_lr_hr+jasa_claim+jasa_lain +sparepart+oli+tire, wbf['content_float']) 
        
        worksheet.merge_range('D%s:S%s' % (15,15), 'III.   Jumlah Unit Sepeda Motor Yang Dikerjakan', wbf['haeader_table_center']) 
        worksheet.merge_range('D%s:D%s' % (16,19), 'No', wbf['header_table_v_center'])  
        worksheet.merge_range('E%s:E%s' % (16,19), 'Type Sepeda Motor Honda', wbf['header_table_v_center'])  
        worksheet.merge_range('F%s:I%s' % (16,17), 'ASS', wbf['header_table_v_center_bold']) 
        worksheet.merge_range('F%s:F%s' % (18,19), 'KPB1', wbf['header_table_v_center'])  
        worksheet.merge_range('G%s:G%s' % (18,19), 'KPB2', wbf['header_table_v_center'])  
        worksheet.merge_range('H%s:H%s' % (18,19), 'KPB3', wbf['header_table_v_center'])  
        worksheet.merge_range('I%s:I%s' % (18,19), 'KPB4', wbf['header_table_v_center'])  
        worksheet.merge_range('J%s:J%s' % (16,19), 'Claim \n C2', wbf['header_table_v_center'])  
        worksheet.merge_range('K%s:M%s' % (16,16), 'QS', wbf['header_table_v_center_bold']) 
        worksheet.merge_range('K%s:K%s' % (17,18), 'Paket \n Lengkap', wbf['header_table_v_center'])   
        worksheet.merge_range('L%s:L%s' % (17,18), 'Paket \n Ringan', wbf['header_table_v_center']) 
        worksheet.merge_range('M%s:M%s' % (17,18), 'Ganti \n Oli +', wbf['header_table_v_center']) 
        worksheet.write('K19', 'CS' , wbf['header_table_v_center_bold'])
        worksheet.write('L19', 'LS' , wbf['header_table_v_center_bold'])
        worksheet.write('M19', 'OR +' , wbf['header_table_v_center_bold'])
        worksheet.merge_range('N%s:N%s' % (16,19), 'LR \n Service \n Ringan', wbf['header_table_v_center'])  
        worksheet.merge_range('O%s:O%s' % (16,19), 'HR \n Service \n Berat', wbf['header_table_v_center'])
        worksheet.merge_range('P%s:Q%s' % (16,19), 'Total \n Pekerjaan', wbf['header_table_v_center_bold'])
        worksheet.merge_range('R%s:R%s' % (16,19), 'Total \n Unit', wbf['header_table_v_center_bold'])
        worksheet.merge_range('S%s:S%s' % (16,19), 'JR \n Pekerjaan \n Ulang', wbf['header_table_v_center'])
        
        worksheet.write('D20', 'A' , wbf['header_table_v_center_bold'])
        worksheet.merge_range('E%s:S%s' % (20,20), 'CUB', wbf['header_table_v_bold'])
        row=20
        rowsaldo = row
        row+=1             
        no = 1  
        row1 = row

        grand_count_kpb1=0
        grand_count_kpb2=0
        grand_count_kpb3=0
        grand_count_kpb4=0
        grand_count_claim = 0
        grand_count_unit = 0
        grand_count_jr = 0
        grand_count_cs = 0
        grand_count_ls = 0
        grand_count_or = 0
        grand_count_lr = 0
        grand_count_hr = 0
        grand_count_pekerjaan = 0
        grand_count_jr = 0
        
        for res in ress:
            id_unit  = res[0]
            description_unit = str(res[1].encode('ascii','ignore').decode('ascii')) if res[1] != None else ''
            code_unit = str(res[2].encode('ascii','ignore').decode('ascii')) if res[2] != None else ''
            category = str(res[3].encode('ascii','ignore').decode('ascii')) if res[3] != None else ''
            category_parent = str(res[4].encode('ascii','ignore').decode('ascii')) if res[4] != None else ''
            count_kpb1 = res[5]
            count_kpb2 = res[6]
            count_kpb3 = res[7]
            count_kpb4 = res[8]
            count_claim = res[9]
            count_unit = res[19]
            count_jr = res[11]
            count_cs = res[12]
            count_ls = res[13]
            count_or = res[14]
            count_lr = res[15]
            count_hr = res[16]
            count_pekerjaan = res[17]
            count_jr = res[18]
            
            if category_parent == 'CUB':
                worksheet.write('D%s' % row, no , wbf['content'])                    
                worksheet.write('E%s' % row, description_unit+' ('+code_unit+')' , wbf['content'])
                worksheet.write('F%s' % row, count_kpb1 , wbf['content_float'])
                worksheet.write('G%s' % row, count_kpb2 , wbf['content_float'])
                worksheet.write('H%s' % row, count_kpb3 , wbf['content_float'])
                worksheet.write('I%s' % row, count_kpb4 , wbf['content_float'])
                worksheet.write('J%s' % row, count_claim , wbf['content_float'])
                worksheet.write('K%s' % row, count_cs , wbf['content_float'])
                worksheet.write('L%s' % row, count_ls , wbf['content_float']) 
                worksheet.write('M%s' % row, count_or, wbf['content_float'])  
                worksheet.write('N%s' % row, count_lr , wbf['content_float'])
                worksheet.write('O%s' % row, count_hr , wbf['content_float'])
                worksheet.merge_range('P%s:Q%s' % (row,row), count_pekerjaan, wbf['content_float'])  
                worksheet.write('R%s' % row, count_unit , wbf['content_float'])
                worksheet.write('S%s' % row, count_jr , wbf['content_float'])
                no+=1
                row+=1
                
                grand_count_kpb1 += count_kpb1
                grand_count_kpb2 += count_kpb2
                grand_count_kpb3 += count_kpb3
                grand_count_kpb4 += count_kpb4
                grand_count_claim += count_claim
                grand_count_cs += count_cs
                grand_count_ls += count_ls
                grand_count_or += count_or
                grand_count_lr += count_lr
                grand_count_hr += count_hr
                grand_count_pekerjaan += count_pekerjaan
                grand_count_unit += count_unit
                grand_count_jr += count_jr
               
        worksheet.merge_range('D%s:E%s' % (row,row), 'Total Tipe Cub', wbf['haeader_table_center_right']) 
        worksheet.write('F%s' % (row), grand_count_kpb1, wbf['content_float_bold'])  
        worksheet.write('G%s' % (row), grand_count_kpb2, wbf['content_float_bold'])
        worksheet.write('H%s' % (row), grand_count_kpb3, wbf['content_float_bold'])
        worksheet.write('I%s' % (row), grand_count_kpb4, wbf['content_float_bold'])
        worksheet.write('J%s' % (row), grand_count_claim, wbf['content_float_bold'])
        worksheet.write('K%s' % (row), grand_count_cs, wbf['content_float_bold'])
        worksheet.write('L%s' % (row), grand_count_ls, wbf['content_float_bold'])
        worksheet.write('M%s' % (row), grand_count_or, wbf['content_float_bold'])
        worksheet.write('N%s' % (row), grand_count_lr, wbf['content_float_bold'])
        worksheet.write('O%s' % (row), grand_count_hr, wbf['content_float_bold'])
        worksheet.merge_range('P%s:Q%s' % (row,row), grand_count_pekerjaan, wbf['content_float_bold'])  
        worksheet.write('R%s' % row, grand_count_unit , wbf['content_float_bold'])
        worksheet.write('S%s' % row, grand_count_jr , wbf['content_float_bold'])
        
        
        
        worksheet.write('D%s'%(row+1), 'B' , wbf['header_table_v_center_bold'])  
        worksheet.merge_range('E%s:S%s'%(row+1,row+1), 'Matic' , wbf['header_table_v_bold'])  
        row2 =row   
        no2 = 1
        
        grand_count_kpb1_matic=0
        grand_count_kpb2_matic=0
        grand_count_kpb3_matic=0
        grand_count_kpb4_matic=0
        grand_count_claim_matic = 0
        grand_count_unit_matic = 0
        grand_count_jr_matic = 0
        grand_count_cs_matic = 0
        grand_count_ls_matic = 0
        grand_count_or_matic = 0
        grand_count_lr_matic = 0
        grand_count_hr_matic = 0
        grand_count_pekerjaan_matic = 0
        grand_count_jr_matic = 0
       
        for ress_matic in ress:
           
            id_unit  = ress_matic[0]
            description_unit = str(ress_matic[1].encode('ascii','ignore').decode('ascii')) if ress_matic[1] != None else ''
            code_unit = str(ress_matic[2].encode('ascii','ignore').decode('ascii')) if ress_matic[2] != None else ''
            category = str(ress_matic[3].encode('ascii','ignore').decode('ascii')) if ress_matic[3] != None else ''
            category_parent = str(ress_matic[4].encode('ascii','ignore').decode('ascii')) if ress_matic[4] != None else ''
            count_kpb1 = ress_matic[5]
            count_kpb2 = ress_matic[6]
            count_kpb3 = ress_matic[7]
            count_kpb4 = ress_matic[8]
            count_claim = ress_matic[9]
            count_unit = ress_matic[19]
            count_jr = ress_matic[11]
            count_cs = ress_matic[12]
            count_ls = ress_matic[13]
            count_or = ress_matic[14]
            count_lr = ress_matic[15]
            count_hr = ress_matic[16]
            count_pekerjaan = ress_matic[17]
            count_jr = ress_matic[18]
            
            
            if category_parent == 'AT':
                worksheet.write('D%s' % (row2+2), no2 , wbf['content'])                    
                worksheet.write('E%s' % (row2+2), description_unit+' ('+code_unit+')' , wbf['content'])
                worksheet.write('F%s' % (row2+2), count_kpb1 , wbf['content_float'])
                worksheet.write('G%s' % (row2+2), count_kpb2 , wbf['content_float'])
                worksheet.write('H%s' % (row2+2), count_kpb3 , wbf['content_float'])
                worksheet.write('I%s' % (row2+2), count_kpb4 , wbf['content_float'])
                worksheet.write('J%s' % (row2+2), count_claim , wbf['content_float'])
                worksheet.write('K%s' % (row2+2), count_cs , wbf['content_float'])
                worksheet.write('L%s' % (row2+2), count_ls , wbf['content_float']) 
                worksheet.write('M%s' % (row2+2), count_or, wbf['content_float'])  
                worksheet.write('N%s' % (row2+2), count_lr , wbf['content_float'])
                worksheet.write('O%s' % (row2+2), count_hr , wbf['content_float'])
                worksheet.merge_range('P%s:Q%s' % (row2+2,row2+2), count_pekerjaan, wbf['content_float'])  
                worksheet.write('R%s' % (row2+2), count_unit , wbf['content_float'])
                worksheet.write('S%s' % (row2+2), count_jr , wbf['content_float'])
                row2+=1
                no2+=1
                grand_count_kpb1_matic += count_kpb1
                grand_count_kpb2_matic += count_kpb2
                grand_count_kpb3_matic += count_kpb3
                grand_count_kpb4_matic += count_kpb4
                grand_count_claim_matic += count_claim
                grand_count_cs_matic += count_cs
                grand_count_ls_matic += count_ls
                grand_count_or_matic += count_or
                grand_count_lr_matic += count_lr
                grand_count_hr_matic += count_hr
                grand_count_pekerjaan_matic += count_pekerjaan
                grand_count_unit_matic += count_unit
                grand_count_jr_matic += count_jr
         
        worksheet.merge_range('D%s:E%s' % (row2+2,row2+2), 'Total Tipe Matic', wbf['haeader_table_center_right']) 
        worksheet.write('F%s' % (row2+2), grand_count_kpb1_matic, wbf['content_float_bold'])  
        worksheet.write('G%s' % (row2+2), grand_count_kpb2_matic, wbf['content_float_bold'])
        worksheet.write('H%s' % (row2+2), grand_count_kpb3_matic, wbf['content_float_bold'])
        worksheet.write('I%s' % (row2+2), grand_count_kpb4_matic, wbf['content_float_bold'])
        worksheet.write('J%s' % (row2+2), grand_count_claim_matic, wbf['content_float_bold'])
        worksheet.write('K%s' % (row2+2), grand_count_cs_matic, wbf['content_float_bold'])
        worksheet.write('L%s' % (row2+2), grand_count_ls_matic, wbf['content_float_bold'])
        worksheet.write('M%s' % (row2+2), grand_count_or_matic, wbf['content_float_bold'])
        worksheet.write('N%s' % (row2+2), grand_count_lr_matic, wbf['content_float_bold'])
        worksheet.write('O%s' % (row2+2), grand_count_hr_matic, wbf['content_float_bold'])
        worksheet.merge_range('P%s:Q%s' % (row2+2,row2+2), grand_count_pekerjaan_matic, wbf['content_float_bold'])  
        worksheet.write('R%s' % (row2+2), grand_count_unit_matic , wbf['content_float_bold'])
        worksheet.write('S%s' % (row2+2), grand_count_jr_matic , wbf['content_float_bold'])
        
        
        worksheet.write('D%s'%(row2+3), 'C' , wbf['header_table_v_center_bold'])  
        worksheet.merge_range('E%s:S%s'%(row2+3,row2+3), 'Sport' , wbf['header_table_v_bold'])  
        row3 =row2+4  
        no3 = 1
        
        grand_count_kpb1_sport=0
        grand_count_kpb2_sport=0
        grand_count_kpb3_sport=0
        grand_count_kpb4_sport=0
        grand_count_claim_sport = 0
        grand_count_unit_sport = 0
        grand_count_jr_sport = 0
        grand_count_cs_sport = 0
        grand_count_ls_sport = 0
        grand_count_or_sport = 0
        grand_count_lr_sport = 0
        grand_count_hr_sport = 0
        grand_count_pekerjaan_sport = 0
        grand_count_jr_sport = 0
        for ress_sport in ress:
           
            id_unit  = ress_sport[0]
            description_unit = str(ress_sport[1].encode('ascii','ignore').decode('ascii')) if ress_sport[1] != None else ''
            code_unit = str(ress_sport[2].encode('ascii','ignore').decode('ascii')) if ress_sport[2] != None else ''
            category = str(ress_sport[3].encode('ascii','ignore').decode('ascii')) if ress_sport[3] != None else ''
            category_parent = str(ress_sport[4].encode('ascii','ignore').decode('ascii')) if ress_sport[4] != None else ''
            count_kpb1 = ress_sport[5]
            count_kpb2 = ress_sport[6]
            count_kpb3 = ress_sport[7]
            count_kpb4 = ress_sport[8]
            count_claim = ress_sport[9]
            count_unit = ress_sport[19]
            count_jr = ress_sport[11]
            count_cs = ress_sport[12]
            count_ls = ress_sport[13]
            count_or = ress_sport[14]
            count_lr = ress_sport[15]
            count_hr = ress_sport[16]
            count_pekerjaan = ress_sport[17]
            count_jr = ress_sport[18]
            
            if category_parent == 'SPORT':
                worksheet.write('D%s' % (row3), no3 , wbf['content'])                    
                worksheet.write('E%s' % (row3), description_unit+' ('+code_unit+')' , wbf['content'])
                worksheet.write('F%s' % (row3), count_kpb1 , wbf['content_float'])
                worksheet.write('G%s' % (row3), count_kpb2 , wbf['content_float'])
                worksheet.write('H%s' % (row3), count_kpb3 , wbf['content_float'])
                worksheet.write('I%s' % (row3), count_kpb4 , wbf['content_float'])
                worksheet.write('J%s' % (row3), count_claim , wbf['content_float'])
                worksheet.write('K%s' % (row3), count_cs , wbf['content_float'])
                worksheet.write('L%s' % (row3), count_ls , wbf['content_float']) 
                worksheet.write('M%s' % (row3), count_or, wbf['content_float'])  
                worksheet.write('N%s' % (row3), count_lr , wbf['content_float'])
                worksheet.write('O%s' % (row3), count_hr , wbf['content_float'])
                worksheet.merge_range('P%s:Q%s' % (row3,row3), count_pekerjaan, wbf['content_float'])  
                worksheet.write('R%s' % (row3), count_unit , wbf['content_float'])
                worksheet.write('S%s' % (row3), count_jr , wbf['content_float'])
                row3+=1
                no3+=1
                grand_count_kpb1_sport += count_kpb1
                grand_count_kpb2_sport += count_kpb2
                grand_count_kpb3_sport += count_kpb3
                grand_count_kpb4_sport += count_kpb4
                grand_count_claim_sport += count_claim
                grand_count_cs_sport += count_cs
                grand_count_ls_sport += count_ls
                grand_count_or_sport += count_or
                grand_count_lr_sport += count_lr
                grand_count_hr_sport += count_hr
                grand_count_pekerjaan_sport += count_pekerjaan
                grand_count_unit_sport += count_unit
                grand_count_jr_sport += count_jr

        worksheet.merge_range('D%s:E%s' % (row3,row3), 'Total Tipe Sport', wbf['haeader_table_center_right']) 
        worksheet.write('F%s' % (row3), grand_count_kpb1_sport, wbf['content_float_bold'])  
        worksheet.write('G%s' % (row3), grand_count_kpb2_sport, wbf['content_float_bold'])
        worksheet.write('H%s' % (row3), grand_count_kpb3_sport, wbf['content_float_bold'])
        worksheet.write('I%s' % (row3), grand_count_kpb4_sport, wbf['content_float_bold'])
        worksheet.write('J%s' % (row3), grand_count_claim_sport, wbf['content_float_bold'])
        worksheet.write('K%s' % (row3), grand_count_cs_sport, wbf['content_float_bold'])
        worksheet.write('L%s' % (row3), grand_count_ls_sport, wbf['content_float_bold'])
        worksheet.write('M%s' % (row3), grand_count_or_sport, wbf['content_float_bold'])
        worksheet.write('N%s' % (row3), grand_count_lr_sport, wbf['content_float_bold'])
        worksheet.write('O%s' % (row3), grand_count_hr_sport, wbf['content_float_bold'])
        worksheet.merge_range('P%s:Q%s' % (row3,row3), grand_count_pekerjaan_sport, wbf['content_float_bold'])  
        worksheet.write('R%s' % (row3), grand_count_unit_sport , wbf['content_float_bold'])
        worksheet.write('S%s' % (row3), grand_count_jr_sport , wbf['content_float_bold'])
        
        all_total_kpb1=grand_count_kpb1+grand_count_kpb1_matic+grand_count_kpb1_sport
        all_total_kpb2=grand_count_kpb2+grand_count_kpb2_matic+grand_count_kpb2_sport
        all_total_kpb3=grand_count_kpb3+grand_count_kpb3_matic+grand_count_kpb3_sport
        all_total_kpb4=grand_count_kpb4+grand_count_kpb4_matic+grand_count_kpb4_sport
        all_total_claim = grand_count_claim+grand_count_claim_matic+grand_count_claim_sport
        all_total_cs = grand_count_cs+grand_count_cs_matic+grand_count_cs_sport
        all_total_ls = grand_count_ls+grand_count_ls_matic+grand_count_ls_sport
        all_total_or = grand_count_or+grand_count_or_matic+grand_count_or_sport
        all_total_lr = grand_count_lr+grand_count_lr_matic+grand_count_lr_sport
        all_total_hr = grand_count_hr+grand_count_hr_matic+grand_count_hr_sport
        all_total_pekerjaan = grand_count_pekerjaan+grand_count_pekerjaan_matic+grand_count_pekerjaan_sport
        all_total_unit = grand_count_unit+grand_count_unit_matic+grand_count_unit_sport
        all_total_jr = grand_count_jr+grand_count_jr_matic+grand_count_jr_sport
        
        worksheet.merge_range('D%s:E%s' % (row3+1,row3+1), 'GRAND TOTAL', wbf['haeader_table_center_right'])
        worksheet.write('F%s' % (row3+1), all_total_kpb1, wbf['content_float_bold'])  
        worksheet.write('G%s' % (row3+1), all_total_kpb2, wbf['content_float_bold'])
        worksheet.write('H%s' % (row3+1), all_total_kpb3, wbf['content_float_bold'])
        worksheet.write('I%s' % (row3+1), all_total_kpb4, wbf['content_float_bold'])
        worksheet.write('J%s' % (row3+1), all_total_claim, wbf['content_float_bold'])
        worksheet.write('K%s' % (row3+1), all_total_cs, wbf['content_float_bold'])
        worksheet.write('L%s' % (row3+1), all_total_ls, wbf['content_float_bold'])
        worksheet.write('M%s' % (row3+1), all_total_or, wbf['content_float_bold'])
        worksheet.write('N%s' % (row3+1), all_total_lr, wbf['content_float_bold'])
        worksheet.write('O%s' % (row3+1), all_total_hr, wbf['content_float_bold'])
        worksheet.merge_range('P%s:Q%s' % (row3+1,row3+1), all_total_pekerjaan, wbf['content_float_bold'])  
        worksheet.write('R%s' % (row3+1), all_total_unit , wbf['content_float_bold'])
        worksheet.write('S%s' % (row3+1), all_total_jr , wbf['content_float_bold']) 
        
        
        
        worksheet.merge_range('D%s:J%s' % (row3+4,row3+4), 'IV.  Laporan Pengeluaran Bengkel', wbf['haeader_table_center']) 
        worksheet.write('D%s'%(row3+5), 'a.' , wbf['content'])  
        worksheet.merge_range('E%s:F%s' % (row3+5,row3+5), 'Bensin', wbf['content'])  
        worksheet.write('G%s'%(row3+5), 'Rp.' , wbf['content']) 
        worksheet.merge_range('H%s:J%s' % (row3+5,row3+5), '', wbf['content_float']) 
        
        worksheet.write('D%s'%(row3+6), 'b.' , wbf['content'])  
        worksheet.merge_range('E%s:F%s' % (row3+6,row3+6), 'Air Accu', wbf['content'])  
        worksheet.write('G%s'%(row3+6), 'Rp.' , wbf['content']) 
        worksheet.merge_range('H%s:J%s' % (row3+6,row3+6), '', wbf['content_float']) 
        
        worksheet.write('D%s'%(row3+7), 'c.' , wbf['content'])  
        worksheet.merge_range('E%s:F%s' % (row3+7,row3+7), 'Lain - Lain', wbf['content'])  
        worksheet.write('G%s'%(row3+7), 'Rp.' , wbf['content']) 
        worksheet.merge_range('H%s:J%s' % (row3+7,row3+7), '', wbf['content'])  
        
        worksheet.merge_range('D%s:F%s' % (row3+8,row3+8), 'T O T A  L', wbf['haeader_table_center'])  
        worksheet.merge_range('G%s:J%s' % (row3+8,row3+8), '', wbf['content_float'])
        
        
        worksheet.merge_range('M%s:S%s' % (row3+3,row3+3), 'V.  JUMLAH HARI KERJA DALAM BULAN INI', wbf['haeader_table_center'])  
        worksheet.merge_range('M%s:S%s' % (row3+4,row3+5), '', wbf['haeader_table_center'])
        worksheet.merge_range('M%s:S%s' % (row3+6,row3+7), 'VI.  RATA-RATA PEKERJAAN PER HARI DALAM BULAN INI', wbf['haeader_table_center']) 
        worksheet.merge_range('M%s:S%s' % (row3+8,row3+8), '', wbf['haeader_table_center']) 
     
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

wtc_report_lbb()
