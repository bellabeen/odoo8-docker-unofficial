import time
from datetime import datetime
from openerp import models, fields, api
from openerp.osv import osv
from openerp.tools.translate import _
    
class wtc_account_asset_asset_custom(models.Model):
    _inherit = 'account.asset.asset'
    
    purchase_asset_id = fields.Many2one('wtc.purchase.asset','Purchase No')        
    receive_id = fields.Many2one('wtc.transfer.asset',string="Receipt No")

    @api.onchange('method_number')
    def change_depreciation(self):
        if self.method_number and self.category_id.type == 'fixed' and self.category_id.method_number != self.method_number :
            self.method_number = self.category_id.method_number
            return {'warning': {'title':'Perhatian !','message':'Number of Depreciations untuk fixed asset tidak bisa diubah !'}}
           
class wtc_transfer_asset(models.Model):
    _name = 'wtc.transfer.asset'
    _desctiption = 'Transfer Asset'
    _order = 'date desc'
    
    STATE_SELECTION = [
        ('draft', 'Draft'),       
        ('done','Posted'),
        ('cancel','Cancelled')
    ]

    @api.multi
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date()
            
    name = fields.Char(string="Receipt Asset No", default="#")
    date = fields.Date(string="Date",default=_get_default_date)
    transfer_ids = fields.One2many('wtc.transfer.asset.line','transfer_id')
    asset_ids = fields.One2many('account.asset.asset','receive_id')    
    state = fields.Selection(STATE_SELECTION, string='State', readonly=True,default='draft')
    confirm_uid = fields.Many2one('res.users',string="Posted by")
    confirm_date = fields.Datetime('Posted on')
    cancel_uid = fields.Many2one('res.users',string="Cancelled by")
    cancel_date = fields.Datetime('Cancelled on')             
                    
    @api.multi
    def create_journal_receipt_asset(self,x,periods):
        branch_config = self.env['wtc.branch.config'].search([
                                                              ('branch_id','=',x.asset_id.branch_id.id)
                                                              ])
        if not branch_config.prepaid_account_id :
                raise osv.except_osv(('Perhatian !'), ("Prepaid account belum diisi di Branch Config %s!")%(x.asset_id.branch_id.name))
        if not branch_config.accrue_account_id :
                raise osv.except_osv(('Perhatian !'), ("Accrue account belum diisi di Branch Config %s!")%(x.asset_id.branch_id.name))
        if not branch_config.receipt_asset_journal_id :
                raise osv.except_osv(('Perhatian !'), ("Journal Receipt Asset belum diisi di Branch Config %s!")%(x.asset_id.branch_id.name))
                
        journal_receipt_id = branch_config.receipt_asset_journal_id
        prepaid_account = branch_config.prepaid_account_id.id
        accrue_account = branch_config.accrue_account_id.id
        gross_value = x.asset_id.purchase_value + x.retensi
        if gross_value < 0 :
            raise osv.except_osv(('Perhatian !'), ("Silahkan lakukan proses Purchase Asset telebih dahulu untuk asset NO ")%(x.asset_id.register_no))
            
        if x.asset_id.state == 'draft' :
            account_debit = x.asset_id.category_id.account_asset_id.id
            amount_debit = x.asset_id.purchase_value
            account_credit = prepaid_account
            amount_credit = x.asset_id.purchase_value #DP # RECONCILE TO DP ON PURCHASE ASSET
            move_id_draft = self.action_move_line_create_from_draft(self.name, self.date,x,periods,journal_receipt_id,account_credit,account_debit,amount_credit,amount_debit)
        elif x.asset_id.state == 'CIP' :
            gross_value = x.asset_id.purchase_value + x.retensi
            account_debit = x.category_id.account_asset_id.id
            amount_debit = gross_value
            account_credit_asset = x.asset_id.category_id.account_asset_id.id
            amount_credit_asset = x.asset_id.purchase_value
            account_credit_accrue = accrue_account
            amount_credit_accrue = x.retensi
            move_id_cip = self.action_move_line_create_from_cip(self.name, self.date, x, periods, journal_receipt_id, account_credit_asset,account_credit_accrue, amount_credit_asset,amount_credit_accrue,account_debit, amount_debit)
        else :
            raise osv.except_osv(('Perhatian !'), ("Status Asset %s (Reg) %s (Name) sudah Running / Closed !")%(x.asset_id.register_no,x.asset_id.name))
            
        return True
    
    @api.cr_uid_ids_context
    def action_move_line_create_from_draft(self, cr, uid, ids, name, date, x,periods,journal_receipt_id,account_credit,account_debit,amount_credit,amount_debit,context=None):
        if context is None:
            context = {}
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        name = name
        date = date
        journal_id = journal_receipt_id.id
        credit_account_id = account_credit
        debit_account_id = account_debit
        if not credit_account_id or not debit_account_id:
            raise osv.except_osv(('Perhatian !'), ("Account belum diisi dalam branch config !"))
        period_id = periods and periods[0]
        ## Create account move
        move = {
            'name': name,
            'ref':name,
            'journal_id': journal_id,
            'date': date,
            'period_id':period_id,
        }
        move_id = move_pool.create(cr, uid, move, context=None)
        
        ## Create account move line for asset
        move_line_asset = {
            'name':x.asset_id.name +' (Asset)',
            'ref':name,
            'account_id': debit_account_id,
            'move_id': move_id,
            'journal_id': journal_id,
            'period_id': period_id,
            'date': date,
            'debit': amount_debit,
            'credit': 0.0,
            'branch_id' : x.asset_id.branch_id.id,
            'division' : x.asset_id.division,
            'ref_asset_id' : x.asset_id.id,     
            'partner_id' : x.asset_id.partner_id.id,    
        }    
        line_asset_id = move_line_pool.create(cr, uid, move_line_asset, context)                     

        ## Create account move line for down payment
        move_line_dp = {
            'name': x.asset_id.name + ' (DP)',
            'ref':name,
            'account_id': credit_account_id,
            'move_id': move_id,
            'journal_id': journal_id,
            'period_id': period_id,
            'date': date,
            'debit': 0.0,
            'credit': amount_credit,
            'branch_id' : x.asset_id.branch_id.id,
            'division' : x.asset_id.division,
            'ref_asset_id' : x.asset_id.id,
            'partner_id' : x.asset_id.partner_id.id,
        }           
        line_dp_id = move_line_pool.create(cr, uid, move_line_dp, context) 
        if journal_receipt_id.entry_posted:
            move_pool.post(cr, uid, [move_id], context=None)
        return move_id

    @api.cr_uid_ids_context
    def action_move_line_create_from_cip(self, cr, uid, ids, name, date, x,periods,journal_receipt_id,account_credit_asset,account_credit_accrue,amount_credit_asset,amount_credit_accrue,account_debit,amount_debit,context=None):
        if context is None:
            context = {}
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        name = name
        date = date
        journal_id = journal_receipt_id.id
        debit_account_id = account_debit
        credit_asset_account_id = account_credit_asset
        credit_accure_account_id = account_credit_accrue
        if not credit_asset_account_id or not credit_accure_account_id or not debit_account_id:
            raise osv.except_osv(('Perhatian !'), ("Account belum diisi dalam branch config !"))
        period_id = periods and periods[0]
                
        ## Create account move
        move = {
            'name': name,
            'ref':name,
            'journal_id': journal_id,
            'date': date,
            'period_id':period_id,
        }
        move_id = move_pool.create(cr, uid, move, context=None)
        
        ## Create account move line for asset New
        move_line_asset_new = {
            'name':x.asset_id.name + ' (New)',
            'ref':name,
            'account_id': debit_account_id,
            'move_id': move_id,
            'journal_id': journal_id,
            'period_id': period_id,
            'date': date,
            'debit': amount_debit,
            'credit': 0.0,
            'branch_id' : x.asset_id.branch_id.id,
            'division' : x.asset_id.division,
            'ref_asset_id' : x.asset_id.id,  
            'partner_id' : x.asset_id.partner_id.id,       
        }    
        line_asset_new_id = move_line_pool.create(cr, uid, move_line_asset_new, context)                     

        ## Create account move line for Asset Old
        move_line_asset_old = {
            'name': x.asset_id.name + ' (Old)',
            'ref':name,
            'account_id': credit_asset_account_id,
            'move_id': move_id,
            'journal_id': journal_id,
            'period_id': period_id,
            'date': date,
            'debit': 0.0,
            'credit': amount_credit_asset,
            'branch_id' : x.asset_id.branch_id.id,
            'division' : x.asset_id.division,
            'ref_asset_id' : x.asset_id.id,
            'partner_id' : x.asset_id.partner_id.id,
        }           
        line_asset_old_id = move_line_pool.create(cr, uid, move_line_asset_old, context)  
        
        ## Create account move line for Accrue Retensi
        move_line_accrue = {
            'name': x.asset_id.name + ' (Retensi)',
            'ref':name,
            'account_id': credit_accure_account_id,
            'move_id': move_id,
            'journal_id': journal_id,
            'period_id': period_id,
            'date': date,
            'debit': 0.0,
            'credit': amount_credit_accrue,
            'branch_id' : x.asset_id.branch_id.id,
            'division' : x.asset_id.division,
            'ref_asset_id' : x.asset_id.id,
            'partner_id' : x.asset_id.partner_id.id,
        }           
        line_dp_accrue = move_line_pool.create(cr, uid, move_line_accrue, context)
        
        if journal_receipt_id.entry_posted:
            move_pool.post(cr, uid, [move_id], context=None)
        return move_id
            
    @api.multi
    def confirm(self) :
        asset_obj = self.env['account.asset.asset']     
        data = {}  
        periods = self.pool.get('account.period').find(self._cr,self._uid,self._get_default_date().date())
        is_validate = False  
                      
        for x in self.transfer_ids : 
            x.asset_id.compute_depreciation_board()
            self.create_journal_receipt_asset(x,periods)
            if x.asset_id.purchase_date != x.document_date :
                data['purchase_date'] = x.document_date            
            if x.asset_id.category_id.is_cip and x.asset_id.state != 'CIP' :
                data['state'] = 'CIP'
                data['code'] =  self.pool.get('ir.sequence').get_id(self._cr, self._uid, [x.asset_id.category_id.sequence_id.id])
            elif (x.asset_id.state == 'draft' and not x.asset_id.category_id.is_cip ) or x.asset_id.state == 'CIP' :
                if x.asset_id.state == 'CIP' :
                    data['category_id'] = x.category_id.id
                    data['prorata'] = x.category_id.prorata
                    data['first_day_of_month'] = x.category_id.first_day_of_month
                    data['method_number'] = x.category_id.method_number
                    data['method_period'] = x.category_id.method_period
                    data['method'] = x.category_id.method
                    data['method_time'] = x.category_id.method_time
                    data['purchase_value'] = x.asset_id.purchase_value + x.retensi
                    data['retensi'] = x.retensi
                    
                is_validate = True
            data['receive_id'] = self.id
            if x.method_number :
                data['method_number'] = x.method_number
            x.asset_id.write(data)
            if is_validate :
                x.asset_id.validate()
        self.write({
                    'date':self._get_default_date(),
                    'state':'done',
                    'confirm_uid':self._uid,
                    'confirm_date':datetime.now()})
        return True
        
    @api.model
    def create(self,values,context=None):
        vals = []
        values['name'] = self.env['ir.sequence'].get_sequence('RA')    
        for x in values['transfer_ids'] :
            if 'method_number' not in x[2] :
                asset_id = self.env['account.asset.asset'].browse(x[2]['asset_id'])
                x[2]['method_number'] = asset_id.method_number
        receipt_asset = super(wtc_transfer_asset,self).create(values)       
        return receipt_asset
            
    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Receipt Asset %s tidak bisa dihapus dalam status 'Posted' !")%(item.name))
        return super(wtc_transfer_asset, self).unlink(cr, uid, ids, context=context)     

