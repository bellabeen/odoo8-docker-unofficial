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

class wtc_report_df(osv.osv_memory):
   
    _name = "wtc.report.control.df"
    _description = "DF Report"

    wbf = {}

    def _get_default(self,cr,uid,date=False,user=False,context=None):
        if date :
            return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)
        else :
            return self.pool.get('res.users').browse(cr, uid, uid)
#         
#     def _get_branch_ids(self, cr, uid, context=None):
#         branch_ids_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
#         branch_ids = [b.id for b in branch_ids_user]
#         return branch_ids
        
    _columns = {
        'state_x': fields.selection( ( ('choose','choose'),('get','get'))), #xls
        'data_x': fields.binary('File', readonly=True),
        'name': fields.char('Filename', 100, readonly=True),
        'per_date': fields.date('Per Date',required=True),           
    }

    _defaults = {
        'state_x': lambda *a: 'choose',
        'per_date':datetime.today(),
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
        
        per_date = data['per_date']
            
        query = """
            select 
            so.id as p_id
            , b.code as p_name          
            , so.name as no_transaksi 
            , partner.default_code as kode_cabang 
            , partner.name  as nama_branch 
            , partner.name as partner_name 
            , ai.number as p_ref 
            , ai.date_invoice
            , ai.date_due
            , ai.amount_total
            , inv_qty.quantity as inv_qty 
            , coalesce(sj_qty.quantity,0) as sj_qty
            , pick.date_done + interval '7 hours' as pick_date
            , pick.name as pick_name 
            , pack.name as pack_name 
            , pack_line.engine_number 
            , pack_line.chassis_number 
            from sale_order so inner join 
            (select so.id as so_id, inv.id as inv_id, sum(quantity) as quantity 
            from sale_order so 
            inner join account_invoice inv on so.name = inv.origin and inv.type = 'out_invoice' 
            inner join account_invoice_line invl on inv.id = invl.invoice_id 
            where so.division = 'Unit' 
            and inv.date_invoice <= '%s' 
            group by so.id, inv.id) inv_qty on so.id = inv_qty.so_id 
            left join (select so.id, so.name, max(pick.date_done) as date_done, sum(quantity) as quantity 
            from sale_order so 
            inner join stock_picking pick on so.name = pick.origin and pick.state = 'done' 
            inner join wtc_stock_packing pack on pick.id = pack.picking_id 
            inner join wtc_stock_packing_line pack_line on pack.id = pack_line.packing_id and pack_line.engine_number is not null 
            where so.division = 'Unit' 
            and pick.date_done <= to_timestamp('%s 23:59:59', 'YYYY-MM-DD HH24:MI:SS') + interval '7 hours' 
            group by so.id, so.name) sj_qty on so.id = sj_qty.id 
            inner join account_invoice ai on ai.id = inv_qty.inv_id and ai.type = 'out_invoice' 
            left join stock_picking pick on so.name = pick.origin and pick.state = 'done' 
            left join wtc_stock_packing pack on pick.id = pack.picking_id 
            left join wtc_stock_packing_line pack_line on pack.id = pack_line.packing_id and pack_line.engine_number is not null 
            left join wtc_branch b on so.branch_id = b.id 
            left join res_partner partner on so.partner_id = partner.id 
            where inv_qty.quantity > sj_qty.quantity 
            or sj_qty.quantity is null 
            or (sj_qty.date_done >= to_timestamp('%s 00:00:00', 'YYYY-MM-DD HH24:MI:SS') + interval '7 hours'
            and sj_qty.date_done <= to_timestamp('%s 23:59:59', 'YYYY-MM-DD HH24:MI:SS') + interval '7 hours') 
            order by b.code, ai.date_invoice, partner.default_code, so.name, ai.number, pick.date_done, pick.name, pack.name
            """ % (per_date, per_date, per_date, per_date)
                            
        cr.execute (query)
        ress = cr.fetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        
        get_date = self._get_default(cr, uid, date=True, context=context)
        date = get_date.strftime("%Y-%m-%d %H:%M:%S")
        date_date = get_date.strftime("%Y-%m-%d")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        filename = 'Report Control DF '+str(date)+'.xlsx'  
        
        #WKS 1
        worksheet = workbook.add_worksheet('Control DF')
        worksheet.set_column('B1:B1', 9)
        worksheet.set_column('C1:C1', 20)
        worksheet.set_column('D1:D1', 20)
        worksheet.set_column('E1:E1', 20)
        worksheet.set_column('F1:F1', 20)
        worksheet.set_column('G1:G1', 20)
        worksheet.set_column('H1:H1', 20)
        worksheet.set_column('I1:I1', 20)
        worksheet.set_column('J1:J1', 20)
        worksheet.set_column('K1:K1', 20)
        worksheet.set_column('L1:L1', 20)
                     
        #WKS 1      
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report Control DF Per Tanggal %s '%(str(per_date)) , wbf['title_doc'])
        
        row=2   
        rowsaldo = row
        row+=1
              
        worksheet.write('A%s' % (row+1), 'No' , wbf['header'])              
        worksheet.write('B%s' % (row+1), 'Code' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'No Transaksi' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'Kode Cabang' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'Nama Dealer' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'No Invoice' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'Tanggal Invoice' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'Tanggal JTP' , wbf['header'])
        worksheet.write('I%s' % (row+1), 'Amount Total' , wbf['header'])
        worksheet.write('J%s' % (row+1), 'Qty Invoice' , wbf['header'])
        worksheet.write('K%s' % (row+1), 'Qty Surat Jalan' , wbf['header'])
        worksheet.write('L%s' % (row+1), 'Tanggal Picking' , wbf['header'])
                                 
        row+=2         
        no = 0
        
        prev_id = False
        for res in ress:
            p_id = res[0]
            if p_id == prev_id :
                continue
            prev_id = p_id
            
            p_name = res[1].encode('ascii','ignore').decode('ascii') if res[1] != None else ''
            no_transaksi = res[2].encode('ascii','ignore').decode('ascii') if res[2] != None else ''
            kode_cabang = res[3].encode('ascii','ignore').decode('ascii') if res[3] != None else ''
            nama_branch = res[4].encode('ascii','ignore').decode('ascii') if res[4] != None else ''
            no_invoice = res[6].encode('ascii','ignore').decode('ascii') if res[6] != None else ''
            tanggal_invoice = datetime.strptime(res[7], "%Y-%m-%d").date() if res[7] != None else ''
            date_due = datetime.strptime(res[8], "%Y-%m-%d").date() if res[8] != None else ''
            amount_total =str(res[9])
            qty_invoice = str(res[10])
            qty_sj = str(res[11])
            tanggal_picking =  datetime.strptime(res[12][0:19], "%Y-%m-%d %H:%M:%S") if res[12] else ''
            #no_picking = res[13].encode('ascii','ignore').decode('ascii') if res[13] != None else ''
            #no_packing = res[14].encode('ascii','ignore').decode('ascii') if res[14] != None else ''
            #no_mesin = res[15].encode('ascii','ignore').decode('ascii') if res[15] != None else ''
            #no_chassis = res[16].encode('ascii','ignore').decode('ascii') if res[16] != None else ''
            p_ref = res[6].encode('ascii','ignore').decode('ascii') if res[6] != None else ''
            no += 1

            worksheet.write('A%s' % row, no , wbf['content_number'])                    
            worksheet.write('B%s' % row, kode_cabang , wbf['content'])
            worksheet.write('C%s' % row, no_transaksi , wbf['content'])
            worksheet.write('D%s' % row, nama_branch , wbf['content'])
            worksheet.write('E%s' % row, p_ref , wbf['content'])
            worksheet.write('F%s' % row, no_invoice , wbf['content'])
            worksheet.write('G%s' % row, tanggal_invoice , wbf['content_date'])
            worksheet.write('H%s' % row, date_due , wbf['content_date'])  
            worksheet.write('I%s' % row, amount_total , wbf['content_float'])
            worksheet.write('J%s' % row, qty_invoice , wbf['content_number'])
            worksheet.write('K%s' % row, qty_sj , wbf['content_number'])
            worksheet.write('L%s' % row, tanggal_picking , wbf['content_datetime'])
            row+=1
            
        worksheet.autofilter('A4:L%s' % (row))  
        worksheet.freeze_panes(4, 3)       
        worksheet.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])  

        #WKS 2
        worksheet2 = workbook.add_worksheet('Control DF Detail')
        worksheet2.set_column('B1:B1', 9)
        worksheet2.set_column('C1:C1', 20)
        worksheet2.set_column('D1:D1', 20)
        worksheet2.set_column('E1:E1', 20)
        worksheet2.set_column('F1:F1', 20)
        worksheet2.set_column('G1:G1', 20)
        worksheet2.set_column('H1:H1', 20)
        worksheet2.set_column('I1:I1', 20)
        worksheet2.set_column('J1:J1', 20)
        worksheet2.set_column('K1:K1', 20)
        worksheet2.set_column('L1:L1', 20)
        worksheet2.set_column('M1:M1', 20)
        worksheet2.set_column('N1:N1', 20)
        worksheet2.set_column('O1:O1', 20)
        worksheet2.set_column('P1:P1', 20)

        worksheet2.write('A1', company_name , wbf['company'])
        worksheet2.write('A2', 'Report Control DF Detail Per Tanggal %s '%(str(per_date)) , wbf['title_doc'])
        
        row=2   
        rowsaldo = row
        row+=1
              
        worksheet2.write('A%s' % (row+1), 'No' , wbf['header'])              
        worksheet2.write('B%s' % (row+1), 'Code' , wbf['header'])
        worksheet2.write('C%s' % (row+1), 'No Transaksi' , wbf['header'])
        worksheet2.write('D%s' % (row+1), 'Kode Cabang' , wbf['header'])
        worksheet2.write('E%s' % (row+1), 'Nama Dealer' , wbf['header'])
        worksheet2.write('F%s' % (row+1), 'No Invoice' , wbf['header'])
        worksheet2.write('G%s' % (row+1), 'Tanggal Invoice' , wbf['header'])
        worksheet2.write('H%s' % (row+1), 'Tanggal JTP' , wbf['header'])
        worksheet2.write('I%s' % (row+1), 'Amount Total' , wbf['header'])
        worksheet2.write('J%s' % (row+1), 'Qty Invoice' , wbf['header'])
        worksheet2.write('K%s' % (row+1), 'Qty Surat Jalan' , wbf['header'])
        worksheet2.write('L%s' % (row+1), 'Tanggal Picking' , wbf['header'])
        worksheet2.write('M%s' % (row+1), 'No Picking' , wbf['header'])
        worksheet2.write('N%s' % (row+1), 'No Packing' , wbf['header'])
        worksheet2.write('O%s' % (row+1), 'No Mesin' , wbf['header'])
        worksheet2.write('P%s' % (row+1), 'No Rangka' , wbf['header'])
                                 
        row+=2         
        no = 0

        prev_id = False
        for res in ress:
            p_id = res[0]

            no_picking = res[13].encode('ascii','ignore').decode('ascii') if res[13] != None else ''
            no_packing = res[14].encode('ascii','ignore').decode('ascii') if res[14] != None else ''
            no_mesin = res[15].encode('ascii','ignore').decode('ascii') if res[15] != None else ''
            no_chassis = res[16].encode('ascii','ignore').decode('ascii') if res[16] != None else ''

            worksheet2.write('M%s' % row, no_picking , wbf['content'])
            worksheet2.write('N%s' % row, no_packing , wbf['content'])
            worksheet2.write('O%s' % row, no_mesin , wbf['content'])
            worksheet2.write('P%s' % row, no_chassis , wbf['content'])

            if p_id != prev_id :
                p_name = res[1].encode('ascii','ignore').decode('ascii') if res[1] != None else ''
                no_transaksi = res[2].encode('ascii','ignore').decode('ascii') if res[2] != None else ''
                kode_cabang = res[3].encode('ascii','ignore').decode('ascii') if res[3] != None else ''
                nama_branch = res[4].encode('ascii','ignore').decode('ascii') if res[4] != None else ''
                no_invoice = res[6].encode('ascii','ignore').decode('ascii') if res[6] != None else ''
                tanggal_invoice = datetime.strptime(res[7], "%Y-%m-%d").date() if res[7] != None else ''
                date_due = datetime.strptime(res[8], "%Y-%m-%d").date() if res[8] != None else ''
                amount_total =str(res[9])
                qty_invoice = str(res[10])
                qty_sj = str(res[11])
                tanggal_picking =  datetime.strptime(res[12][0:19], "%Y-%m-%d %H:%M:%S") if res[12] else ''
                p_ref = res[6].encode('ascii','ignore').decode('ascii') if res[6] != None else ''
                no += 1

                worksheet2.write('A%s' % row, no , wbf['content_number'])                    
                worksheet2.write('B%s' % row, kode_cabang , wbf['content'])
                worksheet2.write('C%s' % row, no_transaksi , wbf['content'])
                worksheet2.write('D%s' % row, nama_branch , wbf['content'])
                worksheet2.write('E%s' % row, p_ref , wbf['content'])
                worksheet2.write('F%s' % row, no_invoice , wbf['content'])
                worksheet2.write('G%s' % row, tanggal_invoice , wbf['content_date'])
                worksheet2.write('H%s' % row, date_due , wbf['content_date'])  
                worksheet2.write('I%s' % row, amount_total , wbf['content_float'])
                worksheet2.write('J%s' % row, qty_invoice , wbf['content_number'])
                worksheet2.write('K%s' % row, qty_sj , wbf['content_number'])
                worksheet2.write('L%s' % row, tanggal_picking , wbf['content_datetime'])
            prev_id = p_id
            
            row+=1
            
        worksheet2.autofilter('A4:P%s' % (row))  
        worksheet2.freeze_panes(4, 3)       
        worksheet2.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])  

        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_df', 'view_wtc_report_control_df')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.report.control.df',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }

wtc_report_df()
