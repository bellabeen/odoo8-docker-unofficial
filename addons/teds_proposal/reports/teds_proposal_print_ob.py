# import time
from datetime import datetime, timedelta,date
# from openerp.report import report_sxw
from openerp import models, fields, api
# from openerp.osv import osv

class PrintOverBudget(models.AbstractModel):
    _name = 'report.teds_proposal.print_overbudget_pdf'

    @api.model
    def render_html(self, docids, data=None):
        docs = self.env[self.env.context.get('active_model')].browse(self.env.context.get('active_ids', []))
        # print "docs >>>>> ", docs
        docargs = {
            'docs': docs, # objek teds.proposal(current_id)
            'data': data['form'], # data lengkap pada form aktif
            'user': data['user'], # nama user
            'unit_bisnis': 'PT TUNAS DWIPA MATRA MAIN DEALER'
        }
        return self.env['report'].render('teds_proposal.print_overbudget_pdf', docargs)

# class Proposal(models.Model):
#     _inherit = "teds.proposal"

#     @api.multi
#     def action_print_ob(self):
#         active_ids = self.env.context.get('active_ids', [])
#         user = self.env['res.users'].browse(self._uid).name

#         datas = {
#             'ids': active_ids,
#             'today':str(datetime.now()),
#             'user': user,
#             # 'branch_id': '['+str(self.branch_id.code)+'] '+str(self.branch_id.name),
#             # 'no_proposal': str(self.name),
#             'unit_bisnis': 'PT TUNAS DWIPA MATRA',
#             'division': str(self.division).upper(),
#             'dept_name': str(self.department_id.name).upper(),
#         }
#         return self.env['report'].get_action(self,'teds_proposal.teds_proposal_print_ob_pdf', data=datas)

# class ProposalObPrintData(report_sxw.rml_parse):
#     def __init__(self, cr, uid, name, context):
#         super(ProposalObPrintData, self).__init__(cr, uid, name, context=context)
#         self.localcontext.update({
#             'data': self._get_data,
#         })

#     def _get_data(self,data):
#         return data

# class ProposalObPrint(osv.AbstractModel):
#     _name = 'report.teds_proposal.teds_proposal_print_ob_pdf'
#     _inherit = 'report.abstract_report'
#     _template = 'teds_proposal.teds_proposal_print_ob_pdf'
#     _wrapped_report_class = ProposalObPrintData


