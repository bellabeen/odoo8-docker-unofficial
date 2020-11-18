from openerp import models, fields, api

class B2bApiConfig(models.Model):
    _inherit = "teds.b2b.api.config"
    
    corporate_id = fields.Char('Corporate ID')