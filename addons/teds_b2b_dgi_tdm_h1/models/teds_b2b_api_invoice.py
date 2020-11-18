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

class B2bApiConfig(models.Model):
    _inherit = "teds.b2b.api.config"

    @api.multi
    def dgi_tdm_inv1_add(self,branch_ids,log=True):
        try:
            data_so = """
                SELECT dso.id as dso_id
                , dso.md_reference_spk as spk_id
                , ai.number as invoice_id
                , to_char(ai.create_date + interval '7 hours','DD/MM/YYYY HH:MM:SS') as create_date
                , ai.amount_total
                , cust.default_code as cust_id
                FROM dealer_sale_order dso
                INNER JOIN account_invoice ai ON ai.transaction_id = dso.id
                INNER JOIN ir_model model ON model.id = ai.model_id
                LEFT JOIN res_partner cust ON cust.id = ai.partner_id
                WHERE dso.branch_id in %s
                AND dso.md_reference_spk is not null
                AND dso.dgi_status_inv = 'draft' 
                AND model.model = 'dealer.sale.order' 
                AND ai.type = 'out_invoice'
                AND ai.tipe = 'customer'
                AND ai.state = 'paid'
                GROUP BY dso.id,ai.id,cust.id
                ORDER BY dso.date_order ASC
                LIMIT 10
            """ % str(tuple(branch_ids)).replace(',)', ')')
            self._cr.execute(data_so)
            ress = self._cr.dictfetchall()
            if ress:
                api_url = "%s/inv1/add" % self.base_url
                
                # epoch = int(time.mktime(time.strptime(datetime.now().strftime(date_format), '%Y-%m-%d %H:%M:%S')))
                epoch = int(time.mktime(time.localtime())) # verify pakai time.localtime() or time.gmtime()

                # TOKEN DGI #
                if not self.api_key and not self.api_secret:
                    error = "API Key dan API Secret Required !"
                    if log:
                        self.create_log_error_dgi('DGI H1 INV ADD TDM',api_url,'post',error,'INV1')
                    return {'status':0,'error':error}

                token_raw = "%s:%s:%s"%(self.api_key, self.api_secret, epoch)
                token = hashlib.sha256(token_raw).hexdigest()

                for res in ress:
                    dso_id = res.get('dso_id')
                    idSPK = res.get('spk_id')
                    idInvoice = res.get('invoice_id')
                    createdTime = res.get('create_date')    
                    amount_total = res.get('amount_total')
                    idCustomer = res.get('cust_id')
                    headers = {
                        "DGI-API-Key":self.api_key,
                        "Content-Type":"application/json",
                        "X-Request-Time":str(epoch),
                        "DGI-API-Token":token
                    }
                    body = {
                        'idInvoice':idInvoice,
                        'idSPK':idSPK,
                        'createdTime':createdTime,
                        'amount':"0",
                        'idCustomer':idCustomer,
                        'tipePembayaran':'Cash',
                        'caraBayar':'Cash',
                        'status':'Close',
                    }
                    
                    response = self.post(name="DGI INV ADD H1 TDM", url=api_url, body=body, headers=headers, type='incoming', verify=self.verify)
                    if response.status_code == 200:
                        content = json.loads(response.content)
                        update_dso = """
                            UPDATE
                            dealer_sale_order
                            SET dgi_status_inv = 'done'
                            WHERE id = %d
                        """ %(dso_id)
                        self._cr.execute(update_dso)
                    else:
                        error = "Gagal ADD INV H1 \nStatus Code: %s\nContent: %s" % (response.status_code, response.content)
                        if log:
                            self.create_log_error_dgi('DGI INV ADD H1 SPK TDM',api_url,'post',error,'INV1')
                        update_dso = """
                            UPDATE
                            dealer_sale_order
                            SET dgi_status_inv = 'error'
                            WHERE id = %d
                        """ %(dso_id)
                        self._cr.execute(update_dso)
                        return {'status':0,'error':error}
            else:
                _logger.warning("Update DGI INV H1 TDM Status error to draft >>>>>>>>>")
                update_dso = """
                    UPDATE
                    dealer_sale_order
                    SET dgi_status_inv = 'draft'
                    WHERE dgi_status_inv = 'error'
                """
                self._cr.execute(update_dso)
        except Exception as err:
            _logger.warning("Exception DGI INV ADD H1 TDM >>>>>>>>> %s"%(err))
            if not log:
                raise Warning(err)
            self.create_log_error_dgi('Exception DGI INV ADD TDM',self.base_url,'post',err,'INV1')
        

    @api.multi
    def schedule_inv1_add_tdm_h1(self,code):
        # Code adalah code config b2b
        config_id = self.search([('code','=',code)],limit=1)
        branch_config_id = self.env['wtc.branch.config'].suspend_security().search([('config_dgi_id','=',config_id.id)])
        if config_id and branch_config_id:
            # Listing Cabang DGI nya
            branch_ids = [b.branch_id.id for b in branch_config_id]
            return config_id.suspend_security().dgi_tdm_inv1_add(branch_ids)
        else:
            error = 'Branch Config code %s DGI belum di setting !'%code
            _logger.warning(error)
            self.create_log_error_dgi('Shedule DGI Invoice H1 ADD TDM',False,'post',error,'INV1')            