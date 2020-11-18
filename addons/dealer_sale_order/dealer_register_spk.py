import itertools
from lxml import etree
from datetime import datetime, timedelta
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import openerp.addons.decimal_precision as dp
from openerp.osv import osv

class dealer_register_spk(models.Model):
    
    _name = "dealer.register.spk"
    _description = "Register SPK Dealer"
    _order = "id asc"

    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
        
    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()
            
    name = fields.Char(string='Register SPK')
    date = fields.Date(string='Date',required=True,default=_get_default_date)
    branch_id = fields.Many2one('wtc.branch', string ='Branch',required=True, default=_get_default_branch)
    prefix = fields.Char(string='Prefix',required=True)
    nomor_awal = fields.Integer(string ='Nomor Awal',required=True,default=1)
    nomor_akhir = fields.Integer(string ='Nomor akhir',required=True,default=2)
    padding = fields.Integer(string='Padding',required=True,default=8)
    state = fields.Selection([
                              ('draft','Draft'),
                              ('posted','Posted'),
                              ],default='draft')
    register_spk_ids = fields.One2many('dealer.register.spk.line','register_spk_id',readonly=True,ondelete='cascade')
    confirm_uid = fields.Many2one('res.users',string="Posted by")
    confirm_date = fields.Datetime('Posted on')    
    
    @api.model
    def create(self,values,context=None):
        vals = {}
        values['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'REG/SPK')
        values['date'] = datetime.today()
        dealer_register_spks = super(dealer_register_spk,self).create(values)
                
        return dealer_register_spks
    
    @api.multi
    def action_post(self):
        self.write({'date':self._get_default_date(),'register_spk_ids': vals,'state':'posted','confirm_uid':self._uid,'confirm_date':datetime.now()})        
        vals = []
        padding ="{0:0"+str(self.padding)+"d}"
        for number in range(self.nomor_awal,self.nomor_akhir+1):
            vals.append([0,0,{
                        'name': self.prefix+padding.format(number),
                        'state': 'open',
                        'branch_id': self.branch_id.id
                                  }])
       
        return True
        
   
    @api.onchange('nomor_awal','nomor_akhir','branch_id')
    def nomor_awal_change(self):
        if self.nomor_awal <= 0:
            self.nomor_awal = 1
            self.nomor_akhir = self.nomor_awal+1
            return {'warning':{'title':'Perhatian!','message':'Nomor awal harus > 0'}}
        
        if self.nomor_akhir <= self.nomor_awal:
            self.nomor_akhir = self.nomor_awal+1
            
        if self.padding <=0:
            return {'warning':{'title':'Perhatian!','message':'Padding harus > 0'}}
        
        if self.branch_id:
            self.prefix=self.prefix=self.branch_id.doc_code+"/SPK/"
            
    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Dealer Register SPK sudah diproses, data tidak bisa didelete !"))
        return super(dealer_register_spk, self).unlink(cr, uid, ids, context=context)           
        
class dealer_register_spk_line(models.Model):
    
    _name = 'dealer.register.spk.line'
    #_inherit = ['mail.thread']
    
    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
    
    register_spk_id = fields.Many2one('dealer.register.spk')
    name = fields.Char(string='No. Register')
    branch_id = fields.Many2one('wtc.branch',string='Branch', default=_get_default_branch)
    state = fields.Selection([
                              ('draft','Draft'),
                              ('open','Open'),
                              ('spk','SPK'),
                              ('so','SO'),
                              ('cancelled','Cancelled')
                              ],default='draft')
    state_register = fields.Selection(related='state',string='State')
    tanggal_distribusi= fields.Date(string='Tanggal Distribusi')
    tanggal_kembali = fields.Date(string='Tanggal Kembali')
    sales_id = fields.Many2one('res.users',string='Salesman')
    spk_id = fields.Many2one('dealer.spk',string ='SPK')
    dealer_sale_order_id = fields.Many2one('dealer.sale.order',string='Dealer Sale Order')
    reason_kembali = fields.Text('Reason Pengembalian SPK')
    
    _sql_constraints = [
    ('unique_nomor_register', 'unique(name)', 'Nomor register sudah pernah dibuat !'),
    ]