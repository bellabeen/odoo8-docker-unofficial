import time
from datetime import datetime, timedelta,date
from openerp.report import report_sxw
from openerp import models, fields, api
from openerp.osv import osv

class BankTransferCancel(models.Model):
    _inherit = "wtc.cancel.bank.transfer"
    
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
            'bt':str(self.bank_transfer_id.name),
            'reason':str(self.reason),
        }
        return self.env['report'].get_action(self,'wtc_bank_transfer.teds_bank_transfer_cancel_print_pdf', data=datas)


class BankTransferCancelPrintData(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(BankTransferCancelPrintData, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'data': self._get_data,
        })

    def _get_data(self,data):
        return data


class BankTransferCancelPrint(osv.AbstractModel):
    _name = 'report.wtc_bank_transfer.teds_bank_transfer_cancel_print_pdf'
    _inherit = 'report.abstract_report'
    _template = 'wtc_bank_transfer.teds_bank_transfer_cancel_print_pdf'
    _wrapped_report_class = BankTransferCancelPrintData


