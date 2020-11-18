import time
from datetime import datetime, timedelta,date
from openerp.report import report_sxw
from openerp import models, fields, api

class ProsesBirojasa(models.Model):
    _inherit = "wtc.proses.birojasa"

    tgl_terima_document_ho = fields.Datetime('Tgl Terima Doc HO')
    tgl_terima_document_pajak = fields.Datetime('Tgl Terima Doc Pajak')
    tgl_terima_document_finance = fields.Datetime('Tgl Terima Doc Finance')

    @api.multi
    def action_confirm_document_ho(self):
        self.tgl_terima_document_ho = self._get_default_date()
    
    @api.multi
    def action_confirm_document_pajak(self):
        self.tgl_terima_document_pajak = self._get_default_date()
    
    @api.multi
    def action_confirm_document_finance(self):
        self.tgl_terima_document_finance = self._get_default_date()
