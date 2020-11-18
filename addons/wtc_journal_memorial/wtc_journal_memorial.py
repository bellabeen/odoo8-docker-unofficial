import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp import SUPERUSER_ID
from lxml import etree

class wtc_journal_memorial(models.Model):
    _name = 'wtc.journal.memorial'
    _description = 'Journal Memorial'
    _order = 'date desc'

    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('waiting_for_approval','Waiting For Approval'),
        ('confirm','Confirmed'),
        ('cancel','Cancelled')
    ]

    @api.one
    @api.depends('journal_memorial_line.amount')
    def _compute_debit(self):
        total_debit = 0.0
        for x in self.journal_memorial_line :
            if x.type == 'Dr' :
                total_debit += x.amount
        self.total_debit = total_debit

    @api.one
    @api.depends('journal_memorial_line.amount')
    def _compute_credit(self):
        total_credit = 0.0
        for x in self.journal_memorial_line :
            if x.type == 'Cr' :
                total_credit += x.amount
        self.total_credit = total_credit
                    
    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
    
    @api.cr_uid_ids_context
    def _get_default_periode(self,cr,uid,ids,context=None):
        periode_obj = self.pool.get('account.period')
        periode_now = periode_obj.search(cr,uid,[
                                      ('date_start','<=',self._get_default_date(cr,uid,context=context)),
                                      ('date_stop','>=',self._get_default_date(cr,uid,context=context)),
                                      ])  
        periode_id = False
        if periode_now :
            periode_id = periode_obj.browse(cr,uid,periode_now).id                     
        return periode_id 
            
    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()
                
    name = fields.Char(string='No')
    branch_id = fields.Many2one('wtc.branch', string='Branch', required=True, default=_get_default_branch)
    date = fields.Date(string="Date",required=True,readonly=True,default=_get_default_date)
    periode_id = fields.Many2one('account.period',string='Periode')
    division = fields.Selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum'),('Finance','Finance')], string='Division',default='Unit', required=True,change_default=True, select=True)
    auto_reverse = fields.Boolean(string="Auto Reverse ?")
    journal_memorial_line = fields.One2many('wtc.journal.memorial.line','journal_memorial_id')
    state= fields.Selection(STATE_SELECTION, string='State', readonly=True,default='draft')
    total_debit = fields.Float(string='Total Debit',digits=dp.get_precision('Account'), store=True,compute='_compute_debit')
    total_credit = fields.Float(string='Total Credit',digits=dp.get_precision('Account'), store=True,compute='_compute_credit')
    move_id = fields.Many2one('account.move', string='Account Entry', copy=False)
    move_ids = fields.One2many('account.move.line',related='move_id.line_id',string='Journal Items', readonly=True)   
    auto_reverse_move_id = fields.Many2one('account.move', string='Account Entry', copy=False)
    auto_reverse_move_ids = fields.One2many('account.move.line',related='auto_reverse_move_id.line_id',string='Auto Reverse Journal Items', readonly=True)   
    prev_periode = fields.Boolean(string="Prev Periode")  
    current_periode_id = fields.Many2one('account.period',string='Current Periode',default=_get_default_periode)
    description = fields.Char(string='Description')
    confirm_uid = fields.Many2one('res.users',string="Confirmed by")
    confirm_date = fields.Datetime('Confirmed on')
    approval_ids = fields.One2many('wtc.approval.line','transaction_id',string="Table Approval",domain=[('form_id','=',_name)])
    approval_state =  fields.Selection([
                                        ('b','Belum Request'),
                                        ('rf','Request For Approval'),
                                        ('a','Approved'),
                                        ('r','Reject')
                                        ],'Approval State', readonly=True,default='b')
    code = fields.Selection([(' ',' '),('cancel','Cancel')],string="Code",default=' ')
    state_periode = fields.Selection(related="periode_id.state")
    cancel_refered = fields.Many2one('wtc.journal.memorial')
    
    @api.onchange('periode_id')
    def onchange_periode(self):
        if self.periode_id :
            if self.periode_id.date_stop > self.date :
                self.prev_periode = True
            else :
                self.prev_periode = False
            
    @api.cr_uid_ids_context    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(wtc_journal_memorial, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        periode_obj = self.pool.get('account.period')
        kolek_periode =[]
        date = self._get_default_date(cr,uid,context=None)
        periode_now = periode_obj.search(cr,uid,[
                                      ('date_start','<=',date),
                                      ('date_stop','>=',date)
                                      ])
        if periode_now :
            periode_id = periode_obj.browse(cr,uid,periode_now)
            kolek_periode.append(periode_id.id)
            prev_periode = periode_obj.search(cr,uid,[
                                               ('date_start','<',date),
                                               ('id','!=',periode_id.id),
                                               ('state','=','draft')
                                               ])
            if prev_periode :
                perv_periode_id2 = periode_obj.browse(cr,uid,prev_periode)
                for x in perv_periode_id2 :
                    kolek_periode.append(x.id)
        
        doc = etree.XML(res['arch'])
        nodes_branch = doc.xpath("//field[@name='periode_id']")
        for node in nodes_branch:
            node.set('domain', '[("id", "in", '+ str(kolek_periode)+')]')
        res['arch'] = etree.tostring(doc)
        return res

    @api.model
    def create(self,vals,context=None):
            
        vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'JM') 
        vals['date'] = self._get_default_date()           
        if not vals.get('journal_memorial_line') :
            raise osv.except_osv(('Perhatian !'), ("Harap isi detail!"))   
            
        res =  super(wtc_journal_memorial, self).create(vals)  
        res.cek_balance()
        return res

    @api.multi
    def write(self,values,context=None):
        res =  super(wtc_journal_memorial,self).write(values)
        self.cek_balance()
        return res
        
    @api.one      
    def cek_balance(self):
        if self.total_debit != self.total_credit :
            raise osv.except_osv(('Perhatian !'), ("Total tidak balance, silahkan periksa kembali !"))   

    @api.multi
    def cancel_memorial(self):
        self.action_create_memorial()
        self.state = 'cancel'
        
    @api.multi
    def action_create_memorial(self):
        memorial_line_vals = []
        memorial_vals = {
                             'branch_id': self.branch_id.id  ,
                             'periode_id': self.periode_id.id ,
                             'description':'Cancel Journal Memorial No %s'%(self.name    )  ,
                             'division' : self.division,
                             'date': self._get_default_date(),
                             'auto_reverse' : self.auto_reverse,
                             'code': 'cancel',
                             'total_debit': self.total_debit,
                             'total_credit' : self.total_credit,
                             'journal_memorial_line':[],
                             }
        for line in self.journal_memorial_line :
            memorial_line_vals.append([0,False,{
                                      'account_id': line.account_id.id,
                                      'amount': line.amount,
                                      'type': 'Dr' if line.type == 'Cr' else 'Cr',
                                      'branch_id':line.branch_id.id,
                                      'partner_id' : line.partner_id.id if line.partner_id else False,
                                      'asset_id':line.asset_id.id if line.asset_id else False,
                                      }])
        memorial_vals['journal_memorial_line'] = memorial_line_vals
        memorial_id = self.sudo().create(memorial_vals)            
        memorial_id.wkf_request_approval()
        self.cancel_refered = memorial_id.id
                                     
    @api.cr_uid_ids_context
    def action_create_move_line(self, cr, uid, ids, context=None):
        
        if context is None:
            context = {}
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        branch_config = self.pool.get('wtc.branch.config')

        ctx = context.copy()
        ctx['novalidate'] = True
        
        for memorial in self.browse(cr, uid, ids, context=context):       
            self.write(cr, uid, memorial.id, {'state': 'confirm','date':self._get_default_date(cr,uid,context=context),'confirm_date':datetime.now(),'confirm_uid':uid})            
            name = memorial.name
            date = memorial.date
            branch_config_journal = branch_config.search(cr,uid,[
                                               ('branch_id','=',memorial.branch_id.id),
                                               ('journal_memorial_journal_id','!=',False)
                                               ])
            if not branch_config_journal :
                raise osv.except_osv(('Perhatian !'), ("Journal Memorial belum diisi dalam master Branch Config !"))  
            branch_journal = branch_config.browse(cr,uid,branch_config_journal)
            journal_id = branch_journal.journal_memorial_journal_id.id            
            amount = memorial.total_credit          
            period_id = memorial.periode_id.id
            reconcile = [] 
            auto_reverse_move_id = False
                                               
            move = {
                'name': name,
                'ref':name,
                'journal_id': journal_id,
                'date': date if period_id == memorial.current_periode_id.id else memorial.periode_id.date_stop,
                'period_id':period_id,
            }
            move_id = move_pool.create(cr, uid, move, context=None)
            
            if memorial.auto_reverse :
                auto_reverse_move = {
                    'name': name,
                    'ref':name,
                    'journal_id': journal_id,
                    'date': date,
                    'period_id':memorial.current_periode_id.id,
                }
                if not memorial.current_periode_id :
                    raise osv.except_osv(('warning !'), ("Make sure you have active period for today!"))
                    
                auto_reverse_move_id = move_pool.create(cr,uid,auto_reverse_move,context) 
                            
            for_name = False
            for_ref= False
            if memorial.auto_reverse :
                for_name = memorial.description + ' (Auto Reverse)'
                for_ref=memorial.name+'R'
            else :
                for_name = memorial.description
                for_ref=memorial.name
                 
            for y in memorial.journal_memorial_line :
                branch_dest = self.pool.get('wtc.branch').browse(cr,uid,[y.branch_id.id])                
                move_line_2 = {
                    'name': _('%s')%(for_name),
                    'ref':for_ref,
                    'account_id': y.account_id.id,
                    'move_id': move_id,
                    'journal_id': journal_id,
                    'period_id': period_id,
                    'date': date if period_id == memorial.current_periode_id.id else memorial.periode_id.date_stop,
                    'debit': y.amount if y.type == 'Dr' else 0.0,
                    'credit': y.amount if y.type == 'Cr' else 0.0,
                    'branch_id' : branch_dest.id,
                    'division' : memorial.division,
                    'partner_id' : y.partner_id.id,
                    'asset_id':y.asset_id.id if y.asset_id else False,                    
                }   
                
                line_id2 = move_line_pool.create(cr, uid, move_line_2, ctx)
                if memorial.auto_reverse :       
                    autoreverse_move_line_2 = {
                        'name': _('%s')%(for_name),
                        'ref':for_ref,
                        'account_id': y.account_id.id,
                        'move_id': auto_reverse_move_id,
                        'journal_id': journal_id,
                        'period_id': memorial.current_periode_id.id,
                        'date': date,
                        'debit': y.amount if y.type == 'Cr' else 0.0,
                        'credit': y.amount if y.type == 'Dr' else 0.0,
                        'branch_id' : branch_dest.id,
                        'division' : memorial.division,
                        'partner_id' : y.partner_id.id,
                        'asset_id':y.asset_id.id if y.asset_id else False,      
                    } 
                    autoreverse_line_id2 = move_line_pool.create(cr,uid,autoreverse_move_line_2,ctx)
                    if y.account_id.type in ('payable','receivable') and y.account_id.reconcile:
                        reconcile.append([line_id2,autoreverse_line_id2])     
                             
                if y.asset_id :
                    self.pool.get('account.asset.asset').compute_depreciation_board(cr,uid,[y.asset_id.id])
                    
            #self.create_intercompany_lines(cr,uid,ids,move_id,context=None) 
            if branch_journal.journal_memorial_journal_id.entry_posted :
                posted = move_pool.post(cr, uid, [move_id], context=None)
            else :
                move_pool.validate(cr, uid, [move_id], context=None)
            
            if memorial.auto_reverse :            
                #self.create_intercompany_lines(cr,uid,ids,auto_reverse_move_id,context=None)  
                if branch_journal.journal_memorial_journal_id.entry_posted :                                     
                    posted2 = move_pool.post(cr, uid, [auto_reverse_move_id], context=None)   
            
            if reconcile :
                for x in reconcile :
                    self.pool.get('account.move.line').reconcile(cr,uid,x)    
            self.write(cr, uid, memorial.id, {'move_id': move_id,'auto_reverse_move_id':auto_reverse_move_id})
        return True

    @api.cr_uid_ids_context   
    def create_intercompany_lines(self,cr,uid,ids,move_id,context=None):
        ##############################################################
        ################# Add Inter Company Journal ##################
        ##############################################################
        
        
        branch_rekap = {}       
        branch_pool = self.pool.get('wtc.branch')        
        vals = self.browse(cr,uid,ids) 
        move_line = self.pool.get('account.move.line')
        move_line_srch = move_line.search(cr,uid,[('move_id','=',move_id)])
        move_line_brw = move_line.browse(cr,uid,move_line_srch)        
        branch = branch_pool.search(cr,uid,[('id','=',vals.branch_id.id)])

        if branch :
            branch_browse = branch_pool.browse(cr,uid,branch)
            inter_branch_header_account_id = branch_browse.inter_company_account_id.id
            if not inter_branch_header_account_id :
                raise osv.except_osv(('Perhatian !'), ("Account Inter Company belum diisi dalam Master branch %s !")%(vals.branch_id.name))

        branch_config_journal = self.pool.get('wtc.branch.config').search(cr,uid,[
                                           ('branch_id','=',vals.branch_id.id),
                                           ('journal_memorial_journal_id','!=',False)
                                           ])
        if not branch_config_journal :
            raise osv.except_osv(('Perhatian !'), ("Journal Memorial belum diisi dalam master Branch Config !"))  
        branch_journal = self.pool.get('wtc.branch.config').browse(cr,uid,branch_config_journal)
        journal_id = branch_journal.journal_memorial_journal_id.id   

        #Grab main entries period (interco entries follow the main entries)
        period_id = False
        #Merge Credit and Debit by Branch                                
        for x in move_line_brw :
            if not period_id :
                period_id = x.period_id and x.period_id.id
            if x.branch_id not in branch_rekap :
                branch_rekap[x.branch_id] = {}
                branch_rekap[x.branch_id]['debit'] = x.debit
                branch_rekap[x.branch_id]['credit'] = x.credit
            else :
                branch_rekap[x.branch_id]['debit'] += x.debit
                branch_rekap[x.branch_id]['credit'] += x.credit  
        #Make account move       
        for key,value in branch_rekap.items() :
            if key != vals.branch_id and value['debit'] != value['credit'] :
        
                inter_branch_detail_account_id = key.inter_company_account_id.id                
                if not inter_branch_detail_account_id :
                    raise osv.except_osv(('Perhatian !'), ("Account Intercompany belum diisi dalam Master branch %s - %s!")%(key.code, key.name))

                balance = value['debit']-value['credit']
                debit = abs(balance) if balance < 0 else 0
                credit = balance if balance > 0 else 0
                
                move_line_create = {
                    'name': _('Interco Journal Memorial %s')%(key.name),
                    'ref':_('Interco Journal Memorial %s')%(key.name),
                    'account_id': inter_branch_header_account_id,
                    'move_id': move_id,
                    'journal_id': journal_id,
                    'period_id': period_id,
                    'date': vals.date,
                    'debit': debit,
                    'credit': credit,
                    'branch_id' : key.id,
                    'division' : vals.division,
                }    
                inter_first_move = move_line.create(cr, uid, move_line_create, context)    
                         
                move_line2_create = {
                    'name': _('Interco Journal Memorial %s')%(vals.branch_id.name),
                    'ref':_('Interco Journal Memorial %s')%(vals.branch_id.name),
                    'account_id': inter_branch_detail_account_id,
                    'move_id': move_id,
                    'journal_id': journal_id,
                    'period_id': period_id,
                    'date': vals.date,
                    'debit': credit,
                    'credit': debit,
                    'branch_id' : vals.branch_id.id,
                    'division' : vals.division,
                }    
                inter_second_move = move_line.create(cr, uid, move_line2_create, context)  
                                                                 
        return True
        
    @api.multi
    def wkf_request_approval(self):
        obj_matrix = self.env["wtc.approval.matrixbiaya"]
        if self.code == 'cancel' :
            obj_matrix.request_by_value(self, self.total_credit,code=self.code)
        else :
            obj_matrix.request_by_value(self, self.total_credit)

        self.state =  'waiting_for_approval'
        self.approval_state = 'rf'
        branch_config_journal = self.env['wtc.branch.config'].search([
                                           ('branch_id','=',self.branch_id.id),
                                           ('journal_memorial_journal_id','!=',False)
                                           ])
        if not branch_config_journal :
            raise osv.except_osv(('Perhatian !'), ("Journal Memorial belum diisi dalam master Branch Config !")) 
                
    @api.multi      
    def wkf_approval(self):
        if not self.journal_memorial_line :
            raise osv.except_osv(('Perhatian !'), ("Detail belum diisi. Data tidak bisa di save."))       
        approval_sts = self.env['wtc.approval.matrixbiaya'].approve(self)
        if approval_sts == 1:
            self.write({'date':self._get_default_date(),'approval_state':'a'})
            self.action_create_move_line()
        elif approval_sts == 0:
                raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group Approval"))    
            
    @api.multi
    def has_approved(self):
       
        if self.approval_state == 'a':
            return True
        
        return False
    
    @api.multi
    def has_rejected(self):
        
        if self.approval_state == 'r':
            self.write({'state':'draft'})
            return True
        return False
    
    @api.one
    def wkf_set_to_draft(self):
        self.write({'state':'draft','approval_state':'r'})
        
    @api.cr_uid_ids_context    
    def view_jm(self,cr,uid,ids,context=None):  
        val = self.browse(cr, uid, ids, context={})[0]
        return {
            'name': 'Journal Memorial',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.journal.memorial',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': val.cancel_refered.id
            }        
                            
    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Journal Memorial tidak bisa didelete !"))
        return super(wtc_journal_memorial, self).unlink(cr, uid, ids, context=context) 
                                
