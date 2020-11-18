from openerp import models, fields, api
from openerp.exceptions import Warning
from datetime import date, timedelta, datetime
import json
import requests

import logging
_logger = logging.getLogger(__name__)

class StockLocation(models.Model):
    _inherit = "stock.location"

    b2b_status_api = fields.Selection([('draft','Draft'),('error','Error'),('done','Done')],default='draft',index=True)
    
    @api.multi
    def write(self, vals):
        if vals.get('jenis',self.jenis) == 'pos':
            if vals.get('start_date') or vals.get('end_date') or vals.get('end_date') or vals.get('jenis'):
                vals['b2b_status_api'] = 'draft'
        return super(StockLocation, self).write(vals)

    @api.multi
    def send_data_stock_location(self):
        if self.b2b_status_api == 'draft' and self.jenis == 'pos':
            self.schedule_b2b_send_stock_location_single()
        else:
            raise Warning('Error kirim data ! Status API harus draft dan jenis harus POS.')
    
    @api.multi
    def schedule_b2b_send_stock_location_single(self):
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
        url = "%s/api/b2b/portal/v1/stock_location/add" %(base_url)
        headers = {"access_token":token}
        body = {'data':str([{
            'name':self.name,
            'branch_code':self.branch_id.code,
            'description':self.description,
            'location_type':self.jenis,
            'start_date':self.start_date,
            'end_date':self.end_date,
            'id_teds':self.id,
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
    def schedule_b2b_send_stock_location(self,branch_code):
        teds_api_log = self.env['teds.api.log']
        log_name = 'Stock Location'
        log_description = 'Send Stock Location'
        log_module = 'Stock Location'
        log_model = 'stock.location'
        log_transaction = False
        log_origin = ''
        today = date.today()
        try:
            query_where = " WHERE stock_location.b2b_status_api = 'draft' AND stock_location.jenis = 'pos' AND stock_location.end_date >= '%s'" %(today)
            query_where += " AND b.code IN %s" % str(tuple(branch_code)).replace(',)', ')')

            query = """
                SELECT 
                stock_location.id as id_teds
                , stock_location.name as name
                , stock_location.description as description
                , stock_location.jenis as location_type
                , stock_location.start_date as start_date
                , stock_location.end_date as end_date
                , b.code as branch_code
                FROM stock_location as stock_location
                INNER JOIN wtc_branch b ON b.id = stock_location.branch_id
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
                url = "%s/api/b2b/portal/v1/stock_location/add" %(base_url)
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
                                stock_location
                                SET b2b_status_api = 'error'
                                WHERE id = %d
                            """ %log_transaction
                            self._cr.execute(update)
                            teds_api_log.suspend_security().create_log_eror(log_name,log_description,log_module,log_model,log_transaction,log_origin)
                        else:
                            update = """
                                UPDATE
                                stock_location
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
                    stock_location
                    SET b2b_status_api = 'draft'
                    WHERE b2b_status_api = 'error'
                """
                self._cr.execute(update)
        except Exception as err:
            log_description = "Exception %s" %(err)
            _logger.warning(log_description)
            # Create Log API
            teds_api_log.suspend_security().create_log_eror(log_name,log_description,log_module,log_model,log_transaction,log_origin)


