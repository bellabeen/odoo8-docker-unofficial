from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning
from datetime import date,timedelta,datetime

class Lead(models.Model):
    _name = "teds.lead"
    _description = "Lead"
    _order = 'date desc'

    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()
    
    def _get_default_datetime(self):
        return self.env['wtc.branch'].get_default_datetime_model()

    def _get_default_branch(self):
        branch_ids = False
        branch_ids = self.env.user.branch_ids
        if branch_ids and len(branch_ids) == 1 :
            return branch_ids[0].id
        return False

    @api.multi
    @api.depends('lead_activity_ids')
    def _compute_follow(self):
        for lead in self:
            lead.follow_ke = len(lead.lead_activity_ids)

    name = fields.Char('Name',index=True)
    no_refrence = fields.Char('No Refrence',index=True)
    name_customer = fields.Char('Nama Customer')
    branch_id = fields.Many2one('wtc.branch', string='Branch',default=_get_default_branch)
    minat = fields.Selection([
        ('cold', 'Cold'),
        ('medium', 'Medium'),
        ('hot', 'Hot')], string='Minat', default='cold')
    no_ktp = fields.Char('Nomor KTP')
    no_kk = fields.Char('Nomor KK')
    date = fields.Date('Date',readonly=True,default=_get_default_date)
    state = fields.Selection([
        ('open', 'Open'),
        ('dealt', 'Dealt'),
        ('cancel','Cancelled')
        ],default='open', string='State')
    mobile = fields.Char('Nomor HP',required=True)
    no_wa = fields.Char('No WhatsApp')
    kontak_tambahan = fields.Char('No HP Tambahan')
    tempat_tgl_lahir = fields.Char('Tempat')
    tgl_lahir = fields.Date('Tanggal Lahir')
    kode_customer = fields.Selection([('G','Group Customer'),('I','Individual Customer(Regular)'),('J','Individual Customer (Joint Promo)'),('C','Individual Customer (Kolektif)')], string='Kode Customer')
    product_id = fields.Many2one('product.product','Product')
    date_jatuh_tempo = fields.Selection([
        ('1','1'),('2','2'),('3','3'),('4','4'),('5','5'),('6','6'),('7','7'),('8','8'),('9','9'),('10','10'),
        ('11','11'),('12','12'),('13','13'),('14','14'),('15','15'),('16','16'),('17','17'),('18','18'),('19','19'),('20','20'),
        ('21','21'),('22','22'),('23','23'),('24','24'),('25','25'),('26','26'),('27','27'),('28','28'),('29','29'),('30','30'),('31','31')
        ],string='Request Tgl Jatuh Tempo')
    employee_id = fields.Many2one('hr.employee',string='Sales Person')
    customer_id = fields.Many2one('res.partner','Customer')
    suku = fields.Char('Suku')
    jabatan = fields.Char('Jabatan')
    penanggung_jawab = fields.Char('Penanggung Jawab')
    
    # Sumber Penjualan
    jaringan_penjualan = fields.Selection([
        ('Showroom','Showroom'),
        ('POS','POS'),
        ('Chanel/Mediator','Chanel/Mediator')],string="Jaringan Penjualan")
    sumber_penjualan_id = fields.Many2one('teds.act.type.sumber.penjualan','Sumber Penjualan')
    is_btl = fields.Boolean(string="Is BTL ?",readonly=True)
    activity_plan_id = fields.Many2one('teds.sales.plan.activity.line','Activity',domain=[('id','=',0)])
    titik_keramaian_id = fields.Many2one('titik.keramaian','Titik Keramaian',readonly=True)
    sales_source_location_id = fields.Many2one('stock.location', string='Sales Source Location')
    motor_sekarang = fields.Char('Motor Sekarang')
    
    # Pembayaran
    payment_type = fields.Selection([
        ('1', 'Cash'),
        ('2', 'Credit')], string='Jenis Pembelian')
    otr = fields.Float('OTR (Rp)',digits=(12,0))
    otr_show = fields.Float('OTR (Rp)')#,compute='_compute_otr',digits=(12,0))
    diskon = fields.Float('Diskon',default=0.00,digits=(12,0))
    atas_nama_stnk = fields.Selection([
        ('sendiri','Sendiri'),
        ('orang_lain','Orang lain')],string='Atas Nama STNK')
    customer_stnk_id = fields.Many2one('res.partner','Customer STNK')
    finco_id = fields.Many2one('res.partner','Finco',domain=[('finance_company','=',True)])
    uang_muka = fields.Float(string='Uang Muka / DP (Rp)',digits=(12,0))
    tgl_uang_muka = fields.Date('Tgl Terima DP',default=_get_default_date)
    tenor = fields.Integer('Tenor')
    cicilan = fields.Float('Cicilan (Rp)',digits=(7,0))
    

    # Questionnaire
    jenis_kelamin_id = fields.Many2one('wtc.questionnaire','Jenis Kelamin',domain=[('type','=','JenisKelamin')])
    agama_id = fields.Many2one('wtc.questionnaire','Agama',domain=[('type','=','Agama')])
    gol_darah = fields.Many2one('wtc.questionnaire','Golongan Darah',domain=[('type','=','GolonganDarah')])
    pendidikan_id = fields.Many2one('wtc.questionnaire','Pendidikan',domain=[('type','=','Pendidikan')])
    pekerjaan_id = fields.Many2one('wtc.questionnaire','Pekerjaan',domain=[('type','=','Pekerjaan')])
    pengeluaran_id = fields.Many2one('wtc.questionnaire','Pengeluaran',domain=[('type','=','Pengeluaran')])
    merkmotor_id = fields.Many2one('wtc.questionnaire','Merk Motor',domain=[('type','=','MerkMotor')])
    jenismotor_id = fields.Many2one('wtc.questionnaire','Jenis Motor',domain=[('type','=','JenisMotor')])
    penggunaan_id = fields.Many2one('wtc.questionnaire','Penggunaan',domain=[('type','=','Penggunaan')])
    pengguna_id = fields.Many2one('wtc.questionnaire','Pengguna',domain=[('type','=','Pengguna')])
    hobi = fields.Many2one('wtc.questionnaire','Hobi',domain=[('type','=','Hobi')])
    status_hp_id = fields.Many2one('wtc.questionnaire','Status HP',domain=[('type','=','Status HP')])
    status_rumah_id = fields.Many2one('wtc.questionnaire','Status Rumah',domain=[('type','=','Status Rumah')])
    sales_koordinator_id = fields.Many2one('hr.employee','Sales Koordinator')
    is_hc = fields.Boolean('Is HC ?')
    diskon_hc = fields.Float('Diskon HC')    
    
    # Media Sosial
    email = fields.Char('Email')
    facebook = fields.Char(string='Facebook')
    instagram = fields.Char(string='Instagram')
    twitter = fields.Char(string='Twitter')
    youtube = fields.Char(string='Youtube')

    
    # Alamat
    street = fields.Char(string='Address')
    rt = fields.Char(string='RT',size=3)
    rw = fields.Char(string='RW',size=3)
    state_id = fields.Many2one('res.country.state',string='Province')
    kabupaten_id = fields.Many2one('wtc.city','Kabupaten',domain="[('state_id','=',state_id)]")
    kecamatan_id = fields.Many2one('wtc.kecamatan','Kecamatan',domain="[('city_id','=',kabupaten_id)]")
    kecamatan = fields.Char(string="Kecamatan") 
    zip_code_id = fields.Many2one('wtc.kelurahan',string='Kelurahan',domain="[('kecamatan_id','=',kecamatan_id)]")
    kelurahan = fields.Char(string="Kelurahan")
    kode_pos = fields.Char(string="Kode Pos")

    is_sesuai_ktp = fields.Boolean('Sesuai KTP ?',default=True)    
    street_domisili = fields.Char(string='Address')
    rt_domisili = fields.Char(string='RT',size=3)
    rw_domisili = fields.Char(string='RW',size=3)
    state_domisili_id = fields.Many2one('res.country.state',string='Province')
    kabupaten_domisili_id = fields.Many2one('wtc.city','Kabupaten',domain="[('state_id','=',state_domisili_id)]")
    kecamatan_domisili_id = fields.Many2one('wtc.kecamatan','Kecamatan',domain="[('city_id','=',kabupaten_domisili_id)]")
    kecamatan_domisili = fields.Char(string="Kecamatan") 
    zip_code_domisili_id = fields.Many2one('wtc.kelurahan',string='Kelurahan',domain="[('kecamatan_id','=',kecamatan_domisili_id)]")
    kelurahan_domisili = fields.Char(string="Kelurahan")
    kode_pos_domisili = fields.Char(string="Kode Pos")

    follow_ke = fields.Integer(string="Follow Up Ke",compute='_compute_follow', store=True)
    next_activity_id = fields.Many2one('teds.lead.activity',string="Next Activity")
    lead_activity_ids = fields.One2many('teds.lead.activity','lead_id')

    deal_date = fields.Datetime('Dealt on',readonly="1")
    deal_uid = fields.Many2one('res.users','Dealt by',readonly="1")
    spk_id = fields.Many2one('dealer.spk','SPK')
    
    version_code = fields.Char('version Code')
    version_name = fields.Char('version Name')
    data_source = fields.Selection([
        ('web','Web'),
        ('apps','Apps'),
        ('dgi','DGI')
        ],'Data Source',default='web')

    @api.model
    def create(self,vals):
        vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'BT')
        if vals.get('is_sesuai_ktp'):
            if vals['is_sesuai_ktp'] == True:
                vals['street_domisili'] = vals.get('street')
                vals['rt_domisili'] = vals.get('rt')
                vals['rw_domisili'] = vals.get('rw')
                vals['state_domisili_id'] = vals.get('state_id')
                vals['kabupaten_domisili_id'] = vals.get('kabupaten_id')
                vals['kecamatan_domisili_id'] = vals.get('kecamatan_id')
                vals['kecamatan_domisili'] = vals.get('kecamatan')
                vals['zip_code_domisili_id'] = vals.get('zip_code_id')
                vals['kelurahan_domisili'] = vals.get('kelurahan')
                vals['kode_pos_domisili'] = vals.get('kode_pos')
        create = super(Lead,self).create(vals)
        return create

    @api.onchange('sumber_penjualan_id')
    def onchange_is_btl(self):
        if self.sumber_penjualan_id:
            self.is_btl = self.sumber_penjualan_id.is_btl
    
    @api.onchange('payment_type')
    def onchange_payment_type(self):
        self.finco_id = False
        self.uang_muka = False
        self.cicilan = False
        self.tenor = False
        self.date_jatuh_tempo = False

    @api.constrains('no_ktp')
    def cek_ktp(self):
        self.ensure_one()
        if self.no_ktp:
            if not self.no_ktp.isdigit() or len(self.no_ktp) != 16:
                raise Warning('Perhatian ! \n Nomor KTP harus angka dan 16 digit.')

    # @api.constrains('mobile')
    # def cek_nomor(self):
    #     self.ensure_one()
    #     if self.mobile:
    #         if not self.mobile.isdigit() or len(self.mobile) < 5 :   
    #             raise Warning('Perhatian! \n Nomor Telepon harus angka dan minimal 5 digit.')
    
    @api.constrains('kontak_tambahan')
    def cek_kontak_tambahan(self):
        self.ensure_one()
        if self.kontak_tambahan:
            if not self.kontak_tambahan.isdigit() or len(self.kontak_tambahan) < 5 :   
                raise Warning('Perhatian! \n Nomor Telepon tambahan harus angka dan minimal 5 digit.')

    @api.constrains('tgl_lahir')
    def cek_tgl_lahir(self):
        if self.tgl_lahir :
            tgl_lahir = datetime.strptime(self.tgl_lahir, '%Y-%m-%d')
            today = datetime.now()
            if tgl_lahir > today :
                raise Warning('Maaf, harap isi tanggal lahir dengan benar !')

    @api.onchange('atas_nama_stnk')
    def onchange_atas_nama(self):
        self.customer_stnk_id = False

    @api.onchange('street','is_sesuai_ktp')
    def _onchange_street(self):
        if self.street and self.is_sesuai_ktp:
            self.street_domisili = self.street
    
    @api.onchange('rt','is_sesuai_ktp')
    def _onchange_rt(self):
        if self.rt and self.is_sesuai_ktp:
            self.rt_domisili = self.rt
    
    @api.onchange('rw','is_sesuai_ktp')
    def _onchange_rw(self):
        if self.rw and self.is_sesuai_ktp:
            self.rw_domisili = self.rw

    @api.onchange('state_id')
    def _onchange_stateId(self):
        self.kabupaten_id = False
        self.kecamatan_id = False
        self.zip_code_id = False
        self.kecamatan = False
        self.kelurahan = False
        if self.is_sesuai_ktp:
            self.kabupaten_domisili_id = False

        if self.is_sesuai_ktp and self.state_id:
            self.state_domisili_id = self.state_id.id
           
    @api.onchange('kabupaten_id')
    def _onchange_kapubatenId(self):
        self.kecamatan_id = False
        self.zip_code_id = False
        self.kecamatan = False
        self.kelurahan = False
        if self.is_sesuai_ktp:
            self.kecamatan_domisili_id = False

        if self.is_sesuai_ktp and self.kabupaten_id:
            self.kabupaten_domisili_id = self.kabupaten_id.id

    @api.onchange('kecamatan_id')
    def _onchange_kecamatanId(self):
        self.zip_code_id = False
        self.kecamatan = False
        self.kelurahan = False
        if self.is_sesuai_ktp:
            self.zip_code_domisili_id = False
            self.kelurahan_domisili = False

        if self.kecamatan_id:
            self.kecamatan = self.kecamatan_id.name
            if self.is_sesuai_ktp:
                self.kecamatan_domisili_id = self.kecamatan_id.id
                self.kecamatan_domisili = self.kecamatan

    @api.onchange('zip_code_id')
    def _onchange_kelurahanId(self):
        self.kelurahan = False
        if self.zip_code_id:
            self.kelurahan = self.zip_code_id.name
            self.kode_pos = self.zip_code_id.zip
            if self.is_sesuai_ktp:
                self.zip_code_domisili_id = self.zip_code_id.id
                self.kelurahan_domisili = self.kelurahan
                self.kode_pos_domisili = self.kode_pos
    
    @api.onchange('state_domisili_id')
    def _onchange_stateDomisiliId(self):
        if (self.state_domisili_id != self.state_id) and self.is_sesuai_ktp:
            self.is_sesuai_ktp = False
        if not self.is_sesuai_ktp:
            self.kabupaten_domisili_id = False
            self.kecamatan_domisili_id = False
            self.zip_code_domisili_id = False
            self.kecamatan_domisili = False
            self.kelurahan_domisili = False
           
    @api.onchange('kabupaten_domisili_id')
    def _onchange_kapubatenDomisiliId(self):
        if (self.kabupaten_domisili_id != self.kabupaten_id) and self.is_sesuai_ktp:
            self.is_sesuai_ktp = False
        if not self.is_sesuai_ktp:
            self.kecamatan_domisili_id = False
            self.zip_code_domisili_id = False
            self.kecamatan_domisili = False
            self.kelurahan_domisili = False

    @api.onchange('kecamatan_domisili_id')
    def _onchange_kecamatanDomisiliId(self):
        if (self.kecamatan_domisili_id != self.kecamatan_id) and self.is_sesuai_ktp:
            self.is_sesuai_ktp = False
        if not self.is_sesuai_ktp:
            self.kecamatan_domisili = False
            self.zip_code_domisili_id = False

        if not self.is_sesuai_ktp and self.kecamatan_domisili_id:
            self.kecamatan_domisili = self.kecamatan_domisili_id.name

    @api.onchange('zip_code_domisili_id')
    def _onchange_kelurahanDomisiliId(self):
        if (self.zip_code_domisili_id != self.zip_code_id) and self.is_sesuai_ktp:
            self.is_sesuai_ktp = False
        if not self.is_sesuai_ktp:
            self.kelurahan_domisili = False
            self.kode_pos_domisili = False
        if not self.is_sesuai_ktp and self.zip_code_domisili_id:
            self.kelurahan_domisili = self.zip_code_domisili_id.name
            self.kode_pos_domisili = self.zip_code_domisili_id.zip

    @api.onchange('is_sesuai_ktp')
    def onchange_sesuai_ktp(self):
        self.street_domisili = False
        self.rt_domisili = False
        self.rw_domisili = False
        self.state_domisili_id = False
        self.kabupaten_domisili_id = False
        self.kecamatan_domisili_id = False
        self.kecamatan_domisili = False
        self.zip_code_domisili_id = False
        self.kelurahan_domisili = False
        self.kode_pos_domisili = False
        if self.is_sesuai_ktp:
            self.street_domisili = self.street
            self.rt_domisili = self.rt
            self.rw_domisili = self.rw
            self.state_domisili_id = self.state_id.id
            self.kabupaten_domisili_id = self.kabupaten_id.id 
            self.kecamatan_domisili_id = self.kecamatan_id.id
            self.kecamatan_domisili = self.kecamatan
            self.zip_code_domisili_id = self.zip_code_id.id
            self.kelurahan_domisili = self.kelurahan
            self.kode_pos_domisili = self.kode_pos

    @api.multi
    def action_activity(self):
        self.ensure_one()

        form1_id = self.env.ref('teds_lead.view_teds_lead_activity_first_view_form').id
        form2_id = self.env.ref('teds_lead.view_teds_lead_activity_second_form').id

        if not self.next_activity_id:
            return {
                'name': ('Next activity'),
                'res_model': 'teds.lead.activity',
                'context': {
                    'default_lead_id': self.id,
                },
                'type': 'ir.actions.act_window',
                'view_id': False,
                'views': [(form1_id, 'form')],
                'view_mode': 'form',
                'target': 'new',
                'view_type': 'form',
                'res_id': False
            }
        if self.next_activity_id:
            res_id = self.next_activity_id.id 
            for record in self.lead_activity_ids:
                if record.stage_result_id or record.minat:
                    continue
                if (not record.stage_result_id) or (not record.minat):
                    return {
                        'type': 'ir.actions.act_window',
                        'name': ('Activity'),
                        'view_type': 'form',
                        'view_mode': 'tree,form',
                        'res_model': 'teds.lead.activity',
                        'context':{'active_id':self.id},
                        'res_id': record.id,
                        'views': [(form2_id, 'form')],
                        'target':'new'
                    }
                else:
                    return {
                        'type': 'ir.actions.act_window',
                        'name': ('Activity'),
                        'view_type': 'form',
                        'view_mode': 'tree,form',
                        'res_model': 'teds.lead.activity',
                        'context':{'active_id':self.id},
                        'res_id': res_id,
                        'views': [(form2_id, 'form')],
                        'target':'new'
                    }
            return {
                'name': ('Next activity'),
                'res_model': 'teds.lead.activity',
                'context': {
                    'default_lead_id': self.id,
                },
                'type': 'ir.actions.act_window',
                'view_id': False,
                'views': [(form1_id, 'form')],
                'view_mode': 'form',
                'target': 'new',
                'view_type': 'form',
                'res_id': False
            }

    # Data untuk menampung values spk other selain dari defaul model ini
    @api.multi
    def _get_spk_vals_other(self):
        data = {}
        return data


    @api.multi
    def action_deal(self):
        # cek partner
        if not self.no_ktp:
            raise Warning('No KTP harus diisi untuk proses deal !')
        jenis_kelamin = False
        religion = False

        if self.jenis_kelamin_id:
            if self.jenis_kelamin_id.value == '1':
                jenis_kelamin = 'lakilaki'
            else:
                jenis_kelamin = 'perempuan'
        
        if self.agama_id:
            if self.agama_id.value == '1':
                religion = 'Islam'
            elif self.agama_id.value == '2':
                religion = 'Kristen'
            elif self.agama_id.value == '3':
                religion = 'Katholik'
            elif self.agama_id.value == '4':
                religion = 'Hindu'
            elif self.agama_id.value == '5':
                religion = 'Budha'

        vals_partner = {
            'branch_id':self.branch_id.id,
            'name':self.name_customer,
            'no_ktp':self.no_ktp,
            'birthday':self.tgl_lahir,
            'mobile':self.mobile,
            'gender':jenis_kelamin,
            'street':self.street,
            'rt':self.rt,
            'rw':self.rw,
            'state_id':self.state_id.id,
            'city_id':self.kabupaten_id.id,
            'kecamatan_id':self.kecamatan_id.id,
            'kecamatan':self.kecamatan,
            'zip_id':self.zip_code_id.id,
            'kelurahan':self.kelurahan,
            'email':self.email,
            'religion':religion,
            'user_id':self.employee_id.user_id.id,
            'customer':True,
            'no_kk':self.no_kk,
            'direct_customer': True,
            'street_tab':self.street,
            'rt_tab':self.rt,
            'rw_tab':self.rw,
            'state_tab_id':self.state_id.id,
            'city_tab_id':self.kabupaten_id.id,
            'kecamatan_tab_id':self.kecamatan_id.id,
            'kecamatan_tab':self.kecamatan,
            'zip_tab_id':self.zip_code_id.id,
            'kelurahan_tab':self.kelurahan,

        }
        customer_id = self.env['res.partner'].search([
            ('no_ktp','=',self.no_ktp)],limit=1)
        
        if not customer_id:
            customer_id = self.env['res.partner'].create(vals_partner)
        else:
            customer_id.write(vals_partner)

        cddb_vals = False
        partner_stnk_id = customer_id
        if self.atas_nama_stnk == 'orang_lain':
            partner_stnk_id = self.customer_stnk_id
        cddb_vals = {
            'name':self.name_customer,
            'street':self.street,
            'rt':self.rt,
            'rw':self.rw,
            'state_id':self.state_id.id,
            'city_id':self.kabupaten_id.id,
            'kecamatan_id':self.kecamatan_id.id,
            'kecamatan':self.kecamatan,
            'zip_id':self.zip_code_id.id,
            'kelurahan':self.kelurahan,
            'no_ktp':self.no_ktp,
            'birtdate':self.tgl_lahir,
            'no_hp':self.mobile,
            'kode_customer':self.kode_customer or 'I',
            'facebook':self.facebook,
            'instagram':self.instagram,
            'twitter':self.twitter,
            'youtube':self.youtube,
            'customer_id':customer_id.id,
            'no_telp':self.kontak_tambahan,
            'dpt_dihubungi':'Y',
            'status_hp_id':self.status_hp_id.id,
            'status_rumah_id':self.status_rumah_id.id,
            'jenis_kelamin_id':self.jenis_kelamin_id.id,
            'agama_id':self.agama_id.id,
            'pendidikan_id':self.pendidikan_id.id,
            'pekerjaan_id':self.pekerjaan_id.id,
            'pengeluaran_id':self.pengeluaran_id.id,
            'jenismotor_id':self.jenismotor_id.id,
            'merkmotor_id':self.merkmotor_id.id,
            'penggunaan_id':self.penggunaan_id.id,
            'pengguna_id':self.pengguna_id.id,
            'gol_darah':self.gol_darah.id,
            'suku':self.suku,
            'hobi':self.hobi.id,
            'jabatan':self.jabatan,
            'penanggung_jawab':self.penanggung_jawab,
            'no_wa':self.no_wa,

        }

        cddb_id = self.env['wtc.cddb'].create(cddb_vals)
        dealer_spk_line = []
        dealer_spk_line.append([0,False,{
            'product_id':self.product_id.id,
            'is_bbn':'Y',
            'partner_stnk_id':partner_stnk_id.id,
            'uang_muka':self.uang_muka,
            'discount_po':self.diskon
        }])
        spk_vals = {
            'branch_id':self.branch_id.id,
            'partner_id':customer_id.id,
            'user_id':self.employee_id.user_id.id,
            'sales_koordinator_id':self.sales_koordinator_id.user_id.id or self.employee_id.coach_id.user_id.id,
            'finco_id':self.finco_id.id,
            'no_ktp':self.no_ktp,
            'cddb_id':cddb_id.id,
            'dealer_spk_line':dealer_spk_line,
            'register_spk_id':False,
            'jaringan_penjualan':self.jaringan_penjualan,
            'sumber_penjualan_id':self.sumber_penjualan_id.id,
            'activity_plan_id':self.activity_plan_id.id,
            'sales_source_location':self.sales_source_location_id.id,
        }
        
        # Funtion untuk menampung data selain default lead
        spk_vals_other = self._get_spk_vals_other()
        if spk_vals_other:
            spk_vals.update(spk_vals_other)
        spk_id = self.env['dealer.spk'].create(spk_vals)
        vals = {
            'customer_id':customer_id.id,
            'state':'dealt',
            'spk_id':spk_id.id,
            'deal_date':self._get_default_datetime(),
            'deal_uid':self._uid,
        }
        self.write(vals)
        
    @api.multi
    def action_detail_spk(self):
        spk_id = self.spk_id.id
        form_id = self.env.ref('dealer_sale_order.spk_dealer_form').id
        if spk_id:
            return {
                'type': 'ir.actions.act_window',
                'name': ('SPK'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'dealer.spk',
                'res_id': spk_id,
                'views': [(form_id, 'form')]
            }