import time
from datetime import datetime
from openerp.report import report_sxw
from openerp.osv import osv
from openerp import pooler
#import fungsi_terbilang
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
import pytz 
from openerp.tools.translate import _
import base64

class wtc_proses_birojasa(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(wtc_proses_birojasa, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'waktu_local': self.waktu_local,
            'waktu_local': self.waktu_local,
            'koreksi': self.koreksi,
            'prog': self.prog,
            'total': self.total,
            'total_bbn': self.total_bbn,
            'jumlah_cetakan': self.jumlah_cetakan,
            
            
        })
        
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
        obj_model_id = obj_model.search(self.cr, self.uid,[ ('model','=','wtc.proses.birojasa') ])[0]
        obj_ir = self.pool.get('ir.actions.report.xml').search(self.cr, self.uid,[('report_name','=','rml.proses.birojasa')])
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
    
    def koreksi(self):
        order = self.pool.get('wtc.proses.birojasa.line').search(self.cr, self.uid,[("proses_biro_jasa_id", "in", self.ids)])
        tot_koreksi=0
        for line in self.pool.get('wtc.proses.birojasa.line').browse(self.cr, self.uid, order) :
            tot_koreksi += line.koreksi
        return tot_koreksi
    
    def prog(self):
        order = self.pool.get('wtc.proses.birojasa.line').search(self.cr, self.uid,[("proses_biro_jasa_id", "in", self.ids)])
        tot_prog=0
        for line in self.pool.get('wtc.proses.birojasa.line').browse(self.cr, self.uid, order) :
            tot_prog += line.pajak_progressive
        return tot_prog
    
    def total(self):
        order = self.pool.get('wtc.proses.birojasa.line').search(self.cr, self.uid,[("proses_biro_jasa_id", "in", self.ids)])
        tot_tagihan=0
        for line in self.pool.get('wtc.proses.birojasa.line').browse(self.cr, self.uid, order) :
            tot_tagihan += line.total_tagihan
        return tot_tagihan
    
    def total_bbn(self):
        order = self.pool.get('wtc.proses.birojasa.line').search(self.cr, self.uid,[("proses_biro_jasa_id", "in", self.ids)])
        tot_bbn=0
        for x in self.pool.get('wtc.proses.birojasa.line').browse(self.cr, self.uid, order) :
           tot_bbn +=  x.name.invoice_bbn.invoice_line.price_subtotal
        return tot_bbn
 
report_sxw.report_sxw('report.rml.proses.birojasa', 'wtc.proses.birojasa', 'addons/wtc_proses_stnk/report/wtc_proses_birojasa_report.rml', parser = wtc_proses_birojasa, header = False)