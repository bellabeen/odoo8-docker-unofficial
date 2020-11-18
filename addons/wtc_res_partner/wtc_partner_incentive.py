from openerp.osv import fields, osv

class wtc_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
        'incentive_finco_ids': fields.one2many('wtc.incentive.finco.line','partner_id',required=True,string='Subsidi'),
    }
