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

class DealerSaleOrder(models.Model):
    _inherit = "dealer.sale.order"

    no_buku_tamu = fields.Char('No Buku Tamu')
    status_api = fields.Selection([
        ('draft','Draft'),
        ('error','Error'),
        ('done','Done'),
    ],default='draft',string='Status API')


    @api.multi
    def api_dms_sale_order(self):
        area = self.env['wtc.area'].search([('code','=','AREA_LAMPUNG')],limit=1)
        list_branch = [b.id for b in area.branch_ids]            
        sale_order = self.search([
            ('state','=','done'),
            ('status_api','=','draft'),
            ('branch_id','in',list_branch),
            ('no_buku_tamu','!=',False),
        ],limit=1)
        if sale_order:
            _logger.warning('Data found Sale Order %s' %(sale_order.id))
            model = 'dealer.sale.order'
            message = False
            config_user = self.env['teds.api.configuration'].search([('branch_id','=',sale_order.branch_id.id)])
            if not config_user:
                message = 'Silahkan buat configuration terlebih dahulu untuk bisa mengakses ke DMS.'
                _logger.warning('%s' %message) 
                self.env['teds.api.log'].sudo().create({
                    'name':'data_not_found',
                    'description':message,
                    'module_name':'DMS API SALE ORDER',
                    'status':0,
                    'model_name':'dealer.sale.order',
                    'transaction_id':sale_order.id,
                    'origin':sale_order.name,    
                })

            if message:
                query = """
                    UPDATE dealer_sale_order 
                    SET status_api='error' 
                    WHERE id = %d
                """ % (sale_order.id)
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
                    for x in sale_order.dealer_sale_order_line:
                        tax = False
                        if x.tax_id:
                            tax = True

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
                        ps_line = []
                        bb_line = []
                        if x.discount_line:
                            for ps in x.discount_line:
                                ps_line.append({
                                'code_ps':ps.program_subsidi.name,
                            })
                        if x.barang_bonus_line:
                            for bb in x.barang_bonus_line:
                                bb_line.append({
                                    'code_bb': bb.barang_subsidi_id.name,    
                                })
                        
                        line.append({
                            'product_code':x.product_id.name,
                            'warna_code':warna_code,
                            'no_engine':x.lot_id.name,
                            'quantity':x.product_qty,
                            'bbn':x.is_bbn,
                            'disc_po':x.discount_po,
                            'biro_jasa_code':x.biro_jasa_id.rel_code,
                            'program_subsidi':ps_line,
                            'barang_bonus':bb_line,
                        })
                    cddb = {
                        'name' : sale_order.cddb_id.name,
                        'street' : sale_order.cddb_id.street,
                        'rt' : sale_order.cddb_id.rt,
                        'rw' : sale_order.cddb_id.rw,
                        'state' : sale_order.cddb_id.state_id.code,
                        'city' : sale_order.cddb_id.city_id.code,
                        'kecamatan' : sale_order.cddb_id.kecamatan_id.code,
                        'kelurahan' : sale_order.cddb_id.zip_id.zip,
                        'no_ktp': sale_order.cddb_id.no_ktp,
                        'birtdate' : sale_order.cddb_id.birtdate,
                        'agama' : sale_order.cddb_id.agama_id.value,
                        'pendidikan' : sale_order.cddb_id.pendidikan_id.value,
                        'pekerjaan' : sale_order.cddb_id.pekerjaan_id.value,
                        'pengeluaran' : sale_order.cddb_id.pengeluaran_id.value,
                        'kode_customer' : sale_order.cddb_id.kode_customer,
                        'penanggung_jawab' : sale_order.cddb_id.penanggung_jawab,
                        'no_hp':sale_order.cddb_id.no_hp,
                        'no_telp':sale_order.cddb_id.no_telp,
                        'dpt_dihubungi' : sale_order.cddb_id.dpt_dihubungi,
                        'status_hp' : sale_order.cddb_id.status_hp_id.value,
                        'status_rumah' : sale_order.cddb_id.status_rumah_id.value,
                        'jenis_kelamin' : sale_order.cddb_id.jenis_kelamin_id.value,
                        'jenismotor' : sale_order.cddb_id.jenismotor_id.value,
                        'merkmotor' : sale_order.cddb_id.merkmotor_id.value,
                        'penggunaan' : sale_order.cddb_id.penggunaan_id.value,
                        'pengguna' : sale_order.cddb_id.pengguna_id.value,
                        'suku' : sale_order.cddb_id.suku,
                        'pin_bbm' : sale_order.cddb_id.pin_bbm,
                        'hobi' : sale_order.cddb_id.hobi.id,
                        'facebook': sale_order.cddb_id.facebook,
                        'instagram': sale_order.cddb_id.instagram,
                        'twitter': sale_order.cddb_id.twitter,
                        'path': sale_order.cddb_id.path,
                        'youtube': sale_order.cddb_id.youtube,
                        'jabatan' : sale_order.cddb_id.jabatan,
                        'no_wa' : sale_order.cddb_id.no_wa,
                        'gol_darah' : sale_order.cddb_id.gol_darah.id,
                    }
                    
                    data = odoo.json(
                        '/web/dataset/call',
                        {'model': 'dms.api','method':'dms_sale_order_create',
                        'args':[[], 
                            {
                                'no_buku_tamu':sale_order.no_buku_tamu,
                                'date_order':sale_order.date_order,
                                'cddb':cddb,
                                'detail': line,
                        }]})
                    
                    # finally
                    result =  data.get('result',False)
                    if result:
                        if result['status'] == 0:
                            _logger.warning('%s' %result.get('message',False)) 
                            self.env['teds.api.log'].sudo().create({
                                'name':result.get('error',False),
                                'description':result.get('remark',False),
                                'module_name':'DMS API SALE ORDER',
                                'status':result.get('status',False),
                                'model_name':model,
                                'transaction_id':sale_order.id,
                                'origin':sale_order.name,    
                            })
                            query = """
                                UPDATE dealer_sale_order 
                                SET status_api='error' 
                                WHERE id = %d
                            """ % (sale_order.id)
                            self._cr.execute(query)
                        elif result['status'] == 1:
                            message = result.get('message',False)
                            _logger.warning('%s' %(message))
                            query = """
                                UPDATE dealer_sale_order 
                                SET status_api='done' 
                                WHERE id = %d
                            """ % (sale_order.id)
                            self._cr.execute(query)
                            
                except odoorpc.error.RPCError as exc:
                    _logger.warning('%s' %(exc))
                    self.env['teds.api.log'].sudo().create({
                        'name':'raise_warning',
                        'description':exc,
                        'module_name':'DMS API SALE ORDER',
                        'status':0,
                        'model_name':model,
                        'transaction_id':sale_order.id,
                        'origin':sale_order.name,    
                    })
                    query = """
                        UPDATE dealer_sale_order 
                        SET status_api='error' 
                        WHERE id = %d
                    """ % (sale_order.id)
                    self._cr.execute(query)  
        else:
            _logger.warning('Data Update Error to Draft Sale Order')
            update_error = """
                UPDATE dealer_sale_order 
                SET status_api = 'draft' 
                WHERE status_api = 'error'
            """
            self._cr.execute(update_error)