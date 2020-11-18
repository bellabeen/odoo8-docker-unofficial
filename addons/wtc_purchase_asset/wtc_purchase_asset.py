import time
from lxml import etree
import pytz
from openerp import SUPERUSER_ID
from openerp.osv import fields, osv
from openerp.tools.translate import _
from datetime import datetime, timedelta
import openerp.addons.decimal_precision as dp
from datetime import datetime, timedelta
from openerp import workflow

class wtc_purchase_asset(osv.osv):
    _name = 'wtc.purchase.asset'
    _description = 'Purchase Asset'
    _order = 'date desc'
    
    STATE_ASSET = [
            ('draft','Draft'),
            ('waiting_for_approval','Waiting for Approval'),
            ('approved','Approved'),
            ('confirmed','Confirmed'),
            ('cancel','Cancelled'),
            ]
           
    def _amount_line_tax(self,cr , uid, line, context=None):
        val=0.0
        for c in self.pool.get('account.tax').compute_all(cr,uid, line.tax_id, line.amount,line.quantity, line.product_id)['taxes']:
            val +=c.get('amount',0.0)
        return val
    
    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        tax_obj = self.pool.get('account.tax')
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
            }
            val = val1 = 0.0
            for line in order.purchase_asset_line:
                taxes = tax_obj.compute_all(cr, uid, line.tax_id,  line.amount, line.quantity, line.product_id)
                val1 += taxes['total']
                val += self._amount_line_tax(cr, uid, line, context=context)

            res[order.id]['amount_tax'] = val
            res[order.id]['amount_untaxed'] =val1
            res[order.id]['amount_total'] = res[order.id]['amount_untaxed'] + res[order.id]['amount_tax']
        return res
    
    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('wtc.purchase.asset.line').browse(cr, uid, ids, context=context):
            result[line.purchase_id.id] = True
        return result.keys()
    
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False  
        return branch_ids 
        
    def _get_default_date(self,cr,uid,context):
        return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context).date() 
        
    _columns = {                               
            'branch_id' : fields.many2one('wtc.branch', string='Branch', required=True),
            'division' : fields.selection([('Umum','Umum')], string='Division',default='Umum', required=True,change_default=True, select=True),    
            'name' : fields.char(string='Reference/Description',readonly=True, states={'draft': [('readonly', False)]}),
            'partner_id' : fields.many2one('res.partner', domain=[('supplier','=',True)],string='Partner', change_default=True,required=True, readonly=True, states={'draft': [('readonly', False)]},),
            'date' : fields.date(string='Date',readonly=True, states={'draft': [('readonly', False)]}, copy=False),
            'supplier_invoice_number' : fields.char(string='Supplier Invoice Number',readonly=True, states={'draft': [('readonly', False)]}),
            'document_date' : fields.date(string='Supplier Invoice Date',required=True),
            'date_due' : fields.date(string='Due Date',readonly=True, states={'draft': [('readonly', False)]}, copy=False,),
            'reference' : fields.char(string='PO Number'),
            'journal_id' : fields.many2one('account.journal', string='Journal', readonly=True, states={'draft': [('readonly', False)]}), 
            'state' : fields.selection(STATE_ASSET, string='Status', readonly=True, default='draft', copy=False),
            'purchase_asset_line' : fields.one2many('wtc.purchase.asset.line', 'purchase_id', string='Purchase Asset Lines',readonly=True, states={'draft': [('readonly', False)]}, copy=True),
            'invoice_id' : fields.many2one('account.invoice',string='Invoice No'),
            'amount_untaxed': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Untaxed Amount',
                store={
                    'wtc.purchase.asset': (lambda self, cr, uid, ids, c={}: ids, ['purchase_asset_line'], 10),
                    'wtc.purchase.asset.line': (_get_order, ['amount', 'tax_id', 'quantity'], 10),
                },
                multi='sums', help="The amount without tax."),
            'amount_tax': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Taxes',
                store={
                    'wtc.purchase.asset': (lambda self, cr, uid, ids, c={}: ids, ['purchase_asset_line'], 10),
                    'wtc.purchase.asset.line': (_get_order, ['amount', 'tax_id', 'quantity'], 10),
                },
                multi='sums', help="The tax amount."),
            'amount_total': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total',
                store={
                    'wtc.purchase.asset': (lambda self, cr, uid, ids, c={}: ids, ['purchase_asset_line'], 10),
                    'wtc.purchase.asset.line': (_get_order, ['amount', 'tax_id', 'quantity'], 10),
                },
                multi='sums', help="The total amount."),
            'comment' : fields.text(string='Additional Information'),
            'approval_ids': fields.one2many('wtc.approval.line','transaction_id',string="Table Approval",domain=[('form_id','=',_name)]),
            'approval_state': fields.selection([('b','Belum Request'),('rf','Request For Approval'),('a','Approved'),('r','Reject')],'Approval State', readonly=True),
            'confirm_uid':fields.many2one('res.users',string="Confirmed by"),
            'confirm_date':fields.datetime('Confirmed on'),
            'cancelled_uid':fields.many2one('res.users',string="Cancelled by"),
            'cancelled_date':fields.datetime('Cancelled on'),           
            'account_id':fields.many2one('account.account',string='Account'),
            'no_faktur_pajak' : fields.char(string='No Faktur Pajak'),
            'tgl_faktur_pajak' : fields.date(string='Tgl Faktur Pajak'),   
            'payment_term_id' : fields.many2one('account.payment.term', string='Payment Terms',states={'draft': [('readonly', False)]}),
            'pajak_gabungan':fields.boolean('Faktur Pajak Gabungan',copy=False),   
            
                                 
    } 
    
    _defaults = {
                'branch_id':_get_default_branch,
                'date':_get_default_date,
                'approval_state':'b',
                }
    
    def create(self, cr, uid, vals, context=None):        
        if not vals['purchase_asset_line'] :
            raise osv.except_osv(('Perhatian !'), ("Detail Transaksi Belum diisi"))
        vals['date'] = self._get_default_date(cr, uid, context).strftime('%Y-%m-%d')
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'PA')
        
        return super(wtc_purchase_asset, self).create(cr, uid, vals, context=context)

    def request_approval(self,cr,uid,ids,context=None):
        obj_matrix = self.pool.get("wtc.approval.matrixbiaya")
        total = 0
        val = self.browse(cr,uid,ids)
        for line in val.purchase_asset_line :
            self.pool.get('wtc.purchase.asset.line').write(cr,uid,[line.id],{'state':'waiting_for_approval'})
            total = total + line.price_subtotal
        obj_matrix.request_by_value(cr, uid, ids, val, total)
        self.write(cr,uid,ids,{'state':'waiting_for_approval','approval_state':'rf'})
        return True
    
    def approve_approval(self,cr,uid,ids,context=None):
        obj_bj = self.browse(cr, uid, ids, context=context)
        approval_sts = self.pool.get("wtc.approval.matrixbiaya").approve(cr, uid, ids, obj_bj)
        if approval_sts == 1:
            self.write(cr, uid, ids, {'approval_state':'a','state':'approved'})
            for x in obj_bj.purchase_asset_line :
                self.pool.get('wtc.purchase.asset.line').write(cr,uid,[x.id],{'state':'approved'})
        elif approval_sts == 0:
            raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group approval"))
        return True
    
    def confirm_order(self,cr,uid,ids,context=None):
        self.write(cr,uid,ids,{'confirm_uid':uid,'confirm_date':datetime.now(),'state':'confirmed','date':datetime.now()})  
        for line in self.browse(cr,uid,ids).purchase_asset_line :
            self.pool.get('wtc.purchase.asset.line').write(cr,uid,[line.id],{'state':'confirmed'})
        invoice_id = self.invoice_create(cr, uid, ids, context=context)
        self.update_asset(cr,uid,ids,invoice_id,context=context)   
        return True
    
    def invoice_create(self,cr,uid,ids,context=None):
        val = self.browse(cr, uid, ids, context={})[0]
        obj_inv = self.pool.get('account.invoice') 

        obj_model = self.pool.get('ir.model')
        obj_model_id = obj_model.search(cr,uid,[ ('model','=',self.__class__.__name__) ])
        
        config = self.pool.get('wtc.branch.config').search(cr,uid,[('branch_id','=',val.branch_id.id)])
        
        if config :
            config_browse = self.pool.get('wtc.branch.config').browse(cr,uid,config)
            journal_purchase_asset_id = config_browse.purchase_asset_journal_id
            invoice_account = journal_purchase_asset_id.default_credit_account_id
            prepaid_account = config_browse.prepaid_account_id
            accrue_account = config_browse.accrue_account_id
            if not journal_purchase_asset_id or not prepaid_account or not accrue_account or not invoice_account :
                raise osv.except_osv(_('Perhatian!'),
                    _('Journal Purchase Asset atau Credit Journal Purchase Asset atau Prepaid Account atau Accrue Account belum diisi, harap isi terlebih dahulu didalam branch config'))   
                             
        elif not config :
            raise osv.except_osv(_('Error!'),
                _('Please define Journal in Setup Division for this branch: "%s".') % \
                (val.branch_id.name))
                            
        invoice_id = {
            'name':val.name,
            'origin': val.name,
            'branch_id':val.branch_id.id,
            'division':val.division,
            'partner_id':val.partner_id.id,
            'date_invoice':val.date,
            'journal_id':journal_purchase_asset_id.id,
            'account_id':invoice_account.id,
            'transaction_id':val.id,
            'model_id':obj_model_id[0],
            'amount_untaxed':val.amount_untaxed,
            'amount_tax':val.amount_tax,
            'amount_total':val.amount_total,
            'comment':val.comment,
            'type': 'in_invoice',
            'supplier_invoice_number' : val.supplier_invoice_number,
            'document_date' : val.document_date,
            'no_faktur_pajak' : val.no_faktur_pajak,
            'tgl_faktur_pajak' : val.tgl_faktur_pajak,   
            'asset' : True,  
            'payment_term' : val.payment_term_id.id
            }
        invoice_line = []
        for x in val.purchase_asset_line:
            if x.asset_register_id.category_id.is_cip or (x.do_number or x.do_date) :
                account_line_id = x.asset_register_id.category_id.account_asset_id.id
            elif x.asset_register_id.category_id.method_number == 0 :
                account_line_id = x.asset_register_id.category_id.account_asset_id.id
            elif x.asset_register_id.state == 'draft' :
                account_line_id = prepaid_account.id
            elif x.asset_register_id.state == 'CIP' :
                account_line_id = x.asset_register_id.category_id.account_asset_id.id
            elif x.asset_register_id.state == 'open' and x.asset_register_id.amount_different != False and x.asset_register_id.retensi > 0 :
                account_line_id = accrue_account.id
            else :
                account_line_id = accrue_account.id
            invoice_line.append([0,False,{
                    'branch_id' :x.branch_id.id,
                    'division' : val.division,
                    'name':x.description,
                    'product_id':x.product_id.id if x.product_id else False,
                    'quantity':x.quantity,
                    'origin':val.name,
                    'price_unit':x.amount,
                    'invoice_line_tax_id': [(6,0,[tax.id for tax in x.tax_id])],
                    'account_id': account_line_id,
                    'ref_asset_id': x.asset_register_id.id,
               }])
        
            
        invoice_id['invoice_line'] = invoice_line
        invoice = obj_inv.create(cr,uid,invoice_id)
        obj_inv.button_reset_taxes(cr,uid,invoice)
        workflow.trg_validate(uid, 'account.invoice', invoice, 'invoice_open', cr)
                        
        self.write(cr,uid,ids,{'invoice_id':invoice,'account_id':val.journal_id.default_credit_account_id.id})
        return invoice
    
    def update_asset(self,cr,uid,ids,invoice_id,context=None):
        val = self.browse(cr,uid,ids)
        asset_obj = self.pool.get('account.asset.asset')
        for x in val.purchase_asset_line :
            res = {}
            do_number = False
            current_value = x.asset_register_id.purchase_value
            real_purchase_value = x.asset_register_id.real_purchase_value
            current_value += x.price_subtotal / x.quantity
            real_purchase_value += x.price_subtotal
            if not x.asset_register_id.real_purchase_date :
                res['real_purchase_date'] = val.date
            if x.asset_register_id.category_id.is_cip :
                res['state'] = 'CIP'
            elif x.do_number or x.do_date :
                res['state'] = 'open'
                res['do_number'] = x.do_number
                res['do_date'] = x.do_date
                res['purchase_date'] = x.do_date
                do_number = True
            res['purchase_asset_id'] = val.id
            res['purchase_value'] = current_value
            res['invoice_id'] = invoice_id
            res['real_purchase_value'] = real_purchase_value
            res['partner_id'] = val.partner_id.id
            asset_obj.write(cr,uid,[x.asset_register_id.id],res)
            if do_number :
                x.asset_register_id.validate()
            else :
                asset_obj.compute_depreciation_board(cr,uid,x.asset_register_id.id,context=context)
        return True
    
    def view_invoice(self,cr,uid,ids,context=None):  
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        result = mod_obj.get_object_reference(cr, uid, 'account', 'action_invoice_tree2')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_supplier_form')
        result['views'] = [(res and res[1] or False, 'form')]
        val = self.browse(cr, uid, ids)
        obj_inv = self.pool.get('account.invoice')
        obj = obj_inv.search(cr,uid,[('origin','=',val.name)])
        result['res_id'] = obj[0] 
        return result
        
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Purchase Asset tidak bisa didelete dalam State selain 'draft' !"))
        return super(wtc_purchase_asset, self).unlink(cr, uid, ids, context=context)
          
    def write(self, cr, uid, ids, vals, context=None):
        #Recalculate date_due value based on document_date and payment_term
        asset_id = self.browse(cr, uid, ids, context=context)
        if not asset_id.date_due :
            vals.update(self._fill_due_date(cr, uid, ids, vals.get('document_date', asset_id.document_date), vals.get('payment_term_id', asset_id.payment_term_id.id), context))
        return super(wtc_purchase_asset, self).write(cr, uid, ids, vals, context=context)
                       
           
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
             
    def onchange_pajak_gabungan(self,cr,uid,ids,pajak_gabungan,context=None):
        vals = {}
        if pajak_gabungan :
            vals['no_faktur_pajak'] = False
            vals['tgl_faktur_pajak'] = False
        return {'value':vals} 
                    
