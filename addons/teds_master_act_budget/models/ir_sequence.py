from openerp import SUPERUSER_ID
from openerp.osv import fields, osv

class wtc_ir_sequence(osv.osv):
    _inherit = 'ir.sequence'

    def get_per_department(self, cr, uid, department_id, prefix, context=None):
        dept_code = self.pool.get('hr.department').browse(cr, uid, department_id).department_code
        seq_name = '{0}/{1}/'.format(prefix, dept_code)

        seq_ids = self.search(cr, uid, [('name','=',seq_name)])
        if not seq_ids:
            # prefix = '/%(y)s/%(month)s/'
            # prefix = seq_name + '/'
            seq_ids = self.create(cr, SUPERUSER_ID, {
                'name': seq_name,
                'implementation': 'standard',
                'prefix': seq_name,
                'padding': 0
            })

        return self.get_id(cr, uid, seq_ids)

    # def get_per_department_st(self, cr, uid, department_id, prefix, context=None):
    #     dept_code = self.pool.get('hr.department').browse(cr, uid, department_id).department_code
    #     seq_name = '{0}/{1}/'.format(prefix, dept_code)

    #     seq_ids = self.search(cr, uid, [('name','=',seq_name)])
    #     if not seq_ids:
    #         prefix = '/%(y)s/%(month)s/'
    #         prefix = seq_name + '/'
    #         seq_ids = self.create(cr, SUPERUSER_ID, {
    #             'name': seq_name,
    #             'implementation': 'standard',
    #             'prefix': prefix,
    #             'padding': 0
    #         })

    #     return self.get_id(cr, uid, seq_ids)