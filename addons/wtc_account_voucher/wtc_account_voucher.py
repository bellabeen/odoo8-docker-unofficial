from openerp.osv import osv, fields, orm
from lxml import etree
from openerp.tools.translate import _
from datetime import datetime
from openerp.exceptions import except_orm, Warning, RedirectWarning

class wtc_account_voucher_custom(osv.osv):
    _inherit = 'account.voucher'

    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')         
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                      
        return branch_ids 
       
    def _get_division(self, cr, uid, context=None):
        if context is None: context = {}
        return context.get('division', False)
    
    def _get_partner_type(self, cr, uid, context=None):
        name = 'supplier'
        if context is None: context = {}        
        if context.get('type') in ('receipt','sale') :
            name = 'customer'
        return name
    
    def _get_default_date(self,cr,uid,ids,context=None):
        return self.pool.get('wtc.branch').get_default_date(cr,uid,ids,context=context)
        
    def _get_default_date_model(self,cr,uid,context=None):
        return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)
    
    _columns = {
                'branch_id': fields.many2one('wtc.branch', string='Branch'),
                'division':fields.selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum'),('Finance','Finance')], 'Division', change_default=True, select=True),
                'inter_branch_id': fields.many2one('wtc.branch',string='Inter Branch'),
                'kwitansi_id': fields.many2one('wtc.register.kwitansi.line', string='Kwitansi'),
                'reason_cancel_kwitansi':fields.char('Reason'),
                'confirm_uid':fields.many2one('res.users',string="Validated by"),
                'confirm_date':fields.datetime('Validated on'),
                'cancel_uid':fields.many2one('res.users',string="Cancelled by"),
                'cancel_date':fields.datetime('Cancelled on'),   
                'date':fields.date('Date'),
                'cetak_ke':fields.integer('Cetak Kwitansi Ke'),
                'pajak_gabungan':fields.boolean('Faktur Pajak Gabungan',copy=False),   
                'faktur_pajak_id':fields.many2one('wtc.faktur.pajak.out',string='No Faktur Pajak',copy=False),    
                'no_faktur_pajak' : fields.char('No Faktur Pajak',copy=False),   
                'tgl_faktur_pajak' : fields.date('Tgl Faktur Pajak',copy=False),
                'is_hutang_lain' : fields.boolean('Is Hutang Lain ?',copy=False),   
                'partner_type':fields.selection([('principle','Principle'),('biro_jasa','Biro Jasa'),('forwarder','Forwarder'),\
                                                  ('supplier','General Supplier'),('finance_company','Finance Company'),\
                                                  ('customer','Customer'),('dealer','Dealer'),('ahass','Ahass')], 'Partner Type', change_default=True, select=True),
                'user_id' : fields.many2one('res.users', string='Responsible', change_default=True,readonly=True, states={'draft': [('readonly', False)]},track_visibility='always'),
                'kwitansi' : fields.boolean('Yg Sudah Print Kwitansi'),
                'transaksi' : fields.selection([
                        ('rutin','Rutin'),
                        ('tidak_rutin','Tidak Rutin'),
                    ], string='Transaksi',  index=True, change_default=True),
                'jenis_transaksi_id' : fields.many2one('wtc.payments.request.type', string='Tipe Transaksi', change_default=True,
                    readonly=True, states={'draft': [('readonly', False)]},
                    track_visibility='always'),
                'no_document' : fields.char(string='No Document', index=True),
                'tgl_document' : fields.date(string='Tgl Document',
                    readonly=True, states={'draft': [('readonly', False)]}, index=True,
                    help="Keep empty to use the current date", copy=False),
                'payments_request_ids' : fields.one2many('account.voucher.line', 'voucher_id',
                     readonly=True, copy=True),
                'paid_amount' : fields.float(string='Paid Amount')
                                                      
                }
    _defaults = {
        'branch_id': _get_default_branch,
        'division': _get_division,
        'journal_id': False,
        'date':_get_default_date,
        'cetak_ke':0,
        'partner_type':_get_partner_type,
    }

    def branch_id_other_payable(self,cr,uid,ids,branch_id,context=None):
        value = {}
        domain = {}
        if branch_id :
            domain['journal_id'] = [('branch_id','=',branch_id),('type','in',['bank','cash','edc'])]
        return {'domain':domain}
    
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        args = args or []
        if name :
            ids = self.search(cr, uid, [('number', operator, name)] + args, limit=limit, context=context or {})
            if not ids:
                ids = self.search(cr, uid, [('name', operator, name)] + args, limit=limit, context=context or {})
        else :
            ids = self.search(cr, uid, args, limit=limit, context=context or {})
        return self.name_get(cr, uid, ids, context or {})
    
    def journal_id_change_other_payable(self,cr,uid,ids,journal_id, context=None):
        val = {}
        account = False
        if journal_id :
            journal = self.pool.get('account.journal').browse(cr,uid,journal_id)
            if journal :
                account = journal.default_debit_account_id.id
                if not account :
                        raise except_orm(_('Warning!'), _('Konfigurasi jurnal account belum dibuat, silahkan setting dulu !'))
        val['account_id'] = account
        return {'value':val}
    
    def onchange_partner_id(self, cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date, context=None):
        res = super(wtc_account_voucher_custom,self).onchange_partner_id(cr,uid,ids,partner_id,journal_id,amount,currency_id,ttype,date,context=context)
        if ttype == 'purchase':
            if journal_id :
                journal = self.pool.get('account.journal').browse(cr,uid,journal_id)
                res['value']['account_id'] = journal.default_credit_account_id.id
        if ttype in ('receipt','payment') and res.get('value'):
            res['value']['line_ids'] = []
            res['value']['line_dr_ids'] = []
            res['value']['line_cr_ids'] = []  
        return res
    
    def transaksi_change(self,cr,uid,ids,transaksi,context=None):
        val = {}
        if transaksi :
            val['jenis_transaksi_id'] = False
        return {'value':val}
      
    def change_kwitansi(self,cr,uid,ids,kwitansi,context=None):
        vals = {}
        if kwitansi :
            vals['line_cr_ids'] = False
            vals['line_dr_ids'] = False
        return {'value':vals}
    
    def jenis_transaksi_change(self, cr, uid, ids, jenis_transaksi_id,branch_id):
        payments_request_histrory=[]
        if jenis_transaksi_id : 
            pr_pool = self.pool.get('account.voucher')
            pr_search = pr_pool.search(cr,uid,[('jenis_transaksi_id','=',jenis_transaksi_id),('branch_id','=',branch_id),])
            pr_pool2 = self.pool.get('account.voucher.line')
            pr_search2 = pr_pool2.search(cr,uid,[('voucher_id','=',pr_search),])
            payments_request_histrory = []
            if not pr_search2 :
                payments_request_histrory = []
            elif pr_search2 :
                pr_browse = pr_pool2.browse(cr,uid,pr_search2)           
                for x in pr_browse :
                    payments_request_histrory.append([0,0,{
                                     'account_id':x.account_id,
                                     'name':x.name,
                                     'amount':x.amount,
                                     'account_analytic_id':x.account_analytic_id
                    }])
        return {'value':{'payments_request_ids': payments_request_histrory}}
        
    def branch_id_onchange(self,cr,uid,ids,branch_id,context=None):
        dom={}
        val = {}
        edi_doc_list = ['&', ('active','=',True), ('type','!=','view')]
        dict=self.pool.get('wtc.account.filter').get_domain_account(cr,uid,ids,'other_receivable_header',context=None)
        edi_doc_list.extend(dict)      
        dom['account_id'] = edi_doc_list
        if branch_id :      
            period_id = self.pool['account.period'].find(cr, uid, dt=self._get_default_date(cr, uid, ids, context=context),context=context)           
            branch_search = self.pool.get('wtc.branch').browse(cr,uid,branch_id)
            branch_config = self.pool.get('wtc.branch.config').search(cr,uid,[
                                                                              ('branch_id','=',branch_id)
                                                                              ])
            if not branch_config :
                raise osv.except_osv(('Perhatian !'), ("Belum ada branch config atas branch %s !")%(branch_search.code))
            else :
                branch_config_browse = self.pool.get('wtc.branch.config').browse(cr,uid,branch_config)
                journal_other_receivable =  branch_config_browse.wtc_other_receivable_account_id.id
                if not journal_other_receivable :
                    raise osv.except_osv(('Perhatian !'), ("Journal Other Receivable belum diisi dalam branch %s !")%(branch_search.code))
                val['journal_id'] = journal_other_receivable
            val['period_id']  = period_id and period_id[0]        
        return {'domain':dom,'value': val} 
        
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
       
    def create(self,cr,uid,vals,context=None):
        raise osv.except_osv(('Perhatian !'), ("Tidak bisa menggunakan form ini !"))                 
        vals['date'] = self._get_default_date_model(cr, uid, context=context)
        if context.get('hutang_lain') :
            vals['is_hutang_lain'] = True  
        amount = 0.0 
        amount_cr = 0.0
        amount_dr = 0.0
        if vals.get('line_cr_ids') :
            for x in vals['line_cr_ids'] :
                amount += x[2]['amount']
                amount_cr += x[2]['amount']
                if x[2]['amount'] <= 0.0 :
                    raise osv.except_osv(('Perhatian !'), ("Amount detail tidak boleh minus atau nol"))
        if vals.get('line_dr_ids') :
            for x in vals['line_dr_ids'] :
                amount += x[2]['amount']
                amount_dr += x[2]['amount']
                if x[2]['amount'] <= 0.0 :
                    raise osv.except_osv(('Perhatian !'), ("Amount detail tidak boleh minus atau nol"))    
        if vals.get('amount') < 0.0 and vals.get('type') in  ('payment','receipt') and not context.get('hutang_lain'):
            raise osv.except_osv(('Perhatian !'), ("Paid Amount tidak boleh minus"))
        if vals.get('type') in ('payment','receipt') and not context.get('hutang_lain') :
            if vals.get('type') == 'receipt' and amount_dr == 0.0 and amount_cr == 0.0 and vals.get('payment_option') == 'without_writeoff' :
                raise osv.except_osv(('Perhatian !'), ('Data tidak bisa save, silahkan input dalam form Hutang Lain'))
            elif vals.get('type') == 'payment' and amount_dr == 0.0 and amount_cr == 0.0  :
                branch_id = self.pool.get('wtc.branch').browse(cr,uid,vals.get('branch_id'))
                if branch_id.branch_type != 'HO' :
                    raise osv.except_osv(('Perhatian !'), ('Akses error, hanya HHO yang boleh input !'))
            elif vals.get('writeoff_amount',0.0) < 0.0 and vals.get('payment_option') == 'without_writeoff' :
                raise osv.except_osv(('Perhatian !'), ("Nilai difference amount tidak boleh kurang dari nol !"))   
            elif vals.get('type') == 'receipt' and vals.get('line_cr_ids') and  vals.get('payment_option') == 'without_writeoff' and vals.get('writeoff_amount',0.0) > 0.0 :
                raise osv.except_osv(('Perhatian !'), ("Nilai difference amount tidak boleh lebih dari nol !"))   
            elif vals.get('type') == 'payment' and vals.get('line_dr_ids') and vals.get('payment_option') == 'without_writeoff' and vals.get('writeoff_amount',0.0) > 0.0 :
                raise osv.except_osv(('Perhatian !'), ("Nilai difference amount tidak boleh lebih dari nol !"))   
            elif vals.get('type') == 'receipt' and vals.get('line_cr_ids') and not vals.get('line_dr_ids') and vals.get('amount') == 0.0 :
                raise osv.except_osv(('Perhatian !'), ("Tidak bisa memotong AR, mohon periksa kembali data anda !"))   
            elif vals.get('type') == 'payment' and vals.get('line_dr_ids') and not vals.get('line_cr_ids') and vals.get('amount') == 0.0 :
                raise osv.except_osv(('Perhatian !'), ("Tidak bisa memotong AP, mohon periksa kembali data anda !"))                 
            debit = round(vals.get('amount',0.0),2) + round(amount_dr,2)
            credit = round(amount_cr,2)            
            if vals.get('type') == 'receipt' and amount_dr != 0.0 :
                if credit > debit :
                    raise osv.except_osv(('Perhatian !'), ("Nilai Difference Amount tidak boleh minus !"))              
            elif vals.get('type') == 'payment' and amount_cr != 0.0 :               
                if credit < debit :
                    raise osv.except_osv(('Perhatian !'), ("Nilai Difference Amount tidak boleh minus !"))              
                                      
        if not vals.get('period_id') :
            vals['period_id'] = self.pool['account.period'].find(cr, uid,dt=get_default_date, context=context)[0]
        vals['number'] = self.generate_sequence(cr, uid, vals, context=context)
