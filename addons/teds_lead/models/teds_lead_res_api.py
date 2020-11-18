import openerp.http as http
from openerp.http import request
from openerp.addons.rest_api.controllers.main import *
from datetime import date,timedelta,datetime,date
import logging
_logger = logging.getLogger(__name__)

def invalid_response(status, error, info,method):
    if method == 'POST':
        return {
            'error': error,
            'error_descrip': info,
        }

    elif method == 'GET':
        return werkzeug.wrappers.Response(
            status=status,
            content_type='application/json; charset=utf-8',
            response=json.dumps({
                'error': error,
                'error_descrip': info,
            }),
        )

def invalid_token(method):
    _logger.error("Token is expired or invalid!")    
    return invalid_response(401, 'invalid_token', "Token is expired or invalid!",method)

def check_valid_token(func):
    @functools.wraps(func)
    def wrap(self, *args, **kwargs):
        access_token = request.httprequest.headers.get('access_token')
        method = request.httprequest.method
        if not access_token:
            info = "Missing access token in request header!"
            error = 'access_token_not_found'
            _logger.error(info)
            return invalid_response(400, error, info,method)

        access_token_data = request.env['oauth.access_token'].sudo().search(
            [('token', '=', access_token)], order='id DESC', limit=1)

        if access_token_data._get_access_token(user_id=access_token_data.user_id.id) != access_token:
            return invalid_token(method)

        request.session.uid = access_token_data.user_id.id
        request.uid = access_token_data.user_id.id
        return func(self, *args, **kwargs)

    return wrap


