from openerp import models, fields, api
from openerp.exceptions import Warning
from datetime import timedelta, datetime
import time
from dateutil.relativedelta import relativedelta
import json
import requests
import hashlib

import logging
_logger = logging.getLogger(__name__)


class B2bApiConfig(models.Model):
    _inherit = "teds.b2b.api.config"

    @api.multi
    def _get_api_prospek_tdm(self, branch, query_date, log=True, idProspect=False):
        api_url = "%s/prsp/read" % self.base_url
        date_format = '%Y-%m-%d %H:%M:%S'

        from_time = datetime.combine(query_date - timedelta(days=7), datetime.min.time())
        to_time = datetime.combine(query_date, datetime.max.time())

        ## EPOCH ##
        # epoch = int(time.mktime(time.strptime(datetime.now().strftime(date_format), '%Y-%m-%d %H:%M:%S')))
        # verify pakai time.localtime() or time.gmtime()
        epoch = int(time.mktime(time.localtime()))

        # TOKEN DGI #
        if not self.api_key and self.api_secret:
            error = "API Key dan API Secret Required !"
            if log:
                self.create_log_error_dgi('DGI H1 SPK TDM',api_url,'post',error,'SPK')
            return {'status':0,'error':error}
        token_raw = "%s:%s:%s" % (self.api_key, self.api_secret, epoch)
        token = hashlib.sha256(token_raw).hexdigest()

        headers = {
            "DGI-API-Key": self.api_key,
            "Content-Type": "application/json",
            "X-Request-Time": str(epoch),
            "DGI-API-Token": token
        }
        # Body #
        body = {
            "fromTime": from_time.strftime(date_format),
            "toTime": to_time.strftime(date_format),
        }
        if branch.md_reference:
            body['dealerId'] = branch.md_reference

        if idProspect:
            body["idProspect"] = idProspect

        response = self.post(name="DGI H1 PRSP TDM", url=api_url, body=body, headers=headers, type='incoming', verify=self.verify)
        if response.status_code == 200:
            content = json.loads(response.content)
            # Get Data Response
            data = content.get('data')
            if not data:
                error = "Data Prospect tidak ditemukan !"
                if idProspect:
                    error = 'Data Prospect %s tidak ditemukan !' % idProspect
                if log:
                    self.create_log_error_dgi('DGI H1 SPK TDM',api_url,'post',error,'PRSP')
                return {'status':0,'error':error}
            return {'status':1, 'data':data}
        else:
            error = "Gagal Get Prospect.\nStatus Code: %s\nContent: %s" % (response.status_code, response.content)
            if log:
                self.create_log_error_dgi('DGI H1 SPK TDM',api_url,'post',error,'PRSP')
            return {'status':0,'error':error}

    @api.multi
    def _get_data_prospek_tdm(self, vals):
        data_stage = self.env['teds.lead.stage']
        data_provinsi = self.env['res.country.state']
        data_emp = self.env['hr.employee']
        data_city = self.env['wtc.city']
        data_kelurahan = self.env['wtc.kelurahan']
        data_kecamatan = self.env['wtc.kecamatan']
        data_type_sumber_penj = self.env['teds.act.type.sumber.penjualan']
        data_questionnaire = self.env['wtc.questionnaire']

        prsp = vals
        note_log = []

        branch_id = prsp.get('branch_id')
        idSalesPeople = prsp.get('idSalesPeople')
        employee_id = False
        if idSalesPeople:
            get_employee = self.env['teds.b2b.api.config']._get_employee(
                branch_id, idSalesPeople)
            if get_employee:
                employee_id = get_employee.id
            else:
                note_log.append('idSalesPeople %s not found !' % idSalesPeople)
        noKontak = prsp.get('noKontak')

        # Sumber Prospect #
            # 0001=Event/pameran(Joint Promo, Grebek Pasar, Indomaret, Mall, dll)
            # 0002=Showroom event
            # 0003=Roadshow
            # 0004=Walk-in
            # 0005=Customer RO H1
            # 0006=Customer RO H23
            # 0007=Website
            # 0008=Sosial Media (Instagram,twitter,facebook,whatsapp)
            # 0009=External parties/reference (Leasing, Insurance)
            # 0010=Mobile apps MD atau Dealer
            # 0011 = Refferal
            # 0012 = Contact Centre
            # 9999=Others
            

        sumberProspect = prsp.get('sumberProspect')
        if sumberProspect == '0001':
            sumberProspect = 'Pameran'
        elif sumberProspect == '0002':
            sumberProspect = 'Showroom Event'
        elif sumberProspect == '0003':
            sumberProspect = 'Road Show'
        elif sumberProspect == '0004':
            sumberProspect = 'Walk In'
        elif sumberProspect == '0005':
            sumberProspect = 'Customer RO H1'
        elif sumberProspect == '0005':
            sumberProspect = 'Customer RO H23'
        elif sumberProspect == '0007':
            sumberProspect = 'Online'
        elif sumberProspect == '0008':
            sumberProspect = 'Online'
        elif sumberProspect == '0009':
            sumberProspect = 'External parties (leasing, insurance)'
        elif sumberProspect == '0010':
            sumberProspect = 'Mobile Apps Md/Dealer'
        elif sumberProspect == '0011':
            sumberProspect = 'Refferal'
        elif sumberProspect == '0012':
            sumberProspect = 'Contact Centre'
        else:
            sumberProspect = 'Others'
        sumber_penjualan_id = data_type_sumber_penj.suspend_security().search([
            ('name', '=', sumberProspect)], limit=1).id
        if not sumber_penjualan_id and sumberProspect:
            note_log.append(
                'Data Sumber Penjualan %s not found !' % sumberProspect)

        # -------------Tanggal Prospek------ #
        tgl_prospek = False
        tanggalProspect = prsp.get('tanggalProspect')
        if tanggalProspect:
            hari, bulan, tahun = tanggalProspect.split("/")
            tgl_prospek = "%s-%s-%s" % (tahun, bulan, hari)

        # Metode Follow Up #
            # Riding Test
            # Call
            # Sms
            # Visit

        metodeFollowUp = prsp.get('metodeFollowUp')
        if metodeFollowUp == 'Sms':
            metodeFollowUp = 'MESSAGE'
        elif metodeFollowUp == 'Call':
            metodeFollowUp = 'CALL'
        elif metodeFollowUp == 'Visit':
            metodeFollowUp = 'VISIT'
        elif metodeFollowUp == 'Riding Test':
            metodeFollowUp = 'RIDING TEST'

        statusFollowUpProspecting = prsp.get('statusFollowUpProspecting')

        tgl_fu = False
        tanggalAppointment = prsp.get('tanggalAppointment')
        if tanggalAppointment:
            hari, bulan, tahun = tanggalAppointment.split("/")
            waktuAppointment = prsp.get('waktuAppointment')
            tgl_fu = "%s-%s-%s %s:00" % (tahun, bulan, hari, waktuAppointment)

        lead_stage_id = data_stage.suspend_security().search(
            [('name', 'ilike', metodeFollowUp), ('type', '=', 'lead')], limit=1).id
        if not lead_stage_id and metodeFollowUp:
            note_log.append('Data Stage Activity %s not found !' %
                            metodeFollowUp)
        # lead_result_id = data_result_stage.get(statusFollowUpProspecting)

        lead_activity_ids = []
        if lead_stage_id:
            lead_activity_ids.append([0, False, {
                'name': lead_stage_id,
                'date': tgl_fu,
                'minat': 'hot',
            }])

        idProspect = prsp.get('idProspect')
        tanggingProspect = prsp.get('tanggingProspect')
        kodePosKantor = prsp.get('kodePosKantor')
        namaLengkap = prsp.get('namaLengkap')
        kodePos = prsp.get('kodePos')
        noKontakKantor = prsp.get('noKontakKantor')
        testRidePreference = prsp.get('testRidePreference')
        idEvent = prsp.get('idEvent')
        kodePekerjaan = prsp.get('kodePekerjaan')
        longitude = prsp.get('longitude')
        kodeKecamatanKantor = prsp.get('kodeKecamatanKantor')
        noKtp = prsp.get('noKtp')
        alamat = prsp.get('alamat')

        provinsi_id = False
        city_id = False
        kecamatan_id = False
        kecamatan = False
        kelurahan_id = False
        kelurahan = False

        kodePropinsi = prsp.get('kodePropinsi')
        kodeKota = prsp.get('kodeKota')
        kodeKecamatan = prsp.get('kodeKecamatan')
        kodeKelurahan = prsp.get('kodeKelurahan')

        if kodeKelurahan:
            obj_kel = data_kelurahan.suspend_security().search(
                [('code', '=', kodeKelurahan)], limit=1)
            if obj_kel:
                kelurahan_id = obj_kel.id
                kelurahan = obj_kel.name
                kecamatan_id = obj_kel.kecamatan_id.id
                kecamatan = obj_kel.kecamatan_id.name
                city_id = obj_kel.kecamatan_id.city_id.id
                provinsi_id = obj_kel.kecamatan_id.city_id.state_id.id
            else:
                note_log.append('Kode Kelurahan %s not found !' %
                                kodeKelurahan)

        if not kecamatan_id and kodeKecamatan:
            obj_kec = data_kecamatan.suspend_security().search(
                [('code', '=', kodeKecamatan)], limit=1)
            if obj_kec:
                kecamatan_id = obj_kec.id
                kecamatan = obj_kec.name
                city_id = obj_kec.city_id.id
                provinsi_id = obj_kec.city_id.state_id.id
            else:
                note_log.append('Kode Kecamatan %s not found !' %
                                kodeKecamatan)

        if not city_id and kodeKota:
            obj_city = data_city.suspend_security().search(
                [('code', '=', kodeKota)], limit=1)
            if obj_city:
                city_id = obj_city.id
                provinsi_id = obj_city.state_id.id
            else:
                note_log.append('Kode Kota %s not found !' % kodeKota)

        if not provinsi_id and kodePropinsi:
            provinsi_id = data_provinsi.suspend_security().search(
                [('code', '=', kodePropinsi)], limit=1).id
            if not provinsi_id:
                note_log.append('Kode Propinsi %s not found !' % kodePropinsi)

        kodePekerjaan = prsp.get('kodePekerjaan')
        pekerjaan_id = False
        if kodePekerjaan:
            pekerjaan_id = data_questionnaire.suspend_security().search([
                ('value', '=', kodePekerjaan),
                ('type', '=', 'Pekerjaan')], limit=1).id
            if not pekerjaan_id:
                note_log.append(
                    'Questionnaire Kode Pekerjaan %s not found !' % kodePekerjaan)

        lead_vals = {
            'branch_id': branch_id,
            'mobile': noKontak,
            'state_id': provinsi_id,
            'kecamatan_id': kecamatan_id,
            'kecamatan': kecamatan,
            'street': alamat,
            'kabupaten_id': city_id,
            'employee_id': employee_id,
            'date': tgl_prospek,
            'zip_code_id': kelurahan_id,
            'kelurahan': kelurahan,
            'name_customer': namaLengkap,
            'kode_pos': kodePos,
            'md_reference_prospect': idProspect,
            'lead_activity_ids': lead_activity_ids,
            'sumber_penjualan_id': sumber_penjualan_id,
            'jaringan_penjualan': 'Showroom',
            'is_sesuai_ktp': True,
            'street_domisili':alamat,
            'state_domisili_id':provinsi_id,
            'kabupaten_domisili_id':city_id,
            'kecamatan_domisili_id':kecamatan_id,
            'zip_code_domisili_id':kelurahan_id,
            'kecamatan_domisili':kecamatan,
            'kelurahan_domisili':kelurahan,
            'pekerjaan_id': pekerjaan_id,
            'minat': 'hot',
            'note_log': note_log,
            'no_ktp': noKtp,
            'data_source': 'dgi',
        }
        return lead_vals
