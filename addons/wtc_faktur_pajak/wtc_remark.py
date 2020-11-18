import itertools
from datetime import datetime, timedelta
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp.osv import osv

class wtc_remark(models.Model):
    _name = 'wtc.remark'
    _description = 'remark Report'
    _rec_name = 'remark'
    
    model_id = fields.Many2one('ir.model',string="Form Name",domain="[('model','in',('wtc.disposal.asset','wtc.faktur.pajak.gabungan','wtc.account.voucher','wtc.work.order','dealer.sale.order'))]")
    remark = fields.Char(string="Remark")

    _sql_constraints = [
    ('unique_model_id', 'unique(model_id)', 'Data master tidak boleh duplicate !'),
    ]
    
    