import itertools
from lxml import etree
from datetime import datetime, timedelta
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import openerp.addons.decimal_precision as dp
from openerp.osv import osv

class wtc_faktur_pajak(models.Model):
    
    _name = "wtc.faktur.pajak"
    _description = "Faktur Pajak"
    _order = "id asc"
         
    @api.multi
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date()
             
    name = fields.Char(string='Faktur Pajak')
    date = fields.Date(string='Date',required=True,default=_get_default_date)
    prefix = fields.Char(string='Prefix',required=True)
    counter_start = fields.Integer(string ='Counter Start',required=True,default=1)
    counter_end = fields.Integer(string ='Counter End',required=True,default=2)
    padding = fields.Integer(string='Padding',required=True,default=8)
    state = fields.Selection([
                              ('draft','Draft'),
                              ('posted','Posted'),
                              ],default='draft')
    faktur_pajak_ids = fields.One2many('wtc.faktur.pajak.out','faktur_pajak_id',readonly=True)
    confirm_uid = fields.Many2one('res.users',string="Posted by")
    confirm_date = fields.Datetime('Posted on')
    thn_penggunaan = fields.Integer(string="Tahun Penggunaan")
    tgl_terbit = fields.Date(string="Tgl Terbit")    
    no_document = fields.Char('No Document')
    
    @api.model
    def create(self,values,context=None):
        vals = []
       
        values['name'] = self.env['ir.sequence'].get_sequence('FP')
        values['date'] = self._get_default_date()
        if len(str(values.get('thn_penggunaan','1'))) < 4 or len(str(values.get('thn_penggunaan','1'))) > 4 :
            raise osv.except_osv(('Perhatian !'), ("Tahun Pembuatan harus 4 digit !"))
        faktur_pajak = super(wtc_faktur_pajak,self).create(values)       
        return faktur_pajak
    
    @api.onchange('thn_penggunaan')
    def onchange_tahun_penggunaan(self):
        warning = {}        
        if self.thn_penggunaan :
            tahun = len(str(self.thn_penggunaan))
            if tahun > 4 or tahun < 4 :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('Tahun hanya boleh 4 digit ! ')),
                }
                self.thn_penggunaan = False                
        return {'warning':warning} 
    
    @api.multi
    def action_post(self):
        vals = []
        self.write({'date':self._get_default_date(),'state':'posted','confirm_uid':self._uid,'confirm_date':datetime.now()})        
        padding ="{0:0"+str(self.padding)+"d}"
        for number in range(self.counter_start,self.counter_end+1):
            vals.append([0,0,{
                        'name': self.prefix+padding.format(number),
                        'state': 'open',
                        'thn_penggunaan' : self.thn_penggunaan,
                        'tgl_terbit' : self.tgl_terbit,
                                    }])
            
        self.write({'faktur_pajak_ids': vals})        
        
        return True
        
   
    @api.onchange('counter_start','counter_end')
    def counter_start_change(self):
        if self.counter_start <= 0:
            self.counter_start = 1
            self.counter_end = self.counter_start+1
            return {'warning':{'title':'Perhatian!','message':'Counter Start harus > 0'}}
        
        if self.counter_end <= self.counter_start:
            self.counter_end = self.counter_start+1
        
        if self.padding <=0:
            return {'warning':{'title':'Perhatian!','message':'Padding harus > 0'}}
    
          
    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Generate Faktur Pajak sudah diproses, data tidak bisa didelete !"))
        return super(wtc_faktur_pajak, self).unlink(cr, uid, ids, context=context) 
            
