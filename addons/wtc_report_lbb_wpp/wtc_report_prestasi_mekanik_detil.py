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

class wtc_report_prestasi_mekanik_detil(osv.osv_memory):
    
    _inherit = "wtc.report.lbb.wizard"
    
    wbf = {}
    
    def _print_excel_report_prestasi_mekanik_detil(self, cr, uid, ids, data, context=None): 
        curr_date= self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)
        user = self.pool.get('res.users').browse(cr, uid, uid)
        company_name = user.company_id.name
        username = user.name
        
        filename = 'Report Prestasi Mekanik Detil '+str(curr_date.strftime("%Y%m%d_%H%M%S"))+'.xlsx'
        
        
        val = self.browse(cr, uid, ids, context={})[0]
        branch_id = data['branch_ids']  
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
        
        if not branch_id :
            query_branch_id = " is not null "
        else:
            query_branch_id = " in %s " % str(tuple(branch_id)).replace(',)', ')')
            
#         if start_date :
#             query_where += " AND wo.date >= '%s'" % str(start_date)
#         if end_date :
#             end_date = end_date + ' 23:59:59'
#             query_where += " AND wo.date <= to_timestamp('%s', 'YYYY-MM-DD HH24:MI:SS') + interval '%s'" % (end_date,tz)

        query_where =" '%s' and '%s' "%(start_date,end_date)
        query = """
                select
                mekanik.branch_id,
                branch.name,
                COALESCE(mekanik.mekanik_id,0)mekanik_id,
                COALESCE(rr.name,'Part Cash')nama,
                cnt_unit.cnt_unit,
                jasa.amt_jasa,
                jasa.amt_oil,
                jasa.amt_part,
                jasa.amt_total,
                jasa.qty_cla,
                jasa.qty_cs,
                jasa.qty_hr,
                jasa.qty_kpb,
                jasa.qty_lr,
                jasa.qty_ls,
                jasa.qty_or,
                jasa.qty_qs,
                jasa.qty_total,
                kpb.cnt_inv,
                kpb.cnt_cla,
                kpb.cnt_kpb_1,
                kpb.cnt_kpb_2,
                kpb.cnt_kpb_3,
                kpb.cnt_kpb_4
                from wtc_work_order mekanik
                LEFT JOIN
                (SELECT COALESCE(wo.mekanik_id,0)mekanik_id
                , SUM(CASE WHEN wol.categ_id = 'Service' THEN COALESCE(wol.price_unit,0) * (1 - COALESCE(NULLIF(wol.discount,0),0) / 100)  * COALESCE(wol.product_qty,0) END) amt_jasa
                , SUM(CASE WHEN wol.categ_id = 'Sparepart' AND pc.name NOT IN ( 'OLI','OIL') THEN COALESCE(wol.price_unit,0) * (1 - COALESCE(NULLIF(wol.discount,0),0) / 100)  * wol.supply_qty END) amt_part
                , SUM(CASE WHEN wol.categ_id = 'Sparepart' AND pc.name = 'OIL' THEN COALESCE(wol.price_unit,0) * (1 - COALESCE(NULLIF(wol.discount,0),0) / 100)  * wol.supply_qty END) amt_oil
                , SUM(COALESCE(wol.price_unit,0) * (1 - COALESCE(NULLIF(wol.discount,0),0) / 100) / 1.1 * CASE WHEN wol.categ_id = 'Sparepart' THEN wol.supply_qty ELSE COALESCE(wol.product_qty,0) END) amt_total
                , SUM(CASE WHEN wol.categ_id = 'Service' AND pc2.name = 'KPB' THEN COALESCE(wol.product_qty,0) END) qty_kpb
                , SUM(CASE WHEN wol.categ_id = 'Service' AND pc.name = 'CS' THEN COALESCE(wol.product_qty,0) END) qty_cs
                , SUM(CASE WHEN wol.categ_id = 'Service' AND pc.name = 'LS' THEN COALESCE(wol.product_qty,0) END) qty_ls
                , SUM(CASE WHEN wol.categ_id = 'Service' AND pc.name = 'OR+' THEN COALESCE(wol.product_qty,0) END) qty_or
                , SUM(CASE WHEN wol.categ_id = 'Service' AND pc2.name = 'QS' THEN COALESCE(wol.product_qty,0) END) qty_qs
                , SUM(CASE WHEN wol.categ_id = 'Service' AND pc.name = 'LR' THEN COALESCE(wol.product_qty,0) END) qty_lr
                , SUM(CASE WHEN wol.categ_id = 'Service' AND pc.name = 'HR' THEN COALESCE(wol.product_qty,0) END) qty_hr
                , SUM(CASE WHEN wol.categ_id = 'Service' AND pc.name = 'CLA' THEN COALESCE(wol.product_qty,0) END) qty_cla
                , SUM(CASE WHEN wol.categ_id = 'Service' THEN COALESCE(wol.product_qty,0) END) qty_total
                FROM wtc_work_order wo
                INNER JOIN account_invoice ai ON wo.id = ai.transaction_id AND ai.model_id IN (SELECT id FROM ir_model WHERE model = 'wtc.work.order')
                INNER JOIN wtc_work_order_line wol ON wo.id = wol.work_order_id
                LEFT JOIN product_product p ON wol.product_id = p.id
                LEFT JOIN product_template pt ON p.product_tmpl_id = pt.id
                LEFT JOIN product_category pc ON pt.categ_id = pc.id
                LEFT JOIN product_category pc2 ON pc.parent_id = pc2.id
                WHERE wo.state IN ('open', 'done')
                AND wo.date_confirm between  %s  and wo.branch_id %s
                GROUP BY wo.mekanik_id)jasa on COALESCE(jasa.mekanik_id,0)=COALESCE(mekanik.mekanik_id,0)
                LEFT JOIN
                (SELECT COALESCE(wo.mekanik_id,0)mekanik_id
                , COUNT(wo.id) AS cnt_inv
                , COUNT(CASE WHEN wo.type = 'KPB' AND wo.kpb_ke = '1' THEN wo.id END) AS cnt_kpb_1
                , COUNT(CASE WHEN wo.type = 'KPB' AND wo.kpb_ke = '2' THEN wo.id END) AS cnt_kpb_2
                , COUNT(CASE WHEN wo.type = 'KPB' AND wo.kpb_ke = '3' THEN wo.id END) AS cnt_kpb_3
                , COUNT(CASE WHEN wo.type = 'KPB' AND wo.kpb_ke = '4' THEN wo.id END) AS cnt_kpb_4
                , COUNT(CASE WHEN wo.type = 'CLA' THEN wo.id END) AS cnt_cla
                FROM wtc_work_order wo
                INNER JOIN account_invoice ai ON wo.id = ai.transaction_id AND ai.model_id IN (SELECT id FROM ir_model WHERE model = 'wtc.work.order')
                WHERE wo.state IN ('open', 'done')
                AND wo.date_confirm between  %s  and wo.branch_id  %s
                GROUP BY wo.mekanik_id) kpb on COALESCE(kpb.mekanik_id,0)=COALESCE(mekanik.mekanik_id,0)
                LEFT JOIN 
                (select unit.mekanik_id,sum(unit.cnt_per_date)cnt_unit from 
                (SELECT wo.branch_id
                , wo.date_confirm
                ,COALESCE(wo.mekanik_id,0)mekanik_id
                , COUNT(DISTINCT wo.lot_id) AS cnt_per_date
                FROM wtc_work_order wo
                INNER JOIN account_invoice ai ON wo.id = ai.transaction_id AND ai.model_id IN (SELECT id FROM ir_model WHERE model = 'wtc.work.order')
                WHERE wo.state IN ('open', 'done')
                AND wo.type <> 'WAR' AND wo.type <> 'SLS'
                AND wo.date_confirm BETWEEN  %s and wo.branch_id  %s
                GROUP BY wo.branch_id, wo.date_confirm,COALESCE(wo.mekanik_id,0))unit
                GROUP BY unit.mekanik_id)cnt_unit on mekanik.mekanik_id=cnt_unit.mekanik_id
                LEFT JOIN resource_resource rr on rr.user_id=mekanik.mekanik_id
                LEFT JOIN wtc_branch branch on mekanik.branch_id=branch.id
                where mekanik.date_confirm between %s and mekanik.branch_id %s
                group by mekanik.branch_id,branch.name,mekanik.mekanik_id,rr.name,cnt_unit.cnt_unit,jasa.amt_jasa,jasa.amt_oil,jasa.amt_part,jasa.amt_total,jasa.qty_cla,jasa.qty_cs,jasa.qty_hr,jasa.qty_kpb,jasa.qty_lr,jasa.qty_ls,jasa.qty_or,jasa.qty_qs,jasa.qty_total,kpb.cnt_inv,
                kpb.cnt_inv,kpb.cnt_cla,kpb.cnt_kpb_1,kpb.cnt_kpb_2,kpb.cnt_kpb_3,kpb.cnt_kpb_4

                """ %(query_where,query_branch_id,query_where,query_branch_id,query_where,query_branch_id,query_where,query_branch_id)
        # print '>>>',query
        cr.execute (query)
        ress = cr.fetchall()
        # print 'xxx',ress
        # sdf
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Prestasi Mekanik Detail')

        worksheet.set_column(0, 0, 8.43)

        worksheet.write_string(0, 0, company_name , wbf['company'])
        worksheet.write_string(1, 0, 'Prestasi Mekanik Detail' , wbf['company'])
        worksheet.write_string(2, 0, 'Date : %s s/d %s' % (str(start_date), str(end_date)), wbf['title_doc'])

        row = 4
        header_row = row

        col = 0 #branch_code
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'No', wbf['header'])
        col += 1 #branch_name
        worksheet.set_column(col, col, 35)
        worksheet.write_string(row, col, 'Branch Code', wbf['header']) 
        col += 1
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'Name', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'Unit', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'Invoice', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'Jasa', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'Part', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'Oil', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'Total', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'KPB1', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'KPB2', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'KPB3', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'KPB4', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'CLA', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'CS', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'LS', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'OR', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'LR', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'HR', wbf['header'])
        col += 1
