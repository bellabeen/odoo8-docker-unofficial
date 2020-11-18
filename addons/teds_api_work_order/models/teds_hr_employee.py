from openerp import models, fields, api

class Employee(models.Model):
    _inherit = "hr.employee"


    code_honda = fields.Char('Honda ID')
    code_ahm = fields.Char('AHM ID')