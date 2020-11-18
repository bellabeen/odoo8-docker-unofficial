import time
from openerp.osv import osv
from openerp.report import report_sxw
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp.exceptions import except_orm, Warning, RedirectWarning

class teds_so_unit_print_bakso(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(teds_so_unit_print_bakso, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'name':self._get_name,
            'branch':self._get_branch,
            'division':self._get_division,
            'tgl_so':self._get_tgl_so,
            'jam_mulai':self._get_jam_mulai,
            'jam_selesai':self._get_jam_selesai,
            'no_urut':self.no_urut,
            'note_bakso':self._get_note_bakso,
            'staff_bbn':self._get_staff_bbn,
            'adh':self._get_adh,
            'soh':self._get_soh,
            'user':self._get_user,
            'date':self._get_date,
            # 'detail_ids':self._get_detail_ids,
            'tabel_1':self._get_table_1,
            'tabel_2':self._get_table_2,
            'tabel_3':self._get_table_3,
            'total_sistem':self._get_total_sistem,
            'total_fisik':self._get_total_fisik,
            'selisih':self._get_selisih,
            'nrfs_ids':self._get_nrfs_ids,
            
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

    # def _get_detail_ids(self,data):
    #     return data['detail_ids']
    
    def _get_table_1(self,data):
        return data['tabel_1']

    def _get_table_2(self,data):
        return data['tabel_2']

    def _get_table_3(self,data):
        return data['tabel_3']

    def _get_total_sistem(self,data):
        return data['total_sistem']
    def _get_total_fisik(self,data):
        return data['total_fisik']
    def _get_selisih(self,data):
        return data['selisih']
    def _get_nrfs_ids(self,data):
        return data['nrfs_ids']

class teds_so_unit_print_bakso_report(osv.AbstractModel):
    _name = 'report.teds_stock_opname_unit.teds_stock_opname_unit_print_bakso'
    _inherit = 'report.abstract_report'
    _template = 'teds_stock_opname_unit.teds_stock_opname_unit_print_bakso'
    _wrapped_report_class = teds_so_unit_print_bakso
