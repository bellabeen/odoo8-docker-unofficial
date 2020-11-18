import itertools
from lxml import etree
from datetime import datetime, timedelta
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import openerp.addons.decimal_precision as dp
from openerp.osv import osv

class dealer_pengembalian_spk(models.Model):
    
    
    _name = 'dealer.pengembalian.spk'
    _description = "Pengembalian SPK Dealer"
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
            
    branch_id = fields.Many2one('wtc.branch',string='Branch',required=True, default=_get_default_branch)
    sales_id = fields.Many2one('res.users',string='Salesman',required=True)
    date = fields.Date(string='Date',required=True,default=_get_default_date)
    pengembalian_spk_ids = fields.One2many('dealer.pengembalian.spk.line','pengembalian_spk_id',ondelete='cascade')
    state = fields.Selection([
                              ('draft','Draft'),
                              ('posted','Posted'),
                              ],default='draft')
    confirm_uid = fields.Many2one('res.users',string="Posted by")
    confirm_date = fields.Datetime('Posted on')
    
    @api.onchange('branch_id','sales_id')
    def onchange_branch_sales(self):
        if self.branch_id and self.sales_id:
            register = []
            spk = self.env['dealer.register.spk.line'].search([
                                                               ('branch_id','=',self.branch_id.id),
                                                               ('sales_id','=',self.sales_id.id),
                                                               ('state','=','open')
                                                               ])
            for no_register in spk:
                register.append([0,0,{
                                     'dealer_register_spk_line_id': no_register.id,
                                     'is_damaged': True
                                     }])
                
            self.pengembalian_spk_ids = register
            
    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Dealer Pengembalian SPK sudah diproses, data tidak bisa didelete !"))
        return super(dealer_pengembalian_spk, self).unlink(cr, uid, ids, context=context) 

    @api.model
    def create(self,values,context=None):
        vals = {}
        values['date'] = datetime.today()
        dealer_kembali_spks = super(dealer_pengembalian_spk,self).create(values)
                
        return dealer_kembali_spks
        
class dealer_pengembalian_spk_line(models.Model):
    _name = 'dealer.pengembalian.spk.line'
    
    pengembalian_spk_id = fields.Many2one('dealer.pengembalian.spk')
    dealer_register_spk_line_id = fields.Many2one('dealer.register.spk.line',string='No. Register')
    is_damaged = fields.Boolean(string='Rusak?',default=True)
    _sql_constraints = [
    ('unique_dealer_register_spk_line', 'unique(dealer_register_spk_line_id)', 'Nomor register sudah pernah dikembalikan !'),
    ]
    
    @api.multi
    def onchange_register_spk(self,branch_id):
        dom = {}
        tampung = []
        if branch_id:
            register_ids = self.env['dealer.register.spk'].search([('branch_id','=',branch_id)])
            dom['dealer_register_spk_line_id']=[('register_spk_id','in',[x['id'] for x in register_ids]),('state','=','open')]
        return {'domain':dom}
    
class dealer_reason_pengembalian_spk_cancel(models.TransientModel):
    _name = "dealer.reason.pengembalian.spk.cancel"
   
    reason = fields.Text('Reason')
    
    @api.multi
    def action_post_cancel(self, context=None):
        pengembalian_id = context.get('active_id',False) #When you call any wizard then in this function ids parameter contain the list of ids of the current wizard record. So, to get the purchase order ID you have to get it from context.
        
        pengembalian_obj = self.env['dealer.pengembalian.spk'].browse(pengembalian_id)
        
        
        for pengembalian_line in pengembalian_obj.pengembalian_spk_ids:
            if pengembalian_line.is_damaged==True:
                pengembalian_line.dealer_register_spk_line_id.write({'state':'cancelled','reason_kembali':self.reason})
            else:
                pengembalian_line.dealer_register_spk_line_id.write({'state':'open','sales_id':False,'tanggal_distribusi':False})
            pengembalian_line.dealer_register_spk_line_id.tanggal_kembali=datetime.now()
        
        pengembalian_obj.state='posted'  
        pengembalian_obj.confirm_uid=self._uid
        pengembalian_obj.date=datetime.today()
        pengembalian_obj.confirm_date= datetime.now()                               
        return True    
    
    