from openerp import models, fields, api
from datetime import date, datetime, timedelta,time
from dateutil.relativedelta import relativedelta
from openerp.exceptions import Warning

class StockOpnameAsset(models.Model):
    _name = "teds.stock.opname.asset"

    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()
    
    @api.model
    def _get_default_datetime(self):
        return datetime.now()

    @api.multi
    def _get_category_asset(self):
        ids = [('All','All')]
        query = """
            SELECT code
            FROM account_asset_category
            group by code
        """
        self.env.cr.execute(query)  
        ress = self.env.cr.dictfetchall()
        for res in ress:
            ids.append((res.get('code'),(res.get('code'))))
        return ids

    name = fields.Char('Name',index=True)
    branch_id = fields.Many2one('wtc.branch','Branch',index=True)
    date = fields.Date('Tanggal SO',default=_get_default_date)
    pdi = fields.Char('PDI / Kamek / SA')
    adh = fields.Char('ADH')
    soh = fields.Char('SOH')
    kategory = fields.Selection(_get_category_asset,string="Kategory")
    status = fields.Selection([('all','All'), ('active','Active'), ('disposed','Disposed'), ('draft','Draft')],default="active")
    post_date = fields.Datetime('Posted on')
    post_uid = fields.Many2one('res.users','Posted by')
    generate_date = fields.Datetime('Generate on')
    state = fields.Selection([
        ('draft','Draft'),
        ('posted','Posted')],default="draft")
    detail_ids = fields.One2many('teds.stock.opname.asset.line','opname_id')
    other_asset_ids = fields.One2many('teds.stock.opname.asset.other','opname_id')
    note_bakso = fields.Text('Note')

    @api.model
    def create(self,vals):
        # cek = self.search([
        #     ('branch_id','=',vals['branch_id']),
        #     ('state','!=','posted')])
        # if cek:
        #     raise Warning('Perhatian ! Masih ada stock opname yang belum selesai !')

        vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'SOAST')
        if vals.get('pdi'):
            vals['pdi'] = vals['pdi'].title()
        if vals.get('adh'):
            vals['adh'] = vals['adh'].title()
        if vals.get('soh'):
            vals['soh'] = vals['soh'].title()
        return super(StockOpnameAsset,self).create(vals)
    
    @api.multi
    def write(self,vals):
        if vals.get('pdi'):
            vals['pdi'] = vals['pdi'].title()
        if vals.get('adh'):
            vals['adh'] = vals['adh'].title()
        if vals.get('soh'):
            vals['soh'] = vals['soh'].title()
        return super(StockOpnameAsset,self).write(vals)

    @api.multi
    def unlink(self):
        for data in self:
            if data.state != "draft":
                raise Warning("Tidak bisa menghapus data yang berstatus selain draft!")
        return super(StockOpnameAsset, self).unlink()

    @api.multi
    def action_generate_stock(self):
        query_where = "WHERE 1=1"
        if self.branch_id:
            query_where += " AND asset.branch_id = %d" %self.branch_id
        
        if self.status == 'draft' :
            query_where += " AND asset.state = 'draft'"
        elif self.status == 'active' :
            query_where += " AND asset.state in ('open','CIP','close') "
        elif self.status == 'disposed' :
            query_where += " AND asset.state = 'disposed'"
        
        if self.kategory:
            if self.kategory != 'All':
                query_where += " AND category.code = '%s'" %self.kategory

        query = """
            SELECT asset.code as asset_code
            , asset.name as asset_name
            , category.name as category_name
            , category.code as category_code
            FROM account_asset_asset asset
            INNER JOIN account_asset_category category ON category.id = asset.category_id
            %s
            ORDER BY asset_name,asset_code ASC
        """ %(query_where)
        self.env.cr.execute(query)
        ress = self.env.cr.dictfetchall()
        lines = []
        for res in ress:
            lines.append([0,False,{
                'code':res.get('asset_code'),
                'name':res.get('asset_name'),
                'kategory':res.get('category_code'),
                'description':res.get('category_name'),
            }])
        self.write({
            'generate_date':self._get_default_datetime(),
            'detail_ids':lines
        })

    @api.multi
    def action_post(self):
        line = self.env['teds.stock.opname.asset.line'].search([
            ('opname_id','=',self.id),
            ('validasi_lokasi','=',False)],limit=1)
        if line:
            raise Warning('Perhatian ! Ceklis Validasi Lokasi masih ada yang belum diisi !')
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
        other_asset_ids = []

        for other in self.other_asset_ids:
            other_asset_ids.append({
                'branch_code':self.branch_id.code,
                'nama_asset':other.name,
                'lokasi_fisik_asset':other.lokasi_fisik_unit,
                'pic_asset':other.pic,
                'kondisi_fisik_asset':other.kondisi_fisik,
                'no_mesin':other.no_mesin,
                'keterangan':other.keterangan,
            })
        
        for line in self.detail_ids:
            detail_ids.append({
                'branch_code':self.branch_id.code,
                'kode_asset':line.code,
                'nama_asset':line.name,
                'kategory':line.kategory,
                'description':line.description,
                'lokasi_fisik_asset':line.validasi_lokasi,
                'pic_asset':line.validasi_pic,
                'kondisi_fisik_asset':line.validasi_kondisi_fisik,
                'no_mesin':line.no_mesin,
                'keterangan':line.keterangan,
            })

        datas = {
            'ids': active_ids,
            'user': user,
            'date': (datetime.now() + timedelta(hours=7)).strftime('%Y-%d-%d %H:%M:%S'),
            'name':str(self.name),
            'branch_id':str(self.branch_id.name_get().pop()[1]),
            'tgl_so':self.date,
            'pdi':self.pdi,
            'soh': self.soh,
            'adh':self.adh,
            'detail_ids':detail_ids,
            'generate_date':str(datetime.strptime(self.generate_date, '%Y-%m-%d %H:%M:%S') + relativedelta(hours=7)),
            'other_asset_ids':other_asset_ids,
            'create_uid':self.create_uid.name,
            'create_date': str(datetime.strptime(self.create_date, '%Y-%m-%d %H:%M:%S') + relativedelta(hours=7)),
        }
        return self.env['report'].get_action(self,'teds_stock_opname_asset.teds_stock_opname_asset_print_validasi', data=datas)

    @api.multi
    def action_bakso(self):
        form_id = self.env.ref('teds_stock_opname_asset.view_teds_so_asset_bakso_wizard').id
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Berita Acara SO',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.stock.opname.asset.bakso.wizard',
            'context':{'default_opname_id':self.id,'default_note_bakso':self.note_bakso},
            'views': [(form_id, 'form')],
            'target':'new'
        }    

    @api.multi
    def action_download_excel(self):
        obj_x = self.env['teds.stock.opname.asset.wizard'].create({'opname_asset_id':self.id})
        obj_x.action_download_excel()
        return {
            'type': 'ir.actions.act_url',
            'name': 'contract',
            'url':'/web/binary/saveas?model=teds.stock.opname.asset.wizard&field=file_excel&filename_field=name&id=%d'%(obj_x.id)
        }

