import time
from openerp.osv import osv
from openerp.report import report_sxw
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp.exceptions import except_orm, Warning, RedirectWarning

class teds_so_asset_print_bakso(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(teds_so_asset_print_bakso, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'name':self._get_name,
            'branch':self._get_branch,
            'tgl_so':self._get_tgl_so,
            'jam_mulai':self._get_jam_mulai,
            'jam_selesai':self._get_jam_selesai,
            'saldo_sistem':self._get_saldo_sistem,
            'saldo_cabang':self._get_saldo_cabang,
            'saldo_pic':self._get_saldo_pic,
            'saldo_hilang':self._get_saldo_hilang,
            'saldo_tidak_ada':self._get_saldo_tidak_ada,
            'other_asset':self._get_other_asset,
            'total_stock':self._get_total_stock,
            'note_bakso':self._get_note_bakso,
            'pdi':self._get_pdi,
            'adh':self._get_adh,
            'soh':self._get_soh,
            'user': self._get_user,
            'date':self._get_date,

        })
        self.no = 0
    def no_urut(self):
        self.no+=1
        return self.no

    def _get_branch(self,data):
        return data['branch']
    
    def _get_name(self,data):
        return data['name']
    
    def _get_tgl_so(self,data):
        return data['tgl_so']

    def _get_jam_mulai(self,data):
        return data['jam_mulai']

    def _get_jam_selesai(self,data):
        return data['jam_selesai']

    def _get_saldo_sistem(self,data):
        return data['saldo_sistem']

    def _get_saldo_cabang(self,data):
        return data['saldo_cabang']

    def _get_saldo_pic(self,data):
        return data['saldo_pic']

    def _get_saldo_hilang(self,data):
        return data['saldo_hilang']

    def _get_saldo_tidak_ada(self,data):
        return data['saldo_tidak_ada']

    def _get_other_asset(self,data):
        return data['other_asset']

    def _get_total_stock(self,data):
        return data['total_stock']
    
    def _get_note_bakso(self,data):
        return data['note_bakso']
    
    def _get_pdi(self,data):
        return data['pdi']
    
    def _get_adh(self,data):
        return data['adh']
    
    def _get_soh(self,data):
        return data['soh']

    def _get_user(self,data):
        return data['user']
    
    def _get_date(self,data):
        return data['date']



class teds_so_asset_print_bakso_report(osv.AbstractModel):
    _name = 'report.teds_stock_opname_asset.teds_stock_opname_asset_print_bakso'
    _inherit = 'report.abstract_report'
    _template = 'teds_stock_opname_asset.teds_stock_opname_asset_print_bakso'
    _wrapped_report_class = teds_so_asset_print_bakso
