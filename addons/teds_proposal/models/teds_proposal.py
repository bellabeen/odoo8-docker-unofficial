import base64
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, ValidationError
import openerp.addons.decimal_precision as dp

class Proposal(models.Model):
    _name = "teds.proposal"
    _description = "Proposal Online"

    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date()

    # def _set_domain_department_id(self):
    #     domain = [('id','=',0)]
    #     if self._uid == 1:
    #         domain = []
    #     else:
    #         get_department_query = """
    #             SELECT dept.id
    #             FROM hr_department dept
    #             JOIN hr_employee emp ON dept.id = emp.department_id
    #             JOIN resource_resource rr ON emp.resource_id = rr.id
    #             JOIN res_users ru ON rr.user_id = ru.id
    #             WHERE ru.id = %d
    #         """ % (self._uid)
    #         self._cr.execute(get_department_query)
    #         dept_ress = self._cr.fetchall()
    #         if dept_ress:
    #             domain = [('id','in',[x[0] for x in dept_ress])]
    #     return domain

    # def _get_default_pic(self):
    #     pic_id = False
    #     get_pic_id_query = """
    #         SELECT emp.id
    #         FROM hr_employee emp
    #         JOIN resource_resource rr ON emp.resource_id = rr.id
    #         JOIN res_users u ON rr.user_id = u.id
    #         WHERE u.id = %d
    #     """ % (self._uid)
    #     self._cr.execute(get_pic_id_query)
    #     ress = self._cr.fetchall()
    #     if ress:
    #         pic_id = ress[0]
    #     return pic_id

    @api.depends('item_ids.amount_total')
    def _compute_amount_total(self):
        for record in self:
            record.amount_total = sum(x.amount_total for x in record.item_ids)

    @api.depends('item_ids.amount_reserved','item_ids.amount_paid')
    def _compute_amount_paid(self):
        for record in self:
            record.amount_reserved = sum(x.amount_reserved for x in record.item_ids)
            record.amount_paid = sum(x.amount_paid for x in record.item_ids)

    @api.depends('state','amount_total','amount_reserved','amount_paid')
    def _compute_amount_sisa(self):
        for record in self:
            amount_sisa = record.amount_total - (record.amount_reserved + record.amount_paid)
            if amount_sisa < 0:
                record.amount_sisa = 0
                record.amount_over = abs(amount_sisa)
                if record.state == 'draft':
                    record.budget_state = False
                else:
                    record.budget_state = 'over' 
            elif amount_sisa == 0: 
                record.amount_sisa = amount_sisa
                record.amount_over = 0
                if record.state == 'draft':
                    record.budget_state = False
                else:
                    record.budget_state = 'on'
            else:
                record.amount_sisa = amount_sisa
                record.amount_over = 0
                if record.state == 'draft':
                    record.budget_state = False
                else:
                    record.budget_state = 'under'

    @api.depends('sponsor_ids.amount')
    def _compute_amount_sponsor(self):
        for record in self:
            record.amount_total_sponsor = sum(x.amount for x in record.sponsor_ids)

    def _compute_is_coo(self):
        is_coo_query = """
            SELECT 
                u.id AS user_id,
                emp.id AS employee_id, 
                g.name AS coo_group
            FROM hr_employee emp
            JOIN resource_resource rr ON emp.resource_id = rr.id
            JOIN res_users u ON rr.user_id = u.id
            JOIN res_groups_users_rel gu ON u.id = gu.uid
            JOIN res_groups g ON gu.gid = g.id
            WHERE g.name = 'COO'
            AND u.id = %d
        """ % (self._uid)
        self._cr.execute(is_coo_query)
        is_coo = self._cr.fetchone()
        if is_coo:
            self.is_coo = True
        else:
            self.is_coo = False

    name = fields.Char(string='Nomor Proposal')
    date_proposal = fields.Date(string='Tanggal', default=_get_default_date)
    branch_id = fields.Many2one('wtc.branch', string='Branch', ondelete='restrict') #
    division = fields.Selection([
        ('Unit','Unit'),
        ('Sparepart','Sparepart'),
        ('Umum','Umum'),
    ], string='Divisi')
    pic_id = fields.Many2one('hr.employee', string='PIC', domain = [('id','=',0)], ondelete='restrict')
    department_id = fields.Many2one('hr.department', string='Departemen', ondelete='restrict')
    # NOTE: NO BUDGET
    # act_budget_id = fields.Many2one('teds.master.act.budget', string='Kode Budget', ondelete='restrict')
    # act_budget_activity = fields.Char(string='Keterangan Aktivitas')
    kode_budget = fields.Char(string='Kode Budget')
    event = fields.Text(string='Keterangan Event')
    latar_belakang = fields.Html(string='Background')
    tujuan = fields.Html(string='Tujuan')
    what = fields.Html(string='What')
    # why = fields.Text(string='Why')
    how = fields.Html(string='How')
    is_penyimpangan = fields.Boolean(string='Penyimpangan?', default=False)
    is_coo = fields.Boolean(string='Grup COO?', compute=_compute_is_coo)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('rfa', 'Waiting for Approval'),
        ('approved', 'Approved'),
        ('reject', 'Rejected'),
        ('close','Closed'),
        ('done', 'Done')
    ], default='draft', string='Status')
    budget_state = fields.Selection([
        ('under','Under Budget'),
        ('on','On Budget'),
        ('over','Over Budget'),
    ], string='Status Budget', compute='_compute_amount_sisa', store=True)
    approval_state = fields.Selection([
        ('b','Belum Request'),
        ('rf','Request for Approval'),
        ('a','Approved'),
        ('r','Rejected'),
        ('c','Closed')
    ], string='Status Approval', default='b', readonly=False)
    # total proposal
    amount_total = fields.Float(string='Total', digits=dp.get_precision('Product Price'), compute='_compute_amount_total', store=True)
    # limit proposal berdasarkan limit approver tertinggi
    amount_approved = fields.Float(string='Total Approved', digits=dp.get_precision('Product Price'))
    # amount_reserved: amount AVP & NC status RFA
    amount_reserved = fields.Float(string='Total Reserved', digits=dp.get_precision('Product Price'), compute='_compute_amount_paid', store=True)
    # amount AVP & NC status approved
    amount_paid = fields.Float(string='Total Paid', digits=dp.get_precision('Product Price'), compute='_compute_amount_paid', store=True)
    amount_sisa = fields.Float(string='Total Sisa', digits=dp.get_precision('Product Price'), compute='_compute_amount_sisa')
    amount_over = fields.Float(string='Total Over', digits=dp.get_precision('Product Price'), compute='_compute_amount_sisa', store=True)
    amount_total_sponsor = fields.Float(string='Beban Sponsor', digits=dp.get_precision('Product Price'), compute='_compute_amount_sponsor', store=True)
    is_print_prop_ok = fields.Boolean(string='Print Proposal OK?', default=False)
    PRINT_PROP_LIMIT = 5000000 # limit GM
    # Audit Trail
    close_uid = fields.Many2one('res.users', string='Closed by', readonly=True)
    close_date = fields.Datetime(string='Closed on', readonly=True)
    # Child Fields
    item_ids = fields.One2many('teds.proposal.line', 'proposal_id', string='Detail')
    sponsor_ids = fields.One2many('teds.proposal.sponsor', 'proposal_id', string='Detail Sponsor')
    schedule_ids = fields.One2many('teds.proposal.schedule', 'proposal_id', string='Schedule')
    attachment_ids = fields.One2many('teds.proposal.attachment', 'proposal_id', string='Dokumen Tambahan')
    approval_ids = fields.One2many('wtc.approval.line', 'transaction_id', string='Budget Approval',domain=[('form_id','=',_name)])
    payment_ids = fields.One2many('teds.proposal.payment', 'proposal_id', string='Detail Pembayaran')

    # Detail proposal wajib diisi
    @api.constrains('item_ids')
    def _check_empty_line(self):
        if len(self.item_ids) <= 0:
            raise ValidationError('Perhatian!\nDetail proposal harus diisi.')

    # Jadwal proposal wajib diisi
    @api.constrains('schedule_ids')
    def _check_empty_schedule(self):
        if len(self.schedule_ids) <= 0:
            raise ValidationError('Perhatian!\nSchedule proposal harus diisi.')

    @api.onchange('branch_id')
    def _set_domain_pic_id(self):
        self.pic_id = False
        domain = {'pic_id': [('id','=',0)]}
        if self.branch_id:
            get_pic_query = """
                SELECT emp.id
                FROM hr_employee emp
                JOIN resource_resource rr ON emp.resource_id = rr.id
                JOIN hr_job j ON emp.job_id = j.id
                JOIN res_users u ON rr.user_id = u.id
                WHERE (emp.tgl_keluar IS NULL OR emp.tgl_keluar > NOW())
                AND u.active = True
                AND rr.active = True
                AND emp.branch_id = %d
            """ % (self.branch_id.id)
            self._cr.execute(get_pic_query)
            pic_ress = self._cr.fetchall()
            if pic_ress:
                domain = {'pic_id': [('id','in',[x[0] for x in pic_ress])]}
        return {'domain': domain}

    @api.onchange('pic_id')
    def _onchange_department_id(self):
        self.department_id = False
        if self.pic_id and self.pic_id.department_id:
            self.department_id = self.pic_id.department_id.id

    # NOTE: NO BUDGET
    # @api.onchange('department_id')
    # def _reset_act_budget_id(self):
    #     self.act_budget_id = False
    
    # NOTE: NO BUDGET
    # @api.onchange('department_id')
    # def _onchange_department_id(self):
    #     domain = {'act_budget_id': [('id','=',0)]}
    #     if self.department_id:
    #         budget_ids = self.env['teds.master.act.budget'].suspend_security().search([
    #             ('department_id','=',self.department_id.id),
    #             ('year','=',str(date.today().year))
    #         ])
    #         if budget_ids:
    #             domain = {'act_budget_id': [('id','in',[x.id for x in budget_ids])]}
    #     return {'domain': domain}

    # NOTE: NO BUDGET
    # @api.onchange('act_budget_id')
    # def _onchange_act_budget_id(self):
    #     self.act_budget_activity = False
    #     if self.act_budget_id:
    #         self.act_budget_activity = self.act_budget_id.activity

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'PROPOSAL')
        return super(Proposal, self).create(vals)

    @api.multi
    def unlink(self):
        for x in self:
            if x.state != 'draft':
                raise Warning('Proposal selain status Draft tidak bisa dihapus!')
        return super(Proposal, self).unlink()

    @api.multi
    def copy(self, default=None, context=None):
        item_ids = []
        sponsor_ids = []
        schedule_ids = []
        if default is None:
            default = {}
        for x in self.item_ids:
            item_ids.append([0, 0, {
                'description': x.description,
                'qty': x.qty,
                'price_unit': x.price_unit,
                'amount_total': x.amount_total,
                'jenis_pembayaran': x.jenis_pembayaran,
                'supplier_id': x.supplier_id.id,
                'cash_remark': x.cash_remark,
                'amount_reserved': 0,
                'amount_paid': 0,
                'payment_ids': []
            }])
        for x in self.sponsor_ids:
            sponsor_ids.append([0, 0, {
                'supplier_id': x.supplier_id.id,
                'amount': x.amount,
            }])
        for x in self.schedule_ids:
            schedule_ids.append([0, 0, {
                'location': x.location,
                'date_start': x.date_start,
                'date_end': x.date_end,
                'day_count': (datetime.strptime(x.date_end, "%Y-%m-%d") - datetime.strptime(x.date_start, "%Y-%m-%d")).days
            }])
        name = self.env['ir.sequence'].get_per_branch(self.branch_id.id, 'PROPOSAL')
        default.update({
            'name': name,
            'branch_id': self.branch_id.id,
            'date_proposal': date.today(),
            'division': self.division,
            'pic_id': self.pic_id.id,
            'department_id': self.department_id.id,
            'event': self.event,
            'kode_budget': self.kode_budget,
            'latar_belakang': self.latar_belakang,
            'tujuan': self.tujuan,
            'what': self.what,
            'how': self.how,
            'state': 'draft',
            'budget_state': False,
            'approval_state': 'b',
            'amount_total': self.amount_total,
            'amount_approved': 0,
            'amount_reserved': 0,
            'amount_paid': 0,
            'amount_sisa': 0,
            'amount_over': 0,
            'amount_total_sponsor': self.amount_total_sponsor,
            'is_print_prop_ok': False,
            'close_uid': False,
            'close_date': False,
            'item_ids': item_ids,
            'sponsor_ids': sponsor_ids,
            'schedule_ids': schedule_ids,
            'attachment_ids': [],
            'approval_ids': [],
            'payment_ids': []
        })
        return super(Proposal, self).copy(default=default, context=context)

    def action_proposal_tree(self):
        tree_id = self.env.ref('teds_proposal.view_teds_proposal_tree').id
        form_id = self.env.ref('teds_proposal.view_teds_proposal_form').id
        search_view_id = self.env.ref('teds_proposal.view_teds_proposal_filter').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Proposal',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'teds.proposal',
            'views': [(tree_id, 'tree'), (form_id, 'form')],
            'search_view_id': search_view_id,
            'context': {'readonly_by_pass': 1, 'search_default_rfa': 1}
        }

    @api.multi
    def action_rfa(self):
        # if self.branch_id.code in ['MML','HHO']:
        #     obj_matrix = self.env['wtc.approval.matrixbiaya'].request_by_dept(self, self.amount_total)
        # else:
        obj_matrix = self.env['wtc.approval.matrixbiaya'].request_by_value(self, self.amount_total)
        if obj_matrix:
            self.write({
                'state': 'rfa',
                'approval_state': 'rf'
            })

    @api.multi
    def action_revise(self):
        self.write({'state': 'draft'})

    def _check_budget_approval(self, proposal_model_id):
        get_proposal_limit_query = """
            SELECT COALESCE(MAX(al.limit),0)
            FROM teds_proposal prop
            JOIN wtc_approval_line al ON al.transaction_id = prop.id AND al.form_id = %d
            WHERE prop.id = %d
            AND al.sts = '2'
        """ % (proposal_model_id, self.id)
        self._cr.execute(get_proposal_limit_query)
        limit_ress = self._cr.fetchone()
        if limit_ress[0] <= 0: # belum approve by budget
            # limit 1 khusus staf budget-checking
            get_budget_group_query = """
                SELECT 
                    CONCAT(md.module, '.', md.name) AS group_name
                FROM ir_model_data md
                JOIN res_groups g ON md.res_id = g.id AND md.model = 'res.groups'
                JOIN wtc_approval_line al ON g.id = al.group_id AND al.form_id = %d AND al.transaction_id = %d
                WHERE al.limit = 1
            """ % (proposal_model_id, self.id)
            self._cr.execute(get_budget_group_query)
            group_ress = self._cr.fetchone()
            if not group_ress[0]:
                raise Warning('Matrix approval by staf budget tidak ditemukan. Cek kembali matrix approval Proposal!')
            if not self.env.user.has_group(str(group_ress[0])):
                raise Warning('Proposal belum di-approve oleh staf budget!')
        return True

    @api.multi
    def action_approved(self):
        proposal_model_id = self.env['ir.model'].suspend_security().search([('model','=','teds.proposal')]).id
        self._check_budget_approval(proposal_model_id)
        approval_sts = self.env['wtc.approval.matrixbiaya'].approve(self)
        if approval_sts == 2: # not fully approved
            get_proposal_limit_query = """
                SELECT MAX(al.limit)
                FROM teds_proposal prop
                JOIN wtc_approval_line al ON al.transaction_id = prop.id AND al.form_id = %d
                WHERE prop.id = %d
                AND al.sts = '2'
            """ % (proposal_model_id, self.id)
            self._cr.execute(get_proposal_limit_query)
            limit_ress = self._cr.fetchone()
            self.amount_approved = limit_ress[0]
            if limit_ress[0] >= self.PRINT_PROP_LIMIT:
                self.is_print_prop_ok = True
        elif approval_sts == 1:
            self.write({
                'approval_state':'a',
                'state':'approved',
                'amount_approved': self.amount_total,
                'is_print_prop_ok': True
            })
        elif approval_sts == 0:
            raise Warning('Perhatian!\nUser tidak termasuk group approval')
        return True

    @api.multi
    def action_reject_form(self):
        form_id = self.env.ref('teds_proposal.view_teds_proposal_budget_reject_form').id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'teds.proposal.budget.reject',
            'name': 'Reject Proposal',
            'views': [(form_id, 'form')],
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': False,
            'target': 'new',
            'context': {'default_proposal_id': self.id}
        }

    @api.multi
    def action_close_proposal(self):
        # Kalau sudah confirm all
        self.write({
            'state': 'close',
            'approval_state': 'c',
            'close_uid': self._uid,
            'close_date': self._get_default_date()
        })

    @api.multi
    def action_print_proposal(self):
        active_ids = self.env.context.get('active_ids', [])
        user = self.env['res.users'].suspend_security().browse(self._uid).name
        datas = {
             'ids': active_ids,
             'model': 'teds.proposal',
             'form': self.read()[0],
             'user': user
        }
        return self.env['report'].suspend_security().get_action(self, 'teds_proposal.print_proposal_pdf', data=datas)

