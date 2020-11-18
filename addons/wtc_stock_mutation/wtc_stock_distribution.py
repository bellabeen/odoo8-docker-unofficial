from openerp import models, fields, api
from openerp.osv import osv
import time
import openerp.addons.decimal_precision as dp
from openerp import models,fields, exceptions, api, _
from datetime import datetime

class wtc_stock_distribution(models.Model):
    _name = "wtc.stock.distribution"
    _description = "Stock Distribution"
    _order = 'date desc'
    
    @api.one
    @api.depends('distribution_line.sub_total')
    def _compute_amount(self):
        self.amount_total = 0
        val_total = 0
        for x in self.distribution_line :
            val_total += x.sub_total
        self.amount_total = val_total
        
    @api.one
    @api.depends('distribution_line.approved_qty','distribution_line.qty')
    def _compute_qty(self):
        self.func_qty = 0
        approved_qty = 0
        qty = 0
        for x in self.distribution_line :
            approved_qty += x.approved_qty
            qty += x.qty
        self.func_qty = approved_qty - qty
    
    def _is_effective_date(self):
        condition = False
        if (not self.start_date and not self.end_date) or (self.start_date and self.end_date and self.start_date <= self._get_default_date().strftime('%Y-%m-%d') and self.end_date >= self._get_default_date().strftime('%Y-%m-%d')) :
            condition = True
        self.is_effective_date = condition
    
    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()
        
    name = fields.Char('Stock Distribution')
    state = fields.Selection([
                              ('confirm','Requested'),
                              ('waiting_for_approval','Waiting For Approval'),
                              ('approved','Approved'),
                              ('open','Open'),
                              ('done','Done'),
                              ('cancel','Cancelled'),
                              ('reject','Rejected'),
                              ('closed','Closed'),
                              ], 'State')
    date = fields.Date('Date',default=_get_default_date)
    branch_id = fields.Many2one('wtc.branch', 'Branch Sender')
    branch_requester_id = fields.Many2one('wtc.branch', 'Branch Requester')
    division = fields.Selection([
                                 ('Unit','Unit'),
                                 ('Sparepart','Sparepart'),
                                 ('Umum','Umum')
                                 ], 'Division')
    type_id = fields.Many2one('wtc.purchase.order.type', 'Type')
    user_id = fields.Many2one('res.users', 'Responsible')
    description = fields.Text('Description')
    distribution_line = fields.One2many('wtc.stock.distribution.line', 'distribution_id', 'Mutation Line')
    amount_total = fields.Float(string='Total', digits=dp.get_precision('Account'), store=True, compute='_compute_amount')
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    request_id = fields.Many2one('wtc.mutation.request', 'Mutation Request', ondelete='restrict')
    func_qty = fields.Float(string='Sisa Qty', digits=dp.get_precision('Account'), store=True, compute='_compute_qty')
    rel_branch_type = fields.Selection(string='Branch Type', related='branch_id.branch_type')
    order_ids = fields.One2many('wtc.mutation.order', 'distribution_id', string='Order ids')
    is_effective_date = fields.Boolean(compute='_is_effective_date', string="Is Effective Date", method=True)
    confirm_uid = fields.Many2one('res.users', string="Confirmed by")
    confirm_date = fields.Datetime('Confirmed on')
    cancel_uid = fields.Many2one('res.users', string="Rejected by")
    cancel_date = fields.Datetime('Rejected on') 
    origin = fields.Char('Origin')
    dealer_id = fields.Many2one('res.partner',string="Dealer Requester")
       
    def create(self, cr, uid, vals, context=None):
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'SD')
        vals['date'] = self._get_default_date(cr,uid)
        return super(wtc_stock_distribution, self).create(cr, uid, vals, context=context)
    
    @api.multi
    def action_mutation_order_create(self):
        self.date = self._get_default_date()
        order_draft = self.env['wtc.mutation.order'].search([
                                                             ('distribution_id','=',self.id),
                                                             ('state','=','draft')
                                                             ])
        if self.state == 'done' or self.func_qty == 0 or order_draft :
            return self.view_order()
        
        order_vals = {
                      'branch_id': self.branch_id.id,
                      'branch_requester_id': self.branch_requester_id.id,
                      'division' : self.division,
                      'user_id': self.user_id.id,
                      'distribution_id': self.id,
                      'date': self.date,
                      'start_date': self.start_date,
                      'end_date': self.end_date,
                      'description': self.description,
                      'dms_po_name': self.dms_po_name,
                      'state': 'draft',
                      }
        order_id = self.env['wtc.mutation.order'].create(order_vals)
        obj_mutation = self.env['wtc.mutation.order'].browse(order_id.id)
        obj_picking = self.env['stock.picking']
        for line in self.distribution_line :
            if (line.approved_qty - line.qty) > 0 :
                qty_available = 0
                if self.division == 'Unit':
                    qty_available = obj_mutation.get_stock_available(line.product_id.id, self.branch_id.id)
                elif self.division == 'Sparepart':
                    qty_available = obj_picking._get_qty_quant(self.branch_id.id, line.product_id.id) - (obj_picking._get_qty_picking(self.branch_id.id, self.division, line.product_id.id) + obj_picking._get_qty_rfa_approved(self.branch_id.id, self.division, line.product_id.id))
                order_line_vals = {
                    'order_id': order_id.id,
                    'product_id': line.product_id.id,
                    'description': line.description,
                    'qty': line.approved_qty - line.qty,
                    'unit_price': line.unit_price,
                    'qty_available': qty_available if qty_available > 0 else 0
                }
                self.env['wtc.mutation.order.line'].create(order_line_vals)
        return self.view_order()
    
    def _get_price_unit(self,cr,uid,pricelist,product_id):
        price_unit = self.pool.get('product.pricelist').price_get(cr,uid,[pricelist],product_id,1)[pricelist]
        return price_unit
    
    @api.multi
    def _get_warehouse(self,branch_id):
        warehouse_ids = self.env['stock.warehouse'].search([('branch_id', '=', branch_id)])
        if not warehouse_ids:
            raise exceptions.ValidationError(('Tidak ditemukan warehouse default cabang'))
        return warehouse_ids
    
    @api.multi
    def action_sale_order_create(self):
        order_draft = self.env['sale.order'].search([
            ('distribution_id','=',self.id),
            ('state','in', ('draft','waiting_for_approval','approved'))
        ])
        if self.state == 'done' or self.func_qty == 0 or order_draft :
            return self.view_order()

        total_inv = 0
        total_inv = self.env['sale.order']._invoice_total(self.dealer_id.id,self.division)        
        pcc_id = self.env['pricelist.config.cabang'].search([
          ('branch_id','=',self.branch_id.id),
          ('partner_id','=',self.dealer_id.id),
          ('division','=',self.division)],limit=1)

        if self.division=='Unit':
            if pcc_id:
              pricelist = pcc_id.md_pricelist_id.id 
            else:
              pricelist = self.branch_id.pricelist_unit_sales_id.id or self.dealer_id.property_product_pricelist.id
        elif self.division=='Sparepart':
            if pcc_id:
              pricelist = pcc_id.md_pricelist_id.id
            else:
              pricelist = self.branch_id.pricelist_part_sales_id.id or self.dealer_id.property_product_pricelist.id
        
        sale_order = {
            'branch_id': self.branch_id.id,
            'division': self.division,
            'user_id': self.user_id.id,
            'date_order': self.date,
            'partner_id': self.dealer_id.id,
            'state': 'draft',
            'warehouse_id': self._get_warehouse(self.branch_id.id)['id'],
            'payment_term': self.dealer_id.property_payment_term.id,
            'distribution_id': self.id,
            'total_invoiced': total_inv,
            'pricelist_id': pricelist,
            'dms_po_name': self.dms_po_name,
        }
        
        # if self.division=='Unit':
        #     pricelist = self.branch_id.pricelist_unit_sales_id.id or self.dealer_id.property_product_pricelist.id
        # elif self.division=='Sparepart':
        #     pricelist = self.branch_id.pricelist_part_sales_id.id or self.dealer_id.property_product_pricelist.id
            
        sale_order_line = []
        obj_sale_order = self.env['sale.order']
        obj_picking = self.env['stock.picking']
        for line in self.distribution_line:
            if (line.approved_qty - line.qty) > 0 :
                qty_available = 0
                if self.division == 'Unit':
                    qty_available = obj_sale_order.get_stock_available(line.product_id.id, self.branch_id.id)
                elif self.division == 'Sparepart':
                    qty_available = obj_picking._get_qty_quant(self.branch_id.id, line.product_id.id) - (obj_picking._get_qty_picking(self.branch_id.id, self.division, line.product_id.id) + obj_picking._get_qty_rfa_approved(self.branch_id.id, self.division, line.product_id.id))
                sale_order_line.append([0,False,{
                    'categ_id': line.product_id.categ_id.id,
                    'product_id': line.product_id.id,
                    'description': line.product_id.name,
                    'product_uom_qty': line.approved_qty - line.qty,
                    'price_unit': self._get_price_unit(pricelist, line.product_id.id),
                    'tax_id': [(6,0,[x.id for x in line.product_id.taxes_id])],
                    'qty_available': qty_available if qty_available > 0 else 0
                }])
        sale_order['order_line'] = sale_order_line
        create_so = self.env['sale.order'].create(sale_order)
        return self.view_order()
    
