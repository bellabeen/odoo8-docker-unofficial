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

    dms_po_name = fields.Char('DMS PO Name')
    dms_transaction_id = fields.Integer('Transaction')
    dms_model_id = fields.Integer('Model')
    dms_model_name = fields.Char('Model Name')

    status_api = fields.Selection([
        ('draft','Draft'),
        ('open','Open'),
        ('error','Error'),
        ('done','Done'),
    ],default='draft',string='Status API')

    @api.multi
    def api_stock_distribution_qty_approved(self):
        message = False
        module_name = 'TEDS API STOCK DISTRIBUTION Qty Approved'
        module_model_name = 'wtc.stock.distribution'

        search = """
            SELECT sd.id
            FROM wtc_stock_distribution sd
            INNER JOIN wtc_branch b ON b.id = sd.branch_id
            WHERE b.branch_type = 'MD'
            AND sd.state in ('open','done')
            AND sd.status_api = 'draft'
            AND sd.dms_po_name IS NOT NULL
            ORDER BY id ASC
            LIMIT 20
        """
        self._cr.execute(search)
        ress = self._cr.dictfetchall()
        if ress:
            for res in ress:
                obj = res.get('id')
                _logger.warning('Data found Distribution Approved Qty %s'%(obj))
                
                dist = self.env['wtc.stock.distribution'].browse(obj)
            
                line = []
                config_user = self.env['teds.api.configuration'].search([('branch_id','=',dist.branch_id.id)])
                if not config_user:
                    message = 'Silahkan buat configuration terlebih dahulu untuk bisa mengakses ke DMS.'
                    _logger.warning('%s' %message) 
                    self.env['teds.api.log'].sudo().create({
                        'name':'data_not_found',
                        'description':message,
                        'module_name':module_name,
                        'status':0,
                        'model_name':module_model_name,
                        'transaction_id':dist.id,
                        'origin':dist.name,    
                    })
                    continue

                # Olah data detail
                for x in dist.distribution_line:
                    if dist.division == "Unit":
                        warna = """
                            SELECT pav.code as warna
                            FROM product_product pp
                            INNER JOIN product_template pt ON pt.id = pp.product_tmpl_id 
                            LEFT JOIN product_attribute_value_product_product_rel rel ON rel.prod_id = pp.id
                            LEFT JOIN product_attribute_value pav ON pav.id = rel.att_id 
                            WHERE pp.id = %d LIMIT 1
                        """ %(x.product_id.id)
                        self._cr.execute(warna)
                        res_warna = self._cr.dictfetchall()
                        warna_code = res_warna[0].get('warna')
                        
                        line.append({
                            'default_code':x.product_id.name,
                            'warna_code':warna_code,
                            'approved_qty':x.approved_qty,
                        })
                    elif dist.division == 'Sparepart':
                        line.append({
                            'default_code':x.product_id.name,
                            'approved_qty':x.approved_qty,
                        })

                # Sudah tidak niat detail transaksi nya di hapus dianggap Done
                if not line:
                    query = """
                        UPDATE wtc_stock_distribution
                        SET status_api = 'done' 
                        WHERE id = %d
                    """ % (dist.id)
                    self._cr.execute(query)
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
                        {'model': 'dms.api','method':'create_purchase_order_qty_approved',
                        'args':[[], 
                            {   
                                'dms_po_name':dist.dms_po_name,
                                'dms_model_name':dist.dms_model_name,
                                'division':dist.division,
                                'line_ids': line,
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
                        message = 'Stock Distribution Approved %s Result not found !' %(dist.name)
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
                    _logger.warning(exc)
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
            _logger.warning('Data UPDATE ERROR to Draft Distribution Qty Approved')
            update_error = """
                    UPDATE wtc_stock_distribution 
                    SET status_api = 'draft' 
                    WHERE status_api = 'error'
                """
            self._cr.execute(update_error)



    @api.multi
    def api_stock_distribution_qty_approved_manual(self,origin):
        raise Warning("Maaf tidak tersedia !")
        message = False
        md_id = self.env['wtc.branch'].sudo().search([('code','=','MML')],limit=1).id
        search = """
            SELECT sd.id
            FROM wtc_stock_distribution sd
            INNER JOIN wtc_branch b ON b.id = sd.branch_id
            WHERE b.branch_type = 'MD'
            AND sd.name = '%s'
            AND sd.state in ('open','done')
            AND sd.status_api = 'draft'
            AND sd.dms_po_name IS NOT NULL
            ORDER BY id ASC
            LIMIT 1
        """ %(origin)
        self._cr.execute(search)
        ress = self._cr.dictfetchall()
        if ress:
            for res in ress:
                obj = res.get('id')
                _logger.warning('Data found Distribution Approved Qty %s'%(obj))
                
                dist = self.env['wtc.stock.distribution'].browse(obj)
            
                line = []
                config_user = self.env['teds.api.configuration'].search([('branch_id','=',dist.branch_id.id)])
                if not config_user:
                    message = 'Silahkan buat configuration terlebih dahulu untuk bisa mengakses ke DMS.'
                    _logger.warning('%s' %message) 
                    self.env['teds.api.log'].sudo().create({
                        'name':'data_not_found',
                        'description':message,
                        'module_name':'DMS API STOCK DISTRIBUTION (Qty Approved)',
                        'status':0,
                        'model_name':'wtc.stock.distribution',
                        'transaction_id':dist.id,
                        'origin':dist.name,    
                    })
                for x in dist.distribution_line:
                    if dist.division == "Unit":
                        warna = """
                                    SELECT pav.code as warna
                                    FROM product_product pp
                                    INNER JOIN product_template pt ON pt.id = pp.product_tmpl_id 
                                    LEFT JOIN product_attribute_value_product_product_rel rel ON rel.prod_id = pp.id
                                    LEFT JOIN product_attribute_value pav ON pav.id = rel.att_id 
                                    WHERE pp.id = %d LIMIT 1
                                """ %(x.product_id.id)
                        self._cr.execute(warna)
                        ress = self._cr.dictfetchall()
                        warna_code = ress[0].get('warna')
                        if warna_code.isdigit():
                            message = 'Code Warna tidak sesuai atau tidak ditemukan'
                            _logger.warning('%s' %message) 
                            self.env['teds.api.log'].sudo().create({
                                'name':'data_not_found',
                                'description':message,
                                'module_name':'DMS API STOCK DISTRIBUTION (Qty Approved)',
                                'status':0,
                                'model_name':'wtc.stock.distribution',
                                'transaction_id':dist.id,
                                'origin':dist.name,    
                            })
                        line.append({
                            'default_code':x.product_id.name,
                            'warna_code':warna_code,
                            'approved_qty':x.approved_qty,
                        })
                    elif dist.division == 'Sparepart':
                        line.append({
                            'default_code':x.product_id.name,
                            'approved_qty':x.approved_qty,
                        })
                if message:
                    query = """
                        UPDATE wtc_stock_distribution 
                        SET status_api='error' 
                        WHERE id = %d
                    """ % (dist.id)
                    self._cr.execute(query)
                else:
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
                            {'model': 'dms.api','method':'create_purchase_order_qty_approved',
                            'args':[[], 
                                {   
                                    'dms_po_name':dist.dms_po_name,
                                    'dms_model_name':dist.dms_model_name,
                                    'division':dist.division,
                                    'line_ids': line,
                            }]})
            
                        # finally
                        result =  data.get('result',False)
                        if result:
                            if result['status'] == 0:
                                _logger.warning('%s' %result.get('message',False)) 
                                self.env['teds.api.log'].sudo().create({
                                    'name':result.get('error',False),
                                    'description':result.get('remark',False),
                                    'module_name':'DMS API STOCK DISTRIBUTION (Qty Approved)',
                                    'status':result.get('status',False),
                                    'model_name':'wtc.stock.distribution',
                                    'transaction_id':dist.id,
                                    'origin':dist.name,    
                                })
                                query = """
                                    UPDATE wtc_stock_distribution 
                                    SET status_api='error' 
                                    WHERE id = %d
                                """ % (dist.id)
                                self._cr.execute(query)
                            elif result['status'] == 1:
                                message = result.get('message',False)
                                _logger.warning('%s' %(message))
                                query = """
                                    UPDATE wtc_stock_distribution 
                                    SET status_api='done' 
                                    WHERE id = %d
                                """ % (dist.id)
                                self._cr.execute(query)    
                    except odoorpc.error.RPCError as exc:
                        _logger.warning('%s' %(exc))
                        self.env['teds.api.log'].sudo().create({
                            'name':'raise_warning',
                            'description':exc,
                            'module_name':'DMS API STOCK DISTRIBUTION (Qty Approved)',
                            'status':0,
                            'model_name':'wtc.stock.distribution',
                            'transaction_id':dist.id,
                            'origin':dist.name,    
                        })

                        query = """
                            UPDATE wtc_stock_distribution 
                            SET status_api='error' 
                            WHERE id = %d
                        """ % (dist.id)
                        self._cr.execute(query)   

                        # --------------Send Notif ke Slack------------- #
                        url = "https://hooks.slack.com/services/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"
                        headers = {'Content-Type': 'application/json'}
                        error_slack = "API Qty Approved Stock Distribution %s Error %s" %(dist.name,exc)
                        body = {'text':error_slack}
                    
                        requests.post(url=url,json=body,headers=headers,verify=True)
        else:
            raise Warning('Data Tidak ditemukan untuk transaksi "%s" ' %(origin))



class StockDsistributionLine(models.Model):
    _inherit = "wtc.stock.distribution.line"

    @api.model
    def create(self,vals):
        res = super(StockDsistributionLine,self).create(vals)
        res.sub_total = res.requested_qty * res.unit_price
        return res

class ApiStockDistribution(models.Model):
    _name = "teds.api.stock.distribution"

    @api.multi
    def create_stock_distribution(self,vals):
        # Nanti ubah dulu nama foldernya ya salah
        cek_group = self.env['res.users'].has_group('dms_api_stock_distribution.group_dms_api_stock_distribution_read')
        if not cek_group:
            return {
                'status':0,
                'error':'not_authorized',
                'remark':'User tidak memiliki hak akses.',
            }

        MANDATORY_FIELDS = [
            'branch_code',
            'po_name',
            'supplier_name',
            'line_ids',
            'type',
            'start_date',
            'end_date',
            'transaction_id',
            'model_id',
            'model_name',
        ]

        fields = []
        for field in MANDATORY_FIELDS :
            if field not in vals.keys():
                fields.append(field)
        if len(fields) > 0:
            return {
                'status':0,
                'error':'mandatory_field',
                'remark': 'Fields ini tidak ada: %s' %(fields)
            }

        branch_code = vals.get('branch_code')
        end_date = vals.get('end_date')
        po_name = vals.get('po_name')
        supplier_name = vals.get('supplier_name')
        line_ids = vals.get('line_ids') 
        type = vals.get('type')
        start_date = vals.get('start_date') 
        end_date = vals.get('end_date') 
        transaction_id = vals.get('transaction_id')
        model_id = vals.get('model_id')
        model_name = vals.get('model_name')

        # Cek Stock Distribution
        obj_cek = self.env['wtc.stock.distribution'].sudo().search([
            ('dms_po_name','=',po_name),
        ])
        if obj_cek:
            return {'status':1, 'message':'OK'}

        # Cari Branch
        dealer_id = False
        branch_requester_id = False
        branch = self.env['wtc.branch'].sudo().search([
            ('code','=',branch_code)
        ],limit=1)
        # import ipdb
        # ipdb.set_trace()
        if not branch:
            partner = self.env['res.partner'].sudo().search([
                ('rel_code','=',branch_code)
            ],limit=1)
            if not partner:
                return {
                    'status':0,
                    'error':'data_not_found',
                    'remark':'dealer_code: %s' %(branch_code)
                }
            dealer_id = partner.id
        else:
            branch_requester_id = branch.id
            dealer_id = branch.partner_id.id

        type_id = self.env['wtc.purchase.order.type'].sudo().search([
            ('category','=','Unit'),
            ('name','=',type.title())
        ]).id
        if not type_id:
            return {
                'status':0,
                'error':'data_not_found',
                'remark':'type: %s' %(type.title())
            }

        MANDATORY_FIELDS_LINE = [
            'default_code',
            'qty',
            'warna_code',
        ]
        md = self.env['wtc.branch'].sudo().search([
            ('code','=','MML'),
            ('branch_type','=','MD')],limit=1)
        line = []
        pricelist = False
        if branch:
            pricelist = branch.pricelist_unit_purchase_id
        else:
            pcc_id = self.env['pricelist.config.cabang'].sudo().search([
              ('branch_id','=',md.id),
              ('partner_id','=',dealer_id),
              ('division','=','Unit')],limit=1)
            
            if pcc_id:
                pricelist = pcc_id.md_pricelist_id
            else:   
                pricelist = md.pricelist_unit_sales_id
        if not pricelist:
            return {
                'status':0,
                'error':'data_not_found',
                'remark':'Pricelist tidak ditemukan.',
            }
        field_line = []
        for x in line_ids:
            for field in MANDATORY_FIELDS_LINE:   
                if field not in x.keys():
                    field_line.append(field)
            if len(field_line) > 0:
                return {
                    'status': 0,
                    'error': 'mandatory_field',
                    'remark': 'Fields detail ini tidak ada: %s.' % str(field_line),
                }
            default_code = x.get('default_code',False)
            warna_code = x.get('warna_code',False)

            query = """
                            SELECT pp.id as prod_id
                            FROM product_product pp
                            INNER JOIN product_template pt ON pt.id = pp.product_tmpl_id 
                            LEFT JOIN product_attribute_value_product_product_rel rel ON rel.prod_id = pp.id
                            LEFT JOIN product_attribute_value pav ON pav.id = rel.att_id 
                            WHERE name_template = '%s' AND pav.code='%s'
                        """ %(default_code,warna_code)
            self._cr.execute(query)
            ress = self._cr.dictfetchall()
            if ress == []:
                return {
                    'status':0,
                    'error':'data_not_found',
                    'remark':'Product code %s type warna %s' %(default_code,warna_code)
                }
            product = ress[0].get('prod_id')
            product_id = self.env['product.product'].browse(product)
            price_get = pricelist.price_get(product_id.id,1)
            price = price_get[pricelist.id] 
            if not price:
                return {
                    'status':0,
                    'error':'data_not_found',
                    'remark':'Product %s di pricelist %s' %(product_id.name,pricelist.name)
                }

            sub = x['qty'] * price
            line.append([0,0,{
                'product_id':product_id.id,
                'requested_qty':x['qty'],
                'unit_price':price,
                'description':product_id.name_get().pop()[1],
                'sub_total': sub,  
            }])
        vals = {
            'branch_id': md.id,
            'branch_requester_id':branch_requester_id,
            'dealer_id':dealer_id,
            'user_id':None,
            'type_id': type_id,
            'start_date':start_date,
            'end_date':end_date,
            'division':'Unit',
            'state':'confirm',
            'dms_po_name':po_name,
            'dms_transaction_id':transaction_id,
            'dms_model_id':model_id,
            'dms_model_name':model_name,
            'description':po_name,
            'distribution_line':line,
        }
        create = self.env['wtc.stock.distribution'].sudo().create(vals)
        
    @api.multi
    def create_stock_distribution_sparepart(self,vals):
        cek_group = self.env['res.users'].has_group('dms_api_stock_distribution.group_dms_api_stock_distribution_sparepart_read')
        if not cek_group:
            return {
                'status':0,
                'error':'not_authorized',
                'remark':'User tidak memiliki hak akses.'
            }

        MANDATORY_FIELDS = [
            'branch_code',
            'po_name',
            'supplier_name',
            'line_ids',
            'type',
            'start_date',
            'end_date',
            'transaction_id',
            'model_id',
            'model_name',
        ]
        fields = []
        for field in MANDATORY_FIELDS :
            if field not in vals.keys():
                fields.append(field)
        if len(fields) > 0:
            return {
                'status': 0,
                'error': 'mandatory_field',
                'remark': 'Fields ini tidak ada: %s.' % str(fields),
            }
        po_name = vals.get('po_name')
        type = vals.get('type')
        type_id = self.env['wtc.purchase.order.type'].sudo().search([
            ('category','=','Sparepart'),
            ('name','=',type.title())
        ]).id
        if not type_id:
            return {
                'status': 0,
                'error': 'data_not_found',
                'remark': 'type: %s' %(type.title()),
            }
        obj_cek = self.env['wtc.stock.distribution'].sudo().search([
            ('dms_po_name','=',po_name),
            ('type_id','=',type_id)
        ])
        if obj_cek:
            return {'status':1, 'message':'OK'}
        
        branch_code = vals.get('branch_code')
        end_date = vals.get('end_date')
        supplier_name = vals.get('supplier_name')
        line_ids = vals.get('line_ids') 
        start_date = vals.get('start_date') 
        end_date = vals.get('end_date') 
        transaction_id = vals.get('transaction_id')
        model_id = vals.get('model_id')
        model_name = vals.get('model_name')
        description = vals.get('description', False)

        # Cari Branch
        dealer_id = False
        branch_requester_id = False
        branch = self.env['wtc.branch'].sudo().search([
            ('code','=',branch_code)
        ],limit=1)
        if not branch:
            partner = self.env['res.partner'].sudo().search([
                ('rel_code','=',branch_code)
            ],limit=1)
            if not partner:
                return {
                    'status': 0,
                    'error': 'data_not_found',
                    'remark': 'code partner: %s.' %(branch_code),
                }
            dealer_id = partner.id
        else:
            branch_requester_id = branch.id
            dealer_id = branch.partner_id.id

        MANDATORY_FIELDS_LINE = [
            'default_code',
            'qty',
        ]
        md = self.env['wtc.branch'].sudo().search([('code','=','MML')])
        pricelist = False
        line = []
        if branch:
            pricelist = branch.pricelist_part_purchase_id
        else:
            pricelist = md.pricelist_part_sales_id
        if not pricelist:
            return {
                'status': 0,
                'error': 'data_not_found',
                'remark': 'pricelist part sales',
            }

        # import ipdb
        # ipdb.set_trace()

        field_line = []
        jml_line = 0
        jml_po = 0
        line.append([])

        for x in line_ids:
            for field in MANDATORY_FIELDS_LINE:        
                if field not in x.keys():
                    field_line.append(field)
            if len(field_line) > 0:
                return {
                    'status': 0,
                    'error': 'mandatory_field',
                    'remark': 'Fields detail ini tidak ada: %s.' % str(field_line),
                }
            default_code = x.get('default_code',False)

            product_id = self.env['product.product'].sudo().search([('name','=',default_code)],limit=1)
            if not product_id:
                return {
                    'status': 0,
                    'error': 'data_not_found',
                    'remark': 'code_product: %s' %(default_code),
                }

            price_get = pricelist.price_get(product_id.id,1)
            price = price_get[pricelist.id] 
            if not price:
                return {
                    'status': 0,
                    'error': 'data_not_found',
                    'remark': 'Product %s di pricelist %s' %(product_id.name,pricelist.name),
                }
            sub = x['qty'] * price
            line[jml_po].append([0,0,{
                'product_id': product_id.id,
                'requested_qty': x['qty'],
                'approved_qty': x['qty'],
                'unit_price': price,
                'description': product_id.name_get().pop()[1],
                'sub_total': sub,  
            }])
            jml_line += 1
            if type.title() == 'Topup' and jml_line == 30:
                # ipdb.set_trace()
                jml_line = 0
                jml_po += 1
                line.append([])
        # ipdb.set_trace()
        create_po = False
        for p in range(0,jml_po+1):
            if len(line[p]) > 0:
                vals = {
                    'branch_id': md.id,
                    'branch_requester_id':branch_requester_id,
                    'dealer_id':dealer_id,
                    'user_id':None,
                    'type_id': type_id,
                    'start_date':start_date,
                    'end_date':end_date,
                    'division':'Sparepart',
                    'state':'confirm',
                    'dms_po_name':po_name,
                    'origin':po_name,
                    'dms_transaction_id':transaction_id,
                    'dms_model_id':model_id,
                    'dms_model_name':model_name,
                    'description': description if type == 'additional' else po_name,
                    'distribution_line':line[p],
                }
                # ipdb.set_trace()
                try:
                    create_po = self.env['wtc.stock.distribution'].sudo().create(vals)
                except Exception as e:
                    self._cr.rollback()
                    return {
                        'status': 0,
                        'error': 'error',
                        'remark': 'When creating PO %s: %s' % (type.title(), e)
                    }
        if create_po and (type.title() == 'Hotline' or type.title() == 'Additional'):
            return {'status':1, 'message':'OK'}
       