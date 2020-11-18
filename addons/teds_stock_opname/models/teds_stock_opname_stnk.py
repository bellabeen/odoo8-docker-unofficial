from openerp import models, fields, api
from datetime import date, datetime, timedelta,time
from dateutil.relativedelta import relativedelta
from openerp.exceptions import Warning

class StockOpnameSTNK(models.Model):
    _name = "teds.stock.opname.stnk"

    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()
    
    @api.model
    def _get_default_datetime(self):
        return datetime.now()

    name = fields.Char('Name',index=True)
    branch_id = fields.Many2one('wtc.branch','Branch',index=True)
    date = fields.Date('Tanggal SO',default=_get_default_date)
    staff_bbn = fields.Char('Staff BBN')
    adh = fields.Char('ADH')
    soh = fields.Char('SOH')
    post_date = fields.Datetime('Posted on')
    post_uid = fields.Many2one('res.users','Posted by')
    generate_date = fields.Datetime('Generate on')
    state = fields.Selection([
        ('draft','Draft'),
        ('posted','Posted')],default="draft")
    division = fields.Selection([('Unit','Unit')],default="Unit")
    detail_ids = fields.One2many('teds.stock.opname.stnk.line','opname_id')
    other_stnk_ids = fields.One2many('teds.stock.opname.stnk.other','opname_id')
    note_bakso = fields.Text('Note')
        
    @api.model
    def create(self,vals):
        cek = self.search([
            ('branch_id','=',vals['branch_id']),
            ('state','!=','posted')])
        if cek:
            raise Warning('Perhatian ! Masih ada stock opname yang belum selesai !')

        vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'SOST')
        if vals.get('staff_bbn'):
            vals['staff_bbn'] = vals['staff_bbn'].title()
        if vals.get('adh'):
            vals['adh'] = vals['adh'].title()
        if vals.get('soh'):
            vals['soh'] = vals['soh'].title()
        return super(StockOpnameSTNK,self).create(vals)
    
    @api.multi
    def write(self,vals):
        if vals.get('staff_bbn'):
            vals['staff_bbn'] = vals['staff_bbn'].title()
        if vals.get('adh'):
            vals['adh'] = vals['adh'].title()
        if vals.get('soh'):
            vals['soh'] = vals['soh'].title()
        return super(StockOpnameSTNK,self).write(vals)

    @api.multi
    def unlink(self):
        for data in self:
            if data.state != "draft":
                raise Warning("Tidak bisa menghapus data yang berstatus selain draft!")
        return super(StockOpnameSTNK, self).unlink()

    @api.multi
    def action_generate_stock(self):
        query = """
            SELECT 
            lot.id as lot_id,
            lot.no_polisi as nopol,
            lot.tgl_terima_stnk as tgl_terima_stnk,
            lot.customer_stnk as customer_stnk,  
            lokasi_stnk.name as lokasi_stnk,
            age(tgl_terima_stnk)::text as umur
            FROM stock_production_lot as lot
            LEFT JOIN wtc_lokasi_stnk as lokasi_stnk ON lokasi_stnk.id=lot.lokasi_stnk_id
            WHERE (penerimaan_stnk_id IS NOT NULL OR tgl_terima_stnk IS NOT NULL)
            AND (penyerahan_stnk_id IS NULL AND tgl_penyerahan_stnk IS NULL)
            AND lokasi_stnk.branch_id = %d
            ORDER BY lot.customer_stnk ASC
        """ %(self.branch_id.id)
        self.env.cr.execute(query)
        ress = self.env.cr.dictfetchall()
        lines = []
        for res in ress:
            lines.append([0,False,{
                'lot_id':res.get('lot_id'),
                'no_polisi':res.get('nopol'),
                'customer_stnk_id':res.get('customer_stnk'),
                'tgl_penerimaan':res.get('tgl_terima_stnk'),
                'lokasi_stnk':res.get('lokasi_stnk'),
                'umur':res.get('umur')
            }])
        self.write({
            'generate_date':self._get_default_datetime(),
            'detail_ids':lines
        })

    @api.multi
    def action_post(self):
        # if not self.detail_ids:
        #     raise Warning('Data Stock STNK tidak boleh kosong !')
        line = self.env['teds.stock.opname.stnk.line'].search([
            ('opname_id','=',self.id),
            ('validasi_ceklis_fisik_stnk','=',False)],limit=1)
        if line:
            raise Warning('Perhatian ! Ceklis Fisik STNK masih ada yang belum diisi !')
        self.write({
            'post_uid':self._uid,
            'post_date':self._get_default_datetime(),
            'state':'posted'
        })

    @api.multi
    def action_print_validasi(self):
        active_ids = self.env.context.get('active_ids', [])
        user = self.env['res.users'].browse(self._uid).name
        detail_ids = []
        other_stnk_ids = []

        for other in self.other_stnk_ids:
            other_stnk_ids.append({
                'nama_stnk':other.nama_stnk,
                'no_engine':other.no_engine,
                'keterangan':other.keterangan
            })
        
        for line in self.detail_ids:
            detail_ids.append({
                'branch_code':self.branch_id.code,
                'nama_stnk':line.customer_stnk_id.name,
                'validasi_nama_stnk':line.validasi_nama_stnk,
                'tgl_penerimaan':line.tgl_penerimaan,
                'lokasi_stnk':line.lokasi_stnk,
                'no_engine':line.lot_id.name,
                'validasi_no_engine':line.validasi_no_engine,
                'no_polisi':line.no_polisi,
                'validasi_no_polisi':line.validasi_no_polisi,
                'validasi_ceklis_fisik_stnk':line.validasi_ceklis_fisik_stnk,
                'keterangan':line.keterangan,
                'umur':line.umur
            })

        datas = {
            'ids': active_ids,
            'user': user,
            'date': (datetime.now() + timedelta(hours=7)).strftime('%Y-%d-%d %H:%M:%S'),
            'name':str(self.name),
            'branch_id':str(self.branch_id.name_get().pop()[1]),
            'division':self.division,
            'tgl_so':self.date,
            'staff_bbn':self.staff_bbn,
            'soh': self.soh,
            'adh':self.adh,
            'detail_ids':detail_ids,
            'other_stnk_ids':other_stnk_ids,
            'create_uid':self.create_uid.name,
            'create_date': str(datetime.strptime(self.create_date, '%Y-%m-%d %H:%M:%S') + relativedelta(hours=7)),
        }
        return self.env['report'].get_action(self,'teds_stock_opname.teds_stock_opname_stnk_print_validasi', data=datas)

    @api.multi
    def action_bakso(self):
        form_id = self.env.ref('teds_stock_opname.view_teds_so_stnk_bakso_wizard').id
    
        return {
            'type': 'ir.actions.act_window',
            'name': 'Berita Acara SO',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.stock.opname.stnk.bakso.wizard',
            'context':{'default_opname_id':self.id,'default_note_bakso':self.note_bakso},
            'views': [(form_id, 'form')],
            'target':'new'
        }    

    @api.multi
    def action_download_excel(self):
        obj_x = self.env['teds.stock.opname.stnk.wizard'].create({'opname_stnk_id':self.id})
        obj_x.action_download_excel()
        return {
            'type': 'ir.actions.act_url',
            'name': 'contract',
            'url':'/web/binary/saveas?model=teds.stock.opname.stnk.wizard&field=file_excel&filename_field=name&id=%d'%(obj_x.id)
        }

