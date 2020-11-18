from openerp.osv import orm, fields, osv
from lxml import etree
from datetime import datetime

class wtc_report_employee_wizard(orm.TransientModel):
    _name = 'wtc.report.employee.wizard'
    _description = 'Report Employee Wizard'
    _rec_name = 'status'
    
    def _get_branch_ids(self, cr, uid, context=None):
        branch_ids_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
        branch_ids = [b.id for b in branch_ids_user]
        return branch_ids
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context:
            context = {}
        res = super(wtc_report_employee_wizard, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        branch_ids = self._get_branch_ids(cr, uid, context)
        doc = etree.XML(res['arch'])
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
        for node in nodes_branch :
            node.set('domain', '[("id", "in", '+ str(branch_ids)+')]')
        res['arch'] = etree.tostring(doc)
        return res
    
    _columns = {
        'status': fields.selection([('all','All'), ('active','Active'), ('non_active','Non Active')], 'Status', required=True, change_default=True, select=True),
        'date': fields.date('Date'),
        'branch_ids': fields.many2many('wtc.branch', 'wtc_report_employee_branch_rel', 'wtc_report_employee_wizard_id',
            'branch_id', 'Branches', copy=False),
        'job_ids': fields.many2many('hr.job', 'wtc_report_employee_job_rel', 'wtc_report_employee_wizard_id',
            'job_id', 'Job Title', copy=False),
    }
    
    _defaults = {
        'status': 'all',
        'date': datetime.now(),
        }
    
    def status_date_change(self, cr, uid, ids, status, date, context=None):
        value = {}
        if status == 'all' :
            value['date'] = False
        return {'value':value}
    
    def print_report(self, cr, uid, ids, context=None):
        if context is None :
            context = {}
        data = self.read(cr, uid, ids)[0]
        if len(data['branch_ids']) == 0 :
            data.update({'branch_ids': self._get_branch_ids(cr, uid, context)})
        return {'type': 'ir.actions.report.xml', 'report_name': 'Report Employee', 'datas': data}
    
    def xls_export(self, cr, uid, ids, context=None):
        return self.print_report(cr, uid, ids, context=context)
    