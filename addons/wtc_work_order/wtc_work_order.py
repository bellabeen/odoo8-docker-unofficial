import time
from lxml import etree
import pytz
from openerp import SUPERUSER_ID, workflow
from openerp.osv import fields, osv
from openerp.tools.translate import _
from datetime import datetime, timedelta
import openerp.addons.decimal_precision as dp
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
import calendar


class wtc_work_order(osv.osv):
    _name = "wtc.work.order"
    _description = "Work Order"
    _order = "date desc"
#     
#     def _report_xls_work_order_fields(self, cr, uid, context=None):
#         return [
#             'branch_id','no_invoice', 'state','tanggal','no_pol','tp','jasa_part','jumlah','harga','discount','jumlah_harga','hpp',
#             'dpp','type'
#             # 'partner_id'
#         ]
#     
#     def _report_xls_stock_sparepart_fields(self, cr, uid, context=None):
#         return [
#             'cabang', 'kode_product','location_id','tanggal','jumlah'
#             # 'partner_id'
#         ]
# ==========
#     # override list in custom module to add/drop columns
#     # or change order of the partner summary table
#     def _report_xls_arap_details_fields(self, cr, uid, context=None):
#         return [
#             'document', 'date', 'date_maturity', 'account', 'description',
#             'rec_or_rec_part', 'debit', 'credit', 'balance',
#             # 'partner_id',
#         ]
# 
#     # Change/Add Template entries
#     def _report_xls_arap_overview_template(self, cr, uid, context=None):
#         """
#         Template updates, e.g.
# 
#         my_change = {
#             'partner_id':{
#                 'header': [1, 20, 'text', _('Partner ID')],
#                 'lines': [1, 0, 'text', _render("p['p_id']")],
#                 'totals': [1, 0, 'text', None]},
#         }
#         return my_change
#         """
#         return {}
# 
#     # Change/Add Template entries
#     def _report_xls_arap_details_template(self, cr, uid, context=None):
#         """
#         Template updates, e.g.
# 
#         my_change = {
#             'partner_id':{
#                 'header': [1, 20, 'text', _('Partner ID')],
#                 'lines': [1, 0, 'text', _render("p['p_id']")],
#                 'totals': [1, 0, 'text', None]},
#         }
#         return my_change
#         """
#         return {}
    
    

    def _amount_line_tax(self,cr , uid, line, context=None):
        val=0.0
        for c in self.pool.get('account.tax').compute_all(cr,uid, line.tax_id, line.price_unit*(1-(line.discount or 0.0)/100.0),line.product_qty, line.product_id)['taxes']:
            val +=c.get('amount',0.0)
        return val
    
    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        tax_obj = self.pool.get('account.tax')
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
            }
            val = val1 = 0.0
            for line in order.work_lines:
                price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, line.product_qty, line.product_id)
                val1 += taxes['total']
                val += self._amount_line_tax(cr, uid, line, context=context)

            res[order.id]['amount_tax'] = val
            res[order.id]['amount_untaxed'] =val1
            res[order.id]['amount_total'] = res[order.id]['amount_untaxed'] + res[order.id]['amount_tax']
        return res
    
    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('wtc.work.order.line').browse(cr, uid, ids, context=context):
            result[line.work_order_id.id] = True
        return result.keys()
    
    
    def _max_warranty(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'warranty': 0.0,
            }
            nilai_max = 0.0
            
            for line in order.work_lines:
                if nilai_max < line.warranty:
                    nilai_max = line.warranty
            res[order.id]['warranty'] = nilai_max
        return res

    def _get_days(self, cr, uid, context=None):
        x = []
        return x
    
    def get_location_ids(self,cr,uid,ids,context=None):
        quants_ids = self.pool.get('stock.quant').search(cr,uid,['&',('product_id','in',ids),('qty','>',0.0),('reservation_id','=',False)])
        loc_ids = self.pool.get('stock.quant').read(cr, uid, quants_ids, ['location_id'])
        return [x['location_id'][0] for x in loc_ids]
    

    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('waiting_for_approval','Waiting Approval'),
        ('confirmed', 'Confirmed'),
        ('approved', 'Approved'),
        ('finished', 'Finished'),
        ('open', 'Open'),
        ('except_picking', 'Shipping Exception'),
        ('except_invoice', 'Invoice Exception'),
        ('done', 'Done'),
        ('unused', 'Unused'),
        ('cancel', 'Cancelled')
    ]
    
    

    
    
    def _invoiced(self, cursor, user, ids, name, arg, context=None):
        res = {}
        for purchase in self.browse(cursor, user, ids, context=context):
            res[purchase.id] = all(line.invoiced for line in purchase.work_lines)
        return res
    
    def _get_picking_in(self, cr, uid, context=None):
        obj_data = self.pool.get('ir.model.data')
        return obj_data.get_object_reference(cr, uid, 'stock','picking_type_in') and obj_data.get_object_reference(cr, uid, 'stock','picking_type_in')[1] or False

    def _get_picking_ids(self, cr, uid, ids, field_names, args, context=None):
        res = {}
        for po_id in ids:
            res[po_id] = []
        query = """
        SELECT picking_id, po.id 
        FROM stock_picking p,
         stock_move m, 
         wtc_work_order_line pol, 
         wtc_work_order po
         
         
            WHERE  po.id in %s
            and po.id = pol.work_order_id
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
        for wo in self.browse(cr, uid, ids, context=context):
            for picking in wo.picking_ids:
                if picking.state != 'done' and picking.state != 'cancel' :
                    return False
        return True

    
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False  
        return branch_ids 
        
    def _get_default_date(self,cr,uid,context):
        return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)  
    
    def _get_history_service(self, cr, uid, ids, field_names, args, context=None): 
        res = {}
        for po_id in ids:
            res[po_id] = []
        data = self.browse(cr,uid,ids)
        history_ids = self.search(cr,uid,[('lot_id','=',data.lot_id.id),('id','not in',ids),('date','<=',data.date)])
        for id in history_ids:
            res[po_id].append(id)
        return res

    _columns = {
        'name': fields.char('Work Order', size=64, required=True),
        'date' : fields.date('Order Date', required=True),
        'state': fields.selection(STATE_SELECTION, 'Status', readonly=True, select=True, copy=False),
        'branch_id':fields.many2one('wtc.branch','Branch',required=True),
        'division':fields.selection([('Sparepart','Sparepart')],'Division', change_default=True,select=True,required=True),
        'driver_id':fields.many2one('res.partner','Pembawa',required=True),
        'customer_id':fields.many2one('res.partner','Pemilik (STNK)'),
        'customer_name':fields.related('customer_id','name',type='char', required=True,readonly=True, string='Customer Name',),
        'type':fields.selection([('KPB','KPB'),('REG','Regular'),('WAR','Job Return'),('CLA','Claim'),('SLS','Part Sales'),('PDI','PDI')],'Type', change_default=True, select=True, readonly=True, required=True),
        'kpb_ke':fields.selection([('1','1'),('2','2'),('3','3'),('4','4')],'KPB Ke',change_default=True,select=True),
        'no_pol':fields.char('No Polisi',size=10,select=True),
        'prev_work_order_id':fields.many2one('wtc.work.order','WO Sebelumnya'), # domain: state = done dan type = REG atau WAR dan date tidak melebihi waktu garansi
        'mekanik_id':fields.many2one('res.users','Mechanic'),
        'employee_id':fields.many2one('hr.employee','Employee'),
        'product_id':fields.many2one('product.product','Product'),
        'km':fields.integer('Km'),
        'work_lines': fields.one2many('wtc.work.order.line', 'work_order_id', 'Order lines'),
        'note': fields.text('Keluhan'),
        'payment_term':fields.many2one('account.payment.term','Payment Terms',required=True),
        'lama_garansi':fields.float('Lama Garansi'),
        'start':fields.datetime('Start',readonly=True),
        'date_break':fields.datetime('Break',readonly=True),
        'end_break':fields.datetime('End Break',readonly=True),
        'finish':fields.datetime('Finish',readonly=True),
        'bensin':fields.selection([('0','0'),('25','25'),('50','50'),('75','75'),('100','100')],'Bensin',change_default=True,select=True),
        'type_motorcycle':fields.char('Type Motorcycle'),
        'member':fields.char('Member'),
        'kode_buku':fields.char('Kode Buku'),
        'nama_buku':fields.char('Nomor Buku'),
        'pekerjaan':fields.many2one('wtc.questionnaire','Pekerjaan Konsumen',domain="[('type','=','Pekerjaan')]"),
        'shipped':fields.boolean('Received', readonly=True, select=True, copy=False,help="It indicates that a picking has been done"),  
        'tanggal_pembelian':fields.date('Tanggal Pembelian'),
        'lot_id':fields.many2one('stock.production.lot','Engine No'),
        'chassis_no':fields.related('lot_id','chassis_no',type='char',string='Chassis Number'),
        'amount_untaxed': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Untaxed Amount',
            store={
                'wtc.work.order': (lambda self, cr, uid, ids, c={}: ids, ['work_lines'], 10),
                'wtc.work.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_qty'], 10),
            },
            multi='sums', help="The amount without tax.", track_visibility='always'),
        'amount_tax': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Taxes',
            store={
                'wtc.work.order': (lambda self, cr, uid, ids, c={}: ids, ['work_lines'], 10),
                'wtc.work.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_qty'], 10),
            },
            multi='sums', help="The tax amount."),
        'amount_total': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total',
            store={
                'wtc.work.order': (lambda self, cr, uid, ids, c={}: ids, ['work_lines'], 10),
                'wtc.work.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_qty'], 10),
            },
            multi='sums', help="The total amount."),
        'warranty':fields.function(_max_warranty, digits_compute=dp.get_precision('Account'), string='Warranty',
            store={
                'wtc.work.order': (lambda self, cr, uid, ids, c={}: ids, ['work_lines'], 10),
                'wtc.work.order.line': (_get_order, ['product_id'], 10),
            },
            multi='sums', help="Warranty"),
        'tipe_buku':fields.char('Tipe Buku Service'),
        'jenis_oli': fields.selection([('MPX', 'MPX'), ('SPX','SPX')], 'Jenis Oli'),
        'dealer_penjual':fields.char('Dealer Penjual'),
        'stampel_ahass': fields.selection([('ada', 'Ada'), ('tidak','Tidak Ada')], 'Stampel Ahass'),
        'stampel_dealer_depan': fields.selection([('ada', 'Ada'), ('tidak','Tidak Ada')], 'Stampel Dealer Depan'),
        'stampel_dealer_belakang': fields.selection([('ada', 'Ada'), ('tidak','Tidak Ada')], 'Stampel Dealer Belakang'),
        'tt_pemilik': fields.selection([('ada', 'Ada'), ('tidak','Tidak Ada')], 'TTD'),
        'km_cek': fields.selection([('ada', 'Ada'), ('tidak','Tidak Ada')], 'KM Cek'),
        'tgl_beli_cek': fields.selection([('ada', 'Ada'), ('tidak','Tidak Ada')], 'Cek Tanggal Beli'),
        'tgl_service_cek': fields.selection([('ada', 'Ada'), ('tidak','Tidak Ada')], 'Cek Tanggal Service'),
        'chassis_no_cek': fields.selection([('ada', 'Ada'), ('tidak','Tidak Ada')], 'Cek No Chassis'),
        'engine_no_cek': fields.selection([('ada', 'Ada'), ('tidak','Tidak Ada')], 'Cek No Engine'),
        'no_buk_cek': fields.selection([('ada', 'Ada'), ('tidak','Tidak Ada')], 'Cek No Buku'),
        'kpb_collected':fields.selection([('belum', 'Belum'), ('ok','OK'), ('not','Not Ok'), ('collected','Collected')], 'KPB Collected'),
        'collecting_id':fields.many2one('wtc.collecting.kpb',string="Collecting KPB ID"),
        'mobile': fields.char('Mobile'),
        'days':fields.integer('Hari'),
        'type_wo':fields.boolean('Type WO', readonly=True, select=True, copy=False),  
        'date_confirm':fields.date('Confirmation date', readonly=1),
        'invoiced': fields.function(_invoiced, string='Invoice Received', type='boolean', copy=False), 
        'invoice_method': fields.selection([('manual','Based on Purchase Order lines'),('order','Based on generated draft invoice'),('picking','Based on incoming shipments')], 'Invoicing Control', required=True,
            readonly=True, states={'draft':[('readonly',False)], 'sent':[('readonly',False)]},
            help="Based on Purchase Order lines: place individual lines in 'Invoice Control / On Purchase Order lines' from where you can selectively create an invoice.\n" \
                "Based on generated invoice: create a draft invoice you can validate later.\n" \
                "Based on incoming shipments: let you create an invoice when receipts are validated."
        ), 
        'invoice_ids': fields.many2many('account.invoice', 'purchase_invoice_rel', 'purchase_id',
                                        'invoice_id', 'Invoices', copy=False),
        'picking_ids': fields.function(_get_picking_ids, method=True, type='one2many', relation='stock.picking', string='Picking List', help="This is the list of receipts that have been generated for this purchase order."),
        'confirm_uid':fields.many2one('res.users',string="Confirmed by"),
        'confirm_date':fields.datetime('Confirmed on'),    
        'pajak_gabungan':fields.boolean('Faktur Pajak Gabungan',copy=False, readonly=True),   
        'faktur_pajak_id':fields.many2one('wtc.faktur.pajak.out',string='No Faktur Pajak',copy=False),                                       
        'is_cancelled': fields.boolean('Is Cancelled'),
        'work_order_history_ids':fields.function(_get_history_service, method=True, type='one2many', relation='wtc.work.order',string='History Service'),
        'reason_unused' : fields.char('Reason Unused'),
        'dealer_sendiri':fields.selection([('ya','Ya'),('tidak','Tidak')]),
        'hubungan_pemilik':fields.char('Hubungan Dengan Pemilik'),
        'alasan_ke_ahass':fields.selection([
            ('regular visit ahass','Regular Visit AHASS'),
            ('sms call remainder','SMS & Call Remainder'),
            ('service visit','Service Visit'),
            ('ahass event','Ahass Event'),
            ('pit express','Pit Express'),
            # ('inisiatif sendiri','Inisiatif Sendiri'),
            # ('sticker remainder','Sticker Remainder'),
            # ('telp remainder','Telp Remainder'),
            # ('visit ahass','Visit AHASS'),
            # ('lainnya','Lainnya')
        ]),
        'tahun_perakitan': fields.char('Tahun Perakitan'),
        'cancelled_uid':fields.many2one('res.users',string="Cancelled by"),
        'cancelled_date':fields.datetime('Cancelled on'),
        'is_event_kpb':fields.boolean('KPB Event State', readonly=True, select=True, copy=False,help="It indicates that this Work Order got an exception on KPB Checking")
    }
    
    _defaults = {
        'name': '/',
        'km':False,
        'state': 'draft',
        'date': _get_default_date,
        'division':'Sparepart',
        'kpb_collected':'belum',
        'stampel_ahass':'tidak',
        'stampel_dealer_depan':'tidak',
        'stampel_dealer_belakang':'tidak',
        'tt_pemilik':'tidak',
        'km_cek':'tidak',
        'tgl_beli_cek':'tidak',
        'tgl_service_cek':'tidak',
        'chassis_no_cek':'tidak',
        'engine_no_cek':'tidak',
        'no_buk_cek':'tidak',
        'tanggal_pembelian':_get_default_date,
        'days':_get_days,
        'invoice_method': 'manual',
        'shipped': 0,
        'state':'draft',
        'type_wo':0,
        'warranty':0.0,
        'branch_id': _get_default_branch,
    }
    _sql_constraints = [
    ('unique_name', 'unique(name)', 'Nama WO harus unik !'),
]
    
 
    def mekanik_id_change (self,cr,uid,ids,mekanik_id):
        if mekanik_id :
            obj_employee=self.pool.get('hr.employee')
            obj_search_empl=obj_employee.search(cr, uid,[('user_id','=',mekanik_id)])
            obj_browse_empl=obj_employee.browse(cr,uid,obj_search_empl)
            return {'value' : {'employee_id':obj_browse_empl.id}}
            
    def chassis_onchange(self, cr, uid, ids,chassis_no):
        if chassis_no :
            chassis_no = chassis_no.replace(' ', '').upper()
            return {'value' : {'chassis_no':chassis_no}}
        

    def no_pol_onchange(self, cr, uid, ids,no_pol):
        if no_pol :
            no_pol = no_pol.replace(' ', '').upper()
            return {'value' : {'no_pol':no_pol}}
    

    def kode_buku_onchange(self, cr, uid, ids,kode_buku):
        if kode_buku :
            kode_buku = kode_buku.replace(' ', '').upper()
            return {'value' : {'kode_buku':kode_buku}}
        

    def nama_buku_onchange(self, cr, uid, ids,nama_buku):
        if nama_buku :
            nama_buku = nama_buku.replace(' ', '').upper()
            return {'value' : {'nama_buku':nama_buku}}

    def onchange_prev_work_order_id(self, cr, uid, ids, prev_work_order_id):
        if prev_work_order_id:
            prev_work_order = self.pool.get('wtc.work.order').browse(cr, uid, prev_work_order_id)
            if prev_work_order:
                return {'value':{
                            'lot_id':prev_work_order.lot_id.id,
                        },}
            return {'value':{'lot_id':False}}
        return True
    
    def onchange_tanggal(self,cr,uid,ids,tanggal_pembelian,date):
        a=datetime.strptime(date,"%Y-%m-%d")
        b=datetime.strptime(tanggal_pembelian,"%Y-%m-%d")
        timedelta = a -b
        diff=timedelta.days
        return {
                'value':{
                         'days':diff
                         }
                }
    
    def onchange_branch_id(self, cr, uid, ids,branch_id,product_id):
        dom = {}
        value = {'mekanik_id':False}
        if branch_id :
            ids_job = self.pool.get('hr.job').search(cr, uid, [('sales_force','=','mechanic')])
            if ids_job :
                ids_employee = self.pool.get('hr.employee').search(cr, uid, [('job_id','in',ids_job),('branch_id','=',branch_id)])
                if ids_employee :
                    ids_user = [employee.user_id.id for employee in self.pool.get('hr.employee').browse(cr, uid, ids_employee)]
                    dom['mekanik_id'] = [('id','in',ids_user)]
                    
        product_ids = self.pool.get('product.category').get_child_ids(cr,uid,ids,'Unit')
        dom['product_id']=[('categ_id','in',product_ids)]
        return {'domain':dom, 'value':value}
    
    def onchange_lot_id(self, cr, uid, ids, lot_id):
        lot = self.pool.get('stock.production.lot').browse(cr, uid, lot_id) 

        if lot:
            return {'value':{
                        'customer_id':lot.customer_id.id,
                        'product_id':lot.product_id.id,
                        'kode_buku':lot.kode_buku,
                        'nama_buku':lot.nama_buku,
                        'tanggal_pembelian':lot.invoice_date,
                        'driver_id':lot.driver_id.id if lot.driver_id else False,
                        'no_pol':lot.no_polisi,
                        'chassis_no':lot.chassis_no,
                    }}
           
        return {'value':{
                    'customer_id':False,
                    'driver_id':False,
                    'product_id':False,
                    'kode_buku':False,
                    'nama_buku':False,
                    'tanggal_pembelian':False,
                    'no_pol':False,
                    'chassis_no':False,
                }}

    def onchange_driver_id(self, cr, uid, ids, driver_id,type,branch_id):
        mobile = []
        payment_term = []
        if driver_id:
            obj_customer = self.pool.get("res.partner").browse(cr,uid,driver_id)
            mobile = obj_customer.mobile

            if type == 'SLS' or type == 'REG' :
                payment_term = obj_customer.property_payment_term.id
            elif type == 'KPB' or type == 'CLA' : 
                obj_payment_term=self.pool.get("wtc.branch").browse(cr,uid,branch_id)
                payment_term = obj_payment_term.default_supplier_id.property_payment_term.id
            if not payment_term :
                 payment_term =1
        else:
            mobile = False
        return {'value':{'mobile' : mobile,'payment_term': payment_term}}

    def onchange_tahun_perakitan(self, cr, uid, ids, tahun_perakitan,date):
        if tahun_perakitan:
            if int(tahun_perakitan) <= 1969 or int(tahun_perakitan) >= int(date[:4])+1:
                raise osv.except_osv(('Warning !'), ("Tahun perakitan minimal 1970 dan maksimal tahun %s")%(date[:4]))

    def wtc_outstanding_claim_kpb_wizard(self,cr,uid,ids,context=None):  
        obj_claim_kpb = self.browse(cr,uid,ids)
        obj_ir_view = self.pool.get("ir.ui.view")
        obj_ir_view_search= obj_ir_view.search(cr,uid,[("name", "=", 'wtc.outstanding.claim.kpb.wizard.form'), ("model", "=", 'wtc.work.order'),])
        obj_ir_view_browse = obj_ir_view.browse(cr,uid,obj_ir_view_search)
        return {
            'name': 'Work Order',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.work.order',
            'type': 'ir.actions.act_window',
            'view_id' : obj_ir_view_browse.id,
            'nodestroy': True,
            'target': 'new',
            'res_id': obj_claim_kpb.id
            } 
        
    def start_stop_wo(self, cr, uid, ids, context=None):
        obj_claim_kpb = self.pool.get("ir.ui.view")
        obj_ir_view = obj_claim_kpb.search(cr,uid, [("name", "=", 'wtc.start.stop.wo.form'),("model", "=", 'wtc.start.stop.wo'),])
        view_id = obj_claim_kpb.browse(cr,uid,obj_ir_view)
        work_order_browse = self.browse(cr, uid, ids[0], context=context)
        return {
            'name':_("Start / Stop Work Order"),
            'view_mode': 'form',
            'view_id': view_id.id,
            'view_type': 'form',
            'res_model': 'wtc.start.stop.wo',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
            'context': {
                'work_order_id': work_order_browse.id,
                'mekanik_id': work_order_browse.mekanik_id.id,
            }
        }
        

    def action_tidak_digunakan(self,cr,uid,ids,context=None):  
        obj_unused = self.browse(cr,uid,ids)
        obj_ir_view = self.pool.get("ir.ui.view")
        obj_ir_view_search= obj_ir_view.search(cr,uid,
                            [("name", "=", 'wtc.work.order.unused'), 
                             ("model", "=", 'wtc.work.order'),])
        obj_ir_view_browse = obj_ir_view.browse(cr,uid,obj_ir_view_search)
        return {
            'name': 'Reason',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.work.order',
            'type': 'ir.actions.act_window',
            'view_id' : obj_ir_view_browse.id,
            'nodestroy': True,
            'target': 'new',
            'res_id': obj_unused.id
            } 
        
    def wkf_action_button_confirm_reason_unused(self, cr, uid, ids, context=None):
        obj_po = self.browse(cr, uid, ids, context=context)

        for line in obj_po.work_lines :
            if line.state == 'draft' :
                self.pool.get('wtc.work.order.line').write(cr,uid,line.id,{'state': 'confirmed'})
        self.write(cr, uid, ids, {'state': 'unused','reason_unused':obj_po.reason_unused})

        obj_picking = self.pool.get('stock.picking')
        ids_picking = obj_po._get_ids_picking()
        picking_ids = obj_picking.browse(cr,uid,ids_picking)
        print 'obj_po',obj_po,' obj_picking',obj_picking,' ids_picking',ids_picking, ' picking_ids',picking_ids
        for picking_id in picking_ids :
            picking_id.action_cancel()
        return True
        

        

    def view_picking(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        mod_obj = self.pool.get('ir.model.data')
        dummy, action_id = tuple(mod_obj.get_object_reference(cr, uid, 'stock', 'action_picking_tree'))
        action = self.pool.get('ir.actions.act_window').read(cr, uid, action_id, context=context)
        pick_ids = []
        for po in self.browse(cr, uid, ids, context=context):
            pick_ids += [picking.id for picking in po.picking_ids]
        action['context'] = {}
        if len(pick_ids) > 1:
            action['domain'] = "[('id','in',[" + ','.join(map(str, pick_ids)) + "])]"
        else:
            res = mod_obj.get_object_reference(cr, uid, 'stock', 'view_picking_form')
            action['views'] = [(res and res[1] or False, 'form')]
            action['res_id'] = pick_ids and pick_ids[0] or False 
        return action
    
    def view_picking_slip(self,cr,uid,ids,context=None): 
        if context is None:
            context = {}
        mod_obj = self.pool.get('ir.model.data')
        dummy, action_id = tuple(mod_obj.get_object_reference(cr, uid, 'stock', 'action_picking_tree'))
        action = self.pool.get('ir.actions.act_window').read(cr, uid, action_id, context=context)
        pick_ids = []
        for po in self.browse(cr, uid, ids, context=context):
            pick_ids += [picking.id for picking in po.picking_ids]
        action['context'] = {}
        if len(pick_ids) > 1:
            action['domain'] = "[('id','in',[" + ','.join(map(str, pick_ids)) + "])]"
        else:
            res = mod_obj.get_object_reference(cr, uid, 'stock', 'view_picking_form')
            action['views'] = [(res and res[1] or False, 'form')]
            action['res_id'] = pick_ids and pick_ids[0] or False 
        return action
    
    
    def _get_jornal_id(self, cr, uid, ids, branch_id,type,context=None):
             obj_account = self.pool.get('wtc.branch.config').search(cr,uid,[('branch_id','=',branch_id),])
             set_account_journal = {}
             jornal=self.pool.get('wtc.branch.config').browse(cr,uid,obj_account)
             if obj_account:
                if type == 'KPB' :
                    journal_id=self.pool.get('wtc.branch.config').browse(cr,uid,obj_account).wo_kpb_journal_id.id
                    account_id=self.pool.get('wtc.branch.config').browse(cr,uid,obj_account).wo_kpb_journal_id.default_debit_account_id.id
                    if not journal_id:
                         raise osv.except_osv(('Warning !'), ("Journal WO KPB Belum di Setting"))
                    if not account_id :
                         raise osv.except_osv(('Warning !'), ("Debit Account WO KPB di Branch Config Belum di Setting"))
                    
                if type == 'CLA' :
                    journal_id=self.pool.get('wtc.branch.config').browse(cr,uid,obj_account).wo_claim_journal_id.id
                    account_id=self.pool.get('wtc.branch.config').browse(cr,uid,obj_account).wo_claim_journal_id.default_debit_account_id.id
                    if not journal_id:
                         raise osv.except_osv(('Warning !'), ("Journal WO Claim Belum di Setting"))
                    if not account_id :
                         raise osv.except_osv(('Warning !'), ("Debit Account WO Claim di Branch Config Belum di Setting"))
                if type == 'SLS' or type == 'REG' or type == 'PDI' or type == 'HOTLINE': 
                    journal_id=self.pool.get('wtc.branch.config').browse(cr,uid,obj_account).wo_reg_journal_id.id
                    account_id=self.pool.get('wtc.branch.config').browse(cr,uid,obj_account).wo_reg_journal_id.default_debit_account_id.id
                    if not journal_id:
                         raise osv.except_osv(('Warning !'), ("Journal WO Regular dan Part Sales Belum di Setting"))
                    if not account_id :
                         raise osv.except_osv(('Warning !'), ("Debit Account WO Regular dan Part Sales di Branch Config Belum di Setting"))
                if type == 'WAR' : 
                    journal_id=self.pool.get('wtc.branch.config').browse(cr,uid,obj_account).wo_war_journal_id.id
                    account_id=self.pool.get('wtc.branch.config').browse(cr,uid,obj_account).wo_war_journal_id.default_debit_account_id.id  
                    if not journal_id:
                         raise osv.except_osv(('Warning !'), ("Journal  WO Parts Sales & Job Return Belum di Setting"))
                    if not account_id :
                         raise osv.except_osv(('Warning !'), ("Debit Account WO Parts Sales & Job Return di Branch Config Belum di Setting"))
                set_account_journal.update({'journal_id':journal_id,'account_id': account_id, })
                return set_account_journal
            
               
    def _get_account_id(self, cr, uid, ids, product_id,context=None):
             obj_account = self.pool.get('product.product').search(cr,uid,[('id','=',product_id),])
             if obj_account:
                account_line=self.pool.get('product.product').browse(cr,uid,obj_account).property_account_income.id
                if not account_line :
                 account_line=self.pool.get('product.product').browse(cr,uid,obj_account).categ_id.property_account_income_categ.id
                 if not account_line :
                     account_line=self.pool.get('product.product').browse(cr,uid,obj_account).categ_id.parent_id.property_account_income_categ.id
                 if not account_line :
                     raise osv.except_osv(('Warning !'), ("Account Untuk Product Belum di Setting"))
                return account_line
  
      
    def _get_customer_id(self, cr, uid, ids, type,customer_id,branch_id,context=None):
             if type == 'KPB' or type == 'CLA' :
                 obj_customer_wo = self.pool.get('wtc.branch').browse(cr, uid,branch_id)
                 customer_id_wo=obj_customer_wo.default_supplier_id.id
                 if not obj_customer_wo.default_supplier_id.id :
                    raise osv.except_osv(('Perhatian !'), ("Principle di Branch Belum di Setting"))
             else :
                customer_id_wo=customer_id
             return customer_id_wo           
 
         
    def _get_dest_location_wo(self,cr,uid,ids,context=None):
        default_location_id = {}
        obj_picking_type = self.pool.get('stock.picking.type')
        for val in self.browse(cr,uid,ids):
            picking_type_id = obj_picking_type.search(cr,uid,[
                ('branch_id','=',val.branch_id.id),
                #('division','=','Sparepart'),
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
     
    
    def _get_wo(self, cr, uid, ids, type,date,tanggal_pembelian,lot_id,kpb_ke,km,is_event_kpb,context=None):
        if type == 'KPB' :
            tanggal_wo=date
            tanggal_pembelian=tanggal_pembelian
            tanggal_wo_format=datetime.strptime(tanggal_wo,"%Y-%m-%d")
            tanggal_pembelian_format=datetime.strptime(tanggal_pembelian,"%Y-%m-%d")
            pengurangan_hari=tanggal_wo_format-tanggal_pembelian_format
            pengurangan_hari_format=abs((pengurangan_hari).days)
            
            obj_engine = self.pool.get('wtc.kpb.expired')
            lot = self.pool.get('stock.production.lot').browse(cr, uid, lot_id)
            vit = obj_engine.search(cr,uid, [("name", "=", lot.name[:4]), ("service", "=", kpb_ke),])
            if not vit:
                raise osv.except_osv(('Perhatian !'), ("No Engine Tidak Ada Di Database KPB"))
            data = obj_engine.browse(cr, uid, vit)
            
            if not is_event_kpb:
                if km>data.km:
                    raise osv.except_osv(('Perhatian !'), ("Kilometer telah lewat batas KPB"))
                elif km==0:
                    raise osv.except_osv(('Perhatian !'), ("Kilometer tidak boleh nol"))
                if pengurangan_hari_format > data.hari:
                    raise osv.except_osv(('Perhatian !'), ("Tanggal KPB sudah lewat batas KPB"))
        elif type != 'SLS' :
            if km==0:
                raise osv.except_osv(('Perhatian !'), ("Kilometer tidak boleh nol"))
        return True


    def create(self, cr, uid, vals, context=None):
#         for x in vals['work_lines'] :
#             product_qty = x[2]['product_qty']
#             price_unit = x[2]['price_unit']
#             categ_id = x[2]['categ_id']
#             discount = x[2]['discount']
#             qty_available = x[2]['qty_available']
#             if price_unit <= 0 :
#                 raise osv.except_osv(('Perhatian !'), ("Price Unit tidak boleh kurang dari nol"))
#             if discount == 100 :
#                 raise osv.except_osv(('Perhatian !'), ("Diskon tidak boleh 100%"))
#             if categ_id == 'Sparepart':
#                 if qty_available <= 0 or qty_available < product_qty:
#                     raise osv.except_osv(('Perhatian !'), ("Stock Tidak Cukup"))
        if vals['mobile'] :
            if len( vals['mobile'] ) < 6 :
                raise osv.except_osv(('Perhatian !'), ("Mobile tidak boleh kurang dari 6 digit !"))
            else: 
                cek = vals['mobile'].isdigit()
            if not cek :
                raise osv.except_osv(('Perhatian !'), ("Mobile hanya boleh angka !"))
  
        if not vals['work_lines'] :
            raise osv.except_osv(('Perhatian !'), ("Detail Transaksi Belum di Isi"))
        vals['date'] = self._get_default_date(cr, uid, context).strftime('%Y-%m-%d')
        is_event = vals['is_event_kpb'] if vals.get('is_event_kpb') else False
        self._get_wo(cr, uid, vals['branch_id'], vals ['type'],vals['date'],vals['tanggal_pembelian'],vals['lot_id'],vals['kpb_ke'],vals['km'],is_event)       
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'WO')

        if 'work_lines' in vals:
            for x in vals.get('work_lines',False):
                x[2]['product_qty'] = round(x[2]['product_qty'],0)
            
        if vals.get('type',False) in ('KPB', 'CLA', 'PDI') :
            vals['pajak_gabungan'] = True
        
        payment_term = 1
        if vals['driver_id']:
            driver_obj = self.pool.get("res.partner").browse(cr,uid,vals['driver_id'])
            if vals['type'] == 'SLS' or vals['type'] == 'REG' :
                if driver_obj.property_payment_term.id:
                    payment_term = driver_obj.property_payment_term.id
            elif vals['type'] == 'KPB' or vals['type'] == 'CLA' : 
                obj_payment_term = self.pool.get("wtc.branch").browse(cr,uid,vals['branch_id'])
                if obj_payment_term.default_supplier_id.property_payment_term.id:
                    payment_term = obj_payment_term.default_supplier_id.property_payment_term.id
        vals['payment_term'] = payment_term

        work_order = super(wtc_work_order, self).create(cr, uid, vals, context=context)
        if work_order:
            obj_lot = self.pool.get('stock.production.lot').browse(cr,SUPERUSER_ID,vals['lot_id'])
            if obj_lot.state != 'stock':
                lot_update_reserve = obj_lot.sudo().write({'no_polisi':vals['no_pol'],'chassis_no':vals['chassis_no'],'product_id':vals['product_id'],'driver_id':vals['driver_id']})       
            
           
            obj_partner = self.pool.get('res.partner')
            # obj_browse = obj_partner.browse(cr,uid,vals['driver_id'])
            res_update_mobile = obj_partner.write(cr,uid,vals['driver_id'],{'mobile':vals['mobile']},{'customer':True})   
        return work_order

    def write(self, cr, uid, ids, vals, context=None):
        context = context or {}
        tgl_break = time.strftime('%Y-%m-%d %H:%M:%S')
       
        if vals.get('type', False ) in ('KPB', 'CLA', 'PDI') :
            vals['pajak_gabungan'] = True

        if vals.get('type', False ) in ('REG', 'WAR', 'SLS') :
            vals['pajak_gabungan'] = False

        #if vals.get('work_lines', False ):
        #    for x in vals['work_lines']:
        #        if x[2].get('product_qty',False) :
        #            x[2]['product_qty'] = round(x[2]['product_qty'],0)
        
        payment_term = 1
        wo_obj = self.browse(cr, uid, ids, context=context)
        if vals.get('driver_id'):
            driver_obj = self.pool.get("res.partner").browse(cr,uid,vals['driver_id'])
            type_service = wo_obj.type
            if vals.get('type',False):
                type_service = vals['type']
            if (type_service == 'SLS') or (type_service == 'REG'):
                payment_term = driver_obj.property_payment_term.id
            elif (type_service == 'KPB') or (type_service == 'CLA'): 
                obj_payment_term = self.pool.get("wtc.branch").browse(cr,uid,wo_obj.branch_id.id)
                payment_term = obj_payment_term.default_supplier_id.property_payment_term.id
            vals['payment_term'] = payment_term

        res=super(wtc_work_order, self).write(cr, uid, ids, vals, context=context)
        for wo in self.browse(cr, uid, ids, context=context):
            for x in wo.work_lines :
                if int(x.product_qty) <= 0:
                    raise osv.except_osv(('Perhatian !'), ("Product Qty tidak boleh 0 !"))
                if x.state == 'draft': 
                    workflow.trg_delete(uid, 'wtc.work.order', x.work_order_id.id, cr) 
                    workflow.trg_create(uid, 'wtc.work.order',  x.work_order_id.id, cr)

                    if (x.categ_id == 'Sparepart' and x.state == 'draft' and x.work_order_id.state_wo == 'in_progress') or (x.categ_id == 'Service' and x.state == 'draft' and x.work_order_id.state_wo == 'in_progress'):
                        super(wtc_work_order, self).write(cr, uid, ids, {'state': 'draft','shipped':0,'type_wo':0,'state_wo':'break','date_break':tgl_break}, context=context)
                    elif x.categ_id == 'Sparepart' and x.state == 'draft':
                        super(wtc_work_order, self).write(cr, uid, ids, {'state': 'draft','shipped':0,'type_wo':0}, context=context)
                    else :
                        super(wtc_work_order, self).write(cr, uid, ids, {'state': 'draft'}, context=context)
                        workflow.trg_validate(uid, 'wtc.work.order',  x.work_order_id.id, 'break_wo', cr)
                
                        
        return res
  
    def button_dummy(self, cr, uid, ids, context=None):
        return True
    
    def wkf_approve_order(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'approved'})
       
        return True
        
    def invoice_done(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'done'}, context=context)
        return True
    
    def wkf_po_done(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'done'}, context=context)
        
    def wo_draft(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'draft'})

    def start2(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state_wo':False})
    
    def start_wo(self, cr, uid, ids, context=None):
        self.signal_workflow(cr, uid, ids, 'in_progress')
    
    def break_wo(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state_wo':'break'})
    
    def end_break_wo(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state_wo':'in_progress'})
    
    def end_wo(self, cr, uid, ids, context=None):
        wo = self.browse(cr,uid,ids)
        if wo.shipped==1:
            self.signal_workflow(cr, uid, ids, 'picking_done')
        return self.write(cr, uid, ids, {'state_wo':'finish'})
    
    def finished(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'finished'})
    
    def invoice_create_wo(self, cr, uid, ids, context=None):
        self.signal_workflow(cr, uid, ids, 'invoice_create')
        return True
    
    def wkf_action_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'cancel','cancelled_uid':uid,'cancelled_date':datetime.now()},context=context)
        
    def wtc_collected_ok(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'kpb_collected':'ok'}, context=context)                                                     
        return True
    
    def _nrfs_update_tgl_selesai(self, cr, uid, ids, wo_obj):
        pass

    def invoice_create(self, cr, uid, ids, context=None):
        force_cogs = 0.0   
        val = self.browse(cr, uid, ids, context={})[0]
        costumer = self._get_customer_id(cr, uid, ids,val.type,val.customer_id.id,val.branch_id.id) 
        account_and_journal = self._get_jornal_id(cr, uid, ids,val.branch_id.id,val.type) 
             
        obj_inv = self.pool.get('account.invoice') 
        obj_inv_line = self.pool.get('account.invoice.line') 
         
        obj_model = self.pool.get('ir.model')
        obj_model_id = obj_model.search(cr,uid,[ ('model','=',self.__class__.__name__) ])
        
        work_id = {
            'name':val.name,
            'origin': val.name,
            'branch_id':val.branch_id.id,
            'division':val.division,
            'partner_id':costumer,
            'date_invoice':val.date,
            'journal_id':account_and_journal['journal_id'],
            'account_id':account_and_journal['account_id'],
            'transaction_id':val.id,
            'model_id':obj_model_id[0],
            'amount_untaxed':val.amount_untaxed,
            'amount_tax':val.amount_tax,
            'amount_total':val.amount_total,
            'comment':val.note,
            'payment_term':val.payment_term.id,
            'type': 'out_invoice'                                          
            }
        #obj_inv_id = obj_inv.search(cr,uid,[ ('transaction_id','=',[val.id]) ])
        #workid = obj_inv.browse(cr,uid,obj_inv_id).id
        obj_line = self.pool.get('account.invoice.line') 
        work_id_lines = []
        per_product = {}
        for x in val.work_lines:
            key_name = "%d|%d" %(x.product_id,x.discount)

            if not per_product.get(key_name,False):
                per_product[key_name] = {}
            
            
            if x.categ_id == "Service" :
                qty=x.product_qty
            elif x.categ_id == "Sparepart" :
                qty=x.supply_qty
                if qty <=0:
                    continue
            per_product[key_name]['product_id'] = x.product_id.id
            per_product[key_name]['price_unit'] = x.price_unit
            per_product[key_name]['product_qty'] = per_product[key_name].get('product_qty',0)+qty
            per_product[key_name]['categ_id'] = x.categ_id
            per_product[key_name]['tax_id'] = [(6, 0, [y.id for y in x.tax_id])]
            per_product[key_name]['discount'] = x.discount

        for key, value in per_product.items():
            product_id = self.pool.get('product.product').browse(cr,uid,value['product_id'])
            if value['categ_id']=='Sparepart':
                force_cogs = self._get_moved_price(cr,uid,val.picking_ids,product_id)
            
            work_id_lines.append([0,False,{
                    'name':product_id.name,
                    'product_id':product_id.id,
                    'quantity':value['product_qty'],
                    'origin':val.name,
                    'price_unit':value['price_unit'],
                    'discount':value['discount'],
                    'invoice_line_tax_id': value['tax_id'],
                    'account_id': self.pool.get('product.product')._get_account_id(cr,uid,ids,product_id.id),
                    'force_cogs': force_cogs
               }])
        
            
        work_id['invoice_line'] = work_id_lines
        move=obj_inv.create(cr,uid,work_id)
        obj_inv.button_reset_taxes(cr,uid,move)
        workflow.trg_validate(uid, 'account.invoice', move, 'invoice_open', cr)
        self.write(cr, uid, ids, {'state': 'open','date_confirm':datetime.now()})
        self._nrfs_update_tgl_selesai(cr, uid, ids, val)
        #if val.amount_tax and not val.pajak_gabungan :
        #    self.pool.get('wtc.faktur.pajak.out').get_no_faktur_pajak(cr,uid,ids,'wtc.work.order',context=context) 
        return move

    def wkf_confirm_order(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'confirm_uid':uid,'confirm_date':datetime.now()})
        for po in self.browse(cr, uid, ids, context=context):
            if not po.work_lines:
                raise osv.except_osv(_('Error!'),_('You cannot confirm a work order without any work oder order line.'))
        self.button_dummy(cr, uid, ids, context=context)
        for id in ids:
            self.write(cr, uid, [id], {'state' : 'confirmed'})
        return True

    def has_sparepart(self, cr, uid, ids, *args):
        for order in self.browse(cr, uid, ids):
            for work_lines in order.work_lines:
                if work_lines.product_id and work_lines.categ_id == "Sparepart":
                    if int(work_lines.product_qty) == int(work_lines.supply_qty):
                        continue
                    return True
        return False
    
    def test_moves_except(self, cr, uid, ids, context=None):
        at_least_one_canceled = False
        alldoneorcancel = True
        for purchase in self.browse(cr, uid, ids, context=context):
            for picking in purchase.picking_ids:
                if picking.state == 'cancel':
                    at_least_one_canceled = True
                if picking.state not in ['done', 'cancel']:
                    alldoneorcancel = False
        return at_least_one_canceled and alldoneorcancel
    

    def _prepare_order_line_move(self, cr, uid, order, work_lines, picking_id, context=None):
        res = []
        average_price = self.pool.get('product.price.branch')._get_price(cr, uid, work_lines.location_id.warehouse_id.id, work_lines.product_id.id)

        location = self._get_dest_location_wo(cr,uid,order.id)
        move_template = {
                    'name': work_lines.name or '',
                    'product_uom': work_lines.product_uom.id,
                    'product_uos': work_lines.product_uom.id,
                    'picking_id': picking_id,
                    'picking_type_id':location['picking_type_id'], 
                    'work_order_line_id':work_lines.id,
                    'product_id': work_lines.product_id.id,
                    'product_uos_qty': work_lines.product_qty,
                    'product_uom_qty': work_lines.product_qty,
                    'state': 'draft',
                    'location_id': work_lines.location_id.id,
                    'location_dest_id': location['destination'],
                    'branch_id': work_lines.work_order_id.branch_id.id,
                    'price_unit': average_price,
                    'origin': work_lines.work_order_id.name
        }
        res.append(move_template)
        return res
     
        
    def _create_stock_moves(self, cr, uid, order, order_lines, picking_id=False, context=None):
        stock_move = self.pool.get('stock.move')
        todo_moves = []
        for work_lines in order_lines:
            if not work_lines.product_id:
                continue
            if work_lines.categ_id == "Sparepart" and work_lines.state == "confirmed": 
                for vals in self._prepare_order_line_move(cr, uid, order, work_lines, picking_id, context=context):
                    self.pool.get('wtc.work.order.line').write(cr,uid,work_lines.id,{'state': 'open'}, context=context)
                    move = stock_move.create(cr, uid, vals, context=context)
                    todo_moves.append(move)
        todo_moves = stock_move.action_confirm(cr, uid, todo_moves)
        stock_move.force_assign(cr, uid, todo_moves)
    

    def action_picking_create(self, cr, uid, ids, context=None):
        for order in self.browse(cr, uid, ids):
            obj_model = self.pool.get('ir.model')
            obj_model_id = obj_model.search(cr,uid,[ ('model','=',order.__class__.__name__) ])
            obj_model_id_model = obj_model.browse(cr,uid,obj_model_id).id
            location = self._get_dest_location_wo(cr,uid,order.id)
            picking_vals = {
                'picking_type_id': location['picking_type_id'],
                'division':'Sparepart',
                'move_type': 'direct',
                'branch_id': order.branch_id.id,
                'partner_id': order.customer_id.id,
                'invoice_state': 'none',
                'transaction_id': order.id,
                'model_id': obj_model_id_model,
                'origin': order.name
            }
            picking_id = self.pool.get('stock.picking').create(cr, uid, picking_vals, context=context)
            self._create_stock_moves(cr, uid, order, order.work_lines, picking_id, context=context)

    def picking_done(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'shipped':1}, context=context)
        return True   
    
    def has_service(self, cr, uid, ids, *args):
        for order in self.browse(cr, uid, ids):
            for work_lines in order.work_lines:
                if work_lines.product_id and work_lines.categ_id == "Service":
                    return True
        return False
    
    def view_invoice(self,cr,uid,ids,context=None):  
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        result = mod_obj.get_object_reference(cr, uid, 'account', 'action_invoice_tree1')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_form')
        result['views'] = [(res and res[1] or False, 'form')]
        val = self.browse(cr, uid, ids)
        obj_inv = self.pool.get('account.invoice')
        #obj = obj_inv.search(cr,uid,[('transaction_id','=',val.id),('model_id','=',self.__class__.__name__)])
        obj = obj_inv.search(cr,uid,[('origin','=',val.name)])
        result['res_id'] = obj[0] 
        return result
    
    def action_view_picking(self,cr,uid,ids,context=None):  
        val = self.browse(cr, uid, ids, context={})[0]
        obj_inv = self.pool.get('stock.picking')
        obj = obj_inv.search(cr,uid,[('transaction_id','=',val.id),('model_id','=',self.__class__.__name__)])
        return {
            'name': 'Picking Slip',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': obj[0]
            } 
        
    def unlink(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids, context={})[0]
        if val.state != 'draft':
            raise osv.except_osv(('Invalid action !'), ('Cannot delete a work order which is in state \'%s\'!') % (val.state,))
        else:
            raise osv.except_osv(('Tidak Bisa Hapus !'), ('Gunakan button unused !'))
        return super(wtc_work_order, self).unlink(cr, uid, ids, context=context) 
    
    def _get_moved_price(self,cr,uid,picking_ids,product_id):
        move_price = 0.0
        for picking in picking_ids:
            for move in picking.move_lines:
                if move.product_id.id == product_id.id and move.state=='done':
                    move_price += move.real_hpp*move.product_qty
                
        return move_price
    
    def _get_invoice_ids(self, cr, uid, ids, context=None):
        wo_id = self.browse(cr, uid, ids, context=context)
        obj_inv = self.pool.get('account.invoice')
        obj_model = self.pool.get('ir.model')
        id_model = obj_model.search(cr, uid, [('model','=','wtc.work.order')])[0]
        ids_inv = obj_inv.search(cr, uid, [
            ('model_id','=',id_model),
            ('transaction_id','=',wo_id.id),
            ('state','!=','cancel')
            ])
        inv_ids = obj_inv.browse(cr, uid, ids_inv)
        return inv_ids
    
    def _get_ids_picking(self, cr, uid, ids, context=None):
        wo_id = self.browse(cr, uid, ids, context=context)
        obj_picking = self.pool.get('stock.picking')
        obj_model = self.pool.get('ir.model')
        id_model = obj_model.search(cr, uid, [('model','=','wtc.work.order')])[0]
        ids_picking = obj_picking.search(cr, uid, [
            ('model_id','=',id_model),
            ('transaction_id','=',wo_id.id),
            ('state','!=','cancel')
            ])
        return ids_picking
    
    def is_wo_done(self, cr, uid, ids, context=None):
        inv_done = False
        wo_id = self.browse(cr, uid, ids, context=context)
        inv_ids = self._get_invoice_ids(cr, uid, ids, context)
        for inv in inv_ids :
            if inv.state == 'paid' :
                inv_done = True
        if inv_done and not wo_id.is_cancelled:
            return self.signal_workflow(cr, uid, ids, 'action_done')
        return True

    
class wtc_work_order_line(osv.osv):
    _name = "wtc.work.order.line"

    def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        res = {}
        if context is None:
            context = {}
        for line in self.browse(cr, uid, ids, context=context):
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, line.product_qty, line.product_id)
            res[line.id]=taxes['total']
        return res
    

    def create_price(self, cr, uid, ids,price_unit):
        value = {}
        
        if not price_unit:
           value ={'price_unit_show':0}
        else:
            value={'price_unit_show':price_unit}
        return {'value':value}
    

    def create_qty_available(self, cr, uid, ids,qty_available):
        value = {}
        if not qty_available:
           value ={'qty_available_show':0}
        else:
            value={'qty_available_show':qty_available}
        return {'value':value}
    
    def create_supply_qty(self, cr, uid, ids,supply_qty):
        value = {}
        if not supply_qty:
           value ={'supply_qty_show':0}
        else:
            value={'supply_qty_show':supply_qty}
        return {'value':value}
    
    def create_warranty(self, cr, uid, ids,warranty):
        value = {}
        if not warranty:
           value ={'warranty_show':0}
        else:
            value={'warranty_show':warranty}
        return {'value':value}
    
    def create_name(self, cr, uid, ids,name):
        value = {}
        if not name:
           value ={'name_show':' '}
        else:
            value={'name_show':name}
        return {'value':value}
    
    
    
    def _get_price(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for price in self.browse(cr, uid, ids, context=context):
            price_unit_show=price.price_unit
            res[price.id]=price_unit_show
        return res
    
    
    
    def _get_supply_qty(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for supply in self.browse(cr, uid, ids, context=context):
            supply_qty_show=supply.supply_qty
            res[supply.id]=supply_qty_show
        return res
    
    def _get_qty_available(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for qty in self.browse(cr, uid, ids, context=context):
            qty_available_show=qty.qty_available
            res[qty.id]=qty_available_show
        return res
    
    def _get_warranty(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for warranty in self.browse(cr, uid, ids, context=context):
            warranty_show=warranty.warranty
            res[warranty.id]=warranty_show
        return res
    

    def _get_name(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            name_show=line.name
            res[line.id]=name_show
        return res
    
    def _get_harga_jasa(self, cr, uid, ids, product_id,branch_id,product_unit_id,context=None):
        categori_workshop =self.pool.get('wtc.branch').browse(cr,uid,branch_id).workshop_category.id
        product_unit =self.pool.get('product.product').browse(cr,uid,product_unit_id).category_product_id.id
        object_harga_jasa=self.pool.get('wtc.harga.jasa').search(cr,uid,[('product_id_jasa','=',product_id),('workshop_category','=',categori_workshop),('category_product_id','=',product_unit)])
        harga_jasa=self.pool.get('wtc.harga.jasa').browse(cr,uid,object_harga_jasa).price
        return harga_jasa
    
    def _get_price_list(self, cr, uid, ids,branch_id,context=None):
        branch_price =self.pool.get('wtc.branch').browse(cr,uid,branch_id).pricelist_part_sales_id.id
        return branch_price
    

    def _get_product(self,cr, uid, ids, categ_id,type,kpb_ke,context=None):
            if type == 'KPB' and kpb_ke == '1' and  categ_id == 'Service':
                categ_ids = self.pool.get('product.category').get_child_ids(cr,uid,ids,'KPB1')
            elif type == 'KPB' and kpb_ke == '2' and categ_id == 'Service':
                categ_ids = self.pool.get('product.category').get_child_ids(cr,uid,ids,'KPB2')
            elif type == 'KPB' and kpb_ke == '2' and categ_id == 'Sparepart':
                categ_ids = self.pool.get('product.category').get_child_ids(cr,uid,ids,'')
            elif type == 'KPB' and kpb_ke == '3' and categ_id == 'Service':
                categ_ids = self.pool.get('product.category').get_child_ids(cr,uid,ids,'KPB3')
            elif type == 'KPB' and kpb_ke == '3' and categ_id == 'Sparepart':
                categ_ids = self.pool.get('product.category').get_child_ids(cr,uid,ids,'')
            elif type == 'KPB' and kpb_ke == '4' and categ_id == 'Service' :
                categ_ids = self.pool.get('product.category').get_child_ids(cr,uid,ids,'KPB4')
            elif type == 'KPB' and kpb_ke == '4' and categ_id == 'Sparepart':
                categ_ids = self.pool.get('product.category').get_child_ids(cr,uid,ids,'')
            elif type == 'CLA' and  categ_id == 'Service':
                categ_ids = self.pool.get('product.category').get_child_ids(cr,uid,ids,'CLA')
            elif type == 'CLA' and  categ_id == 'Sparepart':
                categ_ids = self.pool.get('product.category').get_child_ids(cr,uid,ids,'Sparepart')
            elif type == 'SLS' and  categ_id == 'Sparepart':
                categ_ids = self.pool.get('product.category').get_child_ids(cr,uid,ids,'Sparepart')
            elif type == 'SLS' and  categ_id == 'Service':
                categ_ids = self.pool.get('product.category').get_child_ids(cr,uid,ids,'')   
            else :
                categ_ids = self.pool.get('product.category').get_child_ids(cr,uid,ids,categ_id)
            return categ_ids   
        
    def get_location_ids(self,cr,uid,ids,branch_id,context=None):
        query = """
        SELECT
            q.location_id
        FROM
            stock_quant q
        LEFT JOIN
            stock_location loc on q.location_id=loc.id
        WHERE
            q.product_id = %s and q.qty > 0 and q.reservation_id is Null and q.consolidated_date is not Null
            and loc.branch_id=%s and loc.usage='internal'
        
        """ % (ids,branch_id)
        
        #quants_ids = self.pool.get('stock.quant').search(cr,uid,['&',('product_id','in',ids),('qty','>',0.0),('reservation_id','=',False)])
        #loc_ids = self.pool.get('stock.quant').read(cr, uid, quants_ids, ['location_id'])
        cr.execute (query)
        ress = cr.fetchall()
        return [res[0] for res in ress]
   
    # def _get_default_product(self, cr, uid, context=None):
    #     res = self.pool.get('product.product').search(cr, uid, [('product_id','=','65932')], context=context)
    #     return res and res[0] or False

    _columns = {
        'name': fields.text('Description'),
        'name_show':fields.function(_get_name,string='Description', type='char'),
        'work_order_id': fields.many2one('wtc.work.order', 'Work Order', ondelete='cascade'),
        'categ_id':fields.selection([('Sparepart','Sparepart'),('Service','Service')],'Category',required=True),

        'product_id': fields.many2one('product.product','Product',required=True),

        'product_qty': fields.float('Qty', digits_compute=dp.get_precision('Product UoM')),
        'product_uom': fields.many2one('product.uom', 'UoM'),
        'supply_qty':fields.float('Spl Qty'),
        'supply_qty_show':fields.function(_get_supply_qty,string='Spl Qty'),
        'location_id': fields.many2one('stock.location','Location'),
        'discount':fields.float('Disc'),
        'price_unit_show':fields.function(_get_price,string='Unit Price'),
        'price_unit': fields.float('Unit Price', required=True ),#digits_compute= dp.get_precision('Product Price') , states={'draft': [('readonly', False)]}),
        'price_subtotal': fields.function(_amount_line, string='Subtotal', digits_compute= dp.get_precision('Account')),
        'tax_id': fields.many2many('account.tax', 'work_order_tax', 'order_line_id', 'tax_id', 'Taxes'),#states={'draft': [('readonly', False)]}),
        'warranty':fields.float('Warranty'),
        'warranty_show':fields.function(_get_warranty,string='Warranty'),
        'invoiced': fields.boolean('Invoiced', readonly=True, copy=False),
        'qty_available':fields.float('Qty Avb'),
        'qty_available_show':fields.function(_get_qty_available,string='Qty Avb'),
        'state':fields.selection([('cancel','Cancelled'),('draft','Draft'),('confirmed','Confirmed'),('open','Open'),('done','Done')],required=True,readonly=True,copy=False),
        'tax_id_show': fields.many2many('account.tax', 'work_order_tax', 'order_line_id', 'tax_id', 'Taxes'),#states={'draft': [('readonly', False)]}),
   
    }
    
    _defaults = {
        'product_qty': 1,
        'supply_qty':0,
        'warranty':0.0,
        'state':'draft',
        # 'product_id':_get_default_product,
    }

    


    def change_tax(self,cr,uid,ids,tax_id,context=None):
        return {'value':{'tax_id_show':tax_id}}
    
    def location_change(self, cr, uid, ids, location_id,product_id,categ_id,branch_id):
        qty=0.00
        res2={}
        warning = {}
        if categ_id == 'Sparepart' :
            object_loc=self.pool.get('stock.quant').search(cr,uid,[('location_id','=',location_id),('product_id','=',product_id),('reservation_id','=',False),('consolidated_date','!=',False)])
            if object_loc :
                quant = self.pool.get('stock.quant').browse(cr,uid,object_loc)
                for line in quant :
                    qty +=line.qty
            if int(qty) <= 0:
                warning = {'title':'Perhatian !','message':'Qty Avb Product tidak mencukupi !'} 
                res2 = {'location_id':False,'qty_available':0}
            else:
                res2 = {'qty_available':qty }
        if location_id:
            if not product_id or not categ_id:
                res2 = {'location_id':False,'qty_available':0}
                warning = {'title':'Perhatian !','message':'Silahkan pilih category dan product terlebih dahulu !'} 

            loc_obj = self.pool.get('stock.location').browse(cr,uid,location_id)
            if loc_obj.branch_id.id != branch_id or loc_obj.usage != 'internal':
                res2 = {'location_id':False,'qty_available':0}
                warning = {'title':'Perhatian !','message':'Pilih location yang sesuai !'} 

        return  {'value': res2,'warning':warning}  

    def product_change(self, cr, uid, ids, product_id, categ_id,branch_id, product_unit_id,kpb_ke,type):
        harga_jasa= self._get_harga_jasa(cr, uid, ids,product_id,branch_id,product_unit_id)
        if product_id and categ_id == "Service":
            if harga_jasa <=0:
                return {'value':{'name': False, 
                           'product_uom': False,
                           'price_unit': False,
                           'warranty': False,
                           'tax_id': False,
                           'tax_id_show': False,
                           'categ_id': False,
                           'product_id': False,
                           'location_id': False,
                           'product_qty': False,
                           'discount': False,
                           },
                    'warning':{'title':'Perhatian!','message':'Harga jasa tidak boleh 0'}
                    }
            obj_product = self.pool.get('product.product').browse(cr, uid, product_id)
            res = {'name': obj_product.description, 
                   'product_uom': obj_product.uom_id.id,
                   'price_unit': harga_jasa,
                   'warranty': obj_product.warranty,
                   'tax_id': obj_product.taxes_id,
                   'tax_id_show': obj_product.taxes_id
                   }
            return  {'value': res}
        else :
            obj_product = self.pool.get('product.product').browse(cr, uid, product_id)
            obj_peoduct_motor=self.pool.get('product.product').browse(cr, uid, product_unit_id)
            branch = self.pool.get('wtc.branch').browse(cr,uid,branch_id)
            pricelist = branch.pricelist_part_sales_id.id
            if obj_product :
                if type == 'KPB' and kpb_ke == '1' :
                    price=0
                    obj_categ_service1=self.pool.get('wtc.category.product.service').search(cr,uid,[('category_product_id','=',obj_peoduct_motor.category_product_id.id),('product_id','=',obj_product.id)])
                    price=self.pool.get('wtc.category.product.service').browse(cr,uid,obj_categ_service1).price
                else :
                    price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist], obj_product.id, 1,0)[pricelist]
                    
                res = {'name': obj_product.description,
                       'product_uom': obj_product.uom_id.id,
                       'price_unit': price,
                       'warranty': 0.0,
                       'tax_id': obj_product.taxes_id,
                       'tax_id_show': obj_product.taxes_id
                       }
                
                # domain = {'location_id': "[('id','in',"+str(obj_product.get_location_ids())+"),('branch_id','=',"+str(branch_id)+"),('usage','=','internal')]" }   

                domain = {'location_id': "[('id','in',"+str(self.get_location_ids(cr,uid,product_id,branch_id))+")]"  }   
                return  {'value': res, 'domain': domain}
        return True

    def category_change(self, cr, uid, ids, categ_id,type,kpb_ke,branch_id,division,product_unit_id):
        if not branch_id or not division:
            raise osv.except_osv(_('No Branch Defined!'), _('Sebelum menambah detil transaksi,\n harap isi branch dan division terlebih dahulu.'))
        if not type:
            raise osv.except_osv(_('Warning!'), _('Sebelum menambah detil transaksi,\n harap isi type.'))
        if type != 'SLS':
            if not product_unit_id:
                raise osv.except_osv(_('Warning!'), _('Sebelum menambah detil transaksi,\n harap isi Product.'))

        kategory_workshop = self.pool.get('wtc.branch').browse(cr, uid, branch_id)
        check_kategory_branch=kategory_workshop.workshop_category.id
        if not check_kategory_branch:
            raise osv.except_osv(('Warning !'), ("Cabang tersebut belum dipilih Kategori Workshopnya, Silahkan setting di branch"))
        price_list= self._get_price_list(cr, uid, ids,branch_id)
        if not price_list :
            raise osv.except_osv(('No Sale Pricelist Defined !'), ("Sebelum menambah detil transaksi,\n harap set pricelist terlebih dahulu di Branch Configuration."))
        dom = {}
        product_obj = self.pool.get('product.product')
        product_id = product_obj.browse(cr, uid, product_unit_id)
        if type == 'KPB' and kpb_ke == '1' and not product_id.category_product_id.id :
            raise osv.except_osv(('Perhatian !'), ("Silahkan isi 'Category Service' di master Product utk product '%s' !" %product_id.name))
        
        if type == 'KPB' and kpb_ke == '1' and categ_id == 'Sparepart' :
            ids_product = []
            categ_obj = self.pool.get('product.category')
            categ_product_service_obj = self.pool.get('wtc.category.product.service')
            id_categ = categ_obj.search(cr, uid, [('name','=','OIL')])
            ids_categ_product_service = categ_product_service_obj.search(cr, uid, [('category_product_id','=',product_id.category_product_id.id)])
            categ_product_service_ids = categ_product_service_obj.browse(cr, uid, ids_categ_product_service)
            for categ_product_service in categ_product_service_ids :
                ids_product.append(categ_product_service.product_id.id)
            dom['product_id']=[('id','in',ids_product)]
        else : 
            categ_ids= self._get_product(cr, uid, ids,categ_id,type,kpb_ke)
            dom['product_id']=[('categ_id','in',categ_ids)] 
            dom['location_id']=[('id','=',0)]
        return {'domain':dom}
    
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for rec in self.browse(cr, uid, ids, context=context):
            if rec.state not in ['draft']:
                raise osv.except_osv(_('Invalid Action!'), _('Cannot delete a record which is in state \'%s\'.') %(rec.state,))
        return super(wtc_work_order_line, self).unlink(cr, uid, ids, context=context)

    
class stock_move(osv.osv):
    _inherit = 'stock.move'
    _columns = {
        'work_order_line_id': fields.many2one('wtc.work.order.line',
            'Work Order Order Line', ondelete='set null', select=True,
            readonly=True),
    }

    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = super(stock_move, self).write(cr, uid, ids, vals, context=context)
        from openerp import workflow
        for move in self.browse(cr, uid, ids, context=context):
                if move.work_order_line_id and move.work_order_line_id.work_order_id: 
                    work_order_id = move.work_order_line_id.work_order_id.id 
                    if self.pool.get('wtc.work.order').test_moves_done(cr, uid, [work_order_id], context=context):
                        workflow.trg_validate(uid, 'wtc.work.order', work_order_id, 'picking_done', cr)
                        self.pool.get('wtc.work.order').write(cr, uid,work_order_id, {'type_wo': 2}, context=context)
                        self.pool.get('wtc.work.order.line').write(cr, uid,move.work_order_line_id.id, {'state': 'done'}, context=context)
                    if self.pool.get('wtc.work.order').test_moves_except(cr, uid, [work_order_id], context=context):
                       workflow.trg_validate(uid, 'wtc.work.order', work_order_id, 'picking_cancel', cr)
        return res
    
class wtc_stock_picking_wo(osv.osv):
    _inherit = 'stock.picking'
    
    def transfer(self, cr, uid, picking, context=None):
        res = super(wtc_stock_picking_wo, self).transfer(cr, uid, picking, context=context)
        if picking.picking_type_id.code == 'outgoing' and picking.model_id.model == 'wtc.work.order' :
            obj_order = self.pool.get('wtc.work.order').browse(cr, uid, picking.transaction_id)
            qty = {}
            for x in picking.move_lines :
                for y in obj_order.work_lines :
                    if x.work_order_line_id.id == y.id :
                        supplied_qty = y.supply_qty + x.product_uom_qty
                        y.write({'supply_qty':supplied_qty})
                        continue

        if picking.picking_type_id.code == 'incoming' and picking.model_id.model == 'wtc.work.order' :
            obj_order = self.pool.get('wtc.work.order').browse(cr, uid, picking.transaction_id)
            qty = {}
            for x in picking.move_lines :
                for y in obj_order.work_lines :
                    if x.work_order_line_id.id == y.id :
                        supplied_qty = y.supply_qty - x.product_uom_qty
                        y.write({'supply_qty':supplied_qty})
                        continue
        return res
    
    
    

# class invoice(osv.osv):
#     _inherit = 'account.voucher'
#     def _get_branch_id(self, cr, uid, context=None):
#         if context is None: context = {}
#         return context.get('branch_id', False)    
#     _defaults = {
#         'branch_id': _get_branch_id,
#     }    
#       
#    
#   
# class invoice(osv.osv):
#     _inherit = 'account.invoice'
#     def invoice_pay_customer_wo(self, cr, uid, ids, context=None):
#         if not ids: return []
#         dummy, view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account_voucher', 'view_vendor_receipt_dialog_form')
#         inv = self.browse(cr, uid, ids[0], context=context)
#         return {
#             'name':_("Pay Invoice"),
#             'view_mode': 'form',
#             'view_id': view_id,
#             'view_type': 'form',
#             'res_model': 'account.voucher',
#             'type': 'ir.actions.act_window',
#             'nodestroy': True,
#             'target': 'new',
#             'domain': '[]',
#             'context': {
#                 'payment_expected_currency': inv.currency_id.id,
#                 'default_partner_id': self.pool.get('res.partner')._find_accounting_partner(inv.partner_id).id,
#                 'default_amount': inv.type in ('out_refund', 'in_refund') and -inv.residual or inv.residual,
#                 'branch_id': inv.branch_id.id,
#                 'close_after_process': True,
#                 'invoice_type': inv.type,
#                 'invoice_id': inv.id,
#                 'default_type': inv.type in ('out_invoice','out_refund') and 'receipt' or 'payment',
#                 'type': inv.type in ('out_invoice','out_refund') and 'receipt' or 'payment'
#             }
#         }       
#     
#     
    

    

    