#     @api.multi
#     def action_order_create(self):
#         if self.branch_id.partner_id.branch_id and self.branch_requester_id :
#             self.action_mutation_order_create()
#         else :
#             self.action_sale_order_create()
    
    @api.multi
    def confirm_qty(self):
        if self.state == 'approved' :
            tot_approve_qty = 0
            for x in self.distribution_line :
                tot_approve_qty += x.approved_qty
            if tot_approve_qty > 0 :
                qty = {}
                for x in self.distribution_line :
                    qty[x.product_id] = qty.get(x.product_id,0) + x.approved_qty
                for x in self.sudo().request_id.request_line :
                    qty[x.product_id] = qty.get(x.product_id,0) + x.approved_qty
                    x.write({'approved_qty':qty[x.product_id]})
                self.write({'state': 'open','confirm_uid':self._uid,'confirm_date':datetime.now(),'date':self._get_default_date()})
                self.sudo().request_id.write({'state': 'open'})
            else :
                self.reject_request()
    
    @api.multi
    def is_approved_qty_zero(self):
        if self.state == 'confirm' :
            tot_approve_qty = 0
            for x in self.distribution_line :
                tot_approve_qty += x.approved_qty
            if tot_approve_qty < 1 :
                self.reject_request()
    
    @api.multi
    def reject_request(self):
        if self.state == 'confirm' :
            self.write({'state': 'reject','cancel_uid':self._uid,'cancel_date':datetime.now()})
            self.sudo().request_id.write({'state': 'reject'})
        
    @api.model
    def is_done(self):
        approved_qty = 0
        supply_qty = 0
        for x in self.distribution_line :
            approved_qty += x.approved_qty
            supply_qty += x.supply_qty
        if approved_qty - supply_qty == 0 :
            self.write({'state':'done'})
        if self.state == 'closed' :
            if not self.order_ids :
                self.write({'state':'done'})
            elif all(x.state in ('done','cancelled') for x in self.order_ids) :
                self.write({'state':'done'})
        if self.sudo().request_id :
            self.sudo().request_id.is_done()
        return True
    
    def view_order(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        distribution_id = self.browse(cr, uid, ids, context=context)
        if not distribution_id.branch_requester_id :
            mod_obj = self.pool.get('ir.model.data')
            dummy, action_id = tuple(mod_obj.get_object_reference(cr, uid, 'sale', 'action_orders'))
            action = self.pool.get('ir.actions.act_window').read(cr, uid, action_id, context=context)
            so_ids = []
            obj_me = self.browse(cr, uid, ids, context=context)
            for so in self.pool.get('sale.order').search(cr, uid, [('distribution_id','=',obj_me.id)]):
                so_ids.append(so)
            action['context'] = {}
            if len(so_ids) > 1:
                action['domain'] = "[('id','in',[" + ','.join(map(str, so_ids)) + "])]"
            else:
                res = mod_obj.get_object_reference(cr, uid, 'wtc_sale_order', 'wtc_sale_order_form_view')
                action['views'] = [(res and res[1] or False, 'form')]
                action['res_id'] = so_ids and so_ids[0] or False 
            return action
        else :
            mod_obj = self.pool.get('ir.model.data')
            dummy, action_id = tuple(mod_obj.get_object_reference(cr, uid, 'wtc_stock_mutation', 'wtc_mutation_order_action'))
            action = self.pool.get('ir.actions.act_window').read(cr, uid, action_id, context=context)
            mo_ids = []
            obj_me = self.browse(cr, uid, ids, context=context)
            for mo in self.pool.get('wtc.mutation.order').search(cr, uid, [('distribution_id','=',obj_me.id)]):
                mo_ids.append(mo)
            action['context'] = {}
            if len(mo_ids) > 1:
                action['domain'] = "[('id','in',[" + ','.join(map(str, mo_ids)) + "])]"
            else:
                res = mod_obj.get_object_reference(cr, uid, 'wtc_stock_mutation', 'wtc_mutation_order_form_view')
                action['views'] = [(res and res[1] or False, 'form')]
                action['res_id'] = mo_ids and mo_ids[0] or False 
            return action
    
    @api.multi
    def close_order(self):
        if self.rel_branch_type == 'DL' :
            self.write({'state':'closed'})
            for x in self.order_ids :
                if x.state == 'draft' :
                    x.write({'state':'cancelled'})
            self.is_done()
            
    def unlink(self, cr, uid, ids, context=None):
        raise osv.except_osv(('Invalid action !'), ('Cannot delete Stock Distribution'))
        return super(wtc_stock_distribution, self).unlink(cr, uid, ids, context=context)
    
class wtc_stock_distribution_line(models.Model):
    _name = "wtc.stock.distribution.line"
    
    @api.one
    @api.depends('unit_price', 'approved_qty')
    def _compute_price(self):
        qty = self.approved_qty
        price = self.unit_price
        self.sub_total = qty * price
    
    distribution_id = fields.Many2one('wtc.stock.distribution', 'Mutation')
    product_id = fields.Many2one('product.product', 'Product')
    description = fields.Text('Description')
    requested_qty = fields.Float('Requested Qty', digits=(10,0))
    approved_qty = fields.Float('Approved Qty', digits=(10,0))
    qty = fields.Float('Qty', digits=(10,0))
    supply_qty = fields.Float('Supply Qty', digits=(10,0))
    unit_price = fields.Float('Unit Price')
    unit_price_show = fields.Float(related='unit_price', string='Unit Price')
    sub_total = fields.Float(string='Subtotal', digits=dp.get_precision('Account'),
                             store=True, readonly=True, compute='_compute_price')
    rel_state = fields.Selection(related='distribution_id.state', string='State')
    
    @api.onchange('approved_qty')
    def quantity_change(self):
        if self.approved_qty < 0 :
            self.approved_qty = self.requested_qty
            return {'warning':{'title':'Perhatian !','message':'Quantity tidak boleh kurang dari nol'}}
        elif self.approved_qty > self.requested_qty :
            self.approved_qty = self.requested_qty
            return {'warning':{'title':'Perhatian !','message':'Quantity tidak boleh melebihi permintaan'}}
        else :
            self.approved_qty = self.approved_qty
            