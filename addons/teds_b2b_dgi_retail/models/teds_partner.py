from openerp import models, fields, api

class Partner(models.Model):
    _inherit = "res.partner"

    md_refrence_id = fields.Char('ID Refrence MD',index=True,help="ID Customer Main Dealer")
    
    