from openerp import models, fields, api
import requests
import json

class B2bApiConfig(models.Model):
    _name = "teds.b2b.api.config"

    name = fields.Char(string="Name")
    code = fields.Selection([],string="Code",index=True)
    base_url = fields.Char('Base URL')
    client_id = fields.Char('Client ID')
    client_secret = fields.Char('Client Secret')
    api_key = fields.Char('API Key')
    api_secret = fields.Char('API Secret')
    verify = fields.Boolean('Verify')

    token_ids = fields.One2many('teds.b2b.api.token','config_id')

    @api.multi
    def post(self, name, url, body, headers, type='outgoing', verify=True, log=True):
        response = requests.post(url=url, json=body, headers=headers, verify=verify)
        data_count = 0
        if response.status_code == 200:
            content = json.loads(response.content)
            data_count = len(content.get('data',[]) if content.get('data') else [])
        if log:
            self.env['teds.b2b.api.log'].suspend_security().create_log_api(name, type, url, 'post', {'headers': headers, 'body': body}, response.status_code, response.content, data_count)
        return response

    def send_nonitication_slack(self,url,error):
        headers = {'Content-Type': 'application/json'}
        body = {'text':error}
        
        requests.post(url=url,json=body,headers=headers,verify=True)


class B2bBankToken(models.Model):
    _name = "teds.b2b.api.token"

    config_id = fields.Many2one('teds.b2b.api.config','Config',ondelete='cascade')
    token = fields.Char('Token')
    expired_on = fields.Datetime('Expired on')

    

