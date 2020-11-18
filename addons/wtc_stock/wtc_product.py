from openerp.osv import osv

class wtc_product_product(osv.osv):
    _inherit = "product.product"

    def _get_domain_locations(self, cr, uid, ids, context=None):
    	domain_quant, domain_move_in, domain_move_out = super(wtc_product_product,self)._get_domain_locations(cr, uid, ids, context)
        return (
            domain_quant + [('consolidated_date', '!=', False)],
            domain_move_in,
            domain_move_out
        )
