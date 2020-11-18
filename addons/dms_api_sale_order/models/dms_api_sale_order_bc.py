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
        # area = self.env['wtc.area'].search([('code','=','AREA_LAMPUNG')],limit=1)
        # list_branch = [b.id in b for area.branch_ids]            
        # sale_order = self.search([
        #     ('state','=','done'),
        #     ('status_api','=','draft'),
        #     ('branch_id','in',list_branch)
        #     ('no_buku_tamu','!=',False)
        # ],limit=1)
        
        sale_order = self.search([
            ('id','=',101543),
        ])
        if sale_order:
            model = 'dealer.sale.order'
            message = False
            config_user = self.env['teds.api.configuration'].search([('branch_id','=',sale_order.branch_id.id)])
            if not config_user:
                message = 'Silahkan buat configuration terlebih dahulu untuk bisa mengakses ke DMS.'
                _logger.warning('%s' %message) 
                self.env['teds.api.log'].sudo().create({
                    'name':message,
                    'status':1,
                    'model_name':model,
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
                            'no_chassis':x.chassis_no,
                            'customer_stnk_ktp':x.partner_stnk_id.no_ktp,
                            'customer_stnk_name':x.partner_stnk_id.name,
                            'quantity':x.product_qty,
                            'price':x.price_unit,
                            'plat':x.plat,
                            'bbn':x.is_bbn,
                            'price_bbn':x.price_bbn,
                            'uang_muka':x.uang_muka,
                            'disc_po':x.discount_po,
                            'price_bbn':x.price_bbn,
                            'biro_jasa_code':x.biro_jasa_id.rel_code,
                            'angsuran':x.cicilan,
                            'tenor':x.finco_tenor,
                            'tot_disc':x.discount_total,
                            'tax':tax,
                            'sub_total':x.price_subtotal,
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

                    # DATA SALES
                    salesman_hoda_id = self._get_honda_id_sales(sale_order.user_id.id)
                    sales_koordinator_honda_id = self._get_honda_id_sales(sale_order.sales_koordinator_id.id)
                    
                    data = odoo.json(
                        '/web/dataset/call',
                        {'model': 'dms.api','method':'dms_sale_order_create',
                        'args':[[], 
                            {
                                'branch_code': sale_order.branch_id.code,
                                'division':sale_order.division,
                                'customer_name':sale_order.partner_id.name,
                                'customer_ktp':sale_order.partner_id.no_ktp,
                                'date_order':sale_order.date_order,
                                'finco_code':sale_order.finco_id.rel_code,
                                'salesman_hoda_id': salesman_hoda_id,
                                'sales_koordinator_honda_id':sales_koordinator_honda_id,
                                'no_buku_tamu':sale_order.no_buku_tamu,
                                'cddb':cddb,
                                'line_ids': line,
                        }]})
                    
                    # finally
                    result =  data.get('result',False)
                    if result:
                        if result['status'] == 1:
                            _logger.warning('%s' %result.get('message',False)) 
                            self.env['teds.api.log'].sudo().create({
                                'name':result.get('message',False),
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
                        elif result['status'] == 2:
                            _logger.warning('%s' %result.get('message',False))
                            query = """
                                UPDATE dealer_sale_order 
                                SET status_api='done' 
                                WHERE id = %d
                            """ % (sale_order.id)
                            self._cr.execute(query)
                    else:
                        query = """
                            UPDATE dealer_sale_order 
                            SET status_api='done' 
                            WHERE id = %d
                        """ % (sale_order.id)
                        self._cr.execute(query)              

                except odoorpc.error.RPCError as exc:
                    _logger.warning('%s' %(exc))
                    self.env['teds.api.log'].sudo().create({
                        'name':exc,
                        'status':1,
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
            

    def _get_honda_id_sales(self,user_id):
        honda_id = False 
        emp = self.env['hr.employee'].sudo().search([('user_id','=',user_id)],limit=1)
        if emp:
            honda_id = emp.code_honda
        return honda_id

