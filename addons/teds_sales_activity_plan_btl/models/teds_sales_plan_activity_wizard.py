from openerp import models, fields, api
from datetime import date, datetime, timedelta,time
from dateutil.relativedelta import relativedelta
import calendar
from openerp.exceptions import Warning

import base64
import tempfile
from PIL import Image
import io

class SalesPlanActivity(models.Model):
    _inherit = "teds.sales.plan.activity"

    @api.multi
    def action_add_activity(self):
        date_now = date.today()
        year = date_now.year
        month = date_now.month
        if int(month) == 12 and int(self.bulan) == 1:
            year += 1
            month = 1

        if (int(month) > int(self.bulan)) or (int(year) != int(self.tahun)):
            raise Warning('Sudah tidak bisa melakukan add activity!')
    
        form_id = self.env.ref('teds_sales_activity_plan_btl.view_teds_sales_plan_add_wizard').id
        return {
            'name': ('Add Activity'),
            'res_model': 'teds.sales.plan.add.wizard',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'views': [(form_id, 'form')],
            'view_mode': 'form',
            'target': 'new',
            'view_type': 'form',
            'context': {
                'default_sales_plan_id': self.id,
            },
        }

class SalesPlanAddWizard(models.TransientModel):
    _name = "teds.sales.plan.add.wizard"

    sales_plan_id = fields.Many2one('teds.sales.plan.activity','Activity Plan')
    branch_id = fields.Many2one('wtc.branch',related='sales_plan_id.branch_id',readonly=True)
    bulan = fields.Selection([
        ('1','Januari'),
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
        ('12','Desember')],'Bulan',related='sales_plan_id.bulan',readonly=True)
    tahun = fields.Char('Tahun',related='sales_plan_id.tahun',readonly=True)
    sales_activity_line_ids = fields.One2many('teds.sales.plan.add.line.wizard','activity_id')

    @api.multi
    def action_submit(self):
        ids = []
        if not self.sales_activity_line_ids:
            raise Warning('Detail tidak boleh kosong !')
  
        for line in self.sales_activity_line_ids:
            detail_biaya_ids = []
            history_location_ids = []

            if len(line.detail_biaya_ids) > 0:
                for b in line.detail_biaya_ids:
                    detail_biaya_ids.append([0,False,{
                        'name':b.name,
                        'finco_id':b.finco_id.id,
                        'tipe':b.tipe,
                        'amount':b.amount,
                        'is_ppn':b.is_ppn,
                    }])
            if len(history_location_ids) > 0:
                for h in line.history_location_ids:
                    detail_ids = []
                    for d in h.detail_ids:
                        detail_ids.append([0,False,{
                            'product_id':d.product_id.id
                        }])
                    history_location_ids.append([0,False,{
                        'name':h.name,
                        'qty':h.qty,
                        'detail_ids':detail_ids,
                    }])

            
            ids.append([0,False,{
                'name':line.name,
                'branch_id':line.branch_id.id,
                'jaringan_penjualan':line.jaringan_penjualan,
                'act_type_id':line.act_type_id.id,
                'titik_keramaian_id':line.titik_keramaian_id.id,
                'state_id':line.state_id,
                'city_id':line.city_id.id,
                'kecamatan_id':line.kecamatan_id.id,
                'kelurahan_id':line.kelurahan_id.id,
                'street':line.street,
                'rt':line.rt,
                'rw':line.rw,
                'jenis_pengajuan':line.jenis_pengajuan,
                'source_pos_location_id':line.source_pos_location_id.id,
                'is_location':line.is_location,
                'location_id':line.location_id.id,
                'start_date':line.start_date,
                'end_date':line.end_date,
                'pic_id':line.pic_id.id,
                'no_telp':line.no_telp,
                'display_unit':line.display_unit,
                'target_unit':line.target_unit,
                'target_customer':line.target_customer,
                'detail_biaya_ids':detail_biaya_ids,
                'history_location_ids':history_location_ids,
                'foto':line.foto,
            }])

        self.sales_plan_id.write({
            'state':'waiting_for_approval',
            'activity_line_ids':ids    
        })

