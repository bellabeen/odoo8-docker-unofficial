from openerp import models, fields, api
from datetime import date, datetime, timedelta,time
from dateutil.relativedelta import relativedelta
from openerp.exceptions import Warning

class Branch(models.Model):
    _inherit = "wtc.branch"

    adh_id = fields.Many2one('hr.employee','ADH',domain="[('branch_id','=',id),('tgl_keluar','=',False)]")
    admin_pos_id = fields.Many2one('hr.employee','Admin POS',domain="[('branch_id','=',id),('tgl_keluar','=',False)]")
    kasir_id = fields.Many2one('hr.employee','Kasir',domain="[('branch_id','=',id),('tgl_keluar','=',False)]")
    plafon_petty_cash_sr = fields.Float('Plafon Petty Cash SR')
    plafon_petty_cash_ws = fields.Float('Plafon Petty Cash WS')
    plafon_petty_cash_atl_btl = fields.Float('Plafon Petty Cash ATL/BTL')