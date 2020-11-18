from openerp import netsvc
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
import time
from datetime import datetime
import logging

_log = logging.getLogger('smcus_account_report_zhr')
class smcus_zhr_cash_flow(osv.osv):
    _name = "smcus.zhr.cash.flow"
    _description = "setup cash flow component"
    _order = "type, sequence"
    
    _columns = {
        'type': fields.selection([
            ('1opr_activities', 'Operating Activities'),
            ('2inv_activities', 'Investing Activities'),
            ('3fin_activities', 'Financing Activities'),
            ('4kas', 'Kas dan Setara Kas')], 'Cash Flow Type', size=32,required="1",
             help="Pilih klasifikasi Arus Kas"),
        'name': fields.char("Name", required="1"),
        'sequence': fields.integer("Sequence", required="1"),
    }

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        res = []
        for record in self.read(cr, uid, ids, ['type','name'], context=context):
            if record['type']=='1opr_activities':
                name = 'Operating Activities - '+ record['name']
            elif record['type']=='2inv_activities':
                name = 'Investing Activities - '+ record['name']
            elif record['type']=='3fin_activities':
                name = 'Financing Activities - '+ record['name']
            elif record['type']=='4kas':
                name = 'Kas dan Setara Kas'
            res.append((record['id'],name ))
        return res

smcus_zhr_cash_flow()

class account_account(osv.osv):
    _inherit = "account.account"


    def _set_credit_debit(self, cr, uid, account_id, name, value, arg, context=None):
        if context.get('config_invisible', True):
            return True

        account = self.browse(cr, uid, account_id, context=context)
        diff = value - getattr(account,name)
        if not diff:
            return True

        journal_obj = self.pool.get('account.journal')
        jids = journal_obj.search(cr, uid, [('type','=','situation'),('centralisation','=',1),('company_id','=',account.company_id.id)], context=context)
        if not jids:
            raise osv.except_osv(_('Error!'),_("You need an Opening journal with centralisation checked to set the initial balance."))

        period_obj = self.pool.get('account.period')
        pids = period_obj.search(cr, uid, [('special','=',True),('company_id','=',account.company_id.id)], context=context)
        if not pids:
            raise osv.except_osv(_('Error!'),_("There is no opening/closing period defined, please create one to set the initial balance."))

        move_obj = self.pool.get('account.move.line')
        move_id = move_obj.search(cr, uid, [
            ('journal_id','=',jids[0]),
            ('period_id','=',pids[0]),
            ('account_id','=', account_id),
            (name,'>', 0.0),
            ('name','=', _('Opening Balance'))
        ], context=context)
        if move_id:
            move = move_obj.browse(cr, uid, move_id[0], context=context)
            move_obj.write(cr, uid, move_id[0], {
                name: diff+getattr(move,name)
            }, context=context)
        else:
            if diff<0.0:
                raise osv.except_osv(_('Error!'),_("Unable to adapt the initial balance (negative value)."))
            nameinv = (name=='credit' and 'debit') or 'credit'
            move_id = move_obj.create(cr, uid, {
                'name': _('Opening Balance'),
                'account_id': account_id,
                'journal_id': jids[0],
                'period_id': pids[0],
                name: diff,
                nameinv: 0.0
            }, context=context)
        return True

    def __compute(self, cr, uid, ids, field_names, arg=None, context=None,
                  query='', query_params=()):
        """ compute the balance, debit and/or credit for the provided
        account ids
        Arguments:
        `ids`: account ids
        `field_names`: the fields to compute (a list of any of
                       'balance', 'debit' and 'credit')
        `arg`: unused fields.function stuff
        `query`: additional query filter (as a string)
        `query_params`: parameters for the provided query string
                        (__compute will handle their escaping) as a
                        tuple
        """
        _log.info ('masuk ke compute')
        _log.info (context)
        mapping = {
            'balance': "COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) as balance",
            'debit': "COALESCE(SUM(l.debit), 0) as debit",
            'credit': "COALESCE(SUM(l.credit), 0) as credit",
            # by convention, foreign_balance is 0 when the account has no secondary currency, because the amounts may be in different currencies
            'foreign_balance': "(SELECT CASE WHEN currency_id IS NULL THEN 0 ELSE COALESCE(SUM(l.amount_currency), 0) END FROM account_account WHERE id IN (l.account_id)) as foreign_balance",
        }
        #get all the necessary accounts
        children_and_consolidated = self._get_children_and_consol(cr, uid, ids, context=context)
        #compute for each account the balance/debit/credit from the move lines
        accounts = {}
        res = {}
        null_result = dict((fn, 0.0) for fn in field_names)
        if children_and_consolidated:
            aml_query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)

            wheres = [""]
            if query.strip():
                wheres.append(query.strip())
            if aml_query.strip():
                wheres.append(aml_query.strip())
            filters = " AND ".join(wheres)
            branch_id = context.get('branch_id',False)
            if branch_id:
                branch_filter = " AND aj.branch_id="+str(branch_id[0])
                filters += branch_filter
            # IN might not work ideally in case there are too many
            # children_and_consolidated, in that case join on a
            # values() e.g.:
            # SELECT l.account_id as id FROM account_move_line l
            # INNER JOIN (VALUES (id1), (id2), (id3), ...) AS tmp (id)
            # ON l.account_id = tmp.id
            # or make _get_children_and_consol return a query and join on that
            request = ("SELECT l.account_id as id, " +\
                       ', '.join(mapping.values()) +
                       " FROM account_move_line l inner join account_journal aj on l.journal_id=aj.id " \
                       " WHERE l.account_id IN %s " \
                            + filters +
                       " GROUP BY l.account_id")
            _log.info(filters)
            params = (tuple(children_and_consolidated),) + query_params
            cr.execute(request, params)

            for row in cr.dictfetchall():
                accounts[row['id']] = row

            # consolidate accounts with direct children
            children_and_consolidated.reverse()
            brs = list(self.browse(cr, uid, children_and_consolidated, context=context))
            sums = {}
            currency_obj = self.pool.get('res.currency')
            while brs:
                current = brs.pop(0)
