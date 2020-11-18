import base64
import xlsxwriter
import tempfile
from cStringIO import StringIO
from datetime import date, datetime, timedelta
from openerp import models, fields, api
from openerp.exceptions import Warning, ValidationError
import openerp.addons.decimal_precision as dp

class teds_nrfs(models.Model):
    _name = "teds.nrfs"
    _description = "NRFS"

    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date()

    @api.depends('lot_id')
    def _compute_lot_data(self):
        for record in self:
            if record.lot_id:
                record.chassis_no = record.lot_id.chassis_no
                record.product_id = record.lot_id.product_id.id
                record.tgl_terima_unit = record.lot_id.receive_date
                record.no_shipping_list = record.lot_id.no_ship_list
                record.ekspedisi_id = record.lot_id.expedisi_id.id

    name = fields.Char(string='No NRFS')
    branch_id = fields.Many2one('wtc.branch', string='Dealer')
    lot_id = fields.Many2one('stock.production.lot', string='Nomor Mesin')
    chassis_no = fields.Char(string='Nomor Rangka', compute='_compute_lot_data')
    product_id = fields.Many2one('product.product', string='Tipe Unit', compute='_compute_lot_data')
    no_shipping_list = fields.Char(string='No Shipping List', compute='_compute_lot_data')
    tipe_nrfs = fields.Selection([
        ('LKUAT','LKUAT'),
        ('LKUAS','LKUAS')
    ], string='Tipe NRFS')
    tgl_nrfs = fields.Date(string='Tanggal', default=_get_default_date)
    tgl_terima_unit = fields.Date(string='Tanggal Penerimaan', compute='_compute_lot_data')
    origin = fields.Char(string='Source Document')
    pemeriksa_id = fields.Many2one('hr.employee', string='Nama Pemeriksa')
    ekspedisi_id = fields.Many2one('res.partner', string='Ekspedisi', compute='_compute_lot_data')
    nopol_ekspedisi = fields.Many2one('wtc.plat.number.line', string='Nopol Ekspedisi', domain="[('partner_id','=',ekspedisi_id)]") # Input
    driver_ekspedisi = fields.Many2one('wtc.driver.line', string='Driver Ekspedisi', domain="[('partner_id','=',ekspedisi_id)]") # Input
    kapal_ekspedisi = fields.Char(string='Nama Kapal', size=100) # FM
    branch_partner_id = fields.Many2one('res.partner', string='AHASS Vendor', domain="[('branch','=',True)]")
    tgl_selesai_est = fields.Date(string='Estimasi Selesai')
    tgl_selesai_actual = fields.Date(string='Aktual Selesai')
    state = fields.Selection([
        ('cancel', 'Cancelled'),
        ('draft', 'Draft'),
        ('rfa', 'Waiting for Approval'),
        ('approved', 'Approved'),
        ('confirmed', 'Confirmed'), # all stock part OK
        ('in_progress', 'In Progress'),
        ('done', 'Done')
    ], string='Status', default='draft')
    cancel_uid = fields.Many2one('res.users', string='Cancelled by')
    cancel_date = fields.Datetime(string='Cancelled on')
    confirm_uid = fields.Many2one('res.users', string='Confirmed by')
    confirm_date = fields.Datetime(string='Confirmed on')

    is_sparepart_pesan = fields.Boolean(string='Sparepart dipesan?')
    is_p2p_md = fields.Boolean(string='Dipenuhi dengan P2P?')
    is_po_urgent = fields.Boolean(string='Dipenuhi dengan PO Urgent?')
    no_po_urg = fields.Char(string='No PO Urgent MD', oldname='no_po_md', size=50)
    tgl_po_urg = fields.Date(string='Tanggal PO Urgent', oldname='tgl_po_md')
    
    mft_nrfs = fields.Boolean(default=False, string='Sudah kirim MFT NRFS?')
    mft_ppo_urg = fields.Boolean(default=False, string='Sudah kirim MFT PPO?')
    nama_file_ppo_urg = fields.Char(string='Nama File PPO')
    tgl_kirim_ppo_urg = fields.Date(string='Tgl Kirim PPO')
    line_ids = fields.One2many('teds.nrfs.line', 'lot_id', string='Detail NRFS')
    approval_history_ids = fields.One2many('teds.nrfs.approval', 'lot_id', string='Detail Approval')
    mft_nrfs_history_ids = fields.One2many('teds.nrfs.mft.history', 'lot_id', string='History MFT NRFS')
    work_order_ids = fields.One2many('wtc.work.order','nrfs_id', string='Detail Work Order')

    def _check_line_ids(self):
        if len(self.line_ids) <= 0:
            raise Warning('Detail masalah harus diisi!')
        msg = ""
        for x in self.line_ids:
            if len(x.gejala_ids) <= 0:
                msg += "Gejala untuk sparepart bermasalah %s harus diisi!\n" % (x.part_id.product_tmpl_id.name)
            if len(x.penyebab_ids) <= 0:
                msg += "Penyebab untuk sparepart bermasalah %s harus diisi!\n" % (x.part_id.product_tmpl_id.nama_file_nrfs)
            if x.qty <= 0:
                msg += "Qty sparepart bermasalah %s harus lebih dari 0!\n" % (x.part_id.product_tmpl_id.name)
        if msg:
            raise Warning(msg)

    @api.multi
    def action_check_availability(self):
        for x in self.line_ids:
            x._show_part_stock_all()
    
    @api.onchange('branch_partner_id')
    def _change_stock(self):
        self.action_check_availability()

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].suspend_security().get_per_branch(vals['branch_id'],vals['tipe_nrfs'])
        return super(teds_nrfs, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('line_ids'):
            is_sparepart_pesan = False
            for x in vals['line_ids']:
                if x[0] == 0: # 0 Create data
                    if x[2].get('is_sparepart_pesan', False):
                        is_sparepart_pesan = True
                        break
                elif x[0] in [1,4]:
                    if x[2]: # 1 Update data
                        if x[2].get('is_sparepart_pesan', False):
                            is_sparepart_pesan = True
                            break
                    else: # 4 Retain relationship
                        line_obj = self.line_ids.suspend_security().browse(x[1])
                        if line_obj.is_sparepart_pesan:
                            is_sparepart_pesan = True
                            break
                elif x[0] in [2,3]: # 2,3 Delete data
                    line_objs = self.line_ids.suspend_security().search([
                        ('lot_id','=',self.id),('id','!=',x[1])
                    ])
                    if line_objs:
                        is_sparepart_pesan = all([l.is_sparepart_pesan for l in line_objs])
            vals['is_sparepart_pesan'] = is_sparepart_pesan
        return super(teds_nrfs, self).write(vals)

    @api.multi
    def unlink(self):
        raise Warning('Data NRFS tidak bisa dihapus!')

    @api.multi
    def copy(self):
        raise Warning('Data NRFS tidak bisa diduplikasi!')

    @api.multi
    def action_cancel(self):
        self.write({
            'state': 'cancel',
            'cancel_uid': self._uid,
            'cancel_date': self._get_default_date()
        })
    
    @api.multi
    def action_rfa(self):
        self._check_line_ids()
        self.action_check_availability()
        self.write({'state': 'rfa'})

    @api.multi
    def action_cancel_rfa(self):
        self.write({'state': 'draft'})

    @api.multi
    def action_approve(self):
        self._check_line_ids()
        self.action_check_availability()
        self.write({
            'state': 'approved',
            'approval_history_ids': [[0, 0, {
                'type': 'Approve NRFS',
                'pelaksana_uid': self._uid,
                'pelaksana_date': self._get_default_date()
            }]]
        })

    @api.multi
    def action_reject_form(self):
        form_id = self.env.ref('teds_nrfs.teds_nrfs_reject_view_form').id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'teds.nrfs.reject.wizard',
            'name': 'Reject NRFS',
            'views': [(form_id, 'form')],
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': False,
            'target': 'new',
            'context': {'default_nrfs_id': self.id}
        }

    @api.multi
    def action_cancel_approve_form(self):
        form_id = self.env.ref('teds_nrfs.teds_nrfs_cancel_approve_view_form').id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'teds.nrfs.cancel.approve.wizard',
            'name': 'Cancel Approve NRFS',
            'views': [(form_id, 'form')],
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': False,
            'target': 'new',
            'context': {'default_nrfs_id': self.id}
        }

    @api.multi
    def action_confirm(self):
        self._check_line_ids()
        # check penanganan dan jasa
        msg = ""
        for x in self.line_ids:
            if len(x.service_ids) <= 0:
                msg += "Jasa perbaikan untuk sparepart bermasalah %s harus diisi!\n" % (x.part_id.product_tmpl_id.name)
            if not x.penanganan_vendor_id:
                msg += "Penanganan untuk sparepart bermasalah %s harus diisi!\n" % (x.part_id.product_tmpl_id.name)
        if msg:
            raise Warning(msg)
        # cek stok
        self.action_check_availability()
        self.write({
            'state': 'confirmed',
            'confirm_uid': self._uid,
            'confirm_date': self._get_default_date()
        })

    @api.multi
    def action_confirm_md_sparepart(self):
        po_urg_line = []
        for x in self.line_ids:
            if x.is_po_urgent:
                po_urg_line.append(x.id)
        if po_urg_line:
            now_date = date.today()
            no_po_urg = self.env['ir.sequence'].next_by_code('po_sparepart_urgent')
            self.line_ids.browse(po_urg_line).write({
                'no_po_urg': no_po_urg,
                'tgl_po_urg': now_date.strftime('%Y-%m-%d')
            })
            self.is_po_urgent = True
            self.no_po_urg = no_po_urg
            self.tgl_po_urg = now_date.strftime('%Y-%m-%d')
        else:
            self.write({'is_p2p_md': True})

    @api.multi
    def action_create_wo(self):
        wo_obj = self.env['wtc.work.order'].suspend_security().search([('nrfs_id','=',self.id)],limit=1)
        if not wo_obj:
            msg = "" # warning
            penanganan_wh_part = [
                self.env.ref('teds_nrfs.nrfs_penanganan_unit_tanpa_part').id,
                self.env.ref('teds_nrfs.nrfs_penanganan_unit_repainting_vendor').id,
                self.env.ref('teds_nrfs.nrfs_penanganan_unit_repainting_gudang').id
            ]
            service_list = []
            wo_line_vals = []
            wo_branch_obj = self.env['wtc.branch'].suspend_security().search([('partner_id','=',self.branch_partner_id.id)],limit=1)
            if not wo_branch_obj:
                raise Warning('Branch invalid: AHASS Vendor %d [%s] %s' % (self.branch_partner_id.id, self.branch_partner_id.rel_code, self.branch_partner_id.name))
            pricelist = wo_branch_obj.pricelist_part_sales_id
            for x in self.line_ids:
                x._show_part_stock_all()
                if x.penanganan_vendor_id.id not in penanganan_wh_part and x.total_stock < x.qty:
                    msg += "Stock product %s tidak mencukupi: Qty avb vendor %d, Qty yang dibutuhkan %d\n" % (x.part_id.product_tmpl_id.name, x.total_stock, x.qty)
                    continue
                if x.penanganan_vendor_id.id not in penanganan_wh_part:
                    price = pricelist.price_get(x.part_id.id, 1)[pricelist.id]
                    wo_line_vals.append([0, 0, {
                        'categ_id': 'Sparepart',
                        'product_id': x.part_id.id,
                        'name': x.part_id.description,
                        'name_show': x.part_id.description,
                        'product_qty': x.qty,
                        'product_uom': x.part_id.uom_id.id,
                        'price_unit': price,
                        'price_unit_show': price,
                        'warranty': 0.0,
                        'discount':0,
                        'tax_id': [[6,0,[x.part_id.taxes_id.id]]],
                        'tax_id_show': [[6,0,[x.part_id.taxes_id.id]]],
                        'state':'draft'
                    }])
                for y in x.service_ids:
                    if y.id not in service_list:
                        price_jasa = self.env['wtc.work.order.line'].suspend_security()._get_harga_jasa(y.id,self.branch_id.id,self.lot_id.product_id.id)
                        wo_line_vals.append([0, 0, {
                            'categ_id': 'Service',
                            'product_id': y.id,
                            'name': y.description,
                            'name_show': y.description,
                            'product_qty': 1,
                            'product_uom': y.uom_id.id,
                            'price_unit': price_jasa,
                            'price_unit_show': price_jasa,
                            'warranty': 0.0,
                            'discount':0,
                            'tax_id': [[6,0,[y.taxes_id.id]]],
                            'tax_id_show': [[6,0,[y.taxes_id.id]]],
                            'state':'draft'
                        }])
                        service_list.append(y.id)                    
            if msg:
                raise Warning(msg)
            customer_id = driver_id = mobile = False
            if self.tipe_nrfs == 'LKUAT':
                customer_id = self.ekspedisi_id.id
                driver_id = self.ekspedisi_id.id
                mobile = self.ekspedisi_id.mobile if self.ekspedisi_id.mobile else False
            elif self.tipe_nrfs == 'LKUAS':
                customer_obj = self.env['res.partner'].suspend_security().search([('default_code','=','MML-LKUAS')],limit=1)
                if customer_obj:
                    customer_id = customer_obj.id
                    driver_id = customer_obj.id
                    mobile = customer_obj.mobile if customer_obj.mobile else False
            wo_vals = {
                'branch_id': wo_branch_obj.id,
                'division': 'Sparepart',
                'type': 'CLA',
                'nrfs_id': self.id,
                'lot_id': self.lot_id.id,
                'chassis_no': self.lot_id.chassis_no,
                'product_id': self.lot_id.product_id.id,
                'tahun_perakitan': self.lot_id.tahun,
                'tanggal_pembelian': self.lot_id.receive_date,
                'km': 1,
                'kpb_ke': False,
                'customer_id': customer_id,
                'driver_id': driver_id,
                'mobile': mobile,
                'work_lines': wo_line_vals
            }
            wo_obj = self.env['wtc.work.order'].suspend_security().create(wo_vals)
            if wo_obj:
                self.write({'state': 'in_progress'})
        form_id = self.env.ref('wtc_work_order.view_wtc_work_order_form').id
        return {
            'name': 'Work Order',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.work.order',
            'res_id': wo_obj.id,
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }
        
