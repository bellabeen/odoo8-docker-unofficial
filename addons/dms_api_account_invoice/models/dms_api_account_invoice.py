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

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    status_api = fields.Selection([
        ('draft','Draft'),
        ('error','Error'),
        ('done','Done'),
    ],default='draft',string='Status API')


    @api.multi
    def api_dms_account_invoice(self):
        message = False
        module_name = 'TEDS API INVOICE SUPPLIER'
        module_model_name = 'account.invoice'

        search = """
            SELECT ai.id 
            , sd.dms_po_name
            , sd.dms_transaction_id
            , sd.dms_model_name
            , model.model
            , ai.branch_id
            FROM account_invoice  as ai
            INNER JOIN wtc_branch b on b.id = ai.branch_id
            INNER JOIN ir_model model on model.id = ai.model_id
            INNER JOIN teds_api_list_partner_rel list_p ON list_p.parter_id = ai.partner_id
            LEFT JOIN sale_order as so on so.id= ai.transaction_id
            LEFT JOIN wtc_stock_distribution as sd on sd.id=so.distribution_id
            WHERE b.branch_type = 'MD'
            AND ai.state in ('open','paid')
            AND ai.type = 'out_invoice'
            AND ai.status_api = 'draft'
            AND model.model = 'sale.order'
            ORDER BY ai.id ASC
            LIMIT 20
        """
        self._cr.execute(search)
        ress = self._cr.dictfetchall()
        if ress :
            for res in ress:
                dms_origin = res.get('dms_po_name')
                dms_transaction_id = res.get('dms_transaction_id')
                dms_model_name = res.get('dms_model_name')
                invoice_id = res.get('id')
                branch_id = res.get('branch_id')

                invoice_obj = self.sudo().browse(invoice_id)
                invoice_name = invoice_obj.number
                # Cek Config
                config_user = self.env['teds.api.configuration'].sudo().search([('branch_id','=',branch_id)],limit=1)
                if not config_user:
                    message = 'Invoice Supplier %s silahkan buat configuration terlebih dahulu untuk bisa mengakses ke DMS' %(invoice_name)
                    _logger.warning(message) 
                    self.env['teds.api.log'].sudo().create({
                        'name':'not_authorized',
                        'description':message,
                        'module_name':module_name,
                        'status':0,
                        'model_name':module_model_name,
                        'transaction_id':invoice_id,
                        'origin':invoice_name,    
                    })
                    query = """
                        UPDATE account_invoce
                        SET status_api='error' 
                        WHERE id = %d
                    """ % (invoice_id)
                    self._cr.execute(query)
                    continue

                line = []
                for x in invoice_obj.invoice_line:
                    if invoice_obj.division == 'Unit':
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
                            'product_code':x.product_id.name,
                            'warna_code':warna_code,
                            'description':x.name,
                            'quantity':x.quantity,
                            'price':x.price_unit,
                            'discount':x.discount,
                        })
        
                    else:
                        line.append({
                            'product_code':x.product_id.name,
                            'description':x.name,
                            'quantity':x.quantity,
                            'price':x.price_unit,
                            'discount':x.discount,
                         })
            
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
                        {'model': 'dms.api','method':'dms_account_invoice_create',
                        'args':[[], 
                            {
                                'code_md':invoice_obj.branch_id.code,
                                'code_dealer': invoice_obj.partner_id.default_code,
                                'dms_origin':dms_origin,
                                'dms_model_name': dms_model_name,
                                'dms_transaction_id': dms_transaction_id,
                                'origin':invoice_obj.number,
                                'date_due':invoice_obj.date_due,
                                'date_invoice':invoice_obj.date_invoice,
                                # 'date_invoice_supplier':invoice.document_date,
                                'detail': line,
                                'division': invoice_obj.division,
                                'discount_cash':invoice_obj.discount_cash,
                                'discount_program':invoice_obj.discount_program,
                                'discount_lain':invoice_obj.discount_lain,
                                'source_document':invoice_obj.origin,
                                'comment': invoice_obj.comment,
                                'amount_total': invoice_obj.amount_total
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
                                    'transaction_id':invoice_id,
                                    'origin':invoice_name,    
                                })
                            query = """
                                UPDATE account_invoice 
                                SET status_api = 'error' 
                                WHERE id = %d
                            """ % (invoice_id)
                            self._cr.execute(query)

                        elif result_status == 1:
                            _logger.warning('%s' %(result_message))
                            query = """
                                UPDATE account_invoice 
                                SET status_api='done' 
                                WHERE id = %d
                            """ % (invoice_id)
                            self._cr.execute(query)
                    else:
                        # Response tidak ada 
                        message = 'Invoice Supplier %s Result not found !' %(invoice_name)
                        _logger.warning(message) 
                        self.env['teds.api.log'].sudo().create({
                            'name':'data_not_found',
                            'description':message,
                            'module_name':module_name,
                            'status':0,
                            'model_name':module_model_name,
                            'transaction_id':invoice_id,
                            'origin':invoice_name,    
                        })
                        query = """
                            UPDATE account_invoice 
                            SET status_api='error' 
                            WHERE id = %d
                        """ % (invoice_id)
                        self._cr.execute(query)                    
                except odoorpc.error.RPCError as exc:
                    _logger.warning(exc)
                    self.env['teds.api.log'].sudo().create({
                        'name':'RPCError EXC',
                        'description':exc,
                        'module_name':module_name,
                        'status':0,
                        'model_name':module_model_name,
                        'transaction_id':invoice_id,
                        'origin':invoice_name,
                    })
                    query = """
                        UPDATE account_invoice
                        SET status_api='error' 
                        WHERE id = %d
                    """ % (invoice_id)
                    self._cr.execute(query)
             
        else:
            _logger.warning('Data Update Error to Draft Account Invoice')
            update_error = """
                    UPDATE account_invoice 
                    SET status_api = 'draft' 
                    WHERE status_api = 'error'
                """
            self._cr.execute(update_error)





    @api.multi
    def api_dms_account_invoice_manual(self,origin):
        raise Warning('Tidak bisa digunakan !')
        message = False
        status = 1
        md_id = self.env['wtc.branch'].sudo().search([('code','=','MML')],limit=1).id
        models = self.env['ir.model'].sudo().search([('model','=','sale.order')])
        models =models.id
        partner_dms = self.env['teds.api.list.partner'].sudo().search([('name','=','teds.api.list.partner')])
        # ipdb.set_trace()
        list_partner_dms = [x.id for x in partner_dms.partner_ids]
        search = """
                    SELECT ai.id from account_invoice  as ai
                    LEFT JOIN sale_order as so on so.id= ai.transaction_id
                    LEFT JOIN wtc_stock_distribution as sd on sd.id=so.distribution_id
                    where 1=1 
                    AND ai.state in ('open','paid')
                    AND ai.status_api = 'draft'
                    and ai.type = 'out_invoice'
                    and ai.model_id = '%s'
                    AND ai.branch_id = %s
                    AND ai.partner_id in %s
                    AND ai.number = '%s'
                    limit 1
                """ %(models,md_id,str(tuple(list_partner_dms)).replace(",)",")"),origin)
        self._cr.execute(search)
        ress = self._cr.dictfetchall()

        if ress :
            obj = ress[0].get('id')
            # ipdb.set_trace()
            invoice = self.browse(obj)
            _logger.warning('Data found Account Invoice %s' %(invoice.id))
            transaction_id = invoice.transaction_id
            model_id = invoice.model_id
            sale_order = self.env[model_id.model].sudo().search([
                ('id','=',transaction_id),
            ],limit=1)
            if not sale_order:
                message = 'Object tidak ditemukan.'
                _logger.warning('%s' %message) 
                # create log di teds
                log_obj = self.env['teds.api.log']
                cek_log = log_obj.search([
                    ('name','=','data_not_found'),
                    ('description','=',message),
                    ('module_name','=','DMS API ACCOUNT INVOICE'),
                    ('model_name','=','account.invoice'),
                    ('transaction_id','=',invoice.id),
                    ('origin','=',invoice.number)],limit=1)
                if not cek_log:
                    log_obj.sudo().create({
                        'name':'data_not_found',
                        'description':message,
                        'module_name':'DMS API ACCOUNT INVOICE',
                        'status':0,
                        'model_name':'account.invoice',
                        'transaction_id':invoice.id,
                        'origin':invoice.number,    
                    })

            dms_origin = sale_order.distribution_id.dms_po_name
            dms_model_name = sale_order.distribution_id.dms_model_name
            dms_transaction_id = sale_order.distribution_id.dms_transaction_id
            # if not dms_origin:
            #     query = """
            #         UPDATE account_invoice 
            #         SET status_api='done' 
            #         WHERE id = %d
            #     """ % (invoice.id)
            #     self._cr.execute(query)
            #     return False

            line = []
            for x in invoice.invoice_line:
                if invoice.division == 'Unit':
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
                        'warna_code':warna_code,
                        'description':x.name,
                        'quantity':x.quantity,
                        'price':x.price_unit,
                        'discount':x.discount,
                    })
    
                else:
                    line.append({
                        'product_code':x.product_id.name,
                        'description':x.name,
                        'quantity':x.quantity,
                        'price':x.price_unit,
                        'discount':x.discount,
                     })
            
            config_user = self.env['teds.api.configuration'].search([('branch_id','=',invoice.branch_id.id)])
            if not config_user:
                message = 'Silahkan buat configuration terlebih dahulu untuk bisa akses ke DMS.'
                _logger.warning('%s' %message) 
                # create log di teds
                log_obj = self.env['teds.api.log']
                cek_log = log_obj.search([
                    ('name','=','data_not_found'),
                    ('description','=',message),
                    ('module_name','=','DMS API ACCOUNT INVOICE'),
                    ('model_name','=','account.invoice'),
                    ('transaction_id','=',invoice.id),
                    ('origin','=',invoice.number)],limit=1)
                if not cek_log:
                    log_obj.sudo().create({
                        'name':'data_not_found',
                        'description':message,
                        'module_name':'DMS API ACCOUNT INVOICE',
                        'status':0,
                        'model_name':'account.invoice',
                        'transaction_id':invoice.id,
                        'origin':invoice.number,    
                    })

            if message:
                query = """
                    UPDATE account_invoice 
                    SET status_api = 'error' 
                    WHERE id = %d
                """ % (invoice.id)
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
                        {'model': 'dms.api','method':'dms_account_invoice_create',
                        'args':[[], 
                            {
                                'code_md':invoice.branch_id.code,
                                'code_dealer': invoice.partner_id.default_code,
                                'dms_origin':dms_origin,
                                'dms_model_name': dms_model_name,
                                'dms_transaction_id': dms_transaction_id,
                                'origin':invoice.number,
                                'date_due':invoice.date_due,
                                'date_invoice':invoice.date_invoice,
                                # 'date_invoice_supplier':invoice.document_date,
                                'detail': line,
                                'division': invoice.division,
                                'discount_cash':invoice.discount_cash,
                                'discount_program':invoice.discount_program,
                                'discount_lain':invoice.discount_lain,
                                'source_document':invoice.origin,
                                'comment': invoice.comment,
                                'amount_total': invoice.amount_total
                        }]})
                    
                    # finally
                    result =  data.get('result',False)
                    if result:
                        if result['status'] == 0:
                            _logger.warning('%s' %result.get('message',False)) 
                            # create log di teds
                            log_obj = self.env['teds.api.log']
                            cek_log = log_obj.search([
                                ('name','=',result.get('error',False)),
                                ('description','=',result.get('remark',False)),
                                ('module_name','=','DMS API ACCOUNT INVOICE'),
                                ('model_name','=','account.invoice'),
                                ('transaction_id','=',invoice.id),
                                ('origin','=',invoice.number)],limit=1)
                            if not cek_log:
                                log_obj.sudo().create({
                                    'name':result.get('error',False),
                                    'description':result.get('remark',False),
                                    'module_name':'DMS API ACCOUNT INVOICE',
                                    'status':result.get('status',False),
                                    'model_name':'account.invoice',
                                    'transaction_id':invoice.id,
                                    'origin':invoice.name,    
                                })
                            query = """
                                UPDATE account_invoice 
                                SET status_api = 'error' 
                                WHERE id = %d
                            """ % (invoice.id)
                            self._cr.execute(query)
                        elif result['status'] == 1:
                            message = result.get('message',False)
                            _logger.warning('%s' %(message))
                            query = """
                                UPDATE account_invoice 
                                SET status_api='done' 
                                WHERE id = %d
                            """ % (invoice.id)
                            self._cr.execute(query)    

                except odoorpc.error.RPCError as exc:
                    _logger.warning('%s' %(exc))
                    # create log di teds
                    log_obj = self.env['teds.api.log']
                    cek_log = log_obj.search([
                        ('name','=',result.get('error',False)),
                        ('description','=',result.get('remark',False)),
                        ('module_name','=','DMS API ACCOUNT INVOICE'),
                        ('model_name','=','account.invoice'),
                        ('transaction_id','=',invoice.id),
                        ('origin','=',invoice.number)],limit=1)
                    if not cek_log:
                        log_obj.sudo().create({
                            'name':'raise_warning',
                            'description':exc,
                            'module_name':'DMS API ACCOUNT INVOICE',
                            'status':0,
                            'model_name':'account.invoice',
                            'transaction_id':invoice.id,
                            'origin':invoice.origin,    
                        })
                    query = """
                        UPDATE account_invoice 
                        SET status_api='error' 
                        WHERE id = %d
                    """ % (invoice.id)
                    self._cr.execute(query)   
             
        else:
            raise Warning('Data Tidak ditemukan untuk transaksi "%s" ' %(origin))