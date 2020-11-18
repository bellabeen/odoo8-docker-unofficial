from openerp import models, fields, api

class inherit_wtc_branch(models.Model):
    _inherit = "wtc.branch"

    pricelist_config_ids = fields.One2many('pricelist.config.cabang','branch_id',string="Pricelist")
    
    
class pricelist_config_cabang(models.Model):
    _name = "pricelist.config.cabang"


    branch_id = fields.Many2one('wtc.branch','Branch')
    partner_id = fields.Many2one('res.partner','Partner')
    md_pricelist_id = fields.Many2one('product.pricelist','Pricelist')
    division = fields.Selection([('Unit','Unit'),('Sparepart','Sparepart')],string="Division")

    _sql_constraints = [('partner_id_branch_id_unique', 'unique(partner_id,branch_id)', 'Data partner tidak boleh duplicat.')]

