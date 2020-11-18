import time
from datetime import datetime
from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError

import logging
_logger = logging.getLogger(__name__)

# API
import odoorpc
from pprint import pprint as pp
from json import dumps as json

class WorkOrder(models.Model):
    _inherit = "wtc.work.order"

    @api.multi
    def api_teds_work_order_bundling(self):
        # pilih area lampung
        # area_ids = self.env['wtc.area'].search([('code','=','AREA_LAMPUNG')],limit=1)

        # branch_id diambil dari master partner bundling
        branch_ids = self.env['teds.api.master.partner.bundling'].search([])
        branch_ids_list = [b.branch_id.id for b in branch_ids]
        
        # WO Bundling hanya pakai servis [JASA BUNDLING 1] 
        # bundling_product_id = self.env['product.product'].search([('default_code', '=', 'JASA BUNDLING 1')]).id
        
        # customer_id diambil dari master partner bundling
        customer_ids = self.env['teds.api.master.partner.bundling.line'].search([])
        customer_ids_list = [cust.partner_id.id for cust in customer_ids]

        # search WO cabang bundling yang
        #   state: open atau done, 
        #   tipe WO Claim,
        #   status API draft
        #   partner: bundling
        wo_bundling_query = """
            SELECT
                wo.*, 
                b.code AS wo_dealer_code 
            FROM wtc_work_order wo
            JOIN wtc_branch b ON wo.branch_id = b.id
            WHERE wo.branch_id IN %s
            AND wo.customer_id IN %s
            AND wo.type = 'CLA'
            AND wo.state IN ('open', 'done')
            AND wo.status_api = 'draft'
            LIMIT 1
        """ % (str(tuple(branch_ids_list)).replace(",)", ")"), str(tuple(customer_ids_list)).replace(",)", ")"))
        self._cr.execute(wo_bundling_query)
        wo_bundling_id = self._cr.dictfetchone()

        # jika WO didapatkan
        if wo_bundling_id:
            # write to logger
            _logger.warning('Data found Work Order %s' %(wo_bundling_id['name']))
            # variabel untuk menampung message error
            message = False
            # search konfigurasi API cabang
            config_user = self.env['teds.api.configuration'].search([('branch_id','=',wo_bundling_id['branch_id'])])
            # jika konfigurasi tidak ada
            if not config_user:
                # write to logger
                message = 'Silahkan buat configuration terlebih dahulu.'
                _logger.warning('%s' %message) 
                # create log di teds
                log_obj = self.env['teds.api.log']
                cek_log =  log_obj.search([
                    ('name','=','data_not_found'),
                    ('description','=',message),
                    ('module_name','=','TEDS API WORK ORDER (BUNDLING)'),
                    ('model_name','=','wtc.work.order'),
                    ('transaction_id','=',wo_bundling_id['id']),
                    ('origin','=',wo_bundling_id['name'])],limit=1)
                if not cek_log:
                    log_obj.sudo().create({
                        'name':'data_not_found',
                        'description':message,
                        'module_name':'TEDS API WORK ORDER (BUNDLING)',
                        'status':0,
                        'model_name':'wtc.work.order',
                        'transaction_id':wo_bundling_id['id'],
                        'origin':wo_bundling_id['name'],    
                    })

            # ipdb.set_trace()

            # cek kondisi bensin
            kondisi_bensin = int(wo_bundling_id['bensin'])
            if kondisi_bensin == 0 or kondisi_bensin == 25:
                kondisi_bensin = 1
            elif kondisi_bensin == 50:
                kondisi_bensin = 2
            elif kondisi_bensin == 75:
                kondisi_bensin = 3
            elif kondisi_bensin == 100:
                kondisi_bensin = 4
            else: # kondisi bensin tidak dikenal
                # write to logger
                message = 'Bensin %s tidak dikenal' %(kondisi_bensin)
                _logger.warning('%s' %message)
                # create log di teds 
                log_obj = self.env['teds.api.log']
                cek_log =  log_obj.search([
                    ('name','=','data_not_found'),
                    ('description','=',message),
                    ('module_name','=','TEDS API WORK ORDER (BUNDLING)'),
                    ('model_name','=','wtc.work.order'),
                    ('transaction_id','=',wo_bundling_id['id']),
                    ('origin','=',wo_bundling_id['name'])],limit=1)
                if not cek_log:
                    log_obj.sudo().create({
                        'name':'data_not_found',
                        'description':message,
                        'module_name':'TEDS API WORK ORDER (BUNDLING)',
                        'status':0,
                        'model_name':'wtc.work.order',
                        'transaction_id':wo_bundling_id['id'],
                        'origin':wo_bundling_id['name'],    
                    })

            # jika ada error
            if message:
                # set status API WO: error
                query = """
                    UPDATE wtc_work_order SET status_api='error' 
                    WHERE id = %d
                """ % (wo_bundling_id['id'])
                self._cr.execute(query)
            else:
                try:
                    # connect to DMS
                    username = config_user.username
                    password = config_user.password
                    db = config_user.database
                    host = config_user.host
                    port = config_user.port
                    odoo = odoorpc.ODOO(host, protocol='jsonrpc', port=port)
                    odoo.login(db,username,password)            
                    
                    # variabel untuk menampung data order line WO
                    line = []
                    # search product specification
                    product_spec_query = """
                        SELECT pt.name AS product_code, pa.code AS color_code
                        FROM product_product pp
                        JOIN product_template pt ON pp.product_tmpl_id = pt.id
                        JOIN product_attribute_value_product_product_rel pp_rel_att ON pp.id = pp_rel_att.prod_id
                        JOIN product_attribute_value pa ON pp_rel_att.att_id = pa.id
                        WHERE pp.id = %s
                    """ % (wo_bundling_id['product_id'])
                    self._cr.execute(product_spec_query)
                    product_spec = self._cr.dictfetchone()
                    # ipdb.set_trace()

                    # search lot and then create array to store the data
                    lot_id = self.env['stock.production.lot'].suspend_security().browse(wo_bundling_id['lot_id'])
                    lot = {
                        'name': lot_id.name,
                        'chassis_no': lot_id.chassis_no,
                        'tahun_pembuatan': lot_id.tahun,
                        'product_code': product_spec['product_code'],
                        'color_code': product_spec['color_code'],
                        'hpp': lot_id.hpp
                    }
                    # ipdb.set_trace()

                    # search customer
                    customer_id = self.env['res.partner'].suspend_security().browse(wo_bundling_id['customer_id'])
                    customer = {
                        'name': customer_id.name,
                        'branch_id': wo_bundling_id['branch_id'],
                        'street': customer_id.street,
                        'rt': customer_id.rt,
                        'rw': customer_id.rw,
                        'state_code': customer_id.state_id.code,
                        'kabupaten_code': customer_id.city_id.code,
                        'kecamatan_code': customer_id.kecamatan_id.code,
                        'kecamatan_name': customer_id.kecamatan_id.name,
                        'zip_code': customer_id.zip_id.zip,
                        'kelurahan_name': customer_id.zip_id.name,
                        'contact': wo_bundling_id['mobile']
                    }
                    # ipdb.set_trace()

                    # search order line dari WO
                    wol_query=""" 
                        SELECT 
                            wol.categ_id AS category,
                            pp.name_template AS product_code,
                            st.name AS location_name,
                            SUM(CASE WHEN wol.categ_id = 'Sparepart' THEN wol.supply_qty ELSE 0 END) AS supply_qty_part,
                            SUM(CASE WHEN wol.categ_id = 'Service' THEN wol.product_qty ELSE 0 END) AS supply_qty_service,
                            wol.discount AS discount,
                            wol.price_unit AS price
                        FROM wtc_work_order_line wol 
                        LEFT JOIN product_product AS pp ON wol.product_id = pp.id
                        LEFT JOIN stock_location st ON wol.location_id = st.id
                        WHERE work_order_id = %s 
                        GROUP BY wol.categ_id, pp.name_template, st.name, wol.discount, wol.price_unit 
                    """%(wo_bundling_id['id'])
                    self._cr.execute (wol_query)
                    ress =  self._cr.dictfetchall()

                    supply_qty = 0
                    for res in ress:
                        if res.get('category',False) == 'Service' :
                            supply_qty = res.get('supply_qty_service', False)
                        else:
                            supply_qty = res.get('supply_qty_part', False)

                        line.append({
                            'category': res.get('category',False),
                            'product_code': res.get('product_code',False),
                            'qty': supply_qty,
                            'qty_spl': supply_qty,
                            'diskon': res.get('discount',False),
                            'price': res.get('price',False),
                        })
                    # ipdb.set_trace()

                    # create data in dms
                    data = odoo.json('/web/dataset/call', {
                        'model': 'dms.api',
                        'method':'dms_service_order_bundling_create',
                        'args':[[], 
                        {
                            # data WO
                            'stock_dealer_code': 'MML',
                            'wo_dealer_code': wo_bundling_id['wo_dealer_code'],
                            'service_type': wo_bundling_id['type'],
                            'date': wo_bundling_id['date'],
                            'km':wo_bundling_id['km'],  
                            'kondisi_bensin': kondisi_bensin,
                            'alasan_ke_ahass': wo_bundling_id['alasan_ke_ahass'], 
                            'mekanik_id_tunas': self._get_tunas_id_sales(wo_bundling_id['mekanik_id']),
                            'mekanik_id_name': self.env['res.users'].suspend_security().browse(wo_bundling_id['mekanik_id']).name,
                            'start': wo_bundling_id['start'],
                            'finish': wo_bundling_id['finish'],
                            'wo_line_ids': line,
                            # data lot
                            'lot': lot,
                            # data pemilik / pembawa unit
                            # 'is_pembawa': True,
                            'customer': customer
                        }]
                    })
                    # ipdb.set_trace()

                    result =  data.get('result',False)
                    # cek hasil API
                    if result:
                        # 0 ?
                        if result['status'] == 0:
                            # write to logger
                            _logger.warning('%s' %result.get('message',False)) 
                            # create log di teds
                            log_obj = self.env['teds.api.log']
                            cek_log =  log_obj.search([
                                ('name','=',result.get('error',False)),
                                ('description','=',result.get('remark',False)),
                                ('module_name','=','DMS API SERVICE ORDER (BUNDLING)'),
                                ('model_name','=','wtc.work.order'),
                                ('transaction_id','=',wo_bundling_id['id']),
                                ('origin','=',wo_bundling_id['name'])],limit=1)
                            if not cek_log:
                                log_obj.sudo().create({
                                    'name':result.get('error',False),
                                    'description': result.get('remark',False),
                                    'module_name':'DMS API SERVICE ORDER (BUNDLING)',
                                    'status':result.get('status',False),
                                    'model_name':'wtc.work.order',
                                    'transaction_id': wo_bundling_id['id'],
                                    'origin': wo_bundling_id['name'],
                                })
                            # set status API WO: error
                            query = """
                                UPDATE wtc_work_order SET status_api = 'error' 
                                WHERE id = %d
                            """ % (wo_bundling_id['id'])
                            self._cr.execute(query)
                        # 1 ?
                        elif result['status'] == 1:
                            # write to logger
                            _logger.warning('%s' %result.get('message',False))
                             # set status API WO: error
                            query = """
                                UPDATE wtc_work_order SET status_api='done' 
                                WHERE id = %d
                            """ % (wo_bundling_id['id'])
                            self._cr.execute(query)
                except odoorpc.error.RPCError as exc: #cant connect
                    # write to logger
                    _logger.warning('%s' %(exc))
                    # create log di teds
                    log_obj = self.env['teds.api.log']
                    cek_log =  log_obj.search([
                        ('name','=','raise_warning'),
                        ('description','=',exc),
                        ('module_name','=','DMS API SERVICE ORDER (BUNDLING)'),
                        ('model_name','=','wtc.work.order'),
                        ('transaction_id','=',wo_bundling_id['id']),
                        ('origin','=',wo_bundling_id['name'])],limit=1)
                    if not cek_log:
                        log_obj.sudo().create({
                            'name':'raise_warning',
                            'description':exc,
                            'module_name':'DMS API SERVICE ORDER (BUNDLING)',
                            'status':0,
                            'model_name':'wtc.work.order',
                            'transaction_id':wo_bundling_id['id'],
                            'origin':wo_bundling_id['name'],
                        })
                    # set status API WO: error
                    query = """
                        UPDATE wtc_work_order SET status_api = 'error' 
                        WHERE id = %d
                    """ % (wo_bundling_id['id'])
                    self._cr.execute(query)
    # UPDATE WO ERROR DI 1 METHOD SAJA
        # else: # update status API WO yang error ke draft
        #     # write to logger
        #     _logger.warning('Data Update Error to Draft Work Order')
        #     # query update status API error ke draft
        #     update_error = """
        #         UPDATE wtc_work_order SET status_api = 'draft' 
        #         WHERE status_api = 'error'
        #     """
        #     # eksekusi query
        #     self._cr.execute(update_error)

