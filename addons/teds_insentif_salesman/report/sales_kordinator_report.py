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

    def sales_kordinator_report(self):
        datas = self.generate_branch()
        bulan = int(self.bulan)
        tahun = int(self.tahun)

        start_date = date(tahun, bulan, 1)
        end_date = start_date + relativedelta(months=1) - relativedelta(days=1)
        
        results = {}
        result_details = []

        koordinator_ids = self.env['hr.employee'].sudo().search([('job_id.sales_force','=','sales_koordinator')])
        lst_kordinator = []
        for koordinator in koordinator_ids:
            if koordinator.user_id.id:
                lst_kordinator.append(koordinator.user_id.id)

        lst_kordinator = str(tuple(lst_kordinator)).replace(',)', ')')
        query_1 = """
            SELECT  b.name as branch_name
            , b.code as branch_code
            , b.id as branch_id
            , emp.name_related as karyawan
            , dso.user_id as user_id
            , sum (CASE WHEN dso.finco_id IS NULL THEN 1 ELSE 0 END) as total_cash
            , sum (CASE WHEN dso.finco_id IS NOT NULL THEN 1 ELSE 0 END) total_credit
            FROM dealer_sale_order dso
            LEFT JOIN dealer_sale_order_line dsol ON dsol.dealer_sale_order_line_id = dso.id
            INNER JOIN wtc_branch b ON b.id = dso.branch_id
            INNER JOIN res_users r ON r.id = dso.user_id
            INNER JOIN resource_resource rr ON rr.user_id = r.id
            INNER JOIN hr_employee emp ON emp.resource_id = rr.id
            INNER JOIN hr_job job ON job.id = emp.job_id
            WHERE dso.date_confirm BETWEEN '%s' AND '%s'
            AND dso.state IN ('progress','done')
            AND (dso.user_id in %s)
            GROUP BY dso.user_id,b.id,emp.id
            ORDER BY karyawan ASC
        """ %(str(start_date),str(end_date),lst_kordinator)
        self._cr.execute(query_1)
        ress1 = self._cr.dictfetchall()
        
        query_2 = """
            SELECT  b.name as branch_name
            , b.code as branch_code
            , b.id as branch_id
            , emp.name_related as karyawan
            , dso.sales_koordinator_id as user_id
            , sum (CASE WHEN dso.finco_id IS NULL THEN 1 ELSE 0 END) as total_cash
            , sum (CASE WHEN dso.finco_id IS NOT NULL THEN 1 ELSE 0 END) total_credit
            FROM dealer_sale_order dso
            LEFT JOIN dealer_sale_order_line dsol ON dsol.dealer_sale_order_line_id = dso.id
            INNER JOIN wtc_branch b ON b.id = dso.branch_id
            INNER JOIN res_users r ON r.id = dso.user_id
            INNER JOIN resource_resource rr ON rr.user_id = r.id
            INNER JOIN hr_employee emp ON emp.resource_id = rr.id
            INNER JOIN hr_job job ON job.id = emp.job_id
            WHERE dso.date_confirm BETWEEN '%s' AND '%s'
            AND dso.state IN ('progress','done')
            AND (dso.sales_koordinator_id in %s AND dso.user_id not in %s)
            GROUP BY dso.sales_koordinator_id,b.id,emp.id
            ORDER BY karyawan ASC
        """ %(str(start_date),str(end_date),lst_kordinator,lst_kordinator)
        self._cr.execute(query_2)
        ress2 = self._cr.dictfetchall()

        ress = {}

        for res1 in ress1:
            if not ress.get(res1['user_id']):
                ress[res1['user_id']] = {
                    'user_id':res1['user_id'],
                    'branch_code':res1['branch_code'],
                    'branch_name':res1['branch_name'],
                    'branch_id':res1['branch_id'],
                    'karyawan':res1['karyawan'],
                    'total_cash':res1['total_cash'],
                    'total_credit':res1['total_credit'],
                }
            else:
                ress[res1['user_id']]['total_cash'] += res1['total_cash']
                ress[res1['user_id']]['total_credit'] += res1['total_credit']

        for res2 in ress2:
            if not ress.get(res2['user_id']):
                ress[res2['user_id']] = {
                    'user_id':res2['user_id'],
                    'branch_code':res2['branch_code'],
                    'branch_name':res2['branch_name'],
                    'branch_id':res1['branch_id'],
                    'karyawan':res2['karyawan'],
                    'total_cash':res2['total_cash'],
                    'total_credit':res2['total_credit'],
                }
            else:
                ress[res2['user_id']]['total_cash'] += res2['total_cash']
                ress[res2['user_id']]['total_credit'] += res2['total_credit']


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
                    'reward':0,
                    'total_insentif':0,
                }

        for res in ress.values():
            user_id = res['user_id']
            karyawan = res['karyawan']
            branch_id = res['branch_id']
            branch_code = res['branch_code']
            branch_name = res['branch_name']
            total_cash = res['total_cash']
            total_credit = res['total_credit']
            total_unit =  total_cash + total_credit 
           
            rupiah_unit_cash = self.env['teds.listing.table.insentif'].search([
                ('name','=','KOORDINATOR SALESMAN'),
                ('type_insentif','=','cash_credit'),
                ('total','=',total_unit)],limit=1).akumulasi

            rupiah_unit_credit = self.env['teds.listing.table.insentif'].search([
                ('name','=','KOORDINATOR SALESMAN'),
                ('type_insentif','=','unit_credit_ke'),
                ('total','=',total_credit)],limit=1).akumulasi

            listing_reward = self.env['teds.listing.table.insentif'].search([
                ('name','=','KOORDINATOR SALESMAN'),
                ('type_insentif','=','reward'),
                ('total','=',total_unit)],limit=1).insentif

            rupiah_unit_cash = 0 if not rupiah_unit_cash else rupiah_unit_cash
            rupiah_unit_credit = 0 if not rupiah_unit_credit else rupiah_unit_credit
            
            bawahan = """
                SELECT count(DISTINCT(user_id)) jml
                FROM dealer_sale_order
                WHERE state IN ('progress', 'done','cancelled') 
                AND branch_id = %d
                AND date_confirm BETWEEN '%s' AND '%s'  
                AND sales_koordinator_id = %d
                AND user_id != %d
            """%(branch_id,str(start_date),str(end_date),user_id,user_id)
            self._cr.execute(bawahan)
            jml_bawahan = self._cr.fetchone()[0]

            produktivitas = 0
            if jml_bawahan > 0:
                produktivitas = round(total_unit / jml_bawahan) if total_unit else 0
            
            reward1 = 0
            if jml_bawahan >=10:
                reward1 = listing_reward * 0.5
            
            reward2 = 0
            if produktivitas >= 8:
                reward2 = listing_reward * 0.5
        
            rupiah_reward = reward1 + reward2

            rupiah_total_unit = rupiah_unit_cash + rupiah_unit_credit
            total_insentif = rupiah_unit_cash + rupiah_unit_credit + rupiah_reward

            if results.get(res.get('branch_code')):
                results[res['branch_code']]['jml_karyawan'] += 1
                results[res['branch_code']]['total_unit_cash'] += total_cash
                results[res['branch_code']]['total_unit_credit'] += total_credit
                results[res['branch_code']]['total_insentif_cash'] += rupiah_unit_cash
                results[res['branch_code']]['total_insentif_credit'] += rupiah_unit_credit
                results[res['branch_code']]['reward'] += total_unit

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
                'reward':total_unit,
                'rupiah_reward':rupiah_reward,
                'jml_bawahan':jml_bawahan,
                'produktivitas':produktivitas,
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
        worksheet_summary.set_column('L1:L1', 18)

        
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
        worksheet_detail.set_column('M1:M1', 20)
        
        
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
        worksheet_summary.write('H5', 'Reward' , wbf['header'])
        worksheet_summary.write('I5', 'Total Inc' , wbf['header'])
        worksheet_summary.write('J5', 'Avarange / Orang' , wbf['header'])
        worksheet_summary.write('K5', 'Cost / Unit' , wbf['header'])
        worksheet_summary.write('L5', 'Produktivity' , wbf['header'])

        # Detail
        worksheet_detail.write('A5', 'Cabang' , wbf['header'])
        worksheet_detail.write('B5', 'Karyawan' , wbf['header'])
        worksheet_detail.write('C5', 'Total Cash' , wbf['header'])
        worksheet_detail.write('D5', 'Total Credit' , wbf['header'])
        worksheet_detail.write('E5', 'Total Unit' , wbf['header'])
        worksheet_detail.write('F5', 'Rupiah Cash' , wbf['header'])
        worksheet_detail.write('G5', 'Rupiah Credit' , wbf['header'])
        worksheet_detail.write('H5', 'Total Rupiah Unit' , wbf['header'])
        worksheet_detail.write('I5', 'Reward' , wbf['header'])
        worksheet_detail.write('J5', 'Rupiah Reward' , wbf['header'])
        worksheet_detail.write('K5', 'Jml Bawahan' , wbf['header'])
        worksheet_detail.write('L5', 'Produktivitas' , wbf['header'])
        worksheet_detail.write('M5', 'Total Insentif' , wbf['header'])

        sum_jml_karyawan = 0
        sum_total_unit_cash = 0
        sum_total_unit_credit = 0
        sum_total_unit_sm = 0
        sum_total_insentif_cash = 0
        sum_total_insentif_credit = 0
        sum_reward = 0
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
            worksheet_summary.write('H%s' % row_sm, result['reward'] , wbf['content_float'])
            worksheet_summary.write('I%s' % row_sm, total_insentif_sm , wbf['content_float'])
            worksheet_summary.write('J%s' % row_sm, avg_org , wbf['content_float'])
            worksheet_summary.write('K%s' % row_sm, cost_unit , wbf['content_float'])
            worksheet_summary.write('L%s' % row_sm, productivity , wbf['content_right'])

            sum_jml_karyawan += result['jml_karyawan']
            sum_total_unit_cash += result['total_unit_cash']
            sum_total_unit_credit += result['total_unit_credit']
            sum_total_unit_sm += total_unit_sm
            sum_total_insentif_cash += result['total_insentif_cash']
            sum_total_insentif_credit += result['total_insentif_credit']
            sum_reward += result['reward']
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
        sum_total_reward = 0
        sum_rupiah_reward = 0
        sum_productivitas = 0
        sum_jml_bawahan = 0
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
            worksheet_detail.write('I%s' % row_dt, detail['reward'] , wbf['content_right'])
            worksheet_detail.write('J%s' % row_dt, detail['rupiah_reward'] , wbf['content_float'])
            worksheet_detail.write('K%s' % row_dt, detail['jml_bawahan'] , wbf['content_right'])
            worksheet_detail.write('L%s' % row_dt, detail['produktivitas'] , wbf['content_right'])
            worksheet_detail.write('M%s' % row_dt, detail['total_insentif'] , wbf['content_float'])

            sum_total_cash += detail['total_cash']
            sum_total_credit += detail['total_credit']
            sum_total_uni += detail['total_unit']
            sum_rupiah_unit_cash += detail['rupiah_unit_cash']
            sum_rupiah_unit_credit += detail['rupiah_unit_credit']
            sum_rupiah_total_unit += detail['rupiah_total_unit']
            sum_total_reward += detail['reward']
            sum_rupiah_reward += detail['rupiah_reward']
            sum_jml_bawahan += detail['jml_bawahan']
            sum_productivitas += detail['produktivitas']
            sum_total_insentif += detail['total_insentif']

            row_dt += 1

        #Formula Summary
        formula_jml_karyawan_sm = '{=subtotal(9,B%s:B%s)}' % (row_sm1, row_sm-1)
        formula_total_unit_cash_sm = '{=subtotal(9,C%s:C%s)}' % (row_sm1, row_sm-1)
        formula_total_unit_credit_sm = '{=subtotal(9,D%s:D%s)}' % (row_sm1, row_sm-1)
        formula_total_unti_sm = '{=subtotal(9,E%s:E%s)}' % (row_sm1, row_sm-1)
        formula_total_insentif_cash_sm = '{=subtotal(9,F%s:F%s)}' % (row_sm1, row_sm-1)
        formula_total_insentif_credit_sm = '{=subtotal(9,G%s:G%s)}' % (row_sm1, row_sm-1)
        formula_reward = '{=subtotal(9,H%s:H%s)}' % (row_sm1, row_sm-1)
        formula_total_insentif_sm = '{=subtotal(9,I%s:I%s)}' % (row_sm1, row_sm-1)
        formula_avg_org_sm = '{=subtotal(9,J%s:J%s)}' % (row_sm1, row_sm-1)
        formula_cost_unit_sm = '{=subtotal(9,K%s:K%s)}' % (row_sm1, row_sm-1)
        formula_productivity_sm = '{=subtotal(9,L%s:L%s)}' % (row_sm1, row_sm-1)

        # Formula Detail
        formula_total_cash = '{=subtotal(9,C%s:C%s)}' % (row_dt1, row_dt-1)
        formula_total_credit = '{=subtotal(9,D%s:D%s)}' % (row_dt1, row_dt-1)
        formula_total_unit = '{=subtotal(9,E%s:E%s)}' % (row_dt1, row_dt-1)
        formula_rupiah_unit_cash = '{=subtotal(9,F%s:F%s)}' % (row_dt1, row_dt-1)
        formula_rupiah_unit_credit = '{=subtotal(9,G%s:G%s)}' % (row_dt1, row_dt-1)
        formula_rupiah_total_unit = '{=subtotal(9,H%s:H%s)}' % (row_dt1, row_dt-1)
        formula_total_reward = '{=subtotal(9,I%s:I%s)}' % (row_dt1, row_dt-1)
        formula_rupiah_reward = '{=subtotal(9,J%s:J%s)}' % (row_dt1, row_dt-1)
        formula_jml_bawahan = '{=subtotal(9,K%s:K%s)}' % (row_dt1, row_dt-1)
        formula_productivitas = '{=subtotal(9,L%s:L%s)}' % (row_dt1, row_dt-1)
        formula_total_insentif = '{=subtotal(9,M%s:M%s)}' % (row_dt1, row_dt-1)


        #TOTAL
        worksheet_summary.write('A%s' % (row_sm), 'Total', wbf['total'])

        worksheet_summary.write_formula(row_sm-1,1,formula_jml_karyawan_sm, wbf['total_number_float'], sum_jml_karyawan)
        worksheet_summary.write_formula(row_sm-1,2,formula_total_unit_cash_sm, wbf['total_number_float'], sum_total_unit_cash)
        worksheet_summary.write_formula(row_sm-1,3,formula_total_unit_credit_sm, wbf['total_number_float'], sum_total_unit_credit)
        worksheet_summary.write_formula(row_sm-1,4,formula_total_unti_sm, wbf['total_number_float'], sum_total_unit_sm)
        worksheet_summary.write_formula(row_sm-1,5,formula_total_insentif_cash_sm, wbf['total_number_float'], sum_total_insentif_cash)
        worksheet_summary.write_formula(row_sm-1,6,formula_total_insentif_credit_sm, wbf['total_number_float'], sum_total_insentif_credit)
        worksheet_summary.write_formula(row_sm-1,7,formula_reward, wbf['total_number_float'], sum_reward)
        worksheet_summary.write_formula(row_sm-1,8,formula_total_insentif_sm, wbf['total_number_float'], sum_total_insentif_sm)
        worksheet_summary.write_formula(row_sm-1,9,formula_avg_org_sm, wbf['total_number_float'], sum_avg_org)
        worksheet_summary.write_formula(row_sm-1,10,formula_cost_unit_sm, wbf['total_number_float'], sum_cost_unit)
        worksheet_summary.write_formula(row_sm-1,11,formula_productivity_sm, wbf['total_number_float'], sum_productivity)
        
        worksheet_detail.merge_range('A%s:B%s' % (row_dt,row_dt), 'Total', wbf['total'])

        worksheet_detail.write_formula(row_dt-1,2,formula_total_cash, wbf['total_number_float'], sum_total_cash)
        worksheet_detail.write_formula(row_dt-1,3,formula_total_credit, wbf['total_number_float'], sum_total_credit)
        worksheet_detail.write_formula(row_dt-1,4,formula_total_unit, wbf['total_number_float'], sum_total_uni)
        worksheet_detail.write_formula(row_dt-1,5,formula_rupiah_unit_cash, wbf['total_number_float'], sum_rupiah_unit_cash)
        worksheet_detail.write_formula(row_dt-1,6,formula_rupiah_unit_credit, wbf['total_number_float'], sum_rupiah_unit_credit)
        worksheet_detail.write_formula(row_dt-1,7,formula_rupiah_total_unit, wbf['total_number_float'], sum_rupiah_total_unit)
        worksheet_detail.write_formula(row_dt-1,8,formula_total_reward, wbf['total_number_float'], sum_total_reward)
        worksheet_detail.write_formula(row_dt-1,9,formula_rupiah_reward, wbf['total_number_float'], sum_rupiah_reward)
        worksheet_detail.write_formula(row_dt-1,10,formula_jml_bawahan, wbf['total_number_float'], sum_jml_bawahan)
        worksheet_detail.write_formula(row_dt-1,11,formula_productivitas, wbf['total_number_float'], sum_productivitas)
        worksheet_detail.write_formula(row_dt-1,12,formula_total_insentif, wbf['total_number_float'], sum_total_insentif)

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