#                can_compute = True
#                for child in current.child_id:
#                    if child.id not in sums:
#                        can_compute = False
#                        try:
#                            brs.insert(0, brs.pop(brs.index(child)))
#                        except ValueError:
#                            brs.insert(0, child)
#                if can_compute:
                for fn in field_names:
                    sums.setdefault(current.id, {})[fn] = accounts.get(current.id, {}).get(fn, 0.0)
                    for child in current.child_id:
                        if child.company_id.currency_id.id == current.company_id.currency_id.id:
                            sums[current.id][fn] += sums[child.id][fn]
                        else:
                            sums[current.id][fn] += currency_obj.compute(cr, uid, child.company_id.currency_id.id, current.company_id.currency_id.id, sums[child.id][fn], context=context)

                # as we have to relay on values computed before this is calculated separately than previous fields
                if current.currency_id and current.exchange_rate and \
                            ('adjusted_balance' in field_names or 'unrealized_gain_loss' in field_names):
                    # Computing Adjusted Balance and Unrealized Gains and losses
                    # Adjusted Balance = Foreign Balance / Exchange Rate
                    # Unrealized Gains and losses = Adjusted Balance - Balance
                    adj_bal = sums[current.id].get('foreign_balance', 0.0) / current.exchange_rate
                    sums[current.id].update({'adjusted_balance': adj_bal, 'unrealized_gain_loss': adj_bal - sums[current.id].get('balance', 0.0)})

            for id in ids:
                res[id] = sums.get(id, null_result)
        else:
            for id in ids:
                res[id] = null_result
        return res


    _columns = {
        'smcus_zhr_report': fields.selection([
            ('na', 'N/A'),
            ('neraca_harta_lcr', 'Neraca (Harta Lancar)'),
            ('neraca_harta_ttp', 'Neraca (Harta Tetap)'),
            ('neraca_harta_lain', 'Neraca (Harta Lainnya)'),
            ('neraca_kewajiban_lcr', 'Neraca (Hutang Lancar)'),
            ('neraca_kewajiban_pjg', 'Neraca (Hutang Jangka Panjang)'),
            ('neraca_kewajiban_lain', 'Neraca (Hutang Lainnya)'),
            ('neraca_modal', 'Neraca (Modal dan Laba Ditahan)'),
            ('lr_pendapatan', 'Laba Rugi (Pendapatan)'),
            ('lr_biaya_pendapatan', 'Laba Rugi (Biaya atas Pendapatan)'),
            ('lr_biaya_operasional', 'Laba Rugi (Pengeluaran Operasional)'),
            ('lr_pendapatan_lain', 'Laba Rugi (Pendapatan Lain)'),
            ('lr_biaya_lain', 'Laba Rugi (Pengeluaran Lain)')], 'Posting Report Type', size=32,
             help="Pilih sesuai posting Report Standar"),
        'smcus_zhr_cash_flow': fields.many2one('smcus.zhr.cash.flow', 'Cash Flow Class', help='Pilih klasifikasi Arus Kas'),
        'smcus_laba_rugi': fields.boolean('Reserved for Laba/Rugi Tahun Berjalan'),
        'balance': fields.function(__compute, digits_compute=dp.get_precision('Account'), string='Balance', multi='balance'),
        'credit': fields.function(__compute, fnct_inv=_set_credit_debit, digits_compute=dp.get_precision('Account'), string='Credit', multi='balance'),
        'debit': fields.function(__compute, fnct_inv=_set_credit_debit, digits_compute=dp.get_precision('Account'), string='Debit', multi='balance'),
        'foreign_balance': fields.function(__compute, digits_compute=dp.get_precision('Account'), string='Foreign Balance', multi='balance',
                                           help="Total amount (in Secondary currency) for transactions held in secondary currency for this account."),
        'adjusted_balance': fields.function(__compute, digits_compute=dp.get_precision('Account'), string='Adjusted Balance', multi='balance',
                                            help="Total amount (in Company currency) for transactions held in secondary currency for this account."),
        'unrealized_gain_loss': fields.function(__compute, digits_compute=dp.get_precision('Account'), string='Unrealized Gain or Loss', multi='balance',
                                                help="Value of Loss or Gain due to changes in exchange rate when doing multi-currency transactions."),
    }
    
    _defaults = {
        'smcus_zhr_report': 'na',
    }

    def _check_smcus_laba_rugi_balance(self, cr, uid, ids, context=None):
        obj_self = self.browse(cr, uid, ids[0], context=context)
        if obj_self.smcus_laba_rugi:
            if obj_self.debit or obj_self.credit:
                return False
        return True

    def _check_smcus_laba_rugi_exist(self, cr, uid, ids, context=None):
        obj_self = self.browse(cr, uid, ids[0], context=context)
        if obj_self.smcus_laba_rugi:
            acc_ids = self.search(cr, uid, [('smcus_laba_rugi', '=', True)])
            if acc_ids[0]!=ids[0]:
                return False
        return True

    _constraints = [
        (_check_smcus_laba_rugi_exist, 'Error!\nSudah ada 1 Account yang diset sebagai Account Laba/Rugi Tahun Berjalan .', ['smcus_laba_rugi']),
        (_check_smcus_laba_rugi_balance, 'Error!\nAccount ini sudah pernah digunakan maka tidak bisa diset sebagai Account Laba/Rugi Tahun Berjalan .', ['smcus_laba_rugi']),
    ]

account_account()

class account_move_line(osv.osv):
    _inherit = 'account.move.line'

    def create(self, cr, uid, vals, context=None, check=True):
        account_obj = self.pool.get('account.account')

        if ('account_id' in vals) and account_obj.read(cr, uid, vals['account_id'], ['smcus_laba_rugi'])['smcus_laba_rugi']:
            raise osv.except_osv(_('Bad Account!'), _('You cannot use a Reserved for Laba/Rugi Tahun Berjalan account.'))
 
        result = super(account_move_line, self).create(cr, uid, vals, context, check)          
        return result

    def write(self, cr, uid, ids, vals, context=None, check=True, update_check=True):
        if context is None:
            context={}
        account_obj = self.pool.get('account.account')
        if isinstance(ids, (int, long)):
            ids = [ids]
        if ('account_id' in vals) and account_obj.read(cr, uid, vals['account_id'], ['smcus_laba_rugi'])['smcus_laba_rugi']:
            raise osv.except_osv(_('Bad Account!'), _('You cannot use a Reserved for Laba/Rugi Tahun Berjalan account.'))
 
        result = super(account_move_line, self).write(cr, uid, ids, vals, context, check, update_check)
        return result

account_move_line()
