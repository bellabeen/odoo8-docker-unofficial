import itertools
from lxml import etree
from datetime import datetime, timedelta
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import openerp.addons.decimal_precision as dp
from openerp.osv import osv

class dealer_spk(models.Model):
    _name = "dealer.spk"
    _description = "SPK Dealer"
    _order = "date_order desc"

    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
        
    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()
            
    name = fields.Char(string='SPK')
    
    branch_id = fields.Many2one('wtc.branch',string='Branch',required=True, default=_get_default_branch)
    
    division = fields.Selection([('Unit','Unit')],required=True,string='Division',default="Unit")
    
    date_order = fields.Date(string='Date Order',default=_get_default_date,readonly=True)
    
    payment_term = fields.Many2one('account.payment.term',string='Payment Term')
    
    partner_id = fields.Many2one('res.partner',string='Customer',domain=[('customer','=',True)],required=True)
    
    finco_id = fields.Many2one('res.partner',string='Finco',domain=[('finance_company','=',True)])
    
    user_id = fields.Many2one('res.users',string='Sales Person',required=True,)
    
    sales_koordinator_id = fields.Many2one('res.users',string='Sales Koordinator')
    
    section_id = fields.Many2one('crm.case.section',string='Sales Team')
    
    sales_source = fields.Selection([
        ('Walk In','Walk In'),
        ('canvasing','Kanvasing'),
        ('pameran','Pameran'),
        ('pos','Pos'),
        ('channel','Channel'),
        ('GC','GC'),
        ('TOP-PU','TOP-PU'),
        ('media_sosial','Media Sosial'),
        ('Lain-Lain','Lain-Lain')],string='Sales Source')
    
    sales_source_location = fields.Many2one('stock.location', string='Sales Source Location')
    
    dealer_spk_line = fields.One2many('dealer.spk.line','dealer_spk_line_id',string='SPK Detail',)
    
    state = fields.Selection([
                    ('draft', 'Draft'),                                
                    ('progress', 'SPK'),
                    ('so', 'Sales Order'),
                    ('done', 'Done'),
                    ('cancelled', 'Cancelled'),
                    ],string='Status',default='draft')
    cddb_id = fields.Many2one('wtc.cddb',string='CDDB',required=True)
    alamat_kirim = fields.Text(string='Alamat Kirim')
    register_spk_id = fields.Many2one('dealer.register.spk.line',string='No. Register')
    dealer_sale_order_id = fields.Many2one('dealer.sale.order')
    confirm_date = fields.Datetime('Confirmed on')
    confirm_uid = fields.Many2one('res.users',string="Confirmed by")
    so_create_date = fields.Date()
    user_create_so_id = fields.Many2one('res.users')
    cancel_date = fields.Datetime('Cancelled on')
    cancel_uid = fields.Many2one('res.users',string="Cancelled by")
    no_ktp = fields.Char(related="partner_id.no_ktp",string="No KTP")
    is_mandatory_spk = fields.Boolean(related="branch_id.is_mandatory_spk",string="Mandatory SPK")
    reason_cancel = fields.Text('Reason Cancel')
    
    @api.onchange('no_ktp')
    def onchange_ktp(self):
        if self.no_ktp :
            partner = self.env['res.partner'].search([
                    ('no_ktp','=',self.no_ktp)
                ])
            if partner :
                self.partner_id = partner

    # @api.onchange('branch_id','sales_source')
    # def onchange_sales_source(self):
    #     domain = {}
    #     lokasi = []
    #     self.sales_source_location = False
    #     if self.sales_source and self.branch_id :
    #         locations = self.env['stock.location'].search_read([
    #                 ('jenis','=',self.sales_source),
    #                 ('branch_id','=',self.branch_id.id),
    #                 ('start_date','<=',self._get_default_date()),
    #                 ('end_date','>=',self._get_default_date()),
    #             ], [])
    #         for loc in locations:
    #             lokasi.append(loc['id'])
    #         domain['sales_source_location'] = [('id','in',lokasi)]
    #         return {'domain':domain}
    #     else :
    #         domain['sales_source_location'] = [('id','=',0)]
    #         return {'domain':domain}

    @api.model
    def create(self,values,context=None):
        
        if not values['dealer_spk_line'] :
            return {'warning':{'title':'Perhatian !','message':'Tidak ada detail, tidak bisa disave!'}}
        values['name'] = self.env['ir.sequence'].get_per_branch(values['branch_id'], 'SPK')
        values['date_order'] = self._get_default_date()
        dealer_spks = super(dealer_spk,self).create(values)
        update_reg = self.env['dealer.register.spk.line'].search([('id','=',values['register_spk_id'])])
        update_reg.write({'spk_id':dealer_spks.id,'state':'spk'})
        #values['register_spk_id'].write({'spk_id':dealer_spks})
        return dealer_spks
    
    @api.multi
    def write(self,values,context=None):
        #print self.register_spk_id,"ids<<<<"
        if values.get('register_spk_id',False):
            self.register_spk_id.write({'spk_id':False,'state':'open'})
            new_reg = self.env['dealer.register.spk.line'].search([('id','=',values.get('register_spk_id',False))])
            update_reg_baru = new_reg.write({'spk_id':self.id,'state':'spk'})
        dealer_spks = super(dealer_spk,self).write(values)
        return dealer_spks
    
    
    def _get_sale_order(self):
        payment_term = False
        if self.finco_id and self.partner_id:
            payment_term = self.finco_id.property_payment_term.id
        else:
            payment_term = self.partner_id.property_payment_term.id
        
        so = {
            'branch_id': self.branch_id.id,
            'division': self.division,
            'date_order': self._get_default_date(),
            'partner_id': self.partner_id.id,
            'user_id': self.user_id.id,
            'sales_koordinator_id':self.sales_koordinator_id.id,
            'sales_source': self.sales_source,
            'finco_id': self.finco_id.id,     
            'dealer_spk_id': self.id,
            'cddb_id': self.cddb_id.id,
            'section_id':self.section_id.id,
            'payment_term': payment_term,
            'sales_source_location':self.sales_source_location.id,
        }
        sale_order_line=[]
        for line in self.dealer_spk_line:
            plat = False
            stnk = False
            uang_muka = False
            biro_jasa_branch = False
            price_bbn = 0.0
            total = 0.0
            price_bbn_beli = 0.0
            price_bbn_notice = 0.0
            price_bbn_proses = 0.0
            price_bbn_jasa = 0.0
            price_bbn_jasa_area = 0.0
            price_bbn_fee_pusat = 0.0
            accrue_ekspedisi = self.branch_id.accrue_ekspedisi
            accrue_proses_bbn = self.branch_id.accrue_proses_bbn
            city = False
            if line.uang_muka:
                uang_muka = line.uang_muka
            
            if self.branch_id.pricelist_unit_sales_id.id:
                price = self._get_price_unit(self.branch_id.pricelist_unit_sales_id.id, line.product_id.id)
            else:
                raise Warning('Pricelist jual unit Cabang "%s" belum ada, silahkan buat dulu' %(self.branch_id.name))
            
            if line.is_bbn == 'Y':
                plat = 'H'
                stnk = line.partner_stnk_id.id
                
                if not (line.partner_stnk_id.city_tab_id.id or line.partner_stnk_id.city_id.id):
                    raise Warning('Alamat customer STNK Belum lengkap!')
                
                if line.partner_stnk_id.sama == True:
                    city =  line.partner_stnk_id.city_id.id
                else:
                    city =  line.partner_stnk_id.city_tab_id.id
                   
                #todo ambil detail harga beli bbn
                if self.branch_id.pricelist_bbn_hitam_id.id:
                    price_bbn = self._get_price_unit(self.branch_id.pricelist_bbn_hitam_id.id, line.product_id.id)
                else:
                    raise Warning('Pricelist jual BBN unit Cabang "%s" belum ada, silahkan buat dulu' %(self.branch_id.name))
                
                if self.branch_id.harga_birojasa_ids:
                    biro_jasa_def = self.env['wtc.harga.birojasa'].search([('branch_id','=',self.branch_id.id),('default_birojasa','=',True)])
                    
                    if biro_jasa_def:
                        biro_jasa_branch = biro_jasa_def.birojasa_id.id
                        biro_line = self._get_harga_bbn_detail(biro_jasa_def.birojasa_id.id, plat, city, line.product_id.product_tmpl_id.id,self.branch_id.id)
                        if not biro_line:
                            raise Warning('Pricelist BBN beli produk %s tidak ditemukan, silahkan buat dulu' %(line.product_id.name))
                        price_bbn_beli= biro_line.total
                        price_bbn_notice= biro_line.notice
                        price_bbn_proses= biro_line.proses
                        price_bbn_jasa= biro_line.jasa
                        price_bbn_jasa_area= biro_line.jasa_area
                        price_bbn_fee_pusat= biro_line.fee_pusat
                    #else do nothing req. indira u/ cabang yg berbeda birojasa tiap kota
                    #set price_bbn jual to 0
                    else:
                        price_bbn = 0.0
                else:
                    raise Warning('Pricelist Beli BBN unit Cabang "%s" belum ada, silahkan buat dulu' %(self.branch_id.name))
                
            location_lot = self._get_location_id_branch(line.product_id.id,self.branch_id.id)
            
            if location_lot:
                lot_id = location_lot.id
                location_id = location_lot.location_id.id
                price_unit_beli = location_lot.hpp
                #update state ke reserved in case ada produk yg sama dalam satu spk
                location_lot.write({'state':'reserved'})
            else:
                raise Warning('Tidak ditemukan stock produk')
            vals_line = {
                'categ_id': 'Unit',
                'product_id': line.product_id.id,
                'product_qty': 1,
                'is_bbn': line.is_bbn,
                'plat': plat,
                'partner_stnk_id': stnk,
                'location_id': location_id,
                'lot_id': lot_id,
                'price_unit': price,
                'biro_jasa_id': biro_jasa_branch or False,  
                'price_bbn': price_bbn or 0.0,
                'price_bbn_beli': price_bbn_beli or 0.0,
                'uang_muka': uang_muka or 0.0,
                'price_unit_beli':price_unit_beli or 0.0,
                'price_bbn_notice': price_bbn_notice or 0.0,
                'price_bbn_proses': price_bbn_proses or 0.0,
                'price_bbn_jasa': price_bbn_jasa or 0.0,
                'price_bbn_jasa_area': price_bbn_jasa_area or 0.0,
                'price_bbn_fee_pusat': price_bbn_fee_pusat or 0.0,
                'tax_id': [(6,0,[x.id for x in line.product_id.taxes_id])],
                'city_id': city,
                'discount_po': line.discount_po,
            }
            if line.is_bbn == 'Y':
                vals_line['accrue_ekspedisi'] = accrue_ekspedisi
                vals_line['accrue_proses_bbn'] = accrue_proses_bbn
            sale_order_line.append([0,False,vals_line])
        
        so['dealer_sale_order_line'] = sale_order_line
       
        return so

    @api.multi
    def action_create_so(self):
        sale_order = self._get_sale_order()
        create_so = self.env['dealer.sale.order'].create(sale_order)

        self.register_spk_id.write({'state':'so','dealer_sale_order_id':create_so.id})
        self.write({'state':'so',
            'user_create_so_id': self._uid,
            'so_create_date':self._get_default_date(),
            'dealer_sale_order_id':create_so.id,
        })        
        return True
    
    
    @api.multi        
    def _get_location_id_branch(self,product_id,branch_id):
        lot_id = self.env['stock.production.lot'].search([('product_id','=',product_id),('state','=','stock'),('branch_id','=',branch_id),('location_id.usage','=','internal')])
        lot_ids = []
        for lot in lot_id:
            lot_ids.append(lot.id)
        quant_id = self.env['stock.quant'].search([('lot_id','in',lot_ids),('reservation_id','=',False)])
        if quant_id:
            return quant_id[0].lot_id
        else:
            return False
    
    def _get_price_unit(self,cr,uid,pricelist,product_id):
        price_unit = self.pool.get('product.pricelist').price_get(cr,uid,[pricelist],product_id,1)[pricelist]
        return price_unit  
    
    
    def _get_harga_bbn_detail(self, cr, uid, ids, birojasa_id, plat, city_id, product_template_id,branch_id):
        if not birojasa_id:
            return False
        birojasa = self.pool.get('wtc.harga.birojasa')
        harga_birojasa = birojasa.search(cr,uid,[
                                                 ('birojasa_id','=',birojasa_id),
                                                 ('branch_id','=',branch_id)
                                                 ])
       
        if not harga_birojasa :
            return False
            
        harga_birojasa_browse = birojasa.browse(cr,uid,harga_birojasa)
        
        bbn_search = self.pool.get('wtc.harga.bbn').search(cr,uid,[
                                                                   ('id','=',harga_birojasa_browse.harga_bbn_id.id)
                                                                   ])
        if not bbn_search :
            return False
            
        
        bbn_browse = self.pool.get('wtc.harga.bbn').browse(cr,uid,bbn_search)
                     
        pricelist_harga_bbn = self.pool.get('wtc.harga.bbn.line').search(cr,uid,[
                ('bbn_id','=',bbn_browse.id),                                                                    
                ('tipe_plat','=',plat),
                ('active','=',True),
                ('start_date','<=',self._get_default_date(cr,uid)),
                ('end_date','>=',self._get_default_date(cr,uid)),
            ])

        if not pricelist_harga_bbn:
            return False
       
        for pricelist_bbn in pricelist_harga_bbn:
            bbn_detail = self.pool.get('wtc.harga.bbn.line.detail').search(cr,uid,[
                    ('harga_bbn_line_id','=',pricelist_bbn),
                    ('product_template_id','=',product_template_id),
                    ('city_id','=',city_id)
                ])
            
            if bbn_detail:
                return self.pool.get('wtc.harga.bbn.line.detail').browse(cr,uid,bbn_detail)
            else:
                return False

        return False
    
    @api.multi
    def action_view_so(self):  
       
        return {
            'name': 'Dealer Sale Order',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'dealer.sale.order',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': self.dealer_sale_order_id.id
            }
    
    @api.multi
    def action_confirm_spk(self):
        self.write({
                    'confirm_date': self._get_default_date().strftime('%Y-%m-%d'),
                    'confirm_uid': self._uid,
                    'state': 'progress',
                    'date_order':self._get_default_date()
                    })
        return True
    
    @api.multi
    def action_cancel_spk(self):
        self.write({
                    'cancel_date': self._get_default_date().strftime('%Y-%m-%d'),
                    'cancel_uid': self._uid,
                    'state': 'cancelled'
                    })
        return True
    
    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Dealer SPK sudah diproses, data tidak bisa didelete !"))
        return super(dealer_spk, self).unlink(cr, uid, ids, context=context)    
           
    
    def branch_change(self,cr,uid,ids,branch_id):
        domain = {}
        value = {'user_id':False,'user_koordinator_id':False}
        if branch_id:
            sales = ('salesman', 'sales_counter', 'sales_partner','sales_koordinator','soh')
            query_sales = """
                select r.user_id
                from resource_resource r 
                inner join hr_employee e on r.id = e.resource_id
                inner join hr_job j on e.job_id = j.id
                inner join res_users u on r.user_id = u.id 
                where (e.tgl_keluar IS NULL OR e.tgl_keluar > NOW())
                and u.active = true
                and r.active = true
                and e.branch_id = %d
                and j.sales_force in %s
                """ % (branch_id, str(sales))
            cr.execute(query_sales)
            ress1 = cr.fetchall()
            if len(ress1) > 0 :
                ids_user = [res[0] for res in ress1]
                domain['user_id'] = [('id','in',ids_user)]
                  
            # ids_job = self.pool.get('hr.job').search(cr, uid, [('sales_force','in',['salesman','sales_counter','sales_partner'])])
            # ids_job_coordinator = self.pool.get('hr.job').search(cr, uid, [('sales_force','=','sales_koordinator')])
            # if ids_job_coordinator :
            #     ids_coordinator_employee = self.pool.get('hr.employee').search(cr, uid, [('job_id','in',ids_job_coordinator),('branch_id','=',branch_id)])
            #     if ids_coordinator_employee :
            #         ids_coordinator_user = [employee_coordinator.user_id.id for employee_coordinator in self.pool.get('hr.employee').browse(cr, uid, ids_coordinator_employee)]
            #         domain['sales_koordinator_id'] = [('id','in',ids_coordinator_user)]    
            # if ids_job :
            #     ids_employee = self.pool.get('hr.employee').search(cr, uid, [('job_id','in',ids_job),('branch_id','=',branch_id)])
            #     if ids_employee :
            #         ids_user = [employee.user_id.id for employee in self.pool.get('hr.employee').browse(cr, uid, ids_employee)]
            #         domain['user_id'] = [('id','in',ids_user)]
        return {'value':value, 'domain':domain}
    
    def user_change(self,cr,uid,ids,user_id,branch_id):
        domain = {}
        obj_employee=self.pool.get('hr.employee')
        if user_id :
            obj_search_empl=obj_employee.search(cr, uid,[('user_id','=',user_id)])
            if obj_search_empl :
                obj_browse_empl=obj_employee.browse(cr,uid,obj_search_empl)
                if obj_browse_empl.job_id.sales_force == 'sales_counter' or obj_browse_empl.job_id.sales_force == 'soh':
                    sales_force = ('soh','AM')
                else :
                    sales_force = ('sales_koordinator','soh','AM')
                query_sco = """
                    select r.user_id
                    from resource_resource r
                    inner join hr_employee e on r.id = e.resource_id
                    inner join hr_job j on e.job_id = j.id 
                    inner join res_users u on r.user_id = u.id 
                    INNER JOIN wtc_area_cabang_rel as area on area.area_id=e.area_id
                    where (e.tgl_keluar IS NULL OR e.tgl_keluar > NOW())
                    and u.active = true
                    and r.active = true
                    and area.branch_id = %d
                    and j.sales_force in %s
                    """ % (branch_id, str(sales_force))
                cr.execute(query_sco)
                ress2 = cr.fetchall()
                if len(ress2) > 0 :
                    ids_sco = [res[0] for res in ress2]
                    domain['sales_koordinator_id'] = [('id','in',ids_sco)]
                return {'value':{'sales_koordinator_id':False},'domain':domain}
            
            
    
