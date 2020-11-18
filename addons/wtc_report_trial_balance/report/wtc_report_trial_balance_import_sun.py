from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import orm
from openerp.osv import fields, osv
from openerp.sql_db import db_connect
from openerp.tools.config import config
import logging
_logger = logging.getLogger(__name__)


class wtc_trial_balance_import_sun_report_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(wtc_trial_balance_import_sun_report_print, self).__init__(
            cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({
            'formatLang_zero2blank': self.formatLang_zero2blank,
            })
        
    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context
        
        branch_ids = data['branch_ids']
        account_ids = data['account_ids']        
        journal_ids = data['journal_ids']
        period_id = data['period_id']
        status = data['status']
        start_date = data['start_date']
        end_date = data['end_date']
        title_prefix = ''
        title_short_prefix = ''

        date_stop = self.pool.get('account.period').browse(cr,uid,period_id[0]).date_stop
        date_stop = datetime.strptime(date_stop, '%Y-%m-%d').strftime('%d %B %Y')
        
        report_trial_balance_import_sun = {
            'type': 'import_sun',
            'title': '',
            'title_short': title_short_prefix + ', ' + _('LAPORAN MUTASI PER CABANG')   , 
            'period': date_stop
            }  

        where_account = " 1=1 "
        if account_ids :
            where_account=" aml.account_id  in %s " % str(
                tuple(account_ids)).replace(',)', ')')   
                           
        where_branch = " 1=1 "
        if branch_ids :
            where_branch = " aml.branch_id in %s " % str(
                tuple(branch_ids)).replace(',)', ')')             
        else :
            area_user = self.pool.get('res.users').browse(cr,uid,uid).branch_ids
            branch_ids_user = [b.id for b in area_user]
            where_branch = " aml.branch_id in %s " % str(
                tuple(branch_ids_user))
            
        where_journal = " 1=1 "
        if journal_ids :
            where_account=" aml.journal_id  in %s " % str(
                tuple(journal_ids)).replace(',)', ')')   
            
        where_move_state = " 1=1 "
        if status == 'all' :
            where_move_state=" m.state is not Null "
        elif status == 'posted' :
            where_move_state=" m.state = 'posted' "  
             
        where_period = " 1=1 "                               
        if period_id :
            where_period = " aml.period_id = '%s' " % period_id[0]
        
        where_start_date = " 1=1 "
        where_end_date = " 1=1 "                               
        if start_date :
            where_start_date = " aml.date >= '%s' " % start_date
        if end_date :
            where_end_date = " aml.date <= '%s' " % end_date
        
        query_trial_balance = "SELECT b.code as branch_code, a.code as account_code, a.sap as account_sap, a.name as account_name, "\
        "b.profit_centre as profit_centre, l.branch_id, l.account_id, l.debit as debit, l.credit as credit, l.debit - l.credit as balance , p.date_stop as date_stop "\
        "FROM account_account a INNER JOIN "\
        "(SELECT aml.branch_id, aml.account_id, aml.period_id, SUM(aml.debit) as debit, SUM(aml.credit) as credit "\
        "FROM account_move_line aml "\
        "WHERE "+where_branch+" AND "+where_account+" AND "+where_period+" AND "+where_start_date+" AND "+where_end_date+" AND "+where_journal+" "\
        "GROUP BY aml.branch_id, aml.account_id, aml.period_id) l "\
        "ON a.id = l.account_id "\
        "INNER JOIN wtc_branch b ON l.branch_id = b.id "\
        "LEFT JOIN account_period p ON p.id = l.period_id "\
        "ORDER BY l.branch_id,a.parent_left "
        
        
        move_selection = ""
        report_info = _('')
        move_selection += ""
            
        reports = [report_trial_balance_import_sun]

        conn_str = 'postgresql://' \
           + config.get('report_db_user', False) + ':' \
           + config.get('report_db_password', False) + '@' \
           + config.get('report_db_host', False) + ':' \
           + config.get('report_db_port', False) + '/' \
           + config.get('report_db_name', False)
        conn = db_connect(conn_str, True)
        cur = conn.cursor(False)
        cur.autocommit(True)

        for report in reports:
            # cr.execute(query_trial_balance)
            cur.execute(query_trial_balance)
            # all_lines = cr.dictfetchall()
            all_lines = cur.dictfetchall()
                
            move_lines = []            
            if all_lines:

                p_map = map(
                    lambda x: {
                        'no':0,
                        'branch_code': x['branch_code'].encode('ascii','ignore').decode('ascii') if x['branch_code'] != None else '',   
                        'account_code': x['account_code'].encode('ascii','ignore').decode('ascii') if x['account_code'] != None else '', 
                        'account': x['account_sap'].split('-')[0].encode('ascii','ignore').decode('ascii') if len(x['account_sap'].split('-')) > 0 and x['account_sap'] != None else x['account_sap'].encode('ascii','ignore').decode('ascii'), 
                        'profit_centre': x['profit_centre'].encode('ascii','ignore').decode('ascii') if x['profit_centre'] != None else '', 
                        'div': x['account_sap'].split('-')[1].encode('ascii','ignore').decode('ascii') if len(x['account_sap'].split('-')) > 1 and x['account_sap'] != None else '',
                        'dept': x['account_sap'].split('-')[2] if len(x['account_sap'].split('-')) > 2 and x['account_sap'] != None else '', 
                        'class': x['account_sap'].split('-')[3] if len(x['account_sap'].split('-')) > 3 and x['account_sap'] != None else '',
                        'type': x['account_sap'].split('-')[4] if len(x['account_sap'].split('-')) > 4 and x['account_sap'] != None else '',
                        'account_name': x['account_name'].encode('ascii','ignore').decode('ascii') if x['account_name'] != None else '', 
                        'transaction_amount': x['balance'],
                        'date_stop': x['date_stop'].encode('ascii','ignore').decode('ascii') if x['date_stop'] != None else '', 
                        'debit': x['debit'],
                        'credit': x['credit'],
                        },
                            
                    all_lines)
                
#                 for p in p_map:
#                     if p['branch_code'] not in map(
#                             lambda x: x.get('branch_code', None), move_lines):
#                         move_lines.append(p)
#                         account_move_lines = filter(
#                             lambda x: x['branch_code'] == p['branch_code'], all_lines)
#                         p.update({'lines': account_move_lines})
                report.update({'move_lines': p_map})
        cur.close()

        reports = filter(lambda x: x.get('move_lines'), reports)
        if not reports:
            reports = [{
            'type': 'import_sun',
            'title': '',
            'period': date_stop,
            'title_short': title_short_prefix + ', ' + _('LAPORAN MUTASI PER CABANG')  ,
                        'move_lines':
                            [ {
                        'no':0,
                        'branch_code': 'NO DATA FOUND',
                        'account_code':'NO DATA FOUND',
                        'account': 'NO DATA FOUND',
                        'profit_centre': 'NO DATA FOUND',
                        'div': 'NO DATA FOUND',
                        'dept':'NO DATA FOUND',
                        'class': 'NO DATA FOUND',
                        'type': 'NO DATA FOUND',
                        'account_name': 'NO DATA FOUND',
                        'transaction_amount': 0,
                        'date_stop':'NO DATA FOUND',
                        'debit': 0.0,
                        'credit': 0.0,
                        }], 
                        
            }]
        report_date = datetime_field.context_timestamp(
            cr, uid, datetime.now(), context
            ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        self.localcontext.update({
            'report_info': report_info,
            'report_date': report_date,
            'reports': reports,
            })
        super(wtc_trial_balance_import_sun_report_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(wtc_trial_balance_import_sun_report_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.wtc_account_move.report_trial_balance_import_sun'
    _inherit = 'report.abstract_report'
    _template = 'wtc_account_move.report_trial_balance_import_sun'
    _wrapped_report_class = wtc_trial_balance_import_sun_report_print
