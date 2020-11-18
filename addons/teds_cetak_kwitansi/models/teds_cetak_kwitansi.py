from openerp import models, fields, api
from datetime import datetime, timedelta,date
from openerp.exceptions import Warning

class ListingCetakKwitansi(models.Model):
    _name = "teds.listing.cetak.kwitansi"

    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()
    
    @api.model
    def _get_default_datetime(self):
        return self.env['wtc.branch'].get_default_datetime_model()

    name = fields.Char('No Kwitansi',index=True)
    branch_id = fields.Many2one('wtc.branch','Branch')
    date = fields.Date('Tanggal Kwitansi',default=_get_default_date)
    no_refrence = fields.Char('No Refrence')
    nama_pembayar = fields.Char('Nama Pembayar')
    journal_id = fields.Many2one('account.journal','No Rekening')
    nama_rekening = fields.Char('Nama Rekening',default='PT. Tunas Dwipa Matra')
    total = fields.Float('Jumlah Pembayaran')
    pimpinan_cabang = fields.Char('Pimpinan Cabang')
    redaksi = fields.Char('Redaksi')
    is_ppn = fields.Boolean('PPN ?')
    no_faktur_pajak = fields.Char('No Faktur Pajak')
    state = fields.Selection([
        ('draft','Draft'),
        ('posted','Posted'),
        ('paid','Paid'),
        ('cancelled','Cancelled')],default='draft')
    confirm_date = fields.Datetime('Posted on')
    confirm_uid = fields.Many2one('res.users','Posted By')
    cetakan_ke = fields.Integer('Cetakan Ke')
    jenis_transaksi = fields.Selection([
        ('CLAIM KPB','CLAIM KPB'),
        ('CLAIM AHASS','CLAIM AHASS'),
        ('INSENTIF DEALER','INSENTIF DEALER'), 
        ('INSENTIF PEMASARAN','INSENTIF PEMASARAN'), 
        ('JASA PERANTARA','JASA PERANTARA'), 
        ('SALES INSENTIVE','SALES INSENTIVE'),
        ('CLAIM SCP','CLAIM SCP'),
        ('ONGKOS ANGKUT','ONGKOS ANGKUT')],string="Jenis Transaksi")
    no_bukti_pembayaran = fields.Char('No Bukti Pembayaran')
    tgl_pembayaran = fields.Date('Tanggal Bukti Pembayaran')

    @api.model
    def create(self,vals):
        vals['name'] = self.env['ir.sequence'].get_sequence_no_kwitansi('K-')
        return super(ListingCetakKwitansi,self).create(vals)
        

    @api.multi
    def unlink(self, context=None):
        for tc in self :
            if tc.state != 'draft' :
                raise Warning('Transaksi yang berstatus selain Draft tidak bisa dihapus.')
        return super(TedsCollectingCancel, self).unlink()
    
    @api.onchange('is_ppn')
    def onchange_no_faktur_pajak(self):
        self.no_faktur_pajak = False
    
    @api.onchange('branch_id')
    def onchange_pembayar(self):
        domain = {}
        if self.branch_id:
            self.pimpinan_cabang = self.branch_id.pimpinan_id.name
            self.nama_pembayar = self.branch_id.default_supplier_id.name
            journals = self.env['account.journal'].search(['|',('code','=','BK01HHO'),('branch_id','=',self.branch_id.id),('type','=','bank')])
            ids = [journal.id for journal in journals]
            domain = {'journal_id':[('id','in',ids)]}
        return {'domain':domain}


    @api.multi
    def action_post(self):
        if self.state != 'draft':
            raise Warning('State sudah tidak bisa di posting !')
        self.write({
            'state':'posted',
            'confirm_uid':self._uid,
            'confirm_date':self._get_default_datetime(),
        })

    @api.multi
    def action_to_revisi(self):
        if self.state != 'posted':
            raise Warning('Tidak bisa di Revisi !')
        self.write({
            'state':'draft',
            'cetakan_ke':False,
        })
            

    @api.multi
    def action_update_faktur_pajak(self):
        self.ensure_one()
        form_id = self.env.ref('teds_cetak_kwitansi.view_teds_listing_cetak_kwitansi_faktur_wizard').id
        return {
            'name': ('Faktur Pajak'),
            'res_model': 'teds.listing.cetak.kwitansi',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'views': [(form_id, 'form')],
            'view_mode': 'form',
            'target': 'new',
            'view_type': 'form',
            'context':{'default_is_ppn':True},
            'res_id': self.id,
        }
    
    @api.multi
    def action_submit_faktur(self):
        self.is_ppn = True

    @api.multi
    def action_pembayaran_kwitansi(self):
        self.ensure_one()
        form_id = self.env.ref('teds_cetak_kwitansi.view_teds_listing_cetak_kwitansi_pembawayaran_wizard').id
        return {
            'name': ('Pembayaran'),
            'res_model': 'teds.listing.cetak.kwitansi',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'views': [(form_id, 'form')],
            'view_mode': 'form',
            'target': 'new',
            'view_type': 'form',
            'res_id': self.id,
        }

    @api.multi
    def action_submit_pembayaran(self):
        self.write({
            'state':'paid',    
        })

    @api.multi
    def action_print(self):
        cek_group = self.env['res.users'].has_group('teds_cetak_kwitansi.group_teds_allow_cetak_listing_kwitansi')
        if not cek_group:
            if self.cetakan_ke > 1:
                raise Warning('Kwitansi sudah tidak bisa di cetak !')
            self.sudo().cetakan_ke += 1
        datas = self.read()[0]
        return self.env['report'].get_action(self,'teds_cetak_kwitansi.teds_lisiting_cetak_kwitansi_print', data=datas)
