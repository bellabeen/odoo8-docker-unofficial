from openerp import models, fields, api
from datetime import date, datetime, timedelta,time
from dateutil.relativedelta import relativedelta
from openerp.exceptions import Warning

class StockOpnameBPKB(models.Model):
    _name = "teds.stock.opname.bpkb"

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
    detail_ids = fields.One2many('teds.stock.opname.bpkb.line','opname_id')
    other_bpkb_ids = fields.One2many('teds.stock.opname.bpkb.other','opname_id')
    note_bakso = fields.Text('Note')
    

    @api.model
    def create(self,vals):
        cek = self.search([
            ('branch_id','=',vals['branch_id']),
            ('state','!=','posted')])
        if cek:
            raise Warning('Perhatian ! Masih ada stock opname yang belum selesai !')
        
        vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'SOBP')
        if vals.get('staff_bbn'):
            vals['staff_bbn'] = vals['staff_bbn'].title()
        if vals.get('adh'):
            vals['adh'] = vals['adh'].title()
        if vals.get('soh'):
            vals['soh'] = vals['soh'].title()
        return super(StockOpnameBPKB,self).create(vals)
    
    @api.multi
    def write(self,vals):
        if vals.get('staff_bbn'):
            vals['staff_bbn'] = vals['staff_bbn'].title()
        if vals.get('adh'):
            vals['adh'] = vals['adh'].title()
        if vals.get('soh'):
            vals['soh'] = vals['soh'].title()
        return super(StockOpnameBPKB,self).write(vals)

    @api.multi
    def unlink(self):
        for data in self:
            if data.state != "draft":
                raise Warning("Tidak bisa menghapus data yang berstatus selain draft!")
        return super(StockOpnameBPKB, self).unlink()


    @api.multi
    def action_generate_stock(self):
        query = """
            SELECT 
            lot.id as lot_id,
            lot.customer_stnk as customer_bpkb,
            lokasi_bpkb.name as lokasi_bpkb,
            lot.tgl_terima_bpkb as tgl_terima_bpkb,
            lot.no_bpkb as no_bpkb,
            lot.finco_id as finco_id,
            age(tgl_terima_bpkb)::text as umur,
            EXTRACT(day FROM now() - coalesce(lot.tgl_terima_bpkb,now())) as over_due
            FROM stock_production_lot as lot
            LEFT JOIN wtc_lokasi_bpkb as lokasi_bpkb ON lokasi_bpkb.id = lot.lokasi_bpkb_id
            WHERE (penerimaan_bpkb_id IS NOT NULL OR  tgl_terima_bpkb IS NOT NULL)
            AND (penyerahan_bpkb_id IS NULL AND tgl_penyerahan_bpkb IS NULL)
            AND lokasi_bpkb.branch_id = %d
            ORDER BY lot.customer_stnk ASC
        """ %(self.branch_id.id)
        self.env.cr.execute(query)
        ress = self.env.cr.dictfetchall()
        lines = []
        for res in ress:
            lines.append([0,False,{
                'lot_id':res.get('lot_id'),
                'no_bpkb':res.get('no_bpkb'),
                'customer_bpkb_id':res.get('customer_bpkb'),
                'tgl_penerimaan':res.get('tgl_terima_bpkb'),
                'lokasi_bpkb':res.get('lokasi_bpkb'),
                'finco_id':res.get('finco_id'),
                'umur':res.get('umur'),
                'over_due':int(res.get('over_due'))
            }])
        self.write({
            'generate_date':self._get_default_datetime(),
            'detail_ids':lines
        })

    @api.multi
    def action_post(self):
        # if not self.detail_ids:
        #     raise Warning('Data Stock BPKB tidak boleh kosong !')
        line = self.env['teds.stock.opname.bpkb.line'].search([
            ('opname_id','=',self.id),
            ('validasi_ceklis_fisik_bpkb','=',False)],limit=1)
        if line:
            raise Warning('Perhatian ! Ceklis Fisik BPKB masih ada yang belum diisi !')
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
        other_bpkb_ids = []

        for other in self.other_bpkb_ids:
            other_bpkb_ids.append({
                'nama_bpkb':other.nama_bpkb,
                'no_engine':other.no_engine,
                'keterangan':other.keterangan
            })
        
        for line in self.detail_ids:
            detail_ids.append({
                'branch_code':self.branch_id.code,
                'nama_bpkb':line.customer_bpkb_id.name,
                'validasi_nama_bpkb':line.validasi_nama_bpkb,
                'tgl_penerimaan':line.tgl_penerimaan,
                'lokasi_bpkb':line.lokasi_bpkb,
                'no_engine':line.lot_id.name,
                'validasi_no_engine':line.validasi_no_engine,
                'no_bpkb':line.no_bpkb,
                'finco':line.finco_id.name,
                'validasi_no_bpkb':line.validasi_no_bpkb,
                'validasi_ceklis_fisik_bpkb':line.validasi_ceklis_fisik_bpkb,
                'keterangan':line.keterangan,
                'umur':line.umur,
                'over_due':line.over_due
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
            'other_bpkb_ids':other_bpkb_ids,
            'create_uid':self.create_uid.name,
            'create_date': str(datetime.strptime(self.create_date, '%Y-%m-%d %H:%M:%S') + relativedelta(hours=7)),
        }
        return self.env['report'].get_action(self,'teds_stock_opname.teds_stock_opname_bpkb_print_validasi', data=datas)

    @api.multi
    def action_bakso(self):
        form_id = self.env.ref('teds_stock_opname.view_teds_so_bpkb_bakso_wizard').id
    
        return {
            'type': 'ir.actions.act_window',
            'name': 'Berita Acara SO',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.stock.opname.bpkb.bakso.wizard',
            'context':{'default_opname_id':self.id,'default_note_bakso':self.note_bakso},
            'views': [(form_id, 'form')],
            'target':'new'
        }
    
    @api.multi
    def action_download_excel(self):
        obj_x = self.env['teds.stock.opname.bpkb.wizard'].create({'opname_bpkb_id':self.id})
        obj_x.action_download_excel()
        return {
            'type': 'ir.actions.act_url',
            'name': 'contract',
            'url':'/web/binary/saveas?model=teds.stock.opname.bpkb.wizard&field=file_excel&filename_field=name&id=%d'%(obj_x.id)
        }


class StockOpnameBPKBLine(models.Model):
    _name = "teds.stock.opname.bpkb.line"

    opname_id = fields.Many2one('teds.stock.opname.bpkb','Stock Opname',ondelete='cascade')
    lot_id = fields.Many2one('stock.production.lot','No Engine')
    customer_bpkb_id = fields.Many2one('res.partner','Nama BPKB')
    lokasi_bpkb = fields.Char('Lokasi BPKB')
    no_bpkb = fields.Char('No BPKB')
    tgl_penerimaan = fields.Date('Tanggal Penerimaan')
    finco_id = fields.Many2one('res.partner','Finance Company')
    umur = fields.Char('Umur')
    over_due = fields.Char('Over Due (Hari)')
    validasi_nama_bpkb = fields.Selection([
        ('Nama sesuai dengan buku','Nama sesuai dengan buku'),
        ('Nama tidak sesuai dengan buku','Nama tidak sesuai dengan buku'),
        ('-','-')],string="Validasi Nama BPKB")
    validasi_no_engine = fields.Selection([
        ('No mesin sesuai dengan buku','No mesin sesuai dengan buku'),
        ('No mesin tidak sesuai dengan buku','No mesin tidak sesuai dengan buku'),
        ('-','-')],string="Validasi No Engine")
    validasi_no_bpkb = fields.Selection([
        ('No BPKB sesuai dengan buku','No BPKB sesuai dengan buku'),
        ('No BPKB tidak sesuai dengan buku','No BPKB tidak sesuai dengan buku'),
        ('-','-')],string="Validasi No BPKB")
    validasi_ceklis_fisik_bpkb = fields.Selection([
        ('Fisik Ada','Fisik Ada'),
        ('Fisik di HO','Fisik di HO'),
        ('Fisik di GA','Fisik di GA'),
        ('Fisik di MD','Fisik di MD'),
        ('Revisi Biro Jasa','Revisi Biro Jasa'),
        ('Sudah Penyerahan ke Konsumen','Sudah Penyerahan ke Konsumen'),
        ('Sudah Penyerahan ke Leasing','Sudah Penyerahan ke Leasing'),
        ('Hilang / Fisik tidak diketahui','Hilang / Fisik tidak diketahui')],string="Ceklis Fisik BPKB")
    keterangan = fields.Char('Keterangan')

    @api.multi
    def write(self,vals):
        if vals.get('validasi_ceklis_fisik_bpkb'):
            if vals['validasi_ceklis_fisik_bpkb'] != 'Fisik Ada':
                vals['validasi_nama_bpkb'] = '-'
                vals['validasi_no_engine'] = '-'
                vals['validasi_no_bpkb'] = '-'
        return super(StockOpnameBPKBLine,self).write(vals)



    @api.onchange('validasi_ceklis_fisik_bpkb')
    def onchnage_validasi(self):
        self.validasi_nama_bpkb = False
        self.validasi_no_bpkb = False
        self.validasi_no_engine = False
        if self.validasi_ceklis_fisik_bpkb:
            if self.validasi_ceklis_fisik_bpkb != 'Fisik Ada':
                self.validasi_nama_bpkb = '-'
                self.validasi_no_engine = '-'
                self.validasi_no_bpkb = '-'

    @api.onchange('validasi_ceklis_fisik_bpkb','validasi_nama_bpkb')
    def onchange_validasi_nama_bpkb(self):
        warning = ''
        if self.validasi_ceklis_fisik_bpkb and self.validasi_nama_bpkb:
            if self.validasi_ceklis_fisik_bpkb == 'Fisik Ada' and self.validasi_nama_bpkb == '-':
                warning = {'title':'Perhatian !','message':'Validasi Nama BPKB tidak boleh - !'}
                self.validasi_nama_bpkb = False
            elif self.validasi_ceklis_fisik_bpkb != 'Fisik Ada' and self.validasi_nama_bpkb not in ('-',False):
                warning = {'title':'Perhatian !','message':'Validasi Nama BPKB tidak boleh selain - !'}    
                self.validasi_nama_bpkb = False
        return {'warning':warning}
    
    @api.onchange('validasi_ceklis_fisik_bpkb','validasi_no_bpkb')
    def onchange_validasi_no_bpkb(self):
        warning = ''
        if self.validasi_ceklis_fisik_bpkb and self.validasi_no_bpkb:
            if self.validasi_ceklis_fisik_bpkb == 'Fisik Ada' and self.validasi_no_bpkb == '-':
                warning = {'title':'Perhatian !','message':'Validasi No BPKB tidak boleh - !'}
                self.validasi_no_bpkb = False
            elif self.validasi_ceklis_fisik_bpkb != 'Fisik Ada' and self.validasi_no_bpkb not in ('-',False):
                warning = {'title':'Perhatian !','message':'Validasi No BPKB tidak boleh selain - !'}    
                self.validasi_no_bpkb = False
        return {'warning':warning}
   
    @api.onchange('validasi_ceklis_fisik_bpkb','validasi_no_engine')
    def onchange_validasi_no_engine(self):
        warning = ''
        if self.validasi_ceklis_fisik_bpkb and self.validasi_no_engine:
            if self.validasi_ceklis_fisik_bpkb == 'Fisik Ada' and self.validasi_no_engine == '-':
                warning = {'title':'Perhatian !','message':'Validasi No Engine tidak boleh - !'}
                self.validasi_no_engine = False
            elif self.validasi_ceklis_fisik_bpkb != 'Fisik Ada' and self.validasi_no_engine not in ('-',False):
                warning = {'title':'Perhatian !','message':'Validasi No Engine tidak boleh selain - !'}    
                self.validasi_no_engine = False
        return {'warning':warning}

class StockOpnameBPKBOther(models.Model):
    _name = "teds.stock.opname.bpkb.other"

    opname_id = fields.Many2one('teds.stock.opname.bpkb','Stock Opname',ondelete='cascade')
    nama_bpkb = fields.Char('Nama BPKB')
    no_engine = fields.Char('No Engine')
    keterangan = fields.Char('Keterangan')

class StockOpnameBPKBBaksoWizard(models.TransientModel):
    _name = "teds.stock.opname.bpkb.bakso.wizard"

    note_bakso = fields.Text('Note')
    opname_id = fields.Many2one('teds.stock.opname.bpkb','Stock Opname')
    
    @api.multi
    def action_submit_bakso(self):
        active_ids = self.env.context.get('active_ids', [])
        user = self.env['res.users'].browse(self._uid).name
        
        saldo_sistem = len(self.opname_id.detail_ids)
        saldo_cabang = 0
        saldo_ho = 0
        saldo_ga = 0
        saldo_md = 0
        saldo_birojasa = 0
        saldo_konsumen = 0
        saldo_leasing = 0
        saldo_lainnya = 0
        other_bpkb = len(self.opname_id.other_bpkb_ids)

        for line in self.opname_id.detail_ids:
            if line.validasi_ceklis_fisik_bpkb == 'Fisik Ada':
                saldo_cabang += 1
            elif line.validasi_ceklis_fisik_bpkb == 'Fisik di HO':
                saldo_ho += 1
            elif line.validasi_ceklis_fisik_bpkb == 'Fisik di GA':
                saldo_ga += 1
            elif line.validasi_ceklis_fisik_bpkb == 'Fisik di MD':
                saldo_md += 1    
            elif line.validasi_ceklis_fisik_bpkb == 'Revisi Biro Jasa':
                saldo_birojasa += 1
            elif line.validasi_ceklis_fisik_bpkb == 'Sudah Penyerahan ke Konsumen':
                saldo_konsumen += 1
            elif line.validasi_ceklis_fisik_bpkb == 'Sudah Penyerahan ke Leasing':
                saldo_leasing += 1                
            elif line.validasi_ceklis_fisik_bpkb == 'Hilang / Fisik tidak diketahui':
                saldo_lainnya += 1

        selisih_sistem_fisik = saldo_sistem - saldo_cabang -saldo_ho - saldo_ga - saldo_md - saldo_birojasa - saldo_konsumen - saldo_leasing - saldo_lainnya
        total_stock = saldo_cabang + other_bpkb 
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
            'saldo_ga':saldo_ga,
            'saldo_md':saldo_md,
            'saldo_birojasa':saldo_birojasa,
            'saldo_konsumen':saldo_konsumen,
            'saldo_leasing':saldo_leasing,
            'saldo_lainnya':saldo_lainnya,
            'selisih_sistem_fisik':selisih_sistem_fisik,
            'other_bpkb':other_bpkb,
            'total_stock':total_stock,
            'note_bakso':str(self.note_bakso) if self.note_bakso else '',
            'staff_bbn':str(self.opname_id.staff_bbn),
            'adh':str(self.opname_id.adh),
            'soh':str(self.opname_id.soh),
            'user': user,
            'date': (datetime.now() + timedelta(hours=7)).strftime('%Y-%d-%d %H:%M:%S'),

        }
        self.opname_id.note_bakso = self.note_bakso
        return self.env['report'].get_action(self,'teds_stock_opname.teds_stock_opname_bpkb_print_bakso', data=datas)
