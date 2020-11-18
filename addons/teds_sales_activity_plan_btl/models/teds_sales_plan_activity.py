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
    _name = "teds.sales.plan.activity"
    _inherit = ['ir.needaction_mixin']

    def _get_tahun(self):
        return date.today().year

    @api.one
    @api.depends('activity_line_ids.total_biaya')
    def compute_total_biaya_btl(self):
        total = 0
        for x in self.activity_line_ids:
            if x.state != 'reject':
                total += x.total_biaya
        self.total_biaya_btl = total

    def _get_default_branch(self):
        branch_ids = False
        branch_ids = self.env.user.branch_ids
        if branch_ids and len(branch_ids) == 1 :
            return branch_ids[0].id
        return False

    @api.one
    @api.depends('activity_line_confirm_ids')
    def compute_jml_data(self):
        total = 0
        if self.activity_line_confirm_ids:
            total = len(self.activity_line_confirm_ids)
        self.jml_data_confirm = total

    name = fields.Char('Name')
    branch_id = fields.Many2one('wtc.branch','Branch',default=_get_default_branch)
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
    tahun = fields.Char('Tahun', default=_get_tahun)
    state = fields.Selection([
        ('draft','Draft'),
        ('waiting_for_approval','Waiting Approval'),
        ('approved','Approved'),
        ('open','Open'),
        ('done','Done')],default="draft")
    total_biaya_btl = fields.Float('Total Biaya BTL',compute='compute_total_biaya_btl') 
    approved_am_uid = fields.Many2one('res.users','Approved AM by')
    approved_am_date = fields.Datetime('Approved AM on')
    approved_operation_uid = fields.Many2one('res.users','Approved Operation by')
    approved_aoperation_date = fields.Datetime('Approved Operation on')

    activity_line_ids = fields.One2many('teds.sales.plan.activity.line','activity_id','Detail')
    activity_line_rfa_ids = fields.One2many('teds.sales.plan.activity.line','activity_id',domain=[('state','=','draft')],string="Status")
    activity_line_confirm_ids = fields.One2many('teds.sales.plan.activity.line','activity_id',domain=[('state','=','confirmed')],string="Status")
    jml_data_confirm = fields.Float('Jml Data',compute='compute_jml_data') 

    _sql_constraints = [('branch_bulan_tahun', 'unique(branch_id,bulan,tahun)', 'Activity Plan tidak boleh duplikat !')]
    
    @api.model
    def _needaction_domain_get(self):
        return [('state', '=', 'waiting_for_approval')]        

    def action_spa_approve_am_tree(self):
        tree_id = self.env.ref('teds_sales_activity_plan_btl.view_teds_sales_activity_approved_tree').id
        form_id = self.env.ref('teds_sales_activity_plan_btl.view_teds_sales_activity_approved_form').id
        tgl = str(date.today())
        ids = []
        acts = self.env['teds.sales.plan.activity.line'].search([('state','=','draft')])
        for act in acts:
            if act.activity_id.id not in ids and act.activity_id.state == 'waiting_for_approval':
                ids.append(act.activity_id.id)
        domain = [('id','in',ids)]

        return {
            'type': 'ir.actions.act_window',
            'name': 'Approve AM',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'teds.sales.plan.activity',
            'domain': domain,
            'views': [(tree_id, 'tree'), (form_id, 'form')],
        }
    
    def action_spa_approve_operation_tree(self):
        tree_id = self.env.ref('teds_sales_activity_plan_btl.view_teds_sales_activity_approved_operation_tree').id
        form_id = self.env.ref('teds_sales_activity_plan_btl.view_teds_sales_activity_approved_operation_form').id
        tgl = str(date.today())
        ids = []
        acts = self.env['teds.sales.plan.activity.line'].search([('state','=','confirmed')])
        for act in acts:
            if act.activity_id.id not in ids and act.activity_id.state != 'done':
                ids.append(act.activity_id.id)
        domain = [('id','in',ids)]

        return {
            'type': 'ir.actions.act_window',
            'name': 'Persetujuan BTL',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'teds.sales.plan.activity',
            'domain': domain,
            'views': [(tree_id, 'tree'), (form_id, 'form')],
        }

    @api.multi
    def unlink(self):
        for x in self :
            if x.state != 'draft' :
                raise Warning('Transaksi yang berstatus selain Draft tidak bisa dihapus.')
        return super(PartHotline, self).unlink()

    @api.multi
    def name_get(self):
        if self._context is None:
            self._context = {}
        res = []
        for record in self:
            a = (calendar.month_name[int(record.bulan)])
            tit = "[%s - %s] %s" % (a, record.tahun, record.name)
            res.append((record.id, tit))
        return res

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        if name:
            args = ['|',('name', operator, name),('bulan', operator, name)] + args
        categories = self.search(args, limit=limit)
        return categories.name_get()

    @api.model
    def create(self,values):
        values['name'] = self.env['ir.sequence'].get_per_branch(values['branch_id'], 'BTL')
        if not values['activity_line_ids']:
            raise Warning('Activity Detail tidak boleh kosong !')
        return super(SalesPlanActivity,self).create(values)

    @api.multi
    def write(self,values):
        res = super(SalesPlanActivity,self).write(values)
        if not self.activity_line_ids:
            raise Warning('Activity Detail tidak boleh kosong !')
        return res 

    @api.multi
    def action_rfa(self):
        if self.state != 'draft':
            raise Warning('Silahkan di cek kembali state sudah tidak draft !')
        if not self.activity_line_ids:
            raise Warning('Activity Detail tidak boleh kosong !')
        self.state = 'waiting_for_approval'
    
    @api.multi
    def action_confirm_am(self):
        is_location = False
        if not self.activity_line_rfa_ids:
            raise Warning('Detail tidak boleh kosong !')
        for line in self.activity_line_rfa_ids:
            if line.state == 'draft':
                if line.status_am == 'approved':
                    if line.is_location:
                        line.state = 'open'
                        is_location = True
                    elif int(line.total_biaya) > 0:
                        line.state = 'open'
                    else:
                        line.state = 'done'
                else:
                    line.state = 'reject'
        if is_location:
            status = 'approved'
        else:
            status = 'open'
        self.write({
            'state':status,
            'approved_am_uid':self._uid,
            'approved_am_date':datetime.now()
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.multi
    def get_done_act(self):
        update_done = """
            UPDATE teds_sales_plan_activity 
            SET state = 'done'
            WHERE id in (
                SELECT pa.id
                FROM teds_sales_plan_activity pa
                INNER JOIN teds_sales_plan_activity_line pal ON pal.activity_id = pa.id
                WHERE pa.bulan::int  < (select extract(month from now()))
                AND pa.tahun::int  <= (select extract(year from now()))
            )            
        """
        self._cr.execute(update_done)

        # set_foto_false #
        update_foto = """
            UPDATE teds_sales_plan_activity_line
            SET foto = NULL
            WHERE id in (
                SELECT pal.id
                FROM teds_sales_plan_activity pa
                INNER JOIN teds_sales_plan_activity_line pal ON pal.activity_id = pa.id
                WHERE pa.bulan::int  < (select extract(month from now()))
                AND pa.tahun::int  <= (select extract(year from now()))
                AND foto IS NOT NULL
            )
        """
        self._cr.execute(update_foto)

    @api.multi
    def action_print_btl(self):
        active_ids = self.env.context.get('active_ids', [])
        user = self.env['res.users'].browse(self._uid).name
        detail_ids = []
        total_biaya_tdm = 0
        total_biaya_leasing = 0
        total_biaya_tdm_ppn = 0
        total_biaya_leasing_ppn = 0

        for line in self.activity_line_ids:
            if line.total_biaya > 0 and line.state in ('confirmed','done'):
                biaya_ids = []
                history_ids = [] 
                detail_unit_ids = False
                
                if len(line.detail_biaya_ids) > 0:
                    for biaya in line.detail_biaya_ids:
                        if biaya.name == 'Leasing':
                            total_biaya_leasing += biaya.amount
                            total_biaya_leasing_ppn += biaya.subtotal
                        elif biaya.name == 'Dealer':
                            total_biaya_tdm += biaya.amount
                            total_biaya_tdm_ppn += biaya.subtotal
                        biaya_ids.append({
                            'name':biaya.name,
                            'finco':biaya.finco_id.name if biaya.finco_id != None else '',
                            'amount':biaya.amount,
                            'subtotal':biaya.subtotal,
                        })
                tot_history = len(line.history_location_ids)
                mulai = 0
                if tot_history > 0:
                    categ_list = {}
                    for history in line.history_location_ids:
                        mulai += 1
                        history_ids.append({
                            'name':history.name,
                            'qty':history.qty,
                        })

                        if mulai == tot_history:
                            for unit in history.detail_ids:
                                if not categ_list.get(unit.categ_id.name):
                                    categ_list[unit.categ_id.name] = {'categ_id':unit.categ_id.name,'qty':1}
                                else:
                                    categ_list[unit.categ_id.name]['qty'] += 1

                            detail_unit_ids = categ_list.values()

                detail_ids.append({
                    'name':line.name,
                    'alamat':line.street,
                    'rt':line.rt,
                    'rw':line.rw,
                    'kelurahan':line.kelurahan_id.name,
                    'kecamatan':line.kecamatan_id.name,
                    'city':line.city_id.name,
                    'start_date':line.start_date,
                    'end_date':line.end_date,
                    'pic':line.pic_id.name,
                    'nik':line.nik,
                    'jabatan':line.job,
                    'no_telp':line.no_telp,
                    'display_unit':line.display_unit,
                    'target_unit':line.target_unit,
                    'pencapaian_unit':sum([h.qty for h in line.history_location_ids]),
                    'biaya_ids':biaya_ids,
                    'history_ids':history_ids,
                    'detail_unit_ids':detail_unit_ids,
                    'jarak':line.titik_keramaian_id.jarak if line.titik_keramaian_id.jarak else '0' ,
                    'waktu':line.titik_keramaian_id.waktu if line.titik_keramaian_id.waktu else '0',
                    'foto':line.foto,
                })

        datas = {
            'ids': active_ids,
            'user': user,
            'branch_id': str(self.branch_id.name),
            'periode': str(self.name_get().pop()[1]),
            'total_biaya_tdm':total_biaya_tdm,
            'total_biaya_leasing':total_biaya_leasing,
            'total_biaya_tdm_ppn':total_biaya_tdm_ppn,
            'total_biaya_leasing_ppn':total_biaya_leasing_ppn,
            'detail_ids': detail_ids,
            'create_uid':self.create_uid.name,
            'create_date':self.create_date,
        }
        return self.env['report'].get_action(self,'teds_sales_activity_plan_btl.teds_act_plan_btl_print', data=datas)

    def cek_activity_open(self):
        activity = self.env['teds.sales.plan.activity.line'].sudo().search([
            ('activity_id','=',self.id),
            ('state','in',('draft','open','confirmed'))])
        if not activity:
            self.state = 'open' 

    @api.multi
    def action_confirm_operation(self):
        if not self.activity_line_confirm_ids:
            raise Warning('Detail tidak boleh kosong !')
        vals = {
            'approved_operation_uid':self._uid,
            'approved_aoperation_date':datetime.now()
        }
        for line in self.activity_line_confirm_ids:
            if line.status_operation == 'approved':
                line.state = 'done'
            else:
                line.state = 'reject'
        self.write(vals) 
        self.cek_activity_open()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

class SalesPlanActivityLine(models.Model):
    _name = "teds.sales.plan.activity.line"
    _inherit = ['ir.needaction_mixin']

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
                activity_line_id = self.browse(res[0])
                qty += len(activity_line_id.spk_ids)
            
        self.qty_customer_last = qty


    @api.one
    @api.depends('detail_biaya_ids.subtotal')
    def compute_total_biaya(self):
        total_biaya = sum([x.subtotal for x in self.detail_biaya_ids])
        self.total_biaya = total_biaya

    @api.one
    @api.depends('spk_ids')
    def compute_actual_customer(self):
        total = len(self.spk_ids)
        self.actual_customer = total

    @api.one
    @api.depends('dso_ids')
    def compute_actual_unit(self):
        total = 0
        for so in self.dso_ids:
            for line in so.dealer_sale_order_line:
                total += line.product_qty
        self.actual_unit = total
    
    name = fields.Char('Nama Activity')
    activity_id = fields.Many2one('teds.sales.plan.activity','Plan Activity',ondelete='cascade')
    branch_id = fields.Many2one('wtc.branch','Branch')
    state = fields.Selection([
        ('draft','Draft'),
        ('open','Open'),
        ('confirmed','Confirmed'),
        ('done','Done'),
        ('reject','Reject')],default='draft')
    jaringan_penjualan = fields.Selection([
        ('Showroom','Showroom'),
        ('POS','POS')],'Jaringan Penjualan')
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
        ('update','Perpanjang')],string="Jenis Pengajuan")
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
    detail_biaya_ids = fields.One2many('teds.activity.detail.biaya','activity_id')
    qty_customer_last = fields.Float('Total Customer Bulan Lalu',compute='compute_customer_bulan_lalu')
    history_location_ids = fields.One2many('teds.sales.plan.history.location','activity_id')

    foto = fields.Binary('Foto Lokasi')
    filename_foto = fields.Char('Filename')
    
    reason_reject_location = fields.Text('Reason')
    status_am = fields.Selection([('approved','Approved'),('reject','Reject')],default='approved',string="Status")
    reason_reject_am = fields.Text('Reason')
    status_operation = fields.Selection([('approved','Approved'),('reject','Reject')],default='approved',string="Status")
    reason_reject_operation = fields.Text('Reason')
    
    # Data Actual
    spk_ids = fields.One2many('dealer.spk','activity_plan_id','SPK',domain=[('state','!=','draft')])
    dso_ids = fields.One2many('dealer.sale.order','activity_plan_id','DSO',domain=[('state','in',('progress','done'))])
    actual_unit = fields.Integer('Act Unit',compute='compute_actual_unit')
    actual_customer = fields.Integer('Act Customer',compute='compute_actual_customer')

    # _sql_constraints = [('activity_constraints', 'unique(activity_id,jaringan_penjualan,act_type_id,titik_keramaian_id,location_id)', 'Activity Plan tidak boleh duplikat !')]
    

    def action_teds_sales_plan_actitivty_tree(self):
        tree_id = self.env.ref('teds_sales_activity_plan_btl.view_teds_sales_plan_activity_approved_tree').id
        form_id = self.env.ref('teds_sales_activity_plan_btl.view_teds_sales_plan_activity_approved_form').id
        tgl = str(date.today())
        domain = [('state','in',('open','confirmed','done')),('total_biaya','>',0)]

        return {
            'type': 'ir.actions.act_window',
            'name': 'Review Location BTL',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'teds.sales.plan.activity.line',
            'domain': domain,
            'context':"{'group_by': ['branch_id'],'search_default_state_open':1}",
            'views': [(tree_id, 'tree'), (form_id, 'form')],
        }
    
    def action_spa_status_reject_tree(self):
        tree_id = self.env.ref('teds_sales_activity_plan_btl.view_teds_spa_status_reject_tree').id
        form_id = self.env.ref('teds_sales_activity_plan_btl.view_teds_spa_status_reject_form').id
        tgl = str(date.today())
        domain = [('state','=','reject'),('end_date','>=',tgl)]

        return {
            'type': 'ir.actions.act_window',
            'name': 'Activity & BTL Reject',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'teds.sales.plan.activity.line',
            'domain': domain,
            'views': [(tree_id, 'tree'), (form_id, 'form')],
        }

    def action_print_btl_active(self):
        user = self.env['res.users'].browse(self._uid).name
        detail_ids = []
        total_biaya_tdm = 0
        total_biaya_leasing = 0

        act_ids = []

        for line in self:
            if line.activity_id.name not in act_ids:
                act_ids.append(line.activity_id.name)
            if line.total_biaya > 0 and line.state in ('confirmed','done'):
                biaya_ids = []
                history_ids = [] 
                detail_unit_ids = False
                
                if len(line.detail_biaya_ids) > 0:
                    for biaya in line.detail_biaya_ids:
                        if biaya.name == 'Leasing':
                            total_biaya_leasing += biaya.subtotal
                        elif biaya.name == 'Dealer':
                            total_biaya_tdm += biaya.subtotal

                        biaya_ids.append({
                            'name':biaya.name,
                            'finco':biaya.finco_id.name if biaya.finco_id != None else '',
                            'amount':biaya.subtotal,
                        })
                tot_history = len(line.history_location_ids)
                mulai = 0
                if tot_history > 0:
                    categ_list = {}
                    for history in line.history_location_ids:
                        mulai += 1
                        history_ids.append({
                            'name':history.name,
                            'qty':history.qty,
                        })

                        if mulai == tot_history:
                            for unit in history.detail_ids:
                                if not categ_list.get(unit.categ_id.name):
                                    categ_list[unit.categ_id.name] = {'categ_id':unit.categ_id.name,'qty':1}
                                else:
                                    categ_list[unit.categ_id.name]['qty'] += 1

                            detail_unit_ids = categ_list.values()

                detail_ids.append({
                    'name':line.name,
                    'alamat':line.street,
                    'rt':line.rt,
                    'rw':line.rw,
                    'kelurahan':line.kelurahan_id.name,
                    'kecamatan':line.kecamatan_id.name,
                    'city':line.city_id.name,
                    'start_date':line.start_date,
                    'end_date':line.end_date,
                    'pic':line.pic_id.name,
                    'nik':line.nik,
                    'jabatan':line.job,
                    'no_telp':line.no_telp,
                    'display_unit':line.display_unit,
                    'target_unit':line.target_unit,
                    'pencapaian_unit':sum([h.qty for h in line.history_location_ids]),
                    'biaya_ids':biaya_ids,
                    'history_ids':history_ids,
                    'detail_unit_ids':detail_unit_ids,
                    'jarak':line.titik_keramaian_id.jarak if line.titik_keramaian_id.jarak else '0' ,
                    'waktu':line.titik_keramaian_id.waktu if line.titik_keramaian_id.waktu else '0',
                    'foto':line.foto,
                })
        if len(act_ids) > 1:
            raise Warning('Print Activity BTL hanya bisa untuk satu BTL ! \n List BTL Print : %s'%(str(act_ids)))
        datas = {
            'user': user,
            'branch_id': str(line.branch_id.name),
            'periode': str(line.activity_id.name_get().pop()[1]),
            'total_biaya_tdm':total_biaya_tdm,
            'total_biaya_leasing':total_biaya_leasing,
            'detail_ids': detail_ids,
            'create_uid':line.activity_id.create_uid.name,
            'create_date':line.activity_id.create_date,
        }
        a = self.env['report'].get_action(self,'teds_sales_activity_plan_btl.teds_act_plan_btl_print_tree', data=datas)
    


    @api.model
    def _needaction_domain_get(self):
        return [('state', '=', 'open')]

    @api.model
    def create(self,vals):
        if not vals.get('name'):
            titik_keramaian_id = self.env['titik.keramaian'].sudo().browse(vals['titik_keramaian_id'])
            vals['name'] = titik_keramaian_id.name
        if vals.get('name'):
            vals['name'] = vals['name'].upper()
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
        
        return super(SalesPlanActivityLine,self).create(vals)

    @api.multi
    def write(self,vals):
        if vals.get('status_operation'):
            if vals['status_operation'] == 'approved':
                vals['reason_reject_operation'] = False
        if vals.get('status_am'):
            if vals['status_am'] == 'approved':
                vals['reason_reject_am'] = False
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
                
        return super(SalesPlanActivityLine,self).write(vals)

    @api.multi
    def action_reject_location(self):
        form_id = self.env.ref('teds_sales_activity_plan_btl.view_teds_sales_plan_activity_reject_form').id
        return {
            'name': ('Reject'),
            'res_model': 'teds.sales.plan.activity.line',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'views': [(form_id, 'form')],
            'view_mode': 'form',
            'target': 'new',
            'view_type': 'form',
            'res_id': self.id,
        }
    @api.multi
    def action_reason_reject(self):
        self.state = 'reject'

    @api.multi
    def action_open_location(self):
        if self.is_location:
            location_id = self.location_id        
            vals = {
                'branch_id':self.branch_id.id,
                'usage':'internal',
                'description':self.name,
                'start_date':self.start_date,
                'end_date':self.end_date,
                'maximum_qty':self.display_unit,
                'active':True,
                'jarak':self.titik_keramaian_id.jarak,
                'biaya':self.total_biaya,
                'beban':False,
                'target':self.target_unit,
                'street':self.street,
                'rt':self.rt,
                'rw':self.rw,
                'state_id':self.state_id.id,
                'city_id':self.city_id.id,
                'kecamatan_id':self.kecamatan_id.id,
                'kecamatan':self.kecamatan_id.name,
                'zip_id':self.kelurahan_id.id,
                'kelurahan':self.kelurahan_id.name
            }
            if not self.location_id:
                obj_location = self.env['stock.picking.type'].search([
                    ('branch_id','=',self.branch_id.id),
                    ('code','=','outgoing')],limit=1)
                location_id = obj_location.default_location_src_id.id
                vals['location_id'] = location_id
                if self.act_type_id.name in ('Pameran','Channel'):
                    vals['jenis'] = self.act_type_id.name.lower()
                vals['name'] = self.name
                
                create_loc = self.env['stock.location'].create(vals)
                self.location_id = create_loc.id
            else:
                self.location_id.write(vals)
         
        self.write({
            'state':'confirmed',
            'confirm_uid':self._uid,
            'confirm_date':datetime.now(),
        })

    def action_view_location(self):
        form_id = self.env.ref('stock.view_location_form').id
        return {
            'name': ('Location'),
            'res_model': 'stock.location',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'views': [(form_id, 'form')],
            'view_mode': 'form',
            'target': 'current',
            'view_type': 'form',
            'res_id': self.location_id.id,
        }   
    
    @api.multi
    def action_view_detail_activity(self):
        form_id = self.env.ref('teds_sales_activity_plan_btl.view_teds_sales_plan_activity_detail_form').id
        return {
            'name': ('Detail'),
            'res_model': 'teds.sales.plan.activity.line',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'views': [(form_id, 'form')],
            'view_mode': 'form',
            'target': 'new',
            'view_type': 'form',
            'res_id': self.id,
        }   

    @api.multi
    def action_revisi_activity(self):
        self.write({
            'state':'draft',
            'status_am':'approved',
            'status_operation':'approved',
            'reason_reject_am':False,
            'reason_reject_operation':False,
            'reason_reject_location':False
        })
        self.activity_id.write({'state':'waiting_for_approval'})
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.onchange('status_am')
    def onchange_status_am(self):
        self.reason_reject_am = False
    
    @api.onchange('status_operation')
    def onchange_status_operation(self):
        self.reason_reject_operation = False

    @api.onchange('jenis_pengajuan')
    def onchange_jenis_pengajuan(self):
        self.location_id = False
    
    @api.onchange('is_location')
    def onchange_is_location(self):
        self.jenis_pengajuan = False
        self.location_id = False
        self.display_unit = False
        self.source_pos_location_id = False

    @api.onchange('jaringan_penjualan','act_type_id','titik_keramaian_id','jenis_pengajuan','location_id')
    def onchange_history_location(self):
        if not self.activity_id.branch_id or not self.activity_id.bulan or not self.activity_id.tahun:
            raise Warning('Silahkan isi data header terlebih dahulu !')
        self.history_location_ids = False
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
            raise Warning('Activity %s ,End date tidak boleh kurang dari start date'%(self.name))

    @api.constrains('end_date')
    @api.one
    def cek_end_date(self):
        if self.end_date :
            month = (calendar.month_name[int(self.activity_id.bulan)])
            end_date = datetime.strptime(self.end_date,"%Y-%m-%d")
            if (int(end_date.month) != int(self.activity_id.bulan)) or (int(end_date.year) != int(self.activity_id.tahun)):
                raise Warning('Activity %s , End date tidak masuk pada periode bulan %s !' %(self.name,month))


    @api.multi
    def action_view_location(self):
        if not self.location_id:
            raise Warning('Location not found !')

        form_id = self.env.ref('stock.view_location_form').id
        return {
            'name': ('Location'),
            'res_model': 'stock.location',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'views': [(form_id, 'form')],
            'view_mode': 'form',
            'target': 'current',
            'view_type': 'form',
            'res_id': self.location_id.id,
        }

    @api.multi
    def action_approved_detail(self):
        self.write({
            'state':'done',
            'approved_location_uid':self._uid,
            'approved_location_date':datetime.now(),
        })
        self.activity_id.cek_activity_open()
    
    @api.multi
    def action_reject_detail(self):
        self.write({
            'state':'reject',
            'reject_location_uid':self._uid,
            'reject_location_date':datetime.now(),
        })
        self.activity_id.cek_activity_open()

    @api.multi
    def action_history_result(self):
        if not self.activity_id.branch_id or not self.activity_id.bulan or not self.activity_id.tahun:
            raise Warning('Silahkan isi data header terlebih dahulu !')
        self.history_location_ids = False
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


