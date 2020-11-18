from openerp import models, fields, api

class B2bDgiMappingMasterJasa(models.Model):
    _name = "teds.b2b.dgi.mapping.master.jasa"

    def _domain_product_jasa(self):
        categ_ids = self.env['product.category'].get_child_ids('Service')
        return [('categ_id','in',categ_ids)]

    md_id = fields.Many2one('res.partner','Main Dealer',domain=[('principle','=',True),('supplier','=',True)])
    branch_id = fields.Many2one('wtc.branch','Branch')
    product_id = fields.Many2one('product.product','Product Jasa',domain=_domain_product_jasa)
    value = fields.Char('Kode Product MD')
    sequence = fields.Integer('Seguence',default=5)


    _sql_constraints = [('unique_md_branch_product_value', 'unique(md_id,branch_id,product_id,value)', 'Data tidak boleh duplikat !')]