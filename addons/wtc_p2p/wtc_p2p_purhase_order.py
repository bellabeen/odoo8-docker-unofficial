import time
import base64
from datetime import datetime
from openerp import models, fields, api
from openerp.osv import osv
from openerp.tools.translate import _
import math
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
from openerp import SUPERUSER_ID
from lxml import etree
import os
from openerp.exceptions import Warning

class export_upo(models.Model):
    _name = "eksport.upo"
    
    name = fields.Char('File Name')
    data_file = fields.Text('Isi File')
    url_file = fields.Char('File URL')
    p2p_id = fields.Many2one('wtc.p2p.purchase.order',string='P2P')
    
    _sql_constraints = [
    ('unique_p2p_id', 'unique(p2p_id)', 'File UPO sudah pernah dibuat !'),
    ]
    
    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()
        
    def eksport_upo1(self, cr, uid, uids,trx_obj, context=None):
        result = ''
        kodeMD = trx_obj.dealer_id.branch_id.ahm_code
        bulan = self._get_default_date().strftime('%m')
        tahun = self._get_default_date().strftime('%Y') 
        po_md = trx_obj.name
        if trx_obj.purchase_order_type_id.name=='Fix':
                tipe_po = 'F'
        else:
                tipe_po = 'A'
        periode = self.pool.get('wtc.p2p.periode').search(cr,uid,[('name','=',trx_obj.periode_id)])
        periode_obj = self.pool.get('wtc.p2p.periode').browse(cr,uid,periode)
        eff_start_date = str(datetime.strptime(periode_obj.start_date,'%Y-%m-%d').strftime('%d%m%Y'))
        eff_end_date = str(datetime.strptime(periode_obj.end_date,'%Y-%m-%d').strftime('%d%m%Y'))

        if trx_obj.type_name == 'Fix' :                
            for x in trx_obj.purchase_line :
                product_template = x.product_id.product_tmpl_id.name
                color = x.product_id.attribute_value_ids.code
                
                qty_fix = str(x.fix_qty)
                tent1_qty = str(x.tent1_qty)
                tent2_qty = str(x.tent2_qty)
                result += kodeMD +';'+ bulan +';'+ tahun +';'+ product_template +';'+ color +';'+ qty_fix +';'+tent1_qty+';'+tent2_qty+';'+po_md+';'+tipe_po+';'+eff_start_date+';'+eff_end_date+';'
                result += '\n'  

        elif trx_obj.type_name == 'Additional' :                
            for x in trx_obj.additional_line :
                product_template = x.product_id.product_tmpl_id.name
                color = x.product_id.attribute_value_ids.code
                
                qty_fix = str(x.fix_qty)
                tent1_qty = str(0)
                tent2_qty = str(0)
                result += kodeMD +';'+ bulan +';'+ tahun +';'+ product_template +';'+ color +';'+ qty_fix +';'+tent1_qty+';'+tent2_qty+';'+po_md+';'+tipe_po+';'+eff_start_date+';'+eff_end_date+';'
                result += '\n' 
                
        path = 'static/'
        nama = po_md.replace("/","-") + '.UPO'
        url_file = 'wtc_p2p/'+path+po_md.replace("/","-") + '.UPO'
        create_upo = self.write(cr,uid,ids,{'url_file':url_file,'name':nama,'data_file':result,'p2p_id':trx_obj.id},context=context)
        if create_upo:
            file = open(path+nama,'w+')
            file.write(result)
        #self.write(cr,uid,ids,{'name':nama,'data_file':result})
        #out = base64.encodestring(result)
        #upo = self.write(cr, uid, ids, {'data_file':out, 'name': nama}, context=context)
        
    @api.multi    
    def eksport_upo(self, trx_obj):
        result = ''
        kodeMD = trx_obj.dealer_id.branch_id.ahm_code
        bulan = self._get_default_date().strftime('%m')
        tahun = self._get_default_date().strftime('%Y') 
        po_md = trx_obj.name
        if trx_obj.purchase_order_type_id.name=='Fix':
                tipe_po = 'F'
        else:
                tipe_po = 'A'
        periode = self.env['wtc.p2p.periode'].search([('name','=',trx_obj.periode_id)])
        eff_start_date = str(datetime.strptime(periode.start_date,'%Y-%m-%d').strftime('%d%m%Y'))
        eff_end_date = str(datetime.strptime(periode.end_date,'%Y-%m-%d').strftime('%d%m%Y'))
        dealer_branch_id = trx_obj.dealer_id.branch_id 
        pricelist_id = dealer_branch_id.pricelist_unit_purchase_id 
        uom_id = False
        if not pricelist_id :
                raise osv.except_osv(('Perhatian !'), ("Pricelist beli belum ada, silahkan ditambahkan di Branch."))
        if trx_obj.type_name == 'Fix' :      
            for x in trx_obj.purchase_line :
                product_uom_po_id = x.product_id.uom_po_id.id
                if not uom_id:
                    uom_id = product_uom_po_id      
                date_order_str = datetime.strptime(trx_obj.date, DEFAULT_SERVER_DATETIME_FORMAT).strftime(DEFAULT_SERVER_DATE_FORMAT)
                price = pricelist_id.price_get(x.product_id.id, x.fix_qty or 1.0, trx_obj.supplier_id or False, context={'uom': uom_id, 'date': date_order_str})[pricelist_id.id]
                if not price :
                    raise osv.except_osv(('Perhatian !'), ("Product %s tidak ada dalam pricelist %s")%(x.product_id.name,pricelist_id.name))  
                product_template = x.product_id.product_tmpl_id.name
                color = x.product_id.attribute_value_ids.code
                
                qty_fix = str(x.fix_qty)
                tent1_qty = str(x.tent1_qty)
                tent2_qty = str(x.tent2_qty)
                result += kodeMD +';'+ bulan +';'+ tahun +';'+ product_template +';'+ color +';'+ qty_fix +';'+tent1_qty+';'+tent2_qty+';'+po_md+';'+tipe_po+';'+eff_start_date+';'+eff_end_date+';'
                result += '\n\r'  
        if trx_obj.type_name == 'Additional' :      
            for x in trx_obj.additional_line :
                product_uom_po_id = x.product_id.uom_po_id.id
                if not uom_id:
                    uom_id = product_uom_po_id           
                date_order_str = datetime.strptime(trx_obj.date, DEFAULT_SERVER_DATETIME_FORMAT).strftime(DEFAULT_SERVER_DATE_FORMAT)
                price = pricelist_id.price_get(x.product_id.id, x.fix_qty or 1.0, trx_obj.supplier_id or False, context={'uom': uom_id, 'date': date_order_str})[pricelist_id.id]
                if not price :
                    raise osv.except_osv(('Perhatian !'), ("Product %s tidak ada dalam pricelist %s")%(x.product_id.name,pricelist_id.name))  
                # product_template = x.product_id.product_tmpl_id.name
                # color = x.product_id.attribute_value_ids.code
                product_template = str(x.product_id.product_tmpl_id.name).encode('ascii','ignore').decode('ascii')
                color = str(x.product_id.attribute_value_ids.code).encode('ascii','ignore').decode('ascii')
                
                qty_fix = str(x.fix_qty).encode('ascii','ignore').decode('ascii')
                tent1_qty = str(0).encode('ascii','ignore').decode('ascii')
                tent2_qty = str(0).encode('ascii','ignore').decode('ascii')
                result += kodeMD +';'+ bulan +';'+ tahun +';'+ product_template +';'+ color +';'+ qty_fix +';'+tent1_qty+';'+tent2_qty+';'+po_md+';'+tipe_po+';'+eff_start_date+';'+eff_end_date+';'
                result += '\n\r'         
        path = 'wtc_p2p/static/'
        nama = kodeMD+'-'+po_md.replace("/","") + '.UPO'
        url_file = '/'+path+kodeMD+'-'+po_md.replace("/","") + '.UPO'
        create_upo = self.create({'url_file':url_file,'name':nama,'data_file':result,'p2p_id':trx_obj.id})
        if create_upo:
            file = open(os.path.dirname(os.path.abspath(__file__))+'/static/'+nama,'w+')
            file.write(result)



