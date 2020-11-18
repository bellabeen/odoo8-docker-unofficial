

from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import orm
from openerp.osv import fields, osv
import logging
_logger = logging.getLogger(__name__)


class wtc_work_order_report_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(wtc_work_order_report_print, self).__init__(
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
        date_from = data['date_from']
        date_to = data['date_to']
        type = data['type']

        title_prefix = ''
        title_short_prefix = ''
     
        report_ar = {
            'type': 'receivable',
            'title': title_prefix + _(''),
            'title_short': title_short_prefix + ', ' + _('Dealer_sale_order')}
       


        query_start = "select a.id as p_id, " \
                      "a.name as p_name, " \
                      "c.name as p_cabang, " \
                      "a.state as p_state, " \
                      "a.date as p_tanggal, " \
                      "a.no_pol as p_no_pol, " \
                      "f.name as p_tp, " \
                      "e.description as p_jasa_part, " \
                      "b.price_unit as p_harga, " \
                      "b.product_qty as p_jumlah, " \
                      "b.discount as p_discount, " \
                      "a.type as p_type, " \
                      "round(b.price_unit/1.1) as p_dpp, " \
                      "round((b.price_unit*b.product_qty)-(b.discount/100)) as  p_jumlah_harga " \
                      "from wtc_work_order a  " \
                      "left join wtc_work_order_line b ON a.id = b.work_order_id " \
                      "left join wtc_branch c ON c.id = a.branch_id " \
                      "left join product_product d ON d.id = b.product_id " \
                      "LEFT JOIN product_template e ON e.id = d.product_tmpl_id " \
                      "LEFT JOIN product_category f ON f.id = e.categ_id " \
                     
                      
        query_start +=" where a.id is not null "

        move_selection = ""
        report_info = _('')
        move_selection += ""
            
        query_end=""
        if branch_ids :
            query_end +=" AND  a.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
                
        if type :
            query_end +=" AND  a.type in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
                
        if date_from :
            query_end+= ' AND  a.date >= ' +"'"+ date_from + "'" + \
            'AND  a.date <= ' +"'"+ date_to + "'" + \
            ''
        query_order="order by p_cabang,p_name "
        reports = [report_ar]

        for report in reports:
            cr.execute(query_start + query_end+query_order)
            all_lines = cr.dictfetchall()
            partners = []

            if all_lines:
                def lines_map(x):
                        x.update({'docname': x['p_name']})
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
                        'p_cabang': x['p_cabang'],
                        'p_state': x['p_state'],
                        'p_tanggal': x['p_tanggal'],
                        'p_no_pol': x['p_no_pol'],
                        'p_tp': x['p_tp'],
                        'p_jasa_part': str(x['p_jasa_part']),
                        'p_jumlah': str(x['p_jumlah']),
                        'p_harga': str(x['p_harga']),
                        'p_discount': str(x['p_discount']),
                        'p_type': x['p_type'],
                        'p_dpp': str(x['p_dpp']),
                        'p_jumlah_harga': str(x['p_jumlah_harga'])
                        },
                            
                    all_lines)
                for p in p_map:
                    if p['p_id'] not in map(
                            lambda x: x.get('p_id', None), partners):
                        partners.append(p)
                        partner_lines = filter(
                            lambda x: x['p_id'] == p['p_id'], all_lines)
                        p.update({'lines': partner_lines})
                        p.update(
                            {'d': 1,
                             'c': 2,
                             'b': 3})
                report.update({'partners': partners})

                

        reports = filter(lambda x: x.get('partners'), reports)
        if not reports:
            raise orm.except_orm(
                _('No Data Available'),
                _('No records found for your selection!'))

        report_date = datetime_field.context_timestamp(
            cr, uid, datetime.now(), context
            ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        self.localcontext.update({
            'report_info': report_info,
            'report_date': report_date,
            'reports': reports,
            })
        super(wtc_work_order_report_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(wtc_work_order_report_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.wtc_work_order.report_work_order'
    _inherit = 'report.abstract_report'
    _template = 'wtc_work_order.report_work_order'
    _wrapped_report_class = wtc_work_order_report_print
