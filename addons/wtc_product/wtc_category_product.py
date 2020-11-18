from openerp import models, fields, api, _, SUPERUSER_ID
import time
from datetime import datetime
from openerp.osv import osv
import string


class wtc_category_product(models.Model):
    _name = 'wtc.category.product'
    _description='Category Service'
    
    name=fields.Char(string="Category Product", required=True)
    
    _sql_constraints = [
    ('unique_name', 'unique(name)', 'Master data sudah pernah dibuat !'),
    ] 
    
    @api.onchange('name')
    def change_name(self):
        if self.name :
            self.name = self.name.replace(" ", "")
            self.name = self.name.upper()
            
class wtc_category_product_service(models.Model):
    _name = 'wtc.category.product.service'
    _description = 'Category Product Service'
    _rec_name = 'category_product_id'
    
    category_product_id = fields.Many2one('wtc.category.product', 'Category Service')
    product_id = fields.Many2one('product.product', 'Product')
    price=fields.Float(string="Price")
    
    _sql_constraints = [
                        ('unique_category_service_product', 'unique(category_product_id,product_id)', 'Master data sudah pernah dibuat !'),
                        ]
    