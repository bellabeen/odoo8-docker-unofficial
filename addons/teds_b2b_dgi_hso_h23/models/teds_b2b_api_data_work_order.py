from openerp import models, fields, api
from openerp.exceptions import Warning
from datetime import timedelta,datetime
import time
from dateutil.relativedelta import relativedelta
import json
import requests
import hashlib

import logging
_logger = logging.getLogger(__name__)

class B2bApiConfig(models.Model):
    _inherit = "teds.b2b.api.config"

    code = fields.Selection(selection_add=[('HSO','HSO')])

    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()

    @api.multi
    def _get_api_pkb_hso(self, branch, query_date, log=True, noWorkOrder=False):
        api_url = "%s/pkb/read" % self.base_url
        date_format = '%Y-%m-%d %H:%M:%S'

        from_time = datetime.combine(query_date, datetime.min.time())
        to_time = datetime.combine(query_date, datetime.max.time())

        # epoch = int(time.mktime(time.strptime(datetime.now().strftime(date_format), '%Y-%m-%d %H:%M:%S')))
        epoch = int(time.mktime(time.localtime())) # verify pakai time.localtime() or time.gmtime()

        # TOKEN DGI #
        if not self.api_key and not self.api_secret:
            error = "API Key dan API Secret Required !"
            if log:
                self.create_log_error_dgi('DGI H23 PKB HSO',api_url,'post',error,'PKB')
            return {'status':0,'error':error}

        token_raw = "%s%s%s"%(self.api_key, self.api_secret, epoch)
        token = hashlib.sha256(token_raw).hexdigest()

        headers = {
            "DGI-API-Key":self.api_key,
            "Content-Type":"application/json",
            "X-Request-Time":str(epoch),
            "DGI-API-Token":token
        }
        body = {
            "fromTime": from_time.strftime(date_format),
            "toTime": to_time.strftime(date_format),
        }
        if branch.md_reference:
            body['dealerId'] = branch.md_reference

        if noWorkOrder:
            body['noWorkOrder'] = noWorkOrder
  
        response = self.post(name="DGI H23 PKB HSO", url=api_url, body=body, headers=headers, type='incoming', verify=self.verify)
        if response.status_code == 200:
            content = json.loads(response.content)
            # Get Data Response
            data = content.get('data')
            if not data:
                error = "Data PKB tidak ditemukan !"
                if noWorkOrder:
                    error = 'Data PKB %s tidak ditemukan !' % noWorkOrder
                if not log:
                    raise Warning(error)
                return {'status':1,'data':data}
            if noWorkOrder:
                data = [d for d in data if d.get('noWorkOrder')==noWorkOrder]
                if not data:
                    error = 'Data Work Order %s tidak ditemukan !' % noWorkOrder
                    if not log:
                        raise Warning(error)
                    return {'status':1,'data':data}
            
            query = """
                SELECT md_reference_pkb
                FROM wtc_work_order
                WHERE branch_id = %(branch_id)d
            """ % {'branch_id': branch.id}
            if noWorkOrder:
                query += " AND md_reference_pkb = '%(noWorkOrder)s' " %{'noWorkOrder':noWorkOrder}
            else:
                query += " AND md_reference_pkb IS NOT NULL "
            self._cr.execute(query)
            ress = self._cr.fetchall()
            registered_wo = [res[0] for res in ress]
            data = [d for d in data if d.get('statusWorkOrder') in ('Closed') and d.get('noWorkOrder') not in registered_wo]

            if not data:
                error = "Data PKB tidak ditemukan !"
                if noWorkOrder:
                    error = 'Data PKB %s tidak ditemukan !' % noWorkOrder
                if not log:
                    raise Warning(error)
            return {'status':1, 'data':data}
        else:
            error = "Gagal Get PKB.\nStatus Code: %s\nContent: %s" % (response.status_code, response.content)
            if log:
                self.create_log_error_dgi('DGI H23 wo HSO',api_url,'post',error,'PKB')
            return {'status':0,'error':error}

    @api.multi
    def _get_data_wo_hso_h23(self, branch, query_date=False, log=True, noWorkOrder=False):
        try:
            #default date is today (for scheduler)
            if not query_date:
                query_date = datetime.now()
            #get wo yang status completed/Approved dan belum di proses sebelumnya
            wos = self._get_api_pkb_hso(branch, query_date, log, noWorkOrder)
            if wos.get('status', 0) == 1:
                wos = wos.get('data')
                #daftar id wo yg di proses saat ini, mencegah proses data dua kali
                daftar_wo = []

                #data wo yg siap di proses saat ini
                data_orders = {}

                for wo in wos:
                    statusWorkOrder = wo.get('statusWorkOrder')
                    noWorkOrder = wo.get('noWorkOrder')            

                    #jika belum di proses, lanjut
                    if noWorkOrder not in daftar_wo:
                        data_orders[noWorkOrder] = {'wo': wo}

                        #PROCESS BLOCKING: jika detail parts dan service tidak ada                    
                        services = wo.get('services')
                        parts = wo.get('parts')
                        if len(services) == 0 and len(parts) == 0:
                            error = 'ID PKB %s Data parts dan services kosong !' %noWorkOrder
                            if not log:
                                raise Warning(error)
                            self.create_log_error_dgi('DGI Data Work Order HSO',self.base_url,'post',error,'PKB')
                            continue

                    daftar_wo.append(noWorkOrder)

                result = {
                    'status':1,
                    'data':data_orders.values()
                }
                return result
            else:
                error = wos.get('error')
                if not log:
                    raise Warning(error)
                result = {
                    'status':0,
                    'error':error
                }
                return result
        except Exception as err:
            result = {
                'status':0,
                'error':err
            }
            _logger.warning("Exception DGI Data Work Orderr HSO >>>>>>>>> %s"%(err))
            if not log:
                raise Warning(err)
            self.create_log_error_dgi('Exception DGI Data Work Order HSO',self.base_url,'post',err,'wo')

    @api.multi
    def _process_data_wo_hso_h23(self, branch, datas, log=True):
        data_emp = self.env['hr.employee']
        data_provinsi = self.env['res.country.state']
        data_city = self.env['wtc.city']
        data_kelurahan = self.env['wtc.kelurahan']
        data_kecamatan = self.env['wtc.kecamatan']
        data_lot = self.env['stock.production.lot']
        data_work_order = self.env['wtc.work.order']
        data_product = self.env['product.product']
        data_categ_prod_service = self.env['wtc.category.product.service']
        data_master_jasa =  self.env['teds.b2b.dgi.mapping.master.jasa']
        
        md_id = branch.default_supplier_id.id
        pricelist = branch.pricelist_part_sales_id
        branch_id = branch.id

        for data in datas:                
            if not data.get('wo'):
                error = "Data Work Order tidak ditemukan !"
                if not log:
                    raise Warning(error)
                continue

            # Definision Variabel       
            noWorkOrder = data['wo'].get('noWorkOrder')
            noSAForm = data['wo'].get('noSAForm')
            tanggalServis = data['wo'].get('tanggalServis')
            waktuPKB = data['wo'].get('waktuPKB')
            noPolisi = data['wo'].get('noPolisi')
            noRangka = data['wo'].get('noRangka')
            noMesin = data['wo'].get('noMesin')
            kodeTipeUnit = data['wo'].get('kodeTipeUnit')
            tahunMotor = data['wo'].get('tahunMotor')
            informasiBensin = data['wo'].get('informasiBensin')
            kmTerakhir = data['wo'].get('kmTerakhir')
            tipeComingCustomer = data['wo'].get('tipeComingCustomer')
            namaPemilik = data['wo'].get('namaPemilik')
            alamatPemilik = data['wo'].get('alamatPemilik')
            kodePropinsiPemilik = data['wo'].get('kodePropinsiPemilik')
            kodeKotaPemilik = data['wo'].get('kodeKotaPemilik')
            kodeKecamatanPemilik = data['wo'].get('kodeKecamatanPemilik')
            kodeKelurahanPemilik = data['wo'].get('kodeKelurahanPemilik')
            kodePosPemilik = data['wo'].get('kodePosPemilik')
            alamatPembawa = data['wo'].get('alamatPembawa')
            kodePropinsiPembawa = data['wo'].get('kodePropinsiPembawa')
            kodeKotaPembawa = data['wo'].get('kodeKotaPembawa')
            kodeKecamatanPembawa = data['wo'].get('kodeKecamatanPembawa')
            kodeKelurahanPembawa = data['wo'].get('kodeKelurahanPembawa')
            kodePosPembawa = data['wo'].get('kodePosPembawa')
            namaPembawa = data['wo'].get('namaPembawa')
            noTelpPembawa = data['wo'].get('noTelpPembawa')
            hubunganDenganPemilik = data['wo'].get('hubunganDenganPemilik')
            keluhanKonsumen = data['wo'].get('keluhanKonsumen')
            rekomendasiSA = data['wo'].get('rekomendasiSA')
            hondaIdSA = data['wo'].get('hondaIdSA')
            hondaIdMekanik = data['wo'].get('hondaIdMekanik')
            saranMekanik = data['wo'].get('saranMekanik')
            asalUnitEntry = data['wo'].get('asalUnitEntry')
            idPIT = data['wo'].get('idPIT')
            jenisPIT = data['wo'].get('jenisPIT')
            waktuPendaftaran = data['wo'].get('waktuPendaftaran')
            waktuSelesai = data['wo'].get('waktuSelesai')
            totalFRT = data['wo'].get('totalFRT')
            setUpPembayaran = data['wo'].get('setUpPembayaran')
            catatanTambahan = data['wo'].get('catatanTambahan')
            konfirmasiPekerjaanTambahan = data['wo'].get('konfirmasiPekerjaanTambahan')
            noBukuClaimC2 = data['wo'].get('noBukuClaimC2')
            noWorkOrderJobReturn = data['wo'].get('noWorkOrderJobReturn')
            totalBiayaService = data['wo'].get('totalBiayaService')
            waktuPekerjaan = data['wo'].get('waktuPekerjaan')
            statusWorkOrder = data['wo'].get('statusWorkOrder')
            createdTime = data['wo'].get('createdTime')
            services = data['wo'].get('services')
            parts = data['wo'].get('parts')

            dealer_sendiri = 'ya'
            if noPolisi:
                noPolisi = noPolisi.replace(' ','').upper()
            pembawa_id = False
            # Cek NoMesin
            lot_obj = data_lot.suspend_security().search([('name','=',noMesin)],limit=1)
            if not lot_obj:
                if not kodeTipeUnit:
                    error = 'ID PKB %s Product Kode Tipe Unit %s tidak terisi !' %(noWorkOrder,kodeTipeUnit)   
                    if not log:
                        raise Warning(error)
                    self.create_log_error_dgi('DGI Data Order PKB',self.base_url,'post',error,'PKB')
                    continue

                product_unit_id = self._get_product_unit_h23(kodeTipeUnit)
                if not product_unit_id:
                    error = 'ID PKB %s Product Kode Tipe Unit %s not found !' %(noWorkOrder,kodeTipeUnit)
                    if not log:
                        raise Warning(error)
                    self.create_log_error_dgi('DGI Data Order HSO',self.base_url,'post',error,'PKB')
                    continue
                
                # Data Customer STNK
                provinsi_pemilik_id = False
                city_pemilik_id = False
                kecamatan_pemilik_id = False
                kecamatan_pemilik = False
                kelurahan_pemilik_id = False
                kelurahan_pemilik = False
                kode_pos = kodePosPemilik
                if kodeKelurahanPemilik:
                    obj_kel_pemilik = data_kelurahan.suspend_security().search([('code','=',kodeKelurahanPemilik)],limit=1)
                    if obj_kel_pemilik:
                        kelurahan_pemilik_id = obj_kel_pemilik.id
                        kelurahan_pemilik = obj_kel_pemilik.name
                        kecamatan_pemilik_id = obj_kel_pemilik.kecamatan_id.id
                        kecamatan_pemilik = obj_kel_pemilik.kecamatan_id.name
                        city_pemilik_id = obj_kel_pemilik.kecamatan_id.city_id.id
                        provinsi_pemilik_id = obj_kel_pemilik.kecamatan_id.city_id.state_id.id
                
                if not kecamatan_pemilik_id and kodeKecamatanPemilik:
                    obj_kec_pemilik = data_kecamatan.suspend_security().search([('code','=',kodeKecamatanPemilik)],limit=1)
                    if obj_kec_pemilik:
                        kecamatan_pemilik_id = obj_kec_pemilik.id
                        kecamatan_pemilik = obj_kec_pemilik.name
                        city_pemilik_id = obj_kec_pemilik.city_id.id
                        provinsi_pemilik_id = obj_kec_pemilik.city_id.state_id.id

                if not city_pemilik_id and kodeKotaPemilik:
                    obj_city_pemilik = data_city.suspend_security().search([('code','=',kodeKotaPemilik)],limit=1)
                    if obj_city_pemilik:
                        city_pemilik_id = obj_city_pemilik.id
                        provinsi_pemilik_id = obj_city_pemilik.state_id.id    
                
                if not provinsi_pemilik_id and kodePropinsiPemilik:
                    provinsi_pemilik_id = data_provinsi.suspend_security().search([('code','=',kodePropinsiPemilik)],limit=1).id

                pemilik_stnk_id = self.env['res.partner'].suspend_security().create({
                    'branch_id':branch_id,
                    'name':namaPemilik,
                    'street':alamatPemilik,
                    'state_id':provinsi_pemilik_id,
                    'city_id':city_pemilik_id,
                    'kecamatan_id':kecamatan_pemilik_id,
                    'kecamatan':kecamatan_pemilik,
                    'zip_id':kelurahan_pemilik_id,
                    'kelurahan':kelurahan_pemilik,
                    'customer':True,
                    'direct_customer':True,
                    'street_tab':alamatPemilik,
                    'state_tab_id':provinsi_pemilik_id,
                    'city_tab_id':city_pemilik_id,
                    'kecamatan_tab_id':kecamatan_pemilik_id,
                    'kecamatan_tab':kecamatan_pemilik,
                    'zip_tab_id':kelurahan_pemilik_id,
                    'kelurahan_tab':kelurahan_pemilik,
                }).id
               
                # Data Pembawa Service
                provinsi_pembawa_id = False
                city_pembawa_id = False
                kecamatan_pembawa_id = False
                kecamatan_pembawa = False
                kelurahan_pembawa_id = False
                kelurahan_pembawa = False
                if kodeKelurahanPembawa:
                    obj_kel_pembawa = data_kelurahan.suspend_security().search([('code','=',kodeKelurahanPembawa)],limit=1)
                    if obj_kel_pembawa:
                        kelurahan_pembawa_id = obj_kel_pembawa.id
                        kelurahan_pembawa = obj_kel_pembawa.name
                        kecamatan_pembawa_id = obj_kel_pembawa.kecamatan_id.id
                        kecamatan_pembawa = obj_kel_pembawa.kecamatan_id.name
                        city_pembawa_id = obj_kel_pembawa.kecamatan_id.city_id.id
                        provinsi_pembawa_id = obj_kel_pembawa.kecamatan_id.city_id.state_id.id
                
                if not kecamatan_pembawa_id and kodeKecamatanPembawa:
                    obj_kec_pembawa = data_kecamatan.suspend_security().search([('code','=',kodeKecamatanPembawa)],limit=1)
                    if obj_kec_pembawa:
                        kecamatan_pembawa_id = obj_kec_pembawa.id
                        kecamatan_pembawa = obj_kec_pembawa.name
                        city_pembawa_id = obj_kec_pembawa.city_id.id
                        provinsi_pembawa_id = obj_kec_pembawa.city_id.state_id.id

                if not city_pembawa_id and kodeKotaPembawa:
                    obj_city_pembawa = data_city.suspend_security().search([('code','=',kodeKotaPembawa)],limit=1)
                    if obj_city_pembawa:
                        city_pembawa_id = obj_city_pembawa.id
                        provinsi_pembawa_id = obj_city_pembawa.state_id.id    
                
                if not provinsi_pembawa_id and kodePropinsiPembawa:
                    provinsi_pembawa_id = data_provinsi.suspend_security().search([('code','=',kodePropinsiPembawa)],limit=1).id
                                                                        
                pembawa_id = self.env['res.partner'].suspend_security().create({
                    'branch_id':branch_id,
                    'name':namaPembawa,
                    'street':alamatPembawa,
                    'state_id':provinsi_pembawa_id,
                    'city_id':city_pembawa_id,
                    'kecamatan_id':kecamatan_pembawa_id,
                    'kecamatan':kecamatan_pembawa,
                    'zip_id':kelurahan_pembawa_id,
                    'kelurahan':kelurahan_pembawa,
                    'customer':True,
                    'direct_customer':True,
                    'street_tab':alamatPembawa,
                    'state_tab_id':provinsi_pembawa_id,
                    'city_tab_id':city_pembawa_id,
                    'kecamatan_tab_id':kecamatan_pembawa_id,
                    'kecamatan_tab':kecamatan_pembawa,
                    'zip_tab_id':kelurahan_pembawa_id,
                    'kelurahan_tab':kelurahan_pembawa,
                }).id
                
                noRangka = noRangka[3:]
                lot_obj = self.env['stock.production.lot'].suspend_security().create({
                    'branch_id':branch_id,
                    'name':noMesin,
                    'chassis_no':noRangka,
                    'no_polisi':noPolisi,
                    'state':'workshop', 
                    'product_id':product_unit_id,
                    'customer_id':pemilik_stnk_id,
                    'customer_stnk':pemilik_stnk_id,
                    'driver_id':pembawa_id,
                    'tahun':tahunMotor,
                })
                dealer_sendiri = 'tidak'       

            kpb_ke = False
            prev_work_order_id = False
            type = 'REG'
            part_line = []
            jasa_line = []
            jasa_line_kpb = []

            # Jika Data Work Order Job Return (WAR)
            if noWorkOrderJobReturn:
                type = 'WAR'
                prev_work_order_id = data_work_order.suspend_security().search([
                    ('branch_id','=',branch_id),
                    ('md_reference_pkb','=',noWorkOrderJobReturn)],limit=1).id

            # Mapping Data Job Sparepart
            data_job_part = {}
            for part in parts:
                idJobPart = part.get('idJob')
                partsNumber = part.get('partsNumber')
                kuantitas = part.get('kuantitas')
                hargaParts = part.get('hargaParts')
                createdTime = part.get('createdTime')
                if not partsNumber:
                    error = 'ID PKB %s Part Number %s tidak terisi !' %(noWorkOrder,partsNumber)   
                    if not log:
                        raise Warning(error)
                    self.create_log_error_dgi('DGI Data Order PKB',self.base_url,'post',error,'PKB')
                    continue

                product_part_obj = data_product.search([('name','=',partsNumber)],limit=1)
                if not product_part_obj:
                    error = 'ID PKB %s Part Number %s not found !' %(noWorkOrder,partsNumber)   
                    if not log:
                        raise Warning(error)
                    self.create_log_error_dgi('DGI Data Order PKB',self.base_url,'post',error,'PKB')
                    continue

                price_get_part = pricelist.sudo().price_get(product_part_obj.id, 1)
                price_part = price_get_part[pricelist.id] 

                jenis_pekerjaan_value = idJobPart[-3:-1]

                if jenis_pekerjaan_value == '01':
                    type = 'KPB'
                    kpb_ke = '1'

                    obj_categ_service1 = data_categ_prod_service.suspend_security().search([
                        ('category_product_id','=',lot_obj.product_id.category_product_id.id),
                        ('product_id','=',product_part_obj.id)],limit=1)
                    if obj_categ_service1:
                        price_part = obj_categ_service1.price

                elif jenis_pekerjaan_value == '02':
                    type = 'KPB'
                    kpb_ke = '2'
                elif jenis_pekerjaan_value == '03':
                    type = 'KPB'
                    kpb_ke = '3'
                elif jenis_pekerjaan_value == '04':
                    type = 'KPB'
                    kpb_ke = '4'
                
                if price_part <= 0:
                    error = 'ID PKB %s Harga Part %s tidak boleh 0 !' %(noWorkOrder,product_part_obj.name_get().pop()[1])   
                    if not log:
                        raise Warning(error)
                    self.create_log_error_dgi('DGI Data Order PKB',self.base_url,'post',error,'PKB')
                    continue

                part_line.append([0,False,{
                    'categ_id':'Sparepart',
                    'product_id':product_part_obj.id,
                    'name' :product_part_obj.description,
                    'product_qty':kuantitas, 
                    'price_unit':price_part,
                    'product_uom':1,
                    'warranty': product_part_obj.warranty,
                    'tax_id': [(6,0,[product_part_obj.taxes_id.id])],
                    'tax_id_show': [(6,0,[product_part_obj.taxes_id.id])],
                }])

                if not data_job_part.get(idJobPart) and jenis_pekerjaan_value not in ('02','03','04'):
                    part_number_mapping = partsNumber[0:5]
                    data_job_part[idJobPart] = part_number_mapping

            for service in services:
                idJobService  = service.get('idJob')
                namaPekerjaan = service.get('namaPekerjaan')
                jenisPekerjaan = service.get('jenisPekerjaan')
                biayaService = service.get('biayaService')
                createdTime = service.get('createdTime')
                
                part_job = data_job_part.get(idJobService,'00000')
                jenis_pekerjaan_value = idJobService[-3:-1]
                kategori_pekerjaan_value = idJobService[-1]
                if kategori_pekerjaan_value == '3':
                    kategori_pekerjaan_value = '2'

                jasa_job = "%s%s" %(jenis_pekerjaan_value,kategori_pekerjaan_value)
                value_jasa = "%s%s" %(part_job,jasa_job)
                master_jasa_mapping = data_master_jasa.suspend_security().search([
                    ('md_id','=',md_id),
                    ('value','=',value_jasa)],order="sequence ASC",limit=1)
                if not master_jasa_mapping:
                    error = 'ID PKB %s namaPekerjaan %s idJob %s not found mapping master jasa %s !' %(noWorkOrder,namaPekerjaan,idJobService,value_jasa)   
                    if not log:
                        raise Warning(error)
                    self.create_log_error_dgi('DGI Data Order PKB',self.base_url,'post',error,'PKB')
                    continue

                product_jasa_obj = master_jasa_mapping.product_id
                price_jasa = self.env['wtc.work.order.line']._get_harga_jasa(product_jasa_obj.id,branch_id,lot_obj.product_id.id)
                if price_jasa <= 0:
                    error = 'ID PKB %s Harga jasa %s tidak boleh 0 ! Value MD %s' %(noWorkOrder,product_jasa_obj.name_get().pop()[1],value_jasa)   
                    if not log:
                        raise Warning(error)
                    self.create_log_error_dgi('DGI Data Order PKB',self.base_url,'post',error,'PKB')
                    continue

                if jenis_pekerjaan_value == '01':
                    type = 'KPB'
                    kpb_ke = '1'
                    jasa_line_kpb.append([0,False,{
                        'categ_id':'Service',
                        'product_id':product_jasa_obj.id,
                        'name' :product_jasa_obj.description,
                        'product_qty':1, 
                        'price_unit':price_jasa,
                        'product_uom':1,
                        'warranty': product_jasa_obj.warranty,
                        'tax_id': [(6,0,[product_jasa_obj.taxes_id.id])],
                        'tax_id_show': [(6,0,[product_jasa_obj.taxes_id.id])],    
                    }])
                elif jenis_pekerjaan_value == '02':
                    type = 'KPB'
                    kpb_ke = '2'
                    jasa_line_kpb.append([0,False,{
                        'categ_id':'Service',
                        'product_id':product_jasa_obj.id,
                        'name' :product_jasa_obj.description,
                        'product_qty':1, 
                        'price_unit':price_jasa,
                        'product_uom':1,
                        'warranty': product_jasa_obj.warranty,
                        'tax_id': [(6,0,[product_jasa_obj.taxes_id.id])],
                        'tax_id_show': [(6,0,[product_jasa_obj.taxes_id.id])],    
                    }])
                elif jenis_pekerjaan_value == '03':
                    type = 'KPB'
                    kpb_ke = '3'
                    jasa_line_kpb.append([0,False,{
                        'categ_id':'Service',
                        'product_id':product_jasa_obj.id,
                        'name' :product_jasa_obj.description,
                        'product_qty':1, 
                        'price_unit':price_jasa,
                        'product_uom':1,
                        'warranty': product_jasa_obj.warranty,
                        'tax_id': [(6,0,[product_jasa_obj.taxes_id.id])],
                        'tax_id_show': [(6,0,[product_jasa_obj.taxes_id.id])],    
                    }])
                elif jenis_pekerjaan_value == '04':
                    type = 'KPB'
                    kpb_ke = '4'
                    jasa_line_kpb.append([0,False,{
                        'categ_id':'Service',
                        'product_id':product_jasa_obj.id,
                        'name' :product_jasa_obj.description,
                        'product_qty':1, 
                        'price_unit':price_jasa,
                        'product_uom':1,
                        'warranty': product_jasa_obj.warranty,
                        'tax_id': [(6,0,[product_jasa_obj.taxes_id.id])],
                        'tax_id_show': [(6,0,[product_jasa_obj.taxes_id.id])],    
                    }])
                else:
                    jasa_line.append([0,False,{
                        'categ_id':'Service',
                        'product_id':product_jasa_obj.id,
                        'name' :product_jasa_obj.description,
                        'product_qty':1, 
                        'price_unit':price_jasa,
                        'product_uom':1,
                        'warranty': product_jasa_obj.warranty,
                        'tax_id': [(6,0,[product_jasa_obj.taxes_id.id])],
                        'tax_id_show': [(6,0,[product_jasa_obj.taxes_id.id])],
                    }])

            bensin = False
            if informasiBensin == '1':
                bensin = '25'
            elif informasiBensin == '2':
                bensin = '50'
            elif informasiBensin == '3':
                bensin = '75'
            elif informasiBensin == '4':
                bensin = '100'

            alasan_ke_ahass = 'regular visit ahass'
            if asalUnitEntry:
                if asalUnitEntry == 'Non-Promotion':
                    alasan_ke_ahass = 'regular visit ahass'
                elif asalUnitEntry == 'Reminder':
                    alasan_ke_ahass = 'sms call remainder'
                elif asalUnitEntry in ('Pos Service','Join Dealer Activity','Group Customer','Public Area','Emergency'):
                    alasan_ke_ahass = 'service visit'
                elif asalUnitEntry in ('AHASS Event yang di Develop oleh AHM','AHASS Event yang di Develop oleh MD','AHASS Event yang di Develop oleh AHASS'):
                    alasan_ke_ahass = 'ahass event'
                elif asalUnitEntry == 'Pit Express':
                    alasan_ke_ahass = 'pit express'

            # Data Mekanik
            mekanik_id = False
            if hondaIdMekanik:
                mekanik_id = self._get_employee(branch_id,hondaIdMekanik).user_id.id
            
            work_lines = part_line + jasa_line + jasa_line_kpb
            if not work_lines:
                error = 'ID PKB %s Order Lines kosong !' %(noWorkOrder)   
                if not log:
                    raise Warning(error)
                self.create_log_error_dgi('DGI Data Order PKB',self.base_url,'post',error,'PKB')
                continue

            tanggal_wo = datetime.now().date()
            if tanggalServis:
                tanggal_wo = datetime.strptime(tanggalServis, '%d/%m/%Y').date()

            vals = {
                'branch_id': branch_id,
                'lot_id':lot_obj.id,
                'chassis_no':lot_obj.chassis_no,
                'no_pol':lot_obj.no_polisi,
                'km':kmTerakhir,
                'division':'Sparepart',
                'bensin':bensin,
                'product_id':lot_obj.product_id.id,
                'customer_id':lot_obj.customer_stnk.id,
                'driver_id':lot_obj.driver_id.id if lot_obj.driver_id.id else pembawa_id,
                'mobile':lot_obj.driver_id.mobile if lot_obj.driver_id.mobile else noTelpPembawa,
                'hubungan_pemilik':hubunganDenganPemilik,
                'tahun_perakitan':lot_obj.tahun if lot_obj.tahun else tahunMotor,
                'alasan_ke_ahass':alasan_ke_ahass,
                'dealer_sendiri':dealer_sendiri,
                'type':type,
                'kpb_ke':kpb_ke,
                'prev_work_order_id':prev_work_order_id,
                'work_lines':work_lines,
                'tanggal_pembelian':lot_obj.invoice_date if lot_obj.invoice_date else str(tanggal_wo),
                'mekanik_id':mekanik_id,
                'md_reference_pkb':noWorkOrder,
                'md_reference_sa':noSAForm,
            }
            if type == 'KPB':
                # Proses Blocking Cek KPB Expired
                vit = self.env['wtc.kpb.expired'].suspend_security().search([
                    ("name", "=", lot_obj.name[:4]), 
                    ("service", "=", kpb_ke)],limit=1)
                if not vit:
                    error = 'ID PKB %s No Engine %s Tidak Ada Di Database KPB !' %(noWorkOrder,lot_obj.name[:4])   
                    if not log:
                        raise Warning(error)
                    self.create_log_error_dgi('DGI Data Order PKB',self.base_url,'post',error,'PKB')
                    continue
                if kmTerakhir > vit.km:
                    error = 'ID PKB %s Kilometer telah lewat batas KPB. kmTerakhir %s !' %(noWorkOrder,kmTerakhir)   
                    if not log:
                        raise Warning(error)
                    self.create_log_error_dgi('DGI Data Order PKB',self.base_url,'post',error,'PKB')
                    continue

                if kpb_ke in ('2','3','4') and part_line:
                    vals_kpb_reg = vals.copy()
                    vals_kpb_reg.update({
                        'type':'REG',
                        'kpb_ke':False,
                        'prev_work_order_id':False,
                        'work_lines':jasa_line + part_line,
                    })
                    warranty_list_kpb = [x[2].get('warranty') for x in vals_kpb_reg.get('work_lines')]
                    vals_kpb_reg['warranty'] = max(warranty_list_kpb)

                    vals['work_lines'] = jasa_line_kpb
                    create_kpb_reg = self.env['wtc.work.order'].suspend_security().create(vals_kpb_reg)
                    if create_kpb_reg.tanggal_pembelian == tanggal_wo:
                        create_kpb_reg.tanggal_pembelian = False

            warranty_list = [x[2].get('warranty') for x in vals.get('work_lines')]
            vals['warranty'] = max(warranty_list)
            create_pkb = self.env['wtc.work.order'].suspend_security().create(vals)
            if create_pkb.tanggal_pembelian == tanggal_wo:
                create_pkb.tanggal_pembelian == False
        return True

    @api.multi
    def dgi_hso_order_wo(self,branch):
        try:
            get_response = self._get_data_wo_hso_h23(branch)
            if get_response.get('status') == 1:
                datas = get_response.get('data')
                if datas:
                    md_id = branch.default_supplier_id.id
                    pricelist = branch.pricelist_part_sales_id
                    if not pricelist:
                        error = "Data Pricelist Part Sales belum disetting di master branch !"
                        if not log:
                            raise Warning(error)
                        self.create_log_error_dgi('DGI Data Order PKB',self.base_url,'post',error,'PKB')
                        
                    if not md_id:
                        error = "Data Main Dealer belum disetting di master branch !"
                        if not log:
                            raise Warning(error)
                        self.create_log_error_dgi('DGI Data Order PKB',self.base_url,'post',error,'PKB')

                            
                    # proses data create sale order draft
                    self._process_data_wo_hso_h23(branch,datas)
            else:
                error = get_response.get('error')
                self.create_log_error_dgi('DGI Data Work Order HSO',self.base_url,'post',error,'PKB')
                
                
        except Exception as err:
            _logger.warning("Exception DGI Data Work Order HSO >>>>>>>>> %s"%(err))
            self.create_log_error_dgi('Exception Schedule DGI Data Work Order HSO',self.base_url,'post',err,'PKB')
     

    @api.multi
    def schedule_data_work_order_hso_h23(self,code):
        branch_config_id = self.env['wtc.branch.config'].suspend_security().search([('name','=',code)],limit=1)
        config_id = branch_config_id.config_dgi_h23_id
        branch = branch_config_id.branch_id
        if config_id and branch:
            return config_id.suspend_security().dgi_hso_order_wo(branch)
        else:
            error = 'Branch Config DGI belum di setting !'
            _logger.warning(error)
            self.create_log_error_dgi('DGI Data Work Order HSO',False,'post',error,'Schedule')            
    