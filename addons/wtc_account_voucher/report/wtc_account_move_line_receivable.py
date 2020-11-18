# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import tools
from openerp.osv import fields,osv
import openerp.addons.decimal_precision as dp

class wtc_account_receivable_report(osv.osv):
    _name = "wtc.account.receivable.report"
    _description = "Account Receivable Report"
    _auto = False
    
    def _compute_balances(self, cr, uid, ids, field_names, arg=None, context=None,
                  query='', query_params=()):
        all_treasury_lines = self.search(cr, uid, [], context=context)
        all_companies = self.pool.get('res.company').search(cr, uid, [], context=context)
        current_sum = dict((company, 0.0) for company in all_companies)
        res = dict((id, dict((fn, 0.0) for fn in field_names)) for id in all_treasury_lines)
        for record in self.browse(cr, uid, all_treasury_lines, context=context):
            res[record.id]['starting_balance'] = current_sum[record.company_id.id] 
            current_sum[record.company_id.id] += record.balance
            res[record.id]['ending_balance'] = current_sum[record.company_id.id]
        return res
  

    _columns = {
        'fiscalyear_id': fields.many2one('account.fiscalyear', 'Fiscalyear', readonly=True),
        'period_id': fields.many2one('account.period', 'Period', readonly=True),
        'debit': fields.float('Debit', readonly=True),
        'credit': fields.float('Credit', readonly=True),
        'balance': fields.float('Balance', readonly=True),
        'date': fields.date('Date', readonly=True),
        'starting_balance': fields.function(_compute_balances, digits_compute=dp.get_precision('Account'), string='Starting Balance', multi='balance'),
        'ending_balance': fields.function(_compute_balances, digits_compute=dp.get_precision('Account'), string='Ending Balance', multi='balance'),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'branch_id':fields.many2one('wtc.branch','Branch',readonly=True),
        'partner_id':fields.many2one('res.partner','Partner'),
        'journal_id':fields.many2one('account.journal','Journal'),
    }

    _order = 'date asc'


    def init(self, cr):
        tools.drop_view_if_exists(cr, 'wtc_account_receivable_report')
        cr.execute("""
            create or replace view wtc_account_receivable_report as (
            select
                p.id as id,
                p.fiscalyear_id as fiscalyear_id,
                p.id as period_id,
                sum(l.debit) as debit,
                sum(l.credit) as credit,
                sum(l.debit-l.credit) as balance,
                l.date as date,
                am.company_id as company_id,
                d.branch_id,
                l.partner_id,
                l.journal_id
            from
                account_move_line l
                left join account_account a on (l.account_id = a.id)
                left join account_move am on (am.id=l.move_id)
                left join account_period p on (am.period_id=p.id)
                
                left join res_partner c on (am.partner_id=c.id)
                left join account_journal d on  (l.journal_id=d.id)
                left join wtc_branch b on (d.branch_id=b.id)
                
            where l.reconcile_id is null
              and a.type = 'receivable'
            group by p.id, am.company_id,d.branch_id,l.partner_id,l.journal_id,l.date
            )
        """)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
