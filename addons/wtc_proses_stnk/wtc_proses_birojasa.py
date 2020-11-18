import time
from datetime import datetime
from openerp import workflow
from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp import netsvc
from openerp.tools.translate import _
from openerp.tools.safe_eval import safe_eval
from lxml import etree
from openerp.osv.orm import setup_modifiers

class wtc_proses_birojasa(osv.osv):
    _name = "wtc.proses.birojasa"
    _description = "Tagihan Biro Jasa"
    _order = "tanggal desc,id desc"
    
    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('waiting_for_approval','Waiting For Approval'),
        ('confirmed', 'Approved'),
        ('approved','Process Confirmed'),
        ('except_invoice', 'Invoice Exception'),
        ('done','Done'),
        ('cancel','Cancelled')
    ]
     
    def _get_default_date(self,cr,uid,context=None):
        return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)
          
    def birojasa_change(self,cr,uid,ids,branch_id,birojasa_id,context=None):
        domain = {}
        birojasa = []
        
        if branch_id:
            birojasa_srch = self.pool.get('wtc.harga.birojasa').search(cr,uid,[
                                                                      ('branch_id','=',branch_id)
                                                                      ])
            if birojasa_srch :
                birojasa_brw = self.pool.get('wtc.harga.birojasa').browse(cr,uid,birojasa_srch)
                for x in birojasa_brw :
                    birojasa.append(x.birojasa_id.id)
            
        domain['partner_id'] = [('id','in',birojasa)]
        return {'value':{'partner_id':False},'domain':domain}
              
    def _amount_line_tax(self,cr , uid, line, context=None):
        val=0.0
        for c in self.pool.get('account.tax').compute_all(cr,uid, line.tax_id, line.total_jasa,1)['taxes']:
            val +=c.get('amount',0.0)
        return val 

    def _amount_jasa_tax(self,cr , uid, line,ppn_jasa, context=None):
        val=0.0
        for c in self.pool.get('account.tax').compute_all(cr,uid, line, ppn_jasa,1)['taxes']:
            val +=c.get('amount',0.0)
        return val

    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):

        res = {}
        ppn_jasa = False
        for engine in self.browse(cr, uid, ids, context=context):
            res[engine.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
                'total_approval_koreksi': 0.0,
                'total_koreksi':0.0,
                'total_estimasi':0.0,
                'total_progressive':0.0
            }
            koreksi = nilai = nilai_2 = estimasi = tagihan = progressive =  tax = 0.0
           
            for line in engine.proses_birojasa_line:
                if engine.tax_id:
                    ppn_jasa += line.total_jasa
                koreksi += line.koreksi  
                nilai = abs(line.koreksi)
                nilai_2 += nilai
                estimasi += line.total_estimasi
                tagihan += line.total_tagihan
                progressive += line.pajak_progressive
                tax += self._amount_line_tax(cr, uid, line, context=context)
           
            ppn_jasa = round(self._amount_jasa_tax(cr,uid,engine.tax_id,ppn_jasa,context=context) * 1.1)

            res[engine.id]['ppn_jasa'] = ppn_jasa
            res[engine.id]['total_approval_koreksi'] = nilai_2
            res[engine.id]['amount_tax'] = tax
            res[engine.id]['amount_untaxed'] =tagihan
            res[engine.id]['total_koreksi'] =koreksi
            res[engine.id]['total_estimasi'] =estimasi
            res[engine.id]['total_progressive'] = progressive
            res[engine.id]['amount_total'] = koreksi + estimasi + progressive + ppn_jasa
        return res
    
    def _get_engine(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('wtc.proses.birojasa.line').browse(cr, uid, ids, context=context):
            result[line.proses_biro_jasa_id.id] = True
        return result.keys()

    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
        
    _columns = {
        'branch_id': fields.many2one('wtc.branch', string='Branch', required=True),
        'division':fields.selection([('Unit','Unit')], 'Division', change_default=True, select=True),
        'name': fields.char('No Reference',size=20, readonly=True),
        'tanggal': fields.date('Tanggal'),
        'state': fields.selection(STATE_SELECTION, 'State', readonly=True),
        'proses_birojasa_line': fields.one2many('wtc.proses.birojasa.line','proses_biro_jasa_id',string="Table Permohonan Faktur"), 
        'partner_id':fields.many2one('res.partner','Biro Jasa'),
        'tgl_dok':fields.date('Tgl Dokumen'),
        'no_dok' : fields.char('No Dokumen'),
        'description' : fields.char('Description'),
        'type' : fields.selection([('reg', 'REG'),('adv', 'ADV')], 'Type'),
        'amount_untaxed': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Untaxed Amount',
            store={
                'wtc.proses.birojasa': (lambda self, cr, uid, ids, c={}: ids, ['proses_birojasa_line'], 10),
                'wtc.proses.birojasa.line': (_get_engine, ['total_estimasi', 'tax_id', 'pajak_progressive', 'total_tagihan', 'koreksi'], 10),
            },
            multi='sums', help="The amount without tax.", track_visibility='always'),
        'amount_tax': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Taxes',
            store={
                'wtc.proses.birojasa': (lambda self, cr, uid, ids, c={}: ids, ['proses_birojasa_line'], 10),
                'wtc.proses.birojasa.line': (_get_engine, ['total_estimasi', 'tax_id', 'pajak_progressive', 'total_tagihan', 'koreksi'], 10),
            },
            multi='sums', help="The tax amount."),
        'amount_total': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total Tagihan',
            store={
                'wtc.proses.birojasa': (lambda self, cr, uid, ids, c={}: ids, ['proses_birojasa_line'], 10),
                'wtc.proses.birojasa.line': (_get_engine, ['total_estimasi', 'tax_id', 'pajak_progressive', 'total_tagihan', 'koreksi'], 10),
            },
            multi='sums', help="The total amount."),
        'total_approval_koreksi': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Approval Koreksi',
            store={
                'wtc.proses.birojasa': (lambda self, cr, uid, ids, c={}: ids, ['proses_birojasa_line'], 10),
                'wtc.proses.birojasa.line': (_get_engine, ['total_estimasi', 'tax_id', 'pajak_progressive', 'total_tagihan', 'koreksi'], 10),
            },
            multi='sums', help="The total amount."),
        'total_koreksi': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total Koreksi',
            store={
                'wtc.proses.birojasa': (lambda self, cr, uid, ids, c={}: ids, ['proses_birojasa_line'], 10),
                'wtc.proses.birojasa.line': (_get_engine, ['total_estimasi', 'tax_id', 'pajak_progressive', 'total_tagihan', 'koreksi'], 10),
            },
            multi='sums', help="The total amount."),
        'total_estimasi': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total Estimasi',
            store={
                'wtc.proses.birojasa': (lambda self, cr, uid, ids, c={}: ids, ['proses_birojasa_line'], 10),
                'wtc.proses.birojasa.line': (_get_engine, ['total_estimasi', 'tax_id', 'pajak_progressive', 'total_tagihan', 'koreksi'], 10),
            },
            multi='sums', help="The total amount."),  
        'total_progressive': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total Progresif',
            store={
                'wtc.proses.birojasa': (lambda self, cr, uid, ids, c={}: ids, ['proses_birojasa_line'], 10),
                'wtc.proses.birojasa.line': (_get_engine, ['total_estimasi', 'tax_id', 'pajak_progressive', 'total_tagihan', 'koreksi'], 10),
            },
            multi='sums', help="The total amount."),                               
        'note' : fields.text('Note..'),
        'invoiced': fields.boolean('Invoiced', readonly=True, copy=False),
        'invoice_method': fields.selection([('order','Based on generated draft invoice')], 'Invoicing Control', required=True,
            readonly=True),
        'document_copy':fields.boolean('Document Copy'),
        'ppn_jasa': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='PPN Jasa',
            store={
                'wtc.proses.birojasa': (lambda self, cr, uid, ids, c={}: ids, ['proses_birojasa_line'], 10),
                'wtc.proses.birojasa.line': (_get_engine, ['total_estimasi', 'tax_id', 'pajak_progressive', 'total_tagihan', 'koreksi'], 10),
            },
            multi='sums', help="The total amount."),         
        'engine_no': fields.related('proses_birojasa_line', 'name', type='char', string='No Engine'),
        'customer_stnk': fields.related('proses_birojasa_line', 'customer_stnk', type='many2one', relation='res.partner', string='Customer STNK'),
        'tax_id': fields.many2one('account.tax', string='Taxes'),
        'confirm_uid':fields.many2one('res.users',string="Confirmed by"),
        'confirm_date':fields.datetime('Confirmed on'),
        'cancel_uid':fields.many2one('res.users',string="Cancelled by"),
        'cancel_date':fields.datetime('Cancelled on'),
        'is_cancelled' : fields.boolean('Is Cancelled', readonly=True, copy=False),
        
    }
    _defaults = {
      'tanggal': _get_default_date,
      'tgl_dok': _get_default_date,
      'type':'reg',
      'state':'draft',
      'division' : 'Unit',
      'invoice_method':'order',
      'invoiced': 0,
      'document_copy':True,
      'branch_id': _get_default_branch,
     }
    
    def is_not_cancelled(self,cr,uid,ids,context=None):
        value = self.browse(cr,uid,ids)
        if value.is_cancelled :
            return False
        else :
            return True
        
    def create(self, cr, uid, vals, context=None):
        if not vals['proses_birojasa_line'] :
            raise osv.except_osv(('Perhatian !'), ("Tidak ada detail proses Biro Jasa. Data tidak bisa di save."))
        lot_proses = []
        for x in vals['proses_birojasa_line']:
            lot_proses.append(x.pop(2))
        lot_pool = self.pool.get('stock.production.lot')
        proses_pool = self.pool.get('wtc.proses.birojasa.line')
        vals['name'] = self.pool.get('ir.sequence').get_per_branch(cr, uid, vals['branch_id'], 'PRBJ')
        
        vals['tanggal'] = self._get_default_date(cr, uid, context)
        del[vals['proses_birojasa_line']]

        
        proses_id = super(wtc_proses_birojasa, self).create(cr, uid, vals, context=context) 

        if proses_id :         
            for x in lot_proses :
                lot_search = lot_pool.search(cr,uid,[
                            ('id','=',x['name'])
                            ])
                lot_browse = lot_pool.browse(cr,uid,lot_search)
                lot_browse.write({
                       'proses_biro_jasa_id':proses_id,
                       })   
                proses_pool.create(cr, uid, {
                                                     'name':lot_browse.id,
                                                     'proses_biro_jasa_id':proses_id,
                                                     'customer_stnk':lot_browse.customer_stnk.id,
                                                     'tgl_notice':x['tgl_notice'],
                                                     'no_notice':x['no_notice'],
                                                     'tgl_notice_copy':x['tgl_notice_copy'],
                                                     'no_notice_copy':x['no_notice_copy'],                                            
                                                     'total_estimasi':x['total_estimasi'],
                                                     'total_jasa':x['total_jasa'],
                                                     'pajak_progressive':lot_browse.inv_pajak_progressive_id.amount_total,
                                                     'total_tagihan':x['total_tagihan'],
#                                                      'tax_id':x['tax_id'],
                                                     'pajak_progressive_branch':x['pajak_progressive_branch'],
                                                    })
        return proses_id
    
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Proses Biro Jasa sudah di post ! tidak bisa didelete !"))

        lot_pool = self.pool.get('stock.production.lot')
        lot_search = lot_pool.search(cr,uid,[
                                           ('proses_biro_jasa_id','=',ids)
                                           ])
        lot_browse = lot_pool.browse(cr,uid,lot_search)
        for x in lot_browse :
            x.write({
                     'tgl_proses_birojasa': False,
                     'no_notice_copy': False,
                     'tgl_notice_copy':False,
                     })
        return super(wtc_proses_birojasa, self).unlink(cr, uid, ids, context=context)
    
    
    def button_dummy(self, cr, uid, ids, context=None):
        return True

    def wkf_confirm_birojasa(self, cr, uid, ids, context=None):
        val = self.browse(cr,uid,ids)
        lot_pool = self.pool.get('stock.production.lot') 
        tanggal = self._get_default_date(cr, uid, context)
        self.write(cr, uid, ids, {'state': 'approved','tanggal':tanggal,'confirm_uid':uid,'confirm_date':datetime.now()})
        for x in val.proses_birojasa_line :
            lot_search = lot_pool.search(cr,uid,[
                ('id','=',x.name.id)
                ])
            lot_browse = lot_pool.browse(cr,uid,lot_search)
            lot_browse.write({
                   'tgl_proses_birojasa':val.tanggal,
                   'no_notice_copy': x.no_notice_copy,
                   'tgl_notice_copy':x.tgl_notice_copy,
                   })   
          
        return True
   
    def wkf_action_cancel(self, cr, uid, ids, context=None):
        val = self.browse(cr,uid,ids)  
        lot_pool = self.pool.get('stock.production.lot') 
        for x in val.proses_birojasa_line :
            lot_search = lot_pool.search(cr,uid,[
                        ('id','=',x.name.id)
                        ])
            if not lot_search :
                raise osv.except_osv(('Perhatian !'), ("No Engine Tidak Ditemukan."))
            if lot_search :
                lot_browse = lot_pool.browse(cr,uid,lot_search)
                lot_browse.write({
                                  'proses_biro_jasa_id': False,
                                  'tgl_proses_birojasa':False,
                                  'no_notice_copy':False,
                                  'tgl_notice_copy':False,
                                })
        self.write(cr, uid, ids, {'state': 'cancel','cancel_uid':uid,'cancel_date':datetime.now()})
        return True

    def wkf_act_router(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'approved' })
        return True
    
    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        vals.get('proses_birojasa_line',[]).sort(reverse=True)

        collect = self.browse(cr,uid,ids)
        lot_penerimaan = []
        lot_pool = self.pool.get('stock.production.lot')
        line_pool = self.pool.get('wtc.proses.birojasa.line')
        lot = vals.get('proses_birojasa_line', False)
        
        if lot :
            for x,item in enumerate(lot) :
                lot_id = item[1]
                if item[0] == 2 :               
                    line_browse = line_pool.browse(cr,uid,lot_id)
                    lot_browse = lot_pool.browse(cr,uid,line_browse.name.id)
                    if not line_browse :
                        raise osv.except_osv(('Perhatian !'), ("Nomor Engine tidak ada didalam daftar Penerimaan Line"))
                    if not lot_browse :
                        raise osv.except_osv(('Perhatian !'), ("Nomor Engine tidak ada didalam daftar Engine Nomor"))
                    
                    vals.get('proses_birojasa_line', False) == []
                    lot_browse.write({
                                  'proses_biro_jasa_id': False,
                                  'tgl_proses_birojasa':False,
                                  'no_notice_copy':False,
                                  'tgl_notice_copy':False,
                                     })

                        
                elif item[0] == 0 :
                    values = item[2]
                    lot_browse = lot_pool.browse(cr,uid,values['name'])

                    if not lot_browse :
                        raise osv.except_osv(('Perhatian !'), ("Nomor Engine tidak ada didalam daftar Engine Nomor"))
                    
                    lot_browse.write({
                           'proses_biro_jasa_id':collect.id,
                           }) 
                    
        return super(wtc_proses_birojasa, self).write(cr, uid, ids, vals, context=context)
    
    def wkf_set_to_draft(self,cr,uid,ids):
        return self.write({'state':'draft'})       
     
    def action_invoice_create(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids, context={})[0]
        engine_obj = self.pool.get('stock.production.lot')
        obj_inv = self.pool.get('account.invoice')
        obj_ir_model = self.pool.get('ir.model')
        total_jasa = 0.00
        estimasi = 0.00
        move_ids = {}
        invoice_id = {}
        move_line_obj = self.pool.get('account.move.line')
        #ACCOUNT 
        config = self.pool.get('wtc.branch.config').search(cr,uid,[('branch_id','=',val.branch_id.id),
                                                                ])
        invoice_bbn = {}
        if config :
            config_browse = self.pool.get('wtc.branch.config').browse(cr,uid,config)
            progressive_debit_account = config_browse.tagihan_birojasa_progressive_journal_id.default_debit_account_id.id  
            progressive_credit_account = config_browse.tagihan_birojasa_progressive_journal_id.default_credit_account_id.id                
            bbn_debit_account_id = config_browse.tagihan_birojasa_bbn_journal_id.default_debit_account_id.id 
            bbn_credit_account_id = config_browse.tagihan_birojasa_bbn_journal_id.default_credit_account_id.id  
            journal_birojasa = config_browse.tagihan_birojasa_bbn_journal_id.id
            journal_progressive = config_browse.tagihan_birojasa_progressive_journal_id.id,
            if not journal_birojasa or not journal_progressive :
                raise osv.except_osv(_('Perhatian!'),
                    _('Jurnal Pajak Progressive atau Jurnal BBN Beli belum diisi, harap isi terlebih dahulu didalam branch config'))   
                             
        elif not config :
            raise osv.except_osv(_('Error!'),
                _('Please define Journal in Setup Division for this branch: "%s".') % \
                (val.branch_id.name))
                              
        move_list = []
        if val.amount_total < 1: 
            raise osv.except_osv(_('Perhatian!'),
                _('Mohon periksa kembali detail tagihan birojasa.')) 


        birojasa_id = obj_inv.create(cr,uid, {
                                    'name':val.name,
                                    'origin': val.name,
                                    'branch_id':val.branch_id.id,
                                    'division':val.division,
                                    'partner_id':val.partner_id.id,
                                    'date_invoice':val.tanggal,
                                    'reference_type':'none',
                                    'account_id':bbn_credit_account_id,
                                    'comment':val.note,
                                    'type': 'in_invoice',
                                    'supplier_invoice_number' : val.no_dok,
                                    'journal_id' : journal_birojasa,
                                    'document_date' : val.tgl_dok,
                                    'transaction_id': val.id,
                                    'model_id': obj_ir_model.search(cr, uid, [('model','=',val.__class__.__name__)])[0],
                                                                  
                                })   
        obj_line = self.pool.get('account.invoice.line') 
        selisih = val.total_koreksi + val.total_progressive

        for x in val.proses_birojasa_line :
            invoice_bbn[x.name.move_lines_invoice_bbn_id.account_id] = invoice_bbn.get(x.name.move_lines_invoice_bbn_id.account_id,0) + x.total_estimasi
            move_ids[x.name.move_lines_invoice_bbn_id.account_id] = move_ids.get(x.name.move_lines_invoice_bbn_id.account_id,[]) + [x.name.move_lines_invoice_bbn_id.id]
           
        for key,value in invoice_bbn.items() :                 
            obj_line.create(cr,uid, {
                                    'invoice_id':birojasa_id,
                                    'account_id':key.id,
                                    'partner_id':val.partner_id.id,
                                    'name': 'Total Estimasi',
                                    'quantity': 1,
                                    'origin': val.name,
                                    'price_unit':value  or 0.00,
                                    })
        
        obj_line.create(cr,uid, {
                                'invoice_id':birojasa_id,
                                'account_id':bbn_debit_account_id,
                                'partner_id':val.partner_id.id,
                                'name': 'Total Selisih',
                                'quantity': 1,
                                'origin': val.name,
                                'price_unit':selisih  or 0.00,
                                }) 
        
        if val.ppn_jasa > 0:
            obj_line.create(cr,uid, {
                                    'invoice_id':birojasa_id,
                                    'account_id':val.tax_id.account_collected_id.id,
                                    'partner_id':val.partner_id.id,
                                    'name': 'Total PPN Jasa',
                                    'quantity': 1,
                                    'origin': val.name,
                                    'price_unit':val.ppn_jasa  or 0.00,
                                    }) 
                       
        workflow.trg_validate(uid, 'account.invoice', birojasa_id, 'invoice_open', cr)  
        for key,value in invoice_bbn.items() : 
            rec_ids = [] 
            move = move_line_obj.search(cr,uid,[
                                                ('name','=','Total Estimasi'),
                                                ('invoice','=',birojasa_id),
                                                ('account_id','=',key.id)
                                                ])
            if move :
                self.pool.get('account.move.line').reconcile(cr, uid, move+move_ids[key])     
        return birojasa_id 
        
    def invoice_done(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'done'}, context=context)
        return True
    
    def view_invoice(self,cr,uid,ids,context=None):  
        val = self.browse(cr, uid, ids, context={})[0]
        obj_inv = self.pool.get('account.invoice')
        
        obj = obj_inv.search(cr,uid,[
                                     ('name','=',val.name),
                                     ('type','=','in_invoice')
                                     ])
        obj_hai = obj_inv.browse(cr,uid,obj).id
        return {
            'name': 'Supplier Invoice',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': obj_hai
            }
    
    
