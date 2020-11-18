from openerp import models, fields, api
from datetime import datetime
from openerp.osv import osv

class dealer_sales_order_cancel(models.Model):
    _name = "dealer.sales.order.cancel"
    _description = "Dealer Sales Order Cancel"
    
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
    dealer_sales_order_id = fields.Many2one('dealer.sale.order', 'Dealer Sales Order')
    customer_id = fields.Many2one('res.partner','Customer',related='dealer_sales_order_id.partner_id',readonly=True)
    division = fields.Selection([('Unit','Unit')], 'Division',default='Unit')
    date = fields.Date('Date',default=_get_default_date)
    confirm_uid = fields.Many2one('res.users', string="Confirmed by")
    confirm_date = fields.Datetime('Confirmed on')
    approval_ids = fields.One2many('wtc.approval.line', 'transaction_id', string="Approval", domain=[('form_id','=','dealer.sales.order.cancel')])
    approval_state = fields.Selection([
        ('b','Belum Request'),
        ('rf','Request For Approval'),
        ('a','Approved'),
        ('r','Rejected')
        ], 'Approval State', readonly=True, default='b')
    move_id = fields.Many2one('account.move', string='Account Entry', copy=False)
    move_ids = fields.One2many('account.move.line', related='move_id.line_id', string='Journal Items', readonly=True)
    period_id = fields.Many2one('account.period', string="Period")
    reason = fields.Char('Reason')
    
    _sql_constraints = [
        ('unique_dealer_sales_order_id', 'unique(dealer_sales_order_id)', 'Dealer Sale Order pernah diinput sebelumnya !')
        ]
    
    @api.model
    def create(self, values, context=None):
        dso_id = self.env['dealer.sale.order'].search([('id','=',values['dealer_sales_order_id'])])
        values['name'] = "X" + dso_id.name
        values['date'] = self._get_default_date_model()
        values['period_id'] = self.env['account.period'].find(dt=self._get_default_date_model().date()).id
        return super(dealer_sales_order_cancel, self).create(values)
    
    def unlink(self, cr, uid, ids, context=None):
        dso_cancel_id = self.browse(cr, uid, ids, context=context)
        if dso_cancel_id.state != 'draft':
            raise osv.except_osv(('Invalid action !'), ('Tidak bisa dihapus jika state bukan Draft !'))
        return super(dealer_sales_order_cancel, self).unlink(cr, uid, ids, context=context)
    
    @api.multi
    def check_shipments(self):
        obj_picking = self.env['stock.picking']
        ids_picking = self.dealer_sales_order_id._get_ids_picking()
        picking_ids = obj_picking.browse(ids_picking)
        qty = {}
        for picking in picking_ids :
            if picking.state == 'done' :
                for move in picking.move_lines :
                    if not move.origin_returned_move_id :
                        qty[move.product_id] = qty.get(move.product_id,0) + move.product_uom_qty
                    else :
                        qty[move.product_id] = qty.get(move.product_id,0) - move.product_uom_qty
        products_name = ""
        if qty :
            for key, value in qty.items() :
                if value != 0 :
                    products_name += key.name + ", "
        return products_name
    
    @api.multi
    def check_invoices(self):
        invoice_ids = self.dealer_sales_order_id._get_invoice_ids()
        message = ""
        for invoice_id in invoice_ids :
            for line_id in invoice_id.move_id.line_id :
                if line_id.reconcile_id:
                    if self.dealer_sales_order_id.al_move_id:
                        check_reconcile = self.env['account.move.line'].search([('reconcile_id','=',line_id.reconcile_id.id),('move_id','=',self.dealer_sales_order_id.al_move_id.id)]) 
                        if not check_reconcile:
                            message += invoice_id.number + ", "
                        else:
                            if (len(line_id.reconcile_id.line_id)>2):
                                message += invoice_id.number + ", "
                    else:
                        message += invoice_id.number + ", "
                elif line_id.reconcile_partial_id:
                    if self.dealer_sales_order_id.al_move_id:
                        check_reconcile = self.env['account.move.line'].search([('reconcile_partial_id','=',line_id.reconcile_partial_id.id),('move_id','=',self.dealer_sales_order_id.al_move_id.id)]) 
                        if not check_reconcile:
                            message += invoice_id.number + ", "
                        elif (len(line_id.reconcile_partial_id.line_partial_ids)>2):
                                message += invoice_id.number + ", "
                    else:
                        message += invoice_id.number + ", "
        return message
    
    @api.multi
    def check_permohonan_faktur(self):
        for dso_line in self.dealer_sales_order_id.dealer_sale_order_line :
            if dso_line.lot_id.tgl_faktur :
                raise osv.except_osv(("Perhatian !"), ("Silahkan lakukan pembatalan Permohonan Faktur terlebih dahulu !"))
        return True
    
    @api.multi
    def validity_check(self):
        invoice_warning = ""
        picking_warning = ""
        invoice_number = self.check_invoices()
        product_name = self.check_shipments()
        if invoice_number :
            invoice_warning = "Invoice " + invoice_number + "sudah dibayar, silahkan lakukan pembatalan Customer/Supplier Payment terlebih dahulu !"
        if product_name :
            picking_warning = "\nProduct " + product_name + "belum dikembalikan seluruhnya, silahkan lakukan reverse transfer terlebih dahulu !"
        if invoice_warning or picking_warning :
            raise osv.except_osv(('Perhatian !'), (invoice_warning + picking_warning))
        self.check_permohonan_faktur()
    
    @api.multi
    def picking_cancel(self):
        obj_picking = self.env['stock.picking']
        ids_picking = self.dealer_sales_order_id._get_ids_picking()
        picking_ids = obj_picking.browse(ids_picking)
        for picking_id in picking_ids :
            if picking_id.state != 'done' :
                picking_id.action_cancel()
                packing_id = self.env['wtc.stock.packing'].search([('picking_id','=',picking_id.id),('state','!=','cancelled')])
                if packing_id :
                    packing_id.action_cancel()
    
    @api.multi
    def create_account_move_line(self, move_id):
        ids_to_reconcile = []
        obj_move_line = self.env['account.move.line']
        invoice_ids = self.dealer_sales_order_id._get_invoice_ids()
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
        if self.dealer_sales_order_id.hutang_lain_line:
            for hl_line in self.dealer_sales_order_id.hutang_lain_line:
                move_lines = []
                if hl_line.hl_id.reconcile_id :
                    move_lines = [move_line.id for move_line in hl_line.hl_id.reconcile_id.line_id]
                    hl_line.hl_id.reconcile_id.unlink()
                elif hl_line.hl_id.reconcile_partial_id :
                    move_lines = [move_line.id for move_line in hl_line.hl_id.reconcile_partial_id.line_partial_ids]
                    hl_line.hl_id.reconcile_partial_id.unlink()
                if move_lines :
                    move_lines.remove(hl_line.hl_id.id)
                if len(move_lines) >= 2 :
                    obj_move_line.browse(move_lines).reconcile_partial('auto')
            if self.dealer_sales_order_id.al_move_id:
                for aml in self.dealer_sales_order_id.al_move_id.line_id:
                    if aml.reconcile_id :
                        aml.reconcile_id.unlink()
                    elif aml.reconcile_partial_id:
                        aml.reconcile_partial_id.unlink()
                    new_move = aml.copy({
                    'move_id': move_id.id,
                    'debit': aml.credit,
                    'credit': aml.debit,
                    'name': self.name,
                    'ref': aml.ref,
                    'tax_amount': aml.tax_amount * -1
                    })
                    if aml.account_id.reconcile :
                        ids_to_reconcile.append([aml.id,new_move.id])                     
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
            self.dealer_sales_order_id.write({'is_cancelled':True})
            self.validity_check()
            self.picking_cancel()
            obj_acc_move = self.env['account.move']
            acc_move_line_obj = self.pool.get('account.move.line')
            branch_config_id = self.env['wtc.branch.config'].search([('branch_id','=',self.branch_id.id)])
            journal_id = branch_config_id.dso_cancel_journal_id
            if not journal_id :
                raise osv.except_osv(("Perhatian !"), ("Tidak ditemukan Journal Pembatalan Dealer Sale Order di Branch Config, silahkan konfigurasi ulang !"))
            move_id = obj_acc_move.create({
                'name': self.name,
                'journal_id': journal_id.id,
                'line_id': [],
                'period_id': self.period_id.id,
                'date': self._get_default_date(),
                'ref': self.dealer_sales_order_id.name
                })
            to_reconcile_ids = self.create_account_move_line(move_id)
            for to_reconcile in to_reconcile_ids :
                acc_move_line_obj.reconcile(self._cr, self._uid, to_reconcile)
            self.write({'move_id':move_id.id})
            if journal_id.entry_posted :
                move_id.button_validate()
            if self.dealer_sales_order_id.faktur_pajak_id :
                self.dealer_sales_order_id.faktur_pajak_id.write({'state':'cancel'})
        return self.dealer_sales_order_id.signal_workflow('sale_cancel')
    
