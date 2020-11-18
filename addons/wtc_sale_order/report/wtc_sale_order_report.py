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


class wtc_sale_order(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(wtc_sale_order, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'no_urut': self.no_urut,
            'waktu_local': self.waktu_local,
            'terbilang': self.terbilang,
            'hari': self.hari,
            'invoice' :self.invoice,
            'jumlah_cetakan': self.jumlah_cetakan,
            
        })
        
        self.no = 0
    def no_urut(self):
        self.no+=1
        return self.no
    
    def time_date(self):
        tangal=time.strftime('%Y-%m-%d %H:%M:%S')
        return tangal
    
    def hari(self):
        data_1 = self.pool.get('sale.order').browse(self.cr, self.uid, self.ids)
        data_order = data_1.invoice_ids.date_invoice
        data_2 = self.pool.get('account.payment.term.line').search(self.cr, self.uid,[("payment_id", "=",data_1.payment_term.id)])
        data_3 = self.pool.get('account.payment.term.line').browse(self.cr, self.uid, data_2).days
        a=data_order[:10]
        date_commande= datetime.strptime(a, "%Y-%m-%d").date()
        jpt=datetime.strftime(date_commande+timedelta(days=data_3),"%Y-%m-%d")
        bulan = str(jpt[5:7])
        tanggal = str(jpt[8:10])
        tahun = str(jpt[:4])
        new_date = tanggal+'-'+bulan+'-'+tahun

        return new_date
    
    def invoice(self):
        obj_sale_order = self.pool.get('sale.order').browse(self.cr, self.uid, self.ids)
        #obj_inv=self.pool.get(obj_sale_order.model_id.model).browse(self.cr, self.uid, self.ids,obj_sale_order.transaction_id)
        name_invoice=obj_sale_order.invoice_ids
        #name_invoice=obj_inv.name
        return name_invoice

    
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
        obj_model_id = obj_model.search(self.cr, self.uid,[ ('model','=','sale.order') ])[0]
        obj_ir = self.pool.get('ir.actions.report.xml').search(self.cr, self.uid,[('report_name','=','rml.sale.order')])
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
    
    
    def terbilang(self,amount):
        hasil = fungsi_terbilang.terbilang(amount, "idr", 'id')
        return hasil
    

    

    
report_sxw.report_sxw('report.rml.sale.order', 'sale.order', 'addons/wtc_sale_order/report/wtc_sale_order_report.rml', parser = wtc_sale_order, header = False)