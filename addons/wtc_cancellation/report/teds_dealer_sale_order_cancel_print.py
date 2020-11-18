import time
from datetime import datetime, timedelta,date
from openerp.report import report_sxw
from openerp import models, fields, api
from openerp.osv import osv

class DealerSaleOrderCancel(models.Model):
    _inherit = "dealer.sales.order.cancel"
    
    @api.multi
    def action_print_form(self):
        active_ids = self.env.context.get('active_ids', [])
        user = self.env['res.users'].browse(self._uid).name
        no_mesin = ""
        if len(self.dealer_sales_order_id.dealer_sale_order_line) > 1:
            for line  in self.dealer_sales_order_id.dealer_sale_order_line:
                no_mesin += line.lot_id.name
                no_mesin += ", "
        else:
            for line  in self.dealer_sales_order_id.dealer_sale_order_line:
                no_mesin += line.lot_id.name
        tgl = datetime.strptime(self.date,'%Y-%m-%d')

        datas = {
            'ids': active_ids,
            'today':str(datetime.now()),
            'user': user,
            'branch_id': '['+str(self.branch_id.code)+'] '+str(self.branch_id.name),
            'division': str(self.division),
            'date':datetime.strftime(tgl,'%d %B %Y'),
            'dso':str(self.dealer_sales_order_id.name),
            'partner':str(self.dealer_sales_order_id.partner_id.display_name),
            'reason':str(self.reason) if self.reason else '',
            'no_mesin':no_mesin,
        }
        return self.env['report'].get_action(self,'wtc_cancellation.teds_dso_cancel_print_pdf', data=datas)


class DSOPrintData(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(DSOPrintData, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'data': self._get_data,
        })

    def _get_data(self,data):
        return data



class DSOPrint(osv.AbstractModel):
    _name = 'report.wtc_cancellation.teds_dso_cancel_print_pdf'
    _inherit = 'report.abstract_report'
    _template = 'wtc_cancellation.teds_dso_cancel_print_pdf'
    _wrapped_report_class = DSOPrintData


