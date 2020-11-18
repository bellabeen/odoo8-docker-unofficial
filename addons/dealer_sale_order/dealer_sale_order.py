from datetime import datetime, timedelta
import time
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import openerp.addons.decimal_precision as dp
from openerp import workflow
import pytz 

class dealer_sale_order(osv.osv):
    _name = 'dealer.sale.order'
    _description = "Dealer Sale Order"
    _order = "date_order desc"
    
    def dso_print_subsidi_leasing(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = self.read(cr, uid, ids,context=context)[0]
        return self.pool['report'].get_action(cr, uid, [], 'dealer_sale_order.wtc_report_print_subsidi_leasing', context=context)
 
#     def birojasa_change(self,cr,uid,ids,branch_id,context=None):
#         domain = {}
#         birojasa = []
#         birojasa_srch = self.pool.get('wtc.harga.birojasa').search(cr,uid,[
#                                                                       ('branch_id','=',branch_id)
#                                                                       ])
#         if birojasa_srch :
#             birojasa_brw = self.pool.get('wtc.harga.birojasa').browse(cr,uid,birojasa_srch)
#             for x in birojasa_brw :
#                 birojasa.append(x.birojasa_id.id)
#         domain['dealer_sale_order_line']['partner_id'] = [('id','in',birojasa)]
#         return {'domain':domain}
    
    def _report_xls_dealer_sale_order_fields(self, cr, uid, context=None):
        return [
            'branch_id','order_name', 'order_date','default_code','konsumen','sales','finco','dp_net','sales_source','cicilan','location_id','product_id',
            'warna','mesin','rangka','tenor','is_bbn','nama_stnk','uang_muka','pot_pelanggan','harga','total_discount'
            ,'harga_bbn','state'
            # 'partner_id'
        ]
    
    def _report_xls_stock_sparepart_fields(self, cr, uid, context=None):
        return [
            'cabang', 'kode_product','location_id','tanggal','jumlah'
            # 'partner_id'
        ]

    # override list in custom module to add/drop columns
    # or change order of the partner summary table
    def _report_xls_arap_details_fields(self, cr, uid, context=None):
        return [
            'document', 'date', 'date_maturity', 'account', 'description',
            'rec_or_rec_part', 'debit', 'credit', 'balance',
            # 'partner_id',
        ]

    # Change/Add Template entries
    def _report_xls_arap_overview_template(self, cr, uid, context=None):
        """
        Template updates, e.g.

        my_change = {
            'partner_id':{
                'header': [1, 20, 'text', _('Partner ID')],
                'lines': [1, 0, 'text', _render("p['p_id']")],
                'totals': [1, 0, 'text', None]},
        }
        return my_change
        """
        return {}

    # Change/Add Template entries
    def _report_xls_arap_details_template(self, cr, uid, context=None):
        """
        Template updates, e.g.

        my_change = {
            'partner_id':{
                'header': [1, 20, 'text', _('Partner ID')],
                'lines': [1, 0, 'text', _render("p['p_id']")],
                'totals': [1, 0, 'text', None]},
        }
        return my_change
        """
        return {}
    
    
        
    def _amount_line_tax(self,cr , uid, line, context=None):
        val=val1=disc_total=subtotal=0.0
        for detail in line:
            for disc in detail.discount_line:
                disc_total += disc.discount_pelanggan 
            subtotal+=detail.price_unit-(disc_total+detail.discount_po)
                
            val1 += line.price_unit-(disc_total+line.discount_po)
        #for c in self.pool.get('account.tax').compute_all(cr,uid, line.tax_id, line.price_unit*(1-(line.discount or 0.0)/100.0),line.product_qty, line.product_id)['taxes']:
        for c in self.pool.get('account.tax').compute_all(cr,uid, line.tax_id, subtotal,line.product_qty, line.product_id)['taxes']:
            val +=c.get('amount',0.0)
        return val
    
    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        tax_obj = self.pool.get('account.tax')
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_bbn': 0.0,
                'amount_total': 0.0,
                'amount_hpp':0.0,
                'amount_ps':0.0,
                'amount_pot':0.0,
                'amount_total_disc':0.0,
                'amount_piutang':0.0,
                'amount_gp_unit':0.0,
                'amount_gp_bbn':0.0,
                'amount_hc':0.0,
                'amount_beban_dealer':0.0,
            }
            val = val1 = ps_md = ps_dealer = ps_finco = ps_total = subtotal = valbbn = valbbn_beli = val_hc = disc_total = val_um = val_harga_jual = val_pot = val_beli_unit = val_barang_subsidi = val_ps_dealer = val_bb_dealer = 0.0
           
            for line in order.dealer_sale_order_line:
                disc_total = 0.0
                for disc in line.discount_line:
                    disc_total += disc.discount_pelanggan 
                    val_ps_dealer += disc.ps_dealer
                    ps_md+=disc.ps_md+disc.ps_ahm
                    ps_finco+=disc.ps_finco
                    ps_dealer+=disc.ps_dealer
                for bb in line.barang_bonus_line:
                    val_barang_subsidi += bb.price_barang
                    val_bb_dealer+= bb.bb_dealer
                
                accrue_ekspedisi = 0
                accrue_proses_bbn = 0
                if line.is_bbn == 'Y':
                    accrue_ekspedisi = line.accrue_ekspedisi
                    accrue_proses_bbn = line.accrue_proses_bbn

                taxes = tax_obj.compute_all(cr, uid, line.tax_id, (line.price_unit-(disc_total+line.discount_po)), line.product_qty, line.product_id)
                val1+=taxes['total']
                val += self._amount_line_tax(cr, uid, line, context=context)
                ps_total+=disc_total
                valbbn += line.price_bbn
                val_um += line.uang_muka
                val_harga_jual += tax_obj.compute_all(cr, uid, line.tax_id, line.price_unit, line.product_qty, line.product_id)['total']
                val_pot += line.discount_po
                val_beli_unit+=line.price_unit_beli + accrue_ekspedisi
                valbbn_beli += line.price_bbn_beli + accrue_proses_bbn
                val_hc += line.amount_hutang_komisi
                
            res[order.id]['amount_tax'] = val
            res[order.id]['amount_harga_jual'] = val_harga_jual
            res[order.id]['amount_ps'] = ps_total
            res[order.id]['amount_ps_dealer'] = ps_dealer
            res[order.id]['amount_ps_md'] = ps_md
            res[order.id]['amount_ps_finco'] = ps_finco
            res[order.id]['amount_pot'] = val_pot
            res[order.id]['amount_untaxed'] =val1
            res[order.id]['amount_bbn'] = valbbn
            res[order.id]['amount_hc'] = val_hc
            res[order.id]['customer_dp'] = val_um
            res[order.id]['amount_gp_bbn'] = valbbn - valbbn_beli
            res[order.id]['amount_beban_dealer'] = val_ps_dealer + val_bb_dealer + val_pot
            res[order.id]['amount_total_disc'] = res[order.id]['amount_ps'] + res[order.id]['amount_pot']
            res[order.id]['amount_total'] = res[order.id]['amount_untaxed'] + res[order.id]['amount_tax']+res[order.id]['amount_bbn']
            res[order.id]['amount_gp_unit'] = res[order.id]['amount_harga_jual'] - val_beli_unit - res[order.id]['amount_beban_dealer'] - res[order.id]['amount_hc']
            res[order.id]['amount_piutang'] = res[order.id]['amount_total'] - res[order.id]['customer_dp']
        return res
    
    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        #for order in self.pool.get('dealer.sale.order').browse(cr, uid, ids, context=context):
            #for order_line in self.pool.get('dealer.sale.order.line').browse(cr, uid, order.id, context=context):
                #result[order_line.id] = True
        return result.keys()
    
    def _get_picking_ids(self, cr, uid, ids, field_names, args, context=None):
        res = {}
        for po_id in ids:
            res[po_id] = []
        query = """
        SELECT picking_id, po.id 
        FROM stock_picking p,
         stock_move m, 
         dealer_sale_order_line pol, 
         dealer_sale_order po
         
         
            WHERE  po.id in %s
            and po.id = pol.dealer_sale_order_line_id
            and p.origin=po.name
            and m.picking_id = p.id
            GROUP BY picking_id, po.id
             
        """
        cr.execute(query, (tuple(ids), ))
        picks = cr.fetchall()
        for pick_id, po_id in picks:
            res[po_id].append(pick_id)
       
        return res
    
    def test_moves_done(self, cr, uid, ids, context=None):
        for purchase in self.browse(cr, uid, ids, context=context):
            if not purchase.picking_ids :
                return False
            for picking in purchase.picking_ids:
                if picking.state != 'done':
                    return False
        return True

    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
        
    def _get_default_date(self,cr,uid,ids,context=None):
        return self.pool.get('wtc.branch').get_default_date(cr,uid,ids,context=context)
        
    def _get_default_date_model(self,cr,uid,context=None):
        return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)
    






    _columns = {
                'name' : fields.char('Sales Order'),
                'untuk_pembayaran':fields.char('Untuk Pembayaran'),
                'branch_id': fields.many2one('wtc.branch','Dealer',required=True),
                'division': fields.selection([('Unit','Unit')],required=True,string='Division'),
                'date_order': fields.date('Date Order',required=True),
                'payment_term': fields.many2one('account.payment.term','Payment Term'),
                'partner_id': fields.many2one('res.partner','Customer',domain=[('customer','=',True)],required=True),
                'partner_komisi_id': fields.many2one('res.partner','Mediator'),
                'finco_id': fields.many2one('res.partner','Finco',domain=[('finance_company','=',True)]),
                'user_id': fields.many2one('res.users','Sales Person',required=True,),
                'employee_id':fields.many2one('hr.employee','Employee'),
                'sales_koordinator_id': fields.many2one('res.users','Sales Koordinator'),
                'section_id': fields.many2one('crm.case.section','Sales Team'),
                'sales_source': fields.selection([
                    ('Walk In','Walk In'),
                    ('canvasing','Kanvasing'),
                    ('pameran','Pameran'),
                    ('pos','POS'),
                    ('channel','Channel'),
                    ('GC','GC'),
                    ('TOP-PU','TOP-PU'),
                    ('media_sosial','Media Sosial'),
                    ('Lain-Lain','Lain-Lain')],'Sales Source'),
                'sales_source_location': fields.many2one('stock.location','Sales Source Location'),
                'dealer_sale_order_line': fields.one2many('dealer.sale.order.line','dealer_sale_order_line_id','Sale Order Line',states={'draft': [('readonly', False)],'progress': [('readonly', True)],'invoiced': [('readonly', True)],'done': [('readonly', True)]}),
                'state': fields.selection([
                                ('draft', 'Draft Quotation'),
                                ('waiting_for_approval','Waiting Approval'),
                                ('approved','Approved'),
                                ('progress', 'Sales Order'),
                                ('done', 'Done'),
                                ('cancelled', 'Cancelled'),
                                ('unused', 'Unused'),
                                ],'Status',),
                'date_confirm': fields.date('Confirmation Date', readonly=True, select=True, help="Date on which sales order is confirmed.", copy=False),
                'customer_dp': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='DP Nett',
                    store={
                        'dealer.sale.order': (lambda self, cr, uid, ids, c={}: ids, ['dealer_sale_order_line'], 10),
                        'dealer.sale.order.line': (_get_order, ['uang_muka'], 10),
                    },
                    multi='sums', help="Customer DP", track_visibility='always'),
                'amount_untaxed': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Untaxed Amount',
                    store={
                        'dealer.sale.order': (lambda self, cr, uid, ids, c={}: ids, ['dealer_sale_order_line'], 10),
                        'dealer.sale.order.line': (_get_order, ['price_unit', 'tax_id', 'product_qty'], 10),
                    },
                    multi='sums', help="The amount without tax.", track_visibility='always'),
                
                'amount_tax': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Taxes',
                    store={
                        'dealer.sale.order': (lambda self, cr, uid, ids, c={}: ids, ['dealer_sale_order_line'], 10),
                        'dealer.sale.order.line': (_get_order, ['price_unit', 'tax_id',  'product_qty'], 10),
                    },
                    multi='sums', help="The tax amount."),
                
                'amount_total': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total',
                    store={
                        'dealer.sale.order': (lambda self, cr, uid, ids, c={}: ids, ['dealer_sale_order_line'], 10),
                        'dealer.sale.order.line': (_get_order, ['price_unit', 'tax_id', 'product_qty'], 10),
                    },
                    multi='sums', help="The total amount."),
                
                'amount_bbn': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total BBN',
                    store={
                        'dealer.sale.order': (lambda self, cr, uid, ids, c={}: ids, ['dealer_sale_order_line'], 10),
                        'dealer.sale.order.line': (_get_order, ['price_bbn'], 10),
                    },
                    multi='sums', help="The total amount."),
                'amount_harga_jual': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total Harga Jual',                   
                    multi='sums', help="The total HPP."),
                'amount_pot': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total Potongan',                   
                    multi='sums', help="Total Potongan."),
                'amount_ps': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total PS',                   
                    multi='sums', help="Total PS."),
                'amount_total_disc': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total Disc',                   
                    multi='sums', help="Total Disc."),
                'amount_gp_unit': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='GP Unit',                   
                    multi='sums', help="Total GP Unit."),
                'amount_gp_bbn': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='GP BBN',                   
                    multi='sums', help="Total GP BBN."),
                'amount_piutang': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Sisa Piutang',                   
                    multi='sums', help="Total Piutang."),
                'amount_hc': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total Hutang Komisi',                   
                    multi='sums', help="Total Hutang Komisi."),
                'amount_beban_dealer': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total Beban Dealer',                   
                    multi='sums', help="Total Beban Dealer."),
                'amount_ps_md': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total PS MD',                   
                    multi='sums', help="Total PS MD."),
                'amount_ps_finco': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total PS Finco',                   
                    multi='sums', help="Total PS Finco."),
                'amount_ps_dealer': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total PS Dealer',                   
                    multi='sums', help="Total PS Dealer."),
                #'invoice_ids': fields.many2many('account.invoice', 'dealer_sale_order_invoice_rel', 'dealer_sale_order_id', 'invoice_id', 'Invoices', readonly=True, copy=False, help="This is the list of invoices that have been generated for this sales order. The same sales order may have been invoiced in several times (by line for example)."),
                'qq': fields.char('qq'),
                'alamat_kirim': fields.text('Alamat Kirim'),
                'amount_tax_info':fields.related('amount_tax',string='Total Tax',readonly=True),
                'amount_bbn_info':fields.related('amount_bbn',string='Total BBN',readonly=True),
                'amount_dp_info':fields.related('customer_dp',string='Total DP',readonly=True),
                'picking_ids': fields.function(_get_picking_ids, method=True, type='one2many', relation='stock.picking', string='Picking List', help="This is the list of receipts that have been generated for this sale order."),
                'picking_dummy': fields.related('picking_ids',type='boolean'),
                'summary_diskon_ids': fields.one2many('dealer.sale.order.summary.diskon','dealer_sale_order_id'),
                'dealer_spk_id': fields.many2one('dealer.spk'),
                'cddb_id': fields.many2one('wtc.cddb',string='CDDB',required=True),
                'city_cddb_rel': fields.related('cddb_id','city_id',relation='wtc.city',type='many2one',store=False,readonly=True,string='CDDB City'),
                'kecamatan_cddb_rel': fields.related('cddb_id','kecamatan_id',relation='wtc.kecamatan',type='many2one',store=False,readonly=True,string='CDDB Kecamatan'),
                'is_cod':fields.boolean('Is COD'),
                'is_cancelled':fields.boolean('Cancelled'),
                'confirm_uid':fields.many2one('res.users',string="Approved by"),
                'confirm_date':fields.datetime('Approved on'),
                'cancelled_uid':fields.many2one('res.users', string="Cancelled by"),
                'cancelled_date':fields.datetime('Cancelled on'),
                'payment_term_dummy': fields.related('payment_term',relation='account.payment.term',type='many2one',string='Payment Term',store=False),
                'pajak_gabungan':fields.boolean('Faktur Pajak Gabungan',copy=False),   
                'faktur_pajak_id':fields.many2one('wtc.faktur.pajak.out',string='No Faktur Pajak',copy=False)  ,
                'journal_id':fields.many2one('account.journal', 'Payment Method'),    
                'claimed_date' : fields.datetime(string='Claimed Date'), 
                'reason_unused' : fields.char('Reason Unused'),
                'hutang_lain_line': fields.one2many('dso.hutang.lain.line','dealer_sale_order_id','Hutang Lain Line',states={'draft': [('readonly', False)],'progress': [('readonly', True)],'invoiced': [('readonly', True)],'done': [('readonly', True)]}),
                'al_move_id': fields.many2one('account.move', 'Allocation DP Journal'),     
                }
    _defaults = {
                'state': 'draft',
                'division': 'Unit',
                'date_order': _get_default_date,
                'branch_id' : _get_default_branch
              }
        
    def _get_approval_diskon(self,cr,uid,data):
        per_product = {}
        hasil = []
        update = False
        for line in data:
            if line[0] == 0: 
                if not per_product.get(line[2]['product_id'],False):
                    per_product[line[2]['product_id']] = {}
                
                per_product[line[2]['product_id']]['product_qty'] = per_product[line[2]['product_id']].get('product_qty',0)+line[2].get('product_qty',0)
                per_product[line[2]['product_id']]['beban_po'] = per_product[line[2]['product_id']].get('beban_po',0)+line[2].get('discount_po',0)
                per_product[line[2]['product_id']]['beban_hc'] = per_product[line[2]['product_id']].get('beban_hc',0)+line[2].get('amount_hutang_komisi',0)
                 
                for disc in line[2]['discount_line']:
                    per_product[line[2]['product_id']]['beban_ps'] = per_product[line[2]['product_id']].get('beban_ps',0)+disc[2].get('ps_dealer',0)
                 
                for bb in line[2]['barang_bonus_line']:
                    per_product[line[2]['product_id']]['beban_bb'] = per_product[line[2]['product_id']].get('beban_bb',0)+disc[2].get('discount_dealer',0)
            
       
                
        if update == False:
            for key, value in per_product.items():
                hasil.append([0,False,{
                                        'product_id': key,
                                        'product_qty':value.get('product_qty',0),
                                        'beban_po':value.get('beban_po',0),
                                        'beban_hc':value.get('beban_hc',0),
                                        'beban_ps':value.get('beban_ps',0),
                                        'beban_bb':value.get('beban_bb',0),
                                        'amount_average':(value.get('beban_po',0)+value.get('beban_hc',0)+value.get('beban_ps',0)+value.get('beban_bb',0))/value.get('product_qty',0),
                                        
                                       }])
        else:
           
            for key, value in per_product.items():
                
                hasil.append([0,False,{
                                        'product_id': key,
                                        'product_qty':value.get('product_qty_old',0)-value.get('product_qty',0),
                                        'beban_po':value.get('beban_po_old',0)-value.get('beban_po',0),
                                        'beban_hc':value.get('beban_hc_old',0)-value.get('beban_hc',0),
                                        'beban_ps':value.get('beban_ps_old',0)-value.get('beban_ps',0),
                                        'beban_bb':value.get('beban_bb_old',0),
                                        'amount_average':(value.get('amount_average_old',0)
                                                          -(value.get('beban_po',0)+value.get('beban_hc',0)+value.get('beban_ps',0)+value.get('beban_bb',0)))
                                                          /(value.get('product_qty_old',0)-value.get('product_qty',0)),
                                        
                                       }])
        
        return hasil
    
    def _set_diskon_summary(self,cr,uid,ids,data):
        per_product = {}
        hasil = []
        update = False
        tax_obj = self.pool.get('account.tax')
        for line in data:
            
            if not per_product.get(line.product_id.id,False):
                per_product[line.product_id.id] = {}
            
            accrue_proses_bbn = 0
            accrue_ekspedisi = 0
            if line.is_bbn == 'Y':
                accrue_proses_bbn = line.accrue_proses_bbn
                accrue_ekspedisi = line.accrue_ekspedisi

            per_product[line.product_id.id]['product_qty'] = per_product[line.product_id.id].get('product_qty',0)+line.product_qty
            per_product[line.product_id.id]['beban_po'] = per_product[line.product_id.id].get('beban_po',0)+line.discount_po
            per_product[line.product_id.id]['beban_hc'] = per_product[line.product_id.id].get('beban_hc',0)+line.amount_hutang_komisi
            per_product[line.product_id.id]['harga_beli'] = per_product[line.product_id.id].get('harga_beli',0)+line.price_unit_beli+accrue_ekspedisi
            per_product[line.product_id.id]['harga_jual'] = per_product[line.product_id.id].get('harga_jual',0)+tax_obj.compute_all(cr, uid, line.tax_id, line.price_unit, line.product_qty, line.product_id)['total']
            per_product[line.product_id.id]['harga_bbn_jual'] = per_product[line.product_id.id].get('harga_bbn_jual',0)+line.price_bbn
            per_product[line.product_id.id]['harga_bbn_beli'] = per_product[line.product_id.id].get('harga_bbn_beli',0)+line.price_bbn_beli+accrue_proses_bbn
            
            for disc in line['discount_line']:
                per_product[line.product_id.id]['beban_ps'] = per_product[line.product_id.id].get('beban_ps',0)+disc.ps_dealer
             
            for bb in line['barang_bonus_line']:
                per_product[line.product_id.id]['beban_bb'] = per_product[line.product_id.id].get('beban_bb',0)+bb.bb_dealer
        
        for key, value in per_product.items():
            gp_unit = value.get('harga_jual',0)-(value.get('harga_beli',0)+value.get('beban_po',0)+value.get('beban_hc',0)+value.get('beban_ps',0)+value.get('beban_bb',0))
            gp_bbn = value.get('harga_bbn_jual',0) - value.get('harga_bbn_beli',0)
            average = (gp_unit+gp_bbn)/value.get('product_qty',0)
            hasil.append([0,False,{
                                    'product_id': key,
                                    'product_qty':value.get('product_qty',0),
                                    'beban_po':value.get('beban_po',0),
                                    'beban_hc':value.get('beban_hc',0),
                                    'beban_ps':value.get('beban_ps',0),
                                    'beban_bb':value.get('beban_bb',0),
                                    'amount_average':average,
                                   }])
        check_old_summary = self.pool.get('dealer.sale.order.summary.diskon').search(cr,uid,[('dealer_sale_order_id','in',ids)])
       
        if check_old_summary:
            delete_summary = self.pool.get('dealer.sale.order.summary.diskon').unlink(cr,uid,check_old_summary)
            
        insert_summary = self.write(cr,uid,ids,{'summary_diskon_ids':hasil})
            
        return per_product
    
    
    def print_wizard(self,cr,uid,ids,context=None):  
        obj_claim_kpb = self.browse(cr,uid,ids)
        obj_ir_view = self.pool.get("ir.ui.view")
        obj_ir_view_search= obj_ir_view.search(cr,uid,[("name", "=", 'dealer.sale.order.wizard.print'), ("model", "=", 'dealer.sale.order'),])
        obj_ir_view_browse = obj_ir_view.browse(cr,uid,obj_ir_view_search)
        return {
            'name': 'Print SO',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'dealer.sale.order',
            'type': 'ir.actions.act_window',
            'view_id' : obj_ir_view_browse.id,
            'nodestroy': True,
            'target': 'new',
            'res_id': obj_claim_kpb.id
            } 
        
    
    def print_wizard_subsidi_leasing(self,cr,uid,ids,context=None):  
        obj_claim_kpb = self.browse(cr,uid,ids)
        obj_ir_view = self.pool.get("ir.ui.view")
        obj_ir_view_search= obj_ir_view.search(cr,uid,[("name", "=", 'dealer.sale.order.subsidi.leasing.print'), ("model", "=", 'dealer.sale.order'),])
        obj_ir_view_browse = obj_ir_view.browse(cr,uid,obj_ir_view_search)
        return {
            'name': 'Print SO',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'dealer.sale.order',
            'type': 'ir.actions.act_window',
            'view_id' : obj_ir_view_browse.id,
            'nodestroy': True,
            'target': 'new',
            'res_id': obj_claim_kpb.id
            } 
    
    def print_wizard_pelunasan_leasing(self,cr,uid,ids,context=None):  
        obj_claim_kpb = self.browse(cr,uid,ids)
        obj_ir_view = self.pool.get("ir.ui.view")
        obj_ir_view_search= obj_ir_view.search(cr,uid,[("name", "=", 'dealer.sale.order.pelunasan.leasing.print'), ("model", "=", 'dealer.sale.order'),])
        obj_ir_view_browse = obj_ir_view.browse(cr,uid,obj_ir_view_search)
        return {
            'name': 'Print Pelunasan Leasing',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'dealer.sale.order',
            'type': 'ir.actions.act_window',
            'view_id' : obj_ir_view_browse.id,
            'nodestroy': True,
            'target': 'new',
            'res_id': obj_claim_kpb.id
            } 
        
    def subsidi_leasing(self,cr,uid,ids,context=None):  
        obj_claim_kpb = self.browse(cr,uid,ids)
        obj_ir_view = self.pool.get("ir.ui.view")
        obj_ir_view_search= obj_ir_view.search(cr,uid,[("name", "=", 'dealer.sale.order.subsidi.wizard'), ("model", "=", 'dealer.sale.order'),])
        obj_ir_view_browse = obj_ir_view.browse(cr,uid,obj_ir_view_search)
        return {
            'name': 'Subsidi QQ',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'dealer.sale.order',
            'type': 'ir.actions.act_window',
            'view_id' : obj_ir_view_browse.id,
            'nodestroy': True,
            'target': 'new',
            'res_id': obj_claim_kpb.id
            }
        
                
    def create(self,cr,uid,vals,context=None):
        
        if not vals['dealer_sale_order_line'] :
            raise osv.except_osv(('Perhatian !'), ("Tidak ada detail Sales. Data tidak bisa di save."))
        
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'SO',context)
        #vals['approval_diskon_ids'] = self._get_approval_diskon(cr, uid, vals['dealer_sale_order_line'])
        
        dealer_sales_order = super(dealer_sale_order, self).create(cr, uid, vals, context=context)
        vals['date_order'] = self._get_default_date_model(cr, uid, context=context)
        if dealer_sales_order:
            obj_lot = self.pool.get('stock.production.lot')
            
            for line in vals['dealer_sale_order_line']: 
                if line[2]['is_bbn']=='T' and vals['finco_id']:
                    raise osv.except_osv(('Perhatian !'), ("Penjualan credit harus harus menggunakan biro jasa!"))
                lot_update_reserve = obj_lot.write(cr,uid,line[2]['lot_id'],{'state': 'reserved','sale_order_reserved':dealer_sales_order,'customer_reserved':vals['partner_id']})
                
            #obj_branch_id = self.pool.get('wtc.branch.config').search(cr,uid,[('branch_id','=',vals['branch_id'])])
            obj_branch_config = self._get_branch_journal_config(cr, uid, vals['branch_id'])
