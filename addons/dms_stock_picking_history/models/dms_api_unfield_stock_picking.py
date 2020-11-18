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

class StockPickingHistory(models.Model):
    _inherit = "dms.stock.picking.history"

    @api.multi
    def api_stock_picking_unfield_unit(self):    
        module_name = 'DMS Stock Picking History'
        module_model_name = 'dms.stock.picking.history'

        search = """
            SELECT ph.id as ph_id
            , sp.name as ph_name
            , sp.branch_id
            , no_po_dms
            , ph.origin
            , ph.division
            , sd.dms_model_name
            , no_invoice
            , tgl_invoice
            , ph.distribution_id
            from dms_stock_picking_history ph
            INNER JOIN stock_picking sp ON sp.id = ph.picking_id
            INNER JOIN wtc_stock_distribution sd ON sd.id = ph.distribution_id
            WHERE ph.state = 'draft' 
            ORDER BY ph.date ASC
            LIMIT 20
        """
        self._cr.execute(search)
        ress = self._cr.dictfetchall()
        if ress:
            for obj in ress:
                branch_id = obj.get('branch_id')
                ph_id = obj.get('ph_id')
                ph_name = obj.get('ph_name')
                
                config_user = self.env['teds.api.configuration'].sudo().search([('branch_id','=',branch_id)])
                if not config_user:
                    message = 'Silahkan buat configuration terlebih dahulu untuk bisa mengakses ke DMS.'
                    _logger.warning(message)
                    self.env['teds.api.log'].sudo().create({
                        'name':'not_authorized',
                        'description':message,
                        'module_name':module_name,
                        'status':0,
                        'model_name':module_model_name,
                        'transaction_id':ph_id,
                        'origin':ph_name,    
                    })
                    continue

                dms_po_origin = obj.get('no_po_dms')
                origin = obj.get('origin')
                division = obj.get('division')
                model_name = obj.get('dms_model_name')
                no_inv = obj.get('no_invoice')
                inv_date = obj.get('tgl_invoice')

                vals = {
                    'dms_po_origin':dms_po_origin,
                    'origin':origin,
                    'division':division,
                    'model_name':model_name,
                    'no_inv':no_inv,
                    'inv_date':inv_date,
                }

                line_ids = []
                product_control = {}
                distribution_id = obj.get('distribution_id')
                distribution_obj = self.env['wtc.stock.distribution'].sudo().browse(distribution_id)
                if division == 'Unit':
                    for line in distribution_obj.distribution_line:
                        warna = """
                                SELECT pav.code as warna
                                FROM product_product pp
                                INNER JOIN product_template pt ON pt.id = pp.product_tmpl_id 
                                LEFT JOIN product_attribute_value_product_product_rel rel ON rel.prod_id = pp.id
                                LEFT JOIN product_attribute_value pav ON pav.id = rel.att_id 
                                WHERE pp.id = %d LIMIT 1
                            """ %(line.product_id.id)
                        self._cr.execute(warna)
                        res_warna = self._cr.dictfetchall()
                        warna_code = res_warna[0].get('warna')

                        if not product_control.get(line.product_id.id):
                            product_control[line.product_id.id] = {
                                'product_code':line.product_id.name,
                                'product_warna':warna_code,
                                'qty':line.approved_qty,
                                'qty_spl':0,
                                'detail_ids':[]
                            }
                        else:
                            product_control[line.product_id.id]['qty'] += line.approved_qty

                    vals['line_ids'] = product_control.values()

                elif division == 'Sparepart':
                    for line in distribution_obj.distribution_line:
                        if not product_control.get(line.product_id.id):
                            product_control[line.product_id.id] = {
                                'product_code':line.product_id.name,
                                'qty':line.approved_qty,
                                'qty_spl':0,
                                'detail_ids':[]
                            }
                        else:
                            product_control[line.product_id.id]['qty'] += line.approved_qty

                    vals['line_ids'] = product_control.values()

                
                try:
                    username = config_user.username
                    password = config_user.password
                    db = config_user.database
                    host = config_user.host
                    port = config_user.port
                    odoo = odoorpc.ODOO(host, protocol='jsonrpc', port=port)
                    odoo.login(db,username,password)            
                    data = odoo.json(
                        '/web/dataset/call',
                        {'model': 'dms.api','method':'dms_create_picking_unfield',
                        'args':[[],vals]})
                    
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
                                'transaction_id':ph_id,
                                'origin':ph_name,    
                            })
                            query = """
                                UPDATE dms_stock_picking_history
                                SET state = 'error' 
                                WHERE id = %d
                            """ % (ph_id)
                            self._cr.execute(query)
                            
                        elif result['status'] == 1:
                            _logger.warning(result_message)
                            query = """
                                UPDATE dms_stock_picking_history 
                                SET state = 'done' 
                                WHERE id = %d
                            """ % (ph_id)
                            self._cr.execute(query)
                    else:
                        # Response tidak ada 
                        message = 'Unfield Picking History %s Result not found !' %(ph_name)
                        _logger.warning(message) 
                        self.env['teds.api.log'].sudo().create({
                            'name':'data_not_found',
                            'description':message,
                            'module_name':module_name,
                            'status':0,
                            'model_name':module_model_name,
                            'transaction_id':ph_id,
                            'origin':ph_name,    
                        })
                        query = """
                            UPDATE dms_stock_picking_history 
                            SET state = 'error' 
                            WHERE id = %d
                        """ % (ph_id)
                        self._cr.execute(query)

                except odoorpc.error.RPCError as exc:
                        _logger.warning(exc)
                        self.env['teds.api.log'].sudo().create({
                            'name':'RPCError EXC',
                            'description':exc,
                            'module_name':module_name,
                            'status':0,
                            'model_name':module_model_name,
                            'transaction_id':ph_id,
                            'origin':ph_name,
                        })
                        query = """
                            UPDATE dms_stock_picking_history 
                            SET state = 'error' 
                            WHERE id = %d
                        """ % (ph_id)
                        self._cr.execute(query)

        else:
            _logger.warning('Data UPDATE ERROR to Draft Picking Unfield') 
            update_error = """
                UPDATE dms_stock_picking_history
                SET state = 'draft' 
                WHERE state = 'error'
            """
            self._cr.execute(update_error)

    @api.multi
    def api_stock_picking_unfield_supply(self):    
        module_name = 'DMS Stock Picking History Supply'
        module_model_name = 'dms.stock.picking.history'
        search = """
            SELECT ph.id as ph_id
            , sp.name as ph_name
            , sp.id as picking_id
            , sp.branch_id
            , ph.no_po_dms
            , ph.origin 
            , ph.division
            , sd.dms_model_name
            , ph.no_invoice
            , ph.tgl_invoice
            , ph.distribution_id
            FROM dms_stock_picking_history ph
            INNER JOIN stock_picking sp ON sp.id = ph.picking_id
            INNER JOIN wtc_stock_distribution sd ON sd.id = ph.distribution_id
            WHERE sp.state = 'done'
            AND ph.state = 'done'
            AND ph.status_api = 'draft'
            ORDER BY ph.id ASC
            LIMIT 20
        """
        self._cr.execute(search)
        ress = self._cr.dictfetchall()
        if ress:
            for obj in ress:
                branch_id = obj.get('branch_id')
                ph_id = obj.get('ph_id')
                ph_name = obj.get('ph_name')
                
                config_user = self.env['teds.api.configuration'].sudo().search([('branch_id','=',branch_id)])
                if not config_user:
                    message = 'Silahkan buat configuration terlebih dahulu untuk bisa mengakses ke DMS.'
                    _logger.warning(message)
                    self.env['teds.api.log'].sudo().create({
                        'name':'not_authorized',
                        'description':message,
                        'module_name':module_name,
                        'status':0,
                        'model_name':module_model_name,
                        'transaction_id':ph_id,
                        'origin':ph_name,    
                    })
                    continue

                dms_po_origin = obj.get('no_po_dms')
                origin = obj.get('origin')
                division = obj.get('division')
                model_name = obj.get('dms_model_name')
                no_inv = obj.get('no_invoice')
                inv_date = obj.get('tgl_invoice')

                vals = {
                    'dms_po_origin':dms_po_origin,
                    'origin':origin,
                    'division':division,
                    'model_name':model_name,
                    'no_inv':no_inv,
                    'inv_date':inv_date,
                }

                line_ids = []
                product_control = {}
                distribution_id = obj.get('distribution_id')
                distribution_obj = self.env['wtc.stock.distribution'].sudo().browse(distribution_id)
                
                # Picking Obj 
                picking_id = obj.get('picking_id')
                picking_obj = self.env['stock.picking'].sudo().browse(picking_id)

                if division == 'Unit':
                    for line in distribution_obj.distribution_line:
                        warna = """
                                SELECT pav.code as warna
                                FROM product_product pp
                                INNER JOIN product_template pt ON pt.id = pp.product_tmpl_id 
                                LEFT JOIN product_attribute_value_product_product_rel rel ON rel.prod_id = pp.id
                                LEFT JOIN product_attribute_value pav ON pav.id = rel.att_id 
                                WHERE pp.id = %d LIMIT 1
                            """ %(line.product_id.id)
                        self._cr.execute(warna)
                        res_warna = self._cr.dictfetchall()
                        warna_code = res_warna[0].get('warna')

                        if not product_control.get(line.product_id.id):
                            product_control[line.product_id.id] = {
                                'product_code':line.product_id.name,
                                'product_warna':warna_code,
                                'qty':line.approved_qty,
                                'qty_spl':0,
                                'detail_ids':[]
                            }
                        else:
                            product_control[line.product_id.id]['qty'] += line.approved_qty

                    if len(picking_obj.pack_operation_ids) > 0:
                        # detail_operation_picking
                        for operation in picking_obj.pack_operation_ids:
                            if product_control.get(operation.product_id.id):
                                product_control[operation.product_id.id]['detail_ids'].append({
                                    'no_mesin':operation.lot_id.name,
                                    'no_rangka':operation.lot_id.chassis_no,
                                    'qty':operation.product_qty,
                                    'origin':operation.picking_id.name,
                                })
                                product_control[operation.product_id.id]['qty_spl'] += operation.product_qty

                    vals['line_ids'] = product_control.values()

                elif division == 'Sparepart':
                    product_control = {}
                    for line in distribution_obj.distribution_line:
                        if not product_control.get(line.product_id.id):
                            product_control[line.product_id.id] = {
                                'product_code':line.product_id.name,
                                'qty':line.approved_qty,
                                'qty_spl':0,
                                'detail_ids':[]
                            }
                        else:
                            product_control[line.product_id.id]['qty'] += line.approved_qty


                    if len(picking_obj.pack_operation_ids) > 0:
                        # detail_operation_picking
                        for operation in picking_obj.pack_operation_ids:
                            if product_control.get(operation.product_id.id):
                                product_control[operation.product_id.id]['detail_ids'].append({
                                    'qty':operation.product_qty,
                                    'origin':operation.picking_id.name,
                                })
                                product_control[operation.product_id.id]['qty_spl'] += operation.product_qty

                    vals['line_ids'] = product_control.values()

                try:
                    username = config_user.username
                    password = config_user.password
                    db = config_user.database
                    host = config_user.host
                    port = config_user.port
                    odoo = odoorpc.ODOO(host, protocol='jsonrpc', port=port)
                    odoo.login(db,username,password)            
                    data = odoo.json(
                        '/web/dataset/call',
                        {'model': 'dms.api','method':'dms_create_picking_unfield',
                        'args':[[],vals]})
                    
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
                                'transaction_id':ph_id,
                                'origin':ph_name,    
                            })
                            query = """
                                UPDATE dms_stock_picking_history
                                SET status_api = 'error' 
                                WHERE id = %d
                            """ % (ph_id)
                            self._cr.execute(query)
                            
                        elif result['status'] == 1:
                            _logger.warning(result_message)
                            query = """
                                UPDATE dms_stock_picking_history 
                                SET status_api = 'done' 
                                WHERE id = %d
                            """ % (ph_id)
                            self._cr.execute(query)
                    else:
                        # Response tidak ada 
                        message = 'Unfield Picking History %s Result not found !' %(ph_name)
                        _logger.warning(message) 
                        self.env['teds.api.log'].sudo().create({
                            'name':'data_not_found',
                            'description':message,
                            'module_name':module_name,
                            'status':0,
                            'model_name':module_model_name,
                            'transaction_id':ph_id,
                            'origin':ph_name,    
                        })
                        query = """
                            UPDATE dms_stock_picking_history 
                            SET status_api = 'error' 
                            WHERE id = %d
                        """ % (ph_id)
                        self._cr.execute(query)

                except odoorpc.error.RPCError as exc:
                        _logger.warning(exc)
                        self.env['teds.api.log'].sudo().create({
                            'name':'RPCError EXC',
                            'description':exc,
                            'module_name':module_name,
                            'status':0,
                            'model_name':module_model_name,
                            'transaction_id':ph_id,
                            'origin':ph_name,
                        })
                        query = """
                            UPDATE dms_stock_picking_history 
                            SET status_api = 'error' 
                            WHERE id = %d
                        """ % (ph_id)
                        self._cr.execute(query)
        else:
            _logger.warning('Data UPDATE ERROR to Draft Picking Unfield SUPPLY') 
            update_error = """
                UPDATE dms_stock_picking_history
                SET status_api = 'draft' 
                WHERE status_api = 'error'
            """
            self._cr.execute(update_error)


           