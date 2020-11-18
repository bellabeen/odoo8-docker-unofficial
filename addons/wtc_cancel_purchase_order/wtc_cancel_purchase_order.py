from openerp import models, fields, api
from datetime import datetime
from openerp.osv import osv

class purchase_order_cancel(models.Model):
    _name = "purchase.order.cancel"
    _description = "purchase Order Cancel"
    
    @api.multi
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date()
    
    @api.model
    def _get_default_date_model(self):
        return self.env['wtc.branch'].get_default_date_model()
    
    name = fields.Char('Name')
    state = fields.Selection([
        ('draft','Draft'),
        ('waiting_for_approval','Waiting For Approval'),
        ('approved','Approved'),
        ('confirmed','Confirmed'),
        ], 'State', default='draft')
    branch_id = fields.Many2one('wtc.branch', 'Branch')
    purchase_order_id = fields.Many2one('purchase.order', 'Purchase Order')
    division = fields.Selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum')], 'Division')
    date = fields.Date('Date',default=_get_default_date)
    confirm_uid = fields.Many2one('res.users', string="Confirmed by")
    confirm_date = fields.Datetime('Confirmed on')
    approval_ids = fields.One2many('wtc.approval.line', 'transaction_id', string="Approval", domain=[('form_id','=','purchase.order.cancel')])
    approval_state = fields.Selection([
        ('b','Belum Request'),
        ('rf','Request For Approval'),
        ('a','Approved'),
        ('r','Rejected')
        ], 'Approval State', readonly=True, default='b')
    move_id = fields.Many2one('account.move', string='Account Entry', copy=False)
    move_ids = fields.One2many('account.move.line', related='move_id.line_id', string='Journal Items', readonly=True)
    period_id = fields.Many2one('account.period', string="Period")
    reason = fields.Text('Reason')
    catatan = fields.Text('Catatan')
    
    _sql_constraints = [
        ('unique_purchase_order_id', 'unique(purchase_order_id)', 'Purchase Order pernah diinput sebelumnya !')
        ]
    
    @api.model
    def create(self, values, context=None):
        dso_id = self.env['purchase.order'].search([('id','=',values['purchase_order_id'])])
        values['name'] = "X" + dso_id.name
        values['date'] = self._get_default_date_model()
        values['period_id'] = self.env['account.period'].find(dt=self._get_default_date_model().date()).id
        return super(purchase_order_cancel, self).create(values)
    
    def unlink(self, cr, uid, ids, context=None):
        dso_cancel_id = self.browse(cr, uid, ids, context=context)
        if dso_cancel_id.state != 'draft':
            raise osv.except_osv(('Invalid action !'), ('Tidak bisa dihapus jika state bukan Draft !'))
        return super(purchase_order_cancel, self).unlink(cr, uid, ids, context=context)
    
    @api.multi
    def check_invoices(self):
        invoice_ids = self.purchase_order_id._get_invoice_ids()
        message = ""
        for invoice_id in invoice_ids :
            for line_id in invoice_id.move_id.line_id :
                if line_id.reconcile_id or line_id.reconcile_partial_id :
                    message += invoice_id.number + ", "
        return message
    
    @api.multi
    def check_stock_unit(self):
        picking_ids = self.purchase_order_id._get_ids_picking()
        message = ""
        for picking_id in self.env['stock.picking'].browse(picking_ids) :
            if picking_id.state=='done':
                for moves in picking_id.move_lines:
                    if moves.product_qty==moves.consolidated_qty:
                        quant_ids = self.env['stock.quant'].search([('history_ids','in',moves.id)])
                        for quants in quant_ids:
                            if quants.reservation_id or quants.location_id.usage!='internal':
                                message += quants.lot_id.name + ", "
        return message
    
    def check_stock_sparepart(self):
        message = ""
        list_prod = []
        picking_ids = self.purchase_order_id._get_ids_picking()
        for picking_id in self.env['stock.picking'].browse(picking_ids):
            if picking_id.state == 'done':
                for move in picking_id.move_lines:
                    list_prod.append(move.product_id)

        for lines in self.purchase_order_id.order_line:
            if lines.product_id.id not in list_prod:
                continue
            quant_ids=self.env['stock.quant'].search([
                ('location_id.branch_id','=',self.branch_id.id),
                ('product_id','=',lines.product_id.id),
                ('reservation_id','=',False),
                ('location_id.usage','=','internal')])
            qty_avb = 0
            if quant_ids:
                for quants in quant_ids:
                    qty_avb +=quants.qty
            if qty_avb < lines.product_qty:
                message += lines.product_id.name + ", " 
        return message
    
    @api.multi
    def validity_check(self):
        invoice_warning = ""
        invoice_number = self.check_invoices()
        stock_unit = False
        stock_sparepart = False
        if self.division=='Unit':
            stock_unit = self.check_stock_unit()
        elif self.division=='Sparepart':
            stock_sparepart = self.check_stock_sparepart()
        
        if invoice_number:
            invoice_warning = "Invoice " + invoice_number + "sudah dibayar, silahkan lakukan pembatalan Customer/Supplier Payment terlebih dahulu !"
        if stock_unit:
            invoice_warning = "Unit "+ stock_unit +" sudah dijual/direserved di sales order, silahkan lakukan pembatalan Sales Order terlebih dahulu!"
        if stock_sparepart:
            invoice_warning = "Quantity sparepart "+ stock_sparepart +" yang dibatalkan melebihi stock di cabang, silahkan lakukan pembatalan Work Order/Mutasi terlebih dahulu!"
        if invoice_warning:
            raise osv.except_osv(('Perhatian !'), (invoice_warning))
    
    @api.multi
    def picking_cancel(self):
        obj_picking = self.env['stock.picking']
        ids_picking = self.purchase_order_id._get_ids_picking()
        picking_ids = obj_picking.browse(ids_picking)
        for picking_id in picking_ids :
            if picking_id.state != 'done' :
                picking_id.action_cancel()
                packing_id = self.env['wtc.stock.packing'].search([('picking_id','=',picking_id.id),('state','!=','cancelled')])
                if packing_id :
                    packing_id.action_cancel()
                    
    @api.multi
    def create_picking(self):
        obj_picking = self.env['stock.picking']
        per_product_consolidate = {}
        per_product_unconsolidate = {}
        move_lines_unconsolidated = []
       
        picking_type_out = self.env['stock.picking.type'].search([('branch_id','=',self.branch_id.id),('code','=','outgoing')],limit=1)
        picking_type_in = self.env['stock.picking.type'].search([('branch_id','=',self.branch_id.id),('code','=','incoming')],limit=1)
        total_supplied_consolidated = 0
        total_supplied_unconsolidated = 0
        for picking in obj_picking.browse(self.purchase_order_id._get_ids_picking()):
            move_lines_consolidated = []
            consolidate_ids = self.env['consolidate.invoice'].search([('picking_id','=',picking.id),('state','=','done')])
            if consolidate_ids:
                for consolidate in consolidate_ids:
                    for consolidate_line in consolidate.consolidate_line:
                        move_lines_consolidated.append([0,False,{
                                                        'name': consolidate_line.move_id.name,
                                                        'product_uom': consolidate_line.move_id.product_uom.id,
                                                        'product_uos': consolidate_line.move_id.product_uom.id,
                                                        'picking_type_id': picking_type_in.id, 
                                                        'product_id': consolidate_line.product_id.id,
                                                        'product_uos_qty': consolidate_line.product_qty,
                                                        'product_uom_qty': consolidate_line.product_qty,
                                                        'state': 'draft',
                                                        'location_id': picking_type_in.default_location_dest_id.id,
                                                        'location_dest_id': picking_type_in.default_location_src_id.id,
                                                        'branch_id': self.branch_id.id,
                                                        'origin': self.name,
                                                        'restrict_lot_id': consolidate_line.name.id,
                                                    }])
                        
                obj_model_id = self.env['ir.model'].search([ ('model','=',self.__class__.__name__) ]) 
                picking_consolidated_value = {
                            'picking_type_id': picking_type_out.id,
                            'division':self.division,
                            'move_type': 'direct',
                            'branch_id': self.branch_id.id,
                            'invoice_state': 'none',
                            'transaction_id': self.id,
                            'model_id': obj_model_id.id,
                            'origin': self.name,
                            'move_lines': move_lines_consolidated,
                             }
                create_picking = obj_picking.create(picking_consolidated_value)
                action_confirm = create_picking.action_confirm()
                action_assign = create_picking.action_assign() 
                if create_picking.division == 'Sparepart':
                    if create_picking.state == 'assigned':
                        packing_id = create_picking.create_packing_only(create_picking.id)
                        post_packing = packing_id.sudo().post()
                        if post_packing:
                            self.catatan = 'On Outgoing Shipments [%s] Packing Posted / %s' %(create_picking.name,packing_id.name)
                        else:
                            self.catatan = 'On Outgoing Shipments [%s] Packing Draft / %s' %(create_picking.name,packing_id.name)
                    else:
                        self.catatan = 'On Outgoing Shipments %s / %s' %(create_picking.state,create_picking.name)


            for moves in picking.move_lines:
