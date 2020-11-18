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

class wtc_report_piutang(osv.osv_memory):
   
    _name = "wtc.report.piutang.wizard"
    _description = "Piutang Report"

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
        res = super(wtc_report_piutang, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        branch_ids_user=self.pool.get('res.users').browse(cr,uid,uid).branch_ids
        branch_ids=[b.id for b in branch_ids_user]
        
        doc = etree.XML(res['arch'])      
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
        for node in nodes_branch:
            node.set('domain', '[("id", "in", '+ str(branch_ids)+')]')
        res['arch'] = etree.tostring(doc)
        return res
    
    def per_tgl_change(self, cr, uid, ids, per_tgl, context=None):   
        if per_tgl == False :   
            return {'value':{'per_tgl':datetime.now(), 'end_date':datetime.now()}}  
        return {'value':{'end_date':per_tgl}}
        
    _columns = {
        'state_x': fields.selection( ( ('choose','choose'),('get','get'))), #xls
        'data_x': fields.binary('File', readonly=True),
        'name': fields.char('Filename', 100, readonly=True),
        'division' : fields.selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum')],string='Division'),
        'options': fields.selection([('current','Current Outstanding Piutang'),('all','All Piutang'),('Unit','Piutang Unit'),('Other','Other Receivable')], 'Options', change_default=True, select=True), 
        'per_tgl': fields.date('Per Tanggal'),
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'status': fields.selection([('reconciled','Reconciled'),('outstanding','Outstanding')], 'Status', change_default=True, select=True),
        'branch_ids': fields.many2many('wtc.branch', 'wtc_report_piutang_branch_rel', 'wtc_report_piutang_wizard_id',
                                        'branch_id', 'Branch', copy=False),
        'partner_ids': fields.many2many('res.partner', 'wtc_report_piutang_partner_rel', 'wtc_report_piutang_wizard_id',
                                        'partner_id', 'Customer', copy=False, domain=[('customer','=',True)]),
        'account_ids': fields.many2many('account.account', 'wtc_report_piutang_account_rel', 'wtc_report_piutang_wizard_id',
                                        'account_id', 'Account', copy=False, domain=[('type','=','receivable')]),
        'journal_ids': fields.many2many('account.journal', 'wtc_report_piutang_journal_rel', 'wtc_report_piutang_wizard_id',
                                        'journal_id', 'Journal', copy=False, domain=[('type','in',['sale','purchase_refund'])])     
    }

    _defaults = {
        'state_x': lambda *a: 'choose',
        'options':'current',
        'status': 'outstanding',
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
        if len(data['branch_ids']) == 0 :
            data.update({'branch_ids': self._get_branch_ids(cr, uid, context)})
        account_ids = data['account_ids']  
        if len(data['account_ids']) == 0 : 
            account_ids = self.pool.get('account.account').search(cr, uid, [('type','=','receivable')])
            data.update({'account_ids': account_ids})            
        return self._print_excel_report(cr, uid, ids, data, context=context)
    
    def _print_excel_report(self, cr, uid, ids, data, context=None):
        
        branch_ids = data['branch_ids']
        partner_ids = data['partner_ids']
        account_ids = data['account_ids']
        journal_ids = data['journal_ids']
        options = data['options']
        start_date = data['start_date']
        end_date = data['end_date']          
        status = data['status']
        per_tgl = data['per_tgl'] 
        division = data['division']
            
        overdue = " current_date - aml.date_maturity "
        where_per_tgl_aml2 = " AND 1=1 "
        where_per_tgl_aml4 = " AND 1=1 "
        now_date = datetime.today().date()
        per_date = datetime.strptime(per_tgl, "%Y-%m-%d").date()
        if per_date < now_date:
            where_per_tgl_aml2 = " AND aml2.date <= '%s'" % str(per_tgl)
            where_per_tgl_aml4 = " AND aml4.date <= '%s'" % str(per_tgl)
            overdue = "'%s' - aml.date_maturity" % per_tgl
        
        query_where = ''
        if division :
            query_where += " AND aml.division = '%s'" % str(division)
        if start_date :
            query_where +=" AND aml.date >= '%s'" % str(start_date)
        if end_date :
            query_where +=" AND aml.date <= '%s'" % str(end_date)
        if status == 'reconciled' :
            query_where +=" AND (aml5.debit = aml5.credit) "
        elif status == 'outstanding' and options=='all':
            query_where +=" AND (aml5.debit is null or aml5.debit != aml5.credit) "
        if branch_ids :
            query_where +=" AND aml.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        if partner_ids :
            query_where +=" AND aml.partner_id in %s" % str(
                tuple(partner_ids)).replace(',)', ')')
        if account_ids :
            query_where +=" AND aml.account_id in %s" % str(
                tuple(account_ids)).replace(',)', ')')
        if journal_ids :
            query_where +=" AND aml.journal_id in %s" % str(
                tuple(journal_ids)).replace(',)', ')')
        
        query_select_unit = ""
        query_from_unit = ""
        if options == 'Unit' :
            query_select_unit = """ 
                , aml.id
                , COALESCE(partner.default_code, '') as qq_code
                , COALESCE(partner.name, '') as qq_name
                , lot.name
                , lot.chassis_no 
                , case  when sales_source='GC' then 'GC' 
                        when sales_source='TOP-PU' then 'TOP-PU' 
                        when sales_source not in ('TOP-PU','GC') and dso.finco_id is not null then 'Credit'
                        else 'Cash' end as jenis_penjualan
                """
            
            query_from_unit = """
                INNER JOIN account_invoice ai ON aml.move_id = ai.move_id AND ai.type = 'out_invoice' and aml.account_id = ai.account_id and ai.model_id in (select id from ir_model where model = 'dealer.sale.order')
                INNER JOIN dealer_sale_order dso ON ai.transaction_id = dso.id
                INNER JOIN dealer_sale_order_line dsol ON dso.id = dsol.dealer_sale_order_line_id
                INNER JOIN stock_production_lot lot ON dsol.lot_id = lot.id
                LEFT JOIN res_partner partner ON dso.partner_id = partner.id            
                """
                
        if options == 'Other' :
            query_select_unit = """
                , hre_create.name_related as u_create
                , hre_confirm.name_related as u_confirm  
                """
            
            query_from_unit = """
                inner join account_move am on aml.move_id=am.id
                inner join wtc_dn_nc dnnc on am.id=dnnc.move_id
                left join resource_resource res_create on dnnc.create_uid = res_create.user_id
                left join hr_employee hre_create on res_create.id=hre_create.resource_id
                left join resource_resource res_confirm on dnnc.confirm_uid = res_confirm.user_id
                left join hr_employee hre_confirm on res_confirm.id=hre_confirm.resource_id
                """
        if options=='current':
            query="""
            select b.code as cabang, 
            aml.division as division, 
            rp.default_code as partner_code, 
            rp.name as partner_name, 
            aa.code as account_code, 
            aa.sap as account_sap, 
            b.profit_centre as profit_centre, 
            aml.date as date_aml, 
            aml.date_maturity as due_date,
            %s as overdue, 
            aml.reconcile_id as status, 
            aml.reconcile_partial_id as partial, 
            aml.debit as debit, 
            aml.credit as credit, 
            aml.name as name, 
            aml.ref as reference, 
            j.name as journal_name, 
            m.name as invoice_name,
            A3.balance
            FROM 
            (
                (select id, debit-credit as balance 
                from account_move_line
                where reconcile_id is null and reconcile_partial_id is null
                and account_id in (select id from account_account where type = 'receivable')) 
            UNION
            (
                select a.id,a.balance 
                from (
                    SELECT min(id) as id, reconcile_partial_id, sum(debit-credit) as balance
                    from account_move_line 
                    where reconcile_partial_id is not NULL
                    and account_id in (select id from account_account where type = 'receivable')
                    GROUP BY reconcile_partial_id) AS a
            )) as A3 
            INNER JOIN account_move_line aml on aml.id = a3.id
            INNER JOIN account_account aa ON aml.account_id = aa.id
            LEFT JOIN wtc_branch b on aml.branch_id=b.id
            LEFT JOIN account_move m ON m.id = aml.move_id 
            LEFT JOIN res_partner rp on aml.partner_id=rp.id
            LEFT JOIN account_journal j ON j.id = aml.journal_id
            WHERE 1=1 %s
            """   % (overdue, query_where)
        else:    
            query = """
                SELECT
                b.code as cabang, 
                aml.division as division, 
                rp.default_code as partner_code, 
                rp.name as partner_name, 
                a.code as account_code, 
                a.sap as account_sap, 
                b.profit_centre as profit_centre, 
                aml.date as date_aml, 
                aml.date_maturity as due_date, 
                %s as overdue, 
                aml.reconcile_id as status, 
                aml.reconcile_partial_id as partial, 
                aml.debit as debit, 
                aml.credit as credit, 
                aml.name as name, 
                aml.ref as reference, 
                j.name as journal_name, 
                m.name as invoice_name, 
                CASE WHEN aml.reconcile_id IS NOT NULL THEN aml5.debit - aml5.credit 
                    WHEN aml.reconcile_partial_id IS NULL THEN aml.debit - aml.credit 
                    ELSE aml3.debit - aml3.credit 
                END as residual 
                %s
                
                FROM 
                account_move_line aml
                %s 
                LEFT JOIN (SELECT aml2.reconcile_partial_id, SUM(aml2.debit) as debit, SUM(aml2.credit) as credit
                FROM account_move_line aml2 
                WHERE aml2.reconcile_partial_id is not Null %s  
                GROUP BY aml2.reconcile_partial_id) aml3 on aml.reconcile_partial_id = aml3.reconcile_partial_id 
                LEFT JOIN (SELECT aml4.reconcile_id, SUM(aml4.debit) as debit, SUM(aml4.credit) as credit FROM account_move_line aml4 
                WHERE aml4.reconcile_id is not Null  %s 
                GROUP BY aml4.reconcile_id) aml5 on aml.reconcile_id = aml5.reconcile_id 
                LEFT JOIN wtc_branch b ON b.id = aml.branch_id 
                LEFT JOIN account_move m ON m.id = aml.move_id 
                LEFT JOIN res_partner rp ON rp.id = aml.partner_id 
                LEFT JOIN account_account a ON a.id = aml.account_id 
                LEFT JOIN account_journal j ON j.id = aml.journal_id
                
                where aml.debit > 0 %s
                
                order by b.code, aml.date, aml.name
                """ % (overdue, query_select_unit, query_from_unit, where_per_tgl_aml2, where_per_tgl_aml4, query_where)
        conn_str = 'postgresql://' \
           + config.get('report_db_user', False) + ':' \
           + config.get('report_db_password', False) + '@' \
           + config.get('report_db_host', False) + ':' \
           + config.get('report_db_port', False) + '/' \
           + config.get('report_db_name', False)
        conn = db_connect(conn_str, True)
        cur = conn.cursor(False)
        cur.autocommit(True)

        #cr.execute (query)
        cur.execute (query)
        #ress = cr.fetchall()
        ress = cur.fetchall()
        cur.close()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        
        if options in ('all','current'):
            wks_title = 'All Piutang'
        elif options == 'Unit':
            wks_title = 'Piutang Unit'
        else :
            wks_title = 'Other Receivable'
                
        #WKS 1
        worksheet = workbook.add_worksheet('%s' %(wks_title))
        worksheet.set_column('B1:B1', 9)
        worksheet.set_column('C1:C1', 12)
        worksheet.set_column('D1:D1', 16)
        worksheet.set_column('E1:E1', 30)
        worksheet.set_column('F1:F1', 11)
        worksheet.set_column('G1:G1', 28)
        worksheet.set_column('H1:H1', 21)
        worksheet.set_column('I1:I1', 35)
        worksheet.set_column('J1:J1', 16)
        worksheet.set_column('K1:K1', 16)
        worksheet.set_column('L1:L1', 9)
        worksheet.set_column('M1:M1', 13)
        worksheet.set_column('N1:N1', 20)
        worksheet.set_column('O1:O1', 20)
        worksheet.set_column('P1:P1', 20)
        worksheet.set_column('Q1:Q1', 20)
        worksheet.set_column('R1:R1', 20)
        worksheet.set_column('S1:S1', 20)
        worksheet.set_column('T1:T1', 20)
        worksheet.set_column('U1:U1', 20)
        worksheet.set_column('V1:V1', 20)
        worksheet.set_column('W1:W1', 20)        
        worksheet.set_column('X1:X1', 22)
        worksheet.set_column('Y1:Y1', 22)
        
        if options == 'Unit' : 
            worksheet.set_column('Z1:Z1', 20)
            worksheet.set_column('AA1:AA1', 20)
            worksheet.set_column('AB1:AB1', 22)
            worksheet.set_column('AC1:AC1', 22)
            worksheet.set_column('AD1:AD1', 22)
        elif options == 'Other':
            worksheet.set_column('Z1:Z1', 30)
            worksheet.set_column('AA1:AA1', 30)
                     
        
        get_date = self._get_default(cr, uid, date=True, context=context)
        date = get_date.strftime("%Y-%m-%d %H:%M:%S")
        date_date = get_date.strftime("%Y-%m-%d")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        date_title = per_tgl if per_tgl else date_date
        filename = 'Report %s ' %(wks_title) +str(date)+'.xlsx'  
        
        #WKS 1      
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report %s Per Tanggal %s '%(wks_title,str(date_title)) , wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date),str(end_date)) , wbf['company'])
        
        row=4   
        rowsaldo = row
        row+=1
        
        worksheet.merge_range('A%s:A%s' % (row,(row+1)), 'No' , wbf['header_no'])
        worksheet.merge_range('B%s:P%s' % (row,row), 'Piutang' , wbf['header'])        
        worksheet.write('B%s' % (row+1), 'Branch' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'Division' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'Partner Code' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'Partner Name' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'No Rek' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'No SUN' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'No Sistem' , wbf['header'])
        worksheet.write('I%s' % (row+1), 'Name' , wbf['header'])
        worksheet.write('J%s' % (row+1), 'Tanggal' , wbf['header'])
        worksheet.write('K%s' % (row+1), 'Tgl Jatuh Tempo' , wbf['header'])
        worksheet.write('L%s' % (row+1), 'Overdue' , wbf['header'])
        worksheet.write('M%s' % (row+1), 'Status' , wbf['header'])
        worksheet.write('N%s' % (row+1), 'Total Invoice' , wbf['header'])
        worksheet.write('O%s' % (row+1), 'Sisa Piutang' , wbf['header'])                
        worksheet.write('P%s' % (row+1), 'Current' , wbf['header'])
        worksheet.merge_range('Q%s:W%s' % (row,row), 'Overdue' , wbf['header'])                 
        worksheet.write('Q%s' % (row+1), 'Overdue 1 - 7' , wbf['header'])
        worksheet.write('R%s' % (row+1), 'Overdue 8 - 14' , wbf['header'])
        worksheet.write('S%s' % (row+1), 'Overdue 15 - 21' , wbf['header'])
        worksheet.write('T%s' % (row+1), 'Overdue 22 - 30' , wbf['header'])
        worksheet.write('U%s' % (row+1), 'Overdue 31 - 60' , wbf['header'])
        worksheet.write('V%s' % (row+1), 'Overdue 61 - 90' , wbf['header'])
        worksheet.write('W%s' % (row+1), 'Overdue > 90' , wbf['header'])
        worksheet.merge_range('X%s:Y%s' % (row,row), 'Reference' , wbf['header'])           
        worksheet.write('X%s' % (row+1), 'Ref' , wbf['header'])
        worksheet.write('Y%s' % (row+1), 'Scr' , wbf['header'])
        
        if options == 'Unit' : 
            worksheet.merge_range('Z%s:AA%s' % (row,row), 'QQ' , wbf['header'])           
            worksheet.write('Z%s' % (row+1), 'Code' , wbf['header'])
            worksheet.write('AA%s' % (row+1), 'Name' , wbf['header']) 
            worksheet.merge_range('AB%s:AC%s' % (row,row), 'Engine' , wbf['header'])           
            worksheet.write('AB%s' % (row+1), 'No Engine' , wbf['header'])
            worksheet.write('AC%s' % (row+1), 'No Chassis' , wbf['header'])
            worksheet.merge_range('AD%s:AD%s' % (row,row+1), 'Jenis Penjualan' , wbf['header'])  
            worksheet.write('AD%s' % (row+1), 'Jenis Penjualan' , wbf['header_no'])
        elif options == 'Other':
            worksheet.merge_range('Z%s:AA%s' % (row,row), 'User' , wbf['header'])    
            worksheet.write('Z%s' % (row+1), 'Create' , wbf['header'])
            worksheet.write('AA%s' % (row+1), 'Confirm' , wbf['header']) 
            
        row+=2         
        no = 0
        subtotal_total_invoice =0
        subtotal_sisa_piutang = 0
        subtotal_current = 0
        subtotal_overdue_1_7 = 0     
        subtotal_overdue_8_14 = 0     
        subtotal_overdue_15_21 = 0     
        subtotal_overdue_22_30 = 0        
        subtotal_overdue_31_60 = 0
        subtotal_overdue_61_90 = 0
        subtotal_overdue_91_n = 0
        row1 = row
        branch_code = False
        aml_id = False
        qq_code = False 
        qq_name = False
        
        user = self.pool.get('res.users').browse(cr, uid, uid)
        tz = pytz.timezone(user.tz) if user.tz else pytz.utc
        no_engine = False
          
        partial_reconcile_ids = []
        residu = 0

        for res in ress:
            if abs(round(res[18],2))<0.01:
                continue
            if options == 'Unit' and aml_id == res[19] :
                branch_code =''
                division = ''
                partner_code = ''
                partner_name = ''
                account_code = ''
                account_sap = ''
                invoice_name = ''
                name = ''
                date_aml =  ''
                due_date = ''
                overdue = ''
                status = ''
                tot_invoice = ''
                amount_residual = ''
                current = ''
                overdue_1_7 = ''
                overdue_8_14 = ''
                overdue_15_21 = ''
                overdue_22_30 = ''
                overdue_31_60 = ''
                overdue_61_90 = ''
                overdue_91_n = ''
                reference = ''
                journal_name = ''
                qq_code = ''
                qq_name = ''
            else :
                branch_code = str(res[0].encode('ascii','ignore').decode('ascii')) if res[0] != None else ''
                division = str(res[1].encode('ascii','ignore').decode('ascii')) if res[1] != None else ''
                partner_code = str(res[2].encode('ascii','ignore').decode('ascii')) if res[2] != None else ''
                partner_name = str(res[3].encode('ascii','ignore').decode('ascii')) if res[3] != None else ''
                account_code = str(res[4].encode('ascii','ignore').decode('ascii')) if res[4] != None else ''
                account_sap = str(res[5][:6].encode('ascii','ignore').decode('ascii')) + "-" + str(res[6].encode('ascii','ignore').decode('ascii')) + str(res[5][6:].encode('ascii','ignore').decode('ascii')) if res[5] != None and res[6] != None else ''
                invoice_name = str(res[17].encode('ascii','ignore').decode('ascii')) if res[17] != None else ''
                name = str(res[14].encode('ascii','ignore').decode('ascii')) if res[14] != None else ''
                date_aml = datetime.strptime(res[7], "%Y-%m-%d").date() if res[7] != None else ''
                due_date = datetime.strptime(res[8], "%Y-%m-%d").date() if res[8] != None else ''
                overdue = str(res[9]) if res[9] != None else 0
                status = 'Reconciled' if res[18] == 0 else 'Outstanding'
                tot_invoice = res[12] - res[13]
                if res[11] != None :
                    if res[11] in partial_reconcile_ids :
                        residu = 0
                    else :
                        residu = res[18]
                        partial_reconcile_ids.append(res[11])
                else :
                    residu = res[18]
                amount_residual = residu
                current = amount_residual if res[9] <= 0 or res[9] == None else 0
                overdue_1_7 = amount_residual if res[9] > 0 and res[9] < 8 else 0
                overdue_8_14 = amount_residual if res[9] > 7 and res[9] < 15 else 0
                overdue_15_21 = amount_residual if res[9] > 14 and res[9] < 22 else 0
                overdue_22_30 = amount_residual if res[9] > 21 and res[9] < 31 else 0
                overdue_31_60 = amount_residual if res[9] > 30 and res[9] < 61 else 0
                overdue_61_90 = amount_residual if res[9] > 60 and res[9] < 91 else 0
                overdue_91_n = amount_residual if res[9] > 90 else 0
                reference = str(res[15].encode('ascii','ignore').decode('ascii')) if res[15] != None else ''
                journal_name = str(res[16].encode('ascii','ignore').decode('ascii')) if res[16] != None else ''
                if options == 'Unit' : 
                    qq_code = str(res[20].encode('ascii','ignore').decode('ascii')) if res[20] else ''
                    qq_name = str(res[21].encode('ascii','ignore').decode('ascii')) if res[21] else ''
                no += 1
                               
                subtotal_total_invoice += tot_invoice
                subtotal_sisa_piutang += amount_residual
                subtotal_current += current
                subtotal_overdue_1_7 += overdue_1_7  
                subtotal_overdue_8_14 += overdue_8_14
                subtotal_overdue_15_21 += overdue_15_21
                subtotal_overdue_22_30 += overdue_22_30
                subtotal_overdue_31_60 += overdue_31_60
                subtotal_overdue_61_90 += overdue_61_90
                subtotal_overdue_91_n += overdue_91_n
            
            if options == 'Unit' : 
                aml_id = res[19]
                no_engine = str(res[22].encode('ascii','ignore').decode('ascii')) if res[22] != None else ''
                no_chassis = str(res[23].encode('ascii','ignore').decode('ascii')) if res[23] != None else ''
                jenis_penjualan = res[24]
            elif options == 'Other':
                u_create=res[19]
                u_confirm=res[20]
                            
            worksheet.write('A%s' % row, no , wbf['content_number'])                    
            worksheet.write('B%s' % row, branch_code , wbf['content'])
            worksheet.write('C%s' % row, division , wbf['content'])
            worksheet.write('D%s' % row, partner_code , wbf['content'])
            worksheet.write('E%s' % row, partner_name , wbf['content'])
            worksheet.write('F%s' % row, account_code , wbf['content'])
            worksheet.write('G%s' % row, account_sap , wbf['content'])
            worksheet.write('H%s' % row, invoice_name , wbf['content'])  
            worksheet.write('I%s' % row, name , wbf['content'])
            worksheet.write('J%s' % row, date_aml , wbf['content_date'])
            worksheet.write('K%s' % row, due_date , wbf['content_date'])
            worksheet.write('L%s' % row, overdue , wbf['content_number'])
            worksheet.write('M%s' % row, status , wbf['content'])
            worksheet.write('N%s' % row, tot_invoice , wbf['content_float'])
            worksheet.write('O%s' % row, amount_residual , wbf['content_float'])
            worksheet.write('P%s' % row, current , wbf['content_float'])
            worksheet.write('Q%s' % row, overdue_1_7 , wbf['content_float']) 
            worksheet.write('R%s' % row, overdue_8_14 , wbf['content_float']) 
            worksheet.write('S%s' % row, overdue_15_21 , wbf['content_float']) 
            worksheet.write('T%s' % row, overdue_22_30 , wbf['content_float']) 
            worksheet.write('U%s' % row, overdue_31_60 , wbf['content_float'])
            worksheet.write('V%s' % row, overdue_61_90 , wbf['content_float'])
            worksheet.write('W%s' % row, overdue_91_n , wbf['content_float'])
            worksheet.write('X%s' % row, reference , wbf['content'])
            worksheet.write('Y%s' % row, journal_name , wbf['content'])
            
            if options == 'Unit' : 
                worksheet.write('Z%s' % row, qq_code , wbf['content'])
                worksheet.write('AA%s' % row, qq_name , wbf['content'])
                worksheet.write('AB%s' % row, no_engine , wbf['content'])
                worksheet.write('AC%s' % row, no_chassis , wbf['content'])
                worksheet.write('AD%s' % row, jenis_penjualan , wbf['content'])
            elif options == 'Other':
                worksheet.write('Z%s' % row, u_create , wbf['content'])
                worksheet.write('AA%s' % row, u_confirm , wbf['content'])
            row+=1
            
        worksheet.autofilter('A6:Y%s' % (row))  
        worksheet.freeze_panes(6, 3)
        
        #TOTAL
        worksheet.merge_range('A%s:C%s' % (row,row), 'Total', wbf['total'])    
        worksheet.merge_range('D%s:M%s' % (row,row), '', wbf['total']) 
        worksheet.merge_range('X%s:Y%s' % (row,row), '', wbf['total'])
        
        if options == 'Unit' :
            worksheet.write('A2', 'Report Piutang Penjualan Unit Per Tanggal %s '%(str(date_title)) , wbf['title_doc'])
            worksheet.autofilter('A6:AD%s' % (row))
            worksheet.merge_range('Z%s:AD%s' % (row,row), '', wbf['header'])
        elif options == 'Other':
            worksheet.autofilter('A6:AA%s' % (row))
            worksheet.merge_range('Z%s:AA%s' % (row,row), '', wbf['header'])
    
            
            
        formula_total_invoice = '{=subtotal(9,N%s:N%s)}' % (row1, row-1)
        formula_sisa_piutang = '{=subtotal(9,O%s:O%s)}' % (row1, row-1)
        formula_current = '{=subtotal(9,P%s:P%s)}' % (row1, row-1)
        formula_overdue_1_7 = '{=subtotal(9,Q%s:Q%s)}' % (row1, row-1)      
        formula_overdue_8_14 = '{=subtotal(9,R%s:R%s)}' % (row1, row-1)      
        formula_overdue_15_21 = '{=subtotal(9,S%s:S%s)}' % (row1, row-1)      
        formula_overdue_22_30 = '{=subtotal(9,T%s:T%s)}' % (row1, row-1)      
        formula_overdue_31_60 = '{=subtotal(9,U%s:U%s)}' % (row1, row-1)
        formula_overdue_61_90 = '{=subtotal(9,V%s:V%s)}' % (row1, row-1)
        formula_overdue_91_n = '{=subtotal(9,W%s:W%s)}' % (row1, row-1)
                               
        worksheet.write_formula(row-1,13,formula_total_invoice, wbf['total_float'], subtotal_total_invoice)
        worksheet.write_formula(row-1,14,formula_sisa_piutang, wbf['total_float'], subtotal_sisa_piutang)
        worksheet.write_formula(row-1,15,formula_current, wbf['total_float'], subtotal_current)
        worksheet.write_formula(row-1,16,formula_overdue_1_7, wbf['total_float'], subtotal_overdue_1_7) 
        worksheet.write_formula(row-1,17,formula_overdue_8_14, wbf['total_float'], subtotal_overdue_8_14) 
        worksheet.write_formula(row-1,18,formula_overdue_15_21, wbf['total_float'], subtotal_overdue_15_21) 
        worksheet.write_formula(row-1,19,formula_overdue_22_30, wbf['total_float'], subtotal_overdue_22_30) 
        worksheet.write_formula(row-1,20,formula_overdue_31_60, wbf['total_float'], subtotal_overdue_31_60) 
        worksheet.write_formula(row-1,21,formula_overdue_61_90, wbf['total_float'], subtotal_overdue_61_90) 
        worksheet.write_formula(row-1,22,formula_overdue_91_n, wbf['total_float'], subtotal_overdue_91_n)         
        worksheet.write('A%s'%(row+2), '%s %s' % (str(date),user.name) , wbf['footer'])  
                   
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_piutang', 'view_report_piutang_wizard')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.report.piutang.wizard',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }

wtc_report_piutang()
