import time
from datetime import datetime
from openerp.report import report_sxw
from openerp.osv import osv
from openerp import pooler
import fungsi_terbilang
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
import pytz 
from openerp.tools.translate import _
import base64

class wtc_kwitansi_account_voucher(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(wtc_kwitansi_account_voucher, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'terbilang': self.terbilang,
            'waktu_local': self.waktu_local,
            'original':self.original,
            'kwitansi':self.kwitansi

        })
        self.no = 0
    
    def no_urut(self):
        self.no+=1
        return self.no
    
    def kwitansi(self):
        vals = self.pool.get('wtc.account.voucher').browse(self.cr,self.uid,self.ids)
        move_line = self.pool.get('account.move.line').search(self.cr,self.uid,[
                                                                                ('move_id','=',vals.move_id.id),
                                                                                ('debit','!=',False)
                                                                                ])
        move_line_brw = self.pool.get('account.move.line').browse(self.cr,self.uid,move_line)
        for x in move_line_brw :
            self.pool.get('account.move.line').write(self.cr, self.uid,x.id, {'kwitansi': 1,'kwitansi_id':vals.kwitansi_id.id}) 
        
        kwitansi = self.pool.get('wtc.register.kwitansi.line').search(self.cr,self.uid,[
                                                                                        ('new_payment_id','=',vals.id),
                                                                                        ('state','=','printed'),
                                                                                        ('reason','=',False)
                                                                                        ])
        if kwitansi :
            prev_kwitansi = self.pool.get('wtc.register.kwitansi.line').browse(self.cr,self.uid,kwitansi)
            for x in prev_kwitansi :        
                self.pool.get('wtc.register.kwitansi.line').write(self.cr,self.uid,x.id,{'state':'cancel','reason':str(vals.reason_cancel_kwitansi)})
        self.pool.get('wtc.register.kwitansi.line').write(self.cr, self.uid,vals.kwitansi_id.id, {
                                                                                                  'new_payment_id':vals.id,                                                                                                 
                                                                                                  'state':'printed'
                                                                                                  }) 
        
        obj_model = self.pool.get('ir.model')
        obj_model_id = obj_model.search(self.cr, self.uid,[ ('model','=','wtc.account.voucher') ])[0]
        obj_ir = self.pool.get('ir.actions.report.xml').search(self.cr, self.uid,[('report_name','=','rml.wtc.kwitansi')])
        obj_ir_id = self.pool.get('ir.actions.report.xml').browse(self.cr, self.uid,obj_ir).id                 
        obj_jumlah_cetak=self.pool.get('wtc.jumlah.cetak').search(self.cr,self.uid,[('report_id','=',obj_ir_id),('model_id','=',obj_model_id),('transaction_id','=',self.ids[0])])
        
        if not obj_jumlah_cetak :
            vals.write({'cetak_ke':1,'reason_cancel_kwitansi':False})
            jumlah_cetak_id = {
            'model_id':obj_model_id,
            'transaction_id': self.ids[0],
            'jumlah_cetak': 1,
            'report_id':obj_ir_id                            
            }
            jumlah_cetak=1
            move=self.pool.get('wtc.jumlah.cetak').create(self.cr,self.uid,jumlah_cetak_id)
        else :
            cetakke = vals.cetak_ke+1
            vals.write({'cetak_ke':cetakke,'reason_cancel_kwitansi':False})
            obj_jumalah=self.pool.get('wtc.jumlah.cetak').browse(self.cr,self.uid,obj_jumlah_cetak)
            jumlah_cetak=obj_jumalah.jumlah_cetak+1
            self.pool.get('wtc.jumlah.cetak').write(self.cr, self.uid,obj_jumalah.id, {'jumlah_cetak': jumlah_cetak})  
        cetak = ''
        return cetak    
    
    def terbilang(self,amount):
        hasil = fungsi_terbilang.terbilang(amount, "idr", 'id')        
        return hasil
    
    def waktu_local(self):
        obj_voucher = self.pool.get('wtc.account.voucher').browse(self.cr, self.uid, self.ids)
        self.pool.get('wtc.register.kwitansi.line').write(self.cr, self.uid,obj_voucher.kwitansi_id.id,{'state': 'printed','new_payment_id':obj_voucher.id,'amount':obj_voucher.amount})
        tanggal = datetime.now().strftime('%y%m%d')
        menit = datetime.now()
        user = self.pool.get('res.users').browse(self.cr, self.uid, self.uid)
        tz = pytz.timezone(user.tz) if user.tz else pytz.utc
        start = pytz.utc.localize(menit).astimezone(tz)
        start_date = start.strftime("%d-%m-%Y %H:%M")
        return start_date
    
    def original(self):
        obj_voucher = self.pool.get('wtc.account.voucher').browse(self.cr, self.uid, self.ids)
        if obj_voucher.type == 'sale':
            origin = obj_voucher.reference or obj_voucher.number
        else :
            origin = obj_voucher.origin or obj_voucher.number
        return origin

    
report_sxw.report_sxw('report.rml.wtc.kwitansi', 'wtc.account.voucher', 'addons/wtc_account_voucher/report/wtc_kwitansi.rml', parser = wtc_kwitansi_account_voucher, header = False)