class payment_cancel(models.Model):
    _name = "payment.cancel"
    _description = "Payment Cancel"
    
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
    payment_id = fields.Many2one('account.voucher', 'Payment Old')
    voucher_id = fields.Many2one('wtc.account.voucher', 'Payment')
    dn_nc_id = fields.Many2one('wtc.dn.nc', 'PR / OR')
    division = fields.Selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum'),('Finance','Finance')], 'Division')
    date = fields.Date('Date',default=_get_default_date)
    confirm_uid = fields.Many2one('res.users', string="Confirmed by")
    confirm_date = fields.Datetime('Confirmed on')
    approval_ids = fields.One2many('wtc.approval.line', 'transaction_id', string="Approval", domain=[('form_id','=','payment.cancel')])
    approval_state = fields.Selection([
        ('b','Belum Request'),
        ('rf','Request For Approval'),
        ('a','Approved'),
        ('r','Rejected')
        ], 'Approval State', readonly=True, default='b')
    move_id = fields.Many2one('account.move', string='Account Entry', copy=False)
    move_ids = fields.One2many('account.move.line', related='move_id.line_id', string='Journal Items', readonly=True)
    period_id = fields.Many2one('account.period', string="Period")
    reason = fields.Char('Reason')
    
    _sql_constraints = [
        ('unique_payment_id_voucher_id_dn_nc_id', 'unique(payment_id, voucher_id, dn_nc_id)', 'Transaksi ini sudah pernah diinput sebelumnya !')
        ]
    
    @api.model
    def create(self, values, context=None):
        total = 0
        if values.get('payment_id') :
            payment_id = self.env['account.voucher'].search([('id','=',values['payment_id'])])
            total += 1
        if values.get('voucher_id') :
            payment_id = self.env['wtc.account.voucher'].search([('id','=',values['voucher_id'])])
            total += 1
        if values.get('dn_nc_id') :
            payment_id = self.env['wtc.dn.nc'].search([('id','=',values['dn_nc_id'])])
            total += 1
        if total != 1 :
            raise osv.except_osv(('Perhatian !'), '[1] Pilih salah satu, antara Payment Old, Payment atau PR / OR !')

        values['name'] = "X" + payment_id.number
        values['date'] = self._get_default_date_model()
        values['period_id'] = self.env['account.period'].find(dt=self._get_default_date_model().date()).id
        res = super(payment_cancel, self).create(values)
        return res

    def write(self, cr, uid, ids, vals, context=None):
        res = super(payment_cancel, self).write(cr, uid, ids, vals, context=context)
        if ('payment_id' in vals) or ('voucher_id' in vals) or ('dn_nc_id' in vals) :
            raise osv.except_osv('Perhatian !', 'Tidak bisa ubah nomor bukti yang ingin dibatalkan. Jika ingin mengubahnya, harap hapus transaksi ini dan bikin lagi.')
        return res
    
    def unlink(self, cr, uid, ids, context=None):
        payment_cancel_id = self.browse(cr, uid, ids, context=context)
        if payment_cancel_id.state != 'draft':
            raise osv.except_osv(('Invalid action !'), ('Tidak bisa dihapus jika state bukan Draft !'))
        return super(payment_cancel, self).unlink(cr, uid, ids, context=context)

    @api.multi
    def create_account_move_line(self, move_id):
        ids_to_reconcile = []
        obj_reconcile = self.env['account.move.reconcile']
        obj_move_line = self.env['account.move.line']
        move_ids = False
        if self.payment_id :
            move_ids = self.payment_id.move_ids
        elif self.voucher_id :
            move_ids = self.voucher_id.move_ids
        elif self.dn_nc_id :
            move_ids = self.dn_nc_id.move_ids
        for line_id in move_ids :
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
            move_lines = []
            if line_id.reconcile_id :
                move_lines = [move_line.id for move_line in line_id.reconcile_id.line_id]
                line_id.reconcile_id.unlink()
            elif line_id.reconcile_partial_id :
                move_lines = [move_line.id for move_line in line_id.reconcile_partial_id.line_partial_ids]
                line_id.reconcile_partial_id.unlink()
            if move_lines :
                move_lines.remove(line_id.id)
            if len(move_lines) >= 2 :
                obj_move_line.browse(move_lines).reconcile_partial('auto')
