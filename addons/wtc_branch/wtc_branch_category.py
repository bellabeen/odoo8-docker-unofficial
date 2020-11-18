from openerp.osv import fields, osv


class wtc_workshop_category(osv.osv):
    _name = "wtc.workshop.category"
    _description = "Workshop Category"
    _columns = {
        'name': fields.char('Category', 128, required=True),
    }

class wtc_branch_category(osv.osv):
    _inherit = 'wtc.branch'
    _columns = {
                'workshop_category':fields.many2one('wtc.workshop.category', 'Category'),
                }
    
class stock_picking_type(osv.osv):
    _inherit = 'stock.picking.type'
    
    def _register_hook(self, cr):
        selection = self._columns['code'].selection
        if ('interbranch_in','Interbranch Receipts') not in selection :        
            self._columns['code'].selection.append(
                ('interbranch_in','Interbranch Receipts'))
        if ('interbranch_out','Interbranch Deliveries') not in selection :
            self._columns['code'].selection.append(
                ('interbranch_out','Interbranch Deliveries'))                    
        return super(stock_picking_type, self)._register_hook(cr)
    
#     def _get_default_branch(self,cr,uid,ids,context=None):
#         user_obj = self.pool.get('res.users')        
#         user_browse = user_obj.browse(cr,uid,uid)
#         branch_ids = False
#         branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
#         return branch_ids    
    
    _columns = {
                'branch_id': fields.many2one('wtc.branch', string='Branch', required=True),
                }
#     _defaults = {
#         'branch_id': _get_default_branch,
#     }
   