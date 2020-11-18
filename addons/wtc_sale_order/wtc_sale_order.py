import time
from datetime import datetime
import string 
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import api
from openerp.osv.expression import get_unaccent_wrapper
from openerp import workflow

class wtc_sale_order(osv.osv):
    
    _inherit = 'sale.order'

    STATES = {
        'sent':['state','write_uid','write_date','faktur_pajak_id'],
        'progress':['state','write_uid','write_date','faktur_pajak_id','is_cancelled','cancel_uid','cancel_date','approval_ids'], #'message_last_post'
        'cancel':[],
        'done':['state','write_date','write_uid','cancel_uid','cancel_date','is_cancelled','faktur_pajak_id','approval_ids'],
    }
    
    def _get_default_date(self,cr,uid,context=None):
        return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=None)
    
    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        res = super(wtc_sale_order,self)._amount_all(cr, uid, ids, field_name, arg, context=context)
        total_discount = amount_untaxed = amount_taxed = amount_total = 0.0
        
        for discount in self.browse(cr,uid,ids):
            total_discount = discount.discount_cash+discount.discount_lain+discount.discount_program
            if total_discount>0:
                amount_untaxed = res[ids[0]].get('amount_untaxed',0)-total_discount
                amount_taxed = amount_untaxed*0.1
                amount_total = amount_untaxed+amount_taxed
                res[ids[0]].update({'amount_tax':amount_taxed,'amount_total':amount_total})
                
        return res
    
    def _get_discount_cash(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for disc in self.read(cr, uid, ids, ['discount_cash']):
            discount_cash_show = disc['discount_cash']
            res[disc['id']] = discount_cash_show
        return res
    
    def _get_total_inv(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for inv in self.read(cr, uid, ids, ['total_invoiced']):
            total_invoiced = inv['total_invoiced']
            res[inv['id']] = total_invoiced
        return res
    
    def test_moves_done(self, cr, uid, ids, context=None):
        for sale in self.browse(cr, uid, ids, context=context):
            if not sale.picking_ids :
                return False
            for picking in sale.picking_ids:
                if picking.state != 'done':
                    return False
        return True
    
    
    _columns = {
                'branch_id': fields.many2one('wtc.branch','Branch',required=True),
                'division':fields.selection([('Unit','Unit'),('Sparepart','Sparepart')], 'Division', change_default=True, select=True, required=True),
                'credit_limit_unit': fields.related('partner_id','credit_limit_unit',relation='res.partner',string='Credit Limit Unit'),
                'credit_limit_sparepart': fields.related('partner_id','credit_limit_sparepart',relation='res.partner',string='Credit Limit Sparepart'),
                'total_invoiced_show': fields.function(_get_total_inv, string='Total Invoiced'),
                'total_invoiced': fields.float(),
                'discount_cash_persen': fields.float('Discount Cash (%)'),
                'discount_cash': fields.float(),
                'discount_cash_show': fields.function(_get_discount_cash, string='Discount Cash'),
                'discount_program': fields.float('Discount Program'),
                'discount_lain': fields.float('Discount Lain'),
                'distribution_id': fields.many2one('wtc.stock.distribution','Stock Distribution'),
                'confirm_uid':fields.many2one('res.users',string="Confirmed by"),
                'confirm_date':fields.datetime('Confirmed on'),
                'cancel_uid':fields.many2one('res.users',string="Cancelled by"),
                'cancel_date':fields.datetime('Cancelled on'),     
                'partner_id': fields.many2one('res.partner', 'Customer', readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, required=True, change_default=True, select=True, track_visibility='always'),
                'pajak_gabungan':fields.boolean('Faktur Pajak Gabungan',copy=False),   
                'faktur_pajak_id':fields.many2one('wtc.faktur.pajak.out',string='No Faktur Pajak',copy=False),
                'is_cancelled':fields.boolean('Cancelled'),
                'source_location_id': fields.many2one('stock.location',string='Location'),                                               
                }
    
    _defaults = {
        'warehouse_id': False,
        # 'date_order':_get_default_date
    }

    def _register_hook(self, cr):
        selection = self._columns['state'].selection
        if ('unused','Unused') not in selection :
            self._columns['state'].selection.append(('unused','Unused'))
        return super(wtc_sale_order, self)._register_hook(cr)

    def unlink(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids, context={})[0]
        if val.state == 'draft' :
            raise osv.except_osv(('Perhatian !'), ("Sale Order tidak bisa dihapus. Gunakan tombol Unused."))
        else : #if val.state not in ['draft','unused']:
            raise osv.except_osv(('Invalid action !'), ('Cannot delete a Sale Order which is in state \'%s\'!') % (val.state))
        #else :
        #    val.write({'state':'draft'}) #diwrite jadi draft karena di object bawaannya hanya bisa dihapus jika state in ('draft','cancel')
        return super(wtc_sale_order, self).unlink(cr, uid, ids, context=context)
    
    def discount_cash_change(self, cr, uid, ids, discount_cash_persen, amount_untaxed):
        if discount_cash_persen > 100:
            return {'value':{'discount_cash_persen':0, 'discount_cash': 0}, 'warning': {'title': 'perhatian!', 'message':'maksimal discount cash 100%'}}
        elif discount_cash_persen < 0:
            return {'value':{'discount_cash_persen':0, 'discount_cash': 0}, 'warning': {'title': 'perhatian!', 'message': 'tidak boleh input nilai negatif'}}
        else:
            discount_cash = (discount_cash_persen*amount_untaxed)/100
            return {'value':{'discount_cash': discount_cash,'discount_cash_show':discount_cash }}
        
    
    def onchange_branch(self,cr,uid,ids,branch_id):
        warehouse_ids = self.pool.get('stock.warehouse').search(cr, uid, [('branch_id', '=', branch_id)])
        if not warehouse_ids:
            return False
        return {'value':{'warehouse_id':warehouse_ids[0]}}
    
    def create(self, cr, uid, vals, context=None):
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'SO')
        sale_order = super(wtc_sale_order, self).create(cr, uid, vals, context=context)
        res = self.browse(cr,uid,sale_order) 
        if res.amount_tax :
            res.write({'pajak_gabungan':True})
        return sale_order
    
    def _invoice_total(self, cr, uid, ids, partner_id, division, context=None):
        invoice_total = 0.0
        sale_order = self.browse(cr,uid,ids)
        obj_inv = self.pool.get('account.invoice')
        
        if division=='Unit':
            tipe = 'md_sale_unit'
        elif division=='Sparepart':
            tipe='md_sale_sparepart'
            
        domain = [('partner_id', 'child_of', partner_id),('division','=',division),('state','=','open'),('tipe','=',tipe)]
        invoice_ids = obj_inv.search(cr, uid, domain, context=context)
        invoices = obj_inv.browse(cr, uid, invoice_ids, context=context)
        invoice_total = sum(inv.residual for inv in invoices)
        return invoice_total
    
    def onchange_partner_id_new(self, cr, uid, ids, part, division, context=None):
        res = self.onchange_partner_id(cr, uid, ids, part, context)
               
        if not (part and division):
            return {'value': {'pricelist_id':False,'partner_invoice_id': False, 'partner_shipping_id': False,  'payment_term': False, 'fiscal_position': False}}
        partner_obj = self.pool.get('res.partner').browse(cr,uid,part)
        if partner_obj:
            total_inv = self._invoice_total(cr,uid,ids,part,division)
            res['value'].update({'total_invoiced':total_inv,'total_invoiced_show':total_inv,'credit_limit_unit':partner_obj.credit_limit_unit,'credit_limit_sparepart':partner_obj.credit_limit_sparepart})
        
        if not (res['value'].get('pricelist_id',False)):
            md_id = self.pool.get('wtc.branch').search(cr,uid,[('code','=','MML'),('branch_type','=','MD')])
            if not md_id:
                res.update({'value':{'pricelist_id':False,'partner_id':False},'warning':{'title':'Perhatian','message':'Tidak ditemukan pricelist jual!'}})
            else:
                pcc_id = self.pool.get('pricelist.config.cabang').search(cr,uid,[
                    ('branch_id','=',md_id[0])
                    ('partner_id','=',part),
                    ('division','=',division)],limit=1)
                if division == 'Unit':
                    if pcc_id:
                        pricelist_md = self.pool.get('pricelist.config.cabang').browse(cr,uid,pcc_id[0])['md_pricelist_id']
                    else:
                        pricelist_md = self.pool.get('wtc.branch').browse(cr,uid,md_id[0])['pricelist_unit_sales_id']
                elif division == 'Sparepart':
                    if pcc_id:
                        pricelist_md = self.pool.get('pricelist.config.cabang').browse(cr,uid,pcc_id[0])['md_pricelist_id']
                    else:
                        pricelist_md = self.pool.get('wtc.branch').browse(cr,uid,md_id[0])['pricelist_part_sales_id']

                if pricelist_md and pricelist_md.id:
                    res['value'].update({'pricelist_id':pricelist_md.id})
                else:
                    res.update({'value':{'pricelist_id':False,'partner_id':False},'warning':{'title':'Perhatian','message':'Tidak ditemukan pricelist jual, setting Price List Jual Unit terlebih dahulu !'}})
        return res
    
   
    def _get_default_location_delivery_sales(self,cr,uid,ids,context=None):
        default_location_id = {}
        obj_picking_type = self.pool.get('stock.picking.type')
        for val in self.browse(cr,uid,ids):
            picking_type_id = obj_picking_type.search(cr,uid,[
                                                              ('branch_id','=',val.branch_id.id),
                                                              ('code','=','outgoing')
                                                              ])
            
           
            if picking_type_id:
                for pick_type in obj_picking_type.browse(cr,uid,picking_type_id[0]):
                    if not pick_type.default_location_dest_id.id :
                         raise osv.except_osv(('Perhatian !'), ("Location destination Belum di Setting"))
                    default_location_id.update({
                        'picking_type_id':pick_type.id,
                        'source':pick_type.default_location_src_id.id,
                        'destination': pick_type.default_location_dest_id.id,
                    })
            else:
               raise osv.except_osv(('Error !'), ('Tidak ditemukan default lokasi untuk penjualan di konfigurasi cabang \'%s\'!') % (val.branch_id.name,)) 
        return default_location_id
    
    def _prepare_order_line_procurement(self, cr, uid, order, line, group_id=False, context=None):
        vals = super(wtc_sale_order, self)._prepare_order_line_procurement(cr, uid, order, line, group_id=group_id, context=context)
        location = self._get_default_location_delivery_sales(cr,uid,order.id)
        procurement_rule_id = self.pool.get('procurement.rule').search(cr, uid, [('warehouse_id','=',order.warehouse_id.id),
                                                                           ('picking_type_id','=', location['picking_type_id'])
                                                                           ])
        if procurement_rule_id:
            vals['rule_id'] = procurement_rule_id[0]
        vals['location_id'] = location['destination']
        return vals
    
    def _get_branch_journal_config(self,cr,uid,branch_id):
        result = {}
        branch_journal_id = self.pool.get('wtc.branch.config').search(cr,uid,[('branch_id','=',branch_id)])
        if not branch_journal_id:
            raise osv.except_osv(
                        _('Perhatian'),
                        _('Jurnal penjualan cabang belum dibuat, silahkan setting dulu.'))
            
        branch_journal = self.pool.get('wtc.branch.config').browse(cr,uid,branch_journal_id[0])
        if not(branch_journal.wtc_so_journal_unit_id and branch_journal.wtc_so_journal_sparepart_id and branch_journal.wtc_so_journal_bind_bonus_jual_id):
            raise osv.except_osv(
                        _('Perhatian'),
                        _('Jurnal penjualan cabang belum lengkap, silahkan setting dulu.'))
        result.update({
                  'wtc_so_journal_unit_id':branch_journal.wtc_so_journal_unit_id,
                  'wtc_so_journal_sparepart_id':branch_journal.wtc_so_journal_sparepart_id,
                  'wtc_so_journal_bind_bonus_jual_id': branch_journal.wtc_so_journal_bind_bonus_jual_id,
                  })
        
        return result
    
    def _prepare_invoice(self, cr, uid, order, lines, context=None):
        obj_model = self.pool.get('ir.model')
        obj_model_id = obj_model.search(cr,uid,[ ('model','=',self.__class__.__name__) ])
        journal_config = self._get_branch_journal_config(cr, uid, order.branch_id.id)
        invoice = super(wtc_sale_order,self)._prepare_invoice(cr, uid, order, lines, context=context)
        if order.division=='Unit':
            tipe = 'md_sale_unit'
        elif order.division=='Sparepart':
            tipe='md_sale_sparepart'
        invoice.update({
                'branch_id':order.branch_id.id,
                'division':order.division,
                'tipe': tipe,
                'model_id': obj_model_id[0],
                'transaction_id':order.id,
                })
        
        if order.division == 'Unit':
            invoice['journal_id'] = journal_config['wtc_so_journal_unit_id'].id
            invoice['account_id'] = journal_config['wtc_so_journal_unit_id'].default_debit_account_id.id
        elif order.division == 'Sparepart':
            invoice['journal_id'] = journal_config['wtc_so_journal_sparepart_id'].id
            invoice['account_id'] = journal_config['wtc_so_journal_sparepart_id'].default_debit_account_id.id
            
        if order.discount_cash>0 or order.discount_program>0 or order.discount_lain>0:
            invoice.update({
                            'discount_cash':order.discount_cash,
                            'discount_program':order.discount_program,
                            'discount_lain':order.discount_lain
                            })
        
       
        return invoice
    
    def _make_invoice(self, cr, uid, order, lines, context=None):
        result = super(wtc_sale_order,self)._make_invoice(cr, uid, order, lines, context=context)
        workflow.trg_validate(uid, 'account.invoice', result, 'invoice_open', cr)
        return result
    
    def action_ship_create(self, cr, uid, ids, context=None):
        res = super(wtc_sale_order,self).action_ship_create(cr, uid, ids, context=context)
        self.signal_workflow(cr, uid, ids, 'manual_invoice')
        return res
    
    def action_invoice_bb_jual_create(self,cr,uid,order,total_qty):
        if order.branch_id.blind_bonus_jual<=0:
            raise osv.except_osv(('Perhatian'), ('Amount Blind Bonus Main Dealer tidak boleh <=0, silahkan konfigurasi ulang'))
        
        obj_model = self.pool.get('ir.model')
        obj_model_id = obj_model.search(cr,uid,[ ('model','=',self.__class__.__name__) ])
        journal_config = self._get_branch_journal_config(cr,uid,order.branch_id.id)
        
        inv_bb_line_vals = [(0, 0, {
                'name': 'Blind Bonus Jual '+order.name,
                'quantity': total_qty,
                'origin': order.name,
                'price_unit': order.branch_id.blind_bonus_jual,
                'account_id': journal_config['wtc_so_journal_bind_bonus_jual_id'].default_debit_account_id.id
                })]
            
        inv_bb_vals = {
            'name': order.name,
            'origin': order.name,
            'branch_id': order.branch_id.id,
            'division': order.division,
            'partner_id': order.partner_id.id,
            'date_invoice': self._get_default_date(cr,uid),
            'document_date': self._get_default_date(cr,uid),
            'reference_type': 'none',
            'type': 'in_invoice',
            #'payment_term':val.payment_term,
            'tipe': 'blind_bonus_jual',
            'journal_id': journal_config['wtc_so_journal_bind_bonus_jual_id'].id,
            'account_id': journal_config['wtc_so_journal_bind_bonus_jual_id'].default_credit_account_id.id,
            'invoice_line': inv_bb_line_vals,
            'model_id': obj_model_id[0],
            'transaction_id':order.id,
            }
        id_inv_bb = self.pool.get('account.invoice').create(cr, uid, inv_bb_vals)
        workflow.trg_validate(uid, 'account.invoice', id_inv_bb, 'invoice_open', cr)
        return id_inv_bb
            
    def action_button_confirm(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'date_order':datetime.now(),'confirm_uid':uid,'confirm_date':datetime.now()})        
        obj_picking = self.pool.get('stock.picking')
        order = self.browse(cr,uid,ids)
        total_qty = 0
        qty = {}
        approved_qty = {}
        if order.state == 'approved' :
            for x in order.order_line :
                qty[x.product_id] = qty.get(x.product_id,0) + x.product_uom_qty
            for x in order.distribution_id.distribution_line :
                qty[x.product_id] = qty.get(x.product_id,0) + x.qty
                approved_qty[x.product_id] = approved_qty.get(x.product_id,0) + x.approved_qty
                if (approved_qty[x.product_id] - qty[x.product_id]) >= 0 :
                    x.write({'qty':qty[x.product_id]})
                else :
                    raise osv.except_osv(('Perhatian !'), ("Quantity Product '%s' melebihi Approved Qty"%x.product_id.name_template))
        
        if all(x.approved_qty - x.qty == 0 for x in order.distribution_id.distribution_line) :
            order.distribution_id.state = 'done'
        
        invoice_total = self._invoice_total(cr, uid, ids, order.partner_id.id,order.division) + order.amount_total        
        if order.division == 'Unit' :
            if round(invoice_total,2) > round(order.partner_id.credit_limit_unit,2):
                raise osv.except_osv(('Tidak bisa confirm!'), ('Total order melebihi batas limit plafond\nLimit Plafond = %d sedangkan total invoiced+order sekarang = %d') % (order.partner_id.credit_limit_unit,invoice_total))
        elif order.division == 'Sparepart' :
            if round(invoice_total,2) > round(order.partner_id.credit_limit_sparepart,2):
                raise osv.except_osv(('Tidak bisa confirm!'), ('Total order melebihi batas limit plafond\nLimit Plafond = %d sedangkan total invoiced+order sekarang = %d') % (order.partner_id.credit_limit_sparepart,invoice_total))
        
        for line in order.order_line:
            obj_picking.compare_sale_stock(cr,uid,order.branch_id.id,order.division,line.product_id.id,line.product_uom_qty)
            total_qty+=line.product_uom_qty
        res = super(wtc_sale_order,self).action_button_confirm(cr,uid,ids,context=context)
        
        if order.division == 'Unit' :
            self.action_invoice_bb_jual_create(cr,uid,order,total_qty)
            
        if order.amount_tax and not order.pajak_gabungan :
            self.pool.get('wtc.faktur.pajak.out').get_no_faktur_pajak(cr,uid,ids,'sale.order',context=context)                                
        return res
    
    def _get_pricelist(self, cr, uid, ids):
        sale_order = self.browse(cr, uid, ids)
        if sale_order.division == 'Unit' :
            pcc_id = self.pool.get('pricelist.config.cabang').search(cr,uid,[
                ('branch_id','=',sale_order.branch_id.id),
                ('partner_id','=',sale_order.partner_id.id),
                ('division','=','Unit')],limit=1)
            if pcc_id:
                current_pricelist = self.pool.get('pricelist.config.cabang').browse(cr,uid,pcc_id[0])['md_pricelist_id'].id
            else:
                current_pricelist = sale_order.branch_id.pricelist_unit_sales_id.id
        elif sale_order.division == 'Sparepart' :
            pcc_id = self.pool.get('pricelist.config.cabang').search(cr,uid,[
                ('branch_id','=',sale_order.branch_id.id),
                ('partner_id','=',sale_order.partner_id.id),
                ('division','=','Sparepart')],limit=1)
            if pcc_id:
                current_pricelist = self.pool.get('pricelist.config.cabang').browse(cr,uid,pcc_id[0])['md_pricelist_id'].id
            else:
                current_pricelist = sale_order.branch_id.pricelist_part_sales_id.id
        else :
            current_pricelist = sale_order.partner_id.property_product_pricelist.id
        return current_pricelist
    
    def get_stock_available(self, cr, uid, ids, id_product, id_branch, context=None):
        obj_location = self.pool.get('stock.location')
        ids_location = obj_location.search(cr, uid, [('branch_id','=',id_branch),('usage','=','internal')])
        cr.execute("""
        SELECT
            COALESCE(SUM(q.qty),0) as quantity
        FROM
            stock_quant q
        LEFT JOIN
            stock_production_lot l on l.id = q.lot_id
        WHERE
            q.product_id = %s and q.location_id in %s and q.reservation_id is Null and q.consolidated_date is not Null
            and (q.lot_id is Null or l.state = 'stock')
        """,(id_product,tuple(ids_location)))
        return cr.fetchall()[0][0]
    
    def renew_price(self, cr, uid, ids, context=None):
        for sale_order in self.browse(cr, uid, ids):
            for lines in sale_order.order_line:
                if lines.product_id :
                    current_pricelist = self._get_pricelist(cr, uid, ids)
    
                    if not current_pricelist:
                        raise osv.except_osv( ('Perhatian!'), ("Tidak ditemukan konfigurasi pricelist beli cabang sekarang, konfigurasi dulu!"))
                    
                    current_price = self.pool.get('product.pricelist').price_get(cr, uid, [current_pricelist], lines.product_id.id, 1)[current_pricelist]
                     
                    if not current_price:
                        raise osv.except_osv( ('Perhatian!'), ("Tidak ditemukan harga produk %s di pricelist yg aktif!") % lines.product_id.name)
                    
                    lines.write({'price_unit':current_price})
        return True

    def _get_ids_picking(self, cr, uid, ids, context=None):
        so_id = self.browse(cr, uid, ids, context=context)
        obj_picking = self.pool.get('stock.picking')
        obj_model = self.pool.get('ir.model')
        id_model = obj_model.search(cr, uid, [('model','=',so_id.__class__.__name__)])[0]
        ids_picking = obj_picking.search(cr, uid, [
            ('model_id','=',id_model),
            ('transaction_id','=',so_id.id),
            ('state','!=','cancel')
            ])
        return ids_picking
    
    def _get_invoice_ids(self, cr, uid, ids, context=None):
        so_id = self.browse(cr, uid, ids, context=context)
        obj_inv = self.pool.get('account.invoice')
        obj_model = self.pool.get('ir.model')
        id_model = obj_model.search(cr, uid, [('model','=',so_id.__class__.__name__)])[0]
        ids_inv = obj_inv.search(cr, uid, [
            ('model_id','=',id_model),
            ('transaction_id','=',so_id.id),
            ('state','!=','cancel')
            ])
        inv_ids = obj_inv.browse(cr, uid, ids_inv)
        return inv_ids
    
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
    
    def wkf_action_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'cancel', 'cancel_uid':uid, 'cancel_date':datetime.now()}, context=context)

    def wkf_action_unused(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'unused'}, context=context)
        
    def is_so_done(self, cr, uid, ids, context=None):
        inv_done = False
        so_id = self.browse(cr, uid, ids, context=context)
        reverse = self.reverse(cr, uid, ids, context)
        picking_done = self.test_moves_done(cr, uid, ids, context)
        inv_ids = self._get_invoice_ids(cr, uid, ids, context)
        for inv in inv_ids :
            if inv.tipe in ('md_sale_unit','md_sale_sparepart') and inv.state == 'paid' :
                inv_done = True
        if inv_done and not so_id.is_cancelled and picking_done and not reverse :
            return self.signal_workflow(cr, uid, ids, 'action_done')
        return True

    def write(self, cr, uid, ids, vals, context=None):
        old_data = self.browse(cr,uid,ids)
        if self.STATES.get(old_data.state,False):
            for key,value in vals.items():
                if key not in self.STATES[old_data.state]:
                    raise osv.except_osv(('Maaf!'), ("Gagal melakukan perubahan %s, data sudah di confirm !" %(key)))
        if self.STATES.get(old_data.state,False) == []:
            raise osv.except_osv(('Maaf!'), ("Gagal melakukan perubahan, Data sudah tidak bisa di ubah, state sudah %s!" %(old_data.state)))

        return super(wtc_sale_order, self).write(cr, uid, ids, vals, context=context)

    
