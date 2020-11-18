import time
from openerp.osv import osv
from openerp.report import report_sxw
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp.exceptions import except_orm, Warning, RedirectWarning

class teds_so_unit_print_validasi(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(teds_so_unit_print_validasi, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'no_urut':self.no_urut,
            'name':self._get_name,
            'branch':self._get_branch,
            'division':self._get_division,
            'tgl_so':self._get_tgl_so,
            'staff_bbn':self._get_staff_bbn,
            'adh':self._get_adh,
            'soh':self._get_soh,
            'detail_ids': self._get_detail,
            'user':self._get_user,
            'date':self._get_date,
    
        })

        self.no = 0
        self.no_other = 0
    def no_urut(self):
        self.no+=1
        return self.no

    def _get_branch(self,data):
        return data['branch_id']
    
    def _get_name(self,data):
        return data['name']
    
    def _get_division(self,data):
        return data['division']

    def _get_detail(self,data):
        return data['detail_ids']
    
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

    
class teds_so_unit_print_validasi_report(osv.AbstractModel):
    _name = 'report.teds_stock_opname_unit.teds_stock_opname_unit_print_validasi'
    _inherit = 'report.abstract_report'
    _template = 'teds_stock_opname_unit.teds_stock_opname_unit_print_validasi'
    _wrapped_report_class = teds_so_unit_print_validasi