class wtc_proses_birojasa_line(osv.osv):
    _name = "wtc.proses.birojasa.line"

    def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
        res={}
        for line in self.browse(cr, uid, ids, context=context):
            price = (line.total_tagihan or 0.0) -  (line.total_estimasi or 0.0) - (line.pajak_progressive or 0.0)
            res[line.id]=price
        return res
    
    def onchange_price(self,cr,uid,ids,price_unit):
        value = {'total_estimasi_fake':0}
        if price_unit:
            value.update({'total_estimasi_fake':price_unit})  
        return {'value':value}    
   
    def _get_estimasi(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for price in self.read(cr, uid, ids, ['total_estimasi']):
            price_unit_show = price['total_estimasi']
            res[price['id']] = price_unit_show
        return res
    
    def _pajak_progressive(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for price in self.read(cr, uid, ids, ['total_estimasi']):
            price_unit_show = price['total_estimasi']
            res[price['id']] = price_unit_show   
        return res          
        
    _columns = {
                'name' : fields.many2one('stock.production.lot','No Engine',domain="[('tgl_proses_stnk','!=',False),('proses_biro_jasa_id','=',False),('state_stnk','=','proses_stnk'),('branch_id','=',parent.branch_id),('biro_jasa_id','=',parent.partner_id)]",change_default=True,),
                'proses_biro_jasa_id' : fields.many2one('wtc.proses.birojasa','Proses Biro Jasa'),
                'product_id':fields.related('name','product_id',type='many2one',relation='product.product',readonly=True,string='Product'),
                'customer_stnk':fields.related('name','customer_stnk',type='many2one',relation='res.partner',readonly=True,string='Customer STNK'),
                'tgl_notice' : fields.date('Tgl JTP Notice'),
                'no_notice' : fields.char('No Notice'),
                'tgl_notice_copy' : fields.date('Tgl JTP Notice'),
                'no_notice_copy' : fields.char('No Notice'),
                'total_estimasi' : fields.float('Total Estimasi',digits_compute=dp.get_precision('Account')),
                'total_estimasi_fake' : fields.function(_get_estimasi,string='Total Estimasi',digits_compute=dp.get_precision('Account')),
                'total_jasa' : fields.float('Jasa',digits_compute=dp.get_precision('Account')),
                'pajak_progressive' : fields.float('Pajak Progresif',digits_compute=dp.get_precision('Account')),
                'total_tagihan' : fields.float('Total Tagihan',digits_compute=dp.get_precision('Account')),
                'koreksi': fields.function(_amount_line, string='Koreksi',store=True,digits_compute=dp.get_precision('Account')),
                'tax_id': fields.many2many('account.tax', 'prose_birojasa_tax', 'proses_birojasa_line', 'tax_id', 'Taxes'),
                'type' : fields.selection([('reg', 'REG'),('adv', 'ADV')], 'Type',readonly=True),
                'pajak_progressive_branch' : fields.boolean(string="Pajak Progressive")
                }

    _sql_constraints = [
    ('unique_name_proses_biro_jasa_id', 'unique(name,proses_biro_jasa_id)', 'Detail Engine duplicate, mohon cek kembali !'),
]    
    def onchange_notice(self,cr,uid,ids,notice,tgl,doc):
        value = {}
        if notice :
            notice = notice.replace(' ', '').upper()
            value = {
                     'no_notice_copy':notice,
                     }            
        if not doc :
            if notice :
                value = {
                         'no_notice_copy':notice,
                         'no_notice':notice,
                         }
            if tgl :
                value = {
                         'tgl_notice':tgl,
                         }
        return {'value':value} 
    
                    
    def onchange_engine(self, cr, uid,ids, name,branch_id,partner_id,type,xxx):
        if not branch_id or not partner_id or not type:
            raise osv.except_osv(('No Branch Defined!'), ('Sebelum menambah detil transaksi,\n harap isi branch , type dan Biro Jasa terlebih dahulu.'))
        result = {}
        value = {}
        val = self.browse(cr,uid,ids)
        lot_obj = self.pool.get('stock.production.lot')
        lot_search = lot_obj.search(cr,uid,[
                                              ('id','=',name)
                                              ])
        lot_browse = lot_obj.browse(cr,uid,lot_search)  
        type_selection = str(type)

        so = self.pool.get('dealer.sale.order')
        so_search = so.search(cr,uid,[
                                      ('id','=',lot_browse.dealer_sale_order_id.id)
                                      ])
        so_browse = so.browse(cr,uid,so_search)
        pajak = self.pool.get('wtc.branch').browse(cr,uid,branch_id).pajak_progressive
        if name :
            total_estimasi = 0
            if lot_browse.move_lines_invoice_bbn_id:
                total_estimasi = lot_browse.move_lines_invoice_bbn_id.credit
            else:
                total_estimasi = lot_browse.invoice_bbn.amount_total 

            if lot_browse.no_notice_copy == False :
    
                value = {
                         'customer_stnk':lot_browse.customer_stnk.id,
                         'product_id':lot_browse.product_id.id,
                         'tgl_notice':lot_browse.tgl_notice,
                         'no_notice':lot_browse.no_notice,
                         'tgl_stnk':lot_browse.tgl_stnk,
                         'no_stnk':lot_browse.no_stnk,
                         'no_polisi':lot_browse.no_polisi,
                         # 'total_estimasi':lot_browse.invoice_bbn.amount_total,
                         'total_estimasi':total_estimasi,
                         'total_jasa':lot_browse.total_jasa,
                         'type':type_selection,
                         'no_notice_copy':lot_browse.no_notice,
                         'tgl_notice_copy':lot_browse.tgl_notice,
                         'pajak_progressive_branch':pajak,
                         'pajak_progressive':lot_browse.inv_pajak_progressive_id.amount_total,
                         }
    
            elif lot_browse.no_notice_copy :
                value = {
                         'customer_stnk':lot_browse.customer_stnk.id,
                         'product_id':lot_browse.product_id.id,
                         'tgl_notice':lot_browse.tgl_notice_copy,
                         'no_notice':lot_browse.no_notice_copy,
                         'tgl_stnk':lot_browse.tgl_stnk,
                         'no_stnk':lot_browse.no_stnk,
                         'no_polisi':lot_browse.no_polisi,
                         # 'total_estimasi':lot_browse.invoice_bbn.amount_total,
                         'total_estimasi':total_estimasi,
                         'type':type_selection,
                         'total_jasa':lot_browse.total_jasa,
                         'pajak_progressive_branch':pajak,
                         'pajak_progressive':lot_browse.inv_pajak_progressive_id.amount_total,
                         }
            
        result['value'] = value
        return result

class invoice_birojasa(osv.osv):
    _inherit = 'account.invoice'
   
    def invoice_pay_customer(self, cr, uid, ids, context=None):
        if not ids: return []
        dummy, view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account_voucher', 'view_vendor_receipt_dialog_form')
   
        inv = self.browse(cr, uid, ids[0], context=context)    
        tanggal = self._get_default_date(cr,uid,ids,context=context)

        if inv.type == "in_invoice" :
            birojasa = self.pool.get('wtc.proses.birojasa')
            birojasa_search = birojasa.search(cr,uid,[
                                            ('name','=',inv.origin)
                                            ])
            birojasa_browse = birojasa.browse(cr,uid,birojasa_search)
            if birojasa_search :
                birojasa_browse.write({'invoiced':True})
                for x in birojasa_browse.proses_birojasa_line :
                    lot = self.pool.get('stock.production.lot')
                    lot_search = lot.search(cr,uid,[
                                                    ('id','=',x.name.id)
                                                    ])
                    if lot_search :
                        lot_browse = lot.browse(cr,uid,lot_search)
                        lot_browse.write({'tgl_bayar_birojasa':tanggal})          
        return {
            'name':_("Pay Invoice"),
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'res_model': 'account.voucher',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
            'context': {
                'payment_expected_currency': inv.currency_id.id,
                'default_partner_id': self.pool.get('res.partner')._find_accounting_partner(inv.partner_id).id,
                'default_amount': inv.type in ('out_refund', 'in_refund') and -inv.residual or inv.residual,
                'default_reference': inv.name,
                'close_after_process': True,
                'invoice_type': inv.type,
                'invoice_id': inv.id,
                'default_type': inv.type in ('out_invoice','out_refund') and 'receipt' or 'payment',
                'type': inv.type in ('out_invoice','out_refund') and 'receipt' or 'payment'
            }
        }        