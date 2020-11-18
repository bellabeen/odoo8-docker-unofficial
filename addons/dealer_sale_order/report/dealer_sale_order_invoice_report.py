import time
from openerp.report import report_sxw
from openerp.osv import osv
from openerp import pooler
import fungsi_terbilang
from datetime import datetime, timedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
import pytz 
from openerp.tools.translate import _
import base64

class dealer_sale_order(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(dealer_sale_order, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'no_urut': self.no_urut,
            'terbilang': self.terbilang,
            'invoice_id': self.invoice_id,
            'hari': self.hari,
            'qty': self.qty,
            'total_pot_harga_jual': self.total_pot_harga_jual,
            'total_pot_harga_jual_bbn': self.total_pot_harga_jual_bbn,
            'waktu_local': self.waktu_local,
            'jumlah_cetakan': self.jumlah_cetakan,
            'price': self.price,
            'cus_stnk': self.cus_stnk,
            
        })
        
        self.no = 0
    def no_urut(self):
        self.no+=1
       
        return self.no
    
    def terbilang(self,amount):
        hasil = fungsi_terbilang.terbilang(amount, "idr", 'id')
        return hasil
    
    def waktu_local(self):
        tanggal = datetime.now().strftime('%y%m%d')
        menit = datetime.now()
        user = self.pool.get('res.users').browse(self.cr, self.uid, self.uid)
        tz = pytz.timezone(user.tz) if user.tz else pytz.utc
        start = pytz.utc.localize(menit).astimezone(tz)
        start_date = start.strftime("%d-%m-%Y %H:%M")
        return start_date

    def jumlah_cetakan(self):
        obj_model = self.pool.get('ir.model')
        obj_model_id = obj_model.search(self.cr, self.uid,[ ('model','=','dealer.sale.order') ])[0]
        obj_ir = self.pool.get('ir.actions.report.xml').search(self.cr, self.uid,[('report_name','=','rml.dealer.sale.order.invoice')])
        obj_ir_id = self.pool.get('ir.actions.report.xml').browse(self.cr, self.uid,obj_ir).id
        obj_jumlah_cetak=self.pool.get('wtc.jumlah.cetak').search(self.cr,self.uid,[('report_id','=',obj_ir_id),('model_id','=',obj_model_id),('transaction_id','=',self.ids[0])])
        if not obj_jumlah_cetak :
            jumlah_cetak_id = {
            'model_id':obj_model_id,
            'transaction_id': self.ids[0],
            'jumlah_cetak': 1,
            'report_id':obj_ir_id                            
            }
            jumlah_cetak=1
            move=self.pool.get('wtc.jumlah.cetak').create(self.cr,self.uid,jumlah_cetak_id)
        else :
            obj_jumalah=self.pool.get('wtc.jumlah.cetak').browse(self.cr,self.uid,obj_jumlah_cetak)
            jumlah_cetak=obj_jumalah.jumlah_cetak+1
            self.pool.get('wtc.jumlah.cetak').write(self.cr, self.uid,obj_jumalah.id, {'jumlah_cetak': jumlah_cetak})
            
        return jumlah_cetak
    
    def hari(self):
        data_1 = self.pool.get('dealer.sale.order').browse(self.cr, self.uid, self.ids).payment_term.id
        data_order = self.pool.get('dealer.sale.order').browse(self.cr, self.uid, self.ids).date_order
        data_2 = self.pool.get('account.payment.term.line').search(self.cr, self.uid,[("payment_id", "=",data_1)])
        data_3 = self.pool.get('account.payment.term.line').browse(self.cr, self.uid, data_2).days
        hasil=data_order
        tgl_start = time.strftime('%Y-%m-%d')
        date_commande= datetime.strptime(data_order, "%Y-%m-%d").date()
        jpt=datetime.strftime(date_commande+timedelta(days=data_3),"%Y-%m-%d")
        return jpt
    
    def qty(self):
        order = self.pool.get('dealer.sale.order.line').search(self.cr, self.uid,[("dealer_sale_order_line_id", "in", self.ids)])
        valbbn=0
        for line in self.pool.get('dealer.sale.order.line').browse(self.cr, self.uid, order) :
            valbbn += line.product_qty
        deadline = datetime.now() - timedelta(days=1)
        return valbbn
    
    def price(self):
        order = self.pool.get('dealer.sale.order.line').search(self.cr, self.uid,[("dealer_sale_order_line_id", "in", self.ids)])
        valprice=0
        for line in self.pool.get('dealer.sale.order.line').browse(self.cr, self.uid, order) :
            valprice += line.price_unit_show
        return valprice

    def cus_stnk(self):
        data_stnk = self.pool.get('dealer.sale.order.line').search(self.cr, self.uid,[("dealer_sale_order_line_id", "in",self.ids)])
        stnk = self.pool.get('dealer.sale.order.line').browse(self.cr, self.uid, data_stnk).partner_stnk_id.id
        name_stnk = self.pool.get('res.partner').browse(self.cr, self.uid, stnk).name
        name_stnk_code = self.pool.get('res.partner').browse(self.cr, self.uid, stnk).default_code
        return name_stnk+' ('+name_stnk_code+')'
    
    def total_pot_harga_jual(self):
        data = self.pool.get('dealer.sale.order').browse(self.cr, self.uid, self.ids)
        order = self.pool.get('dealer.sale.order.line').search(self.cr, self.uid,[("dealer_sale_order_line_id", "in", self.ids)])
        valprice=0
        for line in self.pool.get('dealer.sale.order.line').browse(self.cr, self.uid, order) :
            valprice += line.price_unit_show
        total_pot_tambah_harga_jual=valprice-data.amount_pot-data.amount_ps
        return total_pot_tambah_harga_jual
    
    def total_pot_harga_jual_bbn(self):
        data = self.pool.get('dealer.sale.order').browse(self.cr, self.uid, self.ids)
        order = self.pool.get('dealer.sale.order.line').search(self.cr, self.uid,[("dealer_sale_order_line_id", "in", self.ids)])
        valprice=0
        for line in self.pool.get('dealer.sale.order.line').browse(self.cr, self.uid, order) :
            valprice += line.price_unit_show
        total_pot_tambah_harga_jual_bbn=valprice-data.amount_pot-data.amount_ps
        total_pot_tambah_harga_jual_bbn_fix=total_pot_tambah_harga_jual_bbn+data.amount_bbn
        return total_pot_tambah_harga_jual_bbn_fix
    
    def total_pot_harga_jual_k(self):
        data = self.pool.get('dealer.sale.order').browse(self.cr, self.uid, self.ids)
        total_pot_tambah_harga_jual=data.amount_harga_jual-data.amount_pot-data.amount_ps
        return total_pot_tambah_harga_jual
    
    
    def invoice_id(self):
        invoice = self.pool.get('dealer.sale.order').browse(self.cr, self.uid, self.ids).name
        invoice2 = self.pool.get('account.invoice').search(self.cr, self.uid,[ ('origin','=',invoice),('tipe','=','customer') ])
        no_invoice = self.pool.get('account.invoice').browse(self.cr, self.uid,invoice2).number
        return no_invoice
    
report_sxw.report_sxw('report.rml.dealer.sale.order.invoice', 'dealer.sale.order', 'addons/dealer_sale_order/report/dealer_sale_order_invoice_report.rml', parser = dealer_sale_order, header = False)