class wtc_purchase_asset_line(osv.osv):
    _name = "wtc.purchase.asset.line"
    _description = "Purchase Asset Line"
    _order = "purchase_id,id" 
    _rec_name = 'description'
    
    def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        res = {}
        if context is None:
            context = {}
        for line in self.browse(cr, uid, ids, context=context):
            taxes = tax_obj.compute_all(cr, uid, line.tax_id, line.amount, line.quantity, line.product_id)
            res[line.id]=taxes['total']
        return res
    
    def _get_current_value(self, cr, uid, ids, field_name, arg, context=None):
        if context is None:
            context = {}
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = line.asset_register_id.purchase_value
        return res
   
    def _get_asset_name(self, cr, uid, ids, field_name, arg, context=None):
        if context is None:
            context = {}
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id]= line.asset_register_id.name
        return res
    
    def _get_product_id(self, cr, uid, ids, field_name, arg, context=None):
        if context is None:
            context = {}
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id]= line.asset_register_id.product_id.id
        return res
            
    STATE_ASSET = [
            ('draft','Draft'),
            ('waiting_for_approval','Waiting for Approval'),
            ('approved','Approved'),
            ('confirmed','Confirmed'),
            ('cancel','Cancelled'),
            ]
                
    _columns = {
            'purchase_id'       : fields.many2one('wtc.purchase.asset',string='Purchase Asset No'),
            'asset_register_id' : fields.many2one('account.asset.asset',string='Asset Register No',required=True),
            'description'       : fields.char(string='Description',required=True),
            'product_id'        : fields.function(_get_product_id,type='many2one',relation='product.product',string='Product',readonly=True,store=True),
            'asset_name'        : fields.function(_get_asset_name,type='char',string='Asset Name',readonly=True,store=True),
            'quantity'          : fields.integer(string='Quantity'),
            'current_value'     : fields.function(_get_current_value,string='Current Value',readonly=True,store=True),
            'amount'            : fields.float(string='Amount'),
            'tax_id'            : fields.many2many('account.tax', 'wtc_purchase_asset_tax', 'purchase_asset_line_id', 'tax_id', 'Taxes',domain=[('type_tax_use','in',('purchase','all'))]),
            'price_subtotal'    : fields.function(_amount_line, string='Subtotal', digits_compute= dp.get_precision('Account'),store=True),
            'state'             : fields.selection(STATE_ASSET, string='Status', readonly=True, default='draft', copy=False),
            'branch_id'         : fields.many2one('wtc.branch', string='Branch', required=True),
            'do_number'             : fields.char("No.DO"),
            'do_date'            : fields.date("Tgl.DO")
    }
    
    _defaults = {
                'quantity':1,
                'state':'draft',
                }
    
    def onchange_line(self,cr,uid,ids,asset_register_id,quantity,context=None):
        vals = {}
        if asset_register_id :
            asset_id = self.pool.get('account.asset.asset').browse(cr,uid,[asset_register_id])
            vals['asset_name'] =  asset_id.name
            vals['product_id'] =  asset_id.product_id.id
            vals['current_value'] =  asset_id.purchase_value
        # if quantity != 1 :
        #     vals['quantity'] = 1
        return {'value':vals}        
 
    def onchange_branch(self,cr,uid,ids,branch_id,context=None):
        dom = {}
        
        if branch_id :
            asset_id = self.pool.get('account.asset.asset').search(cr,uid,[
                                                                           ('branch_id','=',branch_id),'|',
                                                                           ('state','in',('draft','CIP')),'&',
                                                                           ('state','=','open'),
                                                                           ('amount_different','=',True),
                                                                           ])
            dom['asset_register_id'] = "[('id','in',"+str(tuple(asset_id))+")]"  
            
        return {'domain':dom} 
                
            
            
                        
