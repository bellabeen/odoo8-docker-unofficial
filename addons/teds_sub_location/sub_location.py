import itertools
from openerp.osv import fields, osv
from lxml import etree
from datetime import datetime, timedelta
from openerp.exceptions import except_orm, Warning, RedirectWarning
import openerp.addons.decimal_precision as dp

import time

class teds_sub_location(osv.osv):
    _name = 'teds.sub.location'

    def to_upper_name(self,cr,uid,ids,name,context=None):
        value = {}
        if name:
            x = name.upper()
            value['name'] = x
        return {'value':value}


    _columns = {

        'name': fields.char('Sub Location Name', 18, required=True),
        'branch_id': fields.many2one('wtc.branch','Branch',required=True, ondelete='set null'),
        'product_id' : fields.many2one('product.product','Product', required=True),
        'priority': fields.integer('Priority', required=True),
        # 'pricelist_ids' = fields.many2many('wtc.pricelist','wtc_produck_pricelist_sub_rel','sub_loc_id','pricelist_id','Pricelist')
           
    }



    _sql_constraints = [
       

        ('unique_satu', 'unique(name, branch_id, product_id, priority )','Ditemukan LOcation, Branch, Product, Priority duplicate !'),
        ('unique_dua', 'unique(branch_id, product_id, priority )','Ditemukan Branch, Product, Priority duplicate'),
        ]


    def print_dua(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = self.read(cr, uid, ids,context=context)[0]
        
        return self.pool['report'].get_action(cr, uid, [], 'teds_sub_location.report_location', data=data, context=context)

