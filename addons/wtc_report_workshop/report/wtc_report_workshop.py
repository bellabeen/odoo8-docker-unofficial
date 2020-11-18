from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm

class wtc_report_workshop_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(wtc_report_workshop_print, self).__init__(cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({'formatLang_zero2blank': self.formatLang_zero2blank})

    def set_context(self, objects, data, ids, report_type=None):
        wo_categ = data['wo_categ']
        state = data['state']
        start_date = data['start_date']
        end_date = data['end_date']
        product_ids = data['product_ids']
        branch_ids = data['branch_ids']
        partner_ids = data['partner_ids']
        
        where_wo_categ = " 1=1 "
        if wo_categ :
            where_wo_categ = " wol.categ_id = '%s'" % str(wo_categ)
        where_start_date = " 1=1 "
        if start_date :
            where_start_date = " wo.date >= '%s'" % str(start_date)
        where_end_date = " 1=1 "
        if end_date :
            where_end_date = " wo.date <= '%s'" % str(end_date)
        where_state = " 1=1 "
        if state in ['open','done'] :
            where_state = " wo.state = '%s'" % str(state)
        else :
            where_state = " wo.state in ('open','done')"
        where_branch_ids = " 1=1 "
        if branch_ids :
            where_branch_ids = " wo.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        where_product_ids = " 1=1 "
        if product_ids :
            where_product_ids = " wol.product_id in %s" % str(
                tuple(product_ids)).replace(',)', ')')
        where_partner_ids = " 1=1 "
        if partner_ids :
            where_partner_ids = " wo.customer_id in %s" % str(
                tuple(partner_ids)).replace(',)', ')')
        
        query_workshop = """
            select b.code as branch_code, b.name as branch_name, wo.name as wo_name, case when wo.state = 'open' then 'Open' when wo.state = 'done' then 'Done' else wo.state end as wo_state, wo.date as wo_date, case when wo.type = 'REG' then 'Regular' when wo.type = 'WAR' then 'Job Return' when wo.type = 'CLA' then 'Claim' when wo.type = 'SLS' then 'Part Sales' else wo.type end as wo_type,
            CASE WHEN wo.type = 'KPB' THEN inv.default_code WHEN wo.type = 'CLA' THEN inv.default_code ELSE '' END as main_dealer,
            COALESCE(fp.name,'') as faktur_pajak,
            users.login as login, mechanic.name as mechanic, lot.no_polisi as nopol, customer.default_code as cust_code, customer.name as cust_name, customer.mobile as cust_mobile, unit.name_template as unit_name, lot.name as engine, lot.chassis_no as chassis, wol.categ_id as wo_categ, prod_category.name as prod_categ_name, product.name_template as prod_name, product.default_code as prod_code,
            CASE WHEN wol.categ_id = 'Sparepart' THEN wol.supply_qty ELSE wol.product_qty END as qty, wol.price_unit as het, wol.discount as discount,
            ail.force_cogs / COALESCE(NULLIF(ail.quantity,0),1) * wol.supply_qty as hpp,
            wol.price_unit * (1 - wol.discount / 100) / 1.1 * CASE WHEN wol.categ_id = 'Sparepart' THEN wol.supply_qty ELSE wol.product_qty END as dpp,
            wol.price_unit * (1 - wol.discount / 100) / 1.1 * 0.1 * CASE WHEN wol.categ_id = 'Sparepart' THEN wol.supply_qty ELSE wol.product_qty END as ppn,
            wol.price_unit * (1 - wol.discount / 100) * CASE WHEN wol.categ_id = 'Sparepart' THEN wol.supply_qty ELSE wol.product_qty END as total,
            (wol.price_unit * (1 - wol.discount / 100) / 1.1 * CASE WHEN wol.categ_id = 'Sparepart' THEN wol.supply_qty ELSE wol.product_qty END) - (ail.force_cogs / COALESCE(NULLIF(ail.quantity,0),1) * wol.supply_qty) as total_gp
            from wtc_work_order wo inner join wtc_work_order_line wol on wo.id = wol.work_order_id
            left join wtc_branch b on wo.branch_id = b.id
            left join res_users users on users.id = wo.mekanik_id
            left join res_partner mechanic on users.partner_id = mechanic.id
            left join res_partner customer on customer.id = wo.customer_id
            left join stock_production_lot lot on wo.lot_id = lot.id
            left join product_product unit on wo.product_id = unit.id
            left join product_product product on wol.product_id = product.id
            left join product_template prod_template on product.product_tmpl_id = prod_template.id
            left join product_category prod_category on prod_template.categ_id = prod_category.id
            left join account_invoice ai on ai.origin = wo.name
            left join account_invoice_line ail on ail.invoice_id = ai.id and ail.product_id = wol.product_id
            left join res_partner inv on ai.partner_id = inv.id
            left join wtc_faktur_pajak_out fp ON wo.faktur_pajak_id = fp.id
        """
        
        where = "WHERE" + where_wo_categ + " AND " + where_state + " AND " + where_start_date + " AND " + where_end_date + " AND " + where_product_ids + " AND " + where_branch_ids + " AND " + where_partner_ids
        order = "order by b.code, wo.date"
        
        self.cr.execute(query_workshop + where + order)
        all_lines = self.cr.dictfetchall()
        
        if all_lines :
            datas = map(lambda x : {
                'no': 0,
                'branch_code': str(x['branch_code'].encode('ascii','ignore').decode('ascii')) if x['branch_code'] != None else '',
                'branch_name': str(x['branch_name'].encode('ascii','ignore').decode('ascii')) if x['branch_name'] != None else '',
                'wo_name': str(x['wo_name'].encode('ascii','ignore').decode('ascii')) if x['wo_name'] != None else '',
                'wo_state': str(x['wo_state'].encode('ascii','ignore').decode('ascii')) if x['wo_state'] != None else '',
                'wo_date': str(x['wo_date'].encode('ascii','ignore').decode('ascii')) if x['wo_date'] != None else '',
                'wo_type': str(x['wo_type'].encode('ascii','ignore').decode('ascii')) if x['wo_type'] != None else '',
                'main_dealer': str(x['main_dealer'].encode('ascii','ignore').decode('ascii')) if x['main_dealer'] != None else '',
                'login': str(x['login'].encode('ascii','ignore').decode('ascii')) if x['login'] != None else '',
                'mechanic': str(x['mechanic'].encode('ascii','ignore').decode('ascii')) if x['mechanic'] != None else '',
                'nopol': str(x['nopol'].encode('ascii','ignore').decode('ascii')) if x['nopol'] != None else '',
                'cust_code': str(x['cust_code'].encode('ascii','ignore').decode('ascii')) if x['cust_code'] != None else '',
                'cust_name': x['cust_name'],
                'cust_mobile': str(x['cust_mobile'].encode('ascii','ignore').decode('ascii')) if x['cust_mobile'] != None else '',
                'unit_name': str(x['unit_name'].encode('ascii','ignore').decode('ascii')) if x['unit_name'] != None else '',
                'engine': str(x['engine'].encode('ascii','ignore').decode('ascii')) if x['engine'] != None else str(x['nopol'].encode('ascii','ignore').decode('ascii')) if x['nopol'] != None else '',
                'chassis': str(x['chassis'].encode('ascii','ignore').decode('ascii')) if x['chassis'] != None else '',
                'wo_categ': str(x['wo_categ'].encode('ascii','ignore').decode('ascii')) if x['wo_categ'] != None else '',
                'prod_categ_name': str(x['prod_categ_name'].encode('ascii','ignore').decode('ascii')) if x['prod_categ_name'] != None else '',
                'prod_name': str(x['prod_name'].encode('ascii','ignore').decode('ascii')) if x['prod_name'] != None else '',
                'prod_code': str(x['prod_code'].encode('ascii','ignore').decode('ascii')) if x['prod_code'] != None else '',
                'qty': x['qty'],
                'het': x['het'],
                'discount': x['discount'],
                'hpp': x['hpp'],
                'dpp': x['dpp'],
                'ppn': x['ppn'],
                'total': x['total'],
                'total_gp': x['total_gp'],
                'faktur_pajak': str(x['faktur_pajak'].encode('ascii','ignore').decode('ascii')) if x['faktur_pajak'] != None else '',
                }, all_lines)
            reports = filter(lambda x: datas, [{'datas': datas}])
        else :
            reports = [{'datas': [{
                'no': 'NO DATA FOUND',
                'branch_code': 'NO DATA FOUND',
                'branch_name': 'NO DATA FOUND',
                'wo_name': 'NO DATA FOUND',
                'wo_state': 'NO DATA FOUND',
                'wo_date': 'NO DATA FOUND',
                'wo_type': 'NO DATA FOUND',
                'main_dealer': 'NO DATA FOUND',
                'login': 'NO DATA FOUND',
                'mechanic': 'NO DATA FOUND',
                'nopol': 'NO DATA FOUND',
                'cust_code': 'NO DATA FOUND',
                'cust_name': 'NO DATA FOUND',
                'cust_mobile': 'NO DATA FOUND',
                'unit_name': 'NO DATA FOUND',
                'engine': 'NO DATA FOUND',
                'chassis': 'NO DATA FOUND',
                'wo_categ': 'NO DATA FOUND',
                'prod_categ_name': 'NO DATA FOUND',
                'prod_name': 'NO DATA FOUND',
                'prod_code': 'NO DATA FOUND',
                'qty': 0,
                'het': 0,
                'discount': 0,
                'hpp': 0,
                'dpp': 0,
                'ppn': 0,
                'total': 0,
                'total_gp': 0,
                }]}]
        
        self.localcontext.update({'reports': reports})
        super(wtc_report_workshop_print, self).set_context(objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else :
            return super(wtc_report_workshop_print, self).formatLang(value, digits, date, date_time, grouping, monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.wtc_report_workshop.report_workshop'
    _inherit = 'report.abstract_report'
    _template = 'wtc_report_workshop.report_workshop'
    _wrapped_report_class = wtc_report_workshop_print
    