class ActivityDetailBiaya(models.Model):
    _name = "teds.activity.detail.biaya"

    @api.multi
    @api.depends('amount','is_ppn')
    def _compute_subtotal(self):
        for me in self:
            subtotal = me.amount
            if me.is_ppn:
                subtotal = me.amount / 0.9
            me.subtotal = subtotal

    activity_id = fields.Many2one('teds.sales.plan.activity.line',ondelete='cascade')
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
    state = fields.Selection([
        ('draft','Draft'),
        ('confirmed','Confirmed')],default='draft',string="Status")

    @api.onchange('name')
    def onchange_finco(self):
        self.finco_id = False
        
class SalesPlanHistoryLocation(models.Model):
    _name = "teds.sales.plan.history.location"

    name = fields.Char('Bulan')
    qty = fields.Integer('Qty')
    activity_id = fields.Many2one('teds.sales.plan.activity.line','Activity',ondelete='cascade')
    detail_ids = fields.One2many('teds.history.location.detail','history_id','Detail')

class HistoryLocationDetail(models.Model):
    _name = "teds.history.location.detail"    

    history_id = fields.Many2one('teds.sales.plan.history.location','History',ondelete='cascade')
    product_id = fields.Many2one('product.product','Product')
    categ_id = fields.Many2one('product.category','Category',related='product_id.categ_id')