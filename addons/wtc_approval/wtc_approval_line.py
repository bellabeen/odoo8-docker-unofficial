from openerp import models, fields, api, _

class wtc_approval_discount_line(models.Model):
    _name= "wtc.approval.line"
    
    @api.one
    def _get_transaction_no(self):
        x={}
        if self.form_id.model in ('account.voucher','wtc.account.voucher','wtc.dn.nc'):
            self.transaction_no = self.env[self.form_id.model].browse(self.transaction_id).number            
        else :
            self.transaction_no = self.env[self.form_id.model].browse(self.transaction_id).name
        
    @api.one
    def _get_groups(self):
        x = self.env['res.users'].browse(self._uid)['groups_id']
        #is self.group_id in x ?
        self.is_mygroup = self.group_id in x 
    
    @api.multi
    def _cek_groups(self,operator,value):
         
        group_ids = self.env['res.users'].browse(self._uid)['groups_id']
         
        if operator == '=' and value :
            where = [('group_id', 'in', [x.id for x in group_ids])]
        else :
            where = [('group_id', 'not in', [x.id for x in group_ids])]
 
        return where
    
    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
    
    transaction_id = fields.Integer('Transaction ID')
    value = fields.Float('Value',digits=(12,2))
    form_id = fields.Many2one('ir.model','Form')
    group_id = fields.Many2one('res.groups','Group', select=True)
    branch_id = fields.Many2one('wtc.branch','Branch',select=True, default=_get_default_branch)
    division = fields.Selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum'),('Finance','Finance')], 'Division', change_default=True, select=True)
    limit = fields.Float('Limit', digits=(12,2))
    sts = fields.Selection([('1','Belum Approve'),('2','Approved'),('3','Rejected'),('4','Cancelled')],'Status')
    pelaksana_id = fields.Many2one('res.users','Pelaksana', size=128)
    tanggal = fields.Datetime('Tanggal')
    product_template_id = fields.Many2one('product.template',string='Product Template')
    reason = fields.Text('Reason')
    transaction_no = fields.Char(compute='_get_transaction_no', string="Transaction No")
    is_mygroup = fields.Boolean(compute='_get_groups', string="is_mygroup", method=True, search='_cek_groups')
    view_name = fields.Char('View Name')
              
    @api.multi
    def wtc_get_transaction(self):  
        if self.view_name == False :
            return {
                'name': self.form_id.name,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': self.form_id.model,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new',
                'res_id': self.transaction_id
                }  
        else :
            obj_ir_view = self.env["ir.ui.view"]
            obj_ir_view_browse= obj_ir_view.search([("name", "=", self.view_name), ("model", "=", self.form_id.model)])
            return {
                'name': self.form_id.name,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': self.form_id.model,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new',
                'res_id': self.transaction_id,
                'view_id':obj_ir_view_browse.id
                }             