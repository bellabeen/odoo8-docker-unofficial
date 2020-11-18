import time
from datetime import datetime
from openerp.report import report_sxw
from openerp.osv import osv
from openerp import pooler
# import fungsi_terbilang
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
import pytz 
from openerp.tools.translate import _
import base64

class wtc_faktur_pajak_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(wtc_faktur_pajak_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'waktu_local': self.waktu_local,
            'no_urut':self.no_urut,
            'faktur_name':self.faktur_name,
            'faktur_pajak':self.faktur_pajak,
            'remark':self.remark
        })
        self.no = 0
    
    def faktur_name(self) :
        vals = self.pool.get('wtc.faktur.pajak.out').browse(self.cr,self.uid,self.ids)
        faktur_name = 'FAKTUR PAJAK'
        if vals.pajak_gabungan :
            faktur_name = 'FAKTUR PAJAK GABUNGAN'
        return faktur_name
    
    def remark(self):
        vals = self.pool.get('wtc.faktur.pajak.out').browse(self.cr,self.uid,self.ids)
        invoice = self.pool.get('account.invoice')
        model_id = self.pool.get('wtc.remark').search(self.cr,self.uid,[
                                                                        ('model_id','=',vals.model_id.id)
                                                                        ])
        if not model_id :
            raise osv.except_osv(('Perhatian !'), ("'Model %s tidak ditemukan dalam form Remark, mohon isi terlebih dahulu !")%(vals.model_id.model))
        model_brw = self.pool.get('wtc.remark').browse(self.cr,self.uid,model_id)
        if vals.model_id.model == 'wtc.account.voucher' :
            remark = vals.keterangan
        else :
            remark = model_brw.remark
        if vals.model_id.model == 'wtc.work.order' :
            wo_obj = self.pool.get('wtc.work.order')
            wo_search = wo_obj.browse(self.cr,self.uid,vals.transaction_id)
            inv_wo = invoice.search(self.cr,self.uid,[
                                                      ('origin','=',wo_search.name),
                                                      ('amount_tax','!=',False)
                                                      ])
            if inv_wo :
                invoice_data = invoice.browse(self.cr,self.uid,inv_wo)
                remark += ' ( '+invoice_data.number+' )'
        elif vals.model_id.model == 'dealer.sale.order' :
            ds_obj = self.pool.get('dealer.sale.order')
            ds_search = ds_obj.browse(self.cr,self.uid,vals.transaction_id)
            inv_ds = invoice.search(self.cr,self.uid,[
                                                      ('origin','=',ds_search.name),
                                                      ('amount_tax','!=',False),
                                                      ('tipe','in',('customer','finco'))
                                                      ])
            if inv_ds :
                invoice_data = invoice.browse(self.cr,self.uid,inv_ds)
                for x in invoice_data :
                    remark += ' ( '+str(x.number)+' )'
        return remark
    
    def no_urut(self):
        self.no+=1
        return self.no
    
    def faktur_pajak(self):
        vals = self.pool.get('wtc.faktur.pajak.out').browse(self.cr,self.uid,self.ids)
        obj_model = self.pool.get('ir.model')
        obj_model_id = obj_model.search(self.cr, self.uid,[ ('model','=','wtc.faktur.pajak') ])[0]
        obj_ir = self.pool.get('ir.actions.report.xml').search(self.cr, self.uid,[('report_name','=','rml.faktur_pajak')])
        obj_ir_id = self.pool.get('ir.actions.report.xml').browse(self.cr, self.uid,obj_ir).id                 
        obj_jumlah_cetak=self.pool.get('wtc.jumlah.cetak').search(self.cr,self.uid,[('report_id','=',obj_ir_id),('model_id','=',obj_model_id),('transaction_id','=',self.ids[0])])
        if not obj_jumlah_cetak :
            vals.write({'cetak_ke':1,'state':'print'})
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
            vals.write({'cetak_ke':cetakke,'state':'print'})
            obj_jumalah=self.pool.get('wtc.jumlah.cetak').browse(self.cr,self.uid,obj_jumlah_cetak)
            jumlah_cetak=obj_jumalah.jumlah_cetak+1
            self.pool.get('wtc.jumlah.cetak').write(self.cr, self.uid,obj_jumalah.id, {'jumlah_cetak': jumlah_cetak})  
        cetak = ''
        
        return cetak    
    
    def waktu_local(self):
        obj_voucher = self.pool.get('wtc.account.voucher').browse(self.cr, self.uid, self.ids)
        self.pool.get('wtc.register.kwitansi.line').write(self.cr, self.uid,obj_voucher.kwitansi_id.id,{'state': 'printed','payment_id':obj_voucher.id,'amount':obj_voucher.amount})
        tanggal = datetime.now().strftime('%y%m%d')
        menit = datetime.now()
        user = self.pool.get('res.users').browse(self.cr, self.uid, self.uid)
        tz = pytz.timezone(user.tz) if user.tz else pytz.utc
        start = pytz.utc.localize(menit).astimezone(tz)
        start_date = start.strftime("%d-%m-%Y %H:%M")
        return start_date

    
report_sxw.report_sxw('report.rml.faktur_pajak', 'wtc.faktur.pajak.out', 'addons/wtc_faktur_pajak/report/wtc_faktur_pajak_report.rml', parser = wtc_faktur_pajak_report, header = False)