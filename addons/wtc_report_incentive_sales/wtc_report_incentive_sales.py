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

class wtc_report_incentive_sales(osv.osv_memory):
   
    _name = "wtc.report.incentive.sale.wizard"
    _description = "Report Incentive Sales"

    wbf = {}
    incentive={}
    max_qty={}
    
    def _get_incentive(self,cr,uid,ids,sales_type,cluster,qty_cash,qty_credit, qty_reward,nip_sales,context=None):
        amount_cash=0.0
        amount_credit=0.0
        amount_reward=0.0
        check_inv=[]

        if not self.max_qty.get(sales_type+"|"+cluster,False):
            query_max= """
                        SELECT MAX(listing_line.qty)
                        FROM wtc_listing_incentive_sales as listing
                        LEFT JOIN wtc_listing_incentive_sales_line as listing_line ON listing.id=listing_line.listing_incentive_sales_id
                        WHERE listing.sales_force='%s' AND listing.cluster='%s'
                       """ % (sales_type, cluster)
            cr.execute (query_max)
            res_max = cr.fetchone()
            if len(res_max) > 0:
                self.max_qty[sales_type+"|"+cluster] = res_max[0]
        qty_max = self.max_qty.get(sales_type+"|"+cluster, 0)
        
        
        
        if qty_reward > qty_max :
            qty_reward=qty_max
            qty_cash=qty_max
        else :
            qty_reward=int(qty_reward)
            qty_cash=int(qty_cash)
         
        if qty_credit > qty_max :
            qty_credit=qty_max
        else :
            qty_credit=int(qty_credit)
    
        
        #check if already exists
        
        if not self.incentive.get(sales_type+"|"+cluster+"|"+nip_sales,False):
            check_inv = [qty_cash, qty_credit, qty_reward]
            #print ">>>>>>>>>>>>>>>>>check_inv1",check_inv
            check_inv = list(set(check_inv))
            #print ">>>>>>>>>>>>>>>>>check_inv2",check_inv
        else :
            if not self.incentive[sales_type+"|"+cluster+"|"+nip_sales].get(qty_cash,False):
                if qty_cash not in check_inv :
                    check_inv += [qty_cash]
            else :
                amount_cash = self.incentive[sales_type+"|"+cluster+"|"+nip_sales][qty_cash][0]
            if not self.incentive[sales_type+"|"+cluster+"|"+nip_sales].get(qty_credit,False):
                if qty_credit not in check_inv :
                    check_inv += [qty_credit]
            else :
                amount_credit = self.incentive[sales_type+"|"+cluster+"|"+nip_sales][qty_credit][0]
                
            if not self.incentive[sales_type+"|"+cluster+"|"+nip_sales].get(qty_reward,False):
                if qty_reward not in check_inv :
                    check_inv += [qty_reward]
            else :
                amount_reward = self.incentive[sales_type+"|"+cluster+"|"+nip_sales][qty_reward][0]

        if len(check_inv) > 0 :
            query_incentive="""
                            SELECT 
                            a.sales_force,
                            a.cluster,
                            b.qty,
                            b.cash,
                            b.credit,
                            b.reward
                            from wtc_listing_incentive_sales as a
                            LEFT JOIN wtc_listing_incentive_sales_line as b
                            ON a.id=b.listing_incentive_sales_id
                            where b.qty in %s AND a.cluster = '%s' and a.sales_force = '%s'
                        """ % (str(tuple(check_inv)).replace(',)', ')'),cluster,sales_type)
            cr.execute (query_incentive)
            ress = cr.fetchall()
            
          
            
            if len(check_inv) != len(ress) :
                raise osv.except_osv(('Warning !'), ("Master Incentive untuk " + sales_type + " di cluster " + cluster + " untuk quantity " + str(tuple(check_inv)).replace(',)', ')') + " ada yang belum di setting."))             
            for res in  ress:
                if not self.incentive.get(str(res[0])+"|"+str(res[1]),False):
                    self.incentive[str(res[0])+"|"+str(res[1])] = {}
                self.incentive[str(res[0])+"|"+str(res[1])][res[2]]=[res[3],res[4],res[5]]
    
              
                
                
        if amount_cash==0.0 and qty_cash > 0 :
            amount_cash=self.incentive[sales_type+"|"+cluster][qty_cash][0]
        if amount_credit==0.0 and qty_credit > 0:
            amount_credit=self.incentive[sales_type+"|"+cluster][qty_credit][1]
        if amount_reward==0.0 and qty_reward > 0:
            amount_reward=self.incentive[sales_type+"|"+cluster][qty_reward][2]
        return [amount_cash,amount_credit,amount_reward]
        

        

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
        'start_date': fields.date('Start Date',required=True),
        'end_date': fields.date('End Date',required=True), 
        'branch_ids': fields.many2many('wtc.branch', 'wtc_report_incentive_sales_rel', 'wtc_report_incentive_sales_id',
            'branch_id', 'Branches', copy=False),
        'sales_force' : fields.selection([('salesman','Salesman'),('sales_counter','Sales Counter'),('sales_partner','Sales Partner')
                        ,('sales_koordinator','Sales Koordinator')], string='Sales Force',required=True),
    }

    _defaults = {
        'state_x': lambda *a: 'choose',
    }
    
    def add_workbook_format(self, cr, uid, workbook):      
        self.wbf['header'] = workbook.add_format({'bold': 1,'align': 'center','bg_color': '#FFFFDB','font_color': '#000000'})
        self.wbf['header'].set_border()
        self.wbf['header'].set_align('vcenter')

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
        if data['sales_force'] == 'sales_koordinator' :
            self._print_excel_report_sales_koordinator(cr, uid, ids, data, context=context)
        elif data['sales_force'] == 'sales_counter' :
            self._print_excel_report_sales_counter(cr, uid, ids, data, context=context)
        elif data['sales_force'] == 'sales_partner' :
            self._print_excel_report_sales_partner(cr, uid, ids, data, context=context)
        elif data['sales_force'] == 'salesman' :
            self._print_excel_report_salesman(cr, uid, ids, data, context=context)

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_incentive_sales', 'view_report_incentive_sales_wizard')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.report.incentive.sale.wizard',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }

    def _print_excel_report_sales_koordinator(self, cr, uid, ids, data, context=None): 
        branch_ids = data['branch_ids'] 
        sales_force = data['sales_force']  
        start_date = data['start_date']
        end_date = data['end_date']
        tz = '7 hours'
        query_where = " "
    
        if branch_ids :
            query_where += " AND branch.id in %s" % str(tuple(branch_ids)).replace(',)', ')')
        
        sales_type="sales_koordinator"       
        query_not_in_date=""" AND dso.date_order NOT  BETWEEN '%s' AND '%s' """ %(start_date,end_date)                                    
        query = """
                SELECT
                COALESCE(job.id,0) as job_id, 
                COALESCE(branch.code,'') as branch_code, 
                COALESCE(branch.name,'') as branch_name,
                COALESCE(hr_sales.nip,'') as sales_nip, 
                COALESCE(sales.name,'') as sales_name, 
                COALESCE(job.name,'') as job_name,
                COALESCE( SUM (CASE   WHEN dso.finco_id IS NULL  and dso.state = 'cancelled' """+query_not_in_date+"""  then  -1 *  dsol.product_qty    WHEN dso.finco_id IS NULL then dsol.product_qty  END ),0)  as total_cash,
                COALESCE(SUM (CASE   WHEN dso.finco_id IS NOT NULL  and dso.state = 'cancelled'  """+query_not_in_date+""" then  -1 *  dsol.product_qty    WHEN dso.finco_id IS NOT NULL then dsol.product_qty  END ),0)  as total_credit,
                COALESCE(SUM(case when dso.state = 'cancelled' """+query_not_in_date+""" then -1 *  dsol.product_qty  else  dsol.product_qty  end),0) as total_unit,
                COALESCE(SUM (CASE   WHEN dso.partner_komisi_id IS NOT NULL  and dso.state = 'cancelled'  """+query_not_in_date+""" then  -1 *  dsol.product_qty    WHEN dso.partner_komisi_id IS NOT NULL then dsol.product_qty  END ),0)  as total_mediator,
                tot_salesman.total_bawahan as total_bawahan,
                ROUND( ( COUNT(dsol.id) / tot_salesman.total_bawahan:: FLOAT) ) as produktivitas,
                ' ' as cluster
                FROM dealer_sale_order as dso
                LEFT JOIN dealer_sale_order_line as dsol
                ON  dsol.dealer_sale_order_line_id = dso.id 
                LEFT JOIN res_users as users
                ON users.id=dso.sales_koordinator_id
                LEFT JOIN resource_resource sales 
                ON users.id = sales.user_id 
                LEFT JOIN hr_employee hr_sales 
                ON sales.id = hr_sales.resource_id 
                LEFT JOIN hr_job job
                ON hr_sales.job_id = job.id 
                LEFT JOIN wtc_branch as branch
                ON branch.id=dso.branch_id
                LEFT JOIN (
                    SELECT 
                    sales_koordinator_id,
                    count(user_id) as total_bawahan
                    FROM (
                    SELECT DISTINCT 
                    sales_koordinator_id,user_id
                    FROM 
                    dealer_sale_order as dso
                    LEFT JOIN wtc_branch as branch
                    ON branch.id=dso.branch_id
                    where 1=1  and dso.state in ('progress', 'done') and dso.date_order between '%s' and '%s' 
                    AND sales_koordinator_id IS NOT NULL %s
                    ) as salesman
                GROUP BY salesman.sales_koordinator_id ) as tot_salesman
                ON tot_salesman.sales_koordinator_id=dso.sales_koordinator_id
                where 1=1 AND job.sales_force='sales_koordinator' %s
                and dso.state in ('progress', 'done') and dso.date_order between '%s' and '%s' 
                GROUP BY hr_sales.nip,sales.name,job.name,branch.code,branch.name,job.id,tot_salesman.total_bawahan
                order by sales.name
            """ % (start_date,end_date,query_where,query_where,start_date,end_date)
                   

        cr.execute (query)
        ress = cr.fetchall() 
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Incentive Sales')
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
        
        filename = 'Report Incentive Sales '+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report Incentive Sales' , wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])
        row=3
        rowsaldo = row
        row+=1
        
        worksheet.merge_range('A%s:A%s' % (row+1,row+2), 'No' , wbf['header'])
        worksheet.merge_range('B%s:B%s' % (row+1,row+2), 'Branch Code' , wbf['header'])
        worksheet.merge_range('C%s:C%s' % (row+1,row+2), 'Branch Name' , wbf['header'])
        worksheet.merge_range('D%s:D%s' % (row+1,row+2), 'NIP' , wbf['header'])
        worksheet.merge_range('E%s:E%s' % (row+1,row+2), 'Nama' , wbf['header'])
        worksheet.merge_range('F%s:F%s' % (row+1,row+2), 'Jabatan' , wbf['header'])
        worksheet.merge_range('G%s:G%s' % (row+1,row+2), 'Cash' , wbf['header'])
        worksheet.merge_range('H%s:H%s' % (row+1,row+2), 'Credit' , wbf['header'])
        worksheet.merge_range('I%s:I%s' % (row+1,row+2), 'Total Unit' , wbf['header'])
        worksheet.merge_range('J%s:J%s' % (row+1,row+2), 'Man Power' , wbf['header'])
        worksheet.merge_range('K%s:K%s' % (row+1,row+2), 'Produktivitas' , wbf['header'])
        worksheet.merge_range('L%s:L%s' % (row+1,row+2), 'incentive \n Cash & Credit' , wbf['header'])
        worksheet.merge_range('M%s:M%s' % (row+1,row+2), 'Unit Credit' , wbf['header'])
        worksheet.merge_range('N%s:N%s' % (row+1,row+2), 'Reward' , wbf['header'])
        worksheet.merge_range('O%s:O%s' % (row+1,row+2), 'Total \n Incentive' , wbf['header'])

        row+=3               
        no = 1     
        row1 = row
        
        grand_total_cash=0
        grand_total_credit=0
        grand_total_sales=0
        grand_total_incentive_penjualan=0
        grand_total_incentive_credit=0
        grand_total_incentive_reward=0
        grand_total_incentive=0

        
        for res in ress:
            job_id=res[0]
            branch_code = str(res[1].encode('ascii','ignore').decode('ascii')) if res[1] != None else ''
            branch_name = str(res[2].encode('ascii','ignore').decode('ascii')) if res[2] != None else ''
            nip_sales = str(res[3].encode('ascii','ignore').decode('ascii')) if res[3] != None else ''
            nama_sales = str(res[4].encode('ascii','ignore').decode('ascii')) if res[4] != None else ''
            jabatan = str(res[5].encode('ascii','ignore').decode('ascii')) if res[5] != None else ''
            cash = res[6]
            credit =res[7]
            total_unit = res[8]
            persen_credit=round(float(credit)/float(total_unit)*100)
            mediator = res[9]
            persen_mediator=round(float(mediator)/float(total_unit)*100)
            jumlah_bawahan = res[10]
            produktivitas = res[11]
            cluster = res[12]
             
            [incentive_cash, incentive_credit, incentive_reward]=self._get_incentive(cr,uid,ids,sales_type,cluster,total_unit,credit,total_unit,nip_sales,context) 

            incentive_penjualan=incentive_cash
            incentive_credit=incentive_credit
            incentive_reward=incentive_reward
            
        
            if jumlah_bawahan >= 10 and produktivitas >=8 :
                total_reward=incentive_reward*0.5+incentive_reward*0.5
            else :
                total_reward=incentive_reward*0.5
             
            total_incentive=incentive_penjualan+incentive_credit+total_reward
                 
            worksheet.write('A%s' % row, no , wbf['content_number'])                    
            worksheet.write('B%s' % row, branch_code , wbf['content'])
            worksheet.write('C%s' % row, branch_name , wbf['content'])
            worksheet.write('D%s' % row, nip_sales , wbf['content'])
            worksheet.write('E%s' % row, nama_sales , wbf['content'])
            worksheet.write('F%s' % row, jabatan , wbf['content'])
            worksheet.write('G%s' % row, cash , wbf['content_float'])
            worksheet.write('H%s' % row, credit , wbf['content_float']) 
            worksheet.write('I%s' % row, total_unit, wbf['content_float'])  
            worksheet.write('J%s' % row, jumlah_bawahan , wbf['content_float'])
            worksheet.write('K%s' % row, produktivitas , wbf['content_float'])
            worksheet.write('L%s' % row, incentive_penjualan , wbf['content_float'])
            worksheet.write('M%s' % row, incentive_credit , wbf['content_float'])
            worksheet.write('N%s' % row, total_reward , wbf['content_float'])
            worksheet.write('O%s' % row, total_incentive , wbf['content_float'])
            no+=1
            row+=1
            

        
            grand_total_cash +=cash
            grand_total_credit +=credit
            grand_total_sales +=total_unit
            grand_total_incentive_penjualan +=incentive_penjualan
            grand_total_incentive_credit +=incentive_credit
            grand_total_incentive_reward +=total_reward
            grand_total_incentive +=total_incentive
