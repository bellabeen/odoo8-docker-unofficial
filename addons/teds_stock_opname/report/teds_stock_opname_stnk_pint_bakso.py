import time
from openerp.osv import osv
from openerp.report import report_sxw
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp.exceptions import except_orm, Warning, RedirectWarning

class teds_so_stnk_print_bakso(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(teds_so_stnk_print_bakso, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'name':self._get_name,
            'branch':self._get_branch,
            'division':self._get_division,
            'tgl_so':self._get_tgl_so,
            'jam_mulai':self._get_jam_mulai,
            'jam_selesai':self._get_jam_selesai,
            'saldo_sistem':self._get_saldo_sistem,
            'saldo_cabang':self._get_saldo_cabang,
            'saldo_ho':self._get_saldo_ho,
            'saldo_md':self._get_saldo_md,
            'saldo_birojasa':self._get_saldo_birojasa,
            'saldo_konsumen':self._get_saldo_konsumen,
            'saldo_lainnya':self._get_saldo_lainnya,
            'selisih_sistem_fisik':self._get_selisih_sistem_fisik,
            'other_stnk':self._get_other_stnk,
            'total_stock':self._get_total_stock,
            'no_urut':self.no_urut,
            'note_bakso':self._get_note_bakso,
            'staff_bbn':self._get_staff_bbn,
            'adh':self._get_adh,
            'soh':self._get_soh,
            'user':self._get_user,
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
    
    def _get_division(self,data):
        return data['division']

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

    def _get_saldo_ho(self,data):
        return data['saldo_ho']

    def _get_saldo_md(self,data):
        return data['saldo_md']

    def _get_saldo_birojasa(self,data):
        return data['saldo_birojasa']

    def _get_saldo_konsumen(self,data):
        return data['saldo_konsumen']

    def _get_saldo_lainnya(self,data):
        return data['saldo_lainnya']

    def _get_selisih_sistem_fisik(self,data):
        return data['selisih_sistem_fisik']
    
    def _get_other_stnk(self,data):
        return data['other_stnk']

    def _get_total_stock(self,data):
        return data['total_stock']
    
    def _get_note_bakso(self,data):
        return data['note_bakso']
    
    def _get_staff_bbn(self,data):
        return data['staff_bbn']
    
    def _get_adh(self,data):
        return data['adh']
    
    def _get_soh(self,data):
        return data['soh']

    def _get_user(self,data):
        return data['user']
    
    def _get_date(self,data):
        return data['date']



class teds_so_stnk_print_bakso_report(osv.AbstractModel):
    _name = 'report.teds_stock_opname.teds_stock_opname_stnk_print_bakso'
    _inherit = 'report.abstract_report'
    _template = 'teds_stock_opname.teds_stock_opname_stnk_print_bakso'
    _wrapped_report_class = teds_so_stnk_print_bakso
