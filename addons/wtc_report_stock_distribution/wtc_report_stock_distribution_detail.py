from openerp.osv import fields, osv
from datetime import datetime
from cStringIO import StringIO
import base64
import xlsxwriter

class wtc_report_stock_distribution_detail(osv.osv_memory):
    _inherit = "wtc.report.stock.distribution"

    def _print_excel_report_detail(self, cr, uid, ids, data, context=None):
        curr_date= self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)
        user = self.pool.get('res.users').browse(cr, uid, uid)
        company_name = user.company_id.name
        username = user.name
        # print ">>>>>>>>\n%s\n%s" %(cr, uid)
        filename = 'stock_distribution_'+str(curr_date.strftime("%Y%m%d_%H%M%S"))+'.xlsx'

        state = data['state']
        division = data['division']
        trx_type = data['trx_type']
        start_date = data['start_date']
        end_date = data['end_date']
        branch_ids = data['branch_ids']
        dealer_ids = data['dealer_ids']
        state_str = ''
        division_str = 'All'
        trx_type_str = 'All'

        query = self._query_report_stock_distribution_detail(
            state=state,
            division=division,
            trx_type=trx_type,
            start_date=start_date,
            end_date=end_date,
            branch_ids=branch_ids,
            dealer_ids=dealer_ids,
            state_str=state_str,
            division_str=division_str,
            trx_type_str=trx_type_str,
        )

        cr.execute(query)
        ress = cr.fetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Stock Distribution Detail')

        worksheet.set_column(0, 0, 8.43)

        worksheet.write_string(0, 0, company_name , wbf['company'])
        worksheet.write_string(1, 0, 'Report Stock Distribution Detail' , wbf['title_doc'])
        worksheet.write_string(2, 0, 'State : %s' % state_str, wbf['title_doc'])
        worksheet.write_string(3, 0, 'Division : %s' % division_str, wbf['title_doc'])
        worksheet.write_string(4, 0, 'Transaction Type : %s' % trx_type_str, wbf['title_doc'])
        worksheet.write_string(5, 0, 'Date : %s s/d %s' % (str(start_date), str(end_date)), wbf['title_doc'])

        row = 7
        header_row = row

        col = 0 #branch_code
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'Branch Code', wbf['header'])
        col += 1 #branch_name
        worksheet.set_column(col, col, 35)
        worksheet.write_string(row, col, 'Branch Name', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'Dealer Code', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 35)
        worksheet.write_string(row, col, 'Dealer Name', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 18.83)
        worksheet.write_string(row, col, 'Transaction Type', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 11.83)
        worksheet.write_string(row, col, 'Division', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 15)
        worksheet.write_string(row, col, 'Tipe PO', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 19.5)
        worksheet.write_string(row, col, 'No P2P', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 19.5)
        worksheet.write_string(row, col, 'Stock Distribution', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 12.67)
        worksheet.write_string(row, col, 'Date', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 10)
        worksheet.write_string(row, col, 'State', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 12.67)
        worksheet.write_string(row, col, 'Start Date', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 12.67)
        worksheet.write_string(row, col, 'End Date', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 50)
        worksheet.write_string(row, col, 'Description', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 20)
        worksheet.write_string(row, col, 'Product', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 9.83)
        worksheet.write_string(row, col, 'Color', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 14)
        worksheet.write_string(row, col, 'Category', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 20.5)
        worksheet.write_string(row, col, 'Unit Price', wbf['header'])
        col += 1
        col_requested_qty = col
        worksheet.set_column(col, col, 17.17)
        worksheet.write_string(row, col, 'Requested Qty', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 20.5)
        worksheet.write_string(row, col, 'Requested Amount', wbf['header'])
        col += 1
        col_approved_qty = col
        worksheet.set_column(col, col, 17.17)
        worksheet.write_string(row, col, 'Approved Qty', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 20.5)
        worksheet.write_string(row, col, 'Approved Amount', wbf['header'])
        col += 1
        col_qty = col
        worksheet.set_column(col, col, 17.17)
        worksheet.write_string(row, col, 'Qty', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 20.5)
        worksheet.write_string(row, col, 'Amount', wbf['header'])
        col += 1
        col_supplied_qty = col
        worksheet.set_column(col, col, 17.17)
        worksheet.write_string(row, col, 'Supplied Qty', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 20.5)
        worksheet.write_string(row, col, 'Supplied Amount', wbf['header'])
        data_last_col = col

        row += 1
        data_first_row = row

        for res in ress :
            branch_code = str(res[0].encode('ascii','ignore').decode('ascii')) if res[0] != None else ''
            branch_name = str(res[1].encode('ascii','ignore').decode('ascii')) if res[1] != None else ''
            dealer_code = str(res[2].encode('ascii','ignore').decode('ascii')) if res[2] != None else ''
            dealer_name = str(res[3].encode('ascii','ignore').decode('ascii')) if res[3] != None else ''
            trx_type = str(res[4].encode('ascii','ignore').decode('ascii')) if res[4] != None else ''
            division = str(res[5].encode('ascii','ignore').decode('ascii')) if res[5] != None else ''
            name = str(res[6].encode('ascii','ignore').decode('ascii')) if res[6] != None else ''
            date = datetime.strptime(res[7], "%Y-%m-%d").date() if res[7] else ''
            state = str(res[8].encode('ascii','ignore').decode('ascii')) if res[8] != None else ''
            start_date = datetime.strptime(res[9], "%Y-%m-%d").date() if res[9] else ''
            end_date = datetime.strptime(res[10], "%Y-%m-%d").date() if res[10] else ''
            tipe = str(res[11].encode('ascii','ignore').decode('ascii')) if res[11] != None else ''
            warna = str(res[12].encode('ascii','ignore').decode('ascii')) if res[12] != None else ''
            categ_name = str(res[13].encode('ascii','ignore').decode('ascii')) if res[13] != None else ''
            requested_qty = res[14]
            approved_qty = res[15]
            qty = res[16]
            supplied_qty = res[17]
            description = str(res[18].encode('ascii','ignore').decode('ascii')) if res[18] != None else ''
            unit_price = res[19]
            if not res[20]:
                p2p=''
            else:
                p2p=res[20]
            tipe_po = str(res[21].encode('ascii','ignore').decode('ascii')) if res[21] != None else ''
            
            
            if state == 'confirm' :
                state = 'Requested'
            elif state == 'waiting_for_approval' :
                state = 'Waiting for Approval'
            elif state == 'approved' :
                state = 'Approved'
            elif state == 'open' :
                state = 'Open'
            elif state == 'done' :
                state = 'Done'
            elif state == 'cancel' :
                state = 'Cancelled'
            elif state == 'reject' :
                state = 'Rejected'
            elif state == 'closed' :
                state = 'Closed'

            col = 0 #branch_code
            worksheet.write_string(row, col, branch_code, wbf['content'])
            col += 1 #branch_name
            worksheet.write_string(row, col, branch_name, wbf['content'])
            col += 1 #dealer_code
            worksheet.write_string(row, col, dealer_code, wbf['content'])
            col += 1 #dealer_name
            worksheet.write_string(row, col, dealer_name, wbf['content'])
            col += 1 #trx_type
            worksheet.write_string(row, col, trx_type, wbf['content'])
            col += 1 #division
            worksheet.write_string(row, col, division, wbf['content'])
            col += 1 #tipe_po
            worksheet.write_string(row, col, tipe_po, wbf['content'])
            col += 1 #p2p
            worksheet.write_string(row, col, p2p, wbf['content'])
            col += 1 #name
            worksheet.write_string(row, col, name, wbf['content'])
            col += 1 #date
            worksheet.write_datetime(row, col, date, wbf['content_date'])
            col += 1  #state
            worksheet.write_string(row, col,  state, wbf['content'])
            col += 1 #start_date
            worksheet.write(row, col, start_date, wbf['content_date'])
            col += 1 #end_date
            worksheet.write(row, col, end_date, wbf['content_date'])
            col += 1 #description
            worksheet.write_string(row, col, description, wbf['content'])
            col += 1 #tipe
            worksheet.write_string(row, col, tipe, wbf['content'])
            col += 1 #warna
            worksheet.write_string(row, col, warna, wbf['content'])
            col += 1 #categ_name
            worksheet.write_string(row, col, categ_name, wbf['content'])
            col += 1 #unit_price
            worksheet.write_number(row, col, unit_price, wbf['content_float'])
            col += 1 #requested_qty
            worksheet.write_number(row, col, requested_qty, wbf['content_number'])
            col += 1 #requested_amt
            worksheet.write_formula(row, col, '=S%s*R%s'%(row+1,row+1), wbf['content_float'])
            col += 1 #approved_qty
            worksheet.write_number(row, col, approved_qty, wbf['content_number'])
            col += 1 #approved_amt
            worksheet.write_formula(row, col, '=U%s*R%s'%(row+1,row+1), wbf['content_float'])
            col += 1 #qty
            worksheet.write_number(row, col, qty, wbf['content_number'])
            col += 1 #amt
            worksheet.write_formula(row, col, '=W%s*R%s'%(row+1,row+1), wbf['content_float'])
            col += 1 #supplied_qty
            worksheet.write_number(row, col, supplied_qty, wbf['content_number'])
            col += 1 #supplied_amt
            worksheet.write_formula(row, col, '=Y%s*R%s'%(row+1,row+1), wbf['content_float'])

            row += 1

        worksheet.autofilter(header_row, 0, row, data_last_col)

        #TOTAL
        worksheet.merge_range(row, 0, row, col_requested_qty-2, 'TOTAL', wbf['total'])
        worksheet.write_formula(row, col_requested_qty-1, '=SUBTOTAL(9, R%s:R%s)' % (data_first_row+1, row), wbf['total_number'])
        worksheet.write_formula(row, col_requested_qty, '=SUBTOTAL(9, S%s:S%s)' % (data_first_row+1, row), wbf['total_float'])
        worksheet.write_formula(row, col_approved_qty-1, '=SUBTOTAL(9, T%s:T%s)' % (data_first_row+1, row), wbf['total_number'])
        worksheet.write_formula(row, col_approved_qty, '=SUBTOTAL(9, U%s:U%s)' % (data_first_row+1, row), wbf['total_float'])
        worksheet.write_formula(row, col_qty-1, '=SUBTOTAL(9, V%s:V%s)' % (data_first_row+1, row), wbf['total_number'])
        worksheet.write_formula(row, col_qty, '=SUBTOTAL(9, W%s:W%s)' % (data_first_row+1, row), wbf['total_float'])
        worksheet.write_formula(row, col_supplied_qty-1, '=SUBTOTAL(9, X%s:X%s)' % (data_first_row+1, row), wbf['total_number'])
        worksheet.write_formula(row, col_supplied_qty, '=SUBTOTAL(9, Y%s:Y%s)' % (data_first_row+1, row), wbf['total_float'])
        worksheet.write_formula(row, col_supplied_qty+1, '=SUBTOTAL(9, Z%s:Z%s)' % (data_first_row+1, row), wbf['total_float'])

        worksheet.write(row+2, 0, '%s %s' % (str(curr_date.strftime("%Y-%m-%d %H:%M:%S")),username) , wbf['footer'])  

        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        return True


    def _query_report_stock_distribution_detail(self, **kwargs):
        state = kwargs['state'] if 'state' in kwargs else None
        division = kwargs['division'] if 'division' in kwargs else None
        trx_type = kwargs['trx_type'] if 'trx_type' in kwargs else None
        start_date = kwargs['start_date'] if 'start_date' in kwargs else None
        end_date = kwargs['end_date'] if 'end_date' in kwargs else None
        branch_ids = kwargs['branch_ids'] if 'branch_ids' in kwargs else None
        dealer_ids = kwargs['dealer_ids'] if 'dealer_ids' in kwargs else None
        state_str = kwargs['state_str'] if 'state_str' in kwargs else ''
        division_str = kwargs['division_str'] if 'division_str' in kwargs else 'All'
        trx_type_str = kwargs['trx_type_str'] if 'trx_type_str' in kwargs else 'All'

        query_where = " WHERE 1=1 "

        if state == 'requested' :
            query_where += " AND sd.state in ('confirm', 'waiting_for_approval', 'approved') "
            state_str = 'Requested'
        elif state == 'open' :
            query_where += " AND sd.state = 'open' "
            state_str = 'Open'
        elif state == 'done' :
            query_where += " AND sd.state in ('done', 'closed') "
            state_str = 'Done'
        elif state == 'open_done' :
            query_where += " AND sd.state in ('open', 'done', 'closed') "
            state_str = 'Open & Done'
        elif state == 'open_done_cancel' :
            query_where += " AND sd.state in ('open', 'done', 'closed', 'cancel') "
            state_str = 'Open, Done & Cancelled'
        elif state == 'reject' :
            query_where += " AND sd.state = 'reject' "
            state_str = 'Rejected'
        elif state == 'all' :
            query_where += ""
            state_str = 'All'

        if division == 'Unit' :
            query_where += " AND sd.division = 'Unit' "
            division_str = 'Unit'
        elif division == 'Sparepart' :
            query_where += " AND sd.division = 'Sparepart' "
            division_str = 'Sparepart'

        if trx_type == 'mutation' :
            query_where += " AND sd.branch_requester_id IS NOT NULL "
            trx_type_str = 'Mutation'
        elif trx_type == 'sales' :
            query_where += " AND sd.branch_requester_id IS NULL "
            trx_type_str = 'Sales'

        if start_date :
            query_where += " AND sd.date >= '%s' " % start_date
            
        if end_date :
            query_where += " AND sd.date <= '%s' " % end_date

        if branch_ids :
            query_where += " AND b.id in %s " % str(tuple(branch_ids)).replace(',)', ')')

        if dealer_ids :
            query_where += " AND dealer.id in %s " % str(tuple(dealer_ids)).replace(',)', ')')

        query = """
            select b.code as branch_code
            , b.name as branch_name
            , dealer.default_code as dealer_code
            , dealer.name as dealer_name
            , CASE WHEN sd.branch_requester_id IS NOT NULL THEN 'Mutation' ELSE 'Sales' END as trx_type
            , sd.division
            , sd.name
            , sd.date
            , sd.state
            , sd.start_date
            , sd.end_date
            , product.name_template as tipe
            , COALESCE(pav.code,'') as warna
            , prod_cat.name as categ_name
            , COALESCE(sdl.requested_qty,0) as requested_qty
            , COALESCE(sdl.approved_qty, 0) as approved_qty
            , COALESCE(sdl.qty, 0) as qty
            , COALESCE(sdl.supply_qty, 0) as supplied_qty
            , sd.description
            , COALESCE(sdl.unit_price, 0) as unit_price
            , sd.origin as p2p
            , pot.name as tipe_po            
            from wtc_stock_distribution sd
            left join wtc_branch b on sd.branch_id = b.id
            left join wtc_purchase_order_type pot on sd.type_id = pot.id
            left join res_partner dealer on sd.dealer_id = dealer.id
            left join wtc_stock_distribution_line sdl on sd.id = sdl.distribution_id
            left join product_product product on sdl.product_id = product.id
            left join product_attribute_value_product_product_rel pavpp on pavpp.prod_id = product.id
            left join product_attribute_value pav on pav.id = pavpp.att_id
            left join product_template prod_template on product.product_tmpl_id = prod_template.id
            left join product_category prod_cat on prod_template.categ_id = prod_cat.id

            %s

            order by b.code, sd.date, sd.id, sdl.id
        """ % (query_where)

        return query