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

class wtc_report_incentive_sales_partner(osv.osv_memory):
    _inherit = "wtc.report.incentive.sale.wizard"
    
    wbf = {}
    
    def _print_excel_report_sales_partner(self, cr, uid, ids, data, context=None): 
        branch_ids = data['branch_ids'] 
        start_date = data['start_date']
        end_date = data['end_date']
        tz = '7 hours'
        query_where = " "

        if branch_ids :
            query_where += " AND branch.id in %s" % str(tuple(branch_ids)).replace(',)', ')')
    
        sales_type="sales_partner"   
        query_not_in_date=""" AND dso.date_order NOT  BETWEEN '%s' AND '%s' """ %(start_date,end_date)  
        
        query_jumlah_hari=""" 
        SELECT jumlah_hari_kerja,bulan from wtc_absensi
        where bulan='%s' limit 1 
        """   % (start_date[:-3]) 
        cr.execute (query_jumlah_hari)
        res_max = cr.fetchone()
        jumlah_hari=res_max[0] 
          
        query = """
                SELECT 
                COALESCE(branch.code,'') as branch_code, 
                COALESCE(branch.name,'') as branch_name,
                COALESCE(hr_sales.nip,'') as sales_nip, 
                COALESCE(sales.name,'') as sales_name, 
                COALESCE(job.name,'') as job_name,
                COALESCE( SUM (CASE   WHEN dso.finco_id IS NULL  and dso.state = 'cancelled'  """+query_not_in_date+""" then  -1 *  dsol.product_qty    WHEN dso.finco_id IS NULL then dsol.product_qty  END ),0)  as total_cash,
                COALESCE(SUM (CASE   WHEN dso.finco_id IS NOT NULL  and dso.state = 'cancelled'  """+query_not_in_date+""" then  -1 *  dsol.product_qty    WHEN dso.finco_id IS NOT NULL then dsol.product_qty  END ),0)  as total_credit,
                COALESCE(SUM(case when dso.state = 'cancelled' """+query_not_in_date+""" then -1 *  dsol.product_qty  else  dsol.product_qty  end),0) as total_unit,
                COALESCE(SUM (CASE   WHEN dso.partner_komisi_id IS NOT NULL  and dso.state = 'cancelled'  """+query_not_in_date+""" then  -1 *  dsol.product_qty    WHEN dso.partner_komisi_id IS NOT NULL then dsol.product_qty  END ),0)  as total_mediator,
                ' ' as total_absensi,
                ' ' as jumlah_hari_kerja,
                ' ' as cluster
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
                --LEFT JOIN wtc_absensi as absen
                --ON absen.nip=hr_sales.nip       
                where dso.state in ('progress', 'done') and dso.date_order between '%s' and '%s'
                %s 
                AND job.sales_force='sales_partner' 
                
                GROUP BY hr_sales.nip,sales.name,job.name,branch.code,branch.name
                order by sales.name
            """ % (start_date,end_date,query_where)                    
        
        cr.execute (query)
        ress = cr.fetchall()
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Incentive Sales Partner')
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
        
        filename = 'Report Incentive Sales Partner '+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report Incentive Sales Partner' , wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])
        row=5
        rowsaldo = row
        row+=1
        worksheet.merge_range('A%s:I%s' % (5,6), '' , wbf['header'])
        worksheet.merge_range('J%s:K%s' % (5,6), 'Credit Percentage' , wbf['header'])
        worksheet.merge_range('L%s:N%s' % (5,6), 'Mediator' , wbf['header'])
        worksheet.merge_range('O%s:P%s' % (5,6), 'Absensi' , wbf['header'])
        worksheet.merge_range('Q%s:V%s' % (5,6), ' ' , wbf['header'])
        worksheet.merge_range('A%s:A%s' % (row+1,row+2), 'No' , wbf['header'])
        worksheet.merge_range('B%s:B%s' % (row+1,row+2), 'Branch Code' , wbf['header'])
        worksheet.merge_range('C%s:C%s' % (row+1,row+2), 'Branch Name' , wbf['header'])
        worksheet.merge_range('D%s:D%s' % (row+1,row+2), 'NIP' , wbf['header'])
        worksheet.merge_range('E%s:E%s' % (row+1,row+2), 'Nama' , wbf['header'])
        worksheet.merge_range('F%s:F%s' % (row+1,row+2), 'Jabatan' , wbf['header'])
        worksheet.merge_range('G%s:G%s' % (row+1,row+2), 'Cash' , wbf['header'])
        worksheet.merge_range('H%s:H%s' % (row+1,row+2), 'Credit' , wbf['header'])
        worksheet.merge_range('I%s:I%s' % (row+1,row+2), 'Total Unit' , wbf['header'])
        worksheet.merge_range('J%s:J%s' % (row+1,row+2), '%' , wbf['header'])
        worksheet.merge_range('K%s:K%s' % (row+1,row+2), 'Percentage' , wbf['header'])
        worksheet.merge_range('L%s:L%s' % (row+1,row+2), 'Unit' , wbf['header'])
        worksheet.merge_range('M%s:M%s' % (row+1,row+2), '%' , wbf['header'])
        worksheet.merge_range('N%s:N%s' % (row+1,row+2), 'Mediator' , wbf['header'])
        worksheet.merge_range('O%s:O%s' % (row+1,row+2), 'Hadir' , wbf['header'])
        worksheet.merge_range('P%s:P%s' % (row+1,row+2), '%' , wbf['header'])
        worksheet.merge_range('Q%s:Q%s' % (row+1,row+2), 'Incentive Penjualan' , wbf['header'])
        worksheet.merge_range('R%s:R%s' % (row+1,row+2), 'Unit Kredit' , wbf['header'])
        worksheet.merge_range('S%s:S%s' % (row+1,row+2), 'Reward' , wbf['header'])
        worksheet.merge_range('T%s:T%s' % (row+1,row+2), 'Total Incentive' , wbf['header'])
        worksheet.merge_range('U%s:U%s' % (row+1,row+2), 'Bank' , wbf['header'])
        worksheet.merge_range('V%s:V%s' % (row+1,row+2), 'No Rekening' , wbf['header'])
      
    
        row+=3               
        no = 1     
        row1 = row
        grand_total_cash=0
        grand_total_credit=0
        grand_total_unit=0
        grand_total_persen_credit=0
        grand_total_percentage_credit=0
        grand_total_mediator=0
        grand_total_persen_mediator=0
        grand_total_percentage_mediator=0
        grand_total_mediator=0
        
        grand_total_incentive_penjualan=0
        grand_total_incentive_credit=0
        grand_total_incentive_reward=0
        grand_total_total_incentive=0
        
        for res in ress:
            branch_code = str(res[0].encode('ascii','ignore').decode('ascii')) if res[0] != None else ''
            branch_name = str(res[1].encode('ascii','ignore').decode('ascii')) if res[1] != None else ''
            nip_sales = str(res[2].encode('ascii','ignore').decode('ascii')) if res[2] != None else ''
            nama_sales = str(res[3].encode('ascii','ignore').decode('ascii')) if res[3] != None else ''
            jabatan = str(res[4].encode('ascii','ignore').decode('ascii')) if res[4] != None else ''
            cash = res[5]
            credit =res[6]
            total_unit = res[7]
            persen_credit=round(float(credit)/float(total_unit)*100)
            total_mediator = res[8]
            persen_mediator=round(float(total_mediator)/float(total_unit)*100)
            total_absensi= 'full'
            jumlah_hari_kerja= jumlah_hari
            cluster = res[11]
            #persentasi_absensi=round(( (float(total_absensi)/float(jumlah_hari_kerja)) * 100))
            
            
            [incentive_cash, incentive_credit, incentive_reward]=self._get_incentive(cr,uid,ids,sales_type,cluster,total_unit,credit,total_unit,nip_sales,context) 

            incentive_penjualan=incentive_cash
            incentive_credit=incentive_credit
            incentive_reward=incentive_reward
            percentage_credit=round( (incentive_reward) * (float(credit)/float(total_unit)) )
            persen_mediator_2=round(float(total_mediator)/float(total_unit))
            mediator_a=float(total_mediator)/float(total_unit)
            
            if mediator_a == 0 :
                incentive_reward_fix=percentage_credit;
                percentage_mediator=0
            else :
                incentive_reward_fix= percentage_credit-(round((percentage_credit) * (float(total_mediator)/float(total_unit))))
                percentage_mediator=round((percentage_credit) * (float(total_mediator)/float(total_unit)))
                
            total_incentive=incentive_penjualan+incentive_credit+incentive_reward_fix

            worksheet.write('A%s' % row, no , wbf['content_number'])                    
            worksheet.write('B%s' % row, branch_code , wbf['content'])
            worksheet.write('C%s' % row, branch_name , wbf['content'])
            worksheet.write('D%s' % row, nip_sales , wbf['content'])
            worksheet.write('E%s' % row, nama_sales , wbf['content'])
            worksheet.write('F%s' % row, jabatan , wbf['content'])
            worksheet.write('G%s' % row, cash , wbf['content_float'])
            worksheet.write('H%s' % row, credit , wbf['content_float']) 
            worksheet.write('I%s' % row, total_unit, wbf['content_float'])  
            worksheet.write('J%s' % row, str(persen_credit)+'%', wbf['content_percent'])  
            worksheet.write('K%s' % row, percentage_credit, wbf['content_float']) 
            worksheet.write('L%s' % row, total_mediator , wbf['content_float'])  
            worksheet.write('M%s' % row, str(persen_mediator)+'%', wbf['content_percent']) 
            worksheet.write('N%s' % row, percentage_mediator, wbf['content_float'])  
            worksheet.write('O%s' % row, total_absensi, wbf['content_float']) 
            worksheet.write('P%s' % row, '100%', wbf['content_percent']) 
            worksheet.write('Q%s' % row, incentive_penjualan, wbf['content_float']) 
            worksheet.write('R%s' % row, incentive_credit, wbf['content_float']) 
            worksheet.write('S%s' % row, incentive_reward_fix, wbf['content_float']) 
            worksheet.write('T%s' % row, total_incentive, wbf['content_float']) 
            worksheet.write('U%s' % row, '', wbf['content_float']) 
            worksheet.write('V%s' % row, ' ', wbf['content_float']) 
            no+=1
            row+=1
            
            grand_total_cash +=cash
            grand_total_credit +=credit
            grand_total_unit +=total_unit
            grand_total_persen_credit +=persen_credit
            grand_total_percentage_credit +=percentage_credit
            grand_total_mediator +=total_mediator
            grand_total_persen_mediator +=persen_mediator
            grand_total_percentage_mediator +=percentage_mediator
            grand_total_incentive_penjualan +=incentive_penjualan
            grand_total_incentive_credit +=incentive_credit
            grand_total_incentive_reward +=incentive_reward_fix
            grand_total_total_incentive +=total_incentive
                
        worksheet.autofilter('A7:V%s' % (row))  
