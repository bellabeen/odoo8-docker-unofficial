from openerp import api, fields, models, SUPERUSER_ID
from openerp.osv import osv
from datetime import datetime, timedelta
import time
import pytz
from pytz import timezone

class wtc_branch (models.Model):
    _name = 'wtc.branch'
    _description = 'Branches'
    
    @api.onchange('state_id')
    def _onchange_province(self):
        self.city_id = False
        return {'domain' : {'city_id':[('state_id','=',self.state_id.id)],},}

    @api.onchange('city_id')    
    def _onchange_city(self):
        self.kecamatan_id = False
        return {'domain' : {'kecamatan_id':[('city_id','=',self.city_id.id)],},}

    @api.onchange('kecamatan_id')            
    def _onchange_kecamatan(self):
        self.zip_code_id = False
        self.kecamatan = self.kecamatan_id.name
        return {'domain' : {'zip_code_id':[('kecamatan_id','=',self.kecamatan_id.id)],},}

    @api.onchange('zip_code_id')    
    def _onchange_zip(self):
        self.kelurahan = self.zip_code_id.name
    
    code = fields.Char(string='Code',required=True)
    name = fields.Char(string='Name',required=True)
    company_id = fields.Many2one('res.company',string='Company',default=lambda self: self.env['res.company']._company_default_get('wtc.branch'))
    doc_code = fields.Char(string='Doc Code',required=True)
    branch_type = fields.Selection([('HO','Head Office'),('MD','Main Dealer'),('DL','Dealer')],string='Branch Type',required=True)
    ahm_code = fields.Char(string='AHM Code',required=True)
    default_supplier_id = fields.Many2one('res.partner',string='Principle',domain=[('principle','=',True)])
    street = fields.Char(string='Address')
    street2 = fields.Char()
    rt = fields.Char(string='RT',size=3)
    rw = fields.Char(string='RW',size=3)
    zip_code_id = fields.Many2one('wtc.kelurahan',string='ZIP Code')
    kelurahan = fields.Char(string='Kelurahan',size=100)
    kecamatan_id = fields.Many2one('wtc.kecamatan',string='Kecamatan')
    kecamatan = fields.Char(string='Kecamatan',size=100)
    city_id = fields.Many2one('wtc.city',string='City')
    state_id = fields.Many2one('res.country.state',string='Province')
    phone = fields.Char(string='Phone')
    mobile = fields.Char(string='Mobile')
    fax = fields.Char(string='Fax')
    email = fields.Char(string='e-mail')
    npwp = fields.Char(string='No NPWP')
    no_pkp = fields.Char(string='No PKP')
    tgl_kukuh = fields.Date(string='Tgl Kukuh')
    pimpinan_id = fields.Many2one('hr.employee',string='Pimpinan')
    manager_id = fields.Many2one('hr.employee',string='AM')
    general_manager_id = fields.Many2one('hr.employee',string='GM')
    warehouse_id = fields.Many2one('stock.warehouse',string='Warehouse')
    property_account_payable_id = fields.Many2one('account.account',string='Payable Account')
    property_account_receivable_id = fields.Many2one('account.account',string='Receivable Account')
    property_account_payable_analytic_id = fields.Many2one('account.analytic.account',string='Payable Analytic Account')
    property_account_receivable_analytic_id = fields.Many2one('account.analytic.account',string='Receivable Analytic Account')

    pricelist_unit_sales_id = fields.Many2one('product.pricelist',string='Price List Jual Unit',domain=[('type','=','sale')])
    pricelist_unit_purchase_id = fields.Many2one('product.pricelist',string='Price List Beli Unit',domain=[('type','=','purchase')])
    pricelist_bbn_hitam_id = fields.Many2one('product.pricelist',string='Price List Jual BBN Plat Hitam',domain=[('type','=','sale_bbn_hitam')])
    pricelist_bbn_merah_id = fields.Many2one('product.pricelist',string='Price List Jual BBN Plat Merah',domain=[('type','=','sale_bbn_merah')])

    pricelist_part_sales_id = fields.Many2one('product.pricelist',string='Price List Jual Spare Part',domain=[('type','=','sale')])
    pricelist_part_purchase_id = fields.Many2one('product.pricelist',string='Price List Beli Spare Part',domain=[('type','=','purchase')])

    default_customer_location = fields.Many2one('stock.location',string='Default Customer Location')
    area_ids = fields.Many2many('wtc.area','wtc_area_cabang_rel','branch_id','area_id','Areas')
    user_ids = fields.Many2many('res.users', 'wtc_branch_users_rel', 'branch_id', 'user_id', 'Users')
    blind_bonus_beli = fields.Float(string='Blind Bonus Beli')
    blind_bonus_beli_performance = fields.Float(string='Blind Bonus Beli Performance')
    blind_bonus_jual = fields.Float(string='Blind Bonus Jual')
    profit_centre = fields.Char(string='Profit Centre',required=True,help='please contact your Accounting Manager to get Profit Center.')
    inter_company_account_id = fields.Many2one('account.account',string='Inter Company Account',domain="[('type','!=','view'),'|',('code','ilike',str('1685'+'%')),('code','ilike',str('1696'+'%'))]") 
    pajak_progressive = fields.Boolean('Pajak Progressive',default=True)
    is_mandatory_spk = fields.Boolean('Is Mandatory SPK')
    partner_id = fields.Many2one('res.partner',string='Partner')
    ahass_code = fields.Char(string='Ahass Code')

    _sql_constraints = [
       ('code_unique', 'unique(code)', '`Code` tidak boleh ada yang sama.'),  
    ]
    
    
    def create(self,cr,uid,val,context=None):
        if context is None:
            context = {}  
        wtc_branch_id=[] 
        context.update({
            'form_name': 'Branch'
        })
        obj_res_partner = self.pool.get('res.partner')
        res_partner_id = {
            'name': val['name'],
            'default_code': val['code'],
            'street': val['street']  ,
            'street2': val['street2'],
            'rt': val['rt'],
            'rw': val['rw'],
            'state_id': val['state_id'],
            'city_id': val['city_id'],  
            'kecamatan_id': val['kecamatan_id'],
            'kecamatan': val['kecamatan'],
            'zip_code_id': val['zip_code_id'],
            'kelurahan': val['zip_code_id'],
            'phone': val['phone'],
            'mobile': val['mobile'],
            'fax': val['fax'],
            'email': val['email'] ,                               
            }
        res_partner=obj_res_partner.create(cr,uid,res_partner_id,context=context)
        val['partner_id'] = res_partner
        wtc_branch_id = super(wtc_branch, self).create(cr, uid, val, context=context)
        update_partner = obj_res_partner.write(cr,uid,res_partner,{'branch_id': wtc_branch_id,'customer': False})
        return wtc_branch_id
        
        
    def change_profit_centre(self,cr,uid,ids,profit_centre,context=None):   
        value = {}
        warning = {}
        if profit_centre :
            if len(profit_centre) != 5 :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('Profit Branch harus 5 digit ! ')),
                }
                value = {
                         'profit_centre':False
                         }
            else :
                cek = profit_centre.isdigit()
                if not cek :
                    warning = {
                        'title': ('Perhatian !'),
                        'message': (('Profit Centre hanya boleh numeric ! ')),
                    }
                    value = {
                             'profit_centre':False
                             }      
        return {'warning':warning,'value':value} 
    
    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            name = record.name
            if record.code:
                name = "[%s] %s" % (record.code, name)
            res.append((record.id, name))
        return res

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        if name:
            # Be sure name_search is symetric to name_get
            args = ['|',('name', operator, name),('code', operator, name)] + args
        categories = self.search(args, limit=limit)
        return categories.name_get()
    
    @api.multi
    def get_ids_expedition(self):
        expedition_ids = []
        for expedition in self.harga_ekspedisi_ids :
            expedition_ids.append(expedition.ekspedisi_id.id)
        return expedition_ids
    
    
    @api.multi
    def get_freight_cost_md(self, expedition_id, product_id,kota_penerimaan,branch_id):
        freight_cost = 0
        date = self.get_default_date().strftime('%Y-%m-%d')
        search_expedition_kota=self.env['wtc.harga.ekspedisi'].search([('ekspedisi_id','=',expedition_id),('kota_penerimaan','=',kota_penerimaan),('branch_id','=',branch_id)])
        if not search_expedition_kota :
            raise osv.except_osv(('Perhatian !'), ("Ekspedisi untuk kota '%s' tidak ditemukan di Master Branch '%s' !" %(kota_penerimaan,self.name)))
        effective_pricelist = []
        for ekspedition in search_expedition_kota :
            for line in ekspedition.harga_ekspedisi_id.pricelist_expedition_line_ids :
                if line.start_date <= date and line.end_date >= date :
                    effective_pricelist.append(line.id)
                    for detail in line.pricelist_expedition_line_detail_ids :
                        if detail.product_template_id.id == self.env['product.product'].search([('id','=',product_id)]).product_tmpl_id.id :
                            freight_cost = detail.cost
                            break
            if not effective_pricelist :
                raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan Pricelist aktif utk ekspedisi '%s' di '%s' !" %(ekspedition.ekspedisi_id.name,self.name)))
        return freight_cost
    
    @api.multi
    def get_freight_cost(self, expedition_id, product_id):
        freight_cost = 0
        date = self.get_default_date().strftime('%Y-%m-%d')
        if expedition_id not in self.get_ids_expedition() :
            raise osv.except_osv(('Perhatian !'), ("Ekspedisi tidak ditemukan di Master Branch '%s' !" %self.name))
        for ekspedition in self.harga_ekspedisi_ids :
            if ekspedition.ekspedisi_id.id == expedition_id :
                effective_pricelist = []
                for line in ekspedition.harga_ekspedisi_id.pricelist_expedition_line_ids :
                    if line.start_date <= date and line.end_date >= date :
                        effective_pricelist.append(line.id)
                        for detail in line.pricelist_expedition_line_detail_ids :
                            if detail.product_template_id.id == self.env['product.product'].search([('id','=',product_id)]).product_tmpl_id.id :
                                freight_cost = detail.cost
                                break
                if not effective_pricelist :
                    raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan Pricelist aktif utk ekspedisi '%s' di '%s' !" %(ekspedition.ekspedisi_id.name,self.name)))
        return freight_cost
    
    @api.multi
    def get_default_date(self):
        return pytz.UTC.localize(datetime.now()).astimezone(timezone('Asia/Jakarta'))    
    
    @api.model
    def get_default_date_model(self):
        return pytz.UTC.localize(datetime.now()).astimezone(timezone('Asia/Jakarta'))      

    @api.multi
    def get_default_datetime(self):
        return datetime.now()
    
    @api.model
    def get_default_datetime_model(self):
        return datetime.now()


    @api.model
    def get_default_area_branch(self,id_branch):
        branch_id = self.browse(id_branch)
        if not branch_id.area_id :
            return False
        return branch_id.area_id.id
