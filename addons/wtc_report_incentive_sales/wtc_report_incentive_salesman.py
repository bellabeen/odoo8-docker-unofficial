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

class wtc_report_incentive_salesman(osv.osv_memory):
    _inherit = "wtc.report.incentive.sale.wizard"
    
    wbf = {}
    
    def _print_excel_report_salesman(self, cr, uid, ids, data, context=None): 
        branch_ids = data['branch_ids'] 
        start_date = data['start_date']
        end_date = data['end_date']
        tz = '7 hours'
        query_where = " "
    

        if branch_ids :
            query_where += " AND branch.id in %s" % str(tuple(branch_ids)).replace(',)', ')')
    
        start_date_a= datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date_a= datetime.strptime(end_date, "%Y-%m-%d").date()
        start_date_min = start_date_a + relativedelta(months=-1)
        end_date_min = end_date_a + relativedelta(months=-1)
        
        sales_type="salesman" 
        query_not_in_date=""" AND dso.date_order NOT  BETWEEN '%s' AND '%s' """ %(start_date,end_date)                               
        query = """
                    SELECT 
                    COALESCE(branch.code,'') as branch_code, 
                    COALESCE(branch.name,'') as branch_name,
                    COALESCE(hr_sales.nip,'') as sales_nip, 
                    COALESCE(sales.name,'') as sales_name, 
                    COALESCE(job.name,'') as job_name,
                    absen.total_absensi as total_absensi,
                    (absen.total_absensi / absen.jumlah_hari_kerja :: FLOAT) * 100 as persen_absensi,
                    COALESCE(SUM(case when dso.state = 'cancelled'  """+query_not_in_date+""" then -1 *  dsol.product_qty  else  dsol.product_qty  end),0) as total_unit,
                    COALESCE( SUM (CASE   WHEN dso.finco_id IS NULL  and dso.state = 'cancelled'   """+query_not_in_date+""" then  -1 *  dsol.product_qty    WHEN dso.finco_id IS NULL then dsol.product_qty  END ),0)  as total_cash,
                    COALESCE(SUM (CASE   WHEN dso.finco_id IS NOT NULL  and dso.state = 'cancelled'   """+query_not_in_date+""" then  -1 *  dsol.product_qty    WHEN dso.finco_id IS NOT NULL then dsol.product_qty  END ),0)  as total_credit,
                    
                    COALESCE(SUM (CASE   WHEN dso.partner_komisi_id IS NOT NULL  and dso.finco_id IS NULL and dso.state = 'cancelled'  """+query_not_in_date+"""  then  -1 *  dsol.product_qty    WHEN dso.partner_komisi_id IS NOT NULL and dso.finco_id IS NULL then dsol.product_qty  END ),0)  as total_mediator_cash,
                    COALESCE(SUM (CASE   WHEN dso.partner_komisi_id IS NOT NULL  and dso.finco_id IS NOT NULL and dso.state = 'cancelled'   """+query_not_in_date+""" then  -1 *  dsol.product_qty    WHEN dso.partner_komisi_id IS NOT NULL and dso.finco_id IS NOT NULL then dsol.product_qty  END ),0)  as total_mediator_credit,
                    
                    COALESCE(SUM (CASE   WHEN plat='M'  and dso.finco_id IS NULL and dso.state = 'cancelled'  """+query_not_in_date+""" then  -1 *  dsol.product_qty    WHEN plat='M' and dso.finco_id IS NULL then dsol.product_qty  END ),0)  as total_gc_cash,
                    COALESCE(SUM (CASE   WHEN plat='M' and dso.finco_id IS NOT NULL and dso.state = 'cancelled'  """+query_not_in_date+"""  then  -1 *  dsol.product_qty    WHEN plat='M' and dso.finco_id IS NOT NULL then dsol.product_qty  END ),0)  as total_gc_credit,
                    
                    COALESCE(SUM(CASE   WHEN inv.state='open'   and dso.finco_id IS NULL and plat='H' and dso.state = 'cancelled'   """+query_not_in_date+"""  then -1 * dsol.product_qty   WHEN  inv.state='open'  and dso.finco_id IS NULL and plat='H' then dsol.product_qty  END ),0) as ar_cash_retail,
                    COALESCE(SUM(CASE   WHEN inv.state='open'  and dso.finco_id IS NOT NULL and plat='H' and dso.state = 'cancelled'   """+query_not_in_date+""" then -1 * dsol.product_qty  WHEN  inv.state='open'  and dso.finco_id IS NOT NULL and plat='H' then dsol.product_qty  END ),0) as ar_credit_retail,
                    COALESCE(SUM(CASE   WHEN inv.state='open'  and dso.finco_id IS NULL and plat='M' and dso.state = 'cancelled'  """+query_not_in_date+"""  then -1 * dsol.product_qty  WHEN  inv.state='open'   and dso.finco_id IS NULL and plat='M' then dsol.product_qty  END),0) as ar_cash_gc,
                    COALESCE(SUM(CASE   WHEN inv.state='open'  and dso.finco_id IS NOT NULL and plat='M' and dso.state = 'cancelled'  """+query_not_in_date+"""  then -1 * dsol.product_qty  WHEN  inv.state='open'   and dso.finco_id IS NOT NULL and plat='M' then dsol.product_qty  END),0) as ar_credit_gc,
                    absen.sp as sp,
                    branch.cluster AS cluster
                    FROM dealer_sale_order as dso
                    LEFT JOIN dealer_sale_order_line AS dsol
                    ON  dsol.dealer_sale_order_line_id = dso.id 
                    LEFT JOIN wtc_branch as branch
                    ON branch.id=dso.branch_id
                    LEFT JOIN res_users as users
                    ON users.id=dso.user_id
                    LEFT JOIN resource_resource sales 
                    ON users.id = sales.user_id 
                    LEFT JOIN hr_employee hr_sales 
                    ON sales.id = hr_sales.resource_id 
                    LEFT JOIN hr_job job
                    ON hr_sales.job_id = job.id
                    LEFT JOIN wtc_absensi as absen
                    ON absen.nip=hr_sales.nip 
                    LEFT JOIN account_invoice as inv
                    ON dso.name=inv.origin
                    where  dso.state in ('progress', 'done') and dso.date_order between '%s' and '%s' 
                    %s
                    AND job.sales_force='salesman' 
                    AND absen.bulan='%s'
                    AND inv.tipe='customer'
                    
                    GROUP BY hr_sales.nip,sales.name,job.name,branch.code,branch.name,absen.total_absensi,absen.jumlah_hari_kerja,absen.sp,branch.cluster
                    order by sales.name
            """ % (start_date,end_date,query_where,start_date[:-3])            
                    
        cr.execute (query)
        ress = cr.fetchall()
        
        
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Incentive Salesman')
        worksheet.set_column('B1:B1', 13)
        worksheet.set_column('C1:C1', 25)
        worksheet.set_column('D1:D1', 20)
        worksheet.set_column('E1:E1', 25)
        worksheet.set_column('F1:F1', 25)
        worksheet.set_column('G1:G1', 15)
        worksheet.set_column('H1:H1', 15)
        worksheet.set_column('I1:I1', 15)
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
        worksheet.set_column('V1:V1', 15)
        worksheet.set_column('W1:W1', 15)
        worksheet.set_column('X1:X1', 15)
        worksheet.set_column('Y1:Y1', 15)
        worksheet.set_column('Z1:Z1', 15)
        worksheet.set_column('AA1:AA1', 15)
        worksheet.set_column('AB1:AB1', 15)
        worksheet.set_column('AC1:AC1', 20)
        worksheet.set_column('AD1:AD1', 20) 
        worksheet.set_column('AE1:AE1', 20)
        worksheet.set_column('AF1:AF1', 20)
     
                        
        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        filename = 'Report Incentive Salesman '+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report Incentive Salesman' , wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])
        row=5
        rowsaldo = row
        row+=1
        worksheet.merge_range('A%s:K%s' % (5,6), '' , wbf['header'])
        worksheet.merge_range('L%s:M%s' % (5,6), 'SALES' , wbf['header'])
        worksheet.merge_range('N%s:O%s' % (5,6), 'FIX/MEDIATOR' , wbf['header'])
        worksheet.merge_range('P%s:Q%s' % (5,6), 'GC' , wbf['header'])
        worksheet.merge_range('R%s:U%s' % (5,5), 'AR' , wbf['header'])
        worksheet.merge_range('R%s:S%s' % (6,6), 'RETAIL' , wbf['header'])
        worksheet.merge_range('T%s:U%s' % (6,6), 'GC' , wbf['header'])
        worksheet.merge_range('V%s:Y%s' % (5,5), 'INSENTIF' , wbf['header'])
        worksheet.merge_range('V%s:W%s' % (6,6), 'PER UNIT' , wbf['header'])
        worksheet.merge_range('X%s:Y%s' % (6,6), 'SALES' , wbf['header'])
        worksheet.merge_range('Z%s:AF%s' % (5,6), ' ' , wbf['header'])
        
        
        worksheet.merge_range('A%s:A%s' % (row+1,row+2), 'No' , wbf['header'])
        worksheet.merge_range('B%s:B%s' % (row+1,row+2), 'Branch Code' , wbf['header'])
        worksheet.merge_range('C%s:C%s' % (row+1,row+2), 'Branch Name' , wbf['header'])
        worksheet.merge_range('D%s:D%s' % (row+1,row+2), 'NIP' , wbf['header'])
        worksheet.merge_range('E%s:E%s' % (row+1,row+2), 'Nama' , wbf['header'])
        worksheet.merge_range('F%s:F%s' % (row+1,row+2), 'Jabatan' , wbf['header'])
        worksheet.merge_range('G%s:G%s' % (row+1,row+2), 'N \n Absensi' , wbf['header'])
        worksheet.merge_range('H%s:H%s' % (row+1,row+2), '% \n Absensi' , wbf['header'])
        worksheet.merge_range('I%s:I%s' % (row+1,row+2), 'Ket' , wbf['header'])
        worksheet.merge_range('J%s:J%s' % (row+1,row+2), 'Ket Cluster' , wbf['header'])
        worksheet.merge_range('K%s:K%s' % (row+1,row+2), 'Total' , wbf['header'])
        
        worksheet.merge_range('L%s:L%s' % (row+1,row+2), 'Cash' , wbf['header'])
        worksheet.merge_range('M%s:M%s' % (row+1,row+2), 'Credit' , wbf['header'])
        
        worksheet.merge_range('N%s:N%s' % (row+1,row+2), 'Cash' , wbf['header'])
        worksheet.merge_range('O%s:O%s' % (row+1,row+2), 'Credit' , wbf['header'])
        
        worksheet.merge_range('P%s:P%s' % (row+1,row+2), 'Cash' , wbf['header'])
        worksheet.merge_range('Q%s:Q%s' % (row+1,row+2), 'Credit' , wbf['header'])
        
        worksheet.merge_range('R%s:R%s' % (row+1,row+2), 'Cash' , wbf['header'])
        worksheet.merge_range('S%s:S%s' % (row+1,row+2), 'Credit' , wbf['header'])
        
        worksheet.merge_range('T%s:T%s' % (row+1,row+2), 'Cash' , wbf['header'])
        worksheet.merge_range('U%s:U%s' % (row+1,row+2), 'Credit' , wbf['header'])
        
        worksheet.merge_range('V%s:V%s' % (row+1,row+2), 'Cash' , wbf['header'])
        worksheet.merge_range('W%s:W%s' % (row+1,row+2), 'Credit' , wbf['header'])
        
        worksheet.merge_range('X%s:X%s' % (row+1,row+2), 'Cash' , wbf['header'])
        worksheet.merge_range('Y%s:Y%s' % (row+1,row+2), 'Credit' , wbf['header'])
        
        worksheet.merge_range('Z%s:Z%s' % (row+1,row+2), 'Reward' , wbf['header'])
