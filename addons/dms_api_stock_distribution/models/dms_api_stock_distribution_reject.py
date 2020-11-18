from datetime import timedelta,datetime
from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning

import logging
_logger = logging.getLogger(__name__)

# API
import odoorpc
from pprint import pprint as pp
from json import dumps as json

import requests

class StockDsistribution(models.Model):
    _inherit = "wtc.stock.distribution"

    @api.multi
    def api_reject_stock_distribution(self):
        message = False
        module_name = 'TEDS API STOCK DISTRIBUTION REJECT'
        module_model_name = 'wtc.stock.distribution'
        search = """
            SELECT sd.id
            FROM wtc_stock_distribution sd
            INNER JOIN wtc_purchase_order_type pot ON sd.type_id = pot.id
            INNER JOIN wtc_branch b ON b.id = sd.branch_id
            WHERE b.branch_type = 'MD'
            AND sd.state = 'reject' 
            AND sd.status_api != 'done'
            AND sd.dms_po_name IS NOT NULL
            AND pot.name != 'Hotline'
            ORDER BY sd.id ASC
            LIMIT 20
        """
        self._cr.execute(search)
        ress = self._cr.dictfetchall()
        if ress:
            for res in ress:
                obj = res.get('id')
                _logger.warning('Data found Distribution REJECT %s'%(obj))
                
                dist = self.env['wtc.stock.distribution'].browse(obj)
            
                line = []
                config_user = self.env['teds.api.configuration'].search([('branch_id','=',dist.branch_id.id)])
                if not config_user:
                    message = 'Silahkan buat configuration terlebih dahulu untuk bisa mengakses ke DMS.'
                    _logger.warning('%s' %message) 
                    self.env['teds.api.log'].sudo().create({
                        'name':'data_not_found',
                        'description':message,
                        'module_name':'DMS API STOCK DISTRIBUTION (Reject)',
                        'status':0,
                        'model_name':'wtc.stock.distribution',
                        'transaction_id':dist.id,
                        'origin':dist.name,    
                    })
                    continue
               
                try:
                    username = config_user.username
                    password = config_user.password
                    db = config_user.database
                    host = config_user.host
                    port = config_user.port
                    odoo = odoorpc.ODOO(host, protocol='jsonrpc', port=port)
                    odoo.login(db,username,password)
                    # odoo.save(username) 
                    data = odoo.json(
                        '/web/dataset/call',
                        {'model': 'dms.api','method':'create_purchase_order_reject',
                        'args':[[], 
                            {   
                                'dms_po_name':dist.dms_po_name,
                                'dms_model_name':dist.dms_model_name,
                        }]})
        
                    # finally
                    result =  data.get('result',False)
                    if result:
                        result_status = result.get('status')
                        result_message = result.get('message',False)
                        result_error = result.get('error',False)
                        result_remark = result.get('remark',False)
                        
                        if result_status == 0:
                            _logger.warning(result_message) 
                            self.env['teds.api.log'].sudo().create({
                                'name':result_error,
                                'description':result_remark,
                                'module_name':module_name,
                                'status':0,
                                'model_name':module_model_name,
                                'transaction_id':dist.id,
                                'origin':dist.name,    
                            })
                            query = """
                                UPDATE wtc_stock_distribution 
                                SET status_api='error' 
                                WHERE id = %d
                            """ % (dist.id)
                            self._cr.execute(query)
                            
                        elif result_status == 1:
                            _logger.warning(result_message)
                            query = """
                                UPDATE wtc_stock_distribution 
                                SET status_api='done' 
                                WHERE id = %d
                            """ % (dist.id)

                            self._cr.execute(query) 
                    else:
                        # Response tidak ada 
                        message = 'Stock Distribution Reject %s Result not found !' %(dist.name)
                        _logger.warning(message) 
                        self.env['teds.api.log'].sudo().create({
                            'name':'data_not_found',
                            'description':message,
                            'module_name':module_name,
                            'status':0,
                            'model_name':module_model_name,
                            'transaction_id':dist.id,
                            'origin':dist.name,    
                        })
                        query = """
                            UPDATE wtc_stock_distribution
                            SET status_api='error' 
                            WHERE id = %d
                        """ % (dist.id)
                        self._cr.execute(query)
                except odoorpc.error.RPCError as exc:
                    _logger.warning('%s' %(exc))
                    self.env['teds.api.log'].sudo().create({
                        'name':'raise_warning',
                        'description':exc,
                        'module_name':module_name,
                        'status':0,
                        'model_name':module_model_name,
                        'transaction_id':dist.id,
                        'origin':dist.name,    
                    })

                    query = """
                        UPDATE wtc_stock_distribution 
                        SET status_api='error' 
                        WHERE id = %d
                    """ % (dist.id)
                    self._cr.execute(query)   

        else:
            _logger.warning('Data UPDATE ERROR to Draft Distribution REJECT')
            update_error = """
                    UPDATE wtc_stock_distribution 
                    SET status_api = 'draft' 
                    WHERE status_api = 'error'
                """
            self._cr.execute(update_error)

    @api.multi
    def api_reject_stock_distribution_hotline(self, vals):
        cek_group = self.env['res.users'].has_group('dms_api_stock_distribution.group_dms_api_stock_distribution_sparepart_read')
        if not cek_group:
            return {
                'status':0,
                'error':'not_authorized',
                'remark':'User tidak memiliki hak akses.'
            }
        # variabel untuk menampung nilai PO
        dms_po_name = False
        dms_model_name = False
        # checking: mandatory fields must exist!
        try:
            # checking: mandatory field tidak boleh False
            for key, i in vals.iteritems():
                if not i:
                    return {
                        'status': 0,
                        'error': 'empty_field',
                        'remark': 'Field %s harus diisi.' % (key)
                    }
            # tampung data dari TEDS
            dms_model_name = vals['dms_model_name'] # nama model transaksi DMS
            dms_po_name = vals['dms_po_name'] # nomor PO DMS
        except KeyError as e:
            return {
                'status': 0,
                'error': 'mandatory_field',
                'remark': 'Fields ini tidak ada: %s.' % (e.args[0])
            }
        # import ipdb
        # ipdb.set_trace()
        get_sd_query = """
            SELECT 
                sd.id,
                sd.name,
                sd.state
            FROM wtc_stock_distribution sd
            LEFT JOIN wtc_purchase_order_type pot ON sd.type_id = pot.id
            WHERE sd.dms_model_name = '%s'
            AND sd.dms_po_name = '%s'
            AND pot.name = 'Hotline'
            LIMIT 1
        """ % (dms_model_name, dms_po_name)
        self._cr.execute(get_sd_query)
        ress_sd = self._cr.dictfetchone()
        # checking: PO tidak ditemukan
        if not ress_sd:
            return {
                'status': 0,
                'error': 'data_not_found',
                'remark': 'Stock Distribution dengan PO DMS %s' % (dms_po_name)
            }
        # checking: status Stock Distribution
        if ress_sd['state'] == 'reject':
            return {'status':1, 'message':'OK'}
        if ress_sd['state'] != 'confirm':
            return {
                'status': 0,
                'error': 'error',
                'remark': 'Status Stock Distribution %s sudah %s.' % (ress_sd['name'], dict(self._fields['state'].selection).get(ress_sd['state']))
            }
        try:
            sd_obj = self.browse(ress_sd['id'])
            sd_obj.sudo().reject_request()
            return {'status':1, 'message':'OK'}
        except Exception as e:
            return {
                'status': 0,
                'error': 'error',
                'remark': e
            }




        
