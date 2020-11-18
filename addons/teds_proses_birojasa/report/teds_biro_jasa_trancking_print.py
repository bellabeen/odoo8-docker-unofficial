import time
from openerp.osv import osv
from openerp.report import report_sxw

class ProsesBirojasaTracking(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(ProsesBirojasaTracking, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'tgl':self.get_date,
            'usr':self.get_user,
        })

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

class ProsesBirojasaTrackingData(osv.AbstractModel):
    _name = 'report.teds_proses_birojasa.teds_proses_birojasa_tracking_print'
    _inherit = 'report.abstract_report'
    _template = 'teds_proses_birojasa.teds_proses_birojasa_tracking_print'
    _wrapped_report_class = ProsesBirojasaTracking