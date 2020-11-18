# 1 : imports of python lib
import calendar
from datetime import datetime
# 2 :  imports of odoo
from openerp import api, fields, models
from openerp import SUPERUSER_ID
from openerp.exceptions import Warning
# 3 :  imports from odoo modules

class TedsFiscalyearClose(models.TransientModel):
    # Private attributes
    _name = "teds.fiscalyear.close"
    _description = 'Close Fiscal Year'

    # Default methods
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()

    # Fields declaration
    fy_id = fields.Many2one('account.fiscalyear', string='Fiscal Year to close', domain="[('state','=','draft')]", required=True, help="Select a Fiscal year to close")
    journal_id = fields.Many2one('account.journal', 'Closing Entries Journal', domain="[('type','=','situation')]", required=True, help='The best practice here is to use a journal dedicated to contain the closing entries of all fiscal years. Note that you should define it with default debit/credit accounts, of type \'situation\' and with a centralized counterpart.')
    period_id = fields.Many2one('account.period', 'Closing Entries Period', required=True)
    report_name = fields.Char('Name of new entries', required=True, default="End of Fiscal Year Entry", help="Give name of the new entries")
    branch_ids = fields.Many2many('wtc.branch', 'teds_fiscalyear_close_branch_rel', 'fy_close_id', 'branch_id', string='Branches')

    # compute and search fields, in the same order that fields declaration

    # Constraints and onchanges

    # CRUD methods

    # Action methods
    @api.multi
    def data_save(self):
        self.ensure_one()

        branch_ids_user = False
        branch_ids = []

        branch_ids_user = self.branch_ids
        if not branch_ids_user :
            branch_ids_user = self.env['res.users'].browse(self._uid).branch_ids
        branch_ids=[b.id for b in branch_ids_user]

        today = self._get_default_date()
        journal_id = self.journal_id.id
        re_account_id = self.journal_id.default_debit_account_id.id
        period_id = self.period_id.id
        date = self.period_id.date_start

        self._cr.execute("""
                select aml.branch_id
                , sum(debit-credit) as balance
                from account_move_line aml
                where account_id in (
                    select aa.id
                    from account_account aa
                    inner join account_account_type aat on aa.user_type = aat.id
                    where aa.type = 'other'
                    and aat.code in ('expense', 'income'))
                and period_id in (select id from account_period where fiscalyear_id = %s)
                and aml.branch_id in %s
                group by aml.branch_id
            """ % (self.fy_id.id, str(tuple(branch_ids)).replace(',)', ')')))
        sums = self._cr.dictfetchall()

        move_ids = []

        for sum in sums : 
            if abs(sum['balance']) < 10 ** -4 :
                continue;
            branch_id = sum['branch_id']

            ref = self.env['ir.sequence'].get_per_branch(branch_id, self.journal_id.code)
            move = self.env['account.move'].sudo().create({
                'journal_id': journal_id,
                'line_id': [],
                'period_id': period_id,
                'date': date,
                'name': self.report_name,
                'ref': ref
                })
            move_id = move.id
            move_ids.append(move_id)

            self._cr.execute("""
                    select aml.account_id
                    , aml.branch_id
                    , sum(credit-debit) as balance
                    from account_move_line aml 
                    where account_id in (
                        select aa.id
                        from account_account aa
                        inner join account_account_type aat on aa.user_type = aat.id
                        where aa.type = 'other'
                        and aat.code in ('expense', 'income'))
                    and period_id in (select id from account_period where fiscalyear_id = %s)
                    and aml.branch_id = %s
                    group by aml.account_id, aml.branch_id
                """, (self.fy_id.id, branch_id))
            bals = self._cr.dictfetchall()

            re_per_branch = 0

            query_1st_part = """
                    INSERT INTO account_move_line (
                         debit, credit, name, ref, branch_id, division,
                         date, move_id, journal_id, period_id, account_id,
                         blocked, kwitansi, centralisation, date_created,
                         create_uid, write_uid, create_date, write_date,
                         currency_id, amount_currency, company_id, state) VALUES
                """
            query_2nd_part = ""
            query_2nd_part_args = []
            for bal in bals :
                if bal['balance'] == 0 :
                    continue
                re_per_branch -= bal['balance']
                if query_2nd_part:
                    query_2nd_part += ','
                query_2nd_part += "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), %s, %s, %s, %s)"
                query_2nd_part_args += (bal['balance'] > 0 and bal['balance'] or 0.0,
                       bal['balance'] < 0 and -bal['balance'] or 0.0,
                       self.report_name,
                       ref,
                       branch_id,
                       'Umum',
                       date,
                       move_id,
                       journal_id,
                       period_id,
                       bal['account_id'],
                       False,
                       False,
                       'normal',
                       today,
                       self._uid,
                       self._uid,
                       None,
                       0.0,
                       1, 
                       'draft')

            #TODO: Insert Retained Earning by re_per_branch.
            if re_per_branch != 0.0 :
                if query_2nd_part:
                    query_2nd_part += ','
                query_2nd_part += "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), %s, %s, %s, %s)"
                query_2nd_part_args += (sum['balance'] > 0 and sum['balance'] or 0.0,
                       sum['balance'] < 0 and -sum['balance'] or 0.0,
                       self.report_name,
                       ref,
                       branch_id,
                       'Umum',
                       date,
                       move_id,
                       journal_id,
                       period_id,
                       re_account_id,
                       False,
                       False,
                       'normal',
                       today,
                       self._uid,
                       self._uid,
                       None,
                       0.0,
                       1,
                       'draft')

            if query_2nd_part:
                self._cr.execute(query_1st_part + query_2nd_part, tuple(query_2nd_part_args))

        self.invalidate_cache()

        acc_moves = self.env['account.move'].browse(move_ids)
        if self.journal_id.entry_posted :
            acc_moves.post()
        else :
            acc_moves.validate()

        #create the journal.period object and link it to the old fiscalyear
        ids = self.env['account.journal.period'].search([('journal_id', '=', journal_id), ('period_id', '=', period_id)])
        if not ids:
            ids = [self.env['account.journal.period'].create({
                   'name': (self.journal_id.name or '') + ':' + (self.period_id.code or ''),
                   'journal_id': journal_id,
                   'period_id': period_id
               })]
        self._cr.execute('UPDATE account_fiscalyear ' \
                    'SET end_journal_period_id = %s ' \
                    'WHERE id = %s', (ids[0].id, self.fy_id.id))
        self.env['account.fiscalyear'].invalidate_cache(['end_journal_period_id'], [self.fy_id.id])

        return {'type': 'ir.actions.act_window_close'}


    # Business methods
