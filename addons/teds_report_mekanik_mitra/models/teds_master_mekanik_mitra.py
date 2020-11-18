from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning
from datetime import date, datetime, timedelta,time

class MasterMekanikMitra(models.Model):
    _name = "teds.master.mekanik.mitra"
    _rec_name = "mekanik_id"

    branch_id = fields.Many2one('wtc.branch','Branch')
    mekanik_id = fields.Many2one('hr.employee','Mekanik')
    perjanjian_ke = fields.Char('Perjanjian Ke')
    start_date = fields.Date('Tanggal Mulai')
    end_date = fields.Date('Tanggal Selesai')
    keterangan = fields.Text('Keterangan')
    no_rekening = fields.Char('No Rekening')
    nama_rekening = fields.Char('Nama Rekening')
    bank = fields.Selection([
        ('BCA','BCA'),
        ('Mandiri','Mandiri'),
        ('BRI','BRI'),
        ('other','Other')])
    bank_name = fields.Char('Nama Bank')
    surat_perjanjian = fields.Selection([
        ('Belum','Belum'),
        ('Proses','Proses'),
        ('OK','OK')])
    absen_finger = fields.Char('Absensi Finger ID')
    histrory_absensi_ids = fields.One2many('teds.mekanik.mitra.histrory.absensi','mitra_id')

    _sql_constraints = [('mekanik_id_unique', 'unique(mekanik_id)', 'Mekanik tidak boleh duplikat !')]


    @api.onchange('branch_id')
    def onchange_mekanik(self):
        self.mekanik_id = False
    
    @api.onchange('keterangan')
    def onchange_keterangan(self):
        if self.keterangan:
            self.keterangan = self.keterangan.title()
    
    @api.onchange('bank')
    def onchange_bank(self):
        self.bank_name = False
        if self.bank != 'other':
            self.bank_name = self.bank

    @api.onchange('bank_name')
    def onchange_bank_name(self):
        if self.bank_name:
            self.bank_name = self.bank_name.upper()

class MekanikMitraHistroryAbsensi(models.Model):
    _name = "teds.mekanik.mitra.histrory.absensi"

    def _get_tahun(self):
        return datetime.today().date().year

    mitra_id = fields.Many2one('teds.master.mekanik.mitra','Mitra',ondelete='cascade')
    bulan = fields.Selection([('1','Januari'),
                              ('2','Februari'),
                              ('3','Maret'),
                              ('4','April'),
                              ('5','Mei'),
                              ('6','Juni'),
                              ('7','Juli'),
                              ('8','Agustus'),
                              ('9','September'),
                              ('10','Oktober'),
                              ('11','November'),
                              ('12','Desember')], 'Bulan', required=True)
    tahun = fields.Char('Tahun', default=_get_tahun,required=True)
    jumlah = fields.Float('Jumlah')

    _sql_constraints = [('bulan,tahun_unique', 'unique(mitra_id,bulan,tahun)', 'Absensi tidak boleh duplikat !')]
