import time
from openerp.osv import osv
from openerp.report import report_sxw
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp.exceptions import except_orm, Warning, RedirectWarning

class teds_so_dg_print_validasi(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(teds_so_dg_print_validasi, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'name':self._get_name,
            'branch':self._get_branch,
            'division':self._get_division,
            'tgl_so':self._get_tgl_so,
            'staff_bbn':self._get_staff_bbn,
            'adh':self._get_adh,
            'soh':self._get_soh,
            'detail_ids': self._get_detail,
            'other_dg_ids':self._get_dg_other,
            'no_urut':self.no_urut,
            'no_urut_other': self.no_urut_other,
            'user':self._get_user,
            'date':self._get_date,
            'tot_qty':self._get_tot_qty,
            'tot_amount':self._get_tot_amount,
            'tot_qty_fisik_baik':self._get_tot_qty_fisik_baik,
            'tot_qty_fisik_rusak':self._get_tot_qty_fisik_rusak,
            'tot_qty_fisik_total':self._get_tot_qty_fisik_total,
            'tot_amount_total':self._get_tot_amount_total,
            'tot_selisih_qty':self._get_tot_selisih_qty,
            'tot_selisih_amount':self._get_tot_selisih_amount,
            'tot_saldo_log_book':self._get_tot_saldo_log_book,
            'tot_other_baik':self._get_tot_other_baik,
            'tot_other_rusak':self._get_tot_other_rusak,
            'tot_other_total':self._get_tot_other_total,
            'tot_other_log_book':self._get_tot_other_log_book,
    
        })

        self.no = 0
        self.no_other = 0
    def no_urut(self):
        self.no+=1
        return self.no

    def no_urut_other(self):
        self.no_other+=1
        return self.no_other


    def _get_branch(self,data):
        return data['branch_id']
    
    def _get_name(self,data):
        return data['name']
    
    def _get_division(self,data):
        return data['division']

    def _get_detail(self,data):
        return data['detail_ids']
    
    def _get_dg_other(self,data):
        return data['other_dg_ids']

    def _get_tgl_so(self,data):
        return data['tgl_so']

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

    def _get_tot_qty(self,data):
        return data['tot_qty']
    def _get_tot_amount(self,data):
        return data['tot_amount']
    def _get_tot_qty_fisik_baik(self,data):
        return data['tot_qty_fisik_baik']
    def _get_tot_qty_fisik_rusak(self,data):
        return data['tot_qty_fisik_rusak']
    def _get_tot_qty_fisik_total(self,data):
        return data['tot_qty_fisik_total']
    def _get_tot_amount_total(self,data):
        return data['tot_amount_total']
    def _get_tot_selisih_qty(self,data):
        return data['tot_selisih_qty']
    def _get_tot_selisih_amount(self,data):
        return data['tot_selisih_amount']
    def _get_tot_saldo_log_book(self,data):
        return data['tot_saldo_log_book']
    def _get_tot_other_baik(self,data):
        return data['tot_other_baik']
    def _get_tot_other_rusak(self,data):
        return data['tot_other_rusak']
    def _get_tot_other_total(self,data):
        return data['tot_other_total']
    def _get_tot_other_log_book(self,data):
        return data['tot_other_log_book']

class teds_so_dg_print_validasi_report(osv.AbstractModel):
    _name = 'report.teds_stock_opname_direct_gift.teds_stock_opname_dg_print_validasi'
    _inherit = 'report.abstract_report'
    _template = 'teds_stock_opname_direct_gift.teds_stock_opname_dg_print_validasi'
    _wrapped_report_class = teds_so_dg_print_validasi