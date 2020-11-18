import time
from openerp.osv import osv
from openerp.report import report_sxw

class MutasiAssetBaksoPrint(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(MutasiAssetBaksoPrint, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'no_urut': self.no_urut,
            'tgl':self.get_date,
            'usr':self.get_user,
            'branch_sender_name':self.get_branch_sender_name,
            'branch_sender_code':self.get_branch_sender_code,

        })

        self.no = 0

    def no_urut(self):
        self.no+=1
        return self.no

    def get_branch_sender_name(self,data):
        return data['branch_sender_name']

    def get_branch_sender_code(self,data):
        return data['branch_sender_code']
    
    def get_date(self):
        date= self._get_default(self.cr, self.uid, date=True)
        date = date.strftime("%d-%m-%Y")
        return date

    def get_user(self):
        user = self._get_default(self.cr, self.uid, user=True).name
        return user

    def _get_default(self,cr,uid,date=False,user=False):
        if date :
            return self.pool.get('wtc.branch').get_default_date_model(self.cr, self.uid)
        else :
            return self.pool.get('res.users').browse(self.cr, self.uid, uid)
       

class MutasiAssetBaksoReport(osv.AbstractModel):
    _name = 'report.teds_mutasi_asset.berita_acara_mutasi_asset_print'
    _inherit = 'report.abstract_report'
    _template = 'teds_mutasi_asset.berita_acara_mutasi_asset_print'
    _wrapped_report_class = MutasiAssetBaksoPrint