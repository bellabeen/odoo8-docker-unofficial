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
from openerp.sql_db import db_connect
from openerp.tools.config import config

class wtc_report_asset_wizard(osv.osv_memory):
   
    _name = "wtc.report.asset.wizard"
    _description = "Asset Report"

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
        res = super(wtc_report_asset_wizard, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        branch_ids = self._get_branch_ids(cr, uid, context)
        
        doc = etree.XML(res['arch'])
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
        
        for node in nodes_branch :
            node.set('domain', '[("id", "in", '+ str(branch_ids)+')]')
        res['arch'] = etree.tostring(doc)
        return res
        
    _columns = {
        'state_x': fields.selection( ( ('choose','choose'),('get','get'))), #xls
        'data_x': fields.binary('File', readonly=True),
        'name': fields.char('Filename', 100, readonly=True), 
        'status': fields.selection([('all','All'), ('active','Active'), ('disposed','Disposed'), ('draft','Draft')], 'Status', required=True, change_default=True, select=True),
        'option': fields.selection([('fixed','Asset'), ('prepaid','Prepaid')], 'Option', required=True, change_default=True, select=True),
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'branch_ids': fields.many2many('wtc.branch', 'wtc_report_asset_branch_rel', 'wtc_report_asset_wizard_id',
            'branch_id', 'Branches', copy=False),
        'category_ids': fields.many2many('account.asset.category', 'wtc_report_asset_categ_rel', 'wtc_report_asset_wizard_id',
            'category_id', 'Category', copy=False),
    }

    _defaults = {
        'state_x': lambda *a: 'choose',
        'start_date':datetime.today(),
        'status': 'all',
        'option':'fixed',
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
        return self._print_excel_report(cr, uid, ids, data, context=context)
    
    def _print_excel_report(self, cr, uid, ids, data, context=None):        

        status = data['status']
        option = data['option']
        branch_ids = data['branch_ids']
        category_ids = data['category_ids']

        query = """ 
            select 
            asset.division as division, 
            branch.code as branch_code, 
            asset.code as asset_code, 
            asset.name as asset_name, 
            category.code as category_code, 
            asset.method_number as asset_method_number, 
            account_asset.code as account_asset_code,  
            account_expense.code as account_expense_code, 
            asset.real_purchase_date as asset_purchase_date, 
            coalesce(asset.real_purchase_value,0) as asset_real_purchase_value, 
            case when coalesce(asset.method_number,0) = 0 then 0
                else (coalesce(asset.purchase_value,0) - coalesce(asset.salvage_value,0))/coalesce(asset.method_number,0) end as susut_perbulan,            
            coalesce(depreline.cnt,0) as jumlah_susut, 
            coalesce(asset.real_purchase_value,0) - coalesce(asset.purchase_value,0) + coalesce(susut.amount,0) as total_depresiasi,
            coalesce(asset.purchase_value,0) - coalesce(susut.amount,0) - coalesce(asset.salvage_value,0) as residual_value,
            asset.state as state
            , asset.register_no
            , ra.name as receive_name
            , rp.default_code as vendor_code
            , rp.name as vendor_name
            , disposal.name as disposal_name
            , disposal.date as disposal_date
            , coalesce(disposal.amount_subtotal,0) as disposal_price
            , coalesce(disposal.tax,0) as disposal_tax
            , rp2.default_code as disposal_vendor_code
            , rp2.name as disposal_vendor_name
            , asset.purchase_date as purchase_date
            from account_asset_asset asset
            left join wtc_transfer_asset ra on ra.id = asset.receive_id and ra.state = 'done'
            left join res_partner rp on rp.id = asset.partner_id
            left join 
            (select amount,asset_id,cnt from account_asset_depreciation_line inner join 
                (select max(id) as max_id,count(id) as cnt
                    from account_asset_depreciation_line where move_check = true GROUP BY asset_id) 
                as max_line ON id=max_line.max_id) 
            as depreline ON depreline.asset_id = asset.id
            left join 
            (SELECT l.asset_id as asset_id, SUM(abs(l.debit-l.credit)) AS amount FROM account_move_line l GROUP BY l.asset_id) 
            as susut ON susut.asset_id = asset.id
            left join
            (select dal.asset_id, da.name, da.date, da.partner_id
                , dal.amount_subtotal, (dal.amount-dal.amount_subtotal) as tax
                from wtc_disposal_asset da 
                inner join wtc_disposal_asset_line dal on da.id = dal.disposal_id 
                where da.state = 'confirm') 
            as disposal on asset.id = disposal.asset_id 
            left join res_partner rp2 on rp2.id = disposal.partner_id
            left join wtc_branch branch ON branch.id = asset.branch_id 
            left join account_asset_category category ON category.id = asset.category_id 
            left join account_account account_asset ON account_asset.id = category.account_asset_id 
            left join account_account account_expense ON account_expense.id = category.account_expense_depreciation_id
                
            """

        query_where = " WHERE 1=1  "
        if status == 'all' :
            query_where += " AND 1=1 "
        elif status == 'draft' :
            query_where += " AND asset.state = 'draft' "
        elif status == 'active' :
            query_where += " AND asset.state in ('open','CIP','close') "
        elif status == 'disposed' :
            query_where += " AND asset.state = 'disposed'  "
        
        if option == 'fixed' :
            query_where += " AND category.type = 'fixed'"
        elif option == 'prepaid' :
            query_where += " AND category.type = 'prepaid'"   
        if branch_ids :
            query_where += " AND branch.id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')           
        if category_ids :
            query_where += " AND category.id in %s" % str(
                tuple(category_ids)).replace(',)', ')')

        query_order = " order by branch.code, asset.code, asset.name "
        
        conn_str = 'postgresql://' \
           + config.get('report_db_user', False) + ':' \
           + config.get('report_db_password', False) + '@' \
           + config.get('report_db_host', False) + ':' \
           + config.get('report_db_port', False) + '/' \
           + config.get('report_db_name', False)
        conn = db_connect(conn_str, True)
        cur = conn.cursor(False)
        cur.autocommit(True)

        # cr.execute (query+query_where+query_order)
        cur.execute (query+query_where+query_order)
        # ress = cr.fetchall()
        ress = cur.fetchall()
        cur.close()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Penjualan')
        worksheet.set_column('B1:B1', 13)
        worksheet.set_column('C1:C1', 13)
        worksheet.set_column('D1:D1', 17)
        worksheet.set_column('E1:E1', 18)
        worksheet.set_column('F1:F1', 11)
        worksheet.set_column('G1:G1', 11)
        worksheet.set_column('H1:H1', 11)
        worksheet.set_column('I1:I1', 11)
        worksheet.set_column('J1:J1', 13)
        worksheet.set_column('K1:K1', 15)
        worksheet.set_column('L1:L1', 20)
        worksheet.set_column('M1:M1', 17)
        worksheet.set_column('N1:N1', 20)
        worksheet.set_column('O1:O1', 20)
        worksheet.set_column('P1:P1', 8)       
        worksheet.set_column('Q1:Q1', 20)
        worksheet.set_column('R1:R1', 20)
        worksheet.set_column('S1:S1', 18)
        worksheet.set_column('T1:T1', 25)
        worksheet.set_column('U1:U1', 20)
        worksheet.set_column('V1:V1', 13)
        worksheet.set_column('W1:W1', 20)
        worksheet.set_column('X1:X1', 20)
        worksheet.set_column('Y1:Y1', 18)
        worksheet.set_column('Z1:Z1', 20)
        worksheet.set_column('AA1:AA1', 20)

        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        filename = 'Report Penjualan '+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report Penjualan' , wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s '%(str(date)) , wbf['company'])
        row=4
        rowsaldo = row
        row+=1
        worksheet.write('A%s' % (row+1), 'No' , wbf['header'])
        worksheet.write('B%s' % (row+1), 'DIV' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'CABANG' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'KODE' , wbf['header'])        
        worksheet.write('E%s' % (row+1), 'NAMA AKTIVA' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'KATEGORY' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'LAMA SST' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'NO REK' , wbf['header'])
        worksheet.write('I%s' % (row+1), 'NO REK BIAYA' , wbf['header'])
        worksheet.write('J%s' % (row+1), 'TGL AWAL' , wbf['header'])
        worksheet.write('K%s' % (row+1), 'NILAI AWAL' , wbf['header'])
        worksheet.write('L%s' % (row+1), 'SST PERBULAN' , wbf['header'])
        worksheet.write('M%s' % (row+1), 'JML SUSUT' , wbf['header'])
        worksheet.write('N%s' % (row+1), 'TOTAL DEPRESIASI' , wbf['header'])
        worksheet.write('O%s' % (row+1), 'NILAI AKHIR' , wbf['header'])
        worksheet.write('P%s' % (row+1), 'STATE' , wbf['header'])
        worksheet.write('Q%s' % (row+1), 'NO REGISTER' , wbf['header'])
        worksheet.write('R%s' % (row+1), 'RECEIVE ASSET NUMBER' , wbf['header'])
        worksheet.write('S%s' % (row+1), 'VENDOR CODE' , wbf['header'])
        worksheet.write('T%s' % (row+1), 'VENDOR NAME' , wbf['header'])
        worksheet.write('U%s' % (row+1), 'DISPOSAL NUMBER' , wbf['header'])
        worksheet.write('V%s' % (row+1), 'DISPOSAL DATE' , wbf['header'])
        worksheet.write('W%s' % (row+1), 'DISPOSAL PRICE' , wbf['header'])
        worksheet.write('X%s' % (row+1), 'DISPOSAL TAX' , wbf['header'])
        worksheet.write('Y%s' % (row+1), 'DISPOSAL VENDOR CODE' , wbf['header'])
        worksheet.write('Z%s' % (row+1), 'DISPOSAL VENDOR NAME' , wbf['header'])
        worksheet.write('AA%s' % (row+1), 'EFFECTIVE DATE' , wbf['header'])

        row+=2
        no = 1
        row1 = row
        
        for res in ress:
            
            div = str(res[0].encode('ascii','ignore').decode('ascii')) if res[0] != None else '',
            cabang = str(res[1].encode('ascii','ignore').decode('ascii')) if res[1] != None else '',
            kode = str(res[2].encode('ascii','ignore').decode('ascii')) if res[2] != None else '',
            nama_aktiva = str(res[3].encode('ascii','ignore').decode('ascii')) if res[3] != None else '',
            kategori = str(res[4].encode('ascii','ignore').decode('ascii')) if res[4] != None else '',
            lama_sst = res[5] if res[5] != None else '',
            no_rek = str(res[6].encode('ascii','ignore').decode('ascii')) if res[6] != None else '',
            no_rek_bia = str(res[7].encode('ascii','ignore').decode('ascii')) if res[7] != None else '',
            tgl_awal = datetime.strptime(res[8], "%Y-%m-%d").date() if res[8] else ''
            nilai_awal = res[9] if res[9] != None else '',
            sst_perbulan = res[10] if res[10] != None else '',
            sst_ke = res[11] if res[11] != None else '',
            total_depresiasi = res[12] if res[12] != None else '',
            nilai_akhir = res[13] if res[13] != None else '',
            state =str(res[14])
            no_register = str(res[15].encode('ascii','ignore').decode('ascii')) if res[15] != None else '',
            receive_name = str(res[16].encode('ascii','ignore').decode('ascii')) if res[16] != None else '',
            vendor_code = str(res[17].encode('ascii','ignore').decode('ascii')) if res[17] != None else '',
            vendor_name = str(res[18].encode('ascii','ignore').decode('ascii')) if res[18] != None else '',
            disposal_name = str(res[19].encode('ascii','ignore').decode('ascii')) if res[19] != None else '',
            disposal_code = str(res[20].encode('ascii','ignore').decode('ascii')) if res[20] != None else '',
            disposal_price = res[21]
            disposal_tax = res[22]
            disposal_vendor_code = str(res[23].encode('ascii','ignore').decode('ascii')) if res[23] != None else '',
            disposal_vendor_name = str(res[24].encode('ascii','ignore').decode('ascii')) if res[24] != None else '',
            purchase_date = str(res[25].encode('ascii','ignore').decode('ascii')) if res[25] != None else '',

            worksheet.write('A%s' % row, no , wbf['content_number'])                    
            worksheet.write('B%s' % row, div[0] if type(div) == tuple else div , wbf['content'])
            worksheet.write('C%s' % row,  cabang[0] if type(cabang) == tuple else cabang, wbf['content'])
            worksheet.write('D%s' % row,  kode[0] if type(kode) == tuple else kode, wbf['content'])
            worksheet.write('E%s' % row,  nama_aktiva[0] if type(nama_aktiva) == tuple else nama_aktiva, wbf['content'])
            worksheet.write('F%s' % row,  kategori[0] if type(kategori) == tuple else kategori, wbf['content'])
            worksheet.write('G%s' % row,  lama_sst[0] if type(lama_sst) == tuple else lama_sst, wbf['content_number'])
            worksheet.write('H%s' % row,  no_rek[0] if type(no_rek) == tuple else no_rek, wbf['content']) 
            worksheet.write('I%s' % row,  no_rek_bia[0] if type(no_rek_bia) == tuple else no_rek_bia, wbf['content'])  
            worksheet.write('J%s' % row,  tgl_awal[0] if type(tgl_awal) == tuple else tgl_awal, wbf['content_date'])
            worksheet.write('K%s' % row,  nilai_awal[0] if type(nilai_awal) == tuple else nilai_awal, wbf['content_float'])
            worksheet.write('L%s' % row,  sst_perbulan[0] if type(sst_perbulan) == tuple else sst_perbulan, wbf['content_float'])
            worksheet.write('M%s' % row,  sst_ke[0] if type(sst_ke) == tuple else sst_ke, wbf['content_number'])
            worksheet.write('N%s' % row,  total_depresiasi[0] if type(total_depresiasi) == tuple else total_depresiasi, wbf['content_float'])
            worksheet.write('O%s' % row,  nilai_akhir[0] if type(nilai_akhir) == tuple else nilai_akhir, wbf['content_float'])
            worksheet.write('P%s' % row,  state[0] if type(state) == tuple else state, wbf['content'])
            worksheet.write('Q%s' % row,  no_register[0] if type(no_register) == tuple else no_register, wbf['content'])
            worksheet.write('R%s' % row,  receive_name[0] if type(receive_name) == tuple else receive_name, wbf['content'])
            worksheet.write('S%s' % row,  vendor_code[0] if type(vendor_code) == tuple else vendor_code, wbf['content'])
            worksheet.write('T%s' % row,  vendor_name[0] if type(vendor_name) == tuple else vendor_name, wbf['content'])
            worksheet.write('U%s' % row,  disposal_name[0] if type(disposal_name) == tuple else disposal_name, wbf['content'])
            worksheet.write('V%s' % row,  disposal_code[0] if type(disposal_code) == tuple else disposal_code, wbf['content'])
            worksheet.write('W%s' % row,  disposal_price[0] if type(disposal_price) == tuple else disposal_price, wbf['content_float'])
            worksheet.write('X%s' % row,  disposal_tax[0] if type(disposal_tax) == tuple else disposal_tax, wbf['content_float'])
            worksheet.write('Y%s' % row,  disposal_vendor_code[0] if type(disposal_vendor_code) == tuple else disposal_vendor_code, wbf['content'])
            worksheet.write('Z%s' % row,  disposal_vendor_name[0] if type(disposal_vendor_name) == tuple else disposal_vendor_name, wbf['content'])
            worksheet.write('AA%s' % row,  purchase_date[0] if type(purchase_date) == tuple else purchase_date, wbf['content'])
            no+=1
            row+=1
        
        worksheet.autofilter('A6:Q%s' % (row))  
        worksheet.freeze_panes(6, 3)
         
        worksheet.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])  

        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_asset', 'view_report_asset_wizard')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.report.asset.wizard',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }

wtc_report_asset_wizard()
