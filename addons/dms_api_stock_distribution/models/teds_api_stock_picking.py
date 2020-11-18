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

import requests


class DmsMutationOrder(models.Model):
    _inherit = "wtc.mutation.order"
    dms_po_name = fields.Char('DMS PO Name')


class DmsSaleOrder(models.Model):
    _inherit = "sale.order"
    dms_po_name = fields.Char('DMS PO Name')


class StockPacking(models.Model):
    _inherit = "wtc.stock.packing"

    status_api = fields.Selection([
        ('draft','Draft'),
        ('error','Error'),
        ('done','Done'),
    ],default='draft',string='Status API')


    # Sparepart
    @api.multi
    def api_dms_stock_picking_to_hoki_sparepart(self):
        message = False
        module_name = 'TEDS API STOCK PACKING SPAREPART'
        module_model_name = 'wtc.stock.packing'

        search = """
            SELECT pac.id as packing_id
            , pac.name as packing_name
            , pac.rel_division
            , pic.transaction_id
            , pic.id as picking_id
            , pic.branch_id
            , pic.model_id
            , model.model
            , partner.default_code
            FROM wtc_stock_packing as pac 
            INNER JOIN wtc_branch b on b.id = pac.rel_branch_id
            INNER JOIN stock_picking as pic on pic.id=pac.picking_id
            INNER JOIN ir_model model on model.id = pic.model_id
            INNER JOIN teds_api_list_partner_rel list_p ON list_p.parter_id = pac.rel_partner_id
            INNER JOIN res_partner partner ON partner.id = pac.rel_partner_id
            WHERE b.branch_type = 'MD'
            AND pac.state = 'posted'
            AND pac.rel_division = 'Sparepart'
            AND pac.status_api = 'draft'
            AND model.model in ('wtc.mutation.order','sale.order')
            ORDER BY pac.id ASC
            LIMIT 20
        """
        self._cr.execute(search)
        ress = self._cr.dictfetchall()
        if ress:
            for res in ress:
                packing_id = res.get('packing_id')
                packing_name = res.get('packing_name')
                rel_division =res.get('rel_division')
                picking_id = res.get('picking_id')
                branch_id = res.get('branch_id')
                transaction_id = res.get('transaction_id')
                model_id = res.get('model_id')
                model_name = res.get('model')
                branch_code_partner = res.get('default_code')

                packing_obj = self.env['wtc.stock.packing'].sudo().browse(packing_id)
                
                # Cek Config
                config_user = self.env['teds.api.configuration'].sudo().search([('branch_id','=',branch_id)],limit=1)
                if not config_user:
                    message = 'Stock Packing %s silahkan buat configuration terlebih dahulu untuk bisa mengakses ke DMS' %(packing_name)
                    _logger.warning(message) 
                    self.env['teds.api.log'].sudo().create({
                        'name':'not_authorized',
                        'description':message,
                        'module_name':module_name,
                        'status':0,
                        'model_name':module_model_name,
                        'transaction_id':packing_id,
                        'origin':packing_name,    
                    })
                    query = """
                        UPDATE wtc_stock_packing 
                        SET status_api='error' 
                        WHERE id = %d
                    """ % (packing_id)
                    self._cr.execute(query)
                    continue

                sale_and_mutation_order = self.env[model_name].sudo().search([('id','=',transaction_id)],limit=1)

                if not sale_and_mutation_order:
                    message = 'Stock Packing %s Data Model %s transaction_id %s tidak ditemukan !' %(packing_name,model_name,transaction_id)
                    _logger.warning(message) 
                    self.env['teds.api.log'].sudo().create({
                        'name':'data_not_found',
                        'description':message,
                        'module_name':module_name,
                        'status':0,
                        'model_name':module_model_name,
                        'transaction_id':packing_id,
                        'origin':packing_name,    
                    })
                    query = """
                        UPDATE wtc_stock_packing 
                        SET status_api='error' 
                        WHERE id = %d
                    """ % (packing_id)
                    self._cr.execute(query)
                    continue
                    
                dms_transaction_id = sale_and_mutation_order.distribution_id.dms_transaction_id
                dms_origin = sale_and_mutation_order.distribution_id.dms_po_name
                dms_model_id = sale_and_mutation_order.distribution_id.dms_model_id
                dms_model_name = sale_and_mutation_order.distribution_id.dms_model_name
                distribution_line = sale_and_mutation_order.distribution_id.distribution_line
                packing_rel_origin=sale_and_mutation_order.name

                line = []
                pricelist = False
                obj_branch=self.env['wtc.branch'].sudo().browse(branch_id)
                pricelist = obj_branch.pricelist_part_purchase_id
                # Jika Pricelist tidak ada dr config cabang
                if not pricelist:
                    message = 'Stock Packing %s Pricelist Harga Jual Part tidak ditemukan !' %(packing_name)
                    _logger.warning(message) 
                    self.env['teds.api.log'].sudo().create({
                        'name':'data_not_found',
                        'description':message,
                        'module_name':module_name,
                        'status':0,
                        'model_name':module_model_name,
                        'transaction_id':packing_id,
                        'origin':packing_name,    
                    })
                    query = """
                        UPDATE wtc_stock_packing 
                        SET status_api='error' 
                        WHERE id = %d
                    """ % (packing_id)
                    self._cr.execute(query)
                    continue


                for packing_line in packing_obj.packing_line:
                    price_get = pricelist.price_get(packing_line.product_id.id,1)
                    price = price_get[pricelist.id] 
                    line.append({
                        'product_code':packing_line.product_id.name,
                        'qty':packing_line.quantity,
                        'price':price,
                    })
                if not line:
                    # Jika Detail Packing Tidak Ada
                    message = 'Stock Packing %s Detail Line Kosong !' %(packing_name)
                    _logger.warning(message) 
                    self.env['teds.api.log'].sudo().create({
                        'name':'data_not_found',
                        'description':message,
                        'module_name':module_name,
                        'status':0,
                        'model_name':module_model_name,
                        'transaction_id':packing_id,
                        'origin':packing_name,    
                    })
                    query = """
                        UPDATE wtc_stock_packing 
                        SET status_api='error' 
                        WHERE id = %d
                    """ % (packing_id)
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
                        {'model': 'dms.api','method':'dms_create_stock',
                        'args':[[], 
                            {
                                'code_md':obj_branch.code,
                                'branch_code': branch_code_partner,
                                'dms_transaction_id':dms_transaction_id,
                                'dms_origin':dms_origin,
                                'dms_model_id':dms_model_id,
                                'dms_model_name':dms_model_name,
                                'origin':packing_rel_origin,
                                'surat_jalan':packing_name,
                                'division':rel_division,
                                'dms_po_name':dms_origin,
                                'line_ids': line,
                        }]})
                    # Hasil Response API
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
                                'transaction_id':packing_id,
                                'origin':packing_name,    
                            })
                            query = """
                                UPDATE wtc_stock_packing 
                                SET status_api='error' 
                                WHERE id = %d
                            """ % (packing_id)
                            self._cr.execute(query)                            
                        elif result_status == 1:
                            _logger.warning(result_message)
                            query = """
                                UPDATE wtc_stock_packing 
                                SET status_api='done' 
                                WHERE id = %d
                            """ % (packing_id)
                            self._cr.execute(query)
                    else:
                        # Response tidak ada 
                        message = 'Stock Packing %s Result not found !' %(packing_name)
                        _logger.warning(message) 
                        self.env['teds.api.log'].sudo().create({
                            'name':'data_not_found',
                            'description':message,
                            'module_name':module_name,
                            'status':0,
                            'model_name':module_model_name,
                            'transaction_id':packing_id,
                            'origin':packing_name,    
                        })
                        query = """
                            UPDATE wtc_stock_packing 
                            SET status_api='error' 
                            WHERE id = %d
                        """ % (packing_id)
                        self._cr.execute(query)
                except odoorpc.error.RPCError as exc:
                    _logger.warning(exc)
                    self.env['teds.api.log'].sudo().create({
                        'name':'RPCError EXC',
                        'description':exc,
                        'module_name':module_name,
                        'status':0,
                        'model_name':module_model_name,
                        'transaction_id':packing_id,
                        'origin':packing_name,    
                    })
                    query = """
                        UPDATE wtc_stock_packing 
                        SET status_api='error' 
                        WHERE id = %d
                    """ % (packing_id)
                    self._cr.execute(query)
        else:
            _logger.warning('Data UPDATE ERROR to Draft Packing') 
            update_error = """
                UPDATE wtc_stock_packing 
                SET status_api = 'draft' 
                WHERE status_api = 'error'
            """
            self._cr.execute(update_error)

    # Unit
    @api.multi
    def api_dms_stock_picking_to_hoki_unit(self):
        message = False
        module_name = 'TEDS API STOCK PACKING UNIT'
        module_model_name = 'wtc.stock.packing'

        search = """
            SELECT pac.id as packing_id
            , pac.name as packing_name
            , pac.rel_division
            , pic.transaction_id
            , pic.id as picking_id
            , pic.branch_id
            , pic.model_id
            , model.model
            , partner.default_code
            FROM wtc_stock_packing as pac 
            INNER JOIN wtc_branch b on b.id = pac.rel_branch_id
            INNER JOIN stock_picking as pic on pic.id=pac.picking_id
            INNER JOIN ir_model model on model.id = pic.model_id
            INNER JOIN teds_api_list_partner_rel list_p ON list_p.parter_id = pac.rel_partner_id
            INNER JOIN res_partner partner ON partner.id = pac.rel_partner_id
            WHERE b.branch_type = 'MD'
            AND pac.state = 'posted'
            AND pac.rel_division = 'Unit'
            AND pac.status_api = 'draft'
            AND model.model in ('wtc.mutation.order','sale.order')
            ORDER BY pac.id ASC
            LIMIT 20
        """
        self._cr.execute(search)
        ress = self._cr.dictfetchall()
        if ress:
            for res in ress:
                packing_id=res.get('packing_id')
                packing_name=res.get('packing_name')
                rel_division=res.get('rel_division')
                picking_id = res.get('picking_id')
                branch_id=res.get('branch_id')
                transaction_id = res.get('transaction_id')
                model_id =res.get('model_id')
                model_name=res.get('model')
                branch_code_partner=res.get('default_code')

                
                packing_obj = self.env['wtc.stock.packing'].sudo().browse(packing_id)

                # Cek Config
                config_user = self.env['teds.api.configuration'].sudo().search([('branch_id','=',branch_id)],limit=1)
                if not config_user:
                    message = 'Stock Packing %s silahkan buat configuration terlebih dahulu untuk bisa mengakses ke DMS' %(packing_name)
                    _logger.warning(message) 
                    self.env['teds.api.log'].sudo().create({
                        'name':'not_authorized',
                        'description':message,
                        'module_name':module_name,
                        'status':0,
                        'model_name':module_model_name,
                        'transaction_id':packing_id,
                        'origin':packing_name,    
                    })
                    query = """
                        UPDATE wtc_stock_packing 
                        SET status_api='error' 
                        WHERE id = %d
                    """ % (packing_id)
                    self._cr.execute(query)
                    continue

                sale_and_mutation_order = self.env[model_name].sudo().search([('id','=',transaction_id)],limit=1)

                if not sale_and_mutation_order:
                    message = 'Stock Packing %s Data Model %s transaction_id %s tidak ditemukan !' %(packing_name,model_name,transaction_id)
                    _logger.warning(message) 
                    self.env['teds.api.log'].sudo().create({
                        'name':'data_not_found',
                        'description':message,
                        'module_name':module_name,
                        'status':0,
                        'model_name':module_model_name,
                        'transaction_id':packing_id,
                        'origin':packing_name,    
                    })
                    query = """
                        UPDATE wtc_stock_packing 
                        SET status_api='error' 
                        WHERE id = %d
                    """ % (packing_id)
                    self._cr.execute(query)
                    continue

                dms_transaction_id = sale_and_mutation_order.distribution_id.dms_transaction_id
                dms_origin = sale_and_mutation_order.distribution_id.dms_po_name
                dms_model_id = sale_and_mutation_order.distribution_id.dms_model_id
                dms_model_name = sale_and_mutation_order.distribution_id.dms_model_name
                distribution_line = sale_and_mutation_order.distribution_id.distribution_line
                packing_rel_origin=sale_and_mutation_order.name

                line = []
                pricelist = False
                obj_branch=self.env['wtc.branch'].sudo().browse(branch_id)
                pricelist = obj_branch.pricelist_part_purchase_id
                # Jika Pricelist tidak ada dr config cabang
                if not pricelist:
                    message = 'Stock Packing %s Pricelist Harga Jual Part tidak ditemukan !' %(packing_name)
                    _logger.warning(message) 
                    self.env['teds.api.log'].sudo().create({
                        'name':'data_not_found',
                        'description':message,
                        'module_name':module_name,
                        'status':0,
                        'model_name':module_model_name,
                        'transaction_id':packing_id,
                        'origin':packing_name,    
                    })
                    query = """
                        UPDATE wtc_stock_packing 
                        SET status_api='error' 
                        WHERE id = %d
                    """ % (packing_id)
                    self._cr.execute(query)
                    continue


                for packing_line in packing_obj.packing_line:
                    price_get = pricelist.price_get(packing_line.product_id.id,1)
                    price = price_get[pricelist.id]
                    warna = """
                        SELECT pav.code as warna
                        FROM product_product pp
                        INNER JOIN product_template pt ON pt.id = pp.product_tmpl_id 
                        LEFT JOIN product_attribute_value_product_product_rel rel ON rel.prod_id = pp.id
                        LEFT JOIN product_attribute_value pav ON pav.id = rel.att_id 
                        WHERE pp.id = %d LIMIT 1
                    """ %(packing_line.product_id.id)
                    self._cr.execute(warna)
                    res_warna = self._cr.dictfetchall()
                    warna_code = res_warna[0].get('warna')
                    
                    line.append({
                        'product_code':packing_line.product_id.name,
                        'no_engine':packing_line.serial_number_id.name,
                        'chassis_no':packing_line.serial_number_id.chassis_no,
                        'qty':packing_line.quantity,
                        'tahun_pembuatan':packing_line.tahun_pembuatan,
                        'price':price,
                        'warna_code':warna_code,
                        'no_faktur':packing_line.serial_number_id.no_faktur,
                        'no_ship_list':packing_line.serial_number_id.no_ship_list,
                        'no_sipb':packing_line.serial_number_id.no_sipb,
                        'tgl_ship_list':packing_line.serial_number_id.tgl_ship_list,
                        'tgl_receive':packing_line.serial_number_id.receive_date,
                        'tgl_surat_jalan_md':packing_line.packing_id.date,
                    })
                
                if not line:
                    # Jika Detail Packing Tidak Ada
                    message = 'Stock Packing %s Detail Line Kosong !' %(packing_name)
                    _logger.warning(message) 
                    self.env['teds.api.log'].sudo().create({
                        'name':'data_not_found',
                        'description':message,
                        'module_name':module_name,
                        'status':0,
                        'model_name':module_model_name,
                        'transaction_id':packing_id,
                        'origin':packing_name,    
                    })
                    query = """
                        UPDATE wtc_stock_packing 
                        SET status_api='error' 
                        WHERE id = %d
                    """ % (packing_id)
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
                        {'model': 'dms.api','method':'dms_create_stock',
                        'args':[[], 
                            {
                                'code_md':obj_branch.code,
                                'branch_code': branch_code_partner,
                                'dms_transaction_id':dms_transaction_id,
                                'dms_origin':dms_origin,
                                'dms_model_id':dms_model_id,
                                'dms_model_name':dms_model_name,
                                'origin':packing_rel_origin,
                                'surat_jalan':packing_name,
                                'division':rel_division,
                                'dms_po_name':dms_origin,
                                'line_ids': line,
                        }]})
                    
                    # Hasil Response API
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
                                'transaction_id':packing_id,
                                'origin':packing_name,    
                            })
                            query = """
                                UPDATE wtc_stock_packing 
                                SET status_api='error' 
                                WHERE id = %d
                            """ % (packing_id)
                            self._cr.execute(query)

                        elif result_status == 1:
                            _logger.warning(result_message)
                            query = """
                                UPDATE wtc_stock_packing 
                                SET status_api='done' 
                                WHERE id = %d
                            """ % (packing_id)
                            self._cr.execute(query)
                    else:
                        # Response tidak ada 
                        message = 'Stock Packing %s Result not found !' %(packing_name)
                        _logger.warning(message) 
                        self.env['teds.api.log'].sudo().create({
                            'name':'data_not_found',
                            'description':message,
                            'module_name':module_name,
                            'status':0,
                            'model_name':module_model_name,
                            'transaction_id':packing_id,
                            'origin':packing_name,    
                        })
                        query = """
                            UPDATE wtc_stock_packing 
                            SET status_api='error' 
                            WHERE id = %d
                        """ % (packing_id)
                        self._cr.execute(query)
                except odoorpc.error.RPCError as exc:
                        _logger.warning(exc)
                        self.env['teds.api.log'].sudo().create({
                            'name':'RPCError EXC',
                            'description':exc,
                            'module_name':module_name,
                            'status':0,
                            'model_name':module_model_name,
                            'transaction_id':packing_id,
                            'origin':packing_name,
                        })
                        query = """
                            UPDATE wtc_stock_packing 
                            SET status_api='error' 
                            WHERE id = %d
                        """ % (packing_id)
                        self._cr.execute(query)
                        
        else:
            _logger.warning('Data UPDATE ERROR to Draft Packing') 
            update_error = """
                UPDATE wtc_stock_packing 
                SET status_api = 'draft' 
                WHERE status_api = 'error'
            """
            self._cr.execute(update_error)


    @api.multi
    def api_dms_stock_picking_to_hoki_manual(self,origin):
        raise Warning("Maaf tidak tersedia !")
        message = False
        search = """
            SELECT pac.id as packing_id
            , pac.name as packing_name
            , pac.rel_division
            , pic.transaction_id
            , pic.id as picking_id
            , pic.branch_id
            , pic.model_id
            , model.model
            , partner.default_code
            FROM wtc_stock_packing as pac 
            INNER JOIN wtc_branch b on b.id = pac.rel_branch_id
            INNER JOIN stock_picking as pic on pic.id=pac.picking_id
            INNER JOIN ir_model model on model.id = pic.model_id
            INNER JOIN teds_api_list_partner_rel list_p ON list_p.parter_id = pac.rel_partner_id
            INNER JOIN res_partner partner ON partner.id = pac.rel_partner_id
            WHERE b.branch_type = 'MD'
            and pac.name = '%s'
            AND pac.state = 'posted'
            AND pac.status_api = 'draft'
            AND model.model in ('wtc.mutation.order','sale.order')
            ORDER BY pac.id ASC
            LIMIT 1
        """%(origin)
        
        self._cr.execute(search)
        ress = self._cr.dictfetchall()
        if ress:
            for res in ress:
                packing_id=res.get('packing_id')
                packing_name=res.get('packing_name')
                rel_division=res.get('rel_division')
                picking_id = res.get('picking_id')
                branch_id=res.get('branch_id')
                transaction_id = res.get('transaction_id')
                model_id =res.get('model_id')
                model_name=res.get('model')
                branch_code_partner=res.get('default_code')

                sale_and_mutation_order = self.env[model_name].sudo().search([('id','=',transaction_id)],limit=1)
                if not sale_and_mutation_order:
                    message = 'data_not_found'
                    _logger.warning('%s' %message) 
                    self.env['teds.api.log'].sudo().create({
                        'name':message,
                        'description':'Object tidak ditemukan.',
                        'module_name':'TEDS API STOCK PICKING',
                        'status':0,
                        'model_name':'wtc.stock.packing',
                        'transaction_id':packing_id,
                        'origin':packing_name,    
                    })
                    query = """
                        UPDATE wtc_stock_packing 
                        SET status_api='error' 
                        WHERE id = %d
                    """ % (packing_id)
                    self._cr.execute(query)
                    continue

                dms_transaction_id = sale_and_mutation_order.distribution_id.dms_transaction_id
                dms_origin = sale_and_mutation_order.distribution_id.dms_po_name
                dms_model_id = sale_and_mutation_order.distribution_id.dms_model_id
                dms_model_name = sale_and_mutation_order.distribution_id.dms_model_name
                distribution_line = sale_and_mutation_order.distribution_id.distribution_line
                packing_rel_origin=sale_and_mutation_order.name

                line = []
                if rel_division in ('Unit','Sparepart'):
                    obj_branch=self.env['wtc.branch'].sudo().browse(branch_id)
                    if branch_id :
                        pricelist = obj_branch.pricelist_unit_purchase_id
                    packing_line=self.env['wtc.stock.packing.line'].sudo().search([('packing_id','=',packing_id)])
                    if packing_line :
                        for line_packing in packing_line:
                            if line_packing.serial_number_id:
                                price_get = pricelist.price_get(line_packing.product_id.id,1)
                                price = price_get[pricelist.id]
                                warna = """
                                        SELECT pav.code as warna
                                        FROM product_product pp
                                        INNER JOIN product_template pt ON pt.id = pp.product_tmpl_id 
                                        LEFT JOIN product_attribute_value_product_product_rel rel ON rel.prod_id = pp.id
                                        LEFT JOIN product_attribute_value pav ON pav.id = rel.att_id 
                                        WHERE pp.id = %d LIMIT 1
                                    """ %(line_packing.product_id.id)
                                self._cr.execute(warna)
                                ress = self._cr.dictfetchall()
                                warna_code = ress[0].get('warna')
                                line.append({
                                    'product_code':line_packing.product_id.name,
                                    'no_engine':line_packing.serial_number_id.name,
                                    'chassis_no':line_packing.serial_number_id.chassis_no,
                                    'qty':line_packing.quantity,
                                    'tahun_pembuatan':line_packing.tahun_pembuatan,
                                    'price':price,
                                    'warna_code':warna_code,
                                    'no_faktur':line_packing.serial_number_id.no_faktur,
                                    'no_ship_list':line_packing.serial_number_id.no_ship_list,
                                    'no_sipb':line_packing.serial_number_id.no_sipb,
                                    'tgl_ship_list':line_packing.serial_number_id.tgl_ship_list,
                                })
                            else:
                                price_get = pricelist.price_get(line_packing.product_id.id,1)
                                price = price_get[pricelist.id] 
                                line.append({
                                    'product_code':line_packing.product_id.name,
                                    'qty':line_packing.quantity,
                                    'price':price,
                                })
                    
                        config_user = self.env['teds.api.configuration'].sudo().search([('branch_id','=',branch_id)])
                        if not config_user:
                            message = 'Silahkan buat configuration terlebih dahulu untuk bisa mengakses ke DMS.'
                            _logger.warning(message) 
                            self.env['teds.api.log'].sudo().create({
                                'name':'not_authorized',
                                'description':message,
                                'module_name':'TEDS API STOCK PICKING',
                                'status':0,
                                'model_name':'wtc.stock.packing',
                                'transaction_id':packing_id,
                                'origin':packing_name,    
                            })
                        if message:
                            query = """
                                UPDATE wtc_stock_packing 
                                SET status_api='error' 
                                WHERE id = %d
                            """ % (packing_id)
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
                                    {'model': 'dms.api','method':'dms_create_stock',
                                    'args':[[], 
                                        {
                                            'code_md':obj_branch.code,
                                            'branch_code': branch_code_partner,
                                            'dms_transaction_id':dms_transaction_id,
                                            'dms_origin':dms_origin,
                                            'dms_model_id':dms_model_id,
                                            'dms_model_name':dms_model_name,
                                            'origin':packing_rel_origin,
                                            'surat_jalan':packing_name,
                                            'division':rel_division,
                                            'dms_po_name':dms_origin,
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
                                            'module_name':'TEDS API STOCK PICKING',
                                            'status':result.get('status',False),
                                            'model_name':'wtc.stock.packing',
                                            'transaction_id':packing_id,
                                            'origin':packing_name,    
                                        })
                                        query = """
                                            UPDATE wtc_stock_packing 
                                            SET status_api='error' 
                                            WHERE id = %d
                                        """ % (packing_id)
                                        self._cr.execute(query)

                                        # --------------Send Notif ke Slack------------- #
                                        url = "https://hooks.slack.com/services/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"
                                        headers = {'Content-Type': 'application/json'}
                                        error_slack = "API Stock Packing %s Error %s %s" %(packing_name,result.get('error'),result.get('remark'))
                                        body = {'text':error_slack}
                                    
                                        requests.post(url=url,json=body,headers=headers,verify=True)

                                    elif result['status'] == 1:
                                        message = result.get('message',False)
                                        _logger.warning('%s' %(message))
                                        query = """
                                            UPDATE wtc_stock_packing 
                                            SET status_api='done' 
                                            WHERE id = %d
                                        """ % (packing_id)
                                        self._cr.execute(query)


                            except odoorpc.error.RPCError as exc:
                                _logger.warning('%s' %(exc))
                                self.env['teds.api.log'].sudo().create({
                                    'name':'raise_warning',
                                    'description':exc,
                                    'module_name':'DMS API STOCK PICKING',
                                    'status':0,
                                    'model_name':'wtc.stock.packing',
                                    'transaction_id':packing_id,
                                    'origin':packing_name,    
                                })

                                query = """
                                    UPDATE wtc_stock_packing 
                                    SET status_api='error' 
                                    WHERE id = %d
                                """ % (packing_id)
                                self._cr.execute(query) 

                                # --------------Send Notif ke Slack------------- #
                                url = "https://hooks.slack.com/services/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"
                                headers = {'Content-Type': 'application/json'}
                                error_slack = "API Stock Packing %s Error %s" %(packing_name,exc)
                                body = {'text':error_slack}
                            
                                requests.post(url=url,json=body,headers=headers,verify=True)
                    else:
                        query = """
                            UPDATE wtc_stock_packing 
                            SET status_api='done' 
                            WHERE id = %d
                        """ % (packing_id)
                        self._cr.execute(query) 
        else:
           raise Warning('Data Tidak ditemukan untuk transaksi "%s" ' %(origin))


    @api.multi
    def api_dms_stock_picking_whi(self):
        message = False
        #----------------- Masih harus di review lagi -------------------#
        return True
        # ---------------------------------------------------------------#

        search = """
            SELECT pac.id as id
            FROM wtc_stock_packing pac
            INNER JOIN stock_picking pic ON pac.picking_id = pic.id
            INNER JOIN ir_model model ON model.id = pic.model_id
            INNER JOIN wtc_branch b ON b.id = pac.branch_sender_id
            WHERE b.branch_type = 'MD'
            AND pac.state = 'posted'
            AND pac.rel_division = 'Unit'
            AND pac.status_api = 'draft'
            AND model.model = 'wtc.mutation.order'
            LIMIT 20
        """
        self._cr.execute(search)
        ress = self._cr.dictfetchall()
        if ress :
            obj = ress[0].get('id')
            _logger.warning('Data Found WHI %s' % obj) 
            packing = self.env['wtc.stock.packing'].browse(obj)
            
            if packing.rel_division in ('Unit','Sparepart'):
                picking = packing.picking_id
                transaction_id = picking.transaction_id
                model_id = picking.model_id
    
                obj = self.env[model_id.model].sudo().search([
                    ('id','=',transaction_id),
                ],limit=1)
                if not obj:
                    message = 'Object tidak ditemukan.'
                    _logger.warning('%s' %message) 
                    self.env['teds.api.log'].sudo().create({
                        'name':'data_not_found',
                        'description':message,
                        'module_name':'TEDS API STOCK PICKING',
                        'status':0,
                        'model_name':'wtc.stock.packing',
                        'transaction_id':packing.id,
                        'origin':packing.name,    
                    })
                dms_transaction_id = obj.distribution_id.dms_transaction_id
                dms_origin = obj.distribution_id.dms_po_name
                dms_model_id = obj.distribution_id.dms_model_id
                dms_model_name = obj.distribution_id.dms_model_name
                if not dms_transaction_id or not dms_model_id or not dms_model_name:
                    message = 'Data untuk dikirim belum lengkap, dms_transaction_id,dms_origin,dms_model_id,dms_model_name.'
                    _logger.warning('%s' %message) 
                    self.env['teds.api.log'].sudo().create({
                        'name':'data_not_complate',
                        'description':message,
                        'model_name':'TEDS API STOCK PICKING',
                        'status':0,
                        'model_name':'wtc.stock.packing',
                        'transaction_id':packing.id,
                        'origin':packing.name,    
                    })
    
                pricelist = packing.rel_branch_id.pricelist_unit_purchase_id
                line = []
                for x in packing.packing_line:
                    if x.serial_number_id:
                        price_get = pricelist.price_get(x.product_id.id,1)
                        price = price_get[pricelist.id] 
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
                        line.append({
                            'product_code':x.product_id.name,
                            'no_engine':x.serial_number_id.name,
                            'price':price,
                            'warna_code':warna_code
                        })
                    else:
                        price_get = pricelist.price_get(x.product_id.id,1)
                        price = price_get[pricelist.id] 
                        line.append({
                            'product_code':x.product_id.name,
                            'qty':x.quantity,
                            'price':price,
                         })
                
                config_user = self.env['teds.api.configuration'].search([('branch_id','=',packing.rel_branch_id.id)])
                if not config_user:
                    message = 'Silahkan buat configuration terlebih dahulu untuk bisa mengakses ke DMS.'
                    _logger.warning(message) 
                    self.env['teds.api.log'].sudo().create({
                        'name':'not_authorized',
                        'description':message,
                        'model_name':'TEDS API STOCK PICKING',
                        'status':0,
                        'model_name':'wtc.stock.packing',
                        'transaction_id':packing.id,
                        'origin':packing.name,    
                    })
                if message:
                    query = """
                        UPDATE wtc_stock_packing 
                        SET status_api='error' 
                        WHERE id = %d
                    """ % (packing.id)
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
                            {'model': 'dms.api','method':'dms_stock_picking_whi_create',
                            'args':[[], 
                                {
                                    'code_branch':packing.rel_branch_id.code,
                                    'code_branch_sender': packing.branch_sender_id.code,
                                    'division':packing.rel_division,
                                    'origin':packing.rel_origin,
                                    'dms_transaction_id':dms_transaction_id,
                                    'dms_origin':dms_origin,
                                    'dms_model_id':dms_model_id,
                                    'dms_model_name':dms_model_name,
                                    'surat_jalan':packing.name,
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
                                    'module_name':'TEDS API STOCK PICKING',
                                    'status':result.get('status',False),
                                    'model_name':'wtc.stock.packing',
                                    'transaction_id':packing.id,
                                    'origin':packing.name,    
                                })

                                query = """
                                    UPDATE wtc_stock_packing 
                                    SET status_api='error' 
                                    WHERE id = %d
                                """ % (packing.id)
                                self._cr.execute(query)
                            elif result['status'] == 1:
                                message = result.get('message',False)
                                _logger.warning('%s' %(message))
                                query = """
                                    UPDATE wtc_stock_packing 
                                    SET status_api='done' 
                                    WHERE id = %d
                                """ % (packing.id)
                                self._cr.execute(query)
    
                    except odoorpc.error.RPCError as exc:
                        _logger.warning('%s' %(exc))
                        self.env['teds.api.log'].sudo().create({
                            'name':'raise_warning',
                            'description':exc,
                            'module_name':'TEDS API STOCK PICKING',
                            'status':0,
                            'model_name':'wtc.stock.packing',
                            'transaction_id':packing.id,
                            'origin':packing.name,    
                        })

                        query = """
                            UPDATE wtc_stock_packing 
                            SET status_api='error' 
                            WHERE id = %d
                        """ % (packing.id)
                        self._cr.execute(query)  
            else:
                query = """
                    UPDATE wtc_stock_packing 
                    SET status_api='done' 
                    WHERE id = %d
                """ % (packing.id)
                self._cr.execute(query)

        else:
            _logger.warning('Data UPDATE ERROR to Draft WHI') 
            update_error = """
                UPDATE wtc_stock_packing 
                SET status_api = 'draft' 
                WHERE status_api = 'error'
            """
            self._cr.execute(update_error)
    
