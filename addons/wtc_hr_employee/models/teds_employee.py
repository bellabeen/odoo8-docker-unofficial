from openerp import models, fields, api
from openerp.exceptions import Warning
import json
import requests

import logging
_logger = logging.getLogger(__name__)

class Employee(models.Model):
    _inherit = "hr.employee"

    b2b_status_api = fields.Selection([('draft','Draft'),('error','Error'),('done','Done')],default='draft',index=True)
    b2b_status_api_edit = fields.Selection([('draft','Draft'),('error','Error'),('done','Done')],default='done',index=True)

    @api.multi
    def write(self,vals):
        if vals.get('working_end_date') or vals.get('active') or vals.get('identification_id') or vals.get('job_id') or vals.get('branch_id'):
            vals['b2b_status_api_edit'] = 'draft'
        return super(Employee,self).write(vals)

    @api.onchange('identification_id')
    def onchange_identification(self):
        if self.identification_id:
            if not self.identification_id.isdigit() or len(self.identification_id) != 16:
                warning = {'title':'Perhatian !','message':'No KTP harus 16 digit dan angka !'}
                self.identification_id = False
                return {'warning':warning}
                
    @api.multi
    def send_data_employee(self):
        if self.b2b_status_api == 'draft':
            self.schedule_b2b_send_employee_single()
        else:
            raise Warning('Error kirim data !')
    
    @api.multi
    def schedule_b2b_send_employee_single(self):
        config = self.env['teds.api.configuration'].suspend_security().search([('is_super_user','=',True)],limit=1)
        if not config:
            log_description = 'Configuration Rest API belum di setting !'
            raise Warning(log_description)

        base_url = "%s:%s" %(config.host,config.port)
        if not config.token_ids:
            get_token = config.suspend_security().action_generate_token()
            if not get_token:
                log_description = 'Failed Get Token Rest API!'
                raise Warning(log_description)
        token = config.token_ids[0].token
                
        # HIT KE HOKI API
        url = "%s/api/b2b/portal/v1/employee/add" %(base_url)
        headers = {"access_token":token}
        body = {'data':str([{
            'name':self.name,
            'nip':self.nip,
            'sales_force':self.job_id.sales_force,
            'no_ktp':self.identification_id,
            'transaction_id':self.id,
            'branch_code':self.branch_id.code,
            'working_start_date':self.tgl_masuk,
        }])}
        request_data = requests.post(url, headers=headers, data=body)
        request_status_code = request_data.status_code
        request_content = json.loads(request_data.content)

        if request_status_code == 200:
            # Olah Data Responses
            responses_data = request_content.get('data')
            for responses in responses_data:
                error = responses.get('error')
                error_info = responses.get('info')
                log_transaction =  responses.get('transaction_id')
                log_description = "%s - %s" %(error,error_info)

                if error:
                    raise Warning(log_description)                    
                else:
                    self.b2b_status_api = 'done'
        else:
            log_description = "%s %s" %(error,info)
            raise Warning(log_origin)
    
    @api.multi
    def schedule_b2b_send_employee(self,code):
        teds_api_log = self.env['teds.api.log']
        log_name = 'Employee'
        log_description = 'Send Employee'
        log_module = 'Employee'
        log_model = 'hr.employee'
        log_transaction = False
        log_origin = ''

        try:
            query_where = " WHERE hr.b2b_status_api = 'draft' AND hj.sales_force in ('salesman','sales_counter','sales_partner','sales_koordinator','soh','AM')"
            query_where += " AND b.code IN %s" % str(tuple(code)).replace(',)', ')')

            query = """
                SELECT hr.name_related as name
                , hr.nip
                , hj.sales_force
                , hr.identification_id as no_ktp
                , hr.id as transaction_id
                , b.code as branch_code
                , tgl_masuk as working_start_date
                FROM hr_employee hr
                INNER JOIN hr_job hj ON hj.id = hr.job_id
                INNER JOIN wtc_branch b ON b.id = hr.branch_id
                %s
            """ %query_where
            self.env.cr.execute(query)
            ress = self.env.cr.dictfetchall()
            if ress:
                # Data API
                config = self.env['teds.api.configuration'].suspend_security().search([('is_super_user','=',True)],limit=1)
                if not config:
                    log_description = 'Configuration Rest API belum di setting !'
                    _logger.warning(log_description)
                    # Create Log API
                    teds_api_log.suspend_security().create_log_eror(log_name,log_description,log_module,log_model,log_transaction,log_origin)
                    return False

                base_url = "%s:%s" %(config.host,config.port)
                if not config.token_ids:
                    get_token = config.suspend_security().action_generate_token()
                    if not get_token:
                        log_description = 'Failed Get Token Rest API!'
                        _logger.warning(log_description)
                        # Create Log API
                        teds_api_log.suspend_security().create_log_eror(log_name,log_description,log_module,log_model,log_transaction,log_origin)
                        return False
                token = config.token_ids[0].token
                        
                # HIT KE HOKI API
                url = "%s/api/b2b/portal/v1/employee/add" %(base_url)
                headers = {"access_token":token}
                body = {'data':str(ress)}
                request_data = requests.post(url, headers=headers, data=body)
                request_status_code = request_data.status_code
                request_content = json.loads(request_data.content)

                if request_status_code == 200:
                    # Olah Data Responses
                    responses_data = request_content.get('data')
                    for responses in responses_data:
                        error = responses.get('error')
                        error_info = responses.get('info')
                        log_transaction =  responses.get('transaction_id')
                        log_description = "%s - %s" %(error,error_info)

                        if error:
                            update = """
                                UPDATE
                                hr_employee
                                SET b2b_status_api = 'error'
                                WHERE id = %d
                            """ %log_transaction
                            self._cr.execute(update)
                            teds_api_log.suspend_security().create_log_eror(log_name,log_description,log_module,log_model,log_transaction,log_origin)
                        else:
                            update = """
                                UPDATE
                                hr_employee
                                SET b2b_status_api = 'done'
                                WHERE id = %d
                            """ %log_transaction
                            self._cr.execute(update)
                            teds_api_log.suspend_security().clear_log_eror(log_transaction,log_origin,log_model)

                else:
                    error = request_content.get('error')
                    info =  request_content.get('error')
                    log_description = "%s %s" %(error,info)
                    teds_api_log.suspend_security().create_log_eror(log_name,log_description,log_module,log_model,log_transaction,log_origin)

            else:
                log_description = "Update Send Employee Error to Draft"
                _logger.warning(log_description)
                update = """
                    UPDATE
                    hr_employee
                    SET b2b_status_api = 'draft'
                    WHERE b2b_status_api = 'error'
                """
                self._cr.execute(update)
        except Exception as err:
            log_description = "Exception %s" %(err)
            _logger.warning(log_description)
            # Create Log API
            teds_api_log.suspend_security().create_log_eror(log_name,log_description,log_module,log_model,log_transaction,log_origin)


    @api.multi
    def schedule_b2b_send_employee_edit(self,code):
        teds_api_log = self.env['teds.api.log']
        log_name = 'Employee Edit'
        log_description = 'Send Employee'
        log_module = 'Employee'
        log_model = 'hr.employee'
        log_transaction = False
        log_origin = ''

        try:
            query_where = " WHERE hr.b2b_status_api_edit = 'draft' AND hj.sales_force in ('salesman','sales_counter','sales_partner','sales_koordinator','soh','AM')"
            query_where += " AND b.code IN %s" % str(tuple(code)).replace(',)', ')')

            query = """
                SELECT hr.name_related as name
                , hr.nip
                , hj.sales_force
                , hr.identification_id as no_ktp
                , hr.id as transaction_id
                , b.code as branch_code
                , tgl_masuk as working_start_date
                , tgl_keluar as working_end_date
                FROM hr_employee hr
                INNER JOIN hr_job hj ON hj.id = hr.job_id
                INNER JOIN wtc_branch b ON b.id = hr.branch_id
                %s
            """ %query_where
            self.env.cr.execute(query)
            ress = self.env.cr.dictfetchall()
            if ress:
                # Data API
                config = self.env['teds.api.configuration'].suspend_security().search([('is_super_user','=',True)],limit=1)
                if not config:
                    log_description = 'Configuration Rest API belum di setting !'
                    _logger.warning(log_description)
                    # Create Log API
                    teds_api_log.suspend_security().create_log_eror(log_name,log_description,log_module,log_model,log_transaction,log_origin)
                    return False

                base_url = "%s:%s" %(config.host,config.port)
                if not config.token_ids:
                    get_token = config.suspend_security().action_generate_token()
                    if not get_token:
                        log_description = 'Failed Get Token Rest API!'
                        _logger.warning(log_description)
                        # Create Log API
                        teds_api_log.suspend_security().create_log_eror(log_name,log_description,log_module,log_model,log_transaction,log_origin)
                        return False
                token = config.token_ids[0].token
                        
                # HIT KE HOKI API
                url = "%s/api/b2b/portal/v1/employee/update" %(base_url)
                headers = {"access_token":token}
                body = {'data':str(ress)}
                request_data = requests.post(url, headers=headers, data=body)
                request_status_code = request_data.status_code
                request_content = json.loads(request_data.content)

                if request_status_code == 200:
                    # Olah Data Responses
                    responses_data = request_content.get('data')
                    for responses in responses_data:
                        error = responses.get('error')
                        error_info = responses.get('info')
                        log_transaction =  responses.get('transaction_id')
                        log_description = "%s - %s" %(error,error_info)

                        if error:
                            update = """
                                UPDATE
                                hr_employee
                                SET b2b_status_api_edit = 'error'
                                WHERE id = %d
                            """ %log_transaction
                            self._cr.execute(update)
                            teds_api_log.suspend_security().create_log_eror(log_name,log_description,log_module,log_model,log_transaction,log_origin)
                        else:
                            update = """
                                UPDATE
                                hr_employee
                                SET b2b_status_api_edit = 'done'
                                WHERE id = %d
                            """ %log_transaction
                            self._cr.execute(update)
                            teds_api_log.suspend_security().clear_log_eror(log_transaction,log_origin,log_model)

                else:
                    error = request_content.get('error')
                    info =  request_content.get('error')
                    log_description = "%s %s" %(error,info)
                    teds_api_log.suspend_security().create_log_eror(log_name,log_description,log_module,log_model,log_transaction,log_origin)

            else:
                log_description = "Update Send Employee Error to Draft"
                _logger.warning(log_description)
                update = """
                    UPDATE
                    hr_employee
                    SET b2b_status_api_edit = 'draft'
                    WHERE b2b_status_api_edit = 'error'
                """
                self._cr.execute(update)
        except Exception as err:
            log_description = "Exception %s" %(err)
            _logger.warning(log_description)
            # Create Log API
            teds_api_log.suspend_security().create_log_eror(log_name,log_description,log_module,log_model,log_transaction,log_origin)


