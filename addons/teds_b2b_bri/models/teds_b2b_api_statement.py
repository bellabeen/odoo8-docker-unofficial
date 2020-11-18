from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning
from datetime import timedelta,datetime,date
import json
import requests
import urllib
import binascii
import hmac
import hashlib
import pytz
import base64

import logging
_logger = logging.getLogger(__name__)


class B2bBankMaster(models.Model):
    _inherit = "teds.b2b.api.config"

    def get_time_bri(self):
        utc_now = pytz.utc.localize(datetime.utcnow() - timedelta(hours=7))
        pst_now = utc_now.astimezone(pytz.timezone("Asia/Jakarta"))
        pst_now = pst_now.isoformat()
        pst_now = pst_now[:-9]+"Z"
        return pst_now

    
    @api.multi
    def corporate_account_statements_bri(self,config_id,account,base_url,start_date,end_date):
        client = config_id.api_key
        secret = config_id.api_secret
        path = "/v1/statement/%s/%s/%s" %(account,start_date,end_date)
        url = "%s%s" %(base_url,path)
        verb = "GET"
        token = self.get_token_bri(config_id)
        timestamp = self.get_time_bri()
        body = ""
        result = "path=%s&verb=%s&token=%s&timestamp=%s&body=%s"%(path,verb,token,timestamp,body)
        h = hmac.new(str(secret), str(result), hashlib.sha256)
        signature =  base64.b64encode(h.digest())

        payload = {}
        headers = {
          'BRI-Signature': signature,
          'BRI-Timestamp': timestamp,
          'Authorization': token,
        }
        # Create Log
        name = 'Corporate Statements BRI'
        type = 'outgoing'
        request_type = 'get'

        try:
            response = requests.get(url=url,headers=headers,data=payload)
            response_code = response.status_code
            content = response.content
            jml_data = 0
            if response_code == 200:
                content = json.loads(response.content)
                datas = content.get('data')
                jml_data = len(datas)
                
            self.env['teds.b2b.api.log'].sudo().create_log_api(name,type,url,request_type,"",response_code,content,jml_data)
            return {'status':1,'response':response}
        except Exception as err:
            error = "Corporate Statements BRI %s"%(err)
            _logger.warning(error)
            self.env['teds.b2b.api.log'].sudo().create_log_api(name,type,False,request_type,'',False,error)
            
            # Send Notification Slack
            url_slack = "https://hooks.slack.com/services/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"
            # self.send_nonitication_slack(url_slack,error)
            return {'status':0}       
                   

     
    @api.multi
    def schedule_statements_bri(self):
        try:
            query = """
                SELECT b.id
                , MIN((jam||':'||menit)::time) as schedule_time 
                , b.name as no_rekening
                , COALESCE((b.last_fetch + INTERVAL '7 hours')::date,now()::date) as last_fetch
                , b.account_id
                , b.branch_id
                , ac.base_url
                , ac.id as config_id
                , aa.code as coa
                , current_date as end_date
                , current_date - 1 as h_min_1
                FROM teds_b2b_master_bank b
                INNER JOIN teds_b2b_api_config ac ON ac.id = b.config_id
                INNER JOIN account_account aa ON aa.id = b.account_id
                INNER JOIN teds_b2b_api_schedule s ON s.id = b.schedule_id
                INNER JOIN teds_b2b_api_schedule_detail sd ON
                (
                    (b.last_fetch + INTERVAL '7 hours')::date = current_date 
                    AND (b.last_fetch + INTERVAL '7 hours')::time < (jam||':'||menit)::time 
                    AND (jam||':'||menit)::time < current_time 
                )
                OR 
                (
                    (b.last_fetch + INTERVAL '7 hours'):: date < current_date 
                    AND (jam||':'||menit)::time < current_time
                )
                WHERE ac.code = 'BRI'
                GROUP BY b.id,ac.id,aa.id
                ORDER BY schedule_time ASC
                LIMIT 10          
            """
            self._cr.execute (query)
            ress =  self._cr.dictfetchall()
            for res in ress:
                master_id = res.get('id')
                no_rekening = res.get('no_rekening')
                base_url = res.get('base_url')
                account_id = res.get('account_id')
                branch_id = res.get('branch_id')
                start_date = res.get('last_fetch')
                coa = res.get('coa')
                end_date = res.get('end_date')
                h_min_1 = res.get('h_min_1')
                config_id = self.browse(res.get('config_id'))
                statement_account = self.corporate_account_statements_bri(config_id,no_rekening,base_url,start_date,end_date)

                if statement_account.get('status') == 1:
                    response = statement_account.get('response')
                    if response.status_code == 200:
                        content = json.loads(response.content)
                        datas = content.get('data')

                        #### Delete All Transation PEND Bank Mutation ###
                        delete_bm = """
                            DELETE FROM teds_bank_mutasi
                            WHERE date IS NULL
                            AND account_id = %d
                            AND branch_id = %d
                            AND format = 'bri'
                            AND state = 'Outstanding'
                        """  %(account_id,branch_id)
                        self._cr.execute(delete_bm)

                        for data in datas:
                            # Data Responses #
                            mutasi_debet = data.get('mutasi_debet')
                            ket_tran = data.get('ket_tran') 
                            saldo_akhir_mutasi = data.get('saldo_akhir_mutasi')
                            channel_id = data.get('channel_id') 
                            tanggal_tran = data.get('tanggal_tran') 
                            saldo_awal_mutasi = data.get('saldo_awal_mutasi')
                            kode_tran = data.get('kode_tran') 
                            mutasi_kredit = data.get('mutasi_kredit')
                            nomor_rekening = data.get('nomor_rekening') 
                            nomor_reff = data.get('nomor_reff')
                            posisi_neraca = data.get('posisi_neraca')
                            
                            tgl_rk = False
                            if tanggal_tran:
                                tgl_rk = tanggal_tran[0:10]

                            vals = {
                                'remark':ket_tran,
                                'coa':coa,
                                'account_id':account_id,
                                'format':'bri',
                                'no_sistem':'',
                                'branch_id':branch_id,
                            }
                            if posisi_neraca == 'Debit':
                                vals['debit'] = mutasi_debet
                            elif posisi_neraca == 'Kredit':
                                vals['credit'] = mutasi_kredit

                            # Cek h-1 Transaksi Update Date BM
                            if (tgl_rk == start_date) and (tgl_rk == h_min_1):
                                vals['date'] = tgl_rk
                                create_bm = self.env['teds.bank.mutasi'].sudo().create(vals)
                            # Cek tgl hari ini pending
                            elif tgl_rk == end_date:
                                create_bm = self.env['teds.bank.mutasi'].sudo().create(vals)

                        ### Update Bank Status Fetch Statement ###
                        update_master_bank = """
                            UPDATE
                            teds_b2b_master_bank
                            SET last_fetch = '%s'
                            , balance = '%s'
                            WHERE id = %d
                        """ %(datetime.now(),saldo_akhir_mutasi,master_id)
                        self._cr.execute(update_master_bank)        
            
        except Exception as err:
            error = "Exception Statements BRI %s"%(err)
            _logger.warning(error)

            # Send Notification Slack
            url_slack = "https://hooks.slack.com/services/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"
            self.send_nonitication_slack(url_slack,error)



