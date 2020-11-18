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

    def _print_excel_report_wpp(self, cr, uid, ids, data, context=None): 
        val = self.browse(cr, uid, ids, context={})[0]
        branch_id = data['branch_id']  
        start_date = data['start_date']
        end_date = data['end_date']
        tz = '7 hours'
        
        start_date_a= datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date_a= datetime.strptime(end_date, "%Y-%m-%d").date()
        start_date_min = start_date_a + relativedelta(months=-1)
        end_date_min = end_date_a + relativedelta(months=-1)
        
        query="""
                SELECT 
                    b.code
                    , b.name
                    , COALESCE(wo_jasa.amt_jasa,0) as amt_jasa
                    , COALESCE(wo_inv.cnt_war,0) as cnt_war
                    , COALESCE(wo_inv.cnt_not_war,0) as cnt_not_war
                    , COALESCE(wo_unit.unit_entry,0) as unit_entry
                    , COALESCE(wo_jasa.amt_part,0) AS amt_part 
                    , COALESCE(wo_jasa.amt_oil,0) as amt_oil
                    , COALESCE(wo_jasa.amt_tire,0) as amt_tire
                    , COALESCE(total_mekanik.total_mekanik,0) as total_mekanik
                    , COALESCE(jam_terpakai.jam_terpakai,0) as jam_terpakai
                    , COALESCE(absensi_mekanik.jumlah_hari_kerja,0) as jumlah_hari_kerja
                    , COALESCE(absensi_mekanik.absen,0) as absen
                    , COALESCE(absensi_mekanik.total_masuk,0) as total_masuk
                                    FROM
                                            (SELECT wo.branch_id
                                            , COUNT(CASE WHEN wo.type = 'WAR' THEN wo.id END) AS cnt_war
                                            , COUNT(CASE WHEN wo.type <>  'WAR' THEN wo.id END) AS cnt_not_war
                                            FROM wtc_work_order wo
                                            WHERE wo.date BETWEEN '%s'""" % str(start_date) + """  AND '%s'""" % str(end_date) +"""
                                            GROUP BY wo.branch_id) AS wo_inv
                                FULL OUTER JOIN
                                            (SELECT branch_id, SUM(cnt_per_date) AS unit_entry
                                            FROM (
                                            SELECT wo.branch_id, wo.date, COUNT(DISTINCT lot_id) AS cnt_per_date
                                            FROM wtc_work_order wo
                                            WHERE wo.type <> 'WAR' AND wo.type <> 'SLS' 
                                            AND wo.date BETWEEN '%s'""" % str(start_date) + """  AND '%s'""" % str(end_date) +"""
                                            GROUP BY wo.branch_id, wo.date ) wo_per_date
                                            GROUP BY branch_id) AS wo_unit
                            ON wo_inv.branch_id = wo_unit.branch_id
                            FULL OUTER JOIN
                                            (SELECT  
                                                hr_sales.branch_id as branch_id
                                                ,COUNT(users.id) as total_mekanik
                                                FROM  res_users as users
                                                LEFT JOIN resource_resource sales ON users.id = sales.user_id 
                                                LEFT JOIN hr_employee hr_sales ON sales.id = hr_sales.resource_id 
                                                LEFT JOIN hr_job job ON hr_sales.job_id = job.id
                                                LEFT JOIN wtc_branch as branch ON branch.id=hr_sales.branch_id
                                                WHERE job.sales_force='mechanic'
                                                and hr_sales.branch_id=%s """ % str(val.branch_id.id)+"""
                                                and job.name <> 'KEPALA MEKANIK'
                                                GROUP BY hr_sales.branch_id
                                            ) as total_mekanik
                        ON total_mekanik.branch_id = wo_unit.branch_id
                        FULL OUTER JOIN
                                        (SELECT 
                                            branch.id as branch_id,
                                            absensi.jumlah_hari_kerja as jumlah_hari_kerja, 
                                            sum(jumlah_hari_kerja-total_absensi) absen,
                                            sum(total_absensi) total_masuk
                                            from wtc_absensi as absensi
                                            LEFT JOIN hr_employee hr_sales ON absensi.nip = hr_sales.nip 
                                            LEFT JOIN wtc_branch as branch ON branch.id=hr_sales.branch_id
                                            where branch.id=%s """ % str(val.branch_id.id)+"""  AND absensi.bulan='%s'""" % start_date[:-3] + """
                                            GROUP BY branch.id,absensi.jumlah_hari_kerja
                                        ) as absensi_mekanik
                        ON absensi_mekanik.branch_id = total_mekanik.branch_id
                        FULL OUTER JOIN
                                            (SELECT
                                                    wo.branch_id 
                                                    ,date_part( 'epoch',  SUM(age(wo_start.finish,wo_start.start) )::interval   )/3600 as jam_terpakai
                                                    from wtc_work_order as wo
                                                    LEFT JOIN wtc_start_stop_wo AS wo_start
                                                    ON wo.id=wo_start.work_order_id 
                                                    LEFT JOIN wtc_branch as branch ON branch.id=wo.branch_id
                                                    where 1=1
                                                    and  wo.date BETWEEN '%s'""" % str(start_date) + """  AND '%s'""" % str(end_date) +"""
                                                    GROUP BY wo.branch_id
                                            ) as jam_terpakai
                        ON jam_terpakai.branch_id = total_mekanik.branch_id
                        FULL OUTER JOIN
                                        (SELECT wo.branch_id
                                        , SUM(CASE WHEN wol.categ_id = 'Service' THEN wol.price_unit*(1-COALESCE(wol.discount,0)/100) END) amt_jasa
                                        , SUM(CASE WHEN wol.categ_id = 'Sparepart' AND pc.name NOT IN ( 'OLI','OIL','TIRE','TIRE1') THEN wol.price_unit*(1-COALESCE(wol.discount,0)/100) END) amt_part
                                        , SUM(CASE WHEN wol.categ_id = 'Sparepart' AND pc.name = 'OIL' THEN wol.price_unit*(1-COALESCE(wol.discount,0)/100) END) amt_oil
                                        , SUM(CASE WHEN wol.categ_id = 'Sparepart' AND pc.name in ( 'TIRE' ,'TIRE1') THEN wol.price_unit*(1-COALESCE(wol.discount,0)/100) END) amt_tire
                        
                            FROM wtc_work_order wo
                            INNER JOIN wtc_work_order_line wol ON wo.id = wol.work_order_id
                            LEFT JOIN product_product p ON wol.product_id = p.id 
                            LEFT JOIN product_template pt ON p.product_tmpl_id = pt.id 
                            LEFT JOIN product_category pc ON pt.categ_id = pc.id 
                            LEFT JOIN product_category pc2 ON pc.parent_id = pc2.id
                            WHERE wo.date BETWEEN '%s'""" % str(start_date) + """  AND '%s'""" % str(end_date) +"""
                            GROUP BY wo.branch_id) AS wo_jasa
                            ON wo_inv.branch_id = wo_jasa.branch_id
                            INNER JOIN wtc_branch b ON b.id = COALESCE(wo_inv.branch_id, COALESCE(wo_unit.branch_id, wo_jasa.branch_id,total_mekanik.branch_id ))
                            where 1=1 AND b.id=%s """ % str(val.branch_id.id)+"""
             """ 
             
        cr.execute (query)
        res = cr.fetchone()
       
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('WPP')
        worksheet.set_column('A1:A1', 2)
        worksheet.set_column('A5:A5', 12)
        worksheet.set_column('B1:B1', 15)
        worksheet.set_column('C1:C1', 15)
        worksheet.set_column('D1:D1', 35)
        worksheet.set_column('E1:E1', 6)
        worksheet.set_column('E5:E5', 15)
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
        filename = 'Workshop  Performance Parameter.xlsx'  
        
        code_branch=res[0]
        name_branch=res[1]
        amount_jasa=res[2]
        count_war=res[3]
        count_not_war=res[4]
        count_unit_entry=res[5]
        amount_separepart=res[6]
        amount_oli=res[7]
        amount_tire=res[8]
        jumlah_mekanik=res[9]
        jumlah_jam=res[10]
        jumlah_hari_kerja=res[11]
        total_mekanik_tidak_masuk=res[12]
        total_mekanik_masuk=res[13]
        all_pendapatan=amount_separepart+amount_oli+amount_tire+amount_jasa
        amount_sparepart=amount_separepart+amount_oli+amount_tire
        
    
        
        
        
        worksheet.merge_range('B%s:H%s' % (1,1), 'WORKSHOP  PERFORMANCE PARAMETER', wbf['title']) 
        worksheet.write('A%s' % (5), 'NOMOR AHASS' , wbf['title_2'])
        worksheet.write('A%s' % (6), 'NAMA AHASS' , wbf['title_2'])
        worksheet.write('A%s' % (7), 'KAB/ KOTA' , wbf['title_2'])
        
        worksheet.write('B%s' % (5), val.branch_id.ahm_code , wbf['title_2'])
        worksheet.write('B%s' % (6), name_branch , wbf['title_2'])
        worksheet.write('B%s' % (7), val.branch_id.city_id.name, wbf['title_2'])
        
        
        worksheet.write('E%s' % (5), 'BULAN' , wbf['title_2'])
        worksheet.write('E%s' % (6), 'OLEH' , wbf['title_2'])
        worksheet.write('E%s' % (7), 'TANGGAL' , wbf['title_2'])
        
        worksheet.write('F%s' % (5), '%s s/d %s'%(str(start_date),str(end_date)) , wbf['title_2'])
        worksheet.write('F%s' % (6), user , wbf['title_2'])
        worksheet.write('F%s' % (7), date , wbf['title_2'])
        
        row=7
        rowsaldo = row
        row+=1
        
        if jumlah_mekanik>0:
            jumlah_jam_tersedia=(jumlah_hari_kerja*float(jumlah_mekanik) )*7
        else :
            jumlah_jam_tersedia=0
        if jumlah_jam_tersedia > 0 :
            efesiensi=float(jumlah_jam)/float(jumlah_jam_tersedia)
        else :
            efesiensi=0
        if jumlah_mekanik >0 :
            produktivitas_mekanik=amount_jasa/jumlah_mekanik
        else :
            produktivitas_mekanik=0
        if count_not_war >0 :
            pekerjaan_ulang=float(count_war)/float(count_not_war)*100
        else :
            pekerjaan_ulang =0
        if total_mekanik_masuk >0 :
            absensi_mekanik=float(total_mekanik_tidak_masuk)/float(total_mekanik_masuk)*100
        else :
            absensi_mekanik=0
        if jumlah_mekanik >0 :
            kapasitas_mekanik=float(count_unit_entry)/float(jumlah_mekanik)
        else :
            kapasitas_mekanik=0
        if jumlah_jam >0 :
            harga_jam_kerja=float(amount_jasa)/float(jumlah_jam)
        else :
            harga_jam_kerja=0
        if count_not_war >0 :
            kesanggupan_menjual=float(all_pendapatan)/float(count_not_war)
        else :
            kesanggupan_menjual =0
        if amount_sparepart >0 :
            perbandingan_pendapatan_jasa=float(amount_jasa/amount_sparepart)
        else :
            perbandingan_pendapatan_jasa=0
   
        
        worksheet.write('A%s' % (row+1), 'No' , wbf['header_table_v_center_bold'])
        worksheet.merge_range('B%s:C%s' % (row+1,row+1), 'Parameter Bengkel' , wbf['header_table_v_center_bold'])
        worksheet.write('D%s' % (row+1), 'Penjelasan & Rumus' , wbf['header_table_v_center_bold'])
        worksheet.write('E%s' % (row+1), ' ' , wbf['header_table_v_center_bold'])
        worksheet.merge_range('F%s:H%s' % (row+1,row+1), 'Hasil' , wbf['header_table_v_center_bold'])
        
        worksheet.merge_range('A%s:A%s' % (row+2,row+3), '1' , wbf['header_table_v_center'])
        worksheet.merge_range('B%s:C%s' % (row+2,row+3), 'Produktivitas tiap Mekanik' , wbf['content_wpp'])
        worksheet.write('D%s' % (row+2), 'Pendapatan     Jasa     Service    bulan    ini ' , wbf['content_wpp'])
        worksheet.write('D%s' % (row+3), 'Jumlah Mekanik & ass mekanik yang bekerja ' , wbf['content_wpp'])
        worksheet.write('E%s' % (row+2), amount_jasa , wbf['content_float_bold_wpp'])
        worksheet.write('E%s' % (row+3), jumlah_mekanik , wbf['content_float_bold_wpp'])
        worksheet.merge_range('F%s:H%s' % (row+2,row+3), produktivitas_mekanik , wbf['header_table_v_center_bold'])
        
        
        
        worksheet.merge_range('A%s:A%s' % (row+4,row+5), '2' , wbf['header_table_v_center'])
        worksheet.merge_range('B%s:C%s' % (row+4,row+5), 'Effisiensi' , wbf['content_wpp'])
        worksheet.write('D%s' % (row+4), 'Jumlah jam yang terpakai bulan ini ' , wbf['content_wpp'])
        worksheet.write('D%s' % (row+5), 'Jumlah jam yang tersedia bulan in ' , wbf['content_wpp'])
        worksheet.write('E%s' % (row+4), str(jumlah_jam)+ ' Jam' , wbf['header_table_v_center_bold'])
        worksheet.write('E%s' % (row+5), str(jumlah_jam_tersedia)+ ' Jam' , wbf['header_table_v_center_bold'])
        worksheet.merge_range('F%s:H%s' % (row+4,row+5), efesiensi , wbf['header_table_v_center_bold'])
        
        
        
        worksheet.merge_range('A%s:A%s' % (row+6,row+7), '3' , wbf['header_table_v_center'])
        worksheet.merge_range('B%s:C%s' % (row+6,row+7), 'Pekerjaan Ulang ' , wbf['content_wpp'])
        worksheet.write('D%s' % (row+6), 'Jumlah   pekerjaan   yang    diulang    bulan    ini  ' , wbf['content_wpp'])
        worksheet.write('D%s' % (row+7), 'Jumlah unit yg dikerjakan tak termasuk yg diulang  ' , wbf['content_wpp'])
        worksheet.write('E%s' % (row+6), count_war , wbf['content_float_bold_wpp'])
        worksheet.write('E%s' % (row+7),count_not_war , wbf['content_float_bold_wpp'])
        worksheet.merge_range('F%s:H%s' % (row+6,row+7), str(pekerjaan_ulang)+' %' , wbf['header_table_v_center_bold'])
        
        
         
        worksheet.merge_range('A%s:A%s' % (row+8,row+9), '4' , wbf['header_table_v_center'])
        worksheet.merge_range('B%s:C%s' % (row+8,row+9), 'Absensi mekanik ' , wbf['content_wpp'])
        worksheet.write('D%s' % (row+8), 'Jumlah hari absen mekanik bulan ini ' , wbf['content_wpp'])
        worksheet.write('D%s' % (row+9), 'Jumlah hari hadir mekanik' , wbf['content_wpp'])
        worksheet.write('E%s' % (row+8), total_mekanik_tidak_masuk , wbf['content_float_bold_wpp'])
        worksheet.write('E%s' % (row+9),total_mekanik_masuk , wbf['content_float_bold_wpp'])
        worksheet.merge_range('F%s:H%s' % (row+8,row+9), str(absensi_mekanik)+' %', wbf['header_table_v_center_bold'])
        
        
        
        worksheet.merge_range('A%s:A%s' % (row+10,row+11), '5' , wbf['header_table_v_center'])
        worksheet.merge_range('B%s:C%s' % (row+10,row+11), 'Perbandingan biaya operasi' , wbf['content_wpp'])
        worksheet.write('D%s' % (row+10), 'Biaya pengeluaran bengkel bulan ini ' , wbf['content_wpp'])
        worksheet.write('D%s' % (row+11), 'Pendapatan jasa service bulan ini ' , wbf['content_wpp'])
        worksheet.write('E%s' % (row+10), '0' , wbf['content_float_bold_wpp'])
        worksheet.write('E%s' % (row+11),amount_jasa , wbf['content_float_bold_wpp'])
        worksheet.merge_range('F%s:H%s' % (row+10,row+11), ' ' , wbf['header_table_v_center_bold'])
        
        
        
        worksheet.merge_range('A%s:A%s' % (row+12,row+13), '6' , wbf['header_table_v_center'])
        worksheet.merge_range('B%s:C%s' % (row+12,row+13), 'Kapasitas mekanik' , wbf['content_wpp'])
        worksheet.write('D%s' % (row+12), 'Jumlah unit yang dikerjakan bulan ini ' , wbf['content_wpp'])
        worksheet.write('D%s' % (row+13), 'Jumlah Mekanik & ass mekanik yang bekerja  ' , wbf['content_wpp'])
        worksheet.write('E%s' % (row+12), count_unit_entry , wbf['content_float_bold_wpp'])
        worksheet.write('E%s' % (row+13),jumlah_mekanik , wbf['content_float_bold_wpp'])
        worksheet.merge_range('F%s:H%s' % (row+12,row+13), kapasitas_mekanik , wbf['header_table_v_center_bold'])
        
        
        worksheet.merge_range('A%s:A%s' % (row+14,row+15), '7' , wbf['header_table_v_center'])
        worksheet.merge_range('B%s:C%s' % (row+14,row+15), 'Harga jam kerja' , wbf['content_wpp'])
        worksheet.write('D%s' % (row+14), 'Pendapatan jasa service bulan ini ' , wbf['content_wpp'])
        worksheet.write('D%s' % (row+15), 'Jumlah jam yang terpakai bulan ini' , wbf['content_wpp'])
        worksheet.write('E%s' % (row+14), amount_jasa , wbf['content_float_bold_wpp'])
        worksheet.write('E%s' % (row+15),str(jumlah_jam)+ ' Jam' , wbf['header_table_v_center_bold'])
        worksheet.merge_range('F%s:H%s' % (row+14,row+15), harga_jam_kerja , wbf['header_table_v_center_bold'])
        
        
        worksheet.merge_range('A%s:A%s' % (row+16,row+17), '8' , wbf['header_table_v_center'])
        worksheet.merge_range('B%s:C%s' % (row+16,row+17), 'Kesanggupan menjual' , wbf['content_wpp'])
        worksheet.write('D%s' % (row+16), 'Pendapatan jasa service + spare parts bulan ini' , wbf['content_wpp'])
        worksheet.write('D%s' % (row+17), 'Jumlah unit yang dikerjakan tak termasuk yang diulang' , wbf['content_wpp'])
        worksheet.write('E%s' % (row+16), all_pendapatan , wbf['content_float_bold_wpp'])
        worksheet.write('E%s' % (row+17),count_not_war , wbf['content_float_bold_wpp'])
        worksheet.merge_range('F%s:H%s' % (row+16,row+17), kesanggupan_menjual , wbf['header_table_v_center_bold'])
        
        
        
        worksheet.merge_range('A%s:A%s' % (row+18,row+19), '9' , wbf['header_table_v_center'])
        worksheet.merge_range('B%s:C%s' % (row+18,row+19), 'Perbandingan pendapatan Jasa' , wbf['content_wpp'])
        worksheet.write('D%s' % (row+18), 'Pendapatan jasa service bulan ini' , wbf['content_wpp'])
        worksheet.write('D%s' % (row+19), 'Pendapatan Penjualan Spare Parts bulan ini' , wbf['content_wpp'])
        worksheet.write('E%s' % (row+18), amount_jasa , wbf['content_float_bold_wpp'])
        worksheet.write('E%s' % (row+19),amount_sparepart , wbf['content_float_bold_wpp'])
        worksheet.merge_range('F%s:H%s' % (row+18,row+19), perbandingan_pendapatan_jasa , wbf['header_table_v_center_bold'])
        
        
        
        worksheet.merge_range('A%s:A%s' % (row+20,row+21), '10' , wbf['header_table_v_center'])
        worksheet.merge_range('B%s:C%s' % (row+20,row+21), 'Perbandingan Langganan Baru' , wbf['content_wpp'])
        worksheet.write('D%s' % (row+20), 'Jumlah langganan baru bulan ini' , wbf['content_wpp'])
        worksheet.write('D%s' % (row+21), 'Jumlah seluruh langganan bulan ini ' , wbf['content_wpp'])
        worksheet.write('E%s' % (row+20), '-' , wbf['content_float_bold_wpp'])
        worksheet.write('E%s' % (row+21),'-' , wbf['content_float_bold_wpp'])
        worksheet.merge_range('F%s:H%s' % (row+20,row+21), ' ' , wbf['content_float_bold_wpp'])
        
        
        worksheet.merge_range('A%s:A%s' % (row+22,row+23), '11' , wbf['header_table_v_center'])
        worksheet.merge_range('B%s:C%s' % (row+22,row+23), 'Efektivitas Penanganan' , wbf['content_wpp'])
        worksheet.write('D%s' % (row+22), 'Jumlah langganan baru bulan ini' , wbf['content_wpp'])
        worksheet.write('D%s' % (row+23), 'Jumlah langganan yang terkontrol' , wbf['content_wpp'])
        worksheet.write('E%s' % (row+22), '-' , wbf['content_float_bold_wpp'])
        worksheet.write('E%s' % (row+23),'-' , wbf['content_float_bold_wpp'])
        worksheet.merge_range('F%s:H%s' % (row+22,row+23), ' ' , wbf['content_float_bold_wpp'])
        
        worksheet.merge_range('A%s:A%s' % (row+24,row+25), '12' , wbf['header_table_v_center'])
        worksheet.merge_range('B%s:C%s' % (row+24,row+25), 'Efektivitas Penanganan ' , wbf['content_wpp'])
        worksheet.write('D%s' % (row+24), 'Jumlah langganan baru bulan ini' , wbf['content_wpp'])
        worksheet.write('D%s' % (row+25), 'Jumlah langganan yang terkontrol' , wbf['content_wpp'])
        worksheet.write('E%s' % (row+24), '-' , wbf['content_float_bold_wpp'])
        worksheet.write('E%s' % (row+25),'-' , wbf['content_float_bold_wpp'])
        worksheet.merge_range('F%s:H%s' % (row+24,row+25), ' ' , wbf['content_float_bold_wpp'])
        
        
        worksheet.merge_range('A%s:A%s' % (row+26,row+27), '13' , wbf['header_table_v_center'])
        worksheet.merge_range('B%s:C%s' % (row+26,row+27), 'Perbandingan Spare Parts' , wbf['content_wpp'])
        worksheet.write('D%s' % (row+26), 'Jumlah Spare Parts tak tersedia bulan ini' , wbf['content_wpp'])
        worksheet.write('D%s' % (row+27), 'Jumlah penjualan part + part yg tak tersedia' , wbf['content_wpp'])
        worksheet.write('E%s' % (row+26), '-' , wbf['content_float_bold_wpp'])
        worksheet.write('E%s' % (row+27),'-' , wbf['content_float_bold_wpp'])
        worksheet.merge_range('F%s:H%s' % (row+26,row+27), ' ' , wbf['content_float_bold_wpp'])
        
        worksheet.write('A%s' % (row+30), '14' , wbf['header_table_v_center'])
        worksheet.merge_range('B%s:E%s' % (row+30,row+30), 'Data History - Card' , wbf['content_wpp'])
        
        worksheet.merge_range('B%s:C%s' % (row+31,row+31), 'Langganan lama' , wbf['content_wpp'])
        worksheet.write('D%s' % (row+31), '-' , wbf['content_wpp'])
        worksheet.write('E%s' % (row+31), '-' , wbf['content_float_bold_wpp'])
        
        worksheet.merge_range('B%s:C%s' % (row+32,row+32), 'Langganan baru' , wbf['content_wpp'])
        worksheet.write('D%s' % (row+32), '-' , wbf['content_wpp'])
        worksheet.write('E%s' % (row+32), '-' , wbf['content_float_bold_wpp'])
        
        worksheet.merge_range('B%s:C%s' % (row+33,row+33), 'Jumlah seluruh Langganan bulan ini' , wbf['content_wpp'])
        worksheet.write('D%s' % (row+33), '-' , wbf['content_wpp'])
        worksheet.write('E%s' % (row+33), '-' , wbf['content_float_bold_wpp'])
        
        worksheet.merge_range('B%s:C%s' % (row+34,row+34), 'Langganan yang lebih dari 3 bulan tidak datang' , wbf['content_wpp'])
        worksheet.write('D%s' % (row+34), '-' , wbf['content_wpp'])
        worksheet.write('E%s' % (row+34), '-' , wbf['content_float_bold_wpp'])
        
        worksheet.merge_range('B%s:C%s' % (row+35,row+35), 'Langganan yang rutin datang minimal 1x dalam 3 bulan ( Langganan terkontrol )' , wbf['content_wpp'])
        worksheet.write('D%s' % (row+35), '-' , wbf['content_wpp'])
        worksheet.write('E%s' % (row+35), '-' , wbf['content_float_bold_wpp'])
        
        
        worksheet.merge_range('B%s:C%s' % (row+36,row+36), 'Jumlah langganan selama 2 tahun ' , wbf['content_wpp'])
        worksheet.write('D%s' % (row+36), '-' , wbf['content_wpp'])
        worksheet.write('E%s' % (row+36), '-' , wbf['content_float_bold_wpp'])
        
        worksheet.write('A%s' % (row+38), '15' , wbf['header_table_v_center'])
        worksheet.merge_range('B%s:C%s' % (row+38,row+38), 'Jumlah Laporan Kualitas Honda - LKH yang dikirim bulan ini' , wbf['content_wpp'])
        worksheet.write('D%s' % (row+38), '-' , wbf['content_wpp'])
        worksheet.write('E%s' % (row+38), '-' , wbf['content_float_bold_wpp'])
        
        
        
        
        worksheet.write('B%s' % (row+43), 'Yang membuat,' , wbf['title_2'])
        worksheet.write('D%s' % (row+43), 'Check,' , wbf['title_2'])
        worksheet.write('E%s' % (row+43), 'Disetujui,' , wbf['title_2'])
        worksheet.write('B%s' % (row+44), 'Front Desk,' , wbf['title_2'])
        worksheet.write('D%s' % (row+44), 'Kepala Bengkel / Mekanik,' , wbf['title_2'])
        worksheet.write('E%s' % (row+44), 'Pemilik,' , wbf['title_2'])
        
        
        worksheet.write('B%s' % (row+48), '( _______________ ),' , wbf['title_2'])
        worksheet.write('D%s' % (row+48), '( _______________ ),' , wbf['title_2'])
        worksheet.write('E%s' % (row+48), '( _______________ ),' , wbf['title_2'])
        
        worksheet.write('B%s' % (row+50), 'Note :' , wbf['title_2'])
        worksheet.write('B%s' % (row+51), 'Ditandatangani berikut Cap / Stempel AHASS' , wbf['title_2'])
        
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()
