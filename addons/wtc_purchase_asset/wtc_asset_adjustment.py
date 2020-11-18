import time
from datetime import datetime
from openerp import models, fields, api
from openerp.osv import osv
from openerp.tools.translate import _

class wtc_asset_adjustment(models.Model):
    _name = 'wtc.asset.adjustment'
    _description = 'Asset Adjustment'
    _order = 'date desc'
    
    @api.multi
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date()
        
    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids
            
    name = fields.Char(string='Name')
    date = fields.Date(string='Date',default=_get_default_date)
    branch_id = fields.Many2one('wtc.branch',string='Branch',default=_get_default_branch)
    asset_id = fields.Many2one('account.asset.asset',string='Asset No')
    category_id = fields.Many2one('account.asset.category',string='Category')
    new_category_id = fields.Many2one('account.asset.category',string='New Category')
    number_depreciation = fields.Integer(string='Number of Depreciations')
    new_number_depreciation = fields.Integer(string='New Number of Depreciations')
    purchase_value = fields.Float(string='Gross Value')
    new_purchase_value = fields.Float(string='New Gross Value')
    state = fields.Selection([('draft','Draft'),('waiting_for_approval','Waiting for Approval'),('approved','Approved'),('post','Posted')],default='draft',string='State')
    move_id = fields.Many2one('account.move', string='Account Entry', copy=False)
    move_ids = fields.One2many('account.move.line',related='move_id.line_id',string='Journal Items', readonly=True)   
    confirm_uid = fields.Many2one('res.users',string="Posted by")
    confirm_date = fields.Datetime('Posted on')
    bool_journal_category = fields.Boolean(string='Create Journal Category',default=True)
    bool_journal_gross_value = fields.Boolean(string='Create Journal Gross Value',default=True)
    approval_ids = fields.One2many('wtc.approval.line','transaction_id',string="Table Approval",domain=[('form_id','=',_name)])
    approval_state = fields.Selection([('b','Belum Request'),('rf','Request For Approval'),('a','Approved'),('r','Reject')],'Approval State', default='b',readonly=True)
    division = fields.Selection([('Umum','Umum')],string='Division',default='Umum')
    new_branch_id = fields.Many2one('wtc.branch',string='New Branch')
    bool_journal_branch = fields.Boolean(string='Create Journal Branch',default=True)
    purchase_date = fields.Date(string='Effective Date')
    new_purchase_date = fields.Date(string='New Effective Date')


    def request_approval(self,cr,uid,ids,context=None):
        obj_matrix = self.pool.get("wtc.approval.matrixbiaya")
        val = self.browse(cr,uid,ids)
        total = 5
        obj_matrix.request_by_value(cr, uid, ids, val, total)
        self.write(cr,uid,ids,{'state':'waiting_for_approval','approval_state':'rf'})
        return True
    
    def approve_approval(self,cr,uid,ids,context=None):
        obj_bj = self.browse(cr, uid, ids, context=context)
        approval_sts = self.pool.get("wtc.approval.matrixbiaya").approve(cr, uid, ids, obj_bj)
        if approval_sts == 1:
            self.write(cr, uid, ids, {'approval_state':'a','state':'approved'})
        elif approval_sts == 0:
            raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group approval"))
        return True
                  
    @api.onchange('asset_id')
    def change_asset(self):
        if self.asset_id :
            self.category_id = self.asset_id.category_id.id
            self.new_category_id = self.asset_id.category_id.id
            self.number_depreciation = self.asset_id.method_number
            self.new_number_depreciation = self.asset_id.method_number
            self.purchase_value = self.asset_id.real_purchase_value
            self.new_purchase_value = self.asset_id.real_purchase_value
            self.new_branch_id = self.asset_id.branch_id.id
            self.purchase_date = self.asset_id.purchase_date
            self.new_purchase_date = self.asset_id.purchase_date

    @api.onchange('new_category_id')
    def change_new_category(self):
        if self.new_category_id :
            self.new_number_depreciation = self.new_category_id.method_number
            
    @api.model
    def create(self,vals):
        vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'AA')
        vals['date'] = self._get_default_date().date()
        
        asset_id = self.env['account.asset.asset'].browse(vals['asset_id'])
        vals['category_id'] = asset_id.category_id.id
        vals['number_depreciation'] = asset_id.method_number
        vals['purchase_value'] = asset_id.purchase_value
        vals['purchase_date'] = asset_id.purchase_date

        return super(wtc_asset_adjustment,self).create(vals)
    
    @api.multi
    def post_adjustment(self):
        #variable
        new_category = False
        new_number_depreciation = False
        new_purchase_value = False
        new_branch_id = False
        new_purchase_date = False
        move_id = False
        vals = {}
        
        if self.new_category_id != self.category_id :
            new_category = True
        if self.new_number_depreciation != self.number_depreciation :
            new_number_depreciation = True
        if self.new_purchase_value != self.purchase_value :
            new_purchase_value = True
        if self.new_branch_id != self.branch_id :
            new_branch_id = True
        if self.new_purchase_date != self.purchase_date :
            new_purchase_date = True
            
        move_id = self.cek_changes(new_category,new_number_depreciation,new_purchase_value,new_branch_id,new_purchase_date)
        if move_id :
            vals['move_id'] = move_id
        vals['confirm_uid'] = self._uid
        vals['confirm_date'] = self._get_default_date()
        vals['state'] = 'post'
        self.write(vals)

    @api.cr_uid_ids_context
    def cek_changes(self,cr,uid,ids,new_category,new_number_depreciation,new_purchase_value,new_branch_id,new_purchase_date,context=None):
        #object
        vals = self.browse(cr,uid,ids)
        data = {}
        move_id = False
        
        if vals.new_category_id != vals.category_id :
            data['category_id'] = vals.new_category_id.id
        if vals.new_purchase_value != vals.purchase_value :
            data['purchase_value'] = vals.new_purchase_value
            data['real_purchase_value'] = vals.new_purchase_value
        if new_number_depreciation :
            data['method_number'] = vals.new_number_depreciation
        if new_branch_id :
            data['branch_id'] = vals.new_branch_id.id
        if new_purchase_date :
            data['purchase_date'] = vals.new_purchase_date
            
        if vals.new_purchase_value != vals.purchase_value or vals.new_category_id != vals.category_id or vals.new_branch_id != vals.branch_id :                    
            if vals.bool_journal_category or vals.bool_journal_gross_value or vals.bool_journal_branch :
                account_move = self.pool.get('account.move')
                account_move_line = self.pool.get('account.move.line')
                periods = self.pool.get('account.period').find(cr,uid,self._get_default_date(cr,uid,ids).date())
                branch_config = self.pool.get('wtc.branch.config').search(cr,uid,[
                                                                     ('branch_id','=',vals.branch_id.id)
                                                                     ])              
                if not branch_config :
                    raise osv.except_osv(('Perhatian !'), ("Branch Config tidak ditemukan !"))  
                branch_config = self.pool.get('wtc.branch.config').browse(cr,uid,branch_config)
                
                journal_id = branch_config.journal_asset_adjustment_id
                period_id =  periods and periods[0]
                if not journal_id:
                    raise osv.except_osv(('Perhatian !'), ("Journal Asset Adjsutment belum diisi dalam master Branch Config !"))  
                
                #Create Account MOVE 
                move = {
                    'name': vals.name,
                    'ref': vals.name,
                    'journal_id': journal_id.id,
                    'date': vals.date,
                    'period_id':period_id,
                }
                move_id = account_move.create(cr,uid, move, context=None)
                        
                if vals.bool_journal_category :
                    if vals.new_category_id != vals.category_id :
                        self.create_journal_category_asset(cr,uid,ids,move_id,journal_id,period_id)
                if vals.bool_journal_gross_value :
                    if vals.new_purchase_value != vals.purchase_value :
                        if vals.new_purchase_value < vals.purchase_value :    
                            asset_adjustment_account_id = journal_id.default_credit_account_id.id if journal_id.default_credit_account_id else journal_id.default_debit_account_id.id
                        else :
                            asset_adjustment_account_id = journal_id.default_debit_account_id.id if journal_id.default_debit_account_id else journal_id.default_credit_account_id.id
                        if not asset_adjustment_account_id :
                            raise osv.except_osv(('Perhatian !'), ("Lengkapi account credit dan debit di journal asset adjustment !"))  
                        self.create_journal_gross_value(cr,uid,ids,move_id, journal_id, period_id,asset_adjustment_account_id)
                if vals.bool_journal_branch :
                    if vals.new_branch_id != vals.branch_id :
                        self.create_journal_branch(cr,uid,ids,move_id, journal_id, period_id)
        if len(data) > 0 :
            vals.asset_id.write(data)
        self.pool.get('account.asset.asset').compute_depreciation_board(cr,uid,[vals.asset_id.id])
        return  move_id
        
    @api.multi
    def create_journal_branch(self,move_id,journal_id,period_id):
        account_asset = self.new_category_id.account_asset_id.id
        account_accumulasi = self.new_category_id.account_depreciation_id.id
        if not account_asset or not account_accumulasi :
            raise osv.except_osv(('Perhatian !'), ("Lengkapi account asset dan akumulasi dalam category asset !"))  
                    
        move_line = {
            'name': self.asset_id.name + ' (Branch New)',
            'ref':self.asset_id.code,
            'account_id': account_asset,
            'move_id': move_id,
            'journal_id': journal_id.id,
            'period_id': period_id,
            'date': self.date,
            'debit': self.asset_id.real_purchase_value,
            'credit': 0.0,
            'branch_id' : self.new_branch_id.id,
            'division' : self.asset_id.division,
            'partner_id' : self.asset_id.partner_id.id,
            'ref_asset_id': self.asset_id.id,                   
        }
        
        move_line_old = {
            'name': self.asset_id.name + ' (Branch Old)',
            'ref':self.asset_id.code,
            'account_id': account_asset,
            'move_id': move_id,
            'journal_id': journal_id.id,
            'period_id': period_id,
            'date': self.date,
            'debit': 0.0,
            'credit': self.asset_id.real_purchase_value,
            'branch_id' : self.branch_id.id,
            'division' : self.asset_id.division,
            'partner_id' : self.asset_id.partner_id.id,
            'ref_asset_id': self.asset_id.id,                   
        }

        value = self.asset_id.real_purchase_value - self.asset_id.value_residual
              
        move_line_accumulasi_old = {
            'name': self.asset_id.name,
            'ref':self.asset_id.code,
            'account_id': account_accumulasi,
            'move_id': move_id,
            'journal_id': journal_id.id,
            'period_id': period_id,
            'date': self.date,
            'debit': abs(value) if value > 0 else 0.0,
            'credit': abs(value) if value < 0 else 0.0,
            'branch_id' : self.branch_id.id,
            'division' : self.asset_id.division,
            'partner_id' : self.asset_id.partner_id.id,
            'ref_asset_id': self.asset_id.id,                   
        }
            
        move_line_accumulasi = {
            'name': self.asset_id.name,
            'ref':self.asset_id.code,
            'account_id': account_accumulasi,
            'move_id': move_id,
            'journal_id': journal_id.id,
            'period_id': period_id,
            'date': self.date,
            'debit': abs(value) if value < 0 else 0.0,
            'credit': abs(value) if value > 0 else 0.0,
            'branch_id' : self.new_branch_id.id,
            'division' : self.asset_id.division,
            'partner_id' : self.asset_id.partner_id.id,
            'ref_asset_id': self.asset_id.id,                   
        }
        self.env['account.move.line'].create(move_line)
        self.env['account.move.line'].create(move_line_old)
        self.env['account.move.line'].create(move_line_accumulasi_old)
        self.env['account.move.line'].create(move_line_accumulasi)
                     
    @api.multi
    def create_journal_category_asset(self,move_id,journal_id,period_id):
        new_asset_account_id = self.new_category_id.account_asset_id.id
        old_asset_account_id = self.category_id.account_asset_id.id
        new_account_accumulasi = self.new_category_id.account_depreciation_id.id
        old_account_accumulasi = self.category_id.account_depreciation_id.id

        move_line = {
            'name': self.asset_id.name + ' (New Category)',
            'ref':self.asset_id.code,
            'account_id': new_asset_account_id,
            'move_id': move_id,
            'journal_id': journal_id.id,
            'period_id': period_id,
            'date': self.date,
            'debit': self.asset_id.real_purchase_value,
            'credit': 0.0,
            'branch_id' : self.asset_id.branch_id.id,
            'division' : self.asset_id.division,
            'partner_id' : self.asset_id.partner_id.id,
            'ref_asset_id': self.asset_id.id,                   
        }
            
        move_line_old = {
            'name': self.asset_id.name + ' (Old Category)',
            'ref':self.asset_id.code,
            'account_id': old_asset_account_id,
            'move_id': move_id,
            'journal_id': journal_id.id,
            'period_id': period_id,
            'date': self.date,
            'debit': 0.0,
            'credit': self.asset_id.real_purchase_value,
            'branch_id' : self.asset_id.branch_id.id,
            'division' : self.asset_id.division,
            'partner_id' : self.asset_id.partner_id.id,
            'ref_asset_id': self.asset_id.id,                   
        } 

        value = self.asset_id.real_purchase_value - self.asset_id.value_residual

        move_line_accumulasi_old = {
            'name': self.asset_id.name + ' (Depreciation Old Category)',
            'ref':self.asset_id.code,
            'account_id': old_account_accumulasi,
            'move_id': move_id,
            'journal_id': journal_id.id,
            'period_id': period_id,
            'date': self.date,
            'debit': abs(value) if value > 0 else 0.0,
            'credit': abs(value) if value < 0 else 0.0,
            'branch_id' : self.asset_id.branch_id.id,
            'division' : self.asset_id.division,
            'partner_id' : self.asset_id.partner_id.id,
            'ref_asset_id': self.asset_id.id,                   
        }

        move_line_accumulasi = {
            'name': self.asset_id.name + ' (Depreciation New Category)',
            'ref':self.asset_id.code,
            'account_id': new_account_accumulasi,
            'move_id': move_id,
            'journal_id': journal_id.id,
            'period_id': period_id,
            'date': self.date,
            'debit': abs(value) if value < 0 else 0.0,
            'credit': abs(value) if value > 0 else 0.0,
            'branch_id' : self.asset_id.branch_id.id,
            'division' : self.asset_id.division,
            'partner_id' : self.asset_id.partner_id.id,
            'ref_asset_id': self.asset_id.id, 
        }

        self.env['account.move.line'].create(move_line)
        self.env['account.move.line'].create(move_line_old)
        self.env['account.move.line'].create(move_line_accumulasi_old)
        self.env['account.move.line'].create(move_line_accumulasi)
        
    @api.multi
    def create_journal_gross_value(self,move_id,journal_id,period_id,asset_adjustment_account_id):
        value = self.new_purchase_value - self.purchase_value

        move_line = {
            'name': self.asset_id.name + ' (Gross Value New)',
            'ref':self.asset_id.code,
            'account_id': self.new_category_id.account_asset_id.id,
            'move_id': move_id,
            'journal_id': journal_id.id,
            'period_id': period_id,
            'date': self.date,
            'debit': abs(value) if value > 0 else 0.0,
            'credit': abs(value) if value < 0 else 0.0,
            'branch_id' : self.new_branch_id.id,
            'division' : self.asset_id.division,
            'partner_id' : self.asset_id.partner_id.id,
            'ref_asset_id': self.asset_id.id,                   
        }
            
        move_line_adj = {
            'name': self.asset_id.name + ' (Gross Value Adjustment)',
            'ref':self.asset_id.code,
            'account_id': asset_adjustment_account_id,
            'move_id': move_id,
            'journal_id': journal_id.id,
            'period_id': period_id,
            'date': self.date,
            'debit': abs(value) if value < 0 else 0.0,
            'credit': abs(value) if value > 0 else 0.0,
            'branch_id' : self.new_branch_id.id,
            'division' : self.asset_id.division,
            'partner_id' : self.asset_id.partner_id.id,
            'ref_asset_id': self.asset_id.id,                   
        }
        self.env['account.move.line'].create(move_line)
        self.env['account.move.line'].create(move_line_adj)
            
    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Adjustment Asset %s tidak bisa dihapus dalam status 'Posted' !")%(item.name))
        return super(wtc_asset_adjustment, self).unlink(cr, uid, ids, context=context)         
        
        
        
        
        
