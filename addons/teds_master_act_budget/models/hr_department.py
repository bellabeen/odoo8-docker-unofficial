from openerp import api
from openerp.osv import fields, osv, expression

class hr_department(osv.osv):
    _inherit = "hr.department"

    _columns = {
        # 'branch_id': fields.many2one('wtc.branch', string='Dealer'),
        'department_code': fields.char(string='Department Code')
    }

    def _check_dept_code(self, cr, uid, ids, context=None):
        # import ipdb
        # ipdb.set_trace()
        for dept_obj in self.browse(cr, uid, ids, context=context):
            if dept_obj.department_code:
                print dept_obj.department_code
                dept_count = self.search(cr, uid, [
                    ('department_code','=', dept_obj.department_code)
                    # ('branch_id','=', dept_obj.branch_id.id)
                ], context=context, count=True)
                if dept_count > 1:
                    return False
        return True

    _constraints = [
        (_check_dept_code, '\nKode departemen sudah ada.', ['department_code'])
    ]