class SalesPlanAddLineWizard(models.TransientModel):
    _name = "teds.sales.plan.add.line.wizard"

    @api.one
    @api.depends('jaringan_penjualan','act_type_id','titik_keramaian_id','jenis_pengajuan','location_id')
    def compute_customer_bulan_lalu(self):
        if not self.activity_id.branch_id or not self.activity_id.bulan or not self.activity_id.tahun:
            raise Warning('Silahkan isi data header terlebih dahulu !')
        now = date(int(self.activity_id.tahun), int(self.activity_id.bulan), 1)  
        start_month = now - relativedelta(months=1)
        qty = 0
        if self.jaringan_penjualan and self.act_type_id and self.titik_keramaian_id:
            query_loc = ""
            if self.location_id:
                query_loc = "AND spl.location_id = %d" %(self.location_id.id)
            query = """
                SELECT spl.id
                FROM teds_sales_plan_activity sp
                INNER JOIN teds_sales_plan_activity_line spl ON spl.activity_id = sp.id
                WHERE sp.branch_id = %d
                AND sp.bulan = '%s'
                AND sp.tahun = '%s'
                AND spl.jaringan_penjualan = '%s'
                AND spl.act_type_id = %d
                AND spl.titik_keramaian_id = %d
                %s
            """ %(self.branch_id.id,start_month.month,start_month.year,self.jaringan_penjualan,self.act_type_id.id,self.titik_keramaian_id.id,query_loc)
            self._cr.execute (query)
            ress =  self._cr.fetchall()
            for res in ress:
                activity_line_id = self.env['teds.sales.plan.activity.line'].browse(res[0])
                qty += len(activity_line_id.spk_ids)
            
        self.qty_customer_last = qty

    @api.one
    @api.depends('detail_biaya_ids.subtotal')
    def compute_total_biaya(self):
        total_biaya = sum([x.subtotal if x.tipe == 'Biaya tersedia' else 0 for x in self.detail_biaya_ids])
        self.total_biaya = total_biaya
    
    
    name = fields.Char('Nama Activity')
    activity_id = fields.Many2one('teds.sales.plan.add.wizard','Plan Activity',ondelete='cascade')
    branch_id = fields.Many2one('wtc.branch','Branch')
    jaringan_penjualan = fields.Selection([
        ('Showroom','Showroom'),
        ('POS','POS')])
    state = fields.Selection([
        ('draft','Draft'),
        ('open','Open'),
        ('confirmed','Confirmed'),
        ('revision','Revision')],default='draft')
    source_pos_location_id = fields.Many2one('stock.location','Source POS Location')
    act_type_id = fields.Many2one('teds.act.type.sumber.penjualan','Activity Type',domain=[('is_btl','!=',False)])
    act_type_code = fields.Char('Activity Type Code',related='act_type_id.code')
    titik_keramaian_id = fields.Many2one('titik.keramaian','Titik Keramaian')
    ring_id = fields.Many2one('master.ring','Ring',related='titik_keramaian_id.ring_id',readonly=True)
    state_id = fields.Many2one('res.country.state','Provinsi',related='city_id.state_id')
    city_id = fields.Many2one('wtc.city','Kota / Kab',related='kecamatan_id.city_id')
    kecamatan_id = fields.Many2one('wtc.kecamatan','Kecamatan',related='titik_keramaian_id.kecamatan_id',readonly=True)
    kelurahan_id = fields.Many2one('wtc.kelurahan','Kelurahan',domain="[('kecamatan_id','=',kecamatan_id)]")
    street = fields.Char('Street')
    rt = fields.Char('RT')
    rw = fields.Char('RW')
    jenis_pengajuan = fields.Selection([
        ('new','Baru'),
        ('update','Perpanjang')])
    is_location = fields.Boolean('Location ?',related='act_type_id.is_location',readonly="1")
    location_id = fields.Many2one('stock.location','Location')
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    pic_id = fields.Many2one('hr.employee','PIC',domain="[('branch_id','=',branch_id),('job_id.sales_force','in',('salesman','sales_counter','soh','sales_koordinator'))]")
    nik = fields.Char('NIK',related="pic_id.nip",readonly=True)
    job = fields.Char('Jabatan',related="pic_id.job_id.name",readonly=True)
    no_telp = fields.Char('No Telp')
    display_unit = fields.Integer('Display Unit')
    target_unit = fields.Integer('Target Unit')
    target_customer = fields.Integer('Target Customer')
    total_biaya = fields.Float('Total Biaya',compute='compute_total_biaya')
    detail_biaya_ids = fields.One2many('teds.activity.detail.biaya.wizard','activity_id')
    qty_customer_last = fields.Float('Total Customer Bulan Lalu',compute='compute_customer_bulan_lalu')
    history_location_ids = fields.One2many('teds.sales.plan.history.location.wizard','activity_id')
    foto = fields.Binary('Foto Lokasi')
    filename_foto = fields.Char('Filename')
    
    @api.model
    def create(self,vals):
        if vals.get('foto'):
            data = base64.decodestring(vals['foto'])
            fobj = tempfile.NamedTemporaryFile(delete=False)
            fname = fobj.name
            fobj.write(data)
            fobj.close()
            # open the image with PIL

            basewidth = 500
            img = Image.open(fname,'r')
            wpercent = (basewidth/float(img.size[0]))
            hsize = int((float(img.size[1])*float(wpercent)))
            img = img.resize((basewidth,hsize), Image.ANTIALIAS)
            fname = io.BytesIO()
            img.save(fname, "JPEG")
            data = base64.encodestring(fname.getvalue())
            vals['foto'] = data
                
        return super(SalesPlanAddLineWizard,self).create(vals)

    @api.multi
    def write(self,vals):
        if vals.get('foto'):
            data = base64.decodestring(vals['foto'])
            fobj = tempfile.NamedTemporaryFile(delete=False)
            fname = fobj.name
            fobj.write(data)
            fobj.close()
            # open the image with PIL

            basewidth = 500
            img = Image.open(fname,'r')
            wpercent = (basewidth/float(img.size[0]))
            hsize = int((float(img.size[1])*float(wpercent)))
            img = img.resize((basewidth,hsize), Image.ANTIALIAS)
            fname = io.BytesIO()
            img.save(fname, "JPEG")
            data = base64.encodestring(fname.getvalue())
            vals['foto'] = data
                
        return super(SalesPlanAddLineWizard,self).write(vals)


    @api.onchange('is_location')
    def onchange_is_location(self):
        self.jenis_pengajuan = False
        self.location_id = False
        self.display_unit = False
        self.source_pos_location_id = False


    @api.onchange('jaringan_penjualan','act_type_id','titik_keramaian_id','jenis_pengajuan','location_id')
    def onchange_history_location(self):
        self.foto = False
        self.history_ids = False
        history_ids = []
        now = date(int(self.activity_id.tahun), int(self.activity_id.bulan), 1)  
        start_month = now - relativedelta(months=3)
        if self.jaringan_penjualan and self.act_type_id and self.titik_keramaian_id:
            query_loc = ""
            if self.location_id:
                query_loc += "AND pal.location_id = %d" %(self.location_id)
            query = """
                SELECT EXTRACT(MONTH FROM date_order) as month
                , pp.id as prod_id
                , pt.categ_id as categ_id
                FROM teds_sales_plan_activity pa
                INNER JOIN teds_sales_plan_activity_line pal ON pal.activity_id = pa.id
                INNER JOIN dealer_sale_order so ON so.activity_plan_id = pal.id
                INNER JOIN dealer_sale_order_line sol on so.id = sol.dealer_sale_order_line_id
                INNER JOIN product_product pp ON pp.id = sol.product_id
                INNER JOIN product_template pt ON pt.id = pp.product_tmpl_id                
                WHERE so.jaringan_penjualan = '%s'
                AND so.sumber_penjualan_id = %d
                AND so.titik_keramaian_id = %d
                AND date_order BETWEEN '%s' AND '%s'
                %s
                ORDER BY month ASC
            """ %(self.jaringan_penjualan,self.act_type_id.id,self.titik_keramaian_id.id,start_month,now,query_loc)
            self._cr.execute (query)
            ress =  self._cr.dictfetchall()
            ids = {}
            if len(ress) > 0:
                for res in ress:
                    month = (calendar.month_name[int(res['month'])])
                    if not ids.get(month):
                        ids[month] = {
                            'name':month,
                            'qty':0,
                            'detail_ids':[]
                        }
                    ids[month]['qty'] += 1
                    ids[month]['detail_ids'].append([0,False,{
                        'product_id':res['prod_id'],
                        'categ_id':res['categ_id']
                    }])
            for x in ids.values():
                history_ids.append([0,False,x])
        self.history_location_ids = history_ids

    @api.onchange('location_id')
    def onchange_name_location(self):
        self.name = False
        self.street = False
        self.kelurahan_id = False
        self.rt = False
        self.rw = False
        if self.location_id:
            self.name = self.location_id.description
            self.kelurahan_id = self.location_id.zip_id.id
            self.street = self.location_id.street
            self.rt = self.location_id.rt
            self.rw = self.location_id.rw    

    # @api.onchange('branch_id','act_type_id','titik_keramaian_id','is_location')
    # def onchange_location(self):
    #     domain = {}
    #     self.location_id = False
    #     if self.branch_id and self.act_type_id and self.is_location and self.titik_keramaian_id:
    #         kecamatan_id = self.titik_keramaian_id.kecamatan_id.id
    #         loc = self.env['stock.location'].sudo().search([
    #             ('branch_id','=',self.branch_id.id),
    #             ('usage','=','internal')])
    #         ids = [l.id for l in loc]
    #         domain['location_id'] = [('id','in',ids)]
    #     return {'domain':domain}

    @api.onchange('state')
    def onchange_branch(self):
        if not self.activity_id.branch_id or not self.activity_id.bulan or not self.activity_id.tahun:
            raise Warning('Silahkan isi data header terlebih dahulu !')
        self.branch_id = self.activity_id.branch_id.id


    @api.constrains('start_date')
    @api.one
    def cek_start_date(self):
        if self.start_date :
            month = (calendar.month_name[int(self.activity_id.bulan)])
            start_date = datetime.strptime(self.start_date, "%Y-%m-%d")
            if (int(start_date.month) != int(self.activity_id.bulan)) or (int(start_date.year) != int(self.activity_id.tahun)):
                raise Warning('Start date tidak masuk pada periode bulan %s !' % (month))

        if self.start_date > self.end_date:
            raise Warning('End date tidak boleh kurang dari start date')

    @api.constrains('end_date')
    @api.one
    def cek_end_date(self):
        if self.end_date :
            month = (calendar.month_name[int(self.activity_id.bulan)])
            end_date = datetime.strptime(self.end_date,"%Y-%m-%d")
            if (int(end_date.month) != int(self.activity_id.bulan)) or (int(end_date.year) != int(self.activity_id.tahun)):
                raise Warning('Perhatian ! \n End date tidak masuk pada periode bulan %s !' %(month))