#         worksheet.freeze_panes(6, 4)
        
        #TOTAL
        worksheet.merge_range('A%s:F%s' % (row,row), 'Total', wbf['total'])    
        worksheet.merge_range('O%s:P%s' % (row,row), '', wbf['total'])
        worksheet.merge_range('U%s:V%s' % (row,row), '', wbf['total'])
        worksheet.write('J%s' % (row), '', wbf['total'])
        worksheet.write('M%s' % (row), '', wbf['total'])
       
        formula_total_cash = '{=subtotal(9,G%s:G%s)}' % (row1, row-1) 
        formula_total_credit = '{=subtotal(9,H%s:H%s)}' % (row1, row-1) 
        formula_total_unit = '{=subtotal(9,I%s:I%s)}' % (row1, row-1) 
        formula_total_percentage_credit = '{=subtotal(9,K%s:K%s)}' % (row1, row-1) 
        formula_total_mediator = '{=subtotal(9,L%s:L%s)}' % (row1, row-1) 
        formula_total_percentage_mediator = '{=subtotal(9,N%s:N%s)}' % (row1, row-1) 
        formula_total_incentive_penjualan = '{=subtotal(9,Q%s:Q%s)}' % (row1, row-1) 
        formula_total_incentive_credit = '{=subtotal(9,R%s:R%s)}' % (row1, row-1) 
        formula_total_incentive_reward = '{=subtotal(9,S%s:S%s)}' % (row1, row-1) 
        formula_total_total_incentive = '{=subtotal(9,T%s:T%s)}' % (row1, row-1) 



        worksheet.write_formula(row-1,6,formula_total_cash, wbf['total_float'], grand_total_cash)                  
        worksheet.write_formula(row-1,7,formula_total_credit, wbf['total_float'], grand_total_credit )
        worksheet.write_formula(row-1,8,formula_total_unit, wbf['total_float'],grand_total_unit)
        worksheet.write_formula(row-1,10,formula_total_percentage_credit, wbf['total_float'],grand_total_percentage_credit)
        worksheet.write_formula(row-1,11,formula_total_mediator, wbf['total_float'], grand_total_mediator)
        worksheet.write_formula(row-1,13,formula_total_percentage_mediator, wbf['total_float'], grand_total_percentage_mediator)
        worksheet.write_formula(row-1,16,formula_total_incentive_penjualan, wbf['total_float'], grand_total_incentive_penjualan)
        worksheet.write_formula(row-1,17,formula_total_incentive_credit, wbf['total_float'], grand_total_incentive_credit)
        worksheet.write_formula(row-1,18,formula_total_incentive_reward, wbf['total_float'], grand_total_incentive_reward)
        worksheet.write_formula(row-1,19,formula_total_total_incentive, wbf['total_float'], grand_total_total_incentive)
        worksheet.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])  
                   
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()



       