class wtc_p2p_purchase_order(models.Model):
    _name = "wtc.p2p.purchase.order"
    _description ="P2P Purchase Order"
    _order = "id desc"

    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
    
    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('validate', 'Validated'),
        ('waiting_for_approval','Waiting Approval'),
        ('approved', 'Approved'),
        ('confirmed', 'Confirmed'),        
        ('cancel', 'Cancelled'),
        ('reject', 'Rejected'),
    ]  

    @api.model
    def _periode_get(self):
        obj_periode = self.env['wtc.p2p.periode'].search([
                                                         ('start_date','<=',self._get_default_date()),
                                                         ('end_date','>=',self._get_default_date())
                                                         ], order='name')
        return [(periode.name,periode.name) for periode in obj_periode]
    
    @api.onchange('purchase_order_type_id')
    def get_type(self):
        self.type_name=self.purchase_order_type_id.name                
#     @api.model
#     def _periode_get(self):
#         obj_periode = self.env['wtc.p2p.periode'].search([], order='name')
#         return [(periode.name,periode.name) for periode in obj_periode]

#     @api.onchange('purchase_order_type_id')
#     def get_type(self):
#         order_type = self.env['wtc.purchase.order.type'].search([
#                                                                  ('category','=',self.division),
#                                                                  ('name','=','Fix')
#                                                                  ])
#         if order_type :
#             self.purchase_order_type_id = order_type.id
#         else :
#             self.purchase_order_type_id = False   
             
#     @api.onchange('periode_id')
#     def get_periode(self):
#         obj_periode = self.env['wtc.p2p.periode'].search([
#                                                          ('start_date','<=',datetime.today()),
#                                                          ('end_date','>=',datetime.today())
#                                                          ], order='name')
#         print ">>>>>>>>>>>>>>>>>>>.",obj_periode
#         if obj_periode :
#             self.periode_id = obj_periode[0].name
#         else :
#             self.periode_id = False               
            
    @api.onchange('dealer_id')
    def get_supplier_id(self):
        dealer_id = self.dealer_id
        self.branch_type = dealer_id.branch_id.branch_type

        domain = {}
        warning = {}
        if dealer_id.dealer :
            supplier_id = dealer_id.branch_id.partner_id.id
            self.credit_limit_unit = dealer_id.credit_limit_unit
            self.credit_limit_sparepart = dealer_id.credit_limit_sparepart
           
            if not supplier_id :
                        warning = {
                            'title': ('Perhatian !'),
                            'message': (("Partner belum diisi dalam master branch")),
                        }   
            if not warning :               
                self.supplier_id = supplier_id
                domain['supplier_id'] = [('id','in',[supplier_id])]
        elif dealer_id.branch :
            supplier_id = dealer_id.branch_id.default_supplier_id.id
            if not supplier_id :
                        warning = {
                            'title': ('Perhatian !'),
                            'message': (("Default Supplier belum diisi dalam master branch")),
                        }   
            if not warning :               
                self.supplier_id = supplier_id   
                domain['supplier_id'] = [('id','in',[supplier_id])]
        return {'warning':warning,'domain':domain}         
              
    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()                      
        
    name = fields.Char(string='Name')
    dealer_id = fields.Many2one('res.partner',domain="['|','|',('ahass','=',True),('dealer','=',True),('branch','=',True),('branch_id','!=',False)]",string='Dealer', required=True)
    supplier_id = fields.Many2one('res.partner', string='Supplier', required=True, domain="['|',('principle','!=',False),('branch','!=',False)]")
    division=fields.Selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum')], 'Division', change_default=True, default='Unit',select=True)
    date = fields.Datetime(string='Date',default=_get_default_date)

    credit_limit_unit = fields.Float(string='Credit Limit Unit')
    credit_limit_sparepart = fields.Float(string='Credit Limit Sparepart')

    purchase_order_type_id = fields.Many2one('wtc.purchase.order.type','Type',required=True,domain="[('category','=',division),'|',('name','=','Fix'),('name','=','Additional')]",)
    periode_id = fields.Selection(_periode_get, string='Periode')
    state= fields.Selection(STATE_SELECTION, string='State', readonly=True,default='draft')
    purchase_line = fields.One2many('wtc.p2p.purchase.order.line','purchase_id')
    confirm_uid = fields.Many2one('res.users',string="Confirmed by")
    confirm_date = fields.Datetime('Confirmed on')
    approval_ids = fields.One2many('wtc.approval.line','transaction_id',string="Table Approval",domain=[('form_id','=',_name)])
    approval_state =  fields.Selection([
                                        ('b','Belum Request'),
                                        ('rf','Request For Approval'),
                                        ('a','Approved'),
                                        ('r','Reject')
                                        ],'Approval State', readonly=True,default='b')
    is_branch = fields.Boolean(related='dealer_id.branch')
    branch_id = fields.Many2one(related='dealer_id.branch_id')
    user_id = fields.Many2one('res.users', 'Responsible')
    is_type_po = fields.Boolean(string='Type P2P')
    description = fields.Char('Description')
    additional_line = fields.One2many('wtc.p2p.purchase.order.line','purchase_id')
    type_name = fields.Char()
    branch_type = fields.Char()
    

    @api.model
    def create(self,vals,context=None):  
        partner_id = self.env['res.partner'].search([
                                                          ('id','in',[vals['dealer_id']])
                                                          ])  
        vals['name'] = self.env['ir.sequence'].get_sequence('P2P/'+str(partner_id.default_code))     
        vals['date'] = self._get_default_date()                        
        purchase_id = super(wtc_p2p_purchase_order, self).create(vals)
        return purchase_id         

    def write(self, cr, uid, ids, vals, context=None):
        purchase_id = self.browse(cr, uid, ids, context=context)
        if purchase_id.type_name == 'Fix' :
            vals.get('purchase_line', []).sort(reverse=True)
            vals.pop('additional_line',None)
        elif purchase_id.type_name == 'Additional' :
            vals.get('additional_line', []).sort(reverse=True)
            vals.pop('purchase_line',None)
        return super(wtc_p2p_purchase_order, self).write(cr, uid, ids, vals, context=context)
    
