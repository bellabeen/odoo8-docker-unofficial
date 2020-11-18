from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning
from datetime import date, datetime, timedelta,time

class MutationRequestAsset(models.Model):
    _name = "teds.mutation.request.asset"
    _order = "date DESC"
    _inherit = ['ir.needaction_mixin']

    def _get_default_branch(self):
        branch_ids = False
        branch_ids = self.env.user.branch_ids
        if branch_ids and len(branch_ids) == 1 :
            return branch_ids[0].id
        return False
   
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()
    
    def _get_default_datetime(self):
        return self.env['wtc.branch'].get_default_datetime_model()

    @api.model
    def _branch_request_get(self):
        obj_branch = self.env['wtc.branch'].sudo().search([('branch_type','in',['DL','MD'])], order='name')
        return [(str(branch.id),"[%s] %s"%(branch.code,branch.name)) for branch in obj_branch]

    name = fields.Char('Name')
    branch_id = fields.Many2one('wtc.branch','Branch Sender',default=_get_default_branch)
    date = fields.Date('Date',default=_get_default_date)
    branch_request_id = fields.Selection('_branch_request_get', string='Branch Request')
    division = fields.Selection([('Umum','Umum')],default='Umum',readonly=True)
    detail_ids = fields.One2many('teds.mutation.request.asset.detail','mutation_id')
    state = fields.Selection([
        ('draft','Draft'),
        ('waiting_for_approval','Waiting For Approval'),
        ('approved','Approved'),
        ('open','Open'),
        ('done','Done')],default='draft')
    approval_state = fields.Selection([
        ('b', 'Belum Request'),
        ('rf', 'Request For Approval'),
        ('a', 'Approved'),
        ('r', 'Rejected')], string='Approval State', readonly=True, default='b')
    approval_ids = fields.One2many('wtc.approval.line','transaction_id',string="Table Approval",domain=[('form_id','=',_name)])
    mutation_asset_id = fields.Many2one('teds.mutation.asset','Mutation Asset')
    confirm_date = fields.Datetime('Confirmed on')
    confirm_uid = fields.Many2one('res.users',string="Confirmed by")
    pic_asset_id = fields.Many2one('hr.employee','PIC Asset',domain="[('branch_id','=',branch_id),('job_id.name','!=','SALESMAN PARTNER')]")
    
    @api.model
    def _needaction_domain_get(self):
        return [('state', 'in', ('waiting_for_approval','approved'))] 

    @api.model
    def create(self,vals):
        if not vals.get('detail_ids'):
            raise Warning('Detail Asset tidak boleh kosong !')
        vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'MRA')
        return super(MutationRequestAsset,self).create(vals)

    @api.multi
    def unlink(self):
        for me in self:
            if me.state != 'draft':
                raise Warning("Data selain draft tidak bisa dihapus !")
        return super(MutationRequestAsset, self).unlink()


    @api.multi
    def action_rfa(self):
        if not self.detail_ids:
            raise Warning('Detail Asset tidak boleh kosong !')
        obj_matrix = self.env['wtc.approval.matrixbiaya']
        obj_matrix.request_by_value(self,2)
        self.write({'state':'waiting_for_approval','approval_state':'rf'})

    @api.multi
    def action_approved(self):
        approval_sts = self.env['wtc.approval.matrixbiaya'].approve(self)
        if approval_sts == 1:
            self.write({'approval_state':'a','state':'approved'})
        elif approval_sts == 0:
            raise Warning('Perhatian !\n User tidak termasuk group approval')
    
    @api.multi
    def action_confirm(self):
        if not self.detail_ids:
            raise Warning('Detail Asset tidak boleh kosong !')
        
        # Create Mutasi Asset
        detail_ids = []
        for detail in self.detail_ids:
            amount = detail.asset_id.purchase_value
            akumulasi_penyusutan = detail.asset_id.purchase_value - detail.asset_id.value_residual
            nilai_buku = detail.asset_id.value_residual

            detail_ids.append([0,False,{
                'asset_id':detail.asset_id.id,
                'code':detail.asset_id.code,
                'category_id':detail.asset_id.category_id.id,
                'amount':amount,
                'akumulasi_penyusutan':akumulasi_penyusutan,
                'nilai_buku':nilai_buku,
                'keterangan':detail.keterangan,
            }])

        vals = {
            'branch_id':int(self.branch_request_id),
            'branch_sender_id':str(self.branch_id.id),
            'mutation_request_id':self.id,
            'division':self.division,
            'detail_ids':detail_ids,
        }
        mutation_obj = self.env['teds.mutation.asset'].suspend_security().create(vals)
        
        self.write({
            'state':'open',
            'mutation_asset_id':mutation_obj.id,
            'confirm_uid':self._uid,
            'confirm_date':self._get_default_datetime()
        })

class MutationRequestAssetDetail(models.Model):
    _name = "teds.mutation.request.asset.detail"

    mutation_id = fields.Many2one('teds.mutation.request.asset','Mutation',ondelete='cascade')
    asset_id = fields.Many2one('account.asset.asset','Asset',domain="[('branch_id','=',parent.branch_id),('state','in',['open','close']),('category_id.type','=','fixed')]")
    code = fields.Char('Asset Code',readonly=True) 
    category_id = fields.Many2one('account.asset.category', 'Asset Category')
    amount = fields.Float('Harga Beli')
    akumulasi_penyusutan = fields.Float('Akumulasi Penyusutan')
    nilai_buku = fields.Float('Nilai Buku')
    keterangan = fields.Char('Keterangan')
    lokasi_asset_id = fields.Many2one('teds.master.lokasi.asset','Lokasi Asset')

    _sql_constraints = [('unique_mutasi_asset', 'unique(mutation_id,asset_id)', 'Asset tidak boleh duplikat !')]
    
    @api.onchange('asset_id')
    def onchange_asset(self):
        if self.asset_id:
            self.category_id = self.asset_id.category_id.id
            self.code = self.asset_id.code
            self.amount = self.asset_id.purchase_value
            self.akumulasi_penyusutan = self.asset_id.purchase_value - self.asset_id.value_residual
            self.nilai_buku = self.asset_id.value_residual
            self.lokasi_asset_id = self.asset_id.lokasi_asset_id
            