import string
from openerp.osv import osv, fields

class wtc_product_product(osv.osv):
    _inherit = 'product.product'
    
    def get_location_ids(self,cr,uid,ids,context=None):
        quants_ids = self.pool.get('stock.quant').search(cr,uid,['&',('product_id','in',ids),('qty','>',0.0),('reservation_id','=',False)])
        loc_ids = self.pool.get('stock.quant').read(cr, uid, quants_ids, ['location_id'])
        return [x['location_id'][0] for x in loc_ids]
    
    _defaults = {
             'lst_price': 0
    }
    
    def _get_account_id(self, cr, uid, ids, product_id,context=None):
             obj_account = self.pool.get('product.product').browse(cr,uid,product_id)
             if obj_account:
                account_line= obj_account.property_account_income.id
                if not account_line :
                 account_line= obj_account .categ_id.property_account_income_categ.id
                 if not account_line :
                     account_line= obj_account.categ_id.parent_id.property_account_income_categ.id
                return account_line
    
class wtc_product_attribute_value(osv.osv):
    _inherit = 'product.attribute.value'
    _columns = {
            'code': fields.char('Code'),
            }
    
class wtc_barang_extras(osv.osv):
    _name = 'wtc.barang.extras'
    _columns = {
                'barang_extras_id':fields.many2one('product.template', 'Barang Extras'),
                'product_id':fields.many2one('product.product', 'Product', domain=[('categ_id','child_of','Extras')], required=True),
                'quantity':fields.float('Quantity', required=True)
                }
    
    def product_change(self, cr, uid, ids, product, categ_id):
        value = {}
        value['quantity'] = 1
        root_name = self.pool.get('product.category').get_root_name(cr, uid, categ_id)
        if root_name <> "Unit" :
            raise osv.except_osv(('Perhatian !'), ("Tidak bisa menambahkan Extras, Category bukan Unit"))
        return {'value': value}
    
class wtc_product_template(osv.osv):
    _inherit = 'product.template'
    _columns = {
                'kd_mesin':fields.char('Kode Mesin'),
                'extras_line': fields.one2many('wtc.barang.extras', 'barang_extras_id', 'Barang Extras'),
                'category_product_id':fields.many2one('wtc.category.product', 'Category Service'),
                'series':fields.char('Series'),
                }
    
    _sql_constraints = [
                        ('unique_name', 'unique(name)', 'Ditemukan nama produk duplicate, silahkan cek kembali !'),
                        ]
    
    def kd_mesin_change(self, cr, uid, ids, kd_mesin, context=None):
        value = {}
        warning = {}
        if kd_mesin:
            kd_mesin = kd_mesin.replace(' ','')
            kd_mesin = kd_mesin.upper()
            value['kd_mesin'] = kd_mesin
            pjg = len(kd_mesin)
            for x in range(pjg):
                if kd_mesin[x] in string.punctuation:
                    value['kd_mesin'] = False
                    warning = {
                               'title': 'Perhatian !',
                               'message': 'Kode mesin hanya boleh huruf dan angka !'
                               }
                    return {'warning':warning, 'value':value}
            if pjg > 5 :
                value['kd_mesin'] = kd_mesin[:5]
                warning = {
                           'title': 'Perhatian !',
                           'message': 'Kode mesin maksimal 5 karakter !'
                           }
        return {'warning':warning, 'value':value}
    
    _defaults = {
             'list_price': 0
    }
    
class wtc_product_category(osv.osv):
    _inherit = 'product.category'
    
    def _get_child_ids(self, cr, uid, categ_id):
        res=[]
        child_ids = self.pool.get('product.category').search(cr, uid, [('parent_id','=',categ_id)])
        if child_ids :
            res += child_ids
            for child in child_ids :
                grand_child = self._get_child_ids(cr,uid,child)
                if grand_child :
                    res += grand_child
        return res
    
    def get_child_ids(self, cr, uid, ids, parent_categ_name):
        tampung=[]
        obj_pc = self.pool.get('product.category')
        obj_pc_ids = obj_pc.search(cr, uid, [('name','=',parent_categ_name)])
        tampung += obj_pc_ids
        for obj_pc_id in obj_pc_ids :
            tampung += self._get_child_ids(cr,uid,obj_pc_id)
        return tampung
    
    def get_child_by_ids(self, cr, uid, ids):
        tampung=[]
        if isinstance(ids, (int, long)) :
            ids = [ids]
        obj_pc = self.pool.get('product.category')
        obj_pc_ids = obj_pc.search(cr, uid, [('id','in',ids)])
        tampung += obj_pc_ids
        for obj_pc_id in obj_pc_ids :
            tampung += self._get_child_ids(cr,uid,obj_pc_id)
        return tampung

    def get_root_name(self, cr, uid, ids):
        root_name = ""
        if isinstance(ids, (int, long)):
            ids = [ids]
        for obj_pc in self.browse(cr, uid, ids):
            while (obj_pc.parent_id):
                obj_pc = obj_pc.parent_id
            if root_name == "":
                root_name = obj_pc.name
            elif root_name != obj_pc.name :
                #root name dari list objects tidak sama
                return False
        return root_name
    
    def isParentName(self,cr,uid,ids,parent_name):
        if len(ids)>1:
            return False
        pc_obj=self.pool.get('product.category').browse(cr,uid,ids)
        while (pc_obj.name != parent_name):
            if pc_obj.parent_id:
                pc_obj = pc_obj.parent_id
            else:
                return False
        return True
    