#         worksheet.merge_range('AA%s:AA%s' % (row+1,row+2), 'INCENTIVE DITAHAN' , wbf['header'])
#         worksheet.merge_range('AB%s:AB%s' % (row+1,row+2), 'POTONGAN MEDIATOR' , wbf['header'])
#         worksheet.merge_range('AC%s:AC%s' % (row+1,row+2), 'INCENTIVE BULAN LALU AR LUNAS' , wbf['header'])

        worksheet.merge_range('AA%s:AA%s' % (row+1,row+2), 'INCENTIVE DITAHAN/INCENTIVE BULAN LALU AR LUNAS' , wbf['header'])
        worksheet.merge_range('AB%s:AB%s' % (row+1,row+2), 'POTONGAN MEDIATOR' , wbf['header'])
        worksheet.merge_range('AC%s:AC%s' % (row+1,row+2), '' , wbf['header'])


        worksheet.merge_range('AD%s:AD%s' % (row+1,row+2), 'TOTAL' , wbf['header'])
        worksheet.merge_range('AE%s:AE%s' % (row+1,row+2), 'SP' , wbf['header'])
#         worksheet.merge_range('AF%s:AF%s' % (row+1,row+2), 'Punishment' , wbf['header'])
        worksheet.merge_range('AF%s:AF%s' % (row+1,row+2), 'Total Incentive' , wbf['header'])
        
        

        row+=3               
        no = 1     
        row1 = row
        
        grand_total_unit=0
        grand_total_cash=0
        grand_total_credit=0
        
        grand_total_cash_mediator=0
        grand_total_credit_mediator=0
        
        grand_total_cash_gc=0
        grand_total_credit_gc=0
        
        grand_total_cash_ar_retail=0
        grand_total_credit_ar_retail=0
        
        grand_total_cash_ar_gc=0
        grand_total_credit_ar_gc=0
        
        grand_total_incentive_cash=0
        grand_total_incentive_credit=0
        
        grand_total_incentive_incentive_ditahan=0
        grand_total_incentive_potongan_mediator=0
        grand_total_bulan_lalu=0
        
        
        grand_total_incentive_reward_fix=0
        grand_total_incentive=0
        grand_total_incentive_fix=0
        
        
      

        
        for res in ress:
            mediator_cash = res[10]
            mediator_credit = res[11]
            total_mediator =mediator_cash+mediator_credit #TIDAK DIBAYARKAN
            branch_code = str(res[0].encode('ascii','ignore').decode('ascii')) if res[0] != None else ''
            branch_name = str(res[1].encode('ascii','ignore').decode('ascii')) if res[1] != None else ''
            nip_sales = str(res[2].encode('ascii','ignore').decode('ascii')) if res[2] != None else ''
            nama_sales = str(res[3].encode('ascii','ignore').decode('ascii')) if res[3] != None else ''
            jabatan = str(res[4].encode('ascii','ignore').decode('ascii')) if res[4] != None else ''
            total_absensi = res[5]
            persen_absensi =res[6]
            #total_unit = res[7]-total_mediator
            total_unit = res[7]
            #cash = res[8]-mediator_cash
            cash = res[8]
            #credit = res[9]-mediator_credit
            credit = res[9]
            gc_cash = res[12]
            gc_credit = res[13]
            ar_retail_cash = res[14]
            ar_retail_credit = res[15]
            ar_gc_cash = res[16]
            ar_gc_credit = res[17]
            sp = res[18]
            cluster = res[19]
            
            
            [incentive_cash, incentive_credit, incentive_reward]=self._get_incentive(cr,uid,ids,sales_type,cluster,total_unit,total_unit,total_unit,nip_sales,context) 

            
            incentive_cash_amount=incentive_cash*cash
            incentive_credit_amount=incentive_credit*credit
            incentive_reward=incentive_reward
            ar_cash_retail=incentive_cash*ar_retail_cash
            ar_credit_retail=incentive_credit*ar_retail_credit
            ar_cash_gc=incentive_cash*ar_gc_cash
            ar_credit_gc=incentive_credit*ar_gc_credit
            potongan_mediator_cash=mediator_cash*incentive_cash
            potongan_mediator_creadit=mediator_credit*incentive_credit
            
            incentive_reward_fix=incentive_reward* float( (persen_absensi/100) )
            
            incentive_ditahan=ar_cash_retail+ar_credit_retail+ar_cash_gc+ar_credit_gc
            potongan_mediator_all=potongan_mediator_cash+potongan_mediator_creadit
            
            
            
            total_incentive=(incentive_cash_amount+incentive_credit_amount+incentive_reward_fix)-(incentive_ditahan+potongan_mediator_all)
            
            if sp == 1 :
                total_incentive_fix=total_incentive-(total_incentive*0.25)
            elif sp == 2:
                total_incentive_fix=total_incentive-(total_incentive*0.5)
            elif sp == 3:
                total_incentive_fix=total_incentive-(total_incentive*1)
            else :
                total_incentive_fix=total_incentive
                
            worksheet.write('A%s' % row, no , wbf['content_number'])                    
            worksheet.write('B%s' % row, branch_code , wbf['content'])
            worksheet.write('C%s' % row, branch_name , wbf['content'])
            worksheet.write('D%s' % row, nip_sales , wbf['content'])
            worksheet.write('E%s' % row, nama_sales , wbf['content'])
            worksheet.write('F%s' % row, jabatan , wbf['content'])
            worksheet.write('G%s' % row, total_absensi , wbf['content_float'])
            worksheet.write('H%s' % row, str(persen_absensi)+'%' , wbf['content']) 
            worksheet.write('I%s' % row, ' ', wbf['content_float'])  
            worksheet.write('J%s' % row, cluster , wbf['content'])
            worksheet.write('K%s' % row, total_unit , wbf['content_float'])
            worksheet.write('L%s' % row, cash , wbf['content_float'])
            worksheet.write('M%s' % row, credit , wbf['content_float'])
            worksheet.write('N%s' % row, mediator_cash , wbf['content_float'])
            worksheet.write('O%s' % row, mediator_credit , wbf['content_float'])
            worksheet.write('P%s' % row, gc_cash , wbf['content_float'])
            worksheet.write('Q%s' % row, gc_credit , wbf['content_float'])
            worksheet.write('R%s' % row, ar_cash_retail , wbf['content_float'])
            worksheet.write('S%s' % row, ar_credit_retail , wbf['content_float'])
            worksheet.write('T%s' % row, ar_cash_gc , wbf['content_float'])
            worksheet.write('U%s' % row, ar_credit_gc , wbf['content_float'])
            worksheet.write('V%s' % row, incentive_cash , wbf['content_float'])
            worksheet.write('W%s' % row, incentive_credit , wbf['content_float'])
            worksheet.write('X%s' % row, incentive_cash_amount , wbf['content_float'])
            worksheet.write('Y%s' % row, incentive_credit_amount , wbf['content_float'])
            worksheet.write('Z%s' % row, incentive_reward_fix , wbf['content_float'])
            
            worksheet.write('AA%s' % row, incentive_ditahan , wbf['content_float'])
            worksheet.write('AB%s' % row, potongan_mediator_all , wbf['content'])
            worksheet.write('AC%s' % row, ' ' , wbf['content_float'])
            
            
            worksheet.write('AD%s' % row, total_incentive , wbf['content_float'])
            worksheet.write('AE%s' % row, sp , wbf['content'])
            worksheet.write('AF%s' % row, total_incentive_fix , wbf['content_float'])
            no+=1
            row+=1
            

        
            grand_total_unit +=total_unit
            grand_total_cash +=cash
            grand_total_credit +=credit
            
            grand_total_cash_mediator +=mediator_cash
            grand_total_credit_mediator +=mediator_credit
            
            grand_total_cash_gc +=gc_cash
            grand_total_credit_gc +=gc_credit
            
            grand_total_cash_ar_retail +=ar_cash_retail
            grand_total_credit_ar_retail +=ar_credit_retail
            
            grand_total_cash_ar_gc +=ar_cash_gc
            grand_total_credit_ar_gc +=ar_credit_gc
            
            grand_total_incentive_cash +=incentive_cash
            grand_total_incentive_credit +=incentive_credit
            
            grand_total_incentive +=total_incentive
            
            grand_total_incentive_incentive_ditahan +=incentive_ditahan
            grand_total_incentive_potongan_mediator +=potongan_mediator_all
            grand_total_bulan_lalu=0
        
        
            grand_total_incentive_fix +=total_incentive_fix
            
            grand_total_incentive_reward_fix +=incentive_reward_fix
               
        

            
        
        worksheet.autofilter('A7:O%s' % (row))  
