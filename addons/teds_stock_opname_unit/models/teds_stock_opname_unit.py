from openerp import models, fields, api
from datetime import date, datetime, timedelta,time
from dateutil.relativedelta import relativedelta
from openerp.exceptions import Warning

class StockOpnameUnit(models.Model):
    _name = "teds.stock.opname.unit"
    
    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()
    
    @api.model
    def _get_default_datetime(self):
        return datetime.now()

    
    @api.one
    @api.depends('detail_ids')
    def _compute_unit(self):
        total_fisik = 0
        total_unit = 0
        for x in self.detail_ids:
            fisik = 0
            sistem = 1
            if x.validasi_fisik in ('Fisik Ada','Mutasi POS/PMR/CHN'):
                fisik = 1

            total_fisik += fisik
            total_unit += sistem
        self.total_unit = total_unit
        self.total_fisik = total_fisik


    name = fields.Char('Name',index=True)
    branch_id = fields.Many2one('wtc.branch','Branch',index=True)
    date = fields.Date('Tanggal SO',default=_get_default_date)
    staff_bbn = fields.Char('PDI')
    adh = fields.Char('ADH')
    soh = fields.Char('SOH')
    post_date = fields.Datetime('Posted on')
    post_uid = fields.Many2one('res.users','Posted by')
    generate_date = fields.Datetime('Generate on')
    state = fields.Selection([
        ('draft','Draft'),
        ('posted','Posted')],default="draft")
    division = fields.Selection([('Unit','Unit')],default="Unit")
    detail_ids = fields.One2many('teds.stock.opname.unit.line','opname_id')
    aksesoris_ids = fields.One2many('teds.stock.opname.aksesoris.unit','opname_id')
    total_unit = fields.Integer('Total Sistem',compute='_compute_unit')
    total_fisik = fields.Integer('Total Fisik',compute='_compute_unit')
    note_bakso_unit = fields.Text('Note')
    note_bakso_aksesoris = fields.Text('Note')


    @api.model
    def create(self,vals):
        cek = self.search([
            ('branch_id','=',vals['branch_id']),
            ('state','!=','posted')])
        if cek:
            raise Warning('Perhatian ! Masih ada stock opname yang belum selesai !')
        
        vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'SOMT')
        if vals.get('staff_bbn'):
            vals['staff_bbn'] = vals['staff_bbn'].title()
        if vals.get('adh'):
            vals['adh'] = vals['adh'].title()
        if vals.get('soh'):
            vals['soh'] = vals['soh'].title()
        return super(StockOpnameUnit,self).create(vals)
    
    @api.multi
    def write(self,vals):
        if vals.get('staff_bbn'):
            vals['staff_bbn'] = vals['staff_bbn'].title()
        if vals.get('adh'):
            vals['adh'] = vals['adh'].title()
        if vals.get('soh'):
            vals['soh'] = vals['soh'].title()
        return super(StockOpnameUnit,self).write(vals)

    @api.multi
    def unlink(self):
        for data in self:
            if data.state != "draft":
                raise Warning("Tidak bisa menghapus data yang berstatus selain draft!")
        return super(StockOpnameUnit, self).unlink()

    @api.multi
    def action_generate_stock(self):
        query = """
            SELECT branch_name
            , branch_code
            , tipe
            , warna
            , in_date+ INTERVAL '7 hours' as incoming_date
            , engine_no
            , chassis_no
            , complete_name as lokasi
            , prod_tmpl_id
            , description
            , prod_ext
            , categ_ext
            FROM (
            (
                SELECT b.name as branch_name
                , b.code as branch_code
                , prod.name_template as tipe
                , pav.name as warna
                , lot.name as engine_no
                , lot.chassis_no
                , loc.complete_name
                , quant.in_date
                , pt.id as prod_tmpl_id
                , pt.description
                , ex1.product_id as prod_ext
                , cat_x1.name as categ_ext
                FROM stock_quant quant
                INNER JOIN stock_production_lot lot ON quant.lot_id = lot.id
                INNER JOIN product_product prod ON quant.product_id = prod.id
                INNER JOIN stock_location loc ON quant.location_id = loc.id
                LEFT JOIN wtc_branch b on loc.branch_id = b.id
                LEFT JOIN product_template pt on prod.product_tmpl_id = pt.id
                LEFT JOIN product_category cat on pt.categ_id = cat.id
                LEFT JOIN product_category cat2 on cat.parent_id = cat2.id
                LEFT JOIN product_category cat3 on cat2.parent_id = cat3.id
                LEFT JOIN product_attribute_value_product_product_rel pavpp on prod.id = pavpp.prod_id
                LEFT JOIN product_attribute_value pav on pavpp.att_id = pav.id
                LEFT JOIN wtc_barang_extras ex1 on ex1.barang_extras_id = pt.id
                LEFT JOIN product_product pp_x1 on pp_x1.id = ex1.product_id
                LEFT JOIN product_template pt_x1 on pp_x1.product_tmpl_id = pt_x1.id
                LEFT JOIN product_category cat_x1 on cat_x1.id = pt_x1.categ_id
                
                WHERE cat3.name = 'Unit' and (loc.usage = 'internal' or loc.usage = 'transit' or loc.usage = 'nrfs')
            )-- and quant.consolidated_date is not null)
            UNION
            (
                SELECT b.name as branch_name
                , b.code as branch_code
                , prod.name_template as tipe
                , pav.name as warna
                , lot.name as engine_no
                , lot.chassis_no
                , loc.complete_name
                , lot.create_date as in_date
                , pt.id as prod_tmpl_id
                , pt.description
                , ex2.product_id as prod_ext
                , cat_x2.name as categ_ext
                FROM stock_production_lot lot
                INNER JOIN product_product prod on lot.product_id = prod.id
                LEFT JOIN wtc_branch b on lot.branch_id = b.id
                LEFT JOIN stock_location loc on lot.location_id = loc.id
                LEFT JOIN product_template pt on prod.product_tmpl_id = pt.id
                LEFT JOIN product_category cat on pt.categ_id = cat.id
                LEFT JOIN product_category cat2 on cat.parent_id = cat2.id
                LEFT JOIN product_category cat3 on cat2.parent_id = cat3.id
                LEFT JOIN product_attribute_value_product_product_rel pavpp on prod.id = pavpp.prod_id
                LEFT JOIN product_attribute_value pav on pavpp.att_id = pav.id
                LEFT JOIN wtc_barang_extras ex2 on ex2.barang_extras_id = pt.id
                LEFT JOIN product_product pp_x2 on pp_x2.id = ex2.product_id
                LEFT JOIN product_template pt_x2 on pp_x2.product_tmpl_id = pt_x2.id
                LEFT JOIN product_category cat_x2 on cat_x2.id = pt_x2.categ_id
                WHERE lot.state = 'intransit' and b.branch_type = 'MD'
            )
            ) a
            WHERE branch_code = '%s'
            ORDER BY tipe
        """ %(self.branch_id.code)
        self.env.cr.execute(query)
        ress = self.env.cr.dictfetchall()
        extras_ids = {}
        lines = []
        aksesoris_ids = []
        lst_engine = {}
        lst_aks = {}

        for res in ress:
            # if len(lst_engine) <= 2:
                if not lst_engine.get(res.get('engine_no')):
                    lines.append([0,False,{
                        'name':res.get('description'),
                        'chassis_no':res.get('chassis_no'),
                        'engine_no':res.get('engine_no'),
                        'product_type':res.get('tipe'),
                        'product_warna':res.get('warna'),
                        'incoming_date':res.get('incoming_date'),
                        'lokasi':res.get('lokasi'),
                    }])
                lst_engine[res.get('engine_no')] = res.get('engine_no')

                if not extras_ids.get(res.get('prod_ext')):
                    extras_ids[res.get('prod_ext')] = 1
                else:
                    extras_ids[res.get('prod_ext')] += 1

                if not lst_aks.get(res.get('categ_ext')):
                    lst_aks[res.get('categ_ext')] = 1
                else:
                    lst_aks[res.get('categ_ext')] += 1

        total_unit = len(lst_engine)

        query_aksesoris = """
            SELECT pp.id as pp_id
            , pt.name as prod_name
            , cat.name as cat_name
            , cat.id as cat_id
            FROM product_product pp
            INNER JOIN product_template pt ON pt.id = pp.product_tmpl_id
            LEFT JOIN product_category cat on pt.categ_id = cat.id
            WHERE pp.id in %s
            ORDER BY cat.name ASC
        """ %(str(tuple(extras_ids.keys()))).replace(',)', ')')
        self.env.cr.execute(query_aksesoris)
        ress2 = self.env.cr.dictfetchall()
        aks_ids = {}
        # for res2 in ress2:
        #     if res2.get('cat_name') in ('Battery'):
        #         aksesoris_ids.append([0,False,{
        #             'name':res2.get('prod_name'),
        #             'category':res2.get('cat_name'),
        #             'total_unit':extras_ids.get(res2.get('pp_id'))
        #         }])
        # Disini ubah default aksesoris
        aksesoris_ids.append([0,False,{
            'name':'Battery',
            'category':'Battery',
            # 'total_unit':lst_aks.get('Battery',0) 
            'total_unit':total_unit 
        }])
        aksesoris_ids.append([0,False,{
            'name':'Buku Service',
            'category':'Buku Service',
            # 'total_unit':lst_aks.get('Buku Service',0)    
            'total_unit':total_unit
        }])
        aksesoris_ids.append([0,False,{
            'name':'Helm',
            'category':'Helm',
            # 'total_unit':lst_aks.get('Helm',0)    
            'total_unit':total_unit
        }])
        aksesoris_ids.append([0,False,{
            'name':'Spion',
            'category':'Spion',
            # 'total_unit':lst_aks.get('Spion',0)    
            'total_unit':total_unit
        }])
        aksesoris_ids.append([0,False,{
            'name':'Tools',
            'category':'Tools',
            # 'total_unit':lst_aks.get('Tools',0)    
            'total_unit':total_unit
        }])

        self.write({
            'generate_date':self._get_default_datetime(),
            'detail_ids':lines,
            'aksesoris_ids':aksesoris_ids,
        })            

    @api.multi
    def action_post(self):
        if not self.detail_ids:
            raise Warning('Data Stock Unit tidak boleh kosong !')
        for aks in self.aksesoris_ids:
            if aks.total == 0:
                raise Warning('Perhatian ! Silahkan cek kembali total aksesoris !')
            
        line = self.env['teds.stock.opname.unit.line'].search([
            ('opname_id','=',self.id),
            ('validasi_fisik','=',False)],limit=1)
        if line:
            raise Warning('Perhatian ! Validasi Fisik Unit masih ada yang belum diisi !')

        
        self.write({
            'post_uid':self._uid,
            'post_date':self._get_default_datetime(),
            'state':'posted',
        })

    @api.multi
    def action_print_validasi_aksesoris(self):
        active_ids = self.env.context.get('active_ids', [])
        user = self.env['res.users'].browse(self._uid).name
        aksesoris_ids = []

       
        for line in self.aksesoris_ids:
            aksesoris_ids.append({
                'product':line.name,
                'category':line.category,
                'qty_good':line.qty_good,
                'qty_not_good':line.qty_not_good,
                'total':line.total,
                'total_unit':line.total_unit,
                'ket_not_good':line.ket_not_good,
                'last_not_good':line.last_not_good,
                'selisih':line.selisih,
                'keterangan_selisih':line.keterangan_selisih,
                'selisih_so_lalu':line.selisih_so_lalu,

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
            'detail_ids':aksesoris_ids,
            'create_uid':self.create_uid.name,
            'create_date': str(datetime.strptime(self.create_date, '%Y-%m-%d %H:%M:%S') + relativedelta(hours=7)),
        }
        return self.env['report'].get_action(self,'teds_stock_opname_unit.teds_stock_opname_aksesoris_unit_print_validasi', data=datas)

    
    
    @api.multi
    def action_print_validasi(self):
        active_ids = self.env.context.get('active_ids', [])
        user = self.env['res.users'].browse(self._uid).name
        detail_ids = []

        for line in self.detail_ids:
            split_lokasi = line.lokasi.split('/')
            lokasi = line.lokasi
            if len(split_lokasi) == 3:
                lokasi = str(split_lokasi[-2].strip())+"-"+str(split_lokasi[-1].strip())
            else:
                lokasi = str(split_lokasi[-1].strip())
                
            detail_ids.append({
                'name':line.name,
                'engine_no':line.engine_no,
                'chassis_no':line.chassis_no,
                'product_type':line.product_type,
                'product_warna':line.product_warna,
                'incoming_date':line.incoming_date,
                'lokasi':lokasi,
                'validasi_chassis':line.validasi_chassis,
                'validasi_engine':line.validasi_engine,
                'validasi_fisik':line.validasi_fisik,
                'validasi_warna':line.validasi_warna,
                'validasi_taging':line.validasi_taging,
                'kondisi_fisik':line.kondisi_fisik,
                'keterangan':line.keterangan,
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
            'create_uid':self.create_uid.name,
            'create_date': str(datetime.strptime(self.create_date, '%Y-%m-%d %H:%M:%S') + relativedelta(hours=7)),
        }
        return self.env['report'].get_action(self,'teds_stock_opname_unit.teds_stock_opname_unit_print_validasi', data=datas)

    
    @api.multi
    def action_bakso(self):
        form_id = self.env.ref('teds_stock_opname_unit.view_teds_so_unit_bakso_wizard').id
    
        return {
            'type': 'ir.actions.act_window',
            'name': 'Berita Acara SO Unit',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.stock.opname.unit.bakso.wizard',
            'context':{'default_opname_id':self.id},
            'views': [(form_id, 'form')],
            'target':'new'
        }
        
    @api.multi
    def action_download_excel(self):
        obj_x = self.env['teds.stock.opname.unit.wizard'].create({'opname_unit_id':self.id})
        obj_x.action_download_excel()
        return {
            'type': 'ir.actions.act_url',
            'name': 'contract',
            'url':'/web/binary/saveas?model=teds.stock.opname.unit.wizard&field=file_excel&filename_field=name&id=%d'%(obj_x.id)
        }
        

class StockOpnameUnitLine(models.Model):
    _name = "teds.stock.opname.unit.line"

    
    @api.one
    @api.depends('qty_fisik_baik','qty_fisik_rusak')
    def _compute_fisik_total(self):
        self.qty_fisik_total = self.qty_fisik_baik + self.qty_fisik_rusak
    
    @api.one
    @api.depends('harga_satuan','qty')
    def _compute_amount(self):
        self.amount = self.harga_satuan * self.qty
    
    @api.one
    @api.depends('harga_satuan','qty_fisik_total')
    def _compute_amount_total(self):
        self.amount_total = self.harga_satuan * self.qty_fisik_total
    
    @api.one
    @api.depends('qty','qty_fisik_total')
    def _compute_selisih_qty(self):
        self.selisih_qty = self.qty_fisik_total - self.qty
    
    @api.one
    @api.depends('harga_satuan','selisih_qty')
    def _compute_selisih_amount(self):
        self.selisih_amount = self.harga_satuan * self.selisih_qty


    opname_id = fields.Many2one('teds.stock.opname.unit','Stock Opname',ondelete='cascade')
    name = fields.Char('Product')
    engine_no = fields.Char('Engine No')
    chassis_no = fields.Char('Chassis No')
    product_type = fields.Char('Product Type')
    product_warna = fields.Char('Warna')
    incoming_date = fields.Char('Incoming Date')
    lokasi = fields.Char('Location')

    validasi_chassis = fields.Selection([
        ('No Rangka Sesuai','No Rangka Sesuai'),
        ('No Rangka Tidak Sesuai','No Rangka Tidak Sesuai'),
        ('-','-')],string="Validasi Chassis")
    validasi_engine = fields.Selection([
        ('No Mesin Sesuai','No Mesin Sesuai'),
        ('No Mesin Tidak Sesuai','No Mesin Tidak Sesuai'),
        ('-','-')],string="Validasi Engine")
    validasi_fisik = fields.Selection([
        ('Fisik Ada','Fisik Ada'),
        ('Terjual','Terjual'),
        ('Mutasi POS/PMR/CHN','Mutasi POS/PMR/CHN'),
        ('Mutasi Cabang Lain','Mutasi Cabang Lain'),
        ('Return ke MD','Return ke MD'),
        ('Hilang / Tidak diketahui','Hilang / Tidak diketahui')],string="Validasi Fisik")
    validasi_warna = fields.Selection([
        ('Warna Sesuai','Warna Sesuai'),
        ('Warna Tidak Sesuai','Warna Tidak Sesuai'),
        ('-','-')],string="Validasi Warna")
    validasi_taging = fields.Selection([
        ('Taging Warna & Huruf Sesuai','Taging Warna & Huruf Sesuai'),
        ('Taging Warna & Huruf Tidak Sesuai','Taging Warna & Huruf Tidak Sesuai'),
        ('-','-')],string="Validasi Taging")
    kondisi_fisik = fields.Selection([
        ('Fisik Baik','Fisik Baik'),
        ('Fisik Rusak / Lecet','Fisik Rusak / Lecet'),
        ('Fisik Rubbing','Fisik Rubbing'),
        ('Fisik Return ke MD','Fisik Return ke MD'),
        ('-','-')],string="Kondisi Fisik")
    keterangan = fields.Char('Keterangan')

    @api.multi
    def write(self,vals):
        if vals.get('validasi_fisik'):
            if vals['validasi_fisik'] != 'Fisik Ada':
                vals['validasi_chassis'] = '-'
                vals['validasi_engine'] = '-'
                vals['validasi_warna'] = '-'
                vals['validasi_taging'] = '-'
                vals['kondisi_fisik'] = '-'
        return super(StockOpnameUnitLine,self).write(vals)

    @api.onchange('selisih')
    def onchange_selisih(self):
        self.keterangan_selisih = False
    
    @api.onchange('qty_not_good')
    def onchange_not_good(self):
        self.ket_not_good = False

    @api.onchange('validasi_fisik')
    def onchnage_validasi(self):
        self.validasi_chassis = False
        self.validasi_engine = False
        self.validasi_warna = False
        self.validasi_taging = False
        self.kondisi_fisik = False
        if self.validasi_fisik:
            if self.validasi_fisik != 'Fisik Ada':
                self.validasi_chassis = '-'
                self.validasi_engine = '-'
                self.validasi_warna = '-'
                self.validasi_taging = '-'
                self.kondisi_fisik = '-'

    @api.onchange('validasi_fisik','validasi_chassis')
    def onchange_validasi_chassis(self):
        warning = ''
        if self.validasi_fisik and self.validasi_chassis:
            if self.validasi_fisik == 'Fisik Ada' and self.validasi_chassis == '-':
                warning = {'title':'Perhatian !','message':'Validasi Chassis tidak boleh - !'}
                self.validasi_chassis = False
            elif self.validasi_fisik != 'Fisik Ada' and self.validasi_chassis not in ('-',False):
                warning = {'title':'Perhatian !','message':'Validasi Chassis tidak boleh selain - !'}    
                self.validasi_chassis = False
        return {'warning':warning}

    @api.onchange('validasi_fisik','validasi_engine')
    def onchange_validasi_engine(self):
        warning = ''
        if self.validasi_fisik and self.validasi_engine:
            if self.validasi_fisik == 'Fisik Ada' and self.validasi_engine == '-':
                warning = {'title':'Perhatian !','message':'Validasi Engine tidak boleh - !'}
                self.validasi_engine = False
            elif self.validasi_fisik != 'Fisik Ada' and self.validasi_engine not in ('-',False):
                warning = {'title':'Perhatian !','message':'Validasi Engine tidak boleh selain - !'}    
                self.validasi_engine = False
        return {'warning':warning}
    
    @api.onchange('validasi_fisik','validasi_warna')
    def onchange_validasi_warna(self):
        warning = ''
        if self.validasi_fisik and self.validasi_warna:
            if self.validasi_fisik == 'Fisik Ada' and self.validasi_warna == '-':
                warning = {'title':'Perhatian !','message':'Validasi Warna tidak boleh - !'}
                self.validasi_warna = False
            elif self.validasi_fisik != 'Fisik Ada' and self.validasi_warna not in ('-',False):
                warning = {'title':'Perhatian !','message':'Validasi Warna tidak boleh selain - !'}    
                self.validasi_warna = False
        return {'warning':warning}
    
    @api.onchange('validasi_fisik','validasi_taging')
    def onchange_validasi_taging(self):
        warning = ''
        if self.validasi_fisik and self.validasi_taging:
            if self.validasi_fisik == 'Fisik Ada' and self.validasi_taging == '-':
                warning = {'title':'Perhatian !','message':'Validasi Taging tidak boleh - !'}
                self.validasi_taging = False
            elif self.validasi_fisik != 'Fisik Ada' and self.validasi_taging not in ('-',False):
                warning = {'title':'Perhatian !','message':'Validasi Taging tidak boleh selain - !'}    
                self.validasi_taging = False
        return {'warning':warning}

    @api.onchange('validasi_fisik','kondisi_fisik')
    def onchange_kondisi_fisik(self):
        warning = ''
        if self.validasi_fisik and self.kondisi_fisik:
            if self.validasi_fisik == 'Fisik Ada' and self.kondisi_fisik == '-':
                warning = {'title':'Perhatian !','message':'Kondisi Fisik tidak boleh - !'}
                self.kondisi_fisik = False
            elif self.validasi_fisik != 'Fisik Ada' and self.kondisi_fisik not in ('-',False):
                warning = {'title':'Perhatian !','message':'Kondisi Fisik tidak boleh selain - !'}    
                self.kondisi_fisik = False
        return {'warning':warning}





class StockOpnameAksesorisUnit(models.Model):
    _name = "teds.stock.opname.aksesoris.unit"

    @api.one
    @api.depends('qty_good','qty_not_good')
    def compute_total(self):
        self.total = self.qty_good + self.qty_not_good
    
    @api.one
    @api.depends('total','total_unit')
    def selisih_aksesoris(self):
        self.selisih = self.total_unit - self.total

    opname_id = fields.Many2one('teds.stock.opname.unit',ondelete='cascade')
    name = fields.Char('Product Aksesoris')
    category = fields.Char('Category')
    qty_good = fields.Float('Good')
    qty_not_good = fields.Float('Not Good')
    total = fields.Float('Total Fisik',compute='compute_total')
    total_unit = fields.Float('Total Unit')
    ket_not_good = fields.Char('Ket Not Good')
    last_not_good = fields.Float('(+/- NG dr SO lalu)')
    selisih = fields.Float('Selisih',compute='selisih_aksesoris')
    keterangan_selisih = fields.Char('Ket Selisih')
    selisih_so_lalu = fields.Float('Selisih SO Lalu')

class StockOpnameUnitBaksoWizard(models.TransientModel):
    _name = "teds.stock.opname.unit.bakso.wizard"

    note_bakso = fields.Text('Note')
    opname_id = fields.Many2one('teds.stock.opname.unit','Stock Opname')
    tipe = fields.Selection([('Unit','Unit'),('Aksesoris','Aksesoris')])
    
    @api.onchange('tipe')
    def onchange_tipe(self):
        if self.tipe == 'Unit':
            self.note_bakso = self.opname_id.note_bakso_unit
        elif self.tipe == 'Aksesoris':
            self.note_bakso = self.opname_id.note_bakso_aksesoris

    @api.multi
    def action_submit_bakso(self):
        if self.tipe == 'Unit':
            return self.action_bakso_unit()
        else:
            return self.action_bakso_aksesoris()

    def action_bakso_unit(self):
        active_ids = self.env.context.get('active_ids', [])
        user = self.env['res.users'].browse(self._uid).name
        
        prod_ids = {}
        nrfs_ids = []
        total_sistem = 0
        total_fisik = 0
        for x in self.opname_id.detail_ids:
            fisik = 0
            sistem = 1
            if x.validasi_fisik in ('Fisik Ada','Mutasi POS/PMR/CHN'):
                fisik = 1

            if x.kondisi_fisik in ('Fisik Rusak / Lecet','Fisik Rubbing','Fisik Return ke MD'):
                nrfs_ids.append({
                    'engine_no':x.engine_no,
                    'chassis_no':x.chassis_no,
                    'product_type':x.product_type,
                    'product_warna':x.product_warna,
                    'kondisi_fisik':x.kondisi_fisik,
                    'keterangan':x.keterangan,
                })
            if not prod_ids.get(x.product_type):
                prod_ids[x.product_type] = {'product_type':x.product_type,'sistem':sistem,'fisik':fisik}
            else:
                prod_ids[x.product_type]['sistem'] += sistem
                prod_ids[x.product_type]['fisik'] += fisik
            
            total_fisik += fisik
            total_sistem += sistem

        selisih = total_sistem - total_fisik

        jml = len(prod_ids.values()) / 3
        tabel_1 = prod_ids.values()[0:jml+1]
        tabel_2 = prod_ids.values()[jml+1:jml*2+2]
        tabel_3 = prod_ids.values()[jml*2+2:]

        
        datas = {
            'ids': active_ids,
            'name':str(self.opname_id.name),
            'branch':str(self.opname_id.branch_id.name_get().pop()[1]),
            'division':self.opname_id.division,
            'tgl_so':self.opname_id.date,
            'jam_mulai': str(datetime.strptime(self.opname_id.generate_date, '%Y-%m-%d %H:%M:%S') + relativedelta(hours=7)),
            'jam_selesai': str(datetime.strptime(self.opname_id.post_date, '%Y-%m-%d %H:%M:%S') + relativedelta(hours=7)),
            'note_bakso':str(self.note_bakso) if self.note_bakso else '',
            'staff_bbn':str(self.opname_id.staff_bbn),
            'adh':str(self.opname_id.adh),
            'soh':str(self.opname_id.soh),
            'user': user,
            'date': (datetime.now() + timedelta(hours=7)).strftime('%Y-%d-%d %H:%M:%S'),
            'detail_ids':prod_ids.values(),
            'tabel_1':tabel_1,
            'tabel_2':tabel_2,
            'tabel_3':tabel_3,
            'total_sistem':total_sistem,
            'total_fisik':total_fisik,
            'selisih':selisih,
            'nrfs_ids':nrfs_ids,
        }
        self.opname_id.note_bakso_unit = self.note_bakso

        return self.env['report'].get_action(self,'teds_stock_opname_unit.teds_stock_opname_unit_print_bakso', data=datas)

    def action_bakso_aksesoris(self):
        active_ids = self.env.context.get('active_ids', [])
        user = self.env['res.users'].browse(self._uid).name
        detail_ids = {}
        for x in self.opname_id.aksesoris_ids:
            if not detail_ids.get(x.category):
                detail_ids[x.category] = {
                    'category':x.category,
                    'qty_good':x.qty_good,
                    'qty_not_good':x.qty_not_good,
                    'last_not_good':x.last_not_good,
                    'total':x.total,
                    'total_unit':x.total_unit,
                    'selisih':x.selisih,
                    'selisih_so_lalu':x.selisih_so_lalu,
                }
            else:
                detail_ids[x['category']]['qty_good'] += x.qty_good
                detail_ids[x['category']]['qty_not_good'] += x.qty_not_good
                detail_ids[x['category']]['total'] += x.total
                detail_ids[x['category']]['total_unit'] += x.total_unit
                detail_ids[x['category']]['last_not_good'] += x.last_not_good
                detail_ids[x['category']]['selisih'] += x.selisih
                detail_ids[x['category']]['selisih_so_lalu'] += x.selisih_so_lalu

        datas = {
            'ids': active_ids,
            'name':str(self.opname_id.name),
            'branch':str(self.opname_id.branch_id.name_get().pop()[1]),
            'division':self.opname_id.division,
            'tgl_so':self.opname_id.date,
            'jam_mulai': str(datetime.strptime(self.opname_id.generate_date, '%Y-%m-%d %H:%M:%S') + relativedelta(hours=7)),
            'jam_selesai': str(datetime.strptime(self.opname_id.post_date, '%Y-%m-%d %H:%M:%S') + relativedelta(hours=7)),
            'note_bakso':str(self.note_bakso) if self.note_bakso else '',
            'staff_bbn':str(self.opname_id.staff_bbn),
            'adh':str(self.opname_id.adh),
            'soh':str(self.opname_id.soh),
            'user': user,
            'date': (datetime.now() + timedelta(hours=7)).strftime('%Y-%d-%d %H:%M:%S'),
            'total_unit':self.opname_id.total_unit,
            'total_fisik':self.opname_id.total_fisik,
            'detail_ids':detail_ids.values(),
        }
        self.opname_id.note_bakso_aksesoris = self.note_bakso

        return self.env['report'].get_action(self,'teds_stock_opname_unit.teds_stock_opname_aksesoris_unit_print_bakso', data=datas)

