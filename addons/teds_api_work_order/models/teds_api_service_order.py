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

class ServiceOrder(models.Model):
    _name = "dms.api.service.order"

    @api.multi
    def create_work_order(self,vals):
        cek_group = self.env['res.users'].has_group('teds_api_work_order.group_dms_api_service_order_read')
        if not cek_group:
            return {
                'status':0,
                'error':'not_authorized',
                'remark':'User tidak memiliki hak akses.',
            }

        MANDATORY_FIELDS = [
            'branch_code',
            'type',
            'engine_code',
            'chassis_no',
            'no_pol',
            'km',
            'prod_code',
            'prod_warna',
            'alasan_ke_ahass',
            'bensin',
            'nomor_sa',
            'line_ids',
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
        type = vals.get('type')
        engine_code = vals.get('engine_code')
        chassis_no = vals.get('chassis_no')
        no_pol = vals.get('no_pol')
        km = vals.get('km')
        alasan_ke_ahass = vals.get('alasan_ke_ahass')
        keluhan_konsumen = vals.get('keluhan_konsumen', False)
        bensin = vals.get('bensin')
        nomor_sa = vals.get('nomor_sa')
        prod_code = vals.get('prod_code')
        prod_warna = vals.get('prod_warna')
        is_event_kpb = vals.get('is_event_kpb')
        line_ids = vals.get('line_ids')

        branch = self.env['wtc.branch'].sudo().search([('code','=',branch_code)],limit=1)
        if not branch:
            return {
                'status':0,
                'error':'data_not_found',
                'remark':'dealer_code: %s' %(branch_code)
            }

        lot = self.env['stock.production.lot'].sudo().search([
            ('name','=',engine_code)],limit=1)
        if not lot:
            query = """
                    SELECT pp.id as prod_id
                    FROM product_product pp
                    INNER JOIN product_template pt ON pt.id = pp.product_tmpl_id 
                    LEFT JOIN product_attribute_value_product_product_rel rel ON rel.prod_id = pp.id
                    LEFT JOIN product_attribute_value pav ON pav.id = rel.att_id 
                    WHERE name_template = '%s' AND pav.code='%s'
                """ %(prod_code,prod_warna)
            self._cr.execute(query)
            ress = self._cr.dictfetchall()
            if ress == []:
                return {
                    'status':0,
                    'error':'data_not_found',
                    'remark':'Product code %s type warna %s' %(prod_code,prod_warna)
                }
            product = ress[0].get('prod_id')
            product_id = self.env['product.product'].browse(product)
            create_lot = self.env['stock.production.lot'].sudo().create({
                'branch_id':branch.id,
                'name':engine_code,
                'chassis_no':chassis_no,
                'no_polisi':no_pol,
                'state':'workshop', 
                'product_id':product_id.id,
            })          
            if create_lot:
                lot = create_lot

        # if alasan_ke_ahass == 'Regular Visit Ahass':
        #     alasan_ke_ahass = 'regular visit ahass'
        # elif alasan_ke_ahass in ('Booking Service','Inisiatif Sendiri'):
        #     alasan_ke_ahass = False
        # elif alasan_ke_ahass in ('SMS Reminder','Telp Reminder'):
        #     alasan_ke_ahass = 'sms call remainder'
        # elif alasan_ke_ahass == 'Service Visit':
        #     alasan_ke_ahass = 'service visit'   
        # elif alasan_ke_ahass == 'Ahass Event':
        #     alasan_ke_ahass = 'ahass event'
        # elif alasan_ke_ahass == 'Pit Express':
        #     alasan_ke_ahass = 'pit express'

        if bensin == '25%':
            bensin = '25'
        elif bensin == '50%':
            bensin = '50'
        elif bensin == '75%':
            bensin = '75'
        elif bensin == '100%':
            bensin = '100'

        product_unit_id = lot.product_id

        tanggal_pembelian = vals.get('tanggal_pembelian',False)
        kpb_ke = vals.get('kpb_ke',False)
        payment_term = branch.default_supplier_id.property_payment_term.id

        MANDATORY_FIELDS_LINE = [
            'categ_id',
            'product_code',
            'product_qty',
        ]
        line = []
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

            product_code = x.get('product_code')
            categ_id = x.get('categ_id')
            product_qty = x.get('product_qty')
            diskon = x.get('diskon')

            product = self.env['product.product'].sudo().search([('name','=',product_code)],limit=1)
            if not product:
                return {
                    'status':0,
                    'error':'data_not_found',
                    'remark':'product_code: %s' %(product_code)
                }
            if categ_id == 'Service':
                price = self.env['wtc.work.order.line']._get_harga_jasa(product.id,branch.id,product_unit_id.id)
            else:
                pricelist = branch.pricelist_part_sales_id
                if type == 'KPB' and kpb_ke == '1' :
                    price=0
                    obj_categ_service1 = self.env['wtc.category.product.service'].sudo().search([
                        ('category_product_id','=',product_unit_id.category_product_id.id),
                        ('product_id','=',product.id)])
                    if obj_categ_service1:
                        price = obj_categ_service1.price
                else :
                    price_get = pricelist.sudo().price_get(product.id, 1)
                    price = price_get[pricelist.id]
            line.append([0,False,{
                'categ_id':categ_id,
                'product_id':product.id,
                'name' :product.description,
                'product_qty':product_qty, 
                'discount':diskon,
                'price_unit':price,
                'product_uom':1,
                'warranty': 0.0,
                'tax_id': [(6,0,[product.taxes_id.id])],
                'tax_id_show': [(6,0,[product.taxes_id.id])],
            }])
        
        vals = {
            'branch_id': branch.id,
            'type':type,
            'kpb_ke':kpb_ke,
            'is_event_kpb':is_event_kpb,
            'lot_id':lot.id,
            'chassis_no':lot.chassis_no,
            'no_pol':lot.no_polisi,
            'km':km,
            'alasan_ke_ahass':alasan_ke_ahass,
            'note': keluhan_konsumen,
            'nomor_sa':nomor_sa,
            'division':'Sparepart',
            'bensin':bensin,
            'payment_term':payment_term,
            'tanggal_pembelian':tanggal_pembelian,
            'product_id':lot.product_id.id,
            'driver_id':lot.driver_id.id,
            'mobile':lot.driver_id.mobile,
            'work_lines':line,
        }
        create = self.env['wtc.work.order'].sudo().create(vals)
