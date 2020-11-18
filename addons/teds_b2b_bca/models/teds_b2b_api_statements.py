from openerp import models, fields, api
from datetime import timedelta,datetime,date
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

    @api.multi
    def corporate_account_statements(self,account,config_id,corporate_url,last_fetch,end_date):
        token = self.get_token_bca(config_id)
        body = self.get_hash_body("")
        pst_now = self.get_timestap()
        start_date = last_fetch
        content = "GET:%s/%s/accounts/%s/statements?EndDate=%s&StartDate=%s:%s:%s:%s" %(corporate_url.url,config_id.corporate_id,account,end_date,start_date,token,body,pst_now)
        signature = self.utilities_signature(config_id.api_secret,  content)
        
        headers = {
            "X-BCA-Signature":signature,
            "X-BCA-Timestamp":pst_now,
            "Authorization": "Bearer %s"%(token),
            "X-BCA-Key": str(config_id.api_key)
        }
        ### Base URL/Corporate URL/Corporate ID/accounts/bank account/statements ###
        url = "%s%s/%s/accounts/%s/statements"%(config_id.base_url,corporate_url.url,config_id.corporate_id,account)
        
        params = {
            "StartDate":start_date,
            "EndDate":end_date
        }
        # Create Log
        name = 'Corporate Statements BCA'
        type = 'outgoing'
        request_type = 'get'

        try:
            response = requests.get(url=url,headers=headers,params=params,verify=config_id.verify)
            response_code = response.status_code
            content = response.content
            jml_data = 0
            if response_code == 200:
                content = json.loads(response.content)
                details = content.get('Data',[])
                jml_data = len(details)
            
            self.env['teds.b2b.api.log'].sudo().create_log_api(name,type,url,request_type,params,response_code,content,jml_data)
            return {'status':1,'response':response} 
        except Exception as err:
            error = "Corporate Statements BCA %s"%(err)
            _logger.warning(error)
            self.env['teds.b2b.api.log'].sudo().create_log_api(name,type,False,request_type,'',False,error)
            
            # Send Notification Slack
            url_slack = "https://hooks.slack.com/services/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"
            self.send_nonitication_slack(url_slack,error)
            return {'status':0}        

    @api.multi
    def schedule_statements_bca(self):
        try:
            config_id = self.search([('name','=','BCA')],limit=1)
            corporate_url = self.env['teds.b2b.api.url'].sudo().search([
                ('config_id','=',config_id.id),
                ('type','=','corporates')],limit=1)
            
            if config_id and corporate_url:
                query = """
                    SELECT b.id
                    , b.name
                    , b.account_id
                    , b.branch_id
                    , aa.code as coa
                    , (b.last_fetch + INTERVAL '7 hours')::date as last_fetch
                    , current_date as end_date
                    FROM teds_b2b_master_bank b
                    INNER JOIN account_account aa ON aa.id = b.account_id
                    INNER JOIN teds_b2b_api_config ac ON ac.id = b.config_id
                    WHERE b.is_fetch_statement = True
                    AND ac.code = 'BCA'
                    ORDER BY b.last_balance_check ASC
                """
                self._cr.execute (query)
                ress =  self._cr.dictfetchall()
                if len(ress) > 0:
                    for res in ress:
                        master_id = res.get('id')
                        bank_account = res.get('name')
                        account_id = res.get('account_id')
                        branch_id = res.get('branch_id')
                        last_fetch = res.get('last_fetch')
                        coa = res.get('coa')
                        end_date = res.get('end_date')
                        master_bank_obj = self.env['teds.b2b.master.bank'].browse(master_id)
                        statement_account = self.corporate_account_statements(bank_account,config_id,corporate_url,last_fetch,end_date)
                        if statement_account.get('status') == 1:
                            response = statement_account.get('response')
                            if response.status_code == 200:
                                content = json.loads(response.content)
                                datas = content.get('Data')
                                #### Delete All Transation PEND Bank Mutation ###
                                delete_bm = """
                                    DELETE FROM teds_bank_mutasi
                                    WHERE date IS NULL
                                    AND account_id = %d
                                    AND branch_id = %d
                                    AND format = 'bca'
                                    AND state = 'Outstanding'
                                """  %(account_id,branch_id)
                                self._cr.execute(delete_bm)

                                for data in datas:
                                    transaction_name = data.get('TransactionName','')
                                    trailer = data.get('Trailer','')
                                    remark = str(transaction_name)+' '+str(trailer)
                                    transaction_type = data.get('TransactionType')
                                    transaction_amount = data.get('TransactionAmount')
                                    transaction_date = data.get('TransactionDate')
                                    tahun = date.today().year
                                    bln_now = date.today().month
                                    transaction_date_format = False
                                    if transaction_date != 'PEND':
                                        tgl,bln = transaction_date.split('/')
                                        if (int(bln) == 12) and (int(bln_now) == int(1)):
                                            tahun = tahun - 1
                                        transaction_date_format = str(tahun)+"-"+str(bln)+"-"+str(tgl)  
                            
                                    remark = remark.strip()
                                    
                                    vals = {
                                        'remark':remark,
                                        'coa':coa,
                                        'date':transaction_date_format,
                                        'account_id':account_id,
                                        'format':'bca',
                                        'no_sistem':'',
                                        'branch_id':branch_id,
                                    }
                                    debit = 0
                                    credit = 0
                                    if transaction_type == 'D':
                                        vals['debit'] = transaction_amount
                                        vals['credit'] = 0
                                        debit = float(transaction_amount)
                                    else:
                                        vals['credit'] = transaction_amount
                                        vals['debit'] = 0
                                    

                                    # Bank IN Auto Posted
                                    if (remark[0:17] == 'TRSF E-BANKING DB') and (remark[-23:] == 'KE PS TUNAS DWIPA MATRA') and coa[0:6] == '111205':
                                        vals['is_posted'] = True
                                    
                                    params_transaction = ['PAJAK BUNGA','BIAYA ADM','BUNGA']
                                    if str(transaction_name) in params_transaction:
                                        cek_bm = self.env['teds.bank.mutasi'].sudo().search([
                                            ('branch_id','=',branch_id),
                                            ('date','=',transaction_date_format),
                                            ('remark','=',remark),
                                            ('account_id','=',account_id),
                                            ('amount','=',transaction_amount),
                                            ('format','=','bca')],limit=1)
                                        if not cek_bm:
                                            # Bank IN Auto Posted
                                            if coa[0:6] == '111205':
                                                vals['is_posted'] = True
                                            create_bm = self.env['teds.bank.mutasi'].sudo().create(vals)
                                    else:                                        
                                        create_bm = self.env['teds.bank.mutasi'].sudo().create(vals)
                                ### Update Bank Status Fetch Statement ###
                                master_bank_obj.sudo().write({
                                    'is_fetch_statement':False,
                                    'last_fetch':datetime.now(),
                                })                                
                                
                            elif response.status_code == 404:
                                ### Update Bank Status Fetch Statement ###
                                master_bank_obj.sudo().write({
                                    'is_fetch_statement':False,
                                    'last_fetch':datetime.now(),
                                })

        except Exception as err:
            error = "Exception Statements BCA %s"%(err)
            _logger.warning(error)

            # Send Notification Slack
            url_slack = "https://hooks.slack.com/services/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"
            self.send_nonitication_slack(url_slack,error)



