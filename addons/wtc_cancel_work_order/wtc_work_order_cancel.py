from openerp import models, fields, api
from datetime import datetime
from openerp.osv import osv

class work_order_cancel(models.Model):
    _name = "work.order.cancel"
    _description = "Work Order Cancel"
    
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
    work_order_id = fields.Many2one('wtc.work.order', 'Work Order')
    division = fields.Selection([('Sparepart','Sparepart')], 'Division')
    date = fields.Date('Date',default=_get_default_date)
    confirm_uid = fields.Many2one('res.users', string="Confirmed by")
    confirm_date = fields.Datetime('Confirmed on')
    approval_ids = fields.One2many('wtc.approval.line', 'transaction_id', string="Approval", domain=[('form_id','=','work.order.cancel')])
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
    
    _sql_constraints = [
        ('unique_work_order_id', 'unique(work_order_id)', 'Work Order pernah diinput sebelumnya !')
        ]
    
    @api.model
    def create(self, values, context=None):
        dso_id = self.env['wtc.work.order'].search([('id','=',values['work_order_id'])])
        values['name'] = "X" + dso_id.name
        values['date'] = self._get_default_date_model()
        values['period_id'] = self.env['account.period'].find(dt=self._get_default_date_model().date()).id
        return super(work_order_cancel, self).create(values)
    
    def unlink(self, cr, uid, ids, context=None):
        dso_cancel_id = self.browse(cr, uid, ids, context=context)
        if dso_cancel_id.state != 'draft':
            raise osv.except_osv(('Invalid action !'), ('Tidak bisa dihapus jika state bukan Draft !'))
        return super(work_order_cancel, self).unlink(cr, uid, ids, context=context)
    
    @api.multi
    def check_invoices(self):
        invoice_ids = self.work_order_id._get_invoice_ids()
        message = ""
        for invoice_id in invoice_ids :
            for line_id in invoice_id.move_id.line_id :
                if line_id.reconcile_id or line_id.reconcile_partial_id :
                    message += invoice_id.number + ", "
        return message
    
    @api.multi
    def validity_check(self):
        invoice_warning = ""
        invoice_number = self.check_invoices()
        if invoice_number :
            invoice_warning = "Invoice " + invoice_number + "sudah dibayar, silahkan lakukan pembatalan Customer/Supplier Payment terlebih dahulu !"
        if invoice_warning:
            raise osv.except_osv(('Perhatian !'), (invoice_warning))
   
    @api.multi
    def picking_cancel(self):
        obj_picking = self.env['stock.picking']
        ids_picking = self.work_order_id._get_ids_picking()
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
        per_product = {}
        move_lines = []
        
        picking_type_out = self.env['stock.picking.type'].search([('branch_id','=',self.branch_id.id),('code','=','outgoing')])
        picking_type_in = self.env['stock.picking.type'].search([('branch_id','=',self.branch_id.id),('code','=','incoming')])
        total_supplied = 0
        for order_lines in self.work_order_id.work_lines:
            if order_lines.categ_id == "Sparepart":
                if order_lines.supply_qty >0:
                    if not per_product.get(order_lines.product_id.id,False):
                        per_product[order_lines.product_id.id] = {}
                    per_product[order_lines.product_id.id]['product_qty'] = per_product[order_lines.product_id.id].get('product_qty',0)+order_lines.supply_qty    
                    per_product[order_lines.product_id.id]['name'] = order_lines.name
                    per_product[order_lines.product_id.id]['product_uom'] = order_lines.product_uom.id
                    per_product[order_lines.product_id.id]['location_id'] = order_lines.location_id.id
                    total_supplied+=order_lines.supply_qty
        
        if per_product !={} and total_supplied>0:    
            for key, value in per_product.items():
                product_id = self.env['product.product'].browse(key)
                real_hpp = round((self.work_order_id._get_moved_price(self.work_order_id.picking_ids,product_id)/value['product_qty']),2)
                move_lines.append([0,False,{
                                            'name': value['name'],
                                            'product_uom': value['product_uom'],
                                            'product_uos': value['product_uom'],
                                            'picking_type_id': picking_type_in.id, 
                                            'product_id': key,
                                            'product_uos_qty': value['product_qty'],
                                            'product_uom_qty': value['product_qty'],
                                            'state': 'draft',
                                            'location_id': picking_type_out.default_location_dest_id.id,
                                            'location_dest_id': picking_type_out.default_location_src_id.id,
                                            'branch_id': self.branch_id.id,
                                            'price_unit': real_hpp,
                                            'origin': self.name,
                                            'real_hpp':real_hpp,
                                            }])
            obj_model_id = self.env['ir.model'].search([ ('model','=',self.__class__.__name__) ]) 
            picking_value = {
                            'picking_type_id': picking_type_in.id,
                            'division':'Sparepart',
                            'move_type': 'direct',
                            'branch_id': self.branch_id.id,
                            'invoice_state': 'none',
                            'transaction_id': self.id,
                            'model_id': obj_model_id.id,
                            'origin': self.name,
                            'move_lines': move_lines,
                             }
            create_picking = obj_picking.create(picking_value)
            action_confirm = create_picking.action_confirm()
            action_assign = create_picking.action_assign()
                
                    
    @api.multi
    def create_account_move_line(self, move_id):
        ids_to_reconcile = []
        invoice_ids = self.work_order_id._get_invoice_ids()
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
            self.work_order_id.write({'is_cancelled':True})
            self.validity_check()
            self.picking_cancel()
            self.create_picking()
            obj_acc_move = self.env['account.move']
            acc_move_line_obj = self.pool.get('account.move.line')
            branch_config_id = self.env['wtc.branch.config'].search([('branch_id','=',self.branch_id.id)])
            journal_id = branch_config_id.work_order_cancel_journal_id
            if not journal_id :
                raise osv.except_osv(("Perhatian !"), ("Tidak ditemukan Journal Pembatalan Work Order di Branch Config, silahkan konfigurasi ulang !"))
            
            if self.work_order_id._get_invoice_ids():
                move_id = obj_acc_move.create({
                    'name': self.name,
                    'journal_id': journal_id.id,
                    'line_id': [],
                    'period_id': self.period_id.id,
                    'date': self._get_default_date(),
                    'ref': self.work_order_id.name
                    })
                to_reconcile_ids = self.create_account_move_line(move_id)
                for to_reconcile in to_reconcile_ids :
                    acc_move_line_obj.reconcile(self._cr, self._uid, to_reconcile)
                self.write({'move_id':move_id.id})
                if journal_id.entry_posted :
                    move_id.button_validate()
                if self.work_order_id.faktur_pajak_id :
                    self.work_order_id.faktur_pajak_id.write({'state':'cancel'})
        return self.work_order_id.signal_workflow('wkf_action_cancel')