#                 obj_move_line.reconcile_partial(self._cr, self._uid, move_lines, type='auto', context=self._context)
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
    def validity_check(self):
        if self.payment_id.id :
            if self.payment_id.state != 'posted' :
                raise osv.except_osv(('Perhatian !'), ("Tidak bisa cancel, status Customer/Supplier Payment bukan Posted !"))
            if self.payment_id.type == 'payment' or (self.payment_id.type == 'receipt' and not self.payment_id.is_hutang_lain) :
                if self.payment_id.payment_option == 'without_writeoff' and self.payment_id.writeoff_amount != 0 :
                    for line in self.payment_id.move_ids :
                        if line.name == self.payment_id.number :
                            if line.debit == abs(self.payment_id.writeoff_amount) or line.credit == abs(self.payment_id.writeoff_amount) :
                                if (self.payment_id.type == 'receipt' and line.account_id == self.payment_id.partner_id.property_account_payable) or (self.payment_id.type == 'payment' and line.account_id == self.payment_id.partner_id.property_account_receivable) :
                                    if line.account_id.reconcile and (line.reconcile_id or line.reconcile_partial_id) :
                                        if line.reconcile_id :
                                            transactions = [str(x.move_id.name) for x in line.reconcile_id.line_id if x != line]
                                        else :
                                            transactions = [str(x.move_id.name) for x in line.reconcile_partial_id.line_partial_ids if x != line]
                                        raise osv.except_osv(('Perhatian !'), ("Titipan sudah digunakan untuk transaksi lain '%s', silahkan batalkan terlebih dahulu !" %transactions))
            elif self.payment_id.type in ('sale','purchase') or (self.payment_id.type == 'receipt' and self.payment_id.is_hutang_lain) :
                for line in self.payment_id.move_ids :
                    if line.reconcile_id or line.reconcile_partial_id :
                        if line.reconcile_id :
                            transactions = [str(x.move_id.name) for x in line.reconcile_id.line_id if x != line]
                        else :
                            transactions = [str(x.move_id.name) for x in line.reconcile_partial_id.line_partial_ids if x != line]
                        raise osv.except_osv(('Perhatian !'), ("Transaksi ini sudah digunakan untuk transaksi lain '%s', silahkan batalkan terlebih dahulu !" %transactions))
        elif self.voucher_id.id :
            if self.voucher_id.state != 'posted' :
                raise osv.except_osv(('Perhatian !'), ("Tidak bisa cancel, status Customer/Supplier Payment bukan Posted !"))
            if self.voucher_id.type in ('payment', 'receipt') and self.voucher_id.writeoff_amount != 0 and not self.voucher_id.pembulatan :
                for line in self.voucher_id.move_ids :
                    if line.name == self.voucher_id.number :
                        if line.debit == abs(self.voucher_id.writeoff_amount) or line.credit == abs(self.voucher_id.writeoff_amount) :
                            if (self.voucher_id.type == 'receipt' and line.account_id == self.voucher_id.partner_id.property_account_payable) or (self.voucher_id.type == 'payment' and line.account_id == self.voucher_id.partner_id.property_account_receivable) :
                                if line.account_id.reconcile and (line.reconcile_id or line.reconcile_partial_id) :
                                    if line.reconcile_id :
                                        transactions = [str(x.move_id.name) for x in line.reconcile_id.line_id if x != line]
                                    else :
                                        transactions = [str(x.move_id.name) for x in line.reconcile_partial_id.line_partial_ids if x != line]
                                    raise osv.except_osv(('Perhatian !'), ("Titipan sudah digunakan untuk transaksi lain '%s', silahkan batalkan terlebih dahulu !" %transactions))
            elif self.voucher_id.type == 'hutang_lain' :
                for line in self.voucher_id.move_ids :
                    if line.reconcile_id or line.reconcile_partial_id :
                        if line.reconcile_id :
                            transactions = [str(x.move_id.name) for x in line.reconcile_id.line_id if x != line]
                        else :
                            transactions = [str(x.move_id.name) for x in line.reconcile_partial_id.line_partial_ids if x != line]
                        raise osv.except_osv(('Perhatian !'), ("Transaksi ini sudah digunakan untuk transaksi lain '%s', silahkan batalkan terlebih dahulu !" %transactions))
        elif self.dn_nc_id.id :
            if self.dn_nc_id.state != 'posted' :
                raise osv.except_osv(('Perhatian !'), ("Tidak bisa cancel, status Payment Request / Other Rece bukan Posted !"))
            for line in self.dn_nc_id.move_ids :
                if line.reconcile_id or line.reconcile_partial_id :
                    if line.reconcile_id :
                        transactions = [str(x.move_id.name) for x in line.reconcile_id.line_id if x != line]
                    else :
                        transactions = [str(x.move_id.name) for x in line.reconcile_partial_id.line_partial_ids if x != line]
                    raise osv.except_osv(('Perhatian !'), ("Transaksi ini sudah digunakan untuk transaksi lain '%s', silahkan batalkan terlebih dahulu !" %transactions))
        else :
            raise osv.except_osv(('Perhatian !'), ("Pilih transaksi yang ingin dibatalkan."))
        
    @api.multi
    def confirm(self):
        if self.state == 'approved' :
            self.validity_check()
            self.write({'state':'confirmed', 'date':self._get_default_date(), 'confirm_uid':self._uid, 'confirm_date':datetime.now(), 'period_id':self.env['account.period'].find(dt=self._get_default_date().date()).id})
            obj_acc_move = self.env['account.move']
            acc_move_line_obj = self.pool.get('account.move.line')
            journal_id = False
            vtype = False
            if self.payment_id :
                journal_id = self.payment_id.journal_id
                vtype = self.payment_id.type
            elif self.voucher_id :
                journal_id = self.voucher_id.journal_id
                vtype = self.voucher_id.type
            elif self.dn_nc_id :
                journal_id = self.dn_nc_id.journal_id
                vtype = self.dn_nc_id.type
            if vtype not in ('payment','receipt','hutang_lain') :
                branch_config_id = self.env['wtc.branch.config'].search([('branch_id','=',self.branch_id.id)])
                journal_id = branch_config_id.payment_cancel_journal_id
                if not journal_id :
                    raise osv.except_osv(("Perhatian !"), ("Tidak ditemukan Journal Pembatalan Customer Payment di Branch Config, silahkan konfigurasi ulang !"))
            move_id = obj_acc_move.create({
                'name': self.name,
                'journal_id': journal_id.id,
                'line_id': [],
                'period_id': self.period_id.id,
                'date': self._get_default_date(),
                'ref': self.payment_id.number
                })
            to_reconcile_ids = self.create_account_move_line(move_id)
            for to_reconcile in to_reconcile_ids :
                acc_move_line_obj.reconcile(self._cr, self._uid, to_reconcile)
            self.write({'move_id':move_id.id})
            if journal_id.entry_posted :
                move_id.button_validate()
            if self.payment_id :
                self.payment_id.with_context(pembatalan=True).write({
                    'state':'cancel',
                    'cancel_uid':self._uid,
                    'cancel_date':datetime.now(),
                })
            elif self.voucher_id :
                self.voucher_id.write({
                    'state':'cancel',
                    'cancel_uid':self._uid,
                    'cancel_date':datetime.now(),
                })
            elif self.dn_nc_id :
                self.dn_nc_id.write({
                    'state':'cancel',
                    'cancel_uid':self._uid,
                    'cancel_date':datetime.now(),
                })

        return True
    
