from datetime import timedelta,datetime,date
from dateutil.relativedelta import relativedelta
from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning
import base64
import cStringIO
from cStringIO import StringIO
import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell
import os
import calendar

class InsentiveSalesReport(models.TransientModel):
    _inherit = "teds.insentive.salesman.report.wizard"

    def sales_counter_report(self):
        datas = self.generate_branch()
        bulan = int(self.bulan)
        tahun = int(self.tahun)

        start_date = date(tahun, bulan, 1)
        end_date = start_date + relativedelta(months=1) - relativedelta(days=1)
        
        results = {}
        result_details = []
        query = """
            SELECT b.name as branch_name
            , b.code as branch_code
            , emp.name_related as karyawan
            , dso.user_id
            , sum (CASE WHEN dso.finco_id IS NULL THEN 1 ELSE 0 END) as total_cash
            , sum (CASE WHEN dso.finco_id IS NOT NULL THEN 1 ELSE 0 END) total_credit
            , sum (CASE WHEN dso.finco_id IS NULL AND dso.partner_komisi_id IS NOT NULL THEN 1 ELSE 0 END) as total_mediator_cash
            , sum (CASE WHEN dso.finco_id IS NOT NULL AND dso.partner_komisi_id IS NOT NULL THEN 1 ELSE 0 END) as total_mediator_credit
            , sum (CASE WHEN dso.finco_id IS NULL AND ai.state != 'paid' THEN 1 ELSE 0 END) as total_ar_cash
            , sum (CASE WHEN dso.finco_id IS NOT NULL AND ai.state != 'paid' THEN 1 ELSE 0 END) as total_ar_credit
            FROM dealer_sale_order dso
            LEFT JOIN dealer_sale_order_line dsol ON dsol.dealer_sale_order_line_id = dso.id
            INNER JOIN wtc_branch b ON b.id = dso.branch_id
            INNER JOIN res_users r ON r.id = dso.user_id
            INNER JOIN resource_resource rr ON rr.user_id = r.id
            INNER JOIN hr_employee emp ON emp.resource_id = rr.id
            INNER JOIN hr_job job ON job.id = emp.job_id
            LEFT JOIN account_invoice ai ON ai.origin = dso.name AND number like '%s'
            WHERE dso.date_confirm BETWEEN '%s' AND '%s'
            AND dso.state IN ('progress','done')
            AND job.sales_force = 'sales_counter'
            GROUP BY dso.user_id,b.id,emp.id
        """ %('SL%',str(start_date),str(end_date))
        self._cr.execute(query)
        ress = self._cr.dictfetchall()

        for value in datas.values():
            branch_code = value.get('branch_code')
            branch_name = value.get('branch_name')
            if not results.get(branch_code):
                results[branch_code] = {
                    'branch_code':branch_code,
                    'branch_name':branch_name,
                    'jml_karyawan':0,
                    'total_unit_cash':0,
                    'total_unit_credit':0,
                    'total_insentif_cash':0,
                    'total_insentif_credit':0,
                    'total_insentif':0,
                }

        for res in ress:
            karyawan = res['karyawan'] 
            branch_code = res['branch_code']
            branch_name = res['branch_name']
            total_cash = res['total_cash']
            total_credit = res['total_credit']
            total_mediator_cash = res['total_mediator_cash']
            total_mediator_credit = res['total_mediator_credit']
            total_ar_cash = res['total_ar_cash']
            total_ar_credit = res['total_ar_credit']
            total_ar = total_ar_cash + total_ar_credit

            total_unit =  total_cash + total_credit 
            rp_listing = self.env['teds.listing.table.insentif'].search([
                ('name','=','SALES COUNTER'),
                ('total','=',total_unit)],limit=1)

            listing_cash = rp_listing.cash
            listing_credit = rp_listing.credit
            

            cash_nomed = total_cash - total_mediator_cash
            credit_nomed = total_credit - total_mediator_credit
            total_unit_mediator = total_mediator_cash + total_mediator_credit
            rupiah_unit_cash = cash_nomed * listing_cash 
            rupiah_unit_credit = credit_nomed * listing_credit
            rupiah_unit_ar_cash = total_ar_cash * listing_cash
            rupiah_unit_ar_credit = total_ar_credit * listing_credit
            rupiah_total_ar = rupiah_unit_ar_cash + rupiah_unit_ar_credit
            rupiah_total_unit = rupiah_unit_cash + rupiah_unit_credit 
            total_insentif = rupiah_unit_cash + rupiah_unit_credit - (rupiah_unit_ar_cash + rupiah_unit_ar_credit)

    
            if results.get(res.get('branch_code')):
                results[res['branch_code']]['jml_karyawan'] += 1
                results[res['branch_code']]['total_unit_cash'] += total_cash
                results[res['branch_code']]['total_unit_credit'] += total_credit
                results[res['branch_code']]['total_insentif_cash'] += rupiah_unit_cash
                results[res['branch_code']]['total_insentif_credit'] += rupiah_unit_credit

                results[res['branch_code']]['total_insentif'] += total_insentif
            
            result_details.append({
                'branch_code': branch_code,
                'branch_name':branch_name,
                'karyawan':karyawan,
                'total_cash':total_cash,
                'rupiah_unit_cash': rupiah_unit_cash,
                'total_credit':total_credit,
                'rupiah_unit_credit': rupiah_unit_credit,
                'total_unit':total_unit,
                'rupiah_total_unit':rupiah_total_unit,
                'total_mediator_cash':total_mediator_cash,
                'total_mediator_credit':total_mediator_credit,
                'total_unit_mediator':total_unit_mediator,
                'total_ar_cash':total_ar_cash,
                'total_ar_credit':total_ar_credit,
                'total_ar':total_ar,
                'rupiah_unit_ar_cash':rupiah_unit_ar_cash,
                'rupiah_unit_ar_credit':rupiah_unit_ar_credit,
                'rupiah_total_ar':rupiah_total_ar,
                'total_insentif':total_insentif,
            })

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)       
        workbook = self.add_workbook_format(workbook)
        wbf = self.wbf
        worksheet_summary = workbook.add_worksheet('Summary Insentif')
        worksheet_detail = workbook.add_worksheet('Detail Insentif')

        # Summary
        worksheet_summary.set_column('A1:A1', 23)
        worksheet_summary.set_column('B1:B1', 15)
        worksheet_summary.set_column('C1:C1', 16)
        worksheet_summary.set_column('D1:D1', 16)
        worksheet_summary.set_column('E1:E1', 16)
        worksheet_summary.set_column('F1:F1', 16)
        worksheet_summary.set_column('G1:G1', 16)
        worksheet_summary.set_column('H1:H1', 16)
        worksheet_summary.set_column('I1:I1', 16)
        worksheet_summary.set_column('J1:J1', 16)
        worksheet_summary.set_column('K1:K1', 16)
        
        # Detail
        worksheet_detail.set_column('A1:A1', 23)
        worksheet_detail.set_column('B1:B1', 20)
        worksheet_detail.set_column('C1:C1', 16)
        worksheet_detail.set_column('D1:D1', 16)
        worksheet_detail.set_column('E1:E1', 16)
        worksheet_detail.set_column('F1:F1', 16)
        worksheet_detail.set_column('G1:G1', 16)
        worksheet_detail.set_column('H1:H1', 16)
        worksheet_detail.set_column('I1:I1', 20)
        worksheet_detail.set_column('J1:J1', 20)
        worksheet_detail.set_column('K1:K1', 20)
        worksheet_detail.set_column('L1:L1', 16)
        worksheet_detail.set_column('M1:M1', 16)
        worksheet_detail.set_column('N1:N1', 16)
        worksheet_detail.set_column('O1:O1', 16)
        worksheet_detail.set_column('P1:P1', 16)
        worksheet_detail.set_column('Q1:Q1', 16)
        worksheet_detail.set_column('R1:R1', 16)

        
        bulan = int(self.bulan)
        tahun = int(self.tahun)
        nama_bln = calendar.month_name[bulan]

        filename = 'Report Hitung Insentif %s %s %s.xlsx' %(self.job_title,nama_bln,tahun)

        # Summary
        worksheet_summary.merge_range('A1:B1', 'Summary Insentif' , wbf['company'])
        worksheet_summary.merge_range('A2:B2', 'Job %s'%(self.job_title) , wbf['company'])
        worksheet_summary.merge_range('A3:B3', 'Periode %s %s'%(nama_bln,tahun) , wbf['company'])

        # Detail
        worksheet_detail.merge_range('A1:B1', 'Detail Insentif' , wbf['company'])
        worksheet_detail.merge_range('A2:B2', 'Job %s'%(self.job_title) , wbf['company'])
        worksheet_detail.merge_range('A3:B3', 'Periode %s %s'%(nama_bln,tahun) , wbf['company'])

        row_sm = 6
        row_dt = 6

        row_sm1 = row_sm
        row_dt1 = row_dt

        # Summary
        worksheet_summary.write('A5', 'Cabang' , wbf['header'])
        worksheet_summary.write('B5', 'Jml Karyawan' , wbf['header'])
        worksheet_summary.write('C5', 'Unit Cash' , wbf['header'])
        worksheet_summary.write('D5', 'Unit Credit' , wbf['header'])
        worksheet_summary.write('E5', 'Total Unit' , wbf['header'])
        worksheet_summary.write('F5', 'Inc Total Cash' , wbf['header'])
        worksheet_summary.write('G5', 'Inc Total Credit' , wbf['header'])
        worksheet_summary.write('H5', 'Total Inc' , wbf['header'])
        worksheet_summary.write('I5', 'Avarange / Orang' , wbf['header'])
        worksheet_summary.write('J5', 'Cost / Unit' , wbf['header'])
        worksheet_summary.write('K5', 'Produktivity' , wbf['header'])

        # Detail
        worksheet_detail.write('A5', 'Cabang' , wbf['header'])
        worksheet_detail.write('B5', 'Karyawan' , wbf['header'])
        worksheet_detail.write('C5', 'Total Cash' , wbf['header'])
        worksheet_detail.write('D5', 'Total Credit' , wbf['header'])
        worksheet_detail.write('E5', 'Total Unit' , wbf['header'])
        worksheet_detail.write('F5', 'Rupiah Cash' , wbf['header'])
        worksheet_detail.write('G5', 'Rupiah Credit' , wbf['header'])
        worksheet_detail.write('H5', 'Total Rupiah Unit' , wbf['header'])
        worksheet_detail.write('I5', 'Total Mediator Cash' , wbf['header'])
        worksheet_detail.write('J5', 'Total Mediator Credit' , wbf['header'])
        worksheet_detail.write('K5', 'Total Unit Mediator' , wbf['header'])
        worksheet_detail.write('L5', 'Total AR Cash' , wbf['header'])
        worksheet_detail.write('M5', 'Total AR Credit' , wbf['header'])
        worksheet_detail.write('N5', 'Total AR' , wbf['header'])
        worksheet_detail.write('O5', 'Rupiah AR Cash' , wbf['header'])
        worksheet_detail.write('P5', 'Rupiah AR Credit' , wbf['header'])
        worksheet_detail.write('Q5', 'Total Rupiah  AR' , wbf['header'])
        worksheet_detail.write('R5', 'Total Insentif' , wbf['header'])

        sum_jml_karyawan = 0
        sum_total_unit_cash = 0
        sum_total_unit_credit = 0
        sum_total_unit_sm = 0
        sum_total_insentif_cash = 0
        sum_total_insentif_credit = 0
        sum_total_insentif_sm = 0
        sum_avg_org = 0
        sum_cost_unit = 0
        sum_productivity = 0

        for result in results.values():
            avg_org = 0
            cost_unit = 0
            productivity = 0
            
            total_unit_sm = result['total_unit_cash'] + result['total_unit_credit']

            total_insentif_sm = result['total_insentif_cash'] + result['total_insentif_credit']
            if result['jml_karyawan'] > 0 :
                avg_org = total_insentif_sm / result['jml_karyawan']
                productivity = total_unit_sm / result['jml_karyawan']
            if total_unit_sm > 0: 
                cost_unit = total_insentif_sm / total_unit_sm

            worksheet_summary.write('A%s' % row_sm, result['branch_name'] , wbf['content'])
            worksheet_summary.write('B%s' % row_sm, result['jml_karyawan'] , wbf['content_right'])
            worksheet_summary.write('C%s' % row_sm, result['total_unit_cash'] , wbf['content_right'])
            worksheet_summary.write('D%s' % row_sm, result['total_unit_credit'] , wbf['content_right'])
            worksheet_summary.write('E%s' % row_sm, total_unit_sm , wbf['content_right'])
            worksheet_summary.write('F%s' % row_sm, result['total_insentif_cash'] , wbf['content_float'])
            worksheet_summary.write('G%s' % row_sm, result['total_insentif_credit'] , wbf['content_float'])
            worksheet_summary.write('H%s' % row_sm, total_insentif_sm , wbf['content_float'])
            worksheet_summary.write('I%s' % row_sm, avg_org , wbf['content_float'])
            worksheet_summary.write('J%s' % row_sm, cost_unit , wbf['content_float'])
            worksheet_summary.write('K%s' % row_sm, productivity , wbf['content_right'])

            sum_jml_karyawan += result['jml_karyawan']
            sum_total_unit_cash += result['total_unit_cash']
            sum_total_unit_credit += result['total_unit_credit']
            sum_total_unit_sm += total_unit_sm
            sum_total_insentif_cash += result['total_insentif_cash']
            sum_total_insentif_credit += result['total_insentif_credit']
            sum_total_insentif_sm += total_insentif_sm
            sum_avg_org += avg_org
            sum_cost_unit += cost_unit
            sum_productivity += productivity

            row_sm += 1

        # Detail
        sum_total_cash = 0
        sum_total_credit = 0
        sum_total_uni = 0
        sum_rupiah_unit_cash = 0
        sum_rupiah_unit_credit = 0
        sum_rupiah_total_unit = 0
        sum_total_mediator_cash = 0
        sum_total_mediator_credit = 0
        sum_total_unit_mediator = 0
        sum_total_ar_cash = 0
        sum_total_ar_credit = 0
        sum_total_ar = 0
        sum_rupiah_unit_ar_cash = 0
        sum_rupiah_unit_ar_credit = 0
        sum_rupiah_total_ar = 0
        sum_total_insentif = 0

        for detail in result_details:
            worksheet_detail.write('A%s' % row_dt, detail['branch_name'] , wbf['content'])
            worksheet_detail.write('B%s' % row_dt, detail['karyawan'] , wbf['content'])
            worksheet_detail.write('C%s' % row_dt, detail['total_cash'] , wbf['content_right'])
            worksheet_detail.write('D%s' % row_dt, detail['total_credit'] , wbf['content_right'])
            worksheet_detail.write('E%s' % row_dt, detail['total_unit'] , wbf['content_right'])
            worksheet_detail.write('F%s' % row_dt, detail['rupiah_unit_cash'] , wbf['content_float'])
            worksheet_detail.write('G%s' % row_dt, detail['rupiah_unit_credit'] , wbf['content_float'])
            worksheet_detail.write('H%s' % row_dt, detail['rupiah_total_unit'] , wbf['content_float'])
            worksheet_detail.write('I%s' % row_dt, detail['total_mediator_cash'] , wbf['content_right'])
            worksheet_detail.write('J%s' % row_dt, detail['total_mediator_credit'] , wbf['content_right'])
            worksheet_detail.write('K%s' % row_dt, detail['total_unit_mediator'] , wbf['content_right'])
            worksheet_detail.write('L%s' % row_dt, detail['total_ar_cash'] , wbf['content_right'])
            worksheet_detail.write('M%s' % row_dt, detail['total_ar_credit'] , wbf['content_right'])
            worksheet_detail.write('N%s' % row_dt, detail['total_ar'] , wbf['content_right'])
            worksheet_detail.write('O%s' % row_dt, detail['rupiah_unit_ar_cash'] , wbf['content_float'])
            worksheet_detail.write('P%s' % row_dt, detail['rupiah_unit_ar_credit'] , wbf['content_float'])
            worksheet_detail.write('Q%s' % row_dt, detail['rupiah_total_ar'] , wbf['content_float'])
            worksheet_detail.write('R%s' % row_dt, detail['total_insentif'] , wbf['content_float'])

            sum_total_cash += detail['total_cash']
            sum_total_credit += detail['total_credit']
            sum_total_uni += detail['total_unit']
            sum_rupiah_unit_cash += detail['rupiah_unit_cash']
            sum_rupiah_unit_credit += detail['rupiah_unit_credit']
            sum_rupiah_total_unit += detail['rupiah_total_unit']
            sum_total_mediator_cash += detail['total_mediator_cash']
            sum_total_mediator_credit += detail['rupiah_unit_credit']
            sum_total_unit_mediator += detail['total_unit_mediator']
            sum_total_ar_cash += detail['total_ar_cash']
            sum_total_ar_credit += detail['total_ar_credit']
            sum_total_ar += detail['total_ar']
            sum_rupiah_unit_ar_cash += detail['rupiah_unit_ar_cash']
            sum_rupiah_unit_ar_credit += detail['rupiah_unit_ar_credit']
            sum_rupiah_total_ar += detail['rupiah_total_ar']
            sum_total_insentif += detail['total_insentif']

            row_dt += 1

        #Formula Summary
        formula_jml_karyawan_sm = '{=subtotal(9,B%s:B%s)}' % (row_sm1, row_sm-1)
        formula_total_unit_cash_sm = '{=subtotal(9,C%s:C%s)}' % (row_sm1, row_sm-1)
        formula_total_unit_credit_sm = '{=subtotal(9,D%s:D%s)}' % (row_sm1, row_sm-1)
        formula_total_unti_sm = '{=subtotal(9,E%s:E%s)}' % (row_sm1, row_sm-1)
        formula_total_insentif_cash_sm = '{=subtotal(9,F%s:F%s)}' % (row_sm1, row_sm-1)
        formula_total_insentif_credit_sm = '{=subtotal(9,G%s:G%s)}' % (row_sm1, row_sm-1)
        formula_total_insentif_sm = '{=subtotal(9,H%s:H%s)}' % (row_sm1, row_sm-1)
        formula_avg_org_sm = '{=subtotal(9,I%s:I%s)}' % (row_sm1, row_sm-1)
        formula_cost_unit_sm = '{=subtotal(9,J%s:J%s)}' % (row_sm1, row_sm-1)
        formula_productivity_sm = '{=subtotal(9,K%s:K%s)}' % (row_sm1, row_sm-1)

        # Formula Detail
        formula_total_cash = '{=subtotal(9,C%s:C%s)}' % (row_dt1, row_dt-1)
        formula_total_credit = '{=subtotal(9,D%s:D%s)}' % (row_dt1, row_dt-1)
        formula_total_unit = '{=subtotal(9,E%s:E%s)}' % (row_dt1, row_dt-1)
        formula_rupiah_unit_cash = '{=subtotal(9,F%s:F%s)}' % (row_dt1, row_dt-1)
        formula_rupiah_unit_credit = '{=subtotal(9,G%s:G%s)}' % (row_dt1, row_dt-1)
        formula_rupiah_total_unit = '{=subtotal(9,H%s:H%s)}' % (row_dt1, row_dt-1)
        formula_total_mediator_cash = '{=subtotal(9,I%s:I%s)}' % (row_dt1, row_dt-1)
        formula_total_mediator_credit = '{=subtotal(9,J%s:J%s)}' % (row_dt1, row_dt-1)
        formula_total_unit_mediator = '{=subtotal(9,K%s:K%s)}' % (row_dt1, row_dt-1)
        formula_total_ar_cash = '{=subtotal(9,L%s:L%s)}' % (row_dt1, row_dt-1)
        formula_total_ar_credit = '{=subtotal(9,M%s:M%s)}' % (row_dt1, row_dt-1)
        formula_total_ar = '{=subtotal(9,N%s:N%s)}' % (row_dt1, row_dt-1)
        formula_rupiah_unit_ar_cash = '{=subtotal(9,O%s:O%s)}' % (row_dt1, row_dt-1)
        formula_rupiah_unit_ar_credit = '{=subtotal(9,P%s:P%s)}' % (row_dt1, row_dt-1)
        formula_rupiah_total_ar = '{=subtotal(9,Q%s:Q%s)}' % (row_dt1, row_dt-1)
        formula_total_insentif = '{=subtotal(9,R%s:R%s)}' % (row_dt1, row_dt-1)


        #TOTAL
        worksheet_summary.write('A%s' % (row_sm), 'Total', wbf['total'])

        worksheet_summary.write_formula(row_sm-1,1,formula_jml_karyawan_sm, wbf['total_number_float'], sum_jml_karyawan)
        worksheet_summary.write_formula(row_sm-1,2,formula_total_unit_cash_sm, wbf['total_number_float'], sum_total_unit_cash)
        worksheet_summary.write_formula(row_sm-1,3,formula_total_unit_credit_sm, wbf['total_number_float'], sum_total_unit_credit)
        worksheet_summary.write_formula(row_sm-1,4,formula_total_unti_sm, wbf['total_number_float'], sum_total_unit_sm)
        worksheet_summary.write_formula(row_sm-1,5,formula_total_insentif_cash_sm, wbf['total_number_float'], sum_total_insentif_cash)
        worksheet_summary.write_formula(row_sm-1,6,formula_total_insentif_credit_sm, wbf['total_number_float'], sum_total_insentif_credit)
        worksheet_summary.write_formula(row_sm-1,7,formula_total_insentif_sm, wbf['total_number_float'], sum_total_insentif_sm)
        worksheet_summary.write_formula(row_sm-1,8,formula_avg_org_sm, wbf['total_number_float'], sum_avg_org)
        worksheet_summary.write_formula(row_sm-1,9,formula_cost_unit_sm, wbf['total_number_float'], sum_cost_unit)
        worksheet_summary.write_formula(row_sm-1,10,formula_productivity_sm, wbf['total_number_float'], sum_productivity)
        
        worksheet_detail.merge_range('A%s:B%s' % (row_dt,row_dt), 'Total', wbf['total'])

        worksheet_detail.write_formula(row_dt-1,2,formula_total_cash, wbf['total_number_float'], sum_total_cash)
        worksheet_detail.write_formula(row_dt-1,3,formula_total_credit, wbf['total_number_float'], sum_total_credit)
        worksheet_detail.write_formula(row_dt-1,4,formula_total_unit, wbf['total_number_float'], sum_total_uni)
        worksheet_detail.write_formula(row_dt-1,5,formula_rupiah_unit_cash, wbf['total_number_float'], sum_rupiah_unit_cash)
        worksheet_detail.write_formula(row_dt-1,6,formula_rupiah_unit_credit, wbf['total_number_float'], sum_rupiah_unit_credit)
        worksheet_detail.write_formula(row_dt-1,7,formula_rupiah_total_unit, wbf['total_number_float'], sum_rupiah_total_unit)
        worksheet_detail.write_formula(row_dt-1,8,formula_total_mediator_cash, wbf['total_number_float'], sum_total_mediator_cash)
        worksheet_detail.write_formula(row_dt-1,9,formula_total_mediator_credit, wbf['total_number_float'], sum_total_mediator_credit)
        worksheet_detail.write_formula(row_dt-1,10,formula_total_unit_mediator, wbf['total_number_float'], sum_total_unit_mediator)
        worksheet_detail.write_formula(row_dt-1,11,formula_total_ar_cash, wbf['total_number_float'], sum_total_ar_cash)
        worksheet_detail.write_formula(row_dt-1,12,formula_total_ar_credit, wbf['total_number_float'], sum_total_ar_credit)
        worksheet_detail.write_formula(row_dt-1,13,formula_total_ar, wbf['total_number_float'], sum_total_ar)
        worksheet_detail.write_formula(row_dt-1,14,formula_rupiah_unit_ar_cash, wbf['total_number_float'], sum_rupiah_unit_ar_cash)
        worksheet_detail.write_formula(row_dt-1,15,formula_rupiah_unit_ar_credit, wbf['total_number_float'], sum_rupiah_unit_ar_credit)
        worksheet_detail.write_formula(row_dt-1,16,formula_rupiah_total_ar, wbf['total_number_float'], sum_rupiah_total_ar)
        worksheet_detail.write_formula(row_dt-1,17,formula_total_insentif, wbf['total_number_float'], sum_total_insentif)
        
        


        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write({'state_x':'get', 'data_x':out, 'name': filename})
        fp.close()

        res = self.env.ref('teds_insentif_salesman.view_teds_insentive_salesman_report_wizard', False)

        form_id = res and res.id or False

        return {
            'name': ('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.insentive.salesman.report.wizard',
            'res_id': self.ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }


