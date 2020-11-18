import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import workflow

class wtc_approval_matrixbiaya_header(osv.osv):
    _name = "wtc.approval.matrixbiaya.header"
    _inherit = ['mail.thread']
    _columns = {
                'branch_id':fields.many2one('wtc.branch',string='Branch',required=True),
                'division':fields.selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum'),('Finance','Finance')], 'Division', change_default=True, select=True, required=True),
                'approval_line': fields.one2many('wtc.approval.matrixbiaya', 'header_id', 'Approval lines'),
                'form_id':fields.many2one('wtc.approval.config',string='Form',required=True,domain="[('type','=','biaya')]"),
                }
    
    def _get_default_date(self,cr,uid,ids,context=None):
        return self.pool.get('wtc.branch').get_default_date(cr,uid,ids,context=context)

        
    def create(self, cr, uid, values, context=None):
        form_id = self.pool.get('wtc.approval.config').browse(cr,uid,values['form_id'])       
        for lines in values['approval_line']:
            lines[2].update({'code':form_id.code,'branch_id':values['branch_id'],'division':values['division'],'form_id':form_id.form_id.id})
        approval = super(wtc_approval_matrixbiaya_header,self).create(cr, uid, values, context=context)
        val = self.browse(cr,uid,approval)
        self.message_post(cr, uid, val.id, body=_("Approval created "), context=context) 
        return approval
    
    def write(self, cr, uid,ids,values,context=None):
        app=self.browse(cr,uid,ids)
        if values.get('form_id',False):
            config = self.pool.get('wtc.approval.config').search(cr,uid,[
                                                             ('id','=',values['form_id']),
                                                             ])   
            form_id = self.pool.get('wtc.approval.config').browse(cr,uid,config)               
            new_reg = self.pool.get('wtc.approval.matrixbiaya').search(cr,uid,[('header_id','=',app.id)],order="limit asc")
            self.pool.get('wtc.approval.matrixbiaya').write(cr, uid, new_reg,{'form_id':form_id.form_id.id,'code':form_id.code},context=context)
        if values.get('branch_id',False):
            new_reg = self.pool.get('wtc.approval.matrixbiaya').search(cr,uid,[('header_id','=',app.id)],order="limit asc")
            self.pool.get('wtc.approval.matrixbiaya').write(cr, uid, new_reg,{'branch_id':values['branch_id']},context=context)
            
        if values.get('division',False):
            new_reg = self.pool.get('wtc.approval.matrixbiaya').search(cr,uid,[('header_id','=',app.id)],order="limit asc")
            self.pool.get('wtc.approval.matrixbiaya').write(cr, uid, new_reg,{'division':values['division']},context=context)
        
        if values.get('approval_line',False):
            for lines in values['approval_line']:
                app=self.browse(cr,uid,ids)
                if lines[1]==False:
                    lines[2].update({
                                     'form_id':app.form_id.form_id.id,
                                     'branch_id':app.branch_id.id,
                                     'division':app.division,
                                     'code':app.form_id.code,
                                     })
                    
                    
        approval = super(wtc_approval_matrixbiaya_header,self).write(cr, uid,ids,values)
        self.message_post(cr, uid, app.id, body=_("Approval updated "), context=context) 
        return approval

class wtc_approval_matrixbiaya(osv.osv):
  _name="wtc.approval.matrixbiaya"
  
  
  def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
    
  def _get_default_date(self,cr,uid,ids,context=None):
        return self.pool.get('wtc.branch').get_default_date(cr,uid,ids,context=context)
    

  def _check_limit(self, cr, uid, ids, context=None):
    matrix = self.browse(cr, uid, ids, context=context)[0]
    if matrix.limit > 0:
      return True
    return False
 
    
    

  _columns = {
      'form_id':fields.many2one('ir.model',string='Form',required=True),
      'branch_id':fields.many2one('wtc.branch',string='Branch',required=True),
      'division':fields.selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum'),('Finance','Finance')], 'Division', change_default=True, select=True),
      #'code' : fields.selection([(' ',' ')],string="Code"),
      'code': fields.char('code', size=64, required=True),
      'group_id':fields.many2one('res.groups',string='Group',required=True,domain=[('category_id.name','=','TDM')]),
      'limit': fields.float(digits=(8,2), string="Limit",required=True),
      'header_id': fields.many2one('wtc.approval.matrixbiaya.header', 'Header', ondelete='cascade')
    }

  _constraints = [
      (_check_limit, 'Limit harus lebih besar dari 0!', ['limit']),
  ]


  _defaults = {
               'code':' ',
               'branch_id': _get_default_branch,
               }
  
  
 
    
    
  def request(self, cr, uid, ids, trx, subject_to_approval,code=' ',view_name=None):
    try:
      field_test = trx[subject_to_approval]
    except:
      raise osv.except_osv(('Perhatian !'), ("Transaksi ini tidak memiliki field %s. Cek kembali Matrix Approval.")%(subject_to_approval))
    return self.request_by_value(cr,uid,ids,trx,trx[subject_to_approval],code,view_name)

  def request_by_value(self,cr,uid,ids,trx,value,code=' ',view_name=None):
    config = self.pool.get('wtc.approval.config').search(cr,uid,[
                                                     ('form_id','=',trx.__class__.__name__),
                                                     ('code','=',code)
                                                     ])
    if not config :
        raise osv.except_osv(('Perhatian !'), ("Transaksi ini tidak memiliki Approval Configuration !"))
    config_brw = self.pool.get('wtc.approval.config').browse(cr,uid,config)   
    if trx.branch_id :
        matrix = self.search(cr, uid, [
            ('branch_id','=',trx.branch_id.id),
            ('division','=',trx.division),
            ('form_id','=',config_brw[0].form_id.id),
            ('code','=',config_brw.code)
          ],order="limit asc")  
    else :
        matrix = self.search(cr, uid, [
            ('branch_id','=',trx.branch_destination_id.id),
            ('division','=',trx.division),
            ('form_id','=',config_brw[0].form_id.id),
            ('code','=',config_brw.code)
          ],order="limit asc")              
    if not matrix:
      raise osv.except_osv(('Perhatian !'), ("Transaksi ini tidak memiliki matrix approval. Cek kembali data Cabang & Divisi"))

    data = self.browse(cr, uid, matrix)

    user_limit = 0
    
    if view_name is None :
        for x in data :
          self.pool.get('wtc.approval.line').create(cr, uid, {
              'value':value,
              'group_id':x.group_id.id,
              'transaction_id':trx.id,
              'branch_id':x.branch_id.id,
              'division':x.division,
              'form_id':x.form_id.id,
              'limit':x.limit,
              'sts':'1',
            })
          if user_limit < x.limit:
            user_limit = x.limit
    else :
        for x in data :
          self.pool.get('wtc.approval.line').create(cr, uid, {
              'value':value,
              'group_id':x.group_id.id,
              'transaction_id':trx.id,
              'branch_id':x.branch_id.id,
              'division':x.division,
              'form_id':x.form_id.id,
              'limit':x.limit,
              'sts':'1',
              'view_name':view_name
            })
          if user_limit < x.limit:
            user_limit = x.limit
            
    if user_limit < value:
      raise osv.except_osv(('Perhatian !'), ("Nilai transaksi %d. Nilai terbersar di matrix approval: %d. Cek kembali Matrix Approval.") % (value, user_limit))

    return True

  def request_by_value_branch_destination(self,cr,uid,ids,trx,value,code=' ',view_name=None):
    config = self.pool.get('wtc.approval.config').search(cr,uid,[
                                                     ('form_id','=',trx.__class__.__name__),
                                                     ('code','=',code)
                                                     ])
    if not config :
        raise Warning(('Perhatian !'), ("Form ini tidak memiliki approval configuration"))   
    config_brw = self.pool.get('wtc.approval.config').browse(cr,uid,config)       
    matrix = self.search(cr, uid, [
        ('branch_id','=',trx.branch_destination_id.id),
        ('division','=',trx.division),
        ('form_id','=',config_brw[0].form_id.id),
        ('code','=',config_brw.code)
        ],order="limit asc")      
    if not matrix:
      raise osv.except_osv(('Perhatian !'), ("Transaksi ini tidak memiliki matrix approval. Cek kembali data Cabang & Divisi"))

    data = self.browse(cr, uid, matrix)

    user_limit = 0
    
    if view_name is None :
        for x in data :
          self.pool.get('wtc.approval.line').create(cr, uid, {
              'value':value,
              'group_id':x.group_id.id,
              'transaction_id':trx.id,
              'branch_id':x.branch_id.id,
              'division':x.division,
              'form_id':x.form_id.id,
              'limit':x.limit,
              'sts':'1',
            })
          if user_limit < x.limit:
            user_limit = x.limit
    else :
        for x in data :
          self.pool.get('wtc.approval.line').create(cr, uid, {
              'value':value,
              'group_id':x.group_id.id,
              'transaction_id':trx.id,
              'branch_id':x.branch_id.id,
              'division':x.division,
              'form_id':x.form_id.id,
              'limit':x.limit,
              'sts':'1',
              'view_name':view_name
            })
          if user_limit < x.limit:
            user_limit = x.limit
            
    if user_limit < value:
      raise osv.except_osv(('Perhatian !'), ("Nilai transaksi %d. Nilai terbersar di matrix approval: %d. Cek kembali Matrix Approval.") % (value, user_limit))

    return True

  def approve(self, cr, uid, ids, trx):
    user_groups = self.pool.get('res.users').browse(cr, uid, uid)['groups_id']
    config = self.pool.get('wtc.approval.config').search(cr,uid,[
                                                     ('form_id','=',trx.__class__.__name__),
                                                     ])
    if not config :
        raise Warning(('Perhatian !'), ("Form ini tidak memiliki approval configuration"))   
    config_brw = self.pool.get('wtc.approval.config').browse(cr,uid,config)    
    if trx.branch_id :
        approval_lines_ids = self.pool.get('wtc.approval.line').search(cr, uid, [
            ('branch_id','=',trx.branch_id.id),
            ('division','=',trx.division),
            ('form_id','=',config_brw[0].form_id.id),
            ('transaction_id','=',trx.id),
          ],order="limit asc")
    else :
        approval_lines_ids = self.pool.get('wtc.approval.line').search(cr, uid, [
            ('branch_id','=',trx.branch_destination_id.id),
            ('division','=',trx.division),
            ('form_id','=',config_brw[0].form_id.id),
            ('transaction_id','=',trx.id),
          ],order="limit asc")        
    if not approval_lines_ids:
      raise osv.except_osv(('Perhatian !'), ("Transaksi ini tidak memiliki detail approval. Cek kembali Matrix Approval."))
    approve_all = False
    user_limit = 0
    approval_lines = self.pool.get('wtc.approval.line').browse(cr, uid, approval_lines_ids)
    for approval_line in approval_lines:
      if approval_line.sts == '1':
        if approval_line.group_id in user_groups:
          if approval_line.limit > user_limit:
            user_limit = approval_line.limit
            approve_all = approval_line.value <= user_limit
          approval_line.write({
              'sts':'2',
              'pelaksana_id':uid,
              'tanggal':datetime.now(),
            })
    if user_limit:
      for approval_line in approval_lines:
        if approval_line.sts == '1':
          if approve_all:
            approval_line.write({
                'sts':'2',
                'pelaksana_id':uid,
                'tanggal':datetime.now(),
              })
          elif approval_line.limit <= user_limit:
            approval_line.write({
                'sts':'2',
                'pelaksana_id':uid,
                'tanggal':datetime.now(),
              })
    if approve_all:
      return 1
    elif user_limit:
      return 2
    return 0

  def reject(self, cr, uid, ids, trx, reason):
    user_groups = self.pool.get('res.users').browse(cr, uid, uid)['groups_id']
    config = self.pool.get('wtc.approval.config').search(cr,uid,[
                                                     ('form_id','=',trx.__class__.__name__),
                                                     ])
    if not config :
        raise Warning(('Perhatian !'), ("Form ini tidak memiliki approval configuration"))   
    config_brw = self.pool.get('wtc.approval.config').browse(cr,uid,config)    
    if trx.branch_id :
        approval_lines_ids = self.pool.get('wtc.approval.line').search(cr, uid, [
            ('branch_id','=',trx.branch_id.id),
            ('division','=',trx.division),
            ('form_id','=',config_brw[0].form_id.id),
            ('transaction_id','=',trx.id),
          ],order="limit asc")
    else :
        approval_lines_ids = self.pool.get('wtc.approval.line').search(cr, uid, [
            ('branch_id','=',trx.branch_destination_id.id),
            ('division','=',trx.division),
            ('form_id','=',config_brw[0].form_id.id),
            ('transaction_id','=',trx.id),
          ],order="limit asc")        
    if not approval_lines_ids:
      raise osv.except_osv(('Perhatian !'), ("Transaksi ini tidak memiliki detail approval. Cek kembali Matrix Approval."))
    approval_lines = self.pool.get('wtc.approval.line').browse(cr, uid, approval_lines_ids)
    reject_all = False
    for approval_line in approval_lines:
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
              'reason':reason,
              'tanggal':datetime.now(),
            })
      return 1
    return 0

  def cancel_approval(self, cr, uid, ids, trx, reason):
    config = self.pool.get('wtc.approval.config').search(cr,uid,[
                                                     ('form_id','=',trx.__class__.__name__),
                                                     ])
    if not config :
        raise Warning(('Perhatian !'), ("Form ini tidak memiliki approval configuration"))   
    config_brw = self.pool.get('wtc.approval.config').browse(cr,uid,config)      
    if trx.branch_id :
        approval_lines_ids = self.pool.get('wtc.approval.line').search(cr, uid, [
            ('branch_id','=',trx.branch_id.id),
            ('division','=',trx.division),
            ('form_id','=',config_brw[0].form_id.id),
            ('transaction_id','=',trx.id),
          ],order="limit asc")
    else :
        approval_lines_ids = self.pool.get('wtc.approval.line').search(cr, uid, [
            ('branch_id','=',trx.branch_destination_id.id),
            ('division','=',trx.division),
            ('form_id','=',config_brw[0].form_id.id),
            ('transaction_id','=',trx.id),
          ],order="limit asc")        
    if not approval_lines_ids:
      raise osv.except_osv(('Perhatian !'), ("Transaksi ini tidak memiliki detail approval. Cek kembali Matrix Approval."))
    approval_lines = self.pool.get('wtc.approval.line').browse(cr, uid, approval_lines_ids)
    cancel_all = False
    for approval_line in approval_lines:
      if approval_line.sts == '1':
          cancel_all = True
          approval_line.write({
              'sts':'4',
              'reason':reason,
              'pelaksana_id':uid,
              'tanggal':datetime.now(),
            })
          break
    if cancel_all:
      for approval_line in approval_lines:
        if approval_line.sts == '1':
          approval_line.write({
              'sts':'4',
              'pelaksana_id':uid,
              'reason':reason,
              'tanggal':datetime.now(),
            })
      return 1
    return 0  
 
class wtc_approval_reject(osv.osv_memory):
    _name = "wtc.approval.reject"
    _columns = {
                'reason':fields.text('Reason')
                }
    
    def wtc_approval_reject(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids, context=context)
        
        trx_id = context.get('active_id',False) #When you call any wizard then in this function ids parameter contain the list of ids of the current wizard record. So, to get the purchase order ID you have to get it from context.
        model_name = context.get('model_name',False)
        next_workflow = context.get('next_workflow',False)
        update_value = context.get('update_value',False)
        
        if not trx_id and not model_name:
            raise osv.except_osv(('Perhatian !'), ("Context di button belum lengkap."))

        trx_obj = self.pool.get(model_name).browse(cr,uid,trx_id,context=context)
        if self.pool.get('wtc.approval.matrixbiaya').reject(cr, uid, ids, trx_obj, val.reason):
            if next_workflow:
                workflow.trg_validate(uid, model_name, trx_id, next_workflow, cr) 
            elif update_value :
                self.pool.get(model_name).write(cr,uid,trx_id,update_value)
        else :
            raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group approval"))                                                        
        return True
    
class wtc_approval_cancel(osv.osv_memory):
    _name = "wtc.approval.cancel"
    _columns = {
                'reason':fields.text('Reason')
                }
    
    def wtc_approval_cancel(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids, context=context)
        
        trx_id = context.get('active_id',False) #When you call any wizard then in this function ids parameter contain the list of ids of the current wizard record. So, to get the purchase order ID you have to get it from context.
        model_name = context.get('model_name',False)
        next_workflow = context.get('next_workflow',False)
        update_value = context.get('update_value',False)
        if not trx_id and not model_name:
            raise osv.except_osv(('Perhatian !'), ("Context di button belum lengkap."))

        trx_obj = self.pool.get(model_name).browse(cr,uid,trx_id,context=context)
        if self.pool.get('wtc.approval.matrixbiaya').cancel_approval(cr, uid, ids, trx_obj, val.reason):
            if next_workflow:
                workflow.trg_validate(uid, model_name, trx_id, next_workflow, cr) 
            elif update_value :
                self.pool.get(model_name).write(cr,uid,trx_id,update_value)
        else :
            raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group approval"))                                                        
        return True
    