#                 if not per_product_consolidate.get(moves.product_id.id,False):
#                     per_product_consolidate[moves.product_id.id] = {}
#                 per_product_consolidate[moves.product_id.id]['product_qty'] = per_product_consolidate[moves.product_id.id].get('product_qty',0)+moves.consolidated_qty    
#                 per_product_consolidate[moves.product_id.id]['name'] = moves.name
#                 per_product_consolidate[moves.product_id.id]['product_uom'] = moves.product_uom.id
#                 per_product_consolidate[moves.product_id.id]['location_id'] = moves.location_id.id
#                 total_supplied_consolidated+=moves.consolidated_qty
                
                if moves.consolidated_qty < moves.product_qty:
                    if not per_product_unconsolidate.get(moves.product_id.id,False):
                        per_product_unconsolidate[moves.product_id.id] = {}
                    per_product_unconsolidate[moves.product_id.id]['product_qty'] = per_product_unconsolidate[moves.product_id.id].get('product_qty',0)+moves.product_qty-moves.consolidated_qty    
                    per_product_unconsolidate[moves.product_id.id]['name'] = moves.name
                    per_product_unconsolidate[moves.product_id.id]['product_uom'] = moves.product_uom.id
                    per_product_unconsolidate[moves.product_id.id]['location_id'] = moves.location_id.id
                    total_supplied_unconsolidated+=moves.product_qty-moves.consolidated_qty 
        
