from openerp import models, fields, api

class ProductTemplate(models.Model):
    _inherit = "product.template"

    active = fields.Boolean(default=False)

class ProductProduct(models.Model):
    _inherit = "product.product"

    active = fields.Boolean(default=False)