#                 grand_total_man_power +=floatjumlah_bawahan
#                 grand_total_produktivitas +=produktivitas
            
        
        worksheet.autofilter('A5:O%s' % (row))  
        worksheet.freeze_panes(6, 4)
        
        #TOTAL
        worksheet.merge_range('A%s:F%s' % (row,row), 'Total', wbf['total'])    
        worksheet.merge_range('J%s:K%s' % (row,row), '', wbf['total'])
       
        
        formula_total_cash = '{=subtotal(9,G%s:G%s)}' % (row1, row-1) 
        formula_total_credit = '{=subtotal(9,H%s:H%s)}' % (row1, row-1) 
        formula_total_sales = '{=subtotal(9,I%s:I%s)}' % (row1, row-1) 
        formula_total_man_power = '{=subtotal(9,J%s:J%s)}' % (row1, row-1) 
        formula_total_produktivitas = '{=subtotal(9,K%s:K%s)}' % (row1, row-1) 
        formula_total_incentive_penjualan = '{=subtotal(9,L%s:L%s)}' % (row1, row-1) 
        formula_total_incentive_credit = '{=subtotal(9,M%s:M%s)}' % (row1, row-1) 
        formula_total_incentive_reward = '{=subtotal(9,N%s:N%s)}' % (row1, row-1) 
        formula_total_incentive = '{=subtotal(9,O%s:O%s)}' % (row1, row-1) 



        worksheet.write_formula(row-1,6,formula_total_cash, wbf['total_float'], grand_total_cash)                  
        worksheet.write_formula(row-1,7,formula_total_credit, wbf['total_float'], grand_total_credit )
        worksheet.write_formula(row-1,8,formula_total_sales, wbf['total_float'],grand_total_sales)
#         worksheet.write_formula(row-1,9,formula_total_man_power, wbf['total_float'],grand_total_man_power)
#         worksheet.write_formula(row-1,10,formula_total_produktivitas, wbf['total_float'],grand_total_produktivitas)
        worksheet.write_formula(row-1,11,formula_total_incentive_penjualan, wbf['total_float'], grand_total_incentive_penjualan)
        worksheet.write_formula(row-1,12,formula_total_incentive_credit, wbf['total_float'], grand_total_incentive_credit) 
        worksheet.write_formula(row-1,13,formula_total_incentive_reward, wbf['total_float'], grand_total_incentive_reward)
        worksheet.write_formula(row-1,14,formula_total_incentive, wbf['total_float'], grand_total_incentive)
        worksheet.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])  
                   
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

wtc_report_incentive_sales()

