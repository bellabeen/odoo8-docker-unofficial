from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning
import base64
import json
import requests
import urllib

import binascii
import hmac
import hashlib
import pytz
from datetime import timedelta,datetime

class B2bBankMaster(models.Model):
    _inherit = "teds.b2b.api.config"

    code = fields.Selection(selection_add=[('BCA','BCA')])
    
    @api.multi
    def get_token_bca(self,config_id):
        if len(config_id.token_ids) > 0:
            bca_token = config_id.token_ids[0]
            cek_tgl = datetime.now() + timedelta(seconds=10)
            if cek_tgl > fields.Datetime.from_string(bca_token.expired_on):
                config_id.generate_token_bca(config_id)    
        else:
            config_id.generate_token_bca(config_id)
        return config_id.token_ids[0].token

    @api.multi
    def generate_token_bca(self,config_id):
        base_url = config_id.base_url
        authorization = 'Basic ' + base64.b64encode(str(config_id.client_id)+":"+str(config_id.client_secret))
        headers = {
            "Authorization":authorization,
            "Content-Type":"application/x-www-form-urlencoded",
        }
        form = {"grant_type":'client_credentials'}
        bca_url = self.env['teds.b2b.api.url'].sudo().search([
            ('config_id','=',config_id.id),
            ('type','=','authorization')],limit=1)
        url = base_url + bca_url.url
        response = requests.post(url=url, data=form, headers=headers,verify=config_id.verify)        
        
        ids = []
        if response.status_code == 200:
            self.token_ids.unlink()
            content = json.loads(response.content)
            ids.append([0,False,{
                'token':content.get('access_token'),
                'expired_on': datetime.now() + timedelta(seconds=int(content.get('expires_in')))
            }])
            self.write({
                'token_ids':ids    
            })
        
        # Create Log
        name = 'Generate Token BCA'
        type = 'outgoing'
        url = url
        request_type = 'post'
        request = {'url':url,'data':form}
        response_code = response.status_code
        response = response.content
        self.env['teds.b2b.api.log'].sudo().create_log_api(name,type,url,request_type,request,response_code,response)