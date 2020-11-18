import time
from datetime import datetime
from openerp.report import report_sxw
from openerp.osv import osv
from openerp import pooler
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
import pytz 
from openerp.tools.translate import _
import base64

class wtc_stock_packing(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(wtc_stock_packing, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'no_urut': self.no_urut,
            'waktu_local': self.waktu_local,
            'qty': self.qty,
            'jumlah_cetakan': self.jumlah_cetakan,
            'mutation_order':self.mutation_order,
            'invoice':self.invoice
            

            
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
    
    
    def mutation_order(self):
        packing_id=self.pool.get('wtc.stock.packing').browse(self.cr, self.uid, self.ids).picking_id.id
        obj_picking = self.pool.get('stock.picking').browse(self.cr, self.uid, packing_id)
        nama_dealer=False
        if obj_picking.origin[0:2] == 'MO' :
            obj_mo=self.pool.get('wtc.mutation.order').search(self.cr,self.uid,[('name','=',obj_picking.origin)])
            obj_mo_browse=self.pool.get('wtc.mutation.order').browse(self.cr,self.uid,obj_mo)
            nama_dealer=obj_mo_browse.sudo().branch_requester_id
        elif obj_picking.origin[0:2] == 'SO' and obj_picking.branch_id.code == 'MML' :
            nama_dealer=obj_picking.partner_id
        elif obj_picking.origin[0:2] == 'SO' and obj_picking.branch_id.code != 'MML' :
            dsl_obj= self.pool.get('dealer.sale.order').search(self.cr, self.uid,[('name','=',obj_picking.origin)])
            dsl=self.pool.get('dealer.sale.order').browse(self.cr, self.uid,dsl_obj)
            nama_dealer=dsl.partner_id
        

#         if obj_picking.model_id.model :
#             if obj_picking.model_id.model == 'wtc.mutation.order' :
#                 mutation_order=self.pool.get(obj_picking.model_id.model).browse(self.cr,self.uid,obj_picking.transaction_id)
#                 nama_dealer=mutation_order.branch_requester_id
#      
#         elif obj_picking.branch_id.code == 'MML' and  obj_picking.partner_id:
#             nama_dealer=obj_picking.partner_id 
#         else :
#             nama_dealer=False
#             dsl_obj= self.pool.get('dealer.sale.order').search(self.cr, self.uid,[('name','=',obj_picking.origin)])
#             dsl=self.pool.get('dealer.sale.order').browse(self.cr, self.uid,dsl_obj)
#             nama_dealer=dsl.partner_id
        return nama_dealer
    
    def invoice(self):
        no_invoice=False
        a=self.pool.get('wtc.stock.packing').browse(self.cr, self.uid, self.ids).picking_id.id
        obj_picking = self.pool.get('stock.picking').browse(self.cr, self.uid, a)
        obj_inv=self.pool.get('account.invoice').search(self.cr, self.uid,[('origin','=',obj_picking.origin)])
        inv=self.pool.get('account.invoice').browse(self.cr, self.uid,obj_inv).number
        no_invoice=inv
        return no_invoice
    
    def jumlah_cetakan(self):
        obj_model = self.pool.get('ir.model')
        obj_model_id = obj_model.search(self.cr, self.uid,[ ('model','=','wtc.stock.packing') ])[0]
        obj_ir = self.pool.get('ir.actions.report.xml').search(self.cr, self.uid,[('report_name','=','rml.wtc.stock.packing.surat.jalan')])
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
    
    
    
    def qty(self):
        order = self.pool.get('wtc.stock.packing.line').search(self.cr, self.uid,[("packing_id", "in", self.ids)])
        valbbn=0
        for line in self.pool.get('wtc.stock.packing.line').browse(self.cr, self.uid, order) :
            valbbn += line.quantity
        return valbbn

    
report_sxw.report_sxw('report.rml.wtc.stock.packing.surat.jalan', 'wtc.stock.packing', 'addons/wtc_stock/report/wtc_stock_surat_jalan_report.rml', parser = wtc_stock_packing, header = False)