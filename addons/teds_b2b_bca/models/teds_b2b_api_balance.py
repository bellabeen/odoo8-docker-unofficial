from openerp import models, fields, api
from datetime import timedelta,datetime
import json
import requests
import urllib
import binascii
import hmac
import hashlib
import pytz

import logging
_logger = logging.getLogger(__name__)


class B2bBankMaster(models.Model):
    _inherit = "teds.b2b.api.config"

    def get_hash_body(self,body):
        has = hashlib.sha256(body).hexdigest()
        return str(has).lower()
    
    def get_timestap(self):
        utc_now = pytz.utc.localize(datetime.utcnow())
        pst_now = utc_now.astimezone(pytz.timezone("Asia/Jakarta"))
        pst_now = pst_now.isoformat()
        pst_now = pst_now[:-13]
        pst_now += '.000+07:00'
        return pst_now

    @api.multi
    def utilities_signature(self,api_secret,url):
        h = hmac.new(str(api_secret), str(url), hashlib.sha256)
        return str(h.hexdigest())


    @api.multi
    def corporate_balance(self,accounts):
        config_id = self.search([('code','=','BCA')],limit=1)

        corporate_url = self.env['teds.b2b.api.url'].sudo().search([
            ('config_id','=',config_id.id),
            ('type','=','corporates')],limit=1)

        list_account = accounts
        
        account_urllib = urllib.quote(','.join(list_account))
        token = self.get_token_bca(config_id)
        body = self.get_hash_body("")
        pst_now = self.get_timestap()

        content = "GET:%s/%s/accounts/%s:%s:%s:%s" %(corporate_url.url,config_id.corporate_id,account_urllib,token,body,pst_now)
        signature = self.utilities_signature(config_id.api_secret,content)

        headers = {
            "X-BCA-Signature":signature,
            "X-BCA-Timestamp":pst_now,
            "Authorization": "Bearer %s"%(token),
            "X-BCA-Key": str(config_id.api_key)
        }
        join_account = ','.join(list_account)
        
        ### Base URL/Corporate URL/Corporate ID/accounts/bank account ###
        url = "%s%s/%s/accounts/%s" %(config_id.base_url,corporate_url.url,config_id.corporate_id,join_account)
        # Create Log
        name = 'Corporate Balance BCA'
        type = 'outgoing'
        request_type = 'get'

        try:
            response = requests.get(url=url,headers=headers,verify=config_id.verify)
            response_code = response.status_code
            content = response.content
            jml_data = 0
            if response_code == 200:
                content = json.loads(response.content)
                details = content.get('AccountDetailDataSuccess',[])
                jml_data = len(details)

            self.env['teds.b2b.api.log'].sudo().create_log_api(name,type,url,request_type,'',response_code,content,jml_data)
            return {'status':1,'response':response} 
        except Exception as err:
            error = "Exception Balance BCA %s"%(err)
            _logger.warning(error)
            self.env['teds.b2b.api.log'].sudo().create_log_api(name,type,url,request_type,'',False,error)
            
            # Send Notification Slack
            url_slack = "https://hooks.slack.com/services/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"
            self.send_nonitication_slack(url_slack,error)
            return {'status':0} 
       
    @api.multi
    def schedule_balance_bca(self):        
        try:
            query = """
                SELECT b.id
                , MIN((jam||':'||menit)::time) as schedule_time 
                , b.name as no_rekening
                FROM teds_b2b_master_bank b
                INNER JOIN teds_b2b_api_config ac ON ac.id = b.config_id
                INNER JOIN teds_b2b_api_schedule s ON s.id = b.schedule_id
                INNER JOIN teds_b2b_api_schedule_detail sd ON
                (
                    (b.last_balance_check + INTERVAL '7 hours')::date = current_date 
                    AND (b.last_balance_check + INTERVAL '7 hours')::time < (jam||':'||menit)::time 
                    AND (jam||':'||menit)::time < current_time 
                )
                OR 
                (
                    (b.last_balance_check + INTERVAL '7 hours'):: date < current_date 
                    AND (jam||':'||menit)::time < current_time
                )
                WHERE ac.code = 'BCA'
                GROUP BY b.id
                ORDER BY schedule_time ASC          
                LIMIT 20
            """
            self._cr.execute (query)
            ress =  self._cr.dictfetchall()
            if len(ress) > 0:
                accounts = [res.get('no_rekening') for res in ress]
                corporate_account = self.corporate_balance(accounts)
                if corporate_account.get('status') == 1:
                    response = corporate_account.get('response')
                    if response.status_code == 200:
                        content = json.loads(response.content)
                        details = content.get('AccountDetailDataSuccess')
                        for detail in details:
                            bank_account = detail.get('AccountNumber')
                            dt_balance = detail.get('Balance')
                            master_bank = self.env['teds.b2b.master.bank'].sudo().search([('name','=',bank_account)],limit=1)
                            if master_bank:
                                is_fetch_statement = False
                                last_balance = master_bank.balance
                                if abs(last_balance - float(dt_balance)) != 0:
                                    is_fetch_statement = True
                                elif datetime.strptime(master_bank.last_balance_check, '%Y-%m-%d %H:%M:%S').date() < datetime.now().date():
                                    is_fetch_statement = True

                                vals_mb = {
                                    'plafon':detail.get('Plafon'),
                                    'currency':detail.get('Currency'),
                                    'float_amount':detail.get('FloatAmount'),
                                    'hold_amount':detail.get('HoldAmount'),
                                    'available_balance':detail.get('AvailableBalance'),
                                    'balance':dt_balance,
                                    'is_fetch_statement':is_fetch_statement,
                                    'last_balance_check':datetime.now(),
                                }
                                master_bank.sudo().write(vals_mb)
                            else:
                                error = "Balance BCA AccountNumber %s tidak ditemukan ! " %bank_account
                                # Send Notification Slack
                                url_slack = "https://hooks.slack.com/services/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"
                                self.send_nonitication_slack(url_slack,error)

        except Exception as err:
            error = "Exception Balance BCA %s"%(err)
            _logger.warning(error)

            # Send Notification Slack
            url_slack = "https://hooks.slack.com/services/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"
            self.send_nonitication_slack(url_slack,error)

