import time
from datetime import datetime, timedelta,date
from openerp.report import report_sxw
from openerp import models, fields, api
from openerp.osv import osv

class PenyerahanBPKBCancel(models.Model):
    _inherit = "wtc.cancel.penyerahan.bpkb"
    
    @api.multi
    def action_print_form(self):
        active_ids = self.env.context.get('active_ids', [])
        user = self.env['res.users'].browse(self._uid).name
        no_mesin = ""
        if len(self.penyerahan_bpkb_id.penyerahan_line) > 1:
            for line in self.penyerahan_bpkb_id.penyerahan_line:
                no_mesin += line.name.name
                no_mesin += ", "
        else:
            for line  in self.penyerahan_bpkb_id.penyerahan_line:
                no_mesin += line.name.name
        tgl = datetime.strptime(self.date,'%Y-%m-%d')

        datas = {
            'ids': active_ids,
            'today':str(datetime.now()),
            'user': user,
            'branch_id': '['+str(self.branch_id.code)+'] '+str(self.branch_id.name),
            'date':datetime.strftime(tgl,'%d %B %Y'),
            'penyerahan':str(self.penyerahan_bpkb_id.name),
            'reason':str(self.reason) if self.reason else '',
            'no_mesin':no_mesin,
        }
        return self.env['report'].get_action(self,'wtc_penyerahan_stnk.teds_penyerahan_bpkb_cancel_print_pdf', data=datas)


class PenyerahanBPKBPrintData(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(PenyerahanBPKBPrintData, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'data': self._get_data,
        })

    def _get_data(self,data):
        return data



class PenyerahanBPKBPrint(osv.AbstractModel):
    _name = 'report.wtc_penyerahan_stnk.teds_penyerahan_bpkb_cancel_print_pdf'
    _inherit = 'report.abstract_report'
    _template = 'wtc_penyerahan_stnk.teds_penyerahan_bpkb_cancel_print_pdf'
    _wrapped_report_class = PenyerahanBPKBPrintData


