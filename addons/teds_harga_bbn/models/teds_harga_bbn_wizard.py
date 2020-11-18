import time
import cStringIO
import xlsxwriter
from cStringIO import StringIO
import base64
import tempfile
import os
from openerp import models, fields, api
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from xlsxwriter.utility import xl_rowcol_to_cell
import logging
import re
import pytz
from lxml import etree
from openerp.exceptions import Warning
import xlrd

class HargaBBNWizard(models.TransientModel):
    _name = "teds.harga.bbn.wizard"

    @api.model
    def _get_default_date(self): 
        return self.env['wtc.branch'].get_default_date()

    wbf = {}

    state_x = fields.Selection([('choose','choose'),('get','get')], default='choose')
    file = fields.Binary('File')
    date = fields.Date('Date',default=_get_default_date,readonly=True) 
    options = fields.Selection([
        ('upload','Upload'),
        ('download','Download')], 'Options',default='upload') 
    bbn_id = fields.Many2one('wtc.harga.bbn','Harga BBN')
    nama_bbn = fields.Char('Nama Harga BBN')
    tipe_plat = fields.Selection([
        ('H','Hitam'),
        ('M','Merah')],default='H')
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')

    # download
    name = fields.Char('Filename', readonly=True)
    file_download = fields.Binary('File Upload',readonly="1")
    bbn_detail_id = fields.Many2one('wtc.harga.bbn.line',domain="[('bbn_id','=',bbn_id)]",string='Detail Harga BBN')

    @api.onchange('options')
    def onchange_options(self):
        self.tipe_plat = False
        self.start_date = False
        self.end_date = False
        self.file = False
        self.nama_bbn = False
        self.bbn_detail_id = False

    @api.multi
    def action_submit(self):
        if self.options == 'upload':
            return self.action_upload()
        else:
            return self.action_dowload()

    def action_upload(self):
        cek_data_bbn = self.env['wtc.harga.bbn.line'].search([
            ('bbn_id','=',self.bbn_id.id),
            ('active','=',True),
            ('start_date','<=',self._get_default_date()),
            ('end_date','>=',self._get_default_date())])
        if cek_data_bbn:
            raise Warning('You cannot have 2 pricelist versions that overlap!')

        data = base64.decodestring(self.file)
        excel = xlrd.open_workbook(file_contents = data)  
        sh = excel.sheet_by_index(0)
        ids = []
        product = {}
        city = {}

        for rx in range(1,sh.nrows): 
            prod_code = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [0]
            city_code = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [1]
            notice = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [3]
            proses = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [4]
            jasa = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [5]
            jasa_area = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [6]
            fee_pusat = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [7]
            total = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [8]
            
            prod_obj = False
            city_obj = False

            if not product.get(prod_code):
                prod_obj = self.env['product.template'].sudo().search([('name','=',prod_code)],limit=1).id
                if not prod_obj:
                    raise Warning('Product %s tidak ada di master !'%(prod_code))
            else:
                prod_obj = product[prod_code] 

            if not city.get(city_code):
                city_obj = self.env['wtc.city'].sudo().search([('code','=',city_code)],limit=1).id
                if not city_obj:
                    raise Warning('City %s tidak ada di master !'%(city_code))
            else:
                city_obj = city[city_code] 

            ids.append([0,False,{
                'product_template_id':prod_obj,
                'city_id':city_obj,
                'notice':notice,
                'proses':proses,
                'jasa':jasa,
                'jasa_area':jasa_area,
                'fee_pusat':fee_pusat,
                'total':total
            }])

        bbn_detail = self.env['wtc.harga.bbn.line'].create({    
            'name':self.nama_bbn,
            'tipe_plat':self.tipe_plat,
            'active':True,
            'start_date':self.start_date,
            'end_date':self.end_date,
            'bbn_id':self.bbn_id.id
        })
        if bbn_detail:
            bbn_detail.write({'harga_bbn_line_detail_ids':ids})

        self.write({'state_x':'get'})
        form_id = self.env.ref('teds_harga_bbn.view_teds_harga_bbn_wizard').id
    
        return {
            'name': 'Harga BBN Wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.harga.bbn.wizard',
            'res_id': self.ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
            }

    @api.multi
    def add_workbook_format(self, workbook):      
        self.wbf['header'] = workbook.add_format({'bold': 1,'align': 'center','bg_color': '#FFFFDB','font_color': '#000000'})
        self.wbf['header'].set_border()

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

        self.wbf['content_number'] = workbook.add_format({'align': 'center'})
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

    def action_dowload(self):
        bbn_id = self.bbn_id.id
        bbn_detail_id = self.bbn_detail_id
        
        query = """
            SELECT pt.name as product
                , c.code as city_code
                , c.name as city_name
                , hbld.notice
                , hbld.proses
                , hbld.jasa
                , hbld.jasa_area
                , hbld.fee_pusat
                , hbld.total
            FROM wtc_harga_bbn hb 
            INNER JOIN wtc_harga_bbn_line hbl ON hbl.bbn_id = hb.id
            INNER JOIN wtc_harga_bbn_line_detail hbld ON hbld.harga_bbn_line_id = hbl.id
            INNER JOIN product_template pt ON pt.id = hbld.product_template_id
            INNER JOIN wtc_city c ON c.id = hbld.city_id
            WHERE hb.id = %d
            AND hbl.id = %d
        """ %(bbn_id,bbn_detail_id)
        self.env.cr.execute(query)
        ress = self.env.cr.dictfetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)       
        workbook = self.add_workbook_format(workbook)
        wbf = self.wbf
        worksheet = workbook.add_worksheet('Harga BBN')
        worksheet.set_column('A1:A1', 15)
        worksheet.set_column('B1:B1', 13)
        worksheet.set_column('C1:C1', 25)
        worksheet.set_column('D1:D1', 15)
        worksheet.set_column('E1:E1', 15)
        worksheet.set_column('F1:F1', 15)
        worksheet.set_column('G1:G1', 15)
        worksheet.set_column('H1:H1', 15)
        worksheet.set_column('I1:I1', 15)
      
        date = self._get_default_date()
        date = date.strftime("%d-%m-%Y %H:%M:%S")

        filename = str(self.bbn_id.name)+str(date)+'.xlsx'

        row = 1

        worksheet.write('A1', 'Product' , wbf['header'])
        worksheet.write('B1', 'City Code' , wbf['header'])
        worksheet.write('C1', 'City' , wbf['header'])
        worksheet.write('D1', 'Notice' , wbf['header'])
        worksheet.write('E1', 'Proses' , wbf['header'])
        worksheet.write('F1', 'Jasa' , wbf['header'])
        worksheet.write('G1', 'Jasa Area' , wbf['header'])
        worksheet.write('H1', 'Fee Pusat' , wbf['header'])
        worksheet.write('I1', 'Total' , wbf['header'])

        row += 1
        for res in ress:
            product = str(res.get('product').encode('ascii','ignore').decode('ascii')) if res.get('product') != None else ''
            city_code = str(res.get('city_code').encode('ascii','ignore').decode('ascii')) if res.get('city_code') != None else ''
            city_name = str(res.get('city_name').encode('ascii','ignore').decode('ascii')) if res.get('city_name') != None else ''
            notice = res.get('notice')
            proses = res.get('proses')
            jasa = res.get('jasa')
            jasa_area = res.get('jasa_area')
            fee_pusat = res.get('fee_pusat')
            total = res.get('total')

            worksheet.write('A%s' % row, product , wbf['content_number'])                    
            worksheet.write('B%s' % row, city_code , wbf['content'])
            worksheet.write('C%s' % row, city_name , wbf['content'])
            worksheet.write('D%s' % row, notice , wbf['content_float'])
            worksheet.write('E%s' % row, proses , wbf['content_float'])
            worksheet.write('F%s' % row, jasa , wbf['content_float'])
            worksheet.write('G%s' % row, jasa_area , wbf['content_float'])
            worksheet.write('H%s' % row, fee_pusat , wbf['content_float'])  
            worksheet.write('I%s' % row, total , wbf['content_float'])
            row+=1
      
        workbook.close()
        out = base64.encodestring(fp.getvalue())
        self.write({'state_x':'get', 'file_download':out, 'name': filename})
        fp.close()

        form_id = self.env.ref('teds_harga_bbn.view_teds_harga_bbn_wizard').id
        
        return {
            'name': 'Harga BBN Wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.harga.bbn.wizard',
            'res_id': self.ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
            }
