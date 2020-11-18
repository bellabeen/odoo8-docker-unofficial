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

    code = fields.Selection(selection_add=[('ASP','ASP')])
    
    @api.multi
    def _get_api_spk_asp(self, branch, query_date, log=True, idProspect=False, idSpk=False):
        api_url = "%s/spk/read" % self.base_url
        date_format = '%Y-%m-%d %H:%M:%S'

        from_time = datetime.combine(query_date, datetime.min.time())
        to_time = datetime.combine(query_date, datetime.max.time())

        # epoch = int(time.mktime(time.strptime(datetime.now().strftime(date_format), '%Y-%m-%d %H:%M:%S')))
        epoch = int(time.mktime(time.localtime())) # verify pakai time.localtime() or time.gmtime()

        # TOKEN DGI #
        if not self.api_key and not self.api_secret:
            error = "API Key dan API Secret Required !"
            if log:
                self.create_log_error_dgi('DGI H1 SPK ASP',api_url,'post',error,'SPK')
            return {'status':0,'error':error}

        token_raw = "%s:%s:%s"%(self.api_key, self.api_secret, epoch)
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

        if idProspect:
            body['idProspect'] = idProspect
  
        response = self.post(name="DGI H1 SPK ASP", url=api_url, body=body, headers=headers, type='incoming', verify=self.verify)
        if response.status_code == 200:
            content = json.loads(response.content)
            # Get Data Response
            data = content.get('data')
            if not data:
                error = "Data SPK tidak ditemukan !"
                if idSpk:
                    error = 'Data SPK %s tidak ditemukan !' % idSpk
                if not log:
                    raise Warning(error)
                return {'status':1,'data':data}
            if idSpk:
                data = [d for d in data if d.get('idSpk')==idSpk]
                if not data:
                    error = 'Data SPK %s tidak ditemukan !' % idSpk
                    if not log:
                        raise Warning(error)
                    return {'status':1,'data':data}
            
            query = """
                SELECT md_reference_spk
                FROM dealer_spk
                WHERE branch_id = %(branch_id)d
            """ % {'branch_id': branch.id}
            if idSpk:
                query += " AND md_reference_spk = '%(idSpk)s' " %{'idSpk':idSpk}
            else:
                query += " AND md_reference_spk IS NOT NULL "
            self._cr.execute(query)
            ress = self._cr.fetchall()
            registered_spk = [res[0] for res in ress]
            data = [d for d in data if d.get('statusSPK') in ('sale_order') and d.get('idSpk') not in registered_spk]

            if not data:
                error = "Data SPK tidak ditemukan !"
                if idSpk:
                    error = 'Data SPK %s tidak ditemukan !' % idSpk
                if not log:
                    raise Warning(error)
            return {'status':1, 'data':data}
        else:
            error = "Gagal Get SPK.\nStatus Code: %s\nContent: %s" % (response.status_code, response.content)
            if log:
                self.create_log_error_dgi('DGI H1 SPK ASP',api_url,'post',error,'SPK')
            return {'status':0,'error':error}


    @api.multi
    def _get_data_oder_asp_h1(self, branch, query_date=False, log=True, idProspect=False, idSpk=False):
        try:
            #default date is today (for scheduler)
            if not query_date:
                query_date = datetime.now()
            #get spk yang status completed/Approved dan belum di proses sebelumnya
            spks = self._get_api_spk_asp(branch, query_date, log, idProspect, idSpk)
            if spks.get('status', 0) == 1:
                spks = spks.get('data')
                #daftar id spk yg di proses saat ini, mencegah proses data dua kali
                daftar_spk = []

                #data spk yg siap di proses saat ini
                data_orders = {}

                for spk in spks:
                    statusSPK = spk.get('statusSPK')
                    idSpk = spk.get('idSpk')            
                    tanggalPesanan = spk.get('tanggalPesanan')

                    # tanggal spk dalam format date, jika tidak ada tanggal pesanan gunakan query date
                    tanggal_spk = query_date
                    if tanggalPesanan:
                        tanggal_spk = datetime.strptime(tanggalPesanan, '%d/%m/%Y')

                    tanggal_spk = max(query_date,tanggal_spk)

                    idProspect = spk.get('idProspect')
                    idSalesPeople = spk.get('idSalesPeople')
                    noKtp = spk.get('noKtp',False)
                    noKTPBPKB = spk.get('noKTPBPKB',False)

                    #jika belum di proses, lanjut
                    if idSpk not in daftar_spk:
                        # PROCESS BLOCKING: pada saat tidak terima data sales dari API
                        if not idSalesPeople:
                            error = 'ID SPK %s idSalesPeople Null !' %idSpk
                            if log:
                                self.create_log_error_dgi('DGI Data Order ASP',self.base_url,'post',error,'SPK')
                            continue

                        #PROCESS BLOCKING: jika nomor KTP tidak lengkap
                        if not noKTPBPKB and not noKtp:
                            error = 'ID SPK %s No KTP & No KTP BPKB not found !' %idSpk
                            if not log:
                                raise Warning(error)
                            self.create_log_error_dgi('DGI Data Order ASP',self.base_url,'post',error,'PRSP')
                            continue

                        #PROCESS BLOCKING: jika nomor KTP tidak 16 digit
                        if len(noKtp) != 16:
                            error = 'ID SPK %s No KTP tidak 16 Digit !' %idSpk
                            if not log:
                                raise Warning(error)
                            self.create_log_error_dgi('DGI Data Order ASP',self.base_url,'post',error,'PRSP')
                            continue
                        
                        #PROCESS BLOCKING: jika nomor KTP tidak 16 digit
                        if len(noKTPBPKB) != 16:
                            error = 'ID SPK %s No KTP BPKB tidak 16 Digit !' %idSpk
                            if not log:
                                raise Warning(error)
                            self.create_log_error_dgi('DGI Data Order ASP',self.base_url,'post',error,'PRSP')
                            continue

                        #PROCESS BLOCKING: jika detail unit tidak ada                    
                        unit = spk.get('unit')
                        if len(unit) == 0:
                            error = 'ID SPK %s Data Unit not found !' %idSpk
                            if not log:
                                raise Warning(error)
                            self.create_log_error_dgi('DGI Data Order ASP',self.base_url,'post',error,'SPK')
                            continue

                        data_orders[idSpk] = {'spk': spk}

                        prsp_result = self._get_api_prospek_asp(branch, tanggal_spk, log=log, idProspect=idProspect)
                        prsp = prsp_result.get('data')

                        #PROCESS BLOCKING: jika status=0 ataupun tidak ada data
                        # if prsp_result.get('status', 0)==0 or not prsp:
                        #     error = prsp_result.get('error', 'Get Prospect data not found ! ID Prospect %s' %idProspect)
                        #     if not log:
                        #         raise Warning(error)
                        #     self.create_log_error_dgi('DGI Data Order ASP',self.base_url,'post',error,'PRSP')
                        #     continue
                        if prsp:
                            data_orders[idSpk]['prsp'] = prsp[0]
                        else:
                            prsp = {
                                'idSalesPeople':spk.get('idSalesPeople'),
                                'noKontak':spk.get('noKontak'),
                                'sumberProspect':False,
                                'tanggalProspect':spk.get('tanggalPesanan'),
                                'metodeFollowUp':False,
                                'statusFollowUpProspecting':False,
                                'tanggalAppointment':False,
                                'waktuAppointment':False,
                                'idProspect':spk.get('idProspect') or idSpk,
                                'tanggingProspect':False,
                                'kodePosKantor':False,
                                'namaLengkap':spk.get('namaCustomer'),
                                'kodePos':spk.get('kodePos'),
                                'noKontakKantor':False,
                                'testRidePreference':False,
                                'idEvent':False,
                                'kodePekerjaan':False,
                                'longitude':False,
                                'kodeKecamatanKantor':False,
                                'noKtp':spk.get('noKtp'),
                                'alamat':spk.get('alamat'),
                                'kodePropinsi':spk.get('kodePropinsi'),
                                'kodeKota':spk.get('kodeKota'),
                                'kodeKecamatan':spk.get('kodeKecamatan'),
                                'kodeKelurahan':spk.get('kodeKelurahan'),
                            }

                            data_orders[idSpk]['prsp'] = prsp

                        #--------------Tipe Pembayaran--------------#
                            # 1=Cash
                            # 2=Credit
                        tipePembayaran = unit[0].get('tipePembayaran')
                        if tipePembayaran == 'Credit':
                            #-------------- Api Leasing --------------#
                            lsng_result = self._get_api_lsng_asp(branch, tanggal_spk, idSpk=idSpk)
                            lsng = lsng_result.get('data')

                            if lsng_result.get('status', 0)==0 or not lsng:
                                error = lsng_result.get('error', 'Get Leasing data not found ! ID SPK %s'%idSpk)
                                if not log:
                                    raise Warning(error)
                                self.create_log_error_dgi('DGI Data Order ASP',self.base_url,'post',error,'LSNG')
                                continue

                            data_orders[idSpk]['lsng'] = lsng[0]
                    
                    daftar_spk.append(idSpk)

                result = {
                    'status':1,
                    'data':data_orders.values()
                }
                return result
            else:
                error = spks.get('error')
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
            _logger.warning("Exception DGI Data Order ASP >>>>>>>>> %s"%(err))
            if not log:
                raise Warning(err)
            self.create_log_error_dgi('Exception DGI Data Order ASP',self.base_url,'post',err,'SPK')

    @api.multi
    def _process_data_order_asp_h1(self, branch, datas, log=True):
        #------------Data Finco----------#
        # CREATE INDEX res_partner_finance_company_index ON res_partner(finance_company)
        query_finco = """
            SELECT row_to_json(fincoy) as data
            FROM (SELECT id,ahm_code as code FROM res_partner WHERE finance_company = True) fincoy
        """
        self._cr.execute (query_finco)
        ress =  self._cr.dictfetchall()
        data_fincoy = {}
        for res in ress:
            data_fincoy[res['data']['code']] = res['data']['id'] 

        branch_id = branch.id
        data_emp = self.env['hr.employee']
        data_provinsi = self.env['res.country.state']
        data_city = self.env['wtc.city']
        data_kelurahan = self.env['wtc.kelurahan']
        data_kecamatan = self.env['wtc.kecamatan']
        data_sales_program = self.env['wtc.program.subsidi']

        for data in datas:                
            if not data.get('prsp'):
                error = "Data Prospect tidak ditemukan !"
                if not log:
                    raise Warning(error)
                self.create_log_error_dgi('DGI Data Order ASP',self.base_url,'post',error,'SPK')
                continue
            if not data.get('spk'):
                error = "Data SPK tidak ditemukan !"
                if not log:
                    raise Warning(error)
                continue

            # Definision Variabel       
            idSpk = data['spk'].get('idSpk')
            statusSPK = data['spk'].get('statusSPK')
            idProspect = data['spk'].get('idProspect')
            idSalesPeople = data['spk'].get('idSalesPeople')
            unit = data['spk'].get('unit')
            noKTPBPKB = data['spk'].get('noKTPBPKB')
            noKtp = data['spk'].get('noKtp')
            noKontak = data['spk'].get('noKontak') 
            alamatKK = data['spk'].get('alamatKK')
            kodePropinsiKK = data['spk'].get('kodePropinsiKK')
            kodePropinsi = data['spk'].get('kodePropinsi')
            kodeKotaKK = data['spk'].get('kodeKotaKK')
            kodeKota = data['spk'].get('kodeKota')
            kodeKelurahan = data['spk'].get('kodeKelurahan')
            kodeKelurahanKK = data['spk'].get('kodeKelurahanKK')
            kodePos = data['spk'].get('kodePos')
            kodePosKK = data['spk'].get('kodePosKK')
            kodeKecamatan = data['spk'].get('kodeKecamatan')
            kodeKecamatanKK = data['spk'].get('kodeKecamatanKK')
            alamat = data['spk'].get('alamat')    
            idEvent = data['spk'].get('idEvent')
            longitude = data['spk'].get('longitude')
            namaCustomer = data['spk'].get('namaCustomer') 
            latitude = data['spk'].get('latitude')
            email = data['spk'].get('email')
            npwp = data['spk'].get('npwp')
            fax = data['spk'].get('fax')
            tanggalPesanan = data['spk'].get('tanggalPesanan')
            namaBPKB = data['spk'].get('namaBPKB') 
            kodePosBPKB = data['spk'].get('kodePosBPKB')
            alamatBPKB = data['spk'].get('alamatBPKB') 
            kodePropinsiBPKB = data['spk'].get('kodePropinsiBPKB')
            kodeKotaBPKB = data['spk'].get('kodeKotaBPKB')
            kodeKecamatanBPKB = data['spk'].get('kodeKecamatanBPKB')    
            kodeKelurahanBPKB = data['spk'].get('kodeKelurahanBPKB')
            sales_koordinator_id = False
            product_id = False
            tipePembayaran = False
            dp = 0
            diskon = 0
            quantity = 1
            finco_id = False
            tenor = 0
            cicilan = 0
            finco_no_po = False
            finco_tgl_po = False
            tenor_list = 'lainnya'

            # Program Subsidi
            program_subsidi = False

            note_log = []
            lead_vals = {
                'md_reference_spk':idSpk,
                'md_reference_prospect':idProspect or idSpk,
            }

            kode_warna = unit[0].get('kodeWarna')
            kode_tipe_unit = unit[0].get('kodeTipeUnit')
            product_id = self._get_product_unit(kode_tipe_unit,kode_warna)
            if not product_id:
                error = 'ID SPK %s Product Kode Tipe %s dan Kode Warna %s not found !' %(idSpk,kode_tipe_unit,kode_warna)
                if not log:
                    raise Warning(error)
                self.create_log_error_dgi('DGI Data Order ASP',self.base_url,'post',error,'SPK')
                continue
            quantity = unit[0].get('quantity')
            diskon = unit[0].get('diskon')
            idApparel = unit[0].get('idApparel')
            idSalesProgram = unit[0].get('idSalesProgram')


            # tanggalPengiriman = unit[0].get('tanggalPengiriman')
            # fakturPajak = unit[0].get('fakturPajak')
            # kodePPN = unit[0].get('kodePPN')

            #--------------Tipe Pembayaran--------------#
            # 1=Cash
            # 2=Credit

            tipePembayaran = unit[0].get('tipePembayaran')
            if tipePembayaran == 'Cash':
                tipePembayaran = '1'
            elif tipePembayaran == 'Credit':
                tipePembayaran = '2'

                data_lsng = data['lsng']
                finco_id = data_fincoy.get(data_lsng.get('idFinanceCompany'))
                if not finco_id:
                    note_log.append('Data Finance Company %s not found !'%data_lsng['idFinanceCompany'])
                cicilan = data_lsng.get('jumlahCicilan')
                tenor = data_lsng.get('tenor')
                dp = data_lsng.get('jumlahDP')
                finco_no_po = data_lsng.get('idPOFinanceCompany',False)
                tanggalPembuatanPO = data_lsng.get('tanggalPembuatanPO',False)
                if tanggalPembuatanPO:
                    finco_tgl_po = datetime.strptime(tanggalPembuatanPO, '%d/%m/%Y')
                if tenor in ('12','18','24','36'):
                    tenor_list = tenor

            
            lead_vals.update({
                'product_id':product_id,
                'payment_type':tipePembayaran,
                'finco_id':finco_id,
                'tenor':tenor,
                'cicilan':cicilan,
                'uang_muka':dp,
                'diskon':diskon,
            })
        
            lead_obj = self.env['teds.lead'].suspend_security().search([
                ('branch_id','=',branch_id),
                ('no_ktp','=',noKtp),
                ('product_id','=',product_id),
                ('state','=','open')],limit=1)
            
            # PROSES BLOCKING LEAD TIDAK DITEMUKAN (SOURCE DODOLAN)
            if not lead_obj:
                if branch.is_allow_dgi_prsp:
                    data['prsp']['branch_id'] = branch_id
                    lead = self._get_data_prospek_asp(data['prsp'])
                    lead_obj = self.env['teds.lead'].suspend_security().create(lead)
                else:
                    error = 'Data Prospect Doodool tidak ditemukan ! Atas Nama %s No KTP %s Product Type %s Warna %s' %(
                        namaCustomer,
                        noKtp,
                        kode_tipe_unit,
                        kode_warna
                    )
                    if not log:
                        raise Warning(error)
                    self.create_log_error_dgi('DGI Data Order ASP',self.base_url,'post',error,'SPK')
                    continue
                    
            # --------------Employee Sales-----------------#
            get_employee = self._get_employee(branch_id,idSalesPeople)
            if not get_employee:
                error = 'ID SPK %s idSalesPeople %s not found !' %(idSpk,idSalesPeople)
                if not log:
                    raise Warning(error)
                self.create_log_error_dgi('DGI Data Order ASP',self.base_url,'post',error,'SPK')
                continue
            
            if not lead_obj.employee_id and idSalesPeople:
                lead_vals['employee_id'] = get_employee.id
            
            sales_koordinator_id = get_employee.coach_id.user_id.id

            #--------------Atas Nama STNK------------ #
            if not lead_obj.atas_nama_stnk:
                if noKTPBPKB == noKtp:
                    lead_vals['atas_nama_stnk'] = 'sendiri'
                else:
                    customer_stnk_id = self.env['res.partner'].suspend_security().search([('no_ktp','=',noKTPBPKB)],limit=1).id
                    if not customer_stnk_id:
                        # Data STNK #
                        provinsi_bpkb_id = False
                        city_bpkb_id = False
                        kecamatan_bpkb_id = False
                        kecamatan_bpkb = False
                        kelurahan_bpkb_id = False
                        kelurahan_bpkb = False

                        if kodeKelurahanBPKB:
                            obj_kel_bpkb = data_kelurahan.suspend_security().search([('code','=',kodeKelurahanBPKB)],limit=1)
                            if obj_kel_bpkb:
                                kelurahan_bpkb_id = obj_kel_bpkb.id
                                kelurahan_bpkb = obj_kel_bpkb.name
                                kecamatan_bpkb_id = obj_kel_bpkb.kecamatan_id.id
                                kecamatan_bpkb = obj_kel_bpkb.kecamatan_id.name
                                city_bpkb_id = obj_kel_bpkb.kecamatan_id.city_id.id
                                provinsi_bpkb_id = obj_kel_bpkb.kecamatan_id.city_id.state_id.id

                        if not kecamatan_bpkb_id and kodeKecamatanBPKB:
                            obj_kec_bpkb = data_kecamatan.suspend_security().search([('code','=',kodeKecamatanBPKB)],limit=1)
                            if obj_kec_bpkb:
                                kecamatan_bpkb_id = obj_kec_bpkb.id
                                kecamatan_bpkb = obj_kec_bpkb.name
                                city_bpkb_id = obj_kec_bpkb.city_id.id
                                provinsi_bpkb_id = obj_kec_bpkb.city_id.state_id.id

                        if not city_bpkb_id and kodeKotaBPKB:
                            obj_city_bpkb = data_city.suspend_security().search([('code','=',kodeKotaBPKB)],limit=1)
                            if obj_city_bpkb:
                                city_bpkb_id = obj_city_bpkb.id
                                provinsi_bpkb_id = obj_city_bpkb.state_id.id    
                        
                        if not provinsi_bpkb_id and kodePropinsiBPKB:
                            provinsi_bpkb_id = data_provinsi.suspend_security().search([('code','=',kodePropinsiBPKB)],limit=1).id

                        customer_stnk_id = self.env['res.partner'].suspend_security().create({
                            'branch_id':branch_id,
                            'name':namaBPKB,
                            'no_ktp':noKTPBPKB,
                            'street':alamatBPKB,
                            'state_id':provinsi_bpkb_id,
                            'city_id':city_bpkb_id,
                            'kecamatan_id':kecamatan_bpkb_id,
                            'kecamatan':kecamatan_bpkb,
                            'zip_id':kelurahan_bpkb_id,
                            'kelurahan':kelurahan_bpkb,
                            'customer':True,
                            'direct_customer':True,
                            'street_tab':alamatBPKB,
                            'state_tab_id':provinsi_bpkb_id,
                            'city_tab_id':city_bpkb_id,
                            'kecamatan_tab_id':kecamatan_bpkb_id,
                            'kecamatan_tab':kecamatan_bpkb,
                            'zip_tab_id':kelurahan_bpkb_id,
                            'kelurahan_tab':kelurahan_bpkb,    
                        }).id
                    
                    lead_vals['atas_nama_stnk'] = 'orang_lain'
                    lead_vals['customer_stnk_id'] = customer_stnk_id

            if not lead_obj.street:
                if alamat:
                    lead_vals['street'] = alamat
            # --------------Provinsi-----------------#
            if not lead_obj.state_id:
                provinsi_id = False
                if kodePropinsiKK:
                    provinsi_id = data_provinsi.suspend_security().search([('code','=',kodePropinsiKK)],limit=1).id
                    if not provinsi_id:
                        note_log.append('Kode Propinsi KK %s not found !'%kodePropinsiKK)
                
                if not provinsi_id and kodePropinsi:
                    provinsi_id = data_provinsi.suspend_security().search([('code','=',kodePropinsi)],limit=1).id
                    if not provinsi_id:
                        note_log.append('Kode Propinsi %s not found !'%kodePropinsi)
                if provinsi_id:
                    lead_vals['state_id'] = provinsi_id
                
            # --------------Kota / Kabupaten-----------------#
            if not lead_obj.kabupaten_id:
                city_id = False
                if kodeKotaKK:
                    city_id = data_city.suspend_security().search([('code','=',kodeKotaKK)],limit=1).id
                    if not city_id:
                        note_log.append('Kode Kota KK %s not found !')
                if not city_id and kodeKota:
                    city_id = data_city.suspend_security().search([('code','=',kodeKota)],limit=1).id
                    if not city_id:
                        note_log.append('Kode Kota %s not found !')
                if city_id:
                    lead_vals['kabupaten_id'] = city_id

            # --------------kelurahan-----------------#
            if not lead_obj.zip_code_id:
                kelurahan_id = False
                kelurahan = False
                kode_pos = False
                if kodeKelurahanKK:
                    kelurahan_obj = data_kelurahan.suspend_security().search([('code','=',kodeKelurahanKK)],limit=1)                                    
                    if not kelurahan_obj:
                        note_log.append('Kode Kelurahan KK %s not found !'%kodeKelurahanKK)
                    kelurahan_id = kelurahan_obj.id
                    kelurahan = kelurahan_obj.name
                    if not kodePos:
                        kode_pos = kelurahan.zip
                
                if not kelurahan_id and kodeKelurahan:
                    kelurahan_obj = data_kelurahan.suspend_security().search([('code','=',kodeKelurahan)],limit=1)
                    kelurahan_id = kelurahan_obj.id
                    kelurahan = kelurahan_obj.name
                    if not kodePos:
                        kode_pos = kelurahan_obj.zip
                    if not kelurahan_obj:
                        note_log.append('Kode Kelurahan %s not found !'%kodeKelurahan)                                    
                if kelurahan_id:
                    lead_vals.update({
                        'zip_code_id': kelurahan_id,
                        'kelurahan':kelurahan,
                        'kode_pos':kode_pos,
                    })

            
            # --------------Kecamatan-----------------#
            if not lead_obj.kecamatan_id:
                kecamatan_id = False
                kecamatan = False
                if kodeKecamatanKK:
                    kecamatan_obj = data_kecamatan.suspend_security().search([('code','=',kodeKecamatanKK)],limit=1)
                    if not kecamatan_obj:
                        note_log.append('Kode Kecamatan KK %s not found !'%kodeKecamatanKK)
                    kecamatan_id = kecamatan_obj.id
                    kecamatan = kecamatan_obj.name
                if not kecamatan_id and kodeKecamatan:
                    kecamatan_obj = data_kecamatan.suspend_security().search([('code','=',kodeKecamatan)],limit=1)
                    if not kecamatan_obj:
                        note_log.append('Kode Kecamatan %s not found !'%kodeKecamatan)
                    kecamatan_id = kecamatan_obj.id
                    kecamatan = kecamatan_obj.name
                if kecamatan_id:
                    lead_vals.update({
                        'kecamatan_id':kecamatan_id,
                        'kecamatan':kecamatan    
                    })
                           
            if not lead_obj.no_ktp:
                lead_vals['no_ktp'] = noKtp
           
            lead_obj.suspend_security().write(lead_vals)
            lead_obj.suspend_security().action_deal()

            spk = lead_obj.spk_id
            spk.suspend_security().write({
                'md_reference_spk':idSpk,
                'md_reference_prospect':idProspect,
                'md_reference_lsng':idSpk,
                'sales_koordinator_id':sales_koordinator_id,
                'note_log':note_log
            })
            spk.suspend_security().action_confirm_spk()
            spk.suspend_security().action_create_so()
            spk.dealer_sale_order_id.suspend_security().write({
                'md_reference_spk':idSpk,
                'md_reference_prospect':idProspect,
                'md_reference_lsng':idSpk,
            })
            spk.dealer_sale_order_id.dealer_sale_order_line[0].suspend_security().write({
                'tenor_list':tenor_list,
                'finco_tenor':tenor,
                'cicilan':int(float(cicilan)),
                'finco_no_po':finco_no_po,
                'finco_tgl_po':finco_tgl_po,
            })
            return True

    @api.multi
    def dgi_asp_order_spk(self,branch):        
        try:
            get_response = self._get_data_oder_asp_h1(branch)
            if get_response.get('status') == 1:
                datas = get_response.get('data')
                if datas:
                    # proses data create sale order draft
                    self._process_data_order_asp_h1(branch,datas)
            else:
                error = get_response.get('error')
                self.create_log_error_dgi('DGI Data Order ASP',self.base_url,'post',error,'SPK')
                
                
        except Exception as err:
            _logger.warning("Exception DGI Data Order ASP >>>>>>>>> %s"%(err))
            self.create_log_error_dgi('Exception Schedule DGI Data Order ASP',self.base_url,'post',err,'SPK')
            
    
    @api.multi
    def schedule_data_order_asp_h1(self,code):
        branch_config_id = self.env['wtc.branch.config'].suspend_security().search([('name','=',code)],limit=1)
        config_id = branch_config_id.config_dgi_id
        branch = branch_config_id.branch_id
        if config_id and branch:
            return config_id.suspend_security().dgi_asp_order_spk(branch)
        else:
            error = 'Branch Config DGI belum di setting !'
            _logger.warning(error)
            self.create_log_error_dgi('DGI Data Order ASP',False,'post',error,'Schedule')            