class wtc_approval_cancel_after_approve(osv.osv_memory):
    _name = "wtc.approval.cancel.after.approve"
    _columns = {
                'reason':fields.text('Reason'),
                }    
    
    def _get_default_date(self,cr,uid,ids,context=None):
        return self.pool.get('wtc.branch').get_default_date(cr,uid,ids,context=context)
        
    def wtc_cancel_approval(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids, context=context)
        
        trx_id = context.get('active_id',False) #When you call any wizard then in this function ids parameter contain the list of ids of the current wizard record. So, to get the purchase order ID you have to get it from context.
        model_name = context.get('model_name',False)
        next_workflow = context.get('next_workflow',False)
        update_value = context.get('update_value',False)
        if not trx_id and not model_name:
            raise osv.except_osv(('Perhatian !'), ("Context di button belum lengkap."))
        reject_reason = "batal approve: "+val.reason
        trx_obj = self.pool.get(model_name).browse(cr,uid,trx_id,context=context)
        for approval_line in trx_obj.approval_ids:
            approval_line.write({'sts':'4'})
        form_id = self.pool.get('ir.model').search(cr,uid,[('model','=', model_name)])
        
        history = self.pool.get('wtc.approval.line').create(cr,uid,{
                                                                    'form_id': form_id[0],
                                                                    'sts':'4', 
                                                                    'transaction_id': trx_id, 
                                                                    'pelaksana_id': uid, 
                                                                    'reason': reject_reason,
                                                                    'tanggal':datetime.now(),
                                                                    'division':trx_obj.division,
                                                                    'branch_id':trx_obj.branch_id.id})
        
        if next_workflow:
            workflow.trg_validate(uid, model_name, trx_id, next_workflow, cr)
        elif update_value :
            self.pool.get(model_name).write(cr,uid,trx_id,update_value)
                                                        
        return True 