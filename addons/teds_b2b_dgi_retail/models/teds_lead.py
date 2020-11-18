from openerp import models, fields, api

class Lead(models.Model):
    _inherit = "teds.lead"

    md_reference_prospect = fields.Char('MD Refrence Prospect',index=True,help="ID Prospect Main Dealer")
    md_reference_spk = fields.Char('MD Refrence SPK',index=True,help="ID SPK Main Dealer")
    note_log = fields.Text('Note Log')