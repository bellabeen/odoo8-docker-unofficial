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
   
    _inherit = "wtc.report.lbb.wizard"

    wbf = {}

    def _print_excel_report_prestasi_mekanik(self, cr, uid, ids, data, context=None): 
               
        val = self.browse(cr, uid, ids, context={})[0]
        branch_id = data['branch_id']  
        start_date = data['start_date']
        end_date = data['end_date']
        tz = '7 hours'
        start_date_a= datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date_a= datetime.strptime(end_date, "%Y-%m-%d").date()
        start_date_min = start_date_a + relativedelta(months=-1)
        end_date_min = end_date_a + relativedelta(months=-1)

        
        query_where = ""
        query_group = "GROUP BY mechanic.name, wo.mekanik_id"
        query_order= " order by mechanic.name "
        
        if branch_id :
            query_where += "  AND wo.branch_id = '%s'" % str(val.branch_id.id)
        if start_date :
            query_where += " AND wo.date >= '%s'" % str(start_date)
        if end_date :
            end_date = end_date + ' 23:59:59'
            query_where += " AND wo.date <= to_timestamp('%s', 'YYYY-MM-DD HH24:MI:SS') + interval '%s'" % (end_date,tz)
        
    
        query = """
                    SELECT  
                    
                    COALESCE(sales.name,'') as sales_name 
                    , COALESCE(wo_inv.cnt_kpb_1,0) as cnt_kpb_1
                    , COALESCE(wo_inv.cnt_kpb_2,0) as cnt_kpb_2
                    , COALESCE(wo_inv.cnt_kpb_3,0) as cnt_kpb_3
                    , COALESCE(wo_inv.cnt_kpb_4,0) as cnt_kpb_4
                    , COALESCE(wo_inv.cnt_cla,0) as cnt_cla
                    , COALESCE(wo_jasa.qty_cs,0) as qty_cs
                    , COALESCE(wo_jasa.qty_ls,0) as qty_ls
                    , COALESCE(wo_jasa.qty_or,0) as qty_or
                    , COALESCE(wo_jasa.qty_lr,0) as qty_lr
                    , COALESCE(wo_jasa.qty_hr,0) as qty_hr
                    , COALESCE(wo_inv.cnt_inv,0) as cnt_inv
                    , COALESCE(wo_unit.unit_entry,0) as unit_entry
                    , COALESCE(wo_inv.cnt_war,0) as cnt_war
                    , COALESCE(jam_terpakai.jam_terpakai,0) as jam_terpakai
                    , COALESCE(absensi.absen,0) as total_tidak_masuk
                    , COALESCE(absensi.total_masuk,0) as total_masuk
                    FROM 
                    (SELECT wo.mekanik_id
                    ,wo.branch_id
                    , COUNT(wo.id) AS cnt_inv
                    , COUNT(CASE WHEN wo.type = 'KPB' AND wo.kpb_ke = '1' THEN wo.id END) AS cnt_kpb_1
                    , COUNT(CASE WHEN wo.type = 'KPB' AND wo.kpb_ke = '2' THEN wo.id END) AS cnt_kpb_2
                    , COUNT(CASE WHEN wo.type = 'KPB' AND wo.kpb_ke = '3' THEN wo.id END) AS cnt_kpb_3
                    , COUNT(CASE WHEN wo.type = 'KPB' AND wo.kpb_ke = '4' THEN wo.id END) AS cnt_kpb_4
                    , COUNT(CASE WHEN wo.type = 'CLA' THEN wo.id END) AS cnt_cla
                    , COUNT(CASE WHEN wo.type = 'WAR' THEN wo.id END) AS cnt_war
                    FROM wtc_work_order wo
                    LEFT JOIN  res_users as users     ON users.id=wo.mekanik_id
                    WHERE wo.branch_id=%s """ % str(val.branch_id.id)+"""
                    and wo.date BETWEEN '%s'""" % str(start_date) + """  AND '%s'""" % str(end_date) +"""
                    GROUP BY wo.mekanik_id,wo.branch_id) AS wo_inv
                    FULL OUTER JOIN
                    (SELECT branch_id 
                    ,mekanik_id
                    ,SUM(cnt_per_date) AS unit_entry
                    FROM (
                    SELECT wo.branch_id,wo.mekanik_id, wo.date, COUNT(DISTINCT lot_id) AS cnt_per_date
                    FROM wtc_work_order wo
                    WHERE wo.type <> 'WAR' AND wo.type <> 'SLS' 
                    AND wo.date BETWEEN '%s'""" % str(start_date) + """  AND '%s'""" % str(end_date) +"""
                    GROUP BY wo.branch_id,wo.mekanik_id, wo.date ) wo_per_date
                    GROUP BY branch_id,mekanik_id) AS wo_unit
                    ON wo_inv.branch_id = wo_unit.branch_id
                    AND wo_inv.mekanik_id = wo_unit.mekanik_id
                    FULL OUTER JOIN
                    (    SELECT 
                    branch.id as branch_id,
                    sales.user_id ,
                    sum(jumlah_hari_kerja-total_absensi) absen,
                    sum(total_absensi) total_masuk
                    from wtc_absensi as absensi
                    
                    LEFT JOIN hr_employee hr_sales ON absensi.nip = hr_sales.nip 
                    LEFT JOIN resource_resource sales ON sales.id = hr_sales.resource_id 
                    LEFT JOIN res_users as users ON users.id = sales.user_id 
                    LEFT JOIN wtc_branch as branch ON branch.id=hr_sales.branch_id
                    
                    where branch.id=%s """ % str(val.branch_id.id)+"""  AND absensi.bulan='%s'""" % start_date[:-3] + """
                    GROUP BY branch.id,sales.user_id 
                    
                    
                    ) as absensi
                    ON absensi.branch_id = wo_unit.branch_id
                    AND absensi.user_id = wo_unit.mekanik_id
                    FULL OUTER JOIN
                    (                        select wo.branch_id,wo.mekanik_id
                    ,date_part( 'epoch',  SUM(age(wo_start.finish,wo_start.start) )::interval   )/3600 as jam_terpakai
                    from wtc_work_order as wo
                    LEFT JOIN wtc_start_stop_wo AS wo_start
                    ON wo.id=wo_start.work_order_id 
                    LEFT JOIN wtc_branch as branch ON branch.id=wo.branch_id
                    where 1=1
                    and  wo.date BETWEEN '%s'""" % str(start_date) + """  AND '%s'""" % str(end_date) +"""
                    GROUP BY wo.branch_id,wo.mekanik_id
                    
                    ) as jam_terpakai
                    ON jam_terpakai.branch_id = wo_unit.branch_id
                    AND jam_terpakai.mekanik_id = wo_unit.mekanik_id
                    FULL OUTER JOIN
                    (SELECT wo.branch_id,wo.mekanik_id
                    , SUM(CASE WHEN wol.categ_id = 'Service' THEN wol.price_unit*(1-COALESCE(wol.discount,0)/100) END) amt_jasa
                    , SUM(CASE WHEN wol.categ_id = 'Sparepart' AND pc.name NOT IN ( 'OLI','OIL') THEN wol.price_unit*(1-COALESCE(wol.discount,0)/100) END) amt_part
                    , SUM(CASE WHEN wol.categ_id = 'Sparepart' AND pc.name = 'OIL' THEN wol.price_unit*(1-COALESCE(wol.discount,0)/100) END) amt_oil
                    , SUM(wol.price_unit*(1-COALESCE(wol.discount,0)/100)) amt_total
                    , COUNT(CASE WHEN wol.categ_id = 'Service' AND pc2.name = 'KPB' THEN wol.id END) qty_kpb
                    , COUNT(CASE WHEN wol.categ_id = 'Service' AND pc.name = 'CS' THEN wol.id END) qty_cs
                    , COUNT(CASE WHEN wol.categ_id = 'Service' AND pc.name = 'LS' THEN wol.id END) qty_ls
                    , COUNT(CASE WHEN wol.categ_id = 'Service' AND pc.name = 'OR+' THEN wol.id END) qty_or
                    , COUNT(CASE WHEN wol.categ_id = 'Service' AND pc2.name = 'QS' THEN wol.id END) qty_qs
                    , COUNT(CASE WHEN wol.categ_id = 'Service' AND pc.name = 'LR' THEN wol.id END) qty_lr
                    , COUNT(CASE WHEN wol.categ_id = 'Service' AND pc.name = 'HR' THEN wol.id END) qty_hr
                    , COUNT(CASE WHEN wol.categ_id = 'Service' AND pc.name = 'CLA' THEN wol.id END) qty_cla
                    , COUNT(CASE WHEN wol.categ_id = 'Service' THEN wol.id END) qty_total
                    FROM wtc_work_order wo
                    INNER JOIN wtc_work_order_line wol ON wo.id = wol.work_order_id
                    LEFT JOIN product_product p ON wol.product_id = p.id 
                    LEFT JOIN product_template pt ON p.product_tmpl_id = pt.id 
                    LEFT JOIN product_category pc ON pt.categ_id = pc.id 
                    LEFT JOIN product_category pc2 ON pc.parent_id = pc2.id
                    WHERE wo.date BETWEEN '%s'""" % str(start_date) + """  AND '%s'""" % str(end_date) +"""
                    GROUP BY wo.branch_id,wo.mekanik_id) AS wo_jasa
                    ON wo_inv.branch_id = wo_jasa.branch_id
                    AND wo_inv.mekanik_id = wo_jasa.mekanik_id
                    
                    
                    INNER JOIN res_users users ON users.id = COALESCE( wo_inv.mekanik_id, COALESCE(wo_unit.mekanik_id, wo_jasa.mekanik_id))
                    INNER JOIN wtc_branch c ON c.id = COALESCE(wo_inv.branch_id, COALESCE(wo_unit.branch_id, wo_jasa.branch_id))
                    LEFT JOIN resource_resource sales ON users.id = sales.user_id 
                    LEFT JOIN hr_employee hr_sales ON sales.id = hr_sales.resource_id 
                    LEFT JOIN hr_job job ON hr_sales.job_id = job.id 
                    
                    where c.id=%s """ % str(val.branch_id.id)+"""
                    """ 
        cr.execute (query)
        ress = cr.fetchall()
        
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('PRESTASI MEKANIK')
        worksheet.set_column('A1:A1', 2)
        worksheet.set_column('B1:B1', 2)
        worksheet.set_column('C1:C1', 2)
        worksheet.set_column('D1:D1', 25)
        worksheet.set_column('E1:E1', 6)
        worksheet.set_column('F1:F1', 6)
        worksheet.set_column('G1:G1', 6)
        worksheet.set_column('H1:H1', 6)
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
        worksheet.set_column('N6:N6', 5)
        worksheet.set_column('O1:O1', 2)
        worksheet.set_column('O6:O6', 5)
        worksheet.set_column('P1:P1', 2)
        worksheet.set_column('P6:P6', 5)
        worksheet.set_column('Q1:Q1', 2)
        worksheet.set_column('Q7:Q7', 15)
        worksheet.set_column('Q8:Q8', 15)
        worksheet.set_column('Q9:Q9', 8)
        worksheet.set_column('Q10:Q10', 6)
        worksheet.set_column('R1:R1', 2)
        worksheet.set_column('R16:R16', 5)
        worksheet.set_column('S1:S1', 2)
        worksheet.set_column('S6:S6', 9)
        worksheet.set_column('T1:T1', 7 )
        worksheet.set_column('U1:U1', 7)
        worksheet.set_column('V1:V1', 9)
        worksheet.set_column('W1:W1', 7)
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
       
        
        filename = 'Laporan Prestasi Mekanik'+str(date)+'.xlsx'   

             
        worksheet.merge_range('C%s:V%s' % (1,1), 'LAPORAN MEKANIK', wbf['title']) 
        worksheet.merge_range('C%s:V%s' % (4,4), 'III.   Laporan Prestasi Mekanik Dalam Bulan Ini %s s/d %s' %(str(start_date),str(end_date)), wbf['header_table_v_center_bold'])
        worksheet.merge_range('C%s:C%s' % (5,8), 'No', wbf['header_table_v_center'])
        worksheet.merge_range('D%s:D%s' % (5,8), 'NAMA MEKANIK', wbf['header_table_v_center_bold'])
        worksheet.merge_range('E%s:E%s' % (5,8), 'ABSEN \n (hari)', wbf['header_table_v_center_bold'])
        worksheet.merge_range('F%s:F%s' % (5,8), 'HADIR \n (hari)', wbf['header_table_v_center_bold'])
        worksheet.merge_range('G%s:G%s' % (5,8), 'P M T Ke \n (0/1/2/3)', wbf['header_table_v_center_bold'])
        worksheet.merge_range('H%s:H%s' % (5,8), 'Jumlah \n LKH', wbf['header_table_v_center_bold'])
        worksheet.merge_range('I%s:L%s' % (5,6), 'ASS', wbf['header_table_v_center_bold'])
        worksheet.merge_range('I%s:I%s' % (7,8), 'KPB1', wbf['header_table_v_center'])
        worksheet.merge_range('J%s:J%s' % (7,8), 'KPB2', wbf['header_table_v_center'])
        worksheet.merge_range('K%s:K%s' % (7,8), 'KPB3', wbf['header_table_v_center'])
        worksheet.merge_range('L%s:L%s' % (7,8), 'KPB4', wbf['header_table_v_center'])
        worksheet.merge_range('M%s:M%s' % (5,8), 'Claim \n C2', wbf['header_table_v_center_bold'])
        worksheet.merge_range('N%s:P%s' % (5,5), 'QS', wbf['header_table_v_center_bold'])
        worksheet.write('N8', 'CS' , wbf['header_table_v_center_bold'])
        worksheet.write('O8', 'LS' , wbf['header_table_v_center_bold'])
        worksheet.write('P8', 'OR +' , wbf['header_table_v_center_bold'])
        worksheet.merge_range('N%s:N%s' % (6,7), 'Paket \n Lengkap', wbf['header_table_v_center'])
        worksheet.merge_range('O%s:O%s' % (6,7), 'Paket \n Ringan', wbf['header_table_v_center'])
        worksheet.merge_range('P%s:P%s' % (6,7), 'Ganti \n Oli +', wbf['header_table_v_center'])
        worksheet.merge_range('Q%s:Q%s' % (5,8), 'LR \n Servis \n Ringan', wbf['header_table_v_center_bold'])
        worksheet.merge_range('R%s:R%s' % (5,8), 'HR \n Servis \n Berat', wbf['header_table_v_center_bold'])
        worksheet.merge_range('S%s:S%s' % (5,8), 'TOTAL \n PEKERJAAN', wbf['header_table_v_center_bold'])
        worksheet.merge_range('T%s:T%s' % (5,8), 'TOTAL \n UNIT', wbf['header_table_v_center_bold'])
        worksheet.merge_range('U%s:U%s' % (5,8), 'JR \n Pekerjaan \n Ulang', wbf['header_table_v_center_bold'])
        worksheet.merge_range('V%s:V%s' % (5,8), 'Jam Terpakai \n ( Menit )', wbf['header_table_v_center_bold'])
        row=8
        rowsaldo = row
        row+=1             
        no = 1  
        row1 = row
        
        grand_total_kpb1=0
        grand_total_kpb2=0
        grand_total_kpb3=0
        grand_total_kpb4=0
        grand_total_claim = 0
        grand_total_cs = 0
        grand_total_ls = 0
        grand_total_or = 0
        grand_total_lr = 0
        grand_total_hr = 0
        grand_total_pekerjaan = 0
        grand_total_unit = 0
        grand_total_jr = 0
        
        query_group_total = "GROUP BY wo.mekanik_id"
        for res in ress:
            
            nama_mekanik = str(res[0].encode('ascii','ignore').decode('ascii')) if res[0] != None else ''
            total_kpb1 = res[1]
            total_kpb2 = res[2]
            total_kpb3 = res[3]   
            total_kpb4 = res[4]
            total_claim = res[5]
            total_cs = res[6]
            total_ls = res[7]
            total_or = res[8]
            total_lr = res[9]
            total_hr = res[10]
            total_pekerjaan = res[11]
            total_unit = res[12]
            total_jr = res[13]
            jam_terpakai = res[14]
            total_tidak_masuk = res[15]
            total_masuk = res[16]
            
            worksheet.write('C%s' % row, no , wbf['content'])
            worksheet.write('D%s' % row, nama_mekanik , wbf['content'])
            worksheet.write('E%s' % row, total_tidak_masuk , wbf['content_float'])
            worksheet.write('F%s' % row, total_masuk , wbf['content_float'])
            worksheet.write('G%s' % row, '' , wbf['content_float'])
            worksheet.write('H%s' % row, '' , wbf['content_float'])
            worksheet.write('I%s' % row, total_kpb1 , wbf['content_float'])
            worksheet.write('J%s' % row, total_kpb2 , wbf['content_float'])
            worksheet.write('K%s' % row, total_kpb3 , wbf['content_float'])
            worksheet.write('L%s' % row, total_kpb4 , wbf['content_float'])
            worksheet.write('M%s' % row, total_claim , wbf['content_float'])
            worksheet.write('N%s' % row, total_cs , wbf['content_float'])
            worksheet.write('O%s' % row, total_ls , wbf['content_float'])
            worksheet.write('P%s' % row, total_or , wbf['content_float'])
            worksheet.write('Q%s' % row, total_lr , wbf['content_float'])
            worksheet.write('R%s' % row, total_hr , wbf['content_float'])
            worksheet.write('S%s' % row, total_pekerjaan , wbf['content_float'])
            worksheet.write('T%s' % row, total_unit , wbf['content_float'])
            worksheet.write('U%s' % row, total_jr , wbf['content_float'])
            worksheet.write('V%s' % row, str(jam_terpakai)+' Jam' , wbf['content'])
        
            no+=1
            row+=1
            
            grand_total_kpb1 += total_kpb1
            grand_total_kpb2 += total_kpb2
            grand_total_kpb3 += total_kpb3
            grand_total_kpb4 += total_kpb4
            grand_total_claim += total_claim
            grand_total_cs += total_cs
            grand_total_ls += total_ls
            grand_total_or += total_or
            grand_total_lr += total_lr
            grand_total_hr += total_hr
            grand_total_pekerjaan += total_pekerjaan
            grand_total_unit += total_unit
            grand_total_jr += total_jr
        
        worksheet.merge_range('C%s:D%s' % (row,row), 'TOTAL', wbf['content_total']) 
        worksheet.write('E%s' % row, '' , wbf['content_float_bold'])
        worksheet.write('F%s' % row, '' , wbf['content_float_bold'])
        worksheet.write('G%s' % row, '' , wbf['content_float_bold'])
        worksheet.write('H%s' % row, '' , wbf['content_float_bold'])
        worksheet.write('I%s' % row, grand_total_kpb1 , wbf['content_float_bold'])
        worksheet.write('J%s' % row, grand_total_kpb2 , wbf['content_float_bold'])
        worksheet.write('K%s' % row, grand_total_kpb3 , wbf['content_float_bold'])
        worksheet.write('L%s' % row, grand_total_kpb4 , wbf['content_float_bold'])
        worksheet.write('M%s' % row, grand_total_claim , wbf['content_float_bold'])
        worksheet.write('N%s' % row, grand_total_cs , wbf['content_float_bold'])
        worksheet.write('O%s' % row, grand_total_ls , wbf['content_float_bold'])
        worksheet.write('P%s' % row, grand_total_or , wbf['content_float_bold'])
        worksheet.write('Q%s' % row, grand_total_lr , wbf['content_float_bold'])
        worksheet.write('R%s' % row, grand_total_hr , wbf['content_float_bold'])
        worksheet.write('S%s' % row, grand_total_pekerjaan , wbf['content_float_bold'])
        worksheet.write('T%s' % row, grand_total_unit , wbf['content_float_bold'])
        worksheet.write('U%s' % row, grand_total_jr , wbf['content_float_bold'])
        worksheet.write('V%s' % row, '' , wbf['content_float_bold'])
            
        worksheet.merge_range('C%s:V%s' % (row+1,row+1), '    ASISTEN MEKANIK', wbf['header_table_v_bold']) 
        worksheet.write('C%s' % (row+2), 'No' , wbf['header_table_v_center'])
    
        for loop in xrange(1,4):
           worksheet.write('C%s' % (row+loop+2), loop , wbf['content'])
           worksheet.write('D%s' % (row+loop+2) ,'', wbf['content'])
           worksheet.write('E%s' % (row+loop+2) ,'', wbf['content'])
           worksheet.write('F%s' % (row+loop+2) ,'', wbf['content'])
           worksheet.write('G%s' % (row+loop+2) ,'', wbf['content'])
           worksheet.write('H%s' % (row+loop+2) ,'', wbf['content'])
           worksheet.write('I%s' % (row+loop+2) ,'', wbf['content'])
           worksheet.write('J%s' % (row+loop+2) ,'', wbf['content'])
           worksheet.write('K%s' % (row+loop+2) ,'', wbf['content'])
           worksheet.write('L%s' % (row+loop+2) ,'', wbf['content'])
           worksheet.write('M%s' % (row+loop+2) ,'', wbf['content'])
           worksheet.write('N%s' % (row+loop+2) ,'', wbf['content'])
           worksheet.write('O%s' % (row+loop+2) ,'', wbf['content'])
           worksheet.write('P%s' % (row+loop+2) ,'', wbf['content'])
           worksheet.write('Q%s' % (row+loop+2) ,'', wbf['content'])
           worksheet.write('R%s' % (row+loop+2) ,'', wbf['content'])
           worksheet.write('S%s' % (row+loop+2) ,'', wbf['content'])
           worksheet.write('T%s' % (row+loop+2) ,'', wbf['content'])
           worksheet.write('U%s' % (row+loop+2) ,'', wbf['content'])
           worksheet.write('V%s' % (row+loop+2) ,'', wbf['content'])
           
        worksheet.merge_range('C%s:D%s' % (row+5,row+5), 'TOTAL', wbf['content_total'])   
        worksheet.merge_range('C%s:V%s' % (row+6,row+6), '    TURN OVER  MECHANIC (MEKANIK KELUAR)', wbf['header_table_v_bold'])  
  
        worksheet.write('C%s' % (row+7), 'No' , wbf['header_table_v_center'])
        worksheet.merge_range('D%s:G%s' % (row+7,row+7), 'N A M A    M  E  K  A  N  I  K', wbf['header_table_v_center'])  
        worksheet.merge_range('H%s:K%s' % (row+7,row+7), 'Bergabung Sejak Tanggal', wbf['header_table_v_center'])  
        worksheet.merge_range('L%s:O%s' % (row+7,row+7), 'Mengundurkan Diri Tanggal', wbf['header_table_v_center']) 
        worksheet.merge_range('P%s:V%s' % (row+7,row+7), 'Alasan Keluar', wbf['header_table_v_center'])
         
        for loop_2 in xrange(1,4):
            
            worksheet.write('C%s' % (row+loop_2+7), loop_2 , wbf['content'])
            worksheet.merge_range('D%s:G%s' % (row+loop_2+7,row+loop_2+7), '', wbf['content'])  
            worksheet.merge_range('H%s:K%s' % (row+loop_2+7,row+loop_2+7), '', wbf['content'])  
            worksheet.merge_range('L%s:O%s' % (row+loop_2+7,row+loop_2+7), '', wbf['content']) 
            worksheet.merge_range('P%s:V%s' % (row+loop_2+7,row+loop_2+7), '', wbf['content'])
        

        
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()
