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

class wtc_report_intransit_beli(osv.osv_memory):
   
    _name = "wtc.report.intransit.beli"
    _description = "Intransit Beli Report"

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
        res = super(wtc_report_intransit_beli, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        branch_ids_user=self.pool.get('res.users').browse(cr,uid,uid).branch_ids
        branch_ids=[b.id for b in branch_ids_user]
        
        doc = etree.XML(res['arch'])      
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
        for node in nodes_branch:
            node.set('domain', '[("id", "in", '+ str(branch_ids)+')]')
        res['arch'] = etree.tostring(doc)
        return res
    
    _columns = {
        'state_x': fields.selection( ( ('choose','choose'),('get','get'))), #xls
        'data_x': fields.binary('File', readonly=True),
        'name': fields.char('Filename', 100, readonly=True), 
        'options': fields.selection([('detail','Detail per Product'),('ahm-part','Intransit Sparepart AHM')], 'Options', change_default=True, select=True), 
        'division': fields.selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum')], 'Division', change_default=True, select=True),         
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'branch_ids': fields.many2many('wtc.branch', 'wtc_report_intransit_beli_branch_rel', 'wtc_report_intransit_beli',
                                        'branch_id', 'Branch', copy=False),
        'partner_ids': fields.many2many('res.partner', 'wtc_report_intransit_beli_partner_rel', 'wtc_report_intransit_beli',
                                        'partner_id', 'Partner', copy=False),         
    }

    _defaults = {
        'state_x': lambda *a: 'choose',
        'start_date':datetime.today(),
        'end_date':datetime.today(),
        'options':'detail'        
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

        if data['options'] == 'ahm-part' :
            self._print_excel_report_intransit_part_ahm(cr, uid, ids, data, context=context)
        else :
            self._print_excel_report_detail(cr, uid, ids, data, context=context)

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_intransit_beli', 'view_report_intransit_beli')

        form_id = form_res and form_res[1] or False
        return {
            'name': 'Download XLS',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.report.intransit.beli',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }

    def _print_excel_report_detail(self, cr, uid, ids, data, context=None):
        
        branch_ids = data['branch_ids']
        partner_ids = data['partner_ids']
        division = data['division']
        start_date = data['start_date']
        end_date = data['end_date']          
        
        query = """
                select b.code
                , ai.number
                , ai.division
                , ai.date_invoice
                , partner.default_code
                , partner.name as partner_name
                , ai.supplier_invoice_number
                , ai.document_date
                , ai.date_due
                , prod.name_template
                , ail.name
                , ail.quantity
                , ail.price_unit
                , ail.price_unit / 1.1 as nett_sales
                , ail.discount
                , ail.discount_amount
                , ail.price_subtotal / ail.quantity as dpp
                , ail.price_subtotal
                , ail.consolidated_qty
                , ail.price_subtotal / ail.quantity * (ail.quantity - ail.consolidated_qty) as stock_intransit
                , ai.no_faktur_pajak
                , ai.tgl_faktur_pajak
                from account_invoice ai
                inner join account_invoice_line ail on ai.id = ail.invoice_id
                inner join wtc_branch b on b.id = ai.branch_id
                left join res_partner partner on partner.id = ai.partner_id
                left join product_product prod on prod.id = ail.product_id         
                """
        query_where = """ 
                where ai.division in ('Unit', 'Sparepart')
                and ai.state = 'open'
                and ai.type = 'in_invoice'
                and ai.tipe = 'purchase'
                and ail.quantity != ail.consolidated_qty """
                        
        if branch_ids :
            query_where += " and b.id in %s " % str(tuple(branch_ids)).replace(',)', ')')               
        if partner_ids :
            query_where += " and partner.id  in %s " % str(tuple(partner_ids)).replace(',)', ')')
        if division :
            query_where += " and ai.division = '%s' " % division                             
        if start_date :
            query_where += " and ai.date_invoice >= '%s' " % start_date
        if end_date :
            query_where += " and ai.date_invoice <= '%s' " % end_date 
                   
        query_order = " order by b.code, ai.date_invoice, ai.number "
        
        cr.execute (query+query_where+query_order)
        ress = cr.fetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Intransit Beli')
        worksheet.set_column('B1:B1', 13)
        worksheet.set_column('C1:C1', 21)
        worksheet.set_column('D1:D1', 9)
        worksheet.set_column('E1:E1', 12)
        worksheet.set_column('F1:F1', 18)
        worksheet.set_column('G1:G1', 21)
        worksheet.set_column('H1:H1', 25)
        worksheet.set_column('I1:I1', 12)
        worksheet.set_column('J1:J1', 12)
        worksheet.set_column('K1:K1', 17)
        worksheet.set_column('L1:L1', 20)
        worksheet.set_column('M1:M1', 12)
        worksheet.set_column('N1:N1', 20)
        worksheet.set_column('O1:O1', 20)
        worksheet.set_column('P1:P1', 12)
        worksheet.set_column('Q1:Q1', 20)
        worksheet.set_column('R1:R1', 20)
        worksheet.set_column('S1:S1', 20)
        worksheet.set_column('T1:T1', 15)
        worksheet.set_column('U1:U1', 20)
        worksheet.set_column('V1:V1', 15)
        worksheet.set_column('W1:W1', 16)
                
        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        filename = 'Report Intransit Beli '+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report Intransit Beli' , wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date),str(end_date)) , wbf['company'])
        row=4
        rowsaldo = row
        row+=1
        worksheet.merge_range('A%s:A%s' % (row,(row+1)), 'No' , wbf['header_no'])
        worksheet.merge_range('B%s:O%s' % (row,row), 'Invoice' , wbf['header'])        
        worksheet.write('A%s' % (row+1), 'No' , wbf['header'])
        worksheet.write('B%s' % (row+1), 'Branch' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'Number' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'Division' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'Date Invoice' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'Partner Code' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'Partner Name' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'Supplier Invoice Number' , wbf['header'])
        worksheet.write('I%s' % (row+1), 'Document Date' , wbf['header'])
        worksheet.write('J%s' % (row+1), 'Date Due' , wbf['header'])
        worksheet.merge_range('K%s:U%s' % (row,row), 'Lines' , wbf['header']) 
        worksheet.write('K%s' % (row+1), 'Product Code' , wbf['header'])
        worksheet.write('L%s' % (row+1), 'Product Name' , wbf['header'])
        worksheet.write('M%s' % (row+1), 'Quantity' , wbf['header'])
        worksheet.write('N%s' % (row+1), 'Price Unit' , wbf['header'])
        worksheet.write('O%s' % (row+1), 'Nett Sales' , wbf['header'])
        worksheet.write('P%s' % (row+1), 'Discount' , wbf['header'])                
        worksheet.write('Q%s' % (row+1), 'Discount Amount' , wbf['header'])
        worksheet.write('R%s' % (row+1), 'DPP' , wbf['header'])
        worksheet.write('S%s' % (row+1), 'Sub Total' , wbf['header'])
        worksheet.write('T%s' % (row+1), 'Consolidate Qty' , wbf['header'])
        worksheet.write('U%s' % (row+1), 'Stock Intransit' , wbf['header'])
        worksheet.merge_range('V%s:W%s' % (row,row), 'Faktur Pajak' , wbf['header'])        
        worksheet.write('V%s' % (row+1), 'No Faktur Pajak' , wbf['header'])
        worksheet.write('W%s' % (row+1), 'Tgl Faktur Pajak' , wbf['header'])
        row+=2 
                
        no = 1
        total_net_sales =0
        total_subtotal = 0
        total_consolidated_qty = 0
        total_stock_intransit = 0        
        row1 = row
        branch_code = False
        
        for res in ress:
#             if branch_code != res[0] :
#                 worksheet.write('B%s' % row, "SUBTOTAL %s" % branch_code , wbf['lr'])
#                 row += 2
#                 no = 1
            
            branch_code = res[0]
            invoice_number = res[1]
            division = res[2]
            date_invoice = datetime.strptime(res[3], "%Y-%m-%d").date() if res[3] else ''
            partner_code = res[4]
            partner_name = res[5]
            supp_inv_number = res[6]
            document_date = datetime.strptime(res[7], "%Y-%m-%d").date() if res[7] else ''
            date_due = datetime.strptime(res[8], "%Y-%m-%d").date() if res[8] else ''
            product_code = res[9]
            product_name = res[10]
            quantity = res[11]
            price_unit = res[12]
            nett_sales = res[13]
            discount = res[14] / 100 if res[14] else 0
            discount_amount = res[15]
            dpp = res[16]
            price_subtotal = res[17]
            consolidated_qty = res[18]
            stock_intransit = res[19]
            no_faktur_pajak = res[20]
            tgl_faktur_pajak = datetime.strptime(res[21], "%Y-%m-%d").date() if res[21] else ''
            
            total_net_sales += total_net_sales
            total_subtotal += total_subtotal
            total_consolidated_qty += total_consolidated_qty
            total_stock_intransit += total_stock_intransit  
                            
            worksheet.write('A%s' % row, no , wbf['content_number'])                    
            worksheet.write('B%s' % row, branch_code , wbf['content'])
            worksheet.write('C%s' % row, invoice_number , wbf['content'])
            worksheet.write('D%s' % row, division , wbf['content'])
            worksheet.write('E%s' % row, date_invoice , wbf['content_date'])
            worksheet.write('F%s' % row, partner_code , wbf['content'])
            worksheet.write('G%s' % row, partner_name , wbf['content'])
            worksheet.write('H%s' % row, supp_inv_number , wbf['content_date'])  
            worksheet.write('I%s' % row, document_date , wbf['content_date'])
            worksheet.write('J%s' % row, date_due , wbf['content_date'])
            worksheet.write('K%s' % row, product_code , wbf['content'])
            worksheet.write('L%s' % row, product_name , wbf['content'])
            worksheet.write('M%s' % row, quantity , wbf['content_number'])
            worksheet.write('N%s' % row, price_unit , wbf['content_float'])
            worksheet.write('O%s' % row, nett_sales , wbf['content_float'])
            worksheet.write('P%s' % row, discount , wbf['content_percent'])
            worksheet.write('Q%s' % row, discount_amount , wbf['content_float']) 
            worksheet.write('R%s' % row, dpp , wbf['content_float'])
            worksheet.write('S%s' % row, price_subtotal , wbf['content_float'])
            worksheet.write('T%s' % row, consolidated_qty , wbf['content_number'])
            worksheet.write('U%s' % row, stock_intransit , wbf['content_float'])
            worksheet.write('V%s' % row, no_faktur_pajak , wbf['content_number'])
            worksheet.write('W%s' % row, tgl_faktur_pajak , wbf['content_date'])                      
            no+=1
            row+=1
            
        worksheet.autofilter('A6:Q%s' % (row))  
        worksheet.freeze_panes(6, 3)
        
        #TOTAL
        worksheet.merge_range('A%s:C%s' % (row,row), 'Total', wbf['total'])    
        worksheet.merge_range('D%s:N%s' % (row,row), '', wbf['total']) 
        worksheet.merge_range('P%s:R%s' % (row,row), '', wbf['total'])
        worksheet.merge_range('V%s:W%s' % (row,row), '', wbf['total'])
                     
        formula_nett_sales = '{=subtotal(9,O%s:O%s)}' % (row1, row-1)
        formula_subtotal = '{=subtotal(9,S%s:S%s)}' % (row1, row-1)
        formula_consolidated_qty = '{=subtotal(9,T%s:T%s)}' % (row1, row-1)
        formula_stock_intransit = '{=subtotal(9,U%s:U%s)}' % (row1, row-1)
                 
        worksheet.write_formula(row-1,14,formula_nett_sales, wbf['total_float'], total_net_sales)
        worksheet.write_formula(row-1,18,formula_subtotal, wbf['total_float'], total_subtotal)
        worksheet.write_formula(row-1,19,formula_consolidated_qty, wbf['total_number'], total_consolidated_qty)
        worksheet.write_formula(row-1,20,formula_stock_intransit, wbf['total_float'], total_stock_intransit) 
                
        worksheet.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])  
                   
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        return True
wtc_report_intransit_beli()
