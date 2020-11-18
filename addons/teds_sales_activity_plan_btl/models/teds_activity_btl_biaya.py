from openerp import models, fields, api
from datetime import datetime, timedelta
from openerp.exceptions import Warning

class ActivityBtlBiaya(models.Model):
    _name = "teds.activity.btl.biaya"
    _inherit = ['ir.needaction_mixin']
    _rec_name = "activity_id"

    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()
    
    def _get_default_branch(self):
        branch_ids = False
        branch_ids = self.env.user.branch_ids
        if branch_ids and len(branch_ids) == 1 :
            return branch_ids[0].id
        return False

    @api.one
    @api.depends('total_biaya')
    def compute_total_biaya(self):
        self.total_biaya_show = self.total_biaya

    branch_id = fields.Many2one('wtc.branch','Branch',default=_get_default_branch)
    activity_id = fields.Many2one('teds.sales.plan.activity',domain="[('branch_id','=',branch_id),('state','in',('approved','open'))]",string="Activity")
    tanggal = fields.Date('Tanggal',default=_get_default_date)
    total_biaya = fields.Float('Total Biaya')
    total_biaya_show = fields.Float('Total Biaya',compute='compute_total_biaya')
    detail_biaya_ids = fields.One2many('teds.activity.btl.biaya.detail','biaya_id')
    state = fields.Selection([
        ('draft','Draft'),
        ('waiting_for_approval','Waiting Approval'),
        ('approved','Approved')],default='draft')
    approved_uid = fields.Many2one('res.users','Approved by')
    approved_date = fields.Datetime('Approved on')
    
    @api.model
    def _needaction_domain_get(self):
        return [('state', '=', 'waiting_for_approval')]
    
    @api.model
    def create(self,vals):
        if not vals['detail_biaya_ids']:
            raise Warning('Detail harus diisi !')
        if int(vals['total_biaya']) <= 0:
            raise Warning('Total Biaya 0 !')
        return super(ActivityBtlBiaya,self).create(vals)

    @api.onchange('activity_id')
    def onchange_total_biaya(self):
        if self.activity_id:
            total_biaya = 0
            for line in self.activity_id.activity_line_ids:                 
                for x in line.detail_biaya_ids:
                    if x.state != 'draft':
                        continue
                    total_biaya += x.subtotal
            self.total_biaya = total_biaya
            self.total_biaya_show = total_biaya

    @api.multi
    def action_rfa(self):
        if not self.detail_biaya_ids:
            raise Warning('Detail harus diisi !')
        total = 0
        for x in self.detail_biaya_ids:
            total += x.amount_alokasi 
            if x.amount_alokasi > x.move_line_id.amount_residual_currency:
                raise Warning('Nilai Alokasi tidak boleh lebih besar dari Amount Balance ! Number %s \n Nilai Amount Residual RP. %s ' %(x.move_line_id.ref,x.move_line_id.amount_residual_currency))
            
        # if total < self.total_biaya:
        #     raise Warning('Total Alokasi kurang dari Total Biaya BTL \n Total Biaya Rp. %s \n Total Alokasi Rp. %s'%(self.total_biaya,total))
        self.write({'state':'waiting_for_approval'})

    @api.multi
    def action_approved(self):
        if not self.detail_biaya_ids:
            raise Warning('Detail harus diisi !')
        
        for x in self.activity_id.activity_line_ids:
            for biaya in x.detail_biaya_ids:
                if biaya.state == 'draft':
                    biaya.sudo().state = 'confirmed'

        self.write({
            'state':'approved',
            'approved_uid':self._uid,
            'approved_date':datetime.now()    
        })

class ActivityBtlBiayaDetail(models.Model):
    _name = "teds.activity.btl.biaya.detail"

    @api.one
    @api.depends('move_line_id','type')
    def compute_amount(self):
        if self.move_line_id and self.type:
            nilai = 0
            if self.type == 'credit':
                nilai = abs(self.move_line_id.credit)
            else:
                nilai = abs(self.move_line_id.debit)
            
            self.amount_hl_original = nilai
            self.amount_hl_balance = self.move_line_id.amount_residual

    biaya_id = fields.Many2one('teds.activity.btl.biaya')
    type = fields.Selection([
        ('credit','HL'),
        ('debit','AR')
        ],default='credit',string="Type")
    finco_id = fields.Many2one('res.partner',string='Finco',domain=[('finance_company','=',True)])
    move_line_id = fields.Many2one('account.move.line',string='Number')
    amount_hl_original = fields.Float('Amount Original',compute='compute_amount',readonly=True)
    amount_hl_balance = fields.Float('Amount Balance',compute='compute_amount',readonly=True)
    amount_alokasi = fields.Float('Alokasi')

    _sql_constraints = [('biaya_move_line_unique', 'unique(biaya_id,move_line_id)', 'Number tidak boleh duplicat !')]

    @api.onchange('type','finco_id')
    def onchange_move_line(self):
        self.move_line_id = False
        domain = {'move_line_id':[('id','=',0)]}
        if self.type and self.finco_id:
            domain['move_line_id'] = [('branch_id','=',self.biaya_id.branch_id.id),('partner_id','=',self.finco_id.id),('division','=','Unit'),('account_id.type','=','payable'),('reconcile_id','=',False),(self.type,'>', 0)]

        return {'domain':domain}

    @api.onchange('move_line_id','type')
    def onchange_amount(self):
        self.amount_hl_original = False
        self.amount_hl_balance = False
        if self.type and self.move_line_id:
            nilai = 0
            if self.type == 'credit':
                nilai = abs(self.move_line_id.credit)
            else:
                nilai = abs(self.move_line_id.debit)
            
            self.amount_hl_original = nilai
            self.amount_hl_balance = self.move_line_id.amount_residual
            self.amount_alokasi = self.move_line_id.amount_residual

    @api.onchange('amount_alokasi')
    def onchange_amount_alokasi(self):
        warning = {}
        if self.amount_alokasi:
            if self.amount_alokasi > self.amount_hl_balance:
                self.amount_alokasi = self.move_line_id.amount_residual
                warning = {'title':'Perhatian !','message':'Nilai Alokasi tidak boleh lebih dari Amount Balance !'}
        return {'warning':warning}