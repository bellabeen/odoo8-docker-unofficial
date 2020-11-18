import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp

class wtc_reimbursed(models.Model):
    _name = "wtc.reimbursed"
    _description ="Reimbursed Petty Cash"
    _inherit = ['mail.thread']
    _order = "date_request desc"
    
    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('request', 'Requested'),
        ('approved', 'Approved'),
        ('reject', 'Rejected'),
        ('paid', 'Paid'),
        ('cancel', 'Cancelled'),
    ]   

    @api.one
    @api.depends('pettycash_ids.amount_real')
    def _compute_amount(self):
        self.amount_total = sum(line.amount_real for line in self.pettycash_ids)

    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
 
    @api.one
    @api.depends('pettycash_ids')            
    def _count_detail_payslip(self):
        self.pettycash_count = len(self.pettycash_ids)
           
    @api.multi
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date()
                            
    name = fields.Char(string="Name",readonly=True,default='')
    branch_id = fields.Many2one('wtc.branch', string='Branch', required=True, default=_get_default_branch)
    division = fields.Selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum'),('Finance','Finance')], string='Division',default='Unit', change_default=True, select=True)
    journal_id = fields.Many2one('account.journal',string="Payment Method",domain="[('branch_id','=',branch_id),('type','=','pettycash')]")
    state= fields.Selection(STATE_SELECTION, string='State', readonly=True,default='draft')
    date_request = fields.Date(string="Date Requested",required=True,readonly=True,default=_get_default_date)
    date_approve = fields.Date(string="Date Approved",readonly=True)
    date_cancel = fields.Date(string="Date Rejected/Canceled",readonly=True)
    pettycash_ids = fields.One2many('wtc.pettycash','reimbursed_id','Pettycash Line')
    amount_total = fields.Float(string='Total Amount',digits=dp.get_precision('Account'), store=True, readonly=True, compute='_compute_amount',)
    confirm_uid = fields.Many2one('res.users',string="Requested by")
    confirm_date = fields.Datetime('Requested on')
    cancel_uid = fields.Many2one('res.users',string="Cancelled by")
    cancel_date = fields.Datetime('Cancelled on')
    pettycash_count = fields.Integer(compute=_count_detail_payslip, string="Items")


    def button_pettycash_out(self,cr,uid,ids,context=None):
        mod_obj = self.pool.get('ir.model.data')        
        act_obj = self.pool.get('ir.actions.act_window')        
        result = mod_obj.get_object_reference(cr, uid, 'wtc_pettycash', 'pettycash_action')        
        id = result and result[1] or False        
        result = act_obj.read(cr, uid, [id], context=context)[0]
        val = self.browse(cr, uid, ids)
        if val.pettycash_ids.ids:
            result['domain'] = "[('id','in',"+str(val.pettycash_ids.ids)+")]"
        else:
            res = mod_obj.get_object_reference(cr, uid, 'wtc_pettycash', 'pettycash_tree_view')
            result['views'] = [(res and res[1] or False, 'tree')]
            result['res_id'] = False 
        return result
    
    @api.cr_uid_ids_context
    def button_dummy(self, cr, uid, ids, context=None):
        return True
                
    @api.model
    def create(self,vals,context=None):
        if not vals['pettycash_ids'] :
            raise osv.except_osv(('Perhatian !'), ("Detail belum diisi. Data tidak bisa di save."))
 
        petty = []
        for x in vals['pettycash_ids']:
            petty.append(x.pop(2))
        
        del[vals['pettycash_ids']]               
        vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'PCR')       
        vals['date_request'] = self._get_default_date()
        petty_pool = self.env['wtc.pettycash']
        reimbursed_id = super(wtc_reimbursed, self).create(vals)
        if reimbursed_id :         
                for x in petty :
                    petty_search = petty_pool.search([
                                ('branch_id','=',vals['branch_id']),
                                ('reimbursed_id','=',False),
                                ('name','=',x['name'])
                                ])
                    if not petty_search :
                        raise osv.except_osv(('Perhatian !'), ("Petty Cash Tidak ditemukan"))
                       
                    petty_search.write({
                           'reimbursed_id':reimbursed_id.id,
                           })  
        else :
            return False
        return reimbursed_id 
        
    @api.multi
    def cancel(self):
        pettycash = self.env['wtc.pettycash']
        for x in self.pettycash_ids :
            pettycash_browse = pettycash.search([('name','=',x.name)])
            pettycash_browse.write({'reimbursed_id':False,'state':'posted'})        
        self.state = 'cancel'
        self.date_cancel = self._get_default_date()
        self.cancel_uid = self._uid
        self.cancel_date = datetime.now()
        
    @api.multi
    def reject(self):
        pettycash = self.env['wtc.pettycash']
        for x in self.pettycash_ids :
            pettycash_browse = pettycash.search([('name','=',x.name)])
            pettycash_browse.write({'reimbursed_id':False,'state':'posted'})        
        self.state = 'reject'
        self.date_cancel = self._get_default_date()        
    
    @api.multi
    def request(self):
        pettycash = self.env['wtc.pettycash']
        cash = ''
        for x in self.pettycash_ids :
            pettycash_browse = pettycash.search([('name','=',x.name)])
            pettycash_browse.write({'state':'reimbursed'})
            cash += ('- '+str(x.name)+'<br/>')
        self.message_post(body=_("Reimbursed Requested <br/> Petty Cash No : <br/>  %s ")%(cash))                             
        self.state = 'request'
        self.confirm_uid = self._uid
        self.confirm_date = datetime.now()
        self.date_request = self._get_default_date()
        
    @api.cr_uid_ids_context
    def onchange_pettycash(self, cr, uid, ids,branch_id,division,journal_id,context=None):
        pettycash = self.pool.get('wtc.pettycash')
        if ids :
            obj = self.browse(cr,uid,ids)
            for x in obj.pettycash_ids :
                pettycash_search = pettycash.search(cr,uid,[
                                      ('reimbursed_id','=',obj.id)
                                      ])
                if pettycash_search :
                    pettycash_browse = pettycash.browse(cr,uid,pettycash_search)
                    pettycash_browse.write({
                                       'reimbursed_id':False
                                       })
            
        if context is None:
            context = {}
        if branch_id is None :
            context = {}
        if journal_id is None :
            context = {}
        if division is None :
            context = {}            
        if branch_id and journal_id and division :
            pettycash_search = pettycash.search(cr,uid,[
                                        ('branch_id','=',branch_id),
                                        ('journal_id','=',journal_id),
                                        ('division','=',division),
                                        ('state','=','posted'),
                                        ('reimbursed_id','=',False),
                                        ])
            petty = []
            if not pettycash_search :
                petty = []
            elif pettycash_search :
                pettycash_brw = pettycash.browse(cr,uid,pettycash_search)           
                for x in pettycash_brw :
                    petty.append([0,0,{
                                     'name':x.name, 
                                     'date':x.date,                                                                   
                                     'branch_destination_id':x.branch_destination_id.id,
                                     'amount_real':x.amount_real,
                    }])   
            return {'value':{'pettycash_ids': petty}}        

    @api.multi
    def approve(self):
        pettycash = self.env['wtc.pettycash']
        cash = ''
        for x in self.pettycash_ids :
            cash += ('- '+str(x.name)+'<br/>')
        self.message_post(body=_("Reimbursed Approved <br/> Petty Cash No : <br/>  %s ")%(cash))                             
        self.state = 'approved'
        self.date_approve = self._get_default_date()

    @api.multi
    def sent_to_draft(self):
        if self.state not in ('request','approved'):
            raise osv.except_osv(('Perhatian !'), ("State sudah %s" %(self.state)))
        self.message_post(body=("Reimbursed Sent to Draft"))
        self.state = 'draft'
        
    @api.cr_uid_ids_context        
    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        reimbursed = self.browse(cr,uid,ids)
        petty = vals.get('pettycash_ids', False)
        delcash = ''
        if petty :
            del[vals['pettycash_ids']]
            for x,item in enumerate(petty) :
                pettycash = self.pool.get('wtc.pettycash')
                petty_id = item[1]

                if item[0] == 2 :
                    pettycash_search = pettycash.search(cr,uid,[
                       ('id','=',petty_id)
                       ])
                    if not pettycash_search :
                        raise osv.except_osv(('Perhatian !'), ("Petty Cash tidak ada didalam daftar"))
                    pettycash_browse = pettycash.browse(cr,uid,pettycash_search)
                    pettycash_browse.write({
                                   'reimbursed_id':False,
                                   'state':'posted'
                                     })
                    delcash += ('- '+str(pettycash_browse.name)+'<br/>')
                elif item[0] == 0 :
                    values = item[2]
                    pettycash_search = pettycash.search(cr,uid,[
                                                        ('name','=',values['name'])
                                                        ])
                    if not pettycash_search :
                        raise osv.except_osv(('Perhatian !'), ("Petty Cash tidak ada didalam daftar Engine Nomor"))
            
                
                    pettycash_browse = pettycash.browse(cr,uid,pettycash_search)
                    pettycash_browse.write({
                                      'reimbursed_id':reimbursed.id
                                      })
            if delcash :
                self.message_post(cr, uid, reimbursed.id, body=_("Delete Petty Cash No <br/> %s")%(delcash), context=context)                               
                
        return super(wtc_reimbursed, self).write(cr, uid, ids, vals, context=context) 

    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Reimbursed Petty Cash sudah diproses, data tidak bisa didelete !"))

            for line in item.pettycash_ids:
                if line.reimbursed_id:
                    line.write({'reimbursed_id':False,'state':'posted'})
                    
        return super(wtc_reimbursed, self).unlink(cr, uid, ids, context=context)        