#              
#             if obj_branch_config:
#                 if not (obj_branch_config.dealer_so_journal_pelunasan_id.id and obj_branch_config.dealer_so_journal_dp_id.id and obj_branch_config.dealer_so_journal_psmd_id.id and obj_branch_config.dealer_so_journal_psfinco_id.id and obj_branch_config.dealer_so_journal_bbnbeli_id.id and obj_branch_config.dealer_so_journal_insentive_finco_id.id and obj_branch_config.dealer_so_account_bbn_jual_id.id):
#                     raise osv.except_osv(('Perhatian !'), ("Tidak Ditemukan konfigurasi jurnal Cabang, Silahkan konfigurasi dulu"))
        
        return dealer_sales_order
    
    def _get_branch_journal_config(self,cr,uid,branch_id):
        result = {}
        obj_branch_config_id = self.pool.get('wtc.branch.config').search(cr,uid,[('branch_id','=',branch_id)])
        if not obj_branch_config_id:
            raise osv.except_osv(('Perhatian !'), ("Tidak Ditemukan konfigurasi jurnal Cabang, Silahkan konfigurasi dulu"))
        else:
            
            obj_branch_config = self.pool.get('wtc.branch.config').browse(cr,uid,obj_branch_config_id[0])
            if not(obj_branch_config.dealer_so_journal_pelunasan_id.id and obj_branch_config.dealer_so_journal_dp_id.id and obj_branch_config.dealer_so_journal_psmd_id.id and obj_branch_config.dealer_so_journal_psfinco_id.id and obj_branch_config.dealer_so_journal_bbnbeli_id.id and obj_branch_config.dealer_so_journal_insentive_finco_id.id and obj_branch_config.dealer_so_account_bbn_jual_id.id and obj_branch_config.dealer_so_account_sisa_subsidi_id.id and obj_branch_config.dealer_so_journal_hc_id.id and obj_branch_config.dealer_so_journal_accrue_ekspedisi_id.id and obj_branch_config.dealer_so_journal_accrue_proses_bbn_id.id):
                raise osv.except_osv(('Perhatian !'), ("Konfigurasi jurnal penjualan cabang belum lengkap, silahkan setting dulu"))
            
        return obj_branch_config
   
    def _get_cost_quant_per_lot(self,cr,uid,lot_id):
        cost_quant = 0.0
        obj_quant = self.pool.get('stock.quant')
        quant_id = obj_quant.search(cr,uid,[('lot_id','=',lot_id.id)])
        if quant_id:
            cost_quant = obj_quant.browse(cr,uid,quant_id[0])['cost']
        return cost_quant
    
    def action_button_claim(self, cr ,uid,ids,context=None):
        self.write(cr, uid, ids, {'claimed_date':datetime.now()}, context=context)
        return True
    
    
        
    def action_tidak_digunakan(self,cr,uid,ids,context=None):  
        obj_unused = self.browse(cr,uid,ids)
        obj_ir_view = self.pool.get("ir.ui.view")
        obj_ir_view_search= obj_ir_view.search(cr,uid,
                            [("name", "=", 'dealer.sale.order.unused'), 
                             ("model", "=", 'dealer.sale.order'),])
        obj_ir_view_browse = obj_ir_view.browse(cr,uid,obj_ir_view_search)
        return {
            'name': 'Reason',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'dealer.sale.order',
            'type': 'ir.actions.act_window',
            'view_id' : obj_ir_view_browse.id,
            'nodestroy': True,
            'target': 'new',
            'res_id': obj_unused.id
            } 
        
    def action_button_confirm_reason_unused(self, cr, uid, ids, context=None):
        obj_unused = self.browse(cr,uid,ids)
        if not obj_unused.reason_unused:
            raise osv.except_osv(('Perhatian !'), ("Reason Unused Belum Di Isi"))
        if obj_unused.dealer_sale_order_line:
            for line in obj_unused.dealer_sale_order_line:
                update_lot = self.update_serial_number(cr,uid,{'state': 'stock','sale_order_reserved':False,'customer_reserved':False},line.lot_id.id)
        self.write(cr, uid, ids, {'state': 'unused','reason_unused':obj_unused.reason_unused})
        
    def check_hl(self,cr,uid,ids,context=None):
        dso = self.browse(cr,uid,ids) 
        total_hl = 0
        for hl in dso.hutang_lain_line:
            if round(hl.amount_hl_allocation,2) > round(hl.hl_id.amount_residual,2) :
                raise osv.except_osv(('Perhatian !'), ("Alokasi tidak boleh melebihi open balance!"))
                #throw error
            total_hl+=hl.amount_hl_allocation
            
        if dso.finco_id:
            if dso.is_cod:
                if round(dso.customer_dp,2)<round(total_hl,2):
                    raise osv.except_osv(('Perhatian !'), ("Tidak bisa confirm, nominal hutang lain lebih dari DP!"))
            else:
                if round(dso.customer_dp,2)!=round(total_hl,2):
                    raise osv.except_osv(('Perhatian !'), ("Tidak bisa confirm, nominal hutang lain harus sama dengan DP!"))
        else:
            if not dso.is_cod: #cash & tidak cod
                if round(dso.amount_total,2)!=round(total_hl,2):
                    raise osv.except_osv(('Perhatian !'), ("Tidak bisa confirm, nominal hutang lain harus sama dengan sisa piutang!"))
            else :
                if round(dso.amount_total,2)<round(total_hl,2):
                    raise osv.except_osv(('Perhatian !'), ("Tidak bisa confirm, nominal hutang lain lebih dari sisa piutang!"))
        
    def action_button_confirm(self, cr, uid, ids, context=None):
        assert len(ids) == 1, 'This option should only be used for a single id at a time.'
        self.check_hl(cr,uid,ids)
        self.write(cr,uid,ids,{'confirm_uid':uid,'confirm_date':datetime.now(),'date_order':self._get_default_date(cr, uid, ids)})    
        
        for o in self.browse(cr, uid, ids):
            
            if not o.dealer_sale_order_line:
                raise osv.except_osv(_('Perhatian!'),_('Tidak ada detail Sales. Data tidak bisa di confirm.'))
            else:
                self.write(cr, uid, ids, {'state': 'progress', 'date_confirm': fields.date.context_today(self, cr, uid, context=context)})
            
            for line in o.dealer_sale_order_line:
                if line.lot_id.location_id.id!=line.location_id.id:
                    raise osv.except_osv(_('Perhatian!'),_('Lokasi %s di sale order tidak sama dengan lokasi unit sekarang, silahkan pindahkan unit ke lokasi seperti sale order dulu!') % (line.lot_id.name))
                line.write({'force_cogs':self._get_cost_quant_per_lot(cr, uid, line.lot_id)})
                for barang_bonus in line.barang_bonus_line:
                    barang_bonus.write({'force_cogs':barang_bonus.price_barang})
                    
            self.signal_workflow(cr, uid, ids, 'order_confirm')
            jenis_penjualan = '1'
            finco_id = False
            inv_bbn_jual_id = False
            total_jasa = 0
            
            
            obj_inv = self.pool.get('account.invoice')
            if o.finco_id:
                jenis_penjualan = '2'
                finco_id = o.finco_id.id
        
                inv_id = obj_inv.search(cr,uid,[
                                                 ('origin','=',o.name),
                                                 ('partner_id','=',o.finco_id.id),
                                                 ('tipe','=','finco')
                                                 ])
                inv_id_dp = obj_inv.search(cr,uid,[
                                                 ('origin','=',o.name),
                                                 ('partner_id','=',o.partner_id.id),
                                                 ('tipe','=','customer')
                                                 ])

            else:
                inv_id = obj_inv.search(cr,uid,[
                                                 ('origin','=',o.name),
                                                 ('partner_id','=',o.partner_id.id),
                                                 ('tipe','=','customer')
                                                 ])

            for line in o.dealer_sale_order_line:
                move_line_bbn_ids = False

                if line.is_bbn == 'Y':
                    state = 'sold'
                    inv_bbn_jual = obj_inv.search(cr,uid,[
                                                 ('origin','=',o.name),
                                                 ('partner_id','=',line.biro_jasa_id.id),
                                                 ('tipe','=','bbn'),
                                                 ('dealer_sale_order_store_line_id','=',line.id)
                                                 ])
                    inv_bbn_jual_id = inv_bbn_jual[0]
                    total_jasa = line.price_bbn_jasa+line.price_bbn_jasa_area
                    #store move line bbn in serial number

                    invoice_bbn_move_line = obj_inv.browse(cr,uid,inv_bbn_jual)
                    move_line_bbn_ids = self.get_move_line_bbn(cr,uid,ids,move_line_bbn_ids,invoice_bbn_move_line.move_id.line_id,context=context)

                else:
                    state = 'sold_offtr'
                
                update_lot = self.update_serial_number(cr,uid,{
                                                               'dealer_sale_order_id': o.id,
                                                               'invoice_date': self._get_default_date(cr, uid, ids),
                                                               'customer_id': o.partner_id.id,
                                                               'customer_stnk': line.partner_stnk_id.id,
                                                               'dp': line.uang_muka,
                                                               'tenor': line.finco_tenor,
                                                               'cicilan': line.cicilan,
                                                               'jenis_penjualan':jenis_penjualan,
                                                               'finco_id':finco_id,
                                                               'biro_jasa_id': line.biro_jasa_id.id,
                                                               'invoice_bbn': inv_bbn_jual_id,
                                                               'total_jasa':total_jasa,
                                                               'cddb_id':o.cddb_id.id,
                                                               'move_lines_invoice_bbn_id':move_line_bbn_ids,
                                                               },line.lot_id.id)
        return True
    
    def get_move_line_bbn(self,cr,uid,ids,move_line_bbn_ids,line_ids,context=None):
        for x in line_ids :
            if x.credit > 0.0 :
                move_line_bbn_ids = x.id                              
        return move_line_bbn_ids
    
    def button_dummy(self, cr, uid, ids, context=None):
        return True
    
    def _get_product_template_id(self, cr, uid , product_id, context=None):
        product_template_obj = self.pool.get('product.product').browse(cr,uid,product_id)
        product_template_id = product_template_obj.product_tmpl_id.id
        
        return product_template_id
    
    def onchange_sales(self,cr,uid,ids,sales_id,branch_id):
        domain = {}
        if sales_id:
            partner = self.pool.get('res.users').browse(cr,uid,sales_id)
            obj_employee=self.pool.get('hr.employee')
            obj_search_empl=obj_employee.search(cr, uid,[('user_id','=',sales_id)])
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
            return {'value':{'sales_koordinator_id':False,'employee_id': obj_browse_empl.id},'domain':domain}
        return False
        
        
    # def onchange_source(self, cr, uid, ids,sales_source,branch_id):
    #     ids_location = []
    #     dom = {}
    #     val = {}
    #     val['sales_source_location'] = False
    #     if sales_source and branch_id :
    #         location_obj = self.pool.get('stock.location')
    #         ids_location = location_obj.search(cr, uid, [
    #                 ('jenis','=',sales_source),
    #                 ('branch_id','=',branch_id),
    #                 ('start_date','<=',self._get_default_date(cr, uid, ids, context=None)),
    #                 ('end_date','>=',self._get_default_date(cr, uid, ids, context=None)),
    #             ])
    #         #ids_location_obj_browse= location_obj.browse(cr, uid, ids_location_obj)
    #         #for loca in ids_location_obj_browse :
    #         #    ids_location.append(loca.id)
    #         dom['sales_source_location']=[('id','in',ids_location)]
    #     else :
    #         dom['sales_source_location']=[('id','=',0)]
    #     return {'value':val, 'domain':dom}

    def action_invoice_create(self, cr, uid, ids, context=None):
        sale_order = self.browse(cr, uid, ids, context)
        if not sale_order or not sale_order.ensure_one():
            raise osv.except_osv(_('Error!'),
                _('action_invoice_create() method only for single object.'))
        elif not sale_order.dealer_sale_order_line:
            raise osv.except_osv(_('Error!'),
                _('Harap isi detil sale order terlebih dahulu.'))

        obj_inv = self.pool.get('account.invoice') 
        account_id = False
        ar_branch_id = False
        ap_branch_id = False
        default_supplier = False
        
        #untuk DP konsumen
        invoice_customer = {}
        invoice_customer_line = []
        
        #invoice finco
        invoice_finco = {}
        invoice_finco_line = []
        
        #invoice finco
        invoice_pelunasan = {}
        invoice_pelunasan_line = []
        
        #invoice bbn
        invoice_bbn = {}
        invoice_bbn_line = []
        
        invoice_insentif_finco = {}
        invoice_insentif_finco_line = []
        
        invoice_hc = {}
        invoice_hc_line = []

        invoice_accrue_ekspedisi = {}
        invoice_accrue_ekspedisi_line = []

        invoice_accrue_proses_bbn = {}
        invoice_accrue_proses_bbn_line = []

        qty_bbn = 0
        accrue_ekspedisi = sale_order.branch_id.accrue_ekspedisi
        accrue_proses_bbn = sale_order.branch_id.accrue_proses_bbn

        obj_bbn = self.pool.get('wtc.harga.bbn.line')

        #get AR & AP account dari setting cabang
        obj_branch_config = self._get_branch_journal_config(cr,uid,sale_order.branch_id.id)
        
        if accrue_ekspedisi > 0:
            if not (obj_branch_config.dealer_so_journal_accrue_ekspedisi_id.default_credit_account_id.id and obj_branch_config.dealer_so_journal_accrue_ekspedisi_id.default_debit_account_id.id):
                raise osv.except_osv(('Perhatian !'), ("Konfigurasi journal accrue belum lengkap!"))
        if accrue_proses_bbn > 0:
            if not (obj_branch_config.dealer_so_journal_accrue_proses_bbn_id.default_credit_account_id.id and obj_branch_config.dealer_so_journal_accrue_proses_bbn_id.default_debit_account_id.id):
                raise osv.except_osv(('Perhatian !'), ("Konfigurasi journal accrue belum lengkap!"))
        
        finco = False
        if not obj_branch_config.dealer_so_journal_pelunasan_id.default_debit_account_id.id:
            raise osv.except_osv(('Perhatian !'), ("Konfigurasi account debet jurnal pelunasan belum lengkap!"))
        
        #=======================================================================
        # Collecting invoice data for customer and finco(if exist) 
        #=======================================================================
        obj_ir_model = self.pool.get('ir.model')
        if sale_order.finco_id:
        #fetch finco data
            if not (obj_branch_config.dealer_so_journal_insentive_finco_id.default_debit_account_id.id and obj_branch_config.dealer_so_journal_insentive_finco_id.default_credit_account_id.id):
                raise osv.except_osv(('Perhatian !'), ("Konfigurasi account debet kredit jurnal insentif belum lengkap!"))
            
            finco = sale_order.finco_id.id
            invoice_pelunasan = {
                'name':sale_order.name,
                'origin': sale_order.name,
                'branch_id':sale_order.branch_id.id,
                'division':sale_order.division,
                'partner_id':sale_order.finco_id.id,
                'date_invoice':sale_order.date_order,
                'reference_type':'none',
                'type': 'out_invoice', 
                'tipe': 'finco',
                'qq_id': sale_order.partner_id.id,
                'journal_id': obj_branch_config.dealer_so_journal_pelunasan_id.id,
                'account_id': obj_branch_config.dealer_so_journal_pelunasan_id.default_debit_account_id.id,
                'payment_term': sale_order.payment_term.id,
                'section_id':sale_order.section_id.id,
                'transaction_id': sale_order.id,
                'model_id': obj_ir_model.search(cr, uid, [('model','=',sale_order.__class__.__name__)])[0],
            }
            invoice_insentif_finco = {
                'name':sale_order.name,
                'origin': sale_order.name,
                'branch_id':sale_order.branch_id.id,
                'division':sale_order.division,
                'partner_id':sale_order.finco_id.id,
                'date_invoice':sale_order.date_order,
                'reference_type':'none',
                'type': 'out_invoice', 
                'tipe': 'insentif',
                'qq_id': sale_order.partner_id.id,
                'payment_term': sale_order.payment_term.id,
                'journal_id': obj_branch_config.dealer_so_journal_insentive_finco_id.id,
                'account_id': obj_branch_config.dealer_so_journal_insentive_finco_id.default_debit_account_id.id,
                'transaction_id': sale_order.id,
                'model_id': obj_ir_model.search(cr, uid, [('model','=',sale_order.__class__.__name__)])[0],
            }
        else:
             invoice_pelunasan = {
                'name':sale_order.name,
                'origin': sale_order.name,
                'branch_id':sale_order.branch_id.id,
                'division':sale_order.division,
                'partner_id':sale_order.partner_id.id,
                'date_invoice':sale_order.date_order,
                'reference_type':'none',
                'type': 'out_invoice', 
                'tipe': 'customer',
                'journal_id': obj_branch_config.dealer_so_journal_pelunasan_id.id,
                'account_id': obj_branch_config.dealer_so_journal_pelunasan_id.default_debit_account_id.id,
                'payment_term': sale_order.payment_term.id,
                'section_id':sale_order.section_id.id,     
                'transaction_id': sale_order.id,
                'model_id': obj_ir_model.search(cr, uid, [('model','=',sale_order.__class__.__name__)])[0],                               
            }
        
        if sale_order.partner_komisi_id:
            if not (obj_branch_config.dealer_so_journal_hc_id.default_credit_account_id.id and obj_branch_config.dealer_so_journal_hc_id.default_debit_account_id.id):
                raise osv.except_osv(('Perhatian !'), ("Konfigurasi account debet kredit jurnal HC belum lengkap!"))
            invoice_hc = {
                        'name':sale_order.name,
                        'origin': sale_order.name,
                        'branch_id':sale_order.branch_id.id,
                        'division':sale_order.division,
                        'partner_id':sale_order.partner_komisi_id.id,
                        'date_invoice':sale_order.date_order,
                        'reference_type':'none',
                        'type': 'in_invoice', 
                        'tipe': 'hc',
                        'journal_id': obj_branch_config.dealer_so_journal_hc_id.id,
                        'account_id': obj_branch_config.dealer_so_journal_hc_id.default_credit_account_id.id,
                        'transaction_id': sale_order.id,
                        'model_id': obj_ir_model.search(cr, uid, [('model','=',sale_order.__class__.__name__)])[0],
                          
                          }

        per_product = {}
        per_potongan = {}
        per_barang_bonus = {}
        per_invoice = []

        for line in sale_order.dealer_sale_order_line:
            
            if not per_product.get(line.product_id.id,False):
                per_product[line.product_id.id] = {}
                
            per_product[line.product_id.id]['product_qty'] = per_product[line.product_id.id].get('product_qty',0)+line.product_qty
            per_product[line.product_id.id]['price_unit'] = per_product[line.product_id.id].get('price_unit',0)+line.price_unit
            per_product[line.product_id.id]['force_cogs'] = per_product[line.product_id.id].get('force_cogs',0)+line.force_cogs

            if line.is_bbn == 'Y':
                #update accrue value            
                if accrue_ekspedisi != line.accrue_ekspedisi or accrue_proses_bbn != line.accrue_proses_bbn:
                    line.write({
                        'accrue_ekspedisi': accrue_ekspedisi,
                        'accrue_proses_bbn': accrue_proses_bbn
                    })
                #for accrue ekspedisi & proses bbn
                qty_bbn += line.product_qty

                if not (obj_branch_config.dealer_so_journal_bbnbeli_id.default_credit_account_id.id and obj_branch_config.dealer_so_journal_bbnbeli_id.default_debit_account_id.id):
                    raise osv.except_osv(('Perhatian !'), ("Konfigurasi account debet kredit jurnal BBN Beli belum lengkap!"))
            
                per_product[line.product_id.id]['price_bbn'] = per_product[line.product_id.id].get('price_bbn',0)+line.price_bbn
                per_product[line.product_id.id]['product_qty_bbn'] = per_product[line.product_id.id].get('product_qty_bbn',0)+line.product_qty
               
                biro_line = self.pool.get('dealer.spk')._get_harga_bbn_detail(cr, uid, ids, line.biro_jasa_id.id, line.plat, line.city_id.id, line.product_id.product_tmpl_id.id,sale_order.branch_id.id)
                total = 0
                if not biro_line:
                    total = line.price_bbn_beli
                else:
                    total = biro_line.notice+biro_line.proses+biro_line.jasa+biro_line.jasa_area+biro_line.fee_pusat
                    line.write({
                        'price_bbn_beli': biro_line.notice+biro_line.proses+biro_line.jasa+biro_line.jasa_area+biro_line.fee_pusat,
                        'price_bbn_notice': biro_line.notice,
                        'price_bbn_proses': biro_line.proses,
                        'price_bbn_jasa': biro_line.jasa,
                        'price_bbn_jasa_area': biro_line.jasa_area,
                        'price_bbn_fee_pusat': biro_line.fee_pusat,
                    })

                invoice_bbn = {
                    'name':sale_order.name,
                    'origin':sale_order.name,
                    'branch_id':sale_order.branch_id.id,
                    'division':sale_order.division,
                    'partner_id':line.biro_jasa_id.id,
                    'date_invoice':sale_order.date_order,
                    'reference_type':'none',
                    'type':'in_invoice', 
                    'tipe':'bbn',
                    'qq_id':sale_order.partner_id.id, 
                    'lot_id':line.lot_id.id,
                    'journal_id': obj_branch_config.dealer_so_journal_bbnbeli_id.id,
                    'account_id': obj_branch_config.dealer_so_journal_bbnbeli_id.default_credit_account_id.id,
                    'transaction_id': sale_order.id,
                    'model_id': obj_ir_model.search(cr, uid, [('model','=',sale_order.__class__.__name__)])[0],
                    'dealer_sale_order_store_line_id' : line.id,
                }
                invoice_bbn_line  = [[0,False,{
                    'partner_id':line.biro_jasa_id.id,
                    'name': 'Sales BBN '+line.product_id.name,
                    'quantity': 1,
                    'origin': sale_order.name,
                    'price_unit':total,
                    'price_subtotal':total,
                    'account_id': obj_branch_config.dealer_so_journal_bbnbeli_id.default_debit_account_id.id
                }]]
                invoice_bbn['invoice_line']=invoice_bbn_line
                per_invoice.append(invoice_bbn)
            
            if line.hutang_komisi_id and line.amount_hutang_komisi:
                per_product[line.product_id.id]['amount_hutang_komisi'] = per_product[line.product_id.id].get('amount_hutang_komisi',0)+line.amount_hutang_komisi
            
            per_product[line.product_id.id]['customer_dp'] = per_product[line.product_id.id].get('customer_dp',0)+line.uang_muka
            insentif_finco, insentif_finco_tax = line._get_insentif_finco_value(finco,sale_order.branch_id.id)
            line.write({'insentif_finco':insentif_finco,'insentif_finco_tax':insentif_finco_tax})
            per_product[line.product_id.id]['insentif_finco'] = per_product[line.product_id.id].get('insentif_finco',0)+insentif_finco
            per_product[line.product_id.id]['insentif_finco_tax'] = insentif_finco_tax
            per_potongan['discount_po'] = per_potongan.get('discount_po',0)+line.discount_po
            
            for disc in line.discount_line:
                invoice_ps_finco = {}
                invoice_ps_finco_line = []
        
                per_potongan['discount_pelanggan'] = per_potongan.get('discount_pelanggan',0)+disc.discount_pelanggan
                discount_gap = 0.0
                discount_md = 0.0
                discount_finco = 0.0
                discount_oi = 0.0
                sisa_ke_finco = False
                
                if disc.discount_pelanggan != disc.discount:
                     discount_gap =  disc.discount - disc.discount_pelanggan
                taxes = [(6, 0, [y.id for y in line.tax_id])]
                
                if disc.ps_finco > 0:
                    if not (obj_branch_config.dealer_so_journal_psfinco_id.default_credit_account_id.id and obj_branch_config.dealer_so_journal_psfinco_id.default_debit_account_id.id):
                        raise osv.except_osv(('Perhatian !'), ("Konfigurasi account debet kredit jurnal PS Finco belum lengkap!"))
                
                    invoice_ps_finco = {
                        'name':sale_order.name,
                        'origin': sale_order.name,
                        'branch_id':sale_order.branch_id.id,
                        'division':sale_order.division,
                        'partner_id':sale_order.finco_id.id,
                        'date_invoice':self._get_default_date(cr, uid, ids),
                        'reference_type':'none',
                        'payment_term': sale_order.payment_term.id,
                        'type': 'out_invoice', 
                        'tipe': 'ps_finco',
                        'qq_id': sale_order.partner_id.id,
                        'journal_id': obj_branch_config.dealer_so_journal_psfinco_id.id,
                        'account_id': obj_branch_config.dealer_so_journal_psfinco_id.default_debit_account_id.id,
                        'transaction_id': sale_order.id,
                        'model_id': obj_ir_model.search(cr, uid, [('model','=',sale_order.__class__.__name__)])[0], 
                    }
                    
                    if discount_gap >0:
                        if disc.ps_finco > discount_gap: 
                            discount_finco = disc.ps_finco - discount_gap
                            discount_oi = discount_gap
                            sisa_ke_finco = True
                        elif disc.ps_finco == discount_gap:
                            discount_finco = disc.ps_finco
                        else:
                            discount_oi = discount_gap - disc.ps_finco
                            discount_finco = disc.ps_finco - discount_oi
                            discount_gap = discount_gap - discount_oi
                        
                        if discount_finco > 0:   
                            invoice_ps_finco_line.append([0,False,{
                                'name': 'Subsidi '+disc.program_subsidi.name+' '+line.product_id.name,
                                'quantity': 1,
                                'origin': sale_order.name,
                                'price_unit':discount_finco,
                                'account_id': obj_branch_config.dealer_so_journal_psfinco_id.default_credit_account_id.id
                            }])
                        
                        if discount_oi>0:
                            invoice_ps_finco_line.append([0,False,{
                                'name': 'Sisa subsidi '+disc.program_subsidi.name+' '+line.product_id.name,
                                'quantity': 1,
                                'origin': sale_order.name,
                                'price_unit':discount_oi,
                                'account_id': obj_branch_config.dealer_so_account_sisa_subsidi_id.id
                            }])
                        
                    else:
                        invoice_ps_finco_line.append([0,False,{
                            'name': 'Subsidi '+disc.program_subsidi.name+' '+line.product_id.name,
                            'quantity': 1,
                            'origin': sale_order.name,
                            'price_unit':disc.ps_finco,
                            'account_id': obj_branch_config.dealer_so_journal_psfinco_id.default_credit_account_id.id
                        }])
                        sisa_ke_finco = True
                        
                    invoice_ps_finco['invoice_line'] = invoice_ps_finco_line
                    per_invoice.append(invoice_ps_finco)
                
                if (disc.ps_ahm > 0 or disc.ps_md > 0):
                    #invoice ps_ahm
                    invoice_md = {}
                    invoice_md_line = []
        
                    if not (obj_branch_config.dealer_so_journal_psmd_id.default_credit_account_id.id and obj_branch_config.dealer_so_journal_psmd_id.default_debit_account_id.id):
                        raise osv.except_osv(('Perhatian !'), ("Konfigurasi account debet kredit jurnal PS MD belum lengkap!"))
                    if not sale_order.branch_id.default_supplier_id.id:
                        raise osv.except_osv(('Perhatian !'), ("Principle di branch belum diisi, silahkan setting dulu!"))
                    invoice_md = {
                        'name':sale_order.name,
                        'origin': sale_order.name,
                        'branch_id':sale_order.branch_id.id,
                        'division':sale_order.division,
                        'partner_id':sale_order.branch_id.default_supplier_id.id,
                        'date_invoice':self._get_default_date(cr, uid, ids),
                        'reference_type':'none',
                        'type': 'out_invoice', 
                        #'amount_total':detail.price_bbn,
                        'tipe': 'ps_md',
                        #'qq_id':sale_order.partner_id.id, 
                        'journal_id': obj_branch_config.dealer_so_journal_psmd_id.id,
                        'account_id': obj_branch_config.dealer_so_journal_psmd_id.default_debit_account_id.id,
                        'transaction_id': sale_order.id,
                        'model_id': obj_ir_model.search(cr, uid, [('model','=',sale_order.__class__.__name__)])[0],
                    }
                    
                    if sisa_ke_finco == False:
                        if discount_gap >0:
                            if (disc.ps_md+disc.ps_ahm) >= discount_gap:
                                discount_md = disc.ps_md+disc.ps_ahm-discount_gap
                                discount_oi = discount_gap
                            else:
                                discount_md = discount_gap - disc.ps_md- disc.ps_ahm
                            
                            if discount_md>0:  
                                invoice_md_line.append([0,False,{
                                    'name': 'Subsidi '+disc.program_subsidi.name+' '+line.product_id.name,
                                    'quantity': 1,
                                    'origin': sale_order.name,
                                    'price_unit':discount_md/1.1,
                                    'account_id': obj_branch_config.dealer_so_journal_psmd_id.default_credit_account_id.id
                                }])
                            
                            if discount_oi>0:
                                invoice_md_line.append([0,False,{
                                    'name': 'Sisa subsidi '+disc.program_subsidi.name+' '+line.product_id.name,
                                    'quantity': 1,
                                    'origin': sale_order.name,
                                    'price_unit':discount_gap/1.1,
                                    'account_id': obj_branch_config.dealer_so_account_sisa_subsidi_id.id
                                }])
                        else:
                            invoice_md_line.append([0,False,{
                                'name': 'Subsidi '+disc.program_subsidi.name+' '+line.product_id.name,
                                'quantity': 1,
                                'origin': sale_order.name,
                                'price_unit':(disc.ps_ahm+disc.ps_md)/1.1,
                                'account_id': obj_branch_config.dealer_so_journal_psmd_id.default_credit_account_id.id
                            }])
                        
                    else:
                        invoice_md_line.append([0,False,{
                            'name': 'Subsidi '+disc.program_subsidi.name+' '+line.product_id.name,
                            'quantity': 1,
                            'origin': sale_order.name,
                            'price_unit':(disc.ps_ahm+disc.ps_md)/1.1,
                            'account_id': obj_branch_config.dealer_so_journal_psmd_id.default_credit_account_id.id
                        }])
                            
                    invoice_md['invoice_line'] = invoice_md_line
                    
                    per_invoice.append(invoice_md)
                

            for barang_bonus in line.barang_bonus_line:
                if not per_barang_bonus.get(barang_bonus.product_subsidi_id.id,False):
                    per_barang_bonus[barang_bonus.product_subsidi_id.id] = {}
                per_barang_bonus[barang_bonus.product_subsidi_id.id]['product_qty'] = per_barang_bonus[barang_bonus.product_subsidi_id.id].get('product_qty',0)+ barang_bonus.barang_qty
                per_barang_bonus[barang_bonus.product_subsidi_id.id]['force_cogs'] = per_barang_bonus[barang_bonus.product_subsidi_id.id].get('force_cogs',0)+barang_bonus.price_barang
                if barang_bonus.bb_md > 0 or barang_bonus.bb_ahm > 0:
                    invoice_bb_md = {}
                    invoice_bb_md_line = []
                    
                    if not (obj_branch_config.dealer_so_journal_bbmd_id.default_credit_account_id.id and obj_branch_config.dealer_so_journal_bbmd_id.id):
                        raise osv.except_osv(('Perhatian !'), ("Konfigurasi account debet kredit jurnal Barang Subsidi MD belum lengkap!"))
                    invoice_bb_md = {
                        'name':sale_order.name,
                        'origin': sale_order.name,
                        'branch_id':sale_order.branch_id.id,
                        'division':sale_order.division,
                        'partner_id':sale_order.branch_id.default_supplier_id.id,#default_suplier['default_supplier_id']['id'],
                        'date_invoice':self._get_default_date(cr, uid, ids),
                        'reference_type':'none',
                        'type': 'out_invoice', 
                        'tipe': 'bb_md',
                        'qq_id': sale_order.partner_id.id,
                        'journal_id': obj_branch_config.dealer_so_journal_bbmd_id.id,
                        'account_id': obj_branch_config.dealer_so_journal_bbmd_id.default_debit_account_id.id,
                        'transaction_id': sale_order.id,
                        'model_id': obj_ir_model.search(cr, uid, [('model','=',sale_order.__class__.__name__)])[0], 
                    }
                    invoice_bb_md_line = [[0,False,{
                        'name': 'Subsidi '+barang_bonus.barang_subsidi_id.name+' '+line.product_id.name,
                        'quantity': 1,
                        'origin': sale_order.name,
                        'price_unit':barang_bonus.bb_ahm+barang_bonus.bb_md ,
                        'account_id': obj_branch_config.dealer_so_journal_bbmd_id.default_credit_account_id.id
                    }]]
                    invoice_bb_md['invoice_line'] = invoice_bb_md_line
                    per_invoice.append(invoice_bb_md)
                if barang_bonus.bb_finco > 0:
                    invoice_bb_finco = {}
                    invoice_bb_finco_line = []
                    if not (obj_branch_config.dealer_so_journal_bbfinco_id.default_credit_account_id.id and obj_branch_config.dealer_so_journal_bbfinco_id.id):
                        raise osv.except_osv(('Perhatian !'), ("Konfigurasi account debet kredit jurnal Barang Subsidi Finco belum lengkap!"))
                    invoice_bb_finco = {
                        'name':sale_order.name,
                        'origin': sale_order.name,
                        'branch_id':sale_order.branch_id.id,
                        'division':sale_order.division,
                        'partner_id':sale_order.finco_id.id,
                        'date_invoice':self._get_default_date(cr, uid, ids),
                        'reference_type':'none',
                        'type': 'out_invoice', 
                        'tipe': 'bb_finco',
                        'qq_id': sale_order.partner_id.id,
                        'journal_id': obj_branch_config.dealer_so_journal_bbfinco_id.id,
                        'account_id': obj_branch_config.dealer_so_journal_bbfinco_id.default_debit_account_id.id,
                        'transaction_id': sale_order.id,
                        'model_id': obj_ir_model.search(cr, uid, [('model','=',sale_order.__class__.__name__)])[0], 
                    }
                    invoice_bb_finco_line = [[0,False,{
                        'name': 'Subsidi '+barang_bonus.barang_subsidi_id.name+' '+line.product_id.name,
                        'quantity': 1,
                        'origin': sale_order.name,
                        'price_unit':barang_bonus.bb_finco ,
                        'account_id': obj_branch_config.dealer_so_journal_bbfinco_id.default_credit_account_id.id
                    }]]
                    invoice_bb_finco['invoice_line'] = invoice_bb_finco_line
                    per_invoice.append(invoice_bb_finco)

        for key, value in per_product.items():
            product_id = self.pool.get('product.product').browse(cr,uid,key)

            invoice_pelunasan_line.append([0,False,{
                    'name':product_id.name,
                    'product_id':product_id.id,
                    'quantity':value['product_qty'],
                    'origin':sale_order.name,
                    'price_unit':((value['price_unit'])/value['product_qty']),
                    'invoice_line_tax_id': [(6,0,[2])],
                    'account_id': self.pool.get('product.product')._get_account_id(cr,uid,ids,product_id.id),
                    'force_cogs': value.get('force_cogs',0)
                }])
            
            if value.get('product_qty_bbn',0) > 0:
                invoice_pelunasan_line.append([0,False,{
                        'name': 'BBN '+str(product_id.name),
                        'quantity':value['product_qty'],
                        'origin':sale_order.name,
                        'price_unit':value['price_bbn']/value['product_qty_bbn'],
                        'account_id': obj_branch_config.dealer_so_account_bbn_jual_id.id
                    }])
            if value.get('customer_dp',0) > 0:
                invoice_pelunasan_line.append([0,False,{
                        'name':'Customer DP',
                        'quantity':1,
                        'origin':sale_order.name,
                        'price_unit':-1*value['customer_dp'],
                        'account_id': obj_branch_config.dealer_so_journal_dp_id.default_credit_account_id.id
                    }])
            if value.get('insentif_finco',0) > 0:
                invoice_insentif_finco_line.append([0,False,{
                        'name': 'Insentif '+str(product_id.name),
                        'quantity': value['product_qty'],
                        'origin': sale_order.name,
                        'price_unit':value['insentif_finco']/value['product_qty'],
                        'invoice_line_tax_id': [(6,0,[2])] if value['insentif_finco_tax'] else [],
                        'account_id': obj_branch_config.dealer_so_journal_insentive_finco_id.default_credit_account_id.id
                    }])
                
            if value.get('amount_hutang_komisi') > 0:
                invoice_hc_line.append([0,False,{
                        'name': 'Hutang Komisi '+str(product_id.name),
                        'quantity': value['product_qty'],
                        'origin': sale_order.name,
                        'price_unit':value['amount_hutang_komisi']/value['product_qty'],
                        'account_id': obj_branch_config.dealer_so_journal_hc_id.default_debit_account_id.id
                    }])
        
        for key, value in per_potongan.items():
            if value > 0:
                price_unit = -1*value
                tax = [(6,0,[2])]
                if key=='discount_po':
                    invoice_pelunasan_line.append([0,False,{
                            'name': 'Diskon Reguler',
                            'quantity':1,
                            'origin':sale_order.name,
                            'price_unit':price_unit,
                            'invoice_line_tax_id':tax,
                            'account_id': obj_branch_config.dealer_so_account_potongan_langsung_id.id
                        }])
                
                if key=='discount_pelanggan':
                    invoice_pelunasan_line.append([0,False,{
                            'name': 'Diskon Quotation',
                            'quantity':1,
                            'origin':sale_order.name,
                            'price_unit':price_unit,
                            'invoice_line_tax_id':tax,
                            'account_id': obj_branch_config.dealer_so_account_potongan_subsidi_id.id
                        }])
        for key, value in per_barang_bonus.items():
            product_id = self.pool.get('product.product').browse(cr,uid,key)
            invoice_pelunasan_line.append([0,False,{
                    'name':product_id.name,
                    'product_id':product_id.id,
                    'quantity':value['product_qty'],
                    'origin':sale_order.name,
                    'price_unit': 0,
                    'account_id': self.pool.get('product.product')._get_account_id(cr,uid,ids,product_id.id),
                    'force_cogs': value.get('force_cogs',0)
                }])
                    

                    #TODO assign account to sales diskon quotation
                    #invoice_pelunasan_line.append([0,False,{
                    #        'name': 'Sales Quotation',
                    #        'quantity':1,
                    #        'origin':sale_order.name,
                    #        'price_unit':value/1.1,
                    #        #'invoice_line_tax_id':tax,
                    #        'account_id': obj_branch_config.dealer_so_account_potongan_subsidi_id.id
                    #    }])
                    
        if invoice_insentif_finco_line:
            invoice_insentif_finco['invoice_line']=invoice_insentif_finco_line
            create_invoice_insentif = obj_inv.create(cr,uid,invoice_insentif_finco)
            obj_inv.button_reset_taxes(cr,uid,create_invoice_insentif)
            workflow.trg_validate(uid, 'account.invoice', create_invoice_insentif, 'invoice_open', cr)  
            
        if invoice_hc_line:
            invoice_hc['invoice_line']=invoice_hc_line
            create_invoice_hc = obj_inv.create(cr,uid,invoice_hc)
            obj_inv.button_reset_taxes(cr,uid,create_invoice_hc)
            workflow.trg_validate(uid, 'account.invoice', create_invoice_hc, 'invoice_open', cr)
            
        for value in per_invoice:
            create_invoice = obj_inv.create(cr,uid,value)
            obj_inv.button_reset_taxes(cr,uid,create_invoice)
            workflow.trg_validate(uid, 'account.invoice', create_invoice, 'invoice_open', cr)  
        
        if qty_bbn > 0:
            if accrue_ekspedisi > 0:
                invoice_accrue_ekspedisi = {
                    'name':sale_order.name,
                    'origin': sale_order.name,
                    'branch_id':sale_order.branch_id.id,
                    'division':sale_order.division,
                    'partner_id':sale_order.branch_id.partner_id.id,
                    'date_invoice':sale_order.date_order,
                    'reference_type':'none',
                    'type': 'in_invoice', 
                    'tipe': 'accrue',
                    'journal_id': obj_branch_config.dealer_so_journal_accrue_ekspedisi_id.id,
                    'account_id': obj_branch_config.dealer_so_journal_accrue_ekspedisi_id.default_credit_account_id.id,
                    'transaction_id': sale_order.id,
                    'model_id': obj_ir_model.search(cr, uid, [('model','=',sale_order.__class__.__name__)])[0],                               
                }
                invoice_accrue_ekspedisi_line.append([0,False,{
                    'name': 'Accrue Dana Ongkos Angkut '+str(sale_order.name),
                    'quantity': qty_bbn,
                    'origin': sale_order.name,
                    'price_unit': accrue_ekspedisi,
                    'account_id': obj_branch_config.dealer_so_journal_accrue_ekspedisi_id.default_debit_account_id.id
                }])
                invoice_accrue_ekspedisi['invoice_line']=invoice_accrue_ekspedisi_line
                create_invoice_accrue_ekspedisi = obj_inv.create(cr,uid,invoice_accrue_ekspedisi)
                obj_inv.button_reset_taxes(cr,uid,create_invoice_accrue_ekspedisi)
                workflow.trg_validate(uid, 'account.invoice', create_invoice_accrue_ekspedisi, 'invoice_open', cr)

            if accrue_proses_bbn > 0:
                invoice_accrue_proses_bbn = {
                    'name':sale_order.name,
                    'origin': sale_order.name,
                    'branch_id':sale_order.branch_id.id,
                    'division':sale_order.division,
                    'partner_id':sale_order.branch_id.partner_id and sale_order.branch_id.partner_id.id,
                    'date_invoice':sale_order.date_order,
                    'reference_type':'none',
                    'type': 'in_invoice', 
                    'tipe': 'accrue',
                    'journal_id': obj_branch_config.dealer_so_journal_accrue_proses_bbn_id.id,
                    'account_id': obj_branch_config.dealer_so_journal_accrue_proses_bbn_id.default_credit_account_id.id,
                    'transaction_id': sale_order.id,
                    'model_id': obj_ir_model.search(cr, uid, [('model','=',sale_order.__class__.__name__)])[0],                               
                }
                invoice_accrue_proses_bbn_line.append([0,False,{
                    'name': 'Accrue Biaya Proses BBN '+str(sale_order.name),
                    'quantity': qty_bbn,
                    'origin': sale_order.name,
                    'price_unit': accrue_proses_bbn,
                    'account_id': obj_branch_config.dealer_so_journal_accrue_proses_bbn_id.default_debit_account_id.id
                }])
                invoice_accrue_proses_bbn['invoice_line']=invoice_accrue_proses_bbn_line
                create_invoice_accrue_proses_bbn = obj_inv.create(cr,uid,invoice_accrue_proses_bbn)
                obj_inv.button_reset_taxes(cr,uid,create_invoice_accrue_proses_bbn)
                workflow.trg_validate(uid, 'account.invoice', create_invoice_accrue_proses_bbn, 'invoice_open', cr)

        invoice_pelunasan['invoice_line']= invoice_pelunasan_line
        create_invoice_pelunasan = obj_inv.create(cr,uid,invoice_pelunasan)
        obj_inv.button_reset_taxes(cr,uid,create_invoice_pelunasan)
        workflow.trg_validate(uid, 'account.invoice', create_invoice_pelunasan, 'invoice_open', cr)
        if not sale_order.finco_id and sale_order.hutang_lain_line :
            self.auto_journal_and_reconcile(cr,uid,ids,create_invoice_pelunasan)
        #if sale_order.amount_tax and not sale_order.pajak_gabungan :   
            #self.pool.get('wtc.faktur.pajak.out').get_no_faktur_pajak(cr,uid,ids,'dealer.sale.order',context=context)        
        return create_invoice_pelunasan 
        
    def action_invoice_dp_create(self,cr,uid,ids,context=None):
        invoice_customer = {}
        invoice_customer_line = []
        
        obj_inv = self.pool.get('account.invoice')
        
       
        
        for line in self.browse(cr, uid, ids, context=context): 
            
            #Get property of branch
            obj_branch_id = self.pool.get('wtc.branch.config').search(cr,uid,[('branch_id','=',line.branch_id.id)])
            
            
            if not obj_branch_id:
                raise osv.except_osv(_('Error!'),
                    _('Jurnal tidak ditemukan silahkan configurasi dulu: "%s" .') % \
                    (line.branch_id.name))
            
            obj_branch_config = self.pool.get('wtc.branch.config').browse(cr,uid,obj_branch_id[0])
            if not (obj_branch_config.dealer_so_journal_dp_id.default_debit_account_id.id and obj_branch_config.dealer_so_journal_dp_id.default_credit_account_id.id):
                raise osv.except_osv(('Perhatian !'), ("Konfigurasi account debet kredit jurnal DP belum lengkap!"))
            if line.dealer_sale_order_line:
                obj_ir_model = self.pool.get('ir.model')
                if line.finco_id:
                    invoice_customer = {
                                    'name':line.name,
                                    'origin': line.name,
                                    'branch_id':line.branch_id.id,
                                    'division':line.division,
                                    'partner_id':line.partner_id.id,
                                    'date_invoice':line.date_order,
                                    'reference_type':'none',
                                    'type': 'out_invoice',                                    
                                    #'payment_term':val.payment_term,
                                    'tipe': 'customer',
                                    'journal_id': obj_branch_config.dealer_so_journal_dp_id.id,
                                    'account_id': obj_branch_config.dealer_so_journal_dp_id.default_debit_account_id.id,
                                    'transaction_id': line.id,
                                    'model_id': obj_ir_model.search(cr, uid, [('model','=',line.__class__.__name__)])[0],
                                    }
                    invoice_customer_line.append([0,False,{
                                                    'name': 'Customer DP',
                                                    'quantity': 1,
                                                    'origin': line.name,
                                                    'price_unit':line.customer_dp,
                                                    'account_id': obj_branch_config.dealer_so_journal_dp_id.default_credit_account_id.id
                                                    }])
                invoice_customer['invoice_line'] = invoice_customer_line
                
                invoice_dp_create = obj_inv.create(cr,uid,invoice_customer)
                workflow.trg_validate(uid, 'account.invoice', invoice_dp_create, 'invoice_open', cr)
                
                # Jika ada Alokasi DP: otomatis membuat jurnal & di reconcile ke Invoice DP
                if line.hutang_lain_line :
                    self.auto_journal_and_reconcile(cr,uid,ids,invoice_dp_create)
                
        return invoice_dp_create
    
    def auto_journal_and_reconcile(self,cr,uid,ids,invoice_id):
        ids_to_reconcile = []
        dso = self.browse(cr,uid,ids)
        if dso.hutang_lain_line:
            obj_account_move = self.pool.get('account.move')
            obj_account_move_line = self.pool.get('account.move.line')
            date = self._get_default_date(cr,uid,ids)
            period_id = self.pool.get('account.period').find(cr,uid,date)[0]
            total_hl = 0
            invoice_obj=self.pool.get('account.invoice').browse(cr,uid,invoice_id)
            
            obj_branch_id = self.pool.get('wtc.branch.config').search(cr,uid,[('branch_id','=',dso.branch_id.id)])
            if not obj_branch_id:
                raise osv.except_osv(_('Error!'),
                    _('Jurnal tidak ditemukan silahkan configurasi dulu: "%s" .') % \
                    (dso.branch_id.name))
            
            obj_branch_config = self.pool.get('wtc.branch.config').browse(cr,uid,obj_branch_id[0])
            if not (obj_branch_config.dealer_so_journal_hl_id):
                raise osv.except_osv(('Perhatian !'), ("Konfigurasi Jurnal Reconcile HL belum disetting!"))
                
            create_acc_move = obj_account_move.create(cr,uid,{
                    'journal_id': obj_branch_config.dealer_so_journal_hl_id.id,
                    'line_id': [],
                    'period_id': period_id,
                    'date': date,
                    'ref':  dso.name,
                    'name': self.pool.get('ir.sequence').get_per_branch(cr, uid, dso.branch_id.id, 'AL',context=None)
                    })
            for hl_line in dso.hutang_lain_line:
                total_hl+=hl_line.amount_hl_allocation
                new_line_id = hl_line.hl_id.copy({
                    'move_id': create_acc_move,
                    'debit': hl_line.amount_hl_allocation,
                    'credit': 0,
                    'name': hl_line.hl_id.ref,
                    'ref': dso.name,
                    'tax_amount': hl_line.hl_id.tax_amount * -1
                    })
                if hl_line.hl_id.account_id.reconcile :
                        ids_to_reconcile.append([hl_line.hl_id.id,new_line_id.id])
            #ref samain, name beda            
            create_aml_piu = obj_account_move_line.create(cr,uid,{
                    'move_id': create_acc_move,
                    'debit': 0,
                    'credit': total_hl,
                    'name': invoice_obj.number,
                    'ref': dso.name,
                    'account_id': invoice_obj.account_id.id,
                    'partner_id': dso.partner_id.id,
                    'branch_id': dso.branch_id.id,
                    'division': dso.division
                                          })
            aml_piu_id = obj_account_move_line.search(cr,uid,[('move_id','=',invoice_obj.move_id.id),('account_id','=',invoice_obj.account_id.id)])
            ids_to_reconcile.append([aml_piu_id[0],create_aml_piu])
            for to_reconcile in ids_to_reconcile :
                obj_account_move_line.reconcile_partial(cr, uid, to_reconcile)
            self.write(cr,uid,ids,{'al_move_id':create_acc_move})
                                     
        
    
    def _get_status_inv(self,cr,uid,ids,origin):
        obj_inv = self.pool.get('account.invoice')
        
        obj = obj_inv.search(cr,uid,[
                                     ('origin','=',origin),
                                     ('type','=','out_invoice'),
                                     ('tipe','=','customer')
                                     ])
        if obj:
            invoice = obj_inv.browse(cr,uid,obj[0])
            if invoice.state == 'paid':
                return True
        return False
    
    def action_create_do2(self,cr,uid,ids,context=None):
        sales_obj = self.browse(cr,uid,ids)
        if sales_obj.picking_ids:
            return True
        elif self._get_status_inv(cr,uid,ids,sales_obj.name):
            self.action_create_picking(cr, uid, ids)
        elif sales_obj.is_cod:
            self.action_create_picking(cr, uid, ids)
            
        return True
    
    def action_create_do(self,cr,uid,ids,contex=None):
        do_obj = self.pool.get('stock.picking')
        move_obj = self.pool.get('stock.move')
        quant_obj = self.pool.get('stock.quant')
        #location_cust_id = self.pool.get('stock.location')
        quants_lot = []
        sales_obj = self.browse(cr,uid,ids)
        
        obj_model = self.pool.get('ir.model')
        obj_model_id = obj_model.search(cr,uid,[ ('model','=',sales_obj.__class__.__name__) ])
        obj_model_id_model = obj_model.browse(cr,uid,obj_model_id).id
        
        now = self._get_default_date(cr, uid, ids)
        tomorrow = now + timedelta(days=1)
        
        location = self._get_default_location_delivery_sales(cr,uid,ids)
        transfer_header = {
                           'branch_id': sales_obj.branch_id.id,
                           'division': sales_obj.division,
                           'origin': sales_obj.name,
                           'move_type': 'direct',
                           'invoice_state': 'invoiced',
                           'priority': '0',
                           'min_date': tomorrow,
                           #type 2 = delivery Order
                           'picking_type_id': location['picking_type_id'],
                           'model_id': obj_model_id_model,
                           'transaction_id': sales_obj.id,
                           }
        transfer_line = []
        barang_bonuses = {}
        extras = {}
        for lines in sales_obj['dealer_sale_order_line']:
            
            transfer_line.append([0,False,{
                                  'product_id': lines.product_id.id,
                                  'product_uom_qty': lines.product_qty,
                                  'name': lines.product_id.partner_ref,
                                  'location_id':lines.location_id.id,
                                  'invoice_state': 'invoiced',
                                  'product_uom': lines.product_id.uom_id.id,
                                  'restrict_lot_id': lines.lot_id.id,
                                  'origin': sales_obj.name,
                                  'location_dest_id':location['destination'],
                                  'undelivered_value': lines.force_cogs,
                                  'dealer_sale_order_line_id':lines.id,
                                  'branch_id': sales_obj.branch_id.id,
                                  }])
            
            #search quants by lot_id
            quant_id = quant_obj.search(cr,uid,[('lot_id','=',lines.lot_id.id)])[0]
            if quant_id:
                quants = quant_obj.browse(cr,uid,quant_id)
                quants_lot.append((quants,lines.product_qty))
            else:
                raise osv.except_osv(_('Perhatian!'),_('Tidak Ditemukan stok untuk no engine sales order!'))
            
            if lines.barang_bonus_line:
                for barang_bonus in lines.barang_bonus_line:
                    if not barang_bonuses.get(barang_bonus.product_subsidi_id.id,False):
                        barang_bonuses[barang_bonus.product_subsidi_id.id] = {}
                    barang_bonuses[barang_bonus.product_subsidi_id.id]['qty'] = barang_bonuses[barang_bonus.product_subsidi_id.id].get('qty',0) + barang_bonus.barang_qty
                    barang_bonuses[barang_bonus.product_subsidi_id.id]['price_barang'] = barang_bonuses[barang_bonus.product_subsidi_id.id].get('price_barang',0) + barang_bonus.price_barang

            if lines.product_id.categ_id.isParentName('Unit'):
                for x in lines.product_id.product_tmpl_id.extras_line:
                    extras[x.product_id] = extras.get(x.product_id,0)+x.quantity
    
        
        ##TODO: append bonus to transfer_line
        for key, qty in extras.items():
            transfer_line.append([0,False,{
                    'product_id':key.id,
                    'product_uom_qty':qty,
                    'name':key.partner_ref,
                    'location_id':location['source'],
                    'invoice_state':'none',
                    'product_uom':1,#key.uom_id,
                    'location_dest_id':location['destination'],
                    'dealer_sale_order_line_id':lines.id,
                    'branch_id': sales_obj.branch_id.id,
                    'origin': sales_obj.name,
                }])
        ##TODO: append extras to transfer_line
        for key, value in barang_bonuses.items():
            product_id = self.pool.get('product.product').browse(cr,uid,key)
            transfer_line.append([0,False,{
                          'product_id': product_id.id,
                          'product_uom_qty': value.get('qty',0),
                          'name': product_id.partner_ref,
                          'location_id': location['source'],
                          'invoice_state': 'invoiced',
                          'product_uom': 1,#key.uom_id,
                          'location_dest_id': location['destination'],
                          'dealer_sale_order_line_id':lines.id,
                          'branch_id': sales_obj.branch_id.id,
                          'origin': sales_obj.name,
                          'undelivered_value': value.get('price_barang',0),
                          }])

        #appaend move lines
        transfer_header['move_lines'] = transfer_line
        
        
        create_do = do_obj.create(cr,uid,transfer_header)
       
        if create_do:
            do_obj.action_confirm(cr, uid, [create_do])
            for pick in do_obj.browse(cr,uid,create_do):
                
                if pick.move_lines:
                    count_quants = 0
                    for move in pick.move_lines:
                        if move.state not in ('draft', 'cancel', 'done'):
                            if move.product_id.categ_id.isParentName('Unit'):
                                assign = move_obj.action_assign(cr,uid,move.id)
                                count_quants+=1
        
            
        return True
    
    def waktu_local(self,cr,uid,ids,context=None):
        return self.pool.get('wtc.branch').get_default_date(cr,uid,ids).strftime("%d-%m-%Y %H:%M")

    
    def update_serial_number(self,cr,uid,vals,lot_id):
        obj_lot = self.pool.get('stock.production.lot')
        update_lot = obj_lot.write(cr,uid,lot_id,vals)
        return True
    
    def action_view_invoice_cust(self,cr,uid,ids,context=None):
        mod_obj = self.pool.get('ir.model.data')
        
        act_obj = self.pool.get('ir.actions.act_window')
        
        result = mod_obj.get_object_reference(cr, uid, 'account', 'action_invoice_tree1')
        
        id = result and result[1] or False
        
        result = act_obj.read(cr, uid, [id], context=context)[0]
        
        res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_form')
        
        result['views'] = [(res and res[1] or False, 'form')]
        
        val = self.browse(cr, uid, ids)
        
        obj_inv = self.pool.get('account.invoice')
        
        obj = obj_inv.search(cr,uid,[
                                     ('origin','=',val.name),
                                     ('tipe','=','customer')
                                     ])
        result['res_id'] = obj[0] 
        return result
    
    def action_view_invoices(self,cr,uid,ids,context=None):
        mod_obj = self.pool.get('ir.model.data')
        
        act_obj = self.pool.get('ir.actions.act_window')
        
        result = mod_obj.get_object_reference(cr, uid, 'account', 'action_invoice_tree1')
        
        id = result and result[1] or False
        
        result = act_obj.read(cr, uid, [id], context=context)[0]
        
        val = self.browse(cr, uid, ids)
        obj_inv = self.pool.get('account.invoice')
        obj = obj_inv.search(cr,uid,[
                                     ('origin','=',val.name),
                                     ('type','=','out_invoice')
                                     ])
        
        if len(obj)>0:
            result['domain'] = "[('id','in',["+','.join(map(str, obj))+"])]"
        else:
            res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_form')
            result['views'] = [(res and res[1] or False, 'form')]
            result['res_id'] = obj[0] 
        return result

        
    def action_view_invoice_finco(self,cr,uid,ids,context=None):
        
        mod_obj = self.pool.get('ir.model.data')
        
        act_obj = self.pool.get('ir.actions.act_window')
        
        result = mod_obj.get_object_reference(cr, uid, 'account', 'action_invoice_tree1')
        
        id = result and result[1] or False
        
        result = act_obj.read(cr, uid, [id], context=context)[0]
        
        res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_form')
        
        result['views'] = [(res and res[1] or False, 'form')]
        
        val = self.browse(cr, uid, ids)
        
        obj_inv = self.pool.get('account.invoice')
        
        obj = obj_inv.search(cr,uid,[
                                     ('origin','=',val.name),
                                     ('tipe','=','finco')
                                     ])
        
        result['res_id'] = obj[0]   
        return result
    
    def action_view_do(self,cr,uid,ids,context=None):  
        val = self.browse(cr, uid, ids)
        obj_picking = self.pool.get('stock.picking')
          
        picking_id = obj_picking.search(cr,uid,[
                                     ('origin','=',val.name)
                                     ])
        
        return {
            'name': 'Picking Slip',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': picking_id[0]
            }
        
    def unlink(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids, context={})[0]
        if val.state == 'draft':
            raise osv.except_osv(('Perhatian !'), ("Sale Order Tidak Bisa Di Hapus. Gunakan Tombol Unused."))
        if val.state != 'draft':
            raise osv.except_osv(('Invalid action !'), ('Cannot delete a Sale Order which is in state \'%s\'!') % (val.state,))
        if val.dealer_spk_id:
            self.pool.get('dealer.spk').write(cr,uid,val.dealer_spk_id.id,{'state':'progress','dealer_sale_order_id':False})
        if val.dealer_sale_order_line:
            for line in val.dealer_sale_order_line:
                update_lot = self.update_serial_number(cr,uid,{'state': 'stock','sale_order_reserved':False,'customer_reserved':False},line.lot_id.id)
        return super(dealer_sale_order, self).unlink(cr, uid, ids, context=context)
    
    
    def write(self,cr,uid,ids,vals,context=None):
        #vals.get('dealer_sale_order_line',False):
        line_obj = self.pool.get('dealer.sale.order.line')
        if vals.get('partner_id',False):
            line_ids = line_obj.search(cr,uid,[('dealer_sale_order_line_id','=',ids[0])])
            for detail in line_obj.browse(cr,uid,line_ids):
                update_lot = self.update_serial_number(cr,uid,{'customer_reserved':vals['partner_id']},detail.lot_id.id)
        
        if vals.get('partner_komisi_id')==False:
            if self.browse(cr,uid,ids).dealer_sale_order_line:
                line_ids = line_obj.search(cr,uid,[('dealer_sale_order_line_id','=',ids[0])])
                update_hc = self.pool.get('dealer.sale.order.line').write(cr,uid,line_ids,{'hutang_komisi_id':False,'hutang_komisi_amount':0.0,'amount_hutang_komisi':0.0,'tipe_komisi':False})
            
            
        
        if vals.get('dealer_sale_order_line',False):
            header = self.read(cr,uid,ids,['partner_id'])
            #update_approval = self._get_approval_diskon(cr, uid, vals['dealer_sale_order_line'])
            for line in vals['dealer_sale_order_line']:
                if line[1] == False:
                    if line[2]['lot_id']:                    
                        update_lot = self.update_serial_number(cr,uid,{'state':'reserved','sale_order_reserved':ids[0],'customer_reserved':header[0]['partner_id'][0]},line[2]['lot_id'])
        return super(dealer_sale_order, self).write(cr, uid, ids, vals, context=context)
    
    def _get_branch_setting(self,cr,uid,branch_id,context=None):
        branch = self.pool.get('wtc.branch')
        branch_obj = branch.browse(cr,uid,branch_id)
        return branch_obj
    
    def transferred(self, cr, uid, ids, *args):
        val = self.browse(cr, uid, ids)
        obj_picking = self.pool.get('stock.picking')
          
        picking_id = obj_picking.search(cr,uid,[
                                     ('origin','=',val.name)
                                     ])
       
        status_picking = obj_picking.read(cr,uid,picking_id,['state'])
        if status_picking[0]['state'][0]=='done':
            return True
         
        return False
    
    def paid(self, cr, uid, ids, *args):
        val = self.browse(cr, uid, ids)
        obj_inv = self.pool.get('account.invoice')
        
        if val.finco_id:
            inv_id = obj_inv.search(cr,uid,[
                                         ('origin','=',val.name),
                                         ('partner_id','=',val.finco_id.id),
                                         ('tipe','=','finco')
                                         ])
        else:
            inv_id = obj_inv.search(cr,uid,[
                                         ('origin','=',val.name),
                                         ('partner_id','=',val.partner_id.id),
                                         ('tipe','=','customer')
                                         ])
        inv_status = obj_inv.read(cr,uid,inv_id,['state'])
        if inv_status[0]['state'][0]=='paid':
            return True
         
        return False
    
    def _get_invoice_ids(self, cr, uid, ids, context=None):
        dso_id = self.browse(cr, uid, ids, context=context)
        obj_inv = self.pool.get('account.invoice')
        obj_model = self.pool.get('ir.model')
        id_model = obj_model.search(cr, uid, [('model','=','dealer.sale.order')])[0]
        ids_inv = obj_inv.search(cr, uid, [
            ('model_id','=',id_model),
            ('transaction_id','=',dso_id.id),
            ('state','!=','cancel')
            ])
        inv_ids = obj_inv.browse(cr, uid, ids_inv)
        return inv_ids
    
    def _get_ids_picking(self, cr, uid, ids, context=None):
        dso_id = self.browse(cr, uid, ids, context=context)
        obj_picking = self.pool.get('stock.picking')
        obj_model = self.pool.get('ir.model')
        id_model = obj_model.search(cr, uid, [('model','=','dealer.sale.order')])[0]
        ids_picking = obj_picking.search(cr, uid, [
            ('model_id','=',id_model),
            ('transaction_id','=',dso_id.id),
            ('state','!=','cancel')
            ])
        return ids_picking
    
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
    
    def action_paid(self, cr, uid, ids, *args):
        sale_order = self.browse(cr,uid,ids)
        if not sale_order.is_cod and not sale_order.is_cancelled :
            self.signal_workflow(cr, uid, ids, 'has_been_paid')
        
        for line in sale_order.dealer_sale_order_line:
            if line.is_bbn == 'Y':
                update_lot = self.update_serial_number(cr,uid,{'state':'paid'},line.lot_id.id)
            else:
                update_lot = self.update_serial_number(cr,uid,{'state':'paid_offtr'},line.lot_id.id)
        return True
    
    def dp_paid(self, cr, uid, ids, *args):
        val = self.browse(cr, uid, ids)
        obj_inv = self.pool.get('account.invoice')
        
        if val.finco_id:
            inv_id = obj_inv.search(cr,uid,[
                                         ('origin','=',val.name),
                                         ('partner_id','=',val.partner_id.id),
                                         ('tipe','=','customer')
                                         ])
      
        inv_status = obj_inv.read(cr,uid,inv_id,['state'])
        if inv_status[0]['state'][0]=='paid':
            return True
         
        return False
    
    def credit(self,cr,uid,ids,*args):
        for order in self.browse(cr,uid,ids):
            if order.finco_id:
                return True
            
        return False
    
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
    
    def wkf_dealer_sale_order_done(self,cr,uid,ids):
        sale_order = self.browse(cr,uid,ids)
        if sale_order.dealer_spk_id:
            self.pool.get('dealer.spk').write(cr,uid,sale_order.dealer_spk_id.id,{'state':'done'})
        self.write(cr, uid, ids, {'state': 'done'})
        return True
    
    def partner_id_change(self,cr,uid,ids,partner_id,finco_id):
        value = {}
        if finco_id and partner_id:
            partner = self.pool.get('res.partner').browse(cr,uid,finco_id)
            if not partner.property_payment_term.id:
                return {'value':{'finco_id':False,'payment_term':False,'payment_term_dummy':False},'warning':{'title':'Perhatian !','message':'Tidak ditemukan default payment term finco !'}}
            else:
                value = {'payment_term':partner.property_payment_term.id,'payment_term_dummy':partner.property_payment_term.id}
                return {'value':value}
                  
        elif partner_id:
            partner = self.pool.get('res.partner').browse(cr,uid,partner_id) 
            if not partner.property_payment_term.id:
                return {'value':{'partner_id':False,'payment_term':False,'payment_term_dummy':False},'warning':{'title':'Perhatian !','message':'Tidak ditemukan default payment term customer !'}}
            else:
                value = {'payment_term':partner.property_payment_term.id,'payment_term_dummy':partner.property_payment_term.id}  
                return {'value':value}
    
    def cod(self,cr,uid,ids):
        for sale_order in self.browse(cr,uid,ids):
            total_hl = 0
            for hl in sale_order.hutang_lain_line:
                total_hl+=hl.amount_hl_allocation
            
            if sale_order.finco_id:
                if sale_order.is_cod:
                    if round(sale_order.customer_dp,2)==round(total_hl,2):
                        for line in sale_order.dealer_sale_order_line:
                            if line.is_bbn=='Y':
                                self.update_serial_number(cr, uid, {'state':'paid'}, line.lot_id.id)
                            else:
                                self.update_serial_number(cr, uid, {'state':'paid_offtr'}, line.lot_id.id)
                    else:
                        for line in sale_order.dealer_sale_order_line:
                            if line.is_bbn=='Y':
                                self.update_serial_number(cr, uid, {'state':'sold'}, line.lot_id.id)
                            else:
                                self.update_serial_number(cr, uid, {'state':'sold_offtr'}, line.lot_id.id)
                    return True
                else:
                    if round(sale_order.customer_dp,2)==round(total_hl,2):
                        for line in sale_order.dealer_sale_order_line:
                            if line.is_bbn=='Y':
                                self.update_serial_number(cr, uid, {'state':'paid'}, line.lot_id.id)
                            else:
                                self.update_serial_number(cr, uid, {'state':'paid_offtr'}, line.lot_id.id)
                        return True
                                
                    else:
                        for line in sale_order.dealer_sale_order_line:
                            if line.is_bbn=='Y':
                                self.update_serial_number(cr, uid, {'state':'sold'}, line.lot_id.id)
                            else:
                                self.update_serial_number(cr, uid, {'state':'sold_offtr'}, line.lot_id.id)
                    
            else:
                if sale_order.is_cod:
                    if round(sale_order.amount_total,2)==round(total_hl,2):
                        for line in sale_order.dealer_sale_order_line:
                            if line.is_bbn=='Y':
                                    self.update_serial_number(cr, uid, {'state':'paid'}, line.lot_id.id)
                            else:
                                    self.update_serial_number(cr, uid, {'state':'paid_offtr'}, line.lot_id.id)
                    else:
                        for line in sale_order.dealer_sale_order_line:
                            if line.is_bbn=='Y':
                                self.update_serial_number(cr, uid, {'state':'sold'}, line.lot_id.id)
                            else:
                                self.update_serial_number(cr, uid, {'state':'sold_offtr'}, line.lot_id.id)
                    return True
                else:
                    if round(sale_order.amount_total,2)==round(total_hl,2):
                        for line in sale_order.dealer_sale_order_line:
                            if line.is_bbn=='Y':
                                    self.update_serial_number(cr, uid, {'state':'paid'}, line.lot_id.id)
                            else:
                                    self.update_serial_number(cr, uid, {'state':'paid_offtr'}, line.lot_id.id)
                        return True
                    else:
                        for line in sale_order.dealer_sale_order_line:
                            if line.is_bbn=='Y':
                                self.update_serial_number(cr, uid, {'state':'sold'}, line.lot_id.id)
                            else:
                                self.update_serial_number(cr, uid, {'state':'sold_offtr'}, line.lot_id.id)
                    
        return False
    
    def branch_change(self,cr,uid,ids,branch_id):
        domain = {}
        value = {'user_id':False,'sales_koordinator_id':False}
        if branch_id:
            sales = ('salesman', 'sales_counter', 'sales_partner','sales_koordinator','soh')
            sco = 'sales_koordinator'
            query_sales = """
                select r.user_id
                from resource_resource r
                inner join hr_employee e on r.id = e.resource_id
                inner join hr_job j on e.job_id = j.id 
                where e.branch_id = %d
                and j.sales_force in %s
                """ % (branch_id, str(sales))
            cr.execute(query_sales)
            ress1 = cr.fetchall()
            if len(ress1) > 0 :
                ids_user = [res[0] for res in ress1]
                domain['user_id'] = [('id','in',ids_user)]
