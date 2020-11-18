from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import orm
import logging
_logger = logging.getLogger(__name__)


class wtc_report_control_df_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(wtc_report_control_df_print, self).__init__(
            cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({
            'formatLang_zero2blank': self.formatLang_zero2blank,
            })

    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context
        per_date = data['per_date']
        title_type='Control DF'
        report = {
            'type': 'receivable',
            'title': title_type ,
            'title_short': title_type,
            'per_date': per_date,

            }

        query_start = """
            select b.code as p_name
            , so.id as p_id
            , so.name as no_transaksi 
            , partner.default_code as kode_cabang 
            , partner.name  as nama_branch 
            , partner.name as partner_name 
            , ai.number as p_ref 
            , ai.date_invoice
            , ai.date_due
            , ai.amount_total
            , inv_qty.quantity as inv_qty 
            , coalesce(sj_qty.quantity,0) as sj_qty
            , pick.date_done + interval '7 hours' as pick_date
            , pick.name as pick_name 
            , pack.name as pack_name 
            , pack_line.engine_number 
            , pack_line.chassis_number 
            from sale_order so inner join 
            (select so.id as so_id, inv.id as inv_id, sum(quantity) as quantity 
            from sale_order so 
            inner join account_invoice inv on so.name = inv.origin and inv.type = 'out_invoice' 
            inner join account_invoice_line invl on inv.id = invl.invoice_id 
            where so.division = 'Unit' 
            and inv.date_invoice <= '%s' 
            group by so.id, inv.id) inv_qty on so.id = inv_qty.so_id 
            left join 
            (select so.id, so.name, max(pick.date_done) as date_done, sum(quantity) as quantity 
            from sale_order so 
            inner join stock_picking pick on so.name = pick.origin and pick.state = 'done' 
            inner join wtc_stock_packing pack on pick.id = pack.picking_id 
            inner join wtc_stock_packing_line pack_line on pack.id = pack_line.packing_id and pack_line.engine_number is not null 
            where so.division = 'Unit' 
            and pick.date_done <= to_timestamp('%s 23:59:59', 'YYYY-MM-DD HH24:MI:SS') + interval '7 hours' 
            group by so.id, so.name) sj_qty on so.id = sj_qty.id 
            inner join account_invoice ai on ai.id = inv_qty.inv_id and ai.type = 'out_invoice' 
            left join stock_picking pick on so.name = pick.origin and pick.state = 'done' 
            left join wtc_stock_packing pack on pick.id = pack.picking_id 
            left join wtc_stock_packing_line pack_line on pack.id = pack_line.packing_id and pack_line.engine_number is not null 
            left join wtc_branch b on so.branch_id = b.id 
            left join res_partner partner on so.partner_id = partner.id 
            where inv_qty.quantity > sj_qty.quantity 
            or sj_qty.quantity is null 
            or (sj_qty.date_done >= to_timestamp('%s 00:00:00', 'YYYY-MM-DD HH24:MI:SS') + interval '7 hours'
            and sj_qty.date_done <= to_timestamp('%s 23:59:59', 'YYYY-MM-DD HH24:MI:SS') + interval '7 hours') 
            order by b.code, ai.date_invoice, partner.default_code, so.name, ai.number, pick.date_done, pick.name, pack.name
            """ % (per_date, per_date, per_date, per_date)
            
        reports = [report]
        report_info = title_type

        for report in reports:
            cr.execute(query_start)
            all_lines = cr.dictfetchall()
            partners = []

            if all_lines:
                def lines_map(x):
                    x.update({'docname': x['partner_name']})
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
                        'p_name': x['p_name'].encode('ascii','ignore').decode('ascii') if x['p_name'] != None else '',   
                        'no_transaksi': x['no_transaksi'].encode('ascii','ignore').decode('ascii') if x['no_transaksi'] != None else '',
                        'kode_cabang': x['kode_cabang'].encode('ascii','ignore').decode('ascii') if x['kode_cabang'] != None else '',
                        'nama_branch': x['nama_branch'].encode('ascii','ignore').decode('ascii') if x['nama_branch'] != None else '',
                        'no_invoice': x['p_ref'].encode('ascii','ignore').decode('ascii') if x['p_ref'] != None else '',
                        'tanggal_invoice': x['date_invoice'].encode('ascii','ignore').decode('ascii') if x['date_invoice'] != None else '',
                        'date_due':x['date_due'].encode('ascii','ignore').decode('ascii') if x['date_due'] != None else '',
                        'amount_total':str(x['amount_total']),
                        'qty_invoice': str(x['inv_qty']),
                        'qty_sj': str(x['sj_qty']),
                        'tanggal_picking':  x['pick_date'].encode('ascii','ignore').decode('ascii') if x['pick_date'] != None else '', 
                        'no_picking': x['pick_name'].encode('ascii','ignore').decode('ascii') if x['pick_name'] != None else '', 
                        'no_packing': x['pack_name'].encode('ascii','ignore').decode('ascii') if x['pack_name'] != None else '',
                        'no_mesin': x['engine_number'].encode('ascii','ignore').decode('ascii') if x['engine_number'] != None else '',
                        'no_chassis': x['chassis_number'].encode('ascii','ignore').decode('ascii') if x['chassis_number'] != None else '', 
                        'p_ref': x['p_ref'].encode('ascii','ignore').decode('ascii') if x['p_ref'] != None else '',},
                    all_lines)
                for p in p_map:
                    if p['p_id'] not in map(
                            lambda x: x.get('p_id', None), partners):
                        partners.append(p)
                        partner_lines = filter(
                            lambda x: x['p_id'] == p['p_id'], all_lines)
                        p.update({'lines': partner_lines})
                report.update({'partners': partners})

                

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
        super(wtc_report_control_df_print, self).set_context(
            objects, data, ids, report_type=report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False,
                              date_time=False, grouping=True, monetary=False,
                              dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(wtc_report_control_df_print, self).formatLang(
                value, digits=digits, date=date, date_time=date_time,
                grouping=grouping, monetary=monetary, dp=dp,
                currency_obj=currency_obj)


class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.wtc_report_control_df_xls.report_control_df'
    _inherit = 'report.abstract_report'
    _template = 'wtc_report_surat_jalan_xls.report_control_df'
    _wrapped_report_class = wtc_report_control_df_print
