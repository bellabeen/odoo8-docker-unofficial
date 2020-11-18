from openerp.osv import fields, osv
from datetime import datetime
from cStringIO import StringIO
import base64
import xlsxwriter

class wtc_report_settlement_advance_payment(osv.osv_memory):
    _inherit = "wtc.report.advance.payment"

    def _print_excel_report_settlement(self, cr, uid, ids, data, context=None):
        curr_date= self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)
        user = self.pool.get('res.users').browse(cr, uid, uid)
        company_name = user.company_id.name
        username = user.name
        
#         filename = 'REPORT SETTLEMENT ADVANCE PAYMENT '+str(curr_date.strftime("%Y%m%d_%H%M%S"))+'.xlsx'
        print '#########',data
        options = data['options']
        division = data['division']
        start_date = data['start_date']
        end_date = data['end_date']
        branch_ids = data['branch_ids']
        partner_ids = data['partner_ids']
        journal_ids = data['journal_ids']
        account_ids = data['account_ids']
        status = data['status']
        where_partner = " 1=1 "
        
        if partner_ids :
            where_partner=" p.id  in %s " % str(
                tuple(partner_ids)).replace(',)', ')')  
                            
        where_branch = " 1=1 "
        if branch_ids :
            where_branch = " b.id in %s " % str(
                tuple(branch_ids)).replace(',)', ')')             
        else :
            area_user = self.pool.get('res.users').browse(cr,uid,uid).branch_ids
            branch_ids_user = [b.id for b in area_user]
            if branch_ids_user :
                where_branch = " b.id in %s " % str(
                    tuple(branch_ids_user))
        
        where_journal = " 1=1 "
        if journal_ids :
            where_journal=" j.id  in %s " % str(
                tuple(journal_ids)).replace(',)', ')')   
                 
        where_account = " 1=1 "
        if account_ids :
            where_account=" a.id  in %s " % str(
                tuple(account_ids)).replace(',)', ')') 
                                          
        where_division = " 1=1 "
        if division == 'Unit' :
            where_division=" l.division = 'Unit' "
        elif division == 'Sparepart' :
            where_division=" l.division = 'Sparepart' "  
        elif division == 'Umum' :
            where_division=" l.division = 'Umum' "  
                        
        where_start_date = " 1=1 "
        where_end_date = " 1=1 "                               
        if start_date :
            where_start_date = " l.date >= '%s' " % start_date
        if end_date :
            where_end_date = " l.date <= '%s' " % end_date         

        where_status = " 1=1 "
        if status == 'reconciled' :
            where_status = " l.reconcile_id is not null "
        elif status == 'outstanding' :
            where_status = " l.reconcile_id is null "
        
        query = "SELECT b.code as branch_code, "\
            "a.code as no_rek, "\
            "l.date as date, "\
            "m.name as no_bukti, "\
            "l.reconcile_id as reconcile_id, "\
            "l.ref as keterangan, "\
            "p.name as partner, "\
            "l.debit as total, "\
            "ps.name as user, "\
            "l.date_maturity as due_date "\
            "FROM account_move_line l "\
            "LEFT JOIN wtc_branch b ON b.id = l.branch_id "\
            "LEFT JOIN wtc_settlement st ON st.account_move_id = l.move_id "\
            "LEFT JOIN res_users u ON u.id = l.create_uid "\
            "LEFT JOIN res_partner p ON p.id = l.partner_id "\
            "LEFT JOIN res_partner ps ON ps.id = u.partner_id "\
            "LEFT JOIN account_move m ON m.id = l.move_id "\
            "LEFT JOIN account_account a ON a.id = l.account_id "\
            "LEFT JOIN account_journal j ON j.id = l.journal_id "\
            "WHERE a.type = 'receivable' AND st.account_move_id is not null AND "+where_journal+" AND "+where_status+" AND "+where_partner+" AND "+where_branch+" AND " ""\
            ""+where_account+" AND "+where_division+" AND "+where_start_date+" AND "+where_end_date+" "\
            "ORDER BY l.date,b.code"
        
        move_selection = ""
        report_info = ('')
        move_selection += ""
            
        # reports = [report_advance_payment]

        cr.execute(query)
        all_lines = cr.dictfetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('%s' %(options))

        worksheet.set_column('B1:B1', 13)
        worksheet.set_column('C1:C1', 20)
        worksheet.set_column('D1:D1', 20)
        worksheet.set_column('E1:E1', 30)
        worksheet.set_column('F1:F1', 20)
        worksheet.set_column('G1:G1', 20)
        worksheet.set_column('H1:H1', 20)
        worksheet.set_column('I1:I1', 20)
        worksheet.set_column('J1:J1', 20)
        worksheet.set_column('K1:K1', 20)
        
        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        filename = 'LAPORAN BON SEMENTARA %s '%(options)+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Laporan Bon Sementara' , wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s s/d %s'%(str(start_date),str(end_date)) , wbf['company'])

        row=5
        rowsaldo = row
        row+=1

        worksheet.write('A%s' % (row), 'No' , wbf['header'])
        worksheet.write('B%s' % (row), 'Cabang' , wbf['header'])
        worksheet.write('C%s' % (row), 'No Rek' , wbf['header'])
        worksheet.write('D%s' % (row), 'Tanggal' , wbf['header'])
        worksheet.write('E%s' % (row), 'No Bukti' , wbf['header'])
        worksheet.write('F%s' % (row), 'Sts' , wbf['header'])
        worksheet.write('G%s' % (row), 'Keterangan' , wbf['header'])
        worksheet.write('H%s' % (row), 'Diberikan Ke' , wbf['header'])
        worksheet.write('I%s' % (row), 'Total' , wbf['header'])
        worksheet.write('J%s' % (row), 'Pembuat' , wbf['header'])
        worksheet.write('K%s' % (row), 'Tanggal Jatuh Tempo' , wbf['header'])

        row += 1
        data_first_row = row
        row1 = row
        total = 0
        no = 1
        for x in all_lines:

            branch_code = x['branch_code'].encode('ascii','ignore').decode('ascii') if x['branch_code'] != None else ''
            no_rek = x['no_rek'].encode('ascii','ignore').decode('ascii') if x['no_rek'] != None else ''  
            date = x['date'].encode('ascii','ignore').decode('ascii') if x['date'] != None else ''    
            no_bukti = x['no_bukti'].encode('ascii','ignore').decode('ascii') if x['no_bukti'] != None else ''    
            sts = 'Reconciled' if x['reconcile_id'] else 'Outstanding'
            keterangan = x['keterangan'].encode('ascii','ignore').decode('ascii') if x['keterangan'] != None else ''
            partner = x['partner'].encode('ascii','ignore').decode('ascii') if x['partner'] != None else ''    
            total = x['total']
            user = x['user'].encode('ascii','ignore').decode('ascii') if x['user'] != None else ''
            due_date = x['due_date'].encode('ascii','ignore').decode('ascii') if x['due_date'] != None else ''  


            worksheet.write('A%s' % row, no, wbf['content_number']) 
            worksheet.write('B%s' % row, branch_code, wbf['content'])  
            worksheet.write('C%s' % row, no_rek, wbf['content'])
            worksheet.write('D%s' % row, date, wbf['content_date'])
            worksheet.write('E%s' % row, no_bukti, wbf['content'])
            worksheet.write('F%s' % row, sts, wbf['content'])
            worksheet.write('G%s' % row, keterangan, wbf['content'])
            worksheet.write('H%s' % row, partner, wbf['content'])
            worksheet.write('I%s' % row, total, wbf['content_float'])   
            worksheet.write('J%s' % row, user, wbf['content']) 
            worksheet.write('K%s' % row, due_date, wbf['content_date'])      
            
            no+=1
            row+=1
            total = total

        worksheet.autofilter('A7:G%s' % (row))  
        worksheet.freeze_panes(6, 3)

        worksheet.merge_range('A%s:H%s' % (row,row), 'Total', wbf['total'])    
        worksheet.write('I%s'%(row), '', wbf['total'])
        worksheet.merge_range('J%s:K%s' % (row,row), '', wbf['total'])  
        
        #sheet 1
        formula_total= '{=subtotal(9,H%s:H%s)}' % (row1, row-1) 
       
        
        #sheet 1
        worksheet.write_formula(row-1,7,formula_total, wbf['total_float'], total)  
      
      
        worksheet.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer']) 
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'fname': filename}, context=context)
        fp.close()
        
        return True

