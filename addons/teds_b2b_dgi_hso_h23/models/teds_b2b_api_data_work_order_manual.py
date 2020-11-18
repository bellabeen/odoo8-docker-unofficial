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
    def _get_data_work_order(self):
        order = super(B2bDgiBranchConfig,self)._get_data_work_order()
        if self.config_id.code == "HSO":
            vals = {
                'no_work_order':self.no_wo,
                'date':self.date,
                'type':self.type_h23,
            }
            return self.config_id.suspend_security().action_manual_data_work_order_hso_h23(self.branch_id, vals)             
        return order


class B2bApiConfig(models.Model):
    _inherit = "teds.b2b.api.config"

    @api.multi
    def action_manual_data_work_order_hso_h23(self, branch, vals):
        query_date = datetime.strptime(vals.get('date'),'%Y-%m-%d')
        if vals.get('type') == 'PRSL':
            pkb_result = self._get_data_prsl_hso_h23(branch, query_date, log=False, noWorkOrder=vals.get('no_work_order'))
            datas = pkb_result.get('data')
            if pkb_result.get('status', 0)==0 or not datas:
                error = pkb_result.get('error', 'Get Part Sales data not found ! ID PKB %s' % vals.get('no_work_order'))
                raise Warning(error)
            
            # proses data create sale order draft        
            proses = self._process_data_prsl_hso_h23(branch, datas, log=False)
            return proses
        else:
            pkb_result = self._get_data_wo_hso_h23(branch, query_date, log=False, noWorkOrder=vals.get('no_work_order'))
            datas = pkb_result.get('data')
            if pkb_result.get('status', 0)==0 or not datas:
                error = pkb_result.get('error', 'Get Work Order data not found ! ID PKB %s' % vals.get('no_work_order'))
                raise Warning(error)
            
            # proses data create sale order draft        
            proses = self._process_data_wo_hso_h23(branch, datas, log=False)
            return proses