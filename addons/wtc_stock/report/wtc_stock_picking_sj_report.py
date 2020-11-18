import time
from datetime import datetime
from openerp.report import report_sxw
from openerp.osv import osv
from openerp import pooler
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
import pytz 
from openerp.tools.translate import _
import base64

class stock_picking(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(stock_picking, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'no_urut': self.no_urut,
            'waktu_local': self.waktu_local,
            'sale_order': self.sale_order,
            'no_invoice': self.no_invoice,
            'jumlah_cetakan': self.jumlah_cetakan,
            'mutation_order':self.mutation_order
            
            
        })
        
        self.no = 0
    def no_urut(self):
        self.no+=1
        return self.no

    
    def waktu_local(self):
        tanggal = datetime.now().strftime('%y%m%d')
        menit = datetime.now()
        user = self.pool.get('res.users').browse(self.cr, self.uid, self.uid)
        tz = pytz.timezone(user.tz) if user.tz else pytz.utc
        start = pytz.utc.localize(menit).astimezone(tz)
        start_date = start.strftime("%d-%m-%Y %H:%M")
        return start_date
    
    def sale_order(self):
        obj_picking = self.pool.get('stock.picking').browse(self.cr, self.uid, self.ids).origin
        sale_order_search= self.pool.get('dealer.sale.order').search(self.cr, self.uid,[('name','=',obj_picking)])
        sale_order_id = self.pool.get('dealer.sale.order').browse(self.cr, self.uid,sale_order_search)
        return sale_order_id
    
    def mutation_order(self):
         obj_picking = self.pool.get('stock.picking').browse(self.cr, self.uid, self.ids)
         mutation_order=self.pool.get(obj_picking.model_id).sudo().browse(self.cr,self.uid,obj_picking.transaction_id)
         return mutation_order
    
    def jumlah_cetakan(self):
        obj_model = self.pool.get('ir.model')
        obj_model_id = obj_model.search(self.cr, self.uid,[ ('model','=','stock.picking') ])[0]
        obj_ir = self.pool.get('ir.actions.report.xml').search(self.cr, self.uid,[('report_name','=','rml.wtc.stock.picking.sj')])
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
    
    def no_invoice(self):
        obj_picking = self.pool.get('stock.picking').browse(self.cr, self.uid, self.ids).origin
        invoice_search = self.pool.get('account.invoice').search(self.cr, self.uid,[('name','=',obj_picking),('tipe','=','customer')])
        no_invoice = self.pool.get('account.invoice').browse(self.cr, self.uid,invoice_search)
        return no_invoice
    
report_sxw.report_sxw('report.rml.wtc.stock.picking.sj', 'stock.picking', 'addons/wtc_stock/report/wtc_stock_picking_sj_report.rml', parser = stock_picking, header = False)