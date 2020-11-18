from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from openerp import models, fields, api, _
from openerp.osv import osv

class wtc_faktur_pajak_other(models.Model):
    
    _name = "wtc.faktur.pajak.other"
    _description = "Faktur Pajak Other"
    _order = "id asc"
         
    @api.multi
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date()
             
    name = fields.Char(string='Faktur Pajak Other')
    date = fields.Date(string='Date',required=True,default=_get_default_date)
    faktur_pajak_id = fields.Many2one('wtc.faktur.pajak.out',string='No Faktur Pajak',domain='[("state","=","open")]')
    partner_id = fields.Many2one('res.partner',string='Partner')
    tgl_terbit = fields.Date(string='Tgl Terbit')
    thn_penggunaan = fields.Integer('Tahun Penggunaan')
    pajak_gabungan = fields.Boolean('Pajak Gabungan')
    untaxed_amount = fields.Float(string='Untaxed Amount')
    tax_amount = fields.Float(string='Tax Amount')
    total_amount = fields.Float(string='Total Amount')
    state = fields.Selection([
                              ('draft','Draft'),
                              ('posted','Posted'),
                              ],default='draft')
    confirm_uid = fields.Many2one('res.users',string="Posted by")
    confirm_date = fields.Datetime('Posted on')   
    kwitansi_no = fields.Char(string='No Kwitansi')
    memo = fields.Char(string='Memo')
    
    @api.model
    def create(self,values,context=None):
        vals = []
        values['name'] = self.env['ir.sequence'].get_sequence('FPO')     
        values['date'] = self._get_default_date()
        if len(str(values.get('thn_penggunaan','1'))) < 4 or len(str(values.get('thn_penggunaan','1'))) > 4 :
            raise osv.except_osv(('Perhatian !'), ("Tahun Pembuatan harus 4 digit !"))

        if 'tgl_terbit' in values:
            tgl_terbit = datetime.strptime(values['tgl_terbit'],"%Y-%m-%d")
            date_now = date.today()
            last_month = date_now.replace(day=1) - relativedelta(months=1)
            thn_penggunaan = str(values['thn_penggunaan']).replace(".","")
            thn_penggunaan_fix = int(thn_penggunaan)

            # cek data faktur pajak out
            fpo = values['faktur_pajak_id']
            faktur_pajak = self.env['wtc.faktur.pajak.out'].search([('id','=',fpo)]) 
            date_fpout = datetime.strptime(faktur_pajak.tgl_terbit,"%Y-%m-%d")
            faktur_pajak_tp = int(faktur_pajak.thn_penggunaan)

            if tgl_terbit.date() < date_fpout.date():
                raise osv.except_osv(('Perhatian !'), ("Tanggal terbit faktur pajak other kurang dari tanggal terbit faktur pajak, silahkan di cek kembali !"))            

            if faktur_pajak_tp != thn_penggunaan_fix:
                raise osv.except_osv(('Perhatian !'), ("Tahun penggunaan faktur pajak other tidak sama dengan tahun penggunaan faktur pajak, silahkan di cek kembali !"))            

            if thn_penggunaan_fix != tgl_terbit.year:
                raise osv.except_osv(('Perhatian !'), ("Tahun penggunaan dan tahun tanggal terbit tidak sesuai, silahkan di cek kembali !"))
            
            if tgl_terbit.date() <  last_month:
                raise osv.except_osv(('Perhatian !'), ("Masa tanggal terbit terlalu lama dari bulan sekarang !"))

            if tgl_terbit.date() > date_now:
                raise osv.except_osv(('Perhatian !'), ("Masa tanggal terbit belum lewat dari hari ini !"))


        faktur_pajak = super(wtc_faktur_pajak_other,self).create(values)       
        return faktur_pajak
    
    @api.onchange('thn_penggunaan')
    def onchange_tahun_penggunaan(self):
        warning = {}        
        if self.thn_penggunaan :
            tahun = len(str(self.thn_penggunaan))
            if tahun > 4 or tahun < 4 :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('Tahun hanya boleh 4 digit ! ')),
                }
                self.thn_penggunaan = False                
        return {'warning':warning} 

    @api.onchange('faktur_pajak_id')
    def onchange_faktur_pajak_id(self):
        self.thn_penggunaan = False
        if self.faktur_pajak_id:
            self.thn_penggunaan = self.faktur_pajak_id.thn_penggunaan
    
    @api.multi
    def action_post(self):
        self.confirm_date = datetime.now()
        self.confirm_uid = self._uid
        self.state = 'posted'
        self.date = self._get_default_date() 
        if self.untaxed_amount and self.tax_amount :
            self.total_amount = self.untaxed_amount + self.tax_amount
        elif self.untaxed_amount :
            self.total_amount = self.untaxed_amount
        elif self.tax_amount :
            self.total_amount = self.tax_amount
        else :
            self.total_amount = 0.0

        if self.tgl_terbit:
            tgl_terbit = datetime.strptime(self.tgl_terbit,"%Y-%m-%d")
            date_now = date.today()
            last_month = date_now.replace(day=1) - relativedelta(months=1)

            # cek data faktur pajak out
            faktur_pajak = self.faktur_pajak_id
            faktur_pajak_tt = faktur_pajak.tgl_terbit
            faktur_pajak_tp = int(faktur_pajak.thn_penggunaan)
            date_fpout = datetime.strptime(faktur_pajak_tt,"%Y-%m-%d")

            thn_penggunaan = str(self.thn_penggunaan).replace(".","")
            thn_penggunaan_fix = int(thn_penggunaan)

            if tgl_terbit.date() < date_fpout.date():
                raise osv.except_osv(('Perhatian !'), ("Tanggal terbit faktur pajak other kurang dari tanggal terbit faktur pajak, silahkan di cek kembali !"))            

            if faktur_pajak_tp != thn_penggunaan_fix:
                raise osv.except_osv(('Perhatian !'), ("Tahun penggunaan faktur pajak other tidak sama dengan tahun penggunaan faktur pajak, silahkan di cek kembali !"))            

            if tgl_terbit.date() <  last_month:
                raise osv.except_osv(('Perhatian !'), ("Masa tanggal terbit terlalu lama dari bulan sekarang !"))


            if thn_penggunaan_fix != tgl_terbit.year:
                raise osv.except_osv(('Perhatian !'), ("Tahun penggunaan dan tahun tanggal terbit tidak sesuai, silahkan di cek kembali !"))
            
            if tgl_terbit.date() > date_now:
                raise osv.except_osv(('Perhatian !'), ("Masa tanggal terbit belum lewat dari hari ini !"))

        model_id = self.env['ir.model'].search([
                                ('model','=','wtc.faktur.pajak.other')
                                ])
        if self.faktur_pajak_id.state!='open':
            raise osv.except_osv(('Perhatian !'), ('Nomor faktur pajak telah digunakan oleh transaksi lain !'))
        
        faktur_pajak = self.env['wtc.faktur.pajak.out'].browse(self.faktur_pajak_id.id)
        faktur_pajak.write({
                            'model_id':model_id.id,
                            'pajak_gabungan' :self.pajak_gabungan,
                            'partner_id':self.partner_id.id,
                            'untaxed_amount':self.untaxed_amount,
                            'amount_total':self.total_amount,
                            'date':self.tgl_terbit,
                            'transaction_id':self.id,
                            'tax_amount':self.tax_amount,
                            'company_id':1,
                            'thn_penggunaan':self.thn_penggunaan,
                            'state':'close',
                            })
        return True
          
    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Faktur Pajak Others tidak bisa didelete !"))
        return super(wtc_faktur_pajak_other, self).unlink(cr, uid, ids, context=context) 
             