class StockOpnameAssetLine(models.Model):
    _name = "teds.stock.opname.asset.line"

    @api.multi
    def get_validasi_pic(self):
        ids = []
        query = """
            SELECT name
            FROM teds_stock_opname_asset_pic
            group by name
        """
        self.env.cr.execute(query)  
        ress = self.env.cr.dictfetchall()
        for res in ress:
            ids.append((res.get('name'),(res.get('name'))))
        return ids


    opname_id = fields.Many2one('teds.stock.opname.asset','Stock Opname',ondelete='cascade')
    code = fields.Char('Kode Asset')
    name = fields.Char('Nama Asset')
    kategory = fields.Char('Kategory')
    description = fields.Char('Description')
    validasi_lokasi = fields.Selection([
        ('Di Cabang','Di Cabang'),
        ('Dipinjam PIC','Dipinjam PIC'),
        ('Hilang','Hilang'),
        ('Tidak Ada','Tidak Ada')],string='Lokasi Fisik Asset')
    validasi_pic = fields.Selection(get_validasi_pic,'PIC Asset')
    validasi_kondisi_fisik = fields.Selection([
        ('Baik','Baik'),
        ('Rusak','Rusak'),
        ('Mati','Mati'),
        ('-','-')],string="Kondisi Fisik Asset")
    no_mesin = fields.Char('No Mesin')
    keterangan = fields.Char('Keterangan')

    @api.model
    def create(self,vals):
        if vals.get('kategory'):
            if vals['kategory'] != 'V':
                vals['no_mesin'] = '-'
        return super(StockOpnameAssetLine,self).create(vals)

    @api.multi
    def write(self,vals):
        if vals.get('kategory'):
            if vals['kategory'] != 'V':
                vals['no_mesin'] = '-'
        if vals.get('validasi_lokasi'):
            if vals['validasi_lokasi'] in ('Tidak Ada','Hilang'):
                vals['validasi_pic'] = '-'
                vals['validasi_kondisi_fisik'] = '-'
                vals['no_mesin'] = '-'
        return super(StockOpnameAssetLine,self).write(vals)

    @api.onchange('no_mesin','validasi_lokasi')
    def onchange_no_mesin(self):
        warning = ""
        if self.no_mesin and self.validasi_lokasi:
            if self.validasi_lokasi not in ('Tidak Ada','Hilang') and self.no_mesin != '-' and len(self.no_mesin) != 12:
                warning = {'title':'Perhatian !','message':'No Mesin harus 12 digit !'}
                self.no_mesin = False
        return {'warning':warning}
    
    @api.onchange('validasi_lokasi')
    def onchange_validasi_lokasi(self):
        self.validasi_pic = False
        self.validasi_kondisi_fisik = False
        self.no_mesin = False
        if self.validasi_lokasi:
            if self.validasi_lokasi in ('Tidak Ada','Hilang'):
                self.validasi_pic = '-'
                self.validasi_kondisi_fisik = '-'
                self.no_mesin = '-'
                

