from openerp import models, fields, api
from datetime import date, datetime, timedelta,time
from dateutil.relativedelta import relativedelta
from openerp.exceptions import Warning

class StockOpnameDirectGift(models.Model):
    _name = "teds.stock.opname.direct.gift"
    
    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()
    
    @api.model
    def _get_default_datetime(self):
        return datetime.now()

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
    division = fields.Selection([('Umum','Umum')],default="Umum")
    detail_ids = fields.One2many('teds.stock.opname.direct.gift.line','opname_id')
    other_dg_ids = fields.One2many('teds.stock.opname.direct.gift.other','opname_id')
    note_bakso = fields.Text('Note')
    
    @api.model
    def create(self,vals):
        cek = self.search([
            ('branch_id','=',vals['branch_id']),
            ('state','!=','posted')])
        if cek:
            raise Warning('Perhatian ! Masih ada stock opname yang belum selesai !')
        
        vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'SODG')
        if vals.get('staff_bbn'):
            vals['staff_bbn'] = vals['staff_bbn'].title()
        if vals.get('adh'):
            vals['adh'] = vals['adh'].title()
        if vals.get('soh'):
            vals['soh'] = vals['soh'].title()
        return super(StockOpnameDirectGift,self).create(vals)
    
    @api.multi
    def write(self,vals):
        if vals.get('staff_bbn'):
            vals['staff_bbn'] = vals['staff_bbn'].title()
        if vals.get('adh'):
            vals['adh'] = vals['adh'].title()
        if vals.get('soh'):
            vals['soh'] = vals['soh'].title()
        return super(StockOpnameDirectGift,self).write(vals)

    @api.multi
    def unlink(self):
        for data in self:
            if data.state != "draft":
                raise Warning("Tidak bisa menghapus data yang berstatus selain draft!")
        return super(StockOpnameDirectGift, self).unlink()

    @api.multi
    def action_generate_stock(self):
        query = """
            SELECT quant.product_id
            , quant.product_name
            , COALESCE(ppb.cost, 0.01) as harga_satuan
            , quant.qty_titipan
            , quant.qty_stock
            , date_part('days', now() - quant.in_date)::int as aging
            FROM 
            (SELECT l.branch_id
            , l.warehouse_id
            , p.default_code
            , p.id as product_id
            , t.name as product_name
            , sum(CASE WHEN q.consolidated_date IS NULL THEN q.qty ELSE 0 END) as qty_titipan
            , sum(CASE WHEN q.consolidated_date IS NOT NULL THEN q.qty ELSE 0 END) as qty_stock
            , min(q.in_date) as in_date
            FROM stock_quant q
            INNER JOIN stock_location l ON q.location_id = l.id AND l.usage IN ('internal','transit','nrfs')
            LEFT JOIN product_product p ON q.product_id = p.id
            LEFT JOIN product_template t ON p.product_tmpl_id = t.id
            LEFT JOIN product_category c ON t.categ_id = c.id 
            LEFT JOIN product_category c2 ON c.parent_id = c2.id 
            WHERE 1=1 AND (c.name = 'Umum' OR c2.name = 'Umum')
            GROUP BY l.id, p.id, t.id
            ) as quant
            LEFT JOIN wtc_branch b ON quant.branch_id = b.id
            LEFT JOIN product_price_branch ppb ON ppb.product_id = quant.product_id AND ppb.warehouse_id = quant.warehouse_id
            WHERE b.id = %d
        """ %(self.branch_id.id)
        self.env.cr.execute(query)
        ress = self.env.cr.dictfetchall()
        lines = []
        for res in ress:
            lines.append([0,False,{
                'product_id':res.get('product_id'),
                'name':res.get('product_name'),
                'harga_satuan':res.get('harga_satuan'),
                'qty':res.get('qty_titipan')+res.get('qty_stock'),
                'amount':res.get('harga_satuan'),
                'aging':res.get('aging')
            }])
        self.write({
            'generate_date':self._get_default_datetime(),
            'detail_ids':lines
        })

    @api.multi
    def action_post(self):
        if not self.detail_ids:
            raise Warning('Data Stock Direct Gift tidak boleh kosong !')
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
        other_dg_ids = []

        for other in self.other_dg_ids:
            other_dg_ids.append({
                'nama_product':other.nama_product,
                'qty_fisik_baik':other.qty_fisik_baik,
                'qty_fisik_rusak':other.qty_fisik_rusak,
                'qty_fisik_total':other.qty_fisik_total,
                'saldo_log_book':other.saldo_log_book,
            })
        tot_qty = 0
        tot_amount = 0
        tot_qty_fisik_baik = 0
        tot_qty_fisik_rusak = 0
        tot_qty_fisik_total = 0
        tot_amount_total = 0
        tot_selisih_qty = 0
        tot_selisih_amount = 0
        tot_saldo_log_book = 0
        tot_other_baik = 0
        tot_other_rusak = 0
        tot_other_total = 0 
        tot_other_log_book = 0

        for line in self.detail_ids:
            detail_ids.append({
                'product':line.product_id.name_get().pop()[1],
                'harga_satuan':line.harga_satuan,
                'qty':line.qty,
                'amount':line.amount,
                'qty_fisik_baik':line.qty_fisik_baik,
                'qty_fisik_rusak':line.qty_fisik_rusak,
                'qty_fisik_total':line.qty_fisik_total,
                'amount_total':line.amount_total,
                'selisih_qty':line.selisih_qty,
                'selisih_amount':line.selisih_amount,
                'saldo_log_book':line.saldo_log_book,
                'aging':line.aging,
            })
            tot_qty += line.qty
            tot_amount += line.amount
            tot_qty_fisik_baik += line.qty_fisik_baik
            tot_qty_fisik_rusak += line.qty_fisik_rusak
            tot_qty_fisik_total += line.qty_fisik_total
            tot_amount_total += line.amount_total
            tot_selisih_qty += line.selisih_qty
            tot_selisih_amount += line.selisih_amount
            tot_saldo_log_book += line.saldo_log_book

        for other in self.other_dg_ids:
            tot_other_baik += other.qty_fisik_baik
            tot_other_rusak += other.qty_fisik_rusak
            tot_other_total += other.qty_fisik_total
            tot_other_log_book += other.saldo_log_book

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
            'other_dg_ids':other_dg_ids,
            'create_uid':self.create_uid.name,
            'create_date': str(datetime.strptime(self.create_date, '%Y-%m-%d %H:%M:%S') + relativedelta(hours=7)),
            'tot_qty':tot_qty,
            'tot_amount':tot_amount,
            'tot_qty_fisik_baik':tot_qty_fisik_baik,
            'tot_qty_fisik_rusak':tot_qty_fisik_rusak,
            'tot_qty_fisik_total':tot_qty_fisik_total,
            'tot_amount_total':tot_amount_total,
            'tot_selisih_qty':tot_selisih_qty,
            'tot_selisih_amount':tot_selisih_amount,
            'tot_saldo_log_book':tot_saldo_log_book,
            'tot_other_baik':tot_other_baik,
            'tot_other_rusak':tot_other_rusak,
            'tot_other_total':tot_other_total,
            'tot_other_log_book':tot_other_log_book,
        }
        return self.env['report'].get_action(self,'teds_stock_opname_direct_gift.teds_stock_opname_dg_print_validasi', data=datas)

    @api.multi
    def action_bakso(self):
        form_id = self.env.ref('teds_stock_opname_direct_gift.view_teds_so_dg_bakso_wizard').id
    
        return {
            'type': 'ir.actions.act_window',
            'name': 'Berita Acara SO',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.stock.opname.dg.bakso.wizard',
            'context':{'default_opname_id':self.id,'default_note_bakso':self.note_bakso},
            'views': [(form_id, 'form')],
            'target':'new'
        }

    @api.multi
    def action_download_excel(self):
        obj_x = self.env['teds.stock.opname.direct.gift.wizard'].create({'opname_dg_id':self.id})
        obj_x.action_download_excel()
        return {
            'type': 'ir.actions.act_url',
            'name': 'contract',
            'url':'/web/binary/saveas?model=teds.stock.opname.direct.gift.wizard&field=file_excel&filename_field=name&id=%d'%(obj_x.id)
        }
    