class teds_nrfs_line(models.Model):
    _name = "teds.nrfs.line"
    _description = "NRFS - Detail Masalah"

    def _get_product_ids_by_division(self, division):
        get_product_query = """
            SELECT pp.id
            FROM product_product pp
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
            JOIN product_category pc ON pt.categ_id = pc.id
            JOIN product_category pc_p ON pc.parent_id = pc_p.id
            WHERE pc_p.name = '%s'
        """ % (division)
        self._cr.execute(get_product_query)
        product_ress = self._cr.fetchall()
        return product_ress or False

    def _set_domain_part_id(self):
        domain = [('id','=',0)]
        products = self._get_product_ids_by_division('Sparepart')
        if products:
            domain = [('id','=',[x[0] for x in products])]
        return domain

    def _set_domain_service_ids(self):
        domain = [('id','=',0)]
        products = self._get_product_ids_by_division('Service')
        if products:
            domain = [('id','=',[x[0] for x in products])]
        return domain

    @api.depends('qty','total_stock')
    def _compute_stock(self):
        for x in self:
            if x.total_stock < x.qty:
                x.is_stock_ok = False
            else:
                x.is_stock_ok = True

    lot_id = fields.Many2one('teds.nrfs', string='NRFS ID')
    rel_partner_id = fields.Many2one(related='lot_id.branch_partner_id', string='Vendor')
    part_id = fields.Many2one('product.product', string='Parts Bermasalah', domain=_set_domain_part_id)
    description = fields.Char(related='part_id.product_tmpl_id.default_code', string='Deskripsi Part')
    qty = fields.Float(string='Qty', digits=dp.get_precision('Product Unit of Measure'))
    gejala_ids = fields.Many2many('teds.nrfs.master.gejala', 'teds_nrfs_line_gejala_rel', 'line_id', 'gejala_id', string='Gejala')
    penyebab_ids = fields.Many2many('teds.nrfs.master.penyebab', 'teds_nrfs_line_penyebab_rel', 'line_id', 'penyebab_id', string='Penyebab')
    penanganan_vendor_id = fields.Many2one('teds.nrfs.master.penanganan.unit', string='Penanganan', domain="[('master_type','=','vendor')]")
    penanganan_id = fields.Many2one('teds.nrfs.master.penanganan.unit', string='Penanganan')
    is_sparepart_pesan = fields.Boolean(string='Sparepart dipesan?', default=False)
    is_po_urgent = fields.Boolean(string='Dipenuhi dengan PO Urgent?', default=False)
    no_po_urg = fields.Char(string='No PO Urgent MD', oldname='no_po_md', size=50)
    tgl_po_urg = fields.Date(string='Tanggal PO Urgent', oldname='tgl_po_md')
    no_distribusi = fields.Char(string='No Distribusi')
    service_ids = fields.Many2many('product.product', 'teds_nrfs_line_jasa_rel', 'line_id', 'service_id', string='Jasa', domain=_set_domain_service_ids)
    total_stock = fields.Float(string='Qty Avb Vendor', digits=dp.get_precision('Product Unit of Measure'))
    total_stock_md = fields.Float(string='Qty Avb MD', digits=dp.get_precision('Product Unit of Measure'))
    total_stock_all = fields.Float(string='Qty Avb All', digits=dp.get_precision('Product Unit of Measure'))
    is_stock_ok = fields.Boolean(string='Stock Sparepart OK?', compute='_compute_stock')
    stock_ids = fields.One2many('teds.nrfs.line.stock', 'line_id', string='Info Stok')

    _sql_constraints = [
        ('unique_part_id', 'unique(lot_id, part_id)', 'Ditemukan part duplicate, silahkan cek kembali!'),
    ]

    def _check_part_stock(self, product_id, where_partner):
        _get_stock_query = """
            SELECT 
                dealer.id AS branch_id,
                COALESCE(st.qty_stock,0) - (COALESCE(intransit_out.qty_intransit_out,0) + COALESCE(so_md.qty_rfa,0)) AS qty_stock,
                COALESCE(intransit_in.qty_intransit_in,0) AS qty_intransit_in
            FROM wtc_branch dealer
            JOIN res_partner dealer_p ON dealer.partner_id = dealer_p.id
            LEFT JOIN (
                SELECT 
                    b.id AS branch_id,
                    SUM(COALESCE(sq.qty,0)) AS qty_stock
                FROM stock_quant sq
                JOIN stock_location l ON sq.location_id = l.id
                JOIN wtc_branch b ON l.branch_id = b.id
                JOIN res_partner p ON b.partner_id = p.id
                WHERE l.usage = 'internal'
                AND sq.consolidated_date IS NOT NULL
                AND sq.product_id = %d
                GROUP BY b.id, sq.product_id
            ) st ON dealer.id = st.branch_id
            LEFT JOIN (
                SELECT 
                    b.id AS branch_id,
                    SUM(COALESCE(sm.product_uom_qty,0)) AS qty_intransit_out
                from stock_picking sp
                JOIN stock_picking_type spt ON sp.picking_type_id = spt.id
                JOIN stock_move sm ON sp.id = sm.picking_id
                JOIN wtc_branch b ON sp.branch_id = b.id
                JOIN res_partner p ON b.partner_id = p.id
                WHERE spt.code IN ('outgoing','interbranch_out')
                AND sp.state NOT IN ('draft','cancel','done')
                AND sm.product_id = %d
                GROUP BY b.id, sm.product_id
            ) intransit_out ON dealer.id = intransit_out.branch_id
            LEFT JOIN (
                SELECT 
                    b.id as branch_id,
                    SUM(COALESCE(sm.product_uom_qty,0)) AS qty_intransit_in
                FROM stock_picking sp
                JOIN stock_picking_type spt ON sp.picking_type_id = spt.id
                JOIN stock_move sm ON sp.id = sm.picking_id
                JOIN wtc_branch b ON sp.branch_id = b.id
                JOIN res_partner p ON b.partner_id = p.id
                WHERE spt.code IN ('incoming','interbranch_in')
                AND sp.state NOT IN ('draft','cancel','done')
                AND sm.product_id = %d
                GROUP BY b.id, sm.product_id
            ) intransit_in ON dealer.id = intransit_in.branch_id
            LEFT JOIN (
                SELECT
                    b.id as branch_id,
                    COALESCE(SUM(sol.product_uom_qty),0) AS qty_rfa
                FROM sale_order_line sol
                JOIN sale_order so ON sol.order_id = so.id
                JOIN wtc_branch b ON so.branch_id = b.id
                JOIN res_partner p ON b.partner_id = p.id
                WHERE so.division = 'Sparepart'
                AND so.state IN ('waiting_for_approval','approved')
                AND sol.product_id = %d
                GROUP BY b.id, sol.product_id
            ) so_md ON dealer.id = so_md.branch_id
            %s
            AND COALESCE(st.qty_stock,0) - (COALESCE(intransit_out.qty_intransit_out,0) + COALESCE(so_md.qty_rfa,0)) + COALESCE(intransit_in.qty_intransit_in,0) > 0
        """ % (product_id, product_id, product_id, product_id, where_partner)
        self._cr.execute(_get_stock_query)
        stock_ress = self._cr.dictfetchall()
        return stock_ress

    def _show_part_stock_all(self):
        self.total_stock = 0
        self.total_stock_all = 0
        self.stock_ids = False
        
        if self.rel_partner_id and self.part_id and self.qty:
            total_stock = 0
            total_stock_md = 0
            total_stock_all = 0
            stock_vals = []
            mml_obj = self.env['wtc.branch'].suspend_security().search([('code','=','MML')],limit=1)

            where_partner = " WHERE dealer_p.id IN %s " % (str(tuple([self.rel_partner_id.id])).replace(",)",")"))
            stock = self._check_part_stock(self.part_id.id, where_partner)
            for x in stock:
                total_stock += x['qty_stock'] + x['qty_intransit_in']

            where_partner_md = " WHERE dealer_p.id IN %s " % (str(tuple([mml_obj.partner_id.id])).replace(",)",")"))
            stock = self._check_part_stock(self.part_id.id, where_partner_md)
            for x in stock:
                total_stock_md += x['qty_stock'] + x['qty_intransit_in']

            where_partner_all = " WHERE (dealer.default_supplier_id = %d OR dealer_p.id = %d) " % (mml_obj.partner_id.id, mml_obj.partner_id.id)
            stock = self._check_part_stock(self.part_id.id, where_partner_all)
            for x in stock:
                stock_vals.append([0,0,x])
                total_stock_all += x['qty_stock'] + x['qty_intransit_in']

            self.total_stock = total_stock
            self.total_stock_md = total_stock_md
            self.total_stock_all = total_stock_all
            self.stock_ids = stock_vals
    
    @api.onchange('part_id','qty')
    def _change_stock(self):
        self._show_part_stock_all()

    @api.onchange('penanganan_vendor_id')
    def _change_is_sparepart_pesan_and_penanganan_id(self):
        self.is_sparepart_pesan = False
        self.penanganan_id = False
        if self.penanganan_vendor_id:
            self.penanganan_id = self.penanganan_vendor_id.id
            if self.penanganan_vendor_id.id == self.env.ref('teds_nrfs.nrfs_penanganan_unit_part_pesan_biasa').id:
                self.is_sparepart_pesan = True

    @api.onchange('penanganan_id')
    def _change_is_po_urgent(self):
        self.is_po_urgent = False
        if self.penanganan_id and self.penanganan_id.id == self.env.ref('teds_nrfs.nrfs_penanganan_unit_part_pesan_urgent').id:
            self.is_po_urgent = True

