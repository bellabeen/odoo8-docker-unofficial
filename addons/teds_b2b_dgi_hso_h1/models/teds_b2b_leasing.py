from openerp import models, fields, api
from openerp.exceptions import Warning
from datetime import timedelta, datetime
import time
from dateutil.relativedelta import relativedelta
import json
import requests
import hashlib

import logging
_logger = logging.getLogger(__name__)


class B2bApiConfig(models.Model):
    _inherit = "teds.b2b.api.config"

    @api.multi
    def _get_api_lsng_hso(self, branch, query_date, log=True, idProspect=False, idSpk=False):
        api_url = "%s/lsng/read" % self.base_url
        date_format = '%Y-%m-%d %H:%M:%S'

        from_time = datetime.combine(
            query_date - timedelta(days=6), datetime.min.time())
        to_time = datetime.combine(query_date, datetime.max.time())


        ## EPOCH ##
        # epoch = int(time.mktime(time.strptime(datetime.now().strftime(date_format), '%Y-%m-%d %H:%M:%S')))
        # verify pakai time.localtime() or time.gmtime()
        epoch = int(time.mktime(time.localtime()))

        # TOKEN DGI #
        if not self.api_key and self.api_secret:
            error = "API Key dan API Secret Required !"
            if log:
                self.create_log_error_dgi('DGI H1 SPK HSO',api_url,'post',error,'LSNG')
            return {'status':0,'error':error}
        token_raw = "%s%s%s" % (self.api_key, self.api_secret, epoch)
        token = hashlib.sha256(token_raw).hexdigest()

        headers = {
            "DGI-API-Key": self.api_key,
            "Content-Type": "application/json",
            "X-Request-Time": str(epoch),
            "DGI-API-Token": token
        }
        # Body #
        body = {
            "fromTime": from_time.strftime(date_format),
            "toTime": to_time.strftime(date_format),
        }
        if branch.md_reference:
            body['dealerId'] = branch.md_reference

        if idSpk:
            body['idSPK'] = idSpk

        response = self.post(name="DGI H1 LSNG HSO",url=api_url, body=body, headers=headers, type='incoming', verify=self.verify)
        if response.status_code == 200:
            content = json.loads(response.content)
            # Get Data Response
            data = content.get('data')
            if not data:
                error = "Data Leasing tidak ditemukan !"
                if idProspect:
                    error = 'Data Leasing %s tidak ditemukan !' % idProspect
                if idSpk:
                    error = 'Data Leasing %s tidak ditemukan !' % idSpk
                if log:
                    self.create_log_error_dgi('DGI H1 SPK HSO',api_url,'post',error,'LSNG')
                return {'status':0,'error':error}
            return {'status':1, 'data':data}
        else:
            error = "Gagal Get Leasing.\nStatus Code: %s\nContent: %s" % (response.status_code, response.content)
            if log:
                self.create_log_error_dgi('DGI H1 SPK HSO',api_url,'post',error,'LSNG')
            return {'status':0,'error':error}
