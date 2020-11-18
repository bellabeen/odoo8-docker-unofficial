from openerp import models, fields, api, _, SUPERUSER_ID
from openerp.osv import osv
import time
import openerp.addons.decimal_precision as dp
from datetime import datetime

class wtc_mutation_request(models.Model):
    _name = "wtc.mutation.request"
    _description = "Mutation Request"
    _order = 'date desc'
    
    def _check_branch(self, cr, uid, ids, context=None):
        mutation = self.browse(cr, uid, ids, context=context)[0]
        if mutation.branch_id.id == int(mutation.branch_sender_id) :
            return False
        return True
    
    @api.one
    @api.depends('request_line.sub_total')
    def _compute_amount(self):
        self.amount_total = 0
        val_total = 0
        for x in self.request_line :
            val_total += x.sub_total
        self.amount_total = val_total
    
    @api.model
    def _branch_sender_get(self):
        obj_branch = self.env['wtc.branch'].sudo().search([('branch_type','in',['DL','MD'])], order='name')
        return [(str(branch.id),branch.name) for branch in obj_branch]
    
    @api.model
    def _get_picking_ids(self):
        ids_sd = []
        mo_name = []
        picking_ids = []
        self.picking_ids = False
        for sd in self.env['wtc.stock.distribution'].sudo().search([('request_id','=',self.id)]):
            ids_sd.append(sd.id)
        for mo in self.env['wtc.mutation.order'].sudo().search([('distribution_id','in',ids_sd)]):
            mo_name.append(str(mo.name))
        for picking in self.env['stock.picking'].sudo().search([
                                                                ('origin','in',mo_name),
                                                                ('picking_type_code','=','interbranch_in'),
                                                                ]):
            picking_ids.append(picking.id)
        if picking_ids :
            self.picking_ids = True
    
    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()
        
    name = fields.Char('Mutation Request')
    state = fields.Selection([
                              ('draft','Draft'),
                              ('waiting_for_approval','Waiting For Approval'),
                              ('approved','Approved'),
                              ('confirm','Requested'),
                              ('open','Open'),
                              ('done','Done'),
                              ('cancel','Cancelled'),
                              ('reject','Rejected'),
                              ], 'State', default='draft')
    date = fields.Date('Date')
    branch_id = fields.Many2one('wtc.branch', 'Branch Requester')
    branch_sender_id = fields.Selection('_branch_sender_get', string='Branch Sender')
    division = fields.Selection([
                                 ('Unit','Unit'),
                                 ('Sparepart','Sparepart'),
                                 ('Umum','Umum')
                                 ], 'Division')
    type_id = fields.Many2one('wtc.purchase.order.type', 'Type', required=True)
    user_id = fields.Many2one('res.users', 'Responsible')
    description = fields.Char('Description')
    request_line = fields.One2many('wtc.mutation.request.line', 'request_id', 'Mutation Line')
    amount_total = fields.Float(string='Total', digits=dp.get_precision('Account'),
                                store=True, compute='_compute_amount')
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    rel_date = fields.Date(related='date', string="Date")
    rel_start_date = fields.Date(related='start_date', string="Start Date")
    rel_end_date = fields.Date(related='end_date', string="End Date")
    picking_ids = fields.Boolean(compute='_get_picking_ids', string="Picking Ids", method=True)
    
    _constraints = [
                    (_check_branch, 'Branch Requester dan Branch Sender tidak boleh sama !', ['branch_id', 'branch_sender_id']),
                    ]
    
    _defaults={
               'user_id': lambda obj, cr, uid, context:uid,
               'date' : _get_default_date,
               }
    
    def create(self, cr, uid, vals, context=None):
        if not vals['request_line'] :
            raise osv.except_osv(('Tidak bisa disimpan !'), ("Silahkan isi detil mutasi terlebih dahulu"))
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'MR')
        vals['rel_date'] = self._get_default_date(cr,uid)
        return super(wtc_mutation_request, self).create(cr, uid, vals, context=context)
    
    @api.multi
    def button_dummy(self, context=None):
        return True
    
    @api.onchange('division')
    def division_change(self):
        if self.division :
            self.request_line = False
    
    @api.onchange('start_date','end_date')
    def date_change(self):
        if self.start_date and self.end_date :
            if self.start_date > self.end_date :
                self.start_date = self.end_date = False
                return {'warning':{'title':'Perhatian !','message':'Start Date melebihi End Date'}}
    
    @api.multi
    def wkf_action_cancel(self):
        self.write({'state': 'cancel','cancel_uid':self._uid,'cancel_date':datetime.now()})
        distribution_id = self.env['wtc.stock.distribution'].search([('request_id','=',self.id)])
        distribution_id.write({'state': 'cancel'})
    
    def action_distribution_create(self):
        obj_branch = self.env['wtc.branch'].sudo().search([('id','=',int(self.branch_sender_id))])
        distribution_vals = {
                             'branch_id': obj_branch.id,
                             'branch_requester_id': self.branch_id.id,
                             'division' : self.division,
                             'user_id': self.user_id.id,
                             'request_id': self.id,
                             'type_id': self.type_id.id,
                             'date': self.date,
                             'start_date': self.start_date,
                             'end_date': self.end_date,
                             'description': self.description,
                             'state': 'confirm',
                             }
        distribution_id = self.env['wtc.stock.distribution'].sudo().create(distribution_vals)
        for line in self.request_line :
            distribution_line_vals = {
                                      'distribution_id': distribution_id.id,
                                      'product_id': line.product_id.id,
                                      'description': line.description,
                                      'requested_qty': line.requested_qty,
                                      'approved_qty': line.requested_qty,
                                      'qty': 0,
                                      'supply_qty': 0,
                                      'unit_price': line.unit_price,
                                      }
            self.env['wtc.stock.distribution.line'].sudo().create(distribution_line_vals)
            
    @api.model
    def wkf_confirm_order(self):
        self.sudo().action_distribution_create()
        self.write({'state': 'confirm'})
        
    @api.model
    def is_done(self):
        obj_sd = self.env['wtc.stock.distribution'].search([('request_id','=',self.id)])
        if obj_sd.state == 'done' :
            self.write({'state':'done'})
        return True
    
    @api.onchange('type_id')
    def type_id_change(self):
        type = self.env['wtc.purchase.order.type'].browse(self.type_id.id)
        self.start_date = False
        self.end_date = False
        if type:
            self.start_date = type.get_date(type.date_start)
            self.end_date = type.get_date(type.date_end)
    
    def unlink(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids, context={})[0]
        if val.state != 'draft':
            raise osv.except_osv(('Invalid action !'), ('Cannot delete a Mutation Request which is in state \'%s\'!') % (val.state))
        return super(wtc_mutation_request, self).unlink(cr, uid, ids, context=context)
    
    def view_picking(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        mod_obj = self.pool.get('ir.model.data')
        dummy, action_id = tuple(mod_obj.get_object_reference(cr, uid, 'stock', 'action_picking_tree'))
        action = self.pool.get('ir.actions.act_window').read(cr, uid, action_id, context=context)
        ids_sd = []
        mo_name = []
        picking_ids = []
        obj_me = self.browse(cr, uid, ids, context=context)
        for sd in self.pool.get('wtc.stock.distribution').search(cr, SUPERUSER_ID, [('request_id','=',obj_me.id)]):
            ids_sd.append(sd)
        for mo in self.pool.get('wtc.mutation.order').search(cr, SUPERUSER_ID, [('distribution_id','in',ids_sd)]):
            mo_id = self.pool.get('wtc.mutation.order').browse(cr, SUPERUSER_ID, mo)
            mo_name.append(str(mo_id.name))
        for picking in self.pool.get('stock.picking').search(cr, SUPERUSER_ID, [
                                                                                ('origin','in',mo_name),
                                                                                ('picking_type_code','=','interbranch_in'),
                                                                                ]):
            picking_ids.append(picking)
        if not picking_ids :
            raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan stock intransit untuk Mutation Request '%s'" %obj_me.name))
        action['context'] = {}
        if len(picking_ids) > 1 :
            action['domain'] = "[('id','in',[" + ','.join(map(str, picking_ids)) + "])]"
        else:
            res = mod_obj.get_object_reference(cr, uid, 'stock', 'view_picking_form')
            action['views'] = [(res and res[1] or False, 'form')]
            action['res_id'] = picking_ids and picking_ids[0] or False 
        return action
    
    """
    update wtc_mutation_request
    set branch_sender_id = (select id from wtc_branch where wtc_branch.code = wtc_mutation_request.branch_sender_id)
    """
    
class wtc_mutation_request_line(models.Model):
    _name = "wtc.mutation.request.line"
    
    @api.one
    @api.depends('unit_price', 'requested_qty')
    def _compute_price(self):
        qty = self.requested_qty
        price = self.unit_price
        self.sub_total = qty * price
    
    request_id = fields.Many2one('wtc.mutation.request', 'Request')
    product_id = fields.Many2one('product.product', 'Product')
    description = fields.Text('Description')
    requested_qty = fields.Float('Requested Qty', digits=(10,0))
    approved_qty = fields.Float('Approved Qty', digits=(10,0))
    supply_qty = fields.Float('Supply Qty', digits=(10,0))
    unit_price = fields.Float('Unit Price')
    unit_price_show = fields.Float(related='unit_price', string='Unit Price')
    sub_total = fields.Float(string='Subtotal', digits=dp.get_precision('Account'),
                             store=True, readonly=True, compute='_compute_price')
    
    _sql_constraints = [
                        ('unique_product_id', 'unique(request_id,product_id)', 'Tidak boleh ada product yg sama dalam satu mutasi')
                        ]
    
    def product_id_change(self, cr, uid, ids, product_id, branch_id, branch_sender_id, division, context=None):
        value = {'unit_price':False}
        domain = {}
        if not branch_id or not branch_sender_id or not division :
            return {'warning':{'title':'Perhatian !','message':'Sebelum menambah detil,\n harap isi branch dan division terlebih dahulu'}}
        categ_ids = self.pool.get('product.category').get_child_ids(cr, uid, ids, division)
        domain['product_id'] = [('categ_id','in',categ_ids)]
        if product_id :
            branch = self.pool.get('wtc.branch').browse(cr, SUPERUSER_ID, int(branch_sender_id))
            obj_product = self.pool.get('product.product').browse(cr, uid, product_id)
            pricelist = branch.pricelist_unit_purchase_id.id
            value['description'] = obj_product.name_get().pop()[1]
            value['requested_qty'] = 1
            value['approved_qty'] = 0
            if obj_product.categ_id.isParentName('Unit') :
                price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist], product_id, 1,0)[pricelist]
                value['unit_price'] = price
            else :
                value['unit_price'] = obj_product.lst_price
        return {'value':value, 'domain':domain}
    
    @api.onchange('requested_qty','approved_qty')
    def quantity_change(self):
        if self.requested_qty < 0 :
            self.requested_qty = False
            return {'warning':{'title':'Perhatian !','message':'Request Quantity tidak boleh kurang dari nol'}}
        if self.approved_qty <> 0 :
            self.approved_qty = 0
            return {'warning':{'title':'Perhatian !','message':'Approved Quantity tidak boleh dirubah'}}
        