class wtc_faktur_pajak_out(models.Model):
    _name = 'wtc.faktur.pajak.out'

    @api.cr_uid_ids_context
    def _get_default_company(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.company').search(cr,uid,[]) 
        browse =   self.pool.get('res.company').browse(cr,uid,user_obj)     

        return browse[0].id or False
            
    faktur_pajak_id = fields.Many2one('wtc.faktur.pajak')
    name = fields.Char(string='Faktur Pajak')
    transaction_id = fields.Integer('Transaction ID')
    state = fields.Selection([
                              ('open','Open'),
                              ('close','Closed'),
                              ('print','Printed'),
                              ('cancel','Canceled'),
                              ],default='open')
    untaxed_amount = fields.Float('Untaxed Amount')
    tax_amount = fields.Float('Tax Amount')
    amount_total = fields.Float('Total Amount')
    date = fields.Date('Date')
    partner_id = fields.Many2one('res.partner',string='Partner')
    model_id = fields.Many2one('ir.model',string='Model')
    state_register = fields.Selection(related='state',string='State')
    pajak_gabungan = fields.Boolean('Pajak Gabungan')
    signature_id = fields.Many2one('wtc.signature',string='Signature By')
    cetak_ke = fields.Integer('Cetak ke')
    company_id = fields.Many2one('res.company',string='Company' )
    thn_penggunaan = fields.Integer(string="Tahun Penggunaan")
    tgl_terbit = fields.Date(string="Tgl Terbit")
    keterangan = fields.Text(string="Keterangan")
    kode_transaksi = fields.Char(string="Kode Transaksi")
    ref = fields.Char(string="Reference")
    branch_id = fields.Many2one('wtc.branch',string='Company' )
    

    
    #,default=lambda self: self.env['res.company']._company_default_get('wtc.faktur.pajak.out') ,,default=_get_default_company   
    _sql_constraints = [
    ('unique_nomor_faktur_pajak', 'unique(name)', 'Nomor Faktur Pajak sudah pernah dibuat !'),
    ]
    
    def get_no_faktur_pajak(self,cr,uid,ids,object,context=None):
        vals = self.pool.get(object).browse(cr,uid,ids)
        thn_penggunaan = 0.0
        faktur_pajak = self.pool.get('wtc.faktur.pajak.out')
        if object == 'dealer.sale.order' :
            thn_penggunaan = int(vals.date_order[:4])
            tgl_terbit = vals.date_order
        elif object == 'wtc.work.order' :
            thn_penggunaan = int(vals.date[:4])
            tgl_terbit = vals.date
        elif object == 'wtc.dn.nc' :
            thn_penggunaan = int(vals.date[:4])
            tgl_terbit = vals.date
        elif object == 'sale.order' :
            thn_penggunaan = int(vals.date_order[:4])
            tgl_terbit = vals.date_order   
        elif object == 'wtc.disposal.asset' :
            thn_penggunaan = int(vals.date[:4])
            tgl_terbit = vals.date 
                     
        no_fp = faktur_pajak.search(cr,uid,[
                                            ('state','=','open'),
                                            ('thn_penggunaan','=',thn_penggunaan),
                                            ('tgl_terbit','<=',tgl_terbit)
                                            ],limit=1,order='id')
        
        if not no_fp and object == 'wtc.account.voucher' :
            raise osv.except_osv(('Perhatian !'), ("Nomor faktur pajak tidak ditemukan, silahkan Generate terlebih dahulu !"))
        if no_fp :
            vals.write({'faktur_pajak_id':no_fp[0]})
            model = self.pool.get('ir.model').search(cr,uid,[
                                                             ('model','=',vals.__class__.__name__)
                                                             ])
            if object == 'dealer.sale.order' :
    
                faktur_pajak.write(cr,uid,no_fp,{'model_id':model[0],
                                                'amount_total':vals.amount_total,
                                                'untaxed_amount':vals.amount_untaxed,
                                                'tax_amount':vals.amount_tax,                                                    
                                                'state':'close',
                                                'date':vals.date_order,
                                                'partner_id':vals.partner_id.id,
                                                'transaction_id' : vals.id,
                                                'company_id':1,
                                                'ref':vals.name,
                                                'branch_id':vals.branch_id.id,
                                                        })   
            elif object == 'wtc.work.order' :
               
                customer_id = False
                if vals.type in ('KPB', 'CLA') :
                    customer_id = vals.branch_id.default_supplier_id.id 
                else :
                    customer_id = vals.customer_id.id

                faktur_pajak.write(cr,uid,no_fp,{'model_id':model[0],
                                                'amount_total':vals.amount_total,
                                                'untaxed_amount':vals.amount_untaxed,
                                                'tax_amount':vals.amount_tax,
                                                'state':'close',
                                                'transaction_id':vals.id,
                                                'date':vals.date,
                                                'partner_id':customer_id,
                                                'company_id':1,
                                                'ref':vals.name,
                                                'branch_id':vals.branch_id.id,
                                                    })    
            
            elif object == 'wtc.account.voucher' :
              
                total = 0.0
                for x in vals.line_cr_ids :
                    total += x.amount
                tax = vals.amount - total
                faktur_pajak.write(cr,uid,no_fp,{'model_id':model[0],
                                                'amount_total':vals.amount,
                                                'untaxed_amount':total ,
                                                'tax_amount':tax,
                                                'state':'close',
                                                'transaction_id':vals.id,
                                                'date':vals.date,
                                                'partner_id':vals.partner_id.id,
                                                'company_id':1,
                                                'ref':vals.number,
                                                'branch_id':vals.branch_id.id,
                                                        }) 
            elif object == 'sale.order' :

                faktur_pajak.write(cr,uid,no_fp,{'model_id':model[0],
                                                'amount_total':vals.amount_total,
                                                'untaxed_amount':vals.amount_untaxed,
                                                'tax_amount':vals.amount_tax,                                                    
                                                'state':'close',
                                                'transaction_id':vals.id,
                                                'date':vals.date_order,
                                                'partner_id':vals.partner_id.id,
                                                'company_id':1,
                                                'ref':vals.name,
                                                'branch_id':vals.branch_id.id,
                                                    })       
            elif object == 'wtc.disposal.asset' :
                
                faktur_pajak.write(cr,uid,no_fp,{'model_id':model[0],
                                                'amount_total':vals.amount_total,
                                                'untaxed_amount':vals.amount_untaxed,
                                                'tax_amount':vals.amount_tax,                                                    
                                                'state':'close',
                                                'transaction_id':vals.id,
                                                'date':vals.date,
                                                'partner_id':vals.partner_id.id,
                                                'company_id':1,
                                                'ref':vals.name,
                                                'branch_id':vals.branch_id.id,
                                                    })
            elif object == 'wtc.dn.nc' :
                
                faktur_pajak.write(cr,uid,no_fp,{'model_id':model[0],
                                                'amount_total':vals.amount,
                                                'untaxed_amount':vals.untaxed_amount,
                                                'tax_amount':vals.tax_amount,                                                    
                                                'state':'close',
                                                'transaction_id':vals.id,
                                                'date':vals.date,
                                                'partner_id':vals.partner_id.id,
                                                'company_id':1,
                                                'ref':vals.number,
                                                'branch_id':vals.branch_id.id,
                                                    })                       
        return True
        
    @api.cr_uid_ids_context
    def signature_change(self,cr,uid,ids,signature,context=None):
        vals = self.browse(cr,uid,ids)
        company  = self.pool.get('res.company')._company_default_get(cr,uid,ids,'wtc.faktur.pajak.out') or 1
        vals.write({'company_id':company})
        
    def print_faktur_pajak(self,cr,uid,ids,context=None):  
        res = self.browse(cr,uid,ids)

        if not res.partner_id.pkp :
                raise osv.except_osv(('Perhatian !'), ("Customer non PKP !"))
        obj_ir_view = self.pool.get("ir.ui.view")
        obj_ir_view_search= obj_ir_view.search(cr,uid,[("name", "=", 'wtc.faktur.pajak.out.wizard'), ("model", "=", 'wtc.faktur.pajak.out')])
        obj_ir_view_browse = obj_ir_view.browse(cr,uid,obj_ir_view_search)
            
        return {
            'name': 'Faktur Pajak',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.faktur.pajak.out',
            'type': 'ir.actions.act_window',
            'view_id' : obj_ir_view_browse.id,
            'target': 'new',
            'nodestroy': True,
            'res_id': res.id,
            'context': context
            }    
        
    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        raise osv.except_osv(('Perhatian !'), ("Tidak Boleh menghapus faktur pajak !"))
        return super(wtc_faktur_pajak, self).unlink(cr, uid, ids, context=context)         