class ProposalLine(models.Model):
    _name = "teds.proposal.line"
    _rec_name = "description"
    _description = "Proposal Online - Detail"

    proposal_id = fields.Many2one('teds.proposal', string='Nomor Proposal', ondelete='cascade')
    description = fields.Char(string='Deskripsi')
    qty = fields.Float(string='Qty', digits=dp.get_precision('Product Unit of Measure'), default=1)
    price_unit = fields.Float(string='Price/Qty', digits=dp.get_precision('Product Price'))
    # price * qty
    amount_total = fields.Float(string='Total', digits=dp.get_precision('Product Price'))
    jenis_pembayaran = fields.Selection([
        ('C', 'Cash'),
        ('T', 'Transfer')
    ], string='Jenis Pembayaran')
    # untuk jenis pembayaran Transfer, wajib input vendor
    supplier_id = fields.Many2one('res.partner', string='Supplier', ondelete='restrict')
    # untuk jenis pembayaran Cash, wajib input keterangan
    cash_remark = fields.Char(string='Keterangan')
    # fund booked
    amount_reserved = fields.Float(string='Reserved', digits=dp.get_precision('Product Price'))
    # jumlah yang sudah dibayar
    amount_paid = fields.Float(string='Paid', digits=dp.get_precision('Product Price'))
    # Riwayat pencairan dana
    payment_ids = fields.One2many('teds.proposal.line.payment', 'proposal_line_id', string='Detail Pembayaran')

    @api.onchange('qty','price_unit')
    def _onchange_amount_total(self):
        self.amount_total = self.qty * self.price_unit

