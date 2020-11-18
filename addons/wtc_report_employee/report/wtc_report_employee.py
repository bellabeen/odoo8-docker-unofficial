from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm

class wtc_report_employee_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(wtc_report_employee_print, self).__init__(cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({'formatLang_zero2blank': self.formatLang_zero2blank})

    def set_context(self, objects, data, ids, report_type=None):
        status = data['status']
        date = data['date'] or datetime.now().date()
        branch_ids = data['branch_ids']
        job_ids = data['job_ids']
        
        where_status = " 1=1 "
        if status == 'active' :
            where_status = " employee.tgl_masuk < '%s'" % str(date) + " and (employee.tgl_keluar > '%s'" % str(date) + " or employee.tgl_keluar is null)"
        elif status == 'non_active' :
            where_status = " employee.tgl_keluar < '%s'" % str(date)
        where_branch_ids = " 1=1 "
        if branch_ids :
            where_branch_ids = " b.id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        where_job_ids = " 1=1 "
        if job_ids :
            where_job_ids = " job.id in %s" % str(
                tuple(job_ids)).replace(',)', ')')
        
        query_employee = """
            select b.code as branch_code, b.name as branch_name, area.code as area_code, area.description as area_desc, employee.nip as employee_nip,
            resource.name as resource_name, employee.street as employee_street, employee.street2 as employee_street2, employee.rt as rt, employee.rw as rw, province.name as province, city.name as city, employee.kecamatan as kecamatan, employee.kelurahan as kelurahan,
            job.name as job_name, groups.name as group_name, employee.tgl_masuk as tgl_masuk, employee.tgl_keluar as tgl_keluar, create_partner.name as created_by, employee.create_date as created_date, update_partner.name as updated_by, employee.write_date as updated_date
            from hr_employee employee inner join resource_resource resource on employee.resource_id = resource.id
            left join wtc_branch b on employee.branch_id = b.id
            left join wtc_area area on employee.area_id = area.id
            left join res_country_state province on employee.state_id = province.id
            left join wtc_city city on employee.city_id = city.id
            left join hr_job job on employee.job_id = job.id
            left join res_groups groups on job.group_id = groups.id
            left join res_users create_by on employee.create_uid = create_by.id
            left join res_partner create_partner on create_by.partner_id = create_partner.id
            left join res_users update_by on employee.write_uid = update_by.id
            left join res_partner update_partner on update_by.partner_id = update_partner.id
        """
        
        where = "WHERE employee.nip is not null AND " + where_status + " AND " + where_branch_ids + " AND " + where_job_ids
        order = "order by b.code, job.name, employee.nip"
        
        self.cr.execute(query_employee + where + order)
        all_lines = self.cr.dictfetchall()
        
        if all_lines :
            datas = map(lambda x : {
                'no': 0,
                'branch_code': str(x['branch_code'].encode('ascii','ignore').decode('ascii')) if x['branch_code'] != None else '',
                'branch_name': str(x['branch_name'].encode('ascii','ignore').decode('ascii')) if x['branch_name'] != None else '',
                'area_code': str(x['area_code'].encode('ascii','ignore').decode('ascii')) if x['area_code'] != None else '',
                'area_desc': str(x['area_desc'].encode('ascii','ignore').decode('ascii')) if x['area_desc'] != None else '',
                'employee_nip': str(x['employee_nip'].encode('ascii','ignore').decode('ascii')) if x['employee_nip'] != None else '',
                'resource_name': str(x['resource_name'].encode('ascii','ignore').decode('ascii')) if x['resource_name'] != None else '',
                'employee_street': str(x['employee_street'].encode('ascii','ignore').decode('ascii')) if x['employee_street'] != None else '',
                'employee_street2': str(x['employee_street2'].encode('ascii','ignore').decode('ascii')) if x['employee_street2'] != None else '',
                'rt': str(x['rt'].encode('ascii','ignore').decode('ascii')) if x['rt'] != None else '',
                'rw': str(x['rw'].encode('ascii','ignore').decode('ascii')) if x['rw'] != None else '',
                'province': str(x['province'].encode('ascii','ignore').decode('ascii')) if x['province'] != None else '',
                'city': str(x['city'].encode('ascii','ignore').decode('ascii')) if x['city'] != None else '',
                'kecamatan': str(x['kecamatan'].encode('ascii','ignore').decode('ascii')) if x['kecamatan'] != None else '',
                'kelurahan': str(x['kelurahan'].encode('ascii','ignore').decode('ascii')) if x['kelurahan'] != None else '',
                'job_name': str(x['job_name'].encode('ascii','ignore').decode('ascii')) if x['job_name'] != None else '',
                'group_name': str(x['group_name'].encode('ascii','ignore').decode('ascii')) if x['group_name'] != None else '',
                'tgl_masuk': str(x['tgl_masuk'].encode('ascii','ignore').decode('ascii')) if x['tgl_masuk'] != None else '',
                'tgl_keluar': str(x['tgl_keluar'].encode('ascii','ignore').decode('ascii')) if x['tgl_keluar'] != None else '',
                'created_by': str(x['created_by'].encode('ascii','ignore').decode('ascii')) if x['created_by'] != None else '',
                'created_date': str(x['created_date'].encode('ascii','ignore').decode('ascii')) if x['created_date'] != None else '',
                'updated_by': str(x['updated_by'].encode('ascii','ignore').decode('ascii')) if x['updated_by'] != None else '',
                'updated_date': str(x['updated_date'].encode('ascii','ignore').decode('ascii')) if x['updated_date'] != None else '',
                }, all_lines)
            reports = filter(lambda x: datas, [{'datas': datas}])
        else :
            reports = [{'datas': [{
                'no': 'NO DATA FOUND',
                'branch_code': 'NO DATA FOUND',
                'branch_name': 'NO DATA FOUND',
                'area_code': 'NO DATA FOUND',
                'area_desc': 'NO DATA FOUND',
                'employee_nip': 'NO DATA FOUND',
                'resource_name': 'NO DATA FOUND',
                'employee_street': 'NO DATA FOUND',
                'employee_street2': 'NO DATA FOUND',
                'rt': 'NO DATA FOUND',
                'rw': 'NO DATA FOUND',
                'province': 'NO DATA FOUND',
                'city': 'NO DATA FOUND',
                'kecamatan': 'NO DATA FOUND',
                'kelurahan': 'NO DATA FOUND',
                'job_name': 'NO DATA FOUND',
                'group_name': 'NO DATA FOUND',
                'tgl_masuk': 'NO DATA FOUND',
                'tgl_keluar': 'NO DATA FOUND',
                'created_by': 'NO DATA FOUND',
                'created_date': 'NO DATA FOUND',
                'updated_by': 'NO DATA FOUND',
                'updated_date': 'NO DATA FOUND',
                }]}]
        
        self.localcontext.update({'reports': reports})
        super(wtc_report_employee_print, self).set_context(objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else :
            return super(wtc_report_employee_print, self).formatLang(value, digits, date, date_time, grouping, monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.wtc_report_employee.report_employee'
    _inherit = 'report.abstract_report'
    _template = 'wtc_report_employee.report_employee'
    _wrapped_report_class = wtc_report_employee_print
    