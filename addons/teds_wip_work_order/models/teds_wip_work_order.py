from openerp import models, fields, api
from datetime import date, datetime, timedelta,time
from dateutil.relativedelta import relativedelta
from openerp.exceptions import Warning

class WIPWorkOrder(models.Model):
    _name = "teds.wip.work.order"

    def _get_default_branch(self):
        branch_ids = False
        branch_ids = self.env.user.branch_ids
        if branch_ids and len(branch_ids) == 1 :
            return branch_ids[0].id
        return False

    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()

    @api.model
    def _get_default_datetime(self):
        return self.env['wtc.branch'].get_default_datetime_model()

    @api.multi
    @api.depends('detail_ids','other_ids')
    def _compute_detail_wip(self):
        for me in self:
            total = len(me.detail_ids) + len(me.other_ids)
            me.qty_wip = total

    name = fields.Char('Name')
    date = fields.Date('Date',default=_get_default_date)
    branch_id = fields.Many2one('wtc.branch','Branch',default=_get_default_branch)
    qty_wip = fields.Integer('Qty WIP',compute="_compute_detail_wip",readonly=True)
    state = fields.Selection([
        ('draft','Draft'),
        ('waiting_for_approval','Waiting Approval'),
        ('approved','Approved'),
        ('done','Done')],default='draft')
    detail_ids = fields.One2many('teds.wip.work.order.line','wip_id','Details')
    other_ids = fields.One2many('teds.wip.work.order.other','wip_id','Others')
    generate_date = fields.Datetime('Generate on')
    approve_uid = fields.Many2one('res.users','Approved by')
    approve_date = fields.Datetime('Approved on')
    confirm_uid = fields.Many2one('res.users','Confirmed by')
    confirm_date = fields.Datetime('Confirmed on')

    @api.model
    def create(self,vals):
        vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'WIP')
        return super(WIPWorkOrder,self).create(vals)

    @api.multi
    def unlink(self):
        for me in self:
            if me.state != 'draft':
                raise Warning('Tidak bisa dihapus WIP selain Draft !')
        return super(WIPWorkOrder, self).unlink()
        
    @api.multi
    def action_get_wip(self):
        where = " WHERE wo.state in ('waiting_for_approval','confirmed','approved','finished')"
        if self.branch_id:
            where += " AND wo.branch_id = %d" %(self.branch_id.id)
        query = """
            SELECT wo.id as wo_id
                , wo.date as tgl_wo
                , (current_date - wo.date) as aging
                , wo.no_pol as no_polisi
                , wo.state as state_wo
                , wo.state_wo AS status_wo
                , CASE WHEN wo.type = 'REG' THEN 'Regular'
                WHEN wo.type = 'WAR' THEN 'Job Return'
                WHEN wo.type = 'CLA' THEN 'Claim'
                WHEN wo.type = 'SLS' THEN 'Part Sales' END as type_wo
            FROM wtc_work_order wo
            %s
        """ %(where)
        self._cr.execute(query)
        ress = self._cr.dictfetchall()
        if not ress:
            raise Warning('Data WIP tidak ditemukan !')
        detail_ids = []
        for res in ress:
            detail_ids.append([0,False,{
                'wo_id':res.get('wo_id'),
                'tgl_wo':res.get('tgl_wo'),
                'aging':res.get('aging'),
                'no_polisi':res.get('no_polisi'),
                'state_wo':res.get('state_wo').replace('_',' ').title() if res.get('state_wo') else '',
                'status_wo':res.get('status_wo').replace('_',' ').title() if res.get('status_wo') else '',
                'type_wo':res.get('type_wo'),
            }])
        self.write({
            'generate_date':self._get_default_datetime(),
            'detail_ids':detail_ids
        })

    @api.multi
    def action_rfa(self):
        for line in self.detail_ids:
            line.status_validasi = 'open'
        for other in self.other_ids:
            other.status_validasi = 'open'

        self.write({'state':'waiting_for_approval'})
    
    @api.multi
    def action_approved(self):
        for line in self.detail_ids:
            line.status_validasi = 'done'
        for other in self.other_ids:
            other.status_validasi = 'done'
        self.write({
            'state':'approved',
            'approve_uid':self._uid,
            'approve_date':self._get_default_datetime(),
        })

    @api.multi
    def action_confirm(self):
        self.write({
            'state':'done',
            'confirm_uid':self._uid,
            'confirm_date':self._get_default_datetime(),      
        })


class WIPWorkOrderLine(models.Model):
    _name = "teds.wip.work.order.line"

    wip_id = fields.Many2one('teds.wip.work.order','WIP Order')
    wo_id = fields.Many2one('wtc.work.order','Work Order')
    tgl_wo = fields.Date('Tanggal Service')
    aging = fields.Integer('Aging WIP')
    no_polisi = fields.Char('No Polisi')
    state_wo = fields.Char('State')
    status_wo = fields.Char('Status WO')
    type_wo = fields.Char('Type WO')
    fisik_motor = fields.Selection([('Ada','Ada'),('Tidak Ada','Tidak Ada')],string="Fisik Motor")
    keterangan = fields.Char('Keterangan')
    status_validasi = fields.Selection([('draft','Draft'),('open','Open'),('done','Done')],default='draft')
    is_validasi_adh = fields.Boolean('Verifikasi ADH')

class WIPWorkOrderOther(models.Model):
    _name = "teds.wip.work.order.other"

    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()

    @api.multi
    @api.depends('aging')
    def _compute_aging(self):
        for me in self:
            me.aging_show = me.aging

    name = fields.Char('Work Order')
    wip_id = fields.Many2one('teds.wip.work.order')
    tgl_wo = fields.Date('Tanggal Service')
    aging = fields.Integer('Aging WIP')
    aging_show = fields.Integer('Aging WIP',compute="_compute_aging",readonly=True)
    no_polisi = fields.Char('No Polisi')
    state_wo = fields.Char('State')
    status_wo = fields.Char('Status WO')
    type_wo = fields.Char('Type WO')
    fisik_motor = fields.Selection([('Ada','Ada'),('Tidak Ada','Tidak Ada')],string="Fisik Motor")
    keterangan = fields.Char('Keterangan')
    status_validasi = fields.Selection([('draft','Draft'),('open','Open'),('done','Done')],default='draft')
    is_validasi_adh = fields.Boolean('Verifikasi ADH')

    @api.onchange('tgl_wo')
    def oncange_aging(self):
        aging = 0
        hari_ini = self._get_default_date()
        if self.tgl_wo:
            aging = (hari_ini.date() - datetime.strptime(self.tgl_wo,"%Y-%m-%d").date()).days
        self.aging = aging