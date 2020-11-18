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

class SalesActivityAnsuransiReportWizard(models.TransientModel):
    _name = "teds.sales.activity.ansuransi.report.wizard"
    
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
    base_price = fields.Float('Base Price',default=15000000)
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

        branch_ids = self.branch_ids
        
        query_where = " WHERE pa.bulan = '%s' AND pa.tahun = '%s' AND sp.is_location = True AND pal.state in ('confirmed','done') "%(self.bulan,self.tahun)
        

        if branch_ids:
            query_where += " AND pa.branch_id IN %s" % str(tuple([b.id for b in self.branch_ids])).replace(',)', ')')
        
        query = """
            SELECT 
            b.code as branch_code
            , b.name as branch_name
            , COALESCE(b.street,'-') ||' Rt.'||COALESCE(b.rt,'-')||' Rw.'||COALESCE(b.rw,'-')||', Kelurahan '||initcap(COALESCE(b.kelurahan,'-'))||', Kecamatan '||initcap(COALESCE(b.kecamatan,'-'))||', '||initcap(COALESCE(c.name,'-'))||', Provinsi '||initcap(COALESCE(cs.name,'-')) as alamat
            , l.name as lokasi
            , COALESCE(pal.street,'-') ||' Rt.'||COALESCE(pal.rt,'-')||' Rw.'||COALESCE(pal.rw,'-')||', Kelurahan '||initcap(COALESCE(kel_act.name,'-'))||', Kecamatan '||initcap(COALESCE(kec_act.name,'-'))||', '||initcap(COALESCE(city_act.name,'-'))||', Provinsi '||initcap(COALESCE(state_act.name,'-')) as alamat_lokasi
            , to_char(pal.start_date, 'DD Mon YYYY') as start_date
            , to_char(pal.end_date, 'DD Mon YYYY') as end_date
            , pal.display_unit
            FROM teds_sales_plan_activity pa
            INNER JOIN teds_sales_plan_activity_line pal ON pal.activity_id = pa.id
            INNER JOIN wtc_branch b ON b.id = pa.branch_id
            INNER JOIN stock_location l ON l.id = pal.location_id
            INNER JOIN teds_act_type_sumber_penjualan sp ON sp.id = pal.act_type_id
            LEFT JOIN wtc_city c ON c.id = b.city_id
            LEFT JOIN res_country_state cs ON cs.id = b.state_id
            INNER JOIN titik_keramaian tk ON tk.id = pal.titik_keramaian_id
            LEFT JOIN wtc_kelurahan kel_act ON kel_act.id = pal.kelurahan_id
            LEFT JOIN wtc_kecamatan kec_act ON kec_act.id = tk.kecamatan_id
            LEFT JOIN wtc_city city_act ON city_act.id = kec_act.city_id
            LEFT JOIN res_country_state state_act ON state_act.id = city_act.state_id
            %s
        """ %(query_where)

        self.env.cr.execute(query)
        ress = self.env.cr.dictfetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)       
        workbook = self.add_workbook_format(workbook)
        wbf = self.wbf
        worksheet = workbook.add_worksheet('Report Ansuransi Activity')

        worksheet.set_column('A1:A1', 20)
        worksheet.set_column('B1:B1', 25)
        worksheet.set_column('C1:C1', 35)
        worksheet.set_column('D1:D1', 28)
        worksheet.set_column('E1:E1', 35)
        worksheet.set_column('F1:F1', 13)
        worksheet.set_column('G1:G1', 13)
        worksheet.set_column('H1:H1', 15)
        
        month = self.bulan
        month_str = (calendar.month_name[int(month)])
        tahun = self.tahun
        date_now = self._get_default_date()
        date1 = date_now.strftime("%d-%m-%Y %H:%M:%S")
        date2 = date_now.strftime("%d-%m-%Y")
        user_id = self.env['res.users'].search([('id','=',self._uid)])
        user = user_id.name 
        company = user_id.company_id.name
        filename = 'Report Ansuransi Activity' + str(date1)+'.xlsx'

        worksheet.write('A1', 'Report Pameran TDM' , wbf['company'])
        worksheet.write('A2', 'Per %s %s'%(month_str,tahun) , wbf['company'])

        row=3
        worksheet.write('A%s' % (row+1), 'Induk Lokasi' , wbf['header_left'])
        worksheet.write('B%s' % (row+1), 'Cabang Induk' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'Alamat Cabang Induk' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'Nama Lokasi' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'Alamat' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'Awal' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'Akhir' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'Nilai' , wbf['header'])
        
        row+=2       
        row1=row
        no = 1
        if ress == []:
            worksheet.merge_range('A%s:H%s' % (row,row), 'Data tidak ada !' , wbf['content'])

        for res in ress:
            branch_code = str(res.get('branch_code').encode('ascii','ignore').decode('ascii'))
            branch_name = str(res.get('branch_name').encode('ascii','ignore').decode('ascii'))
            alamat = str(res.get('alamat'))
            lokasi = str(res.get('lokasi'))
            alamat_lokasi = str(res.get('alamat_lokasi'))
            start_date = str(res.get('start_date'))
            end_date = str(res.get('end_date'))
            display_unit = res.get('display_unit')
            nilai = display_unit * self.base_price
            
            worksheet.write('A%s' % row, branch_code , wbf['content_left']) 
            worksheet.write('B%s' % row, branch_name , wbf['content']) 
            worksheet.write('C%s' % row, alamat , wbf['content']) 
            worksheet.write('D%s' % row, lokasi , wbf['content'])
            worksheet.write('E%s' % row, alamat_lokasi , wbf['content'])
            worksheet.write('F%s' % row, start_date , wbf['content'])
            worksheet.write('G%s' % row, end_date , wbf['content'])
            worksheet.write('H%s' % row, nilai , wbf['content'])
            
            no += 1 
            row += 1     

        worksheet.autofilter('A4:H%s' % (row)) 
        worksheet.freeze_panes(4, 2)

        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write({'state_x':'get', 'name': filename,'data_x':out})
        fp.close()

        res = self.env.ref('teds_sales_activity_plan_btl.view_teds_sales_activity_ansuransi_report_wizard', False)

        form_id = res and res.id or False

        return {
            'name': ('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.sales.activity.ansuransi.report.wizard',
            'res_id': self.ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }     