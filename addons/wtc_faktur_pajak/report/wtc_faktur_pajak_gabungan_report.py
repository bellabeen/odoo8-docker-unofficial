import time
from openerp.osv import osv
from openerp.report import report_sxw

class faktur_gabungan(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(faktur_gabungan, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'no_urut': self.no_urut,
            'get_total_amount': self._get_total_amount,
            'get_untaxed_amount': self._get_untaxed_amount,
            'get_tax_amount': self._get_tax_amount,
            'get_default': self._get_default,
            'tgl': self.get_date,
        })

        self.no = 0

    def no_urut(self):
        self.no+=1
        return self.no



    def _get_total_amount(self):
        val=self.pool.get('wtc.faktur.pajak.gabungan').browse(self.cr,self.uid,self.ids)
        total_amount=0

        for x in val.pajak_gabungan_line :
            total_amount += x.total_amount

        return total_amount


    def _get_untaxed_amount (self):
        val=self.pool.get('wtc.faktur.pajak.gabungan').browse(self.cr,self.uid,self.ids)
        untaxed_amount=0

        for x in val.pajak_gabungan_line :
            untaxed_amount += x.untaxed_amount

        return untaxed_amount


    def _get_tax_amount (self):
        val=self.pool.get('wtc.faktur.pajak.gabungan').browse(self.cr,self.uid,self.ids)
        tax_amount=0

        for x in val.pajak_gabungan_line :
            tax_amount += x.tax_amount

        return tax_amount

        
    def _get_default(self, data):
        cr=self.cr
        uid=self.uid

        division = data['division']  
    
        if division == 'Unit' :
            string="PENJUALAN SEPEDA MOTOR HONDA (PERINCIAN TERLAMPIR)"
            return string

        elif division == 'Sparepart' :
            string="PENJUALAN SPAREPART HONDA (PERINCIAN TERLAMPIR) "
            return string

   
     
    def get_date(self):
        date= self._get_default_date(self.cr, self.uid, date=True)
        date = date.strftime("%Y-%m-%d")
        return date

    def _get_default_date(self,cr,uid,date=False,user=False):
        if date :
            return self.pool.get('wtc.branch').get_default_date_model(self.cr, self.uid)
       

class report_faktur_gabungan(osv.AbstractModel):
    _name = 'report.wtc_faktur_pajak.wtc_faktur_pajak_gabungan_report'
    _inherit = 'report.abstract_report'
    _template = 'wtc_faktur_pajak.wtc_faktur_pajak_gabungan_report'
    _wrapped_report_class = faktur_gabungan

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
