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

class penyerahanStnk(models.Model):
    _inherit = "wtc.penyerahan.stnk"

    status_api = fields.Selection([
        ('draft','Draft'),
        ('error','Error'),
        ('done','Done'),
    ],default='draft',string='Status API')

    @api.multi
    def api_dms_penyerahan_stnk(self):
        area = self.env['wtc.area'].search([('code','=','AREA_LAMPUNG')],limit=1)
        list_branch = [b.id for b in area.branch_ids]  
        penyerahan_stnk = self.search([
            ('state','=','posted'),
            ('status_api','=','draft'),
            ('branch_id','in',list_branch)
        ],limit=1)
        
        if penyerahan_stnk:
            _logger.warning('Data found penyerahan STNK %s' %(penyerahan_stnk.id)) 
            model = 'wtc.penyerahan.stnk'
            message = False
            config_user = self.env['teds.api.configuration'].search([('branch_id','=',penyerahan_stnk.branch_id.id)])
            if not config_user:
                message = 'Silahkan buat configuration terlebih dahulu.'
                _logger.warning('%s' %message) 
                self.env['teds.api.log'].sudo().create({
                    'name':'data_not_found',
                    'description':message,
                    'module_name':'DMS API PENYERAHAN STNK',
                    'status':0,
                    'model_name':model,
                    'transaction_id':penyerahan_stnk.id,
                    'origin':penyerahan_stnk.name,    
                })
            if message:
                query = """
                    UPDATE wtc_penyerahan_stnk
                    SET status_api='error' 
                    WHERE id = %d
                """ % (penyerahan_stnk.id)
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
                    for x in penyerahan_stnk.penyerahan_line:  
                        serah_stnk = False
                        serah_nopol = False
                        serah_stck = False
                        if x.tgl_ambil_stnk:
                            serah_stnk = True
                        if x.tgl_ambil_polisi:
                            serah_nopol = True
                        line.append({
                            'no_engine':x.name.name,
                            'serah_stnk':serah_stnk,
                            'serah_nopol':serah_nopol,
                            'serah_stck':serah_stck,
                        })

                    data = odoo.json(
                        '/web/dataset/call',
                        {'model': 'dms.api','method':'dms_penyerahan_stnk_create',
                        'args':[[], 
                            {   
                                'dealer_code':penyerahan_stnk.branch_id.code,
                                'tanggal':penyerahan_stnk.tanggal,    
                                'penerima':penyerahan_stnk.penerima,
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
                                'module_name':'DMS API PENYERAHAN STNK',
                                'status':result.get('status',False),
                                'model_name':model,
                                'transaction_id':penyerahan_stnk.id,
                                'origin':penyerahan_stnk.name,    
                            })
                            query = """
                                UPDATE wtc_penyerahan_stnk 
                                SET status_api='error' 
                                WHERE id = %d
                            """ % (penyerahan_stnk.id)
                            self._cr.execute(query)
                        elif result['status'] == 1:
                            message = result.get('message',False)
                            _logger.warning('%s' %(message))
                            query = """
                                UPDATE wtc_penyerahan_stnk 
                                SET status_api='done' 
                                WHERE id = %d
                            """ % (penyerahan_stnk.id)
                            self._cr.execute(query)
        
                except odoorpc.error.RPCError as exc:
                    _logger.warning('%s' %(exc))
                    self.env['teds.api.log'].sudo().create({
                        'name':'raise_warning',
                        'description':exc,
                        'module_name':'DMS API PENYERAHAN STNK',
                        'status':0,
                        'model_name':model,
                        'transaction_id':penyerahan_stnk.id,
                        'origin':penyerahan_stnk.name,    
                    })
                    query = """
                        UPDATE wtc_penyerahan_stnk 
                        SET status_api='error' 
                        WHERE id = %d
                    """ % (penyerahan_stnk.id)
                    self._cr.execute(query)    
        else:
            _logger.warning('Data UPDATE ERROR to Draft Penyerahan STNK') 
            update_error = """
                UPDATE wtc_penyerahan_stnk 
                SET status_api = 'draft' 
                WHERE status_api = 'error'
            """
            self._cr.execute(update_error)