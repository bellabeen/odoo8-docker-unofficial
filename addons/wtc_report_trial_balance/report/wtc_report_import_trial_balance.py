import time
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


class wtc_import_trial_balance_report_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(wtc_import_trial_balance_report_print, self).__init__(
            cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({
            'formatLang_zero2blank': self.formatLang_zero2blank,
            })

    def get_fiscalyear(self,period_id):
        cr = self.cr
        query_fiscal = "SELECT fiscalyear_id FROM account_period WHERE id = %s"
        
        cr.execute(query_fiscal, (period_id, ))
        fiscalyear_id = cr.fetchall()
        return fiscalyear_id[0][0]
    
    def get_period(self,period_id,fiscalyear_id):
        cr = self.cr
        query_period = "SELECT id from account_period " \
            "WHERE id < %s AND fiscalyear_id = %s "
            
        cr.execute(query_period, (period_id,fiscalyear_id ))
        period_ids = cr.fetchall() 
        period_id_kolek = []
        for id in period_ids:
            period_id_kolek.append(id)      
        if not period_id_kolek :
            return False 
             
        return period_id_kolek
            
    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context
        branch_ids = data['branch_ids']
        account_ids = data['account_ids']
        period_id = data['period_id']
        status = data['status']
        start_date = data['start_date']
        end_date = data['end_date']
        title_prefix = ''
        title_short_prefix = ''
        
        date_stop = self.pool.get('account.period').browse(cr,uid,period_id[0]).date_stop
        date_stop = datetime.strptime(date_stop, '%Y-%m-%d').strftime('%d %B %Y')
        report_import_trial_balance = {
            'type': 'BukuBesar',
            'title': '',
            'title_short': title_short_prefix + ', ' + _('LAPORAN BUKU BESAR'),
            'period': date_stop,
            'start_date': start_date,
            'end_date': end_date
            }  

        where_account = " 1=1 "
        if account_ids :
            where_account=" a.id  in %s " % str(
                tuple(account_ids)).replace(',)', ')')              
        where_branch = " 1=1 "
        if branch_ids :
            where_branch = " b.id in %s " % str(
                tuple(branch_ids)).replace(',)', ')')             
        else :
            area_user = self.pool.get('res.users').browse(cr,uid,uid).branch_ids
            branch_ids_user = [b.id for b in area_user]
            where_branch = " b.id in %s " % str(
                tuple(branch_ids_user))
        where_move_state = " 1=1 "
        if status == 'all' :
            where_move_state=" m.state is not Null "
        elif status == 'posted' :
            where_move_state=" m.state = 'posted' "   
        where_prev_period = " 1=1 "
        where_period = " 1=1 "                               
        if period_id :
            fiscalyear_id = self.get_fiscalyear(period_id[0])
            period_ids = self.get_period(period_id[0], fiscalyear_id)
            if period_ids :
                where_prev_period =" l.period_id  in %s " % str(
                    tuple(period_ids)).replace(',)', ')')
            else :
                where_prev_period = " 1!=1 "
                
            where_period = " l.period_id = '%s' " % period_id[0]
            
            where_prev_start_date = " 1!=1 "
            where_start_date = " 1=1 "
            where_end_date = " 1=1 "
            if start_date :
                where_prev_start_date = " l.date < '%s' " % start_date
                where_start_date = " l.date >= '%s' " % start_date
            if end_date :
                where_end_date = " l.date <= '%s' " % end_date
            
        query_trial_balance = "SELECT a.code as account_code, a.name as account_name, a.sap as account_sap, b.profit_centre as profit_centre, b.name as branch_name, COALESCE(line.saldo_awal_debit,0) as saldo_awal_debit, "\
            "COALESCE(line.saldo_awal_credit,0) as saldo_awal_credit, "\
            "COALESCE(line.mutasi_debit,0) as mutasi_debit, "\
            "COALESCE(line.mutasi_credit,0) as mutasi_credit, "\
            "saldo_awal_debit - saldo_awal_credit as saldo_awal, "\
            "saldo_awal_debit - saldo_awal_credit + mutasi_debit - mutasi_credit as saldo_akhir "\
            "FROM account_account a "\
            "LEFT JOIN "\
            "(SELECT COALESCE(aml1.account_id,aml2.account_id) as account_id, COALESCE(aml1.branch_id,aml2.branch_id) as branch_id, "\
            "COALESCE(aml1.saldo_awal_debit,0) as saldo_awal_debit, "\
            "COALESCE(aml1.saldo_awal_credit,0) as saldo_awal_credit, "\
            "COALESCE(aml2.mutasi_debit,0) as mutasi_debit, "\
            "COALESCE(aml2.mutasi_credit,0) as mutasi_credit FROM "\
            "(SELECT l.account_id as account_id, l.branch_id as branch_id, SUM(l.debit) as saldo_awal_debit, SUM(l.credit) as saldo_awal_credit "\
            "FROM account_move_line l LEFT JOIN account_move m ON l.move_id = m.id WHERE "+where_move_state+" AND ("+where_prev_period+" OR ("+where_period+" AND "+where_prev_start_date+")) GROUP BY l.account_id, l.branch_id) AS aml1 "\
            "FULL OUTER JOIN "\
            "(SELECT l.account_id as account_id, l.branch_id as branch_id, SUM(l.debit) as mutasi_debit, SUM(l.credit) as mutasi_credit "\
            "FROM account_move_line l LEFT JOIN account_move m ON l.move_id = m.id WHERE "+where_move_state+" AND "+where_period+" AND "+where_start_date+" AND "+where_end_date+" GROUP BY l.account_id, l.branch_id) AS aml2 "\
            "ON aml1.account_id = aml2.account_id AND aml1.branch_id = aml2.branch_id) line ON line.account_id = a.id "\
            "LEFT JOIN wtc_branch b ON line.branch_id = b.id "\
            "WHERE a.type != 'view' AND a.type != 'consolidation' AND a.type != 'closed' AND b.id is not null "\
            "AND "+where_branch+" AND "+where_account+" "\
            "ORDER BY b.code, a.parent_left"    
        
        move_selection = ""
        report_info = _('')
        move_selection += ""
            
        reports = [report_import_trial_balance]

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
            # a = cr.execute(query_trial_balance)
            cur.execute(query_trial_balance)
            # all_lines = cr.dictfetchall()
            all_lines = cur.dictfetchall()
            
            move_lines = []            
            if all_lines:

                p_map = map(
                    lambda x: {
                        'no':0,
                        'branch_name': x['branch_name'].encode('ascii','ignore').decode('ascii') if x['branch_name'] != None else '',    
                        'account': x['account_sap'].split('-')[0].encode('ascii','ignore').decode('ascii') if len(x['account_sap'].split('-')) > 0 and x['account_sap'] != None else x['account_sap'].encode('ascii','ignore').decode('ascii'), 
                        'profit_centre': x['profit_centre'].encode('ascii','ignore').decode('ascii') if x['profit_centre'] != None else '', 
                        'div': x['account_sap'].split('-')[1].encode('ascii','ignore').decode('ascii') if len(x['account_sap'].split('-')) > 1 and x['account_sap'] != None else '',
                        'dept': x['account_sap'].split('-')[2] if len(x['account_sap'].split('-')) > 2 and x['account_sap'] != None else '', 
                        'class': x['account_sap'].split('-')[3] if len(x['account_sap'].split('-')) > 3 and x['account_sap'] != None else '',
                        'type': x['account_sap'].split('-')[4] if len(x['account_sap'].split('-')) > 4 and x['account_sap'] != None else '',
                        'account_code': x['account_code'].encode('ascii','ignore').decode('ascii') if x['account_code'] != None else '',    
                        'account_name': x['account_name'].encode('ascii','ignore').decode('ascii') if x['account_name'] != None else '',    
                        'mutasi_debit': x['mutasi_debit'],
                        'mutasi_credit': x['mutasi_credit'],
                        },
                            
                    all_lines)
                
                report.update({'move_lines': p_map})
        cur.close()


        reports = filter(lambda x: x.get('move_lines'), reports)
        if not reports:
            reports = [{
            'type': 'BukuBesar',
            'title': '',
            'period': date_stop ,
            'title_short': title_short_prefix + ', ' + _('LAPORAN BUKU BESAR')   ,
                        'move_lines':
                            [{
                        'no':0,
                        'branch_name': 'NO DATA FOUND',
                        'account_code': 'NO DATA FOUND',
                        'account':'NO DATA FOUND',
                        'profit_centre':'NO DATA FOUND',
                        'div':'NO DATA FOUND',
                        'dept':'NO DATA FOUND',
                        'class':'NO DATA FOUND',
                        'type':'NO DATA FOUND',
                        'account_name': 'NO DATA FOUND',
                        'mutasi_debit': 0,
                        'mutasi_credit': 0,
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
        super(wtc_import_trial_balance_report_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(wtc_import_trial_balance_report_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.wtc_account_move_line.report_import_trial_balance'
    _inherit = 'report.abstract_report'
    _template = 'wtc_account_move_line.report_import_trial_balance'
    _wrapped_report_class = wtc_import_trial_balance_report_print