class wtc_journal_memorial_line(models.Model):
    _name = 'wtc.journal.memorial.line'
    _rec_name = 'account_id'
        
    account_id = fields.Many2one('account.account',string="Account",domain="[('type','not in',('view','consolidation'))]")
    amount = fields.Float(string="Amount")
    type = fields.Selection([('Dr','Dr'),('Cr','Cr')],string="Dr/Cr")
    journal_memorial_id = fields.Many2one('wtc.journal.memorial')
    branch_id = fields.Many2one('wtc.branch', string='Branch', required=True)   
    partner_id = fields.Many2one('res.partner',string='Partner') 
    asset_id = fields.Many2one('account.asset.asset',string='Asset',domain="[('state','!=','close')]")
    
    @api.onchange('account_id')
    def onchange_account(self):
        domain ={}
        branch_ids_user=self.env['res.users'].browse(self._uid).branch_ids
        branch_ids=[b.id for b in branch_ids_user]
        domain['account_id'] = '["|",("branch_id", "in", '+ str(branch_ids)+'),("branch_id", "=", False),("type","not in",("view","consolidation"))]'        
        if self.account_id :
            if self.account_id.branch_id :
                domain['branch_id'] = '[("id","=",'+str(self.account_id.branch_id.id)+')]'
                self.branch_id = self.account_id.branch_id.id
            else :
                domain['branch_id'] = []
                self.branch_id = False
        return {'domain':domain}   
    
    _sql_constraints = [
    ('unique_name_account_id', 'unique(journal_memorial_id,account_id,branch_id,partner_id)', 'Tidak boleh ada account yang sama dalam satu branch  !'),
] 
    