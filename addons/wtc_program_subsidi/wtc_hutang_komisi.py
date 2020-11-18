import itertools
from lxml import etree
from datetime import datetime, timedelta
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import openerp.addons.decimal_precision as dp
from openerp.osv import osv

class wtc_hutang_komisi(models.Model):
    _name = "wtc.hutang.komisi"
    _description = "Hutang Komisi"
    _order = "id asc"
    
    @api.multi
    def _get_max_hc(self):
        nilai_max = 0.0
        if not self.hutang_komisi_line:
            self.nilai_komisi=nilai_max
        for line in self.hutang_komisi_line :
            if nilai_max < line.amount :
                nilai_max = line.amount
            self.nilai_komisi=nilai_max

    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
    
    branch_id = fields.Many2one('wtc.branch','Branch', required=True, default=_get_default_branch)
    division=fields.Selection([('Unit','Unit')], 'Division', change_default=True, select=True,required=True,default='Unit')                     
    
    name=fields.Char("Name", size=30,required=True)
    date_start=fields.Date("Date Start",required=True)
    date_end=fields.Date("Date End",required=True)
    keterangan=fields.Text("Keterangan")
    tipe_komisi=fields.Selection([('fix','Fix'),('non','Non Fix')], "Tipe Komisi", change_default=True, select=True,required=True)                  
    state = fields.Selection([('draft', 'Draft'),
                              ('waiting_for_approval','Waiting For Approval'), 
                              ('approved', 'Approved'),
                              ('rejected','Rejected'),
                              ('editable','Editable'),
                              ('on_revision','On Revision')], 'State', default='draft',readonly=True)
    hutang_komisi_line = fields.One2many('wtc.hutang.komisi.line','hutang_komisi_id')
    area_id = fields.Many2one('wtc.area',string='Area',required=True)
    active = fields.Boolean('Active', default=True)
    nilai_komisi = fields.Float(string='Nilai Hutang Komisi',compute="_get_max_hc")
    confirm_uid = fields.Many2one('res.users',string="Approved by")
    confirm_date=fields.Datetime('Approved on')
    cancel_uid=fields.Many2one('res.users',string="Cancelled by")
    cancel_date=fields.Datetime('Cancelled on')    
    
    @api.multi
    def copy(self, default=None, context=None):
        hutang_komisi_line = []
        if default is None:
            default = {}
        
        start_date = datetime.strptime(self.date_start,'%Y-%m-%d') + timedelta(days=1)
        end_date = datetime.strptime(self.date_start,'%Y-%m-%d') + timedelta(days=2)
        default.update({
                        'branch_id': self.branch_id.id,
                        'division': self.division,
                        'area_id': self.area_id.id,
                        'name': self.name,
                        'date_start': start_date,
                        'date_end': end_date,
                        'keterangan': self.keterangan,
                        'tipe_komisi':self.tipe_komisi,              
                        'state': 'draft',
                        'active': True,
                        'approval_state': 'b',
                        })
        for lines in self.hutang_komisi_line:
            hutang_komisi_line.append([0,False,{
                                          'product_template_id':lines.product_template_id.id,
                                        'amount':lines.amount,
                                        
                                          }])
        default.update({'hutang_komisi_line':hutang_komisi_line})
                
        return super(wtc_hutang_komisi, self).copy(default=default, context=context)
    
    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Hutang Komisi sudah diproses, data tidak bisa didelete !"))
        return super(wtc_hutang_komisi, self).unlink(cr, uid, ids, context=context)     
    
class wtc_hutang_komisi_line(models.Model):
    _name = "wtc.hutang.komisi.line"
    _description = "Hutang Komisi Line"
    _order = "id asc"
    
    hutang_komisi_id = fields.Many2one('wtc.hutang.komisi',ondelete='cascade')
    product_template_id = fields.Many2one('product.template','Product Template')
    amount = fields.Float('Amount')
    
    _sql_constraints = [
    ('unique_product_hc', 'unique(hutang_komisi_id,product_template_id)', 'Tidak boleh ada produk yg sama didalam satu master hutang komisi !'),
    ]
    
    @api.onchange('product_template_id')
    def _get_domain_product_type(self):
        domain = {} 
        categ_ids = self.env['product.category'].get_child_ids('Unit')
        domain['product_template_id'] = [('type','!=','view'),('categ_id','in',categ_ids)]
        return {'domain':domain}      