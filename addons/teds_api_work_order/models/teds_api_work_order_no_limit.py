from openerp import models, fields, api
import time
from datetime import datetime
from openerp.exceptions import except_orm, Warning, RedirectWarning

import logging
_logger = logging.getLogger(__name__)


# API
import odoorpc
from pprint import pprint as pp
from json import dumps as json

class WorkOrder(models.Model):
    _inherit = "wtc.work.order"


    @api.multi
    def api_teds_work_order_configuration(self,wo):
        message = False
        config_user = self.env['teds.api.configuration'].search([('branch_id','=',wo.branch_id.id)])
        if not config_user:
            message = 'Silahkan buat configuration terlebih dahulu.'
            _logger.warning('%s' %message) 
            self.env['teds.api.log'].sudo().create({
                'name':'data_not_found',
                'description':message,
                'module_name':'TEDS API WORK ORDER',
                'status':0,
                'model_name':'wtc.work.order',
                'transaction_id':wo.id,
                'origin':wo.name,    
            })
            return False
        else :
            username = config_user.username
            password = config_user.password
            db = config_user.database
            host = config_user.host
            port = config_user.port
            return [username,password,db,host,port]


    @api.multi
    def api_teds_work_order_no_limit(self):
        line = []
        area = self.env['wtc.area'].search([('code','=','AREA_LAMPUNG')],limit=1)
        list_branch = [b.id for b in area.branch_ids] 
        if list_branch :
            work_order = self.search([
                ('state','in',['open','done']),
                ('state_wo','=','finish'),
                ('branch_id','in',list_branch),
                ('status_api','=','draft'),
                ('nomor_sa','!=',False)],limit=100, order='branch_id,id desc')
            if work_order :
                for wo in work_order :
                    _logger.warning('Data found Work Order %s' %(wo.id))
                    configuration=self.api_teds_work_order_configuration(wo)
                    try:
                        if configuration :
                            odoo = odoorpc.ODOO(configuration[3], protocol='jsonrpc', port=configuration[4])
                            odoo.login(configuration[2],configuration[0],configuration[1])  
                            type_service = wo.type
                            alasan_ke_ahass = wo.alasan_ke_ahass
                            kondisi_bensin = wo.bensin
                            for x in wo.work_lines:
                                line.append({
                                    'category':x.categ_id,
                                    'product_code':x.product_id.name,
                                    'qty':x.product_qty,
                                    'qty_spl':x.supply_qty,
                                    'discount':x.discount,
                                    'price':x.price_unit,
                                }) 

                            data = odoo.json('/web/dataset/call',{'model': 'dms.api','method':'dms_service_order_create_no_limit','args':[[], 
                            {
                                'dealer_code': wo.branch_id.code,
                                    'nomor_sa':wo.nomor_sa,
                                    'work_order_name':wo.name,
                                    'service_type':type_service,
                                    'date':wo.date,
                                    'kpb_ke':wo.kpb_ke,
                                    'no_engine':wo.lot_id.name,
                                    'customer_stnk_name':wo.customer_id.name,
                                    'customer_stnk_no_ktp':wo.customer_id.no_ktp,
                                    'customer_stnk_no_hp':wo.customer_id.mobile,
                                    'pembawa_sendiri':False,
                                    'pembawa_name': wo.driver_id.name,
                                    'pembawa_mobile':wo.mobile,
                                    'km':wo.km,  
                                    'alasan_ke_ahass': alasan_ke_ahass, 
                                    'mekanik_tunasId': self._get_tunas_id_sales(wo.mekanik_id.id),    
                                    'keluhan':False, 
                                    'kondisi_bensin':kondisi_bensin,  
                                    'analisa_sa':False,  
                                    'saran_mekanik':False,   
                                    'est_waktu_pendaftaran':False,   
                                    'est_waktu_pengerjaan':False,
                                    'start':wo.start,
                                    'finish':wo.finish,
                                    'detail':line,
                            }]})
                            line=[]
                            result =  data.get('result',False)
                            if result['status'] == 0:
                                _logger.warning('%s' %result.get('message',False)) 
                                self.env['teds.api.log'].sudo().create({
                                    'name':result.get('error',False),
                                    'description':result.get('remark',False),
                                    'module_name':'DMS API WORK ORDER',
                                    'status':result.get('status',False),
                                    'model_name':'wtc.work.order',
                                    'transaction_id':wo.id,
                                    'origin':wo.name,    
                                })

                                query = """
                                    UPDATE wtc_work_order 
                                    SET status_api='error' 
                                    WHERE id = %d
                                """ % (wo.id)
                                self._cr.execute(query)
                            elif result['status'] == 1:
                                _logger.warning('%s' %result.get('message',False)) 
                                query = """
                                    UPDATE wtc_work_order 
                                    SET status_api='done' 
                                    WHERE id = %d
                                """ % (wo.id)
                                self._cr.execute(query)
                        else :
                            query = """
                            UPDATE wtc_work_order 
                            SET status_api='error' 
                            WHERE id = %d
                            """ % (wo.id)
                            self._cr.execute(query)
                    except odoorpc.error.RPCError as exc:
                        _logger.warning('%s' %(exc))
                        self.env['teds.api.log'].sudo().create({
                            'name':'raise_warning',
                            'description':exc,
                            'module_name':'DMS API WORK ORDER',
                            'status':0,
                            'model_name':'wtc.work.order',
                            'transaction_id':wo.id,
                            'origin':wo.name,    
                        })
                        query = """
                            UPDATE wtc_work_order 
                            SET status_api='error' 
                            WHERE id = %d
                        """ % (wo.id)
                        self._cr.execute(query) 
            else:
                _logger.warning('Data Update Error to Draft Work Order')
                update_error = """
                    UPDATE wtc_work_order 
                    SET status_api = 'draft' 
                    WHERE status_api = 'error' """
                self._cr.execute(update_error)

