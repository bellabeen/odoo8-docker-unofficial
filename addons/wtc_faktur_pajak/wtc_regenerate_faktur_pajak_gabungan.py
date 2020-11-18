from datetime import datetime, timedelta
from openerp import models, fields, api, _
from openerp.osv import osv

class wtc_regenerate_faktur_pajak_gabungan(models.Model):
    _name ="wtc.regenerate.faktur.pajak.gabungan"
    _description = "Regenerate Faktur Pajak Gabungan"
    _order = "date desc,id desc"
    
    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()
        
    name = fields.Char('Regenerate No')
    date = fields.Date('Date',default=_get_default_date)
    model_id = fields.Many2one('ir.model',string="Form Name",domain="[('model','in',('wtc.disposal.asset','dealer.sale.order','wtc.account.voucher','wtc.work.order'))]")
    state = fields.Selection([('draft','Draft'),('post','Posted')],default='draft')
    regenerate_line = fields.One2many('wtc.regenerate.faktur.pajak.gabungan.line','regenerate_id',string="Regenerate Line")
    confirm_uid = fields.Many2one('res.users',string="Posted by")
    confirm_date = fields.Datetime('Posted on')   
    
    @api.onchange('model_id')
    @api.multi
    def onchange_generate_line(self):
        warning = {}  
        transaction = []
        if self.model_id :
            if self.model_id.model == 'dealer.sale.order' :
                dso = self.env['dealer.sale.order']
                search_dso = dso.search([
                                         ('faktur_pajak_id','=',False),
                                         ('state','in',('progress','done'))
                                         ],order='date_order',limit=100)
                if not search_dso :
                    warning = {
                        'title': ('Perhatian !'),
                        'message': (('Tidak ada data transaksi yang belum memiliki no faktur pajak ! ')),
                    }
                    self.model_id = False
                if not warning :
                    for x in search_dso :
                        transaction.append([0,0,{
                                                 'name':x.name,                               
                                                 'untaxed_amount':x.amount_untaxed,
                                                 'tax_amount':x.amount_tax,
                                                 'amount_total':x.amount_total,
                                                 'date':x.date_order,
                                                 'partner_id':x.partner_id.id,
                                                 'transaction_id':x.id,
                                                 'model_id':self.model_id.id,
                                                }])
            elif self.model_id.model == 'wtc.account.voucher' :
                av = self.env['wtc.account.voucher']
                search_av = av.search([
                                         ('faktur_pajak_id','=',False),
                                         ('type','=','sale'),
                                         ('state','=','posted')
                                         ],order='date',limit=100)
                if not search_av :
                    warning = {
                        'title': ('Perhatian !'),
                        'message': (('Tidak ada data transaksi yang belum memiliki no faktur pajak ! ')),
                    }
                    self.model_id = False
                if not warning :
                    for x in search_av :
                        total = 0.0
                        for line in x.line_cr_ids :
                            total += line.amount
                        tax = x.amount - total                     
                        transaction.append([0,0,{
                                                 'name':x.number,                               
                                                 'untaxed_amount':total,
                                                 'tax_amount':tax,
                                                 'amount_total':x.amount,
                                                 'date':x.date,
                                                 'partner_id':x.partner_id.id,
                                                 'transaction_id':x.id,
                                                 'model_id':self.model_id.id,
                                                }])   
            elif self.model_id.model == 'wtc.work.order' :
                wo = self.env['wtc.work.order']
                search_wo = wo.search([
                                         ('faktur_pajak_id','=',False),
                                         ('state','in',('open','done'))
                                         ],order='date',limit=100)
                if not search_wo :
                    warning = {
                        'title': ('Perhatian !'),
                        'message': (('Tidak ada data transaksi yang belum memiliki no faktur pajak ! ')),
                    }
                    self.model_id = False
                if not warning :
                    for x in search_wo :                   
                        transaction.append([0,0,{
                                                 'name':x.name,                               
                                                 'untaxed_amount':x.amount_untaxed,
                                                 'tax_amount':x.amount_tax,
                                                 'amount_total':x.amount_total,
                                                 'date':x.date,
                                                 'partner_id':x.customer_id.id,
                                                 'transaction_id':x.id,
                                                 'model_id':self.model_id.id,
                                                }])    
            elif self.model_id.model == 'wtc.disposal.asset' :
                da = self.env['wtc.disposal.asset']
                search_da = da.search([
                                     ('faktur_pajak_id','=',False),
                                     ('state','in',('confirm'))
                                     ],order='date',limit=100)
                if not search_da :
                    warning = {
                        'title': ('Perhatian !'),
                        'message': (('Tidak ada data transaksi yang belum memiliki no faktur pajak ! ')),
                    }
                    self.model_id = False
                if not warning :
                    for x in search_da :                   
                        transaction.append([0,0,{
                                                 'name':x.name,                               
                                                 'untaxed_amount':x.amount_untaxed,
                                                 'tax_amount':x.amount_tax,
                                                 'amount_total':x.amount_total,
                                                 'date':x.date,
                                                 'partner_id':x.partner_id.id,
                                                 'transaction_id':x.id,
                                                 'model_id':self.model_id.id,
                                                }])                                                                            
        self.regenerate_line = transaction    
        return {'warning':warning}                    
    
    @api.multi        
    def get_regenerate_faktur_pajak(self,tgl_terbit):
        faktur_pajak = self.env['wtc.faktur.pajak.out']
        thn_penggunaan = int(tgl_terbit[:4])

        no_fp = faktur_pajak.search([
                                    ('state','=','open'),
                                    ('thn_penggunaan','=',thn_penggunaan),
                                    ('tgl_terbit','<=',tgl_terbit)
                                    ],limit=1,order='id')
        
        if not no_fp :
            raise osv.except_osv(('Perhatian !'), ("Nomor faktur pajak tidak ditemukan, silahkan Generate terlebih dahulu !"))
        return no_fp
              
    @api.model
    def create(self,values,context=None):
        values['name'] = self.env['ir.sequence'].get_sequence('RFP')     
        values['date'] = self._get_default_date()
        faktur_pajak = super(wtc_regenerate_faktur_pajak_gabungan,self).create(values)       
        return faktur_pajak
                         
    @api.multi
    def action_post(self):
        self.date = self._get_default_date()
        self.state = 'post'
        dso = self.env['dealer.sale.order']
        av = self.env['wtc.account.voucher']
        wo = self.env['wtc.work.order']
        da = self.env['wtc.disposal.asset']
        value = False    
            
        for x in self.regenerate_line :
            
            no_faktur = self.get_regenerate_faktur_pajak(x.date)
            no_faktur.write({
                            'model_id':x.model_id.id,
                            'amount_total':x.amount_total,
                            'untaxed_amount':x.untaxed_amount,
                            'tax_amount':x.tax_amount,                                                    
                            'state':'close',
                            'transaction_id':x.transaction_id,
                            'date':x.date,
                            'partner_id':x.partner_id.id,
                            'company_id':1,
                            })   
            if not no_faktur :
                raise osv.except_osv(('Perhatian !'), ("Nomor faktur pajak tidak tersedia !"))
            
            #cek every object
            if self.model_id.model == 'dealer.sale.order' :
                value = dso.browse([x.transaction_id])                    
            elif self.model_id.model == 'wtc.account.voucher' :
                value = av.browse([x.transaction_id])
            elif self.model_id.model == 'wtc.work.order' :
                value = wo.browse([x.transaction_id])                
            elif self.model_id.model == 'wtc.disposal.asset' :
                value = da.browse([x.transaction_id])  
                            
            #cek existense  
            if not value :
                raise osv.except_osv(('Perhatian !'), ("No %s tidak ditemukan !")%x.name)                                        
            if value.faktur_pajak_id :
                raise osv.except_osv(('Perhatian !'), ("No %s sudah memiliki faktur pajak !")%x.name)                    
            
            #write value
            value.write({'faktur_pajak_id':no_faktur.id,'pajak_gabungan':False})                
            x.write({'no_faktur_pajak':no_faktur.id})
            
    @api.multi
    def unlink(self):
        if self.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Regenerate Faktur Pajak sudah diproses, data tidak bisa didelete !"))
        return super(wtc_regenerate_faktur_pajak_gabungan, self).unlink() 
                
class wtc_regenerate_faktur_pajak_gabungan_line(models.Model):
    _name ="wtc.regenerate.faktur.pajak.gabungan.line"
    _description = "Regenerate Faktur Pajak Gabungan Line"
    
    name = fields.Char(string="Transaction No")
    regenerate_id = fields.Many2one('wtc.regenerate.faktur.pajak.gabungan')
    untaxed_amount = fields.Float('Untaxed Amount')
    tax_amount = fields.Float('Tax Amount')
    amount_total = fields.Float('Total Amount')
    date = fields.Date('Date')
    partner_id = fields.Many2one('res.partner',string='Partner')
    transaction_id = fields.Integer(string='Transaction ID')
    model_id = fields.Many2one('ir.model',string='Form Name')
    no_faktur_pajak = fields.Many2one('wtc.faktur.pajak.out',string='Faktur Pajak')
    