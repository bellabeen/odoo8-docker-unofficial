import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp import api

class account_invoice(osv.osv):
    _inherit = "account.invoice"


        
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids
    
    def _get_default_date(self,cr,uid,ids,context=None):
        return self.pool.get('wtc.branch').get_default_date(cr,uid,ids,context=context)
        
    def _get_default_date_model(self,cr,uid,context=None):
        return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)
        
    _columns = {    
        'branch_id' : fields.many2one('wtc.branch', string='Branch', required=True),
        'division' : fields.selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum')], string='Division', change_default=True, select=True),
        'lot_id' : fields.many2one('stock.production.lot',string='No. Mesin'),
        'qq_id' : fields.many2one('res.partner',string='QQ'),
        'tipe' : fields.selection([('customer','Customer'),('finco','Finco'),('ps_ahm','Program Subsidi AHM'),('ps_md','Program Subsidi MD'),('ps_finco','Program Subsidi Finco'),('bb_md','Barang Bonus MD'),('bb_finco','Barang Bonus Finco'),('bbn','BBN'),('insentif','Insentif'),('hc','Hutang Komisi'),('blind_bonus_beli','Blind Bonus Beli')]),
        'validate_date': fields.date('Validate Date'),
        'confirm_uid':fields.many2one('res.users',string="Validated by"),
        'confirm_date':fields.datetime('Validated on'),
        'cancel_uid':fields.many2one('res.users',string="Set to draft by"),
        'cancel_date':fields.datetime('Set to draft on'),
        'document_date':fields.date('Supplier Invoice Date'),
        'pajak_gabungan':fields.boolean('Faktur Pajak Gabungan'),   
        'no_faktur_pajak':fields.char(string='No Faktur Pajak'),
        'tgl_faktur_pajak':fields.date(string='Tgl Faktur Pajak'),
        'date_invoice' : fields.date(string='Date',
            readonly=True, states={'draft': [('readonly', False)]}, index=True,
            help="Keep empty to use the current date", copy=False),
        'transaction_id': fields.integer('Transaction ID'),
        'model_id': fields.many2one('ir.model','Model'),
        'asset':fields.boolean('Asset')
   }
    
    def faktur_pajak_change(self,cr,uid,ids,no_faktur_pajak,context=None):   
        value = {}
        warning = {}
        if no_faktur_pajak :
            cek = no_faktur_pajak.isdigit()
            if not cek :
                warning = {
                    'title': ('Perhatian !'),
                    'message': (('Nomor Faktur Pajak Hanya Boleh Angka ! ')),
                }
                value = {
                         'no_faktur_pajak':False
                         }     
        return {'warning':warning,'value':value} 
        
    _defaults = {
                 'branch_id' : _get_default_branch,
                 'date_invoice': _get_default_date,
                 }
    
    def invoice_validate(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
                                  'confirm_uid':uid,
                                  'confirm_date':datetime.now(),
                                  'date_invoice':self._get_default_date_model(cr, uid)
                                  })        
        res = super(account_invoice, self).invoice_validate(cr, uid, ids, context=context)
        return res