#         worksheet.freeze_panes(6, 5)
        
        #TOTAL
        worksheet.merge_range('A%s:F%s' % (row,row), 'Total', wbf['total'])    
        worksheet.merge_range('G%s:J%s' % (row,row), '', wbf['total'])
        worksheet.merge_range('V%s:W%s' % (row,row), '', wbf['total'])
        worksheet.write('AF%s' % (row), '', wbf['total'])
        
       
        
        formula_total_unit = '{=subtotal(9,K%s:K%s)}' % (row1, row-1) 
        formula_total_cash = '{=subtotal(9,L%s:L%s)}' % (row1, row-1) 
        formula_total_credit = '{=subtotal(9,M%s:M%s)}' % (row1, row-1) 
        formula_total_cash_mediator = '{=subtotal(9,N%s:N%s)}' % (row1, row-1) 
        formula_total_credit_mediator = '{=subtotal(9,O%s:O%s)}' % (row1, row-1) 
        formula_total_cash_gc = '{=subtotal(9,P%s:P%s)}' % (row1, row-1) 
        formula_total_credit_gc = '{=subtotal(9,Q%s:Q%s)}' % (row1, row-1) 
        formula_total_cash_ar_retail = '{=subtotal(9,R%s:R%s)}' % (row1, row-1) 
        formula_total_credit_ar_retail = '{=subtotal(9,S%s:S%s)}' % (row1, row-1) 
        formula_total_cash_ar_gc = '{=subtotal(9,T%s:T%s)}' % (row1, row-1) 
        formula_total_credit_ar_gc = '{=subtotal(9,U%s:U%s)}' % (row1, row-1)
        formula_total_incentive_cash = '{=subtotal(9,X%s:X%s)}' % (row1, row-1) 
        formula_total_incentive_credit = '{=subtotal(9,Y%s:Y%s)}' % (row1, row-1)  
        formula_total_reward_fix = '{=subtotal(9,Z%s:Z%s)}' % (row1, row-1)  
        
        formula_total_incentive_ditahan = '{=subtotal(9,AA%s:AA%s)}' % (row1, row-1) 
        formula_total_incentive_potongan_mediator = '{=subtotal(9,AB%s:AB%s)}' % (row1, row-1) 
        bulan_lalu = '{=subtotal(9,AC%s:AC%s)}' % (row1, row-1)   
        
        formula_total_incentive = '{=subtotal(9,AD%s:AD%s)}' % (row1, row-1) 
        formula_total_incentive_fix = '{=subtotal(9,AF%s:AFC%s)}' % (row1, row-1)  
 
 
 
        worksheet.write_formula(row-1,10,formula_total_unit, wbf['total_float'], grand_total_unit)                  
        worksheet.write_formula(row-1,11,formula_total_cash, wbf['total_float'], grand_total_cash )
        worksheet.write_formula(row-1,12,formula_total_credit, wbf['total_float'],grand_total_credit)
        worksheet.write_formula(row-1,13,formula_total_cash_mediator, wbf['total_float'],grand_total_cash_mediator)
        worksheet.write_formula(row-1,14,formula_total_credit_mediator, wbf['total_float'],grand_total_credit_mediator)
        worksheet.write_formula(row-1,15,formula_total_cash_gc, wbf['total_float'], grand_total_cash_gc)
        worksheet.write_formula(row-1,16,formula_total_credit_gc, wbf['total_float'], grand_total_credit_gc) 
        worksheet.write_formula(row-1,17,formula_total_cash_ar_retail, wbf['total_float'], grand_total_cash_ar_retail)
        worksheet.write_formula(row-1,18,formula_total_credit_ar_retail, wbf['total_float'], grand_total_credit_ar_retail)
        worksheet.write_formula(row-1,19,formula_total_cash_ar_gc, wbf['total_float'], grand_total_cash_ar_gc)
        worksheet.write_formula(row-1,20,formula_total_credit_ar_gc, wbf['total_float'], grand_total_credit_ar_gc)
        worksheet.write_formula(row-1,23,formula_total_incentive_cash, wbf['total_float'], grand_total_incentive_cash)
        worksheet.write_formula(row-1,24,formula_total_incentive_credit, wbf['total_float'], grand_total_incentive_credit)
        worksheet.write_formula(row-1,25,formula_total_reward_fix, wbf['total_float'], grand_total_incentive_reward_fix)
        
        worksheet.write_formula(row-1,26,formula_total_incentive_ditahan, wbf['total_float'], grand_total_incentive_incentive_ditahan)
        worksheet.write_formula(row-1,27,formula_total_incentive_potongan_mediator, wbf['total_float'], grand_total_incentive_potongan_mediator)
        worksheet.write_formula(row-1,28,bulan_lalu, wbf['total_float'], grand_total_bulan_lalu)
        
        worksheet.write_formula(row-1,29,formula_total_incentive, wbf['total_float'], grand_total_incentive)
        worksheet.write_formula(row-1,31,formula_total_incentive_fix, wbf['total_float'], grand_total_incentive_fix)
        worksheet.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])  
                   
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()
       