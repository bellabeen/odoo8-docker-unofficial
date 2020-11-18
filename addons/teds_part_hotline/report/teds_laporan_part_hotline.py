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

class LaporanPartHotlineWizard(models.TransientModel):
    _name = "teds.laporan.part.hotline.wizard"
    
    def _get_default_branch(self):
        branch_ids = False
        branch_ids = self.env.user.branch_ids
        if branch_ids and len(branch_ids) == 1 :
            return [branch_ids[0].id]
        return False

    @api.model
    def _get_default_date(self): 
        return self.env['wtc.branch'].get_default_date()
    
    @api.model
    def _get_default_datetime(self): 
        return self.env['wtc.branch'].get_default_datetime()

    wbf = {}

    name = fields.Char('Filename', readonly=True)
    state_x = fields.Selection([('choose','choose'),('get','get')], default='choose')
    data_x = fields.Binary('File', readonly=True)
    options = fields.Selection([
        ('Summary','Summary'),
        ('Detail','Detail')], 'Options',default='Summary')
    status = fields.Selection([
        ('Outstanding','Outstanding'),
        ('Done','Done'),
        ('All','All')], 'Status',default='All')
    start_date = fields.Date('Start Date',default=_get_default_date)
    end_date = fields.Date('End Date',default=_get_default_date)
    branch_ids = fields.Many2many('wtc.branch', 'teds_part_hotline_report_branch_rel', 'teds_part_hotline_id', 'branch_id',default=_get_default_branch)

    @api.multi
    def add_workbook_format(self,workbook):      
        self.wbf['header'] = workbook.add_format({'bold': 1,'align': 'center','bg_color': '#FFFFDB','font_color': '#000000'})
        self.wbf['header'].set_border()
        self.wbf['header'].set_font_size(10)


        self.wbf['header_no'] = workbook.add_format({'bold': 1,'align': 'center','bg_color': '#FFFFDB','font_color': '#000000'})
        self.wbf['header_no'].set_border()
        self.wbf['header_no'].set_align('vcenter')
                
        self.wbf['footer'] = workbook.add_format({'align':'left'})
        
        self.wbf['content_datetime'] = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss'})
        self.wbf['content_datetime'].set_left()
        self.wbf['content_datetime'].set_right()
        
        self.wbf['content_datetime_12_hr'] = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm AM/PM'})
        self.wbf['content_datetime_12_hr'].set_left()
        self.wbf['content_datetime_12_hr'].set_right()        
                
        self.wbf['content_date'] = workbook.add_format({'num_format': 'yyyy-mm-dd'})
        self.wbf['content_date'].set_left()
        self.wbf['content_date'].set_right() 
        
        self.wbf['title_doc'] = workbook.add_format({'bold': 1,'align': 'left'})
        self.wbf['title_doc'].set_font_size(10)
        
        self.wbf['company'] = workbook.add_format({'align': 'left'})
        self.wbf['company'].set_font_size(11)
        
        self.wbf['content'] = workbook.add_format()
        self.wbf['content'].set_left()
        self.wbf['content'].set_right() 

        
        self.wbf['content_float'] = workbook.add_format({'align': 'right','num_format': '#,##0.00'})
        self.wbf['content_float'].set_right() 
        self.wbf['content_float'].set_left()

        self.wbf['content_center'] = workbook.add_format({'align': 'centre'})
        self.wbf['content_center'].set_align('vcenter')
        self.wbf['content_center'].set_font_size(10)
        
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

    @api.multi
    def action_export(self):
        self.ensure_one()

        query_where = " WHERE 1=1"
        query_where_po = " "
        query_where_wo = " "

        if self.branch_ids:
            branch = [b.id for b in self.branch_ids]
            query_where += " AND ph.branch_id in %s" % str(tuple(branch)).replace(',)', ')')

        if self.start_date:
            query_where += " AND ph.date >= '%s'" % self.start_date
            query_where_po += " AND po.date_order >= '%s'" % self.start_date
            query_where_wo += " AND wo.date >= '%s'" % self.start_date
        
        if self.end_date:
            query_where += " AND ph.date <= '%s'" % self.end_date
            query_where_po += " AND po.date_order <= '%s'" % self.end_date
            query_where_wo += " AND wo.date <= '%s'" % self.end_date

        if self.status == 'Outstanding':
            query_where += " AND ph.state = 'approved'"
        elif self.status == 'Done':
            query_where += " AND ph.state = 'done'"         
        else:
            query_where += " AND ph.state != 'draft'"
    
  
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Laporan Part Hotline %s' %(self.options))
        worksheet.set_column('A1:A1', 5)
        worksheet.set_column('B1:B1', 6)
        worksheet.set_column('C1:C1', 18)
        worksheet.set_column('D1:D1', 24)
        worksheet.set_column('E1:E1', 12)
        worksheet.set_column('F1:F1', 17)
        worksheet.set_column('G1:G1', 17)
        worksheet.set_column('H1:H1', 13)
        worksheet.set_column('I1:I1', 35)
        worksheet.set_column('J1:J1', 17)
        worksheet.set_column('K1:K1', 18)
        worksheet.set_column('L1:L1', 15)
        



        date= self._get_default_datetime()
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        
        filename = 'Laporan Part Hotline'+' '+str(date)+'.xlsx'        
        worksheet.merge_range('A1:C1', 'Laporan Part Hotline %s'%(self.options) , wbf['title_doc'])
        worksheet.merge_range('A2:C2', 'Periode %s - %s'%(self.start_date,self.end_date) , wbf['title_doc'])
        
        row=3
        rowsaldo = row
        worksheet.write('A%s' % (row+1), 'No' , wbf['header'])
        worksheet.write('B%s' % (row+1), 'Code' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'Cabang' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'No Hotline' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'Tgl Hotline' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'No Engine' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'No Chassis' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'No Polisi' , wbf['header'])
        worksheet.write('I%s' % (row+1), 'Customer' , wbf['header'])
        worksheet.write('J%s' % (row+1), 'Pembawa' , wbf['header'])
        worksheet.write('K%s' % (row+1), 'No Telp' , wbf['header'])
        worksheet.write('L%s' % (row+1), 'Jenis PO' , wbf['header'])
        
        if self.options == 'Summary':
            worksheet.set_column('M1:M1', 16)
            worksheet.set_column('N1:N1', 17)
            worksheet.set_column('O1:O1', 15)
            worksheet.set_column('P1:P1', 15)
            worksheet.set_column('Q1:Q1', 15)
            worksheet.set_column('R1:R1', 15)
            worksheet.set_column('S1:S1', 20)
            worksheet.set_column('T1:T1', 20)

            query_summary = """
                SELECT b.code as branch_code
                , b.name as branch_name
                , ph.id as hotline_id
                , ph.name as hotline_name
                , ph.date as hotline_date
                , lot.name as no_engine
                , lot.chassis_no as no_chassis
                , lot.no_polisi
                , p.display_name as customer
                , ph.pembawa
                , ph.no_telp
                , phd.qty as qty_hotline
                , phd.qty_po
                , phd.qty_wo
                , COALESCE(ph.amount_total,0) as total_inv
                , COALESCE(dp.amount,0) as total_hl
                , INITCAP (ph.state) as state
                , ph.jenis_po
                , ph.tgl_order_po
                FROM teds_part_hotline ph
                INNER JOIN (
                    SELECT hotline_id 
                    , sum(qty) as qty
                    , COALESCE(sum(qty_spl),0) as qty_po
                    , COALESCE(sum(qty_wo),0) as qty_wo
                    FROM teds_part_hotline_detail GROUP BY hotline_id) as phd ON phd.hotline_id = ph.id 
                LEFT JOIN (
                    SELECT hotline_id
                    , COALESCE(sum(amount_hl_allocation),0) as amount
                    FROM teds_part_hotline_alokasi_dp GROUP BY hotline_id) as dp ON dp.hotline_id = ph.id
                INNER JOIN stock_production_lot lot ON lot.id = ph.lot_id
                INNER JOIN res_partner p ON p.id = ph.customer_id
                INNER JOIN wtc_branch b ON b.id = ph.branch_id
                %s
            """ %(query_where)
            query = query_summary
            worksheet.write('M%s' % (row+1), 'Qty Hotline' , wbf['header'])
            worksheet.write('N%s' % (row+1), 'Amount Hotline' , wbf['header'])
            worksheet.write('O%s' % (row+1), 'Qty PO' , wbf['header'])
            worksheet.write('P%s' % (row+1), 'Qty WO' , wbf['header'])
            worksheet.write('Q%s' % (row+1), 'Total DP' , wbf['header'])
            worksheet.write('R%s' % (row+1), 'Sisa DP' , wbf['header'])
            worksheet.write('S%s' % (row+1), 'Tgl PO MD' , wbf['header'])
            worksheet.write('T%s' % (row+1), 'State' , wbf['header'])

            row+=2               
            no = 1     
            row1 = row
            self._cr.execute (query)
            ress =  self._cr.dictfetchall()
            for res in ress:
                hotline_id = res.get('hotline_id')
                hotline_name = res.get('hotline_name')
                hotline_date = res.get('hotline_date')
                no_engine = res.get('no_engine')
                no_chassis = res.get('no_chassis')
                no_polisi = res.get('no_polisi')
                customer = res.get('customer')
                pembawa = res.get('pembawa')
                no_telp = res.get('no_telp')
                qty_hotline = res.get('qty_hotline')
                qty_po = res.get('qty_po')
                qty_wo = res.get('qty_wo')
                total_inv = res.get('total_inv')
                total_hl = res.get('total_hl')
                state = res.get('state')
                branch_code = res.get('branch_code')
                branch_name = res.get('branch_name')
                jenis_po = res.get('jenis_po')                
                # holine
                sisa_dp = 0
                dp_obj = self.env['teds.part.hotline.alokasi.dp'].sudo().search([('hotline_id','=',hotline_id)])
                if dp_obj:
                    sisa_dp = sum([dp.hl_id.amount_residual_currency for dp in dp_obj])
                tgl_order_po = res.get('tgl_order_po')

                worksheet.write('A%s' % row, no , wbf['content'])
                worksheet.write('B%s' % row, branch_code , wbf['content'])
                worksheet.write('C%s' % row, branch_name , wbf['content'])
                worksheet.write('D%s' % row, hotline_name , wbf['content'])
                worksheet.write('E%s' % row, hotline_date , wbf['content'])
                worksheet.write('F%s' % row, no_engine , wbf['content'])
                worksheet.write('G%s' % row, no_chassis ,wbf['content'])
                worksheet.write('H%s' % row, no_polisi , wbf['content'])
                worksheet.write('I%s' % row, customer , wbf['content'])
                worksheet.write('J%s' % row, pembawa , wbf['content'])
                worksheet.write('K%s' % row, no_telp , wbf['content'])
                worksheet.write('L%s' % row, jenis_po , wbf['content'])
                worksheet.write('M%s' % row, qty_hotline , wbf['content_float'])
                worksheet.write('N%s' % row, total_inv , wbf['content_float'])
                worksheet.write('O%s' % row, qty_po , wbf['content_float'])
                worksheet.write('P%s' % row, qty_wo , wbf['content_float'])
                worksheet.write('Q%s' % row, total_hl , wbf['content_float'])
                worksheet.write('R%s' % row, sisa_dp , wbf['content_float'])
                worksheet.write('S%s' % row, tgl_order_po , wbf['content'])
                worksheet.write('T%s' % row, state , wbf['content'])


                no+=1
                row+=1
            worksheet.autofilter('A4:T%s' % (row))  
        else:
            worksheet.set_column('M1:M1', 20)
            worksheet.set_column('N1:N1', 30)
            worksheet.set_column('O1:O1', 17)
            worksheet.set_column('P1:P1', 15)
            worksheet.set_column('Q1:Q1', 13)
            worksheet.set_column('R1:R1', 17)
            worksheet.set_column('S1:S1', 20)
            worksheet.set_column('T1:T1', 17)
            worksheet.set_column('U1:U1', 15)
            worksheet.set_column('V1:V1', 20)
            worksheet.set_column('W1:W1', 20)
            worksheet.set_column('X1:X1', 17)
            worksheet.set_column('Y1:Y1', 20)
            worksheet.set_column('Z1:Z1', 20)

            query_detail = """
                SELECT b.code as branch_code
                , b.name as branch_name
                , ph.jenis_po
                , ph.name as hotline_name
                , ph.date as hotline_date
                , lot.name as no_engine
                , lot.chassis_no as no_chassis
                , lot.no_polisi
                , p.display_name as customer
                , ph.pembawa
                , ph.no_telp
                , pt.name as product
                , pp.default_code as description
                , phd.qty as qty_hotline
                , phd.price
                , COALESCE(po.product_qty,COALESCE(phd.qty_spl,0)) as qty_po
                , COALESCE(ail.consolidated_qty,0) as qty_consolidate
                , CASE WHEN (po.product_qty > 0 or phd.qty_spl > 0) THEN COALESCE(po.name,phd.no_po) ELSE NULL END  as po_name
                , CASE WHEN (po.product_qty > 0 or phd.qty_spl > 0) THEN COALESCE(to_char(po.date_order + interval '7 hours','YYYY-MM-DD'),to_char(phd.tgl_po,'YYYY-MM-DD')) ELSE NULL END as po_date
                , CASE WHEN (wo.product_qty > 0 and phd.qty_wo > 0) THEN COALESCE(wo.product_qty,COALESCE(phd.qty_wo,0)) ELSE 0 END as qty_wo
                , CASE WHEN (wo.product_qty > 0 and phd.qty_wo > 0) THEN wo.date ELSE NULL END as wo_date
                , CASE WHEN (wo.product_qty > 0 and phd.qty_wo > 0) THEN COALESCE(wo.name,phd.no_wo) ELSE NULL END  as wo_name
                , date_part('days',wo.date - COALESCE(po.date_order,phd.tgl_po)) as umur
                , INITCAP (ph.state) as state
                , ph.tgl_order_po
                FROM teds_part_hotline ph
                INNER JOIN teds_part_hotline_detail phd ON phd.hotline_id = ph.id 
                INNER JOIN wtc_branch b ON b.id = ph.branch_id
                INNER JOIN stock_production_lot lot ON lot.id = ph.lot_id
                INNER JOIN res_partner p ON p.id = ph.customer_id
                INNER JOIN product_product pp ON pp.id = phd.product_id
                INNER JOIN product_template pt ON pt.id = pp.product_tmpl_id
                LEFT JOIN (
                    SELECT po.id
                    , po.name
                    , date_order
                    , po.part_hotline_id
                    , pol.product_id
                    , COALESCE(pol.product_qty,0) as product_qty
                    FROM purchase_order po
                    INNER JOIN purchase_order_line pol ON pol.order_id = po.id
                    WHERE po.state in ('approved','done')
                    AND po.part_hotline_id IS NOT NULL
                    %s
                ) po ON po.part_hotline_id = ph.id and po.product_id = phd.product_id
                LEFT JOIN (
                    SELECT wo.id
                    , wo.name
                    , wo.date
                    , wo.part_hotline_id
                    , wol.product_id
                    , COALESCE(wol.product_qty,0) as product_qty
                    FROM wtc_work_order wo
                    INNER JOIN wtc_work_order_line wol ON wol.work_order_id = wo.id
                    WHERE wo.state in ('open','done')
                    AND wo.part_hotline_id IS NOT NULL
                    %s
                ) wo ON wo.part_hotline_id = ph.id and wo.product_id = phd.product_id
                LEFT JOIN account_invoice ai ON ai.transaction_id = po.id AND model_id = (select id from ir_model where model = 'purchase.order') AND ai.state in ('open','paid')
                LEFT JOIN account_invoice_line ail ON ail.invoice_id = ai.id AND ail.product_id = po.product_id
                %s
                ORDER BY ph.name ASC
            """ %(query_where_po,query_where_wo,query_where)
            query = query_detail
            worksheet.write('M%s' % (row+1), 'Product' , wbf['header'])
            worksheet.write('N%s' % (row+1), 'Description' , wbf['header'])
            worksheet.write('O%s' % (row+1), 'Price' , wbf['header'])
            worksheet.write('P%s' % (row+1), 'Qty Hotline' , wbf['header'])
            worksheet.write('Q%s' % (row+1), 'Qty PO' , wbf['header'])
            worksheet.write('R%s' % (row+1), 'Qty Consolidated' , wbf['header'])
            worksheet.write('S%s' % (row+1), 'No PO' , wbf['header'])
            worksheet.write('T%s' % (row+1), 'Tgl PO' , wbf['header'])
            worksheet.write('U%s' % (row+1), 'Umur PO' , wbf['header'])
            worksheet.write('V%s' % (row+1), 'Qty WO' , wbf['header'])
            worksheet.write('W%s' % (row+1), 'No WO' , wbf['header'])
            worksheet.write('X%s' % (row+1), 'Tgl WO' , wbf['header'])
            worksheet.write('Y%s' % (row+1), 'Tgl PO MD' , wbf['header'])
            worksheet.write('Z%s' % (row+1), 'State' , wbf['header'])

            row+=2               
            no = 1     
            row1 = row
            self._cr.execute (query)
            ress =  self._cr.dictfetchall()
            cek_detail = ""
            for res in ress:
                branch_code = res.get('branch_code')
                branch_name = res.get('branch_name')
                hotline_name = res.get('hotline_name')
                hotline_date = res.get('hotline_date')
                no_engine = res.get('no_engine')
                no_chassis = res.get('no_chassis')
                no_polisi = res.get('no_polisi')
                customer = res.get('customer')
                pembawa = res.get('pembawa')
                no_telp = res.get('no_telp')
                product = res.get('product')
                description = res.get('description')
                qty_hotline = res.get('qty_hotline')
                qty_po = res.get('qty_po')
                price = res.get('price',0)
                qty_consolidate = res.get('qty_consolidate')
                qty_wo = res.get('qty_wo')
                po_name = res.get('po_name')
                po_date = res.get('po_date')
                wo_name = res.get('wo_name')
                wo_date = res.get('wo_date')
                umur = res.get('umur')
                jenis_po = res.get('jenis_po')
                state = res.get('state')
                tgl_order_po = res.get('tgl_order_po')

                combain_detail = "%s|%s" %(hotline_name,product)
                if (int(qty_hotline) - int(qty_po) != 0) or (int(qty_po) - int(qty_wo) != 0):
                    self.wbf['content'] = workbook.add_format({'font_color': '#FF0000'})
                    self.wbf['content_float'] = workbook.add_format({'font_color': '#FF0000'})
                else:
                    self.wbf['content'] = workbook.add_format()
                    self.wbf['content_float'] = workbook.add_format()

                if cek_detail != combain_detail:
                    worksheet.write('A%s' % row, no , wbf['content'])
                    worksheet.write('B%s' % row, branch_code , wbf['content'])
                    worksheet.write('C%s' % row, branch_name , wbf['content'])
                    worksheet.write('D%s' % row, hotline_name , wbf['content'])
                    worksheet.write('E%s' % row, hotline_date , wbf['content'])
                    worksheet.write('F%s' % row, no_engine , wbf['content'])
                    worksheet.write('G%s' % row, no_chassis ,wbf['content'])
                    worksheet.write('H%s' % row, no_polisi , wbf['content'])
                    worksheet.write('I%s' % row, customer , wbf['content'])
                    worksheet.write('J%s' % row, pembawa , wbf['content'])
                    worksheet.write('K%s' % row, no_telp , wbf['content'])
                    worksheet.write('L%s' % row, jenis_po , wbf['content'])
                    worksheet.write('M%s' % row, product , wbf['content'])
                    worksheet.write('N%s' % row, description , wbf['content'])
                    worksheet.write('O%s' % row, price , wbf['content_float'])
                    worksheet.write('P%s' % row, qty_hotline , wbf['content_float'])
                    # Pecah #
                    worksheet.write('Q%s' % row, qty_po , wbf['content_float'])
                    worksheet.write('R%s' % row, qty_consolidate , wbf['content_float'])
                    worksheet.write('S%s' % row, po_name , wbf['content'])
                    worksheet.write('T%s' % row, po_date , wbf['content'])
                    worksheet.write('U%s' % row, umur , wbf['content'])
                    worksheet.write('V%s' % row, qty_wo , wbf['content_float'])
                    worksheet.write('W%s' % row, wo_name , wbf['content'])
                    worksheet.write('X%s' % row, wo_date , wbf['content'])
                    worksheet.write('Y%s' % row, tgl_order_po , wbf['content'])
                    worksheet.write('Z%s' % row, state , wbf['content'])

                    no+=1
                else:
                    worksheet.write('A%s' % row, "" , wbf['content'])
                    worksheet.write('B%s' % row, "" , wbf['content'])
                    worksheet.write('C%s' % row, "" , wbf['content'])
                    worksheet.write('D%s' % row, "" , wbf['content'])
                    worksheet.write('E%s' % row, "" , wbf['content'])
                    worksheet.write('F%s' % row, "" , wbf['content'])
                    worksheet.write('G%s' % row, "" ,wbf['content'])
                    worksheet.write('H%s' % row, "" , wbf['content'])
                    worksheet.write('I%s' % row, "" , wbf['content'])
                    worksheet.write('J%s' % row, "" , wbf['content'])
                    worksheet.write('K%s' % row, "" , wbf['content'])
                    worksheet.write('L%s' % row, "" , wbf['content'])
                    worksheet.write('M%s' % row, "" , wbf['content'])
                    worksheet.write('N%s' % row, "" , wbf['content'])
                    worksheet.write('O%s' % row, "" , wbf['content_float'])
                    worksheet.write('P%s' % row, "" , wbf['content_float'])
                    # Pecah #
                    worksheet.write('Q%s' % row, qty_po , wbf['content_float'])
                    worksheet.write('R%s' % row, qty_consolidate , wbf['content_float'])
                    worksheet.write('S%s' % row, po_name , wbf['content'])
                    worksheet.write('T%s' % row, po_date , wbf['content'])
                    worksheet.write('U%s' % row, umur , wbf['content'])
                    worksheet.write('V%s' % row, qty_wo , wbf['content_float'])
                    worksheet.write('W%s' % row, wo_name , wbf['content'])
                    worksheet.write('X%s' % row, wo_date , wbf['content'])
                    worksheet.write('Y%s' % row, tgl_order_po , wbf['content'])
                    worksheet.write('Z%s' % row, state , wbf['content'])

                row+=1
                cek_detail = combain_detail
            worksheet.autofilter('A4:Z%s' % (row))  
        user = self.env['res.users'].browse(self._uid).name
        
        worksheet.freeze_panes(4, 5)
        worksheet.write('A%s'%(row+1), 'Create By: %s %s' % (user,str(date)) , wbf['footer']) 

        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write({'state_x':'get', 'data_x':out, 'name': filename})
        fp.close()

        ir_model_data = self.env['ir.model.data']
        form_res = ir_model_data.get_object_reference('teds_part_hotline', 'view_teds_laporan_part_hotline_wizard')
        
        form_id = form_res and form_res[1] or False
        return {
            'name':('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.laporan.part.hotline.wizard',
            'res_id': self.ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }