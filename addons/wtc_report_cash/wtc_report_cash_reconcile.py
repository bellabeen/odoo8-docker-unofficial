from openerp.osv import fields, osv
from datetime import datetime
from cStringIO import StringIO
import base64
import xlsxwriter

class wtc_report_cash_non_pettycash(osv.osv_memory):
    _inherit = "wtc.report.cash"

    def _print_excel_report_cash_reconcile(self, cr, uid, ids, data, context=None):
        curr_date= self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)
        user = self.pool.get('res.users').browse(cr, uid, uid)
        company_name = user.company_id.name
        username = user.name
        
        filename = 'report_cash_reconcile_'+str(curr_date.strftime("%Y%m%d_%H%M%S"))+'.xlsx'

        branch_ids = data['branch_ids']
        journal_ids = data['journal_ids']
        status = data['status']
        start_date = data['start_date']
        end_date = data['end_date']
        option = data['option']

        status_str = ""

        query_select_br = " "
        query_from_br = " "
        query_order_br = " "

        query_where = " WHERE 1=1  "
        if status == 'outstanding' :
            status_str = "Outstanding"
            query_select_br = " , '' as reconcile_name, '' as reconcile_date "
            query_where += " AND aml.bank_reconcile_id IS NULL "
        elif status == 'reconcile' :
            status_str = "Reconciled"
            query_select_br = " , br.name as reconcile_name, (br.create_date + interval '7 hours')::timestamp::date as reconcile_date "
            query_from_br = " left join wtc_bank_reconcile br on aml.bank_reconcile_id = br.id "
            query_order_br = " , br.create_date, br.name "
            if start_date :
                query_where += " AND br.create_date >= '%s' " % start_date
            if end_date :
                query_where += " AND br.create_date <= '%s' " % end_date
        if branch_ids :
            query_where += " AND aml.branch_id in %s " % str(tuple(branch_ids)).replace(',)', ')')
        if not journal_ids :
            journal_ids = self.pool.get('account.journal').search(cr, uid, [('branch_id','in',branch_ids),('type','=','cash')])
        if journal_ids :
            journals = self.pool.get('account.journal').browse(cr, uid, journal_ids)
            query_where += " AND aml.account_id in %s " % str(tuple([x.default_debit_account_id.id for x in journals if x.type == 'cash'])).replace(',)', ')')

        query = """
            select b.code as branch_code
            , b.name as branch_name
            , aa.code as account_code
            , aa.name as account_name
            %s
            , aml.ref as transaction_ref
            , aml.name as transaction_name
            , aml.date as transaction_date
            , aml.debit as debit
            , aml.credit as credit
            , aj.name as journal_name
            from account_move_line aml
            %s
            left join account_journal aj on aj.id = aml.journal_id
            left join wtc_branch b on b.id = aml.branch_id
            left join account_account aa on aml.account_id = aa.id
            %s
            order by b.code, aa.code %s , aml.id
        """ % (query_select_br, query_from_br, query_where, query_order_br)
 
        cr.execute (query)
        ress = cr.fetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet("Report Cash Reconcile")

        worksheet.write_string(0, 0, company_name , wbf['company'])
        worksheet.write_string(1, 0, "Report Cash Reconcile" , wbf['title_doc'])
        worksheet.write_string(2, 0, "Status : %s" % status_str, wbf['title_doc'])
        if status == 'reconcile' :
            worksheet.write_string(3, 0, "Tanggal : %s s/d %s" % (str(start_date), str(end_date)), wbf['title_doc'])

        row = 5
        header_row = row

        col = 0 #no
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'No', wbf['header'])
        col += 1 #branch_code
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'Branch Code', wbf['header'])
        col += 1 #branch_name
        worksheet.set_column(col, col, 35)
        worksheet.write_string(row, col, 'Branch Name', wbf['header'])
        col += 1 #account_code
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'Account Code', wbf['header'])
        col += 1 #account_name
        worksheet.set_column(col, col, 35)
        worksheet.write_string(row, col, 'Account Name', wbf['header'])
        col += 1 #reconcile_name
        worksheet.set_column(col, col, 18)
        worksheet.write_string(row, col, 'Reconcile Code', wbf['header'])
        col += 1 #reconcile_date
        worksheet.set_column(col, col, 18)
        worksheet.write_string(row, col, 'Reconcile Date', wbf['header'])
        col += 1 #transaction_ref
        worksheet.set_column(col, col, 24)
        worksheet.write_string(row, col, 'Transaction Ref', wbf['header'])
        col += 1 #transaction_name
        worksheet.set_column(col, col, 50)
        worksheet.write_string(row, col, 'Transaction Name', wbf['header'])
        col += 1 #transaction_date
        worksheet.set_column(col, col, 19.5)
        worksheet.write_string(row, col, 'Transaction Date', wbf['header'])
        col += 1 #debit
        worksheet.set_column(col, col, 19.5)
        worksheet.write_string(row, col, 'Debit', wbf['header'])
        col += 1 #credit
        worksheet.set_column(col, col, 19.5)
        worksheet.write_string(row, col, 'Credit', wbf['header'])
        col += 1 #balance
        worksheet.set_column(col, col, 19.5)
        worksheet.write_string(row, col, 'Balance', wbf['header'])
        col += 1 #journal_name
        worksheet.set_column(col, col, 25)
        worksheet.write_string(row, col, 'Journal Name', wbf['header'])

        data_last_col = col
        row += 1
        data_first_row = row

        no = 1

        branch_code_prev = False
        account_code_prev = False
        restart_balance = True

        for res in ress :
            branch_code = str(res[0].encode('ascii','ignore').decode('ascii')) if res[0] != None else ''
            account_code = str(res[2].encode('ascii','ignore').decode('ascii')) if res[2] != None else ''

            if (account_code_prev != account_code or branch_code_prev != branch_code) :
                restart_balance = True
            else :
                restart_balance = False

            if account_code_prev == False or account_code_prev != account_code or branch_code_prev != branch_code :
                account_code_prev = account_code
                branch_code_prev = branch_code

            branch_name = str(res[1].encode('ascii','ignore').decode('ascii')) if res[1] != None else ''
            account_code = str(res[2].encode('ascii','ignore').decode('ascii')) if res[2] != None else ''
            account_name = str(res[3].encode('ascii','ignore').decode('ascii')) if res[3] != None else ''
            reconcile_name = str(res[4].encode('ascii','ignore').decode('ascii')) if res[4] != None else ''
            reconcile_date = datetime.strptime(res[5], "%Y-%m-%d").date() if res[5] else ''
            transaction_ref = str(res[6].encode('ascii','ignore').decode('ascii')) if res[6] != None else ''
            transaction_name = str(res[7].encode('ascii','ignore').decode('ascii')) if res[7] != None else ''
            transaction_date = datetime.strptime(res[8], "%Y-%m-%d").date() if res[8] else ''
            debit = res[9]
            credit = res[10]
            journal_name = str(res[11].encode('ascii','ignore').decode('ascii')) if res[11] != None else ''

            col = 0 #no
            worksheet.write_number(row, col, no, wbf['content_number'])
            col += 1 #branch_code
            worksheet.write_string(row, col, branch_code, wbf['content'])
            col += 1 #branch_name
            worksheet.write_string(row, col, branch_name, wbf['content'])
            col += 1 #account_code
            worksheet.write_string(row, col, account_code, wbf['content'])
            col += 1 #account_name
            worksheet.write_string(row, col, account_name, wbf['content'])
            col += 1 #reconcile_name
            worksheet.write_string(row, col, reconcile_name, wbf['content'])
            col += 1 #reconcile_date
            if reconcile_date == "" :
                worksheet.write_blank(row, col, None, wbf['content_date'])
            else :
                worksheet.write_datetime(row, col, reconcile_date, wbf['content_date'])
            col += 1 #transaction_ref
            worksheet.write_string(row, col, transaction_ref, wbf['content'])
            col += 1 #transaction_name
            worksheet.write_string(row, col, transaction_name, wbf['content'])
            col += 1 #transaction_date
            worksheet.write_datetime(row, col, transaction_date, wbf['content_date'])
            col += 1 #debit
            worksheet.write_number(row, col, debit, wbf['content_float'])
            col += 1 #credit
            worksheet.write_number(row, col, credit, wbf['content_float'])
            col += 1 #balance
            if restart_balance :
                worksheet.write_formula(row, col, '=K%s-L%s'%(row+1,row+1), wbf['content_float'])
            else :
                worksheet.write_formula(row, col, '=M%s+K%s-L%s'%(row,row+1,row+1), wbf['content_float'])
            col += 1 #journal_name
            worksheet.write_string(row, col, journal_name, wbf['content'])

            no += 1
            row += 1

        worksheet.autofilter(header_row, 0, row, data_last_col)

        #TOTAL
        for i in range (0, data_last_col) :
            worksheet.write_blank(row, i, None, wbf['total'])

        worksheet.write(row+2, 0, '%s %s' % (str(curr_date.strftime("%Y-%m-%d %H:%M:%S")),username) , wbf['footer'])  

        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        return True
