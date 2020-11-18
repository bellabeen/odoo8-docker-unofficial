import time
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)
from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning
# API
import odoorpc
from pprint import pprint as pp
from json import dumps as json

import requests

class WorkOrder(models.Model):
    _inherit = "wtc.work.order"

    nomor_sa = fields.Char('No Service Advisor')
    status_api = fields.Selection([
        ('draft','Draft'),
        ('error','Error'),
        ('done','Done'),
    ],default='draft',string='Status API')
    is_error_wo = fields.Boolean('DMS Error?')
    
    @api.multi
    def action_error_detail(self):
        logs = self.env['teds.api.log'].sudo().search([
            ('model_name','=','wtc.work.order'),
            ('transaction_id','=',str(self.id))
        ])
        tree_id = self.env.ref('teds_api_configuration.view_teds_api_log_tree').id
        ids = [log.id for log in logs]
        return {
            'name': ('Error API'),
            'res_model': 'teds.api.log',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'views': [(tree_id, 'tree')],
            'view_mode': 'tree',
            'target': 'current',
            'view_type': 'form',
            'domain':[('id','in',ids)]
        }        

    # MANUAL SLS / NON SLS
    @api.multi
    def api_teds_work_order_manual(self, origin):
        query = """
        SELECT wo.id
        , wo.type
        FROM wtc_work_order wo
        INNER JOIN (
            SELECT acr.branch_id
             FROM wtc_area_cabang_rel acr 
             INNER JOIN wtc_area area ON area.id = acr.area_id
             WHERE area.code = 'AREA_LAMPUNG'
        ) cabang ON cabang.branch_id = wo.branch_id
        WHERE name = '%s'
        AND wo.state in ('open','done')
        AND wo.status_api in ('draft')
        LIMIT 1
        """ %(origin)
        self._cr.execute(query)
        ress = self._cr.dictfetchall()
        for res in ress:
            if res.get('type') != 'SLS':
                self.api_teds_work_order([res.get('id')])
            else:
                self.api_teds_work_order_sls([res.get('id')])

    # 1 menit 1x NON SLS, EXCLUDE ERROR
    @api.multi
    def api_teds_work_order_limit(self):
        query = """
            SELECT wo.id
            FROM wtc_work_order wo
            INNER JOIN (
                SELECT acr.branch_id
                 FROM wtc_area_cabang_rel acr 
                 INNER JOIN wtc_area area ON area.id = acr.area_id
                 WHERE area.code = 'AREA_LAMPUNG'
            ) cabang ON cabang.branch_id = wo.branch_id
            WHERE wo.state in ('open','done')
            AND wo.status_api in ('draft')
            AND wo.type != 'SLS'
            AND wo.nomor_sa is not null
            AND (wo.is_error_wo = False OR wo.is_error_wo IS NULL)
            ORDER BY wo.id ASC
            LIMIT 20
        """
        self._cr.execute(query)
        ress = self._cr.dictfetchall()
        if ress:
            self.api_teds_work_order([res.get('id') for res in ress])
    
    # 1 menit 1x SLS / NON SLS ERROR
    @api.multi
    def api_teds_work_order_error(self):
        query = """
            SELECT wo.id
            , wo.type
            FROM wtc_work_order wo
            INNER JOIN (
                SELECT acr.branch_id
                 FROM wtc_area_cabang_rel acr 
                 INNER JOIN wtc_area area ON area.id = acr.area_id
                 WHERE area.code = 'AREA_LAMPUNG'
            ) cabang ON cabang.branch_id = wo.branch_id
            WHERE wo.state in ('open','done')
            AND wo.status_api in ('draft')
            AND wo.is_error_wo = True
            ORDER BY wo.id,wo.type ASC
            LIMIT 20
        """
        self._cr.execute(query)
        ress = self._cr.dictfetchall()
        non_sls = []
        sls = []
        for res in ress:
            if res.get('type') != 'SLS':
                non_sls.append(res.get('id'))
            else:
                sls.append(res.get('id'))

        if non_sls:
            self.api_teds_work_order(non_sls)
        if sls:
            self.api_teds_work_order_sls(sls)

        # Update WO status API error to draft
        else:
            _logger.warning('Data Update Error to Draft Work Order')
            update_error = """
                UPDATE wtc_work_order 
                SET status_api = 'draft' 
                WHERE status_api = 'error'
            """
            self._cr.execute(update_error)

    # 1 menit 1x SLS, EXCLUDE ERROR
    @api.multi
    def api_teds_work_order_part_sales(self):
        query = """
            SELECT wo.id
            FROM wtc_work_order wo
            INNER JOIN (
                SELECT acr.branch_id
                 FROM wtc_area_cabang_rel acr 
                 INNER JOIN wtc_area area ON area.id = acr.area_id
                 WHERE area.code = 'AREA_LAMPUNG'
            ) cabang ON cabang.branch_id = wo.branch_id
            WHERE wo.state in ('open','done')
            AND wo.status_api in ('draft')
            AND type = 'SLS'
            AND date >= '2018-12-30'
            AND (is_error_wo = False OR is_error_wo IS NULL)
            ORDER BY id ASC
            LIMIT 20
        """
        self._cr.execute(query)
        ress = self._cr.dictfetchall()
        if ress:
            self.api_teds_work_order_sls([res.get('id') for res in ress])

    @api.multi
    def api_teds_work_order(self,datas):
        log_obj = self.env['teds.api.log']
        for data in datas:
            work_order = self.env['wtc.work.order'].sudo().browse(data)
            if work_order:
                _logger.warning('Data found %s (ID %d)' % (work_order.name, work_order.id))
            message = False
        
            # API Config
            config_user = self.env['teds.api.configuration'].search([('branch_id','=',work_order.branch_id.id)])
            if not config_user:
                message = 'Silahkan buat configuration terlebih dahulu.'
                _logger.warning('%s' % message)
                cek_log = log_obj.search([
                    ('name','=','data_not_found'),
                    ('description','=',message),
                    ('module_name','=','TEDS API WORK ORDER'),
                    ('model_name','=','wtc.work.order'),
                    ('transaction_id','=',work_order.id),
                    ('origin','=',work_order.name)],limit=1)
                if not cek_log:
                    log_obj.sudo().create({
                        'name':'data_not_found',
                        'description':message,
                        'module_name':'TEDS API WORK ORDER',
                        'status':0,
                        'model_name':'wtc.work.order',
                        'transaction_id':work_order.id,
                        'origin':work_order.name,    
                    })
            # Type Service
            # [KPB =  1 , REG = 2 , WAR = 3 , CLA = 4 , PDI = 5]
            type_service = work_order.type
            if type_service not in ['KPB','REG','WAR','CLA','PDI','HOTLINE']:
                message = 'Tipe service %s tidak dikenal' % (type_service)
                _logger.warning('%s' % message)
                cek_log =  log_obj.search([
                    ('name','=','data_not_found'),
                    ('description','=',message),
                    ('module_name','=','TEDS API WORK ORDER'),
                    ('model_name','=','wtc.work.order'),
                    ('transaction_id','=',work_order.id),
                    ('origin','=',work_order.name)],limit=1)
                if not cek_log:
                    log_obj.sudo().create({
                        'name':'data_not_found',
                        'description':message,
                        'module_name':'TEDS API WORK ORDER',
                        'status':0,
                        'model_name':'wtc.work.order',
                        'transaction_id':work_order.id,
                        'origin':work_order.name,    
                    })
            if type_service == 'PDI':
                type_service = 'REG'
            
            # Alasan ke AHASS
            alasan_ke_ahass = work_order.alasan_ke_ahass
            # Keluhan Konsumen
            keluhan_konsumen = work_order.note
            # Kondisi Bensin
            # [25% = 1 , 50% = 2 , 75% = 3 , 100% = 4]
            kondisi_bensin = int(work_order.bensin)
            if kondisi_bensin == 0 or kondisi_bensin == 25:
                kondisi_bensin = 1
            elif kondisi_bensin == 50:
                kondisi_bensin = 2
            elif kondisi_bensin == 75:
                kondisi_bensin = 3
            elif kondisi_bensin == 100:
                kondisi_bensin = 4
            else:
                message = 'Bensin %s tidak dikenal' % (kondisi_bensin)
                _logger.warning('%s' % message)
                cek_log = log_obj.search([
                    ('name','=','data_not_found'),
                    ('description','=',message),
                    ('module_name','=','TEDS API WORK ORDER'),
                    ('model_name','=','wtc.work.order'),
                    ('transaction_id','=',work_order.id),
                    ('origin','=',work_order.name)],limit=1)
                if not cek_log:
                    log_obj.sudo().create({
                        'name':'data_not_found',
                        'description':message,
                        'module_name':'TEDS API WORK ORDER',
                        'status':0,
                        'model_name':'wtc.work.order',
                        'transaction_id':work_order.id,
                        'origin':work_order.name,    
                    })
            # Detail
            line = []
            query = """ 
                SELECT 
                    wol.categ_id AS category,
                    pp.name_template AS product_code,
                    SUM(
                        CASE 
                            WHEN wol.categ_id = 'Sparepart' AND wol.price_unit > 0 THEN wol.supply_qty 
                            ELSE 0 
                        END
                    ) AS qty_spl_part,
                    SUM(
                        CASE 
                            WHEN wol.categ_id = 'Service' AND wol.price_unit > 0 THEN wol.product_qty 
                            ELSE 0 
                        END
                    ) AS qty_spl_service,
                    SUM(wol.discount) AS discount_cumulative,
                    SUM(
                        CASE 
                            WHEN wol.categ_id = 'Service' THEN wol.product_qty * wol.price_unit 
                            WHEN wol.categ_id = 'Sparepart' THEN wol.supply_qty * wol.price_unit 
                        END
                    ) AS price_cumulative
                FROM wtc_work_order_line wol 
                LEFT JOIN product_product pp ON wol.product_id = pp.id
                WHERE wol.work_order_id = %d 
                GROUP BY 1, 2
            """ % (work_order.id)
            self._cr.execute(query)
            ress = self._cr.dictfetchall()
            for res in ress:
                supply_qty = 0
                if res.get('category',False) == 'Service':
                    supply_qty = float(res.get('qty_spl_service',0))
                elif res.get('category',False) == 'Sparepart':
                    supply_qty = float(res.get('qty_spl_part',0))
                else:
                    message = '[DETAIL] Kategori %s tidak valid' % (res.get('category',False))
                    _logger.warning('%s' % message)
                    cek_log = log_obj.search([
                        ('name','=','data_not_valid'),
                        ('description','=',message),
                        ('module_name','=','TEDS API WORK ORDER'),
                        ('model_name','=','wtc.work.order'),
                        ('transaction_id','=',work_order.id),
                        ('origin','=',work_order.name)],limit=1)
                    if not cek_log:
                        log_obj.sudo().create({
                            'name':'data_not_valid',
                            'description':message,
                            'module_name':'TEDS API WORK ORDER',
                            'status':0,
                            'model_name':'wtc.work.order',
                            'transaction_id':work_order.id,
                            'origin':work_order.name,    
                        })                
                try:
                    discount = float(res.get('discount_cumulative',0))/supply_qty
                    price = float(res.get('price_cumulative',0))/supply_qty
                except Exception as exc:
                    message = 'Setup detail %s: %s' % (work_order.name, exc)
                    _logger.warning('%s' % message)
                    cek_log = log_obj.search([
                        ('name','=','error'),
                        ('description','=',message),
                        ('module_name','=','TEDS API WORK ORDER'),
                        ('model_name','=','wtc.work.order'),
                        ('transaction_id','=',work_order.id),
                        ('origin','=',work_order.name)],limit=1)
                    if not cek_log:
                        log_obj.sudo().create({
                            'name':'error',
                            'description':message,
                            'module_name':'TEDS API WORK ORDER',
                            'status':0,
                            'model_name':'wtc.work.order',
                            'transaction_id':work_order.id,
                            'origin':work_order.name,    
                        })
                line.append({
                    'category': res.get('category',False),
                    'product_code': res.get('product_code',False),
                    'qty': supply_qty,
                    # 'qty_spl': 0,
                    'diskon': discount,
                    'price': price,
                })
            # Hasil cek: ada potensi error
            if message:
                query = """
                    UPDATE wtc_work_order 
                    SET status_api = 'error' 
                    WHERE id = %d
                """ % (work_order.id)
                self._cr.execute(query)
            # Hasil cek: OK => Send to DMS
            else:
                try:
                    username = config_user.username
                    password = config_user.password
                    db = config_user.database
                    host = config_user.host
                    port = config_user.port
                    odoo = odoorpc.ODOO(host, protocol='jsonrpc', port=port)
                    odoo.login(db,username,password)
                    data = odoo.json('/web/dataset/call', {
                        'model': 'dms.api',
                        'method': 'dms_service_order_create',
                        'args': [[], {
                            'dealer_code': work_order.branch_id.code,
                            'nomor_sa': work_order.nomor_sa,
                            'service_type': type_service,
                            'date': work_order.date,
                            'kpb_ke': work_order.kpb_ke,
                            'no_engine': work_order.lot_id.name,
                            'pembawa_sendiri': True if work_order.customer_id.id == work_order.driver_id.id else False,
                            'pembawa_name': work_order.driver_id.name,
                            'pembawa_mobile': work_order.mobile,
                            'km': work_order.km,
                            'alasan_ke_ahass': alasan_ke_ahass,
                            'kebutuhan_konsumen': keluhan_konsumen,
                            'mekanik_tunasId': self._get_tunas_id_sales(work_order.mekanik_id.id),
                            'kondisi_bensin': kondisi_bensin,
                            'start': work_order.start,
                            'finish': work_order.finish,
                            'detail': line,
                        }]
                    })
                    # finally
                    result = data.get('result',False)
                    if result:
                        if result['status'] == 0:
                            _logger.warning('%s' % result.get('message',False))
                            cek_log =  log_obj.search([
                                ('name','=',result.get('error',False)),
                                ('description','=',result.get('remark',False)),
                                ('module_name','=','DMS API WORK ORDER'),
                                ('model_name','=','wtc.work.order'),
                                ('transaction_id','=',work_order.id),
                                ('origin','=',work_order.name)],limit=1)
                            if not cek_log:
                                log_obj.sudo().create({
                                    'name':result.get('error',False),
                                    'description':result.get('remark',False),
                                    'module_name':'DMS API WORK ORDER',
                                    'status':result.get('status',False),
                                    'model_name':'wtc.work.order',
                                    'transaction_id':work_order.id,
                                    'origin':work_order.name,    
                                })
                            query = """
                                UPDATE wtc_work_order 
                                SET status_api = 'error', is_error_wo = True 
                                WHERE id = %d
                            """ % (work_order.id)
                            self._cr.execute(query)
                        elif result['status'] == 1:
                            _logger.warning('%s' % result.get('message',False)) 
                            query = """
                                UPDATE wtc_work_order 
                                SET status_api = 'done', is_error_wo = False 
                                WHERE id = %d;

                                DELETE FROM teds_api_log
                                WHERE model_name = 'wtc.work.order'
                                AND origin = '%s';
                            """ % (work_order.id, work_order.name)
                            self._cr.execute(query)
                except odoorpc.error.RPCError as exc:
                    _logger.warning('%s'% (exc))
                    cek_log = log_obj.search([
                        ('name','=','raise_warning'),
                        ('description','=',exc),
                        ('module_name','=','DMS API WORK ORDER'),
                        ('model_name','=','wtc.work.order'),
                        ('transaction_id','=',work_order.id),
                        ('origin','=',work_order.name)],limit=1)
                    if not cek_log:
                        log_obj.sudo().create({
                            'name':'raise_warning',
                            'description':exc,
                            'module_name':'DMS API WORK ORDER',
                            'status':0,
                            'model_name':'wtc.work.order',
                            'transaction_id':work_order.id,
                            'origin':work_order.name,    
                        })
                    query = """
                        UPDATE wtc_work_order 
                        SET status_api = 'error', is_error_wo = True 
                        WHERE id = %d
                    """ % (work_order.id)
                    self._cr.execute(query)    


    @api.multi
    def api_teds_work_order_sls(self,datas):
        log_obj = self.env['teds.api.log']
        for data in datas:
            work_order = self.env['wtc.work.order'].sudo().browse(data)
            if work_order:
                _logger.warning('Data found %s SLS (ID %d)' % (work_order.name, work_order.id))
            message = False
            # API Config
            config_user = self.env['teds.api.configuration'].search([('branch_id','=',work_order.branch_id.id)])
            if not config_user:
                message = 'Silahkan buat configuration terlebih dahulu.'
                _logger.warning('%s' % message)
                cek_log =  log_obj.search([
                    ('name','=','data_not_found'),
                    ('description','=',message),
                    ('module_name','=','TEDS API WORK ORDER SLS'),
                    ('model_name','=','wtc.work.order'),
                    ('transaction_id','=',work_order.id),
                    ('origin','=',work_order.name)],limit=1)
                if not cek_log:
                    log_obj.sudo().create({
                        'name':'data_not_found',
                        'description':message,
                        'module_name':'TEDS API WORK ORDER SLS',
                        'status':0,
                        'model_name':'wtc.work.order',
                        'transaction_id':work_order.id,
                        'origin':work_order.name,    
                    })
            # Detail
            line = []
            query = """ 
                SELECT 
                    wol.categ_id AS category,
                    pp.name_template AS product_code,
                    SUM(
                        CASE 
                            WHEN wol.categ_id = 'Sparepart' AND wol.price_unit > 0 THEN wol.supply_qty 
                            ELSE 0 
                        END
                    ) AS qty_spl_part,
                    SUM(
                        CASE 
                            WHEN wol.categ_id = 'Service' AND wol.price_unit > 0 THEN wol.product_qty 
                            ELSE 0 
                        END
                    ) AS qty_spl_service,
                    SUM(wol.discount) AS discount_cumulative,
                    SUM(
                        CASE 
                            WHEN wol.categ_id = 'Service' THEN wol.product_qty * wol.price_unit 
                            WHEN wol.categ_id = 'Sparepart' THEN wol.supply_qty * wol.price_unit 
                        END
                    ) AS price_cumulative
                FROM wtc_work_order_line wol 
                LEFT JOIN product_product pp ON wol.product_id = pp.id
                WHERE wol.work_order_id = %d 
                GROUP BY 1, 2
            """ % (work_order.id)
            self._cr.execute(query)
            ress = self._cr.dictfetchall()
            for res in ress:
                supply_qty = 0
                if res.get('category',False) == 'Service':
                    supply_qty = float(res.get('qty_spl_service',0))
                elif res.get('category',False) == 'Sparepart':
                    supply_qty = float(res.get('qty_spl_part',0))
                else:
                    message = '[DETAIL] Kategori %s tidak valid' % (res.get('category',False))
                    _logger.warning('%s' % message)
                    cek_log = log_obj.search([
                        ('name','=','data_not_valid'),
                        ('description','=',message),
                        ('module_name','=','TEDS API WORK ORDER SLS'),
                        ('model_name','=','wtc.work.order'),
                        ('transaction_id','=',work_order.id),
                        ('origin','=',work_order.name)],limit=1)
                    if not cek_log:
                        log_obj.sudo().create({
                            'name':'data_not_valid',
                            'description':message,
                            'module_name':'TEDS API WORK ORDER SLS',
                            'status':0,
                            'model_name':'wtc.work.order',
                            'transaction_id':work_order.id,
                            'origin':work_order.name,    
                        })
                
                try:
                    discount = float(res.get('discount_cumulative',0))/supply_qty
                    price = float(res.get('price_cumulative',0))/supply_qty
                except Exception as exc:
                    message = 'Setup detail %s: %s' % (work_order.name, exc)
                    _logger.warning('%s' % message)
                    cek_log = log_obj.search([
                        ('name','=','error'),
                        ('description','=',message),
                        ('module_name','=','TEDS API WORK ORDER'),
                        ('model_name','=','wtc.work.order'),
                        ('transaction_id','=',work_order.id),
                        ('origin','=',work_order.name)],limit=1)
                    if not cek_log:
                        log_obj.sudo().create({
                            'name':'error',
                            'description':message,
                            'module_name':'TEDS API WORK ORDER',
                            'status':0,
                            'model_name':'wtc.work.order',
                            'transaction_id':work_order.id,
                            'origin':work_order.name,    
                        })
                line.append({
                    'product_code': res.get('product_code',False),
                    'qty': supply_qty,
                    # 'qty_spl': 0,
                    'discount': discount,
                    'price': price,
                })
            # Hasil cek: ada potensi error
            if message:
                query = """
                    UPDATE wtc_work_order 
                    SET status_api = 'error' 
                    WHERE id = %d
                """ % (work_order.id)
                self._cr.execute(query)
            # Hasil cek: OK => Send to DMS
            else:
                try:
                    username = config_user.username
                    password = config_user.password
                    db = config_user.database
                    host = config_user.host
                    port = config_user.port
                    odoo = odoorpc.ODOO(host, protocol='jsonrpc', port=port)
                    odoo.login(db,username,password)            
            
                    vals = {
                        'dealer_code': work_order.branch_id.code,
                        'date': work_order.date,
                        'work_order_name': work_order.name,
                        'no_engine': work_order.lot_id.name,
                        'customer_stnk_no_ktp': work_order.customer_id.no_ktp,
                        'customer_stnk_name': work_order.customer_id.name,
                        'customer_stnk_street': work_order.customer_id.street,
                        'customer_stnk_rt': work_order.customer_id.rt,
                        'customer_stnk_rw': work_order.customer_id.rw,
                        'customer_stnk_prov': work_order.customer_id.state_id.code,
                        'customer_stnk_kota': work_order.customer_id.city_id.code,
                        'customer_stnk_kecamatan': work_order.customer_id.kecamatan_id.code,
                        'customer_stnk_kelurahan': work_order.customer_id.zip_id.zip,
                        'customer_type': work_order.type_customer,
                        'detail': line,
                    }
                    if work_order.customer_id.branch_id.id == work_order.branch_id.id:
                        if work_order.customer_id.id == work_order.driver_id.id:
                            vals.update({'customer_stnk_no_hp': work_order.mobile})
                        else:
                            vals.update({'customer_stnk_no_hp': work_order.customer_id.mobile})
                    if work_order.nomor_sa:
                        vals.update({'nomor_sa': work_order.nomor_sa})
                    data = odoo.json('/web/dataset/call', {
                        'model': 'dms.api',
                        'method': 'dms_part_sales_create',
                        'args': [[], vals]
                    })
                    # finally
                    result =  data.get('result',False)
                    if result:
                        if result['status'] == 0:
                            _logger.warning('%s' % result.get('message',False)) 
                            cek_log =  log_obj.search([
                                ('name','=',result.get('error',False)),
                                ('description','=',result.get('remark',False)),
                                ('module_name','=','DMS API WORK ORDER SLS'),
                                ('model_name','=','wtc.work.order'),
                                ('transaction_id','=',work_order.id),
                                ('origin','=',work_order.name)],limit=1)
                            if not cek_log:
                                log_obj.sudo().create({
                                    'name':result.get('error',False),
                                    'description':result.get('remark',False),
                                    'module_name':'DMS API WORK ORDER SLS',
                                    'status':result.get('status',False),
                                    'model_name':'wtc.work.order',
                                    'transaction_id':work_order.id,
                                    'origin':work_order.name,    
                                })
                            query = """
                                UPDATE wtc_work_order 
                                SET status_api = 'error', is_error_wo = True
                                WHERE id = %d
                            """ % (work_order.id)
                            self._cr.execute(query)
                        elif result['status'] == 1:
                            _logger.warning('%s' % result.get('message',False)) 
                            query = """
                                UPDATE wtc_work_order 
                                SET status_api = 'done', is_error_wo = False 
                                WHERE id = %d;
                                
                                DELETE FROM teds_api_log
                                WHERE model_name = 'wtc.work.order'
                                AND origin = '%s';
                            """ % (work_order.id, work_order.name)
                            self._cr.execute(query)
                except odoorpc.error.RPCError as exc:
                    _logger.warning('%s' %(exc))
                    cek_log =  log_obj.search([
                        ('name','=','raise_warning'),
                        ('description','=',exc),
                        ('module_name','=','DMS API WORK ORDER SLS'),
                        ('model_name','=','wtc.work.order'),
                        ('transaction_id','=',work_order.id),
                        ('origin','=',work_order.name)],limit=1)
                    if not cek_log:
                        log_obj.sudo().create({
                            'name':'raise_warning',
                            'description':exc,
                            'module_name':'DMS API WORK ORDER SLS',
                            'status':0,
                            'model_name':'wtc.work.order',
                            'transaction_id':work_order.id,
                            'origin':work_order.name,    
                        })
                    query = """
                        UPDATE wtc_work_order 
                        SET status_api = 'error', is_error_wo = True
                        WHERE id = %d
                    """ % (work_order.id)
                    self._cr.execute(query)

    def _get_tunas_id_sales(self,user_id):
        nip = False 
        emp = self.env['hr.employee'].sudo().search([('user_id','=',user_id)],limit=1)
        if emp:
            nip = emp.code_honda
        return nip