#     @api.cr_uid_ids_context 
#     def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
#         if not context: context = {}
#         res = super(wtc_p2p_purchase_order, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
#         user=self.pool.get('res.users').browse(cr,uid,uid)
#         branch_user = user.branch_ids
#         dealer_user = user.dealer_id
#         partner_ids = []
#         for x in branch_user :
#             if x.partner_id :
#                 partner_ids.append(x.partner_id.id)
#         if dealer_user :
#             if dealer_user.id not in partner_ids :
#                 partner_ids.append(dealer_user.id)
# 
#         doc = etree.XML(res['arch'])
#         if view_type == 'search' :
#             nodes_branch = doc.xpath("//filter[@name='partner_filter']")
#             for node in nodes_branch:
#                 node.set('domain', '[("dealer_id", "in", '+ str(partner_ids)+')]')
#         res['arch'] = etree.tostring(doc)
#         return res

    @api.multi
    def reject_by_ahm(self):
        self.state = 'reject'
        self.copy()
 
    @api.multi
    def copy(self, default=None, context=None):
        purchase_line = []
        additional_line = []
        if default is None:
            default = {}
         
        date = self._get_default_date()
        default.update({
                        'dealer_id': self.dealer_id.id,
                        'supplier_id':self.supplier_id.id,
                        'division': self.division,
                        'date': date,
                        'purchase_order_type_id': self.purchase_order_type_id.id,
                        'periode_id': self.periode_id,
                        'state': 'draft',
                        'is_branch': self.is_branch,
                        'branch_id':self.branch_id.id or False,              
                        'user_id': self.user_id.id,
                        'is_type_po': self.is_type_po,
                        'description':self.description,
                        'approval_state': 'b',
                        'type_name':self.type_name,
                        'branch_type':self.branch_type,
                        })
        if self.type_name == 'Fix' :
            for lines in self.purchase_line:
                purchase_line.append([0,False,{
                                              'product_id':lines.product_id.id,
                                              'product_id_show':lines.product_id_show.id,
                                              'fix_qty':lines.fix_qty,
                                              'tent1_qty':lines.tent1_qty,
                                              'tent2_qty':lines.tent2_qty,
                                              'tent1_prev_qty':lines.tent1_prev_qty,
                                              'tent2_prev_qty':lines.tent2_prev_qty,
                                              'tent1_prev_qty_show':lines.tent1_prev_qty_show,
                                              'tent2_prev_qty_show':lines.tent2_prev_qty_show,
                                              'qty_available':lines.qty_available,
                                              'qty_available':lines.qty_available_show,
                                              'active':lines.active,
                                              'type':lines.type                                            
                                             
                                              }])
            default.update({'purchase_line':purchase_line})
        elif self.type_name == 'Additional' :
            for lines in self.additional_line:
                additional_line.append([0,False,{
                                              'product_id':lines.product_id.id,
                                              'fix_qty':lines.fix_qty,
                                              'tent1_qty':0,
                                              'tent2_qty':0,
                                              'tent1_prev_qty':0,
                                              'tent2_prev_qty':0,
                                              'tent1_prev_qty_show':0,
                                              'tent2_prev_qty_show':0, 
                                              'qty_available':0,
                                              'qty_available_show':0, 
                                              'active':lines.active,
                                              'type':lines.type                                            
                                             
                                              }])
            default.update({'additional_line':additional_line})            
        return super(wtc_p2p_purchase_order, self).copy(default=default, context=context)
              
    @api.multi
    def generate_line(self):
        product = []
        rekap_periode=[]
        categ_ids = self.env['product.category'].get_child_ids(self.division)
        date = datetime.strptime(self.date,'%Y-%m-%d %H:%M:%S') 
        rekap_product = self.env['wtc.p2p.product'].search([
                                                            ('categ_id','in',categ_ids),
                                                            ('start_date','<=',str(date.date())),
                                                            ('end_date','>=',str(date.date()))
                                                            ])
        for x in rekap_product :
            product.append(x.product_id)
         
        product_line = self.env['wtc.p2p.purchase.order.line']
        
        if self.periode_id[-2:] == '01' :
            periode_prev = int(self.periode_id[:4]) - 1
            obj_periode = self.env['wtc.p2p.periode'].search([
                                                              ('name','like',str(periode_prev))
                                                              ])
            for x in obj_periode :
                rekap_periode.append(x.name)
            prev_periode = max(rekap_periode)  
        else :
            prev_periode = int(self.periode_id) - 1
        prev_purchase = self.search([
                                    ('periode_id','=',prev_periode),
                                    ('supplier_id','=',self.supplier_id.id),
                                    ('dealer_id','=',self.dealer_id.id),
                                    ('division','=',self.division),
                                    ('state','=','confirmed'),
                                    ('purchase_order_type_id','=',self.purchase_order_type_id.id)
                                     ])
        if prev_purchase :
            product_rekap = {}
            for line in product : 
                product_get = product_line.search([
                                                   ('purchase_id','=',prev_purchase.id),
                                                   ('product_id','=',line.id)
                                                   ])
                if product_get :
                    if self.division=='Unit' :
                        qty_in_picking = self.env['stock.picking']._get_qty_picking(self.supplier_id.branch_id.id,self.division,product_get.product_id.id)
                        qty_in_lot     = self.env['stock.picking']._get_qty_lot(self.supplier_id.branch_id.id,product_get.product_id.id)
                        qty=qty_in_lot-qty_in_picking
                       



                    elif self.division=='Sparepart':
                         qty_in_picking = self.env['stock.picking']._get_qty_picking(self.supplier_id.branch_id.id,self.division,product_get.product_id.id)
                         qty_in_quant = self.env['stock.picking']._get_qty_quant(self.supplier_id.branch_id.id,product_get.product_id.id)
                         qty=qty_in_quant-qty_in_picking

                    product_line_vals = {
                                            'product_id': product_get.product_id.id,
                                            'purchase_id' :self.id,
                                            'qty_available' :qty,
                                            'qty_available_show' :qty,
                                            'fix_qty':product_get.tent1_qty,
                                            'tent1_qty': product_get.tent2_qty,
                                            'tent1_prev_qty' :product_get.tent1_qty,
                                            'tent2_prev_qty' : product_get.tent2_qty, 
                                            'tent1_prev_qty_show' : product_get.tent1_qty,
                                            'tent2_prev_qty_show' : product_get.tent2_qty,                                
                                          }
                    self.env['wtc.p2p.purchase.order.line'].create(product_line_vals)    
                else :
                    product_line_vals = {
                                            'product_id': line.id,
                                            'purchase_id' :self.id,         
                                            'tent1_prev_qty' :-1,
                                            'tent2_prev_qty' : -1, 
                                            'tent1_prev_qty_show' : -1,
                                            'tent2_prev_qty_show' : -1,  
                                            'qty_available' : -1,
                                            'qty_available_show' : -1,                                                                                                
                                          }
                    self.env['wtc.p2p.purchase.order.line'].create(product_line_vals)                     
        if not prev_purchase :
            if not product :
                raise osv.except_osv(('Perhatian !'), ('Silahkan isi product dalam master P2P product terlebih dahulu !'))
            for line in product : 
                if self.division=='Unit' :
                        qty_in_picking = self.env['stock.picking']._get_qty_picking(self.supplier_id.branch_id.id,self.division,line.id)
                        qty_in_lot = self.env['stock.picking']._get_qty_lot(self.supplier_id.branch_id.id,line.id)
                        qty=qty_in_lot-qty_in_picking
                        
                elif self.division=='Sparepart':
                        qty_in_picking = self.env['stock.picking']._get_qty_picking(self.supplier_id.branch_id.id,self.division,line.id)
                        qty_in_quant = self.env['stock.picking']._get_qty_quant(self.supplier_id.branch_id.id,line.id)
                        qty=qty_in_quant-qty_in_picking

                product_line_vals = {
                                        'product_id': line.id,
                                        'purchase_id' :self.id,  
                                        'qty_available' :qty,  
                                        'tent1_prev_qty' :-1,
                                        'tent2_prev_qty' : -1, 
                                        'tent1_prev_qty_show' : -1,
                                        'tent2_prev_qty_show' : -1,                                                                     
                                      }
                self.env['wtc.p2p.purchase.order.line'].create(product_line_vals)                   
    @api.multi 
    def action_recheck(self):
        warning = ""
        msg = ""
        for line in self.additional_line :
            qty_in_picking = self.env['stock.picking']._get_qty_picking(line.purchase_id.branch_id.id,line.purchase_id.division,line.product_id.id)
            qty_in_quant = self.env['stock.picking']._get_qty_quant(line.purchase_id.branch_id.id,line.product_id.id)
            stock_rfs = qty_in_quant-qty_in_picking   
            if stock_rfs < line.fix_qty:
                # print stock_rfs,'<',line.fix_qty, stock_rfs < line.fix_qty
                if stock_rfs <= 0:
                    msg = 'Qty Not Available'
                else:
                    msg = 'Qty Available %s' %stock_rfs
                warning += "- %s %s \r\n" % (line.product_id.name,msg)

        if warning != "" :
            raise Warning("Stok Available tidak mencukupi untuk Barang-barang dibawah ini:\r\n %s " % warning)

    @api.multi 
    def validate_order(self):
        if self.division == 'Sparepart' and self.branch_id.branch_type=='MD':
            self.action_recheck()

        ids_product = []
        for line in self.additional_line :
            ids_product.append(line.product_id.id)
        if ids_product :
            ids_product.sort(reverse=False)
            id_product_before = 0
            for id in ids_product :
                if id_product_before == id :
                    raise osv.except_osv(('Perhatian !'), ('Tidak boleh ada Product yg sama dalam satu transaksi !'))
                id_product_before = id
            
        if not self.purchase_line and self.type_name == 'Fix':
            raise osv.except_osv(('Perhatian !'), ('Silahkan Generate data terlebih dahulu !'))                     
        
        if not self.additional_line and self.type_name == 'Additional':
            raise osv.except_osv(('Perhatian !'), ('Silahkan isi detil terlebih dahulu !'))                     
                
        supplier_id = self.supplier_id
            
        periode_id = self.env['wtc.p2p.periode'].search([
                                                         ('name','=',self.periode_id)
                                                         ])
        if self.type_name == 'Fix' :    
            self.cek_data(periode_id)
            
        self.cek_p2p_type_color()
        total_qty = 0.0   
        if self.type_name == 'Fix'   :                                          
            for line in self.purchase_line :
                  total_qty += line.fix_qty 
            if total_qty < 1 :
                    raise osv.except_osv(('Perhatian !'), ("Total Fix Qty harus lebih besar dari 0"))
        elif self.type_name == 'Additional'   :                                          
            for line in self.additional_line :
                  total_qty += line.fix_qty 
            if total_qty < 1 :
                    raise osv.except_osv(('Perhatian !'), ("Total Fix Qty harus lebih besar dari 0"))
                            
        self.cek_p2p_config(supplier_id)
        self.cek_p2p_periode(periode_id)
        self.state = 'validate'
        
    @api.multi
    def cancel_order(self):
        self.state = 'cancel'
        
    @api.multi
    def cek_data(self,periode_id):
        #cek data                
        data_search = self.search([
                                   ('id','!=',self.id),
                                   ('supplier_id','=',self.supplier_id.id),
                                   ('periode_id','=',periode_id.name),
                                   ('purchase_order_type_id','=',self.purchase_order_type_id.id),
                                   ('dealer_id','=',self.dealer_id.id),'|','|','|',
                                   ('state','=','validate'),
                                   ('state','=','waiting_for_approval'),
                                   ('state','=','confirmed'),
                                   ('state','=','approved')
                                   ])
        if data_search :
            raise osv.except_osv(('Perhatian !'), ('Transaksi pernah dibuat dengan nomor Transaksi %s')%(data_search[0].name))
           
    @api.multi
    def cek_p2p_type_color(self):
        #cek product
        date = datetime.strptime(self.date,'%Y-%m-%d %H:%M:%S')        
        for x in self.purchase_line :
            product = self.env['wtc.p2p.product'].search([
                                                             ('product_id','=',x.product_id.id)
                                                             ])
            if not product :
                raise osv.except_osv(('Perhatian !'), ("Product %s(%s) tidak ada dalam Master P2P Product !")%(x.product_id.name,x.product_id.attribute_value_ids.name))
             
            if product.start_date > str(date.date()) or product.end_date < str(date.date()) :
                raise osv.except_osv(('Perhatian !'), ("Product %s(%s) sudah tidak aktif !")%(x.product_id.name,x.product_id.attribute_value_ids.name))
      
    @api.multi
    def cek_p2p_config(self,supplier_id):
        #cek type color
        p2p_config = self.env['wtc.p2p.config'].search([
                                                        ('supplier_id','=',supplier_id.id)
                                                        ])
        if not p2p_config :
                raise osv.except_osv(('Perhatian !'), ("Supplier %s tidak ditemukan di Master P2P Config")%(supplier_id.name))
        
            
    @api.multi
    def cek_p2p_periode(self,periode_id):
        #cek periode
        periode = self.env['wtc.p2p.periode'].search([
                                                      ('name','=',periode_id.name)
                                                      ])        
        date = datetime.strptime(self.date,'%Y-%m-%d %H:%M:%S')        
        if str(date.date()) < periode.start_date or str(date.date()) > periode.end_date:
            raise osv.except_osv(('Perhatian !'), ("Tanggal tidak termasuk dalam periode %s, mohon cek kembali Master P2P Periode")%(periode.name))
    @api.multi
    def wkf_request_approval(self):
        obj_matrix = self.env["wtc.approval.matrixbiaya"]
        total = 0
        for qty in self.purchase_line :
            total = total + qty.fix_qty
        obj_matrix.request_by_value(self, total)

        self.state =  'waiting_for_approval'
        self.approval_state = 'rf'
    
    @api.multi      
    def wkf_approval(self):
        
        approval_sts = self.env['wtc.approval.matrixbiaya'].approve(self)
        if approval_sts == 1:
            self.write({'approval_state':'a','confirm_uid':self._uid,'confirm_date':datetime.now(),'state':'approved'})