class sale_order_cancel(models.Model):
    _name = "sale.order.cancel"
    _description = "MD Sales Order Cancel"
    
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
    sale_order_id = fields.Many2one('sale.order', 'Sales Order')
    division = fields.Selection([('Unit','Unit'),('Sparepart','Sparepart')], 'Division')
    date = fields.Date('Date',default=_get_default_date)
    confirm_uid = fields.Many2one('res.users', string="Confirmed by")
    confirm_date = fields.Datetime('Confirmed on')
    approval_ids = fields.One2many('wtc.approval.line', 'transaction_id', string="Approval", domain=[('form_id','=','sale.order.cancel')])
    approval_state = fields.Selection([
        ('b','Belum Request'),
        ('rf','Request For Approval'),
        ('a','Approved'),
        ('r','Rejected')
        ], 'Approval State', readonly=True, default='b')
    move_id = fields.Many2one('account.move', string='Account Entry', copy=False)
    move_ids = fields.One2many('account.move.line', related='move_id.line_id', string='Journal Items', readonly=True)
    period_id = fields.Many2one('account.period', string="Period")
    reason = fields.Char('Reason')
    
    _sql_constraints = [
        ('unique_sale_order_id', 'unique(sale_order_id)', 'Sale Order pernah diinput sebelumnya !')
        ]
    
    @api.model
    def create(self, values, context=None):
        so_id = self.env['sale.order'].search([('id','=',values['sale_order_id'])])
        values['name'] = "X" + so_id.name
        values['date'] = self._get_default_date_model()
        values['period_id'] = self.env['account.period'].find(dt=self._get_default_date_model().date()).id
        return super(sale_order_cancel, self).create(values)
    
    def unlink(self, cr, uid, ids, context=None):
        so_cancel_id = self.browse(cr, uid, ids, context=context)
        if so_cancel_id.state != 'draft':
            raise osv.except_osv(('Invalid action !'), ('Tidak bisa dihapus jika state bukan Draft !'))
        return super(sale_order_cancel, self).unlink(cr, uid, ids, context=context)
    
    @api.multi
    def check_shipments(self):
        obj_picking = self.env['stock.picking']
        ids_picking = self.sale_order_id._get_ids_picking()
        if not ids_picking:
            raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan picking untuk transaksi %s \n silahkan periksa kembali transaksi") % self.sale_order_id.name)
        picking_ids = obj_picking.browse(ids_picking)
        qty = {}
        for picking in picking_ids :
            if picking.state == 'done' :
                for move in picking.move_lines :
                    if not move.origin_returned_move_id :
                        qty[move.product_id] = qty.get(move.product_id,0) + move.product_uom_qty
                    else :
                        qty[move.product_id] = qty.get(move.product_id,0) - move.product_uom_qty
        products_name = ""
        if qty :
            for key, value in qty.items() :
                if value != 0 :
                    products_name += key.name + ", "
        if products_name :
            raise osv.except_osv(('Perhatian !'), ("Product " + products_name + "belum dikembalikan seluruhnya, silahkan lakukan reverse transfer terlebih dahulu !"))
        return True
    
    @api.multi
    def check_invoices(self):
        invoice_ids = self.sale_order_id._get_invoice_ids()
        if not invoice_ids:
            raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan invoice untuk transaksi %s \n silahkan periksa kembali transaksi") % self.sale_order_id.name)
        message = ""
        for invoice_id in invoice_ids :
            for line_id in invoice_id.move_id.line_id :
                if line_id.reconcile_id or line_id.reconcile_partial_id :
                    message += invoice_id.number + ", "
        if message :
            raise osv.except_osv(("Perhatian !"), ("Invoice " + message + "sudah dibayar, silahkan lakukan pembatalan Customer/Supplier Payment terlebih dahulu !"))
        return True
    
    @api.multi
    def validity_check(self):
        self.check_shipments()
        self.check_invoices()
        
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
    def picking_cancel(self):
        obj_picking = self.env['stock.picking']
        ids_picking = self.sale_order_id._get_ids_picking()
        picking_ids = obj_picking.browse(ids_picking)
        for picking_id in picking_ids :
            if picking_id.state != 'done' :
                picking_id.action_cancel()
                packing_id = self.env['wtc.stock.packing'].search([('picking_id','=',picking_id.id),('state','!=','cancelled')])
                if packing_id :
                    packing_id.action_cancel()
    
    @api.multi
    def create_account_move_line(self, move_id):
        ids_to_reconcile = []
        invoice_ids = self.sale_order_id._get_invoice_ids()
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
    def confirm(self):
        if self.state == 'approved' :
            self.write({'state':'confirmed', 'date':self._get_default_date(), 'confirm_uid':self._uid, 'confirm_date':datetime.now(), 'period_id':self.env['account.period'].find(dt=self._get_default_date().date()).id})
            self.sale_order_id.write({'is_cancelled':True})
            self.validity_check()
            self.picking_cancel()
            obj_acc_move = self.env['account.move']
            acc_move_line_obj = self.pool.get('account.move.line')
            branch_config_id = self.env['wtc.branch.config'].search([('branch_id','=',self.branch_id.id)])
            if self.division =='Unit':
                journal_id = branch_config_id.so_cancel_unit_journal_id
            elif self.division =='Sparepart':
                journal_id = branch_config_id.so_cancel_sparepart_journal_id
            if not journal_id :
                raise osv.except_osv(("Perhatian !"), ("Tidak ditemukan Journal Pembatalan Dealer Sale Order di Branch Config, silahkan konfigurasi ulang !"))
            move_id = obj_acc_move.create({
                'name': self.name,
                'journal_id': journal_id.id,
                'line_id': [],
                'period_id': self.period_id.id,
                'date': self._get_default_date(),
                'ref': self.sale_order_id.name
                })
            to_reconcile_ids = self.create_account_move_line(move_id)
            for to_reconcile in to_reconcile_ids :
                acc_move_line_obj.reconcile(self._cr, self._uid, to_reconcile)
            self.write({'move_id':move_id.id})
            if journal_id.entry_posted :
                move_id.button_validate()
            self.sale_order_id.signal_workflow('so_cancel')
            
