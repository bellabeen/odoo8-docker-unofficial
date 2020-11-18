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
_log = logging.getLogger('laba_rugi_report')

class report_account_common(report_sxw.rml_parse, common_report_header):
    _name = 'laba.rugi.report'
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

    def get_laba_rugi(self, new_context):
        #pendapatan - biaya
        #pendapatan
        account_obj = self.pool.get('account.account')
        total_pendapatan=0
        account_ids = account_obj.search(self.cr, self.uid, [('smcus_zhr_report','in', ['lr_pendapatan','lr_pendapatan_lain']),('type','!=','view')])
        if account_ids:
            for account in account_obj.browse(self.cr, self.uid, account_ids, context=new_context):
                total_pendapatan += account.balance
        total_pendapatan=(total_pendapatan*-1)
        total_biaya=0
        account_ids = account_obj.search(self.cr, self.uid, [('smcus_zhr_report','in', ['lr_biaya_pendapatan','lr_biaya_operasional','lr_biaya_lain']),('type','!=','view')])
        if account_ids:
            for account in account_obj.browse(self.cr, self.uid, account_ids, context=new_context):
                total_biaya += account.balance
        laba_rugi = total_pendapatan-total_biaya
        return laba_rugi

    def get_lines(self, data):
        lines = []
        _log.info ('=================================LABA RUGI====================================')
        _log.info (data['form'])
        account_obj = self.pool.get('account.account')
        currency_obj = self.pool.get('res.currency')

        report_type = data['form']['report_type']
        used_context = {}
        used_context_2 = {}
        nextcontext={}
        iscmp=False
        isyear=False
        if report_type == 'cmp':
            old_used_context_2 = data['form']['used_context_2']
            _log.info(old_used_context_2)
            used_context_2 = dict(old_used_context_2, lang=self.context.get('lang', 'en_US'))
            iscmp=True
        if report_type == 'year':
            isyear=True
            old_used_context = data['form']['used_context_m1']
            used_context = dict(old_used_context, lang=self.context.get('lang', 'en_US'))
            m=2
            while m<=12:
                contextname='used_context_m'+str(m)
                old_used_context = data['form'][contextname]
                nextcontext[m] = dict(old_used_context, lang=self.context.get('lang', 'en_US'))
                m+=1
            _log.info(nextcontext)
        else:
            old_used_context = data['form']['used_context']
            used_context = dict(old_used_context, lang=self.context.get('lang', 'en_US'))

        #bagian laba/rugi kotor
        report_h = [
            {'code': 'lr_pendapatan','name':'Pendapatan'},
            {'code': 'lr_biaya_pendapatan','name':'Biaya atas Pendapatan'},
            ]

        pendapatan = 0
        pendapatan_cmp = 0
        pendapatan_m = {}
        biaya = 0
        biaya_cmp = 0
        biaya_m = {}
        if isyear:
            m=2
            while m<=12:
                pendapatan_m[m]=0
                biaya_m[m]=0
                m+=1

        for report in report_h:
            rcode =  report['code']
            rname =  report['name']
            #Operating Activities
            vals_view = {
                'name': rname,
                'balance': '',
                'balance_cmp': '',
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
            lines.append(vals_view)
            total_head = 0
            total_head_cmp = 0
            total_head_m = {}
            if isyear:
                m=2
                while m<=12:
                    total_head_m[m]=0
                    m+=1

            account_ids = account_obj.search(self.cr, self.uid, [('smcus_zhr_report','=', rcode)])
            if account_ids:
                for account in account_obj.browse(self.cr, self.uid, account_ids, context=used_context):
                    balance = account.balance
                    if rcode=='lr_pendapatan':
                        balance = balance !=0 and balance*-1 or balance
                    vals = {
                        'name': account.code +' '+ account.name,
                        'balance':  balance,
                        'type': 'account',
                        'level': min(account.level + 1,6) or 6, 
                        'account_type': account.type,
                    }
                    if account.type!='view':
                        total_head+=balance

                    if iscmp:
                        balance_cmp = account_obj.browse(self.cr, self.uid, account.id, context=used_context_2).balance
                        if rcode=='lr_pendapatan':
                            balance_cmp = balance_cmp !=0 and balance_cmp*-1 or balance_cmp
                        vals['balance_cmp'] = balance_cmp
                        if account.type!='view':
                            total_head_cmp+=balance_cmp                                
                        
                    if isyear:
                        m=2
                        while m<=12:
                            balance_m = account_obj.browse(self.cr, self.uid, account.id, context=nextcontext[m]).balance
                            if rcode=='lr_pendapatan':
                                balance_m = balance_m !=0 and balance_m*-1 or balance_m
                            vals['balance_cmp_m'+str(m)] = balance_m
                            if account.type!='view':
                                total_head_m[m]+=balance_m                                       
                            m+=1

                    lines.append(vals)
                        
            vals_view = {
                'name': 'Total '+rname,
                'balance': total_head,
                'balance_cmp': total_head_cmp,
                'type': 'report',
                'level': 1,
                'account_type': 'view', 
            }
            if isyear:
                m=2
                while m<=12:
                    vals_view['balance_cmp_m'+str(m)] = total_head_m[m]
                    m+=1

            lines.append(vals_view)
            if rcode=='lr_pendapatan':
                pendapatan+=total_head
                pendapatan_cmp+=total_head_cmp
                if isyear:
                    m=2
                    while m<=12:
                        pendapatan_m[m]+=total_head_m[m]
                        m+=1

            else:
                biaya+=total_head
                biaya_cmp+=total_head_cmp
                if isyear:
                    m=2
                    while m<=12:
                        biaya_m[m]+=total_head_m[m]
                        m+=1
                
        laba_rugi_kotor=pendapatan-biaya
        laba_rugi_kotor_cmp=pendapatan_cmp-biaya_cmp
                       
        vals_view = {
            'name': 'Laba/Rugi Kotor',
            'balance': laba_rugi_kotor,
            'balance_cmp': laba_rugi_kotor_cmp,
            'type': 'view',
            'level': 0,
            'account_type': 'view', 
        }
        if isyear:
            m=2
            while m<=12:
                vals_view['balance_cmp_m'+str(m)] = pendapatan_m[m]-biaya_m[m]
                m+=1

        lines.append(vals_view)
        vals_view = {
            'name': '',
            'balance': '',
            'balance_cmp': '',
            'type': 'view',
            'level': 3,
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
        lines.append(vals_view)
        vals_view = {
            'name': '',
            'balance': '',
            'balance_cmp': '',
            'type': 'view',
            'level': 3,
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
        lines.append(vals_view)

        #Laba rugi operasional
        report_k = [
            {'code': 'lr_biaya_operasional','name':'Pengeluaran Operasional'},
            ]
        p_operasional = 0
        p_operasional_cmp = 0
        p_operasional_m = {}
        if isyear:
            m=2
            while m<=12:
                p_operasional_m[m]=0
                m+=1
        for report in report_k:
            rcode =  report['code']
            rname =  report['name']
            #Operating Activities
            vals_view = {
                'name': rname,
                'balance': '',
                'balance_cmp': '',
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
            lines.append(vals_view)
            total_head = 0
            total_head_cmp = 0
            total_head_m = {}
            if isyear:
                m=2
                while m<=12:
                    total_head_m[m]=0
                    m+=1
            account_ids = account_obj.search(self.cr, self.uid, [('smcus_zhr_report','=', rcode)])
            if account_ids:
                for account in account_obj.browse(self.cr, self.uid, account_ids, context=used_context):                        
                    balance = account.balance
                        
                    vals = {
                        'name': account.code +' '+ account.name,
                        'balance':  balance !=0 and balance or balance,
                        'type': 'account',
                        'level': min(account.level + 1,6) or 6, 
                        'account_type': account.type,
                    }
                    
                    if iscmp:
                        balance_cmp = account_obj.browse(self.cr, self.uid, account.id, context=used_context_2).balance
                                
                        vals['balance_cmp'] = balance_cmp !=0 and balance_cmp or balance_cmp
                        if account.type!='view':
                            total_head_cmp+=balance_cmp

                    if isyear:
                        m=2
                        while m<=12:
                            balance_m = account_obj.browse(self.cr, self.uid, account.id, context=nextcontext[m]).balance
                            if rcode=='lr_pendapatan':
                                balance_m = balance_m !=0 and balance_m*-1 or balance_m
                            vals['balance_cmp_m'+str(m)] = balance_m
                            if account.type!='view':
                                total_head_m[m]+=balance_m                                       
                            m+=1

                    lines.append(vals)
                        
                    if account.type!='view':
                        total_head+=balance

            vals_view = {
                'name': 'Total '+rname,
                'balance': total_head,
                'balance_cmp': total_head_cmp,
                'type': 'report',
                'level': 1,
                'account_type': 'view', 
            }
            if isyear:
                m=2
                while m<=12:
                    vals_view['balance_cmp_m'+str(m)] = total_head_m[m]
                    m+=1
            lines.append(vals_view)
            p_operasional+=total_head        
            p_operasional_cmp+=total_head_cmp        
            if isyear:
                m=2
                while m<=12:
                    p_operasional_m[m]+=total_head_m[m]
                    m+=1

        laba_rugi_operasional=laba_rugi_kotor-p_operasional
        laba_rugi_operasional_cmp=laba_rugi_kotor_cmp-p_operasional_cmp        
                       
        vals_view = {
            'name': 'Laba/Rugi Operasi',
            'balance': laba_rugi_operasional,
            'balance_cmp': laba_rugi_operasional_cmp,
            'type': 'view',
            'level': 0,
            'account_type': 'view', 
        }

        if isyear:
            m=2
            while m<=12:
                vals_view['balance_cmp_m'+str(m)] = pendapatan_m[m]-biaya_m[m]-p_operasional_m[m]
                m+=1
        lines.append(vals_view)
        vals_view = {
            'name': '',
            'balance': '',
            'balance_cmp': '',
            'type': 'view',
            'level': 3,
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
        lines.append(vals_view)
        vals_view = {
            'name': '',
            'balance': '',
            'balance_cmp': '',
            'type': 'view',
            'level': 3,
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
        lines.append(vals_view)
        
        #bagian pendapatan/pengeluaran lain
        report_h = [
            {'code': 'lr_pendapatan_lain','name':'Pendapatan Lain'},
            {'code': 'lr_biaya_lain','name':'Pengeluaran Lain'},
            ]

        p_lain = 0
        p_lain_cmp = 0
        b_lain = 0
        b_lain_cmp = 0
        p_lain_m = {}
        b_lain_m = {}
        if isyear:
            m=2
            while m<=12:
                p_lain_m[m]=0
                b_lain_m[m]=0
                m+=1
                
        for report in report_h:
            rcode =  report['code']
            rname =  report['name']
            #Operating Activities
            vals_view = {
                'name': rname,
                'balance': '',
                'balance_cmp': '',
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
            lines.append(vals_view)
            total_head = 0
            total_head_cmp = 0
            total_head_m = {}
            if isyear:
                m=2
                while m<=12:
                    total_head_m[m]=0
                    m+=1
            account_ids = account_obj.search(self.cr, self.uid, [('smcus_zhr_report','=', rcode)])
            if account_ids:
                for account in account_obj.browse(self.cr, self.uid, account_ids, context=used_context):
                    balance = account.balance
                    if rcode=='lr_pendapatan_lain':
                        balance = balance !=0 and balance*-1 or balance
                    vals = {
                        'name': account.code +' '+ account.name,
                        'balance':  balance,
                        'type': 'account',
                        'level': min(account.level + 1,6) or 6, 
                        'account_type': account.type,
                    }
                    if account.type!='view':
                        total_head+=balance

                    if iscmp:
                        balance_cmp = account_obj.browse(self.cr, self.uid, account.id, context=used_context_2).balance
                        if rcode=='lr_pendapatan_lain':
                            balance_cmp = balance_cmp !=0 and balance_cmp*-1 or balance_cmp
                        vals['balance_cmp'] = balance_cmp
                        if account.type!='view':
                            total_head_cmp+=balance_cmp

                    if isyear:
                        m=2
                        while m<=12:
                            balance_m = account_obj.browse(self.cr, self.uid, account.id, context=nextcontext[m]).balance
                            if rcode=='lr_pendapatan_lain':
                                balance_m = balance_m !=0 and balance_m*-1 or balance_m
                            vals['balance_cmp_m'+str(m)] = balance_m
                            if account.type!='view':
                                total_head_m[m]+=balance_m                                       
                            m+=1
                    
                    lines.append(vals)
                        
            vals_view = {
                'name': 'Total '+rname,
                'balance': total_head,
                'balance_cmp': total_head_cmp,
                'type': 'report',
                'level': 1,
                'account_type': 'view', 
            }
            if isyear:
                m=2
                while m<=12:
                    vals_view['balance_cmp_m'+str(m)] = total_head_m[m]
                    m+=1
            lines.append(vals_view)

            if rcode=='lr_pendapatan_lain':
                p_lain+=total_head
                p_lain_cmp+=total_head_cmp
                if isyear:
                    m=2
                    while m<=12:
                        p_lain_m[m]+=total_head_m[m]
                        m+=1
            else:
                b_lain+=total_head
                b_lain_cmp+=total_head_cmp
                if isyear:
                    m=2
                    while m<=12:
                        b_lain_m[m]+=total_head_m[m]
                        m+=1
                       
        laba_rugi_bersih=laba_rugi_operasional+p_lain-b_lain
        laba_rugi_bersih_cmp=laba_rugi_operasional_cmp+p_lain_cmp-b_lain_cmp

        vals_view = {
            'name': 'Net Profit',
            'balance': laba_rugi_bersih,
            'balance_cmp': laba_rugi_bersih_cmp,
            'type': 'view',
            'level': 0,
            'account_type': 'view', 
        }
        if isyear:
            m=2
            while m<=12:
                vals_view['balance_cmp_m'+str(m)] =  pendapatan_m[m]-biaya_m[m]-p_operasional_m[m]+p_lain_m[m]-b_lain_m[m]
                m+=1

        lines.append(vals_view)

        return lines

report_sxw.report_sxw('report.smcus.laba.rugi.report.zhr', 'account.financial.report',
    'addons/wtc_account_report_zhr/report/laba_rugi_report.rml', parser=report_account_common, header='internal')
report_sxw.report_sxw('report.smcus.laba.rugi.cmp.report.zhr', 'account.financial.report',
    'addons/wtc_account_report_zhr/report/laba_rugi_report_cmp.rml', parser=report_account_common, header='internal')
report_sxw.report_sxw('report.smcus.laba.rugi.year.report.zhr', 'account.financial.report',
    'addons/wtc_account_report_zhr/report/laba_rugi_report_year.rml', parser=report_account_common, header='internal landscape')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
