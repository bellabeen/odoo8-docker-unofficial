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

class wtc_report_pembelian(osv.osv_memory):
   
    _name = "wtc.report.pembelian.wizard"
    _description = "Pembelian Report"

    wbf = {}

    def _get_default(self,cr,uid,date=False,user=False,context=None):
        if date :
            return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)
        else :
            return self.pool.get('res.users').browse(cr, uid, uid)
        
    def _get_branch_ids(self, cr, uid, context=None):
        branch_ids_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
        branch_ids = [b.id for b in branch_ids_user]
        return branch_ids
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(wtc_report_pembelian, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        branch_ids_user=self.pool.get('res.users').browse(cr,uid,uid).branch_ids
        branch_ids=[b.id for b in branch_ids_user]
        
        doc = etree.XML(res['arch'])      
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
        for node in nodes_branch:
            node.set('domain', '[("id", "in", '+ str(branch_ids)+')]')
        res['arch'] = etree.tostring(doc)
        return res
    
    def division_change(self, cr, uid, ids, division, context=None):
        value = {}
        domain = {}
        value['product_ids'] = False
        obj_categ = self.pool.get('product.category')
        all_categ = obj_categ.search(cr,uid,[])
        categ_ids = obj_categ.get_child_ids(cr, uid, all_categ, division)
        domain['product_ids'] = [('categ_id','in',categ_ids)]
        return {'value':value, 'domain':domain}
        
    _columns = {
        'state_x': fields.selection( ( ('choose','choose'),('get','get'))), #xls
        'data_x': fields.binary('File', readonly=True),
        'name': fields.char('Filename', 100, readonly=True), 
        'options': fields.selection([('pembelian','Pembelian'),('consolidate','Consolidate Invoice')], 'Options', change_default=True, select=True), 
        'division': fields.selection([('Sparepart','Sparepart'),('Unit','Unit'),('Umum','Umum')], 'Division'),
        'state': fields.selection([('open','Open'), ('paid','Paid'), ('open_paid','Open and Paid')], 'State', change_default=True, select=True),
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'product_ids': fields.many2many('product.product', 'wtc_report_pembelian_product_rel', 'wtc_report_pembelian_wizard_id',
            'product_id', 'Products'),
        'branch_ids': fields.many2many('wtc.branch', 'wtc_report_pembelian_branch_rel', 'wtc_report_pembelian_wizard_id',
            'branch_id', 'Branches', copy=False),
        'partner_ids': fields.many2many('res.partner', 'wtc_report_pembelian_partner_rel', 'wtc_report_pembelian_wizard_id',
            'partner_id', 'Suppliers', copy=False, domain=[('supplier','=',True)]),        
    }

    _defaults = {
        'state_x': lambda *a: 'choose',
        'start_date':datetime.today(),
        'end_date':datetime.today(),
        'options':'pembelian'        
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
        if data['options'] == 'consolidate' :
            return self._print_excel_report_consolidate_invoice(cr, uid, ids, data, context=context)
        else :
            return self._print_excel_report(cr, uid, ids, data, context=context)
    
    def _print_excel_report(self, cr, uid, ids, data, context=None):        
        
        division = data['division']
        state = data['state']
        branch_ids = data['branch_ids']
        start_date = data['start_date']
        end_date = data['end_date']
        product_ids = data['product_ids']
        partner_ids = data['partner_ids']
        options = data['options']
                        
        query = """
                select b.code as branch_code,
                res.name as name_partner,
                res.default_code as default_code,
                b.name as branch_name, 
                ai.division as division, 
                ai.number as inv_number, 
                ai.date_invoice as date_invoice, 
                ai.origin as origin, 
                CASE WHEN ai.state = 'open' THEN 'Open' WHEN ai.state = 'done' THEN 'Done' WHEN ai.state IS NULL THEN '' ELSE ai.state END as state, 
                product.name_template as type, 
                COALESCE(pav.code,'') as warna, 
                prod_cat.name as prod_categ_name, 
                ail.quantity as qty, 
                ail.consolidated_qty as consolidated_qty, 
                ail.quantity - ail.consolidated_qty as unconsolidated_qty,
                ail.price_unit as price_unit, 
                ail.discount as discount, 
                ail.discount_amount as disc_amount, 
                ail.price_subtotal / ail.quantity as sales_per_unit, 
                ail.price_subtotal as total_sales,
                COALESCE(ai.discount_cash,0) / tent.total_qty * ail.quantity as discount_cash_avg,
                COALESCE(ai.discount_program,0) / tent.total_qty * ail.quantity as discount_program_avg,
                COALESCE(ai.discount_lain,0) / tent.total_qty * ail.quantity as discount_lain_avg,
                ail.price_subtotal - (COALESCE(ai.discount_cash,0) / tent.total_qty * ail.quantity) - (COALESCE(ai.discount_program,0) / tent.total_qty * ail.quantity) - (COALESCE(ai.discount_lain,0) / tent.total_qty * ail.quantity) as total_dpp,
                (ail.price_subtotal - (COALESCE(ai.discount_cash,0) / tent.total_qty * ail.quantity) - (COALESCE(ai.discount_program,0) / tent.total_qty * ail.quantity) - (COALESCE(ai.discount_lain,0) / tent.total_qty * ail.quantity)) * 0.1 as total_ppn,
                (ail.price_subtotal - (COALESCE(ai.discount_cash,0) / tent.total_qty * ail.quantity) - (COALESCE(ai.discount_program,0) / tent.total_qty * ail.quantity) - (COALESCE(ai.discount_lain,0) / tent.total_qty * ail.quantity)) * 1.1 as total_hutang,
                ai.supplier_invoice_number
                from account_invoice ai inner join account_invoice_line ail on ai.id = ail.invoice_id
                inner join (select tent_ai.id, COALESCE(sum(tent_ail.quantity),0) as total_qty
                from account_invoice tent_ai inner join account_invoice_line tent_ail on tent_ai.id = tent_ail.invoice_id group by tent_ai.id) tent on ai.id = tent.id
                --inner join purchase_order po on ai.origin = po.name
                left join res_partner as res on res.id=ai.partner_id
                left join wtc_branch b on ai.branch_id = b.id
                left join product_product product on product.id = ail.product_id
                left join product_attribute_value_product_product_rel pavpp on pavpp.prod_id = product.id
                left join product_attribute_value pav on pav.id = pavpp.att_id
                left join product_template prod_template on product.product_tmpl_id = prod_template.id
                left join product_category prod_cat on prod_template.categ_id = prod_cat.id         
                """
        query_where = " WHERE ai.type = 'in_invoice' "
        if division :
            query_where += " AND ai.division = '%s'" % str(division)
        if start_date :
            query_where += " AND ai.date_invoice >= '%s'" % str(start_date)
        if end_date :
            query_where += " AND ai.date_invoice <= '%s'" % str(end_date)
        if state in ['open','paid'] :
            query_where += " AND ai.state = '%s'" % str(state)
        else :
            query_where += " AND ai.state in ('open','paid')"
        if branch_ids :
            query_where += " AND ai.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        if product_ids :
            query_where += " AND ail.product_id in %s" % str(
                tuple(product_ids)).replace(',)', ')')
        if partner_ids :
            query_where += " AND ai.partner_id in %s" % str(
                tuple(partner_ids)).replace(',)', ')')
        query_order = "order by b.code, ai.date_invoice"
        
        cr.execute (query+query_where+query_order)
        ress = cr.fetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Pembelian')
        worksheet.set_column('B1:B1', 13)
        worksheet.set_column('C1:C1', 21)
        worksheet.set_column('D1:D1', 25)
        worksheet.set_column('E1:E1', 18)
        worksheet.set_column('F1:F1', 9)
        worksheet.set_column('G1:G1', 21)
        worksheet.set_column('H1:H1', 11)
        worksheet.set_column('I1:I1', 22)
        worksheet.set_column('J1:J1', 7)
        worksheet.set_column('K1:K1', 15)
        worksheet.set_column('L1:L1', 15)
        worksheet.set_column('M1:M1', 17)
        worksheet.set_column('N1:N1', 9)
        worksheet.set_column('O1:O1', 17)
        worksheet.set_column('P1:P1', 20)
        worksheet.set_column('Q1:Q1', 20)
        worksheet.set_column('R1:R1', 20)
        worksheet.set_column('S1:S1', 20)
        worksheet.set_column('T1:T1', 26)
        worksheet.set_column('U1:U1', 20)
        worksheet.set_column('V1:V1', 20)
        worksheet.set_column('W1:W1', 24)
        worksheet.set_column('X1:X1', 20)
        worksheet.set_column('Y1:Y1', 20)
        worksheet.set_column('Z1:Z1', 20)
        worksheet.set_column('AA1:AA1', 20)
        worksheet.set_column('AB1:AB1', 20)
                        
        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        filename = 'Report Pembelian '+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report Pembelian' , wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date),str(end_date)) , wbf['company'])
        row=3
        rowsaldo = row
        row+=1
        worksheet.write('A%s' % (row+1), 'No' , wbf['header'])
        worksheet.write('B%s' % (row+1), 'Branch Code' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'Branch Name' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'Supplier' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'Kode Supplier' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'Division' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'Invoice Number' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'Date' , wbf['header'])
        worksheet.write('I%s' % (row+1), 'PO Number' , wbf['header'])
        worksheet.write('J%s' % (row+1), 'State' , wbf['header'])
        worksheet.write('K%s' % (row+1), 'Type' , wbf['header'])
        worksheet.write('L%s' % (row+1), 'Color' , wbf['header'])
        worksheet.write('M%s' % (row+1), 'Product Category' , wbf['header'])
        worksheet.write('N%s' % (row+1), 'Quantity' , wbf['header'])
        worksheet.write('O%s' % (row+1), 'Consolidated Qty' , wbf['header'])
        worksheet.write('P%s' % (row+1), 'Unconsolidated Qty' , wbf['header'])                
        worksheet.write('Q%s' % (row+1), 'Price Unit' , wbf['header'])
        worksheet.write('R%s' % (row+1), 'Discount 1 (%)' , wbf['header'])
        worksheet.write('S%s' % (row+1), 'Discount 2 (Rp)' , wbf['header'])
        worksheet.write('T%s' % (row+1), 'Gross Purchase (Per Unit)' , wbf['header'])
        worksheet.write('U%s' % (row+1), 'Gross Purchase' , wbf['header'])
        worksheet.write('V%s' % (row+1), 'Discount Cash (Avg)' , wbf['header'])
        worksheet.write('W%s' % (row+1), 'Discount Program (Avg)' , wbf['header'])
        worksheet.write('X%s' % (row+1), 'Discount Lain (Avg)' , wbf['header'])
        worksheet.write('Y%s' % (row+1), 'Total DPP' , wbf['header'])
        worksheet.write('Z%s' % (row+1), 'Total PPN' , wbf['header'])
        worksheet.write('AA%s' % (row+1), 'Total Hutang' , wbf['header'])      
        worksheet.write('AB%s' % (row+1), 'Supplier Invoice Number', wbf['header'])  
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
        row1 = row
        
        for res in ress:
            
            branch_code = str(res[0].encode('ascii','ignore').decode('ascii')) if res[0] != None else ''
            branch_name = str(res[3].encode('ascii','ignore').decode('ascii')) if res[3] != None else ''
            name_partner = str(res[1].encode('ascii','ignore').decode('ascii')) if res[1] != None else ''
            default_code = str(res[2].encode('ascii','ignore').decode('ascii')) if res[2] != None else ''
            division = str(res[4].encode('ascii','ignore').decode('ascii')) if res[4] != None else ''
            inv_number = str(res[5].encode('ascii','ignore').decode('ascii')) if res[5] != None else ''
            date_invoice =  datetime.strptime(res[6], "%Y-%m-%d").date() if res[6] != None else ''
            origin = str(res[7].encode('ascii','ignore').decode('ascii')) if res[7] != None else ''
            state = str(res[8].encode('ascii','ignore').decode('ascii')) if res[8] != None else ''
            type = str(res[9].encode('ascii','ignore').decode('ascii')) if res[9] != None else ''
            warna = str(res[10].encode('ascii','ignore').decode('ascii')) if res[10] != None else ''
            prod_categ_name = str(res[11].encode('ascii','ignore').decode('ascii')) if res[11] != None else ''
            qty = res[12] if res[12] else 0
            consolidated_qty = res[13] if res[13] else 0
            unconsolidated_qty = res[14] if res[14] else 0
            price_unit = res[15] if res[15] else 0
            discount = res[16] / 100 if res[16] else 0 
            disc_amount = res[17] if res[17] else 0
            sales_per_unit = res[18] if res[18] else 0
            total_sales = res[19] if res[19] else 0
            discount_cash_avg = res[20] if res[20] else 0
            discount_program_avg = res[21] if res[21] else 0
            discount_lain_avg = res[22] if res[22] else 0
            total_dpp = res[23] if res[23] else 0
            total_ppn = res[24] if res[24] else 0
            total_hutang = res[25] if res[25] else 0
            supplier_invoice_number = str(res[26].encode('ascii','ignore').decode('ascii')) if res[26] != None else ''
            
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
                            
            worksheet.write('A%s' % row, no , wbf['content_number'])                    
            worksheet.write('B%s' % row, branch_code , wbf['content'])
            worksheet.write('C%s' % row, branch_name , wbf['content'])
            worksheet.write('D%s' % row, name_partner , wbf['content'])
            worksheet.write('E%s' % row, default_code , wbf['content'])
            worksheet.write('F%s' % row, division , wbf['content'])
            worksheet.write('G%s' % row, inv_number , wbf['content'])
            worksheet.write('H%s' % row, date_invoice , wbf['content_date'])  
            worksheet.write('I%s' % row, origin , wbf['content'])
            worksheet.write('J%s' % row, state , wbf['content'])
            worksheet.write('K%s' % row, type , wbf['content'])
            worksheet.write('L%s' % row, warna , wbf['content'])
            worksheet.write('M%s' % row, prod_categ_name , wbf['content'])
            worksheet.write('N%s' % row, qty , wbf['content_number'])
            worksheet.write('O%s' % row, consolidated_qty , wbf['content_number'])
            worksheet.write('P%s' % row, unconsolidated_qty , wbf['content_number'])
            worksheet.write('Q%s' % row, price_unit , wbf['content_float']) 
            worksheet.write('R%s' % row, discount , wbf['content_float'])
            worksheet.write('S%s' % row, disc_amount , wbf['content_float'])
            worksheet.write('T%s' % row, sales_per_unit , wbf['content_float'])
            worksheet.write('U%s' % row, total_sales , wbf['content_float'])
            worksheet.write('V%s' % row, discount_cash_avg , wbf['content_float'])
            worksheet.write('W%s' % row, discount_program_avg , wbf['content_float'])     
            worksheet.write('X%s' % row, discount_lain_avg , wbf['content_float'])
            worksheet.write('Y%s' % row, total_dpp , wbf['content_float'])
            worksheet.write('Z%s' % row, total_ppn , wbf['content_float'])
            worksheet.write('AA%s' % row, total_hutang , wbf['content_float'])
            worksheet.write('AB%s' % row, supplier_invoice_number, wbf['content'])
            no+=1
            row+=1
            
        worksheet.autofilter('A5:AB%s' % (row))  
        worksheet.freeze_panes(5, 3)
        
        #TOTAL
        worksheet.merge_range('A%s:C%s' % (row,row), 'Total', wbf['total'])    
        worksheet.merge_range('D%s:M%s' % (row,row), '', wbf['total']) 
        worksheet.merge_range('Z%s:AA%s' % (row,row), '', wbf['total']) 
                     
        formula_total_qty =  '{=subtotal(9,N%s:N%s)}' % (row1, row-1)
        formula_total_consolidated_qty =  '{=subtotal(9,O%s:O%s)}' % (row1, row-1)
        formula_total_unconsolidated_qty =   '{=subtotal(9,P%s:P%s)}' % (row1, row-1)
        formula_total_price_unit = '{=subtotal(9,Q%s:Q%s)}' % (row1, row-1)
        formula_total_discount =   '{=subtotal(9,R%s:R%s)}' % (row1, row-1)
        formula_total_disc_amount = '{=subtotal(9,S%s:S%s)}' % (row1, row-1)
        formula_total_sales_per_unit =  '{=subtotal(9,T%s:T%s)}' % (row1, row-1)
        formula_total_total_sales =  '{=subtotal(9,U%s:U%s)}' % (row1, row-1)
        formula_total_discount_cash_avg =  '{=subtotal(9,V%s:V%s)}' % (row1, row-1)
        formula_total_discount_program_avg =  '{=subtotal(9,W%s:W%s)}' % (row1, row-1)
        formula_total_discount_lain_avg =  '{=subtotal(9,X%s:X%s)}' % (row1, row-1)
        formula_total_total_dpp =  '{=subtotal(9,Y%s:Y%s)}' % (row1, row-1) 
                 
        worksheet.write_formula(row-1,13,formula_total_qty, wbf['total_number'], total_qty)
        worksheet.write_formula(row-1,14,formula_total_consolidated_qty, wbf['total_number'], total_consolidated_qty)
        worksheet.write_formula(row-1,15,formula_total_unconsolidated_qty, wbf['total_number'], total_unconsolidated_qty)
        worksheet.write_formula(row-1,16,formula_total_price_unit, wbf['total_float'], total_unconsolidated_qty) 
        worksheet.write_formula(row-1,17,formula_total_discount, wbf['total_float'], total_discount)
        worksheet.write_formula(row-1,18,formula_total_disc_amount, wbf['total_float'], total_disc_amount)
        worksheet.write_formula(row-1,19,formula_total_sales_per_unit, wbf['total_float'], total_sales_per_unit)
        worksheet.write_formula(row-1,20,formula_total_total_sales, wbf['total_float'], total_total_sales)
        worksheet.write_formula(row-1,21,formula_total_discount_cash_avg, wbf['total_float'], total_discount_cash_avg)
        worksheet.write_formula(row-1,22,formula_total_discount_program_avg, wbf['total_float'], total_discount_program_avg)
        worksheet.write_formula(row-1,23,formula_total_discount_lain_avg, wbf['total_float'], total_discount_lain_avg)
        worksheet.write_formula(row-1,24,formula_total_total_dpp, wbf['total_float'], total_total_dpp)
                                
        worksheet.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])  
                   
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_pembelian', 'view_report_pembelian_wizard')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.report.pembelian.wizard',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }

wtc_report_pembelian()
