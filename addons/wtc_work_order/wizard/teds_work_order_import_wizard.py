from openerp import models, fields, api
from openerp.exceptions import Warning
from datetime import date, datetime, timedelta
import base64
import xlrd

class WorkOrderImportWizard(models.Model):
    _name = "teds.work.order.import.wizard"

    file = fields.Binary('File')

    @api.multi
    def action_import(self):
        data = base64.decodestring(self.file)
        excel = xlrd.open_workbook(file_contents = data)  
        sh = excel.sheet_by_index(0)

        # Data Search
        data_branch = self.env['wtc.branch']
        data_lot = self.env['stock.production.lot']
        data_partner = self.env['res.partner']
        data_product = self.env['product.product']
        data_categ_prod_service = self.env['wtc.category.product.service']

        # Data Tampungan WO
        result = {}
        no = 0
        for rx in range(1,sh.nrows): 
            branch_code = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [0]
            type_wo = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [1]
            kpb_ke = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [2]
            no_mesin = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [3]
            chassis_no = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [4]
            no_polisi = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [5]
            type_code = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [6]
            type_warna = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [7]
            km = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [8]
            tanggal_pembelian = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [9]
            alasan_ke_ahass = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [10]
            dealer_sendiri = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [11]
            hubungan_pemilik = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [12]
            bensin = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [13]
            tahun_perakitan = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [14]
            stk_pemilik = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [15]
            nama_pemilik = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [16]
            mobile_pemilik = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [17]
            stk_pembawa = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [18]
            nama_pembawa = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [19]
            mobile_pembawa = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [20]
            type_customer = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [21]
            # Data Line Detail WO
            category_line = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [22]
            prod_code_line = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [23]
            qty_line = [sh.cell(rx, ry).value for ry in range(sh.ncols)] [24]

            # Pengolahan pengelompokan wo
            vals = {
                'branch_code':branch_code,
                'type_wo':type_wo,
                'kpb_ke':kpb_ke,
                'no_mesin':no_mesin,
                'chassis_no':chassis_no,
                'no_polisi':no_polisi,
                'type_code':type_code,
                'type_warna':type_warna,
                'km':km,
                'tanggal_pembelian':tanggal_pembelian,
                'alasan_ke_ahass':alasan_ke_ahass,
                'dealer_sendiri':dealer_sendiri,
                'hubungan_pemilik':hubungan_pemilik,
                'bensin':bensin,
                'tahun_perakitan':tahun_perakitan,
                'stk_pemilik':stk_pemilik,
                'nama_pemilik':nama_pemilik,
                'mobile_pemilik':mobile_pemilik,
                'stk_pembawa':stk_pembawa,
                'nama_pembawa':nama_pembawa,
                'mobile_pembawa':mobile_pembawa,
                'type_customer':type_customer,
                'detail':[{
                    'category_line':category_line,
                    'prod_code_line':prod_code_line,
                    'qty_line':qty_line
                }]
            }
            # Jika Kolom A dan B disi diapnggap 1 WO
            if branch_code and type_wo:
                no += 1
                result[no] = vals
            # Mengisi detail WO Diatas
            else:
                result[no]['detail'].append({
                    'category_line':category_line,
                    'prod_code_line':prod_code_line,
                    'qty_line':qty_line,    
                })

        
        for res in result.values():
            branch_code = res.get('branch_code')
            type_wo = res.get('type_wo')
            kpb_ke = res.get('kpb_ke')
            no_mesin = res.get('no_mesin')
            chassis_no = res.get('chassis_no')
            no_polisi = res.get('no_polisi')
            type_code = res.get('type_code')
            type_warna = res.get('type_warna')
            km = res.get('km')
            tanggal_pembelian = res.get('tanggal_pembelian')
            alasan_ke_ahass = res.get('alasan_ke_ahass')
            dealer_sendiri = res.get('dealer_sendiri')
            hubungan_pemilik = res.get('hubungan_pemilik')
            bensin = res.get('bensin')
            tahun_perakitan = res.get('tahun_perakitan')
            stk_pemilik = res.get('stk_pemilik')
            nama_pemilik = res.get('nama_pemilik')
            mobile_pemilik = res.get('mobile_pemilik')
            stk_pembawa = res.get('stk_pembawa')
            nama_pembawa = res.get('nama_pembawa')
            mobile_pembawa = res.get('mobile_pembawa')
            type_customer = res.get('type_customer')
            detail = res.get('detail')

            branch_id = False
            branch_obj = data_branch.search([('code','=',branch_code)],limit=1)
            if not branch_obj:
                raise Warning('Branch Code %s tidak ditemukan !')
            branch_id = branch_obj.id
            pricelist = branch_obj.pricelist_part_sales_id
            if not pricelist:
                raise Warning('Master Pricelist Part belum di setting !')

            # Data Lot
            lot_id = False
            customer_id = False
            driver_id = False
            mobile = False
            product_id = False

            # Cek lot jika data no mesin dan chassis ada
            if no_mesin and chassis_no:
                lot_obj = data_lot.search([('name','=',name),('chassis_no','=',chassis_no)],limit=1)
                if lot_obj:
                    lot_id = lot_obj.id
                    customer_id = lot_obj.customer_id.id
                    driver_id = lot_obj.driver_id.id
                    product_id = lot_obj.product_id.id
                    tahun_perakitan = lot_obj.tahun
                else:
                    # Jika lot tidak ada dan data product customer ada, buat lot
                    if nama_pemilik and type_code and type_warna:
                        query_prod_type = """
                            SELECT pp.id as prod_id
                            FROM product_product pp
                            INNER JOIN product_template pt ON pt.id = pp.product_tmpl_id 
                            LEFT JOIN product_attribute_value_product_product_rel rel ON rel.prod_id = pp.id
                            LEFT JOIN product_attribute_value pav ON pav.id = rel.att_id 
                            WHERE name_template = '%s' AND pav.code='%s'
                            LIMIT 1
                        """ %(type_code,type_warna)
                        self._cr.execute(query_prod_type)
                        res_prod = self._cr.fetchone()
                        if not res_prod:
                            raise Warning('Master Product Type Code %s dan Warna Code %s tidak ditemukan !'%(type_code,type_warna))
                        product_id = res_prod[0]

                        # Customer STNK
                        if stk_pemilik:
                            pemilik_obj = data_partner.search([('default_code','=',stk_pemilik)],limit=1).id
                            if pemilik_obj:
                                customer_id = pemilik_obj.id
                            else:
                                if nama_pemilik:
                                    pemilik_obj = data_partner.create({
                                        'name':nama_pemilik,
                                        'mobile':mobile_pemilik,    
                                    })
                                    customer_id = pemilik_obj.id
                        
                        # Jika customer diatas gagal dan nama pemilik nya ada create customer
                        if not customer_id and nama_pemilik:
                            pemilik_obj = data_partner.create({
                                'name':nama_pemilik,
                                'mobile':mobile_pemilik,    
                            })
                            customer_id = pemilik_obj.id

                        # Data Pemabawa
                        if stk_pemilik and stk_pembawa:
                            if stk_pemilik == stk_pembawa:
                                driver_id = customer_id
                            else:
                                driver_obj = data_partner.search([('default_code','=',stk_pembawa)],limit=1)
                                if driver_obj:
                                    driver_id = driver_obj.id
                                else:
                                    # Create Driver
                                    if nama_pembawa:
                                        pembawa_obj = data_partner.create({
                                            'name':nama_pembawa,
                                            'mobile':mobile_pembawa,    
                                        })
                                        driver_id = pembawa_obj.id

                        # Jika driver diatas gagal dan nama pembawa nya ada create driver
                        if not driver_id and nama_pembawa:
                            # Create Driver
                            pembawa_obj = data_partner.create({
                                'name':nama_pembawa,
                                'mobile':mobile_pembawa,    
                            })
                            driver_id = pembawa_obj.id


                        lot_obj = data_lot.create({
                            'branch_id':branch_id,
                            'name':no_mesin,
                            'chassis_no':chassis_no,
                            'no_polisi':no_polisi,
                            'state':'workshop', 
                            'product_id':product_id,
                            'customer_id':customer_id,
                            'tahun':tahun_perakitan,
                        })
                        lot_id = lot_obj.id

            if not customer_id and nama_pemilik:
                pemilik_obj = data_partner.create({
                    'name':nama_pemilik,
                    'mobile':mobile_pemilik,    
                })
                customer_id = pemilik_obj.id
            if not driver_id and nama_pembawa:
                pembawa_obj = data_partner.create({
                    'name':nama_pembawa,
                    'mobile':mobile_pembawa,    
                })
                driver_id = pembawa_obj.id

            # Looping Detail
            line_ids = []
            for d in detail:
                # Data Line Detail WO
                category_line = d.get('category_line')
                prod_code_line = d.get('prod_code_line')
                qty_line = d.get('qty_line')
                
                # Search Product Detail
                product_detail_obj = data_product.sudo().search([('name','=',prod_code_line)],limit=1)
                if not product_detail_obj:
                    raise Warning('Data Master Order Line Product Code %s tidak ditemukan !' %prod_code_line)
                price = 0
                if category_line == 'Service':
                    price = self.env['wtc.work.order.line']._get_harga_jasa(
                        product_detail_obj.id,
                        branch_id,
                        lot_obj.product_id.id
                    )
                    if price <= 0:
                        error = 'Harga jasa %s tidak boleh 0 !' %(product_detail_obj.name_get().pop()[1])   
                        raise Warning(error)
                elif category_line == 'Sparepart':
                    price_get_part = pricelist.sudo().price_get(product_detail_obj.id, 1)
                    price = price_get_part[pricelist.id]

                    if kpb_ke == '1':
                        obj_categ_service1 = data_categ_prod_service.sudo().search([
                            ('category_product_id','=',lot_obj.product_id.category_product_id.id),
                            ('product_id','=',product_detail_obj.id)],limit=1)
                        if obj_categ_service1:
                            price = obj_categ_service1.price
                    if price <= 0:
                        error = 'Harga jasa %s tidak boleh 0 !' %(product_detail_obj.name_get().pop()[1])   
                        raise Warning(error)

                line_ids.append([0,False,{
                    'categ_id':category_line,
                    'product_id':product_detail_obj.id,
                    'name' :product_detail_obj.description,
                    'product_qty':qty_line, 
                    'price_unit':price,
                    'product_uom':1,
                    'warranty': product_detail_obj.warranty,
                    'tax_id': [(6,0,[product_detail_obj.taxes_id.id])],
                    'tax_id_show': [(6,0,[product_detail_obj.taxes_id.id])],    
                }])

            
            
            vals_wo = {
                'branch_id': branch_id,
                'type':type_wo,
                'kpb_ke':kpb_ke,
                'lot_id':lot_id,
                'chassis_no':chassis_no,
                'no_pol':no_polisi,
                'product_id':product_id,
                'km':km,
                'alasan_ke_ahass':alasan_ke_ahass,
                'division':'Sparepart',
                'bensin':bensin,
                'driver_id':driver_id,
                'customer_id':customer_id,
                'mobile':mobile_pembawa,
                'hubungan_pemilik':hubungan_pemilik,
                'tahun_perakitan':tahun_perakitan,
                'alasan_ke_ahass':alasan_ke_ahass,
                'dealer_sendiri':dealer_sendiri,
                'work_lines':line_ids,
                'tanggal_pembelian':False,
            }
            if tanggal_pembelian:
                vals_wo['tanggal_pembelian'] = tanggal_pembelian

            warranty_list = [x[2].get('warranty') for x in vals_wo.get('work_lines')]
            vals_wo['warranty'] = max(warranty_list)
            create_wo = self.env['wtc.work.order'].create(vals_wo)