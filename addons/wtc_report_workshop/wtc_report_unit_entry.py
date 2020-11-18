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

class wtc_report_workshop(osv.osv_memory):
    _inherit = "wtc.report.workshop.wizard"
    wbf = {}

    def _print_excel_report_unit_entry(self, cr, uid, ids, data, context=None): 
        wo_categ = data['wo_categ']
        product_ids = data['product_ids']
        start_date = data['start_date']
        end_date = data['end_date']
        state = data['state']
        branch_ids = data['branch_ids']
        partner_ids = data['partner_ids']        
        tz = '7 hours'
        query_where = " WHERE 1=1"
        query_where_wo_date = ""
        query_where_woc_date = ""

        if start_date:
            query_where_wo_date += " AND wo.date_confirm BETWEEN '%s'" % str(start_date)
            query_where_woc_date += " AND woc.date BETWEEN '%s'" % str(start_date)

        if end_date:
            query_where_wo_date += " AND '%s'" % str(end_date)
            query_where_woc_date += " AND '%s'" % str(end_date)

        if branch_ids :
            query_where += " AND b.id in %s" % str(tuple(branch_ids)).replace(',)', ')')
        
        query = """
                    SELECT b.id as branch_id
                        , b.code as branch_code          
                        , b.name as branch_name         
                        , COALESCE(wo_unit.unit_entry,0) as unit_entry          
                        , COALESCE(wo_inv.cnt_inv,0) as cnt_inv         
                        , COALESCE(wo_jasa.amt_jasa,0) as amt_jasa          
                        , COALESCE(wo_jasa.amt_part,0) AS amt_part          
                        , COALESCE(wo_jasa.amt_oil,0) as amt_oil          
                        , COALESCE(wo_jasa.amt_total,0) as amt_total          
                        , COALESCE(wo_inv.cnt_kpb_1,0) as cnt_kpb_1         
                        , COALESCE(wo_inv.cnt_kpb_2,0) as cnt_kpb_2         
                        , COALESCE(wo_inv.cnt_kpb_3,0) as cnt_kpb_3         
                        , COALESCE(wo_inv.cnt_kpb_4,0) as cnt_kpb_4         
                        , COALESCE(wo_inv.cnt_cla,0) as cnt_cla         
                        , COALESCE(wo_jasa.qty_kpb,0) as qty_kpb          
                        , COALESCE(wo_jasa.qty_cs,0) as qty_cs          
                        , COALESCE(wo_jasa.qty_ls,0) as qty_ls          
                        , COALESCE(wo_jasa.qty_or,0) as qty_or          
                        , COALESCE(wo_jasa.qty_qs,0) as qty_qs          
                        , COALESCE(wo_jasa.qty_lr,0) as qty_lr          
                        , COALESCE(wo_jasa.qty_hr,0) as qty_hr          
                        , COALESCE(wo_jasa.qty_cla,0) as qty_cla          
                        , COALESCE(wo_jasa.qty_total,0) as qty_total          
                    FROM wtc_branch b         
                    FULL OUTER JOIN         
                        (         
                        SELECT branch_id, SUM(cnt_per_date) as unit_entry FROM        
                            (
                                (        
                                    SELECT wo.branch_id     
                                        , wo.date_confirm     
                                        , COUNT(DISTINCT wo.lot_id) AS cnt_per_date     
                                    FROM wtc_work_order wo      
                                    INNER JOIN account_invoice ai ON wo.id = ai.transaction_id AND ai.model_id IN (SELECT id FROM ir_model WHERE model = 'wtc.work.order')
                                    WHERE wo.state IN ('open', 'done', 'cancel')      
                                    AND wo.type <> 'WAR' AND wo.type <> 'SLS'       
                                    %s  
                                    GROUP BY wo.branch_id, wo.date_confirm      
                                ) 
                                UNION ALL 
                                (       
                                    SELECT wo.branch_id   
                                        , woc.date    
                                        , -1 * COUNT(DISTINCT wo.lot_id) AS cnt_per_date    
                                    FROM work_order_cancel woc    
                                    INNER JOIN wtc_work_order wo ON woc.work_order_id = wo.id   
                                    INNER JOIN account_invoice ai ON wo.id = ai.transaction_id AND ai.model_id IN (SELECT id FROM ir_model WHERE model = 'wtc.work.order')
                                    WHERE woc.state = 'confirmed'   
                                    AND wo.type <> 'WAR' AND wo.type <> 'SLS'     
                                    %s    
                                    GROUP BY wo.branch_id, woc.date     
                                )
                            ) lot_count        
                        GROUP BY branch_id        
                        ORDER BY branch_id        
                        ) wo_unit         
                ON b.id = wo_unit.branch_id         
                FULL OUTER JOIN         
                    (         
                        SELECT branch_id      
                            , SUM(cnt_inv) as cnt_inv     
                            , SUM(cnt_kpb_1) as cnt_kpb_1     
                            , SUM(cnt_kpb_2) as cnt_kpb_2     
                            , SUM(cnt_kpb_3) as cnt_kpb_3     
                            , SUM(cnt_kpb_4) as cnt_kpb_4     
                            , SUM(cnt_cla) as cnt_cla     
                        FROM 
                        (      
                            (   
                                SELECT wo.branch_id   
                                    , COUNT(wo.id) AS cnt_inv 
                                    , COUNT(CASE WHEN wo.type = 'KPB' AND wo.kpb_ke = '1' THEN wo.id END) AS cnt_kpb_1  
                                    , COUNT(CASE WHEN wo.type = 'KPB' AND wo.kpb_ke = '2' THEN wo.id END) AS cnt_kpb_2  
                                    , COUNT(CASE WHEN wo.type = 'KPB' AND wo.kpb_ke = '3' THEN wo.id END) AS cnt_kpb_3  
                                    , COUNT(CASE WHEN wo.type = 'KPB' AND wo.kpb_ke = '4' THEN wo.id END) AS cnt_kpb_4  
                                    , COUNT(CASE WHEN wo.type = 'CLA' THEN wo.id END) AS cnt_cla  
                                FROM wtc_work_order wo  
                                INNER JOIN account_invoice ai ON wo.id = ai.transaction_id AND ai.model_id IN (SELECT id FROM ir_model WHERE model = 'wtc.work.order')
                                WHERE wo.state IN ('open', 'done', 'cancel')  
                                %s 
                                GROUP BY wo.branch_id 
                            )   
                            UNION ALL   
                            (   
                                SELECT wo.branch_id
                                    , -1 * COUNT(wo.id) AS cnt_inv
                                    , -1 * COUNT(CASE WHEN wo.type = 'KPB' AND wo.kpb_ke = '1' THEN wo.id END) AS cnt_kpb_1
                                    , -1 * COUNT(CASE WHEN wo.type = 'KPB' AND wo.kpb_ke = '2' THEN wo.id END) AS cnt_kpb_2
                                    , -1 * COUNT(CASE WHEN wo.type = 'KPB' AND wo.kpb_ke = '3' THEN wo.id END) AS cnt_kpb_3
                                    , -1 * COUNT(CASE WHEN wo.type = 'KPB' AND wo.kpb_ke = '4' THEN wo.id END) AS cnt_kpb_4
                                    , -1 * COUNT(CASE WHEN wo.type = 'CLA' THEN wo.id END) AS cnt_cla
                                FROM work_order_cancel woc 
                                INNER JOIN wtc_work_order wo ON woc.work_order_id = wo.id 
                                INNER JOIN account_invoice ai ON wo.id = ai.transaction_id AND ai.model_id IN (SELECT id FROM ir_model WHERE model = 'wtc.work.order')
                                WHERE woc.state = 'confirmed'
                                %s
                                GROUP BY wo.branch_id
                            )   
                        ) invoice_count       
                        GROUP BY branch_id      
                        ORDER BY branch_id      
                    ) wo_inv          
                ON b.id = wo_inv.branch_id          
                FULL OUTER JOIN         
                    (         
                        SELECT branch_id    
                            , SUM(amt_jasa) as amt_jasa   
                            , SUM(amt_part) as amt_part   
                            , SUM(amt_oil) AS amt_oil   
                            , SUM(amt_total) AS amt_total   
                            , SUM(qty_kpb) AS qty_kpb   
                            , SUM(qty_cs) AS qty_cs   
                            , SUM(qty_ls) AS qty_ls   
                            , SUM(qty_or) AS qty_or   
                            , SUM(qty_qs) AS qty_qs   
                            , SUM(qty_lr) AS qty_lr   
                            , SUM(qty_hr) AS qty_hr   
                            , SUM(qty_cla) AS qty_cla   
                            , SUM(qty_total) AS qty_total   
                        FROM (
                                (    
                                    SELECT wo.branch_id   
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
                                    WHERE wo.state IN ('open', 'done', 'cancel')  
                                    %s  
                                    GROUP BY wo.branch_id   
                                    ORDER BY wo.branch_id   
                                ) 
                                UNION ALL 
                                (   
                                    SELECT wo.branch_id 
                                        , -1 * SUM(CASE WHEN wol.categ_id = 'Service' THEN COALESCE(wol.price_unit,0) * (1 - COALESCE(NULLIF(wol.discount,0),0) / 100) * COALESCE(wol.product_qty,0) END) amt_jasa
                                        , -1 * SUM(CASE WHEN wol.categ_id = 'Sparepart' AND pc.name NOT IN ( 'OLI','OIL') THEN COALESCE(wol.price_unit,0) * (1 - COALESCE(NULLIF(wol.discount,0),0) / 100)  * wol.supply_qty END) amt_part
                                        , -1 * SUM(CASE WHEN wol.categ_id = 'Sparepart' AND pc.name = 'OIL' THEN COALESCE(wol.price_unit,0) * (1 - COALESCE(NULLIF(wol.discount,0),0) / 100)  * wol.supply_qty END) amt_oil
                                        , -1 * SUM(COALESCE(wol.price_unit,0) * (1 - COALESCE(NULLIF(wol.discount,0),0) / 100) / 1.1 * CASE WHEN wol.categ_id = 'Sparepart' THEN wol.supply_qty ELSE COALESCE(wol.product_qty,0) END) amt_total
                                        , -1 * SUM(CASE WHEN wol.categ_id = 'Service' AND pc2.name = 'KPB' THEN COALESCE(wol.product_qty,0) END) qty_kpb
                                        , -1 * SUM(CASE WHEN wol.categ_id = 'Service' AND pc.name = 'CS' THEN COALESCE(wol.product_qty,0) END) qty_cs
                                        , -1 * SUM(CASE WHEN wol.categ_id = 'Service' AND pc.name = 'LS' THEN COALESCE(wol.product_qty,0) END) qty_ls
                                        , -1 * SUM(CASE WHEN wol.categ_id = 'Service' AND pc.name = 'OR+' THEN COALESCE(wol.product_qty,0) END) qty_or
                                        , -1 * SUM(CASE WHEN wol.categ_id = 'Service' AND pc2.name = 'QS' THEN COALESCE(wol.product_qty,0) END) qty_qs
                                        , -1 * SUM(CASE WHEN wol.categ_id = 'Service' AND pc.name = 'LR' THEN COALESCE(wol.product_qty,0) END) qty_lr
                                        , -1 * SUM(CASE WHEN wol.categ_id = 'Service' AND pc.name = 'HR' THEN COALESCE(wol.product_qty,0) END) qty_hr
                                        , -1 * SUM(CASE WHEN wol.categ_id = 'Service' AND pc.name = 'CLA' THEN COALESCE(wol.product_qty,0) END) qty_cla
                                        , -1 * SUM(CASE WHEN wol.categ_id = 'Service' THEN COALESCE(wol.product_qty,0) END) qty_total
                                    FROM work_order_cancel woc 
                                    INNER JOIN wtc_work_order wo ON woc.work_order_id = wo.id 
                                    INNER JOIN account_invoice ai ON wo.id = ai.transaction_id AND ai.model_id IN (SELECT id FROM ir_model WHERE model = 'wtc.work.order')
                                    INNER JOIN wtc_work_order_line wol ON wo.id = wol.work_order_id
                                    LEFT JOIN product_product p ON wol.product_id = p.id 
                                    LEFT JOIN product_template pt ON p.product_tmpl_id = pt.id 
                                    LEFT JOIN product_category pc ON pt.categ_id = pc.id 
                                    LEFT JOIN product_category pc2 ON pc.parent_id = pc2.id 
                                    WHERE woc.state = 'confirmed'
                                    %s
                                    GROUP BY wo.branch_id 
                                    ORDER BY wo.branch_id 
                                )
                            ) detil_count    
                        GROUP BY branch_id    
                        ORDER BY branch_id    
                    ) wo_jasa         
                ON b.id = wo_jasa.branch_id         
                %s
                AND (wo_unit.branch_id > 0 OR wo_inv.branch_id > 0 OR wo_jasa.branch_id > 0)          
                ORDER BY branch_id              

                
            """ % (
                    query_where_wo_date,
                    query_where_woc_date,
                    query_where_wo_date,
                    query_where_woc_date,
                    query_where_wo_date,
                    query_where_woc_date,
                    query_where
                )  
        # print query
        # sdf
        cr.execute (query)
        ress = cr.dictfetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Unit Entry')
        worksheet.set_column('B1:B1', 16)
        worksheet.set_column('C1:C1', 26)
        worksheet.set_column('D1:D1', 13)
        worksheet.set_column('E1:E1', 18)
        worksheet.set_column('F1:F1', 18)
        worksheet.set_column('G1:G1', 18)
        worksheet.set_column('H1:H1', 18)
        worksheet.set_column('I1:I1', 20)
        worksheet.set_column('J1:J1', 15)
        worksheet.set_column('K1:K1', 15)
        worksheet.set_column('L1:L1', 15)
        worksheet.set_column('M1:M1', 15)
        worksheet.set_column('N1:N1', 15)
        worksheet.set_column('O1:O1', 15)
        worksheet.set_column('P1:P1', 15)
        worksheet.set_column('Q1:Q1', 15)
        worksheet.set_column('R1:R1', 15)
        worksheet.set_column('S1:S1', 15)
        worksheet.set_column('T1:T1', 15)
        worksheet.set_column('U1:U1', 15)
        worksheet.set_column('V1:V1', 17)
       
                        
        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        filename = 'Report Unit Entry '+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report Unit Entry' , wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])
        row=3
        rowsaldo = row
        row+=1
        no = 1 
        worksheet.merge_range('A%s:A%s' % (row+1,row+2), 'No', wbf['header'])  
        worksheet.merge_range('B%s:B%s' % (row+1,row+2), 'Branch Name', wbf['header']) 
        worksheet.merge_range('C%s:C%s' % (row+1,row+2), 'Branch Code', wbf['header']) 
        worksheet.merge_range('D%s:D%s' % (row+1,row+2), 'Unit', wbf['header']) 
        worksheet.merge_range('E%s:E%s' % (row+1,row+2), 'Invoice', wbf['header']) 
        worksheet.merge_range('F%s:F%s' % (row+1,row+2), 'Jasa', wbf['header']) 
        worksheet.merge_range('G%s:G%s' % (row+1,row+2), 'Part', wbf['header']) 
        worksheet.merge_range('H%s:H%s' % (row+1,row+2), 'Oli', wbf['header']) 
        worksheet.merge_range('I%s:I%s' % (row+1,row+2), 'Total', wbf['header']) 
        worksheet.merge_range('J%s:N%s' % (row+1,row+1), 'JENIS INVOICE', wbf['header']) 
        worksheet.write('J%s' % (row+2), 'KPB1' , wbf['header'])
        worksheet.write('K%s' % (row+2), 'KPB2' , wbf['header'])
        worksheet.write('L%s' % (row+2), 'KPB3' , wbf['header'])
        worksheet.write('M%s' % (row+2), 'KPB4' , wbf['header'])
        worksheet.write('N%s' % (row+2), 'CLAIM' , wbf['header'])
        worksheet.merge_range('O%s:T%s' % (row+1,row+1), 'KATEGORI JASA', wbf['header']) 
        worksheet.write('O%s' % (row+2), 'KPB' , wbf['header'])
        worksheet.write('P%s' % (row+2), 'CS' , wbf['header'])
        worksheet.write('Q%s' % (row+2), 'LS' , wbf['header'])
        worksheet.write('R%s' % (row+2), 'OR+' , wbf['header'])
        worksheet.write('S%s' % (row+2), 'LR' , wbf['header'])
        worksheet.write('T%s' % (row+2), 'HR +' , wbf['header'])
        worksheet.write('U%s' % (row+2), 'CLA' , wbf['header'])
        worksheet.write('V%s' % (row+2), 'Total' , wbf['header'])
        row+=3              
        no = 1     
        row1 = row
        
        grand_total_unit = 0
        grand_total_inv = 0
        grand_total_jasa = 0
        grand_total_sparepart = 0
        grand_total_oil = 0
        grand_total_all = 0
        grand_total_kpb1 = 0
        grand_total_kpb2 = 0
        grand_total_kpb3 = 0
        grand_total_kpb4 = 0
        grand_total_claim = 0
        grand_total_all_kpb = 0
        grand_total_cs = 0
        grand_total_ls = 0
        grand_total_or = 0
        grand_total_lr = 0
        grand_total_hr = 0
        grand_total_cla = 0
        grand_total_qty = 0
            
        for res in ress:
            branch_code = str(res.get('branch_code').encode('ascii','ignore').decode('ascii')) if res.get('branch_code') != None else ''
            branch_name = str(res.get('branch_name').encode('ascii','ignore').decode('ascii')) if res.get('branch_name') != None else ''
            total_unit = res.get('unit_entry')
            total_inv = res.get('cnt_inv')
            total_jasa = res.get('amt_jasa')
            total_sparepart = res.get('amt_part')
            total_oil = res.get('amt_oil')
            total_all = res.get('amt_total')
            total_kpb1 = res.get('cnt_kpb_1')
            total_kpb2 = res.get('cnt_kpb_2')
            total_kpb3 = res.get('cnt_kpb_3')
            total_kpb4 = res.get('cnt_kpb_4')
            total_claim = res.get('cnt_cla')
            total_all_kpb = res.get('qty_kpb')
            total_cs = res.get('qty_cs')
            total_ls = res.get('qty_ls')
            total_or = res.get('qty_or')
            total_qs = res.get('qty_qs')
            total_lr = res.get('qty_lr')
            total_hr = res.get('qty_hr')
            total_cla = res.get('qty_cla')
            total_qty = res.get('qty_total')

            worksheet.write('A%s' % row, no , wbf['content_number'])                    
            worksheet.write('B%s' % row, branch_code , wbf['content'])
            worksheet.write('C%s' % row, branch_name , wbf['content'])
            worksheet.write('D%s' % row, total_unit , wbf['content_float'])
            worksheet.write('E%s' % row, total_inv , wbf['content_float'])
            worksheet.write('F%s' % row, total_jasa , wbf['content_float'])
            worksheet.write('G%s' % row, total_sparepart , wbf['content_float'])
            worksheet.write('H%s' % row, total_oil , wbf['content_float'])
            worksheet.write('I%s' % row, total_all, wbf['content_float']) 
            worksheet.write('J%s' % row, total_kpb1 , wbf['content_float']) 
            worksheet.write('K%s' % row, total_kpb2, wbf['content_float'])  
            worksheet.write('L%s' % row, total_kpb3 , wbf['content_float'])
            worksheet.write('M%s' % row, total_kpb4 , wbf['content_float'])
            worksheet.write('N%s' % row, total_claim , wbf['content_float'])
            worksheet.write('O%s' % row, total_all_kpb , wbf['content_float'])
            worksheet.write('P%s' % row, total_cs , wbf['content_float'])
            worksheet.write('Q%s' % row, total_ls , wbf['content_float'])
            worksheet.write('R%s' % row, total_or , wbf['content_float'])
            worksheet.write('S%s' % row, total_lr , wbf['content_float'])
            worksheet.write('T%s' % row, total_hr , wbf['content_float'])
            worksheet.write('U%s' % row, total_cla , wbf['content_float'])
            worksheet.write('V%s' % row, total_qty, wbf['content_float'])

            no+=1
            row+=1
            
        
            grand_total_unit += total_unit
            grand_total_inv += total_inv
            grand_total_jasa += total_jasa
            grand_total_sparepart  += total_sparepart
            grand_total_oil += total_oil
            grand_total_all += total_all
            grand_total_kpb1 += total_kpb1
            grand_total_kpb2 += total_kpb2 
            grand_total_kpb3 += total_kpb3
            grand_total_kpb4 += total_kpb4
            grand_total_claim += total_claim
            grand_total_all_kpb += total_all_kpb
            grand_total_cs += total_cs
            grand_total_ls += total_ls
            grand_total_or += total_or
            grand_total_lr += total_lr 
            grand_total_hr += total_hr
            grand_total_cla += total_cla
            grand_total_qty += total_qty
            
        
        worksheet.autofilter('A6:T%s' % (row))  
        worksheet.freeze_panes(6, 3)
        
        #TOTAL
        worksheet.merge_range('A%s:C%s' % (row,row), 'Total', wbf['total'])  

        formula_total_unit = '{=subtotal(9,D%s:D%s)}' % (row1, row-1) 
        formula_total_inv = '{=subtotal(9,E%s:E%s)}' % (row1, row-1) 
        formula_total_jasa = '{=subtotal(9,F%s:F%s)}' % (row1, row-1) 
        formula_total_sparepart = '{=subtotal(9,G%s:G%s)}' % (row1, row-1) 
        formula_total_oil = '{=subtotal(9,H%s:H%s)}' % (row1, row-1) 
        formula_total_all = '{=subtotal(9,I%s:I%s)}' % (row1, row-1) 
        formula_total_kpb1 = '{=subtotal(9,J%s:J%s)}' % (row1, row-1) 
        formula_total_kpb2 = '{=subtotal(9,K%s:K%s)}' % (row1, row-1)   
        formula_total_kpb3 = '{=subtotal(9,L%s:L%s)}' % (row1, row-1) 
        formula_total_kpb4 = '{=subtotal(9,M%s:M%s)}' % (row1, row-1) 
        formula_total_claim = '{=subtotal(9,N%s:N%s)}' % (row1, row-1) 
        formula_total_all_kpb = '{=subtotal(9,O%s:O%s)}' % (row1, row-1) 
        formula_total_cs = '{=subtotal(9,P%s:P%s)}' % (row1, row-1) 
        formula_total_ls = '{=subtotal(9,Q%s:Q%s)}' % (row1, row-1) 
        formula_total_or = '{=subtotal(9,R%s:R%s)}' % (row1, row-1) 
        formula_total_lr = '{=subtotal(9,S%s:S%s)}' % (row1, row-1) 
        formula_total_hr = '{=subtotal(9,T%s:T%s)}' % (row1, row-1) 
        formula_total_cla = '{=subtotal(9,U%s:U%s)}' % (row1, row-1) 
        formula_total_qty = '{=subtotal(9,V%s:V%s)}' % (row1, row-1) 
       
       
        worksheet.write_formula(row-1,3,formula_total_unit, wbf['total_float'], grand_total_unit)                  
        worksheet.write_formula(row-1,4,formula_total_inv, wbf['total_float'], grand_total_inv)
        worksheet.write_formula(row-1,5,formula_total_jasa, wbf['total_float'],grand_total_jasa)
        worksheet.write_formula(row-1,6,formula_total_sparepart, wbf['total_float'], grand_total_sparepart)
        worksheet.write_formula(row-1,7,formula_total_oil, wbf['total_float'], grand_total_oil) 
        worksheet.write_formula(row-1,8,formula_total_all, wbf['total_float'], grand_total_all)
        worksheet.write_formula(row-1,9,formula_total_kpb1, wbf['total_float'], grand_total_kpb1)
        worksheet.write_formula(row-1,10,formula_total_kpb2, wbf['total_float'], grand_total_kpb2)
        worksheet.write_formula(row-1,11,formula_total_kpb3, wbf['total_float'], grand_total_kpb3)
        worksheet.write_formula(row-1,12,formula_total_kpb4, wbf['total_float'], grand_total_kpb4)
        worksheet.write_formula(row-1,13,formula_total_claim, wbf['total_float'], grand_total_claim)
        worksheet.write_formula(row-1,14,formula_total_all_kpb, wbf['total_float'], grand_total_all_kpb)
        worksheet.write_formula(row-1,15,formula_total_cs, wbf['total_float'], grand_total_cs)
        worksheet.write_formula(row-1,16,formula_total_ls, wbf['total_float'], grand_total_ls)
        worksheet.write_formula(row-1,17,formula_total_or, wbf['total_float'], grand_total_or)
        worksheet.write_formula(row-1,18,formula_total_lr, wbf['total_float'], grand_total_lr)
        worksheet.write_formula(row-1,19,formula_total_hr, wbf['total_float'], grand_total_hr)
        worksheet.write_formula(row-1,20,formula_total_cla, wbf['total_float'], grand_total_cla)
        worksheet.write_formula(row-1,21,formula_total_qty, wbf['total_float'], grand_total_qty)
        
        worksheet.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])  
        
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_workshop', 'view_report_workshop_wizard')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.report.workshop.wizard',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }

wtc_report_workshop()
