from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from datetime import datetime
from openerp import workflow
from openerp.tools.translate import _


class wtc_approval_matrixdiscount_header(models.Model):
    _name ="wtc.approval.matrixdiscount.header"
    _inherit = ['mail.thread']
    
    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 

    @api.cr_uid_ids_context
    def _get_default_form(self,cr,uid,ids,context=None):
        form = self.pool.get('wtc.approval.config').search(cr,uid,[
                                                       ('type','=','discount')
                                                       ]) 
        form_id = False
        if form :
            form_id =  self.pool.get('wtc.approval.config').browse(cr,uid,form)      
        return form_id
        
    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()
            
    form_id = fields.Many2one('wtc.approval.config',string='Form',domain="[('type','=','discount')]", default=_get_default_form)
    branch_id = fields.Many2one('wtc.branch',string='Branch', default=_get_default_branch)
    division = fields.Selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum')], 'Division', change_default=True, select=True)
    product_template_id = fields.Many2one('product.template',string='Product Template')
    wtc_approval_md_ids = fields.One2many('wtc.approval.matrixdiscount','wtc_approval_md_id')
    
    _sql_constraints = [
    ('unique_product_branch_form', 'unique(form_id,branch_id,product_template_id)', 'Approval sudah pernah dibuat !'),
    ]
    
    @api.model
    def create(self,values):
        config = self.env['wtc.approval.config'].search([
                                                         ('id','=',values['form_id']),
                                                         ])   
        for lines in values['wtc_approval_md_ids']:
            lines[2].update({'product_template_id':values['product_template_id'],'branch_id':values['branch_id'],'division':values['division'],'form_id':config.form_id.id})
        
        approval = super(wtc_approval_matrixdiscount_header,self).create(values)
        val = self.browse(approval)
        val.id.message_post(body=_("Approval created ")) 

        return approval
    
    @api.multi
    def write(self,values,context=None):
        if values.get('form_id',False):
            config = self.env['wtc.approval.config'].search([
                                                             ('id','=',values['form_id']),
                                                             ])            
            new_reg = self.env['wtc.approval.matrixdiscount'].search([('wtc_approval_md_id','=',self.id)],order="limit asc")
            update_reg_baru = new_reg.write({'form_id':config.form_id.id})
            
        if values.get('branch_id',False):
            new_reg = self.env['wtc.approval.matrixdiscount'].search([('wtc_approval_md_id','=',self.id)],order="limit asc")
            update_reg_baru = new_reg.write({'branch_id':values['branch_id']})
            
        if values.get('division',False):
            new_reg = self.env['wtc.approval.matrixdiscount'].search([('wtc_approval_md_id','=',self.id)],order="limit asc")
            update_reg_baru = new_reg.write({'division':values['division']})
            
        if values.get('product_template_id',False):
            new_reg = self.env['wtc.approval.matrixdiscount'].search([('wtc_approval_md_id','=',self.id)],order="limit asc")
            update_reg_baru = new_reg.write({'product_template_id':values['product_template_id']})
        
        if values.get('wtc_approval_md_ids',False):
            for lines in values['wtc_approval_md_ids']:
                if lines[1]==False:
                    lines[2].update({
                                     'form_id':self.form_id.form_id.id,
                                     'branch_id': self.branch_id.id,
                                     'division': self.division,
                                     'product_template_id': self.product_template_id.id
                                     })
        approval = super(wtc_approval_matrixdiscount_header,self).write(values)
        val = self.browse([self.id])
        val.message_post(body=_("Approval updated "))
        return approval
    
    @api.onchange('division')
    def category_change(self):
        dom = {}
        tampung = []
        if self.division:
            categ_ids = self.env['product.category'].get_child_ids(self.division)
            dom['product_template_id']=[('categ_id','in',categ_ids)]
        return {'domain':dom}
    
   

class wtc_approval_matrixdiscount(models.Model):
    _name = "wtc.approval.matrixdiscount"
    _description = "Approval Sales Order"
    _order = "id asc"
    
    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()
        
    @api.multi
    def _check_limit(self):
        if self.limit > 0:
          return True
        return False

    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
    
    form_id = fields.Many2one('ir.model',string='Form')
    branch_id = fields.Many2one('wtc.branch',string='Branch', default=_get_default_branch)
    division = fields.Selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum')], 'Division', change_default=True, select=True, required=True)
    group_id = fields.Many2one('res.groups',string='Group')
    product_template_id = fields.Many2one('product.template',string='Product Template')
    limit =  fields.Float(digits=(8,2), string="Limit")
    wtc_approval_md_id = fields.Many2one('wtc.approval.matrixdiscount.header',ondelete='cascade')
    
