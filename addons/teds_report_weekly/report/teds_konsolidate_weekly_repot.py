import time
import cStringIO
import xlsxwriter
from cStringIO import StringIO
import base64
import tempfile
import os
from openerp import models, fields, api
from datetime import datetime, timedelta,date
from dateutil.relativedelta import relativedelta
from xlsxwriter.utility import xl_rowcol_to_cell
import calendar


class KonsolidateWeeklyReportWizard(models.TransientModel):
    _name = "teds.konsolidate.weekly.report.wizard"

    def _get_tahun(self):
        return date.today().year

    wbf = {}

    name = fields.Char('Filename', readonly=True)
    state_x = fields.Selection([('choose','choose'),('get','get')], default='choose')
    data_x = fields.Binary('File', readonly=True)
    bulan = fields.Selection([
        ('1','January'),
        ('2','February'),
        ('3','March'),
        ('4','April'),
        ('5','May'),
        ('6','June'),
        ('7','July'),
        ('8','August'),
        ('9','September'),
        ('10','October'),
        ('11','November'),
        ('12','December')], 'Bulan', required=True)
    tahun = fields.Char('Tahun', default=_get_tahun,required=True)

    @api.multi
    def add_workbook_format(self,workbook):      
        self.wbf['title_doc'] = workbook.add_format({'bold': 1,'align': 'left'})
        self.wbf['title_doc'].set_font_size(20)
        
        self.wbf['header'] = workbook.add_format({'bold': 1,'align': 'center','bg_color': '#E67E22','font_color': '#FFFFFF'})
        self.wbf['header'].set_border()
        self.wbf['header'].set_align('vcenter')
        self.wbf['header'].set_font_size(12)

        self.wbf['header_no'] = workbook.add_format({'bold': 1,'align': 'center','bg_color': '#E67E22','font_color': '#FFFFFF'})
        self.wbf['header_no'].set_border()
        self.wbf['header_no'].set_align('vcenter')
        self.wbf['header_no'].set_font_size(12)
                
        self.wbf['footer'] = workbook.add_format({'align':'left'})
        
                
        self.wbf['company'] = workbook.add_format({'align': 'left'})
        self.wbf['company'].set_font_size(11)
        
        self.wbf['content'] = workbook.add_format()
        self.wbf['content'].set_left()
        self.wbf['content'].set_right() 
        
        self.wbf['content_percent'] = workbook.add_format({'num_format':'#0%'})
        self.wbf['content_percent'].set_left()
        self.wbf['content_percent'].set_right() 
        
        self.wbf['content_color'] = workbook.add_format({'bg_color':'#82F3B1'})
        self.wbf['content_color'].set_left()
        self.wbf['content_color'].set_right() 

        self.wbf['content_percent_color'] = workbook.add_format({'bg_color':'#82F3B1','num_format':'#0%'})
        self.wbf['content_percent_color'].set_left()
        self.wbf['content_percent_color'].set_right() 
        
        self.wbf['content_center'] = workbook.add_format({'align': 'center'})
        self.wbf['content_center'].set_left()
        self.wbf['content_center'].set_right() 
        self.wbf['content_center'].set_align('vcenter')
        
                
        self.wbf['total_float'] = workbook.add_format({'bold':1,'bg_color': '#D5F5E3','align': 'right','num_format': '#,##0.00'})
        self.wbf['total_float'].set_top()
        self.wbf['total_float'].set_bottom()            
        self.wbf['total_float'].set_left()
        self.wbf['total_float'].set_right()         
        
        self.wbf['total_number'] = workbook.add_format({'align':'right','bg_color': '#FFFFDB','bold':1})
        self.wbf['total_number'].set_top()
        self.wbf['total_number'].set_bottom()            
        self.wbf['total_number'].set_left()
        self.wbf['total_number'].set_right()
        
        self.wbf['total'] = workbook.add_format({'bold':1,'bg_color': '#D5F5E3','align':'center'})
        self.wbf['total'].set_left()
        self.wbf['total'].set_right()
        self.wbf['total'].set_top()
        self.wbf['total'].set_bottom()
        
        return workbook

    @api.multi
    def action_export(self):
        self.ensure_one()
        
        query_where = " WHERE 1=1"
        if self.bulan and self.tahun:
            query_where += " AND wk.bulan = '%s' AND wk.tahun = '%s'" %(self.bulan,self.tahun)

        query_week = """
            SELECT
            to_char(wk.start_date,'dd') ||'-'|| to_char(wk.end_date,'dd') ||' '|| to_char(wk.end_date,'Mon') as week
            FROM teds_report_weekly_konsolidate wk
            INNER JOIN teds_report_weekly_master_area ma ON ma.id = wk.area_id
            INNER JOIN teds_report_weekly_konsolidate_dealer kd ON kd.konsolidate_id = wk.id
            %s
            GROUP BY start_date,end_date
            ORDER BY end_date ASC
        """ %(query_where)
        self._cr.execute (query_week)
        week =  self._cr.fetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(workbook)
        wbf = self.wbf
        worksheet = workbook.add_worksheet('Konsolidate Weekly %s')
        worksheet.set_column('A1:A1', 5)
        worksheet.set_column('B1:B1', 25)
        worksheet.set_column('C1:C1', 25)
        worksheet.set_column('D1:D1', 30)
        worksheet.set_column('E1:E1', 15)
        worksheet.set_column('F1:F1', 15)
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
        
        
        
        bulan = int(self.bulan)
        tahun = int(self.tahun)
        nama_bln = calendar.month_name[bulan]
        
        filename = 'Report Konsolidate Periode %s %s.xlsx' %(nama_bln,tahun)
        worksheet.merge_range('A1:B1','%s %s'%(nama_bln,tahun), wbf['title_doc'])
        
        worksheet.merge_range('A3:A4', 'No' , wbf['header_no'])
        worksheet.merge_range('B3:B4', 'Main Dealer' , wbf['header'])
        worksheet.merge_range('C3:C4', 'Kabupaten' , wbf['header'])
        worksheet.merge_range('D3:D4', 'Nama Dealer' , wbf['header'])
        worksheet.merge_range('E3:I3', 'Unit Sales' , wbf['header'])
        worksheet.merge_range('J3:N3', 'Rank M' , wbf['header'])
        worksheet.merge_range('O3:O4', 'RANK M-1 CLS' , wbf['header'])
        worksheet.merge_range('P3:T3', 'GROWTH VS LM' , wbf['header'])

        
        week_1 = ""
        week_2 = ""
        week_3 = ""
        week_4 = ""
        week_5 = ""

        report = False
        if len(week) == 5 :
            report = True
            week_1 = week[0][0]
            week_2 = week[1][0]
            week_3 = week[2][0]
            week_4 = week[3][0]
            week_5 = week[4][0]

            # Unit Sales #
            worksheet.write('E4','Week 1',wbf['header'])
            worksheet.write('F4','Week 2',wbf['header'])
            worksheet.write('G4','Week 3',wbf['header'])
            worksheet.write('H4','Week 4',wbf['header'])
            worksheet.write('I4','Week 5',wbf['header'])
            
            # Rank M #
            worksheet.write('J4','Week 1',wbf['header'])
            worksheet.write('K4','Week 2',wbf['header'])
            worksheet.write('L4','Week 3',wbf['header'])
            worksheet.write('M4','Week 4',wbf['header'])
            worksheet.write('N4','Week 5',wbf['header'])
            
            # Growth #
            worksheet.write('P4','Week 1',wbf['header'])
            worksheet.write('Q4','Week 2',wbf['header'])
            worksheet.write('R4','Week 3',wbf['header'])
            worksheet.write('S4','Week 4',wbf['header'])
            worksheet.write('T4','Week 5',wbf['header'])

            row=2

        # worksheet.merge_range('I3:I4','Closing' , wbf['header'])
            
        if report:
            query = """
                SELECT kd.id as kd_id
                , ma.name as area
                , kd.name as dealer
                , kd.type
                , wk.start_date
                , wk.end_date
                , to_char(wk.start_date,'dd') ||'-'|| to_char(wk.end_date,'dd') ||' '|| to_char(wk.end_date,'Mon') as week
                , COALESCE(kd.total,0) as total
                , ma.main_dealer
                FROM teds_report_weekly_konsolidate wk
                INNER JOIN teds_report_weekly_master_area ma ON ma.id = wk.area_id
                INNER JOIN teds_report_weekly_konsolidate_dealer kd ON kd.konsolidate_id = wk.id
                %s
                ORDER BY area ASC
            """ %(query_where)
            self._cr.execute (query)
            ress =  self._cr.dictfetchall()
            result = {}
            for res in ress:
                area = res.get('area')
                dealer = res.get('dealer')
                week = res.get('week')
                total = res.get('total')
                type = res.get('type')
                main_dealer = res.get('main_dealer')
                kd_id = res.get('kd_id')
                obj_kd = self.env['teds.report.weekly.konsolidate.dealer'].browse(kd_id)
                ranking_lm = obj_kd.ranking_lm
                total_lm = obj_kd.total_lm

                if not result.get(area):
                    result[area] = {dealer:{'dealer':dealer,'area':area,week:[total,obj_kd.ranking,ranking_lm,total_lm],'type':type,'main_dealer':main_dealer}}
                else:
                    if not result[area].get(dealer):
                        result[area][dealer] = {'dealer':dealer,'area':area,week:[total,obj_kd.ranking,ranking_lm,total_lm],'type':type,'main_dealer':main_dealer}
                    else:
                        if not result[area][dealer].get(week):
                            result[area][dealer][week] = [total,obj_kd.ranking,ranking_lm,total_lm]
            row = 5             
            row1 = row
            no = 1     
            n = 0
            for vals in result.values():
                tot_week_1 = 0
                tot_week_2 = 0
                tot_week_3 = 0
                tot_week_4 = 0
                tot_week_5 = 0
                tot_closing = 0

                for val in vals.values():
                    jml = result.get(val.get('area'),[])
                    
                    # Weekly # 
                    total_week = int(val.get(week_1)[0]) + int(val.get(week_2)[0]) + int(val.get(week_3)[0]) + int(val.get(week_4)[0]) + int(val.get(week_5)[0])
                    row_x = len(jml)
                    worksheet.write('A%s' %(row), no , wbf['content_center'])
                    worksheet.write('D%s' %(row), val.get('dealer') , wbf['content'] if val.get('type') != 'Cabang' else wbf['content_color'])
                    worksheet.write('E%s' %(row), val.get(week_1)[0] , wbf['content'] if val.get('type') != 'Cabang' else wbf['content_color'])
                    worksheet.write('F%s' %(row), val.get(week_2)[0] , wbf['content'] if val.get('type') != 'Cabang' else wbf['content_color'])
                    worksheet.write('G%s' %(row), val.get(week_3)[0] , wbf['content'] if val.get('type') != 'Cabang' else wbf['content_color'])
                    worksheet.write('H%s' %(row), val.get(week_4)[0] , wbf['content'] if val.get('type') != 'Cabang' else wbf['content_color'])
                    worksheet.write('I%s' %(row), val.get(week_5)[0] , wbf['content'] if val.get('type') != 'Cabang' else wbf['content_color'])
                    
                    # Ranking #
                    worksheet.write('J%s' %(row), val.get(week_1)[1] , wbf['content'] if val.get('type') != 'Cabang' else wbf['content_color'])
                    worksheet.write('K%s' %(row), val.get(week_2)[1] , wbf['content'] if val.get('type') != 'Cabang' else wbf['content_color'])
                    worksheet.write('L%s' %(row), val.get(week_3)[1] , wbf['content'] if val.get('type') != 'Cabang' else wbf['content_color'])
                    worksheet.write('M%s' %(row), val.get(week_4)[1] , wbf['content'] if val.get('type') != 'Cabang' else wbf['content_color'])
                    worksheet.write('N%s' %(row), val.get(week_5)[1] , wbf['content'] if val.get('type') != 'Cabang' else wbf['content_color'])
                    
                    # Ranking M-1 #
                    worksheet.write('O%s' %(row), val.get(week_5)[2] , wbf['content'] if val.get('type') != 'Cabang' else wbf['content_color'])
                    
                    # Growth vs LM#
                    growth1 = 0
                    growth2 = 0
                    growth3 = 0
                    growth4 = 0
                    growth5 = 0

                    if val.get(week_1)[3] > 0:
                        growth1 = (val.get(week_1)[0] / val.get(week_1)[3])-1
                    if val.get(week_2)[3] > 0:
                        growth2 = (val.get(week_2)[0] / val.get(week_2)[3])-1
                    if val.get(week_3)[3] > 0:
                        growth3 = (val.get(week_3)[0] / val.get(week_3)[3])-1
                    if val.get(week_4)[3] > 0:
                        growth4 = (val.get(week_4)[0] / val.get(week_4)[3])-1
                    if val.get(week_5)[3] > 0:
                        growth5 = (val.get(week_5)[0] / val.get(week_5)[3])-1


                    worksheet.write('P%s' %(row), growth1 , wbf['content_percent'] if val.get('type') != 'Cabang' else wbf['content_percent_color'])
                    worksheet.write('Q%s' %(row), growth2 , wbf['content_percent'] if val.get('type') != 'Cabang' else wbf['content_percent_color'])
                    worksheet.write('R%s' %(row), growth3 , wbf['content_percent'] if val.get('type') != 'Cabang' else wbf['content_percent_color'])
                    worksheet.write('S%s' %(row), growth4 , wbf['content_percent'] if val.get('type') != 'Cabang' else wbf['content_percent_color'])
                    worksheet.write('T%s' %(row), growth5 , wbf['content_percent'] if val.get('type') != 'Cabang' else wbf['content_percent_color'])
                    
                    no += 1
                    row += 1
                    n += 1
                    if n == row_x:
                        n = 0
                        awal = row1-n
                        akhir =  row-1
                        worksheet.merge_range('B%s:B%s' %(awal,akhir), val.get('main_dealer') , wbf['content_center'])
                        worksheet.merge_range('C%s:C%s' %(awal,akhir), val.get('area') , wbf['content_center'])

                        formula_week_1 =  '{=subtotal(9,E%s:E%s)}' % (row1, row-1)
                        formula_week_2 =  '{=subtotal(9,F%s:F%s)}' % (row1, row-1)
                        formula_week_3 =  '{=subtotal(9,G%s:G%s)}' % (row1, row-1)
                        formula_week_4 =  '{=subtotal(9,H%s:H%s)}' % (row1, row-1)
                        formula_week_5 =  '{=subtotal(9,I%s:I%s)}' % (row1, row-1)
                        # formula_closing =  '{=subtotal(9,I%s:I%s)}' % (row1, row-1)


                        worksheet.merge_range('A%s:D%s' %(row,row), 'Total' , wbf['total'])    
                        worksheet.write_formula(row-1,4,formula_week_1, wbf['total_float'], tot_week_1)
                        worksheet.write_formula(row-1,5,formula_week_2, wbf['total_float'], tot_week_2)
                        worksheet.write_formula(row-1,6,formula_week_3, wbf['total_float'], tot_week_3)
                        worksheet.write_formula(row-1,7,formula_week_4, wbf['total_float'], tot_week_4)
                        worksheet.write_formula(row-1,8,formula_week_5, wbf['total_float'], tot_week_5)
                        worksheet.merge_range('J%s:T%s' %(row,row), '' , wbf['total'])    
                        # worksheet.write_formula(row-1,8,formula_closing, wbf['total_float'], tot_closing)
                        row += 1
                        row1 = row

        worksheet.freeze_panes(4, 4)
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write({'state_x':'get', 'data_x':out, 'name': filename})
        fp.close()
        ir_model_data = self.env['ir.model.data']
        form_id = self.env.ref('teds_report_weekly.view_teds_konsolidate_weekly_report_wizard').id
        return {
            'name':('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.konsolidate.weekly.report.wizard',
            'res_id': self.ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }


            