class ControllerREST(http.Controller):
    @http.route('/api/dodol/v1/new-order/add', methods=['POST'], type='json', auth='none', csrf=False)
    @check_valid_token
    def lead_new_order(self, **post):
        remark = []
        vals = post.get('leads')
        activity = post.get('activity')

        res_activity = {}
        tgl_now = date.today()
        
        data_provinsi = request.env['res.country.state']
        data_city = request.env['wtc.city']
        data_kelurahan = request.env['wtc.kelurahan']
        data_kecamatan = request.env['wtc.kecamatan']
        

        data_lead = post.get('lead')
        data_activity = post.get('activity')

        # Olah Data Lead
        message = ''
        is_allow_lead = True

        # Definition
        branch_code = data_lead.get('branch_code')
        prod_code = data_lead.get('prod_code')
        warna_code = data_lead.get('warna_code')

        branch_id = request.env['wtc.branch'].sudo().search([('code','=',branch_code)],limit=1)
        if not branch_id:
            message += "Branch Code %s not found \n"%(branch_code)
        is_allow_lead = branch_id.is_allow_lead
        branch_id = branch_id.id
        
        product = """
            SELECT pp.id as prod_id
            FROM product_product pp
            INNER JOIN product_template pt ON pt.id = pp.product_tmpl_id 
            LEFT JOIN product_attribute_value_product_product_rel rel ON rel.prod_id = pp.id
            LEFT JOIN product_attribute_value pav ON pav.id = rel.att_id 
            WHERE name_template = '%s' AND pav.code='%s'
        """ %(prod_code,warna_code)
        request._cr.execute(product)
        res = request._cr.fetchone()
        product_id = False
        if not res:
            message += "Product Code %s & Warna Code %s not found \n"%(prod_code,warna_code)
        else:    
            product_id = res[0]

        # CEK SALESMAN
        tunas_id = data_lead.get('tunas_id')
        nip_sales = data_lead.get('nip_sales')
        identification_id = data_lead.get('identification_id')
        nama_sales = data_lead.get('nama_sales')
        employee_id = False
        if not identification_id and not tunas_id:
            message += "Data Salesman belum di setting (Tunas ID, No KTP, NIP) ! \n"
        
        emp_where = """ 
            WHERE hr.branch_id = %d 
            AND job.sales_force IN ('salesman','sales_counter','sales_partner','sales_koordinator','soh')
            AND hr.tgl_keluar IS NULL
        """ %(branch_id)
        emp_where_ktp = ""
        emp_where_nip = ""
        emp_where_tunas_id = ""
        if tunas_id:
            emp_where_tunas_id += " hr.code_honda = '%s'" %(tunas_id)
        if identification_id:
            emp_where_ktp += " OR hr.identification_id = '%s'" %(identification_id)
        if nip_sales:
            emp_where_nip += " OR hr.nip = '%s'" %(nip_sales)
                
        emp_where += " AND (%s %s %s)" %(emp_where_tunas_id,emp_where_ktp,emp_where_nip)
        emp_query = """
            SELECT
            rr.user_id as user_id
            , hr.id as employee_id
            FROM hr_employee hr
            INNER JOIN hr_job job ON job.id = hr.job_id
            LEFT JOIN resource_resource rr ON rr.id = hr.resource_id
            %s
            LIMIT 1
        """ %(emp_where)
        request._cr.execute (emp_query)
        res_emp = request._cr.dictfetchall()
        if not res_emp:
            message += "Sales A/n %s belum di mapping di TEDS !\n"%(nama_sales)
        else:
            user_id = res_emp[0].get('user_id')
            employee_id = res_emp[0].get('employee_id')            
            if not user_id:
                message += "Sales A/n %s tidak memiliki Data User di TEDS ! \n"%(nama_sales)
        
        # CEK SALES KOORDINATOR
        sco_identification_id = data_lead.get('sco_identification')
        sco_tunas_id = data_lead.get('sco_tunas_id')
        sco_nip = data_lead.get('sco_nip')
        nama_sco = data_lead.get('nama_sco')
        sales_koordinator_id = False
        if sco_tunas_id or sco_nip:
            sco_where = """ 
                WHERE hr.branch_id = %d 
                AND job.sales_force IN ('salesman','sales_counter','sales_partner','sales_koordinator','soh','AM')
                AND hr.tgl_keluar IS NULL
            """ %(branch_id)
            sco_where_ktp = ""
            sco_where_tunas_id = ""
            sco_where_nip = ""
            if sco_tunas_id:
                sco_where_tunas_id += " hr.code_honda = '%s'" %sco_tunas_id 
            if sco_identification_id:
                sco_where_ktp += " OR hr.identification_id = '%s'" %(sco_identification_id)
            if sco_nip:
                sco_where_nip += " OR hr.nip = '%s'" %sco_nip
            sco_where += " AND (%s %s %s)" %(sco_where_tunas_id,sco_where_ktp,sco_where_nip)
            sco_query = """
                SELECT
                rr.user_id as user_id
                , hr.id as employee_id
                FROM hr_employee hr
                INNER JOIN hr_job job ON job.id = hr.job_id
                LEFT JOIN resource_resource rr ON rr.id = hr.resource_id
                %s
                LIMIT 1
            """ %(sco_where)
            request._cr.execute (sco_query)
            res_sco = request._cr.dictfetchall()
            if not res_sco:
                message += "Sales Koordinator A/n %s belum di mapping di TEDS !\n"%(nama_sco)
            else:    
                sales_koordinator_id = res_sco[0].get('employee_id')            
                user_sco_id = res_sco[0].get('user_id')
                if not user_sco_id:
                    message += "Sales Koordinator A/n %s tidak memiliki Data User di TEDS ! \n"%(nama_sco)

        # Function untuk penambahan values lead
        vals_lead_other = request.env['teds.lead'].sudo()._get_values_lead_other(data_lead)
        # Error harus mengirimkan status error dan message
        if vals_lead_other.get('error'):
            message += vals_lead_other.get('message','Error Get Values Lead Other')
        
        remark_val = {}
        error = False
        if message:
            remark_val = {
                'error':True,
                'error_descrip':message
            }
            return {'status':1,'message':remark_val}
        else:
            # Mulai Pengecekan LEAD setelah tidak ada message error
            state_id = False
            kabupaten_id = False
            kecamatan_id = False
            kecamatan = False
            zip_code_id = False
            kelurahan = False
            
            state_domisili_id = False
            kabupaten_domisili_id = False
            kecamatan_domisili_id = False
            kecamatan_domisili = False
            zip_code_domisili_id = False
            kelurahan_domisili = False

            kel_code = data_lead.get('kel_code')
            kec_code = data_lead.get('kec_code')
            city_code = data_lead.get('city_code')
            state_code = data_lead.get('state_code')

            state_code_domisili = data_lead.get('state_code_domisili')
            city_code_domisili = data_lead.get('city_code_domisili')
            kec_code_domisili = data_lead.get('kec_code_domisili')
            kel_code_domisili = data_lead.get('kel_code_domisili')

            # Alamat
            if kel_code:
                obj_kel = data_kelurahan.sudo().search([('code','=',kel_code)],limit=1)
                if obj_kel:
                    zip_code_id = obj_kel.id
                    kelurahan = obj_kel.name
                    kecamatan_id = obj_kel.kecamatan_id.id
                    kecamatan = obj_kel.kecamatan_id.name
                    kabupaten_id = obj_kel.kecamatan_id.city_id.id
                    state_id = obj_kel.kecamatan_id.city_id.state_id.id

            if not kecamatan_id and kec_code:
                obj_kec = data_kecamatan.sudo().search([('code','=',kec_code)],limit=1)
                if obj_kec:
                    kecamatan_id = obj_kec.id
                    kecamatan = obj_kec.name
                    kabupaten_id = obj_kec.city_id.id
                    state_id = obj_kec.city_id.state_id.id

            if not kabupaten_id and city_code:
                obj_city = data_city.sudo().search([('code','=',city_code)],limit=1)
                if obj_city:
                    kabupaten_id = obj_city.id
                    state_id = obj_city.state_id.id
            
            if not state_id and state_code:
                state_id = data_provinsi.sudo().search([('code','=',state_code)],limit=1).id

            # Alamat Domisili
            if not data_lead.get('is_sesuai_ktp'):
                if kel_code_domisili:
                    obj_kel_dom = data_kelurahan.sudo().search([('code','=',kel_code_domisili)],limit=1)
                    if obj_kel_dom:
                        zip_code_domisili_id = obj_kel_dom.id
                        kelurahan_domisili = obj_kel_dom.name
                        kecamatan_domisili_id = obj_kel_dom.kecamatan_id.id
                        kecamatan_domisili = obj_kel_dom.kecamatan_id.name
                        kabupaten_domisili_id = obj_kel_dom.kecamatan_id.city_id.id
                        state_domisili_id = obj_kel_dom.kecamatan_id.city_id.state_id.id

                if not kecamatan_domisili_id and kec_code_domisili:
                    obj_kec_dom = data_kecamatan.sudo().search([('code','=',kec_code_domisili)],limit=1)
                    if obj_kec_dom:
                        kecamatan_domisili_id = obj_kec_dom.id
                        kecamatan_domisili = obj_kec_dom.name
                        kabupaten_domisili_id = obj_kec_dom.city_id.id
                        state_domisili_id = obj_kec_dom.city_id.state_id.id

                if not kabupaten_domisili_id and city_code_domisili:
                    obj_city_dom = data_city.sudo().search([('code','=',city_code_domisili)],limit=1)
                    if obj_city_dom:
                        kabupaten_domisili_id = obj_city_dom.id
                        state_domisili_id = obj_city_dom.state_id.id
                
                if not state_domisili_id and state_code_domisili:
                    state_domisili_id = data_provinsi.sudo().search([('code','=',state_code_domisili)],limit=1).id
            
            # Questionaire
            jenis_kelamin_id = False
            agama_id = False
            gol_darah_id = False
            pekerjaan_id = False
            pengeluaran_id = False
            pendidikan_id = False
            merkmotor_id = False
            jenismotor_id = False
            penggunaan_id = False
            pengguna_id = False
            hobi_id = False
            status_hp_id = False
            status_rumah_id = False

            query_questionnaire = """
                SELECT row_to_json(questionnaire) as data
                FROM (SELECT id,type||'|'||value as value FROM wtc_questionnaire WHERE type is not null and value is not null) questionnaire
            """
            request._cr.execute (query_questionnaire)
            ress =  request._cr.dictfetchall()
            data_questionnaire = {}
            for res in ress:
                data_questionnaire[res['data']['value']] = res['data']['id'] 

            status_hp = data_lead.get('status_hp')
            if status_hp:
                value_status_hp = "%s|%s" %('Status HP',status_hp)
                status_hp_id = data_questionnaire.get(value_status_hp)
            
            status_rumah = data_lead.get('status_rumah')
            if status_rumah:
                value_status_rumah = "%s|%s" %('Status Rumah',status_rumah)
                status_rumah_id = data_questionnaire.get(value_status_rumah)

            jenis_kelamin = data_lead.get('jk')
            if jenis_kelamin:
                value_jk = "%s|%s" %('JenisKelamin',jenis_kelamin)
                jenis_kelamin_id = data_questionnaire.get(value_jk)

            agama = data_lead.get('agama') 
            if agama:
                value_agama = "%s|%s" %('Agama',agama)
                agama_id = data_questionnaire.get(value_agama)
                
            gol_darah = data_lead.get('gol_darah')
            if gol_darah:
                value_gol_darah = "%s|%s" %('GolonganDarah',gol_darah)
                gol_darah_id = data_questionnaire.get(value_gol_darah)

            pekerjaan = data_lead.get('pekerjaan')
            if pekerjaan:
                value_pekerjaan = "%s|%s" %('Pekerjaan',pekerjaan)
                pekerjaan_id = data_questionnaire.get(value_pekerjaan)
            
            pengeluaran = data_lead.get('pengeluaran') 
            if pengeluaran:
                value_pengeluaran = "%s|%s" %('Pengeluaran',pengeluaran)
                pengeluaran_id = data_questionnaire.get(value_pengeluaran)
            
            pendidikan = data_lead.get('pendidikan')     
            if pendidikan:
                value_pendidikan = "%s|%s" %('Pendidikan',pendidikan)
                pendidikan_id = data_questionnaire.get(value_pendidikan)
            
            merkmotor = data_lead.get('merkmotor')     
            if merkmotor:
                value_merkmotor = "%s|%s" %('MerkMotor',merkmotor)
                merkmotor_id = data_questionnaire.get(value_merkmotor)
            
            jenismotor = data_lead.get('jenismotor')     
            if jenismotor:
                value_jenismotor = "%s|%s" %('JenisMotor',jenismotor)
                jenismotor_id = data_questionnaire.get(value_jenismotor)
            
            penggunaan = data_lead.get('penggunaan')     
            if penggunaan:
                value_penggunaan = "%s|%s" %('Penggunaan',penggunaan)
                penggunaan_id = data_questionnaire.get(value_penggunaan)
            
            pengguna = data_lead.get('pengguna')     
            if pengguna:
                value_pengguna = "%s|%s" %('Pengguna',pengguna)
                pengguna_id = data_questionnaire.get(value_pengguna)
            
            hobi = data_lead.get('hobi')     
            if hobi:
                value_hobi = "%s|%s" %('Hobi',hobi)
                hobi_id = data_questionnaire.get(value_hobi)

            finco_id = False
            if data_lead.get('finco',False):
                finco_id = request.env['res.partner'].sudo().search([
                    ('ahm_code','=',data_lead['finco']),
                    ('finance_company','=',True)],limit=1).id

            #Mapping Sumber Penjualan#
            transaction_id = data_lead.get('transaction_id')
            jaringan_penjualan = data_lead.get('jaringan_penjualan',False)
            sales_source_location_id = data_lead.get('stock_location_id')
            act_type = data_lead.get('act_type','WI')
            
            if jaringan_penjualan == 'showroom':
                jaringan_penjualan = 'Showroom'
                sales_source_location_id = False
            elif jaringan_penjualan == 'pos':
                jaringan_penjualan = 'POS'
            else: 
                jaringan_penjualan = 'Showroom'

            sumber_penjualan_id = request.env['teds.act.type.sumber.penjualan'].sudo().search([('code','=',act_type)],limit=1).id
            activity_plan_id = False
            is_btl = False
            titik_keramaian_id = False
            
            if transaction_id:
                activity_plan_obj = request.env['teds.sales.plan.activity.line'].sudo().browse(transaction_id)
                if activity_plan_obj:
                    jaringan_penjualan = activity_plan_obj.jaringan_penjualan
                    sumber_penjualan_id = activity_plan_obj.act_type_id.id
                    is_btl = activity_plan_obj.act_type_id.is_btl
                    activity_plan_id = transaction_id
                    titik_keramaian_id = activity_plan_obj.titik_keramaian_id.id

            if jaringan_penjualan == 'POS' and is_btl:
                sales_source_location_id = False

            lead_vals = {
                'branch_id': branch_id, 
                'name_customer':data_lead.get('name_customer'),
                'minat': data_lead.get('minat'), 
                'product_id':product_id,
                'no_ktp': data_lead.get('no_ktp'), 
                'mobile': data_lead.get('mobile'), 
                'kontak_tambahan': data_lead.get('kontak_tambahan'),
                'employee_id':employee_id,
                'no_refrence':data_lead.get('no_refrence'),
                
                # Data Jaringan Penjualan
                'jaringan_penjualan':jaringan_penjualan,
                'sumber_penjualan_id':sumber_penjualan_id,
                'is_btl':is_btl,
                'activity_plan_id':activity_plan_id,
                'titik_keramaian_id':titik_keramaian_id,
                'sales_source_location_id':sales_source_location_id,
                # ---------------------------------------

                'street': data_lead.get('street'), 
                'rt': data_lead.get('rt'), 
                'rw': data_lead.get('rw'), 
                'state_id':state_id,
                'kabupaten_id':kabupaten_id,
                'kecamatan_id':kecamatan_id,
                'kecamatan': data_lead.get('kecamatan'),
                'zip_code_id':zip_code_id, 
                'kelurahan': kelurahan, 
                'kode_pos': data_lead.get('kode_pos'),

                'is_sesuai_ktp': data_lead.get('is_sesuai_ktp'), 
                'street_domisili': data_lead.get('street_domisili'),
                'rt_domisili':data_lead.get('rt_domisili'),
                'rw_domisili':data_lead.get('rw_domisili'),
                'state_domisili_id':state_domisili_id,
                'kabupaten_domisili_id':kabupaten_domisili_id,
                'kecamatan_domisili_id':kecamatan_domisili_id,
                'zip_code_domisili_id':zip_code_domisili_id,
                'kecamatan_domisili': data_lead.get('kecamatan_domisili'),
                'kelurahan_domisili': data_lead.get('kelurahan_domisili'),
                'kode_pos_domisili': data_lead.get('kode_pos_domisili'),
                
                'tempat_tgl_lahir': data_lead.get('tempat_tgl_lahir'), 
                'tgl_lahir': data_lead.get('tgl_lahir'),
                'no_kk': data_lead.get('no_kk'), 
                'motor_sekarang': data_lead.get('motor_sekarang'),

                'payment_type': data_lead.get('payment_type'),
                'finco_id':finco_id,
                'uang_muka': data_lead.get('uang_muka'),
                'tgl_uang_muka': data_lead.get('tgl_uang_muka'), 
                'date_jatuh_tempo': data_lead.get('date_jatuh_tempo'), 
                'tenor': data_lead.get('tenor'), 
                'cicilan': data_lead.get('cicilan'), 
                'otr': data_lead.get('otr'),
                'diskon': data_lead.get('diskon'), 
                'atas_nama_stnk': data_lead.get('atas_nama_stnk'),
                'email': data_lead.get('email'), 
                'facebook': data_lead.get('facebook'), 
                'instagram': data_lead.get('instagram'), 
                'twitter': data_lead.get('twitter'), 
                'youtube': data_lead.get('youtube'), 
                'kode_customer': data_lead.get('kode_customer') or 'I',
                
                # DATA QUESTIONNAIRE
                'jenis_kelamin_id':jenis_kelamin_id,
                'status_hp_id': status_hp_id,
                'penggunaan_id': penggunaan_id,
                'pengguna_id': pengguna_id,
                'hobi': hobi_id,
                'agama_id':agama_id,
                'gol_darah':gol_darah_id,
                'pekerjaan_id':pekerjaan_id,
                'pengeluaran_id':pengeluaran_id,
                'merkmotor_id':merkmotor_id,
                'jenismotor_id':jenismotor_id,
                'status_rumah_id':status_rumah_id,
                'pendidikan_id':pendidikan_id,
                
                'no_wa': data_lead.get('no_wa'),
                'jabatan': data_lead.get('jabatan'),
                'suku': data_lead.get('suku'),
                'penanggung_jawab':data_lead.get('penanggung_jawab'),
                'sales_koordinator_id':sales_koordinator_id,
                'is_hc':data_lead.get('is_hc'),
                'diskon_hc':data_lead.get('diskon_hc'),
                'version_code':data_lead.get('version_code'),
                'version_name':data_lead.get('version_name'),
                'data_source':data_lead.get('data_source'),
            }

            lead_vals.update(vals_lead_other)

            if data_lead.get('atas_nama_stnk') == 'orang_lain':
                customer_stnk_id = False
                if data_lead.get('stnk_ktp'):
                    customer_stnk_id = request.env['res.partner'].sudo().search([
                        ('no_ktp','=',data_lead.get('stnk_ktp'))],limit=1).id

                    if not customer_stnk_id:
                        state_stnk_id = False
                        city_stnk_id = False
                        kecamatan_stnk_id = False
                        kecamatan_stnk = False
                        kelurahan_stnk_id = False
                        kelurahan_stnk = False

                        state_code_stnk = data_lead.get('state_code_stnk')
                        city_code_stnk = data_lead.get('city_code_stnk')
                        kec_code_stnk = data_lead.get('kec_code_stnk')
                        kel_code_stnk = data_lead.get('kel_code_stnk')

                        # Alamat STNK
                        if kel_code_stnk:
                            obj_kel_stnk = data_kelurahan.sudo().search([('code','=',kel_code_stnk)],limit=1)
                            if obj_kel_stnk:
                                kelurahan_stnk_id = obj_kel_stnk.id
                                kelurahan_stnk = obj_kel_stnk.name
                                kecamatan_stnk_id = obj_kel_stnk.kecamatan_id.id
                                kecamatan_stnk = obj_kel_stnk.kecamatan_id.name
                                city_stnk_id = obj_kel_stnk.kecamatan_id.city_id.id
                                state_stnk_id = obj_kel_stnk.kecamatan_id.city_id.state_id.id

                        if not kecamatan_stnk_id and kec_code_stnk:
                            obj_kec_stnk = data_kecamatan.sudo().search([('code','=',kec_code_stnk)],limit=1)
                            if obj_kec_stnk:
                                kecamatan_stnk_id = obj_kec_stnk.id
                                kecamatan_stnk = obj_kec_stnk.name
                                city_stnk_id = obj_kec_stnk.city_id.id
                                state_stnk_id = obj_kec_stnk.city_id.state_id.id

                        if not city_stnk_id and city_code_stnk:
                            obj_city_stnk = data_city.sudo().search([('code','=',city_code_stnk)],limit=1)
                            if obj_city_stnk:
                                city_stnk_id = obj_city_stnk.id
                                state_stnk_id = obj_city_stnk.state_id.id
                        
                        if not state_stnk_id and state_code_stnk:
                            state_stnk_id = data_provinsi.sudo().search([('code','=',state_code_stnk)],limit=1).id

                        customer_stnk_id = request.env['res.partner'].sudo().create({
                            'branch_id':branch_id,
                            'name':data_lead.get('stnk_name'),
                            'no_ktp':data_lead.get('stnk_ktp'),
                            'street':data_lead.get('street_stnk'),
                            'rt':data_lead.get('rt_stnk'),
                            'rw':data_lead.get('rw_stnk'),
                            'state_id':state_stnk_id,
                            'city_id':city_stnk_id,
                            'kecamatan_id':kecamatan_stnk_id,
                            'kecamatan':kecamatan_stnk or data_lead.get('kecamatan_stnk'),
                            'zip_id':kelurahan_stnk_id,
                            'kelurahan': kelurahan_stnk or data_lead.get('kelurahan_stnk'),
                            'mobile':data_lead.get('mobile_stnk'),
                            'customer':True,

                            'direct_customer':True,
                            'street_tab':data_lead.get('street_stnk'),
                            'rt_tab':data_lead.get('rt_stnk'),
                            'rw_tab':data_lead.get('rw_stnk'),
                            'state_tab_id':state_stnk_id,
                            'city_tab_id':city_stnk_id,
                            'kecamatan_tab_id':kecamatan_stnk_id,
                            'kecamatan_tab': kecamatan_stnk or data_lead.get('kecamatan_stnk'),
                            'zip_tab_id':kelurahan_stnk_id,
                            'kelurahan_tab':kelurahan_stnk or data_lead.get('kelurahan_stnk'),
                            'birthday':data_lead.get('birtdate_stnk')
                        }).id
                    lead_vals['customer_stnk_id'] = customer_stnk_id

            # Cek LEAD terlebih dahulu
            lead = request.env['teds.lead'].sudo().search([
                ('branch_id','=', branch_id), 
                ('no_ktp','=',data_lead.get('no_ktp')),
                ('spk_id.state','!=','cancelled'),
                ('product_id','=',product_id)],limit=1)
            if not lead:
                lead = request.env['teds.lead'].sudo().create(lead_vals)
                if is_allow_lead:
                    lead.action_deal()
                res_activity[data_lead['lead_id']] = lead.id

            remark_val = {
                'error':False,
                'data':{'id':data_lead['lead_id'],'name':lead.name}
            }
            
            # DATA ACTIVITY FOLLOWUP
            for act in activity:
                lead_id = res_activity.get(act['lead_id'])
                if lead_id:
                    stage_id = request.env['teds.lead.stage'].sudo().search([
                        ('name','ilike',act['stage'])],limit=1).id
                    stage_result_id = request.env['teds.master.result.lead.activity'].sudo().search([
                        ('name','ilike',act['result'])],limit=1).id
                    activities = request.env['teds.lead.activity'].sudo().create({
                        'lead_id':lead_id,
                        'name':stage_id,
                        'stage_result_id':stage_result_id,
                        'date':act['date'],
                        'remark':act['remark'],
                        'minat':act['minat'],
                    })
                                  
        return {'status':1,'message':remark_val}
