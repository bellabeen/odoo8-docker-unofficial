from datetime import timedelta,datetime
from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning
import datetime
from dateutil.relativedelta import relativedelta
import base64
from cStringIO import StringIO
import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell
import xlrd

class StockDistributionCreateOrderWizard(models.TransientModel):
    _name = "teds.stock.distribution.create.order.wizard"

    @api.multi
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date()
   
    wbf = {}

    options = fields.Selection([
        ('Upload','Upload'),
        ('Download','Download')
    ],string="Options",required=True)
    
    name = fields.Char('Name')
    file_upload = fields.Binary('File Upload')
    file_download  = fields.Binary('File')
    date = fields.Date('Date',default=_get_default_date,readonly=True)
    division = fields.Selection([
        ('Unit','Unit'),
        ('Sparepart','Sparepart')
    ])
    type_id = fields.Many2one('wtc.purchase.order.type','Type')

    @api.multi
    def action_wizard(self):
        if self.options == 'Upload':
            self._action_upload()
        else:
            form_id = self.env.ref('teds_stock_distribution.view_teds_stock_distribution_create_order_download_wizard').id
            res = self._action_download()
            return {
                'name': ('Download XLS'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'teds.stock.distribution.create.order.wizard',
                'res_id': res,
                'view_id': False,
                'views': [(form_id, 'form')],
                'type': 'ir.actions.act_window',
                'target': 'current'
            }

    def _action_upload(self):
        data = base64.decodestring(self.file_upload)
        excel = xlrd.open_workbook(file_contents = data)  
        sh = excel.sheet_by_index(0) 
        vals_mo = {}
        vals_so = {}
        for rx in range(3,sh.nrows):
            distribution = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [1] 
            prod = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [11]
            division = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [7]
            qty = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [16]
            prod_id = int(prod)
            where = " WHERE sd.division = '%s' AND sd.name = '%s' AND sdl.product_id = %d" %(division,distribution,prod_id)
            query = """
                        SELECT sdl.id as id_line
                            , sd.id as id_dist
                        FROM wtc_stock_distribution sd
                        INNER JOIN wtc_stock_distribution_line sdl
                        ON sd.id = sdl.distribution_id
                        %s
                        LIMIT 1
                    """ %(where)
            self._cr.execute (query)
            ress =  self._cr.dictfetchall()[0]
            line = ress.get('id_line')
            id_dist = ress.get('id_dist')
            distribution_line = self.env['wtc.stock.distribution.line'].sudo().browse(line)
            if distribution_line:
                distribution_line.write({'approved_qty':qty})
            
            distribution_id = self.env['wtc.stock.distribution'].sudo().browse(id_dist)
            if distribution_id and distribution_line:
                qty_avb = self.env['wtc.mutation.order'].sudo().get_stock_available(distribution_line.product_id.id,distribution_id.branch_id.id)
                
                # Data Mutation Order
                if distribution_id.branch_requester_id:
                    if vals_mo.get(distribution_id):
                        vals_mo[distribution_id]['order_line'].append([0,False,{
                                'product_id': distribution_line.product_id.id,
                                'description':distribution_line.description,
                                'qty':distribution_line.approved_qty - distribution_line.qty,
                                'unit_price':distribution_line.unit_price,
                                'qty_available':qty_avb,
                            }])
                    else:
                        vals_mo[distribution_id] = {
                            'branch_id':distribution_id.branch_id.id,
                            'branch_requester_id':distribution_id.branch_requester_id.id,
                            'division':distribution_id.division,
                            'user_id':distribution_id.user_id.id,
                            'distribution_id':distribution_id.id,
                            'date':distribution_id.date,
                            'start_date':distribution_id.start_date,
                            'end_date':distribution_id.end_date,
                            'description':distribution_id.description,
                            'state':'draft',
                            'order_line':[[0,False,{
                                'product_id': distribution_line.product_id.id,
                                'description':distribution_line.description,
                                'qty':distribution_line.approved_qty - distribution_line.qty,
                                'unit_price':distribution_line.unit_price,
                                'qty_available':qty_avb,
                            }]]
                        }
                # Data Sale Order 
                else:
                    total_inv = 0
                    total_inv = self.env['sale.order'].sudo()._invoice_total(distribution_id.dealer_id.id,distribution_id.division)        
                    pcc_id = self.env['pricelist.config.cabang'].search([
                      ('branch_id','=',distribution_id.branch_id.id),
                      ('partner_id','=',distribution_id.dealer_id.id),
                      ('division','=',distribution_id.division)],limit=1)

                    if distribution_id.division=='Unit':
                        if pcc_id:
                          pricelist = pcc_id.md_pricelist_id.id 
                        else:
                          pricelist = distribution_id.branch_id.pricelist_unit_sales_id.id or distribution_id.dealer_id.property_product_pricelist.id
                    elif distribution_id.division=='Sparepart':
                        if pcc_id:
                          pricelist = pcc_id.md_pricelist_id.id
                        else:
                          pricelist = distribution_id.branch_id.pricelist_part_sales_id.id or distribution_id.dealer_id.property_product_pricelist.id

                    if vals_so.get(distribution_id):
                        vals_so[distribution_id]['order_line'].append([0,False,{
                            'categ_id': distribution_line.product_id.categ_id.id,
                            'product_id': distribution_line.product_id.id,
                            'description': distribution_line.product_id.name,
                            'product_uom_qty': distribution_line.approved_qty - distribution_line.qty,
                            'price_unit': distribution_id._get_price_unit(pricelist,distribution_line.product_id.id),
                            'tax_id': [(6,0,[x.id for x in distribution_line.product_id.taxes_id])],
                         }])

                    else:
                        vals_so[distribution_id] = {
                            'branch_id': distribution_id.branch_id.id,
                            'division': distribution_id.division,
                            'user_id': distribution_id.user_id.id,
                            'date_order': distribution_id.date,
                            'partner_id': distribution_id.dealer_id.id,
                            'warehouse_id': distribution_id._get_warehouse(distribution_id.branch_id.id)['id'],
                            'payment_term': distribution_id.dealer_id.property_payment_term.id,
                            'distribution_id': distribution_id.id,
                            'total_invoiced': total_inv,
                            'pricelist_id': pricelist,
                            'state':'draft',
                            'order_line':[[0,False,{
                                'categ_id': distribution_line.product_id.categ_id.id,
                                'product_id': distribution_line.product_id.id,
                                'description': distribution_line.product_id.name,
                                'product_uom_qty': distribution_line.approved_qty - distribution_line.qty,
                                'price_unit': distribution_id._get_price_unit(pricelist,distribution_line.product_id.id),
                                'tax_id': [(6,0,[x.id for x in distribution_line.product_id.taxes_id])],
                            }]]
                        }

        
        for key,vals in vals_mo.items():
            mo = self.env['wtc.mutation.order'].search([
                ('distribution_id','=',key.id),
                ('state','=','draft')
            ])
            if key.state == 'done' or key.func_qty == 0 or mo:
                continue
            create_mo = self.env['wtc.mutation.order'].sudo().create(vals)
            print "berhasil create MO",create_mo    

        for key2,vals2 in vals_so.items():
            so = self.env['sale.order'].search([
                ('distribution_id','=',key2.id),
                ('state','=','draft')
            ])
            if key2.state == 'done' or key2.func_qty == 0 or so:
                continue
            create_so = self.env['sale.order'].sudo().create(vals2)
            print "berhasil create SO",create_so    
        


    @api.multi
    def add_workbook_format(self, workbook):
        self.wbf['company'] = workbook.add_format({'bold':1,'align': 'left','font_color':'#000000','num_format': 'dd-mm-yyyy'})
        self.wbf['company'].set_font_size(10)
        
        self.wbf['header'] = workbook.add_format({'bold': 1,'align': 'center','font_color': '#000000','bg_color':'#2E9AFE'})
        self.wbf['header'].set_top()
        self.wbf['header'].set_bottom()
        self.wbf['header'].set_font_size(10)
 
        self.wbf['header_right'] = workbook.add_format({'bold': 1,'align': 'center','font_color': '#000000','bg_color':'#2E9AFE'})
        self.wbf['header_right'].set_top()
        self.wbf['header_right'].set_bottom()
        self.wbf['header_right'].set_right()
        self.wbf['header_right'].set_font_size(10)
 
        self.wbf['content'] = workbook.add_format({'align': 'left','font_color': '#000000'})
        self.wbf['content'].set_font_size(10)
        
        self.wbf['content_number'] = workbook.add_format({'align': 'center','font_color': '#000000'})
        self.wbf['content_number'].set_font_size(10)
        
        self.wbf['context'] = workbook.add_format({'align': 'left','font_color': '#000000'})
        self.wbf['context'].set_font_size(12)
                
        self.wbf['content_float'] = workbook.add_format({'align': 'right','num_format': '#,##0.00'})
        self.wbf['content_float'].set_font_size(10)
 
 
        self.wbf['content_float_right'] = workbook.add_format({'align': 'right','num_format': '#,##0.00','bg_color':'#F7FE2E'})
        self.wbf['content_float_right'].set_font_size(10)
        self.wbf['content_float_right'].set_right()

        
        self.wbf['footer'] = workbook.add_format({'font_color':'#B45F04'})
        self.wbf['footer'].set_top()
       
        
        return workbook
    
    def _action_download(self):
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)       
        workbook = self.add_workbook_format(workbook)
        wbf = self.wbf
        worksheet = workbook.add_worksheet('Stock Distribution')
        worksheet.set_column('A1:A1', 9)
        worksheet.set_column('B1:B1', 23)
        worksheet.set_column('C1:C1', 23)
        worksheet.set_column('D1:D1', 10)
        worksheet.set_column('E1:E1', 14)
        worksheet.set_column('F1:F1', 22)
        worksheet.set_column('G1:G1', 13)   
        worksheet.set_column('H1:H1', 15)
        worksheet.set_column('I1:I1', 15)
        worksheet.set_column('J1:J1', 15)
        worksheet.set_column('K1:K1', 15)
        worksheet.set_column('L1:L1', 15)
        worksheet.set_column('M1:M1', 15)
        worksheet.set_column('N1:N1', 23)
        worksheet.set_column('O1:O1', 12)
        worksheet.set_column('P1:P1', 12)
        worksheet.set_column('Q1:Q1', 12)


        date_now = self._get_default_date()
        date1 = date_now.strftime("%d-%m-%Y %H:%M:%S")
        date2 = date_now.strftime("%d-%m-%Y")


        user_id = self.env['res.users'].search([('id','=',self._uid)])
        user = user_id.name 
        filename = 'Stock Distribution'+' '+str(date1)+'.xlsx'

        worksheet.write('A1', 'Data Stock Distribution' , wbf['company']) 
        
        row=2
        worksheet.write('A%s' %(row+1), 'No', wbf['header'])
        worksheet.write('B%s' %(row+1), 'Distribution', wbf['header'])
        worksheet.write('C%s' %(row+1), 'Purchase Order', wbf['header'])
        worksheet.write('D%s' %(row+1), 'Branch Code', wbf['header'])
        worksheet.write('E%s' %(row+1), 'Branch Name', wbf['header'])
        worksheet.write('F%s' %(row+1), 'Dealer', wbf['header'])
        worksheet.write('G%s' %(row+1), 'Type Order', wbf['header'])
        worksheet.write('H%s' %(row+1), 'Division', wbf['header'])
        worksheet.write('I%s' %(row+1), 'Date', wbf['header'])
        worksheet.write('J%s' %(row+1), 'Start Date', wbf['header'])
        worksheet.write('K%s' %(row+1), 'End Date', wbf['header'])
        worksheet.write('L%s' %(row+1), 'Product ID', wbf['header'])
        worksheet.write('M%s' %(row+1), 'Kode Type', wbf['header'])
        worksheet.write('N%s' %(row+1), 'Kode Warna', wbf['header'])
        worksheet.write('O%s' %(row+1), 'Qty Order', wbf['header'])
        worksheet.write('P%s' %(row+1), 'Qty Approve', wbf['header'])
        worksheet.write('Q%s' %(row+1), 'Qty', wbf['header'])

        row +=2
        no = 1
        where = " WHERE sd.is_download = False AND sd.status_api = 'done' AND sd.state = 'open'"
        if self.division:
            where += " AND sd.division = '%s'" %(str(self.division))   
        if self.type_id:
            where += " AND sd.type_id = %d" %(self.type_id.id)
                    

        query = """
                    SELECT rb.code as code_branch,
                        rb.name as nama_branch,
                        rp.name as nama_dealer,
                        pot.name as type_order,
                        sd.date as date,
                        sd.start_date as start_date,
                        sd.end_date as end_date,
                        pt.name as kode_type,
                        pav.name as kode_warna,
                        sdl.requested_qty as qty_request,
                        sdl.approved_qty as qty_approved,
                        sdl.qty as qty,
                        sd.name as name,
                        sd.dms_po_name as po_name,
                        sd.division as division,
                        pp.id as prod_id
                    FROM wtc_stock_distribution sd
                    INNER JOIN wtc_stock_distribution_line sdl ON sdl.distribution_id = sd.id 
                    LEFT JOIN wtc_branch rb ON rb.id = sd.branch_id
                    LEFT JOIN res_partner rp ON rp.id = sd.dealer_id
                    LEFT JOIN wtc_purchase_order_type pot ON pot.id = sd.type_id
                    LEFT JOIN product_product pp ON pp.id = sdl.product_id 
                    INNER JOIN product_template pt ON pt.id = pp.product_tmpl_id 
                    LEFT JOIN product_attribute_value_product_product_rel rel ON rel.prod_id = pp.id
                    LEFT JOIN product_attribute_value pav ON pav.id = rel.att_id                     
                    %s
                    ORDER BY sd.id ASC  
                """ %(where)
        print "ddddddd",query

        self._cr.execute (query)
        ress =  self._cr.dictfetchall()
        for res in ress:
            code_branch = res.get('code_branch')
            nama_branch = res.get('nama_branch')
            nama_dealer = res.get('nama_dealer')
            type_order = res.get('type_order')
            date = res.get('date')
            start_date = res.get('start_date')
            end_date = res.get('end_date')
            kode_type = res.get('kode_type')
            kode_warna = res.get('kode_warna')
            qty_request = res.get('qty_request')
            qty_approved  = res.get('qty_approved')
            qty = res.get('qty')
            name = res.get('name')
            po_name = res.get('po_name')
            division = res.get('division')
            prod_id =  res.get('prod_id')

            worksheet.write('A%s' % row, no , wbf['content_number']) 
            worksheet.write('B%s' % row, name , wbf['content']) 
            worksheet.write('C%s' % row, po_name , wbf['content']) 
            worksheet.write('D%s' % row, code_branch , wbf['content']) 
            worksheet.write('E%s' % row, nama_branch , wbf['content']) 
            worksheet.write('F%s' % row, nama_dealer , wbf['content']) 
            worksheet.write('G%s' % row, type_order , wbf['content']) 
            worksheet.write('H%s' % row, division , wbf['content_number']) 
            worksheet.write('I%s' % row, date , wbf['content']) 
            worksheet.write('J%s' % row, start_date , wbf['content']) 
            worksheet.write('K%s' % row, end_date , wbf['content']) 
            worksheet.write('L%s' % row, prod_id , wbf['content']) 
            worksheet.write('M%s' % row, kode_type , wbf['content']) 
            worksheet.write('N%s' % row, kode_warna , wbf['content']) 
            worksheet.write('O%s' % row, qty_request , wbf['content_float']) 
            worksheet.write('P%s' % row, qty_approved , wbf['content_float']) 
            worksheet.write('Q%s' % row, qty, wbf['content_float_right']) 
            no+=1
            row+=1

        worksheet.write('A%s' %row, "" , wbf['footer'])
        worksheet.write('B%s' %row, "" , wbf['footer'])
        worksheet.write('C%s' %row, "" , wbf['footer'])
        worksheet.write('D%s' %row, "" , wbf['footer'])
        worksheet.write('E%s' %row, "" , wbf['footer'])
        worksheet.write('F%s' %row, "" , wbf['footer'])
        worksheet.write('G%s' %row, "" , wbf['footer'])
        worksheet.write('H%s' %row, "" , wbf['footer'])
        worksheet.write('I%s' %row, "" , wbf['footer'])
        worksheet.write('J%s' %row, "" , wbf['footer'])
        worksheet.write('K%s' %row, "" , wbf['footer'])
        worksheet.write('L%s' %row, "" , wbf['footer'])
        worksheet.write('M%s' %row, "" , wbf['footer'])
        worksheet.write('N%s' %row, "" , wbf['footer'])
        worksheet.write('O%s' %row, "" , wbf['footer'])
        worksheet.write('P%s' %row, "" , wbf['footer'])
        worksheet.write('Q%s' %row, "" , wbf['footer'])
        row += 2

        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write({'file_download':out, 'name': filename})
        fp.close()
        result = self.ids[0]
        return result