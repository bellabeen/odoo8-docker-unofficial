import time
from lxml import etree
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

class wtc_report_payment(osv.osv_memory):
    _name = 'wtc.report.payment'
    _description = 'WTC Report Payment'


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
        res = super(wtc_report_payment, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
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

        'option': fields.selection([('customer_payment_detail_old','Customer Payment Old'),('supplier_payment_detail_old','Supplier Payment Old'),('customer_payment_detail','Customer Payment'),('supplier_payment_detail','Supplier Payment')], 'Option', change_default=True, select=True), 
        'division': fields.selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum')], 'Division', change_default=True, select=True),         
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'branch_ids': fields.many2many('wtc.branch', 'wtc_report_payment_branch_rel', 'wtc_report_payment',
                                        'branch_id', 'Branch', copy=False),
        'account_ids': fields.many2many('account.account', 'wtc_report_payment_account_rel', 'wtc_report_payment',
                                        'account_id', 'Account', copy=False, ), 
        'journal_ids': fields.many2many('account.journal', 'wtc_report_payment_journal_rel', 'wtc_report_payment',
                                        'journal_id', 'Journal', copy=False, ),
        'partner_ids': fields.many2many('res.partner', 'wtc_report_payment_partner_rel', 'wtc_report_payment',
                                        'partner_id', 'Partner', copy=False),
                
    }
    _defaults = {
        'start_date':datetime.today(),
        'end_date':datetime.today(),
        'option':'customer_payment_detail'
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
        
        self.wbf['content'] = workbook.add_format({'align': 'left','bg_color': '#00ffff','bold': 1})
        self.wbf['content'].set_left()
        self.wbf['content'].set_right() 

        self.wbf['content_d'] = workbook.add_format()
        self.wbf['content_d'].set_left()
        self.wbf['content_d'].set_right() 
        
        self.wbf['content_float'] = workbook.add_format({'align': 'right','num_format': '#,##0.00','bg_color': '#00ffff','bold': 1})
        self.wbf['content_float'].set_right() 
        self.wbf['content_float'].set_left()

        self.wbf['content_float_d'] = workbook.add_format({'align': 'right','num_format': '#,##0.00'})
        self.wbf['content_float_d'].set_right() 
        self.wbf['content_float_d'].set_left()


        self.wbf['content_center'] = workbook.add_format({'align': 'centre'})
        
        self.wbf['content_number'] = workbook.add_format({'align': 'right', 'bg_color': '#00ffff','bold': 1})
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

        branch_ids = data['branch_ids']
        account_ids = data['account_ids']
        journal_ids = data['journal_ids']
        partner_ids = data['partner_ids']
        division = data['division']
        option = data['option']
        start_date = data['start_date']
        end_date = data['end_date']
        digits = self.pool['decimal.precision'].precision_get(cr, uid, 'Account')

        if option == 'customer_payment_detail' :
            title_type='Customer Payment'
        else :
            title_type='Supplier Payment'
            
        report = {
            'type': 'receivable',
            'title': title_type ,
            'title_short': title_type,
            'start_date': start_date,
            'end_date': end_date  
            }
        is_hutang_lain_where =' 1=1 '
        where_option= " 1=1 "
        if option == 'customer_payment_detail_old' :
            where_option=" av.type = 'receipt' "
            table = "account_voucher"
            model_name = "account.voucher"
            table_line = "account_voucher_line"
            is_hutang_lain_where = 'is_hutang_lain = false'
        elif option == 'supplier_payment_detail_old' :
            where_option=" av.type = 'payment' "
            table = "account_voucher"
            model_name = "account.voucher"
            table_line = "account_voucher_line"
            is_hutang_lain_where = 'is_hutang_lain = false'
        elif option == 'customer_payment_detail' :
            where_option=" av.type = 'receipt' "
            table = "wtc_account_voucher"
            model_name = "wtc.account.voucher"
            table_line = "wtc_account_voucher_line"    
        elif option == 'supplier_payment_detail' :
            where_option=" av.type = 'payment' "
            table = "wtc_account_voucher"
            model_name = "wtc.account.voucher"
            table_line = "wtc_account_voucher_line"
            
        where_branch = " 1=1 "
        if branch_ids :
            where_branch = " b.id in %s " % str(
                tuple(branch_ids)).replace(',)', ')')
        else :
            area_user = self.pool.get('res.users').browse(cr,uid,uid).branch_ids
            branch_ids_user = [b.id for b in area_user]
            where_branch = " b.id in %s " % str(
                tuple(branch_ids_user))
            
        where_account = " 1=1 "
        if account_ids :
            where_account=" aa.id  in %s " % str(
                tuple(account_ids)).replace(',)', ')') 
        where_journal = " 1=1 "
        if journal_ids :
            where_journal=" aj.id  in %s " % str(
                tuple(journal_ids)).replace(',)', ')')   
        
        where_partner = " 1=1 "
        if partner_ids :
            where_partner=" partner.id  in %s " % str(
                tuple(partner_ids)).replace(',)', ')')
                          
        where_division = " 1=1 "
        if division == 'Unit' :
            where_division=" av.division = 'Unit' "
        elif division == 'Sparepart' :
            where_division=" av.division = 'Sparepart' "  
        elif division == 'Umum' :
            where_division=" av.division = 'Umum' "  
                        
        where_start_date = " 1=1 "
        where_end_date = " 1=1 "                               
        if start_date :
            where_start_date = " av.date >= '%s' " % start_date
        if end_date :
            where_end_date = " av.date <= '%s' " % end_date 
        
        query_saldo = """
            SELECT 
                payment.id
                ,payment.p_ref
                ,payment.p_name
                ,payment.total_credit
                ,payment.total_debit
                ,approval_line.tanggal as tgl_approve
                ,pelaksana_partner.name as pelaksana
                ,groups.name as groups
                ,payment.limitation
            FROM 
                (SELECT 
                    av.id,
                    av.number as p_ref,
                    b.code as p_name ,
                    SUM(case WHEN avl.type='cr' THEN avl.amount else 0 end) as total_credit ,
                    SUM(case WHEN avl.type='dr' THEN avl.amount else 0 end) as total_debit ,
                    MAX(approval_line.limit) as limitation,
                    model.id as model
                FROM %s avl 
                    LEFT JOIN %s av on avl.voucher_id=av.id 
                    LEFT JOIN wtc_branch b on av.branch_id = b.id 
                    LEFT JOIN wtc_branch b_to on av.inter_branch_id = b_to.id 
                    LEFT JOIN account_journal aj on av.journal_id = aj.id 
                    LEFT JOIN account_account aa on av.account_id = aa.id 
                    LEFT JOIN res_partner partner on av.partner_id = partner.id 
                    LEFT JOIN ir_model as model on model.model = '%s'
                    LEFT JOIN wtc_approval_line as approval_line 
                        on approval_line.transaction_id = av.id 
                        AND approval_line.form_id = model.id 
                    LEFT JOIN res_users as pelaksana on pelaksana.id = approval_line.pelaksana_id 
                    LEFT JOIN res_partner as pelaksana_partner on pelaksana_partner.id = pelaksana.partner_id 
                    LEFT JOIN res_groups as groups on groups.id = approval_line.group_id 
                WHERE %s
                AND %s
                AND %s 
                AND %s
                AND %s
                AND %s 
                AND %s 
                AND %s 
                AND %s 
                GROUP BY av.id,b.id,model.id) AS payment
            LEFT JOIN wtc_approval_line as approval_line 
                ON approval_line.transaction_id = payment.id
                AND approval_line.form_id = payment.model
                AND approval_line.limit = payment.limitation
            LEFT JOIN res_users as pelaksana on pelaksana.id = approval_line.pelaksana_id 
            LEFT JOIN res_partner as pelaksana_partner on pelaksana_partner.id = pelaksana.partner_id 
            LEFT JOIN res_groups as groups on groups.id = approval_line.group_id 
        """ %(table_line,table,model_name,is_hutang_lain_where,where_account,where_option,where_branch,where_journal,where_division,where_start_date,where_end_date,where_partner)
        cr.execute (query_saldo)
        result = cr.dictfetchall()


        query_start = "select av.id as p_id, "\
            "b.code as p_name, " \
            "b.name as nama_cabang_untuk, "\
            "b_to.code as code_cabang_terima, "\
            "b_to.name as nama_cabang_terima, "\
            "av.number as p_ref, " \
            "av.state as status, "\
            "aj.name as payment_method, "\
            "aa.code as account, "\
            "av.amount as paid_amount, "\
            "partner.default_code as partner_code, "\
            "partner.name as partner_name, " \
            "av.amount-COALESCE(line_cr.amount,0)+COALESCE(line_dr.amount,0) as diff, " \
            "aml.ref as no_transaksi, " \
            "avl.type as a_type, " \
            "(CASE WHEN avl.type='cr' THEN avl.amount   END) AS credit, " \
            "(CASE WHEN avl.type='dr' THEN avl.amount   END) AS debit, "\
            "partner_user.name as create_by, " \
            "to_char(av.create_date,'dd-MM-yyyy') create_date " \
            "from "+table+" av " \
            "INNER JOIN "+table_line+" avl ON avl.voucher_id=av.id " \
            "INNER JOIN account_move_line aml ON avl.move_line_id=aml.id " \
            "left join (select voucher_id, sum(amount) as amount from "+table_line+" where type = 'cr' group by voucher_id) line_cr on av.id = line_cr.voucher_id " \
            "left join (select voucher_id, sum(amount) as amount from "+table_line+" where type = 'dr' group by voucher_id) line_dr on av.id = line_dr.voucher_id " \
            "left join wtc_branch b on av.branch_id = b.id " \
            "left join wtc_branch b_to on av.inter_branch_id = b_to.id " \
            "left join account_journal aj on av.journal_id = aj.id " \
            "left join account_account aa on av.account_id = aa.id " \
            "left join res_partner partner on av.partner_id = partner.id " \
            "left join res_users u on u.id = av.create_uid " \
            "left join res_partner partner_user on partner_user.id = u.partner_id " \
            "where  "+is_hutang_lain_where+" " \
            "AND "+where_account+" AND "+where_option+" AND "+where_branch+" AND "+where_journal+" AND "+where_division+" AND "+where_start_date+" AND "+where_end_date+" AND "+where_partner+" "\
            "ORDER BY av.number ASC "
        reports = [report]
        report_info = title_type

        cr.execute(query_start)
        all_lines = cr.dictfetchall()
        # print">>>>>>>>>>>>>>>>>>>>>>>>>>>",(query_start)


        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet1 = workbook.add_worksheet  ('%s' %(title_type))

        worksheet2 = workbook.add_worksheet  ('%s Details' %(title_type))
        worksheet1.set_column('B1:B1', 20)
        worksheet1.set_column('C1:C1', 20)
        worksheet1.set_column('D1:D1', 20)
        worksheet1.set_column('E1:E1', 20)
        worksheet1.set_column('F1:F1', 20)
        worksheet1.set_column('G1:G1', 20)
        worksheet1.set_column('H1:H1', 20)
        worksheet1.set_column('I1:I1', 25)

        worksheet2.set_column('B1:B1', 20)
        worksheet2.set_column('C1:C1', 20)
        worksheet2.set_column('D1:D1', 20)
        worksheet2.set_column('E1:E1', 20)
        worksheet2.set_column('F1:F1', 15)
        worksheet2.set_column('G1:G1', 25)
        worksheet2.set_column('H1:H1', 15)
        worksheet2.set_column('I1:I1', 20)
        worksheet2.set_column('J1:J1', 20)
        worksheet2.set_column('K1:K1', 25)
        worksheet2.set_column('L1:L1', 20)
        worksheet2.set_column('M1:M1', 15)
        worksheet2.set_column('N1:N1', 15)
        worksheet2.set_column('O1:O1', 15)
        worksheet2.set_column('P1:P1', 20)
        worksheet2.set_column('Q1:Q1', 17)


        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name

        filename = '%s' %(title_type)+str(date)+'.xlsx'        
        worksheet1.write('A1', company_name , wbf['company'])
        worksheet1.write('A2', '%s' %(title_type) , wbf['title_doc'])
        worksheet1.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])
        

        # filename = 'Laporan Faktur Pajak Gabungan D'+str(date)+'.xlsx'        
        worksheet2.write('A1', company_name , wbf['company'])
        worksheet2.write('A2', '%s Details' %(title_type) , wbf['title_doc'])
        worksheet2.write('A3', 'Tanggal : %s s/d %s'%(str(start_date) if start_date else '-',str(end_date) if end_date else '-') , wbf['company'])
        
        
        row=5
        rowsaldo = row
        row+=1

        row_a=5
        rowsaldo_a = row_a
        row_a+=1

        worksheet1.write('A%s' % (row+1), 'Partner' , wbf['header'])
        worksheet1.write('B%s' % (row+1), 'Partner Reference' , wbf['header'])
        worksheet1.write('C%s' % (row+1), 'Credit' , wbf['header'])
        worksheet1.write('D%s' % (row+1), 'Debit' , wbf['header'])
        worksheet1.write('E%s' % (row+1), 'Balance' , wbf['header'])
        worksheet1.write('F%s' % (row+1), 'Tanggal Approval' , wbf['header'])
        worksheet1.write('G%s' % (row+1), 'Employee' , wbf['header'])
        worksheet1.write('H%s' % (row+1), 'Jabatan' , wbf['header'])
        worksheet1.write('I%s' % (row+1), 'Limit' , wbf['header'])


        worksheet2.write('A%s' % (row+1), 'Cabang' , wbf['header'])
        worksheet2.write('B%s' % (row+1), 'Nama Cabang' , wbf['header'])
        worksheet2.write('C%s' % (row+1), 'Terima Untuk' , wbf['header'])
        worksheet2.write('D%s' % (row+1), 'Cabang Untuk' , wbf['header'])
        worksheet2.write('E%s' % (row+1), 'Number' , wbf['header'])
        worksheet2.write('F%s' % (row+1), 'Status' , wbf['header'])
        worksheet2.write('G%s' % (row+1), 'Payment Method' , wbf['header'])
        worksheet2.write('H%s' % (row+1), 'Account' , wbf['header'])
        worksheet2.write('I%s' % (row+1), 'Paid Amount' , wbf['header'])
        worksheet2.write('J%s' % (row+1), 'Partner' , wbf['header'])
        worksheet2.write('K%s' % (row+1), 'Nama Partner' , wbf['header'])
        worksheet2.write('L%s' % (row+1), 'No Transaksi' , wbf['header'])
        worksheet2.write('M%s' % (row+1), 'Debit' , wbf['header'])
        worksheet2.write('N%s' % (row+1), 'Credit' , wbf['header'])
        worksheet2.write('O%s' % (row+1), 'Diff' , wbf['header'])
        worksheet2.write('P%s' % (row+1), 'Create by' , wbf['header'])
        worksheet2.write('Q%s' % (row+1), 'Create on' , wbf['header'])
        

        row+=2
        no = 1
        row1 = row


        row_a+=2                
        no_a = 1     
        row2 = row_a


        p_ref_old = ''
        p_ref_old_a = ''
       
      

        for ress in (result):
            total_credit = ress['total_credit']
            total_debit = ress['total_debit']
            balance = total_credit - total_debit
            p_ref = ress['p_ref']
            p_name = ress['p_name']
            tgl_approve = ress['tgl_approve']
            pelaksana = ress['pelaksana']
            groups = ress['groups']
            limitation = ress['limitation']


            ##shet1
            if p_ref != p_ref_old_a and worksheet1:
                worksheet1.write('A%s' % row_a, p_name, wbf['content_d']) 

            if p_ref != p_ref_old_a and worksheet1:          
                worksheet1.write('B%s' % row_a, p_ref, wbf['content_d']) 

            if p_ref != p_ref_old_a and worksheet1:     
                worksheet1.write('C%s' % row_a, total_credit, wbf['content_float_d'])  

            if p_ref != p_ref_old_a and worksheet1:     
                worksheet1.write('D%s' % row_a, total_debit, wbf['content_float_d']) 

            if p_ref != p_ref_old_a and worksheet1:     
                worksheet1.write('E%s' % row_a, balance, wbf['content_float_d'])  

            if p_ref != p_ref_old_a and worksheet1:     
                worksheet1.write('F%s' % row_a, tgl_approve, wbf['content_d'])  

            if p_ref != p_ref_old_a and worksheet1:     
                worksheet1.write('G%s' % row_a, pelaksana, wbf['content_d'])  

            if p_ref != p_ref_old_a and worksheet1:     
                worksheet1.write('H%s' % row_a, groups, wbf['content_d'])  

            if p_ref != p_ref_old_a and worksheet1:     
                worksheet1.write('I%s' % row_a, limitation, wbf['content_float_d'])  
          
            row_a+=1

            

        for res in (all_lines):

            p_id = res['p_id']
            p_name = res['p_name']
            nama_cabang_untuk = res['nama_cabang_untuk']
            code_cabang_terima = res['code_cabang_terima']
            nama_cabang_terima = res['nama_cabang_terima']
            p_ref = res['p_ref']
            status = res ['status']
            payment_method = res['payment_method']
            account = res['account']
            paid_amount = str(res['paid_amount'])
            partner_code = res['partner_code']
            partner_name = res['partner_name']
            diff = str(res['diff'])
            no_transaksi = res['no_transaksi']
            a_type = res['a_type']
            debit = res['debit'] if res['debit'] > 0 else 0.0
            credit = res['credit'] if res['credit'] > 0 else 0.0
            create_by = str(res['create_by']) 
            create_date = str(res['create_date'])

            ##shet2
            if p_ref != p_ref_old:
                worksheet2.write('A%s' % row, p_name, wbf['content'])
                worksheet2.write('B%s' % row, nama_cabang_untuk, wbf['content'])
                worksheet2.write('C%s' % row, code_cabang_terima, wbf['content'])
                worksheet2.write('D%s' % row, nama_cabang_terima, wbf['content'])
                worksheet2.write('E%s' % row, p_ref, wbf['content_number'])
                worksheet2.write('F%s' % row, status, wbf['content'])
                worksheet2.write('G%s' % row, payment_method, wbf['content'])
                worksheet2.write('H%s' % row, account, wbf['content'])
                worksheet2.write('I%s' % row, paid_amount, wbf['content_float'])
                worksheet2.write('J%s' % row, partner_code, wbf['content'])
                worksheet2.write('K%s' % row, partner_name , wbf['content'])
                worksheet2.write('L%s' % row, no_transaksi,wbf['content'])
                worksheet2.write('M%s' % row, debit,wbf['content_float'])
                worksheet2.write('N%s' % row, credit,wbf['content_float'])
                worksheet2.write('O%s' % row, diff,wbf['content_float'])
                worksheet2.write('P%s' % row, create_by ,wbf['content'])
                worksheet2.write('Q%s' % row, create_date ,wbf['content'])
            else:
                worksheet2.write('L%s' % row, no_transaksi,wbf['content_d']) 
                worksheet2.write('M%s' % row, debit, wbf['content_float_d'])
                worksheet2.write('N%s' % row, credit, wbf['content_float_d'])
            p_ref_old = p_ref
           
            no+=1
            row+=1



        worksheet1.merge_range('A%s:I%s' % (row_a,row_a), ' ', wbf['total']) 
        worksheet1.write('A%s'%(row_a+2), '%s %s' % (str(date),user) , wbf['footer']) 
        worksheet2.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])  
        
        worksheet2.autofilter('A7:N%s' % (row))  
        worksheet2.freeze_panes(7, 5)

        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()
        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_payment', 'view_wtc_report_payment')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.report.payment',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }



    # def print_report(self, cr, uid, ids, context=None):
    #     if context is None:
    #         context = {}
    #     branch_ids_user=self.pool.get('res.users').browse(cr,uid,uid).branch_ids
    #     data = self.read(cr, uid, ids)[0]
    #     branch_ids = data['branch_ids']
    #     cek=len(branch_ids)
    #     if cek == 0 :
    #         branch_ids=[b.id for b in branch_ids_user]
    #     else :
    #         branch_ids=data['branch_ids']
    #     account_ids = data['account_ids']
    #     journal_ids = data['journal_ids']
    #     partner_ids = data['partner_ids']
    #     division = data['division']
    #     option = data['option']
    #     start_date = data['start_date']
    #     end_date = data['end_date']

    #     data.update({
    #         'branch_ids': branch_ids,
    #         'account_ids': account_ids,
    #         'journal_ids': journal_ids,
    #         'start_date': start_date,
    #         'end_date': end_date,
    #         'option': option,
            
    #     })
    #     if context.get('xls_export'):
    #         return {'type': 'ir.actions.report.xml',
    #                 'report_name': 'wtc.report.payment.xls',
    #                 'datas': data}
    #     else:
    #         context['landscape'] = True
    #         return self.pool['report'].get_action(
    #             cr, uid, [],
    #             'wtc_report_payment_xls.report_payment',
    #             data=data, context=context)

    # def xls_export(self, cr, uid, ids, context=None):
    #     return self.print_report(cr, uid, ids, context=context)
