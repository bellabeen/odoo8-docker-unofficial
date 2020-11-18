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

class wtc_report_mo_fulfillment(osv.osv_memory):
   
    _name = "wtc.report.mo.fulfillment.wizard"
    _description = "Mo Fulfillment Report"

    STATE_SELECTION = [
        ('assigned','Assigned'),
        ('done','Done')
        
    ]

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

    _columns = {
        'state_x': fields.selection( ( ('choose','choose'),('get','get'))), #xls
        'data_x': fields.binary('File', readonly=True),
        'name': fields.char('Filename', 100, readonly=True),

        'division' : fields.selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum')],string='Division' ,required=True, select=True),
        'picking_type_code': fields.selection([('interbranch_in','Interbranch Receipts'),('interbranch_out','Interbranch Deliveries')], 'Picking Type', change_default=True, select=True),
        'state': fields.selection(STATE_SELECTION, string='State'),
        'branch_sender' : fields.many2one('wtc.branch', 'Branch Sender'),
        'branch_receiver' : fields.many2one('wtc.branch', 'Branch Receiver'),
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
     }

    _defaults = {
        'state_x': lambda *a: 'choose',
        'start_date':datetime.today(),
        'end_date':datetime.today(),
        'division' : 'Unit'    
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
        
        self.wbf['header_detail_space'] = workbook.add_format({})
        self.wbf['header_detail_space'].set_left()
        self.wbf['header_detail_space'].set_right()
        self.wbf['header_detail_space'].set_top()
        self.wbf['header_detail_space'].set_bottom()
                
        self.wbf['header_detail'] = workbook.add_format({'bg_color': '#E0FFC2'})
        self.wbf['header_detail'].set_left()
        self.wbf['header_detail'].set_right()
        self.wbf['header_detail'].set_top()
        self.wbf['header_detail'].set_bottom()
                        
        return workbook
        

    def excel_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
            
        data = self.read(cr, uid, ids,context=context)[0] 
        return self._print_excel_report(cr, uid, ids, data, context=context)
    
    def _print_excel_report(self, cr, uid, ids, data, context=None):
        division = data['division']
        state = data['state']
        start_date = data['start_date']
        end_date = data['end_date']     
        picking_type_code = data['picking_type_code'] 
        branch_sender = data['branch_sender']   
        branch_receiver = data['branch_receiver']  
   
        if not branch_sender and not branch_receiver:
                raise osv.except_osv(_('Perhatian!'),
                    _('Branch Sender atau Branch Receiver belum diisi, harap isi terlebih dahulu'))   


        query = """
          SELECT 
            COALESCE(sm.price_unit,0) / 1.1 as hpp
            , branch_sender.code as branch_sender
            , mo.division as division
            , mo.name as name_mo
            , mo.date as date_mo
            , branch_receiver.code as branch_receiver
            , sp.name as name_sp
            , sp.date as date
            , sp.state as state
            , sp.date_done as date_done
            , p.name_template as name_template
            , p.default_code as default_code
            , sm.product_qty as product_qty
             

            FROM stock_picking sp 
            INNER JOIN stock_picking_type spt ON sp.picking_type_id = spt.id 
            INNER JOIN stock_move sm ON sp.id = sm.picking_id 

            LEFT JOIN wtc_mutation_order mo ON sp.transaction_id = mo.id
            LEFT JOIN wtc_branch branch_receiver ON sp.branch_id = branch_receiver.id
            LEFT JOIN wtc_branch branch_sender ON mo.branch_id = branch_sender.id 
            LEFT JOIN product_product p ON sm.product_id = p.id 

            WHERE sp.model_id IN (SELECT id FROM ir_model WHERE model = 'wtc.mutation.order' LIMIT 1)
           
            
            """ 

        
        query_where=''

        tz = '7 hours'

        if picking_type_code :
            if picking_type_code == 'in' :
                query_where += "  AND spt.code in ('incoming','interbranch_in')"
            elif picking_type_code == 'out' :
                query_where += "  AND spt.code in ('outgoing','interbranch_out')"
            else :
                query_where += "  AND spt.code = '%s'" % str(picking_type_code)


        if branch_sender :
            query_where += "  AND branch_sender.id in ('%s') " % branch_sender[0]
          

        if branch_receiver :
            query_where += "  AND branch_receiver.id in ('%s') " % branch_receiver[0]

        if division :
            query_where += "  AND mo.division = '%s'" % str(division)

        if state :
            query_where += "  AND sp.state = '%s'" % str(state)

        if start_date :
            query_where += " and sp.date >= '%s' " % start_date

        if end_date :
            end_date = end_date + ' 23:59:59'
            query_where += " AND sp.date_done <= to_timestamp('%s', 'YYYY-MM-DD HH24:MI:SS') + interval '%s'" % (end_date,tz)

        # if end_date :
        #     query_where += " and sp.date_done <= '%s' " % end_date 

        query_order = "ORDER BY branch_sender.code, branch_receiver.code, mo.date, mo.name, sp.date, sp.date_done, p.name_template"
       
        cr.execute (query+query_where+query_order)
        ress = cr.fetchall()

        # print">>>>>>>>>>>>>>>>>>>>>",(query+query_where+query_order)
        
   
    

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('MO Fulfillment')
        worksheet.set_column('B1:B1', 13)
        worksheet.set_column('C1:C1', 10)
        worksheet.set_column('D1:D1', 20)
        worksheet.set_column('E1:E1', 19)
        worksheet.set_column('F1:F1', 8)
        worksheet.set_column('G1:G1', 21)
        worksheet.set_column('H1:H1', 25)
        worksheet.set_column('I1:I1', 12)
        worksheet.set_column('J1:J1', 25)
        worksheet.set_column('K1:K1', 12)
        worksheet.set_column('L1:L1', 20)
        worksheet.set_column('M1:M1', 10)
        worksheet.set_column('N1:N1', 15)
        worksheet.set_column('O1:O1', 20)



        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        filename = 'Report MO Fulfillment '+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report MO Fulfillment' , wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date),str(end_date)) , wbf['company'])
        
        
        row=4
        rowsaldo = row
        row+=1
        worksheet.write('A%s' % (row+1), 'No' , wbf['header'])       
        worksheet.write('B%s' % (row+1), 'Branch' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'Division' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'No MO', wbf['header'])
        worksheet.write('E%s' % (row+1), 'Date', wbf['header'])
        worksheet.write('F%s' % (row+1), 'Branch Receiver' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'No Picking' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'Date' , wbf['header'])    
        worksheet.write('I%s' % (row+1), 'State' , wbf['header'])
        worksheet.write('J%s' % (row+1), 'Date Done' , wbf['header'])
        worksheet.write('K%s' % (row+1), 'Templete Name' , wbf['header'])
        worksheet.write('L%s' % (row+1), 'Default Code' , wbf['header'])
        worksheet.write('M%s' % (row+1), 'Qty' , wbf['header'])
        worksheet.write('N%s' % (row+1), 'Price Unit' , wbf['header'])
        worksheet.write('O%s' % (row+1), 'Sub Total' , wbf['header'])
       
        row+=2 
        row1 = row        
        no = 1   
        sub_total = 0
        hpp = 0

        user = self.pool.get('res.users').browse(cr, uid, uid)
        tz = pytz.timezone(user.tz) if user.tz else pytz.utc

        for res in ress:

            hpp = res[0]
            branch_sender = res[1]
            division = res[2]                
            name_mo = res[3] 
            date_mo = res[4]
            branch_receiver = res[5]
            name_sp = res[6]
            date_sp = res[7]
            state = res[8]
            date_done = res[9]
            name_template = res[10]
            default_code = res[11]
            product_qty = res[12]

            sub_total = res[12] * res[0]
            



            worksheet.write('A%s' % row, no , wbf['content_number'])                    
            worksheet.write('B%s' % row, branch_sender , wbf['content'])
            worksheet.write('C%s' % row, division , wbf['content'])
            worksheet.write('D%s' % row, name_mo , wbf['content'])
            worksheet.write('E%s' % row, date_mo , wbf['content_date'])
            worksheet.write('F%s' % row, branch_receiver, wbf['content'])
            worksheet.write('G%s' % row, name_sp , wbf['content'])
            worksheet.write('H%s' % row, date_sp , wbf['content_date'])  
            worksheet.write('I%s' % row, state , wbf['content'])
            worksheet.write('J%s' % row, date_done , wbf['content_date'])
            worksheet.write('K%s' % row, name_template , wbf['content'])
            worksheet.write('L%s' % row, default_code , wbf['content'])
            worksheet.write('M%s' % row, product_qty , wbf['content_number'])
            worksheet.write('N%s' % row, hpp , wbf['content_float'])
            worksheet.write('O%s' % row, sub_total , wbf['content_float'])

            no+=1
            row+=1


            hpp = hpp
            sub_total = sub_total

        worksheet.autofilter('A6:M%s' % (row))  
        worksheet.freeze_panes(6, 3)

         #TOTAL
        ##sheet 1
        worksheet.merge_range('A%s:C%s' % (row,row), 'Total', wbf['total'])    
        worksheet.merge_range('D%s:M%s' % (row,row), 'Total', wbf['total']) 

        worksheet.write('N%s'%(row), '', wbf['total'])
        worksheet.write('O%s'%(row), '', wbf['total'])

        formula_total_hpp = '{=subtotal(9,N%s:N%s)}' % (row1, row-1) 
        formula_total_sub = '{=subtotal(9,O%s:O%s)}' % (row1, row-1) 

        worksheet.write_formula(row-1,13,formula_total_hpp, wbf['total_float'], hpp)   
        worksheet.write_formula(row-1,14,formula_total_sub, wbf['total_float'], sub_total)   

  
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_mo_fulfillment', 'view_report_mo_fulfillment_wizard')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.report.mo.fulfillment.wizard',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }

wtc_report_mo_fulfillment()
