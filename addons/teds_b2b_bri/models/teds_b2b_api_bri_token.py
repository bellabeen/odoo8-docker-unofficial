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

    code = fields.Selection(selection_add=[('BRI','BRI')])

    @api.multi
    def get_token_bri_manual(self):
        url = self.env['teds.b2b.api.url'].sudo().search([('config_id','=',self.id),('type','=','authorization')]).url
        self.generate_token_bri(url,self.api_key,self.api_secret)

    def get_token_bri(self,config_id):
        client = config_id.api_key
        secret = config_id.api_secret
        url = self.env['teds.b2b.api.url'].sudo().search([('config_id','=',config_id.id),('type','=','authorization')]).url
        if client and secret and url:
            if len(config_id.token_ids) > 0:
                bca_token = config_id.token_ids[0]
                cek_tgl = datetime.now() + timedelta(seconds=10)
                if cek_tgl > fields.Datetime.from_string(bca_token.expired_on):
                    config_id.generate_token_bri(url,client,secret)    
            else:
                config_id.generate_token_bri(url,client,secret)
            if not config_id.token_ids:
                return False
            token = "Bearer %s" %config_id.token_ids[0].token
            return token 
        else:
            return False

    def generate_token_bri(self,url,client,secret):
        payload = 'client_id=%s&client_secret=%s' %(client,secret)
        headers = {
          'Content-Type': 'application/x-www-form-urlencoded',
        }
        response = requests.request("POST", url, headers=headers, data = payload) 
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
        name = 'Generate Token BRI'
        type = 'outgoing'
        url = url
        request_type = 'post'
        request = {'url':url}
        response_code = response.status_code
        response = response.content
        self.env['teds.b2b.api.log'].sudo().create_log_api(name,type,url,request_type,request,response_code,response)

        