#             self.confirm_order()
            
        elif approval_sts == 0:
                raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group Approval"))
    
    @api.multi
    def confirm_order(self):
        self.state = 'confirmed'
        self.date = self._get_default_date()     
        if self.dealer_id.branch and self.dealer_id.branch_id.branch_type == 'MD' :
            self.action_create_purchase_order()
            self.is_type_po = True
        else :
            self.action_create_distribution()

        return True
    
    @api.multi
    def confirm_order_dealer(self):
        self.state = 'confirmed'
        self.date = self._get_default_date()       
        if self.dealer_id.branch and self.dealer_id.branch_id.branch_type == 'MD' :
            self.action_create_purchase_order()
            self.is_type_po = True
        else :
            self.action_create_distribution()

        return True
        
    @api.multi
    def action_create_distribution(self):
        type = self.purchase_order_type_id
        self.start_date = False
        self.end_date = False
        branch_requester_id = False
        if type:
            self.start_date = type.get_date(type.date_start)
            self.end_date = type.get_date(type.date_end)
        
        if self.supplier_id.branch_id.id :
            branch_sender_id=self.supplier_id.branch_id.id
        else :
            raise osv.except_osv(('Perhatian !'), ("Branch belum di isi di Supplier"))
        
        if self.dealer_id.branch_id and self.dealer_id.branch:
            branch_requester_id = self.dealer_id.branch_id.id
        elif not self.dealer_id.branch_id and self.dealer_id.branch:
            raise osv.except_osv(('Perhatian !'), ("Branch belum di isi di Dealer"))

        total_qty = 0.0   
        if self.type_name == 'Fix'   :                                          
            for line in self.purchase_line :
                  total_qty += line.fix_qty 
            if total_qty < 1 :
                    raise osv.except_osv(('Perhatian !'), ("Total Fix Qty harus lebih besar dari 0"))
        elif self.type_name == 'Additional'   :                                          
            for line in self.additional_line :
                  total_qty += line.fix_qty 
            if total_qty < 1 :
                    raise osv.except_osv(('Perhatian !'), ("Total Fix Qty harus lebih besar dari 0"))
                        
        distribution_vals = {
                             'branch_id': branch_sender_id  ,
                             'dealer_id': self.dealer_id.id ,
                             'branch_requester_id':branch_requester_id  ,
                             'division' : self.division,
                             'origin' : self.name,
                             'user_id': self.user_id.id,
                             'type_id': self.purchase_order_type_id.id,
                             'date': self.date,
                             'start_date': self.start_date,
                             'end_date': self.end_date,
                             'description': self.description,
                             'state': 'confirm',
                             }
        
        
        distribution_line_vals = []
        if self.type_name == 'Fix' :
            for line in self.purchase_line :
                if line.fix_qty > 0 :
                    if self.division == 'Unit' :
                        if self.branch_id.pricelist_unit_purchase_id.id:
                            price=self._get_price_unit(self.branch_id.pricelist_unit_purchase_id.id,line.product_id.id)
                        if not price :
                            raise osv.except_osv(('Perhatian !'), ("Product %s tidak ada dalam pricelist beli unit")%(line.product_id.name))  
                    elif self.division == 'Sparepart' :
                        if self.branch_id.pricelist_part_purchase_id.id:
                            price=self._get_price_unit(self.branch_id.pricelist_part_purchase_id.id,line.product_id.id)
                        if not price :
                            raise osv.except_osv(('Perhatian !'), ("Product %s tidak ada dalam pricelist beli part")%(line.product_id.name))  
                    distribution_line_vals.append([0,False,
                                            {
                                              'product_id': line.product_id.id,
                                              'description': line.product_id.description,
                                              'requested_qty': line.fix_qty,
                                              'approved_qty':line.fix_qty,
                                              'qty': 0,
                                              'supply_qty': 0,
                                              'unit_price': price,
                                              }])
        elif self.type_name == 'Additional' :
            for line in self.additional_line :
                if line.fix_qty > 0 :
                    if self.division == 'Unit' :
                        if self.branch_id.pricelist_unit_purchase_id.id:
                            price=self._get_price_unit(self.branch_id.pricelist_unit_purchase_id.id,line.product_id.id)
                        if not price :
                            raise osv.except_osv(('Perhatian !'), ("Product %s tidak ada dalam pricelist beli unit")%(line.product_id.name))  
                    elif self.division == 'Sparepart' :
                        if self.branch_id.pricelist_part_purchase_id.id:
                            price=self._get_price_unit(self.branch_id.pricelist_part_purchase_id.id,line.product_id.id)
                        if not price :
                            raise osv.except_osv(('Perhatian !'), ("Product %s tidak ada dalam pricelist beli part")%(line.product_id.name))  
                                                                
                    distribution_line_vals.append([0,False,
                                            {
                                              'product_id': line.product_id.id,
                                              'description': line.product_id.description,
                                              'requested_qty': line.fix_qty,
                                              'approved_qty':line.fix_qty,
                                              'qty': 0,
                                              'supply_qty': 0,
                                              'unit_price': price,
                                              }])
                    
        distribution_vals['distribution_line'] = distribution_line_vals
        distribution_id = self.env['wtc.stock.distribution'].sudo().create(distribution_vals)
           
            
            
    def _get_price_unit(self,cr,uid,pricelist,product_id):
        price_unit = self.pool.get('product.pricelist').price_get(cr,uid,[pricelist],product_id,1)[pricelist]
        return price_unit
    
    @api.multi
    def action_create_purchase_order(self):
        periode = self.env['wtc.p2p.periode'].sudo().search([
                                                      ('name','=',self.periode_id)
                                                      ])         
        start_date = periode.periode_start_date
        end_date = periode.periode_end_date
        product_pricelist = self.env['product.pricelist']
        dealer_branch_id = self.dealer_id.branch_id 
        picking = self.env['stock.picking.type'].search([
                                                        ('branch_id','=',dealer_branch_id.id),
                                                        ('code','=','incoming'),
                                                        ])[0]
        total_qty = 0.0   
        if self.type_name == 'Fix'   :                                          
            for line in self.purchase_line :
                  total_qty += line.fix_qty 
            if total_qty < 1 :
                    raise osv.except_osv(('Perhatian !'), ("Total Fix Qty harus lebih besar dari 0"))
        elif self.type_name == 'Additional'   :                                          
            for line in self.additional_line :
                  total_qty += line.fix_qty 
            if total_qty < 1 :
                    raise osv.except_osv(('Perhatian !'), ("Total Fix Qty harus lebih besar dari 0"))
                            
        if self.supplier_id :
            pricelist_id = False
            if self.division == 'Unit':
                pricelist_id = dealer_branch_id.pricelist_unit_purchase_id
            elif self.division == 'Sparepart':
                pricelist_id = dealer_branch_id.pricelist_part_purchase_id

            if not pricelist_id :
                raise osv.except_osv(('Perhatian !'), ("Pricelist beli cabang belum ada, silahkan ditambahkan di Branch."))
            order_vals = {
                          'branch_id': dealer_branch_id.id,
                          'origin':self.name,
                          'partner_id': self.supplier_id.id,
                          'division' : self.division,
                          'date_order': self.date,
                          'purchase_order_type_id': self.purchase_order_type_id.id,
                          'start_date': start_date,
                          'end_date': end_date,
                          'state': 'draft',
                          'picking_type_id' :picking.id,
                          'location_id' : picking.default_location_dest_id.id,
                          'pricelist_id':pricelist_id.id,
                          'minimum_planned_date' : end_date,
                          'related_location_id':picking.default_location_dest_id and picking.default_location_dest_id.id or False
#                           'payment_term_id': partner.property_supplier_payment_term.id or False,
#                         'fiscal_position': partner.property_account_position and partner.property_account_position.id or False,

                          }
            order_id = self.env['purchase.order'].sudo().create(order_vals)
            if self.type_name == 'Fix' :
                for line in self.purchase_line :
                    if line.fix_qty > 0 :
    
                        uom_id = False
                        product_uom_po_id = line.product_id.uom_po_id.id
                        if not uom_id:
                            uom_id = product_uom_po_id                
                        price_unit = False
                        price = price_unit
                        if price_unit is False or price_unit is None:
                            # - determine price_unit and taxes_id
                            if pricelist_id:
                                date_order_str = datetime.strptime(self.date, DEFAULT_SERVER_DATETIME_FORMAT).strftime(DEFAULT_SERVER_DATE_FORMAT)
                                price = pricelist_id.price_get(line.product_id.id, line.fix_qty or 1.0, self.supplier_id or False, context={'uom': uom_id, 'date': date_order_str})[pricelist_id.id]

                                print 'XXXXXXXXXXXXXXXXXXX>date_order_str ',date_order_str
                                print 'XXXXXXXXXXXXXXXXXXX>line.product_id.id ',line.product_id
                                print 'XXXXXXXXXXXXXXXXXXX>line.fix_qty ',line.fix_qty
                                print 'XXXXXXXXXXXXXXXXXXX>pricelist_id.price_get ',pricelist_id.price_get(line.product_id.id, line.fix_qty or 1.0, self.supplier_id or False, context={'uom': uom_id, 'date': date_order_str})
                            else:
                                price = line.product_id.standard_price   
                                print 'XXXXXXXXXXXXXXXXXXX>line.product_id.standard_price ',line.product_id.standard_price   
                        if not price :
                             raise osv.except_osv(('Perhatian !'), ("Product %s tidak ada dalam pricelist %s")%(line.product_id.name,pricelist_id.name))  
                           
                        order_line_vals = {
                                           
                                           'order_id': order_id.id,
                                           'categ_id': line.product_id.categ_id.id,
                                           'product_id': line.product_id.id,
                                           'product_qty': line.fix_qty,
                                           'price_unit': price,
                                           'product_uom' : uom_id,
                                           'price_unit_show':price,
                                           'name':line.product_id.description or '',
                                           'date_planned':end_date,
                                           'taxes_id':[(6,0,[line.product_id.supplier_taxes_id.id])]
                                           
                                           }
                        self.env['purchase.order.line'].sudo().create(order_line_vals)
            elif self.type_name == 'Additional' :
                for line in self.additional_line :
                    if line.fix_qty > 0 :
    
                        uom_id = False
                        product_uom_po_id = line.product_id.uom_po_id.id
                        if not uom_id:
                            uom_id = product_uom_po_id                
                        price_unit = False
                        price = price_unit
                        if price_unit is False or price_unit is None:
                            # - determine price_unit and taxes_id
                            if pricelist_id:
                                date_order_str = datetime.strptime(self.date, DEFAULT_SERVER_DATETIME_FORMAT).strftime(DEFAULT_SERVER_DATE_FORMAT)
                                price = pricelist_id.price_get(line.product_id.id, line.fix_qty or 1.0, self.supplier_id or False, context={'uom': uom_id, 'date': date_order_str})[pricelist_id.id]
                            else:
                                price = line.product_id.standard_price  
                        if not price :
                             raise osv.except_osv(('Perhatian !'), ("Product %s tidak ada dalam pricelist %s")%(line.product_id.name,pricelist_id.name))  
                                                            
                        order_line_vals = {
                                           
                                           'order_id': order_id.id,
                                           'categ_id': line.product_id.categ_id.id,
                                           'product_id': line.product_id.id,
                                           'product_qty': line.fix_qty,
                                           'price_unit': price,
                                           'product_uom' : uom_id,
                                           'price_unit_show':price,
                                           'name':line.product_id.description or '',
                                           'date_planned':end_date,
                                           'taxes_id':[(6,0,[line.product_id.supplier_taxes_id.id])]
                                           
                                           }
                        self.env['purchase.order.line'].sudo().create(order_line_vals)                
                
    @api.cr_uid_ids_context    
    def view_po(self,cr,uid,ids,context=None):  
        val = self.browse(cr, uid, ids, context={})[0]
        obj_po = self.pool.get('purchase.order')
        
        obj = obj_po.search(cr,uid,[
                                     ('origin','=',val.name),
                                     ])
        obj_hai = obj_po.browse(cr,uid,obj).id
        return {
            'name': 'Purchase Order',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': obj_hai
            }
        
    @api.cr_uid_ids_context    
    def view_sd(self,cr,uid,ids,context=None):  
        val = self.browse(cr, uid, ids, context={})[0]
        obj_po = self.pool.get('wtc.stock.distribution')
        
        obj = obj_po.search(cr,uid,[
                                     ('origin','=',val.name),
                                     ])
        obj_hai = obj_po.browse(cr,uid,obj).id
        return {
            'name': 'Stock Distribution',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.stock.distribution',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': obj_hai
            }
                        
    @api.multi
    def has_approved(self):
       
        if self.approval_state == 'a':
            return True
        
        return False
    
    @api.multi
    def has_rejected(self):
        
        if self.approval_state == 'r':
            self.write({'state':'draft'})
            return True
        return False
    
    @api.one
    def wkf_set_to_draft(self):
        self.write({'state':'draft','approval_state':'r'})
        
    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Form P2P Purchase Order tidak bisa didelete karena sudah di validate !"))
        return super(wtc_p2p_purchase_order, self).unlink(cr, uid, ids, context=context)  
    
    @api.multi
    def action_export_upo(self):
        self.env['eksport.upo'].eksport_upo(self)      
        
