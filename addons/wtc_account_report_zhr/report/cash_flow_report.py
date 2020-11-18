##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

import time

from openerp.report import report_sxw
from common_report_header import common_report_header
from openerp.tools.translate import _
import logging
_log = logging.getLogger('cash_flow_report')

class report_account_common(report_sxw.rml_parse, common_report_header):
    _name = 'cash.flow.report'

    def __init__(self, cr, uid, name, context=None):
        super(report_account_common, self).__init__(cr, uid, name, context=context)
        self.localcontext.update( {
            'get_lines': self.get_lines,
            'time': time,
            'get_fiscalyear': self._get_fiscalyear,
            'get_account': self._get_account,
            'get_start_period': self.get_start_period,
            'get_end_period': self.get_end_period,
            'has_filter': self._has_filter,
            'get_filter': self._get_filter,
            'get_start_date':self._get_start_date,
            'get_end_date':self._get_end_date,
        })
        self.context = context

    def set_context(self, objects, data, ids, report_type=None):
        new_ids = ids
        if (data['model'] == 'ir.ui.menu'):
            new_ids = 'chart_account_id' in data['form'] and [data['form']['chart_account_id']] or []
            objects = self.pool.get('account.account').browse(self.cr, self.uid, new_ids)
        return super(report_account_common, self).set_context(objects, data, new_ids, report_type=report_type)

    def get_lines(self, data):
        lines = []
        _log.info ('=====================================================================')
        _log.info (data['form'])
        account_obj = self.pool.get('account.account')
        cf_obj = self.pool.get('smcus.zhr.cash.flow')
        currency_obj = self.pool.get('res.currency')
        
        #new
        report_type = data['form']['report_type']
        used_context = {}
        used_context_2 = {}
        comparison_context = {}
        comparison_context_2 = {}
        iscmp=False
        isyear=False
        nextcontext={}
        nextcontextcmp={}
        if report_type == 'cmp':
            iscmp=True
            old_used_context = data['form']['used_context']
            used_context = dict(old_used_context, lang=self.context.get('lang', 'en_US'))
            
            old_used_context = data['form']['comparison_context']
            comparison_context = dict(old_used_context, lang=self.context.get('lang', 'en_US'))

            old_used_context = data['form']['used_context_2']
            used_context_2 = dict(old_used_context, lang=self.context.get('lang', 'en_US'))
            
            old_used_context = data['form']['comparison_context_2']
            comparison_context_2 = dict(old_used_context, lang=self.context.get('lang', 'en_US'))

        elif report_type == 'year':
            isyear=True
            old_used_context = data['form']['used_context_m1']
            used_context = dict(old_used_context, lang=self.context.get('lang', 'en_US'))

            old_used_context = data['form']['comparison_context_m1']
            comparison_context = dict(old_used_context, lang=self.context.get('lang', 'en_US'))
            m=2
            while m<=12:
                contextname='used_context_m'+str(m)
                old_used_context = data['form'][contextname]
                nextcontext[m] = dict(old_used_context, lang=self.context.get('lang', 'en_US'))
                
                contextname='comparison_context_m'+str(m)
                old_used_context = data['form'][contextname]
                nextcontextcmp[m] = dict(old_used_context, lang=self.context.get('lang', 'en_US'))
               
                m+=1
        else:
            old_used_context = data['form']['used_context']
            used_context = dict(old_used_context, lang=self.context.get('lang', 'en_US'))
            
            old_used_context = data['form']['comparison_context']
            comparison_context = dict(old_used_context, lang=self.context.get('lang', 'en_US'))
        
        #
        report_3 = [
            {'code': '1opr_activities','name':'Operating Activities'},
            {'code': '2inv_activities','name':'Investing Activities'},
            {'code': '3fin_activities','name':'Financing Activities'},
            ]
        total_kenaikan = 0
        total_kenaikan_cmp = 0
        total_kenaikan_m = {}
        if isyear:
            m=2
            while m<=12:
                total_kenaikan_m[m]=0
                m+=1

        for report in report_3:
            rcode =  report['code']
            rname =  report['name']
            #Operating Activities
            vals_view = {
                'name': rname,
                'balance': '',
                'type': 'report',
                'level': 2,
                'account_type': 'view', 
            }
            #cmp
            if iscmp:
                vals_view['balance_cmp'] = ''
            #year
            if isyear:
                m=2
                while m<=12:
                    vals_view['balance_cmp_m'+str(m)] = ''
                    m+=1
            #
            lines.append(vals_view)
            total_head = 0
            total_head_cmp = 0
            total_head_m = {}
            if isyear:
                m=2
                while m<=12:
                    total_head_m[m]=0
                    m+=1
            #cf_obj
            cf_ids = cf_obj.search(self.cr, self.uid, [('type','=', rcode)])
            if cf_ids:
                cf_data = cf_obj.browse(self.cr, self.uid, cf_ids)
                for cf in cf_data:
                    account_ids = account_obj.search(self.cr, self.uid, [('smcus_zhr_cash_flow','=', cf.id)])
                    if account_ids:
                        total_class = 0
                        total_class_cmp = 0
                        total_class_m = {}
                        if isyear:
                            m=2
                            while m<=12:
                                total_class_m[m]=0
                                m+=1
                                
                        for account in account_obj.browse(self.cr, self.uid, account_ids, context=used_context):
                            balance_previous = account_obj.browse(self.cr, self.uid, account.id, context=comparison_context).balance
                            balance = balance_previous - account.balance
                                
                            total_head+=balance
                            total_class+=balance
                            #cmp
                            if iscmp:
                                balance_cmp = account_obj.browse(self.cr, self.uid, account.id, context=used_context_2).balance
                                balance_cmp_previous = account_obj.browse(self.cr, self.uid, account.id, context=comparison_context_2).balance
                                balance_cmp = balance_cmp_previous - balance_cmp
                                total_head_cmp+=balance_cmp                                
                                total_class_cmp+=balance_cmp                                
                            
                            #year
                            if isyear:
                                m=2
                                while m<=12:
                                    balance_m = account_obj.browse(self.cr, self.uid, account.id, context=nextcontext[m]).balance
                                    balance_m_prev = account_obj.browse(self.cr, self.uid, account.id, context=nextcontextcmp[m]).balance
                                    balance_m = balance_m_prev - balance_m

                                    total_head_m[m]+=balance_m                                       
                                    total_class_m[m]+=balance_m                                       
                                    m+=1
                            #
                        vals = {
                            'name': cf.name,
                            'balance':  total_class,
                            'type': 'account',
                            'level': 3, 
                            'account_type': 'view',
                        }
                        #cmp
                        if iscmp:
                            vals['balance_cmp'] = total_class_cmp
                        #year
                        if isyear:
                            m=2
                            while m<=12:
                                vals['balance_cmp_m'+str(m)] = total_class_m[m]
                                m+=1
                        #
                        lines.append(vals)
                        
            total_kenaikan+=total_head
            vals_view = {
                'name': 'Net Cash Provided by '+rname,
                'balance': total_head,
                'type': 'report',
                'level': 1,
                'account_type': 'view', 
            }
            #cmp
            if iscmp:
                vals_view['balance_cmp'] = total_head_cmp
                total_kenaikan_cmp+=total_head_cmp
            #year
            if isyear:
                m=2
                while m<=12:
                    vals_view['balance_cmp_m'+str(m)] = total_head_m[m]
                    total_kenaikan_m[m]+=total_head_m[m]
                    m+=1
            #
        
            lines.append(vals_view)
            
        vals_view = {
            'name': '',
            'balance': '',
            'type': 'report',
            'level': 2,
            'account_type': 'view', 
        }
        #cmp
        if iscmp:
            vals_view['balance_cmp'] = ''
        #year
        if isyear:
            m=2
            while m<=12:
                vals_view['balance_cmp_m'+str(m)] = ''
                m+=1
        #
        lines.append(vals_view)
        vals_view = {
            'name': 'Net Cash Increase',
            'balance': total_kenaikan,
            'type': 'report',
            'level': 2,
            'account_type': 'view', 
        }
        #cmp
        if iscmp:
            vals_view['balance_cmp'] = total_kenaikan_cmp
        #year
        if isyear:
            m=2
            while m<=12:
                vals_view['balance_cmp_m'+str(m)] = total_kenaikan_m[m]
                m+=1
        lines.append(vals_view)
        #cash 
        total_balance_begining_period=0
        total_balance_end_period=0
        total_balance_begining_period_cmp=0
        total_balance_end_period_cmp=0
        total_balance_begining_period_m={}
        total_balance_end_period_m={}
        if isyear:
            m=2
            while m<=12:
                total_balance_begining_period_m[m]=0
                total_balance_end_period_m[m]=0
                m+=1

        cf_ids = cf_obj.search(self.cr, self.uid, [('type','=', '4kas')])
        if cf_ids:
            cf_data = cf_obj.browse(self.cr, self.uid, cf_ids)
            for cf in cf_data:
                account_ids = account_obj.search(self.cr, self.uid, [('smcus_zhr_cash_flow','=', cf.id)])
                if account_ids:
                    for account in account_obj.browse(self.cr, self.uid, account_ids, context=used_context):
                        balance_begining_period = account_obj.browse(self.cr, self.uid, account.id, context=comparison_context).balance
                        total_balance_begining_period+=balance_begining_period

                        balance_end_period = account.balance
                        total_balance_end_period+=balance_end_period

                        #cmp
                        if iscmp:
                            balance_begining_period_cmp = account_obj.browse(self.cr, self.uid, account.id, context=comparison_context_2).balance
                            total_balance_begining_period_cmp+=balance_begining_period_cmp
                            
                            balance_end_period_cmp = account_obj.browse(self.cr, self.uid, account.id, context=used_context_2).balance
                            total_balance_end_period_cmp+=balance_end_period_cmp
                        #year
                        if isyear:
                            m=2
                            while m<=12:
                                balance_begining_period_m = account_obj.browse(self.cr, self.uid, account.id, context=nextcontextcmp[m]).balance
                                total_balance_begining_period_m[m] += balance_begining_period_m
                                
                                balance_end_period_m = account_obj.browse(self.cr, self.uid, account.id, context=nextcontext[m]).balance
                                total_balance_end_period_m[m] += balance_end_period_m
                                       
                                m+=1

        vals_view = {
            'name': 'Cash at beginning of period',
            'balance': total_balance_begining_period,
            'type': 'report',
            'level': 2,
            'account_type': 'view', 
        }
        #cmp
        if iscmp:
            vals_view['balance_cmp'] = total_balance_begining_period_cmp
        #year
        if isyear:
            m=2
            while m<=12:
                vals_view['balance_cmp_m'+str(m)] = total_balance_begining_period_m[m]
                m+=1
            
        lines.append(vals_view)
        
        vals_view = {
            'name': 'Cash at end of period',
            'balance': total_balance_end_period,
            'type': 'report',
            'level': 1,
            'account_type': 'view', 
        }
        #cmp
        if iscmp:
            vals_view['balance_cmp'] = total_balance_end_period_cmp
        #year
        if isyear:
            m=2
            while m<=12:
                vals_view['balance_cmp_m'+str(m)] = total_balance_end_period_m[m]
                m+=1
        lines.append(vals_view)
        return lines

report_sxw.report_sxw('report.smcus.cash.flow.report.zhr', 'account.financial.report',
    'addons/wtc_account_report_zhr/report/cash_flow_report.rml', parser=report_account_common, header='internal')
report_sxw.report_sxw('report.smcus.cash.flow.cmp.report.zhr', 'account.financial.report',
    'addons/wtc_account_report_zhr/report/cash_flow_report_cmp.rml', parser=report_account_common, header='internal')
report_sxw.report_sxw('report.smcus.cash.flow.year.report.zhr', 'account.financial.report',
    'addons/wtc_account_report_zhr/report/cash_flow_report_year.rml', parser=report_account_common, header='internal landscape')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