class sale_order_line(osv.osv):
    
    _inherit = 'sale.order.line'
    
    def _get_default_date(self,cr,uid,ids,context=None):
        return self.pool.get('wtc.branch').get_default_date(cr,uid,ids,context=context)
    
    def _get_hpp_average(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for order_line in self.browse(cr, uid, ids):
            if order_line.force_cogs:
                hpp_average = order_line.force_cogs
            else:
                hpp_average = self.pool.get('product.price.branch')._get_price(cr,uid,order_line.order_id.warehouse_id.id,order_line.product_id.id)
            res[order_line.id] = hpp_average
        return res
    
    def product_id_change_dev(self, cr, uid, ids, division,branch_id, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, context=None):
        context = context or {}
        lang = lang or context.get('lang', False)
        if not partner_id:
            raise osv.except_osv(_('No Customer Defined!'), _('Before choosing a product,\n select a customer in the sales form.'))
        warning = False
        product_uom_obj = self.pool.get('product.uom')
        partner_obj = self.pool.get('res.partner')
        product_obj = self.pool.get('product.product')
        context = {'lang': lang, 'partner_id': partner_id}
        partner = partner_obj.browse(cr, uid, partner_id)
        lang = partner.lang
        context_partner = {'lang': lang, 'partner_id': partner_id}

        if not product:
            return {'value': {'th_weight': 0,
                'product_uos_qty': qty}, 'domain': {'product_uom': [],
                   'product_uos': []}}
        if not date_order:
            date_order = time.strftime(DEFAULT_SERVER_DATE_FORMAT)

        result = {}
        warning_msgs = ''
        product_obj = product_obj.browse(cr, uid, product, context=context_partner)

        uom2 = False
                
        if uom:
            uom2 = product_uom_obj.browse(cr, uid, uom)
            if product_obj.uom_id.category_id.id != uom2.category_id.id:
                uom = False
        if uos:
            if product_obj.uos_id:
                uos2 = product_uom_obj.browse(cr, uid, uos)
                if product_obj.uos_id.category_id.id != uos2.category_id.id:
                    uos = False
            else:
                uos = False

        fpos = False
        if not fiscal_position:
            fpos = partner.property_account_position or False
        else:
            fpos = self.pool.get('account.fiscal.position').browse(cr, uid, fiscal_position)
        if update_tax: #The quantity only have changed
            result['tax_id'] = self.pool.get('account.fiscal.position').map_tax(cr, uid, fpos, product_obj.taxes_id)

        if not flag:
            result['name'] = self.pool.get('product.product').name_get(cr, uid, [product_obj.id], context=context_partner)[0][1]
            if product_obj.description_sale:
                result['name'] += '\n'+product_obj.description_sale
        domain = {}
        if (not uom) and (not uos):
            result['product_uom'] = product_obj.uom_id.id
            if product_obj.uos_id:
                result['product_uos'] = product_obj.uos_id.id
                result['product_uos_qty'] = qty * product_obj.uos_coeff
                uos_category_id = product_obj.uos_id.category_id.id
            else:
                result['product_uos'] = False
                result['product_uos_qty'] = qty
                uos_category_id = False
            result['th_weight'] = qty * product_obj.weight
            domain = {'product_uom':
                        [('category_id', '=', product_obj.uom_id.category_id.id)],
                        'product_uos':
                        [('category_id', '=', uos_category_id)]}
        elif uos and not uom: # only happens if uom is False
            result['product_uom'] = product_obj.uom_id and product_obj.uom_id.id
            result['product_uom_qty'] = qty_uos / product_obj.uos_coeff
            result['th_weight'] = result['product_uom_qty'] * product_obj.weight
        elif uom: # whether uos is set or not
            default_uom = product_obj.uom_id and product_obj.uom_id.id
            q = product_uom_obj._compute_qty(cr, uid, uom, qty, default_uom)
            if product_obj.uos_id:
                result['product_uos'] = product_obj.uos_id.id
                result['product_uos_qty'] = qty * product_obj.uos_coeff
            else:
                result['product_uos'] = False
                result['product_uos_qty'] = qty
            result['th_weight'] = q * product_obj.weight        # Round the quantity up

        if not uom2:
            uom2 = product_obj.uom_id
        # get unit price

        if not pricelist:
            warn_msg = _('You have to select a pricelist or a customer in the sales form !\n'
                    'Please set one before choosing a product.')
            warning_msgs += _("No Pricelist ! : ") + warn_msg +"\n\n"
        else:
            price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist],
                    product, qty or 1.0, partner_id, {
                        'uom': uom or result.get('product_uom'),
                        'date': date_order,
                        })[pricelist]
            if price is False:
                warn_msg = _("Cannot find a pricelist line matching this product and quantity.\n"
                        "You have to change either the product, the quantity or the pricelist.")

                warning_msgs += _("No valid pricelist line found ! :") + warn_msg +"\n\n"
            else:
                result.update({'price_unit': price})
        if warning_msgs:
            warning = {
                       'title': _('Configuration Error!'),
                       'message' : warning_msgs
                    }
        
        if product:
            obj_location=self.pool.get('stock.location')
            ids_location=obj_location.search(cr,uid,[('branch_id','=',branch_id),('usage','=','internal')])
            qty_avb = 0
            if division=='Unit':
                query = """
                    SELECT COALESCE(SUM(q.qty),0) AS quantity
                    FROM stock_quant q 
                    LEFT JOIN stock_production_lot l ON l.id = q.lot_id
                    WHERE q.product_id = %s 
                    AND q.location_id IN %s 
                    AND q.reservation_id IS NULL 
                    AND q.consolidated_date IS NOT NULL
                    AND (q.lot_id IS NULL OR l.state='stock')
                """ % (product, str(tuple(ids_location)).replace(',)',')'))
                cr.execute(query)
                qty_avb = cr.fetchall()[0][0]
            elif division == 'Sparepart':
                obj_picking = self.pool.get('stock.picking')
                qty_avb = obj_picking._get_qty_quant(cr, uid, branch_id, product) - (obj_picking._get_qty_picking(cr, uid, branch_id, division, product) + obj_picking._get_qty_rfa_approved(cr, uid, branch_id, division, product))
            result['qty_available'] = qty_avb
            result['qty_available_show'] = qty_avb
        
        return {'value': result, 'domain': domain, 'warning': warning}
    
    def _get_keterangan(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for show in self.read(cr, uid, ids, ['qty_available']):
            qty_show = show['qty_available']
            res[show['id']] = qty_show
        return res
        
    _columns = {
                'categ_id':fields.many2one('product.category','Category',required=True),
                'force_cogs': fields.float('Force COGS'),
                'hpp_average': fields.function(_get_hpp_average,string='HPP'),
                'qty_available':fields.float('Qty'),
                'qty_available_show':fields.function(_get_keterangan,type='float',string='Qty Avb')
    }
    
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
    
    def _search_pricelist_ekspedisi(self,cr,uid,ids,product_id,branch_id):
        price_list_ekspedisi_def = self.pool.get('wtc.harga.ekspedisi').search(cr,uid,[('branch_id','=',branch_id),('default_ekspedisi','=',True)])
        if not price_list_ekspedisi_def:
            raise osv.except_osv(('Tidak ditemukan default harga ekspedisi!'), ('Tidak bisa confirm, silahkan setting dulu di pengaturan cabang!'))
        else:
            pricelist_ekspedisi = self.pool.get('wtc.harga.ekspedisi').browse(cr,uid,price_list_ekspedisi_def[0])
            pl_ekspedisi_line_active = self.pool.get('wtc.pricelist.expedition.line').search(cr,uid,[
                                                                                                     ('pricelist_expedition_id','=',pricelist_ekspedisi.harga_ekspedisi_id.id),
                                                                                                     ('active','=',True),
                                                                                                     ('start_date','<=',self._get_default_date(cr, uid, ids, context=None)),
                                                                                                     ('end_date','>=',self._get_default_date(cr, uid, ids, context=None)),
                                                                                                     ])
            if not pl_ekspedisi_line_active:
                raise osv.except_osv(('Tidak ditemukan harga ekspedisi yang aktif!'), ('Tidak bisa confirm, silahkan setting dulu di pengaturan cabang!'))
            else:
                pl_eks_det_obj = self.pool.get('wtc.pricelist.expedition.line.detail')
                pl_ekspedisi_product = pl_eks_det_obj.search(cr,uid,[
                                                                    ('pricelist_expedition_line_id','=',pl_ekspedisi_line_active[0]),
                                                                    ('product_template_id','=',product_id.product_tmpl_id.id),
                                                                    ])
                if not pl_ekspedisi_product:
                    raise osv.except_osv(('Tidak ditemukan harga ekspedisi product %s!') % (product_id.product_tmpl_id.name), ('Tidak bisa confirm, silahkan setting dulu di pengaturan cabang!'))
                else:
                    harga_ekspedisi_product = pl_eks_det_obj.browse(cr,uid,pl_ekspedisi_product[0])
                    return harga_ekspedisi_product.cost
    
    def _prepare_order_line_invoice_line(self, cr, uid, line, account_id=False, context=None):
        res = super(sale_order_line,self)._prepare_order_line_invoice_line(cr, uid, line, account_id=False, context=context)
        if line.product_id:
            if line.product_id.product_tmpl_id.cost_method == 'real':
                pricelist_beli_md = line.order_id.branch_id.pricelist_unit_purchase_id.id
                if not pricelist_beli_md:
                    raise osv.except_osv(('No Sale Pricelist Defined!'), ('Tidak bisa confirm'))
                purchase_price = round(self.pool.get('product.pricelist').price_get(cr, uid, [pricelist_beli_md], line.product_id.id, 1,0)[pricelist_beli_md]/1.1,2)
                harga_ekspedisi = self._search_pricelist_ekspedisi(cr, uid, line.id,line.product_id, line.order_id.branch_id.id)
                purchase_price+=harga_ekspedisi
                force_cogs = purchase_price*line.product_uom_qty
                res.update({'force_cogs':force_cogs})
                line.update({'force_cogs':force_cogs})
            elif line.product_id.product_tmpl_id.cost_method == 'average':
                product_price_branch_obj = self.pool.get('product.price.branch')
                product_price_avg_id = product_price_branch_obj._get_price(cr, uid, line.order_id.warehouse_id.id, line.product_id.id)*line.product_uom_qty
                line.update({'force_cogs':product_price_avg_id})
                res.update({'force_cogs':product_price_avg_id})
        return res
    
    def button_confirm(self, cr, uid, ids, context=None):
        res = super(sale_order_line,self).button_confirm(cr, uid, ids, context=context)
        for line in self.browse(cr, uid, ids):
            if line.order_id.division == 'Unit' :
                pcc_id = self.pool.get('pricelist.config.cabang').search(cr,uid,[
                    ('branch_id','=',line.order_id.branch_id.id),
                    ('partner_id','=',line.order_id.partner_id.id),
                    ('division','=','Unit')],limit=1)
                if pcc_id:
                    current_pricelist = self.pool.get('pricelist.config.cabang').browse(cr,uid,pcc_id[0])['md_pricelist_id'].id
                else:
                    current_pricelist = line.order_id.branch_id.pricelist_unit_sales_id.id
            elif line.order_id.division == 'Sparepart' :
                pcc_id = self.pool.get('pricelist.config.cabang').search(cr,uid,[
                    ('branch_id','=',line.order_id.branch_id.id),
                    ('partner_id','=',line.order_id.partner_id.id),
                    ('division','=','Sparepart')],limit=1)
                if pcc_id:
                    current_pricelist = self.pool.get('pricelist.config.cabang').browse(cr,uid,pcc_id[0])['md_pricelist_id'].id
                else:
                    current_pricelist = line.order_id.branch_id.pricelist_part_sales_id.id
            price_unit = round(line.price_unit,2) 
            current_price = round(self.pool.get('product.pricelist').price_get(cr, uid, [current_pricelist], line.product_id.id, 1,0)[current_pricelist],2)
            if round(price_unit) != round(current_price):
                raise osv.except_osv(('Price unit %s Rp %s tidak sama dengan pricelist Rp %s') % (line.product_id.name,price_unit,current_price), ('Klik Renew Price untuk update harga'))
        return res