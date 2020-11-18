import time
from openerp.osv import fields, osv
from openerp import api, fields, models
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.tools import float_compare
from openerp.exceptions import Warning
from datetime import date, datetime, timedelta
from openerp import SUPERUSER_ID
import base64
import xlrd

# Excel
import cStringIO
from cStringIO import StringIO
import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell
import os

class CustomerPaymentImportWizard(models.TransientModel):
    _name = "teds.customer.payment.import.wizard"

    def _get_default_branch(self):
        branch = self.env['wtc.branch'].search([('code','=','HHO')],limit=1).id
        return branch

    def _get_default_partner(self):
        partner = self.env['res.partner'].search([('default_code','=','FIF')],limit=1).id
        return partner

    @api.multi
    def _compute_amount_unreconcile(self):
        for me in self:
            me.amount_unreconcile_show = me.amount_unreconcile

    wbf = {}

    branch_id = fields.Many2one('wtc.branch','Branch',default=_get_default_branch)
    file_import = fields.Binary('File Import')
    file_export = fields.Binary('File Export')
    name = fields.Char('File Name')
    division = fields.Selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umumum'),('Finance','Finance')],default="Unit")
    partner_id = fields.Many2one('res.partner','Finance Company',domain=[('finance_company','=',True)],default=_get_default_partner)
    move_line_id = fields.Many2one('account.move.line','No HL',domain="[('account_id.type','=','payable'),('credit','!=',0),('reconcile_id','=',False),('partner_id','=',partner_id),('branch_id','=',branch_id)]")
    amount_unreconcile = fields.Float('Open Balance')
    amount_unreconcile_show = fields.Float('Open Balance',compute="_compute_amount_unreconcile",readonly=True)

    journal_id = fields.Many2one('account.journal','Payment Method',domain="[('type','in',('bank','cash','edc')),('branch_id','=',branch_id)]")

    state_x = fields.Selection([('choose','choose'),('get','get')], default='choose')

    @api.onchange('move_line_id')
    def onchange_open_balance(self):
        if self.move_line_id:
            self.amount_unreconcile = abs(self.move_line_id.amount_residual_currency)
            self.amount_unreconcile_show = abs(self.move_line_id.amount_residual_currency)
            
    
    @api.multi
    def add_workbook_format(self,workbook):      
        self.wbf['header'] = workbook.add_format({'bold': 1,'align': 'center','bg_color': '#E67E22','font_color': '#FFFFFF'})
        self.wbf['header'].set_border()
        self.wbf['header'].set_align('vcenter')
        self.wbf['header'].set_font_size(12)

        self.wbf['header_no'] = workbook.add_format({'bold': 1,'align': 'center','bg_color': '#E67E22','font_color': '#FFFFFF'})
        self.wbf['header_no'].set_border()
        self.wbf['header_no'].set_align('vcenter')
        self.wbf['header_no'].set_font_size(12)
                
        self.wbf['content'] = workbook.add_format()
        self.wbf['content'].set_left()
        self.wbf['content'].set_right()         

        self.wbf['content_float'] = workbook.add_format({'align': 'right','num_format': '#,##0.00'})
        self.wbf['content_float'].set_right() 
        self.wbf['content_float'].set_left()

        return workbook

    @api.multi
    def excel_report(self):
        # try:
            lot_excel = {}
            # Simpan data no mesin ke lots
            data = base64.decodestring(self.file_import)
            excel = xlrd.open_workbook(file_contents = data)  
            sh = excel.sheet_by_index(0)  
            
            for rx in range(1,sh.nrows):
                no_mesin = str([sh.cell(rx, ry).value for ry in range(sh.ncols)] [21])
                chassis_no = str([sh.cell(rx, ry).value for ry in range(sh.ncols)] [22])
                nilai = int([sh.cell(rx, ry).value for ry in range(sh.ncols)] [12])
                customer = str([sh.cell(rx, ry).value for ry in range(sh.ncols)] [16])

                if not lot_excel.get(no_mesin):
                    lot_excel[no_mesin] ={
                        'nilai':nilai,
                        'chassis_no':chassis_no,
                        'customer':customer,
                    }            
            
            # Excel
            fp = StringIO()
            workbook = xlsxwriter.Workbook(fp)        
            workbook = self.add_workbook_format(workbook)
            wbf = self.wbf
            # ---------Sheet 1------------#
            worksheet1 = workbook.add_worksheet('Data Selisih Amount')
            worksheet1.set_column('A1:A1', 18)
            worksheet1.set_column('B1:B1', 20)
            worksheet1.set_column('C1:C1', 20)
            worksheet1.set_column('D1:D1', 20)
            worksheet1.set_column('E1:E1', 20)


            row_1 = 2
            worksheet1.write('A1', 'No Mesin' , wbf['header'])
            worksheet1.write('B1', 'No Sale Order' , wbf['header'])
            worksheet1.write('C1', 'Open Balance' , wbf['header'])
            worksheet1.write('D1', 'Pencairan FIF' , wbf['header'])
            worksheet1.write('E1', 'Selisih' , wbf['header'])

            # ---------Sheet 2------------#        
            worksheet2 = workbook.add_worksheet('Data Not Found')
            worksheet2.set_column('A1:A1', 18)
            worksheet2.set_column('B1:B1', 20)
            worksheet2.set_column('C1:C1', 25)


            row_2 = 2
            worksheet2.write('A1', 'No Mesin' , wbf['header'])
            worksheet2.write('B1', 'No Chassis' , wbf['header'])
            worksheet2.write('C1', 'Customer' , wbf['header'])
            
            # ---------Sheet 3------------#
            worksheet3 = workbook.add_worksheet('Data Customer Payment')
            worksheet3.set_column('A1:A1', 23)
            worksheet3.set_column('B1:B1', 13)
            worksheet3.set_column('C1:C1', 20)
            worksheet3.set_column('D1:D1', 19)
            worksheet3.set_column('E1:E1', 19)
            worksheet3.set_column('F1:F1', 16)

            
            row_3 = 2
            worksheet3.write('A1', 'Customer Payment' , wbf['header'])
            worksheet3.write('B1', 'Code Cabang' , wbf['header'])
            worksheet3.write('C1', 'Nama Cabang' , wbf['header'])
            worksheet3.write('D1', 'No SL' , wbf['header'])
            worksheet3.write('E1', 'No SO' , wbf['header'])
            worksheet3.write('F1', 'Alokasi' , wbf['header'])

        
            query = """
                SELECT
                dso.branch_id
                , b.code as code_cabang
                , b.name as nama_cabang
                , lot.name as no_mesin
                , aml.id as aml_id
                , aml.account_id
                , aml.debit
                , aml.date as aml_date
                , aml.date_maturity
                , dso.name as no_so
                , am.name as no_sl
                FROM stock_production_lot lot
                INNER JOIN dealer_sale_order dso ON dso.id = lot.dealer_sale_order_id
                INNER JOIN wtc_branch b ON b.id = dso.branch_id
                INNER JOIN account_invoice ai ON ai.transaction_id = dso.id AND ai.model_id = (select id from ir_model where model = 'dealer.sale.order') and ai.tipe = 'finco'
                INNER JOIN account_move am ON am.id = ai.move_id
                INNER JOIN account_move_line aml ON aml.move_id = am.id AND aml.name = dso.name
                INNER JOIN account_account aa ON aa.id = ai.account_id
                WHERE  aml.partner_id = %d
                AND aml.reconcile_id IS NULL
                AND aa.code = '11210101'
                AND lot.name in %s
                ORDER BY am.name asc
            """ % (self.partner_id.id,str(tuple(lot_excel.keys())).replace(',)', ')'))
            self._cr.execute(query)
            ress = self._cr.dictfetchall()

            lot_sl = []
            branches = {}
            paid_amount = 0
            for res in ress:
                no_mesin = res.get('no_mesin') 
                if no_mesin not in lot_sl:
                    lot_sl.append(no_mesin)
                
                aml_id = res.get('aml_id')
                aml_obj = self.env['account.move.line'].sudo().browse(aml_id)

                branch_id = res.get('branch_id')
                account_id = res.get('account_id')
                debit = aml_obj.amount_residual_currency
                aml_date = res.get('aml_date')
                date_maturity = res.get('date_maturity')
                no_so = res.get('no_so')
                no_sl = res.get('no_sl')
                code_cabang = res.get('code_cabang')
                nama_cabang = res.get('nama_cabang')

                nilai_lot = lot_excel.get(no_mesin).get('nilai',0)
                selisih = (debit - nilai_lot) * -1
                alokasi = debit
                reconcile = True
                if nilai_lot > debit:
                    alokasi = debit
                    reconcile = True

                    worksheet1.write('A%s' %(row_1), no_mesin, wbf['content'])
                    worksheet1.write('B%s' %(row_1), no_so, wbf['content'])
                    worksheet1.write('C%s' %(row_1), debit, wbf['content_float'])
                    worksheet1.write('D%s' %(row_1), nilai_lot, wbf['content_float'])
                    worksheet1.write('E%s' %(row_1), selisih, wbf['content_float'])
                    row_1 += 1
                    
                elif nilai_lot < debit:
                    reconcile = False
                    alokasi = nilai_lot

                    worksheet1.write('A%s' %(row_1), no_mesin, wbf['content'])
                    worksheet1.write('B%s' %(row_1), no_so, wbf['content'])
                    worksheet1.write('C%s' %(row_1), debit, wbf['content_float'])
                    worksheet1.write('D%s' %(row_1), nilai_lot, wbf['content_float'])
                    worksheet1.write('E%s' %(row_1), selisih, wbf['content_float'])
                    row_1 += 1

                if not branches.get(branch_id):
                    branches[branch_id] = {'line_cr_ids':[
                        [0,False,{
                            'move_line_id':aml_id,
                            'name':no_so,
                            'amount_original':debit,
                            'amount_unreconciled':debit,
                            'date_original':aml_date,
                            'date_due':date_maturity,
                            'type':'cr',
                            'account_id':account_id,
                            'reconcile':reconcile,
                            'amount':alokasi
                            }]
                        ],
                        'amount_reconcile':alokasi,
                        'code_cabang':code_cabang,
                        'nama_cabang':nama_cabang,
                        'row':row_3
                    }

                else:
                    branches[branch_id]['line_cr_ids'].append([0,False,{
                        'move_line_id':aml_id,
                        'name':no_so,
                        'amount_original':debit,
                        'amount_unreconciled':debit,
                        'date_original':aml_date,
                        'date_due':date_maturity,
                        'type':'cr',    
                        'account_id':account_id,
                        'reconcile':reconcile,
                        'amount':alokasi
                    }])
                    branches[branch_id]['amount_reconcile'] += alokasi
                    
                paid_amount += alokasi

                worksheet3.write('B%s' %(row_3), '' , wbf['content'])
                worksheet3.write('C%s' %(row_3), '' , wbf['content'])
                worksheet3.write('D%s' %(row_3), no_sl , wbf['content'])
                worksheet3.write('E%s' %(row_3), no_so , wbf['content'])
                worksheet3.write('F%s' %(row_3), alokasi , wbf['content_float'])
                row_3 += 1
                

            if paid_amount > self.amount_unreconcile:
                raise Warning('Total Amount Pembayaran lebih besar dari Amount Balance ! \n Amount Pembayaran %s, Amount Balance %s'%(paid_amount,self.amount_unreconcile))

            company_id = self.env['res.company']._company_default_get('account.voucher')
            currency_id = False
            if self.journal_id.currency:
                currency_id = journal.currency.id
            else:
                currency_id = self.journal_id.company_id.currency_id.id
            
            account_id = self.journal_id.default_credit_account_id.id or self.journal_id.default_debit_account_id.id

            lot_difrent = list(set(lot_excel) - set(lot_sl))
            for lot_d in lot_difrent:
                chassis =  lot_excel.get(lot_d).get('chassis_no')
                nama_customer = lot_excel.get(lot_d).get('customer')
                worksheet2.write('A%s' %(row_2), lot_d, wbf['content'])
                worksheet2.write('B%s' %(row_2), chassis, wbf['content'])
                worksheet2.write('C%s' %(row_2), nama_customer, wbf['content'])

                row_2 += 1

            new_branch = False
            tgl = ((datetime.now()-timedelta(days=1)).date()).strftime("%d%m%y")
            for key, value in branches.items():
                memo = "ADV DISBURSE FIF %s %s" %(tgl,value.get('code_cabang'))
                vals_payment =  {
                    'name':memo,
                    'branch_id':self.branch_id.id,
                    'division':self.division,
                    'inter_branch_id':key,
                    'partner_type':'finance_company',
                    'partner_id':self.partner_id.id,
                    'journal_id':self.journal_id.id,
                    'company_id':company_id,
                    'currency_id':currency_id,
                    'account_id':account_id,
                    'type':'receipt',
                    'line_cr_ids':value.get('line_cr_ids'),
                    'line_dr_ids':[[0,False,{
                        'move_line_id':self.move_line_id.id,
                        'account_id':self.move_line_id.account_id.id,
                        'name':self.move_line_id.name,
                        'amount_original':self.move_line_id.amount_currency,
                        'amount_unreconciled':self.move_line_id.amount_residual_currency,
                        'date_original':self.move_line_id.date,
                        'date_due':self.move_line_id.date_maturity,
                        'type':'dr',            
                        'amount':value.get('amount_reconcile')
                    }]]
                }
                create_ar = self.env['wtc.account.voucher'].create(vals_payment)
                # AR Replace Disini
                worksheet3.write('A%s' %(value.get('row')), create_ar.number , wbf['content'])
                worksheet3.write('B%s' %(value.get('row')), value.get('code_cabang') , wbf['content'])
                worksheet3.write('C%s' %(value.get('row')), value.get('nama_cabang') , wbf['content'])
            
            workbook.close()
            out=base64.encodestring(fp.getvalue())

            filename = 'Data Advance %s.xlsx' %((datetime.now()+timedelta(hours=7)).strftime("%d-%m-%Y %H:%M:%S"))
            self.write({'state_x':'get','file_export':out,'name':filename})
            fp.close()
            form_id = self.env.ref('teds_customer_payment_import.view_teds_customer_payment_import_wizard').id
            
            return {
                'name': ('Download XLS'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'teds.customer.payment.import.wizard',
                'res_id': self.ids[0],
                'view_id': False,
                'views': [(form_id, 'form')],
                'type': 'ir.actions.act_window',
                'target': 'current'
            }
        # except Exception as err:
        #     raise Warning(err)
    