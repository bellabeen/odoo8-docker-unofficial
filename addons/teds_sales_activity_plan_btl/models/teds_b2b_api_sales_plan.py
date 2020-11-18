from openerp import models, fields, api
import json
import requests

import logging
_logger = logging.getLogger(__name__)

class APIButton(models.Model):
    _inherit = "teds.api.button"

    @api.multi
    def schedule_b2b_send_activity_plan(self):
        branches = ['DDS','DDD']
        self.env['teds.sales.plan.activity.line'].schedule_b2b_send_activity_plan(branches)


class SalesPlanActivityLine(models.Model):
    _inherit = "teds.sales.plan.activity.line"

    b2b_status_api = fields.Selection([('draft','Draft'),('error','Error'),('done','Done')],default='draft',index=True)

    @api.multi
    def schedule_b2b_send_activity_plan(self,code):
        teds_api_log = self.env['teds.api.log']
        log_name = 'Sales Activity Plan'
        log_description = 'Send Activity Plan'
        log_module = 'Sales Activity Plan BTL'
        log_model = 'teds.sales.plan.activity.line'
        log_transaction = False
        log_origin = ''

        try:
            query_where = " WHERE spal.b2b_status_api = 'draft' AND spal.state = 'done'"
            query_where += " AND b.code IN %s" % str(tuple(code)).replace(',)', ')')

            query = """
                SELECT b.code as branch_code
                , spa.bulan
                , spa.tahun
                , spal.id as transaction_id
                , act_type.code as act_type_code
                , spal.start_date
                , spal.end_date
                , spal.target_unit
                , spal.target_customer  as target_data_cust
                , tk.name as tk_name
                , tk_kelurahan.code as tk_kelurahan_code
                , tk_kecamatan.code as tk_kecamatan_code
                , tk_kabupaten.code as tk_kabupaten_code
                , '' as tk_lat
                , '' as tk_lng
                , tk.profil_konsumen as tk_profil_konsumen
                , tk.dealer_kompetitor as tk_dealer_kompetitor
                , tk.jarak as tk_jarak
                , tk.waktu as tk_waktu
                , ring.name as tk_ring
                FROM teds_sales_plan_activity spa
                INNER JOIN teds_sales_plan_activity_line spal ON spal.activity_id = spa.id
                INNER JOIN wtc_branch b ON b.id = spa.branch_id
                INNER JOIN titik_keramaian tk ON tk.id = spal.titik_keramaian_id
                INNER JOIN teds_act_type_sumber_penjualan act_type ON act_type.id = spal.act_type_id
                LEFT JOIN wtc_kelurahan tk_kelurahan ON tk_kelurahan.id = tk.kelurahan_id
                LEFT JOIN wtc_kecamatan tk_kecamatan ON tk_kecamatan.id = tk.kecamatan_id
                LEFT JOIN wtc_city tk_kabupaten ON tk_kabupaten.id = tk_kecamatan.city_id
                LEFT JOIN master_ring ring ON ring.id = tk.ring_id
                %s
                ORDER BY spa.name ASC
                LIMIT 50
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
                url = "%s/api/b2b/portal/v1/sales_activity_plan/add" %(base_url)
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
                                teds_sales_plan_activity_line
                                SET b2b_status_api = 'error'
                                WHERE id = %d
                            """ %log_transaction
                            self._cr.execute(update)
                            teds_api_log.suspend_security().create_log_eror(log_name,log_description,log_module,log_model,log_transaction,log_origin)
                        else:
                            update = """
                                UPDATE
                                teds_sales_plan_activity_line
                                SET b2b_status_api = 'done'
                                WHERE id = %d
                            """ %log_transaction
                            self._cr.execute(update)
                            teds_api_log.suspend_security().clear_log_eror(log_transaction,log_origin,log_model)
                else:
                    error = request_content.get('error')
                    info =  request_content.get('error')
                    log_origin = "%s %s" %(error,info)
                    teds_api_log.suspend_security().clear_log_eror(False,log_origin,log_model)

            else:
                log_description = "Update Send Sales Activity Plan Error to Draft"
                _logger.warning(log_description)
                update = """
                    UPDATE
                    teds_sales_plan_activity_line
                    SET b2b_status_api = 'draft'
                    WHERE b2b_status_api = 'error'
                """
                self._cr.execute(update)
        except Exception as err:
            log_description = "Exception %s" %(err)
            _logger.warning(log_description)
            # Create Log API
            teds_api_log.suspend_security().create_log_eror(log_name,log_description,log_module,log_model,log_transaction,log_origin)


