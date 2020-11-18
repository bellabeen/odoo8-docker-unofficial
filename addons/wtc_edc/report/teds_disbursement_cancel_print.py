import time
from datetime import datetime, timedelta,date
from openerp.report import report_sxw
from openerp import models, fields, api
from openerp.osv import osv

class DisbursementCancel(models.Model):
    _inherit = "wtc.cancel.disbursement"
    
    @api.multi
    def action_print_form(self):
        active_ids = self.env.context.get('active_ids', [])
        user = self.env['res.users'].browse(self._uid).name
        tgl = datetime.strptime(self.date,'%Y-%m-%d')

        datas = {
            'ids': active_ids,
            'today':str(datetime.now()),
            'user': user,
            'branch_id': '['+str(self.branch_id.code)+'] '+str(self.branch_id.name),
            'division': str(self.division),
            'date':datetime.strftime(tgl,'%d %B %Y'),
            'disbursement':str(self.disbursement_id.name),
            'reason':str(self.reason) if self.reason else '',
        }
        return self.env['report'].get_action(self,'wtc_edc.teds_disbursement_cancel_print_pdf', data=datas)


class DisbursementPrintData(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(DisbursementPrintData, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'data': self._get_data,
        })

    def _get_data(self,data):
        return data



class DisbursementPrint(osv.AbstractModel):
    _name = 'report.wtc_edc.teds_disbursement_cancel_print_pdf'
    _inherit = 'report.abstract_report'
    _template = 'wtc_edc.teds_disbursement_cancel_print_pdf'
    _wrapped_report_class = DisbursementPrintData