class mutation_order_cancel(models.Model):
    _name = "mutation.order.cancel"
    _description = "Mutation Order Cancel"
    
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
    mutation_order_id = fields.Many2one('wtc.mutation.order', 'Mutation Order')
    division = fields.Selection([('Unit','Unit'),('Sparepart','Sparepart')], 'Division')
    date = fields.Date('Date',default=_get_default_date)
    confirm_uid = fields.Many2one('res.users', string="Confirmed by", copy=False)
    confirm_date = fields.Datetime('Confirmed on', copy=False)
    approval_ids = fields.One2many('wtc.approval.line', 'transaction_id', string="Approval", domain=[('form_id','=','mutation.order.cancel')])
    approval_state = fields.Selection([
        ('b','Belum Request'),
        ('rf','Request For Approval'),
        ('a','Approved'),
        ('r','Rejected')
        ], 'Approval State', readonly=True, default='b')
    reason = fields.Text('Reason')
    
    _sql_constraints = [
        ('unique_mutation_order_id', 'unique(mutation_order_id)', 'Mutation Order pernah diinput sebelumnya !')
        ]
    
    @api.model
    def create(self, values, context=None):
        mo_id = self.env['wtc.mutation.order'].search([('id','=',values['mutation_order_id'])])
        values['name'] = "X" + mo_id.name
        values['date'] = self._get_default_date_model()
        values['period_id'] = self.env['account.period'].find(dt=self._get_default_date_model().date()).id
        return super(mutation_order_cancel, self).create(values)
    
    def unlink(self, cr, uid, ids, context=None):
        mo_cancel_id = self.browse(cr, uid, ids, context=context)
        if mo_cancel_id.state != 'draft':
            raise osv.except_osv(('Invalid action !'), ('Tidak bisa dihapus jika state bukan Draft !'))
        return super(mutation_order_cancel, self).unlink(cr, uid, ids, context=context)
    
    @api.multi
    def check_shipments(self):
        obj_picking = self.env['stock.picking']
        ids_picking = self.mutation_order_id._get_ids_picking()
        picking_ids = obj_picking.browse(ids_picking)
        for picking in picking_ids :
            if picking.state == 'done' :
                raise osv.except_osv(('Tidak bisa cancel !'), ("Nomor picking '%s' sudah ditransfer, silahkan selesaikan proses mutasi dan lakukan mutasi balik. Pembatalan mutasi hanya bisa dilakukan jika belum dilakukan transfer !" %picking.name))
        return True
    
    @api.multi
    def validity_check(self):
        self.check_shipments()
    
    @api.multi
    def picking_cancel(self):
        obj_picking = self.env['stock.picking']
        ids_picking = self.mutation_order_id._get_ids_picking()
        picking_ids = obj_picking.browse(ids_picking)
        for picking_id in picking_ids :
            if picking_id.state != 'done' :
                picking_id.action_cancel()
                packing_id = self.env['wtc.stock.packing'].search([('picking_id','=',picking_id.id),('state','!=','cancelled')])
                if packing_id :
                    packing_id.action_cancel()
    
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
            self.validity_check()
            self.picking_cancel()
        self.mutation_order_id.action_cancel()
    
