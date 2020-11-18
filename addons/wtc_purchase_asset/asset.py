from openerp.osv import fields, osv
from openerp.tools.translate import _
from datetime import date, datetime
from lxml import etree
from dateutil.relativedelta import relativedelta
import openerp.addons.decimal_precision as dp

class wtc_asset(osv.osv):
    _inherit = "account.asset.asset"
    _order = 'purchase_date desc'
    
    def _amount_residual(self, cr, uid, ids, name, args, context=None):
        cr.execute("""SELECT
                        l.asset_id as id, SUM(l.debit-l.credit) AS amount
                        FROM
                        account_move_line l
                        WHERE
                        l.asset_id IN %s GROUP BY l.asset_id """, (tuple(ids),))
        res=dict(cr.fetchall())
        for asset in self.browse(cr, uid, ids, context):
            res[asset.id] = asset.purchase_value - res.get(asset.id, 0.0) - asset.salvage_value
        for id in ids:
            res.setdefault(id, 0.0)
        return res
        
    def _amount_different(self, cr, uid, ids, field_names, args, context=None):
        res = {}
        if context is None:
            context = {}
        for asset in self.browse(cr, uid, ids, context=context):
            res[asset.id] = {
                'amount_different': 0.0,
            }
            purchase_value = asset.purchase_value if asset.purchase_value else 0.0
            real_purchase_value = asset.real_purchase_value if asset.real_purchase_value else 0.0
            nilai = float(purchase_value - real_purchase_value)
            if nilai > 0 :
                nilai = True
            else :
                nilai = False
            res[asset.id]['amount_different'] = True if nilai else False
        return res
                                
    _columns = {
                'confirm_uid':fields.many2one('res.users',string="Validated by"),
                'confirm_date':fields.datetime('Validated on'),
                'branch_id': fields.many2one('wtc.branch', string='Branch'),
                'division':fields.selection([('Umum','Umum')], 'Division', select=True),   
                'product_id' : fields.many2one('product.product',string="Product"),
                'invoice_id' : fields.many2one('account.invoice',string="Invoice No"), 
                'category_id': fields.many2one('account.asset.category', 'Asset Category',required=True, change_default=True, readonly=True, states={'draft':[('readonly',False)]}),
                'categ_type' : fields.related('category_id','type',type='char',string="Type"),
                'first_day_of_month' : fields.boolean(string="First day of Month"),
                'responsible_id' : fields.many2one('hr.employee',string="Responsible"),
                'cost_centre_id' : fields.related('branch_id','profit_centre',relation="stock.warehouse",type="char",string="Cost Centre"),
                'asset_classification_id' : fields.many2one('wtc.asset.classification',string="Asset Classification",domain="[('categ_id','=',category_id)]"),
                'code': fields.char('Asset Code', size=32, readonly=True,copy=False),
                'account_asset_id' : fields.related('category_id','account_asset_id',relation='account.account',type='many2one',readonly=True,string="Asset Account"),
                'account_depreciation_id' : fields.related('category_id','account_depreciation_id',relation='account.account',type='many2one',readonly=True,string="Depreciation Account"),
                'account_expense_depreciation_id' : fields.related('category_id','account_expense_depreciation_id',relation='account.account',type='many2one',readonly=True,string="Depr. Expense Account"),
                'real_purchase_value' : fields.float(string="Purchase Value"),
                'real_purchase_date' : fields.date(string="Purchase Date"),
                'value_residual': fields.function(_amount_residual, method=True, digits_compute=dp.get_precision('Account'), string='Residual Value'),
                'register_no' : fields.char(string='Register No'),
                'purchase_asset_ids': fields.one2many('wtc.purchase.asset.line','asset_register_id',string="Detail Purchase Asset"),
                'po_value' : fields.float(string='PO Value'),
                'retensi' : fields.float(string='Retensi'),
                'state': fields.selection([('draft','Draft'),('CIP','CIP'),('open','Running'),('close','Close'),('disposed','Disposed'),('cancel','Cancelled')], 'Status', required=True, copy=False),
                'amount_different': fields.function(_amount_different, multi='sums',store=True,type='boolean',string='Different Amount', digits_compute=dp.get_precision('Account')),                
                'disposal_id':fields.many2one('wtc.disposal.asset',string='Disposal No',copy=False),
                'do_number': fields.char("No.DO"),
                'do_date': fields.date("Tgl.DO"),
                'asset_adjustment_ids': fields.one2many('wtc.asset.adjustment', 'asset_id', string="History Adjustment"),
                }
    
    _defaults = {
      'division' : 'Umum',
     }   
    
    _sql_constraints = [
    ('unique_name_asset_code', 'unique(code)', 'Code/Reference Asset duplicate mohon periksa kembali data anda !'),
]        
   
    def _compute_entries(self, cr, uid, ids, period_id, context=None):
        result = []
        period_obj = self.pool.get('account.period')
        depreciation_obj = self.pool.get('account.asset.depreciation.line')
        period = period_obj.browse(cr, uid, period_id, context=context)
        depreciation_ids = depreciation_obj.search(cr, uid, [
                                                             ('asset_id', 'in', ids), 
                                                             ('depreciation_date', '<=', period.date_stop), 
#                                                              ('depreciation_date', '>=', period.date_start), 
                                                             ('move_check', '=', False)],limit=500, context=context)
        context = dict(context or {}, depreciation_date=period.date_stop)
        return depreciation_obj.create_move(cr, uid, depreciation_ids, context=context)
           
    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            tit = "[%s]-[%s] %s" % (record.register_no,str(record.code), record.name)
            res.append((record.id, tit))
        return res

    def name_search(self, cr, uid, name='', args=None, operator='ilike',context=None, limit=100):
        args = args or []
        if name :
            ids = self.search(cr, uid, ['|',('code', operator, name),('register_no', operator, name)] + args, limit=limit, context=context or {})
            if not ids:
                ids = self.search(cr, uid, [('name', operator, name)] + args, limit=limit, context=context or {})
        else :
            ids = self.search(cr, uid, args, limit=limit, context=context or {})
        return self.name_get(cr, uid, ids, context or {})
        
    def onchange_category_id(self, cr, uid, ids, category_id, context=None):
        res = super(wtc_asset,self).onchange_category_id(cr, uid, ids, category_id, context=context)
        asset_categ_obj = self.pool.get('account.asset.category')
        if category_id:
            category_obj = asset_categ_obj.browse(cr, uid, category_id, context=context)
            res['value'].update({'first_day_of_month': category_obj.first_day_of_month})
        
        return res

    def set_to_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'cancel'})
            
    def validate(self, cr, uid, ids, context=None):
        vals = super(wtc_asset,self).validate(cr,uid,ids,context=context)
        asset = self.browse(cr,uid,ids)
        if asset.code == '/' or not asset.code :
            self.write(cr, uid, ids, {
                'confirm_uid':uid,
                'confirm_date':datetime.now(),
                'code': self.pool.get('ir.sequence').get_id(cr, uid, [asset.category_id.sequence_id.id],context=context)}, context)
        else :  
            self.write(cr, uid, ids, {
                'confirm_uid':uid,
                'confirm_date':datetime.now()}, context)
        if not asset.purchase_value :
            raise osv.except_osv(_('Invalid Action!'), _('Nilai Gross Value tidak boleh nol'))
        self.compute_depreciation_board(cr,uid,ids)   
        return vals
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(wtc_asset, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
         
        branch_ids_user=self.pool.get('res.users').browse(cr,uid,uid).branch_ids
        branch_ids=[b.id for b in branch_ids_user]
        doc = etree.XML(res['arch'])
        nodes_branch = doc.xpath("//field[@name='branch_id']")
        nodes_categ = doc.xpath("//field[@name='category_id']")        
        for node in nodes_branch:
            node.set('domain', '[("id", "in", '+ str(branch_ids)+')]')
        if context.get('type') == 'prepaid' :
            for node in nodes_categ:
                node.set('domain', '[("type","=","prepaid")]') 
        else  :       
            for node in nodes_categ:
                node.set('domain', '[("type","=","fixed")]')                 
        res['arch'] = etree.tostring(doc)           
        return res  
    
    def create(self,cr,uid,vals,context=None):
        sequence = self.pool.get('ir.sequence')
        vals['register_no']  = sequence.get_per_branch(cr, uid, vals['branch_id'], 'REGAS')
        res = super(wtc_asset,self).create(cr,uid,vals,context=context)
        return res

    def check_posted_depreciation_amount(self, cr ,uid, ids, context=None):
        asset_id = self.browse(cr,uid,ids)
        depreciation_lin_obj = self.pool.get('account.asset.depreciation.line')
        posted_amount_before = 0.0
        posted_depre_date_before_list = []
        length_unposted = 0
        posted_depreciation_line_ids = depreciation_lin_obj.search(cr, uid, [('asset_id', '=', asset_id.id),
                                                                             ('move_check', '=', True)],
                                                                            order='depreciation_date desc')
        last_depreciation = posted_depreciation_line_ids[0] if posted_depreciation_line_ids else []
        if last_depreciation :
            last_depreciation = depreciation_lin_obj.browse(cr, uid, last_depreciation)
            last_depreciation = datetime.strptime(last_depreciation.depreciation_date, '%Y-%m-%d')
            purchase_date = datetime.strptime(asset_id.purchase_date, '%Y-%m-%d')
            if asset_id.prorata :
                purchase_date = datetime(purchase_date.year, purchase_date.month, 1)

            if last_depreciation < purchase_date :
                int_year = purchase_date.year - last_depreciation.year
                int_year_month = 0
                if int_year > 0 :
                    int_year_month = int_year * 12

                length_unposted = (purchase_date.month - last_depreciation.month - 1) + int_year_month

        if posted_depreciation_line_ids:
            posted_depre_date_after_list,posted_depre_date_before_list, posted_depre_date_list, posted_amount_before, first_depreciation_date = self.get_posted_depreciation_vals(cr,uid,asset_id,posted_depreciation_line_ids,context=context)
        return length_unposted,posted_depre_date_before_list, posted_amount_before

    def get_posted_depreciation_vals(self,cr,uid,asset_id,posted_depreciation_line_ids,context=None):
        depreciation_lin_obj = self.pool.get('account.asset.depreciation.line')
        posted_depre_date_list = []
        posted_depre_date_before_list = []
        posted_depre_date_after_list = []
        posted_amount_before = 0.0
        purchase_date = datetime.strptime(asset_id.purchase_date, '%Y-%m-%d')

        if asset_id.prorata:
            purchase_date = datetime(purchase_date.year, purchase_date.month, 1)

        # get date list of posted depreciation then get the first depreciation date
        # get sum amount of depreciated item before purchase date
        for depre in depreciation_lin_obj.browse(cr, uid, posted_depreciation_line_ids) :
            depre_date = datetime.strptime(depre.depreciation_date, '%Y-%m-%d')
            posted_depre_date_list.append(depre_date)
            if depre_date < purchase_date :
                posted_depre_date_before_list.append(depre_date)
                posted_amount_before += depre.amount
            else :
                posted_depre_date_after_list.append(depre_date)

        posted_depre_date_list.sort()
        first_depreciation_date = posted_depre_date_list[0]
        return  posted_depre_date_after_list,posted_depre_date_before_list,posted_depre_date_list,posted_amount_before,first_depreciation_date

    def get_depreciation_detail(self,cr,uid,asset_id,posted_depreciation_line_ids,context=None):
        depreciation_lin_obj = self.pool.get('account.asset.depreciation.line')
        last_depreciation_date = datetime.strptime(depreciation_lin_obj.browse(cr, uid, posted_depreciation_line_ids[0], context=context).depreciation_date,'%Y-%m-%d')
        depreciation_date = (last_depreciation_date + relativedelta(months=+asset_id.method_period))
        posted_depre_date_after_list,posted_depre_date_before_list, posted_depre_date_list, posted_amount_before, first_depreciation_date = self.get_posted_depreciation_vals(cr, uid,
                                                                                                                  asset_id,
                                                                                                                  posted_depreciation_line_ids,
                                                                                                                  context=context)
        return posted_depre_date_after_list,last_depreciation_date, depreciation_date, posted_depre_date_list, posted_amount_before, first_depreciation_date, posted_depre_date_before_list

    def compute_depreciation_board(self, cr, uid, ids, context=None):
        res = super(wtc_asset,self).compute_depreciation_board(cr,uid,ids,context=context)        
        depreciation_lin_obj = self.pool.get('account.asset.depreciation.line')
        currency_obj = self.pool.get('res.currency')
        for asset in self.browse(cr, uid, ids, context=context):
            if asset.value_residual == 0.0:
                continue
            if asset.method_number == 0:
                continue
            posted_amount_before = 0
            skip_number = 0
            posted_depre_date_list = []
            posted_depre_date_before_list = []
            posted_depre_date_after_list = []
            purchase_date = datetime.strptime(asset.purchase_date, '%Y-%m-%d')
            posted_depreciation_line_ids = depreciation_lin_obj.search(cr, uid, [('asset_id', '=', asset.id),
                                                                                 ('move_check', '=', True)],order='depreciation_date desc')
            old_depreciation_line_ids = depreciation_lin_obj.search(cr, uid, [('asset_id', '=', asset.id), ('move_id', '=', False)])
            if old_depreciation_line_ids:
                depreciation_lin_obj.unlink(cr, uid, old_depreciation_line_ids, context=context)

            amount_to_depr = residual_amount = asset.value_residual

            if asset.prorata and not asset.first_day_of_month:
                if posted_depreciation_line_ids:
                    posted_depre_date_after_list,last_depreciation_date, depreciation_date, posted_depre_date_list, posted_amount_before, first_depreciation_date,posted_depre_date_before_list = self.get_depreciation_detail(cr,uid,asset,posted_depreciation_line_ids,context=context)
                    if first_depreciation_date :
                        #check if first date more than purchase date then replace next depreciation to purchase date
                        first_purchase_date = datetime(purchase_date.year,purchase_date.month,1)
                        if first_purchase_date < first_depreciation_date:
                            skip_number = len(posted_depre_date_list) - 1
                            depreciation_date = datetime(purchase_date.year, purchase_date.month, purchase_date.day)
                else :
                    skip_number -= 1
                    depreciation_date = datetime.strptime(self._get_last_depreciation_date(cr, uid, [asset.id], context)[asset.id], '%Y-%m-%d')

            elif asset.prorata and asset.first_day_of_month :
                if posted_depreciation_line_ids:
                    posted_depre_date_after_list,last_depreciation_date, depreciation_date, posted_depre_date_list, posted_amount_before, first_depreciation_date,posted_depre_date_before_list = self.get_depreciation_detail(cr,uid,asset,posted_depreciation_line_ids,context=context)
                    if first_depreciation_date :
                        #check if first date more than purchase date then replace next depreciation to purchase date
                        if purchase_date < first_depreciation_date:
                            skip_number = len(posted_depre_date_list)
                            depreciation_date = datetime(purchase_date.year, purchase_date.month, 1)
                else :
                    depreciation_date = datetime(purchase_date.year, purchase_date.month, 1)
            else:
                # depreciation_date = 1st January of purchase year
                #if we already have some previous validated entries, starting date isn't 1st January but last entry + method period
                if posted_depreciation_line_ids:
                    posted_depre_date_after_list,last_depreciation_date, depreciation_date, posted_depre_date_list, posted_amount_before, first_depreciation_date,posted_depre_date_before_list = self.get_depreciation_detail(cr,uid,asset,posted_depreciation_line_ids,context=context)
                    if first_depreciation_date :
                        #check if first date more than purchase date then replace next depreciation to purchase date
                        if purchase_date < first_depreciation_date:
                            skip_number = len(posted_depre_date_list)
                            depreciation_date = datetime(purchase_date.year, 1, 1)
                else:
                    depreciation_date = datetime(purchase_date.year, 1, 1)

            day = depreciation_date.day
            month = depreciation_date.month
            year = depreciation_date.year
            total_days = (year % 4) and 365 or 366

            #get number of depreciation + count of posted depre + count of unposted depre
            undone_dotation_number = self._compute_board_undone_dotation_nb(cr, uid, asset, depreciation_date, total_days, context=context)

            #first amount compute depreciation board
            i = len(posted_depreciation_line_ids)+1
            amount = self._compute_board_amount_first_month(cr, uid, asset, i, residual_amount, amount_to_depr, undone_dotation_number, posted_depreciation_line_ids, total_days, depreciation_date, posted_amount_before, posted_depre_date_before_list,posted_depre_date_after_list, context=context)

            #set amount to zero if depreciation date less than purchase date, then set amount to temporary variable to be able to be used by next period
            temp = False
            temp_first_amount = 0

            print "amount",amount
            if posted_amount_before :
                amount -= posted_amount_before
            print "amount after posted",amount
            if asset.prorata:
                prorata_purchase_date = datetime(purchase_date.year, purchase_date.month, 1)
                if depreciation_date < prorata_purchase_date:
                    temp_first_amount = amount
                    temp = True
                    amount = 0
            else:
                if depreciation_date < purchase_date:
                    temp_first_amount = amount
                    temp = True
                    amount = 0

            residual_amount-=amount
            vals = {
                'amount': amount,
                'asset_id': asset.id,
                'sequence': i,
                'name': (asset.code or '') + '/' + str(i),
                'remaining_value': residual_amount,
                'depreciated_value': asset.purchase_value - (asset.salvage_value + residual_amount),
                'depreciation_date': depreciation_date.strftime('%Y-%m-%d'),
            }
            print "vals",vals
            depreciation_lin_obj.create(cr, uid, vals, context=context)
            depreciation_date = date(year, month, day) + relativedelta(months=+asset.method_period)
            day = depreciation_date.day
            month = depreciation_date.month
            year = depreciation_date.year
            value_skip = 0.0
            number_skip = 0
            count_skip = 0
            for x in range(len(posted_depreciation_line_ids)+1, undone_dotation_number + skip_number):
                if isinstance(depreciation_date,date) :
                    depreciation_date = datetime.combine(depreciation_date, datetime.min.time())

                depre_date = datetime(depreciation_date.year,depreciation_date.month,1)
                if depre_date in posted_depre_date_list :
                    residual_amount -= amount
                    value_skip -= amount

                    depreciation_date = (datetime(year, month, day) + relativedelta(months=+asset.method_period))
                    day = depreciation_date.day
                    month = depreciation_date.month
                    year = depreciation_date.year
                    if not asset.first_day_of_month :
                        number_skip -=1

                    count_skip +=1
                    continue

                if i == undone_dotation_number:
                    if not count_skip :
                        continue

                i = x + 1 + number_skip
                amount = self._compute_board_amount(cr, uid, asset, i, residual_amount, amount_to_depr, undone_dotation_number, posted_depreciation_line_ids, total_days, depreciation_date, context=context)

                #set amount to zero for unposted depreciation which has depreciation date less than purchase date
                is_zero = False
                if asset.prorata:
                    prorata_purchase_date = datetime(purchase_date.year, purchase_date.month, 1)
                    if depre_date < prorata_purchase_date:
                        amount = 0
                        is_zero = True
                else:
                    if depre_date < purchase_date:
                        amount = 0
                        is_zero = True

                #set once amount for depreciation detail which has depreciation date more or equal than purchase date
                if not is_zero :
                    if temp :
                        amount = temp_first_amount
                        temp = False
                    else :
                        amount += temp_first_amount
                    temp_first_amount = 0

                company_currency = asset.company_id.currency_id.id
                current_currency = asset.currency_id.id
                # compute amount into company currency
                amount = currency_obj.compute(cr, uid, current_currency, company_currency, amount, context=context)
                residual_amount -= amount
                vals = {
                    'amount': amount,
                    'asset_id': asset.id,
                    'sequence': i,
                    'name': str(asset.code) +'/' + str(i),
                    'remaining_value': residual_amount - value_skip,
                    'depreciated_value': asset.purchase_value - (asset.salvage_value + residual_amount) + value_skip,
                    'depreciation_date': depreciation_date.strftime('%Y-%m-%d'),
                }
                depreciation_lin_obj.create(cr, uid, vals, context=context)
                # Considering Depr. Period as months
                depreciation_date = (datetime(year, month, day) + relativedelta(months=+asset.method_period))
                day = depreciation_date.day
                month = depreciation_date.month
                year = depreciation_date.year
        return True
    
    def _compute_board_undone_dotation_nb(self, cr, uid, asset, depreciation_date, total_days, context=None):
        res = super(wtc_asset,self)._compute_board_undone_dotation_nb(cr, uid, asset, depreciation_date, total_days, context=context)
        #get variable
        length_unposted, posted_depre_date_before_list, posted_amount_before = self.check_posted_depreciation_amount(cr, uid,asset.id,
                                                                                                     context=context)
        #get length posted depreciation
        posted_depre_date_before_list = len(posted_depre_date_before_list)
        #count number of depreciation + count posted depreciation + count unposted depreciation
        if posted_depre_date_before_list:
            res += posted_depre_date_before_list + length_unposted

        if asset.prorata and asset.first_day_of_month :
            return res - 1
        return res
       
    def _compute_board_amount_x(self, cr, uid, asset, i, residual_amount, amount_to_depr, undone_dotation_number, posted_depreciation_line_ids, total_days, depreciation_date, context=None):
        #by default amount = 0
        amount = 0
        if i == undone_dotation_number:
            amount = residual_amount
        else:
            if asset.method == 'linear':
                amount = amount_to_depr / (undone_dotation_number - len(posted_depreciation_line_ids))
                if asset.prorata :
                    amount = amount_to_depr / asset.method_number
                    days = total_days - float(depreciation_date.strftime('%j'))
                    if i == 1 and not asset.first_day_of_month:
                        amount = (amount_to_depr / asset.method_number) / total_days * days
                         
                    elif i == undone_dotation_number:
                        amount = (amount_to_depr / asset.method_number) / total_days * (total_days - days)
                    #change amount if gross value changed
                    if posted_depreciation_line_ids or residual_amount != amount_to_depr :
                        depreciation_obj = self.pool.get('account.asset.depreciation.line')
                        browse_depre_line = depreciation_obj.browse(cr,uid,posted_depreciation_line_ids)
                        if browse_depre_line :
                            total_posted_depre_amount = 0.0
                            for x in browse_depre_line :
                                total_posted_depre_amount += x.amount 
                            gross_value = amount_to_depr + total_posted_depre_amount
                            if asset.prorata and asset.first_day_of_month :
                                amt_per_month = gross_value / (undone_dotation_number)
                            else :
                                amt_per_month = gross_value / (undone_dotation_number - 1)
                            should = i * amt_per_month
                            amount = should - total_posted_depre_amount - (amount_to_depr - residual_amount)
                            if amount < 0 :
                                amount = 0
            elif asset.method == 'degressive':
                amount = residual_amount * asset.method_progress_factor
                if asset.prorata:
                    days = total_days - float(depreciation_date.strftime('%j'))
                    if i == 1:
                        amount = (residual_amount * asset.method_progress_factor) / total_days * days
                    elif i == undone_dotation_number:
                        amount = (residual_amount * asset.method_progress_factor) / total_days * (total_days - days)
        return amount
    
    def _compute_board_amount_first_month(self, cr, uid, asset, i, residual_amount, amount_to_depr, undone_dotation_number,
                                          posted_depreciation_line_ids, total_days, depreciation_date, posted_amount_before,
                                          posted_depre_date_before_list,posted_depre_date_after_list, context=None):
        #by default amount = 0
        amount = 0
        if i == undone_dotation_number:
            amount = residual_amount
        else:
            len_depre_before = len(posted_depre_date_before_list)
            len_depre_after = len(posted_depre_date_after_list)
            count_posted_line = 0
            if len_depre_after > asset.method_number :
                count_posted_line = len_depre_after - asset.method_number + 1
            amount = (((asset.purchase_value-asset.salvage_value)/(asset.method_number))*(len(posted_depreciation_line_ids)+1-len_depre_before-count_posted_line))-(sum(self.pool.get('account.asset.depreciation.line').browse(cr,uid,x).amount for x in posted_depreciation_line_ids)-posted_amount_before)
        return amount
    
    def _compute_board_amount(self, cr, uid, asset, i, residual_amount, amount_to_depr, undone_dotation_number,
                              posted_depreciation_line_ids, total_days, depreciation_date, context=None):
        #by default amount = 0
        amount = 0
        if i == undone_dotation_number:
            amount = residual_amount
        else:

            if asset.method_number and (asset.purchase_value -  asset.salvage_value) :
                amount = (asset.purchase_value-asset.salvage_value)/(asset.method_number)
        return amount
    
    def write(self,cr,uid,ids,vals,context=None):
        res = super(wtc_asset,self).write(cr,uid,ids,vals,context=context)
        if vals.get('purchase_value') or vals.get('purchase_date') or vals.get('method_number'):
            self.compute_depreciation_board(cr,uid,ids,context=context)
        asset = self.browse(cr,uid,ids)
        if vals.get('code') and asset.code :
            del vals['code']
        return res
    
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Asset tidak bisa didelete dalam State selain 'draft' !"))
        return super(wtc_asset, self).unlink(cr, uid, ids, context=context)
        
class wtc_asset_category(osv.osv):
    _inherit = "account.asset.category"
    
    _columns = {
                'type':fields.selection([('prepaid','Prepaid'),('fixed','Fixed Asset')],string="Type"),
                'code' : fields.char(string="Asset Code"),
                'first_day_of_month' : fields.boolean(string="First day of Month"),
                'sequence_id' : fields.many2one('ir.sequence',string='Sequence'),
                'is_cip' : fields.boolean(string='Is CIP ?')
                }
    _defaults = {
                 'first_day_of_month':True
                 }
      
    _sql_constraints = [
    ('unique_name_asset_category_name', 'unique(name)', 'Nama duplicate mohon periksa kembali data anda !'),
]   
          
    def create(self,cr,uid,vals,context=None):
        sequence = self.pool.get('ir.sequence')
        code = vals.get('code',vals['name'])
        vals['sequence_id'] = sequence.get_sequence_asset_category(cr,uid,code,context=context)
        res = super(wtc_asset_category,self).create(cr,uid,vals,context=None)
        return res
    
class wtc_asset_depreciation_line(osv.osv):
    _inherit = "account.asset.depreciation.line"
    
    def _get_default_date(self,cr,uid,ids,context=None):
        return self.pool.get('wtc.branch').get_default_date(cr,uid,ids,context=None)
    
    def create_move(self, cr, uid, ids, context=None):
        res = super(wtc_asset_depreciation_line,self).create_move(cr,uid,ids,context=context)
        move_lines = self.pool.get('account.move').browse(cr,uid,res)
        periods = self.pool.get('account.period').find(cr, uid,dt=self._get_default_date(cr,uid,ids,context=context).date(), context=context)
        vals = {}
        if periods :
            vals['period_id'] = periods[0]
        for move_line in move_lines :
            branch_id = False
            for x in move_line.line_id :
                if not branch_id :
                    branch_id = x.asset_id.branch_id.id
                x.write({'branch_id':branch_id,'division':'Umum'})
            get_name = self.pool.get('ir.sequence').get_per_branch(cr,uid,[branch_id], move_line.journal_id.code) 
            vals['name'] = get_name
            move_line.write(vals)
        return res
    
    
class wtc_asset_classification(osv.osv):
    _name = "wtc.asset.classification"
    _description = "Asset Classification"
    
    _columns = {
                'name' : fields.char(string="Name"),
                'code' : fields.char(string='Code'),
                'categ_id' : fields.many2one('account.asset.category',string="Asset Category")
                }
    
    _sql_constraints = [
    ('unique_name_asset_classification', 'unique(code)', 'Code duplicate mohon periksa kembali data anda !'),
]        
    
    
class account_period_close(osv.osv_memory):
    _inherit = "account.period.close"
    
    def data_save(self, cr, uid, ids, context=None):
        journal_period_pool = self.pool.get('account.journal.period')
        period_pool = self.pool.get('account.period')
        account_move_obj = self.pool.get('account.move')
        #obj_depreciation_line = self.pool.get('account.asset.depreciation.line')

        pad = period_pool.browse(cr, uid, context['active_ids'])[0]
        #did = obj_depreciation_line.search(cr, uid, [('depreciation_date', '>=', pad.date_start), ('depreciation_date', '<=', pad.date_stop), ('move_check','=',False)])
        #if did :
        #    dad = obj_depreciation_line.browse(cr, uid, did)
        #    obj_depreciation_line.create_move(cr, uid, [x.id for x in dad])

        mid = account_move_obj.search(cr, uid, [('period_id', '=', pad.id), ('state', '=', "draft")], context=context)
        if mid :
            account_move_obj.button_validate(cr, uid, mid)
        
        mode = 'done'
        for form in self.read(cr, uid, ids, context=context):
            if form['sure']:
                for id in context['active_ids']:
                    account_move_ids = account_move_obj.search(cr, uid, [('period_id', '=', id), ('state', '=', "draft")], context=context)
                    if account_move_ids:
                        raise osv.except_osv(_('Invalid Action!'), _('In order to close a period, you must first post related journal entries.'))

                    cr.execute('update account_journal_period set state=%s where period_id=%s', (mode, id))
                    cr.execute('update account_period set state=%s where id=%s', (mode, id))
                    self.invalidate_cache(cr, uid, context=context)

        return {'type': 'ir.actions.act_window_close'}    
    
    
    