class StockOpnameDirectGiftLine(models.Model):
    _name = "teds.stock.opname.direct.gift.line"

    
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


    opname_id = fields.Many2one('teds.stock.opname.direct.gift','Stock Opname',ondelete='cascade')
    product_id = fields.Many2one('product.product','Product')
    name = fields.Char('Description')
    harga_satuan = fields.Float('Harga Satuan')
    qty = fields.Float('Qty Sistem')
    amount = fields.Float('Amount Total Sistem',compute='_compute_amount')
    qty_fisik_baik = fields.Float('Qty Fisik Baik')
    qty_fisik_rusak = fields.Float('Qty Fisik Rusak')
    qty_fisik_total = fields.Float('Total Qty Fisik',compute='_compute_fisik_total')
    amount_total = fields.Float('Amount Total Fisik',compute='_compute_amount_total')
    selisih_qty = fields.Float('Selisih Qty',compute='_compute_selisih_qty')
    selisih_amount = fields.Float('Selisih Amount',compute='_compute_selisih_amount')
    saldo_log_book = fields.Float('Saldo Logbook')
    aging = fields.Integer('Aging')


class StockOpnameDirectGiftOther(models.Model):
    _name = "teds.stock.opname.direct.gift.other"

    @api.one
    @api.depends('qty_fisik_baik','qty_fisik_rusak')
    def _compute_fisik_total(self):
        self.qty_fisik_total = self.qty_fisik_baik + self.qty_fisik_rusak

    opname_id = fields.Many2one('teds.stock.opname.direct.gift',ondelete='cascade')
    nama_product = fields.Char('Nama Barang')
    qty_fisik_baik = fields.Float('Qty Fisik Baik')
    qty_fisik_rusak = fields.Float('Qty Fisik Rusak')
    qty_fisik_total = fields.Float('Total Qty Fisik',compute='_compute_fisik_total')
    saldo_log_book = fields.Float('Saldo Logbook')

