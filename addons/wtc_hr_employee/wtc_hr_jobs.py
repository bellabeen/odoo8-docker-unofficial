from openerp.osv import osv, fields
from openerp.tools.translate import _

class hr_job(osv.osv):
    _inherit = 'hr.job'
    
    _columns = {
        'group_id' : fields.many2one('res.groups',string="Group",domain="[('category_id.name','=','TDM')]"),
        'branch_control' : fields.boolean(string='Branch Control'),
        'sales_force' : fields.selection([('salesman','Salesman'),('sales_counter','Sales Counter'),('sales_partner','Sales Partner')
                        ,('sales_koordinator','Sales Koordinator'),('soh','SOH'),('AM','Area Manager'),('mechanic','Mechanic')], string='Sales Force'),
        }