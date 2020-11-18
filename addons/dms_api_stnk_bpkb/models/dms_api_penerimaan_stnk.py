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

class PenerimaanStnk(models.Model):
    _inherit = "wtc.penerimaan.stnk"

    status_api = fields.Selection([
        ('draft','Draft'),
        ('error','Error'),
        ('done','Done'),
    ],default='draft',string='Status API')

    @api.multi
    def api_dms_penerimaan_stnk(self):
        area = self.env['wtc.area'].search([('code','=','AREA_LAMPUNG')],limit=1)
        list_branch = [b.id for b in area.branch_ids] 
        penerimaan_stnk = self.search([
            ('state','=','posted'),
            ('status_api','=','draft'),
            ('branch_id','in',list_branch)
        ],limit=1)
        
        if penerimaan_stnk:
            _logger.warning('Data found Penerimaan Stnk %s' %(penerimaan_stnk.id)) 
            model = 'wtc.penerimaan.stnk'
            message = False
            config_user = self.env['teds.api.configuration'].search([('branch_id','=',penerimaan_stnk.branch_id.id)])
            if not config_user:
                message = 'Silahkan buat configuration terlebih dahulu.'
                _logger.warning('%s' %message) 
                self.env['teds.api.log'].sudo().create({
                    'name':'data_not_found',
                    'description':message,
                    'module_name':'DMS API PENERIMAAN STNK',
                    'status':0,
                    'model_name':model,
                    'transaction_id':penerimaan_stnk.id,
                    'origin':penerimaan_stnk.name,    
                })
            if message:
                query = """
                    UPDATE wtc_penerimaan_stnk
                    SET status_api='error' 
                    WHERE id = %d
                """ % (penerimaan_stnk.id)
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
                    for x in penerimaan_stnk.penerimaan_line:  
                        line.append({
                            'no_engine':x.name.name
                        })
                        terima_hologram = False
                        terima_notice = False
                        terima_stnk = False
                        terima_nopol = x.is_nopol
                        terima_stck = False
                        if x.no_notice:
                            terima_notice = True
                            terima_hologram = True
                        if x.no_stnk:
                            terima_stnk = True
                        if terima_hologram:
                            line[0]['terima_hologram']= terima_hologram
                        if terima_notice:
                            line[0]['terima_notice'] = terima_notice
                        if terima_stnk:
                            line[0]['terima_stnk'] = terima_stnk
                        if terima_nopol:
                            line[0]['terima_nopol'] = terima_nopol
                        if terima_stck:
                            line[0]['terima_stck'] = terima_stck
                        
                    data = odoo.json(
                        '/web/dataset/call',
                        {'model': 'dms.api','method':'dms_penerimaan_stnk_create',
                        'args':[[], 
                            {
                                'dealer_code':penerimaan_stnk.branch_id.code,
                                'birojasa_code':penerimaan_stnk.partner_id.rel_code,
                                'lokasi_stnk':penerimaan_stnk.lokasi_stnk_id.name,
                                'tanggal':penerimaan_stnk.tgl_terima,    
                                'detail':line,
                        }]})
                    
                    # finally
                    result =  data.get('result',False)
                    if result:
                        if result['status'] == 0:
                            _logger.warning('%s' %result.get('error',False)) 
                            self.env['teds.api.log'].sudo().create({
                                'name':result.get('error',False),
                                'description':result.get('remark',False),
                                'module_name':'DMS API PENERIMAAN STNK',
                                'status':result.get('status',False),
                                'model_name':model,
                                'transaction_id':penerimaan_stnk.id,
                                'origin':penerimaan_stnk.name,    
                            })
                            query = """
                                UPDATE wtc_penerimaan_stnk 
                                SET status_api='error' 
                                WHERE id = %d
                            """ % (penerimaan_stnk.id)
                            self._cr.execute(query)
                        elif result['status'] == 1:
                            message = result.get('message',False)
                            _logger.warning('%s' %(message))
                            query = """
                                UPDATE wtc_penerimaan_stnk 
                                SET status_api='done' 
                                WHERE id = %d
                            """ % (penerimaan_stnk.id)
                            self._cr.execute(query)

                except odoorpc.error.RPCError as exc:
                    _logger.warning('%s' %(exc))
                    self.env['teds.api.log'].sudo().create({
                        'name':'raise_warning',
                        'description':exc,
                        'module_name':'DMS API PENERIMAAN STNK',
                        'status':0,
                        'model_name':model,
                        'transaction_id':penerimaan_stnk.id,
                        'origin':penerimaan_stnk.name,    
                    })
                    query = """
                        UPDATE wtc_penerimaan_stnk 
                        SET status_api='error' 
                        WHERE id = %d
                    """ % (penerimaan_stnk.id)
                    self._cr.execute(query)
        else:
            _logger.warning('Data UPDATE ERROR to Draft Penerimaan STNK') 
            update_error = """
                UPDATE wtc_penerimaan_stnk 
                SET status_api = 'draft' 
                WHERE status_api = 'error'
            """
            self._cr.execute(update_error)