class teds_nrfs_mft_history(models.Model):
    _name = "teds.nrfs.mft.history"
    _description = "NRFS - History MFT"

    lot_id = fields.Many2one('teds.nrfs', string='NRFS ID')
    nama_file_nrfs = fields.Char(string='Nama File NRFS')
    tgl_kirim_nrfs = fields.Date(string='Tanggal Kirim NRFS')

class teds_nrfs_line_stock(models.Model):
    _name = "teds.nrfs.line.stock"
    _description = "NRFS - Stok Sparepart"

    line_id = fields.Many2one('teds.nrfs.line', 'ID Case NRFS', ondelete='cascade')
    branch_id = fields.Many2one('wtc.branch', string='Dealer')
    qty_stock = fields.Float(string='Qty Stock', digits=dp.get_precision('Product Unit of Measure'))
    qty_intransit_in = fields.Float(string='Qty Intransit IN', digits=dp.get_precision('Product Unit of Measure'))

class teds_nrfs_approval(models.Model):
    _name = "teds.nrfs.approval"
    _description = "NRFS - Approval"

    lot_id = fields.Many2one('teds.nrfs', string='ID NRFS', ondelete='cascade')
    type = fields.Char(string='Tipe Approval')
    pelaksana_uid = fields.Many2one('res.users', string='Approved / Rejected / Cancelled by')
    pelaksana_date = fields.Datetime(string='Approved / Rejected / Cancelled on')
    reason = fields.Char(string='Alasan Reject / Cancel')