#             query_sco = """
#                 select r.user_id
#                 from resource_resource r
#                 inner join hr_employee e on r.id = e.resource_id
#                 inner join hr_job j on e.job_id = j.id 
#                 where e.branch_id = %d
#                 and j.sales_force= '%s'
#                 """ % (branch_id,sco)
#             cr.execute(query_sco)
#             ress2 = cr.fetchall()
#             if len(ress2) > 0 :
#                 ids_sco = [res[0] for res in ress2]
#                 domain['sales_koordinator_id'] = [('id','in',ids_sco)]
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
            
            branch = self.pool.get('wtc.branch').browse(cr,uid,branch_id)
            if branch.is_mandatory_spk:
                return {'value':{'branch_id':False},'warning':{'title':'Perhatian','message':'Tidak boleh create so langsung, harus dari spk!'}}

        return {'value':value, 'domain':domain}
    
    def wkf_action_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'cancelled', 'cancelled_uid':uid, 'cancelled_date':datetime.now()}, context=context)
        dso_ids = self.browse(cr, uid, ids, context=context)
        lot_ids = []
        for line in dso_ids.dealer_sale_order_line :
            lot_ids.append(line.lot_id.id)
            self.pool.get('stock.production.lot').write(cr, uid, lot_ids, {
                'dealer_sale_order_id': False,
                'invoice_date': False,
                'customer_id': False,
                'customer_stnk': False,
                'dp': False,
                'tenor': False,
                'cicilan': False,
                'jenis_penjualan': False,
                'finco_id': False,
                'state': 'stock',
                'biro_jasa_id': False,
                'invoice_bbn': False,
                'total_jasa': False,
                'cddb_id': False,
                'customer_reserved': False,
                'sale_order_reserved': False,
                })
    
    def is_so_done(self, cr, uid, ids, context=None):
        inv_done = False
        dso_id = self.browse(cr, uid, ids, context=context)
        reverse = self.reverse(cr, uid, ids, context)
        picking_done = self.test_moves_done(cr, uid, ids, context)
        inv_ids = self._get_invoice_ids(cr, uid, ids, context)
        for inv in inv_ids :
            if inv.tipe in ('customer','finco') and inv.state == 'paid' :
                inv_done = True
        if inv_done and not dso_id.is_cancelled and picking_done and not reverse :
            return self.signal_workflow(cr, uid, ids, 'action_done')
        return True
    
    def check_done(self,cr,uid,ids,context=None):
        dso=self.browse(cr,uid,ids)
        if dso.state=='done':
            return False
        inv_done = False
        picking_done = self.test_moves_done(cr, uid, dso.id, context)
        reverse = self.reverse(cr, uid, dso.id, context)
        inv_ids = self._get_invoice_ids(cr, uid, dso.id, context)
        for inv in inv_ids :
            if inv.tipe in ('customer','finco') and inv.state == 'paid' :
                inv_done = True
        if inv_done and not dso.is_cancelled and picking_done and not reverse :
            self.write(cr,uid,ids,{'state':'done'})
        return True

    
