# -*- coding: utf-8 -*-
from openerp import models, fields, api
from datetime import datetime
from openerp.osv import osv
import openerp.addons.decimal_precision as dp
from openerp import workflow


class TedsTopup(models.Model):
    _inherit = 'wtc.p2p.purchase.order'

    purchase_order_type_id = fields.Many2one('wtc.purchase.order.type', 'Type', required=True,
        domain="[('category','=',division), '|', ('name','=','Fix'), '|', ('name','=','Additional'), ('name','=','Topup')]",)


    @api.onchange('purchase_order_type_id')
    def get_type(self):
        self.type_name=self.purchase_order_type_id.name
        # print ">>>type_name", self.type_name

    """
        Jika P2P tipe Topup dipilih:
        1. Ambil start_date dan end_date milik periode_id di wtc.p2p.periode
        2. Ambil id dari stock.ideal, milik dealer_id dengan effective_start_date >= start_date 
        dan effective_end_date <= end_date di ideal.stock
        3. Search product dan min_qty dari stock.ideal.line, menggunakan id stock ideal
        yang diperoleh di poin 2
        4. isi field di wtc.p2p.purchase.order dengan nilai yang didapat di poin 3
    """
    
    
    
    def _get_qty_picking(self,cr,uid,branch_id,division,product_id,type):
        qty_picking_product = 0
        obj_picking = self.pool.get('stock.picking')
        obj_move = self.pool.get('stock.move')
        picking_type = ''
        if type == 'in' :
            picking_type = self.pool.get('stock.picking.type').search(cr,uid,[('branch_id','=',branch_id),('code','in',['incoming','interbranch_in'])])
        elif type == 'out' :
            picking_type = self.pool.get('stock.picking.type').search(cr,uid,[('code','in',['outgoing','interbranch_out'])])
            
        if picking_type:
            if type == 'in' :
                picking_ids = obj_picking.search(cr,uid,
                                                [('branch_id','=',branch_id),
                                                 ('division','=',division),
                                                 ('picking_type_id','in',picking_type),
                                                 ('state','not in',('draft','cancel','done'))
                                                 ])
                if picking_ids:
                    move_ids = obj_move.search(cr,uid,[('picking_id','in',picking_ids),('product_id','=',product_id)])
                    if move_ids:
                        for move in obj_move.browse(cr,uid,move_ids):
                            qty_picking_product+=move.product_uom_qty
            elif type == 'out' : 
                picking_ids = obj_picking.search(cr,uid,
                                                [('partner_id','=',branch_id),
                                                 ('division','=',division),
                                                 ('picking_type_id','in',picking_type),
                                                 ('state','not in',('draft','cancel','done'))
                                                 ])
                if picking_ids:
                    move_ids = obj_move.search(cr,uid,[('picking_id','in',picking_ids),('product_id','=',product_id)])
                    if move_ids:
                        for move in obj_move.browse(cr,uid,move_ids):
                            qty_picking_product+=move.product_uom_qty
        return qty_picking_product
    
   
    def get_qty_avb(self, cr, uid, ids,branch_id,product_id):
        
        query="""
               SELECT
                    q.product_id, l.branch_id, q.reservation_id, q.consolidated_date, sum(q.qty)
                FROM
                    stock_quant q
                JOIN
                    stock_location l on q.location_id = l.id
                WHERE
                    q.product_id = %s and l.branch_id = %s and l.usage in ('internal','transit')
                GROUP BY
                    q.product_id, l.branch_id, q.reservation_id, q.consolidated_date
        
                """ %(product_id,branch_id)
        cr.execute (query)
        ress = cr.fetchall()
        
        part_intransit = 0
        part_available = 0
        part_reserved = 0 
        for x in ress :
            if x[2] <> None and x[3] <> None :
                part_reserved += x[4]
            elif x[2] == None and x[3] <> None :
                part_available += x[4]
            elif x[3] == None :
                part_intransit += x[4]
        return part_available
        
    @api.multi
    def generate_line(self):
        self.ensure_one()
        if self.type_name == 'Topup' and self.division == 'Sparepart':
            p2p_start_date = self.env['wtc.p2p.periode'].search([
                ('name', '=', self.periode_id)]).start_date
            # print ">>>p2p_start_date", p2p_start_date
            p2p_end_date = self.env['wtc.p2p.periode'].search([
                ('name', '=', self.periode_id)]).end_date
            # print ">>>p2p_end_date", p2p_end_date
            # print ">>>branch_id", self.branch_id.id

            stock_ideal_id = self.env['stock.ideal'].search(
                [('branch_id', '=', self.branch_id.id),
                ('effective_start_date', '>=', p2p_start_date),
                ('effective_end_date', '<=', p2p_end_date)])
            # print ">>>stock_ideal_id", stock_ideal_id

            if stock_ideal_id:
                vals = []
                for sp in stock_ideal_id.stock_ideal_line :
                    qty_available_md,qty_stock_cabang, qty_in_picking_in_cabang,qty_in_picking_out_cabang, qty_in_picking_out_cabang_partner, fix_qty = [0,0, 0, 0, 0,0]

                    qty_stock_cabang=self.sudo().get_qty_avb(self.dealer_id.branch_id.id, sp.product_id.id)
                    qty_in_picking_in_cabang = self.sudo()._get_qty_picking(self.dealer_id.branch_id.id, self.division, sp.product_id.id,'in')
                    qty_in_picking_out_cabang = self.env['stock.picking'].sudo()._get_qty_picking(self.dealer_id.branch_id.id, self.division, sp.product_id.id)
                    qty_in_picking_out_cabang_partner = self.sudo()._get_qty_picking(self.dealer_id.id, self.division, sp.product_id.id,'out')
                   
                    fix_qty = sp.min_qty-qty_stock_cabang-qty_in_picking_in_cabang-qty_in_picking_out_cabang_partner
                    qty_available_md=self.sudo().get_qty_avb(self.supplier_id.branch_id.id, sp.product_id.id)
                  
                    #min-stock avb cabng-     posting-stock picking keluar ke cabang tersebut yang belum posting
                    if fix_qty > 0 :
                        sp_vals = [0,0,{
                            'product_id': sp.product_id.id,
                            'purchase_id': self.id,
                            'qty_available': qty_available_md,
                            'qty_available_show': qty_available_md,
                            'fix_qty': fix_qty,
                        }]
                        vals.append(sp_vals)
                if vals:
                    self.write({'additional_line':vals})
        else:
            super(TedsTopup, self).generate_line()

    def write(self, cr, uid, ids, vals, context=None):
        purchase_id = self.browse(cr, uid, ids, context=context)
        if purchase_id.type_name == 'Fix' :
            vals.get('purchase_line', []).sort(reverse=True)
            vals.pop('additional_line',None)
        elif purchase_id.type_name == 'Additional' or purchase_id.type_name == 'Topup':
            vals.get('additional_line', []).sort(reverse=True)
            vals.pop('purchase_line',None)
        return super(TedsTopup, self).write(cr, uid, ids, vals, context=context)

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
        price = False
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
        elif self.type_name == 'Additional' or self.type_name == 'Topup' :
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
           
            
            
            
#         sdfd
# class TedsTopupLine(models.Model):
#     _inherit = 'wtc.p2p.purchase.order.line'