from openerp import models, fields, api
from openerp.exceptions import Warning
from datetime import timedelta,datetime
import time
from dateutil.relativedelta import relativedelta
import json
import requests
import hashlib

import logging
_logger = logging.getLogger(__name__)

class B2bDgiBranchConfig(models.Model):
    _inherit = "teds.b2b.dgi.branch.config"
    
    @api.multi
    def _get_data_order(self):
        order = super(B2bDgiBranchConfig,self)._get_data_order()
        if self.config_id.code == "SINSEN":
            vals = {
                'no_prospect':self.no_prospect,
                'no_spk':self.no_spk,
                'date':self.date,
            }
            return self.config_id.suspend_security().action_manual_data_order_sinsen_h1(self.branch_id, vals)             
        return order


class B2bApiConfig(models.Model):
    _inherit = "teds.b2b.api.config"

    @api.multi
    def action_manual_data_order_sinsen_h1(self, branch, vals):
        query_date = datetime.strptime(vals.get('date'),'%Y-%m-%d')
        spks_result = self._get_data_oder_sinsen_h1(branch, query_date, log=False, idProspect=vals.get('no_prospect'), idSpk=vals.get('no_spk'))
        datas = spks_result.get('data')

        if spks_result.get('status', 0)==0 or not datas:
            error = spks_result.get('error', 'Get Prospect data not found ! ID Prospect %s' %vals.get('no_prospect'))
            raise Warning(error)

        # proses data create sale order draft        
        proses = self._process_data_order_sinsen_h1(branch, datas, log=False)
        return proses