#     _constraints = [
#       (_check_limit, 'Limit harus lebih besar dari 0!', ['limit']),
#     ]

    _sql_constraints = [
    ('unique_approval_diskon', 'unique(group_id,wtc_approval_md_id)', 'Tidak boleh ada duplicate group approval!'),
    ]
    
    
    @api.multi
    def request(self, object, object_line, subject_to_approval,product_id):
        for obj_line in object_line:
            try:
                field_test = obj_line[subject_to_approval] and obj_line[product_id]
            except:
                raise Warning(('Perhatian !'), ("Transaksi ini tidak memiliki field " + subject_to_approval + ". Cek kembali Matrix Approval."))
            self.request_by_value(object,obj_line,obj_line[subject_to_approval],obj_line.product_id)
        return True
    
    @api.multi
    def request_by_value(self,object,object_line,value,product_id):
        product_template_id = product_id.product_tmpl_id.id
        config = self.env['wtc.approval.config'].search([
                                                         ('form_id','=',object.__class__.__name__),
                                                         ])
        if not config :
            raise Warning(('Perhatian !'), ("Form ini tidak memiliki approval configuration"))
        matrix = self.search([
            ('branch_id','=',object.branch_id.id),
            ('division','=',object.division),
            ('form_id','=',config.form_id.id),
            ('product_template_id','=',product_template_id)
          ],order="limit desc")
        if not matrix:
            raise Warning(('Perhatian !'), ("Transaksi ini tidak memiliki matrix approval. Cek kembali data Cabang & Divisi"))
    
        user_limit = 99999999999999

        approval_lines = []        
        for data in matrix :
            approval_lines.append(self.env['wtc.approval.line'].create({
              'value':value,
              'group_id':data.group_id.id,
              'transaction_id':object.id,
              'product_template_id': product_template_id,
              'branch_id':data.branch_id.id,
              'division':data.division,
              'form_id':data.form_id.id,
              'limit':data.limit,
              'sts':'1',
            }))

            if user_limit > data.limit:
                user_limit = data.limit
    
        if user_limit > value:
            raise Warning(('Perhatian !'), ("Nilai transaksi %d. Nilai terbersar di matrix approval: %d. Cek kembali Matrix Approval.") % (value, user_limit))
    
        # handle approval line
        #prepare_approval(object, approval_lines)
            
        return True

    @api.multi
    def prepare_approval(self, approval_lines):
        return True
    
    @api.multi
    def approve(self, trx, product_id):
        user_groups = self.env['res.users'].browse(self._uid)['groups_id']
        config = self.env['wtc.approval.config'].search([
                                                         ('form_id','=',trx.__class__.__name__),
                                                         ])
        if not config :
            raise Warning(('Perhatian !'), ("Form ini tidak memiliki approval configuration"))        
        approval_lines_ids = self.env['wtc.approval.line'].search([
                                                            ('branch_id','=',trx.branch_id.id),
                                                            ('division','=',trx.division),
                                                            ('form_id','=',config.form_id.id),
                                                            ('transaction_id','=',trx.id),
                                                            ('product_template_id','=',product_id.product_tmpl_id.id),
                                                          ],order="limit desc")
        if not approval_lines_ids:
            raise Warning('Perhatian ! Transaksi ini tidak memiliki detail approval. Cek kembali Matrix Approval.')
        approve_all = False
        user_limit = 999999999999999999
        
        for approval_line in approval_lines_ids:
            if approval_line.sts == '1':
                if approval_line.group_id in user_groups:
                    if approval_line.limit < user_limit:
                        user_limit = approval_line.limit
                        approve_all = approval_line.value >= user_limit
                        approval_line.write({
                                      'sts':'2',
                                      'pelaksana_id':self._uid,
                                      'tanggal':datetime.now(),
                                        })
    	    elif approval_line.sts=='2':
                user_limit = approval_line.limit
                approve_all = approval_line.value >= user_limit
        if user_limit:
            for approval_line in approval_lines_ids:
                if approval_line.sts == '1':
                    if approve_all:
                        approval_line.write({
                        'sts':'2',
                        'pelaksana_id':self._uid,
                        'tanggal':datetime.now(),
                      })
                    elif approval_line.limit >= user_limit:
                        approval_line.write({
                        'sts':'2',
                        'pelaksana_id':self._uid,
                        'tanggal':datetime.now(),
                      })
	
        if approve_all:
            return 1
        elif user_limit:
            return 2
	return 0
    
    @api.multi
    def reject(self, trx, reason):
        user_groups = self.env['res.users'].browse(self._uid)['groups_id']
        config = self.env['wtc.approval.config'].search([
                                                         ('form_id','=',trx.__class__.__name__),
                                                         ])
        if not config :
            raise Warning(('Perhatian !'), ("Form ini tidak memiliki approval configuration"))        
        approval_lines_ids = self.env['wtc.approval.line'].search([
                                                            ('branch_id','=',trx.branch_id.id),
                                                            ('division','=',trx.division),
                                                            ('form_id','=',config.id),
                                                            ('transaction_id','=',trx.id),
                                                            ('product_template_id','=',trx.id),
                                                          ],order="limit desc")
        if not approval_lines_ids:
            raise exceptions(('Perhatian !'), ("Transaksi ini tidak memiliki detail approval. Cek kembali Matrix Approval."))
        
        reject_all = False
        for approval_line in approval_lines_ids:
            if approval_line.sts == '1':
                if approval_line.group_id in user_groups:
                    reject_all = True
                    approval_line.write({
                      'sts':'3',
                      'reason':reason,
                      'pelaksana_id':uid,
                      'tanggal':datetime.now(),
                    })
                    break
        if reject_all:
            for approval_line in approval_lines:
                if approval_line.sts == '1':
                    approval_line.write({
                  'sts':'3',
                  'pelaksana_id':uid,
                  'tanggal':datetime.now(),
                })
            return 1
        return 0
    
    
