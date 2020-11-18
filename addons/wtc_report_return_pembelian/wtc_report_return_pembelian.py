import time
import cStringIO
import xlsxwriter
from cStringIO import StringIO
import base64
import tempfile
import os
from openerp.osv import osv
from openerp import models, fields, api
from openerp.tools.translate import _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from xlsxwriter.utility import xl_rowcol_to_cell
import logging
import re
import pytz
_logger = logging.getLogger(__name__)
from lxml import etree

class wtc_report_return_pembelian(models.TransientModel):
   
    _name = "wtc.report.return.pembelian.wizard"
    _description = "Return Pembelian Report"

    wbf = {}

    
    def _get_default(self,cr,uid,date=False,user=False,context=None):
        if date :
            return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)
        else :
            return self.pool.get('res.users').browse(cr, uid, uid)

    def _get_branch_ids(self):
        branch_ids_user = self.env['res.users'].browse(self._uid).branch_ids
        branch_ids = [b.id for b in branch_ids_user]
        return branch_ids
    
    @api.multi
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date()

    name = fields.Char('Filename',readonly=True)
    state_x = fields.Selection([('choose','choose'),('get','get')], default='choose')
    data_x = fields.Binary('File', readonly=True)
    options = fields.Selection([('return_pembelian','Retur Pembelian'),('return_penjualan','Retur Penjualan')], 'Options', change_default=True, select=True) 
    division = fields.Selection([('Sparepart','Sparepart'),('Unit','Unit'),('Umum','Umum')], 'Division')
    state = fields.Selection([('draft','Draft'), ('posted','Posted')], 'State', change_default=True, select=True, default='posted')
    start_date = fields.Date('Start Date', default=_get_default_date)
    end_date = fields.Date('End Date', default=_get_default_date)
    branch_ids = fields.Many2many('wtc.branch', 'wtc_report_return_pembelian_branch_rel', 'wtc_report_return_pembelian_wizard_id','branch_id', 'Branches', copy=False)
    partner_ids = fields.Many2many('res.partner', 'wtc_report_return_pembelian_partner_rel', 'wtc_report_return_pembelian_wizard_id','partner_id', 'Suppliers', copy=False)

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


    @api.multi
    def excel_report(self):
        self.ensure_one()

        if len(self['branch_ids']) == 0 :
            self.update({'branch_ids': self._get_branch_ids()})
        if self['options'] == 'return_pembelian' :
            return self._print_excel_report_return_pembelian()
        elif self['options'] == 'return_penjualan' :
            return self._print_excel_report_return_penjualan()
        # else :
        #    return self._print_excel_report(cr, uid, ids, data, context=context)

    def _print_excel_report_return_pembelian(self):
        division = self.division
        state = self.state
        branch_ids = self.branch_ids
        start_date = self.start_date
        end_date = self.end_date
        partner_ids = self.partner_ids
        options = self.options

        query = """
                select b.code as branch_code
                , b.name as branch_name
                , rp.default_code as partner_code
                , rp.name as partner_name
                , rb.division as division
                , rb.date as inv_date
                , ai.number as inv_number
                , CASE WHEN rb.state = 'draft' THEN 'Draft' WHEN rb.state = 'validate' THEN 'Validated' WHEN rb.state = 'waiting_for_approval' THEN 'Waiting Approval' WHEN rb.state = 'approved' THEN 'Approved' WHEN rb.state = 'posted' THEN 'Posted' WHEN rb.state = 'cancel' THEN 'Cancelled' WHEN rb.state = 'reject' THEN 'Rejected' WHEN rb.state IS NULL THEN '' ELSE rb.state END as state
                , product.name_template as tipe
                , COALESCE(pav.code,'') as warna
                , prod_cat.name as prod_categ_name 
                , ail.quantity as qty
                , ail.consolidated_qty as consolidated_qty
                , ail.quantity - ail.consolidated_qty as unconsolidated_qty
                , ail.price_unit as price_unit
                , ail.discount as discount
                , ail.discount_amount as disc_amount
                , ail.price_subtotal / ail.quantity as sales_per_unit
                , ail.price_subtotal as total_sales
                , COALESCE(ai.discount_cash,0) / tent.total_qty * ail.quantity as discount_cash_avg
                , COALESCE(ai.discount_program,0) / tent.total_qty * ail.quantity as discount_program_avg
                , COALESCE(ai.discount_lain,0) / tent.total_qty * ail.quantity as discount_lain_avg
                , ail.price_subtotal - (COALESCE(ai.discount_cash,0) / tent.total_qty * ail.quantity) - (COALESCE(ai.discount_program,0) / tent.total_qty * ail.quantity) - (COALESCE(ai.discount_lain,0) / tent.total_qty * ail.quantity) as total_dpp
                , (ail.price_subtotal - (COALESCE(ai.discount_cash,0) / tent.total_qty * ail.quantity) - (COALESCE(ai.discount_program,0) / tent.total_qty * ail.quantity) - (COALESCE(ai.discount_lain,0) / tent.total_qty * ail.quantity)) * 0.1 as total_ppn
                , (ail.price_subtotal - (COALESCE(ai.discount_cash,0) / tent.total_qty * ail.quantity) - (COALESCE(ai.discount_program,0) / tent.total_qty * ail.quantity) - (COALESCE(ai.discount_lain,0) / tent.total_qty * ail.quantity)) * 1.1 as total_hutang
                , ai2.origin as origin                                
                , ai2.number as number                 
                from wtc_return_pembelian rb 
                left join wtc_branch b on rb.branch_id = b.id 
                left join res_partner rp on rb.supplier_id = rp.id 
                left join account_invoice ai2 on rb.no_faktur = ai2.id
                left join account_invoice ai on rb.id = ai.transaction_id and ai.model_id in (select id from ir_model where model ='wtc.return.pembelian')
                left join account_invoice_line ail on ai.id = ail.invoice_id
                left join (select tent_ai.id, COALESCE(sum(tent_ail.quantity),0) as total_qty
                    from account_invoice tent_ai inner join account_invoice_line tent_ail on tent_ai.id = tent_ail.invoice_id group by tent_ai.id) tent on ai.id = tent.id

                left join wtc_return_pembelian_line rbl on rb.id = rbl.return_pembelian_id
                left join product_product product on rbl.product_id = product.id 
                left join product_attribute_value_product_product_rel pavpp on rbl.product_id = pavpp.prod_id
                left join product_attribute_value pav on pav.id = pavpp.att_id
                left join product_template prod_template on product.product_tmpl_id = prod_template.id
                left join product_category prod_cat on prod_template.categ_id = prod_cat.id         

                """
        query_where = " WHERE 1=1 "
        if division in ['Unit','Sparepart','Umum'] :
            query_where += " AND rb.division = '%s'" % str(division)
        if start_date :
            query_where += " AND rb.date >= '%s'" % str(start_date)
        if end_date :
            query_where += " AND rb.date <= '%s'" % str(end_date)
        # TODO: Tambahin sebanyak state selection
        if state in ['draft','validate','waiting_for_approval','approved','posted','cancel','reject'] :
            query_where += " AND rb.state = '%s'" % str(state)       
        if branch_ids :
            query_where += " AND rb.branch_id in %s" % str(tuple([b.id for b in branch_ids])).replace(',)', ')')
        if partner_ids :
            query_where += " AND rb.supplier_id in %s" % str(tuple([p.id for p in partner_ids])).replace(',)', ')')
     
        query_order = "order by b.code, rb.name, rb.date"

        self.env.cr.execute (query+query_where+query_order)
        ress = self.env.cr.dictfetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Retur Pembelian')
        worksheet.set_column('B1:B1', 17)
        worksheet.set_column('C1:C1', 20)
        worksheet.set_column('D1:D1', 30)
        worksheet.set_column('E1:E1', 19)
        worksheet.set_column('F1:F1', 13)
        worksheet.set_column('G1:G1', 30)
        worksheet.set_column('H1:H1', 30)
        worksheet.set_column('I1:I1', 21)
        worksheet.set_column('J1:J1', 12)
        worksheet.set_column('K1:K1', 13)
        worksheet.set_column('L1:L1', 11)
        worksheet.set_column('M1:M1', 15)
        worksheet.set_column('N1:N1', 21)
        worksheet.set_column('O1:O1', 14)
        worksheet.set_column('P1:P1', 21)
        worksheet.set_column('Q1:Q1', 23)
        worksheet.set_column('R1:R1', 20)
        worksheet.set_column('S1:S1', 20)
        worksheet.set_column('T1:T1', 20)
        worksheet.set_column('U1:U1', 20)
        worksheet.set_column('V1:P1', 20)
        worksheet.set_column('W1:W1', 23)
        worksheet.set_column('X1:X1', 26)
        worksheet.set_column('Y1:Y1', 22)
        worksheet.set_column('Z1:Z1', 20)
        worksheet.set_column('AA1:AA1', 20)
        worksheet.set_column('AB:AB1', 20)
      
        date= self._get_default_date()
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default().company_id.name
        user = self._get_default().name
        
        filename = 'Report Retur Pembelian '+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report Retur Pembelian' , wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date),str(end_date)) , wbf['company'])
        row=3
        rowsaldo = row
        row+=1
        worksheet.write('A%s' % (row+1), 'No' , wbf['header_no'])
        worksheet.write('B%s' % (row+1), 'Branch Code' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'Branch Name' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'Supplier' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'Kode Supplier' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'Division' , wbf['header'])

        worksheet.write('G%s' % (row+1), 'Origin' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'Number' , wbf['header'])



        worksheet.write('I%s' % (row+1), 'Invoice Number' , wbf['header'])
        worksheet.write('J%s' % (row+1), 'Date' , wbf['header'])
        worksheet.write('K%s' % (row+1), 'State' , wbf['header'])
        worksheet.write('L%s' % (row+1), 'Type' , wbf['header'])
        worksheet.write('M%s' % (row+1), 'Warna' , wbf['header'])
        worksheet.write('N%s' % (row+1), 'Product Category' , wbf['header'])
        worksheet.write('O%s' % (row+1), 'Quantity' , wbf['header'])
        worksheet.write('P%s' % (row+1), 'Consolidated Qty' , wbf['header'])
        worksheet.write('Q%s' % (row+1), 'Unconsolidated Qty' , wbf['header'])                
        worksheet.write('R%s' % (row+1), 'Price Unit' , wbf['header'])
        worksheet.write('S%s' % (row+1), 'Discount 1 (%)' , wbf['header'])
        worksheet.write('T%s' % (row+1), 'Discount 2 (Rp)' , wbf['header'])
        worksheet.write('U%s' % (row+1), 'Sales (Per Unit)' , wbf['header'])
        worksheet.write('V%s' % (row+1), 'Total Sales' , wbf['header'])
        worksheet.write('W%s' % (row+1), 'Discount Cash (Avg)' , wbf['header'])
        worksheet.write('X%s' % (row+1), 'Discount Program (Avg)' , wbf['header'])
        worksheet.write('Y%s' % (row+1), 'Discount Lain (Avg)' , wbf['header'])
        worksheet.write('Z%s' % (row+1), 'Total DPP' , wbf['header'])
        worksheet.write('AA%s' % (row+1), 'Total PPN' , wbf['header'])
        worksheet.write('AB%s' % (row+1), 'Total Hutang' , wbf['header'])      
        row+=2 

        no = 1
        total_qty = 0
        total_consolidated_qty = 0
        total_unconsolidated_qty = 0
        total_price_unit = 0
        total_discount = 0
        total_disc_amount = 0
        total_sales_per_unit = 0
        total_total_sales = 0
        total_discount_cash_avg = 0
        total_discount_program_avg = 0
        total_discount_lain_avg = 0
        total_total_dpp = 0       
        total_total_ppn = 0       
        total_total_hutang = 0       
        row1 = row
        
        for res in ress:
            
            branch_code = str(res.get('branch_code').encode('ascii','ignore').decode('ascii')) if res.get('branch_code') != None else ''
            branch_name = str(res.get('branch_name').encode('ascii','ignore').decode('ascii')) if res.get('branch_name') != None else ''
            partner_name = str(res.get('partner_name').encode('ascii','ignore').decode('ascii')) if res.get('partner_name') != None else ''
            partner_code = str(res.get('partner_code').encode('ascii','ignore').decode('ascii')) if res.get('partner_code') != None else ''
            division = str(res.get('division').encode('ascii','ignore').decode('ascii')) if res.get('division') != None else ''
           
            origin =  str(res.get('origin').encode('ascii','ignore').decode('ascii')) if res.get('origin') != None else ''
            number =  str(res.get('number').encode('ascii','ignore').decode('ascii')) if res.get('number') != None else ''

            inv_number = str(res.get('inv_number').encode('ascii','ignore').decode('ascii')) if res.get('inv_number') != None else ''
            date_invoice =  datetime.strptime(res.get('inv_date'), "%Y-%m-%d").date() if res.get('inv_date') != None else ''
            state = str(res.get('state').encode('ascii','ignore').decode('ascii')) if res.get('state') != None else ''
            tipe = str(res.get('tipe').encode('ascii','ignore').decode('ascii')) if res.get('tipe') != None else ''
            warna = str(res.get('warna').encode('ascii','ignore').decode('ascii')) if res.get('warna') != None else ''
            prod_categ_name = str(res.get('prod_categ_name').encode('ascii','ignore').decode('ascii')) if res.get('prod_categ_name') != None else ''
            qty = res.get('qty',0)
            consolidated_qty = res.get('consolidated_qty') if res.get('consolidated_qty') else 0
            unconsolidated_qty = res.get('unconsolidated_qty') if res.get('unconsolidated_qty') else 0
            price_unit = res.get('price_unit',0)
            discount = res.get('discount') / 100 if res.get('discount') else 0 
            disc_amount = res.get('disc_amount') if res.get('disc_amount') else 0
            sales_per_unit = res.get('sales_per_unit') if res.get('sales_per_unit') else 0
            total_sales = res.get('total_sales') if res.get('total_sales') else 0
            discount_cash_avg = res.get('discount_cash_avg') if res.get('discount_cash_avg') else 0
            discount_program_avg = res.get('discount_program_avg') if res.get('discount_program_avg') else 0
            discount_lain_avg = res.get('discount_lain_avg') if res.get('discount_lain_avg') else 0
            total_dpp = res.get('total_dpp') if res.get('total_dpp') else 0
            total_ppn = res.get('total_ppn') if res.get('total_ppn') else 0
            total_hutang = res.get('total_hutang') if res.get('total_hutang') else 0
            
            total_qty += qty
            total_consolidated_qty += consolidated_qty
            total_unconsolidated_qty += unconsolidated_qty
            total_price_unit += price_unit
            total_discount += discount
            total_disc_amount += disc_amount
            total_sales_per_unit += sales_per_unit
            total_total_sales += total_sales
            total_discount_cash_avg += discount_cash_avg
            total_discount_program_avg += discount_program_avg
            total_discount_lain_avg += discount_lain_avg
            total_total_dpp += total_dpp
            total_total_ppn += total_ppn
            total_total_hutang += total_hutang
                            
            worksheet.write('A%s' % row, no , wbf['content_number'])                    
            worksheet.write('B%s' % row, branch_code , wbf['content'])
            worksheet.write('C%s' % row, branch_name , wbf['content'])
            worksheet.write('D%s' % row, partner_name , wbf['content'])
            worksheet.write('E%s' % row, partner_code , wbf['content']) 
            worksheet.write('F%s' % row, division , wbf['content'])

            worksheet.write('G%s' % row, origin , wbf['content'])
            worksheet.write('H%s' % row, number , wbf['content'])

            worksheet.write('I%s' % row, inv_number , wbf['content'])
            worksheet.write('J%s' % row, date_invoice , wbf['content_date'])
            worksheet.write('K%s' % row, state , wbf['content'])
            worksheet.write('L%s' % row, tipe , wbf['content'])
            worksheet.write('M%s' % row, warna , wbf['content'])
            worksheet.write('N%s' % row, prod_categ_name , wbf['content'])
            worksheet.write('O%s' % row, qty , wbf['content_number'])
            worksheet.write('P%s' % row, consolidated_qty , wbf['content_number'])
            worksheet.write('Q%s' % row, unconsolidated_qty , wbf['content_number'])
            worksheet.write('R%s' % row, price_unit , wbf['content_float']) 
            worksheet.write('S%s' % row, discount , wbf['content_float'])
            worksheet.write('T%s' % row, disc_amount , wbf['content_float'])
            worksheet.write('U%s' % row, sales_per_unit , wbf['content_float'])
            worksheet.write('V%s' % row, total_sales , wbf['content_float'])
            worksheet.write('W%s' % row, discount_cash_avg , wbf['content_float'])
            worksheet.write('X%s' % row, discount_program_avg , wbf['content_float'])     
            worksheet.write('Y%s' % row, discount_lain_avg , wbf['content_float'])
            worksheet.write('Z%s' % row, total_dpp , wbf['content_float'])
            worksheet.write('AA%s' % row, total_ppn , wbf['content_float'])
            worksheet.write('AB%s' % row, total_hutang , wbf['content_float'])
            no+=1
            row+=1
        worksheet.autofilter('A5:AB%s' % (row))  
        worksheet.freeze_panes(5, 3)
        
        #TOTAL
        worksheet.merge_range('A%s:C%s' % (row,row), 'Total', wbf['total'])    
        worksheet.merge_range('D%s:N%s' % (row,row), '', wbf['total']) 
        
        formula_total_qty =  '{=subtotal(9,M%s:M%s)}' % (row1, row-1)
        formula_total_consolidated_qty =  '{=subtotal(9,N%s:N%s)}' % (row1, row-1)
        formula_total_unconsolidated_qty =   '{=subtotal(9,O%s:O%s)}' % (row1, row-1)
        formula_total_price_unit = '{=subtotal(9,P%s:P%s)}' % (row1, row-1)
        formula_total_discount =   '{=subtotal(9,Q%s:Q%s)}' % (row1, row-1)
        formula_total_disc_amount = '{=subtotal(9,R%s:R%s)}' % (row1, row-1)
        formula_total_sales_per_unit =  '{=subtotal(9,S%s:S%s)}' % (row1, row-1)
        formula_total_total_sales =  '{=subtotal(9,T%s:T%s)}' % (row1, row-1)
        formula_total_discount_cash_avg =  '{=subtotal(9,U%s:U%s)}' % (row1, row-1)
        formula_total_discount_program_avg =  '{=subtotal(9,V%s:V%s)}' % (row1, row-1)
        formula_total_discount_lain_avg =  '{=subtotal(9,W%s:W%s)}' % (row1, row-1)
        formula_total_total_dpp =  '{=subtotal(9,X%s:X%s)}' % (row1, row-1) 
        formula_total_total_ppn =  '{=subtotal(9,Y%s:Y%s)}' % (row1, row-1) 
        formula_total_total_hutang =  '{=subtotal(9,Z%s:Z%s)}' % (row1, row-1) 
                 
        worksheet.write_formula(row-1,14,formula_total_qty, wbf['total_number'], total_qty)
        worksheet.write_formula(row-1,15,formula_total_consolidated_qty, wbf['total_number'], total_consolidated_qty)
        worksheet.write_formula(row-1,16,formula_total_unconsolidated_qty, wbf['total_number'], total_unconsolidated_qty)
        worksheet.write_formula(row-1,17,formula_total_price_unit, wbf['total_float'], total_price_unit) 
        worksheet.write_formula(row-1,18,formula_total_discount, wbf['total_float'], total_discount)
        worksheet.write_formula(row-1,19,formula_total_disc_amount, wbf['total_float'], total_disc_amount)
        worksheet.write_formula(row-1,20,formula_total_sales_per_unit, wbf['total_float'], total_sales_per_unit)
        worksheet.write_formula(row-1,21,formula_total_total_sales, wbf['total_float'], total_total_sales)
        worksheet.write_formula(row-1,22,formula_total_discount_cash_avg, wbf['total_float'], total_discount_cash_avg)
        worksheet.write_formula(row-1,23,formula_total_discount_program_avg, wbf['total_float'], total_discount_program_avg)
        worksheet.write_formula(row-1,24,formula_total_discount_lain_avg, wbf['total_float'], total_discount_lain_avg)
        worksheet.write_formula(row-1,25,formula_total_total_dpp, wbf['total_float'], total_total_dpp)
        worksheet.write_formula(row-1,26,formula_total_total_ppn, wbf['total_float'], total_total_ppn)
        worksheet.write_formula(row-1,27,formula_total_total_hutang, wbf['total_float'], total_total_hutang)

                                
        worksheet.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])  
                   
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write({'state_x':'get', 'data_x':out, 'name': filename})
        fp.close()

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(self._cr, self._uid, 'wtc_report_return_pembelian', 'view_report_return_pembelian_wizard')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.report.return.pembelian.wizard',
            'res_id': self.ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }


    #laporan return penjualan 
    def _print_excel_report_return_penjualan(self):
        division = self.division
        state = self.state
        branch_ids = self.branch_ids
        start_date = self.start_date
        end_date = self.end_date
        partner_ids = self.partner_ids
        options = self.options

        query = """
                select b.code as branch_code
                , b.name as branch_name
                , rp.default_code as partner_code
                , rp.name as partner_name
                , rpj.division as division
                , rpj.date as inv_date
                , ai.number as inv_number
                , CASE WHEN rpj.state = 'draft' THEN 'Draft' WHEN rpj.state = 'validate' THEN 'Validated' WHEN rpj.state = 'waiting_for_approval' THEN 'Waiting Approval' WHEN rpj.state = 'approved' THEN 'Approved' WHEN rpj.state = 'posted' THEN 'Posted' WHEN rpj.state = 'cancel' THEN 'Cancelled' WHEN rpj.state = 'reject' THEN 'Rejected' WHEN rpj.state IS NULL THEN '' ELSE rpj.state END as state
                , product.name_template as tipe
                , COALESCE(pav.code,'') as warna
                , prod_cat.name as prod_categ_name
                , ail.quantity as qty
                , ail.price_unit as price_unit
                , ail.discount as discount
                , ail.discount_amount as disc_amount
                , ail.price_subtotal / ail.quantity as sales_per_unit
                , ail.price_subtotal as total_sales
                , COALESCE(ai.discount_cash,0) / tent.total_qty * ail.quantity as discount_cash_avg
                , COALESCE(ai.discount_program,0) / tent.total_qty * ail.quantity as discount_program_avg
                , COALESCE(ai.discount_lain,0) / tent.total_qty * ail.quantity as discount_lain_avg
                , ail.price_subtotal - (COALESCE(ai.discount_cash,0) / tent.total_qty * ail.quantity) - (COALESCE(ai.discount_program,0) / tent.total_qty * ail.quantity) - (COALESCE(ai.discount_lain,0) / tent.total_qty * ail.quantity) as total_dpp
                , (ail.price_subtotal - (COALESCE(ai.discount_cash,0) / tent.total_qty * ail.quantity) - (COALESCE(ai.discount_program,0) / tent.total_qty * ail.quantity) - (COALESCE(ai.discount_lain,0) / tent.total_qty * ail.quantity)) * 0.1 as total_ppn
                , (ail.price_subtotal - (COALESCE(ai.discount_cash,0) / tent.total_qty * ail.quantity) - (COALESCE(ai.discount_program,0) / tent.total_qty * ail.quantity) - (COALESCE(ai.discount_lain,0) / tent.total_qty * ail.quantity)) * 1.1 as total_hutang
                , ai2.origin as origin
                , ai2.number as number 
                                 
                from wtc_return_penjualan rpj 
                left join wtc_branch b on rpj.branch_id = b.id 
                left join res_partner rp on rpj.customer_id = rp.id 
                left join account_invoice ai2 on rpj.no_faktur = ai2.id
                left join account_invoice ai on rpj.id = ai.transaction_id 
                and ai.model_id in (select id from ir_model where model = 'wtc.return.penjualan')
                left join account_invoice_line ail on ai.id = ail.invoice_id
                left join (select tent_ai.id, COALESCE(sum(tent_ail.quantity),0) as total_qty
                    from account_invoice tent_ai inner join account_invoice_line tent_ail on tent_ai.id = tent_ail.invoice_id group by tent_ai.id) tent on ai.id = tent.id
                left join wtc_return_penjualan_line rpl on rpj.id = rpl.return_penjualan_id
                left join product_product product on rpl.product_id = product.id 
                left join product_attribute_value_product_product_rel pavpp on rpl.product_id = pavpp.prod_id
                left join product_attribute_value pav on pav.id = pavpp.att_id
                left join product_template prod_template on product.product_tmpl_id = prod_template.id
                left join product_category prod_cat on prod_template.categ_id = prod_cat.id         

                """
        query_where = " WHERE 1=1 "
        if division in ('Unit','Sparepart','Umum'):
            query_where += " AND rpj.division = '%s'" % str(division)
        if start_date :
            query_where += " AND rpj.date >= '%s'" % str(start_date)
        if end_date :
            query_where += " AND rpj.date <= '%s'" % str(end_date)
        if state in ['draft','validate','waiting_for_approval','approved','posted','cancel','reject'] :
            query_where += " AND rpj.state = '%s'" % str(state)
        if branch_ids :
            query_where += " AND rpj.branch_id in %s" % str(tuple([b.id for b in branch_ids])).replace(',)', ')')
        if partner_ids :
            query_where += " AND rpj.customer_id in %s" % str(tuple([p.id for p in partner_ids])).replace(',)', ')')
     
        query_order = "order by b.code, rpj.name, rpj.date"
        self.env.cr.execute (query+query_where+query_order)
        ress = self.env.cr.dictfetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Retur Penjualan')
        worksheet.set_column('B1:B1', 17)
        worksheet.set_column('C1:C1', 20)
        worksheet.set_column('D1:D1', 30)
        worksheet.set_column('E1:E1', 19)
        worksheet.set_column('F1:F1', 13)
        worksheet.set_column('G1:G1', 30)
        worksheet.set_column('H1:H1', 30)
        worksheet.set_column('I1:I1', 21)
        worksheet.set_column('J1:J1', 12)
        worksheet.set_column('K1:K1', 13)
        worksheet.set_column('L1:L1', 11)
        worksheet.set_column('M1:M1', 15)
        worksheet.set_column('N1:N1', 21)
        worksheet.set_column('O1:O1', 14)
        worksheet.set_column('P1:P1', 21)
        worksheet.set_column('Q1:Q1', 23)
        worksheet.set_column('R1:R1', 20)
        worksheet.set_column('S1:S1', 20)
        worksheet.set_column('T1:T1', 20)
        worksheet.set_column('U1:U1', 20)
        worksheet.set_column('V1:P1', 20)
        worksheet.set_column('W1:W1', 23)
        worksheet.set_column('X1:X1', 26)
        worksheet.set_column('Y1:Y1', 22)
        worksheet.set_column('Z1:Z1', 20)
        worksheet.set_column('AA1:AA1', 20)
        worksheet.set_column('AB:AB1', 20)
      
        date= self._get_default_date()
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default().company_id.name
        user = self._get_default().name
        
        filename = 'Report Retur Penjualan '+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report Retur Penjualan' , wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date),str(end_date)) , wbf['company'])
        row=3
        rowsaldo = row
        row+=1
        worksheet.write('A%s' % (row+1), 'No' , wbf['header_no'])
        worksheet.write('B%s' % (row+1), 'Branch Code' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'Branch Name' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'Supplier' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'Kode Supplier' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'Division' , wbf['header'])

        worksheet.write('G%s' % (row+1), 'Origin' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'Number' , wbf['header'])



        worksheet.write('I%s' % (row+1), 'Invoice Number' , wbf['header'])
        worksheet.write('J%s' % (row+1), 'Date' , wbf['header'])
        worksheet.write('K%s' % (row+1), 'State' , wbf['header'])
        worksheet.write('L%s' % (row+1), 'Type' , wbf['header'])
        worksheet.write('M%s' % (row+1), 'Warna' , wbf['header'])
        worksheet.write('N%s' % (row+1), 'Product Category' , wbf['header'])
        worksheet.write('O%s' % (row+1), 'Quantity' , wbf['header'])
        worksheet.write('P%s' % (row+1), 'Consolidated Qty' , wbf['header'])
        worksheet.write('Q%s' % (row+1), 'Unconsolidated Qty' , wbf['header'])                
        worksheet.write('R%s' % (row+1), 'Price Unit' , wbf['header'])
        worksheet.write('S%s' % (row+1), 'Discount 1 (%)' , wbf['header'])
        worksheet.write('T%s' % (row+1), 'Discount 2 (Rp)' , wbf['header'])
        worksheet.write('U%s' % (row+1), 'Sales (Per Unit)' , wbf['header'])
        worksheet.write('V%s' % (row+1), 'Total Sales' , wbf['header'])
        worksheet.write('W%s' % (row+1), 'Discount Cash (Avg)' , wbf['header'])
        worksheet.write('X%s' % (row+1), 'Discount Program (Avg)' , wbf['header'])
        worksheet.write('Y%s' % (row+1), 'Discount Lain (Avg)' , wbf['header'])
        worksheet.write('Z%s' % (row+1), 'Total DPP' , wbf['header'])
        worksheet.write('AA%s' % (row+1), 'Total PPN' , wbf['header'])
        worksheet.write('AB%s' % (row+1), 'Total Hutang' , wbf['header'])      
        row+=2 

        no = 1
        total_qty = 0
        total_consolidated_qty = 0
        total_unconsolidated_qty = 0
        total_price_unit = 0
        total_discount = 0
        total_disc_amount = 0
        total_sales_per_unit = 0
        total_total_sales = 0
        total_discount_cash_avg = 0
        total_discount_program_avg = 0
        total_discount_lain_avg = 0
        total_total_dpp = 0       
        total_total_ppn = 0       
        total_total_hutang = 0       
        row1 = row
        
        for res in ress:
            
            branch_code = str(res.get('branch_code').encode('ascii','ignore').decode('ascii')) if res.get('branch_code') != None else ''
            branch_name = str(res.get('branch_name').encode('ascii','ignore').decode('ascii')) if res.get('branch_name') != None else ''
            partner_name = str(res.get('partner_name').encode('ascii','ignore').decode('ascii')) if res.get('partner_name') != None else ''
            partner_code = str(res.get('partner_code').encode('ascii','ignore').decode('ascii')) if res.get('partner_code') != None else ''
            division = str(res.get('division').encode('ascii','ignore').decode('ascii')) if res.get('division') != None else ''
           
            origin =  str(res.get('origin').encode('ascii','ignore').decode('ascii')) if res.get('origin') != None else ''
            number =  str(res.get('number').encode('ascii','ignore').decode('ascii')) if res.get('number') != None else ''

            inv_number = str(res.get('inv_number').encode('ascii','ignore').decode('ascii')) if res.get('inv_number') != None else ''
            date_invoice =  datetime.strptime(res.get('inv_date'), "%Y-%m-%d").date() if res.get('inv_date') != None else ''
            state = str(res.get('state').encode('ascii','ignore').decode('ascii')) if res.get('state') != None else ''
            tipe = str(res.get('tipe').encode('ascii','ignore').decode('ascii')) if res.get('tipe') != None else ''
            warna = str(res.get('warna').encode('ascii','ignore').decode('ascii')) if res.get('warna') != None else ''
            prod_categ_name = str(res.get('prod_categ_name').encode('ascii','ignore').decode('ascii')) if res.get('prod_categ_name') != None else ''
            qty = res.get('qty',0)
            consolidated_qty = res.get('consolidated_qty') if res.get('consolidated_qty') else 0
            unconsolidated_qty = res.get('unconsolidated_qty') if res.get('unconsolidated_qty') else 0
            price_unit = res.get('price_unit',0)
            discount = res.get('discount') / 100 if res.get('discount') else 0 
            disc_amount = res.get('disc_amount') if res.get('disc_amount') else 0
            sales_per_unit = res.get('sales_per_unit') if res.get('sales_per_unit') else 0
            total_sales = res.get('total_sales') if res.get('total_sales') else 0
            discount_cash_avg = res.get('discount_cash_avg') if res.get('discount_cash_avg') else 0
            discount_program_avg = res.get('discount_program_avg') if res.get('discount_program_avg') else 0
            discount_lain_avg = res.get('discount_lain_avg') if res.get('discount_lain_avg') else 0
            total_dpp = res.get('total_dpp') if res.get('total_dpp') else 0
            total_ppn = res.get('total_ppn') if res.get('total_ppn') else 0
            total_hutang = res.get('total_hutang') if res.get('total_hutang') else 0
            
            total_qty += qty
            total_consolidated_qty += consolidated_qty
            total_unconsolidated_qty += unconsolidated_qty
            total_price_unit += price_unit
            total_discount += discount
            total_disc_amount += disc_amount
            total_sales_per_unit += sales_per_unit
            total_total_sales += total_sales
            total_discount_cash_avg += discount_cash_avg
            total_discount_program_avg += discount_program_avg
            total_discount_lain_avg += discount_lain_avg
            total_total_dpp += total_dpp
            total_total_ppn += total_ppn
            total_total_hutang += total_hutang
                            
            worksheet.write('A%s' % row, no , wbf['content_number'])                    
            worksheet.write('B%s' % row, branch_code , wbf['content'])
            worksheet.write('C%s' % row, branch_name , wbf['content'])
            worksheet.write('D%s' % row, partner_name , wbf['content'])
            worksheet.write('E%s' % row, partner_code , wbf['content']) 
            worksheet.write('F%s' % row, division , wbf['content'])

            worksheet.write('G%s' % row, origin , wbf['content'])
            worksheet.write('H%s' % row, number , wbf['content'])

            worksheet.write('I%s' % row, inv_number , wbf['content'])
            worksheet.write('J%s' % row, date_invoice , wbf['content_date'])
            worksheet.write('K%s' % row, state , wbf['content'])
            worksheet.write('L%s' % row, tipe , wbf['content'])
            worksheet.write('M%s' % row, warna , wbf['content'])
            worksheet.write('N%s' % row, prod_categ_name , wbf['content'])
            worksheet.write('O%s' % row, qty , wbf['content_number'])
            worksheet.write('P%s' % row, consolidated_qty , wbf['content_number'])
            worksheet.write('Q%s' % row, unconsolidated_qty , wbf['content_number'])
            worksheet.write('R%s' % row, price_unit , wbf['content_float']) 
            worksheet.write('S%s' % row, discount , wbf['content_float'])
            worksheet.write('T%s' % row, disc_amount , wbf['content_float'])
            worksheet.write('U%s' % row, sales_per_unit , wbf['content_float'])
            worksheet.write('V%s' % row, total_sales , wbf['content_float'])
            worksheet.write('W%s' % row, discount_cash_avg , wbf['content_float'])
            worksheet.write('X%s' % row, discount_program_avg , wbf['content_float'])     
            worksheet.write('Y%s' % row, discount_lain_avg , wbf['content_float'])
            worksheet.write('Z%s' % row, total_dpp , wbf['content_float'])
            worksheet.write('AA%s' % row, total_ppn , wbf['content_float'])
            worksheet.write('AB%s' % row, total_hutang , wbf['content_float'])
            no+=1
            row+=1
        worksheet.autofilter('A5:AB%s' % (row))  
        worksheet.freeze_panes(5, 3)
        
        #TOTAL
        worksheet.merge_range('A%s:C%s' % (row,row), 'Total', wbf['total'])    
        worksheet.merge_range('D%s:N%s' % (row,row), '', wbf['total']) 
        
        formula_total_qty =  '{=subtotal(9,M%s:M%s)}' % (row1, row-1)
        formula_total_consolidated_qty =  '{=subtotal(9,N%s:N%s)}' % (row1, row-1)
        formula_total_unconsolidated_qty =   '{=subtotal(9,O%s:O%s)}' % (row1, row-1)
        formula_total_price_unit = '{=subtotal(9,P%s:P%s)}' % (row1, row-1)
        formula_total_discount =   '{=subtotal(9,Q%s:Q%s)}' % (row1, row-1)
        formula_total_disc_amount = '{=subtotal(9,R%s:R%s)}' % (row1, row-1)
        formula_total_sales_per_unit =  '{=subtotal(9,S%s:S%s)}' % (row1, row-1)
        formula_total_total_sales =  '{=subtotal(9,T%s:T%s)}' % (row1, row-1)
        formula_total_discount_cash_avg =  '{=subtotal(9,U%s:U%s)}' % (row1, row-1)
        formula_total_discount_program_avg =  '{=subtotal(9,V%s:V%s)}' % (row1, row-1)
        formula_total_discount_lain_avg =  '{=subtotal(9,W%s:W%s)}' % (row1, row-1)
        formula_total_total_dpp =  '{=subtotal(9,X%s:X%s)}' % (row1, row-1) 
        formula_total_total_ppn =  '{=subtotal(9,Y%s:Y%s)}' % (row1, row-1) 
        formula_total_total_hutang =  '{=subtotal(9,Z%s:Z%s)}' % (row1, row-1) 
                 
        worksheet.write_formula(row-1,14,formula_total_qty, wbf['total_number'], total_qty)
        worksheet.write_formula(row-1,15,formula_total_consolidated_qty, wbf['total_number'], total_consolidated_qty)
        worksheet.write_formula(row-1,16,formula_total_unconsolidated_qty, wbf['total_number'], total_unconsolidated_qty)
        worksheet.write_formula(row-1,17,formula_total_price_unit, wbf['total_float'], total_price_unit) 
        worksheet.write_formula(row-1,18,formula_total_discount, wbf['total_float'], total_discount)
        worksheet.write_formula(row-1,19,formula_total_disc_amount, wbf['total_float'], total_disc_amount)
        worksheet.write_formula(row-1,20,formula_total_sales_per_unit, wbf['total_float'], total_sales_per_unit)
        worksheet.write_formula(row-1,21,formula_total_total_sales, wbf['total_float'], total_total_sales)
        worksheet.write_formula(row-1,22,formula_total_discount_cash_avg, wbf['total_float'], total_discount_cash_avg)
        worksheet.write_formula(row-1,23,formula_total_discount_program_avg, wbf['total_float'], total_discount_program_avg)
        worksheet.write_formula(row-1,24,formula_total_discount_lain_avg, wbf['total_float'], total_discount_lain_avg)
        worksheet.write_formula(row-1,25,formula_total_total_dpp, wbf['total_float'], total_total_dpp)
        worksheet.write_formula(row-1,26,formula_total_total_ppn, wbf['total_float'], total_total_ppn)
        worksheet.write_formula(row-1,27,formula_total_total_hutang, wbf['total_float'], total_total_hutang)

                                
        worksheet.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])  
                   
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write({'state_x':'get', 'data_x':out, 'name': filename})
        fp.close()

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(self._cr, self._uid, 'wtc_report_return_pembelian', 'view_report_return_pembelian_wizard')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.report.return.pembelian.wizard',
            'res_id': self.ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }

                


