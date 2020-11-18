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
import logging
import re
import pytz
from lxml import etree
import calendar

class SalesActivityReportWizard(models.TransientModel):
    _name = "teds.sales.activity.report.wizard"
    
    def _get_default_branch(self):
        branch_ids = False
        branch_ids = self.env.user.branch_ids
        if branch_ids and len(branch_ids) == 1 :
            return branch_ids[0].id
        return False

    @api.model
    def _get_default_date(self): 
        return self.env['wtc.branch'].get_default_date()

    def _get_tahun(self):
        return date.today().year

    wbf = {}

    name = fields.Char('Filename', readonly=True)
    state_x = fields.Selection([('choose','choose'),('get','get')], default='choose')
    data_x = fields.Binary('File', readonly=True)
    bulan = fields.Selection([('1','Januari'),
                              ('2','Februari'),
                              ('3','Maret'),
                              ('4','April'),
                              ('5','Mei'),
                              ('6','Juni'),
                              ('7','Juli'),
                              ('8','Agustus'),
                              ('9','September'),
                              ('10','Oktober'),
                              ('11','November'),
                              ('12','Desember')], 'Bulan', required=True)
    tahun = fields.Char('Tahun', default=_get_tahun,required=True)
    options = fields.Selection([
        ('all','All'),
        ('open','Open'),
        ('confirm_done','Confirm & Done'),
        ('reject','Reject')],string="Options" ,default="confirm_done")
    branch_ids = fields.Many2many('wtc.branch', 'teds_sales_activity_report', 'teds_sales_activity_report_wizard_id','branch_id', 'Branches', default=_get_default_branch)

    @api.multi
    def add_workbook_format(self, workbook):
        self.wbf['company'] = workbook.add_format({'bold':1,'align': 'left','font_color':'#000000','num_format': 'dd-mm-yyyy'})
        self.wbf['company'].set_font_size(12)

        self.wbf['footer'] = workbook.add_format({'align':'left'})

        self.wbf['header'] = workbook.add_format({'bg_color':'#FFFF00','bold': 1,'align': 'center','font_color': '#000000'})
        self.wbf['header'].set_top(2)
        self.wbf['header'].set_bottom()
        self.wbf['header'].set_left()
        self.wbf['header'].set_right()
        self.wbf['header'].set_font_size(11)
        self.wbf['header'].set_align('vcenter')

        self.wbf['header_left'] = workbook.add_format({'bg_color':'#FFFF00','bold': 1,'align': 'center','font_color': '#000000'})
        self.wbf['header_left'].set_top(2)
        self.wbf['header_left'].set_bottom()
        self.wbf['header_left'].set_left(2)
        self.wbf['header_left'].set_right()
        self.wbf['header_left'].set_font_size(11)
        self.wbf['header_left'].set_align('vcenter')
        
        self.wbf['header_right'] = workbook.add_format({'bg_color':'#FFFF00','bold': 1,'align': 'center','font_color': '#000000'})
        self.wbf['header_right'].set_top(2)
        self.wbf['header_right'].set_bottom()
        self.wbf['header_right'].set_left()
        self.wbf['header_right'].set_right(2)
        self.wbf['header_right'].set_font_size(11)
        self.wbf['header_right'].set_align('vcenter')


        self.wbf['content'] = workbook.add_format({'align': 'left','font_color': '#000000'})
        self.wbf['content'].set_left()
        self.wbf['content'].set_right()
        self.wbf['content'].set_top()
        self.wbf['content'].set_bottom()
        self.wbf['content'].set_font_size(10)                

        self.wbf['content_bg'] = workbook.add_format({'bg_color': '#81DAF5','align': 'right','font_color': '#000000'})
        self.wbf['content_bg'].set_left()
        self.wbf['content_bg'].set_right()
        self.wbf['content_bg'].set_top()
        self.wbf['content_bg'].set_bottom()
        self.wbf['content_bg'].set_font_size(10)                
      
        self.wbf['content_center'] = workbook.add_format({'align': 'center','font_color': '#000000'})
        self.wbf['content_center'].set_left()
        self.wbf['content_center'].set_right()
        self.wbf['content_center'].set_top()
        self.wbf['content_center'].set_bottom()
        self.wbf['content_center'].set_font_size(10)
        
        self.wbf['content_left'] = workbook.add_format({'align': 'left','font_color': '#000000'})
        self.wbf['content_left'].set_left(2)
        self.wbf['content_left'].set_right()
        self.wbf['content_left'].set_top()
        self.wbf['content_left'].set_bottom()
        self.wbf['content_left'].set_font_size(10)
        
        self.wbf['content_right'] = workbook.add_format({'align': 'right','font_color': '#000000'})
        self.wbf['content_right'].set_left()
        self.wbf['content_right'].set_right(2)
        self.wbf['content_right'].set_top()
        self.wbf['content_right'].set_bottom()
        self.wbf['content_right'].set_font_size(10)

        self.wbf['content_bottom'] = workbook.add_format({'align': 'center','font_color': '#000000'})
        self.wbf['content_bottom'].set_left()
        self.wbf['content_bottom'].set_right()
        self.wbf['content_bottom'].set_top()
        self.wbf['content_bottom'].set_bottom(2)
        self.wbf['content_bottom'].set_font_size(10)

        self.wbf['content_left_bottom'] = workbook.add_format({'align': 'center','font_color': '#000000'})
        self.wbf['content_left_bottom'].set_left(2)
        self.wbf['content_left_bottom'].set_right()
        self.wbf['content_left_bottom'].set_top()
        self.wbf['content_left_bottom'].set_bottom(2)
        self.wbf['content_left_bottom'].set_font_size(10)
        
        self.wbf['content_right_bottom'] = workbook.add_format({'align': 'center','font_color': '#000000'})
        self.wbf['content_right_bottom'].set_left()
        self.wbf['content_right_bottom'].set_right(2)
        self.wbf['content_right_bottom'].set_top()
        self.wbf['content_right_bottom'].set_bottom(2)
        self.wbf['content_right_bottom'].set_font_size(10)


        self.wbf['content_center_bg'] = workbook.add_format({'bg_color':'#85C1E9', 'align': 'center','font_color': '#000000'})
        self.wbf['content_center_bg'].set_left()
        self.wbf['content_center_bg'].set_right()
        self.wbf['content_center_bg'].set_top()
        self.wbf['content_center_bg'].set_bottom()
        self.wbf['content_center_bg'].set_font_size(10)                
        
        self.wbf['content_center_bg_bottom'] = workbook.add_format({'bg_color':'#85C1E9', 'align': 'center','font_color': '#000000'})
        self.wbf['content_center_bg_bottom'].set_left()
        self.wbf['content_center_bg_bottom'].set_right()
        self.wbf['content_center_bg_bottom'].set_top()
        self.wbf['content_center_bg_bottom'].set_bottom(2)
        self.wbf['content_center_bg_bottom'].set_font_size(10)               

        self.wbf['total'] = workbook.add_format({'bold':1,'bg_color': '#FFFFDB','align':'center'})
        self.wbf['total'].set_left()
        self.wbf['total'].set_right()
        self.wbf['total'].set_top()
        self.wbf['total'].set_bottom()
        
        self.wbf['total_float'] = workbook.add_format({'bold':1,'bg_color': '#FFFFDB','align': 'right','num_format': '#,##0.00'})
        self.wbf['total_float'].set_top()
        self.wbf['total_float'].set_bottom()            
        self.wbf['total_float'].set_left()
        self.wbf['total_float'].set_right()         
       
        return workbook

    @api.multi
    def excel_report(self):
        self.ensure_one()

        bulan = self.bulan
        tahun = self.tahun
        branch_ids = self.branch_ids
        
        query_where = " WHERE pa.state != 'draft' AND pa.bulan = '%s' AND pa.tahun = '%s'"%(bulan,tahun)
        
        if branch_ids:
            query_where += " AND pa.branch_id IN %s" % str(tuple([b.id for b in self.branch_ids])).replace(',)', ')')
        
        if self.options == 'open':
            query_where += " AND pal.state = 'open'"
        elif self.options == 'confirm_done':
            query_where += " AND pal.state in ('confirmed','done')"
        elif self.options == 'reject':
            query_where += " AND pal.state = 'reject'"

        query = """
            SELECT
            b.code as branch_code
            , b.name as branch_name
            , CASE WHEN pa.bulan = '1' THEN 'Januari'
            WHEN pa.bulan = '2' THEN 'Februari'
            WHEN pa.bulan = '3' THEN 'Maret'
            WHEN pa.bulan = '4' THEN 'April'
            WHEN pa.bulan = '5' THEN 'Mei'
            WHEN pa.bulan = '6' THEN 'Juni'
            WHEN pa.bulan = '7' THEN 'Juli'
            WHEN pa.bulan = '8' THEN 'Agustus'
            WHEN pa.bulan = '9' THEN 'September'
            WHEN pa.bulan = '10' THEN 'Oktober'
            WHEN pa.bulan = '11' THEN 'November'
            WHEN pa.bulan = '12' THEN 'Desember'
            END ||'-' || pa.tahun as periode
            , pal.name as activity
            , pal.jaringan_penjualan
            , pal.display_unit
            , pal.target_unit
            , pal.target_customer
            , pal.no_telp as no_telp
            , pal.street || ', RT/RW: '|| pal.rt || '/' || pal.rw as alamat
            , pal.state as status_detail 
            , sp.name as type_act
            , tk.name as titik_keramaian
            , mr.name as ring
            , COALESCE(biaya.subtotal,0) as biaya
            , city.name as city
            , kec.name as kecamatan
            , kel.name as kelurahan
            , hr.name_related as pic
            , COALESCE(to_char(pal.start_date, 'DD-Mon-YYYY'),'') as start_date
            , COALESCE(to_char(pal.end_date, 'DD-Mon-YYYY'),'') as end_date
            , loc.complete_name as location
            , (SELECT count(id) FROM dealer_spk WHERE activity_plan_id = pal.id) as actual_customer
            , (SELECT sum(sol.product_qty) FROM dealer_sale_order so 
            INNER JOIN dealer_sale_order_line sol ON sol.dealer_sale_order_line_id = so.id
            WHERE so.activity_plan_id = pal.id
            AND so.state in ('progress','done')
            ) as actual_unit
            , l_s.complete_name as loc_src
            FROM teds_sales_plan_activity pa
            INNER JOIN teds_sales_plan_activity_line pal ON pal.activity_id = pa.id
            INNER JOIN wtc_branch b ON b.id = pa.branch_id
            INNER JOIN teds_act_type_sumber_penjualan sp ON sp.id = pal.act_type_id
            INNER JOIN titik_keramaian tk ON tk.id = pal.titik_keramaian_id
            INNER JOIN master_ring mr ON mr.id = tk.ring_id
            INNER JOIN wtc_kecamatan kec On kec.id = tk.kecamatan_id
            LEFT JOIN wtc_kelurahan kel ON kel.id = pal.id
            LEFT JOIN wtc_city city ON city.id = kec.city_id
            INNER JOIN hr_employee hr ON hr.id = pal.pic_id
            LEFT JOIN stock_location loc ON loc.id = pal.location_id
            LEFT JOIN (
                SELECT COALESCE(sum(amount / 0.9),0) as subtotal
                , activity_id
                FROM teds_activity_detail_biaya 
                GROUP BY activity_id
            ) biaya ON biaya.activity_id = pal.id
            LEFT JOIN stock_location l_s ON l_s.id = pal.source_pos_location_id 
            %s
            ORDER BY b.code ASC
        """ %(query_where)

        self.env.cr.execute(query)
        ress = self.env.cr.dictfetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)       
        workbook = self.add_workbook_format(workbook)
        wbf = self.wbf
        worksheet = workbook.add_worksheet('Report Sales Activity')

        worksheet.set_column('B1:B1', 10)
        worksheet.set_column('C1:C1', 23)
        worksheet.set_column('D1:D1', 14)
        worksheet.set_column('E1:E1', 15)
        worksheet.set_column('F1:F1', 15)
        worksheet.set_column('G1:G1', 24)
        worksheet.set_column('H1:H1', 22)
        worksheet.set_column('I1:I1', 10)
        worksheet.set_column('J1:J1', 12)
        worksheet.set_column('K1:K1', 15)
        worksheet.set_column('L1:L1', 15)
        worksheet.set_column('M1:M1', 35)
        worksheet.set_column('N1:N1', 20)
        worksheet.set_column('O1:O1', 23)
        worksheet.set_column('P1:P1', 18)
        worksheet.set_column('Q1:Q1', 20)
        worksheet.set_column('R1:R1', 18)
        worksheet.set_column('S1:S1', 14)
        worksheet.set_column('T1:T1', 14)
        worksheet.set_column('U1:U1', 15)
        worksheet.set_column('V1:V1', 40)
        worksheet.set_column('W1:W1', 17)
        worksheet.set_column('X1:X1', 17)
        worksheet.set_column('Y1:Y1', 17)
        worksheet.set_column('Z1:Z1', 17)
        worksheet.set_column('AA1:AA1', 17)
        worksheet.set_column('AB1:AB1', 40)
        worksheet.set_column('AC1:AC1', 18)
        
        month = self.bulan
        month_str = (calendar.month_name[int(month)])
        tahun = self.tahun
        date_now = self._get_default_date()
        date1 = date_now.strftime("%d-%m-%Y %H:%M:%S")
        date2 = date_now.strftime("%d-%m-%Y")
        user_id = self.env['res.users'].search([('id','=',self._uid)])
        user = user_id.name 
        company = user_id.company_id.name
        filename = 'Report Sales Activity' + str(date1)+'.xlsx'

        worksheet.merge_range('A1:C1', company , wbf['company'])
        worksheet.merge_range('A2:B2', 'Report Sales Activity' , wbf['company'])
        worksheet.write('A3', 'Periode' , wbf['company'])
        worksheet.write('B3', ": %s-%s" %(month_str,tahun) , wbf['company'])
        worksheet.write('A4', 'Options' , wbf['company'])
        worksheet.write('B4', ': %s' %self.options.title().replace('_',' ') , wbf['company'])
        
        row=5

        worksheet.write('A%s' % (row+1), 'No' , wbf['header_left'])
        worksheet.write('B%s' % (row+1), 'Code' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'Branch' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'Periode' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'Jaringan Penjualan' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'Act Type' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'Activity' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'Titik Keramaian' , wbf['header'])
        worksheet.write('I%s' % (row+1), 'Ring' , wbf['header'])
        worksheet.write('J%s' % (row+1), 'Jenis Biaya' , wbf['header'])
        worksheet.write('K%s' % (row+1), 'Est Biaya' , wbf['header'])
        worksheet.write('L%s' % (row+1), 'Biaya' , wbf['header'])
        worksheet.write('M%s' % (row+1), 'Alamat' , wbf['header'])
        worksheet.write('N%s' % (row+1), 'Kabupaten' , wbf['header'])
        worksheet.write('O%s' % (row+1), 'Kecamatan' , wbf['header'])
        worksheet.write('P%s' % (row+1), 'Kelurahan' , wbf['header_right'] )
        worksheet.write('Q%s' % (row+1), 'PIC' , wbf['header_right'] )
        worksheet.write('R%s' % (row+1), 'Contact' , wbf['header_right'] )
        worksheet.write('S%s' % (row+1), 'Start Date' , wbf['header_right'] )
        worksheet.write('T%s' % (row+1), 'End Date' , wbf['header_right'] )
        worksheet.write('U%s' % (row+1), 'Location ?' , wbf['header_right'] )
        worksheet.write('V%s' % (row+1), 'Location' , wbf['header_right'] )
        worksheet.write('W%s' % (row+1), 'Display Unit' , wbf['header_right'] )
        worksheet.write('X%s' % (row+1), 'Target Unit' , wbf['header_right'] )
        worksheet.write('Y%s' % (row+1), 'Target Customer' , wbf['header_right'] )
        worksheet.write('Z%s' % (row+1), 'Actual Unit' , wbf['header_right'] )
        worksheet.write('AA%s' % (row+1), 'Actual Customer' , wbf['header_right'] )
        worksheet.write('AB%s' % (row+1), 'POS Source Location' , wbf['header_right'] )
        worksheet.write('AC%s' % (row+1), 'State' , wbf['header_right'] )

        
        row+=2       
        row1=row
        no = 1
        
        total_display_unit = 0
        total_target_unit = 0
        total_target_customer = 0
        total_act_unit = 0
        total_act_customer = 0 

        for res in ress:
            branch_code = str(res.get('branch_code').encode('ascii','ignore').decode('ascii'))
            branch_name = str(res.get('branch_name').encode('ascii','ignore').decode('ascii'))
            periode = str(res.get('periode').encode('ascii','ignore').decode('ascii'))
            jaringan_penjualan = str(res.get('jaringan_penjualan').encode('ascii','ignore').decode('ascii'))
            type_act = str(res.get('type_act').encode('ascii','ignore').decode('ascii'))
            activity = str(res.get('activity').encode('ascii','ignore').decode('ascii'))
            titik_keramaian = str(res.get('titik_keramaian').encode('ascii','ignore').decode('ascii'))
            ring = str(res.get('ring').encode('ascii','ignore').decode('ascii'))
            jenis_biaya = res.get('jenis_biaya')
            estimasi_biaya = res.get('estimasi_biaya')
            biaya = res.get('biaya')
            alamat = res.get('alamat')
            city = str(res.get('city').encode('ascii','ignore').decode('ascii'))
            kecamatan = str(res.get('kecamatan').encode('ascii','ignore').decode('ascii'))
            kelurahan = res.get('kelurahan')
            pic = str(res.get('pic').encode('ascii','ignore').decode('ascii'))
            no_telp = str(res.get('no_telp').encode('ascii','ignore').decode('ascii'))
            start_date = str(res.get('start_date').encode('ascii','ignore').decode('ascii'))
            end_date = str(res.get('end_date').encode('ascii','ignore').decode('ascii'))
            is_location = 'Ya' if res.get('location') else 'Tidak'
            location = res.get('location')
            display_unit = res.get('display_unit')
            target_unit = res.get('target_unit')
            target_customer = res.get('target_customer')
            actual_unit = res.get('actual_unit') if res.get('actual_unit') else 0
            actual_customer = res.get('actual_customer') if res.get('actual_customer') else 0
            loc_src = res.get('loc_src')
            status_detail = res.get('status_detail','').title()

            worksheet.write('A%s' % row, no , wbf['content_left']) 
            worksheet.write('B%s' % row, branch_code , wbf['content']) 
            worksheet.write('C%s' % row, branch_name , wbf['content']) 
            worksheet.write('D%s' % row, periode , wbf['content'])
            worksheet.write('E%s' % row, jaringan_penjualan , wbf['content'])
            worksheet.write('F%s' % row, type_act , wbf['content'])
            worksheet.write('G%s' % row, activity , wbf['content'])
            worksheet.write('H%s' % row, titik_keramaian , wbf['content'])
            worksheet.write('I%s' % row, ring , wbf['content'])
            worksheet.write('J%s' % row, jenis_biaya , wbf['content'])
            worksheet.write('K%s' % row, estimasi_biaya , wbf['content_right'])
            worksheet.write('L%s' % row, biaya , wbf['content_right'])
            worksheet.write('M%s' % row, alamat , wbf['content'])
            worksheet.write('N%s' % row, city , wbf['content'])
            worksheet.write('O%s' % row, kecamatan , wbf['content'])
            worksheet.write('P%s' % row, kelurahan , wbf['content'])
            worksheet.write('Q%s' % row, pic , wbf['content'])
            worksheet.write('R%s' % row, no_telp , wbf['content'])
            worksheet.write('S%s' % row, start_date , wbf['content'])
            worksheet.write('T%s' % row, end_date , wbf['content'])
            worksheet.write('U%s' % row, is_location , wbf['content'])
            worksheet.write('V%s' % row, location , wbf['content'])
            worksheet.write('W%s' % row, display_unit , wbf['content_right'])
            worksheet.write('X%s' % row, target_unit , wbf['content_right'])
            worksheet.write('Y%s' % row, target_customer , wbf['content_right'])
            worksheet.write('Z%s' % row, actual_unit , wbf['content_bg'])
            worksheet.write('AA%s' % row, actual_customer , wbf['content_bg'])
            worksheet.write('AB%s' % row, loc_src , wbf['content'])
            worksheet.write('AC%s' % row, status_detail , wbf['content'])

            
            total_display_unit += display_unit
            total_target_unit += target_unit 
            total_target_customer += target_customer
            total_act_unit += actual_unit if actual_unit !=  None else 0
            total_act_customer += actual_customer if actual_customer !=  None else 0

            no += 1 
            row += 1     

        worksheet.autofilter('A6:AC%s' % (row)) 
        worksheet.freeze_panes(6, 6)

        worksheet.merge_range('A%s:V%s' % (row,row), '', wbf['total'])    
        
        formula_display_unit = '{=subtotal(9,W%s:W%s)}' % (row1, row-1) 
        formula_target_unit = '{=subtotal(9,X%s:X%s)}' % (row1, row-1) 
        formula_target_customer = '{=subtotal(9,Y%s:Y%s)}' % (row1, row-1) 
        formula_act_unit = '{=subtotal(9,Z%s:Z%s)}' % (row1, row-1) 
        formula_act_customer = '{=subtotal(9,AA%s:AA%s)}' % (row1, row-1) 
        
        worksheet.write_formula(row-1,22,formula_display_unit, wbf['total_float'], total_display_unit)
        worksheet.write_formula(row-1,23,formula_target_unit, wbf['total_float'], total_target_unit)
        worksheet.write_formula(row-1,24,formula_target_customer, wbf['total_float'], total_target_customer)
        worksheet.write_formula(row-1,25,formula_act_unit, wbf['total_float'], total_act_unit)
        worksheet.write_formula(row-1,26,formula_act_customer, wbf['total_float'], total_act_customer)
        
        worksheet.merge_range('AB%s:AC%s'% (row,row), '', wbf['total'])
        

        worksheet.merge_range('A%s:B%s'%(row+2,row+2), '%s %s' % (str(date2),user) , wbf['footer']) 

        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write({'state_x':'get', 'name': filename,'data_x':out})
        fp.close()

        res = self.env.ref('teds_sales_activity_plan_btl.view_teds_sales_activity_report_wizard', False)

        form_id = res and res.id or False

        return {
            'name': ('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.sales.activity.report.wizard',
            'res_id': self.ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }     