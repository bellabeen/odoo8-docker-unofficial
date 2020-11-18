import itertools
from lxml import etree
from datetime import datetime, timedelta
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import openerp.addons.decimal_precision as dp
from openerp.osv import osv
import time


class wtc_faktur_pajak_gabungan(models.Model):
    _name = "wtc.faktur.pajak.gabungan"
    _description = "Faktur Pajak Gabungan"


    def print_report_pdf(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = self.read(cr, uid, ids,context=context)[0]

        return self.pool['report'].get_action(cr, uid, [], 'wtc_faktur_pajak.wtc_faktur_pajak_gabungan_report', data=data, context=context)


    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 

    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancel','Cancelled')
    ]
    
    @api.multi
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date()
                
    name = fields.Char(string="Name",readonly=True,default='')
    branch_id = fields.Many2one('wtc.branch', string='Branch', required=True, default=_get_default_branch)
    state= fields.Selection(STATE_SELECTION, string='State', readonly=True,default='draft')
    date = fields.Date(string="Date",required=True,readonly=True,default=_get_default_date)
    pajak_gabungan_line = fields.One2many('wtc.faktur.pajak.gabungan.line','pajak_gabungan_id')
    faktur_pajak_id = fields.Many2one('wtc.faktur.pajak.out',string='No Faktur Pajak',domain="[('state','=','open')]")
    start_date = fields.Date(string="Transaction Date")
    end_date = fields.Date(string="End Date")
    customer_id = fields.Many2one('res.partner',string="Customer",domain="[('customer','!=',False)]")
    division = fields.Selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum'),('Finance','Finance')], string='Division',default='Unit', required=True,change_default=True, select=True)
    confirm_uid = fields.Many2one('res.users',string="Posted by")
    confirm_date = fields.Datetime('Posted on')
    cancel_uid = fields.Many2one('res.users',string="Cancelled by")
    cancel_date = fields.Datetime('Cancelled on')
    remark = fields.Char('Remark')  
    date_pajak = fields.Date(string='Tanggal Faktur Pajak') 

    @api.onchange('end_date')
    def onchange_date(self):
        warning = {}
        if self.end_date and self.start_date :
            if self.start_date >= self.end_date :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (("End Date tidak boleh kurang dari Start Date")),
                }   
                self.end_date = False
        return {'warning':warning}

    
    @api.multi
    def action_generate(self):
        work_order = self.env['wtc.work.order']
        other_receivable = self.env['wtc.account.voucher'] #type Sales
        sales_order = self.env['dealer.sale.order']
        sales_order_md = self.env['sale.order']
        disposal_asset = self.env['wtc.disposal.asset']
        
        pajak_line = self.env['wtc.faktur.pajak.gabungan.line']
        
        so_data = sales_order.search([
                                     ('branch_id','=',self.branch_id.id),
                                     ('state','in',('approved','progress','done')),
                                     ('pajak_gabungan','=',True),
                                     ('faktur_pajak_id','=',False),
                                     ('partner_id','=',self.customer_id.id),
                                     ('division','=',self.division),'|',
                                     ('date_order','>=',self.start_date),
                                     ('date_order','<=',self.end_date),
                                     ])

        wo_data = work_order.search([
                                     ('branch_id','=',self.branch_id.id),
                                     ('state','in',('confirmed','approved','finished','open','done')),
                                     ('pajak_gabungan','=',True),
                                     ('faktur_pajak_id','=',False),
                                     ('customer_id','=',self.customer_id.id),
                                     ('division','=',self.division),'|',
                                     ('date','>=',self.start_date),
                                     ('date','<=',self.end_date),
                                     ]) 
        
        or_data = other_receivable.search([
                                     ('branch_id','=',self.branch_id.id),
                                     ('state','in',('proforma','posted')),
                                     ('pajak_gabungan','!=',False),
                                     ('type','=','sale'),
                                     ('faktur_pajak_id','=',False),
                                    ('partner_id','=',self.customer_id.id),
                                    ('division','=',self.division),'|',
                                    ('date','>=',self.start_date),
                                    ('date','<=',self.end_date),
                                     ])  
        
        so_md_data = sales_order_md.search([
                                     ('branch_id','=',self.branch_id.id),
                                     ('state','in',('progress','manual','done')),
                                     ('pajak_gabungan','=',True),
                                     ('faktur_pajak_id','=',False),
                                     ('partner_id','=',self.customer_id.id),
                                     ('division','=',self.division),'|',
                                     ('date_order','>=',self.start_date),
                                     ('date_order','<=',self.end_date),
                                     ])

        da_data = disposal_asset.search([
                                     ('branch_id','=',self.branch_id.id),
                                     ('state','in',('confirmed','approved')),
                                     ('pajak_gabungan','=',True),
                                     ('faktur_pajak_id','=',False),
                                     ('partner_id','=',self.customer_id.id),
                                     ('division','=',self.division),'|',
                                     ('date','>=',self.start_date),
                                     ('date','<=',self.end_date),
                                     ]) 
                
                
        rekap = {}
        if so_data :
            for x in so_data :
                if not rekap.get(str(x.name)) :
                    rekap[str(x.name)] = {}                
                    rekap[str(x.name)]['date'] = x.date_order
                    rekap[str(x.name)]['total_amount'] = x.amount_total
                    rekap[str(x.name)]['untaxed_amount'] = x.amount_untaxed
                    rekap[str(x.name)]['tax_amount'] = x.amount_tax
                    rekap[str(x.name)]['model'] = 'dealer.sale.order'
        
        if wo_data :
            for x in wo_data :
                if not rekap.get(str(x.name)) :
                    rekap[str(x.name)] = {}      
                    rekap[str(x.name)]['date'] = x.date
                    rekap[str(x.name)]['total_amount'] = x.amount_total
                    rekap[str(x.name)]['untaxed_amount'] = x.amount_untaxed
                    rekap[str(x.name)]['tax_amount'] = x.amount_tax   
                    rekap[str(x.name)]['model'] = 'wtc.work.order' 
        
        if or_data :
            for x in or_data :
                if not rekap.get(str(x.number)) :
                    rekap[str(x.number)] = {}                
                    rekap[str(x.number)]['date'] = x.date
                    rekap[str(x.number)]['total_amount'] = x.amount
                    rekap[str(x.number)]['untaxed_amount'] = x.untaxed_amount
                    rekap[str(x.number)]['tax_amount'] = x.tax_amount   
                    rekap[str(x.number)]['model'] = 'wtc.account.voucher' 
        
        if so_md_data :
            for x in so_md_data :
                if not rekap.get(str(x.name)) :
                    rekap[str(x.name)] = {}                
                    rekap[str(x.name)]['date'] = x.date_order
                    rekap[str(x.name)]['total_amount'] = x.amount_total
                    rekap[str(x.name)]['untaxed_amount'] = x.amount_untaxed
                    rekap[str(x.name)]['tax_amount'] = x.amount_tax
                    rekap[str(x.name)]['model'] = 'sale.order'
                            
        if rekap :
            for x,y in rekap.items() :
                pajak_line.create({
                                   'name':x,
                                   'model':y['model'],
                                   'pajak_gabungan_id':self.id,
                                   'date':y['date'],
                                   'total_amount':y['total_amount'],
                                   'untaxed_amount':y['untaxed_amount'],
                                   'tax_amount':y['tax_amount'],
                                   'model':y['model'],
                                   
                                   })
        if da_data :
            for x in da_data :
                if not rekap.get(str(x.name)) :
                    rekap[str(x.name)] = {}      
                    rekap[str(x.name)]['date'] = x.date
                    rekap[str(x.name)]['total_amount'] = x.amount_total
                    rekap[str(x.name)]['untaxed_amount'] = x.amount_untaxed
                    rekap[str(x.name)]['tax_amount'] = x.amount_tax   
                    rekap[str(x.name)]['model'] = 'wtc.disposal.asset'                 
        if not rekap :
            raise osv.except_osv(('Perhatian !'), ('Data tidak ditemukan !'))  
                
    @api.multi
    def action_confirmed(self):
        self.state = 'confirmed'    
        self.confirm_uid = self._uid
        self.confirm_date = datetime.now() 
        self.date = self._get_default_date()  
        if not self.pajak_gabungan_line :
            raise osv.except_osv(('Perhatian !'), ('Silahkan Generate data terlebih dahulu !'))   
        find_similar = self.search([
                                    ('id','!=',self.id),
                                    ('faktur_pajak_id','=',self.faktur_pajak_id.id),
                                    ('state','!=','draft')
                                    ])
        if find_similar :
            raise osv.except_osv(('Perhatian !'), ('Nomor faktur pajak telah digunakan oleh no %s !')%(find_similar.name)) 
        
        if self.faktur_pajak_id.state != 'open':
            raise osv.except_osv(('Perhatian !'), ('Nomor faktur pajak telah digunakan oleh transaksi lain !'))
        
        work_order = self.env['wtc.work.order']
        other_receivable = self.env['wtc.account.voucher'] #type Sales
        sales_order = self.env['dealer.sale.order'] 
        sales_order_md = self.env['sale.order'] 
        disposal_asset = self.env['wtc.disposal.asset']
        pajak_out = self.env['wtc.faktur.pajak.out'] 
        pajak_id = pajak_out.browse(self.faktur_pajak_id.id)   
        tax_amount = 0.0
        untaxed_amount = 0.0
        total_amount = 0.0
        vals = self.browse(self.id)
        
        for x in self.pajak_gabungan_line :
            tax_amount += x.tax_amount
            untaxed_amount += x.untaxed_amount
            total_amount += x.total_amount
            if x.model == 'wtc.work.order' :
                wo_data = work_order.search([
                                             ('name','=',x.name),
                                             ('faktur_pajak_id','=',False)
                                             ])
                if wo_data :
                    wo_data.write({
                                   'faktur_pajak_id':self.faktur_pajak_id.id
                                   })
                else :
                    raise osv.except_osv(('Perhatian !'), ('Detil dari pajak gabungan (" + %s + ") sudah diproses sebelumnya.')%(x.name))  
            elif x.model == 'dealer.sale.order' :
                so_data = sales_order.search([
                                             ('name','=',x.name),
                                             ('faktur_pajak_id','=',False)
                                             ])
                if so_data :
                    so_data.write({
                                   'faktur_pajak_id':self.faktur_pajak_id.id
                                   })  
                else :
                    raise osv.except_osv(('Perhatian !'), ('Detil dari pajak gabungan (" + %s + ") sudah diproses sebelumnya.')%(x.name))                     
            elif x.model == 'wtc.account.voucher' :
                or_data = other_receivable.search([
                                             ('number','=',x.name),
                                             ('faktur_pajak_id','=',False)
                                             ])
                if or_data :
                    or_data.write({
                                   'faktur_pajak_id':self.faktur_pajak_id.id
                                   })  
                else :
                    raise osv.except_osv(('Perhatian !'), ('Detil dari pajak gabungan (" + %s + ") sudah diproses sebelumnya.')%(x.name))
            elif x.model == 'sale.order' :
                so_md_data = sales_order_md.search([
                                             ('name','=',x.name),
                                             ('faktur_pajak_id','=',False)
                                             ])
                if so_md_data :
                    so_md_data.write({
                                   'faktur_pajak_id':self.faktur_pajak_id.id
                                   })  
                else :
                    raise osv.except_osv(('Perhatian !'), ('Detil dari pajak gabungan (" + %s + ") sudah diproses sebelumnya.')%(x.name))
            elif x.model == 'wtc.disposal.asset' :
                da_data = disposal_asset.search([
                                             ('name','=',x.name),
                                             ('faktur_pajak_id','=',False)
                                             ])
                if da_data :
                    da_data.write({
                                   'faktur_pajak_id':self.faktur_pajak_id.id
                                   })
                else :
                    raise osv.except_osv(('Perhatian !'), ('Detil dari pajak gabungan (" + %s + ") sudah diproses sebelumnya.')%(x.name))                                                 
        model = self.env['ir.model'].search([
                                             ('model','=',vals.__class__.__name__)
                                             ])
        pajak_id.write({
                        'state':'close',
                        'model_id':model.id,
                        'partner_id':self.customer_id.id,
                        'transaction_id':self.id,
                        'date':self.date_pajak,
                        'untaxed_amount':untaxed_amount,
                        'amount_total':total_amount,
                        'tax_amount':tax_amount,
                        'pajak_gabungan':True,
                        'ref':self.name,
                        })
                               
    @api.model
    def create(self,vals,context=None):  
        vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'FPG')     
        vals['date'] = self._get_default_date()                     
        pajak_gab = super(wtc_faktur_pajak_gabungan, self).create(vals)
        return pajak_gab 
    
    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Faktur Pajak Gabungan sudah diproses, data tidak bisa didelete !"))
        return super(wtc_faktur_pajak_gabungan, self).unlink(cr, uid, ids, context=context)     
            
class wtc_faktur_pajak_gabungan_line(models.Model):
    _name = "wtc.faktur.pajak.gabungan.line"
    _description = "Faktur Pajak Gabungan Line"
    
    pajak_gabungan_id = fields.Many2one('wtc.faktur.pajak.gabungan')
    model = fields.Char(string='Object Name')
    name = fields.Char(string="Transaction No")
    date = fields.Date(string='Date')
    total_amount = fields.Float(string="Total Amount")
    untaxed_amount = fields.Float(string="Untaxed Amount")
    tax_amount = fields.Float(string="Tax Amount")