class ProposalLinePayment(models.Model):
    _name = "teds.proposal.line.payment"
    _description = "Proposal Online - Detail - Riwayat Pembayaran"

    proposal_line_id = fields.Many2one('teds.proposal.line', string='Nomor Proposal', ondelete='cascade')
    name = fields.Char(string='Nomor Pembayaran')
    jenis_pembayaran = fields.Selection([
        ('C', 'Cash'),
        ('T', 'Transfer')
    ], string='Jenis Pembayaran')
    supplier_id = fields.Many2one('res.partner', string='Supplier', ondelete='restrict')
    amount_paid = fields.Float(string='Paid', digits=dp.get_precision('Product Price'))

class ProposalSponsor(models.Model):
    _name = "teds.proposal.sponsor"
    _description = "Proposal Online - Sponsor"

    proposal_id = fields.Many2one('teds.proposal', string='Nomor Proposal', ondelete='cascade')
    supplier_id = fields.Many2one('res.partner', string='Sponsor', ondelete='restrict')
    amount = fields.Float(string='Nominal', digits=dp.get_precision('Product Price'))

    @api.constrains('amount')
    def _check_amount(self):
        if self.amount <= 0:
            raise ValidationError('Beban sponsor %s harus lebih dari 0.' % (self.supplier_id.name))