class wtc_p2p_purchase_order_line(models.Model):
    _name = 'wtc.p2p.purchase.order.line'
    _rec_name = 'product_id'
    
    purchase_id = fields.Many2one('wtc.p2p.purchase.order',string='Purchase')
    product_id = fields.Many2one('product.product',string='Product')
    product_id_show = fields.Many2one(related='product_id',string='Product')
    fix_qty = fields.Integer(string='Fix Qty')
    qty_available = fields.Integer(string='Qty Available')
    qty_available_show = fields.Integer(string='Qty Available(Prev)')
    tent1_qty = fields.Integer(string='Tent 1 Qty')
    tent2_qty = fields.Integer(string='Tent 2 Qty')
    tent1_prev_qty = fields.Integer(string='Tent 1 Qty(Prev)')
    tent1_prev_qty_show = fields.Integer(string='Tent 1 Qty(Prev)')
    tent2_prev_qty = fields.Integer(string='Tent 2 Qty(Prev)')
    tent2_prev_qty_show = fields.Integer(string='Tent 2 Qty(Prev)')
    active = fields.Boolean(default=True)  
    type = fields.Char(related="purchase_id.type_name",string="Type")     
    


    @api.onchange('product_id')
    def product_change(self):
        domain = {}       
        if self.purchase_id.type_name == 'Additional' :
            date = datetime.strptime(self.purchase_id.date,'%Y-%m-%d %H:%M:%S') 
            product_ids = []
            query = "select product_id from wtc_p2p_product where division='%s' and start_date<='%s' and end_date>='%s'" % (self.purchase_id.division, str(date.date()), str(date.date()))
            self._cr.execute(query)
            ress = self._cr.fetchall()
           
            for res in ress:
                product_ids.append(res[0])
                domain['product_id'] = [('id','in',product_ids)]
                
            if self.purchase_id.division=='Unit' and self.product_id:
                qty_in_picking = self.env['stock.picking']._get_qty_picking(self.purchase_id.supplier_id.branch_id.id,self.purchase_id.division,self.product_id.id)
                qty_in_lot = self.env['stock.picking']._get_qty_lot(self.purchase_id.supplier_id.branch_id.id,self.product_id.id)
                self.qty_available=qty_in_lot-qty_in_picking
                self.qty_available_show=qty_in_lot-qty_in_picking
            elif self.purchase_id.division=='Sparepart' and self.product_id:
                 qty_in_picking = self.env['stock.picking']._get_qty_picking(self.purchase_id.supplier_id.branch_id.id,self.purchase_id.division,self.product_id.id)
                 qty_in_quant = self.env['stock.picking']._get_qty_quant(self.purchase_id.supplier_id.branch_id.id,self.product_id.id)
                 self.qty_available=qty_in_quant-qty_in_picking
                 self.qty_available_show=qty_in_quant-qty_in_picking

        return {'domain':domain}



    @api.onchange('fix_qty')
    def fixqty_change(self):
        warning = {}
        if self.purchase_id.type_name == 'Fix' and self.fix_qty < 0 :
                        warning = {
                            'title': ('Perhatian !'),
                            'message': (("Nilai Fix Qty tidak boleh kurang dari nol")),
                        }                      
                        self.fix_qty = 0        
        else :
            if self.purchase_id.type_name == 'Fix' and self.fix_qty and self.tent1_prev_qty >= 0 :
                prev_qty = self.tent1_prev_qty
                fix_qty = self.fix_qty                        
            #cek P2P config based on branch or branch destination
                supplier_id = self.purchase_id.supplier_id
                    
                p2p_config = self.env['wtc.p2p.config'].search([
                                                                ('supplier_id','=',supplier_id.id)
                                                                ])
                if not p2p_config :
                    warning = {
                        'title': ('Perhatian !'),
                        'message': (("Mohon isi P2P Config untuk supplier %s terlebih dahulu !")%(supplier_id.name)),
                    }    
                if not warning :
                    config = p2p_config.tentative_1
                    ceil = math.ceil(prev_qty * (100.0 + config)/100)
                    floor = math.floor(prev_qty * (100.0 - config)/100)
                  
                    if fix_qty > ceil or fix_qty < floor :
                        warning = {
                            'title': ('Perhatian !'),
                            'message': (("Nilai Fix Qty tidak boleh melebihi batas min/max %s%s !")%(config,'%')),
                        }                      
                        self.fix_qty = self.tent1_prev_qty
        return {'warning':warning}
           


    @api.onchange('tent1_qty')
    def tentqty_change(self):
        warning = {}
        if self.purchase_id.type_name == 'Fix' and self.tent1_qty < 0 :
                        warning = {
                            'title': ('Perhatian !'),
                            'message': (("Nilai Tentative 1 Qty tidak boleh kurang dari nol")),
                        }                      
                        self.tent1_qty = 0        
        else :        
            if self.purchase_id.type_name == 'Fix' and self.tent1_qty and self.tent2_prev_qty >= 0 :
                prev_qty = self.tent2_prev_qty
                fix_qty = self.tent1_qty
   
            #cek P2P config based on branch or branch destination
                supplier_id = self.purchase_id.supplier_id
                    
                p2p_config = self.env['wtc.p2p.config'].search([
                                                                ('supplier_id','=',supplier_id.id)
                                                                ])
                if not p2p_config :
                    warning = {
                        'title': ('Perhatian !'),
                        'message': (("Mohon isi P2P Config untuk %s terlebih dahulu !")%(branch_id.name)),
                    }    
                if not warning :
                    config = p2p_config.tentative_2
                    ceil = math.ceil(prev_qty * (100.0 + config)/100)
                    floor = math.floor(prev_qty * (100.0 - config)/100)
    
                    if fix_qty > ceil or fix_qty < floor :
                        warning = {
                            'title': ('Perhatian !'),
                            'message': (("Nilai Fix Qty tidak boleh melebihi batas min/max %s%s !")%(config,'%')),
                        }                      
                        self.tent1_qty = self.tent2_prev_qty
        return {'warning':warning}                          
            
    @api.onchange('tent2_qty')
    def tent2qty_change(self):  
        warning = {}
        if self.purchase_id.type_name == 'Fix' and self.tent2_qty < 0 :
                        warning = {
                            'title': ('Perhatian !'),
                            'message': (("Nilai Tentative 2 Qty tidak boleh kurang dari nol")),
                        }                      
                        self.tent2_qty = 0                        
        return {'warning':warning} 