class StockOpnameAssetOther(models.Model):
    _name = "teds.stock.opname.asset.other"

    @api.multi
    def get_validasi_pic(self):
        ids = []
        query = """
            SELECT name
            FROM teds_stock_opname_asset_pic
            group by name
        """
        self.env.cr.execute(query)  
        ress = self.env.cr.dictfetchall()
        for res in ress:
            ids.append((res.get('name'),(res.get('name'))))
        return ids

    opname_id = fields.Many2one('teds.stock.opname.asset','Stock Opname',ondelete='cascade')
    name = fields.Char('Nama Asset')
    lokasi_fisik_unit = fields.Selection([
        ('Di Cabang','Di Cabang'),
        ('Dipinjam PIC','Dipinjam PIC'),
        ('Tidak diketahui','Tidak diketahui'),
        # ('Hilang','Hilang'),
        # ('Tidak Ada','Tidak Ada'),
        ('-','-')],string='Status Unit')
    pic = fields.Selection(get_validasi_pic,'PIC Asset')
    kondisi_fisik = fields.Selection([
        ('Baik','Baik'),
        ('Rusak','Rusak'),
        ('Mati','Mati'),
        ('-','-')],string="Kondisi Fisik Asset")
    no_mesin = fields.Char('No Mesin')
    keterangan = fields.Char('Keterangan')

class StockOpnameAssetBaksoWizard(models.TransientModel):
    _name = "teds.stock.opname.asset.bakso.wizard"

    note_bakso = fields.Text('Note')
    opname_id = fields.Many2one('teds.stock.opname.asset','Stock Opname')
    
    @api.multi
    def action_submit_bakso(self):
        active_ids = self.env.context.get('active_ids', [])
        user = self.env['res.users'].browse(self._uid).name
        
        saldo_sistem = len(self.opname_id.detail_ids)
        saldo_cabang = 0
        saldo_pic = 0
        saldo_hilang = 0
        saldo_tidak_ada = 0
        other_asset = len(self.opname_id.other_asset_ids)

        for line in self.opname_id.detail_ids:
            if line.validasi_lokasi == 'Di Cabang':
                saldo_cabang += 1
            elif line.validasi_lokasi == 'Dipinjam PIC':
                saldo_pic += 1
            elif line.validasi_lokasi == 'Hilang':
                saldo_hilang += 1
            elif line.validasi_lokasi == 'Tidak Ada':
                saldo_tidak_ada += 1

        total_stock = saldo_cabang + other_asset + saldo_pic 
        datas = {
            'ids': active_ids,
            'name':str(self.opname_id.name),
            'branch':str(self.opname_id.branch_id.name_get().pop()[1]),
            'tgl_so':self.opname_id.date,
            'jam_mulai': str(datetime.strptime(self.opname_id.generate_date, '%Y-%m-%d %H:%M:%S') + relativedelta(hours=7)),
            'jam_selesai': str(datetime.strptime(self.opname_id.post_date, '%Y-%m-%d %H:%M:%S') + relativedelta(hours=7)),
            'saldo_sistem': saldo_sistem,
            'saldo_cabang':saldo_cabang,
            'saldo_pic':saldo_pic,
            'saldo_hilang':saldo_hilang,
            'saldo_tidak_ada':saldo_tidak_ada,
            'other_asset':other_asset,
            'total_stock':total_stock,
            'note_bakso':str(self.note_bakso) if self.note_bakso else '',
            'pdi':str(self.opname_id.pdi),
            'adh':str(self.opname_id.adh),
            'soh':str(self.opname_id.soh),
            'user': user,
            'date': (datetime.now() + timedelta(hours=7)).strftime('%Y-%d-%d %H:%M:%S'),
        }
        print "datas>>>>>>>>>>>>>",datas
        self.opname_id.note_bakso = self.note_bakso
        
        return self.env['report'].get_action(self,'teds_stock_opname_asset.teds_stock_opname_asset_print_bakso', data=datas)
