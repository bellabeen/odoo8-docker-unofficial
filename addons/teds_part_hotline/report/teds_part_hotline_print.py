import time
from datetime import datetime, timedelta,date
from openerp.report import report_sxw
from openerp import models, fields, api
from openerp.osv import osv

class PartHotlint(models.Model):
    _inherit = "teds.part.hotline"

    @api.multi
    def action_print_form(self):
        active_ids = self.env.context.get('active_ids', [])
        user = self.env['res.users'].browse(self._uid).name
        tgl = datetime.strptime(self.date,'%Y-%m-%d')
        dp_ids = []
        detail = []
        if len(self.alokasi_dp_ids) > 0:
            for dp in self.alokasi_dp_ids:
                dp_ids.append({
                    'name': dp.hl_id.ref,
                    'amount': dp.amount_hl_allocation
                })
        for line in self.part_detail_ids:
            detail.append({
                'product':line.product_id.name_get().pop()[1],
                'qty': line.qty,
                'price': line.price,
                'tax': line.tax_id.name,
                'subtotal': line.subtotal    
            })

        datas = {
            'ids': active_ids,
            'today':str(datetime.now()),
            'user': user,
            'branch_id': '['+str(self.branch_id.code)+'] '+str(self.branch_id.name),
            'date':datetime.strftime(tgl,'%d %B %Y'),
            'no_hotline': str(self.name),
            'customer': str(self.customer_id.display_name),
            'mobile': str(self.no_telp),
            'no_mesin': str(self.lot_id.name),
            'dp_ids': dp_ids,
            'detail': detail,
            'amount_untaxed':self.amount_untaxed,
            'amount_tax':self.amount_tax,
            'amount_total':self.amount_total,

        }
        return self.env['report'].get_action(self,'teds_part_hotline.teds_part_hotline_print_pdf', data=datas)


class PartHotlinePrintData(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(PartHotlinePrintData, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'data': self._get_data,
        })

    def _get_data(self,data):
        return data

class PartHotlinePrint(osv.AbstractModel):
    _name = 'report.teds_part_hotline.teds_part_hotline_print_pdf'
    _inherit = 'report.abstract_report'
    _template = 'teds_part_hotline.teds_part_hotline_print_pdf'
    _wrapped_report_class = PartHotlinePrintData


