from openerp import models, fields, api
from datetime import date, datetime, timedelta,time

class ProsesBirojasaLine(models.Model):
    _inherit = "wtc.proses.birojasa.line"

    @api.one
    @api.depends('pajak_progressive')
    def _compute_pp(self):
        self.pajak_progressive_show = self.pajak_progressive

    pajak_progressive_show = fields.Float('Pajak Progresif',compute="_compute_pp")
                

    @api.onchange('pajak_progressive')
    def onchange_pajak_progressive_show(self):
        if self.pajak_progressive:
            self.pajak_progressive_show = self.pajak_progressive