class ProposalSchedule(models.Model):
    _name = "teds.proposal.schedule"
    _description = "Proposal Online - Schedule"

    proposal_id = fields.Many2one('teds.proposal', string='Nomor Proposal', ondelete='cascade')
    location = fields.Char(string='Lokasi')
    date_start = fields.Date(string='Start Date')
    date_end = fields.Date(string='End Date')
    # date_close = fields.Date(string='Close Date')
    day_count = fields.Integer(string='Days')

    @api.onchange('date_start','date_end')
    def _onchange_date(self):
        if self.date_end and self.date_start:
            self.day_count = (datetime.strptime(self.date_end, "%Y-%m-%d") - datetime.strptime(self.date_start, "%Y-%m-%d")).days + 1

class ProposalAttachment(models.Model):
    _name = "teds.proposal.attachment"
    _description = "Proposal Online - Attachment"

    def _compute_files(self):
        for x in self:       
            if x.filename:
                x.files = self.env['teds.config.files'].suspend_security().get_file(x.filename)

    proposal_id = fields.Many2one('teds.proposal', string='Nomor Proposal', ondelete='cascade')
    is_files_fix = fields.Boolean()
    files_upload = fields.Binary('Upload Berkas')
    filename_upload = fields.Char('Nama Berkas')
    files = fields.Binary('Download Berkas', compute='_compute_files') #, store=False
    filename = fields.Char('Nama Berkas')
    remark = fields.Text(string='Keterangan')

    @api.model
    def create(self,vals):
        if not vals.get('files_upload'):
            raise Warning('Perhatian!\nAnda belum upload berkas apapun.')

        files = vals.get('files_upload')
        
        filename_upload_tokens = str(vals.get('filename_upload')).split('.')
        now = (datetime.today() + relativedelta(hours=7)).strftime('-%Y-%m-%d_%H_%M_%S')
        filename = str('teds_proposal-')+str(vals['proposal_id'])+now+'.'+filename_upload_tokens[len(filename_upload_tokens) - 1]

        self.env['teds.config.files'].suspend_security().upload_file(filename, files)
        vals['files_upload'] = False
        vals['filename_upload'] = filename
        vals['files'] = False
        vals['filename'] = filename
        return super(ProposalAttachment, self).create(vals)

    @api.multi
    def write(self,vals):
        # if not vals.get('is_files_fix'):
        if not vals.get('files_upload'):
            raise Warning('Perhatian!\nAnda belum upload berkas apapun.')

        files = vals.get('files_upload')
        # replace files
        filename_db = self.search([('id','=',self.id)]).filename
        filename_db_tokens = str(filename_db).split('.')
        filename_upload_tokens = str(vals.get('filename_upload')).split('.')
        filename = filename_db_tokens[0]+'.'+filename_upload_tokens[len(filename_upload_tokens) - 1]
        
        self.env['teds.config.files'].suspend_security().upload_file(filename, files)
        vals['files_upload'] = False
        vals['filename_upload'] = filename
        vals['files'] = False
        vals['filename'] = filename
        
        return super(ProposalAttachment, self).write(vals)

    @api.multi
    def export_file(self):
        return {
            'type' : 'ir.actions.act_url',
            'name': 'contract',
            'url':'/web/binary/saveas?model=teds.proposal.attachment&field=files&filename_field=filename&id=%d'%(self.id)
            }