#         self.cek_double_entries(cr, uid, vals, amount_dr, context=context)
        
        
        res = super(wtc_account_voucher_custom,self).create(cr,uid,vals,context=context)
        value = self.browse(cr,uid,res)

        if (not value.line_cr_ids or value.line_cr_ids == []) and value.is_hutang_lain :
            raise osv.except_osv(('Perhatian !'), ("Detail harus diisi !")) 
        elif (not value.line_cr_ids or value.line_cr_ids == []) and value.type == 'sale' and not value.is_hutang_lain :
            raise osv.except_osv(('Perhatian !'), ("Detail harus diisi !"))
        elif (not value.line_dr_ids or value.line_dr_ids == []) and value.type == 'purchase' :
              raise osv.except_osv(('Perhatian !'), ("Detail harus diisi !"))           
        if value.type in ('sale','purchase') or value.type == 'receipt' and value.is_hutang_lain :
            self.compute_tax(cr,uid,value.id,context)
            if value.payment_option == 'without_writeoff' :
                self.cek_amount_total_per_detail(cr, uid, value.id, value, amount, context=context)         
        return res
    
    def cek_double_entries(self,cr,uid,vals,amount_dr,context=None):
        
        if vals.get('type') == 'payment' or (vals.get('type') == 'receipt' and amount_dr != 0.0) :
                
                move_line_id = []
                if vals.get('type') == 'payment' :
                    type = 'dr'
                    if len(vals['line_dr_ids']) > 0 :
                        for x in vals['line_dr_ids'] :
                            mv_id = self.pool.get('account.move.line').browse(cr,uid,[x[2]['move_line_id']])
                            move_line_id.append(mv_id.id)                    
                elif vals.get('type') == 'receipt' :
                    type = 'cr'
                    for x in vals['line_cr_ids'] :
                        mv_id = self.pool.get('account.move.line').browse(cr,uid,[x[2]['move_line_id']])
                        move_line_id.append(mv_id.id)
                
                if len(move_line_id) > 0 :
                    move_line_id = str(tuple(move_line_id)).replace(',)', ')')
                    query = """
                    select avl.move_line_id, 
                    aml.name, aml.ref, av.number
                    from account_voucher av
                    inner join account_voucher_line avl on av.id = avl.voucher_id
                    inner join account_move_line aml on avl.move_line_id = aml.id
                    where av.state in ('draft','waiting_for_approval','approved','request_approval','confirmed')
                    and avl.type = '%s'
                    and avl.move_line_id in %s"""%(type,move_line_id)
                    cr.execute(query)
                    data = cr.fetchall()
                    if len(data) > 0 :
                        message = ""
                        for x in data :                 
                            message += "Detil %s %s sudah ditarik di nomor %s. \r\n "%(x[1],x[2],x[3])
                        raise osv.except_osv(('Perhatian !'), (message))
                
        return True                                                                      
                                                     
    def cek_amount_total_per_detail(self,cr,uid,ids,value,amount,context=None):
        amount_value = round(value.amount,2)
        amount_and_tax = round(amount,2)+round(value.tax_amount,2)
        diff_total = amount_value - amount_and_tax
        if value.type in ('sale','purchase') :
            if diff_total != 0 :
                raise osv.except_osv(('Perhatian !'), ("Amount total harus sama dengan total detail Rp.%s")%(amount))                               
        elif value.type == 'receipt' and value.is_hutang_lain :
            if diff_total != 0 :
                raise osv.except_osv(('Perhatian !'), ("Amount total harus sama dengan total detail Rp.%s")%(amount))            
        return True
                
    def write(self,cr,uid,ids,vals,context=None):
        if not context.get('pembatalan') and not (len(vals) == 1 and ('message_last_post' in vals)) :
            raise osv.except_osv(('Perhatian !'), ("Tidak bisa menggunakan form ini !"))                 
        
        res = super(wtc_account_voucher_custom,self).write(cr,uid,ids,vals)
        value = self.browse(cr,uid,ids)
        if (not value.line_cr_ids or value.line_cr_ids == []) and value.is_hutang_lain :
            raise osv.except_osv(('Perhatian !'), ("Detail harus diisi !")) 
        elif (not value.line_cr_ids or value.line_cr_ids == []) and value.type == 'sale' and not value.is_hutang_lain :
            raise osv.except_osv(('Perhatian !'), ("Detail harus diisi !"))
        elif (not value.line_dr_ids or value.line_dr_ids == []) and value.type == 'purchase' :
              raise osv.except_osv(('Perhatian !'), ("Detail harus diisi !"))                
        if vals.get('type') or vals.get('line_cr_ids') or vals.get('line_dr_ids') or vals.get('amount') or vals.get('writeoff_amount') or vals.get('payment_option') :
            if value.type in ('sale','purchase') or (value.type =='receipt' and value.is_hutang_lain) :
                if vals.get('tax_id') or vals.get('line_cr_ids') or vals.get('line_dr_ids'):
                    self.compute_tax(cr,uid,ids,context) 
            else :             
                self.check_amount_with_or_not_writeoff(cr, uid, ids, context=context)                                                                                                                                                                                             
        return res       
        
    def account_move_get(self, cr, uid, voucher_id, context=None):
        res = super(wtc_account_voucher_custom,self).account_move_get(cr,uid,voucher_id,context=context)
        return res
    
    def cek_double_entries_write(self,cr,uid,ids,amount_dr,context=None):
        voucher = self.browse(cr,uid,ids)
        if voucher.type == 'payment' or (voucher.type == 'receipt' and amount_dr != 0.0) :
                
                move_line_id = []
                if voucher.type == 'payment' :
                    type = 'dr'
                    if len(voucher.line_dr_ids) > 0 :
                        for x in voucher.line_dr_ids :
                            move_line_id.append(x.move_line_id.id)                    
                elif voucher.type == 'receipt' :
                    type = 'cr'
                    for x in voucher.line_cr_ids :
                        move_line_id.append(x.move_line_id.id)
                
                if len(move_line_id) > 0 :
                    move_line_id = str(tuple(move_line_id)).replace(',)', ')')
                    query = """
                    select avl.move_line_id, 
                    aml.name, aml.ref, av.number
                    from account_voucher av
                    inner join account_voucher_line avl on av.id = avl.voucher_id
                    inner join account_move_line aml on avl.move_line_id = aml.id
                    where av.state in ('draft')
                    and av.id not in (%s)
                    and avl.type = '%s'
                    and avl.move_line_id in %s"""%(voucher.id,type,move_line_id)
                    cr.execute(query)
                    data = cr.fetchall()
                    if len(data) > 0 :
                        message = ""
                        for x in data :                 
                            message += "Detil %s %s sudah ditarik di nomor %s. \r\n "%(x[1],x[2],x[3])
                        raise osv.except_osv(('Perhatian !'), (message))
                
        return True
        
    def check_amount_with_or_not_writeoff(self,cr,uid,ids,context=None):
        voucher = self.browse(cr,uid,ids)
        amount = 0.0 
        amount_cr = 0.0
        amount_dr = 0.0      
        if voucher.line_cr_ids :
            for x in voucher.line_cr_ids :
                amount += x.amount
                amount_cr += x.amount
                if x.amount <= 0.0 :
                    raise osv.except_osv(('Perhatian !'), ("Amount %s tidak boleh minus atau nol")%(x.move_line_id.name))                               
                
        if voucher.line_dr_ids :
            for x in voucher.line_dr_ids :
                amount += x.amount
                amount_dr += x.amount
                if x.amount <= 0.0 :
                    raise osv.except_osv(('Perhatian !'), ("Amount %s tidak boleh minus atau nol")%(x.move_line_id.name))    
        amount += voucher.tax_amount              
        if voucher.amount < 0.0 and voucher.type in ('payment','receipt') and not voucher.is_hutang_lain:
                raise osv.except_osv(('Perhatian !'), ("Paid Amount tidak boleh minus")) 
        if voucher.type in ('payment','receipt') and not voucher.is_hutang_lain :    
            amount_writeoff = voucher.writeoff_amount or 0.0      
            amount2 = self._compute_writeoff_amount(cr, uid, voucher.line_dr_ids, voucher.line_cr_ids, voucher.amount, voucher.type)
            if voucher.type == 'receipt' and amount_dr == 0.0 and amount_cr == 0.0 and voucher.payment_option == 'without_writeoff' :
                raise osv.except_osv(('Perhatian !'), ('Data tidak bisa save, silahkan input dalam form Hutang Lain'))            
            elif amount2 < 0.0 and voucher.payment_option == 'without_writeoff' :
                raise osv.except_osv(('Perhatian !'), ("Nilai difference amount tidak boleh kurang dari nol !"))   
            elif voucher.type == 'receipt' and voucher.line_cr_ids and voucher.payment_option == 'without_writeoff' and voucher.writeoff_amount > 0.0 :
                raise osv.except_osv(('Perhatian !'), ("Nilai difference amount tidak boleh lebih dari nol !"))   
            elif voucher.type == 'payment' and voucher.line_dr_ids and voucher.payment_option == 'without_writeoff' and voucher.writeoff_amount > 0.0 :
                raise osv.except_osv(('Perhatian !'), ("Nilai difference amount tidak boleh lebih dari nol !"))   
            elif voucher.type == 'receipt' and voucher.line_cr_ids and not voucher.line_dr_ids and voucher.amount == 0.0 :
                raise osv.except_osv(('Perhatian !'), ("Tidak bisa memotong AR, mohon periksa kembali data anda !"))   
            elif voucher.type == 'payment' and voucher.line_dr_ids and not voucher.line_cr_ids and voucher.amount == 0.0 :
                raise osv.except_osv(('Perhatian !'), ("Tidak bisa memotong AP, mohon periksa kembali data anda !"))                
            debit = round(voucher.amount,2) + round(amount_dr,2)
            credit = round(amount_cr,2)            
            if voucher.type  == 'receipt' and amount_dr != 0.0 :
                if credit > debit :
                    raise osv.except_osv(('Perhatian !'), ("Nilai Difference Amount tidak boleh minus !"))              
            elif voucher.type == 'payment' and amount_cr != 0.0   :
                if credit < debit :
                    raise osv.except_osv(('Perhatian !'), ("Nilai Difference Amount tidak boleh minus !"))              