class StockOpnameSTNKLine(models.Model):
    _name = "teds.stock.opname.stnk.line"

    opname_id = fields.Many2one('teds.stock.opname.stnk','Stock Opname',ondelete='cascade')
    lot_id = fields.Many2one('stock.production.lot','No Engine')
    no_polisi = fields.Char('No Polisi')
    customer_stnk_id = fields.Many2one('res.partner','Nama STNK')
    tgl_penerimaan = fields.Date('Tanggal Penerimaan')
    lokasi_stnk = fields.Char('Lokasi STNK')
    umur = fields.Char('Umur')
    validasi_nama_stnk = fields.Selection([
        ('Nama sesuai dengan STNK','Nama sesuai dengan STNK'),
        ('Nama tidak sesuai dengan STNK','Nama tidak sesuai dengan STNK'),
        ('-','-')],string="Validasi Nama STNK")
    validasi_no_engine = fields.Selection([
        ('No mesin sesuai dengan STNK','No mesin sesuai dengan STNK'),
        ('No mesin tidak sesuai dengan STNK','No mesin tidak sesuai dengan STNK'),
        ('-','-')],string="Validasi No Engine")
    validasi_no_polisi = fields.Selection([
        ('No Polisi sesuai dengan STNK','No Polisi sesuai dengan STNK'),
        ('No Polisi tidak sesuai dengan STNK','No Polisi tidak sesuai dengan STNK'),
        ('No Polisi belum diterima','No Polisi belum diterima'),
        ('-','-')],string="Validasi No Polisi")
    validasi_ceklis_fisik_stnk = fields.Selection([
        ('Fisik Ada','Fisik Ada'),
        ('Fisik di HO','Fisik di HO'),
        ('Fisik di MD','Fisik di MD'),
        ('Revisi Biro Jasa','Revisi Biro Jasa'),
        ('Sudah Penyerahan ke Konsumen','Sudah Penyerahan ke Konsumen'),
        ('Hilang / Fisik tidak diketahui','Hilang / Fisik tidak diketahui')],string="Ceklis Fisik STNK")
    keterangan = fields.Char('Keterangan')

    @api.multi
    def write(self,vals):
        if vals.get('validasi_ceklis_fisik_stnk'):
            if vals['validasi_ceklis_fisik_stnk'] != 'Fisik Ada':
                vals['validasi_nama_stnk'] = '-'
                vals['validasi_no_engine'] = '-'
                vals['validasi_no_polisi'] = '-'
        return super(StockOpnameSTNKLine,self).write(vals)

    @api.onchange('validasi_ceklis_fisik_stnk')
    def onchnage_validasi(self):
        self.validasi_nama_stnk = False
        self.validasi_no_engine = False
        self.validasi_no_polisi = False
        if self.validasi_ceklis_fisik_stnk:
            if self.validasi_ceklis_fisik_stnk != 'Fisik Ada':
                self.validasi_nama_stnk = '-'
                self.validasi_no_engine = '-'
                self.validasi_no_polisi = '-'

    @api.onchange('validasi_ceklis_fisik_stnk','validasi_nama_stnk')
    def onchange_validasi_nama_stnk(self):
        warning = ''
        if self.validasi_ceklis_fisik_stnk and self.validasi_nama_stnk:
            if self.validasi_ceklis_fisik_stnk == 'Fisik Ada' and self.validasi_nama_stnk == '-':
                warning = {'title':'Perhatian !','message':'Validasi Nama STNK tidak boleh - !'}
                self.validasi_nama_stnk = False
            elif self.validasi_ceklis_fisik_stnk != 'Fisik Ada' and self.validasi_nama_stnk not in ('-',False):
                warning = {'title':'Perhatian !','message':'Validasi Nama STNK tidak boleh selain - !'}    
                self.validasi_nama_stnk = False
        return {'warning':warning}
    
    @api.onchange('validasi_ceklis_fisik_stnk','validasi_no_polisi')
    def onchange_validasi_no_polisi(self):
        warning = ''
        if self.validasi_ceklis_fisik_stnk and self.validasi_no_polisi:
            if self.validasi_ceklis_fisik_stnk == 'Fisik Ada' and self.validasi_no_polisi == '-':
                warning = {'title':'Perhatian !','message':'Validasi No Polisi tidak boleh - !'}
                self.validasi_no_polisi = False
            elif self.validasi_ceklis_fisik_stnk != 'Fisik Ada' and self.validasi_no_polisi not in ('-',False):
                warning = {'title':'Perhatian !','message':'Validasi No Polisi tidak boleh selain - !'}    
                self.validasi_no_polisi = False
        return {'warning':warning}
            
    @api.onchange('validasi_ceklis_fisik_stnk','validasi_no_engine')
    def onchange_validasi_no_engine(self): 
        warning = ''
        if self.validasi_ceklis_fisik_stnk and self.validasi_no_engine:
            if self.validasi_ceklis_fisik_stnk == 'Fisik Ada' and self.validasi_no_engine == '-':
                warning = {'title':'Perhatian !','message':'Validasi No Engine tidak boleh - !'}
                self.validasi_no_engine = False
            elif self.validasi_ceklis_fisik_stnk != 'Fisik Ada' and self.validasi_no_engine not in ('-',False):
                warning = {'title':'Perhatian !','message':'Validasi No Engine tidak boleh selain - !'}    
                self.validasi_no_engine = False
        return {'warning':warning}