class StockOpnameDGBaksoWizard(models.TransientModel):
    _name = "teds.stock.opname.dg.bakso.wizard"

    note_bakso = fields.Text('Note')
    opname_id = fields.Many2one('teds.stock.opname.direct.gift','Stock Opname')
    
    @api.multi
    def action_submit_bakso(self):
        active_ids = self.env.context.get('active_ids', [])
        user = self.env['res.users'].browse(self._uid).name
        
        tot_qty = 0
        tot_amount = 0
        tot_qty_fisik_baik = 0
        tot_qty_fisik_rusak = 0
        tot_amount_total = 0
        tot_selisih_qty = 0
        tot_selisih_amount = 0
        tot_saldo_log_book = 0
        tot_qty_fisik_baik_other = 0
        tot_qty_fisik_rusak_other = 0 
        
        tot_qty_fisik_total = 0
        tot_dg_other = 0

        for line in self.opname_id.detail_ids:
            tot_qty += line.qty
            tot_amount += line.amount
            tot_qty_fisik_baik += line.qty_fisik_baik
            tot_qty_fisik_rusak += line.qty_fisik_rusak
            tot_qty_fisik_total += line.qty_fisik_total
            tot_amount_total += line.amount_total
            tot_selisih_qty += line.selisih_qty
            tot_selisih_amount += line.selisih_amount
            tot_saldo_log_book += line.saldo_log_book
        
        for other in self.opname_id.other_dg_ids:
            tot_saldo_log_book += other.saldo_log_book
            tot_qty_fisik_baik_other += other.qty_fisik_baik
            tot_qty_fisik_rusak_other += other.qty_fisik_rusak
            tot_dg_other += other.qty_fisik_total

        tot_dg = tot_qty_fisik_total + tot_dg_other
        
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
            'tot_qty':tot_qty,
            'tot_amount':tot_amount,
            'tot_qty_fisik_baik':tot_qty_fisik_baik,
            'tot_qty_fisik_rusak':tot_qty_fisik_rusak,
            'tot_amount_total':tot_amount_total,
            'tot_selisih_qty':tot_selisih_qty,
            'tot_selisih_amount':tot_selisih_amount,
            'tot_saldo_log_book':tot_saldo_log_book,
            'tot_qty_fisik_baik_other':tot_qty_fisik_baik_other,
            'tot_qty_fisik_rusak_other':tot_qty_fisik_rusak_other,
            'tot_qty_fisik_total':tot_qty_fisik_total,
            'tot_dg_other':tot_dg_other,
            'tot_dg':tot_dg,

        }
        self.opname_id.note_bakso = self.note_bakso
        return self.env['report'].get_action(self,'teds_stock_opname_direct_gift.teds_stock_opname_dg_print_bakso', data=datas)