#         if per_product_consolidate !={} and total_supplied_consolidated>0:
#             for key, value in per_product_consolidate.items():
#                 product_id = self.env['product.product'].browse(key)
#                 move_lines.append([0,False,{
#                                             'name': value['name'],
#                                             'product_uom': value['product_uom'],
#                                             'product_uos': value['product_uom'],
#                                             'picking_type_id': picking_type_in.id, 
#                                             'product_id': key,
#                                             'product_uos_qty': value['product_qty'],
#                                             'product_uom_qty': value['product_qty'],
#                                             'state': 'draft',
#                                             'location_id': picking_type_in.default_location_dest_id.id,
#                                             'location_dest_id': picking_type_in.default_location_src_id.id,
#                                             'branch_id': self.branch_id.id,
#                                             'origin': self.name,
#                                             }])
#             obj_model_id = self.env['ir.model'].search([ ('model','=',self.__class__.__name__) ]) 
#             picking_consolidated_value = {
#                             'picking_type_id': picking_type_out.id,
#                             'division':self.division,
#                             'move_type': 'direct',
#                             'branch_id': self.branch_id.id,
#                             'invoice_state': 'none',
#                             'transaction_id': self.id,
#                             'model_id': obj_model_id.id,
#                             'origin': self.name,
#                             'move_lines': move_lines,
#                              }
#             create_picking = obj_picking.create(picking_consolidated_value)
#             action_confirm = create_picking.action_confirm()
#             action_assign = create_picking.action_assign()
            
        if per_product_unconsolidate !={} and total_supplied_unconsolidated>0:    
            for key, value in per_product_unconsolidate.items():
                product_id = self.env['product.product'].browse(key)
                move_lines_unconsolidated.append([0,False,{
                                            'name': value['name'],
                                            'product_uom': value['product_uom'],
                                            'product_uos': value['product_uom'],
                                            'picking_type_id': picking_type_in.id, 
                                            'product_id': key,
                                            'product_uos_qty': value['product_qty'],
                                            'product_uom_qty': value['product_qty'],
                                            'state': 'draft',
                                            'location_id': picking_type_in.default_location_dest_id.id,
                                            'location_dest_id': picking_type_in.default_location_src_id.id,
                                            'branch_id': self.branch_id.id,
                                            'origin': self.name,
                                            }])
            obj_model_id = self.env['ir.model'].search([ ('model','=',self.__class__.__name__) ]) 
            picking_unconsolidated_value = {
                            'picking_type_id': picking_type_out.id,
                            'division':self.division,
                            'move_type': 'direct',
                            'branch_id': self.branch_id.id,
                            'invoice_state': 'none',
                            'transaction_id': self.id,
                            'model_id': obj_model_id.id,
                            'origin': self.name,
                            'move_lines': move_lines_unconsolidated,
                            'is_unconsolidated_reverse': True,
                             }
            create_picking = obj_picking.create(picking_unconsolidated_value)
            action_confirm = create_picking.action_confirm()
            if self.division == 'Sparepart':
                action_assign = create_picking.action_assign()        
           
            else:
                action_assign = create_picking.force_assign()

    @api.multi
    def create_account_move_line(self, move_id):
        ids_to_reconcile = []
        invoice_ids = self.purchase_order_id._get_invoice_ids()
        for invoice_id in invoice_ids :
            for line_id in invoice_id.move_id.line_id :
                new_line_id = line_id.copy({
                    'move_id': move_id.id,
                    'debit': line_id.credit,
                    'credit': line_id.debit,
                    'name': self.name,
                    'ref': line_id.ref,
                    'tax_amount': line_id.tax_amount * -1
                    })
                if line_id.account_id.reconcile :
                    ids_to_reconcile.append([line_id.id,new_line_id.id])
        return ids_to_reconcile
    
    @api.multi
    def request_approval(self):
        self.validity_check()
        obj_matrix = self.env['wtc.approval.matrixbiaya']
        obj_matrix.request_by_value(self, 5)
        self.write({'state':'waiting_for_approval', 'approval_state':'rf'})
    
    @api.multi
    def approve(self):
        approval_sts = self.env['wtc.approval.matrixbiaya'].approve(self)
        if approval_sts == 1 :
            self.write({'approval_state':'a','state':'approved'})
        elif approval_sts == 0 :
            raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group Approval !"))
        
    @api.multi
    def confirm(self):
        if self.state == 'approved' :
            self.write({'state':'confirmed', 'date':self._get_default_date(), 'confirm_uid':self._uid, 'confirm_date':datetime.now(), 'period_id':self.env['account.period'].find(dt=self._get_default_date().date()).id})
            self.purchase_order_id.write({'is_cancelled':True})
            self.validity_check()
            self.picking_cancel()
            self.create_picking()
            obj_acc_move = self.env['account.move']
            acc_move_line_obj = self.pool.get('account.move.line')
            branch_config_id = self.env['wtc.branch.config'].search([('branch_id','=',self.branch_id.id)])
            journal_id = branch_config_id.purchase_order_cancel_journal_id
            if not journal_id :
                raise osv.except_osv(("Perhatian !"), ("Tidak ditemukan Journal Pembatalan Purchase Order di Branch Config, silahkan konfigurasi ulang !"))
            invoice_ids = self.purchase_order_id._get_invoice_ids()
            if invoice_ids:
                for invoice in invoice_ids:
                    if invoice.state=='open':
                        move_id = obj_acc_move.create({
                            'name': self.name,
                            'journal_id': journal_id.id,
                            'line_id': [],
                            'period_id': self.period_id.id,
                            'date': self._get_default_date(),
                            'ref': self.purchase_order_id.name
                            })
                        to_reconcile_ids = self.create_account_move_line(move_id)
                        for to_reconcile in to_reconcile_ids :
                            acc_move_line_obj.reconcile(self._cr, self._uid, to_reconcile)
                        self.write({'move_id':move_id.id})
                        if journal_id.entry_posted :
                            move_id.button_validate()
                    if invoice.state=='draft':
                        invoice.action_cancel()
            
        return self.purchase_order_id.signal_workflow('purchase_cancel')


class wtc_purchase_order(osv.osv):
    _inherit = 'purchase.order'
    
    def _get_invoice_ids(self, cr, uid, ids, context=None):
        po_id = self.browse(cr, uid, ids, context=context)
        obj_inv = self.pool.get('account.invoice')
        obj_model = self.pool.get('ir.model')
        id_model = obj_model.search(cr, uid, [('model','=','purchase.order')])[0]
        ids_inv = obj_inv.search(cr, uid, [
            ('model_id','=',id_model),
            ('transaction_id','=',po_id.id),
            ('state','!=','cancel')
            ])
        inv_ids = obj_inv.browse(cr, uid, ids_inv)
        return inv_ids
    
    def _get_ids_picking(self, cr, uid, ids, context=None):
        po_id = self.browse(cr, uid, ids, context=context)
        obj_picking = self.pool.get('stock.picking')
        obj_model = self.pool.get('ir.model')
        id_model = obj_model.search(cr, uid, [('model','=','purchase.order')])[0]
        ids_picking = obj_picking.search(cr, uid, [
            ('model_id','=',id_model),
            ('transaction_id','=',po_id.id),
            ('state','!=','cancel')
            ])
        return ids_picking
    

    