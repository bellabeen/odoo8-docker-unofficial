import time
from openerp.osv import osv
from openerp.report import report_sxw

class penerimaan_bpkb(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(penerimaan_bpkb, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'no_urut': self.no_urut,
            'tgl':self.get_date,
            'usr':self.get_user,
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
       

class report_penerimaan_bpkb(osv.AbstractModel):
    _name = 'report.wtc_proses_stnk.wtc_penerimaan_bpkb_report'
    _inherit = 'report.abstract_report'
    _template = 'wtc_proses_stnk.wtc_penerimaan_bpkb_report'
    _wrapped_report_class = penerimaan_bpkb

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
