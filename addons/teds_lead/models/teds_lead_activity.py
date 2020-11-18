from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning
from datetime import date,timedelta,datetime

class LeadActivity(models.Model):
    _name = "teds.lead.activity"
    _description = "Lead Activity"

    def _get_default_date(self):
        return date.today()

    name = fields.Many2one('teds.lead.stage')
    lead_id = fields.Many2one('teds.lead', index=True,ondelete='cascade')
    date = fields.Datetime ('Tanggal',default=_get_default_date)
    stage_result_id = fields.Many2one('teds.master.result.lead.activity','Result')
    next_activity = fields.Many2one('teds.lead.activity')
    remark = fields.Text('Remark')
    minat = fields.Selection([
        ('cold', 'Cold'),
        ('medium', 'Medium'),
        ('hot', 'Hot')], string='Minat')
    lat = fields.Float('Latitude', digits=(3, 6))
    lng = fields.Float('Longtitude', digits=(3,6)) 

    no_ktp = fields.Char('No KTP', related='lead_id.no_ktp')
    no_kk = fields.Char('No KK', related='lead_id.no_kk')
    mobile = fields.Char('No HP', related='lead_id.mobile')
    tempat_tgl_lahir = fields.Char('Tempat', related='lead_id.tempat_tgl_lahir')
    tgl_lahir = fields.Date('Tanggal Lahir', related='lead_id.tgl_lahir')

    
    # Questionnaire
    jenis_kelamin_id = fields.Many2one('wtc.questionnaire','Jenis Kelamin',domain=[('type','=','JenisKelamin')],related='lead_id.jenis_kelamin_id')
    agama_id = fields.Many2one('wtc.questionnaire','Agama',domain=[('type','=','Agama')],related='lead_id.agama_id')
    gol_darah = fields.Many2one('wtc.questionnaire','Golongan Darah',domain=[('type','=','GolonganDarah')],related='lead_id.gol_darah')
    pekerjaan_id = fields.Many2one('wtc.questionnaire','Pekerjaan',domain=[('type','=','Pekerjaan')],related='lead_id.pekerjaan_id')
    
    # Alamat
    street = fields.Char(string='Address', related='lead_id.street')
    rt = fields.Char(string='RT',size=3, related='lead_id.rt')
    rw = fields.Char(string='RW',size=3, related='lead_id.rw')
    state_id = fields.Many2one('res.country.state',string='Province', related='lead_id.state_id')
    kabupaten_id = fields.Many2one('wtc.city','Kabupaten',domain="[('state_id','=',state_id)]", related='lead_id.kabupaten_id')
    kecamatan_id = fields.Many2one('wtc.kecamatan','Kecamatan',domain="[('city_id','=',kabupaten_id)]", related='lead_id.kecamatan_id')
    kecamatan = fields.Char(string="Kecamatan", related='lead_id.kecamatan') 
    zip_code_id = fields.Many2one('wtc.kelurahan',string='Kelurahan',domain="[('kecamatan_id','=',kecamatan_id)]", related='lead_id.zip_code_id')
    kelurahan = fields.Char(string="Kelurahan", related='lead_id.kelurahan')
    kode_pos = fields.Char(string="Kode Pos", related='lead_id.kode_pos')

    is_sesuai_ktp = fields.Boolean('Sesuai KTP ?',default=True,related='lead_id.is_sesuai_ktp')    
    street_domisili = fields.Char(string='Address',related='lead_id.street_domisili')
    rt_domisili = fields.Char(string='RT',size=3,related='lead_id.rt_domisili')
    rw_domisili = fields.Char(string='RW',size=3,related='lead_id.rw_domisili')
    state_domisili_id = fields.Many2one('res.country.state',string='Province',related='lead_id.state_domisili_id')
    kabupaten_domisili_id = fields.Many2one('wtc.city','Kabupaten',domain="[('state_id','=',state_domisili_id)]",related='lead_id.kabupaten_domisili_id')
    kecamatan_domisili_id = fields.Many2one('wtc.kecamatan','Kecamatan',domain="[('city_id','=',kabupaten_domisili_id)]",related='lead_id.kecamatan_domisili_id')
    kecamatan_domisili = fields.Char(string="Kecamatan",related='lead_id.kecamatan_domisili') 
    zip_code_domisili_id = fields.Many2one('wtc.kelurahan',string='Kelurahan',domain="[('kecamatan_id','=',kecamatan_domisili_id)]",related='lead_id.zip_code_domisili_id')
    kelurahan_domisili = fields.Char(string="Kelurahan",related='lead_id.kelurahan_domisili')
    kode_pos_domisili = fields.Char(string="Kode Pos",related='lead_id.kode_pos_domisili')


    motor_sekarang = fields.Char('Motor Sekarang', related='lead_id.motor_sekarang')
    payment_type = fields.Selection([
        ('1', 'Cash'),
        ('2', 'Credit'),
    ], string='Pembelian', related='lead_id.payment_type')
    finco_id = fields.Many2one('res.partner','Finco', related='lead_id.finco_id',domain=[('finance_company','=',True)])
    date_jatuh_tempo = fields.Selection([
        ('1','1'),('2','2'),('3','3'),('4','4'),('5','5'),('6','6'),('7','7'),('8','8'),('9','9'),('10','10'),
        ('11','11'),('12','12'),('13','13'),('14','14'),('15','15'),('16','16'),('17','17'),('18','18'),('19','19'),('20','20'),
        ('21','21'),('22','22'),('23','23'),('24','24'),('25','25'),('26','26'),('27','27'),('28','28'),('29','29'),('30','30'),('31','31')
        ],string='Request Tgl Jatuh Tempo',related='lead_id.date_jatuh_tempo')
    uang_muka = fields.Float(string='Tanda Jadi (Rp)', related='lead_id.uang_muka',digits=(12,0))
    tgl_uang_muka = fields.Date('Tgl Terima Tanda Jadi',default=_get_default_date, related='lead_id.tgl_uang_muka')
    tenor = fields.Integer('Tenor', related='lead_id.tenor')
    cicilan = fields.Float('Cicilan (Rp)', related='lead_id.cicilan',digits=(12,0))
    product_id = fields.Many2one('product.product','Product',related='lead_id.product_id')
    
    @api.constrains('no_ktp')
    def cek_ktp(self):
        self.ensure_one()
        if self.no_ktp:
            if not self.no_ktp.isdigit() or len(self.no_ktp) != 16:
                raise Warning('Perhatian ! \n Nomor KTP harus angka dan 16 digit.')

    @api.constrains('mobile')
    def cek_nomor(self):
        self.ensure_one()
        if self.mobile:
            if not self.mobile.isdigit() or len(self.mobile) < 5 :   
                raise Warning('Perhatian! \n Nomor Telepon harus angka dan minimal 5 digit.')
    
    
    @api.constrains('tgl_lahir')
    def cek_tgl_lahir(self):
        if self.tgl_lahir :
            tgl_lahir = datetime.strptime(self.tgl_lahir, '%Y-%m-%d')
            today = datetime.now()
            if tgl_lahir > today :
                raise Warning('Maaf, harap isi tanggal lahir dengan benar !')

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
    def action_add_only(self):
        self.ensure_one()

        if self.lead_id.state == 'open':
            self.lead_id.write({
                'next_activity_id': False,
                'minat': self.minat,
            })
        val = {
            'stage_result_id':self.stage_result_id.id,
            'remark':self.remark,
        }
        self.write(val)
    
    @api.multi
    def action_add_activity(self):
        self.ensure_one()
        
        self.lead_id.write({
            'next_activity_id':self.id,
        })

    @api.multi
    def action_add_and_next_activity(self):
        self.ensure_one()
        self.action_add_activity()
        form1_id = self.env.ref('teds_lead.view_teds_lead_activity_first_view_form').id
        return {
            'name': ('Next activity'),
            'res_model': 'teds.lead.activity',
            'context': {
                'default_lead_id': self.lead_id.id,
            },
            'type': 'ir.actions.act_window',
            'view_id': False,
            'views': [(form1_id, 'form')],
            'view_mode': 'form',
            'target': 'new',
            'view_type': 'form',
            'res_id': False
        }