class teds_nrfs_reject_wizard(models.TransientModel):
    _name = "teds.nrfs.reject.wizard"
    _description = "NRFS - Reject Wizard"

    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date()
    
    nrfs_id = fields.Many2one('teds.nrfs', string='ID NRFS', ondelete='cascade')
    reject_reason = fields.Text(string='Alasan Reject')

    @api.multi
    def action_reject(self):
        self.nrfs_id.suspend_security().write({
            'state': 'draft',
            'approval_history_ids': [[0, 0, {
                'type': 'Reject NRFS',
                'pelaksana_uid': self._uid,
                'pelaksana_date': self._get_default_date(),
                'reason': self.reject_reason
            }]]
        })

class teds_nrfs_cancel_approve_wizard(models.TransientModel):
    _name = "teds.nrfs.cancel.approve.wizard"
    _description = "NRFS - Cancel Approve Wizard"

    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date()
    
    nrfs_id = fields.Many2one('teds.nrfs', string='ID NRFS', ondelete='cascade')
    cancel_reason = fields.Text(string='Alasan Cancel')

    @api.multi
    def action_cancel_approve(self):
        self.nrfs_id.suspend_security().write({
            'state': 'draft',
            'approval_history_ids': [[0, 0, {
                'type': 'Cancel Approve NRFS',
                'pelaksana_uid': self._uid,
                'pelaksana_date': self._get_default_date(),
                'reason': self.cancel_reason
            }]]
        })