class ApiMasterBundling(models.Model):
    _name = "teds.api.master.partner.bundling"
    _description = "Master Partner Bundling"
    _rec_name = "branch_id"

    def _get_default_branch(self):
        branch_ids = False
        branch_ids = self.env.user.branch_ids
        if branch_ids and len(branch_ids) == 1 :
            return branch_ids[0].id
        return False

    branch_id = fields.Many2one("wtc.branch", string="Dealer", default=_get_default_branch)
    partner_bundling_ids = fields.One2many("teds.api.master.partner.bundling.line", "branch_bundling_id", string="Detail Partner Bundling")

    _sql_constraints = [
        ('branch_id_uniq', 'unique(branch_id)', "Perhatian!\nDealer sudah ada.")
    ]

    @api.constrains('partner_bundling_ids')
    def _check_partner_bundling_empty(self):
        if not self.partner_bundling_ids:
            raise ValidationError('Perhatian!\nPartner Bundling harus diisi.')

class ApiMasterBundlingLine(models.Model):
    _name = "teds.api.master.partner.bundling.line"
    _description = "Master Partner Bundling (Detail)"
    _rec_name = "partner_id"

    branch_bundling_id = fields.Many2one('teds.api.master.partner.bundling', string='Dealer Bundling')
    partner_id = fields.Many2one("res.partner", string="Nama Partner", domain=[('branch','=',False),'|', ('customer','=',True), ('direct_customer','=',True)])

    _sql_constraints = [
        ('branch_id_partner_id_uniq', 'unique(branch_bundling_id, partner_id)', "Perhatian!\nPartner sudah ada.")
    ]