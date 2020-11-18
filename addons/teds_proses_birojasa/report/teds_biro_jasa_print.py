import time
from openerp.osv import osv
from openerp.report import report_sxw

class ProsesBirojasaPrint(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(ProsesBirojasaPrint, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'no_urut': self.no_urut,
            'tgl':self.get_date,
            'usr':self.get_user,
            'jumlah_cetakan':self.jumlah_cetakan,
            'barcode': self.barcode,
        })

        self.no = 0

    def no_urut(self):
        self.no+=1
        return self.no



    def get_date(self):
        date= self._get_default(self.cr, self.uid, date=True)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        return date

    def get_user(self):
        user = self._get_default(self.cr, self.uid, user=True).name
        return user

    def _get_default(self,cr,uid,date=False,user=False):
        if date :
            return self.pool.get('wtc.branch').get_default_date_model(self.cr, self.uid)
        else :
            return self.pool.get('res.users').browse(self.cr, self.uid, uid)

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

    def barcode(self,data):
        cabang = self.pool.get('wtc.branch').browse(self.cr,self.uid,data['branch_id'][0]).name
        birojasa = self.pool.get('res.partner').browse(self.cr,self.uid,data['partner_id'][0]).name 
        name = data['name']
        tgl = data['tanggal']
        amount = data['amount_total']
        res = "%s|%s|%s|%s|%s" %(str(cabang),str(birojasa),str(name),str(tgl),str(amount)) 
        
        return res
  
class ProsesBirojasaData(osv.AbstractModel):
    _name = 'report.teds_proses_birojasa.teds_proses_birojasa_print'
    _inherit = 'report.abstract_report'
    _template = 'teds_proses_birojasa.teds_proses_birojasa_print'
    _wrapped_report_class = ProsesBirojasaPrint