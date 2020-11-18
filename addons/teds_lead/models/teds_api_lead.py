from openerp import models, fields, api
from datetime import date,timedelta,datetime,date
from openerp.exceptions import Warning
import json
import requests

import logging
_logger = logging.getLogger(__name__)

class Lead(models.Model):
    _inherit = "teds.lead"

    b2b_status_spk_api = fields.Selection([('draft','Draft'),('error','Error'),('done','Done')],default='draft',index=True)
    b2b_remark_spk_api = fields.Char(string="Remark API status SPK")
    
    @api.multi
    def _get_values_lead_other(self,vals):
        data = {}
        return data

    @api.multi
    def api_create_lead(self,data):
        remark = []
        vals = data.get('leads')
        activity = data.get('activity')

        res_activity = {}
        tgl_now = date.today()
        
        data_provinsi = self.env['res.country.state']
        data_city = self.env['wtc.city']
        data_kelurahan = self.env['wtc.kelurahan']
        data_kecamatan = self.env['wtc.kecamatan']
        data_questionnaire = self.env['wtc.questionnaire']

        for val in vals:
            message = ''
            is_allow_lead = True
            branch_id = self.env['wtc.branch'].search([('code','=',val['branch_code'])],limit=1)
            if not branch_id:
                message += "Branch Code %s not found \n"%(val['branch_code'])
            is_allow_lead = branch_id.is_allow_lead
            branch_id = branch_id.id
                
                
            product = """
                SELECT pp.id as prod_id
                FROM product_product pp
                INNER JOIN product_template pt ON pt.id = pp.product_tmpl_id 
                LEFT JOIN product_attribute_value_product_product_rel rel ON rel.prod_id = pp.id
                LEFT JOIN product_attribute_value pav ON pav.id = rel.att_id 
                WHERE name_template = '%s' AND pav.code='%s'
            """ %(val['prod_code'],val['warna_code'])
            self._cr.execute(product)
            res = self._cr.fetchone()
            product_id = False
            if not res:
                message += "Product Code %s & Warna Code %s not found \n"%(val['prod_code'],val['warna_code'])
            else:    
                product_id = res[0]
            
            identification_id = val.get('identification_id')
            tunas_id = val['tunas_id']
            if not identification_id and not tunas_id:
                message += "Tunas ID or Identification ID sales required ! \n"
            
            emp_where = " WHERE hr.branch_id = %d AND job.sales_force IN ('salesman','sales_counter','sales_partner','sales_koordinator','soh')" %(branch_id)
            emp_where_ktp = ""
            if identification_id:
                emp_where_ktp += " OR hr.identification_id = '%s'" %(identification_id)
            if tunas_id:
                emp_where += " AND (hr.nip = '%s' OR code_honda = '%s' %s)" %(tunas_id,tunas_id,emp_where_ktp)
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
            self._cr.execute (emp_query)
            res_emp = self._cr.dictfetchall()
            if not res_emp:
                message += "Tunas ID %s or Identification ID sales %s not found \n"%(tunas_id,identification_id)
            else:
                user_id = res_emp[0].get('user_id')
                employee_id = res_emp[0].get('employee_id')            
                if not user_id:
                    message += "User ID pada Tunas ID %s or Identification ID sales %s not found \n"%(tunas_id,identification_id)
            
            sco_identification_id = val.get('sco_identification')
            sco_tunas_id = val.get('sco_tunas_id')
            sales_koordinator_id = False
            if sco_tunas_id:
                sco_where = " WHERE hr.branch_id = %d AND job.sales_force IN ('salesman','sales_counter','sales_partner','sales_koordinator','soh')" %(branch_id)
                sco_where_ktp = ""
                if sco_identification_id:
                    sco_where_ktp = " OR hr.identification_id = '%s'" %(sco_identification_id)
            
                if sco_tunas_id:
                    sco_where += " AND (hr.nip = '%s' OR code_honda = '%s' %s)" %(sco_tunas_id,sco_tunas_id,sco_where_ktp)
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
                self._cr.execute (sco_query)
                res_sco = self._cr.dictfetchall()
                if not res_sco:
                    message += "Tunas ID %s or Identification ID sales %s not found \n"%(sco_tunas_id,sco_identification_id)
                else:    
                    user_sco_id = res_sco[0].get('user_id')
                    sales_koordinator_id = res_sco[0].get('employee_id')            
                    if not user_sco_id:
                        message += "User ID pada Tunas ID %s or Identification ID sales kordinator %s not found \n"%(sco_tunas_id,sco_identification_id)
            
            # Function untuk penambahan values lead
            vals_lead_other = self._get_values_lead_other(val)
            # Error harus mengirimkan status error dan message
            if vals_lead_other.get('error'):
                message += vals_lead_other.get('message','Error Get Values Lead Other')
            
            remark_val = {}
            error = False
            if message:
                remark_val = {
                    'error':True,
                    'remark':{'id':val['lead_id'],'name':message}
                }
                remark.append(remark_val)
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

                kel_code = val.get('kel_code')
                kec_code = val.get('kec_code')
                city_code = val.get('city_code')
                state_code = val.get('state_code')

                state_code_domisili = val.get('state_code_domisili')
                city_code_domisili = val.get('city_code_domisili')
                kec_code_domisili = val.get('kec_code_domisili')
                kel_code_domisili = val.get('kel_code_domisili')

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
                if not val['is_sesuai_ktp']:
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
                gol_darah = False
                pekerjaan_id = False
                pengeluaran_id = False
                pendidikan_id = False
                merkmotor_id = False
                jenismotor_id = False
                penggunaan_id = False
                pengguna_id = False
                hobi = False
                status_hp_id = False
                status_rumah_id = False

                if val.get('status_hp'):
                    status_hp_id = data_questionnaire.sudo().search([
                        ('type','=','Status HP'),
                        ('value','=',val['status_hp'])],limit=1).id
                
                if val.get('status_rumah'):
                    status_rumah_id = data_questionnaire.sudo().search([
                        ('type','=','Status Rumah'),
                        ('value','=',val['status_rumah'])],limit=1).id
                
                if val.get('jk'):
                    jenis_kelamin_id = data_questionnaire.sudo().search([
                        ('type','=','JenisKelamin'),
                        ('value','=',val['jk'])],limit=1).id
                
                if val.get('agama'):
                    agama_id = data_questionnaire.sudo().search([
                        ('type','=','Agama'),
                        ('value','=',val['agama'])],limit=1).id
                if val.get('gol_darah'):
                    gol_darah = self.env['wtc.questionnaire'].sudo().search([
                        ('type','=','GolonganDarah'),
                        ('value','=',val['gol_darah'])],limit=1).id
                if val.get('pekerjaan'):
                    pekerjaan_id = data_questionnaire.sudo().search([
                        ('type','=','Pekerjaan'),
                        ('value','=',val['pekerjaan'])],limit=1).id
                
                if val.get('pengeluaran'):
                    pengeluaran_id = data_questionnaire.sudo().search([
                        ('type','=','Pengeluaran'),
                        ('value','=',val['pengeluaran'])],limit=1).id
                
                if val.get('pendidikan'):
                    pendidikan_id = data_questionnaire.sudo().search([
                        ('type','=','Pendidikan'),
                        ('value','=',val['pendidikan'])],limit=1).id
                
                if val.get('merkmotor'):
                    merkmotor_id = data_questionnaire.sudo().search([
                        ('type','=','MerkMotor'),
                        ('value','=',val['merkmotor'])],limit=1).id
                
                if val.get('jenismotor'):
                    jenismotor_id = data_questionnaire.sudo().search([
                        ('type','=','JenisMotor'),
                        ('value','=',val['jenismotor'])],limit=1).id
                
                if val.get('penggunaan'):
                    penggunaan_id = data_questionnaire.sudo().search([
                        ('type','=','Penggunaan'),
                        ('value','=',val['penggunaan'])],limit=1).id
                
                if val.get('pengguna'):
                    pengguna_id = data_questionnaire.sudo().search([
                        ('type','=','Pengguna'),
                        ('value','=',val['pengguna'])],limit=1).id
                if val.get('hobi'):
                    hobi = data_questionnaire.sudo().search([
                        ('type','=','Hobi'),
                        ('value','=',val['hobi'])],limit=1).id
                
                finco_id = False
                if val.get('finco',False):
                    finco_id = self.env['res.partner'].sudo().search([
                        ('ahm_code','=',val['finco']),
                        ('finance_company','=',True)],limit=1).id

                #Mapping Sumber Penjualan#
                transaction_id = val.get('transaction_id')
                jaringan_penjualan = val.get('jaringan_penjualan',False)
                sales_source_location_id = val.get('stock_location_id')
                act_type = val.get('act_type','WI')
                
                if jaringan_penjualan == 'showroom':
                    jaringan_penjualan = 'Showroom'
                    sales_source_location_id = False
                elif jaringan_penjualan == 'pos':
                    jaringan_penjualan = 'POS'
                else: 
                    jaringan_penjualan = 'Showroom'

                sumber_penjualan_id = self.env['teds.act.type.sumber.penjualan'].sudo().search([('code','=',act_type)],limit=1).id
                activity_plan_id = False
                is_btl = False
                titik_keramaian_id = False

                if transaction_id:
                    activity_plan_obj = self.env['teds.sales.plan.activity.line'].sudo().browse(transaction_id)
                    if activity_plan_obj:
                        jaringan_penjualan = activity_plan_obj.jaringan_penjualan
                        sumber_penjualan_id = activity_plan_obj.act_type_id.id
                        is_btl = activity_plan_obj.act_type_id.is_btl
                        activity_plan_id = transaction_id
                        titik_keramaian_id = activity_plan_obj.titik_keramaian_id.id



                lead_vals = {
                    'branch_id': branch_id, 
                    'name_customer':val.get('name_customer'),
                    'minat': val.get('minat'), 
                    'product_id':product_id,
                    'no_ktp': val.get('no_ktp'), 
                    'mobile': val.get('mobile'), 
                    'kontak_tambahan': val.get('kontak_tambahan'),
                    'employee_id':employee_id,
                    'no_refrence':val.get('no_refrence'),
                    
                    # Data Jaringan Penjualan
                    'jaringan_penjualan':jaringan_penjualan,
                    'sumber_penjualan_id':sumber_penjualan_id,
                    'is_btl':is_btl,
                    'activity_plan_id':activity_plan_id,
                    'titik_keramaian_id':titik_keramaian_id,
                    'sales_source_location_id':sales_source_location_id,
                    # ---------------------------------------

                    'street': val.get('street'), 
                    'rt': val.get('rt'), 
                    'rw': val.get('rw'), 
                    'state_id':state_id,
                    'kabupaten_id':kabupaten_id,
                    'kecamatan_id':kecamatan_id,
                    'kecamatan': val.get('kecamatan'),
                    'zip_code_id':zip_code_id, 
                    'kelurahan': kelurahan, 
                    'kode_pos': val.get('kode_pos'),

                    'is_sesuai_ktp': val.get('is_sesuai_ktp'), 
                    'street_domisili': val.get('street_domisili'),
                    'rt_domisili':val.get('rt_domisili'),
                    'rw_domisili':val.get('rw_domisili'),
                    'state_domisili_id':state_domisili_id,
                    'kabupaten_domisili_id':kabupaten_domisili_id,
                    'kecamatan_domisili_id':kecamatan_domisili_id,
                    'zip_code_domisili_id':zip_code_domisili_id,
                    'kecamatan_domisili': val.get('kecamatan_domisili'),
                    'kelurahan_domisili': val.get('kelurahan_domisili'),
                    'kode_pos_domisili': val.get('kode_pos_domisili'),
                    
                    'tempat_tgl_lahir': val.get('tempat_tgl_lahir'), 
                    'tgl_lahir': val.get('tgl_lahir'),
                    'jenis_kelamin_id':jenis_kelamin_id,
                    'no_kk': val.get('no_kk'), 
                    'agama_id':agama_id,
                    'gol_darah':gol_darah,
                    'pekerjaan_id':pekerjaan_id,
                    'motor_sekarang': val.get('motor_sekarang'),

                    'payment_type': val.get('payment_type'),
                    'finco_id':finco_id,
                    'uang_muka': val.get('uang_muka'),
                    'tgl_uang_muka': val.get('tgl_uang_muka'), 
                    'date_jatuh_tempo': val.get('date_jatuh_tempo'), 
                    'tenor': val.get('tenor'), 
                    'cicilan': val.get('cicilan'), 
                    'otr': val.get('otr'),
                    'diskon': val.get('diskon'), 
                    'atas_nama_stnk': val.get('atas_nama_stnk'),
                    'email': val.get('email'), 
                    'facebook': val.get('facebook'), 
                    'instagram': val.get('instagram'), 
                    'twitter': val.get('twitter'), 
                    'youtube': val.get('youtube'), 
                    'kode_customer': val.get('kode_customer') or 'I',
                    'status_hp_id': status_hp_id,
                    'penggunaan_id': penggunaan_id,
                    'pengguna_id': pengguna_id,
                    'hobi': hobi,
                    
                    'pin_bbm': val.get('pin_bbm'),
                    'no_wa': val.get('no_wa'),
                    'jabatan': val.get('jabatan'),
                    'suku': val.get('suku'),
                    'penanggung_jawab':val.get('penanggung_jawab'),
                    'pengeluaran_id':pengeluaran_id,
                    'merkmotor_id':merkmotor_id,
                    'jenismotor_id':jenismotor_id,
                    'status_rumah_id':status_rumah_id,
                    'pendidikan_id':pendidikan_id,
                    'sales_koordinator_id':sales_koordinator_id,
                    'is_hc':val.get('is_hc'),
                    'diskon_hc':val.get('diskon_hc'),
                    'version_code':val.get('version_code'),
                    'version_name':val.get('version_name'),
                    'data_source':val.get('data_source'),
                }

                lead_vals.update(vals_lead_other)
                
                if val['atas_nama_stnk'] == 'orang_lain':
                    customer_stnk_id = False
                    if val.get('stnk_ktp'):
                        customer_stnk_id = self.env['res.partner'].sudo().search([
                            ('no_ktp','=',val['stnk_ktp'])],limit=1).id
                    if not customer_stnk_id:
                        state_stnk_id = False
                        city_stnk_id = False
                        kecamatan_stnk_id = False
                        kecamatan_stnk = False
                        kelurahan_stnk_id = False
                        kelurahan_stnk = False

                        state_code_stnk = val.get('state_code_stnk')
                        city_code_stnk = val.get('city_code_stnk')
                        kec_code_stnk = val.get('kec_code_stnk')
                        kel_code_stnk = val.get('kel_code_stnk')

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

                        customer_stnk_id = self.env['res.partner'].sudo().create({
                            'branch_id':branch_id,
                            'name':val['stnk_name'],
                            'no_ktp':val['stnk_ktp'],
                            'street':val['street_stnk'],
                            'rt':val['rt_stnk'],
                            'rw':val['rw_stnk'],
                            'state_id':state_stnk_id,
                            'city_id':city_stnk_id,
                            'kecamatan_id':kecamatan_stnk_id,
                            'kecamatan':kecamatan_stnk or val['kecamatan_stnk'],
                            'zip_id':kelurahan_stnk_id,
                            'kelurahan': kelurahan_stnk or val['kelurahan_stnk'],
                            'mobile':val['mobile_stnk'],
                            'customer':True,
                            'direct_customer':True,
                            'street_tab':val['street_stnk'],
                            'rt_tab':val['rt_stnk'],
                            'rw_tab':val['rw_stnk'],
                            'state_tab_id':state_stnk_id,
                            'city_tab_id':city_stnk_id,
                            'kecamatan_tab_id':kecamatan_stnk_id,
                            'kecamatan_tab': kecamatan_stnk or val['kecamatan_stnk'],
                            'zip_tab_id':kelurahan_stnk_id,
                            'kelurahan_tab':kelurahan_stnk or val['kelurahan_stnk'],
                            'birthday':val['birtdate_stnk']
                        }).id
                    lead_vals['customer_stnk_id'] = customer_stnk_id

                # Cek LEAD terlebih dahulu
                lead = self.search([
                    ('branch_id','=', branch_id), 
                    ('name_customer','=',val['name_customer']),
                    ('product_id','=',product_id),
                    ('no_ktp','=',val['no_ktp']), 
                    ('employee_id','=',employee_id),
                    ('date','=',str(tgl_now))],limit=1)
                if not lead:
                    lead = self.create(lead_vals)
                    if is_allow_lead:
                        lead.action_deal()
                    res_activity[val['lead_id']] = lead.id

                remark_val = {
                    'error':False,
                    'remark':{'id':val['lead_id'],'name':lead.name}
                }
                remark.append(remark_val)


        for act in activity:
            lead_id = res_activity.get(act['lead_id'])
            if lead_id:
                stage_id = self.env['teds.lead.stage'].search([('name','ilike',act['stage'])],limit=1).id
                stage_result_id = self.env['teds.master.result.lead.activity'].search([('name','ilike',act['result'])],limit=1).id
                activities = self.env['teds.lead.activity'].create({
                    'lead_id':lead_id,
                    'name':stage_id,
                    'stage_result_id':stage_result_id,
                    'date':act['date'],
                    'remark':act['remark'],
                    'minat':act['minat'],
                })
        return {
            'result': remark,
        }

    # @api.multi
    # def action_deal(self):
    #     super(Lead, self).action_deal()
    #     if self.no_refrence:
    #         try:
    #             self.send_lead_status_spk()
    #             self.b2b_status_spk_api = 'done'
    #         except:
    #             self.b2b_status_spk_api = 'error'

    @api.multi
    def send_lead_status_spk(self):
        config = self.env['teds.api.configuration'].suspend_security().search([('is_super_user','=',True)],limit=1)
        if not config:
            log_description = 'Configuration Rest API belum di setting !'
            raise Warning(log_description)

        base_url = "%s:%s" %(config.host,config.port)
        if not config.token_ids:
            get_token = config.suspend_security().action_generate_token()
            if not get_token:
                log_description = 'Failed Get Token Rest API!'
                raise Warning(log_description)
        token = config.token_ids[0].token
                
        # HIT KE HOKI API
        url = "%s/api/b2b/portal/v1/lead/teds_state_spk" %(base_url)
        headers = {"access_token":token}
        body = {'data':str([{
            'transaction_id':self.id,
            'name':self.name,
            'no_refrence':self.no_refrence,
            'spk_name':self.spk_id.name,
        }])}
        request_data = requests.post(url, headers=headers, data=body)
        request_status_code = request_data.status_code
        request_content = json.loads(request_data.content)

        if request_status_code == 200:
            # Olah Data Responses
            responses_data = request_content.get('data')
            for responses in responses_data:
                error = responses.get('error')
                error_info = responses.get('info')
                log_description = "%s - %s" %(error,error_info)

                if error:
                    raise Warning(log_description)                    
                else:
                    self.b2b_status_api = 'done'
        else:
            raise Warning("gagal update status")
    
    @api.multi
    def multi_send_lead_status_spk(self,code):
        teds_api_log = self.env['teds.api.log']
        log_name = 'Lead SPk'
        log_description = 'Send Status lead SPK'
        log_module = 'Lead'
        log_model = 'teds.lead'
        log_transaction = False
        log_origin = ''
        try:
            query = """
                SELECT
                    lead.id as transaction_id
                    ,lead.name as name
                    ,lead.no_refrence as no_refrence
                    ,spk.name as spk_name
                FROM teds_lead as lead 
                    JOIN dealer_spk as spk on spk.id = lead.spk_id
                    JOIN wtc_branch branch ON branch.id = lead.branch_id
                WHERE lead.b2b_status_spk_api in ('draft','error')
                    AND lead.no_refrence is not null
                    AND branch.code in %s
                LIMIT 20
            """ %str(tuple(code)).replace(',)', ')')

            self.env.cr.execute(query)
            ress = self.env.cr.dictfetchall()
            if ress:
                # Data API
                config = self.env['teds.api.configuration'].suspend_security().search([('is_super_user','=',True)],limit=1)
                if not config:
                    log_description = 'Configuration Rest API belum di setting !'
                    _logger.warning(log_description)
                    # Create Log API
                    teds_api_log.suspend_security().create_log_eror(log_name,log_description,log_module,log_model,log_transaction,log_origin)
                    return False

                base_url = "%s:%s" %(config.host,config.port)
                if not config.token_ids:
                    get_token = config.suspend_security().action_generate_token()
                    if not get_token:
                        log_description = 'Failed Get Token Rest API!'
                        _logger.warning(log_description)
                        # Create Log API
                        teds_api_log.suspend_security().create_log_eror(log_name,log_description,log_module,log_model,log_transaction,log_origin)
                        return False
                token = config.token_ids[0].token
                        
                # HIT KE HOKI API
                url = "%s/api/b2b/portal/v1/lead/teds_state_spk" %(base_url)
                headers = {"access_token":token}
                body = {'data':str(ress)}
                request_data = requests.post(url, headers=headers, data=body)
                request_status_code = request_data.status_code
                request_content = json.loads(request_data.content)

                if request_status_code == 200:
                    # Olah Data Responses
                    responses_data = request_content.get('data')
                    for responses in responses_data:
                        error = responses.get('error')
                        error_info = responses.get('info')
                        log_transaction =  responses.get('transaction_id')
                        log_description = "%s - %s" %(error,error_info)

                        if error:
                            update = """
                                UPDATE
                                teds_lead
                                SET b2b_status_spk_api = 'error'
                                WHERE id = %d
                            """ %log_transaction
                            self._cr.execute(update)
                            teds_api_log.suspend_security().create_log_eror(log_name,log_description,log_module,log_model,log_transaction,log_origin)
                        else:
                            update = """
                                UPDATE
                                teds_lead
                                SET b2b_status_spk_api = 'done'
                                WHERE id = %d
                            """ %log_transaction
                            self._cr.execute(update)
                            teds_api_log.suspend_security().clear_log_eror(log_transaction,log_origin,log_model)

                else:
                    error = request_content.get('error')
                    info =  request_content.get('error')
                    log_description = "%s %s" %(error,info)
                    teds_api_log.suspend_security().create_log_eror(log_name,log_description,log_module,log_model,log_transaction,log_origin)

        except Exception as err:
            log_description = "Exception %s" %(err)
            _logger.warning(log_description)
            # Create Log API
            teds_api_log.suspend_security().create_log_eror(log_name,log_description,log_module,log_model,log_transaction,log_origin)
