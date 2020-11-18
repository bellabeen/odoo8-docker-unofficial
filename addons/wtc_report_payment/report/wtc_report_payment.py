from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import orm
import logging
_logger = logging.getLogger(__name__)


class wtc_report_payment_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(wtc_report_payment_print, self).__init__(
            cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({
            'formatLang_zero2blank': self.formatLang_zero2blank,
            })

    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context
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
            table_line = "account_voucher_line"
            is_hutang_lain_where = 'is_hutang_lain = false'
        elif option == 'supplier_payment_detail_old' :
            where_option=" av.type = 'payment' "
            table = "account_voucher"
            table_line = "account_voucher_line"
            is_hutang_lain_where = 'is_hutang_lain = false'
        elif option == 'customer_payment_detail' :
            where_option=" av.type = 'receipt' "
            table = "wtc_account_voucher"
            table_line = "wtc_account_voucher_line"    
        elif option == 'supplier_payment_detail' :
            where_option=" av.type = 'payment' "
            table = "wtc_account_voucher"
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
        
        query_start = "select av.id as p_id, b.code as p_name, " \
            "b.name as nama_cabang_untuk, b_to.code as code_cabang_terima, b_to.name as nama_cabang_terima, av.number as p_ref, " \
            "av.state as status, aj.name as payment_method, aa.code as account, av.amount as paid_amount, partner.default_code as partner_code, partner.name as partner_name, " \
            "av.amount-COALESCE(line_cr.amount,0)+COALESCE(line_dr.amount,0) as diff, " \
            "aml.ref as no_transaksi, " \
            "avl.type as a_type, " \
            "(CASE WHEN avl.type='cr' THEN avl.amount   END) AS credit, " \
            " (CASE WHEN avl.type='dr' THEN avl.amount   END) AS debit " \
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
            "where  "+is_hutang_lain_where+" " \
            "AND "+where_account+" AND "+where_option+" AND "+where_branch+" AND "+where_journal+" AND "+where_division+" AND "+where_start_date+" AND "+where_end_date+" AND "+where_partner+" "\

        reports = [report]
        report_info = title_type

        for report in reports:
            cr.execute(query_start)
            all_lines = cr.dictfetchall()
            partners = []

            if all_lines:
                def lines_map(x):
                    x.update({'docname': x['nama_cabang_untuk']})
                map(lines_map, all_lines)
                for cnt in range(len(all_lines)-1):
                    if all_lines[cnt]['p_id'] != all_lines[cnt+1]['p_id']:
                        all_lines[cnt]['draw_line'] = 1
                    else:
                        all_lines[cnt]['draw_line'] = 0
                all_lines[-1]['draw_line'] = 1

                p_map = map(
                    lambda x: {
                        'p_id': x['p_id'],
                        'p_name': x['p_name'],
                        'nama_cabang_untuk': x['nama_cabang_untuk'],
                        'code_cabang_terima': x['code_cabang_terima'],
                        'nama_cabang_terima': x['nama_cabang_terima'],
                        'p_ref': x['p_ref'],
                        'no_transaksi':x['no_transaksi'],
                        'status': x['status'],
                        'payment_method': x['payment_method'],
                        'account': x['account'],
                        'paid_amount': str(x['paid_amount']),
                        'partner_code': x['partner_code'],
                        'diff': str(x['diff']),
                        'partner_name': x['partner_name']},
                    all_lines)
                for p in p_map:
                    if p['p_id'] not in map(
                            lambda x: x.get('p_id', None), partners):
                        partners.append(p)
                        partner_lines = filter(
                            lambda x: x['p_id'] == p['p_id'], all_lines)
                        p.update({'lines': partner_lines})
                        debits = map(
                            lambda x: x['debit'] or 0.0, partner_lines)
                        sum_debit = reduce(lambda x, y: x + y, debits)
                        sum_debit = round(sum_debit, digits)
                        credits = map(
                            lambda x: x['credit'] or 0.0, partner_lines)
                        sum_credit = reduce(lambda x, y: x + y, credits)
                        sum_credit = round(sum_credit, digits)
                        balance = sum_debit - sum_credit
                        p.update(
                            {'d': sum_debit,
                             'c': sum_credit,
                             'b': balance})
                report.update({'partners': partners})

                sum_debit = 0.0
                sum_credit = 0.0
                acc_lines = filter(
                    lambda x: x['a_type'] == report['type'], all_lines)
                debits = map(lambda x: x['debit'] or 0.0, acc_lines)
                if debits:
                    sum_debit = reduce(lambda x, y: x + y, debits)
                    sum_debit = round(sum_debit, digits)
                credits = map(lambda x: x['credit'] or 0.0, acc_lines)
                if credits:
                    sum_credit = reduce(lambda x, y: x + y, credits)
                    sum_credit = round(sum_credit, digits)
                balance = sum_debit - sum_credit
                report.update({'d': sum_debit, 'c': sum_credit, 'b': balance})

        reports = filter(lambda x: x.get('partners'), reports)
        
        if not reports:
            partners = []
            reports = [{'title_short': 'Report Payment', 'type': '', 'partners':'null', 'title': title_type}]


        report_date = datetime_field.context_timestamp(
            cr, uid, datetime.now(), context
            ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        self.localcontext.update({
            'report_info': report_info,
            'report_date': report_date,
            'reports': reports,
            })
        super(wtc_report_payment_print, self).set_context(
            objects, data, ids, report_type=report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False,
                              date_time=False, grouping=True, monetary=False,
                              dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(wtc_report_payment_print, self).formatLang(
                value, digits=digits, date=date, date_time=date_time,
                grouping=grouping, monetary=monetary, dp=dp,
                currency_obj=currency_obj)


class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.wtc_report_payment_xls.report_payment'
    _inherit = 'report.abstract_report'
    _template = 'wtc_report_payment_xls.report_payment'
    _wrapped_report_class = wtc_report_payment_print
