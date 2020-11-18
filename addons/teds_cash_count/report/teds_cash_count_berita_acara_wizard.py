import time
from openerp.osv import osv
from openerp.report import report_sxw
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp.exceptions import except_orm, Warning, RedirectWarning

class teds_cash_count_print_berita_acara(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(teds_cash_count_print_berita_acara, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'name':self._get_name,
            'branch':self._get_branch,
            'lokasi':self._get_lokasi,
            'tanggal':self._get_tanggal,
            'saldo_fisik_cash':self._get_saldo_fisik_cash,
            'cash_detail':self._get_cash_detail,
            'plafon_petty_cash_sr':self._get_plafon_petty_cash_sr,
            'saldo_sistem_petty_cash_sr':self._get_saldo_sistem_petty_cash_sr,
            'saldo_fisik_petty_cash_sr':self._get_saldo_fisik_petty_cash_sr,
            'saldo_pc_sr':self._get_saldo_pc_sr,
            'saldo_pc_ws':self._get_saldo_pc_ws,
            'saldo_pc_atl_btl':self._get_saldo_pc_atl_btl,
            'selisih_petty_cash_sr':self._get_selisih_petty_cash_sr,
            'saldo_sistem_reimburse_sr':self._get_saldo_sistem_reimburse_sr,
            'petty_cash_sr_detail':self._get_petty_cash_sr_detail,
            'reimburse_petty_cash_sr_detail':self._get_reimburse_petty_cash_sr_detail,
            'plafon_petty_cash_ws':self._get_plafon_petty_cash_ws,
            'saldo_sistem_petty_cash_ws':self._get_saldo_fisik_petty_cash_ws,
            'saldo_fisik_petty_cash_ws':self._get_saldo_fisik_petty_cash_ws,
            'selisih_petty_cash_ws':self._get_selisih_petty_cash_ws,
            'saldo_sistem_reimburse_ws':self._get_saldo_sistem_reimburse_ws,
            'petty_cash_ws_detail':self._get_petty_cash_ws_detail,
            'reimburse_petty_cash_ws_detail':self._get_reimburse_petty_cash_ws_detail,
            'plafon_petty_cash_atl_btl':self._get_plafon_petty_cash_atl_btl,
            'saldo_sistem_petty_cash_atl_btl':self._get_saldo_sistem_petty_cash_atl_btl,
            'saldo_fisik_petty_cash_atl_btl':self._get_saldo_fisik_petty_cash_atl_btl,
            'selisih_petty_cash_atl_btl':self._get_selisih_petty_cash_atl_btl,
            'saldo_sistem_reimburse_atl_btl':self._get_saldo_sistem_reimburse_atl_btl,
            'petty_cash_atl_btl_detail':self._get_petty_cash_atl_btl_detail,
            'reimburse_petty_cash_atl_btl_detail':self._get_reimburse_petty_cash_atl_btl_detail,
            'note':self._get_note,
            'options':self._get_options,
            'kasir':self._get_kasir,
            'admin_pos':self._get_admin_pos,
            'adh':self._get_adh,
            'soh':self._get_soh,
            'total_saldo_sistem_petty_cash_sr':self._get_total_saldo_sistem_petty_cash_sr,
            'total_saldo_sistem_petty_cash_ws':self._get_total_saldo_sistem_petty_cash_ws,
            'total_saldo_sistem_petty_cash_atl_btl':self._get_total_saldo_sistem_petty_cash_atl_btl,
            'total_saldo_fisik':self._get_total_saldo_fisik,
            'saldo_fisik_other':self._get_saldo_fisik_other,
            'other_detail':self._get_other_detail,
            'total_saldo_sistem_all':self._get_total_saldo_sistem_all,
            'no_urut':self.no_urut,
            'create_uid':self._get_create_uid,
            'approved_adh_uid':self._get_approved_adh_uid,
            'approved_soh_uid':self._get_approved_soh_uid,
            'create_date':self._get_create_date,
            'approved_adh_on':self._get_approved_adh_on,
            'approved_soh_on':self._get_approved_soh_on,
        })

        self.no = 0
    def no_urut(self):
        self.no+=1
        return self.no

    def _get_branch(self,data):
        return data['branch']
    
    def _get_name(self,data):
        return data['name']
    
    def _get_lokasi(self,data):
        return data['lokasi']

    def _get_tanggal(self,data):
        return data['tanggal']
    def _get_saldo_fisik_cash(self,data):
        return data['saldo_fisik_cash']
    def _get_cash_detail(self,data):
        return data['cash_detail']
    def _get_plafon_petty_cash_sr(self,data):
        return data['plafon_petty_cash_sr']
    def _get_saldo_sistem_petty_cash_sr(self,data):
        return data['total_saldo_sistem_petty_cash_sr']
    def _get_saldo_fisik_petty_cash_sr(self,data):
        return data['saldo_fisik_petty_cash_sr']
    def _get_saldo_pc_sr(self,data):
        return data['saldo_pc_sr']
    def _get_saldo_pc_ws(self,data):
        return data['saldo_pc_ws']
    def _get_saldo_pc_atl_btl(self,data):
        return data['saldo_pc_atl_btl']
    def _get_selisih_petty_cash_sr(self,data):
        return data['selisih_petty_cash_sr']
    def _get_saldo_sistem_reimburse_sr(self,data):
        return data['saldo_sistem_reimburse_sr']
    def _get_petty_cash_sr_detail(self,data):
        return data['petty_cash_sr_detail']
    def _get_reimburse_petty_cash_sr_detail(self,data):
        return data['reimburse_petty_cash_sr_detail']
    def _get_plafon_petty_cash_ws(self,data):
        return data['plafon_petty_cash_ws']
    def _get_saldo_fisik_petty_cash_ws(self,data):
        return data['saldo_fisik_petty_cash_ws']
    def _get_saldo_fisik_petty_cash_ws(self,data):
        return data['saldo_fisik_petty_cash_ws']
    def _get_selisih_petty_cash_ws(self,data):
        return data['selisih_petty_cash_ws']
    def _get_saldo_sistem_reimburse_ws(self,data):
        return data['saldo_sistem_reimburse_ws']
    def _get_petty_cash_ws_detail(self,data):
        return data['petty_cash_ws_detail']
    def _get_reimburse_petty_cash_ws_detail(self,data):
        return data['reimburse_petty_cash_ws_detail']
    def _get_plafon_petty_cash_atl_btl(self,data):
        return data['plafon_petty_cash_atl_btl']
    def _get_saldo_sistem_petty_cash_atl_btl(self,data):
        return data['saldo_sistem_petty_cash_atl_btl']
    def _get_saldo_fisik_petty_cash_atl_btl(self,data):
        return data['saldo_fisik_petty_cash_atl_btl']
    def _get_selisih_petty_cash_atl_btl(self,data):
        return data['selisih_petty_cash_atl_btl']
    def _get_saldo_sistem_reimburse_atl_btl(self,data):
        return data['saldo_sistem_reimburse_atl_btl']
    def _get_petty_cash_atl_btl_detail(self,data):
        return data['petty_cash_atl_btl_detail']
    def _get_reimburse_petty_cash_atl_btl_detail(self,data):
        return data['reimburse_petty_cash_atl_btl_detail']
    def _get_note(self,data):
        return data['note']
    def _get_options(self,data):
        return data['options']
    def _get_kasir(self,data):
        return data['kasir']
    def _get_admin_pos(self,data):
        return data['admin_pos']
    def _get_adh(self,data):
        return data['adh']
    def _get_soh(self,data):
        return data['soh']
    def _get_total_saldo_sistem_petty_cash_sr(self,data):
        return data['total_saldo_sistem_petty_cash_sr']
    def _get_total_saldo_sistem_petty_cash_ws(self,data):
        return data['total_saldo_sistem_petty_cash_ws']
    def _get_total_saldo_sistem_petty_cash_atl_btl(self,data):
        return data['total_saldo_sistem_petty_cash_atl_btl']
    def _get_total_saldo_fisik(self,data):
        return data['total_saldo_fisik']
    def _get_saldo_fisik_other(self,data):
        return data['saldo_fisik_other']
    def _get_other_detail(self,data):
        return data['other_detail']
    def _get_total_saldo_sistem_all(self,data):
        return data['total_saldo_sistem_all']
    def _get_create_uid(self,data):
        return data['create_uid']
    def _get_approved_adh_uid(self,data):
        return data['approved_adh_uid']
    def _get_approved_soh_uid(self,data):
        return data['approved_soh_uid']
    def _get_create_date(self,data):
        return data['create_date']
    def _get_approved_adh_on(self,data):
        return data['approved_adh_on']
    def _get_approved_soh_on(self,data):
        return data['approved_soh_on']

class teds_cash_count_print_berita_acara_report(osv.AbstractModel):
    _name = 'report.teds_cash_count.teds_cash_count_print_berita_acara'
    _inherit = 'report.abstract_report'
    _template = 'teds_cash_count.teds_cash_count_print_berita_acara'
    _wrapped_report_class = teds_cash_count_print_berita_acara
