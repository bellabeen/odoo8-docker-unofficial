from openerp import models, fields, api

class B2bApiURL(models.Model):
    _inherit = "teds.b2b.api.url"

    type = fields.Selection(selection_add=[
        ('utilities_signature','Utilities Signature'),
        ('corporates','Corporates')])
    