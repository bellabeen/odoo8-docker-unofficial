from openerp import models, fields, api

class WorkOrder(models.Model):
    _inherit = "wtc.work.order"

    md_reference_pkb = fields.Char('MD Refrence PKB',index=True,help="ID PKB Main Dealer")
    md_reference_sa = fields.Char('MD Refrence SA',index=True,help="ID SA Main Dealer")
    note_log = fields.Text('Note Log')