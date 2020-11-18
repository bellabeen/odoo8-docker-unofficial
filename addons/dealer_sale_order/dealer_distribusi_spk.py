import itertools
from lxml import etree
from datetime import datetime, timedelta
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import openerp.addons.decimal_precision as dp
from openerp.osv import osv

class dealer_distribusi_spk(models.Model):
    
    _name = "dealer.distribusi.spk"
    _description = "Distribusi SPK Dealer"
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
        
    branch_id = fields.Many2one('wtc.branch',string='Branch',required=True,default=_get_default_branch)
    sales_id = fields.Many2one('res.users',string='Salesman',required=True)
    date = fields.Date(string='Date',required=True,default=_get_default_date)
    distribusi_spk_ids = fields.One2many('dealer.distribusi.spk.line','distribusi_spk_id',ondelete='cascade')
    state = fields.Selection([
                              ('draft','Draft'),
                              ('posted','Posted'),
                              ],default='draft')
    confirm_uid = fields.Many2one('res.users',string="Posted by")
    confirm_date = fields.Datetime('Posted on')
    
    @api.model
    def create(self,values,context=None):
        vals = {}
        values['date'] = self._get_default_date()
        create_dealer_distribusi_spks = super(dealer_distribusi_spk,self).create(values)
                
        return create_dealer_distribusi_spks
    
    @api.multi
    def action_post(self):
        self.state = 'posted'
        self.confirm_date = datetime.now()
        self.confirm_uid = self._uid
        self.date = self._get_default_date()         
        for distribusi in self.distribusi_spk_ids:
            distribusi.dealer_register_spk_line_id.write({'sales_id':self.sales_id.id,'tanggal_distribusi':datetime.now().strftime('%Y-%m-%d')})     
        return True
    
    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Dealer Distribusi SPK sudah diproses, data tidak bisa didelete !"))
        return super(dealer_distribusi_spk, self).unlink(cr, uid, ids, context=context)    
    
class dealer_distribusi_spk_line(models.Model):
    _name = 'dealer.distribusi.spk.line'
    
    distribusi_spk_id = fields.Many2one('dealer.distribusi.spk')
    dealer_register_spk_line_id = fields.Many2one('dealer.register.spk.line',string='No. Register')
    
    _sql_constraints = [
    ('unique_dealer_register_spk_line', 'unique(dealer_register_spk_line_id)', 'Nomor register sudah pernah didistribusi !'),
    ]
    
    @api.multi
    def onchange_register_spk(self,branch_id):
        dom = {}
        tampung = []
        if branch_id:
            register_ids = self.env['dealer.register.spk'].search([('branch_id','=',branch_id)])
            dom['dealer_register_spk_line_id']=[('register_spk_id','in',[x['id'] for x in register_ids]),('state','=','open'),('sales_id','=',False)]
        return {'domain':dom}
    
    