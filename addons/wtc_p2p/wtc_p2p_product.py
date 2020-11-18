import time
from datetime import datetime
from openerp import models, fields, api
from openerp.osv import osv, expression
from openerp.tools.translate import _
from openerp import SUPERUSER_ID
import re

class wtc_p2p_product(models.Model):
    _name = "wtc.p2p.product"
    _description ="P2P Product"

    @api.one
    @api.depends('product_id')
    def _get_division(self):
        if self.product_id :
            categ_id = self.categ_id
            division = False
            div = False
            while not div :
                if division == 'Unit' or division == 'Sparepart' or division == 'Umum' or division == 'Extras':
                    div = division
                    break
                categ_id = categ_id.parent_id
                division = categ_id.name
            self.division = div
                    
    name = fields.Char(related='product_id.name',string='Name')
    product_id = fields.Many2one('product.product', string='Product')
    categ_id = fields.Many2one(related='product_id.categ_id', string='Categori')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    division = fields.Char(string="Division",store=True, readonly=True, compute='_get_division',)
    default_code = fields.Char(related='product_id.default_code',string="Default Code")
    attribute_value_ids = fields.Many2many(related='product_id.attribute_value_ids')
    
    
    _sql_constraints = [
    ('unique_branch_id', 'unique(product_id)', 'Master data sudah pernah dibuat !'),
    ]  
    
    @api.onchange('start_date','end_date')
    def onchange_date(self):
        warning = {}
        if self.start_date and self.end_date :
            if self.end_date < self.start_date :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('End Date tidak boleh kurang dari Start Date ! ')),
                } 
                self.end_date = False                  
        return {'warning':warning}