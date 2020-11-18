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


class wtc_report_data_konsumen(osv.osv_memory):
    _name='wtc.report.data.konsumen'
    
    wbf={}

    def _get_default(self,cr,uid,date=False,user=False,context=None):
        if date :
            return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)
        else :
            return self.pool.get('res.users').browse(cr, uid, uid)
    
    def _get_branch_ids(self, cr, uid, context=None):
        branch_ids_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
        branch_ids = [b.id for b in branch_ids_user]
        return branch_ids
    
    _columns={
        'state_x': fields.selection( ( ('choose','choose'),('get','get'))), #xls
        'data_x': fields.binary('File', readonly=True),
        'name': fields.char('Filename', 100, readonly=True), 
        'options':fields.selection([('Penjualan Unit','Penjualan Unit')]),
        'start_date':fields.date('Start Date'),
        'end_date':fields.date('End Date'),
        'branch_ids': fields.many2many('wtc.branch', 'wtc_report_data_konsumen_rel', 'wtc_report_data_konsumen_wizard_id','branch_id', 'Branch', copy=False),
    }
    
    _defaults = {
        'state_x': lambda *a: 'choose',
        'start_date':datetime.today(),
        'end_date':datetime.today(),
    }
    
    def add_workbook_format(self, cr, uid, workbook):      
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

        self._print_excel_report_data_konsumen_unit(cr, uid,ids,data,context=context)

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_data_konsumen', 'wtc_report_data_konsumen_view')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.report.data.konsumen',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }
    
    def _print_excel_report_data_konsumen_unit(self, cr, uid, ids, data, context=None):        
        start_date = data['start_date']
        end_date = data['end_date']
        branch_ids = data['branch_ids']
        options = data['options']
        
        tz = '7 hours'
        query_where = ""
        query_saldo_where = ""
        if branch_ids :
            query_where += " AND dso.branch_id in %s " % str(tuple(branch_ids)).replace(',)', ')') 
        if start_date :
            query_where += " AND dso.date_order >= '%s' " % (start_date)
        if end_date :
            query_where += " AND dso.date_order <= '%s' "  % (end_date)

        query="""
            SELECT b.code as branch_code
            , b.name as branch_name 
            , COALESCE(cdb.no_hp,'') as no_hp
            , COALESCE(cdb.name,'') as nama
            , COALESCE(q_gender.name,'') as jenis_kelamin
            , cdb.birtdate as tgl_lahir
            , dso.date_order as tgl_beli
            , COALESCE(q_agama.name,'') as agama
            , COALESCE(p.name_template,'') as tipe 
            , COALESCE(pav.code,'') as warna
            , lot.tgl_penyerahan_stnk
            , lot.tgl_penyerahan_bpkb
            , COALESCE(q_pekerjaan.name,'') as pekerjaan
            , COALESCE(cdb.street || ' ','') || COALESCE(cdb.street2,'') as alamat
            , COALESCE(cdb.rt,'') as rt
            , COALESCE(cdb.rw,'') as rw
            , COALESCE(cdb.kelurahan,'') as kelurahan
            , COALESCE(cdb.kecamatan,'') as kecamatan
            , COALESCE(city.name,'') as kota
            , COALESCE(state.name,'') as propinsi
            , dso.name as no_faktur
            , lot.name as no_mesin
            FROM dealer_sale_order dso 
            INNER JOIN dealer_sale_order_line dsol on dso.id = dsol.dealer_sale_order_line_id 
            INNER JOIN wtc_branch b on dso.branch_id = b.id 
            INNER JOIN wtc_cddb cdb on dso.cddb_id = cdb.id 
            INNER JOIN res_partner rp on dso.partner_id = rp.id
            LEFT JOIN product_product p on dsol.product_id = p.id 
            LEFT JOIN product_attribute_value_product_product_rel pavpp ON p.id = pavpp.prod_id 
            LEFT JOIN product_attribute_value pav ON pavpp.att_id = pav.id 
            LEFT JOIN stock_production_lot lot on dsol.lot_id = lot.id
            LEFT JOIN wtc_questionnaire q_gender on cdb.jenis_kelamin_id = q_gender.id
            LEFT JOIN wtc_questionnaire q_agama on cdb.agama_id = q_agama.id
            LEFT JOIN wtc_questionnaire q_pekerjaan on cdb.pekerjaan_id = q_pekerjaan.id
            LEFT JOIN wtc_city city on city.id = cdb.city_id
            LEFT JOIN res_country_state state on state.id = cdb.state_id
            WHERE dso.state in ('progress', 'done')
            %s
            """ % (query_where)
    
        cr.execute (query)
        ress = cr.fetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('%s' %(options)) 
        worksheet.set_column('B1:B1', 15)
        worksheet.set_column('C1:C1', 25)
        worksheet.set_column('D1:D1', 20)
        worksheet.set_column('E1:E1', 40)
        worksheet.set_column('F1:F1', 20)
        worksheet.set_column('G1:G1', 10)
        worksheet.set_column('H1:H1', 10)
        worksheet.set_column('I1:I1', 10)
        worksheet.set_column('J1:J1', 10)
        worksheet.set_column('K1:K1', 10)    
        worksheet.set_column('L1:L1', 15)    
        worksheet.set_column('M1:M1', 15)    
        worksheet.set_column('N1:N1', 25)    
        worksheet.set_column('O1:O1', 35)    
        worksheet.set_column('P:P', 5)    
        worksheet.set_column('Q:Q', 5)    
        worksheet.set_column('R:R', 20)    
        worksheet.set_column('S:S', 25)    
        worksheet.set_column('T:T', 25)    
        worksheet.set_column('U:U', 15) 
        worksheet.set_column('V:V', 20) 
        worksheet.set_column('W:W', 20) 
        
        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        filename = 'Report Data Konsumen '+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report Data Konsumen (%s)' %(options) , wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])

        row=4
        col=0
        worksheet.write(row+1, col, 'No' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Branch Code' , wbf['header'])
        col+=1
        worksheet.write(row+1, col, 'Branch Name' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'No HP' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Nama' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Jenis Kelamin' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Tgl Lahir' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Tgl Beli' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Agama' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Tipe' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Color' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Tgl Penyerahan STNK' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Tgl Penyerahan BPKB' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Pekerjaan' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Alamat' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'RT' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'RW' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Kelurahan' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Kecamatan' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Kota' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'Propinsi' , wbf['header'])
        col+=1
        worksheet.write(row+1, col,  'No Faktur' , wbf['header'])    
        col+=1
        worksheet.write(row+1, col,  'No Mesin' , wbf['header'])    
         
        row+=2               
        no = 1     
        row1 = row
        
        for res in ress:
            branch_code=res[0]
            branch_name=res[1]
            nohp=res[2]
            nama=res[3]
            jenis_kelamin=res[4]
            tgl_lahir=res[5]
            tgl_beli=res[6]
            agama=res[7]
            tipe=res[8]
            warna=res[9]
            tgl_penyerahan_stnk=res[10]
            tgl_penyerahan_bpkb=res[11]
            pekerjaan=res[12]
            alamat=res[13]
            rt=res[14]
            rw=res[15]
            kelurahan=res[16]
            kecamatan=res[17]
            kota=res[18]
            propinsi=res[19]
            no_faktur=res[20]
            no_mesin=res[21]

            col=0
            worksheet.write(row, col, no , wbf['content_number'])
            col+=1
            worksheet.write(row, col, branch_code , wbf['content'])
            col+=1
            worksheet.write(row, col, branch_name , wbf['content'])
            col+=1
            worksheet.write(row, col, nohp , wbf['content'])
            col+=1
            worksheet.write(row, col, nama , wbf['content'])
            col+=1
            worksheet.write(row, col, jenis_kelamin , wbf['content'])
            col+=1
            worksheet.write(row, col, tgl_lahir , wbf['content_date'])
            col+=1
            worksheet.write(row, col, tgl_beli , wbf['content'])
            col+=1
            worksheet.write(row, col, agama, wbf['content'])
            col+=1
            worksheet.write(row, col, tipe , wbf['content'])
            col+=1
            worksheet.write(row, col, warna , wbf['content'])
            col+=1
            worksheet.write(row, col, tgl_penyerahan_stnk , wbf['content'])
            col+=1
            worksheet.write(row, col, tgl_penyerahan_bpkb , wbf['content'])
            col+=1
            worksheet.write(row, col, pekerjaan , wbf['content'])
            col+=1
            worksheet.write(row, col, alamat , wbf['content_float'])
            col+=1
            worksheet.write(row, col, rt , wbf['content_float'])
            col+=1
            worksheet.write(row, col, rw , wbf['content_float'])
            col+=1
            worksheet.write(row, col, kelurahan , wbf['content'])
            col+=1
            worksheet.write(row, col, kecamatan , wbf['content'])
            col+=1
            worksheet.write(row, col, kota , wbf['content'])
            col+=1
            worksheet.write(row, col, propinsi , wbf['content'])
            col+=1
            worksheet.write(row, col, no_faktur , wbf['content'])
            col+=1
            worksheet.write(row, col, no_mesin , wbf['content'])

            no+=1
            row+=1
                
        worksheet.autofilter('A5:R%s' % (row))  
        worksheet.freeze_panes(5, 3)
        worksheet.write('A%s'%(row+2), 'Create By: %s %s' % (user,str(date)) , wbf['footer'])  

        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        # return true

wtc_report_data_konsumen()