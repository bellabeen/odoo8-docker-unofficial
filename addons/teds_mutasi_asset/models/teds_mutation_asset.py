from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning
from datetime import date, datetime, timedelta,time

class MutationAsset(models.Model):
    _name = "teds.mutation.asset"
    _order = "date DESC"
    _inherit = ['ir.needaction_mixin']

    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()
    
    def _get_default_datetime(self):
        return self.env['wtc.branch'].get_default_datetime_model()

    @api.model
    def _branch_sender_get(self):
        obj_branch = self.env['wtc.branch'].sudo().search([('branch_type','in',['DL','MD'])], order='name')
        return [(str(branch.id),"[%s] %s"%(branch.code,branch.name)) for branch in obj_branch]

    name = fields.Char('Name')
    mutation_request_id = fields.Many2one('teds.mutation.request.asset','Mutation Request')
    branch_id = fields.Many2one('wtc.branch','Branch Request')
    branch_sender_id = fields.Selection('_branch_sender_get', string='Branch Sender')
    date = fields.Date('Date',default=_get_default_date)
    division = fields.Selection([('Umum','Umum')],default='Umum',readonly=True)
    detail_ids = fields.One2many('teds.mutation.asset.detail','mutation_id')
    state = fields.Selection([
        ('requested','Requested'),
        ('waiting_for_approval','Waiting For Approval'),
        ('approved','Approved'),
        ('done','Done')],default='requested')
    approval_state = fields.Selection([
        ('b', 'Belum Request'),
        ('rf', 'Request For Approval'),
        ('a', 'Approved'),
        ('r', 'Rejected')], string='Approval State', readonly=True, default='b')
    approval_ids = fields.One2many('wtc.approval.line','transaction_id',string="Table Approval",domain=[('form_id','=',_name)])
    confirm_date = fields.Datetime('Confirmed on')
    confirm_uid = fields.Many2one('res.users',string="Confirmed by")
    pic_asset_id = fields.Many2one('hr.employee','PIC Asset',domain="[('branch_id','=',branch_id),('job_id.name','!=','SALESMAN PARTNER')]")
    
    @api.model
    def _needaction_domain_get(self):
        return [('state', 'in', ('requested','waiting_for_approval','approved'))] 

    @api.model
    def create(self,vals):
        if not vals.get('detail_ids'):
            raise Warning('Detail Asset tidak boleh kosong !')
        vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'SDA')
        return super(MutationAsset,self).create(vals)

    @api.multi
    def unlink(self):
        raise Warning("Data Distribution Asset tidak bisa dihapus !")
        
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

        # Create Asset Adjusment
        for detail in self.detail_ids:
            vals = {
                'branch_id':detail.asset_id.branch_id.id,
                'asset_id':detail.asset_id.id,
                'category_id':detail.asset_id.category_id.id,
                'number_depreciation':detail.asset_id.method_number,
                'purchase_value':detail.asset_id.purchase_value,
                'purchase_date':detail.asset_id.purchase_date,
                'new_category_id':detail.asset_id.category_id.id,
                'new_number_depreciation':detail.asset_id.method_number,
                'new_purchase_value':detail.asset_id.purchase_value,
                'new_purchase_date':detail.asset_id.purchase_date,
                'new_branch_id':self.branch_id.id,
                'bool_journal_category':False,
                'bool_journal_gross_value':False,
            }
            asset_adjusment_obj = self.env['wtc.asset.adjustment'].suspend_security().create(vals)
            asset_adjusment_obj.suspend_security().post_adjustment()
            detail.write({'asset_adjusment_id':asset_adjusment_obj.id})

        self.write({
            'state':'done',
            'confirm_uid':self._uid,
            'confirm_date':self._get_default_datetime()
        })
        # Mutasi Request Update Done
        self.mutation_request_id.suspend_security().write({'state':'done'})

    @api.multi    
    def action_print_bakso(self):
        datas = self.suspend_security().read()[0]

        branch_sender_id = self.env['wtc.branch'].suspend_security().browse(int(self.branch_sender_id))
        branch_sender_code = branch_sender_id.code
        branch_sender_name = branch_sender_id.name
        datas.update({
            'branch_sender_name':branch_sender_name,
            'branch_sender_code':branch_sender_code
        })
        return self.env['report'].get_action(self,'teds_mutasi_asset.berita_acara_mutasi_asset_print', data=datas)


class MutationAssetDetail(models.Model):
    _name = "teds.mutation.asset.detail"
        
    mutation_id = fields.Many2one('teds.mutation.asset','Mutation',ondelete='cascade')
    asset_id = fields.Many2one('account.asset.asset','Asset')
    code = fields.Char('Asset Code') 
    category_id = fields.Many2one('account.asset.category', 'Asset Category')
    amount = fields.Float('Harga Beli')
    akumulasi_penyusutan = fields.Float('Akumulasi Penyusutan')
    nilai_buku = fields.Float('Nilai Buku')
    keterangan = fields.Char('Keterangan')
    asset_adjusment_id = fields.Many2one('wtc.asset.adjustment','Asset Adjusment')
    lokasi_asset_id = fields.Many2one('teds.master.lokasi.asset','Lokasi Asset')
    
    _sql_constraints = [('unique_mutasi_asset', 'unique(mutation_id,asset_id)', 'Asset tidak boleh duplikat !')]