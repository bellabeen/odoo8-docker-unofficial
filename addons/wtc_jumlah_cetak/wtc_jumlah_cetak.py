from datetime import datetime, timedelta
from openerp import models, fields, api, _


class wtc_jumlah_cetak(models.Model):
    _name ="wtc.jumlah.cetak"
    _description="Jumlah Cetak"
    
    report_id = fields.Many2one('ir.actions.report.xml',string='Report')
    transaction_id = fields.Integer(string='Transaction Id')
    model_id = fields.Many2one('ir.model','Model')
    jumlah_cetak = fields.Integer(string='Jumlah Cetak')
    