from openerp import models, fields, api
from openerp.exceptions import Warning
import time
from openerp.osv import osv
from openerp.report import report_sxw

class DisposalAssetPrintFormData(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(DisposalAssetPrintFormData, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'data': self._get_data,
            'no_urut':self.no_urut,
        })

        self.no = 0
    def no_urut(self):
        self.no+=1
        return self.no
    def _get_data(self,data):
        return data

class DisposalAssetPrintForm(osv.AbstractModel):
    _name = 'report.wtc_purchase_asset.teds_disposal_asset_print_form_pdf'
    _inherit = 'report.abstract_report'
    _template = 'wtc_purchase_asset.teds_disposal_asset_print_form_pdf'
    _wrapped_report_class = DisposalAssetPrintFormData