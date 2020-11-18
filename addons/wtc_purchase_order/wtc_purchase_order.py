from openerp.osv import osv, fields, orm
from openerp.tools.translate import _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import calendar
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP

class wtc_purchase_order(osv.osv):
    _inherit = 'purchase.order'

    def _get_backorders(self, cr, uid, ids, res):
        re_fetch = False
        picking_ids = []
        for key, value in res.items():
            picking_ids = picking_ids + value

        if picking_ids :
            query = """
            SELECT a.id, b.id FROM stock_picking a JOIN stock_picking b ON b.backorder_id = a.id
                WHERE a.id in %s
                GROUP BY a.id, b.id
                   
            """
            cr.execute(query, (tuple(picking_ids), ))
            picks = cr.fetchall()

            for pick_id, backorder_id in picks:
                for key, value in res.items():
                    if pick_id in value and backorder_id not in value :
                        res[key].append(backorder_id)
                        re_fetch = True
            if re_fetch :
                res = self._get_backorders(cr, uid, ids, res)
        return res
    
    def _get_picking_ids(self, cr, uid, ids, field_names, args, context=None):
        res = super(wtc_purchase_order,self)._get_picking_ids(cr, uid, ids, field_names, args, context=context)
        res = self._get_backorders(cr, uid, ids, res)
        return res
    
    def _get_picking_type_ids(self, cr, uid, context=None):
        obj_user = self.pool.get('res.users').browse(cr, uid, uid)
        branch_ids = []
        for x in obj_user.area_id.branch_ids :
            branch_ids.append(x.id)
        if branch_ids :
            if len(branch_ids) > 1 :
                return False
            else :
                return self.pool.get('stock.picking.type').search(cr, uid, [
                                                                            ('branch_id','=',branch_ids[0]),
                                                                            ('code','=','incoming'),
                                                                            ])[0]
        return False
    
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids
    
    def _get_default_date(self,cr,uid,context=None):
        return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)
        
    _columns = {
                'branch_id':fields.many2one('wtc.branch','Branch', required=True),
                'division':fields.selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum')], 'Division', change_default=True, select=True, required=True),
                'purchase_order_type_id':fields.many2one('wtc.purchase.order.type','Type',required=True),
                'start_date':fields.date('Start Date'),
                'end_date':fields.date('End Date'),
                'po_ref':fields.char('PO Ref'),
                'dealer_id':fields.many2one('res.partner','Dealer'),
                'back_order':fields.char('Back Order'),
                'salesman_id':fields.many2one('res.users','Salesman'),
                'no_claim':fields.char('No. Claim'),
                'ship_to':fields.char('Ship To'),
                'delivery_date':fields.date('Delivery Date'),
                'customer_id':fields.many2one('res.partner','Customer'),
                'post_code':fields.char('Post Code'),
                'type_motor_id':fields.many2one('product.product','Type Motor'),
                'assembling':fields.char('Year of Assembling'),
                'of_the_road':fields.selection([('y','Y'),('n','N')],'Vehicle of The Road'),
                'return_service':fields.selection([('y','Y'),('n','N')],'Job Return Service'),
                'confirm_uid':fields.many2one('res.users',string="Confirmed by"),
                'confirm_date':fields.datetime('Confirmed on'),
                'cancel_uid':fields.many2one('res.users',string="Cancelled by"),
                'cancel_date':fields.datetime('Cancelled on'),      
                'date_order':fields.datetime('Order Date'),
                'picking_ids': fields.function(_get_picking_ids, method=True, type='one2many', relation='stock.picking', string='Picking List', help="This is the list of receipts that have been generated for this purchase order."),
                'is_cancelled':fields.boolean('Cancelled'),
                }
    
    _defaults = {
                 'name': '/',
                 'branch_id': _get_default_branch,
                 'salesman_id': lambda obj, cr, uid, context:uid,
                 'date_order':datetime.now(),
#                  'invoice_method': 'manual',
                 }
    
    def create(self, cr, uid, vals, context=None):