class dealer_spk_line(models.Model):
    _name = "dealer.spk.line"
    _description = "SPK Line"
    _order = "id"
    
    categ_id = fields.Selection([('Unit','Unit')],string='Category',required=True,default="Unit")
    dealer_spk_line_id = fields.Many2one('dealer.spk')
    product_id = fields.Many2one('product.product',string="Produk")
    product_qty = fields.Integer(string="Qty",default=1)
    is_bbn = fields.Selection([('Y','Y'),('T','T')],'BBN',required=True)
    plat = fields.Selection([('H','H'),('M','M')],string='Plat')
    partner_stnk_id = fields.Many2one('res.partner',string='STNK',domain=[('customer','=',True)])
    uang_muka = fields.Float(string='Uang Muka')
    discount_po = fields.Float(string='Potongan Pelanggan')
    
    @api.onchange('categ_id')
    def category_change(self):
        dom = {}
        tampung = []
        if self.categ_id:
            categ_ids = self.env['product.category'].get_child_ids(self.categ_id)
            dom['product_id']=[('categ_id','in',categ_ids)]
        return {'domain':dom}
    
class dealer_reason_spk_cancel(models.TransientModel):
    _name = "dealer.reason.cancel.spk"
   
    reason = fields.Text('Reason',required=True)
    
    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()
        
    @api.multi
    def action_post_cancel(self, context=None):
        spk_id = context.get('active_id',False) #When you call any wizard then in this function ids parameter contain the list of ids of the current wizard record. So, to get the purchase order ID you have to get it from context.
        
        spk_obj = self.env['dealer.spk'].browse(spk_id)
        spk_obj.write({'reason_cancel':self.reason,
                    'cancel_date': self._get_default_date().strftime('%Y-%m-%d'),
                    'cancel_uid': self._uid,
                    'state': 'cancelled'
                       })
        return True
    
   