#         worksheet.set_column(col, col, 15)
#         worksheet.write_string(row, col, 'TOTAL WAKTU', wbf['header'])
        
        data_last_col = col

        row += 1
        data_first_row = row
        no = 0
        for res in ress :
            no +=1
            # branch_id   = res.get('branch_id')
            name    = res[1]
            # mekanik_id  = res[3]
            nama    = res[3]
            cnt_unit    = res[4]
            amt_jasa    = res[5]
            amt_oil = res[6]
            amt_part    = res[7]
            amt_total   = res[8]
            qty_cla = res[9]
            qty_cs  = res[10]
            qty_hr  = res[11]
            qty_kpb = res[12]
            qty_lr  = res[13]
            qty_ls  = res[14]
            qty_or  = res[15]
            qty_qs  =res[16]
            qty_total   = res[17]
            cnt_inv = res[18]
            cnt_cla = res[19]
            cnt_kpb_1   = res[20]
            cnt_kpb_2   = res[21]
            cnt_kpb_3   = res[22]
            cnt_kpb_4   = res[23]


#             branch_code = res[0]
#             name = res[1]
# #             unit_entry = res[15]+res[16]+res[17]+res[18]+res[19]
#             unit_inv = res[13]
#             unit_mekanik = res[14]
#             jasa = res[2]
#             part = res[3]
#             oil = res[4]
#             total = float(res[2])+float(res[3])+float(res[4])
#             kpb1 =  res[16]
#             kpb2 =  res[17]
#             kpb3 =  res[18]
#             kpb4 = res[19]
#             claim = res[20]
#             qty_cs = res[6]
#             qty_ls = res[7]
#             qty_or = res[8]
#             qty_lr = res[10]
#             qty_hr = res[11]
#             tot_waktu = res[]
            
            col = 0 #branch_code
            worksheet.write(row, col, no, wbf['content'])
            col += 1 #branch_name
            worksheet.write_string(row, col, name, wbf['content'])
            col += 1 #dealer_code
            worksheet.write_string(row, col, nama, wbf['content'])
            col += 1 #dealer_code
            worksheet.write(row, col, cnt_unit, wbf['content'])            
            col += 1 #dealer_code
            worksheet.write(row, col, cnt_inv, wbf['content'])  
            col += 1 #dealer_code
            worksheet.write(row, col, amt_jasa, wbf['content'])  
            col += 1 #dealer_code
            worksheet.write(row, col, amt_part, wbf['content'])  
            col += 1 #dealer_code
            worksheet.write(row, col, amt_oil, wbf['content'])
            col += 1 #dealer_code
            worksheet.write(row, col, amt_total, wbf['content'])
            col += 1
            worksheet.write(row, col, cnt_kpb_1, wbf['content'])
            col += 1
            worksheet.write(row, col, cnt_kpb_2, wbf['content'])
            col += 1
            worksheet.write(row, col, cnt_kpb_3, wbf['content'])
            col += 1
            worksheet.write(row, col, cnt_kpb_4, wbf['content'])
            col += 1
            worksheet.write(row, col, cnt_cla, wbf['content'])
            col += 1
            worksheet.write(row, col, qty_cs, wbf['content'])
            col += 1
            worksheet.write(row, col, qty_ls, wbf['content'])
            col += 1
            worksheet.write(row, col, qty_or, wbf['content'])
            col += 1
            worksheet.write(row, col, qty_lr, wbf['content'])
            col += 1
            worksheet.write(row, col, qty_hr, wbf['content'])
#             col += 1
#             worksheet.write(row, col, tot_waktu, wbf['content'])
            
            row += 1
        worksheet.autofilter(header_row, 0, row, data_last_col)

        #Datecreate and Created
        worksheet.write(row+2, 0, '%s %s' % (str(curr_date.strftime("%Y-%m-%d %H:%M:%S")),username) , wbf['footer'])  

        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        return True

            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            