#         if not vals['order_line'] :
#             raise osv.except_osv(('Tidak bisa disimpan !'), ("Silahkan isi detail order terlebih dahulu"))
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'PO')
        vals['date_order'] = datetime.now()
        return super(wtc_purchase_order, self).create(cr, uid, vals, context=context)
    
    def has_stockable_product(self, cr, uid, ids, *args):
        res = super(wtc_purchase_order,self).has_stockable_product(cr,uid,ids,*args)
        for order in self.browse(cr, uid, ids):
            for order_line in order.order_line:
                if order_line.product_id and order_line.product_id.type in ('product', 'consu'):
                    return True
        return False
            
    def onchange_division(self, cr, uid, ids, branch_id, division, partner_id):
        res={}
        war={}
        res['purchase_order_type_id']=False
        
        if branch_id :
            branch_obj = self.pool.get('wtc.branch').browse(cr, uid, branch_id)
            if division == 'Unit':
                res['pricelist_id']=branch_obj.pricelist_unit_purchase_id
            elif division == 'Sparepart':
                res['pricelist_id']=branch_obj.pricelist_part_purchase_id
            elif partner_id :
                partner_obj = self.pool.get('res.partner').browse(cr, uid, partner_id)
                res['pricelist_id'] = partner_obj.property_product_pricelist_purchase
            if not res.get('pricelist_id',True) :
                war = {'title': _('Perhatian !'), 'message': _('Pricelist beli cabang belum ada, silahkan ditambahkan di Branch Configuration.')}
        else :
            res['pricelist_id']=False

        return {'value':res,'warning':war}
    
    def purchase_order_type_id_change(self, cr, uid, ids, purchase_order_type_id):
        po_type = self.pool.get('wtc.purchase.order.type').browse(cr, uid, purchase_order_type_id)
        res={}
        res['start_date']=False
        res['end_date']=False
        if po_type:
            res['start_date'] = po_type.get_date(po_type.date_start)
            res['end_date'] = po_type.get_date(po_type.date_end)
        return {'value':res}
    
    def _get_branch_journal_config(self,cr,uid,branch_id):
        result = {}
        branch_journal_id = self.pool.get('wtc.branch.config').search(cr,uid,[('branch_id','=',branch_id)])
        if not branch_journal_id:
            raise osv.except_osv(
                        _('Perhatian'),
                        _('Jurnal pembelian cabang belum dibuat, silahkan setting dulu.'))
            
        branch_journal = self.pool.get('wtc.branch.config').browse(cr,uid,branch_journal_id[0])
        if not(branch_journal.wtc_po_journal_unit_id and branch_journal.wtc_po_journal_sparepart_id and branch_journal.wtc_po_journal_umum_id and branch_journal.wtc_po_journal_blind_bonus_beli_id and branch_journal.wtc_po_account_blind_bonus_beli_dr_id and branch_journal.wtc_po_account_blind_bonus_beli_cr_id and branch_journal.wtc_po_account_blind_bonus_performance_dr_id and branch_journal.wtc_po_account_blind_bonus_performance_cr_id):
            raise osv.except_osv(
                        _('Perhatian'),
                        _('Jurnal pembelian cabang belum lengkap, silahkan setting dulu.'))
        result.update({
                  'wtc_po_journal_unit_id':branch_journal.wtc_po_journal_unit_id,
                  'wtc_po_journal_sparepart_id':branch_journal.wtc_po_journal_sparepart_id,
                  'wtc_po_journal_umum_id':branch_journal.wtc_po_journal_umum_id,
                  'wtc_po_journal_blind_bonus_beli_id':branch_journal.wtc_po_journal_blind_bonus_beli_id,
                  'wtc_po_account_blind_bonus_beli_dr_id':branch_journal.wtc_po_account_blind_bonus_beli_dr_id,
                  'wtc_po_account_blind_bonus_beli_cr_id':branch_journal.wtc_po_account_blind_bonus_beli_cr_id,
                  'wtc_po_account_blind_bonus_performance_dr_id':branch_journal.wtc_po_account_blind_bonus_performance_dr_id,
                  'wtc_po_account_blind_bonus_performance_cr_id':branch_journal.wtc_po_account_blind_bonus_performance_cr_id,
                  })
        
        return result
    
    def _prepare_invoice(self, cr, uid, order, line_ids, context=None):
        journal_config = self._get_branch_journal_config(cr, uid, order.branch_id.id)
        result = super(wtc_purchase_order, self)._prepare_invoice(cr, uid, order, line_ids, context)
        obj_model = self.pool.get('ir.model')
        obj_model_id = obj_model.search(cr,uid,[ ('model','=',self.__class__.__name__) ])
        
        if order.division == 'Unit':
            result['journal_id'] = journal_config['wtc_po_journal_unit_id'].id
            result['account_id'] = journal_config['wtc_po_journal_unit_id'].default_credit_account_id.id
        elif order.division == 'Sparepart':
            result['journal_id'] = journal_config['wtc_po_journal_sparepart_id'].id
            result['account_id'] = journal_config['wtc_po_journal_sparepart_id'].default_credit_account_id.id
        elif order.division == 'Umum':
            result['journal_id'] = journal_config['wtc_po_journal_umum_id'].id 
            result['account_id'] = journal_config['wtc_po_journal_umum_id'].default_credit_account_id.id
        result['branch_id'] = order.branch_id.id
        result['division'] = order.division
        result['tipe'] = 'purchase'
        result['model_id'] = obj_model_id[0]
        result['transaction_id'] = order.id
        return result
    
    def _prepare_order_line_move(self, cr, uid, order, order_line, picking_id, group_id, context=None):
        ''' prepare the stock move data from the PO line. This function returns a list of dictionary ready to be used in stock.move's create()'''
        product_uom = self.pool.get('product.uom')
        price_unit = order_line.price_unit
        if order_line.product_uom.id != order_line.product_id.uom_id.id:
            price_unit *= order_line.product_uom.factor / order_line.product_id.uom_id.factor
        if order.currency_id.id != order.company_id.currency_id.id:
            #we don't round the price_unit, as we may want to store the standard price with more digits than allowed by the currency
            price_unit = self.pool.get('res.currency').compute(cr, uid, order.currency_id.id, order.company_id.currency_id.id, price_unit, round=False, context=context)
        res = []
        move_template = {
            'branch_id': order.branch_id.id,
            'categ_id': order_line.product_id.categ_id.id,
            'name': order_line.name or '',
            'product_id': order_line.product_id.id,
            'product_uom': order_line.product_uom.id,
            'product_uos': order_line.product_uom.id,
            'date': order.date_order,
            'date_expected': order.end_date,
            'location_id': order.picking_type_id.default_location_src_id.id,
            'location_dest_id': order.location_id.id,
            'picking_id': picking_id,
            'partner_id': order.dest_address_id.id or order.partner_id.id,
            'move_dest_id': False,
            'state': 'draft',
            'purchase_line_id': order_line.id,
            'company_id': order.company_id.id,
            'price_unit': price_unit,
            'picking_type_id': order.picking_type_id.id,
            'group_id': group_id,
            'procurement_id': False,
            'origin': order.name,
            'route_ids': order.picking_type_id.warehouse_id and [(6, 0, [x.id for x in order.picking_type_id.warehouse_id.route_ids])] or [],
            'warehouse_id':order.picking_type_id.warehouse_id.id,
            'invoice_state': order.invoice_method == 'picking' and '2binvoiced' or 'none',
        }

        diff_quantity = order_line.product_qty
        for procurement in order_line.procurement_ids:
            procurement_qty = product_uom._compute_qty(cr, uid, procurement.product_uom.id, procurement.product_qty, to_uom_id=order_line.product_uom.id)
            tmp = move_template.copy()
            tmp.update({
                'product_uom_qty': min(procurement_qty, diff_quantity),
                'product_uos_qty': min(procurement_qty, diff_quantity),
                'move_dest_id': procurement.move_dest_id.id,  #move destination is same as procurement destination
                'group_id': procurement.group_id.id or group_id,  #move group is same as group of procurements if it exists, otherwise take another group
                'procurement_id': procurement.id,
                'invoice_state': procurement.rule_id.invoice_state or (procurement.location_id and procurement.location_id.usage == 'customer' and procurement.invoice_state=='picking' and '2binvoiced') or (order.invoice_method == 'picking' and '2binvoiced') or 'none', #dropship case takes from sale
                'propagate': procurement.rule_id.propagate,
            })
            diff_quantity -= min(procurement_qty, diff_quantity)
            res.append(tmp)
        #if the order line has a bigger quantity than the procurement it was for (manually changed or minimal quantity), then
        #split the future stock move in two because the route followed may be different.
        if diff_quantity > 0:
            move_template['product_uom_qty'] = diff_quantity
            move_template['product_uos_qty'] = diff_quantity
            res.append(move_template)
        return res
    
    def action_picking_create(self, cr, uid, ids, context=None):
        for order in self.browse(cr, uid, ids):
            if order.division is not 'Umum' :
                picking_vals = {
                    'picking_type_id': order.picking_type_id.id,
                    'partner_id': order.partner_id.id,
                    'date': order.date_order,
                    'start_date': order.start_date,
                    'end_date': order.end_date,
                    'origin': order.name,
                    'branch_id': order.branch_id.id,
                    'division': order.division,
                    'transaction_id': order.id,
                    'model_id': self.pool.get('ir.model').search(cr,uid,[('model','=',order.__class__.__name__)])[0],
                }
                picking_id = self.pool.get('stock.picking').create(cr, uid, picking_vals, context=context)
                self._create_stock_moves(cr, uid, order, order.order_line, picking_id, context=context)
    
    def effective_date_change(self, cr, uid, ids, start_date, end_date, context=None):
        value = {}
        warning = {}
        if start_date and datetime.strptime(start_date, "%Y-%m-%d").date() < self._get_default_date(cr, uid, context).date() :
            warning = {'title':'Perhatian','message':'Tanggal tidak boleh kurang dari tanggal hari ini !'}
            value['start_date'] = False
        elif start_date and end_date and datetime.strptime(start_date, "%Y-%m-%d").date() > datetime.strptime(end_date, "%Y-%m-%d").date() :
            warning = {'title':'Perhatian','message':'End Date tidak boleh sama atau kurang dari Start Date !'}
            value['end_date'] = False
        if end_date and not warning :
            value['minimum_planned_date'] = end_date
        return {'value':value, 'warning':warning}
    
    def onchange_partner_id(self, cr, uid, ids, partner_id, context=None):
        result = super(wtc_purchase_order,self).onchange_partner_id(cr, uid, ids, partner_id, context=context)
        if result.get('value',False) :
            if result['value'].get('pricelist_id',False) :
                if context.get('division') != 'Umum' :
                    result['value'].pop('pricelist_id', None)
                    
        return result
    
    def default_get(self, cr, uid, fields, context=None):
         context = context or {}
         res = super(wtc_purchase_order, self).default_get(cr, uid, fields, context=context)
         if 'picking_type_id' in fields:
             res.update({'picking_type_id': self._get_picking_type_ids(cr, uid)})
         return res
    
    def onchange_picking_type_id(self, cr, uid, ids, id_branch, id_picking_type, context=None):
        value = {}
        warning = {}
        value['picking_type_id'] = False
        branch_id = self.pool.get('wtc.branch').browse(cr, uid, id_branch)
        obj_picking_type = self.pool.get('stock.picking.type')
        picking_type_ids = obj_picking_type.search(cr, uid, [
                                                            ('code','=','incoming'),
                                                            ('branch_id','=',id_branch)
                                                            ])
        id_picking_type = False
        if picking_type_ids :
        	id_picking_type = picking_type_ids[0]
        if id_branch :
            if id_picking_type :
                value['picking_type_id'] = id_picking_type
            else :
                warning = {"title":"Perhatian", "message":"Tidak ditemukan type picking 'Receipts' untuk '%s'\nsilahkan buat di menu Warehouse > Type Of Operation" %branch_id.name}
                value['picking_type_id'] = False
                value['branch_id'] = False
        if id_picking_type :
            picktype = self.pool.get("stock.picking.type").browse(cr, uid, id_picking_type, context=context)
            if picktype.default_location_dest_id :
                value.update({'location_id': picktype.default_location_dest_id.id})
            value.update({'related_location_id': picktype.default_location_dest_id and picktype.default_location_dest_id.id or False})
        return {'value': value, 'warning':warning}
    
    def wkf_confirm_order(self, cr, uid, ids, context=None):
        self.write(cr,uid,ids,{'confirm_uid':uid,'confirm_date':datetime.now(),'date_order':datetime.now()})        
        vals = super(wtc_purchase_order,self).wkf_confirm_order(cr,uid,ids,context=context)
        return vals
    
    def action_cancel(self, cr, uid, ids, context=None):
        vals = super(wtc_purchase_order,self).action_cancel(cr,uid,ids,context=context)
        self.write(cr,uid,ids,{'cancel_uid':uid,'cancel_date':datetime.now()})
        return vals        
    
    def write(self, cr, uid, ids, vals, context=None):
        vals.get('order_line', []).sort(reverse=True)
        return super(wtc_purchase_order, self).write(cr, uid, ids, vals, context=context)
    
    def test_moves_done(self, cr, uid, ids, context=None):
        for purchase in self.browse(cr, uid, ids, context=context):
            if not purchase.picking_ids :
                return False
            for picking in purchase.picking_ids:
                if picking.state != 'done':
                    return False
        return True
    
    def reverse(self, cr, uid, ids, context=None):
        ids_picking = self._get_ids_picking(cr, uid, ids, context)
        ids_move = self.pool.get('stock.move').search(cr, uid, [
            ('picking_id','in',ids_picking),
            ('origin_returned_move_id','!=',False),
            ('state','!=','cancel')
            ])
        if ids_move :
            return True
        return False
    
    def is_po_done(self, cr, uid, ids, context=None):
        inv_done = False
        po_id = self.browse(cr, uid, ids, context=context)
        reverse = self.reverse(cr, uid, ids, context)
        picking_done = self.test_moves_done(cr, uid, ids, context)
        inv_ids = self._get_invoice_ids(cr, uid, ids, context)
        for inv in inv_ids :
            if inv.tipe in ('purchase') and inv.state == 'paid' :
                inv_done = True
        if inv_done and not po_id.is_cancelled and picking_done and not reverse :
            return self.signal_workflow(cr, uid, ids, 'action_done')
        return True
    
   
