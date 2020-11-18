import time
import cStringIO
import xlsxwriter
import xlrd
from cStringIO import StringIO
import base64
import tempfile
import os
from openerp import models, fields, api
from datetime import datetime, timedelta,date
from dateutil.relativedelta import relativedelta
from xlsxwriter.utility import xl_rowcol_to_cell
from openerp.exceptions import Warning
import calendar

class MekanikMitraAbsensiWizard(models.TransientModel):
    _name = "teds.mekanik.mitra.absensi.wizard"
    _rec_name = "state_x"

    def _get_tahun(self):
        return datetime.today().date().year

    wbf = {}

    name = fields.Char('Filename')
    file = fields.Binary('File Excel')
    data_x = fields.Binary('File')
    options = fields.Selection([
        ('Upload','Upload'),
        ('Download','Download')],string="Options")
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
    state_x = fields.Selection([('choose','Choose'),('get','Get')], default='choose')
    branch_ids = fields.Many2many('wtc.branch', 'teds_mekanik_mitra_absensi_rel', 'mitra_id','branch_id', string='Branch')


    @api.onchange('options')
    def onchange_options(self):
        self.file = False

    @api.multi
    def action_submit(self):
        if self.options == 'Upload':
            return self.action_upload()
        elif self.options == 'Download':
            return self.action_download()
    
    
    def action_upload(self):
        data = base64.decodestring(self.file)
        excel = xlrd.open_workbook(file_contents = data)  
        sh = excel.sheet_by_index(0)

        for rx in range(1,sh.nrows): 
            branch_code = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [0]
            mekanik = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [1]
            jml = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [2]
            
            branch_id = self.env['wtc.branch'].sudo().search([('code','=',branch_code)],limit=1)
            if not branch_id:
                raise Warning('Branch code %s tidak ditemukan !'%(branch_code))
            
            employee_id = self.env['hr.employee'].sudo().search([
                ('branch_id','=',branch_id.id),
                ('name','=',mekanik)],limit=1)
            if not employee_id:
                raise Warning('Nama mekanik %s tidak ditemukan !'%(mekanik))

            mekanik_mitra = self.env['teds.master.mekanik.mitra'].sudo().search([
                ('branch_id','=',branch_id.id),
                ('mekanik_id','=',employee_id.id)],limit=1)
            if not mekanik_mitra:
                raise Warning('Mekanik %s tidak ditemukan di data mekanik mitra !'%(mekanik))
            
            histrory_absensi_ids = []

            histrory_absensi_ids.append([0,False,{
                'bulan':self.bulan,
                'tahun':self.tahun,
                'jumlah':jml
            }])
            mekanik_mitra.write({
                'histrory_absensi_ids':histrory_absensi_ids    
            })
        self.state_x = 'get'
            
        res = self.env.ref('teds_report_mekanik_mitra.view_teds_mekanik_mitra_absensi_wizard', False)

        form_id = res and res.id or False

        return {
            'name': ('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.mekanik.mitra.absensi.wizard',
            'res_id': self.ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }     


    @api.multi
    def add_workbook_format(self, workbook):
        self.wbf['header'] = workbook.add_format({'bg_color':'#FFFF00','bold': 1,'align': 'center','font_color': '#000000'})
        self.wbf['header'].set_top(2)
        self.wbf['header'].set_bottom()
        self.wbf['header'].set_left()
        self.wbf['header'].set_right()
        self.wbf['header'].set_font_size(11)
        self.wbf['header'].set_align('vcenter')

        self.wbf['content'] = workbook.add_format({'align': 'left','font_color': '#000000'})
        self.wbf['content'].set_left()
        self.wbf['content'].set_right()
        self.wbf['content'].set_top()
        self.wbf['content'].set_bottom()
        self.wbf['content'].set_font_size(10)                
       
        return workbook

    def action_download(self):
        domain = []
        if self.branch_ids:
            branch = [b.id for b in self.branch_ids]
            branch = tuple(branch)
            domain = [('branch_id','in',branch)]
        
        masters = self.env['teds.master.mekanik.mitra'].sudo().search(domain)
        bulan = int(self.bulan)
        tahun = int(self.tahun)
        nama_bln = calendar.month_name[bulan]

        start_date = date(tahun, bulan, 1)
        end_date = start_date + relativedelta(months=1) - relativedelta(days=1)

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)       
        workbook = self.add_workbook_format(workbook)
        wbf = self.wbf
        worksheet = workbook.add_worksheet('Mekanik Mitra %s %s'%(nama_bln,tahun))

        worksheet.set_column('A1:A1', 10)
        worksheet.set_column('B1:B1', 25)
        worksheet.set_column('C1:C1', 10)
            
        
        filename = 'Absensi Mekanik Mitra %s %s.xlsx'%(nama_bln,tahun)

        worksheet.write('A1', 'Branch' , wbf['header'])
        worksheet.write('B1', 'Mekanik' , wbf['header'])
        worksheet.write('C1', 'Jumlah' , wbf['header'])

        row = 2
        for master in masters:
            hari_kerja = self.get_hari_kerja(master.mekanik_id.user_id,master.branch_id.id,start_date,end_date)

            worksheet.write('A%s' % row, master.branch_id.code , wbf['content']) 
            worksheet.write('B%s' % row, master.mekanik_id.name_related , wbf['content']) 
            worksheet.write('C%s' % row, hari_kerja , wbf['content']) 

            row += 1    

        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write({'state_x':'get', 'name': filename,'data_x':out})
        fp.close()

        res = self.env.ref('teds_report_mekanik_mitra.view_teds_mekanik_mitra_absensi_wizard', False)

        form_id = res and res.id or False

        return {
            'name': ('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.mekanik.mitra.absensi.wizard',
            'res_id': self.ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }     



    def get_hari_kerja(self,user_id,branch_id,start_date,end_date):
        query = """
            SELECT COALESCE(count(DISTINCT(date)),0) as jml
            FROM wtc_work_order
            WHERE branch_id = %d
            AND mekanik_id = %d
            AND date_confirm BETWEEN '%s' AND '%s' 
        """ %(branch_id,user_id,start_date,end_date)
        self._cr.execute(query)
        res = self._cr.fetchone()

        return res[0]

