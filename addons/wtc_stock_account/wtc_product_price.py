from openerp.osv import osv, fields

class wtc_product_price_branch(osv.osv):
    _name = 'product.price.branch'
    _rec_name = 'product_id'

    _columns = {
        'cost': fields.float('Cost'),
        'product_id': fields.many2one('product.product','Product', required=True),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', required=True)
    }

    def create(self, cr, uid, vals, context=None):
        super(wtc_product_price_branch, self).create(cr, uid, vals, context=context)
        hist_price = self.pool.get('product.price.history.branch').create(cr, uid, {
            'warehouse_id': vals.get('warehouse_id'),
            'product_id': vals.get('product_id'),
            'cost': vals.get('cost')
        })

    def write(self, cr, uid, ids, vals, context=None):
        super(wtc_product_price_branch, self).write(cr, uid, ids, vals, context=context)
        if vals.get('cost'):
            product_price = self.browse(cr, uid, ids)
            hist_price = self.pool.get('product.price.history.branch').create(cr, uid, {
                'warehouse_id': product_price.warehouse_id.id,
                'product_id': product_price.product_id.id,
                'cost': vals.get('cost')
            })
    
    def _get_price(self, cr, uid, warehouse_id, product_id):
        cost = 0.0
        price_id = self.search(cr, uid, [('warehouse_id','=', warehouse_id), ('product_id','=', product_id)])
        if price_id:
            price_obj = self.browse(cr, uid, price_id[0])
            if price_obj:
                cost = price_obj.cost
        return cost

class wtc_product_price_history_branch(osv.osv):
    """
    Keep track of the ``product.template`` standard prices as they are changed.
    """

    _name = 'product.price.history.branch'
    _rec_name = 'datetime'
    _order = 'warehouse_id asc,datetime desc'

    def _get_default_company(self, cr, uid, context=None):
        if 'force_company' in context:
            return context['force_company']
        else:
            company = self.pool['res.users'].browse(cr, uid, uid, context=context).company_id
            return company.id if company else False

    def _get_default_branch(self, cr, uid, context=None):
        user_browse = self.pool['res.users'].browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 

    _columns = {
        'company_id': fields.many2one('res.company', required=True),
        'warehouse_id': fields.many2one('stock.warehouse', required=True),
        'product_id' : fields.many2one('product.product', 'Product', required=True),
        'datetime': fields.datetime('Historization Time'),
        'cost': fields.float('Historized Cost'),
    }

    _defaults = {
        'datetime': fields.datetime.now,
        'company_id': _get_default_company,
    }