#             self.cek_double_entries_write(cr, uid, ids, amount_dr, context=context)              
        if voucher.type in ('sale','purchase') or voucher.type == 'receipt' and voucher.is_hutang_lain :
            if voucher.payment_option == 'without_writeoff' :
                self.cek_amount_total_per_detail(cr, uid, ids, voucher, amount, context=context) 
        return True        
    
    def generate_sequence(self,cr,uid,vals,context=None):
        name = '/'
        if vals.get('is_hutang_lain') == True and vals.get('type') == 'receipt' :
            name = self.pool.get('ir.sequence').get_per_branch(cr,uid,vals.get('branch_id'),'HL') 
        elif not vals.get('is_hutang_lain') and vals.get('type') == 'receipt' :
            name = self.pool.get('ir.sequence').get_per_branch(cr,uid,vals.get('branch_id'),'AR') 
        elif vals.get('type') == 'payment' :
            name = self.pool.get('ir.sequence').get_per_branch(cr,uid,vals.get('branch_id'),'PV') 
        elif vals.get('type') == 'sale' :
            name = self.pool.get('ir.sequence').get_per_branch(cr,uid,vals.get('branch_id'),'DN')
        elif vals.get('type') == 'purchase' :
            name = self.pool.get('ir.sequence').get_per_branch(cr,uid,vals.get('branch_id'),'NC')                                
        return name   

             
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(wtc_account_voucher_custom, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        obj_active = self.browse(cr,uid,context.get('active_ids',[]))
        if not context.get('portal') :
            branch_id = obj_active.branch_id.id
            kwitansi=obj_active.kwitansi_id.id
            doc = etree.XML(res['arch'])
            nodes = doc.xpath("//field[@name='kwitansi_id']")
            for node in nodes:
                    node.set('domain', '[("payment_id","=",False),("branch_id", "=", '+ str(branch_id)+'),("state","=","open")]')
            res['arch'] = etree.tostring(doc)
        return res

    def onchange_price(self, cr, uid, ids, line_ids, tax_id, partner_id=False, context=None):
        context = context or {}
        tax_pool = self.pool.get('account.tax')
        partner_pool = self.pool.get('res.partner')
        position_pool = self.pool.get('account.fiscal.position')
        if not line_ids:
            line_ids = []
        res = {
            'tax_amount': False,
            'amount': False,
        }
        voucher_total = 0.0
 
        # resolve the list of commands into a list of dicts
        line_ids = self.resolve_2many_commands(cr, uid, 'line_ids', line_ids, ['amount'], context)
 
        total_tax = 0.0
        for line in line_ids:
            line_amount = 0.0
            line_amount = line.get('amount',0.0)
 
            if tax_id:
                tax = [tax_pool.browse(cr, uid, tax_id, context=context)]
                if partner_id:
                    partner = partner_pool.browse(cr, uid, partner_id, context=context) or False
                    taxes = position_pool.map_tax(cr, uid, partner and partner.property_account_position or False, tax)
                    tax = tax_pool.browse(cr, uid, taxes, context=context)
 
                if not tax[0].price_include:
                    for tax_line in tax_pool.compute_all(cr, uid, tax, line_amount, 1).get('taxes', []):
                        total_tax += tax_line.get('amount')
 
            voucher_total += line_amount
        total = voucher_total + total_tax
 
        res.update({
            'amount': total or voucher_total,
            'tax_amount': total_tax
        })
        if tax_id == False :
            res.update({
                'pajak_gabungan':False,
                'no_faktur_pajak': False,
                'tgl_faktur_pajak':False,
                'account_analytic_id':False,
            })            
        return {
            'value': res
        }
            
    def branch_onchange_payment_request(self,cr,uid,ids,branch_id,context=None):
        account_id=False
        journal_id=False
        val ={}
        if branch_id :
            branch_config =self.pool.get('wtc.branch.config').search(cr,uid,[
                                                                             ('branch_id','=',branch_id)])
            branch_config_browse = self.pool.get('wtc.branch.config').browse(cr,uid,branch_config)
            journal_id=branch_config_browse.wtc_payment_request_account_id.id
            account_id=branch_config_browse.wtc_payment_request_account_id.default_credit_account_id.id
            if not journal_id :
                    raise except_orm(_('Warning!'), _('Konfigurasi jurnal cabang belum dibuat, silahkan setting dulu !'))
            if not account_id :
                    raise except_orm(_('Warning!'), _('Konfigurasi jurnal account cabang belum dibuat, silahkan setting dulu !'))
        val['account_id'] = account_id
        val['journal_id'] = journal_id
        return {'value':val}
                    
    def branch_change(self, cr, uid, ids, branch, context=None):
        value = {}
        domain = {}
        if branch :
            period_id = self.pool['account.period'].find(cr, uid, dt=self._get_default_date(cr, uid, ids, context=context),context=context)
            value['inter_branch_id'] = branch
            domain['journal_id'] = [('branch_id','=',branch),('type','in',['bank','cash','edc'])]
            value['journal_id'] = False
            value['line_ids'] = []
            value['line_cr_ids'] = []
            value['line_dr_ids'] = []
            value['period_id'] = period_id and period_id[0]
            edi_doc_list2 = ['&', ('active','=',True), ('type','=','other')]
            dict=self.pool.get('wtc.account.filter').get_domain_account(cr,uid,ids,'payments',context=None)
            edi_doc_list2.extend(dict)      
            domain['writeoff_acc_id'] = edi_doc_list2            
        return {'value':value, 'domain':domain}
        
    def inter_branch_receipt_change(self, cr, uid, ids, inter_branch, context=None):
        value = {}
        if inter_branch :
            value['line_ids'] = []
            value['line_cr_ids'] = []
            value['line_dr_ids'] = []            
        return {'value':value}    

    def inter_branch_payment_change(self, cr, uid, ids, inter_branch, context=None):
        value = {}
        if inter_branch :
            value['line_cr_ids'] = []
            value['line_ids'] = []
            value['line_cr_ids'] = []
            value['line_dr_ids'] = []
        return {'value':value}
    
    def action_move_line_create(self, cr, uid, ids, context=None):
        res = super(wtc_account_voucher_custom,self).action_move_line_create(cr, uid, ids, context=context)
        for voucher_data in self.browse(cr,uid,ids) :
            if voucher_data.move_ids :
                for line in voucher_data.move_ids :
                    if voucher_data.writeoff_acc_id :
                        if line.account_id == voucher_data.writeoff_acc_id and line.name == voucher_data.comment:
                            line.write({'branch_id':voucher_data.inter_branch_id.id,'division':voucher_data.division,'date_maturity':voucher_data.date_due})
                    if not line.branch_id :
                        line.write({'branch_id':voucher_data.branch_id.id,'division':voucher_data.division,'date_maturity':voucher_data.date_due})
                    if not line.division :
                        line.write({'division':voucher_data.division,'date_maturity':voucher_data.date_due})                        
                if voucher_data.type in ('receipt', 'payment') and voucher_data.branch_id != voucher_data.inter_branch_id :        
                    self.interco_move_line_create(cr, uid, ids, voucher_data.move_ids,voucher_data,context=context)
        return res
        
    def onchange_division(self,cr,uid,ids,division,context=None):
        value = {}
        if division :
            value['line_cr_ids'] = []
            value['line_ids'] = []
            value['line_cr_ids'] = []
            value['line_dr_ids'] = []
        return {'value':value}
                        
    def onchange_journal_account_voucher(self, cr, uid, ids, journal_id, line_ids, tax_id, partner_id, date, amount, ttype, company_id, context=None):
        if context is None:
            context = {}
        if not journal_id:
            return False
        journal_pool = self.pool.get('account.journal')
        journal = journal_pool.browse(cr, uid, journal_id, context=context)
        account_id = journal.default_credit_account_id or journal.default_debit_account_id
        tax_id = False
        if account_id and account_id.tax_ids:
            tax_id = account_id.tax_ids[0].id
        vals = {'value':{} }
        if ttype in ('sale', 'purchase'):
#             vals = self.onchange_price(cr, uid, ids, line_ids, tax_id, partner_id, context)
            vals['value'].update({'tax_id':tax_id,'amount': amount})
        currency_id = False
        if journal.currency:
            currency_id = journal.currency.id
        else:
            currency_id = journal.company_id.currency_id.id
        period_id = self.pool['account.period'].find(cr, uid, dt=self._get_default_date(cr, uid, ids, context),context=dict(context, company_id=company_id))
        vals['value'].update({
            'currency_id': currency_id,
            'payment_rate_currency_id': currency_id,
            'period_id' : period_id and period_id[0],
            'account_id':account_id
        })
        return vals
                            
    def interco_move_line_create(self,cr,uid,ids,move_lines,voucher_data,context=None):
        #Make journal intercompany
        branch_rekap = {}    
        branch_pool = self.pool.get('wtc.branch')        
        if voucher_data.inter_branch_id :      
            move_line = self.pool.get('account.move.line')          
            #Merge Credit and Debit by Branch                          
            for x in move_lines :
                if x.branch_id not in branch_rekap :
                    branch_rekap[x.branch_id] = {}
                    branch_rekap[x.branch_id]['debit'] = x.debit
                    branch_rekap[x.branch_id]['credit'] = x.credit
                else :
                    branch_rekap[x.branch_id]['debit'] += x.debit
                    branch_rekap[x.branch_id]['credit'] += x.credit    
                                                
            config = branch_pool.search(cr,uid,[('id','=',voucher_data.branch_id.id)])
            config_destination = branch_pool.search(cr,uid,[('id','=',voucher_data.inter_branch_id.id)])
            
            if config :
                config_browse = branch_pool.browse(cr,uid,config)
                inter_branch_account_id = config_browse.inter_company_account_id.id
                if not inter_branch_account_id :
                    raise osv.except_osv(('Perhatian !'), ("Account Inter Company belum diisi dalam Master branch %s !")%(voucher_data.branch_id.name))
            elif not config :
                    raise osv.except_osv(('Perhatian !'), ("Account Inter Company belum diisi dalam Master branch %s !")%(voucher_data.branch_id.name))
            
            if config_destination :
                config_browse_destination = branch_pool.browse(cr,uid,config_destination)
                inter_branch_terima_account_id = config_browse_destination.inter_company_account_id.id
                if not inter_branch_terima_account_id :
                    raise osv.except_osv(('Perhatian !'), ("Account Inter Company belum diisi dalam Master branch %s !")%(voucher_data.inter_branch_terima_account_id.name))   
            for key,value in branch_rekap.items() :
                if key != voucher_data.branch_id :
                    balance = value['debit']-value['credit']
                    debit = abs(balance) if balance < 0 else 0
                    credit = balance if balance > 0 else 0
                    
                    if balance != 0:
                        move_line_create = {
                            'name': _('Interco Account Voucher %s')%(key.name),
                            'ref':_('Interco Account Voucher %s')%(key.name),
                            'account_id': inter_branch_account_id,
                            'move_id': voucher_data.move_id.id,
                            'journal_id': voucher_data.journal_id.id,
                            'period_id': voucher_data.period_id.id,
                            'date': voucher_data.date,
                            'debit': debit,
                            'credit': credit,
                            'branch_id' : key.id,
                            'division' : voucher_data.division,
                            'partner_id' : voucher_data.partner_id.id                    
                        }    
                        inter_first_move = move_line.create(cr, uid, move_line_create, context)    
                                 
                        move_line2_create = {
                            'name': _('Interco Account Voucher %s')%(voucher_data.branch_id.name),
                            'ref':_('Interco Account Voucher %s')%(voucher_data.branch_id.name),
                            'account_id': inter_branch_terima_account_id,
                            'move_id': voucher_data.move_id.id,
                            'journal_id': voucher_data.journal_id.id,
                            'period_id': voucher_data.period_id.id,
                            'date': voucher_data.date,
                            'debit': credit,
                            'credit': debit,
                            'branch_id' : voucher_data.branch_id.id,
                            'division' : voucher_data.division,
                            'partner_id' : voucher_data.partner_id.id                       
                        }    
                        inter_second_move = move_line.create(cr, uid, move_line2_create, context) 
        return True

    def voucher_move_line_create(self, cr, uid, voucher_id, line_total, move_id, company_currency, current_currency, context=None):
        voucher = super(wtc_account_voucher_custom,self).voucher_move_line_create(cr,uid,voucher_id, line_total, move_id, company_currency, current_currency, context=context)
        # method super returns (0.0,[[123,124],[125,126]]) 
#         line_total, rec_list_ids = super(wtc_account_voucher_custom,self).voucher_move_line_create(cr,uid,voucher_id, line_total, move_id, company_currency, current_currency, context=context)
        vals = self.browse(cr,uid,voucher_id)
        move_line = self.pool.get('account.move.line')
        move_obj = self.pool.get('account.move.line')
        if vals.type in ('receipt', 'payment') :
            if vals.inter_branch_id :
                inter_branch = vals.inter_branch_id.id
            else :
                inter_branch = vals.branch_id.id          
            move_ids = []
            for x in voucher[1] :
                move_ids += x
            move_browse = move_obj.browse(cr,uid,move_ids)
            for value in move_browse :
                if value.move_id.id != move_id :
                    continue
                if vals.type == 'receipt' :
                    if value.account_id.type == 'payable' :
                        value.write({'branch_id':vals.branch_id.id,'division':vals.division})
                    else :
                        value.write({'branch_id':inter_branch,'division':vals.division})
                elif vals.type == 'payment' :
                    if value.account_id.type == 'receivable' :
                        value.write({'branch_id':vals.branch_id.id,'division':vals.division})
                    else :
                        value.write({'branch_id':inter_branch,'division':vals.division})       
                       
        return voucher   
    
    def onchange_partner_type(self,cr,uid,ids,partner_type,context=None):
        dom={}        
        val={}
        if partner_type :
            val['partner_id'] = False
            if partner_type == 'biro_jasa' :
                dom['partner_id'] = [('biro_jasa','!=',False)]
            elif partner_type == 'forwarder' :
                dom['partner_id'] = [('forwarder','!=',False)]                
            elif partner_type == 'supplier' :
                dom['partner_id'] = [('supplier','!=',False)]                
            elif partner_type == 'finance_company' :
                dom['partner_id'] = [('finance_company','!=',False)]                
            elif partner_type == 'customer' :
                dom['partner_id'] = [('customer','!=',False)]                
            elif partner_type == 'dealer' :
                dom['partner_id'] = [('dealer','!=',False)] 
            elif partner_type == 'ahass' :
                dom['partner_id'] = [('ahass','!=',False)]     
            elif partner_type == 'principle' :
                dom['partner_id'] = [('principle','!=',False)]                                   
        return {'domain':dom,'value':val} 
            
    def print_wizard_kwitansi(self,cr,uid,ids,context=None):  
        obj_claim_kpb = self.browse(cr,uid,ids)
        obj_ir_view = self.pool.get("ir.ui.view")
        obj_ir_view_search= obj_ir_view.search(cr,uid,[("name", "=", 'kwitansi.wizard.customer.payment'), ("model", "=", 'account.voucher'),])
        obj_ir_view_browse = obj_ir_view.browse(cr,uid,obj_ir_view_search)
        return {
            'name': 'Kwitansi',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.voucher',
            'type': 'ir.actions.act_window',
            'view_id' : obj_ir_view_browse.id,
            'target': 'new',
            'nodestroy': True,
            'res_id': obj_claim_kpb.id,
            'context': context
            }
        
    def reg_kwitansi(self, cr, uid, ids, vals, context=None):
        res = super(wtc_account_voucher_custom, self).write(cr, uid, ids, vals, context=context)
        return res

    def recompute_voucher_lines(self, cr, uid, ids, partner_id, journal_id, price, currency_id, ttype, date, context=None):
        vals = super(wtc_account_voucher_custom, self).recompute_voucher_lines(cr, uid, ids, partner_id, journal_id, price, currency_id, ttype, date, context=context)
        if vals :
            if 'line_cr_ids' in vals['value'] :      
                del(vals['value']['line_cr_ids'])    
                                    
            if 'line_dr_ids' in vals['value'] :  
                del(vals['value']['line_dr_ids'])
                
        return vals

    def proforma_voucher(self, cr, uid, ids, context=None):
        periods = self.pool.get('account.period').find(cr, uid,dt=self._get_default_date(cr, uid, ids, context), context=context)
        if periods :
            periods = periods and periods[0]
        self.write(cr,uid,ids,{'confirm_uid':uid,'confirm_date':datetime.now(),'date':self._get_default_date(cr, uid, ids, context=context),'period_id':periods})
        vals = super(wtc_account_voucher_custom,self).proforma_voucher(cr, uid, ids, context=context)
        value = self.browse(cr,uid,ids)
        if not value.amount and value.journal_id.type == 'edc'  :
            raise osv.except_osv(('Perhatian !'), ("'Paid Amount' harus diisi untuk pembayaran menggunakan EDC"))
        if value.tax_id and not value.pajak_gabungan and value.type == 'sale' :
            no_pajak = self.pool.get('wtc.faktur.pajak.out').get_no_faktur_pajak(cr,uid,ids,'account.voucher',context=context)
        return vals
    
    def create_new_move(self, cr, uid, ids, id_old_move, context=None):
        move_pool = self.pool.get('account.move')
        new_move_line_id = False
        new_id_move = move_pool.copy(cr, uid, id_old_move)
        new_move_id = move_pool.browse(cr, uid, new_id_move)
        for line in new_move_id.line_id :
            if line.account_id.type in ('payable','receivable') :
                new_move_line_id = line.id
            credit = line.debit
            debit = line.credit
            line.write({'debit':debit,'credit':credit})
            
        return new_move_line_id
    
    def cancel_voucher(self, cr, uid, ids, context=None):
        if context == None :
            context = {}        
        self.write(cr,uid,ids,{'cancel_uid':uid,'cancel_date':datetime.now()})
        reconcile_pool = self.pool.get('account.move.reconcile')
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        for voucher in self.browse(cr, uid, ids, context=context):
            # refresh to make sure you don't unlink an already removed move
            voucher.refresh()
            for line in voucher.move_ids:
                # refresh to make sure you don't unreconcile an already unreconciled entry
                line.refresh()
                values = {}
                if line.reconcile_id:
                    move_lines = [move_line.id for move_line in line.reconcile_id.line_id]
                    new_move_line_id = self.create_new_move(cr, uid, ids, line.move_id.id, context)
                    move_lines.append(new_move_line_id)
                    reconcile_pool.unlink(cr, uid, [line.reconcile_id.id])
                    if len(move_lines) >= 2:
                        move_line_pool.reconcile_partial(cr, uid, move_lines, 'auto',context=context)
                elif line.reconcile_partial_id :
                    move_lines = [move_line.id for move_line in line.reconcile_partial_id.line_partial_ids]
                    new_move_line_id = self.create_new_move(cr, uid, ids, line.move_id.id, context)
                    move_lines.append(new_move_line_id)
                    reconcile_pool.unlink(cr, uid, [line.reconcile_partial_id.id])
                    if len(move_lines) >= 2:
                        move_line_pool.reconcile_partial(cr, uid, move_lines, 'auto',context=context)
                    
            if voucher.move_id:
                move_pool.button_cancel(cr, uid, [voucher.move_id.id])
        
        res = {
            'state':'cancel',
            'move_id':False,
        }
        self.write(cr, uid, ids, res)
        return True
    
    def writeoff_move_line_get(self, cr, uid, voucher_id, line_total, move_id, name, company_currency, current_currency, context=None):
        res = super(wtc_account_voucher_custom,self).writeoff_move_line_get(cr,uid,voucher_id,line_total,move_id,name,company_currency,current_currency,context=context)
        currency_obj = self.pool.get('res.currency')
        move_line = {}
        voucher = self.pool.get('account.voucher').browse(cr,uid,voucher_id,context)
        if voucher.payment_option == 'without_writeoff' and voucher.type in ('receipt', 'payment') :
            current_currency_obj = voucher.currency_id or voucher.journal_id.company_id.currency_id
            if not currency_obj.is_zero(cr, uid, current_currency_obj, line_total):
                diff = line_total
                account_id = res.get('account_id')
                if voucher.type == 'receipt':
                        account_id = voucher.partner_id.property_account_payable.id
                elif voucher.type == 'payment':
                        account_id = voucher.partner_id.property_account_receivable.id
                if not account_id :
                    raise osv.except_osv(('Perhatian !'), ("Mohon lengkapi account payable/receivable partner %s !")%(voucher.partner_id.name))  
                res.update({'account_id':account_id})    
        return res
    
class wtc_account_voucher_line(osv.osv):
    _inherit = "account.voucher.line"
    
    _columns = {
                'kwitansi' : fields.boolean(related='voucher_id.kwitansi',string='Yg Sudah Print Kwitansi'),
                'name' : fields.text(string='Description'),
                'branch_id' :fields.many2one('wtc.branch',string='Branch'),
                }
    
    def onchange_amount(self, cr, uid, ids, amount, amount_unreconciled, context=None):
        res = super(wtc_account_voucher_line,self).onchange_amount(cr,uid,ids,amount,amount_unreconciled,context=context)
        if amount:
            if amount > amount_unreconciled :
                Warning = {
                            'title': ('Perhatian !'),
                            'message': ("Nilai allocation tidak boleh lebih dari open balance !"),
                        }  
                res['value']['amount'] = amount_unreconciled
                res['warning'] = Warning       
        return res    
    
    def name_payable_onchange(self,cr,uid,ids,account_id,branch_id,division,context=None):
        if not branch_id or not division:
            raise except_orm(_('No Branch Defined!'), _('Sebelum menambah detil transaksi,\n harap isi branch dan division terlebih dahulu.'))
        dom2={}
        vals={}
        edi_doc_list2 = ['&', ('active','=',True), ('type','=','payable')]
        dict=self.pool.get('wtc.account.filter').get_domain_account(cr,uid,ids,'other_payable',context=None)
        edi_doc_list2.extend(dict)      
        dom2['account_id'] = edi_doc_list2

        
        return {'domain':dom2,'value':vals}
        
    def name_onchange(self,cr,uid,ids,name,branch_id,division,context=None):
        if not branch_id or not division:
            raise except_orm(_('No Branch Defined!'), _('Sebelum menambah detil transaksi,\n harap isi branch dan division terlebih dahulu.'))
        dom={}
        edi_doc_list = ['&', ('active','=',True), ('type','!=','view')]
        dict=self.pool.get('wtc.account.filter').get_domain_account(cr,uid,ids,'payments_request',context=None)
        edi_doc_list.extend(dict)      
        dom['account_id'] = edi_doc_list
        return {'domain':dom}
        
    def account_id_onchange(self,cr,uid,ids,account_id,branch_id,division,context=None):
        if not branch_id or not division:
            raise except_orm(_('No Branch Defined!'), _('Sebelum menambah detil transaksi,\n harap isi branch dan division terlebih dahulu.'))
        dom2={}
        edi_doc_list2 = ['&', ('active','=',True), ('type','!=','view')]
        dict=self.pool.get('wtc.account.filter').get_domain_account(cr,uid,ids,'other_receivable_detail',context=context)
        edi_doc_list2.extend(dict)      
        dom2['account_id'] = edi_doc_list2
        return {'domain':dom2}  
        
    def onchange_move_line_id(self, cr, user, ids, move_line_id, amount,currency_id,journal, context=None):
        res = super(wtc_account_voucher_line, self).onchange_move_line_id(cr, user, ids, move_line_id, context=context)
        move_line_pool = self.pool.get('account.move.line')
        currency_pool = self.pool.get('res.currency')
        account_journal = self.pool.get('account.journal')
        purchase_order = self.pool.get('purchase.order')
        stock_picking = self.pool.get('stock.picking')
        serial_number = self.pool.get('stock.production.lot')
        Warning = {}
        if move_line_id :
            remaining_amount = amount
            journal_brw = account_journal.browse(cr,user,journal)
            currency_id = currency_id or journal_brw.company_id.currency_id.id
            company_currency = journal_brw.company_id.currency_id.id
            move_line_brw = move_line_pool.browse(cr,user,move_line_id)

            if move_line_brw.currency_id and currency_id == move_line_brw.currency_id.id:
                amount_original = abs(move_line_brw.amount_currency)
                amount_unreconciled = abs(move_line_brw.amount_residual_currency)
            else:
                #always use the amount booked in the company currency as the basis of the conversion into the voucher currency
                amount_original = currency_pool.compute(cr, user, company_currency, currency_id, move_line_brw.credit or move_line_brw.debit or 0.0, context=context)
                amount_unreconciled = currency_pool.compute(cr, user, company_currency, currency_id, abs(move_line_brw.amount_residual), context=context)
            res['value'].update({
                                'name':move_line_brw.move_id.name,
                                'move_line_id':move_line_brw.id,                
                                'amount_original': amount_original,
                                'amount': move_line_id and min(abs(remaining_amount), amount_unreconciled) or 0.0,
                                'date_original':move_line_brw.date,
                                'date_due':move_line_brw.date_maturity,
                                'amount_unreconciled': amount_unreconciled,})
            
            ####################### CEK CONSOLIDATE INVOICE ###############################
            if not move_line_brw.invoice.asset :
                if move_line_brw.invoice.type == 'in_invoice' and move_line_brw.invoice.tipe == 'purchase' and not move_line_brw.invoice.consolidated :
                    Warning = {
                                'title': ('Perhatian !'),
                                'message': ("Penerimaan atas Invoice '%s' belum lengkap, mohon lakukan consolidate invoice !")%(move_line_brw.invoice.number),
                            }
                    res['warning'] = Warning
                    res['value'] = {}
                    res['value']['move_line_id'] = False
        return res
    
class invoice(osv.osv):
    _inherit = 'account.invoice'
    
    def invoice_pay_customer(self, cr, uid, ids, context=None):
        if not ids: return []
        dummy, view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account_voucher', 'view_vendor_receipt_dialog_form')
        inv = self.browse(cr, uid, ids[0], context=context)
        return {
            'name':("Pay Invoice"),
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
                'branch_id': inv.branch_id.id,
                'division': inv.division,
                'close_after_process': True,
                'invoice_type': inv.type,
                'invoice_id': inv.id,
                'default_type': inv.type in ('out_invoice','out_refund') and 'receipt' or 'payment',
                'type': inv.type in ('out_invoice','out_refund') and 'receipt' or 'payment'
            }
        }   
        
        
class wtc_register_kwitansi_payments(osv.osv):
    _inherit = 'wtc.register.kwitansi.line'   
    
    _columns = {
                'amount':fields.float('Amount')
                }
    
class wtc_payments_request_type(osv.osv):
    _name = "wtc.payments.request.type" 
    _description = 'Payment Request Type'
    
    _columns ={
               'name' : fields.text(string='Description') 
               } 
   
