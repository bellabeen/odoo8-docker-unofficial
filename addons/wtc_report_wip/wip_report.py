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

class wtc_wip_report(models.TransientModel):
   
    _name = "wtc.wo.wip.report"
    _description = "WIP Report"

    def _get_branch_ids(self):
        branch_ids_user = self.env['res.users'].browse(self._uid).branch_ids
        branch_ids = [b.id for b in branch_ids_user]
    
    wbf = {}

    state_x = fields.Selection([('choose','choose'),('get','get')],default="choose")
    data_x = fields.Binary('File', readonly=True)
    name = fields.Char('Filename', readonly=True)
    branch_ids = fields.Many2many('wtc.branch', 'wtc_report_wo_wip_branch_rel', 'wtc_report_wo_wip_wizard_id','branch_id', 'Branch')

    
    def add_workbook_format(self,workbook):      
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
        
        self.wbf['content_percent'] = workbook.add_format({'align': 'right','num_format': '0%'})
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
        if len(self.branch_ids) == 0 :
            self.branch_ids = self._get_branch_ids()
        return self._print_excel_report()
    
    @api.multi
    def _print_excel_report(self):
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)
        
        user = self.env['res.users'].browse(self._uid)
        company_name = user.company_id.name

        date = datetime.now()
        date = date.strftime("%d-%m-%Y %H:%M:%S")

        branch_ids = [b.id for b in self.branch_ids]
        filename = 'Report WIP Work Order'+str(date)+'.xlsx'
        
        workbook = self.add_workbook_format(workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('WIP')
        worksheet.set_column('B1:B1', 12)
        worksheet.set_column('C1:C1', 18)
        worksheet.set_column('D1:D1', 20)
        worksheet.set_column('E1:E1', 14)
        worksheet.set_column('F1:F1', 10)
        worksheet.set_column('G1:G1', 18)
        worksheet.set_column('H1:H1', 17)
        worksheet.set_column('I1:I1', 20)
        worksheet.set_column('J1:J1', 25)
        worksheet.set_column('K1:K1', 15)
        worksheet.set_column('L1:L1', 18)
        worksheet.set_column('M1:M1', 20)
        worksheet.set_column('N1:N1', 13)
        worksheet.set_column('O1:O1', 18)
        worksheet.set_column('P1:P1', 20)
        worksheet.set_column('Q1:Q1', 17)
        worksheet.set_column('R1:R1', 17)
        worksheet.set_column('S1:S1', 17)
        worksheet.set_column('T1:T1', 17)
        worksheet.set_column('U1:U1', 13)
        worksheet.set_column('V1:V1', 23)   
        worksheet.set_column('W1:W1', 23)
        worksheet.set_column('X1:X1', 14)
        worksheet.set_column('Y1:Y1', 14)
        worksheet.set_column('Z1:Z1', 15)
        worksheet.set_column('AA1:AA1', 15)
        worksheet.set_column('AB1:AB1', 15)
        worksheet.set_column('AC1:AC1', 15)
        worksheet.set_column('AD1:AD1', 15)
        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report Work Order WIP' , wbf['title_doc'])
        row=3
        rowsaldo = row
        row+=1
        worksheet.merge_range('A%s:A%s' % (row,(row+1)), 'No' , wbf['header_no'])
        worksheet.merge_range('B%s:P%s' % (row,row), 'Work Order' , wbf['header'])
        worksheet.write('B%s' % (row+1), 'Branch Code' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'Branch Name' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'Name' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'Division' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'Date' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'Type' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'State' , wbf['header'])
        worksheet.write('I%s' % (row+1), 'Partner Code' , wbf['header'])
        worksheet.write('J%s' % (row+1), 'Partner' , wbf['header'])
        worksheet.write('K%s' % (row+1), 'No Polisi' , wbf['header'])
        worksheet.write('L%s' % (row+1), 'No Engine' , wbf['header'])
        worksheet.write('M%s' % (row+1), 'No Chassis' , wbf['header'])
        worksheet.write('N%s' % (row+1), 'Unit Type' , wbf['header'])
        worksheet.write('O%s' % (row+1), 'NIP' , wbf['header'])
        worksheet.write('P%s' % (row+1), 'Mechanic' , wbf['header'])
        worksheet.merge_range('Q%s:T%s' % (row,row), 'Time Log' , wbf['header'])
        worksheet.write('Q%s' % (row+1), 'Start' , wbf['header'])                
        worksheet.write('R%s' % (row+1), 'Break' , wbf['header'])
        worksheet.write('S%s' % (row+1), 'End Break' , wbf['header'])
        worksheet.write('T%s' % (row+1), 'Finish' , wbf['header'])
        worksheet.merge_range('U%s:AB%s' % (row,row), 'Lines' , wbf['header'])
        worksheet.write('U%s' % (row+1), 'Category' , wbf['header'])
        worksheet.write('V%s' % (row+1), 'Product' , wbf['header'])
        worksheet.write('W%s' % (row+1), 'Description' , wbf['header'])
        worksheet.write('X%s' % (row+1), 'Quantity' , wbf['header'])
        worksheet.write('Y%s' % (row+1), 'Price Unit' , wbf['header'])
        worksheet.write('Z%s' % (row+1), 'Nett Sales' , wbf['header'])
        worksheet.write('AA%s' % (row+1), 'Discount' , wbf['header'])
        worksheet.write('AB%s' % (row+1), 'Subtotal' , wbf['header'])
        worksheet.merge_range('AC%s:AD%s' % (row,row), 'Picking' , wbf['header'])
        worksheet.write('AC%s' % (row+1), 'Supply Qty' , wbf['header'])
        worksheet.write('AD%s' % (row+1), 'Stock WIP' , wbf['header'])        
        row+=2            
        
        query_where = " WHERE 1=1"
        if branch_ids :
            query_where += " AND b.id in %s " % str(tuple(branch_ids)).replace(',)', ')')        
        query_where += " AND wo.state in ('waiting_for_approval', 'confirmed', 'approved', 'finished')"

        query = """
            SELECT b.code as branch_code
            , b.name as branch_name
            , wo.name as wo_name
            , wo.division as wo_division
            , wo.date as wo_date
            , CASE WHEN wo.type = 'REG' THEN 'Regular'
                WHEN wo.type = 'WAR' THEN 'Job Return'
                WHEN wo.type = 'CLA' THEN 'Claim'
                WHEN wo.type = 'SLS' THEN 'Part Sales' END as wo_type
            , wo.state as wo_state
            , partner.default_code as partner_code
            , partner.name as partner_no
            , lot.no_polisi as no_polisi
            , lot.name as engine_no
            , lot.chassis_no as no_chassis
            , unit.name_template as unit_type
            , emp.nip as nip
            , res.name as mechanic_name
            , wo.start + interval '7 hours' as start
            , wo.date_break + interval '7 hours' as date_break
            , wo.end_break + interval '7 hours' as end_break
            , wo.finish + interval '7 hours' as finish
            , wol.categ_id as categ_id
            , prod.name_template as product_template
            , pt.description as description
            , wol.product_qty as quantity
            , wol.price_unit as price_unit
            , wol.price_unit / 1.1 * wol.product_qty as nett_sales
            , wol.discount as discount
            , (wol.price_unit * (1 - coalesce(wol.discount,0) / 100)) / 1.1 * wol.product_qty as subtotal
            , coalesce(wol.supply_qty, 0) as supply_qty
            , (wol.price_unit * (1 - coalesce(wol.discount,0) / 100)) / 1.1 * wol.supply_qty as stock_wip
            FROM wtc_work_order wo
            INNER JOIN wtc_work_order_line wol on wo.id = wol.work_order_id
            INNER JOIN wtc_branch b on b.id = wo.branch_id
            LEFT JOIN res_partner partner on partner.id = wo.customer_id
            LEFT JOIN stock_production_lot lot on lot.id = wo.lot_id
            LEFT JOIN product_product unit on unit.id = wo.product_id
            LEFT JOIN res_users mechanic on mechanic.id = wo.mekanik_id
            LEFT JOIN resource_resource res on res.user_id = mechanic.id
            LEFT JOIN hr_employee emp on res.id = emp.resource_id
            LEFT JOIN product_product prod on prod.id = wol.product_id
            LEFT JOIN product_template pt on pt.id = prod.product_tmpl_id
            %s
            ORDER BY b.code,wo.date,wo.name,wol.categ_id
        """ %(query_where)
        self._cr.execute(query)
        ress = self._cr.dictfetchall()

        no = 1
        total_nett_sales =0
        total_stock_wip = 0
        total_quantity = 0
        total_supply_qty = 0
        total_subtotal = 0
        
        row1 = row
        branch_code = False
        
        for res in ress:
            branch_code = res.get('branch_code')
            branch_name = res.get('branch_name')
            wo_name = res.get('wo_name')
            wo_division = res.get('wo_division')
            wo_date = res.get('wo_date')
            wo_type = res.get('wo_type')
            wo_state = res.get('wo_state').replace('_',' ').title() if res.get('wo_state') else ''
            partner_code = res.get('partner_code')
            partner_no = res.get('partner_no')
            no_polisi = res.get('no_polisi')
            engine_no = res.get('engine_no')
            no_chassis = res.get('no_chassis')
            unit_type = res.get('unit_type')
            nip = res.get('nip')
            mechanic_name = res.get('mechanic_name')
            start = res.get('start')
            date_break = res.get('date_break')
            end_break = res.get('end_break')
            finish = res.get('finish')
            categ_id = res.get('categ_id')
            product_template = res.get('product_template')
            description = res.get('description')
            quantity = res.get('quantity')
            price_unit = res.get('price_unit')
            nett_sales = res.get('nett_sales')
            discount = res.get('discount')
            subtotal = res.get('subtotal')
            supply_qty = res.get('supply_qty')
            stock_wip = res.get('stock_wip')
                
            total_nett_sales += nett_sales
            total_stock_wip += stock_wip
            total_quantity += quantity
            total_supply_qty += supply_qty
            total_subtotal += subtotal      
                    
            worksheet.write('A%s' % row, no , wbf['content_number'])                    
            worksheet.write('B%s' % row, branch_code , wbf['content'])
            worksheet.write('C%s' % row, branch_name , wbf['content'])
            worksheet.write('D%s' % row, wo_name , wbf['content'])
            worksheet.write('E%s' % row, wo_division , wbf['content'])
            worksheet.write('F%s' % row, wo_date , wbf['content_date'])
            worksheet.write('G%s' % row, wo_type , wbf['content'])
            worksheet.write('H%s' % row, wo_state , wbf['content'])
            worksheet.write('I%s' % row, partner_code , wbf['content'])  
            worksheet.write('J%s' % row, partner_no , wbf['content'])
            worksheet.write('K%s' % row, no_polisi , wbf['content'])
            worksheet.write('L%s' % row, engine_no , wbf['content'])
            worksheet.write('M%s' % row, no_chassis , wbf['content'])
            worksheet.write('N%s' % row, unit_type , wbf['content'])
            worksheet.write('O%s' % row, nip , wbf['content'])
            worksheet.write('P%s' % row, mechanic_name , wbf['content'])
            worksheet.write('Q%s' % row, start , wbf['content_datetime'])
            worksheet.write('R%s' % row, date_break , wbf['content_datetime'])
            worksheet.write('S%s' % row, end_break , wbf['content_datetime'])
            worksheet.write('T%s' % row, finish , wbf['content_datetime'])
            worksheet.write('U%s' % row, categ_id , wbf['content'])
            worksheet.write('V%s' % row, product_template , wbf['content'])
            worksheet.write('W%s' % row, description , wbf['content'])
            worksheet.write('X%s' % row, quantity , wbf['content_number'])
            worksheet.write('Y%s' % row, price_unit , wbf['content_float'])            
            worksheet.write('Z%s' % row, nett_sales , wbf['content_float'])
            worksheet.write('AA%s' % row, discount , wbf['content_percent'])
            worksheet.write('AB%s' % row, subtotal , wbf['content_float'])
            worksheet.write('AC%s' % row, supply_qty , wbf['content_number'])
            worksheet.write('AD%s' % row, stock_wip , wbf['content_float'])            
            no+=1
            row+=1
            
        worksheet.autofilter('A5:AD%s' % (row))
        worksheet.freeze_panes(5, 3)
        
        #TOTAL
        worksheet.merge_range('A%s:D%s' % (row,row), 'Total', wbf['total'])    
        worksheet.merge_range('E%s:W%s' % (row,row), '', wbf['total']) 
        
        formula_quantity = '{=subtotal(9,X%s:X%s)}' % (row1, row-1)
        formula_nett_sales = '{=subtotal(9,Z%s:Z%s)}' % (row1, row-1)
        formula_subtotal = '{=subtotal(9,AB%s:AB%s)}' % (row1, row-1)
        formula_supply_qty = '{=subtotal(9,AC%s:AC%s)}' % (row1, row-1)
        formula_stock_wip = '{=subtotal(9,AD%s:AD%s)}' % (row1, row-1)
        
        worksheet.write_formula(row-1,23,formula_quantity, wbf['total_number'], total_quantity)
        worksheet.write('Y%s'%(row), '', wbf['total']) 
        worksheet.write_formula(row-1,25,formula_nett_sales, wbf['total_float'], total_nett_sales)
        worksheet.write('AA%s'%(row), '', wbf['total'])
        worksheet.write_formula(row-1,27,formula_subtotal, wbf['total_float'], total_subtotal)
        worksheet.write_formula(row-1,28,formula_supply_qty, wbf['total_number'], total_supply_qty)
        worksheet.write_formula(row-1,29,formula_stock_wip, wbf['total_number'], total_stock_wip)

        worksheet.write('A%s'%(row+2), '%s %s' % (str(date),user.name) , wbf['footer'])  
                   
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write({'state_x':'get', 'data_x':out, 'name': filename})
        fp.close()

        form_id = self.env.ref('wtc_report_wip.wtc_wip_report_view').id
        return {
            'name': ('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.wo.wip.report',
            'res_id': self.ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }

wtc_wip_report()