#  
# class wtc_approval_discount_line(models.Model):
#     _name= "wtc.approval.line"
#     
#     @api.one
#     def _get_transaction_no(self):
#         x={}
#         self.transaction_no = self.env[self.form_id.model].browse(self.transaction_id).name
#         
#     
#     @api.one
#     def _get_groups(self):
#         x = self.env['res.users'].browse(self._uid)['groups_id']
#         #is self.group_id in x ?
#         self.is_mygroup = self.group_id in x 
#     
#     @api.multi
#     def _cek_groups(self,operator,value):
#         
#         group_ids = self.env['res.users'].browse(self._uid)['groups_id']
#         
#         if operator == '=' and value :
#             where = [('group_id', 'in', [x.id for x in group_ids])]
#         else :
#             where = [('group_id', 'not in', [x.id for x in group_ids])]
# 
#         return where
# 
#     @api.cr_uid_ids_context
#     def _get_default_branch(self,cr,uid,ids,context=None):
#         user_obj = self.pool.get('res.users')        
#         user_browse = user_obj.browse(cr,uid,uid)
#         branch_ids = False
#         branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
#         return branch_ids 
#         
#     transaction_id = fields.Integer('Transaction ID')
#     value = fields.Float('Value',digits=(12,2))
#     form_id = fields.Many2one('ir.model','Form')
#     group_id = fields.Many2one('res.groups','Group', select=True)
#     branch_id = fields.Many2one('wtc.branch','Branch',select=True, default=_get_default_branch)
#     division = fields.Selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum'),('Finance','Finance')], 'Division', change_default=True, select=True)
#     limit = fields.Float('Limit', digits=(12,2))
#     sts = fields.Selection([('1','Belum Approve'),('2','Approved'),('3','Rejected'),('4','Canceled')],'Status',change_default='1')
#     pelaksana_id = fields.Many2one('res.users','Pelaksana', size=128)
#     tanggal = fields.Datetime('Tanggal')
#     product_template_id = fields.Many2one('product.template',string='Product Template')
#     reason = fields.Text('Reason')
#     transaction_no = fields.Char(compute='_get_transaction_no', string="Transaction No")
#     is_mygroup = fields.Boolean(compute='_get_groups', string="is_mygroup", method=True, search='_cek_groups')
#               
#     @api.multi
#     def wtc_get_transaction(self):  
#         return {
#             'name': self.form_id.name,
#             'view_type': 'form',
#             'view_mode': 'form',
#             'res_model': self.form_id.model,
#             'type': 'ir.actions.act_window',
#             'nodestroy': True,
#             'target': 'new',
#             'res_id': self.transaction_id
#             }  
#         
# class wtc_approval_discount_reject(models.TransientModel):
#     _name = "wtc.approval.discount.reject"
#     
#     reason = fields.Text('Reason')
#                 
#     
#     @api.multi
#     def wtc_approval_reject(self, context=None):
#         
#         trx_id = context.get('active_id',False) #When you call any wizard then in this function ids parameter contain the list of ids of the current wizard record. So, to get the purchase order ID you have to get it from context.
#         model_name = context.get('model_name',False)
#         next_workflow = context.get('next_workflow',False)
# 
#         if not trx_id and not model_name:
#             raise exceptions(('Perhatian !'), ("Context di button belum lengkap."))
# 
#         trx_obj = self.env['model_name'].browse(trx_id,context=context)
#         if self.env['wtc.approval.matrixbiaya'].reject(cr, uid, ids, trx_obj, val.reason):
#             if next_workflow:
#                 workflow.trg_validate(uid, model_name, trx_id, next_workflow, cr) 
#         else :
#             raise exceptions(('Perhatian !'), ("User tidak termasuk group approval"))
#                                                       
#         return True
    
    
