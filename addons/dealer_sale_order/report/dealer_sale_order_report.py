

from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import orm
from openerp.osv import fields, osv
import logging
_logger = logging.getLogger(__name__)


class wtc_dealer_sale_order_report_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(wtc_dealer_sale_order_report_print, self).__init__(
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
        state = data['state']
        jenis_penjualan = data['jenis_penjualan']

        title_prefix = ''
        title_short_prefix = ''
     
        report_ar = {
            'type': 'receivable',
            'title': title_prefix + _(''),
            'title_short': title_short_prefix + ', ' + _('Dealer_sale_order')}
       


        query_start = "select a.id as p_id, " \
                      "a.name as p_name, " \
                      "a.state as p_state, " \
                      "a.date_order as p_date_order, " \
                      "c.name as p_konsumen, " \
                      "z.name as p_salesman, " \
                      "e.name as p_fincoy, " \
                      "a.customer_dp as p_customer_dp, " \
                      "a.sales_source as p_sales_source, " \
                      "b.cicilan as p_cicilan, " \
                      "f.name as p_location_id, " \
                      "g.name_template as p_kode_product,  " \
                      "j.code as p_warna  , " \
                      "k.name as p_mesin,  " \
                      "k.chassis_no as p_rangka,  " \
                      "b.finco_tenor as p_tenor,  " \
                      "b.is_bbn as p_is_bbn,  " \
                      "l.name as p_nama_stnk,  " \
                      "b.uang_muka as p_uang_muka,  " \
                      "b.discount_po as p_pot_pelanggan,  " \
                      "b.price_unit as p_harga,  " \
                      "b.discount_total as p_total_discount,  " \
                      "b.price_bbn as p_harga_bbn,  " \
                      "m.name as p_cabang,  " \
                      "c.default_code as p_default_code  " \
                      "from dealer_sale_order a " \
                      "left join dealer_sale_order_line b ON a.id = b.dealer_sale_order_line_id " \
                      "left join res_partner c ON c.id = a.partner_id " \
                      "left join res_users d ON d.id = a.user_id " \
                      "left join res_partner z ON z.id = d.partner_id " \
                      "left join res_partner e ON e.id = a.finco_id " \
                      "left join stock_location f ON f.id = b.location_id " \
                      "LEFT JOIN product_product g ON g.id = b.product_id " \
                      "LEFT JOIN product_template h ON h.id = g.product_tmpl_id " \
                      "LEFT JOIN product_attribute_value_product_product_rel i ON i.prod_id = b.product_id " \
                      "LEFT JOIN product_attribute_value j ON j.id = i.att_id " \
                      "LEFT JOIN stock_production_lot k ON k.id = b.lot_id " \
                      "left join res_partner l ON l.id = b.partner_stnk_id " \
                      "left join wtc_branch m ON m.id = a.branch_id " \
                      
        query_start +=" where a.id is not null "

        move_selection = ""
        report_info = _('')
        move_selection += ""
            
        query_end=""
        if branch_ids :
            query_end +=" AND  a.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
                
        if state :
            query_end +=" AND  a.state in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
                
        if date_from :
            query_end+= ' AND  a.date_order >= ' +"'"+ date_from + "'" + \
            'AND  a.date_order <= ' +"'"+ date_to + "'" + \
            ''
        if jenis_penjualan  and jenis_penjualan == 'cash':
            query_end +=" AND  a.finco_id is null "
            
        if jenis_penjualan  and jenis_penjualan == 'kredit':
            query_end +=" AND  a.finco_id is not null "
            
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
                        'p_state': x['p_state'],
                        'p_date_order': x['p_date_order'],
                        'p_konsumen': x['p_konsumen'],
                        'p_salesman': x['p_salesman'],
                        'p_fincoy': x['p_fincoy'],
                        'p_sales_source': x['p_sales_source'],
                        'p_cicilan': str(x['p_cicilan']),
                        'p_location_id': x['p_location_id'],
                        'p_kode_product': x['p_kode_product'],
                        'p_warna': x['p_warna'],
                        'p_cabang': x['p_cabang'],
                        'p_mesin': x['p_mesin'],
                        'p_default_code': x['p_default_code'],
                        'p_rangka': x['p_rangka'],
                        'p_tenor': str(x['p_tenor']),
                        'p_is_bbn': x['p_is_bbn'],
                        'p_nama_stnk': x['p_nama_stnk'],
                        'p_uang_muka': str(x['p_uang_muka']),
                        'p_pot_pelanggan': str(x['p_pot_pelanggan']),
                        'p_harga': str(x['p_harga']),
                        'p_total_discount': str(x['p_total_discount']),
                        'p_harga_bbn': str(x['p_harga_bbn']),
                        'p_customer_dp': str(x['p_customer_dp'])
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
        super(wtc_dealer_sale_order_report_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(wtc_dealer_sale_order_report_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dealer_sale_order.report_dealer_sale_order'
    _inherit = 'report.abstract_report'
    _template = 'dealer_sale_order.report_dealer_sale_order'
    _wrapped_report_class = wtc_dealer_sale_order_report_print
