from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning
import requests
import json

class ApiConfiguration(models.Model):
    _name = "teds.api.configuration"
    _rec_name = "username"

    def _get_default_branch(self):
        branch_ids = False
        branch_ids = self.env.user.branch_ids
        if branch_ids and len(branch_ids) == 1 :
            return branch_ids[0].id
        return False
   

    branch_id = fields.Many2one('wtc.branch','Branch',default=_get_default_branch)
    username = fields.Char('Username',required=True)
    password = fields.Char('Password',required=True)
    database = fields.Char('Database',required=True)
    host = fields.Char('Host',required=True)
    port = fields.Char('Port',required=True)
    is_super_user = fields.Boolean('Super User ?')
    token_ids = fields.One2many('teds.api.configuration.token','config_id','Tokens')

    _sql_constraints = [('branch_id_unique', 'unique(branch_id)', 'User cabang tidak boleh lebih dari satu.')]

    @api.model
    def create(self,vals):
        cek = self.search([('is_super_user','=',True)],limit=1)
        if cek:
            raise Warning('Super User sudah dibuat !')
        return super(ApiConfiguration,self).create(vals)

    @api.multi
    def action_generate_token(self):
        # Generate Token
        url = "%s:%s/api/auth/get_tokens" %(self.host,self.port)
        
        payload = "username=%s&password=%s&db=%s"%(self.username,self.password,self.database)
        headers = {
            'content-type': "application/x-www-form-urlencoded",
        }

        hit_token = requests.post(url, data=payload, headers=headers)
        hit_status_code = hit_token.status_code
        if hit_status_code == 200:
            hit_content = json.loads(hit_token.content)
            token_ids = []
            token_ids.append([0,False,{
                'token':hit_content.get('access_token')
            }])
            self.suspend_security().write({'token_ids':token_ids})
        else:
            # NOTIF KE SLACK
            return False
        return True


class ApiConfigurationToken(models.Model):
    _name = "teds.api.configuration.token"

    config_id = fields.Many2one('teds.api.configuration')
    token = fields.Char('Token')
    expired_on = fields.Datetime('Expired On')