class StockOpnameSTNKOther(models.Model):
    _name = "teds.stock.opname.stnk.other"

    opname_id = fields.Many2one('teds.stock.opname.stnk','Stock Opname',ondelete='cascade')
    nama_stnk = fields.Char('Nama STNK')
    no_engine = fields.Char('No Engine')
    keterangan = fields.Char('Keterangan')

class StockOpnameSTNKBaksoWizard(models.TransientModel):
    _name = "teds.stock.opname.stnk.bakso.wizard"

    note_bakso = fields.Text('Note')
    opname_id = fields.Many2one('teds.stock.opname.stnk','Stock Opname')
    
    @api.multi
    def action_submit_bakso(self):
        active_ids = self.env.context.get('active_ids', [])
        user = self.env['res.users'].browse(self._uid).name
        
        saldo_sistem = len(self.opname_id.detail_ids)
        saldo_cabang = 0
        saldo_ho = 0
        saldo_md = 0
        saldo_birojasa = 0
        saldo_konsumen = 0
        saldo_lainnya = 0
        other_stnk = len(self.opname_id.other_stnk_ids)

        for line in self.opname_id.detail_ids:
            if line.validasi_ceklis_fisik_stnk == 'Fisik Ada':
                saldo_cabang += 1
            elif line.validasi_ceklis_fisik_stnk == 'Fisik di HO':
                saldo_ho += 1
            elif line.validasi_ceklis_fisik_stnk == 'Revisi Biro Jasa':
                saldo_birojasa += 1
            elif line.validasi_ceklis_fisik_stnk == 'Sudah Penyerahan ke Konsumen':
                saldo_konsumen += 1
            elif line.validasi_ceklis_fisik_stnk == 'Hilang / Fisik tidak diketahui':
                saldo_lainnya += 1

        selisih_sistem_fisik = saldo_sistem - saldo_cabang - saldo_ho - saldo_md - saldo_birojasa - saldo_konsumen - saldo_lainnya
        total_stock = saldo_cabang + other_stnk 
        datas = {
            'ids': active_ids,
            'name':str(self.opname_id.name),
            'branch':str(self.opname_id.branch_id.name_get().pop()[1]),
            'division':self.opname_id.division,
            'tgl_so':self.opname_id.date,
            'jam_mulai': str(datetime.strptime(self.opname_id.generate_date, '%Y-%m-%d %H:%M:%S') + relativedelta(hours=7)),
            'jam_selesai': str(datetime.strptime(self.opname_id.post_date, '%Y-%m-%d %H:%M:%S') + relativedelta(hours=7)),
            'saldo_sistem': saldo_sistem,
            'saldo_cabang':saldo_cabang,
            'saldo_ho':saldo_ho,
            'saldo_md':saldo_md,
            'saldo_birojasa':saldo_birojasa,
            'saldo_konsumen':saldo_konsumen,
            'saldo_lainnya':saldo_lainnya,
            'selisih_sistem_fisik':selisih_sistem_fisik,
            'other_stnk':other_stnk,
            'total_stock':total_stock,
            'note_bakso':str(self.note_bakso) if self.note_bakso else '',
            'staff_bbn':str(self.opname_id.staff_bbn),
            'adh':str(self.opname_id.adh),
            'soh':str(self.opname_id.soh),
            'user': user,
            'date': (datetime.now() + timedelta(hours=7)).strftime('%Y-%d-%d %H:%M:%S'),
        }
        self.opname_id.note_bakso = self.note_bakso
        
        return self.env['report'].get_action(self,'teds_stock_opname.teds_stock_opname_stnk_print_bakso', data=datas)
