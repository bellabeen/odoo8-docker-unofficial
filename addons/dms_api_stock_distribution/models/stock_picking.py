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

class StockPicking(models.Model):
    _inherit = "stock.picking"

    api_dms = fields.Selection([
        ('draft','draft'),
        ('error','error'),
        ('done','done')],default='draft')        

    @api.multi
    def api_stock_picking_booking_unit(self):
        module_name = 'TEDS API STOCK PICKING BOOKING UNIT'
        module_model_name = 'stock.picking'

        assigned_picking_query = """
            SELECT sp.id as picking_id
            , sp.name as picking_name
            , sp.date as picking_date
            , sp.division as division
            , sp.transaction_id as transaction
            , sp.branch_id as branch
            , model.model as model
            , partner.default_code as default_code
            FROM stock_picking sp 
            INNER JOIN wtc_branch b ON b.id = sp.branch_id
            INNER JOIN ir_model model ON model.id = sp.model_id
            INNER JOIN teds_api_list_partner_rel list_p ON list_p.parter_id = sp.partner_id
            INNER JOIN res_partner partner ON partner.id = sp.partner_id
            WHERE b.branch_type = 'MD'
            AND sp.state = 'assigned'
            AND sp.division = 'Unit'
            AND sp.api_dms = 'draft'
            AND model.model IN ('wtc.mutation.order','sale.order')
            ORDER BY sp.id ASC
            LIMIT 20
        """
        self._cr.execute(assigned_picking_query)
        ress = self._cr.dictfetchall()
        if ress:
            for res in ress:
                picking_id = res.get('picking_id')
                picking_name = res.get('picking_name')
                branch_id = res.get('branch')
                division = res.get('division')
                transaction_id = res.get('transaction')
                model_name = res.get('model')
                
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
                        'transaction_id':picking_id,
                        'origin':picking_name,    
                    })
                    continue

                # OBJEK PICKING
                picking_obj = self.env['stock.picking'].sudo().browse(picking_id)
                sale_and_mutation_order = self.env[model_name].sudo().search([('id','=',transaction_id)],limit=1)
                
                if not sale_and_mutation_order:
                    message = 'Stock Picking %s Data Model %s transaction_id %s tidak ditemukan !' %(picking_name,model_name,transaction_id)
                    _logger.warning(message) 
                    self.env['teds.api.log'].sudo().create({
                        'name': 'data_not_found',
                        'description': message,
                        'module_name': module_name,
                        'status': 0,
                        'model_name': module_model_name,
                        'transaction_id': picking_id,
                        'origin': picking_name,    
                    })
                    query = """
                        UPDATE stock_picking
                        SET api_dms = 'error' 
                        WHERE id = %d
                    """ % (picking_id)
                    self._cr.execute(query)
                    continue
                    
                dms_po_origin = sale_and_mutation_order.distribution_id.dms_po_name
                dms_model_name = sale_and_mutation_order.distribution_id.dms_model_name
                if not dms_po_origin:
                    query = """
                        UPDATE stock_picking
                        SET api_dms = 'done' 
                        WHERE id = %d
                    """ % (picking_id)
                    self._cr.execute(query)
                    continue

                vals = {
                    'dms_po_origin': dms_po_origin,
                    'origin': sale_and_mutation_order.name,
                    'division': division,
                    'model_name': dms_model_name,
                    'picking_name':  picking_obj.name,
                    'picking_date':  picking_obj.date
                }
                if model_name == 'sale.order':
                    vals['no_inv'] = sale_and_mutation_order.invoice_ids[0].number
                    vals['inv_date'] = sale_and_mutation_order.invoice_ids[0].date_invoice

                lines = []
                for line in picking_obj.move_lines:                    
                    warna = """
                        SELECT 
                            pav.code AS warna,
                            pt.name AS kode_product
                        FROM product_product pp
                        INNER JOIN product_template pt ON pp.product_tmpl_id = pt.id 
                        LEFT JOIN product_attribute_value_product_product_rel pavpp_rel ON pp.id = pavpp_rel.prod_id
                        LEFT JOIN product_attribute_value pav ON pavpp_rel.att_id = pav.id
                        WHERE pp.id = %d 
                        LIMIT 1
                    """ % (line.product_id.id)
                    self._cr.execute(warna)
                    res_warna = self._cr.dictfetchall()
                    for res in res_warna:
                        lines.append({
                            'product_warna': res.get('warna',False),
                            'product_code': res.get('kode_product',False),
                            'qty': line.product_uom_qty
                        })
                if not lines:
                    message = 'Stock Picking %s data Line kosong !' %(picking_name)
                    query = """
                        UPDATE stock_picking
                        SET api_dms = 'done' 
                        WHERE id = %d
                    """ % (picking_id)
                    self._cr.execute(query)
                    continue

                vals['line_ids'] = lines
    
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
                        {'model': 'dms.api','method':'dms_create_picking_booking',
                        'args':[[],vals]})
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
                                'name':'data_not_found',
                                'description':result_message,
                                'module_name':module_name,
                                'status':0,
                                'model_name':module_model_name,
                                'transaction_id':picking_id,
                                'origin':picking_name,    
                            })
                            query = """
                                UPDATE stock_picking
                                SET api_dms = 'error' 
                                WHERE id = %d
                            """ % (picking_id)
                            self._cr.execute(query)                        

                        elif result_status == 1:
                            message = result.get('message',False)
                            _logger.warning(result_message)
                            query = """
                                UPDATE stock_picking
                                SET api_dms = 'done' 
                                WHERE id = %d
                            """ % (picking_id)
                            self._cr.execute(query)
                    else:
                        # Response tidak ada 
                        message = 'Stock Picking %s Result not found !' %(picking_name)
                        _logger.warning(message) 
                        self.env['teds.api.log'].sudo().create({
                            'name':'data_not_found',
                            'description':message,
                            'module_name':module_name,
                            'status':0,
                            'model_name':module_model_name,
                            'transaction_id':picking_id,
                            'origin':picking_name,    
                        })
                        query = """
                            UPDATE stock_picking
                            SET api_dms = 'error' 
                            WHERE id = %d
                        """ % (picking_id)
                        self._cr.execute(query)
                except odoorpc.error.RPCError as exc:
                    _logger.warning(exc)
                    self.env['teds.api.log'].sudo().create({
                        'name':'RPCError EXC',
                        'description':exc,
                        'module_name':module_name,
                        'status':0,
                        'model_name':module_model_name,
                        'transaction_id':picking_id,
                        'origin':picking_name,    
                    })
                    query = """
                        UPDATE stock_picking
                        SET api_dms = 'error' 
                        WHERE id = %d
                    """ % (picking_id)
                    self._cr.execute(query)
        else:
            _logger.warning('Data UPDATE ERROR to Draft Picking Booking') 
            update_error = """
                UPDATE stock_picking 
                SET api_dms = 'draft' 
                WHERE api_dms = 'error'
            """
            self._cr.execute(update_error)

    def api_stock_picking_unfield_unit(self):
        # ---------------Apakah masih digunakan? ----------------- #
        return True
        # -------------------------------------------------------- #
        md_id = self.env['wtc.branch'].sudo().search([('branch_type','=','MD')],limit=1).id
        models = self.env['ir.model'].sudo().search([('model','in',('wtc.mutation.order','sale.order'))])
        partner_dms = self.env['teds.api.list.partner'].sudo().search([('name','=','teds.api.list.partner')])
        list_model = [x.id for x in models]
        list_partner_dms = [x.id for x in partner_dms.partner_ids]
        
        picking_query = """
            SELECT  
                sp.id as picking_id
                , sp.name as picking_name
                , sp.division as division
                , sp.transaction_id as transaction
                , sp.branch_id as branch
                , md.model as model
                , part.default_code as default_code
                FROM stock_picking as sp 
                LEFT JOIN ir_model AS md on md.id=sp.model_id
                LEFT JOIN res_partner as part on part.id = sp.partner_id
                WHERE 1=1
                AND sp.state = 'done'
                AND sp.status_api = 'draft'
                AND sp.branch_id = %d
                AND sp.model_id in %s
                AND sp.partner_id in %s
                AND sp.division in ('Unit','Sparepart')
                LIMIT 1
        """ %(md_id,tuple(list_model),tuple(list_partner_dms))
        self._cr.execute(picking_query)
        ress = self._cr.dictfetchall()
        
        if ress :    
            picking_id = ress[0].get('picking_id')
            division = ress[0].get('division')
            transaction_id = ress[0].get('transaction')
            branch_id = ress[0].get('branch')
            model_name = ress[0].get('model')
            branch_code_partner = ress[0].get('default_code')
            picking_name = ress[0].get('picking_name')

            picking_obj = self.env['stock.picking'].sudo().browse(picking_id)

            sale_and_mutation_order = self.env[model_name].sudo().search([('id','=',transaction_id)],limit=1)
            if not sale_and_mutation_order:
                    message = 'data_not_found'
                    _logger.warning('%s' %message) 
                    self.env['teds.api.log'].sudo().create({
                        'name':message,
                        'description':'Object tidak ditemukan.',
                        'module_name':'TEDS API STOCK PICKING',
                        'status':0,
                        'model_name':'stock.picking',
                        'transaction_id':picking_id,
                        'origin':picking_name,    
                    })
                    picking_obj.sudo().status_api = 'error'
                    return True

            dms_po_origin = sale_and_mutation_order.distribution_id.dms_po_name
            dms_model_id = sale_and_mutation_order.distribution_id.dms_model_id
            dms_model_name = sale_and_mutation_order.distribution_id.dms_model_name
            distribution_line = sale_and_mutation_order.distribution_id.distribution_line
            picking_origin = sale_and_mutation_order.name


            if not dms_po_origin:
                picking_obj.sudo().status_api = 'done'
                return True

            
            vals = {
                'dms_po_origin':dms_po_origin,
                'origin':sale_and_mutation_order.name,
                'division':division,
                'model_name':dms_model_name,
            }

            no_inv = False
            if model_name == 'sale.order':
                no_inv = sale_and_mutation_order.invoice_ids[0].number
                date_inv = sale_and_mutation_order.invoice_ids[0].date_invoice
                vals['no_inv'] = no_inv
                vals['inv_date'] = date_inv


            line_ids = []
            if division == 'Unit':
                product_control = {}
                for line in distribution_line:
                    warna = """
                            SELECT pav.code as warna
                            FROM product_product pp
                            INNER JOIN product_template pt ON pt.id = pp.product_tmpl_id 
                            LEFT JOIN product_attribute_value_product_product_rel rel ON rel.prod_id = pp.id
                            LEFT JOIN product_attribute_value pav ON pav.id = rel.att_id 
                            WHERE pp.id = %d LIMIT 1
                        """ %(line.product_id.id)
                    self._cr.execute(warna)
                    ress = self._cr.fetchone()
                    warna_code = ress[0]

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


                # detail_operation_picking
                for operation in picking_obj.pack_operation_ids:
                    if product_control[operation.product_id.id]:
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
                for line in distribution_line:
                    if not product_control.get(line.product_id.id):
                        product_control[line.product_id.id] = {
                            'product_code':line.product_id.name,
                            'qty':line.approved_qty,
                            'qty_spl':0,
                            'detail_ids':[]
                        }
                    else:
                        product_control[line.product_id.id]['qty'] += line.approved_qty


                # detail_operation_picking
                for operation in picking_obj.pack_operation_ids:
                    if product_control[operation.product_id.id]:
                        product_control[operation.product_id.id]['detail_ids'].append({
                            'qty':operation.product_qty,
                            'origin':operation.picking_id.name,
                        })
                        product_control[operation.product_id.id]['qty_spl'] += operation.product_qty

                vals['line_ids'] = product_control.values()

            
            config_user = self.env['teds.api.configuration'].sudo().search([('branch_id','=',branch_id)])
            if not config_user:
                message = 'Silahkan buat configuration terlebih dahulu untuk bisa mengakses ke DMS.'
                _logger.warning('%s' %message) 
                self.env['teds.api.log'].sudo().create({
                    'name':'not_authorized',
                    'description':message,
                    'module_name':'TEDS API STOCK PICKING',
                    'status':0,
                    'model_name':'stock.picking',
                    'transaction_id':picking_id,
                    'origin':picking_name,    
                })

                picking_obj.sudo().status_api = 'error'

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
                            'model_name':'stock.picking',
                            'transaction_id':picking_id,
                            'origin':picking_name,    
                        })
                        picking_obj.sudo().status_api = 'error'
                    
                    elif result['status'] == 1:
                        message = result.get('message',False)
                        _logger.warning('%s' %(message))
                        picking_obj.sudo().status_api = 'done'
                    

            except odoorpc.error.RPCError as exc:
                _logger.warning('%s' %(exc))
                self.env['teds.api.log'].sudo().create({
                    'name':'raise_warning',
                    'description':exc,
                    'module_name':'DMS API STOCK PICKING',
                    'status':0,
                    'model_name':'stock.picking',
                    'transaction_id':picking_id,
                    'origin':picking_name,    
                })

                picking_obj.sudo().status_api = 'error'
        else:
            _logger.warning('Data UPDATE ERROR to Draft Picking Unfield') 
            update_error = """
                UPDATE stock_picking 
                SET status_api = 'draft' 
                WHERE status_api = 'error'
            """
            self._cr.execute(update_error)