class wtc_account_invoice_cancel(models.Model):
    _name = "wtc.account.invoice.cancel"
    _description = "Account Invoice Cancel"
    
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
    invoice_id = fields.Many2one('account.invoice', 'Invoice')
    division = fields.Selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum')], 'Division')
    date = fields.Date('Date',default=_get_default_date)
    confirm_uid = fields.Many2one('res.users', string="Confirmed by", copy=False)
    confirm_date = fields.Datetime('Confirmed on', copy=False)
    approval_ids = fields.One2many('wtc.approval.line', 'transaction_id', string="Approval", domain=[('form_id','=','wtc.account.invoice.cancel')])
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
        ('unique_invoice_id', 'unique(invoice_id)', 'Invoice pernah diinput sebelumnya !')
        ]
    
    @api.model
    def create(self, values, context=None):
        invoice_id = self.env['account.invoice'].search([('id','=',values['invoice_id'])])
        values['name'] = "X" + invoice_id.name
        values['date'] = self._get_default_date_model()
        values['period_id'] = self.env['account.period'].find(dt=self._get_default_date_model().date()).id
        return super(wtc_account_invoice_cancel, self).create(values)
    
    def unlink(self, cr, uid, ids, context=None):
        invoice_cancel_id = self.browse(cr, uid, ids, context=context)
        if invoice_cancel_id.state != 'draft':
            raise osv.except_osv(('Invalid action !'), ('Tidak bisa dihapus jika state bukan Draft !'))
        return super(wtc_account_invoice_cancel, self).unlink(cr, uid, ids, context=context)
    
    @api.multi
    def check_payments(self):
        for line_id in self.invoice_id.move_id.line_id :
            if line_id.reconcile_id or line_id.reconcile_partial_id :
                raise osv.except_osv(("Perhatian !"), ("Invoice '%s' sudah dibayar, silahkan lakukan pembatalan Customer/Supplier Payment terlebih dahulu !")%self.invoice_id.number)
        return True
    
    @api.multi
    def validity_check(self):
        self.check_payments()
    
    @api.multi
    def create_account_move_line(self, move_id):
        ids_to_reconcile = []
        for line_id in self.invoice_id.move_id.line_id :
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
            self.validity_check()
            self.write({'state':'confirmed', 'date':self._get_default_date(), 'confirm_uid':self._uid, 'confirm_date':datetime.now(), 'period_id':self.env['account.period'].find(dt=self._get_default_date().date()).id})
            obj_acc_move = self.env['account.move']
            acc_move_line_obj = self.pool.get('account.move.line')
            branch_config_id = self.env['wtc.branch.config'].search([('branch_id','=',self.branch_id.id)])
            journal_id = branch_config_id.account_invoice_unit_cancel_journal_id
            if self.division == 'Sparepart' :
                journal_id = branch_config_id.account_invoice_sparepart_cancel_journal_id
            elif self.division == 'Umum' :
                journal_id = branch_config_id.account_invoice_umum_cancel_journal_id
            if not journal_id :
                raise osv.except_osv(("Perhatian !"), ("Tidak ditemukan Journal Pembatalan Invoice '%s' di Branch Config, silahkan konfigurasi ulang !"%self.division))
            move_id = obj_acc_move.create({
                'name': self.name,
                'journal_id': journal_id.id,
                'line_id': [],
                'period_id': self.period_id.id,
                'date': self._get_default_date(),
                'ref': self.invoice_id.number
                })
            to_reconcile_ids = self.create_account_move_line(move_id)
            for to_reconcile in to_reconcile_ids :
                acc_move_line_obj.reconcile(self._cr, self._uid, to_reconcile)
            self.write({'move_id':move_id.id})
            if journal_id.entry_posted :
                move_id.button_validate()
        
