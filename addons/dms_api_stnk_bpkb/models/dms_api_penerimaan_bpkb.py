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

class PenerimaanBpkb(models.Model):
    _inherit = "wtc.penerimaan.bpkb"

    status_api = fields.Selection([
        ('draft','Draft'),
        ('error','Error'),
        ('done','Done'),
    ],default='draft',string='Status API')

    @api.multi
    def api_dms_penerimaan_bpkb(self):
        area = self.env['wtc.area'].search([('code','=','AREA_LAMPUNG')],limit=1)
        list_branch = [b.id for b in area.branch_ids] 
        penerimaan_bpkb = self.search([
            ('state','=','posted'),
            ('status_api','=','draft'),
            ('branch_id','in',list_branch),
        ],limit=1)
        
        if penerimaan_bpkb:
            _logger.warning('Data found Penerimaan BPKB %s' %(penerimaan_bpkb.id))
            model = 'wtc.penerimaan.bpkb'
            message = False
            config_user = self.env['teds.api.configuration'].search([('branch_id','=',penerimaan_bpkb.branch_id.id)])
            if not config_user:
                message = 'Silahkan buat configuration terlebih dahulu untuk bisa akses ke DMS.'
                _logger.warning('%s' %message) 
                self.env['teds.api.log'].sudo().create({
                    'name':'data_not_found',
                    'description':message,
                    'module_name':'DMS API PENERIMAAN BPKB',
                    'status':0,
                    'model_name':model,
                    'transaction_id':penerimaan_bpkb.id,
                    'origin':penerimaan_bpkb.name,    
                })

            if message:
                query = """
                    UPDATE wtc_penerimaan_bpkb
                    SET status_api='error' 
                    WHERE id = %d
                """ % (penerimaan_bpkb.id)
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

                    line = []
                    for x in penerimaan_bpkb.penerimaan_line:  
                        terima_bpkb = False
                        if x.no_bpkb:
                            terima_bpkb = True
                        line.append({
                            'no_engine':x.name.name,
                            'terima_bpkb':terima_bpkb,
                        })

                    data = odoo.json(
                        '/web/dataset/call',
                        {'model': 'dms.api','method':'dms_penerimaan_bpkb_create',
                        'args':[[], 
                            {
                                'dealer_code':penerimaan_bpkb.branch_id.code,
                                'birojasa_code':penerimaan_bpkb.partner_id.rel_code,
                                'lokasi_bpkb':penerimaan_bpkb.lokasi_bpkb_id.name,
                                'tgl_terima':penerimaan_bpkb.tgl_terima,    
                                'detail':line,
                        }]})
                    
                    # finally
                    result =  data.get('result',False)
                    if result:
                        if result['status'] == 0:
                            _logger.warning('%s' %result.get('message',False)) 
                            self.env['teds.api.log'].sudo().create({
                                'name':result.get('error',False),
                                'description':result.get('remark',False),
                                'module_name':'DMS API PENERIMAAN BPKB',
                                'status':result.get('status',False),
                                'model_name':model,
                                'transaction_id':penerimaan_bpkb.id,
                                'origin':penerimaan_bpkb.name,    
                            })
                            query = """
                                UPDATE wtc_penerimaan_bpkb 
                                SET status_api='error' 
                                WHERE id = %d
                            """ % (penerimaan_bpkb.id)
                            self._cr.execute(query)
                        elif result['status'] == 1:
                            _logger.warning('%s' %result.get('message',False))
                            query = """
                                UPDATE wtc_penerimaan_bpkb 
                                SET status_api='done' 
                                WHERE id = %d
                            """ % (penerimaan_bpkb.id)
                            self._cr.execute(query)

                except odoorpc.error.RPCError as exc:
                    _logger.warning('%s' %(exc))
                    self.env['teds.api.log'].sudo().create({
                        'name':'raise_warning',
                        'description':exc,
                        'module_name':'DMS API PENERIMAAN BPKB',
                        'status':0,
                        'model_name':model,
                        'transaction_id':penerimaan_bpkb.id,
                        'origin':penerimaan_bpkb.name,    
                    })
                    query = """
                        UPDATE wtc_penerimaan_bpkb 
                        SET status_api='error' 
                        WHERE id = %d
                    """ % (penerimaan_bpkb.id)
                    self._cr.execute(query)    
        else:
            _logger.warning('Data UPDATE ERROR to Draft Penerimaan BPKB') 
            update_error = """
                UPDATE wtc_penerimaan_bpkb 
                SET status_api = 'draft' 
                WHERE status_api = 'error'
            """
            self._cr.execute(update_error)