class ProposalRejectBudget(models.TransientModel):
    _name = "teds.proposal.budget.reject"
    
    proposal_id = fields.Many2one('teds.proposal', string='ID Proposal', ondelete='cascade')
    reject_reason = fields.Text(string='Alasan Reject')

    @api.multi
    def action_reject(self):
        if self.env['wtc.approval.matrixbiaya'].suspend_security().reject(self.proposal_id, self.reject_reason):
            try:
                self.proposal_id.suspend_security().write({'state': 'reject','approval_state':'r'})
            except Exception:
                self._cr.rollback()
                raise Warning('Terjadi kesalahan saat update Proposal %s.' % (self.proposal_id.suspend_security().name))
        else:
            raise Warning("User tidak termasuk group approval.")
        return True

class ProposalPayment(models.Model):
    _name = "teds.proposal.payment"
    _description = "Proposal Online - List Pembayaran"
    _order = "id desc"

    proposal_id = fields.Many2one('teds.proposal', string='Nomor Proposal', ondelete='cascade')
    payment_num = fields.Char(string='Nomor Pembayaran')
    payment_model_id = fields.Integer(string='ID Model Pembayaran')
    payment_transaction_id = fields.Integer(string='ID Transaksi')
    payment_date = fields.Date(string='Tanggal Pembayaran')
    payment_amount = fields.Float(string='Total Pembayaran', digits=dp.get_precision('Product Price'))