class ActivityDetailBiayaWizard(models.TransientModel):
    _name = "teds.activity.detail.biaya.wizard"

    @api.multi
    @api.depends('amount','is_ppn')
    def _compute_subtotal(self):
        for me in self:
            subtotal = me.amount
            if me.is_ppn:
                subtotal = me.amount / 0.9
            me.subtotal = subtotal

    activity_id = fields.Many2one('teds.sales.plan.add.line.wizard',ondelete='cascade')
    name = fields.Selection([
        ('Dealer','Dealer'),
        ('Leasing','Leasing'),
        ('Mediator','Mediator')],string='Sumber Biaya')
    finco_id = fields.Many2one('res.partner','Finco',domain=[('finance_company','=',True)])
    tipe = fields.Selection([
        ('Sudah dibayar ke vendor','Sudah dibayar ke vendor'),
        ('Beban Cabang (opex)','Beban Cabang (opex)'),
        ('Beban Leasing (HL tersedia)','Beban Leasing (HL tersedia)'),
        ('Beban Leasing (HL belum tersedia)','Beban Leasing (HL belum tersedia)')],'Ket.')
    
    amount = fields.Float('Amount')
    is_ppn = fields.Boolean('PPN ?',default=True)
    subtotal = fields.Float('Subtotal',compute="_compute_subtotal",readonly=True)

    @api.onchange('name')
    def onchange_finco(self):
        self.finco_id = False

class SalesPlanHistoryWizard(models.TransientModel):
    _name = "teds.sales.plan.history.location.wizard"

    activity_id = fields.Many2one('teds.sales.plan.add.line.wizard','Activity',ondelete='cascade')
    name = fields.Char('Bulan')
    qty = fields.Integer('Qty')
    detail_ids = fields.One2many('teds.history.location.detail.wizard','history_id','Detail')

class HistoryLocationDetailWizard(models.TransientModel):
    _name = "teds.history.location.detail.wizard"    

    history_id = fields.Many2one('teds.sales.plan.history.location.wizard','History',ondelete='cascade')
    product_id = fields.Many2one('product.product')
    categ_id = fields.Many2one('product.category','Category',related='product_id.categ_id')

