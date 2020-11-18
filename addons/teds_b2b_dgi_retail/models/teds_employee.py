from openerp import models, fields, api

class Employee(models.Model):
    _inherit = "hr.employee"

    code_md = fields.Char('ID Main Dealer',index=True,help="ID Sales People Main Dealer")