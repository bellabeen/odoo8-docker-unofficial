from openerp import models, fields, api
from datetime import datetime
import time

import requests
import json

class ApiLog(models.Model):
    _name = "teds.api.log"
    _order = "date desc"

    def _get_default_date(self):
        return datetime.now()

    name = fields.Text('Code')
    description = fields.Text('Description')
    status = fields.Boolean('Status')
    module_name = fields.Char('Module')
    model_name = fields.Char('Model')
    transaction_id = fields.Char('Transaction ID')
    origin = fields.Char('Origin')
    date = fields.Datetime('Datetime',default=_get_default_date)


    @api.multi
    def clear_log_eror(self,transaction_id,origin,model_name):
        delete = """
            DELETE 
            FROM teds_api_log
            WHERE transaction_id = '%s'
            AND origin = '%s'
            AND model_name = '%s'
        """%(transaction_id,origin,model_name)
        res = self._cr.execute(delete)

    @api.multi
    def create_log_eror(self,name,description,module_name,model_name,transaction_id,origin,status=False):
        query = """
            SELECT id FROM teds_api_log
            WHERE name = '%s'
            AND description = '%s'
            AND module_name = '%s'
            AND model_name = '%s'
            AND transaction_id = '%s'
            AND origin = '%s'
            AND status = %s
            AND date + interval '7 hours' BETWEEN (now() - interval '1 hours') AND now()
            LIMIT 1
        """ %(name,description,module_name,model_name,transaction_id,origin,status)
        self._cr.execute (query)
        res =  self._cr.fetchone()
        if not res:
            self.create({
                'name':name,
                'description':description,
                'module_name':module_name,
                'model_name':model_name,
                'transaction_id':transaction_id,
                'origin':origin,
                'status':status,
            })
            # Kirim error ke slack
            url = "https://hooks.slack.com/services/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"
            error_slack = "%s %s" %(name,description)
            self.send_nonitication_slack(url,error_slack)


    def send_nonitication_slack(self,url,error):
        headers = {'Content-Type': 'application/json'}
        body = {'text':error}

        requests.post(url=url,json=body,headers=headers,verify=True)

    
    

