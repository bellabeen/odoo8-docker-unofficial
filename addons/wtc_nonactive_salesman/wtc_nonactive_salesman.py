from openerp.osv import fields,osv


class wtc_nonactive_salesman(osv.osv):
    _name='wtc.nonactive.salesman'
    _columns={
              'branch_id':fields.many2one('wtc.branch','Branch',required=True),
              'job_title':fields.selection([('salesman','Salesman'),('sales_counter','Sales Counter'),('sales_partner','Sales Partner')
                                            ,('sales_koordinator','Sales Koordinator'),('mechanic','Mechanic')], string='Sales Force',required=True),
              'cut_off':fields.integer('Cut Off',required=True),
              'nonactive_line_ids':fields.one2many('wtc.nonactive.salesman.line','nonactive_id','Nonactive Lines'),
              'user_ids':fields.many2many('res.users','wtc_nonactive_salesman_user_rel','nonactive_id','user_id','List of Users',readonly=True),
              'state':fields.selection([('draft', 'Draft'), ('confirm', 'Confirm')], 'State', readonly=True, select=True),
              }
    
    _defaults={
               'cut_off':90,
               'state':'draft'
               }
    
    def get_detail(self, cr, uid, ids, context=None):
        value={}
        nonactive_line_list=[]
        
        get_obj=self.browse(cr,uid,ids,context=None)
        branch_id=get_obj.branch_id.id
        cut_off=get_obj.cut_off
        sales_force=get_obj.job_title
        if branch_id:
            query="""
                    SELECT * FROM
                    (
                        SELECT
                            sls.user_id as user_id,
                            rr.name as name,
                            job.sales_force as sales_force,
                            emp.tgl_masuk as tgl_masuk,
                            sls.date_order as date_order,
                            (date(now())-sls.date_order)threshold,
                            (date(now())-sls.date_order)>=%s non_active
                        FROM
                        (
                            SELECT 
                                user_id,
                                branch_id, 
                                max(date_order) as date_order
                            FROM dealer_sale_order
                            WHERE state IN ('done', 'progress', 'cancelled')
                            AND branch_id=%s
                            GROUP BY user_id,branch_id
                            ORDER BY user_id
                        ) sls
                        LEFT JOIN res_users users ON sls.user_id=users.id
                        LEFT JOIN resource_resource rr ON sls.user_id=rr.user_id
                        LEFT JOIN hr_employee emp ON rr.id=emp.resource_id
                        LEFT JOIN hr_job job ON emp.job_id = job.id
                        WHERE job.sales_force='%s'
                        AND users.active=True 
                        AND emp.tgl_keluar is null
                        AND emp.branch_id = %s
                    )a
                    WHERE non_active='t'

                    """ %(cut_off,branch_id,sales_force,branch_id)
            cr.execute(query)    
            ress = cr.dictfetchall()
            for d in ress :
                nonactive_line_list.append(d['user_id'])
            if not nonactive_line_list :
                raise osv.except_osv(('No data found !'), ("Data tidak ditemukan"))
            self.write(cr,uid,ids,{'user_ids': [(6,0,nonactive_line_list)]})

    def _get_default_date(self,cr,uid,ids,context=None):
        return self.pool.get('wtc.branch').get_default_date(cr,uid,ids,context=context)
    
    def nonactive_confirm(self,cr,uid,ids,context=None):
        self.write(cr,uid,ids,{'state':'confirm'})
        obj=self.browse(cr,uid,ids,context=None)

        obj_lines = self.pool.get('wtc.nonactive.salesman.line') 
        lines=[]
        branch_id=obj.branch_id.id
        
        for a in obj.user_ids:
            self.pool.get('res.users').write(cr,uid,a.id,{'active':False})
            lines.append(a.id)
            
        query="""
                select sls_rel.user_id user_id,
                res_res.name as name,
                job.sales_force sales_force,
                emp.tgl_masuk tgl_masuk,
                emp.id employee_id,
                sls.date_order date_order,
                (date(now())-sls.date_order) threshold 
                from wtc_nonactive_salesman_user_rel sls_rel
                left join resource_resource res_res on sls_rel.user_id=res_res.user_id
                left join hr_employee emp on res_res.id = emp.resource_id
                left join hr_job job on emp.job_id = job.id 
                left join (
                select user_id,branch_id, MAX(date_order) as date_order
                from dealer_sale_order dso 
                where dso.state in ('done', 'progress', 'cancelled') 
                and branch_id=%s
                group by user_id,branch_id
                ) sls on sls_rel.user_id = sls.user_id 
                where sls_rel.user_id in %s
            """ % (branch_id,str(tuple(lines)).replace(',)', ')'))
        cr.execute(query)
        ress=cr.dictfetchall()
        nonactive_line_list=[]
        line_ids = []
        emp_ids = []
        for res in ress:
            print "<><><><><><><>",res['user_id']
            nonactive_line_list={
                'nonactive_id':ids[0],
                'user_id':res['user_id'],
                'sales_force':res['sales_force'],
                'tgl_masuk':res['tgl_masuk'],
                'date_order':res['date_order'],
                'threshold':res['threshold'],
                'tgl_confirm':self._get_default_date(cr,uid,ids)
            }
            emp_ids.append(res['employee_id'])
            line_ids.append((0,0,nonactive_line_list))
            # self.pool.get('wtc.nonactive.salesman.line').create(cr,uid,nonactive_line_list)
            # self.pool.get('hr.employee').write(cr,uid,res['employee_id'],{'tgl_keluar':self._get_default_date(cr,uid,ids)})
        if len(line_ids) > 0 :
            self.write(cr,uid,ids,{'nonactive_line_ids': line_ids})
        tgl_keluar = str(self._get_default_date(cr,uid,ids).date())
        self.pool.get('hr.employee').write(cr,uid,emp_ids,{'tgl_keluar':tgl_keluar})
            
        
class wtc_nonactive_salesman_line(osv.osv):
    _name='wtc.nonactive.salesman.line'
    _columns={
              'nonactive_id':fields.many2one('wtc.nonactive.salesman'),
              'user_id':fields.many2one('res.users','Name'),
              'sales_force':fields.char('Sales Force'),
              'tgl_masuk':fields.date('Tgl Masuk'),
              'date_order':fields.datetime('Tgl Order'),
              'threshold':fields.char('Threshold'),
              'tgl_confirm':fields.date('Tgl Confirm'),
              }

