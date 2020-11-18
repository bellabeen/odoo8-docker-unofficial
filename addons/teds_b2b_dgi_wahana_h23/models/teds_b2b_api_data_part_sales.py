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

    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()

    @api.multi
    def _get_api_prsl_wahana(self, branch, query_date, log=True, noWorkOrder=False):
        api_url = "%s/prsl/read" % self.base_url
        date_format = '%Y-%m-%d %H:%M:%S'

        from_time = datetime.combine(query_date, datetime.min.time())
        to_time = datetime.combine(query_date, datetime.max.time())

        # epoch = int(time.mktime(time.strptime(datetime.now().strftime(date_format), '%Y-%m-%d %H:%M:%S')))
        epoch = int(time.mktime(time.localtime())) # verify pakai time.localtime() or time.gmtime()

        # TOKEN DGI #
        if not self.api_key and not self.api_secret:
            error = "API Key dan API Secret Required !"
            if log:
                self.create_log_error_dgi('DGI H23 Part Sales Wahana',api_url,'post',error,'PRSL')
            return {'status':0,'error':error}

        token_raw = "%s%s%s"%(self.api_key, self.api_secret, epoch)
        token = hashlib.sha256(token_raw).hexdigest()

        headers = {
            "DGI-API-Key":self.api_key,
            "Content-Type":"application/json",
            "X-Request-Time":str(epoch),
            "DGI-API-Token":token
        }
        body = {
            "fromTime": from_time.strftime(date_format),
            "toTime": to_time.strftime(date_format),
        }
        if branch.md_reference:
            body['dealerId'] = branch.md_reference

        if noWorkOrder:
            body['noSO'] = noWorkOrder
  
        response = self.post(name="DGI H23 Part Sales Wahana", url=api_url, body=body, headers=headers, type='incoming', verify=self.verify)
        if response.status_code == 200:
            content = json.loads(response.content)
            # Get Data Response
            data = content.get('data')
            if not data:
                error = "Data Part Sales tidak ditemukan !"
                if noWorkOrder:
                    error = 'Data Part Sales %s tidak ditemukan !' % noWorkOrder
                if not log:
                    raise Warning(error)
                return {'status':1,'data':data}
            if noWorkOrder:
                data = [d for d in data if d.get('noSO')==noWorkOrder]
                if not data:
                    error = 'Data Part Sales %s tidak ditemukan !' % noWorkOrder
                    if not log:
                        raise Warning(error)
                    return {'status':1,'data':data}
            
            query = """
                SELECT md_reference_pkb
                FROM wtc_work_order
                WHERE branch_id = %(branch_id)d
            """ % {'branch_id': branch.id}
            if noWorkOrder:
                query += " AND md_reference_pkb = '%(noWorkOrder)s' " %{'noWorkOrder':noWorkOrder}
            else:
                query += " AND md_reference_pkb IS NOT NULL "
            self._cr.execute(query)
            ress = self._cr.fetchall()
            registered_wo = [res[0] for res in ress]
            data = [d for d in data if d.get('noSO') not in registered_wo]

            if not data:
                error = "Data Part Sales tidak ditemukan !"
                if noWorkOrder:
                    error = 'Data Part Sales %s tidak ditemukan !' % noWorkOrder
                if not log:
                    raise Warning(error)
            return {'status':1, 'data':data}
        else:
            error = "Gagal Get Part Sales.\nStatus Code: %s\nContent: %s" % (response.status_code, response.content)
            if log:
                self.create_log_error_dgi('DGI H23 Part Sales Wahana',api_url,'post',error,'PRSL')
            return {'status':0,'error':error}

    @api.multi
    def _get_data_prsl_wahana_h23(self, branch, query_date=False, log=True, noWorkOrder=False):
        try:
            #default date is today (for scheduler)
            if not query_date:
                query_date = datetime.now()
            #get wo yang status completed/Approved dan belum di proses sebelumnya
            prsls = self._get_api_prsl_wahana(branch, query_date, log, noWorkOrder)
            if prsls.get('status', 0) == 1:
                prsls = prsls.get('data')
                #daftar id wo yg di proses saat ini, mencegah proses data dua kali
                daftar_wo = []

                #data wo yg siap di proses saat ini
                data_orders = {}

                for prsl in prsls:
                    noWorkOrder = prsl.get('noSO')

                    #jika belum di proses, lanjut
                    if noWorkOrder not in daftar_wo:
                        data_orders[noWorkOrder] = {'prsl': prsl}

                        #PROCESS BLOCKING: jika detail parts tidak ada                    
                        parts = prsl.get('parts')
                        if len(parts) == 0:
                            error = 'ID Part Sales %s Data parts kosong !' %noWorkOrder
                            if not log:
                                raise Warning(error)
                            self.create_log_error_dgi('DGI Data Part Sales Wahana',self.base_url,'post',error,'PRSL')
                            continue

                    daftar_wo.append(noWorkOrder)

                result = {
                    'status':1,
                    'data':data_orders.values()
                }
                return result
            else:
                error = prsls.get('error')
                if not log:
                    raise Warning(error)
                result = {
                    'status':0,
                    'error':error
                }
                return result
        except Exception as err:
            result = {
                'status':0,
                'error':err
            }
            _logger.warning("Exception DGI Data Part Sales Wahana >>>>>>>>> %s"%(err))
            if not log:
                raise Warning(err)
            self.create_log_error_dgi('Exception DGI Data Part Sales Wahana',self.base_url,'post',err,'PRSL')


    @api.multi
    def _process_data_prsl_wahana_h23(self, branch, datas, log=True):
        data_work_order = self.env['wtc.work.order']
        data_partner = self.env['res.partner']
        data_product = self.env['product.product']

        md_id = branch.default_supplier_id.id
        pricelist = branch.pricelist_part_sales_id
        branch_id = branch.id

        for data in datas:                
            if not data.get('prsl'):
                error = "Data Part Sales tidak ditemukan !"
                if not log:
                    raise Warning(error)
                continue

            # Definision Variabel
            noWorkOrder = data['prsl'].get('noSO')
            tglSO = data['prsl'].get('tglSO')
            idCustomer = data['prsl'].get('idCustomer')
            namaCustomer = data['prsl'].get('namaCustomer')
            discSO = data['prsl'].get('discSO')
            totalHargaSO = data['prsl'].get('totalHargaSO')
            parts = data['prsl'].get('parts')

            # Customer
            customer_id = data_partner.suspend_security().search([('branch_id','=',branch_id),('md_refrence_id','=',idCustomer)],limit=1).id
            if not customer_id:
                customer_id = data_partner.suspend_security().create({
                    'name':namaCustomer,
                    'mobile':False,
                    'md_refrence_id':idCustomer,
                }).id
            type = 'SLS'

            # Mapping Data Job Sparepart
            part_line = []
            for part in parts:
                idJobPart = part.get('idJob')
                partsNumber = part.get('partsNumber')
                kuantitas = part.get('kuantitas')
                hargaParts = part.get('hargaParts')
                createdTime = part.get('createdTime')
                if not partsNumber:
                    error = 'ID PKB %s Part Number %s tidak terisi !' %(noWorkOrder,partsNumber)   
                    if not log:
                        raise Warning(error)
                    self.create_log_error_dgi('DGI Data Order PKB',self.base_url,'post',error,'PKB')
                    continue

                product_part_obj = data_product.search([('name','=',partsNumber)],limit=1)
                if not product_part_obj:
                    error = 'ID PKB %s Part Number %s not found !' %(noWorkOrder,partsNumber)   
                    if not log:
                        raise Warning(error)
                    self.create_log_error_dgi('DGI Data Order PKB',self.base_url,'post',error,'PKB')
                    continue

                price_get_part = pricelist.sudo().price_get(product_part_obj.id, 1)
                price_part = price_get_part[pricelist.id]    
                if price_part <= 0:
                    error = 'ID PKB %s Harga Part %s tidak boleh 0 !' %(noWorkOrder,product_part_obj.name_get().pop()[1])   
                    if not log:
                        raise Warning(error)
                    self.create_log_error_dgi('DGI Data Order PKB',self.base_url,'post',error,'PKB')
                    continue

                part_line.append([0,False,{
                    'categ_id':'Sparepart',
                    'product_id':product_part_obj.id,
                    'name' :product_part_obj.description,
                    'product_qty':kuantitas, 
                    'price_unit':price_part,
                    'product_uom':1,
                    'warranty': product_part_obj.warranty,
                    'tax_id': [(6,0,[product_part_obj.taxes_id.id])],
                    'tax_id_show': [(6,0,[product_part_obj.taxes_id.id])],
                }])
            
            vals = {
                'branch_id': branch_id,
                'division':'Sparepart',
                'customer_id':customer_id,
                'driver_id':customer_id,
                'type':type,
                'work_lines':part_line,
                'chassis_no':False,
                'product_id':False,
                'no_pol':False,
                'chassis_no':False,
                'tanggal_pembelian':False,
                'mobile':False,
                'lot_id':False,
                'kpb_ke':False,
                'km':False,
                'md_reference_pkb':noWorkOrder,
                # 'md_reference_sa':noWorkOrder,
            }
            create_pkb = self.env['wtc.work.order'].suspend_security().create(vals)
        return True

    @api.multi
    def dgi_wahana_order_prsl(self,branch):
        try:
            get_response = self._get_data_prsl_wahana_h23(branch)
            if get_response.get('status') == 1:
                datas = get_response.get('data')
                if datas:
                    md_id = branch.default_supplier_id.id
                    pricelist = branch.pricelist_part_sales_id
                    if not pricelist:
                        error = "Data Pricelist Part Sales belum disetting di master branch !"
                        if not log:
                            raise Warning(error)
                        self.create_log_error_dgi('DGI Data Order Part Sales',self.base_url,'post',error,'PRSL')
                        
                    if not md_id:
                        error = "Data Main Dealer belum disetting di master branch !"
                        if not log:
                            raise Warning(error)
                        self.create_log_error_dgi('DGI Data Order Part Sales',self.base_url,'post',error,'PRSL')

                            
                    # proses data create sale order draft
                    self._process_data_prsl_wahana_h23(branch,datas)
            else:
                error = get_response.get('error')
                self.create_log_error_dgi('DGI Data Part Sales Wahana',self.base_url,'post',error,'PRSL')
                
                
        except Exception as err:
            _logger.warning("Exception DGI Data Part Sales Wahana >>>>>>>>> %s"%(err))
            self.create_log_error_dgi('Exception Schedule DGI Data Part Sales Wahana',self.base_url,'post',err,'PRSL')
     

    @api.multi
    def schedule_data_work_order_prsl_wahana_h23(self,code):
        branch_config_id = self.env['wtc.branch.config'].suspend_security().search([('name','=',code)],limit=1)
        config_id = branch_config_id.config_dgi_h23_id
        branch = branch_config_id.branch_id
        if config_id and branch:
            return config_id.suspend_security().dgi_wahana_order_prsl(branch)
        else:
            error = 'Branch Config DGI belum di setting !'
            _logger.warning(error)
            self.create_log_error_dgi('DGI Data Part Sales Wahana',False,'post',error,'Schedule')            
    
