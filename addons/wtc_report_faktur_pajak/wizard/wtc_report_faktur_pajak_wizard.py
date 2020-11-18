import time
from lxml import etree
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



class wtc_report_faktur_pajak(osv.osv_memory):
    _name = 'wtc.report.faktur.pajak'
    _description = 'WTC Report Payment'
    _rec_name = 'option'

    wbf={}

    def _get_branch_ids(self, cr, uid, context=None):
        branch_ids_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
        branch_ids = [b.id for b in branch_ids_user]
        return branch_ids
        
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(wtc_report_faktur_pajak, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        branch_ids_user=self.pool.get('res.users').browse(cr,uid,uid).branch_ids
        branch_ids=[b.id for b in branch_ids_user]
        
        doc = etree.XML(res['arch'])      
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
        for node in nodes_branch:
            node.set('domain', '[("id", "in", '+ str(branch_ids)+')]')
        res['arch'] = etree.tostring(doc)
        return res
    

    def _get_default(self,cr,uid,date=False,user=False,context=None):
        if date :
            return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)
        else :
            return self.pool.get('res.users').browse(cr, uid, uid)
    
    _columns = {
        'state_x': fields.selection( ( ('choose','choose'),('get','get'))), #xls
        'data_x': fields.binary('File', readonly=True),
        'name': fields.char('Filename', 100, readonly=True), 
        'option': fields.selection([
                                    ('faktur_pajak','Faktur Pajak'),
                                    ('generate_faktur_pajak','Generate Faktur Pajak'),
                                    ('faktur_pajak_gabungan','Faktur Pajak Gabungan'),
                                    ('faktur_pajak_others','Faktur Pajak Others'),
                                    ('regenerate_faktur_pajak','Regenerate Faktur Pajak'),
                                    ], 'Option', change_default=True, select=True),
        'pajak_gabungan' : fields.boolean(string="Pajak Gabungan"),
        'model_ids': fields.many2many('ir.model', 'wtc_report_faktur_pajak_model_rel', 'wtc_report_faktur_pajak',
                                        'model_id', 'Form Name', copy=False),
        'state_faktur_pajak' : fields.selection([
                                                  ('open','Open'),
                                                  ('close','Closed'),
                                                  ('print','Printed'),
                                                  ('cancel','Canceled'),
                                                  ],string='State'), 
        'thn_penggunaan' : fields.integer(string="Tahun Penggunaan"),
        'state_generate_faktur_pajak' : fields.selection([
                                                  ('draft','Draft'),
                                                  ('posted','Posted'),
                                                  ],string='State'),  
        'division': fields.selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum')], 'Division', change_default=True, select=True),                 
        'branch_ids': fields.many2many('wtc.branch', 'wtc_report_faktur_pajak_branch_rel', 'wtc_report_faktur_pajak',
                                        'branch_id', 'Branch', copy=False),
        'partner_ids': fields.many2many('res.partner', 'wtc_report_faktur_pajak_partner_rel', 'wtc_report_faktur_pajak',
                                        'partner_id', 'Partner', copy=False),
        'state_gabungan_faktur_pajak' : fields.selection([
                                                    ('draft', 'Draft'),
                                                    ('confirmed', 'Confirmed'),
                                                    ('cancel','Cancelled')
                                                    ],string='State'),    
        'state_other_faktur_pajak' : fields.selection([
                                                  ('draft','Draft'),
                                                  ('posted','Posted'),
                                                  ],string='State'),  
        'state_regenerate_faktur_pajak' : fields.selection([
                                                  ('draft','Draft'),
                                                  ('post','Posted'),
                                                  ],string='State'),                  
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),                                    
    }
    _defaults = {
        'state_x': lambda *a: 'choose',
        'start_date':_get_default,
        'end_date':_get_default,
        'option':'faktur_pajak'
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

        if data['option']  == 'faktur_pajak' :
            self._print_excel_report_faktur_pajak(cr, uid, ids, data, context=context)

        if data['option'] == 'generate_faktur_pajak' :
            self._print_excel_report_faktur_pajak_generate(cr, uid, ids, data, context=context)

        if data['option'] == 'faktur_pajak_gabungan' :
            self._print_excel_report_faktur_pajak_gabungan(cr, uid, ids, data, context=context)

        if data['option'] == 'faktur_pajak_others' :
            self._print_excel_report_faktur_pajak_others(cr, uid, ids, data, context=context)

        if data['option'] == 'regenerate_faktur_pajak' :
            self._print_excel_report_regenerate_faktur_pajak(cr, uid,ids,data,context=context)


   

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_faktur_pajak', 'view_wtc_report_all_faktur_pajak')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.report.faktur.pajak',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }
    

    def _print_excel_report_faktur_pajak(self, cr, uid, ids, data, context=None):  

        model_ids = data['model_ids']
        pajak_gabungan = data['pajak_gabungan']
        partner_ids = data['partner_ids']
        state_faktur_pajak = data['state_faktur_pajak']
        thn_penggunaan = data['thn_penggunaan']
        start_date = data['start_date']
        end_date = data['end_date']
      
                
        where_start_date = " 1=1 "
        if start_date :
            where_start_date = " fpo.date >= '%s'" % str(start_date)
            
        where_end_date = " 1=1 "
        if end_date :
            where_end_date = " fpo.date <= '%s'" % str(end_date)
                            
        where_pajak_gabungan = " 1=1 "
        if pajak_gabungan :
            where_pajak_gabungan = " fpo.pajak_gabungan = 't' "
            
        where_state_faktur_pajak = " 1=1 "
        if state_faktur_pajak :
            where_state_faktur_pajak = " fpo.state = '%s'" % str(state_faktur_pajak)
            
        where_thn_penggunaan = " 1=1 "
        if thn_penggunaan :
            where_thn_penggunaan = " fpo.thn_penggunaan = '%s'" % str(thn_penggunaan)  
                      
        where_model_ids = " 1=1 "
        if model_ids :
            where_model_ids = " m.id in %s" % str(
                tuple(model_ids)).replace(',)', ')')
                
        where_partner_ids = " 1=1 "
        if partner_ids :
            where_partner_ids = " p.id in %s" % str(
                tuple(partner_ids)).replace(',)', ')')
        
        query_faktur_pajak = """
        select 
        fpo.name as code_pajak,
        m.name as form_name,
        fpo.pajak_gabungan as pajak_gabungan,
        p.default_code as partner_code,
        p.name as partner_name,
        fpo.date as date, 
        fpo.untaxed_amount as untaxed_amount,
        fpo.tax_amount as tax_amount,
        fpo.amount_total as amount_total,
        fpo.tgl_terbit as tgl_terbit, 
        fpo.thn_penggunaan as thn_penggunaan,
        fpo.cetak_ke as cetak_ke, 
        fpo.state as state
        from wtc_faktur_pajak_out fpo 
        left join ir_model m ON m.id = fpo.model_id
        left join res_partner p ON p.id = fpo.partner_id
        """
        
        where = "WHERE " + where_start_date +" AND "+ where_end_date +" AND "+ where_pajak_gabungan + " AND " + where_state_faktur_pajak + " AND " + where_thn_penggunaan + " AND " + where_model_ids + " AND " + where_partner_ids
        order = "order by fpo.name, fpo.id"

        cr.execute(query_faktur_pajak + where + order)
        all_lines = cr.fetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Laporan Faktur Pajak')
        worksheet.set_column('B1:B1', 20)
        worksheet.set_column('C1:C1', 20)
        worksheet.set_column('D1:D1', 20)
        worksheet.set_column('E1:E1', 20)
        worksheet.set_column('F1:F1', 15)
        worksheet.set_column('G1:G1', 15)
        worksheet.set_column('H1:H1', 10)
        worksheet.set_column('I1:I1', 10)
        worksheet.set_column('J1:J1', 10)
        worksheet.set_column('K1:K1', 20)    
        worksheet.set_column('L1:L1', 20)
        worksheet.set_column('M1:M1', 20)

        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        filename = 'Laporan Faktur Pajak'+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Laporan Paktur Pajak' , wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])
        

        
        row=5
        rowsaldo = row
        row+=1

        worksheet.write('A%s' % (row+1), 'No' , wbf['header'])
        worksheet.write('B%s' % (row+1), 'Code Pajak' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'Form Name' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'Pajak Gabungan' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'Partner Code' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'Tanggal Transaksi' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'Tanggal Terbit' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'Tahun' , wbf['header'])
        worksheet.write('I%s' % (row+1), 'Cetak Ke' , wbf['header'])
        worksheet.write('J%s' % (row+1), 'State' , wbf['header'])
        worksheet.write('K%s' % (row+1), 'Untaxed Amount' , wbf['header'])
        worksheet.write('L%s' % (row+1), 'Tax Amount' , wbf['header'])
        worksheet.write('M%s' % (row+1), 'Amount Total' , wbf['header'])
           

        row+=2               
        no = 1     
        row1 = row
        
        amount_total= 0
        untaxed_amount = 0
        tax_amount = 0

        for res in all_lines:
           

            code_pajak = res[0]
            form_name  = res[1]
            pajak_gabungan  = res[2]
            partner_code = res[3].encode('ascii','ignore').decode('ascii') if res[3] != None else ''
            partner_name = res[4].encode('ascii','ignore').decode('ascii') if res[4] != None else ''
            date = res[5]
            untaxed_amount = res[6]
            tax_amount = res[7]
            amount_total = res[8]
            tgl_terbit = res[9]
            thn_penggunaan = res[10]
            cetak_ke = res[11]
            state = res[12]

            
            worksheet.write('A%s' % row, no, wbf['content_number'])                    
            worksheet.write('B%s' % row, code_pajak, wbf['content_number'])
            worksheet.write('C%s' % row, form_name, wbf['content'])
            worksheet.write('D%s' % row, pajak_gabungan, wbf['content'])
            worksheet.write('E%s' % row, partner_code, wbf['content'])
            worksheet.write('F%s' % row, date, wbf['content_date'])
            worksheet.write('G%s' % row, tgl_terbit, wbf['content_date'])
            worksheet.write('H%s' % row, thn_penggunaan, wbf['content'])
            worksheet.write('I%s' % row, cetak_ke, wbf['content_number'])
            worksheet.write('J%s' % row, state, wbf['content'])
            worksheet.write('K%s' % row, untaxed_amount, wbf['content_float'])
            worksheet.write('L%s' % row, tax_amount, wbf['content_float'])
            worksheet.write('M%s' % row, amount_total, wbf['content_float'])

            no+=1
            row+=1
                
            untaxed_amount = untaxed_amount
            tax_amount = tax_amount
            amount_total = amount_total

        worksheet.autofilter('A7:J%s' % (row))  
        worksheet.freeze_panes(7, 3)

        #TOTAL
        worksheet.merge_range('A%s:C%s' % (row,row), 'Total', wbf['total'])    
        worksheet.merge_range('D%s:J%s' % (row,row), '', wbf['total'])
        worksheet.write('K%s'%(row), '', wbf['total'])


        formula_total_untaxed_amount = '{=subtotal(9,K%s:K%s)}' % (row1, row-1) 
        formula_total_tax_amount = '{=subtotal(9,L%s:L%s)}' % (row1, row-1) 
        formula_total_amount = '{=subtotal(9,M%s:M%s)}' % (row1, row-1) 

             
        worksheet.write_formula(row-1,10,formula_total_untaxed_amount, wbf['total_float'], untaxed_amount)                  
        worksheet.write_formula(row-1,11,formula_total_tax_amount, wbf['total_float'], tax_amount)
        worksheet.write_formula(row-1,12,formula_total_amount, wbf['total_float'], amount_total) 



        worksheet.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])

        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        return True


wtc_report_faktur_pajak()