#     
#     def finalize_invoice_move_lines(self,cr,uid,ids, move_lines,context=None):
#         ##################################################################################################
#         # This method used to attached branch and division on both customer invoice and supplier invoice #
#         ##################################################################################################
#         
#         finalize =  super(account_invoice, self).finalize_invoice_move_lines(cr,uid,ids, move_lines,context=context)
#         vals = self.browse(cr,uid,ids)
#         if not vals.branch_id.id or not vals.division :
#             raise osv.except_osv(_('Perhatian!'), _('Pastikan Branch dan Division sudah diisi !'))
#         print "finalize",finalize
#         print "move_lines",move_lines
#         for x in finalize :
#             if 'branch_id' not in x[2] :
#                 x[2]['branch_id'] = vals.branch_id.id
#             if 'division' not in x[2] :
#                 x[2]['division'] = vals.division
#             if 'date_maturity' not in x[2] :
#                 x[2]['date_maturity'] = vals.date_due
#         return finalize
    
    def action_cancel(self,cr,uid,ids,context=None):
        self.write(cr,uid,ids,{'cancel_uid':uid,'cancel_date':datetime.now()})        
        vals = super(account_invoice,self).action_cancel(cr,uid,ids,context=context)
        return vals 
    
    def _fill_due_date(self, cr, uid, ids, document_date, payment_term, context=None):
        value = {}
        if not document_date:
            document_date = fields.date.context_today(self,cr,uid,context=context)
        if not payment_term:
            # To make sure the invoice due date should contain due date which is
            # entered by user when there is no payment term defined
            value =  {'date_due': document_date}
        if payment_term and document_date:
            pterm = self.pool.get('account.payment.term').browse(cr,uid,payment_term)
            pterm_list = pterm.compute(value=1, date_ref=document_date)[0]
            if pterm_list:
                value = {'date_due': max(line[0] for line in pterm_list)}
        return value
    
    def onchange_document_date(self, cr, uid, ids, document_date, payment_term, context=None):
        value = self._fill_due_date(cr, uid, ids, document_date, payment_term, context)
        return {'value': value}

    def create(self, cr, uid, vals, context=None):
        vals['date_invoice'] = self._get_default_date_model(cr, uid)
        
        res = super(account_invoice,self).create(cr, uid, vals, context=context)
        invoice = self.browse(cr,uid,res)
        if not invoice.payment_term :
            pterm = self.pool.get('account.payment.term').search(cr,uid,[
                                                                         ('name','=','Immediate Payment')
                                                                         ])
            if pterm :
                pterm_browse = self.pool.get('account.payment.term').browse(cr,uid,pterm)
                invoice.write({'payment_term':pterm_browse.id})
        return res
    
    def write(self, cr, uid, ids, vals, context=None):
        #Recalculate date_due value based on document_date and payment_term
        if vals.get('document_date') or vals.get('payment_term') :
            invoice_id = self.browse(cr, uid, ids, context=context)
            vals.update(self._fill_due_date(cr, uid, ids, vals.get('document_date', invoice_id.document_date), vals.get('payment_term', invoice_id.payment_term.id), context))
        return super(account_invoice, self).write(cr, uid, ids, vals, context=context)
    
    def action_date_assign(self,cr,uid,ids,context=None):
        period = self.pool.get('account.period').find(cr,uid,dt=self._get_default_date_model(cr, uid))[0]
        self.write(cr, uid, ids, {
                                  'confirm_uid':uid,
                                  'confirm_date':datetime.now(),
                                  'date_invoice':self._get_default_date_model(cr, uid),
                                  'period_id': period
                                  })        
        res1 = super(account_invoice,self).action_date_assign(cr,uid,ids,context=context)
        for inv in self.browse(cr,uid,ids):
            res = self.onchange_document_date(cr,uid,ids,inv.document_date,inv.payment_term.id,context=context)
            if res and res.get('value'):
                inv.write(res['value'])
        return res1
    
    def action_move_create(self,cr,uid,ids,context=None):
        res = super(account_invoice,self).action_move_create(cr,uid,ids,context=context)
        val = self.browse(cr,uid,ids)
        move = self.pool.get('account.move')
        move_name = self.pool.get('ir.sequence').get_per_branch(cr, uid, val.branch_id.id, val.journal_id.code)
        move.write(cr,uid,val.move_id.id,{'name':move_name})
        return res
    
    @api.model
    def _prepare_refund(self, invoice, date=None, period_id=None, description=None, journal_id=None):
        res = super(account_invoice,self)._prepare_refund(invoice, date, period_id, description, journal_id)
        res['branch_id'] = invoice.branch_id.id
        res['division'] = invoice.division
        res['document_date'] = invoice.document_date
        res['origin'] = invoice.origin
        return res

    @api.model
    def line_get_convert(self, line, part, date):
        res = super(account_invoice,self).line_get_convert( line, part, date)
        res['branch_id'] = line['branch_id'] if 'branch_id' in line else self.branch_id.id
        res['division'] = line['division'] if 'division' in line else self.division
        res['date_maturity'] = self.date_due
        res['ref_asset_id'] = line['ref_asset_id'] if 'ref_asset_id' in line else False
        
        return res
        
class account_invoice_line(osv.osv):
    
    _inherit = 'account.invoice.line'
    
    _columns = {
        'force_cogs': fields.float(string='Force COGS'),
        'branch_id' : fields.many2one('wtc.branch',string='Branch'),
        'division' : fields.selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum')], string='Division', change_default=True, select=True),
        'ref_asset_id' : fields.many2one('account.asset.asset',string='Asset No'),
    }
    
    def move_line_get_item(self,cr,uid, line):
        res = super(account_invoice_line,self).move_line_get_item(cr,uid,line)
        if 'branch_id' not in res :
            res['branch_id'] =  line.branch_id.id if line.branch_id else line.invoice_id.branch_id.id
        if 'division' not in res :
            res['division'] = line.division if line.division else line.invoice_id.division
        if 'date_maturity' not in res :
            res['date_maturity'] = line.invoice_id.date_due
        if 'ref_asset_id' not in res :
            res['ref_asset_id'] = line.ref_asset_id.id if line.ref_asset_id else False
        return res    
       
# class account_invoice_tax(osv.osv):
#     _inherit = 'account.invoice.tax'
    
#     @api.model
#     def move_line_get(self, invoice_id):
#         res =  super(account_invoice_tax,self).move_line_get(invoice_id)  
#         invoice = self.env['account.invoice'].browse(invoice_id)
#         print "res",res
# 
#         for x in res :
#             if 'branch_id' not in x :
#                 x['branch_id'] = invoice.branch_id.id
#             if 'division' not in x :
#                 x['division'] = invoice.division
#                
#         print "tax2",res
#         return res
           