class wtc_transfer_asset_line(models.Model):
    _name = 'wtc.transfer.asset.line'
    _rec_name = 'description'
    
    @api.depends('price_unit')
    def get_price_unit(self):
        self.price_unit_show = self.price_unit 
        
    transfer_id = fields.Many2one('wtc.transfer.asset',string="Transfer No")
    product_id = fields.Many2one(related='asset_id.product_id',string="Product",store=True)
    asset_id = fields.Many2one('account.asset.asset',string="Asset",domain="[('state','in',('draft','CIP')),('real_purchase_value','>',0)]",store=True)
    description = fields.Char(related='asset_id.name',string='Description',store=True)
    category_id = fields.Many2one('account.asset.category','Asset Category',store=True)
    branch_id = fields.Many2one(related='asset_id.branch_id',string="Branch",store=True)
    document_date = fields.Date(string="Document Date")
    method_number = fields.Integer(string='Number of Depreciations',help="Jumlah depresiasi")
    method_period = fields.Integer(related='asset_id.method_period',string='Period Length',help="Per berapa bulan ?",default=1,store=True)  
    purchase_value = fields.Float('Current Value',store=True)
    responsible_id = fields.Many2one(related='asset_id.responsible_id',string="Responsible",store=True)
    asset_classification_id = fields.Many2one(related='asset_id.asset_classification_id',store=True,string="Asset Classification",domain="[('categ_id','=',asset_categ_id)]")
    retensi = fields.Float(string='Retensi')
    
    _sql_constraints = [('unique_transfer_asset_line', 'unique(transfer_id,asset_id)', 'Nomor Asset tidak boleh duplikat,silahkan periksa kembali data anda !'),]  

    @api.onchange('asset_id','category_id','purchase_value')
    def onchange_asset(self):
        if self.asset_id :
            if self.asset_id.state != 'CIP' :
                self.category_id = self.asset_id.category_id.id  
            self.branch_id = self.asset_id.branch_id.id 
            self.document_date = self.asset_id.purchase_date
            self.method_number = self.asset_id.category_id.method_number
            self.method_period = self.asset_id.category_id.method_period
            self.prorata = self.asset_id.category_id.prorata
            self.first_day_of_month = self.asset_id.category_id.first_day_of_month
            self.responsible_id = self.asset_id.responsible_id.id
            self.product_id = self.asset_id.product_id.id
            self.description = self.asset_id.name
            self.purchase_value = self.asset_id.purchase_value
            self.asset_classification_id = self.asset_id.asset_classification_id.id            
         
    @api.onchange('asset_id','retensi')
    def onchange_retensi(self):
            if not self.asset_id.state == 'CIP' :
                self.retensi = 0
                
    @api.onchange('method_number')
    def change_depreciation(self):
        if self.method_number and self.category_id.type == 'fixed' and self.asset_id.category_id.method_number != self.method_number :
            self.method_number = self.asset_id.category_id.method_number
            return {'warning': {'title':'Perhatian !','message':'Number of Depreciations untuk fixed asset tidak bisa diubah !'}}