class dealer_sale_order_line(osv.osv):
    _name = 'dealer.sale.order.line'
    
    def _get_default_date(self,cr,uid,ids,context=None):
        return self.pool.get('wtc.branch').get_default_date(cr,uid,ids,context=context)
        
    def discount_line_change(self, cr, uid, ids, discount_line):
        pass

    def _umur_stock(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        umr = self.browse(cr, uid, ids)
        for x in umr:
            res[x] = []
            query = """
            SELECT AGE(CURRENT_DATE, in_date) as umur_stock from stock_quant 
                WHERE  lot_id = %s   
            """ % (x.lot_id.id)
           
            cr.execute(query)
            picks = cr.fetchall()
            res[x.id]=str(picks[0][0])
              
        return res

    def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
        tax_obj = self.pool.get('account.tax')
        #cur_obj = self.pool.get('res.currency')
        res = {}
        disc_total = 0
        if context is None:
            context = {}
        for line in self.browse(cr, uid, ids, context=context):
            for detail in line.discount_line:
                disc_total += detail.discount_pelanggan
            price = line.price_unit - (disc_total+line.discount_po)
            taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, line.product_qty, line.product_id)
            #cur = line.work_order_id.pricelist_id.currency_id
            res[line.id]=taxes['total']
        return res
    
    def _amount_total_discount(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for discount in self.browse(cr, uid, ids, context=context):
            res[discount.id] = {
                'discount_total': 0.0,
            }
            val = discount.discount_po
            for line in discount.discount_line:
                val += line.discount_pelanggan
            res[discount.id]['discount_total'] = val
           
        return res
    
    def product_id_change(self, cr, uid, ids, product_id, branch_id):
        if branch_id:
            branch = self.pool.get('wtc.branch').browse(cr,uid,branch_id)
        else:
            raise osv.except_osv(('Perhatian !'), ("Pilih Cabang Terlebih Dahulu"))
        result = {}
        domain  = {}

        if not product_id:
            return {'value':{'price_unit':0,'price_unit_beli':0,'accrue_ekspedisi':0,'accrue_proses_bbn':0,'discount_line':False,'barang_bonus_line':False}}
        if not branch.pricelist_unit_sales_id and branch.pricelist_unit_purchase_id.id:
            return {'value':{'product_id':False,'price_unit':0,'price_unit_beli':0,'accrue_ekspedisi':0,'accrue_proses_bbn':0,'discount_line':False,'barang_bonus_line':False},'warning':{'title':'Perhatian !','message':'Data Pricelist tidak ditemukan, silahkan konfigurasi data cabang dulu.'}}
            
        obj_product = self.pool.get('product.product').browse(cr, uid, product_id)
        taxes = obj_product.taxes_id or obj_product.product_tmpl_id.taxes_id
        pricelist = branch.pricelist_unit_sales_id.id
        
        price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist], product_id, 1,0)[pricelist]
        
        
        if price is False:
            return {'value':{'product_id':False,'price_unit':0,'accrue_ekspedisi':0,'accrue_proses_bbn':0,'discount_line':False,'barang_bonus_line':False},'warning':{'title':'Perhatian !','message':'Data Pricelist tidak ditemukan untuk produk "%s", silahkan konfigurasi data cabang dulu.' % (obj_product.name)}}
        else:
            result.update({'price_unit':price,'accrue_ekspedisi':branch.accrue_ekspedisi,'accrue_proses_bbn':branch.accrue_proses_bbn,'tax_id':taxes,'discount_line':False,'barang_bonus_line':False})
            domain = {
                'location_id': "[('id','in',"+str(obj_product.get_location_ids())+"),"+"('branch_id','=',"+str(branch_id)+"),('usage','=','internal')]"
            }
        
        return { 'value' : result ,'domain': domain}

    def partner_stnk_id_change(self, cr, uid, ids, partner_stnk_id):
        if not partner_stnk_id:
            return {'value':{'city_id':False}}
        partner_stnk_id = self.pool.get('res.partner').browse(cr,uid,partner_stnk_id)
        if partner_stnk_id:
            if partner_stnk_id.sama == True:
                return {'value':{'city_id':partner_stnk_id.city_id}}
            else:
                return {'value':{'city_id':partner_stnk_id.city_tab_id}}
        return {'value':{'city_id':False}}
    
    def biro_jasa_id_change(self, cr, uid, ids, product_id, branch_id, plat, biro_jasa_id, city_id):
        if branch_id:
            branch = self.pool.get('wtc.branch').browse(cr,uid,branch_id)
            
        else:
            return {'value':{'biro_jasa_id':False,'price_bbn':0,'price_bbn_beli':0,'price_bbn_notice':0,'price_bbn_proses':0,'price_bbn_jasa':0,'price_bbn_jasa_area':0,'price_bbn_fee_pusat':0},'warning':{'title':'Perhatian !','message':'Pilih Cabang Terlebih Dahulu.'}}
        result = {}

        if not biro_jasa_id:
            return {'value':{'biro_jasa_id':False,'price_bbn':0,'price_bbn_beli':0,'price_bbn_notice':0,'price_bbn_proses':0,'price_bbn_jasa':0,'price_bbn_jasa_area':0,'price_bbn_fee_pusat':0}}

        if not city_id:
            return {'value':{'biro_jasa_id':False,'price_bbn':0,'price_bbn_beli':0,'price_bbn_notice':0,'price_bbn_proses':0,'price_bbn_jasa':0,'price_bbn_jasa_area':0,'price_bbn_fee_pusat':0},'warning':{'title':'Perhatian !','message':'Kabupaten / City dari A/N STNK belum diisi.'}}
        
        if not product_id:            
            return {'value':{'biro_jasa_id':False,'price_bbn':0,'price_bbn_beli':0,'price_bbn_notice':0,'price_bbn_proses':0,'price_bbn_jasa':0,'price_bbn_jasa_area':0,'price_bbn_fee_pusat':0}}
        
        if not plat:
            return {'value':{'biro_jasa_id':False,'price_bbn':0,'price_bbn_beli':0,'price_bbn_notice':0,'price_bbn_proses':0,'price_bbn_jasa':0,'price_bbn_jasa_area':0,'price_bbn_fee_pusat':0},'warning':{'title':'Perhatian !','message':'Pilih warna plat terlebih dahulu.'}}

        elif plat=='H':
            if not branch.pricelist_bbn_hitam_id:
                return {'value':{'biro_jasa_id':False,'price_bbn':0,'price_bbn_beli':0,'price_bbn_notice':0,'price_bbn_proses':0,'price_bbn_jasa':0,'price_bbn_jasa_area':0,'price_bbn_fee_pusat':0},'warning':{'title':'Perhatian !','message':'Data Pricelist tidak ditemukan, silahkan konfigurasi data cabang dulu.'}}
            else :
                pricelist = branch.pricelist_bbn_hitam_id.id
        else:
            if not branch.pricelist_bbn_merah_id:
                return {'value':{'biro_jasa_id':False,'price_bbn':0,'price_bbn_beli':0,'price_bbn_notice':0,'price_bbn_proses':0,'price_bbn_jasa':0,'price_bbn_jasa_area':0,'price_bbn_fee_pusat':0},'warning':{'title':'Perhatian !','message':'Data Pricelist tidak ditemukan, silahkan konfigurasi data cabang dulu.'}}
            else :
                pricelist = branch.pricelist_bbn_merah_id.id
        
        
        price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist], product_id, 1,0)[pricelist]
        if price is False:
            return {'value':{'biro_jasa_id':False,'price_bbn':0,'price_bbn_beli':0,'price_bbn_notice':0,'price_bbn_proses':0,'price_bbn_jasa':0,'price_bbn_jasa_area':0,'price_bbn_fee_pusat':0},'warning':{'title':'Perhatian !','message':'Data Pricelist BBN tidak ditemukan untuk produk ini, silahkan konfigurasi data cabang dulu.'}}
        else:
            result.update({'price_bbn': price})
        
        product_template_obj = self.pool.get('product.product').browse(cr,uid,product_id)
        product_template_id = product_template_obj.product_tmpl_id.id
        
        harga_beli = self.pool.get('dealer.spk')._get_harga_bbn_detail(cr, uid, ids, biro_jasa_id, plat, city_id, product_template_id,branch_id)
        if harga_beli:
            result.update({
                            'price_bbn_beli': harga_beli.total,
                            'price_bbn_notice': harga_beli.notice,
                            'price_bbn_proses': harga_beli.proses,
                            'price_bbn_jasa': harga_beli.jasa,
                            'price_bbn_jasa_area': harga_beli.jasa_area,
                            'price_bbn_fee_pusat': harga_beli.fee_pusat,
                           })
        else:
            return {'value':{'biro_jasa_id':False,'price_bbn':0,'price_bbn_beli':0,'price_bbn_notice':0,'price_bbn_proses':0,'price_bbn_jasa':0,'price_bbn_jasa_area':0,'price_bbn_fee_pusat':0},'warning':{'title':'Perhatian !','message':'Data Pricelist Beli BBN tidak ditemukan, silahkan konfigurasi dulu.'}}
        
        return { 'value' : result}
    
    def lot_id_change(self, cr, uid, ids, lot_id):
        result = {}
        if not lot_id:
            return {'value':{'price_unit_beli':False}}
        lot_obj = self.pool.get('stock.production.lot').browse(cr,uid,lot_id)
        if lot_obj:
            result.update({'price_unit_beli': lot_obj.hpp})
        return {'value':result}
    
    def _get_discount(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('dealer.sale.order.line.discount.line').browse(cr, uid, ids, context=context):
            result[line.dealer_sale_order_line_discount_line_id.id] = True
        return result.keys()
    
    def _get_branch(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for dso in self.browse(cr, uid, ids):
            res[dso.id] = {
                'branch_dummy': 0,
                'finco_dummy': 0,
                'komisi_dummy': 0,
                
            }
            for sale_order in self.pool.get('dealer.sale.order').browse(cr,uid,dso.dealer_sale_order_line_id.id):
                res[dso.id]['branch_dummy'] = sale_order.branch_id.id
                res[dso.id]['finco_dummy'] = sale_order.finco_id.id
                res[dso.id]['komisi_dummy'] = sale_order.partner_komisi_id.id
                
        return res
    
    def category_change(self, cr, uid, ids, categ_id,branch_id, finco_id,komisi_id):
        dom = {}
        tampung = []
        if categ_id:
            categ_ids = self.pool.get('product.category').get_child_ids(cr,uid,ids,categ_id)
            dom['product_id']=[('categ_id','in',categ_ids),('sale_ok','=',True)]
        return {'value':{'branch_dummy':branch_id,'finco_dummy':finco_id,'komisi_dummy': komisi_id},'domain':dom}
    
    def location_change(self, cr, uid, ids, location_id,product_id):
        obj_product_location = self.pool.get('product.product').browse(cr, uid, product_id)      
        dom = {}
        
        obj_stock2 = self.pool.get('stock.quant').search(cr, uid, [('location_id','=',location_id),('product_id','=',product_id),('reservation_id','=',False),('consolidated_date','!=',False)])
        if obj_stock2:
            lots = self.pool.get('stock.quant').read(cr, uid,obj_stock2,['lot_id'])
            if lots:
                dom['lot_id']=[('id','in',[x['lot_id'][0] for x in lots]),('state','=','stock')]
            else:
                return {'value':{'product_id':False,'location_id':False,'price_unit':0},'warning':{'title':'Perhatian !','message':'Stock tidak ditemukan'}}
        else :
            dom['lot_id']=[('id','in',[]),('state','=','stock')] 

        return  {'domain': dom}
    
    def onchange_price(self,cr,uid,ids,price_unit):
        value = {'price_unit_show':0}
        if price_unit:
            value.update({'price_unit_show':price_unit})       
        return {'value':value}

    def _get_price_unit(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for price in self.read(cr, uid, ids, ['price_unit']):
            price_unit_show = price['price_unit']
            res[price['id']] = price_unit_show
        return res
    
    def onchange_price_bbn(self,cr,uid,ids,price_bbn):
        value = {'price_bbn_show':0}
        if price_bbn:
            value.update({'price_bbn_show':price_bbn})       
        return {'value':value}
    
    def onchange_hutang_komisi(self,cr,uid,ids,product_id,hutang_komisi,partner_komisi_id):
        result = {'hutang_komisi_id':False,'hutang_komisi_amount': 0}
        date = self._get_default_date(cr, uid, ids).strftime('%Y-%m-%d')
         
        if not hutang_komisi:
            return {'value':{'hutang_komisi_id':False,'hutang_komisi_amount': 0,'amount_hutang_komisi': 0}}
        
        if not product_id:
#             return result
            return {'value':{'hutang_komisi_id':False,'hutang_komisi_amount': 0,'amount_hutang_komisi': 0,},
                    'warning':{'title':'Perhatian !','message':'Pilih produk terlebih dahulu'}}
        else:
            product_template_obj = self.pool.get('product.product').browse(cr,uid,product_id)
            product_template_id = product_template_obj.product_tmpl_id.id
        
        if not partner_komisi_id:
            return {'value':{'hutang_komisi_id':False,'hutang_komisi_amount': 0,'amount_hutang_komisi': 0,},
                    'warning':{'title':'Perhatian !','message':'Hutang Komisi jika partner komisi terisi'}}
        
        hc = self.pool.get('wtc.hutang.komisi').browse(cr, uid, hutang_komisi)

        if hc.date_start > date or hc.date_end < date:# or not ps.active:
            return {'value':{'hutang_komisi_id':False,'hutang_komisi_amount': 0,'amount_hutang_komisi': 0,},
                    'warning':{'title':'Perhatian !','message':'Hutang komisi sudah tidak aktif.'}}
            
        if not hc.hutang_komisi_line:
            return {'value':{'hutang_komisi_id':False,'hutang_komisi_amount': 0,'amount_hutang_komisi': 0},
                    'warning':{'title':'Perhatian !','message':'Detail hutang komisi tidak ditemukan.'}}
        
        hc_line_id = hc.hutang_komisi_line      
       
        hc_line_obj = self.pool.get('wtc.hutang.komisi.line').search(cr, uid,[('product_template_id','=',product_template_id),('hutang_komisi_id','=',hutang_komisi)])
        
        if not hc_line_obj:
            return {'value':{'hutang_komisi_id':False,'hutang_komisi_amount': 0,'amount_hutang_komisi': 0},
                    'warning':{'title':'Perhatian !','message':'Detail hutang komisi tidak ditemukan.'}}
        else:
            hc_obj = self.pool.get('wtc.hutang.komisi.line').browse(cr, uid,hc_line_obj)
            
            result.update({
                           'hutang_komisi_id': hutang_komisi,
                           'tipe_komisi': hc.tipe_komisi,
                           'hutang_komisi_amount': hc_obj.amount,
                           'amount_hutang_komisi': hc_obj.amount,
                           })
        return {'value':result}
    
    def onchange_amount_hc(self,cr,uid,ids,product_id,hutang_komisi,tipe_komisi,amount_hutang_komisi,partner_komisi_id,hutang_komisi_amount):
        if not hutang_komisi and not product_id:
            return {'value':{'hutang_komisi_id':False,'amount_hutang_komisi': 0}}
        if tipe_komisi == 'fix':
            return {'value':{'amount_hutang_komisi':hutang_komisi_amount}}
        elif tipe_komisi=='non':
            if amount_hutang_komisi < 0 or amount_hutang_komisi > hutang_komisi_amount:
                return {'value':{'amount_hutang_komisi':hutang_komisi_amount},'warning':{'title':'Perhatian !','message':'Amount Hutang Komisi Tidak Boleh nilai negatif atau lebih dari master hutang komisi.'}}

        return True
        

    def _get_price_bbn(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for price in self.read(cr, uid, ids, ['price_bbn']):
            price_bbn_show = price['price_bbn']
            res[price['id']] = price_bbn_show
        return res
    
    def _get_order_line(self, cr, uid, ids, context=None):
        result = {}
        for line in self.browse(cr, uid, ids, context=context):
            result[line.id] = True
        return result.keys()

    def _get_harga_bbn_detail(self, cr, uid, ids, birojasa_id, plat, city_id, product_template_id):
        if not birojasa_id:
            return False

        pricelist_harga_bbn = self.pool.get('wtc.harga.bbn.line').search(cr,uid,[
                ('partner_id','=',birojasa_id),
                ('tipe_plat','=',plat),
                ('active','=',True),
                ('start_date','<=',self._get_default_date(cr, uid, ids, context=None)),
                ('end_date','>=',self._get_default_date(cr, uid, ids, context=None)),
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

        return False
   
    def _get_insentif_finco_value(self, cr, uid, ids, finco_id, branch_id):
        if not finco_id or not branch_id:
            return (0, True)
        pricelist_incentives = self.pool.get('wtc.incentive.finco.line').search(cr,uid,[
                ('partner_id','=',finco_id),
                ('active','=',True),
                ('start_date','<=',self._get_default_date(cr, uid, ids, context=None)),
                ('end_date','>=',self._get_default_date(cr, uid, ids, context=None)),
            ])
        if not pricelist_incentives:
            raise osv.except_osv(('Perhatian !'), ("Master insentif finco belum di set atau sudah expired!"))

        incentive_value = self.pool.get('wtc.incentive.finco.line.detail').search(cr, uid,[
                ('incentive_finco_line_id','=',pricelist_incentives[0]),
                ('branch_id','=',branch_id),
            ])
        
        if incentive_value:
            incentive = self.pool.get('wtc.incentive.finco.line.detail').browse(cr,uid,incentive_value[0])
            return (incentive['incentive'], incentive.incentive_finco_line_id.is_include_ppn)
        else:
            raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan insentif cabang dalam master insentif finco!"))
        return (0, True)
    
    
    _columns = {
                    'dealer_sale_order_line_id': fields.many2one('dealer.sale.order','Sales Order Line',ondelete='cascade'),
                    'categ_id':fields.selection([('Unit','Unit')],'Category',required=True),
                    'product_id': fields.many2one('product.product','Produk',required=True,domain="[('sale_ok','=',True)]"),
                    'product_desc': fields.related('product_id','description',relation='product.product',type='text',store=False,readonly=True,string='Product Desc'),
                    'price_unit': fields.float(required=True,string='Unit Price'),
                    'price_unit_beli': fields.float(string='Unit Price Beli'),
                    'price_unit_show': fields.function(_get_price_unit,string='Unit Price'),
                    'product_qty': fields.integer('Qty',required=True),
                    'location_id': fields.many2one('stock.location','Location',domain=[('location_id','=','dealer.sale.order.branch_id')],required=True),
                    'lot_id': fields.many2one('stock.production.lot','No. Engine',required=True),
                    'chassis_no': fields.related('lot_id','chassis_no',relation='stock.production.lot',type='char',store=False,readonly=True,string='No. Chassis'),
                    'is_bbn': fields.selection([('Y','Y'),('T','T')],'BBN',required=True),
                    'plat': fields.selection([('H','H'),('M','M')],'Plat'),
                    'partner_stnk_id': fields.many2one('res.partner','STNK',domain=[('customer','=',True)]),
                    'city_id': fields.many2one('wtc.city','City'),
                    #'partner_stnk_line': fields.one2many('res.partner.cdb','partner_stnk_line_id'),
                    'biro_jasa_id': fields.many2one('res.partner','Biro Jasa',domain=[('biro_jasa','=',True)]),
                    'price_bbn': fields.float('Price BBN',),
                    'price_bbn_show': fields.function(_get_price_bbn,string='Price BBN'),
                    'tax_id': fields.many2many('account.tax', 'dealer_sale_order_tax', 'dealer_sale_order_line_id', 'tax_id', 'Taxes'),                    
                    'uang_muka': fields.float('Uang Muka'),
                    'discount_po':fields.float('Potongan Pelanggan'),
                    'discount_line': fields.one2many('dealer.sale.order.line.discount.line','dealer_sale_order_line_discount_line_id','Discount Line',),
                    'discount_total': fields.function(_amount_total_discount, string='Disc Total', digits_compute= dp.get_precision('Account'),
                                                      store={
                                                            'dealer.sale.order.line': (lambda self, cr, uid, ids, c={}: ids, ['price_unit','discount_line','discount_po'], 10),
                                                            'dealer.sale.order.line.discount.line': (_get_discount, ['discount'], 10),
                                                             },multi='sums', help="The total Discount."),
                    'price_subtotal': fields.function(_amount_line, string='Subtotal', digits_compute= dp.get_precision('Account'),
                                                      store = {
                                                               'dealer.sale.order.line': (lambda self, cr, uid, ids, c={}: ids, ['price_unit','discount_line','discount_po'], 10),
                                                               'dealer.sale.order.line.discount.line': (_get_discount, ['discount'], 10),
                                                               }
                                                      ),
                    'price_bbn_beli': fields.float(),
                    'price_bbn_notice': fields.float(),
                    'price_bbn_proses': fields.float(),
                    'price_bbn_jasa': fields.float(),
                    'price_bbn_jasa_area': fields.float(),
                    'price_bbn_fee_pusat': fields.float(), 
                    'insentif_finco': fields.float(),
                    'insentif_finco_tax': fields.boolean('Insentif Finco Tax'),
                    'finco_tgl_po': fields.date('Tanggal PO'),
                    'finco_no_po': fields.char('No. PO'),
                    'finco_tenor': fields.integer('Tenor'),
                    'barang_bonus_line': fields.one2many('dealer.sale.order.line.brgbonus.line','dealer_sale_order_line_brgbonus_line_id', 'Barang Bonus Line'),
                    'cicilan': fields.integer('Cicilan'),
                    'hutang_komisi_id':fields.many2one('wtc.hutang.komisi','Hutang Komisi'),
                    'hutang_komisi_amount':fields.float('Hutang Komisi Amount (from master data)'),
                    'amount_hutang_komisi': fields.float('Amount'),
                    'tipe_komisi':fields.char('Tipe Komisi'),
                    'branch_dummy': fields.function(_get_branch,type='integer',multi=True),
                    'finco_dummy': fields.function(_get_branch, type='integer',multi=True),
                    'komisi_dummy': fields.function(_get_branch, type='integer',multi=True),
                    'force_cogs': fields.float(),
                    'umur_stock': fields.function(_umur_stock, type='char',string='Umur'),
                    'accrue_ekspedisi': fields.float(),
                    'accrue_proses_bbn': fields.float(),
                }
    
    _defaults = {
                 'product_qty' : 1,
                 'is_bbn': 'Y',
                 'plat':'H',
                 'categ_id':'Unit',
                 'price_bbn_beli': 0,
                 'insentif_finco':0
                 }
    
    _sql_constraints = [('lot_id_unique', 'unique(dealer_sale_order_line_id,lot_id)', 'No Engine sudah pernah diinput!')]
    
    def unlink(self, cr, uid, ids, context=None):
        header_obj = self.pool.get('dealer.sale.order')
        for val in self.browse(cr, uid, ids, context={}):
            
            header = header_obj.browse(cr,uid,val.dealer_sale_order_line_id.id)
            for data in header:            
                if data.state != 'draft':
                    raise osv.except_osv(('Invalid action !'), ('Cannot delete a Sale Order Line which is in state \'%s\'!') % (data.state,))
            update_lot = header_obj.update_serial_number(cr,uid,{'state': 'stock','sale_order_reserved':False,'customer_reserved':False},val.lot_id.id)
        return super(dealer_sale_order_line, self).unlink(cr, uid, ids, context=context) 
    
    def write(self,cr,uid,ids,vals,context=None):
        header_obj = self.pool.get('dealer.sale.order')      
        sale_order_id = self.read(cr,uid,ids[0],['dealer_sale_order_line_id'])         
        header_id = sale_order_id['dealer_sale_order_line_id'][0]
        
        if vals.get('lot_id',False):    
            lot_lawas = self.read(cr,uid,ids[0],['lot_id'])
            lot_lawas_id =  lot_lawas['lot_id'][0]
            update_lot = header_obj.update_serial_number(cr,uid,{'state':'stock','sale_order_reserved':False,'customer_reserved':False},lot_lawas_id)
            for header in header_obj.browse(cr,uid,header_id):
                update_lot = header_obj.update_serial_number(cr,uid,{'state':'reserved','sale_order_reserved':header_id,'customer_reserved':header.partner_id.id},vals['lot_id'])
        
        if vals.get('is_bbn',False):   
            for header in header_obj.browse(cr,uid,header_id):
                if vals['is_bbn']=='T' and header.finco_id:
                    raise osv.except_osv(('Perhatian !'), ("Penjualan credit harus harus menggunakan biro jasa!"))
                
                elif vals['is_bbn']=='T' and not header.finco_id:
                    self.write(cr,uid,ids,{'partner_stnk_id':False,'plat':False,'biro_jasa_id':False,'price_bbn':0.0})
        
        
        return super(dealer_sale_order_line, self).write(cr, uid, ids, vals, context=context)
    
    def onchange_uang_muka(self,cr,uid,ids,uang_muka,finco_id):
        result = {}
        if uang_muka < 0:
            result = {'value':{'uang_muka':0},'warning':{'title':'Perhatian !','message':'Tidak boleh memasukkan nilai negatif!'}}
        if not finco_id and uang_muka > 0:
            result = {'value':{'uang_muka':0},'warning':{'title':'Perhatian !','message':'Uang Muka hanya diisi untuk penjualan kredit!'}}
        return result

    def onchange_is_bbn(self,cr,uid,ids,is_bbn,branch_id):
        result = {}
        birojasa = []
        birojasa_srch = self.pool.get('wtc.harga.birojasa').search(cr,uid,[
                                                                      ('branch_id','=',branch_id)
                                                                      ])
        if birojasa_srch :
            birojasa_brw = self.pool.get('wtc.harga.birojasa').browse(cr,uid,birojasa_srch)
            for x in birojasa_brw :
                birojasa.append(x.birojasa_id.id)
                        
        if not is_bbn:
            result = {'value':{'is_bbn':'Y'},'domain':{'biro_jasa_id':[('id','in',birojasa)]}}
        if is_bbn == 'T':
            result = {'value':{'plat':False,'partner_stnk_id':False,'biro_jasa_id':False},'domain':{'biro_jasa_id':[('id','in',birojasa)]}}
        elif is_bbn == 'Y':
            result = {'value':{'plat':'H'},'domain':{'biro_jasa_id':[('id','in',birojasa)]}}
        return result
    
    def onchange_discount_po(self,cr,uid,ids,discount_po):
        result = {}
        if discount_po < 0:
            result = {'value':{'discount_po':0},'warning':{'title':'Perhatian !','message':'Tidak boleh memasukkan nilai negatif!'}}
        return True
    """
    def create(self,cr,uid,vals,context=None):
        if vals.get('dealer_sale_order_line_id',False):            
            header_obj = self.pool.get('dealer.sale.order')
            for header in header_obj.browse(cr,uid,vals['dealer_sale_order_line_id']):                
                lot_update_reserve = header_obj.update_serial_number(cr,uid,{'state': 'reserved','sale_order_reserved':vals['dealer_sale_order_line_id'],'customer_reserved':header.partner_id.id},vals['lot_id'])
            
            dealer_sales_order_line = super(dealer_sale_order_line, self).create(cr, uid, vals, context=context)
        
        
        return dealer_sale_order_line
    """  
    
class dealer_sale_order_discount_line(osv.osv):
    _name = 'dealer.sale.order.line.discount.line'       

    _columns = {
                'dealer_sale_order_line_discount_line_id': fields.many2one('dealer.sale.order.line',ondelete='cascade'),
                'program_subsidi': fields.many2one('wtc.program.subsidi','Program Subsidi',required=True),
                'discount': fields.float('Total Subsidi',required=True),
                #'tipe_potongan': fields.selection([('um','UM'),('piu','PIU')],'Pot',required=True),
                'discount_pelanggan': fields.float('Discount',required=True),
                'tipe_subsidi': fields.char(),
                'ps_md':fields.float(),
                'ps_ahm':fields.float(),
                'ps_finco':fields.float(),
                'ps_dealer':fields.float(),
                'ps_others':fields.float(),
                }

    _default = {
                'ps_md':0,
                'ps_ahm':0,
                'ps_finco':0,
                'ps_dealer':0,
                'ps_others':0,
                'tipe_potongan':'piu',
                }
    
    def _get_default_date(self,cr,uid,ids,context=None):
        return self.pool.get('wtc.branch').get_default_date(cr,uid,ids,context=context)
    
    def program_subsidi_change(self, cr, uid, ids, product_id, program_subsidi,uang_muka,finco_dummy,branch_dummy):
        result = {}
        domain = {}
        date = self._get_default_date(cr, uid, ids).strftime('%Y-%m-%d')
        if not product_id:
            raise osv.except_osv(('Perhatian !'), ("Pilih Produk Terlebih Dahulu"))
        else:
            product_template_obj = self.pool.get('product.product').browse(cr,uid,product_id)
            
        if finco_dummy>0:
            
            domain = {'program_subsidi': "[('area_id.branch_ids','=',"+str(branch_dummy)+"),('date_end','>=','"+date+"'),('date_start','<=','"+date+"'),('state','=','approved'),('active','=',True),('instansi_id','=',"+str(finco_dummy)+")]"}
            #return {'domain':domain}
        else:
            domain = {'program_subsidi': "[('area_id.branch_ids','=',"+str(branch_dummy)+"),('date_end','>=','"+date+"'),('date_start','<=','"+date+"'),('state','=','approved'),('active','=',True),('instansi_id','=',False)]"}
            #return {'domain':domain}
        product_template_id = product_template_obj.product_tmpl_id.id
        if not program_subsidi:
            return {'domain':domain,'value':{'discount': 0,'tipe_potongan':False,'discount_pelanggan':0,'ps_ahm':0,'ps_md':0,'ps_finco':0,'ps_dealer':0,'ps_others':0},}
        
       
        
        ps = self.pool.get('wtc.program.subsidi').browse(cr, uid, program_subsidi)
            
        if not ps.program_subsidi_line:
            return {'value':{'discount': 0,'tipe_potongan':False,'discount_pelanggan':0,'ps_ahm':0,'ps_md':0,'ps_finco':0,'ps_dealer':0,'ps_others':0},
                    'warning':{'title':'Perhatian !','message':'Detail program subsidi tidak ditemukan.'}}
        
        ps_line_id = ps.program_subsidi_line      
       
        ps_line_obj = self.pool.get('wtc.program.subsidi.line').search(cr, uid,[('product_template_id','=',product_template_id),('program_subsidi_id','=',program_subsidi)])
        
        if not ps_line_obj:
            return {'value':{'discount': 0,'tipe_potongan':False,'discount_pelanggan':0,'ps_ahm':0,'ps_md':0,'ps_finco':0,'ps_dealer':0,'ps_others':0},
                    'warning':{'title':'Perhatian !','message':'Detail produk program subsidi tidak ditemukan.'}}
        else:
            dis_obj = self.pool.get('wtc.program.subsidi.line').browse(cr, uid,ps_line_obj)
            
            #Pengecekan DP berdasarkan tipe dp di Program subsidi
            if dis_obj.tipe_dp == 'min':
                if uang_muka < dis_obj.amount_dp:
                    return {'value':{'discount': 0,'tipe_potongan':False,'discount_pelanggan':0,'ps_ahm':0,'ps_md':0,'ps_finco':0,'ps_dealer':0,'ps_others':0},
                            'warning':{'title':'Perhatian !','message':'DP konsumen tidak memenuhi nilai minimum untuk mendapatkan PS.'}}
            
            elif dis_obj.tipe_dp == 'max':
                if uang_muka > dis_obj.amount_dp:
                    return {'value':{'discount': 0,'tipe_potongan':False,'discount_pelanggan':0,'ps_ahm':0,'ps_md':0,'ps_finco':0,'ps_dealer':0,'ps_others':0},
                            'warning':{'title':'Perhatian !','message':'DP konsumen melebihi nilai maksimum untuk mendapatkan PS.'}}
            
            

            result.update({'discount': dis_obj.total_diskon,
                           'discount_pelanggan': dis_obj.total_diskon,
                           'ps_ahm': dis_obj.diskon_ahm,
                           'ps_md': dis_obj.diskon_md,
                           'ps_finco':dis_obj.diskon_finco,
                           'ps_dealer':dis_obj.diskon_dealer,
                           'ps_others':dis_obj.diskon_others,
                           'tipe_subsidi':ps.tipe_subsidi,
                           'tipe_potongan':'piu'
                           })

        return {'domain':domain,'value':result}
    
    def onchange_discount_pelanggan(self,cr,uid,ids,program_subsidi,tipe_subsidi,discount,discount_pelanggan):
        result = {}
        if discount_pelanggan < 0:
            return {'value':{'discount_pelanggan':0},
                    'warning':{'title':'Perhatian !','message':'Tidak boleh memasukkan nilai negatif!'}}
        if tipe_subsidi=='fix':
            result.update({'discount_pelanggan':discount})  
        return {'value':result}

class dealer_sale_order_brgbonus_line(osv.osv):
    
    def _get_default_date(self,cr,uid,ids,context=None):
        return self.pool.get('wtc.branch').get_default_date(cr,uid,ids,context=context)
    
    _name = 'dealer.sale.order.line.brgbonus.line'       
    _columns = {
                'dealer_sale_order_line_brgbonus_line_id': fields.many2one('dealer.sale.order.line',ondelete='cascade'),
                'barang_subsidi_id': fields.many2one('wtc.subsidi.barang','Kode Barang Subsidi',required=True,domain="[('state','=','approved')]"),
                'product_subsidi_id': fields.many2one('product.product','Barang Subsidi',required=True),
                'barang_qty': fields.integer('Qty',required=True),
                'price_barang': fields.float('Harga',required=True),
                'bb_md':fields.float(),
                'bb_ahm':fields.float(),
                'bb_finco':fields.float(),
                'bb_dealer':fields.float(),
                'bb_others':fields.float(),
                'force_cogs':fields.float(),
                }
    _default = {
                'bb_md':0,
                'bb_ahm':0,
                'bb_finco':0,
                'bb_dealer':0,
                'bb_others':0,
                }

    def barang_bonus_change(self, cr, uid, ids, product_id, barang_subsidi):
        result = {}
        domain = {}
        date = self._get_default_date(cr, uid, ids).strftime('%Y-%m-%d')
        
        if not product_id:
            raise osv.except_osv(('Perhatian !'), ("Pilih Produk Terlebih Dahulu"))            
        else:
            product_template_obj = self.pool.get('product.product').browse(cr,uid,product_id)

        product_template_id = product_template_obj.product_tmpl_id.id

        if not barang_subsidi:
            return {'value':{'barang_subsidi_id':False,'price_barang': 0,'product_subsidi_id':False,'barang_qty':0,'bb_md':0,'bb_ahm':0,'bb_finco':0,'bb_dealer':0,'bb_others':0},}
        else:
            domain = {'barang_subsidi_id': "[('date_end','<=','"+date+"')]"} 

        ps = self.pool.get('wtc.subsidi.barang').browse(cr, uid, barang_subsidi)

        if ps.date_start > date or ps.date_end < date:# or not ps.active:
            return {'value':{'barang_subsidi_id':False,'price_barang': 0,'product_subsidi_id':False,'barang_qty':0,'bb_md':0,'bb_ahm':0,'bb_finco':0,'bb_dealer':0,'bb_others':0},
                    'warning':{'title':'Perhatian !','message':'Barang subsidi sudah tidak aktif.'}}
            
        if not ps.subsidi_barang_line:
            return {'value':{'barang_subsidi_id':False,'price_barang': 0,'product_subsidi_id':False,'barang_qty':0,'bb_md':0,'bb_ahm':0,'bb_finco':0,'bb_dealer':0,'bb_others':0},
                    'warning':{'title':'Perhatian !','message':'Detail barang subsidi tidak ditemukan.'}}
        
        ps_line_id = ps.subsidi_barang_line      
       
        ps_line_obj = self.pool.get('wtc.subsidi.barang.line').search(cr, uid,[('product_id','=',product_template_id),('subsidi_barang_id','=',barang_subsidi)])
        
        if not ps_line_obj:
            return {'value':{'barang_subsidi_id':False,'price_barang': 0,'product_subsidi_id':False,'barang_qty':0,'bb_md':0,'bb_ahm':0,'bb_finco':0,'bb_dealer':0,'bb_others':0},
                    'warning':{'title':'Perhatian !','message':'Detail produk barang subsidi tidak ditemukan.'}}
        else:
            dis_obj = self.pool.get('wtc.subsidi.barang.line').browse(cr, uid,ps_line_obj)
            result.update({'product_subsidi_id':  ps.product_template_id.id,
                            'barang_qty': dis_obj.qty,
                            'price_barang': dis_obj.total_diskon,
                            'bb_md':dis_obj.diskon_md,
                            'bb_ahm':dis_obj.diskon_ahm,
                            'bb_finco':dis_obj.diskon_finco,
                            'bb_dealer':dis_obj.diskon_dealer,
                            'bb_others':dis_obj.diskon_others,
                           })
            domain = {'product_subsidi_id': "[('id','=',"+str(ps.product_template_id.id)+")]"}
       
        return {'value':result,'domain':domain}
    
class dealer_sale_order_hutang_lain_line(osv.osv):
    _name = 'dso.hutang.lain.line'
    
    def _get_amount_hl(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        
        for hl in self.browse(cr, uid, ids):
            res[hl.id] = {
                'amount_hl_original_show': 0.0,
                'amount_hl_balance_show': 0.0,
            }
            res[hl.id]['amount_hl_original_show'] = hl.amount_hl_original
            res[hl.id]['amount_hl_balance_show'] = hl.amount_hl_balance

        return res
    
    _columns = {
        'dealer_sale_order_id': fields.many2one('dealer.sale.order',
            ondelete='set null', select=True,
            readonly=True),
                
        'hl_id': fields.many2one('account.move.line','Hutang Lain'),
        'amount_hl_original': fields.float('HL Original'),
        'amount_hl_balance': fields.float('HL Balance'),
        'amount_hl_allocation': fields.float('Allocation'),
        'amount_hl_original_show':fields.function(_get_amount_hl,multi='sums',string='Opening Balance',digits_compute=dp.get_precision('Account')),
        'amount_hl_balance_show':fields.function(_get_amount_hl,multi='sums',string='Amount Balance',digits_compute=dp.get_precision('Account'))
    }
    
    def onchange_hl(self,cr,uid,ids,hl_id):
        result = {}
        if hl_id:
            aml = self.pool.get('account.move.line').browse(cr,uid,hl_id)
            result.update({'amount_hl_original':abs(aml.credit),
                           'amount_hl_original_show':abs(aml.credit),
                           'amount_hl_balance':abs(aml.amount_residual_currency),
                           'amount_hl_balance_show':abs(aml.amount_residual_currency)
                           })
        return {'value':result} 
    
    def onchange_amount_hl(self,cr,uid,ids,amount_hl_allocation,amount_hl_balance):
        result = {}
        warning={}
        if amount_hl_allocation:
            if amount_hl_allocation>amount_hl_balance:
                 warning = {
                        'title': ('Perhatian !'),
                        'message': ("Nilai allocation tidak boleh lebih dari open balance !"),
                    }
                 result.update({'amount_hl_allocation': False})
            elif amount_hl_allocation<=0:
                warning = {
                'title': 'Perhatian !',
                'message': 'Nilai allocation tidak boleh negatif!',
            }
                result.update({'amount_hl_allocation': False})
        return {'value':result,'warning':warning} 

class stock_move(osv.osv):
    _inherit = 'stock.move'
    _columns = {
        'dealer_sale_order_line_id': fields.many2one('dealer.sale.order.line',
            'Dealer Sale Order Line', ondelete='set null', select=True,
            readonly=True),
    }

    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = super(stock_move, self).write(cr, uid, ids, vals, context=context)
        for move in self.browse(cr, uid, ids, context=context):
            if move.dealer_sale_order_line_id: 
                dealer_sale_order_id = move.dealer_sale_order_line_id.dealer_sale_order_line_id.id 
                #self.pool.get('dealer.sale.order').check_done(cr,uid,dealer_sale_order_id)
                #if self.pool.get('dealer.sale.order').test_moves_done(cr, uid, [dealer_sale_order_id], context=context):
                #    workflow.trg_validate(uid, 'dealer.sale.order', dealer_sale_order_id, 'picking_done', cr)
                #    self.pool.get('dealer.sale.order').check_done(cr,uid,dealer_sale_order_id)
        return res
    
class wtc_stock_picking_dso(osv.osv):
    _inherit = 'stock.picking'
    
    def write(self, cr, uid, ids, vals, context=None):
        res = super(wtc_stock_picking_dso, self).write(cr, uid, ids, vals, context=context)
        if vals.get('date_done'):
            for pick in self.browse(cr, uid, ids, context=context):
                if pick.model_id.model=='dealer.sale.order': 
                    self.pool.get('dealer.sale.order').check_done(cr,uid,pick.transaction_id)
        return res
    
    def transfer(self, cr, uid, picking, context=None):
        res = super(wtc_stock_picking_dso, self).transfer(cr, uid, picking, context=context)
        if picking.picking_type_id.code == 'outgoing' and picking.model_id.model == 'dealer.sale.order' :
            obj_order = self.pool.get('dealer.sale.order').browse(cr, uid, picking.transaction_id)
            qty = {}
            for x in picking.move_lines :
                qty[x.product_id] = qty.get(x.product_id,0) + x.product_uom_qty
            for x in obj_order.dealer_sale_order_line :
                qty[x.product_id] = qty.get(x.product_id,0) + x.product_qty
                x.write({'supply_qty':qty[x.product_id]})
        if picking.picking_type_id.code == 'incoming' and picking.model_id.model == 'dealer.sale.order' :
            obj_order = self.pool.get('dealer.sale.order').browse(cr, uid, picking.transaction_id)
            qty = {}
            for x in picking.move_lines :
                qty[x.product_id] = qty.get(x.product_id,0) + x.product_uom_qty
            for x in obj_order.dealer_sale_order_line :
                qty[x.product_id] =-(qty.get(x.product_id,0)) + x.product_qty
                x.write({'supply_qty':qty[x.product_id]})
       
        return res
    