class wtc_purchase_order_line(osv.osv):
    _inherit = "purchase.order.line"
    
    def _get_price(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for purchase_order_line in self.browse(cr, uid, ids, context=context):
            price_unit_show=purchase_order_line.price_unit
            
            res[purchase_order_line.id]=price_unit_show
        return res
    
    _columns = {
                'date_planned': fields.date('Scheduled Date', select=True),
                'received':fields.float('Received', digits=(16,0)),
                'categ_id':fields.many2one('product.category','Category',required=True),
                'price_unit_show':fields.function(_get_price,string='Unit Price'),
                'taxes_id_show': fields.many2many('account.tax', 'purchase_order_taxe', 'ord_id', 'tax_id', 'Taxes'),
                'qty_invoiced': fields.float('Invoiced', digits=(16,0)),
                }
    
    _sql_constraints = [('product_id_unique', 'unique(order_id,product_id)', 'Tidak boleh ada product yg sama dalam satu transaksi !')]

    def change_tax(self,cr,uid,ids,tax_id,context=None):
        return {'value':{'taxes_id_show':tax_id}}
        
    def category_change(self, cr, uid, ids, categ_id, branch_id, division, pricelist_id):
        if not branch_id or not division :
            raise osv.except_osv(('No Branch or Division Defined!'), ('Sebelum menambah detil transaksi,\n harap isi branch dan division terlebih dahulu.'))
        if division in ('Unit', 'Sparepart') and not pricelist_id :
            raise osv.except_osv(('No Purchase Pricelist Defined!'), ('Sebelum menambah detil transaksi,\n harap set pricelist terlebih dahulu di Branch Configuration.'))
        dom = {}
        if categ_id:
            categ_ids = self.pool.get('product.category').get_child_by_ids(cr,uid,categ_id)
            dom['product_id']=[('categ_id','in',categ_ids),('purchase_ok','=',True)]
        return {'domain':dom}
    
    def price_unit_change(self, cr, uid, ids, price_unit):
        value = {}
        if not price_unit:
           value ={'price_unit_show':0}
        else:
            value={'price_unit_show':price_unit}
        return {'value':value}
    
    def onchange_product_id(self, cr, uid, ids, pricelist_id, product_id, qty, uom_id,
            partner_id, date_order=False, fiscal_position_id=False, date_planned=False,
            name=False, price_unit=False, state='draft', context=None):
        res = super(wtc_purchase_order_line, self).onchange_product_id(cr, uid, ids, pricelist_id, product_id, qty, uom_id,
            partner_id, date_order=date_order, fiscal_position_id=fiscal_position_id, date_planned=date_planned,
            name=name, price_unit=price_unit, state='draft', context=context)
        pricelist = self.pool.get('product.pricelist').browse(cr,uid,pricelist_id)
        description = self.pool.get('product.product').browse(cr, uid, product_id).description
        res['value'].update({'name': description})
        
        return res
    
class wtc_purchase_line_invoice(osv.osv_memory):
    _inherit = 'purchase.order.line_invoice'
    
    def makeInvoices(self, cr, uid, ids, context=None):

        """
             To get Purchase Order line and create Invoice
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param context: A standard dictionary
             @return : retrun view of Invoice
        """

        if context is None:
            context={}

        record_ids =  context.get('active_ids',[])
        if record_ids:
            res = False
            invoices = {}
            invoice_obj = self.pool.get('account.invoice')
            purchase_obj = self.pool.get('purchase.order')
            purchase_line_obj = self.pool.get('purchase.order.line')
            invoice_line_obj = self.pool.get('account.invoice.line')
            account_jrnl_obj = self.pool.get('account.journal')

            def multiple_order_invoice_notes(orders):
                branch_id = False
                division = False
                partner_id = False
                notes = ""
                for order in orders:
                    notes += "%s \n" % order.notes
                    if branch_id != False and branch_id != order.branch_id.id :
                        raise osv.except_osv(('Perhatian !'), ("Branch harus sama, silahkan cek kembali"))
                    if division != False and division != order.division :
                        raise osv.except_osv(('Perhatian !'), ("Division harus sama, silahkan cek kembali"))
                    if partner_id != False and partner_id != order.partner_id.id :
                        raise osv.except_osv(('Perhatian !'), ("Supplier harus sama, silahkan cek kembali"))
                    branch_id = order.branch_id.id
                    division = order.division
                    partner_id = order.partner_id.id
                    
                return notes

            def make_invoice_by_partner(partner, orders, lines_ids):
                """
                    create a new invoice for one supplier
                    @param partner : The object partner
                    @param orders : The set of orders to add in the invoice
                    @param lines : The list of line's id
                """
                name = orders and orders[0].name or ''
#                 journal_id = account_jrnl_obj.search(cr, uid, [('type', '=', 'purchase')], context=None)
#                 journal_id = journal_id and journal_id[0] or False
#                 a = partner.property_account_payable.id
                
                journal_config = self.pool.get('purchase.order')._get_branch_journal_config(cr, uid, orders[0].branch_id.id)
                
                if orders[0].division == 'Unit' :
                    journal_id = journal_config['wtc_po_journal_unit_id']
                    account_id = journal_config['wtc_po_journal_unit_id'].default_credit_account_id
                elif orders[0].division == 'Sparepart' :
                    journal_id = journal_config['wtc_po_journal_sparepart_id']
                    account_id = journal_config['wtc_po_journal_sparepart_id'].default_credit_account_id
                else :
                    journal_id = journal_config['wtc_po_journal_umum_id']
                    account_id = journal_config['wtc_po_journal_umum_id'].default_credit_account_id
                
                inv = {
                    'branch_id': orders[0].branch_id.id,
                    'division': orders[0].division,
                    'name': False,
                    'origin': False,
                    'type': 'in_invoice',
                    'tipe': 'purchase',
                    'journal_id':journal_id.id,
                    'reference' : partner.ref,
                    'account_id': account_id.id,
                    'partner_id': partner.id,
                    'invoice_line': [(6,0,lines_ids)],
                    'currency_id' : orders[0].currency_id.id,
                    'comment': multiple_order_invoice_notes(orders),
                    'payment_term': orders[0].payment_term_id.id,
                    'fiscal_position': partner.property_account_position.id
                }
                
                inv_id = invoice_obj.create(cr, uid, inv)
                for order in orders:
                    order.write({'invoice_ids': [(4, inv_id)]})
                
                return inv_id

            for line in purchase_line_obj.browse(cr, uid, record_ids, context=context):
                if (not line.invoiced) and (line.state not in ('draft', 'cancel')):
                    if not line.partner_id.id in invoices:
                        invoices[line.partner_id.id] = []
                    acc_id = purchase_obj._choose_account_from_po_line(cr, uid, line, context=context)
                    inv_line_data = purchase_obj._prepare_inv_line(cr, uid, acc_id, line, context=context)
                    inv_line_data.update({'origin': line.order_id.name, 'quantity': line.product_qty-line.qty_invoiced})
                    inv_id = invoice_line_obj.create(cr, uid, inv_line_data, context=context)
                    purchase_line_obj.write(cr, uid, [line.id], {'invoice_lines': [(4, inv_id)]})
                    invoices[line.partner_id.id].append((line,inv_id))
            
            order_id = False
            partner_id = False
            for key, value in invoices.items():
                if partner_id != False and partner_id != key :
                    raise osv.except_osv(('Perhatian !'), ("Supplier harus sama, silahkan cek kembali"))
                partner_id = key
                for inv_id in value :
                    if order_id != False and order_id != inv_id[0].order_id.id :
                        raise osv.except_osv(('Perhatian !'), ("Satu invoice hanya bisa satu PO, silahkan cek kembali"))
                    order_id = inv_id[0].order_id.id
            
            res = []
            for result in invoices.values():
                il = map(lambda x: x[1], result)
                orders = list(set(map(lambda x : x[0].order_id, result)))
                
                # Supplier, Branch, Division harus sama
                branch_id = False
                division = False
                for order in orders:
                    if branch_id != False and branch_id != order.branch_id.id :
                        raise osv.except_osv(('Perhatian !'), ("Branch harus sama, silahkan cek kembali"))
                    if division != False and division != order.division :
                        raise osv.except_osv(('Perhatian !'), ("Division harus sama, silahkan cek kembali"))
                    branch_id = order.branch_id.id
                    division = order.division
                
                res.append(make_invoice_by_partner(orders[0].partner_id, orders, il))

            # compute the invoice
            invoice_obj.button_compute(cr, uid, res, context=context, set_total=True)
            
        return {
            'domain': "[('id','in', ["+','.join(map(str,res))+"])]",
            'name': _('Supplier Invoices'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'view_id': False,
            'context': "{'type':'in_invoice', 'journal_type': 'purchase'}",
            'type': 'ir.actions.act_window'
        }
        