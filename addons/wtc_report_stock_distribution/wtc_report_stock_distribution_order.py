from openerp.osv import fields, osv
from datetime import datetime
from cStringIO import StringIO
import base64
import xlsxwriter

class wtc_report_stock_distribution_order(osv.osv_memory):
    _inherit = "wtc.report.stock.distribution"

    def _print_excel_report_order(self, cr, uid, ids, data, context=None):
        curr_date= self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)
        user = self.pool.get('res.users').browse(cr, uid, uid)
        company_name = user.company_id.name
        username = user.name
        
        filename = 'stock_distribution_'+str(curr_date.strftime("%Y%m%d_%H%M%S"))+'.xlsx'

        state = data['state']
        order_state = data['order_state']
        division = data['division']
        trx_type = data['trx_type']
        start_date = data['start_date']
        end_date = data['end_date']
        branch_ids = data['branch_ids']
        dealer_ids = data['dealer_ids']
        state_str = ''
        order_state_str = 'All'
        division_str = 'All'
        trx_type_str = 'All'

        query_where = ""

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

        if order_state == 'draft' :
            query_where += " AND so.state = 'draft' "
            order_state_str = 'Draft'
        elif order_state == 'confirm' :
            query_where += " AND so.state in ('progress', 'confirm') "
            order_state_str = 'In Progress'
        elif order_state == 'done' :
            query_where += " AND so.state = 'done' "
            order_state_str = 'Done'
        elif order_state == 'cancel' :
            query_where += " AND so.state in ('cancel', 'cancelled') "
            order_state_str = 'Cancelled'

        if division == 'Unit' :
            query_where += " AND sd.division = 'Unit' "
            division_str = 'Unit'
        elif division == 'Sparepart' :
            query_where += " AND sd.division = 'Sparepart' "
            division_str = 'Sparepart'

        if start_date :
            query_where += " AND sd.date >= '%s' " % start_date
            
        if end_date :
            query_where += " AND sd.date <= '%s' " % end_date

        if branch_ids :
            query_where += " AND b.id in %s " % str(tuple(branch_ids)).replace(',)', ')')

        if dealer_ids :
            query_where += " AND dealer.id in %s " % str(tuple(dealer_ids)).replace(',)', ')')

        query_mutation = ""
        if trx_type == 'mutation' or trx_type == 'all' or trx_type == False :
            query_mutation = """
                (select b.code as branch_code
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
                , sd.description
                , so.name as order_name
                , so.date as order_date
                , so.state as order_state
                , product.name_template as tipe
                , COALESCE(pav.code,'') as warna
                , prod_cat.name as categ_name
                , COALESCE(sol.qty, 0) as qty
                , COALESCE(sol.unit_price, 0) as unit_price
                , 0 as discount
                , COALESCE(sol.supply_qty,0) as supplied_qty
                from wtc_stock_distribution sd
                left join wtc_branch b on sd.branch_id = b.id
                left join res_partner dealer on sd.dealer_id = dealer.id
                left join wtc_mutation_order so on sd.id = so.distribution_id
                left join wtc_mutation_order_line sol on so.id = sol.order_id
                left join product_product product on sol.product_id = product.id
                left join product_attribute_value_product_product_rel pavpp on pavpp.prod_id = product.id
                left join product_attribute_value pav on pav.id = pavpp.att_id
                left join product_template prod_template on product.product_tmpl_id = prod_template.id
                left join product_category prod_cat on prod_template.categ_id = prod_cat.id
                where sd.branch_requester_id IS NOT NULL
                %s
                order by branch_code, dealer_code, date, name, order_date, order_name, tipe)
            """ % (query_where)

        query_sales = ""
        if trx_type == 'sales' or trx_type == 'all' or trx_type == False :
            if order_state == 'confirm' :
                query_where += " AND (sol.product_uom_qty IS NOT NULL AND dist.qty IS NOT NULL AND sol.product_uom_qty != dist.qty) "
            query_sales = """
                (select b.code as branch_code
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
                , sd.description
                , so.name as order_name
                , (so.date_order + interval '7 hours')::timestamp::date as order_date
                , so.state as order_state
                , product.name_template as tipe
                , COALESCE(pav.code,'') as warna
                , prod_cat.name as categ_name
                , COALESCE(sol.product_uom_qty, 0) as qty
                , COALESCE(sol.price_unit, 0) as unit_price
                , COALESCE(sol.discount, 0) as discount
                , COALESCE(dist.qty, 0) as supplied_qty
                from wtc_stock_distribution sd
                left join wtc_branch b on sd.branch_id = b.id
                left join res_partner dealer on sd.dealer_id = dealer.id
                left join sale_order so on sd.id = so.distribution_id
                left join sale_order_line sol on so.id = sol.order_id
                left join product_product product on sol.product_id = product.id
                left join product_attribute_value_product_product_rel pavpp on pavpp.prod_id = product.id
                left join product_attribute_value pav on pav.id = pavpp.att_id
                left join product_template prod_template on product.product_tmpl_id = prod_template.id
                left join product_category prod_cat on prod_template.categ_id = prod_cat.id
                left join (select pick.transaction_id, pick.origin, move.product_id, sum(move.product_qty) as qty
                from stock_picking pick
                inner join stock_move move on pick.id = move.picking_id
                inner join ir_model mdl on pick.model_id = mdl.id
                where pick.state = 'done'
                and mdl.model = 'sale.order'
                group by pick.transaction_id, pick.origin, move.product_id) dist on so.name = dist.origin and sol.product_id = dist.product_id
                where sd.branch_requester_id IS NULL
                %s
                order by branch_code, dealer_code, date, name, order_date, order_name, tipe)
            """ % (query_where)


        if trx_type == 'mutation' :
            query = query_mutation
        elif trx_type == 'sales' :
            query = query_sales
        else :
            query = """
                select * from (%s UNION %s) a
                order by branch_code, dealer_code, date, name, order_date, order_name, tipe
            """ % (query_mutation, query_sales)

        cr.execute(query)
        ress = cr.fetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet("Stock Distribution Order")

        worksheet.set_column(0, 0, 8.43)

        worksheet.write_string(0, 0, company_name , wbf['company'])
        worksheet.write_string(1, 0, "Report Stock Distribution's Order" , wbf['title_doc'])
        worksheet.write_string(2, 0, "Distribution's State : %s" % state_str, wbf['title_doc'])
        worksheet.write_string(3, 0, "Order's State : %s" % order_state_str, wbf['title_doc'])
        worksheet.write_string(4, 0, 'Division : %s' % division_str, wbf['title_doc'])
        worksheet.write_string(5, 0, 'Transaction Type : %s' % trx_type_str, wbf['title_doc'])
        worksheet.write_string(6, 0, 'Date : %s s/d %s' % (str(start_date), str(end_date)), wbf['title_doc'])

        row = 8
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
        worksheet.set_column(col, col, 19.5)
        worksheet.write_string(row, col, 'Stock Distribution', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 12.67)
        worksheet.write_string(row, col, 'Date', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 10)
        worksheet.write_string(row, col, "Distribution's State", wbf['header'])
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
        worksheet.set_column(col, col, 19.5)
        worksheet.write_string(row, col, 'Order Name', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 12.67)
        worksheet.write_string(row, col, 'Order Date', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 10)
        worksheet.write_string(row, col, 'Order State', wbf['header'])
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
        col_qty = col
        worksheet.set_column(col, col, 17.17)
        worksheet.write_string(row, col, 'Qty', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 20.5)
        worksheet.write_string(row, col, 'Unit Price', wbf['header'])
        col += 1
        worksheet.set_column(col, col, 20.5)
        worksheet.write_string(row, col, 'Discount', wbf['header'])
        col += 1
        col_amt = col
        worksheet.set_column(col, col, 20.5)
        worksheet.write_string(row, col, 'Est Amount', wbf['header'])
        col += 1
        col_supplied_qty = col
        worksheet.set_column(col, col, 17.17)
        worksheet.write_string(row, col, 'Supplied Qty', wbf['header'])
        col += 1
        col_supplied_amt = col
        worksheet.set_column(col, col, 20.5)
        worksheet.write_string(row, col, 'Est Supplied Amount', wbf['header'])
        col += 1
        col_outstanding_qty = col
        worksheet.set_column(col, col, 17.17)
        worksheet.write_string(row, col, 'Outstanding Qty', wbf['header'])
        col += 1
        col_outstanding_amt = col
        worksheet.set_column(col, col, 20.5)
        worksheet.write_string(row, col, 'Est Outstanding Amount', wbf['header'])
        data_last_col = col

        row += 1
        data_first_row = row

        name_prev = False
        row_prev = False
        
        for res in ress :
            name = str(res[6].encode('ascii','ignore').decode('ascii')) if res[6] != None else ''

            if name_prev != False and name_prev != name :
                col = 0 #branch_code
                worksheet.merge_range(row_prev, col, row-1, col, "")
                worksheet.write_string(row_prev, col, branch_code, wbf['content'])
                col += 1 #branch_name
                worksheet.merge_range(row_prev, col, row-1, col, "")
                worksheet.write_string(row_prev, col, branch_name, wbf['content'])
                col += 1 #dealer_code
                worksheet.merge_range(row_prev, col, row-1, col, "")
                worksheet.write_string(row_prev, col, dealer_code, wbf['content'])
                col += 1 #dealer_name
                worksheet.merge_range(row_prev, col, row-1, col, "")
                worksheet.write_string(row_prev, col, dealer_name, wbf['content'])
                col += 1 #trx_type
                worksheet.merge_range(row_prev, col, row-1, col, "")
                worksheet.write_string(row_prev, col, trx_type, wbf['content'])
                col += 1 #division
                worksheet.merge_range(row_prev, col, row-1, col, "")
                worksheet.write_string(row_prev, col, division, wbf['content'])
                col += 1 #name
                worksheet.merge_range(row_prev, col, row-1, col, "")
                worksheet.write_string(row_prev, col, name_prev, wbf['content'])
                col += 1 #date
                worksheet.merge_range(row_prev, col, row-1, col, "")
                worksheet.write(row_prev, col, date, wbf['content_date'])
                col += 1  #state
                worksheet.merge_range(row_prev, col, row-1, col, "")
                worksheet.write_string(row_prev, col,  state, wbf['content'])
                col += 1 #start_date
                worksheet.merge_range(row_prev, col, row-1, col, "")
                worksheet.write(row_prev, col, start_date, wbf['content_date'])
                col += 1 #end_date
                worksheet.merge_range(row_prev, col, row-1, col, "")
                worksheet.write(row_prev, col, end_date, wbf['content_date'])
                col += 1 #description
                worksheet.merge_range(row_prev, col, row-1, col, "")
                worksheet.write_string(row_prev, col, description, wbf['content'])

            if name_prev == False or name_prev != name :
                name_prev = name
                row_prev = row

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
            description = str(res[11].encode('ascii','ignore').decode('ascii')) if res[11] != None else ''
            order_name = str(res[12].encode('ascii','ignore').decode('ascii')) if res[12] != None else ''
            order_date = datetime.strptime(res[13], "%Y-%m-%d").date() if res[13] and res[13] != '' else ''
            order_state = str(res[14].encode('ascii','ignore').decode('ascii')) if res[14] != None else ''
            tipe = str(res[15].encode('ascii','ignore').decode('ascii')) if res[15] != None else ''
            warna = str(res[16].encode('ascii','ignore').decode('ascii')) if res[16] != None else ''
            categ_name = str(res[17].encode('ascii','ignore').decode('ascii')) if res[17] != None else ''
            qty = res[18]
            unit_price = res[19]
            discount = res[20]
            supplied_qty = res[21]

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

            if order_state == 'draft' :
                order_state = 'Draft'
            elif order_state == 'confirm' or order_state == 'progress' :
                order_state = 'In Progress'
            elif order_state == 'done' :
                order_state = 'Done'
            elif order_state == 'cancel' or order_state == 'cancelled' :
                order_state = 'Cancelled'

            if trx_type == 'Sales' and qty > 0 and qty == supplied_qty :
                order_state = 'Done'

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
            col += 1 #name
            worksheet.write_string(row, col, name, wbf['content'])
            col += 1 #date
            worksheet.write(row, col, date, wbf['content_date'])
            col += 1  #state
            worksheet.write_string(row, col,  state, wbf['content'])
            col += 1 #start_date
            worksheet.write(row, col, start_date, wbf['content_date'])
            col += 1 #end_date
            worksheet.write(row, col, end_date, wbf['content_date'])
            col += 1 #description
            worksheet.write_string(row, col, description, wbf['content'])
            col += 1 #order_name
            worksheet.write_string(row, col, order_name, wbf['content'])

            col += 1 #order_date
            if order_date == '' :
                worksheet.write_blank(row, col, None, wbf['content_date'])
            else :
                worksheet.write_datetime(row, col, order_date, wbf['content_date'])
            col += 1 #order_state
            worksheet.write_string(row, col, order_state, wbf['content'])
            col += 1 #tipe
            worksheet.write_string(row, col, tipe, wbf['content'])
            col += 1 #warna
            worksheet.write_string(row, col, warna, wbf['content'])
            col += 1 #categ_name
            worksheet.write_string(row, col, categ_name, wbf['content'])
            col += 1 #qty
            worksheet.write_number(row, col, qty, wbf['content_number'])
            col += 1 #unit_price
            worksheet.write_number(row, col, unit_price, wbf['content_float'])
            col += 1 #discount
            worksheet.write_number(row, col, discount, wbf['content_float'])
            col += 1 #amount
            worksheet.write_formula(row, col, '=S%s*T%s*(100-U%s)/100'%(row+1,row+1,row+1), wbf['content_float'])
            col += 1 #supplied_qty
            worksheet.write_number(row, col, supplied_qty, wbf['content_number'])
            col += 1 #supplied_amount
            worksheet.write_formula(row, col, '=W%s*T%s*(100-U%s)/100'%(row+1,row+1,row+1), wbf['content_float'])
            col += 1 #outstanding_qty
            worksheet.write_formula(row, col, '=S%s-W%s'%(row+1,row+1), wbf['content_number'])
            col += 1 #outstanding_amount
            worksheet.write_formula(row, col, '=Y%s*T%s*(100-U%s)/100'%(row+1,row+1,row+1), wbf['content_float'])

            row += 1

        if name_prev != False :
            col = 0 #branch_code
            worksheet.merge_range(row_prev, col, row-1, col, "")
            worksheet.write_string(row_prev, col, branch_code, wbf['content'])
            col += 1 #branch_name
            worksheet.merge_range(row_prev, col, row-1, col, "")
            worksheet.write_string(row_prev, col, branch_name, wbf['content'])
            col += 1 #dealer_code
            worksheet.merge_range(row_prev, col, row-1, col, "")
            worksheet.write_string(row_prev, col, dealer_code, wbf['content'])
            col += 1 #dealer_name
            worksheet.merge_range(row_prev, col, row-1, col, "")
            worksheet.write_string(row_prev, col, dealer_name, wbf['content'])
            col += 1 #trx_type
            worksheet.merge_range(row_prev, col, row-1, col, "")
            worksheet.write_string(row_prev, col, trx_type, wbf['content'])
            col += 1 #division
            worksheet.merge_range(row_prev, col, row-1, col, "")
            worksheet.write_string(row_prev, col, division, wbf['content'])
            col += 1 #name
            worksheet.merge_range(row_prev, col, row-1, col, "")
            worksheet.write_string(row_prev, col, name_prev, wbf['content'])
            col += 1 #date
            worksheet.merge_range(row_prev, col, row-1, col, "")
            worksheet.write(row_prev, col, date, wbf['content_date'])
            col += 1  #state
            worksheet.merge_range(row_prev, col, row-1, col, "")
            worksheet.write_string(row_prev, col,  state, wbf['content'])
            col += 1 #start_date
            worksheet.merge_range(row_prev, col, row-1, col, "")
            worksheet.write(row_prev, col, start_date, wbf['content_date'])
            col += 1 #end_date
            worksheet.merge_range(row_prev, col, row-1, col, "")
            worksheet.write(row_prev, col, end_date, wbf['content_date'])
            col += 1 #description
            worksheet.merge_range(row_prev, col, row-1, col, "")
            worksheet.write_string(row_prev, col, description, wbf['content'])

        worksheet.autofilter(header_row, 0, row, data_last_col)

        #TOTAL
        for i in range (0, data_last_col) :
            worksheet.write_blank(row, i, None, wbf['total'])
        worksheet.merge_range(row, 0, row, col_qty-1, 'TOTAL', wbf['total'])
        worksheet.write_formula(row, col_qty, '=SUBTOTAL(9, S%s:S%s)' % (data_first_row+1, row), wbf['total_number'])
        worksheet.write_formula(row, col_amt, '=SUBTOTAL(9, V%s:V%s)' % (data_first_row+1, row), wbf['total_float'])
        worksheet.write_formula(row, col_supplied_qty, '=SUBTOTAL(9, W%s:W%s)' % (data_first_row+1, row), wbf['total_number'])
        worksheet.write_formula(row, col_supplied_amt, '=SUBTOTAL(9, X%s:X%s)' % (data_first_row+1, row), wbf['total_float'])
        worksheet.write_formula(row, col_outstanding_qty, '=SUBTOTAL(9, Y%s:Y%s)' % (data_first_row+1, row), wbf['total_number'])
        worksheet.write_formula(row, col_outstanding_amt, '=SUBTOTAL(9, Z%s:Z%s)' % (data_first_row+1, row), wbf['total_float'])

        worksheet.write(row+2, 0, '%s %s' % (str(curr_date.strftime("%Y-%m-%d %H:%M:%S")),username) , wbf['footer'])  

        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        return True
