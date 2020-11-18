from openerp import models, fields, api

class ProductTemplate(models.Model):
	_inherit = "product.template"

	kode_tipe_unit = fields.Char('Kode Tipe Unit',index=True)