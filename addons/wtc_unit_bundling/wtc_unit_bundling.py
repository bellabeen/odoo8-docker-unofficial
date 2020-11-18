import time
import base64
from datetime import datetime
from openerp import models, fields, api
from openerp.osv import osv
from openerp.tools.translate import _
import math
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
from openerp import SUPERUSER_ID
from lxml import etree
import openerp.addons.decimal_precision as dp


class wtc_unit_bundling(models.Model):
    _name = "wtc.unit.bundling"
    _description = "Unit Bundling"
    _order = "date desc"
    
    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids
    
    @api.one
    @api.depends('bundling_line.hpp')
    def _compute_amount(self):
        self.amount_total = 0
        val_total = 0
        for x in self.bundling_line :
            val_total += x.hpp+x.freight_cost
        self.amount_total = val_total

    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('waiting_for_approval','Waiting Approval'),
        ('approved', 'Approved'),
        ('done', 'Done'),        
        ('cancel', 'Cancelled'),
        ('reject', 'Rejected'),
    ]
    
    @api.multi
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date()
        
    name = fields.Char('Unit Bundling')
    branch_id = fields.Many2one('wtc.branch', 'Branch',required=True,default=_get_default_branch)
    date = fields.Date('Date',default=_get_default_date,readonly=True)
    division = fields.Selection([
                                 ('Unit','Unit'),
                                 ], 'Division',default='Unit')
    product_id_from = fields.Many2one('product.product',string='Product From',required=True)
    product_id_to = fields.Many2one('product.product',string='Product To',required=True)
    description = fields.Char('Keterangan')
    bundling_line = fields.One2many('wtc.unit.bundling.line', 'bundling_id', 'Bundling Line')
    approval_state =  fields.Selection([
                                        ('b','Belum Request'),
                                        ('rf','Request For Approval'),
                                        ('a','Approved'),
                                        ('r','Reject')
                                        ],'Approval State', readonly=True,default='b')
    approval_ids = fields.One2many('wtc.approval.line', 'transaction_id', string="Table Approval",domain=[('form_id','=',_name)])
    state= fields.Selection(STATE_SELECTION, string='State', readonly=True,default='draft')
    amount_total = fields.Float(string='Total', digits=dp.get_precision('Account'), store=True, compute='_compute_amount')
    confirm_uid = fields.Many2one('res.users', string="Confirmed by")
    confirm_date = fields.Datetime('Confirmed on')
    cancel_uid = fields.Many2one('res.users', string="Rejected by")
    cancel_date = fields.Datetime('Rejected on')

    def create(self, cr, uid, vals, context=None):
        if not vals['bundling_line'] :
            raise osv.except_osv(('Perhatian !'), ("Line Unit Building Belum di Isi !"))
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'UB')
        unit_bundling = super(wtc_unit_bundling, self).create(cr, uid, vals, context=context)
        return unit_bundling
    
    
    @api.multi
    def wkf_request_approval(self):
        obj_matrix = self.env['wtc.approval.matrixbiaya']
        obj_matrix.request(self, 'amount_total')
        self.write({'state':'waiting_for_approval', 'approval_state':'rf'})
        return True
    
    
    @api.multi
    def wkf_approval(self):
        approval_sts = self.env['wtc.approval.matrixbiaya'].approve(self)
        if approval_sts == 1 :
            self.write({'approval_state':'a', 'state':'approved','confirm_uid':self._uid,'confirm_date':datetime.now()})
        elif approval_sts == 0 :
            raise exceptions.ValidationError( ("User tidak termasuk group approval"))
        return True
    
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
    
    @api.cr_uid_ids_context
    def wkf_set_to_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'r'})
    
    @api.cr_uid_ids_context
    def wkf_set_to_draft_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'b'})
        
        
    @api.multi
    def confirm(self):
        for line in  self.bundling_line:
            line.lot_id.sudo().write({'product_id':self.product_id_to.id})
            quant_id = self.env['stock.quant'].sudo().search([('lot_id','=',line.lot_id.id)])
            quant_id.sudo().write({'product_id':self.product_id_to.id})
        return self.write({'state': 'done','confirm_uid':self._uid,'confirm_date':datetime.now(),'date':self._get_default_date()})
                
    
    
    @api.onchange('product_id_from')
    def product_id_from_change(self):
        domain={}
        if self.product_id_from :
            self.bundling_line=False
        categ_ids=self.env['product.category'].get_child_ids('Unit')
        domain['product_id_from']=[('categ_id','in',categ_ids)]
        return {'domain':domain}
    
    @api.onchange('product_id_to')
    def product_id_to_change(self):
        domain={}
        if self.product_id_to :
            self.bundling_line=False
        categ_ids=self.env['product.category'].get_child_ids('Unit')
        domain['product_id_to']=[('categ_id','in',categ_ids)]
        return {'domain':domain}
    
    

class wtc_unit_bundling_line(models.Model):
    _name = "wtc.unit.bundling.line"
    _description = "Unit Bundling Line"

    bundling_id = fields.Many2one('wtc.unit.bundling',string='Bundling')
    lot_id = fields.Many2one('stock.production.lot',string='Engine Number')
    product_id = fields.Many2one('product.product',string='Product')
    name = fields.Char('Desc')
    chassis_number = fields.Char('Chassis Number')
    hpp = fields.Float('HPP')
    freight_cost= fields.Float('Freight cost')
    location_id= fields.Many2one('stock.location',string='Location')
    
    @api.onchange('lot_id')
    def change_lot_id(self):
        domain={}
        if not self.bundling_id.branch_id or not self.bundling_id.product_id_to or not self.bundling_id.product_id_from:
            raise osv.except_osv(('Perhatian !'), ("Branch, Product From atau Product To Belum di Isi !"))
        domain['lot_id']=[('product_id','=',self.bundling_id.product_id_from.id),
            ('branch_id','=',self.bundling_id.branch_id.id),
            ('state','=','stock')]
        if self.lot_id :
            self.chassis_number=self.lot_id.chassis_no
            self.product_id=self.lot_id.product_id.id
            self.name=self.lot_id.product_id.description
            self.location_id=self.lot_id.location_id.id
            self.hpp=self.lot_id.hpp
            self.freight_cost=self.lot_id.freight_cost
        else :
            self.chassis_number = False
            self.product_id = False
            self.name = False
            self.location = False
            self.hpp = False
            self.freight_cost = False
        return {'domain':domain }
    
    
    
class wtc_reject_approval_unit_bundling(models.TransientModel):
    _name = "wtc.reject.approval.unit.bundling"
     
    reason = fields.Text('Reason')
     
    @api.multi
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date()     
    
    @api.multi
    def wtc_reject_approval(self, context=None):
        user = self.env['res.users'].browse(self)['group_id']
        unit_bunlind_id = context.get('active_id',False) #When you call any wizard then in this function ids parameter contain the list of ids of the current wizard record. So, to get the purchase order ID you have to get it from context.
        
        line = self.env['wtc.unit_bundling'].browse(unit_bunlind_id,context=context)
        objek = False
        for x in line.approval_ids :
            for y in user :
                    if y == x.group_id :
                        objek = True
                        for z in line.approval_ids :
                            if z.reason == False :
                                z.write({
                                        'reason':self.reason,
                                        'value':line.amount_total,
                                        'sts':'3',
                                        'pelaksana_id':self.uid,
                                        'tanggal':self._get_default_date()
                                        })
         
                                self.env['wtc.unit_bundling'].write({'state':'confirm','approval_state':'r'})
        if objek == False :
            raise exceptions.ValidationError("User tidak termasuk group approval")
        
        return True     
    