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

from openerp import netsvc
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
import time
import datetime
import base64
from openerp.addons.wtc_account_report_zhr.report import cash_flow_report, neraca_report, laba_rugi_report
import openerp.addons.custom_style_xls
from openerp.addons.custom_style_xls import excel_css
import xlwt
from xlwt import *
import cStringIO

import logging
_log = logging.getLogger('smcus_new_account_report')

class smcus_new_accounting_report(osv.osv_memory):
    _name = "smcus.new.accounting.report"

    _columns = {
        'chart_account_id': fields.many2one('account.account', 'Chart of Account', help='Select Charts of Accounts', required=True, domain = [('parent_id','=',False)]),
        'account_report': fields.selection([('laba_rugi', 'Laporan Laba Rugi'),
                                         ('neraca', 'Neraca'),
                                         ('arus_kas', 'Arus Kas'),
                                        ], 'Report Name', required=True),
        'report_type': fields.selection([('std', 'Standard'),
                                         ('cmp', 'Comparison'),
                                         ('year', 'Yearly'),
                                        ], 'Report Type', required=True),
        'company_id': fields.related('chart_account_id', 'company_id', type='many2one', relation='res.company', string='Company', readonly=True),
        'date_to': fields.date("Per Date"),
        'date_to_cmp': fields.date("Compared Per Date"),
        'fiscalyear_id': fields.many2one('account.fiscalyear', 'Year'),
        'period_id': fields.many2one('account.period', 'Per Month', domain=[('special', '=', False)], ),
        'period_comp_id': fields.many2one('account.period', 'Compared to Month', domain=[('special', '=', False)], ),
        'state': fields.selection([('posted', 'All Posted Entries'),
                                         ('all', 'All Entries'),
                                        ], 'Target Moves', required=True),
        'state_x': fields.selection( ( ('choose','choose'),('get','get'),)), #xls
        'data_x': fields.binary('File', readonly=True),
        'name_x': fields.char('Filename', 100, readonly=True),  
        'branch_id': fields.many2one('wtc.branch', 'Branch'),
    }

    _defaults = {
        'state_x': lambda *a: 'choose',
    }

    def _get_period(self, cr, uid, context=None):
        if context is None:
            context = {}
        now = time.strftime('%Y-%m-%d')
        company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        domain = [('company_id', '=', company_id), ('date_start', '<', now), ('date_stop', '>', now)]
        periods = self.pool.get('account.period').search(cr, uid, domain, limit=1)
        return periods and periods[0] or False

    def _get_account(self, cr, uid, context=None):
        accounts = self.pool.get('account.account').search(cr, uid, [('parent_id', '=', False)], limit=1)
        return accounts and accounts[0] or False

    _defaults = {
        'date_to': fields.date.context_today,
        'state': 'posted',
        'report_type': 'std',
        'chart_account_id': _get_account,
        'period_id': _get_period,
    }

    def onchange_chart_id(self, cr, uid, ids, chart_account_id=False, context=None):
        company_id=False
        if chart_account_id:
            company_id = self.pool.get('account.account').browse(cr, uid, chart_account_id, context=context).company_id.id
        return {'value': {'company_id': company_id}}

    def onchange_period_id(self, cr, uid, ids, period_id=False, context=None):
        date_stop=False
        if period_id:
            date_stop = self.pool.get('account.period').browse(cr, uid, period_id, context=context).date_stop
        return {'value': {'date_to': date_stop}}

    def onchange_period_cmp_id(self, cr, uid, ids, period_cmp_id=False, context=None):
        date_stop=False
        if period_cmp_id:
            date_stop = self.pool.get('account.period').browse(cr, uid, period_cmp_id, context=context).date_stop
        return {'value': {'date_to_cmp': date_stop}}

    def _build_contexts(self, cr, uid, ids, data, context=None):
        if context is None:
            context = {}
        result = {}
        date_to = data['form']['date_to'] 
        result['fiscalyear'] = False
        result['journal_ids'] = False
        result['chart_account_id'] = 'chart_account_id' in data['form'] and data['form']['chart_account_id'] or False
        result['state']=data['form']['state']
        result['branch_id']=data['form']['branch_id']
        if data['form']['account_report'] in ('neraca', 'arus_kas'):
            result['fiscalyear'] = False
            result['journal_ids'] = False
            result['chart_account_id'] = 'chart_account_id' in data['form'] and data['form']['chart_account_id'] or False
            #bulan date_to
            month = time.strptime(date_to, '%Y-%m-%d').tm_mon
            year = time.strptime(date_to, '%Y-%m-%d').tm_year
            #make sure date_from is 01/01/2013
            first_month = datetime.date(day=1, month=1, year=year)
            date_from = first_month.strftime('%Y-%m-%d')
            result['date_from'] = date_from #dibuat default awal tahun
            result['date_to'] = data['form']['date_to'] 
        elif data['form']['account_report'] == 'laba_rugi':
            result['fiscalyear'] = False
            result['journal_ids'] = False
            result['chart_account_id'] = 'chart_account_id' in data['form'] and data['form']['chart_account_id'] or False
            #bulan date_to
            month = time.strptime(date_to, '%Y-%m-%d').tm_mon
            year = time.strptime(date_to, '%Y-%m-%d').tm_year
            #make sure date_from is 01/month/2013
            first_month = datetime.date(day=1, month=month, year=year)
            date_from = first_month.strftime('%Y-%m-%d')
            result['date_from'] = date_from #dibuat default awal bulan
            result['date_to'] = date_to
        return result

    def _build_contexts_2(self, cr, uid, ids, data, context=None):
        if context is None:
            context = {}
        result = {}
        date_to = data['form']['date_to_cmp']
        result['fiscalyear'] = False
        result['journal_ids'] = False
        result['chart_account_id'] = 'chart_account_id' in data['form'] and data['form']['chart_account_id'] or False
        result['state']=data['form']['state']
        result['branch_id']=data['form']['branch_id']
        
        if data['form']['account_report'] in ('neraca', 'arus_kas'):
            #bulan date_to
            month = time.strptime(date_to, '%Y-%m-%d').tm_mon
            year = time.strptime(date_to, '%Y-%m-%d').tm_year
            #make sure date_from is 01/01/2013
            first_month = datetime.date(day=1, month=1, year=year)
            date_from = first_month.strftime('%Y-%m-%d')
            result['date_from'] = date_from #dibuat default awal tahun
            result['date_to'] = date_to
        elif data['form']['account_report'] == 'laba_rugi':
            result['fiscalyear'] = False
            result['journal_ids'] = False
            result['chart_account_id'] = 'chart_account_id' in data['form'] and data['form']['chart_account_id'] or False
            #bulan date_to
            month = time.strptime(date_to, '%Y-%m-%d').tm_mon
            year = time.strptime(date_to, '%Y-%m-%d').tm_year
            #make sure date_from is 01/month/2013
            first_month = datetime.date(day=1, month=month, year=year)
            date_from = first_month.strftime('%Y-%m-%d')
            result['date_from'] = date_from #dibuat default awal bulan
            result['date_to'] = date_to
        return result

    def _build_comparison_context(self, cr, uid, ids, data, context=None):
        if context is None:
            context = {}
        result = {}
        result['fiscalyear'] = False
        result['journal_ids'] = False
        result['chart_account_id'] = 'chart_account_id' in data['form'] and data['form']['chart_account_id'] or False
        result['state']=data['form']['state']
        result['branch_id']=data['form']['branch_id']
        date_to = data['form']['date_to']
        if data['form']['account_report']=='arus_kas':     
            #bulan date_to
            month = time.strptime(date_to, '%Y-%m-%d').tm_mon
            year = time.strptime(date_to, '%Y-%m-%d').tm_year
            #make sure date_from is 01/01/2013
            first_month = datetime.date(day=1, month=1, year=year)
            date_from = first_month.strftime('%Y-%m-%d')
            first = datetime.date(day=1, month=month, year=year)
            # dapatkan tanggal sebelum 01/06/2013 yaitu 31/05/2013
            prev_month_end = first - datetime.timedelta(days=1)
            date_to_previous = prev_month_end.strftime('%Y-%m-%d')
            result['date_from'] = date_from
            result['date_to'] = date_to_previous
        return result

    def _build_comparison_context_2(self, cr, uid, ids, data, context=None):
        if context is None:
            context = {}
        result = {}
        result['fiscalyear'] = False
        result['journal_ids'] = False
        result['chart_account_id'] = 'chart_account_id' in data['form'] and data['form']['chart_account_id'] or False
        result['state']=data['form']['state']
        result['branch_id']=data['form']['branch_id']

        date_to = data['form']['date_to_cmp']
        if data['form']['account_report']=='arus_kas':     

            #bulan date_to
            month = time.strptime(date_to, '%Y-%m-%d').tm_mon
            year = time.strptime(date_to, '%Y-%m-%d').tm_year
            #make sure date_from is 01/01/2013
            first_month = datetime.date(day=1, month=1, year=year)
            date_from = first_month.strftime('%Y-%m-%d')
            first = datetime.date(day=1, month=month, year=year)
            # dapatkan tanggal sebelum 01/06/2013 yaitu 31/05/2013
            prev_month_end = first - datetime.timedelta(days=1)
            date_to_previous = prev_month_end.strftime('%Y-%m-%d')
            result['date_from'] = date_from
            result['date_to'] = date_to_previous
        return result

    #untuk neraca yg dibutuhkan used_context dan used_context_2
    #untuk arus kas yg dibutuhkan used_context(2) dan comparison nya
    #untuk laba rugi yg dibutuhkan used_context dan used_context_2
    def check_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = {}
        data['ids'] = context.get('active_ids', [])
        data['model'] = context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(cr, uid, ids, ['date_to', 'chart_account_id', 'account_report', 'report_type', 'state', 'fiscalyear_id', 'date_to_cmp', 'branch_id'], context=context)[0]
        for field in ['chart_account_id']:
            if isinstance(data['form'][field], tuple):
                data['form'][field] = data['form'][field][0]
        _log.info (data['form'])
        
        #cek sudah diset account reserved for laba rugi gak? untuk laporan neraca
        if data['form']['account_report']=='neraca':     
            account_ids = self.pool.get('account.account').search(cr, uid, [('smcus_laba_rugi','=', True)])
            if not account_ids:
                raise osv.except_osv(_('Error!'), _('Tolong set 1 Account sebagai Account Laba/Rugi Tahun Berjalan '))

        
        if data['form']['report_type']=='year': 
            #used_context
            year_obj = self.pool.get('account.fiscalyear').browse(cr, uid, data['form']['fiscalyear_id'][0])
            month = 1
            for period in year_obj.period_ids:
                if period.special:
                    continue
                data['form']['date_to']=period.date_stop
                used_context = self._build_contexts(cr, uid, ids, data, context=context)
                contextname='used_context_m'+str(month)
                data['form'][contextname] = used_context
                comparison_context = self._build_comparison_context(cr, uid, ids, data, context=context)
                contextname='comparison_context_m'+str(month)
                data['form'][contextname] = comparison_context
                month+=1
            _log.info(data['form'])
        else:
            #filter 1
            used_context = self._build_contexts(cr, uid, ids, data, context=context)
            data['form']['used_context'] = used_context
            comparison_context = self._build_comparison_context(cr, uid, ids, data, context=context)
            data['form']['comparison_context'] = comparison_context
            #filter 2
            used_context_2 = {}
            comparison_context_2 = {}
            if data['form']['report_type']=='cmp': 
                used_context_2 = self._build_contexts_2(cr, uid, ids, data, context=context)
                data['form']['used_context_2'] = used_context_2
                comparison_context_2 = self._build_comparison_context_2(cr, uid, ids, data, context=context)
                data['form']['comparison_context_2'] = comparison_context_2
        return self._print_report(cr, uid, ids, data, context=context)

    def _print_report(self, cr, uid, ids, data, context=None):
        if data['form']['account_report']=='arus_kas':   
            if data['form']['report_type']=='std': 
                return {
                    'type': 'ir.actions.report.xml',
                    'report_name': 'smcus.cash.flow.report.zhr',
                    'datas': data,
                }
            elif data['form']['report_type']=='cmp': 
                return {
                    'type': 'ir.actions.report.xml',
                    'report_name': 'smcus.cash.flow.cmp.report.zhr',
                    'datas': data,
                }
            elif data['form']['report_type']=='year': 
                return {
                    'type': 'ir.actions.report.xml',
                    'report_name': 'smcus.cash.flow.year.report.zhr',
                    'datas': data,
                }
        elif data['form']['account_report']=='neraca':   
            if data['form']['report_type']=='std': 
                return {
                    'type': 'ir.actions.report.xml',
                    'report_name': 'smcus.neraca.report.zhr',
                    'datas': data,
                }
            elif data['form']['report_type']=='cmp': 
                return {
                    'type': 'ir.actions.report.xml',
                    'report_name': 'smcus.neraca.cmp.report.zhr',
                    'datas': data,
                }
            elif data['form']['report_type']=='year': 
                return {
                    'type': 'ir.actions.report.xml',
                    'report_name': 'smcus.neraca.year.report.zhr',
                    'datas': data,
                }
        elif data['form']['account_report']=='laba_rugi':   
            if data['form']['report_type']=='std': 
                return {
                    'type': 'ir.actions.report.xml',
                    'report_name': 'smcus.laba.rugi.report.zhr',
                    'datas': data,
                }
            elif data['form']['report_type']=='cmp': 
                return {
                    'type': 'ir.actions.report.xml',
                    'report_name': 'smcus.laba.rugi.cmp.report.zhr',
                    'datas': data,
                }
            elif data['form']['report_type']=='year': 
                return {
                    'type': 'ir.actions.report.xml',
                    'report_name': 'smcus.laba.rugi.year.report.zhr',
                    'datas': data,
                }

    def excel_report(self, cr, uid, ids, data, context=None):
        if context is None:
            context = {}
        data = {}
        data['ids'] = context.get('active_ids', [])
        data['model'] = context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(cr, uid, ids, ['date_to', 'chart_account_id', 'account_report', 'report_type', 'state', 'fiscalyear_id', 'date_to_cmp', 'branch_id'], context=context)[0]
        for field in ['chart_account_id']:
            if isinstance(data['form'][field], tuple):
                data['form'][field] = data['form'][field][0]
        _log.info (data['form'])
        
        #cek sudah diset account reserved for laba rugi gak? untuk laporan neraca
        if data['form']['account_report']=='neraca':     
            account_ids = self.pool.get('account.account').search(cr, uid, [('smcus_laba_rugi','=', True)])
            if not account_ids:
                raise osv.except_osv(_('Error!'), _('Tolong set 1 Account sebagai Account Laba/Rugi Tahun Berjalan '))

        
        used_context = self._build_contexts(cr, uid, ids, data, context=context)
        data['form']['used_context'] = used_context
        if data['form']['report_type']=='year': 
            #used_context
            year_obj = self.pool.get('account.fiscalyear').browse(cr, uid, data['form']['fiscalyear_id'][0])
            month = 1
            for period in year_obj.period_ids:
                if period.special:
                    continue
                data['form']['date_to']=period.date_stop
                used_context = self._build_contexts(cr, uid, ids, data, context=context)
                contextname='used_context_m'+str(month)
                data['form'][contextname] = used_context
                comparison_context = self._build_comparison_context(cr, uid, ids, data, context=context)
                contextname='comparison_context_m'+str(month)
                data['form'][contextname] = comparison_context
                month+=1
            _log.info(data['form'])
        else:
            #filter 1
            comparison_context = self._build_comparison_context(cr, uid, ids, data, context=context)
            data['form']['comparison_context'] = comparison_context
            #filter 2
            used_context_2 = {}
            comparison_context_2 = {}
            if data['form']['report_type']=='cmp': 
                used_context_2 = self._build_contexts_2(cr, uid, ids, data, context=context)
                data['form']['used_context_2'] = used_context_2
                comparison_context_2 = self._build_comparison_context_2(cr, uid, ids, data, context=context)
                data['form']['comparison_context_2'] = comparison_context_2

        return self._print_excel_report(cr, uid, ids, data, context=context)

    def _print_excel_report(self, cr, uid, ids, data, context=None):
        wb = xlwt.Workbook()
        judul = 'rekap'
        header = 'LAPORAN'
        if data['form']['account_report']=='arus_kas':   
            context = data['form']['used_context']
            obj_report = cash_flow_report.report_account_common(cr, uid, 'cash.flow.report', context=context)
            lines = obj_report.get_lines(data)
            judul+='_arus_kas'
            header+=' ARUS KAS'
        elif data['form']['account_report']=='laba_rugi':   
            context = data['form']['used_context']
            obj_report = laba_rugi_report.report_account_common(cr, uid, 'laba.rugi.report', context=context)
            lines = obj_report.get_lines(data)
            judul+='_laba_rugi'
            header+=' LABA RUGI'
        elif data['form']['account_report']=='neraca':   
            context = data['form']['used_context']
            obj_report = neraca_report.report_account_common(cr, uid, 'neraca.report', context=context)
            lines = obj_report.get_lines(data)
            judul+='_neraca'
            header+=' NERACA'
        baris = 0
        if data['form']['report_type']=='std': 
            judul += '_standard'
            wsh = wb.add_sheet(judul)
            wsh.write_merge(baris, baris, 0, 1, header, excel_css.getstyle('style_line_title'))
            baris+=1
            wsh.write(baris,0,'PER '+time.strftime('%B %Y', time.strptime(data['form']['date_to'], '%Y-%m-%d')), excel_css.getstyle('style_desc_title'))
            baris+=1
            wsh.write(baris,0,'Branch '+(data['form']['branch_id'] and data['form']['branch_id'][1] or 'All'), excel_css.getstyle('style_desc_title'))
            baris +=2
            wsh.write(baris,0,'Name', excel_css.getstyle('style_line_title'))
            baris +=2
            #datas
            for line in lines:
                space=''
                l=2
                while l<line['level']:
                    space+='  '
                    l+=1
                if line['level']<=2:
                    wsh.write(baris,0,space+line['name'], excel_css.getstyle('style_reg_bold'))
                    wsh.write(baris,1,line['balance'], excel_css.getstyle('style_reg_number_bold'))
                else:               
                    wsh.write(baris,0,space+line['name'], excel_css.getstyle('style_reg'))
                    wsh.write(baris,1,line['balance'], excel_css.getstyle('style_reg_number'))
                baris+=1
        elif data['form']['report_type']=='cmp': 
            judul += '_perbandingan'
            wsh = wb.add_sheet(judul)
            wsh.write_merge(baris, baris, 0, 2, header, excel_css.getstyle('style_line_title'))
            baris+=1
            wsh.write_merge(baris, baris, 0, 2,'PER '+time.strftime('%B %Y', time.strptime(data['form']['date_to'], '%Y-%m-%d'))+' dan '+time.strftime('%B %Y', time.strptime(data['form']['date_to_cmp'], '%Y-%m-%d')), excel_css.getstyle('style_desc_title'))
            baris+=1
            wsh.write(baris,0,'Branch '+(data['form']['branch_id'] and data['form']['branch_id'][1] or 'All'), excel_css.getstyle('style_desc_title'))
            baris +=2
            wsh.write(baris,0,'Name', excel_css.getstyle('style_line_title'))
            wsh.write(baris,1,'PER ' +time.strftime('%b %Y', time.strptime(data['form']['date_to'], '%Y-%m-%d')), excel_css.getstyle('style_line_title'))
            wsh.write(baris,2,'PER ' +time.strftime('%b %Y', time.strptime(data['form']['date_to_cmp'], '%Y-%m-%d')), excel_css.getstyle('style_line_title'))
            baris +=2
            for line in lines:
                space=''
                l=2
                while l<line['level']:
                    space+='  '
                    l+=1
                if line['level']<=2:
                    wsh.write(baris,0,space+line['name'], excel_css.getstyle('style_reg_bold'))
                    wsh.write(baris,1,line['balance'], excel_css.getstyle('style_reg_number_bold'))
                    wsh.write(baris,2,line['balance_cmp'], excel_css.getstyle('style_reg_number_bold'))
                else:               
                    wsh.write(baris,0,space+line['name'], excel_css.getstyle('style_reg'))
                    wsh.write(baris,1,line['balance'], excel_css.getstyle('style_reg_number'))
                    wsh.write(baris,2,line['balance_cmp'], excel_css.getstyle('style_reg_number'))
                baris+=1
        elif data['form']['report_type']=='year': 
            judul += '_tahunan'
            wsh = wb.add_sheet(judul)
            wsh.write_merge(baris, baris, 0, 12, header, excel_css.getstyle('style_line_title'))
            baris+=1
            wsh.write_merge(baris, baris, 0, 12,'PER '+data['form']['fiscalyear_id'][1], excel_css.getstyle('style_desc_title'))
            baris+=1
            wsh.write(baris,0,'Branch '+(data['form']['branch_id'] and data['form']['branch_id'][1] or 'All'), excel_css.getstyle('style_desc_title'))
            baris +=2
            wsh.write(baris,0,'Name', excel_css.getstyle('style_line_title'))
            wsh.write(baris,1,'1-'+data['form']['fiscalyear_id'][1], excel_css.getstyle('style_line_title'))
            wsh.write(baris,2,'2-'+data['form']['fiscalyear_id'][1], excel_css.getstyle('style_line_title'))
            wsh.write(baris,3,'3-'+data['form']['fiscalyear_id'][1], excel_css.getstyle('style_line_title'))
            wsh.write(baris,4,'4-'+data['form']['fiscalyear_id'][1], excel_css.getstyle('style_line_title'))
            wsh.write(baris,5,'5-'+data['form']['fiscalyear_id'][1], excel_css.getstyle('style_line_title'))
            wsh.write(baris,6,'6-'+data['form']['fiscalyear_id'][1], excel_css.getstyle('style_line_title'))
            wsh.write(baris,7,'7-'+data['form']['fiscalyear_id'][1], excel_css.getstyle('style_line_title'))
            wsh.write(baris,8,'8-'+data['form']['fiscalyear_id'][1], excel_css.getstyle('style_line_title'))
            wsh.write(baris,9,'9-'+data['form']['fiscalyear_id'][1], excel_css.getstyle('style_line_title'))
            wsh.write(baris,10,'10-'+data['form']['fiscalyear_id'][1], excel_css.getstyle('style_line_title'))
            wsh.write(baris,11,'11-'+data['form']['fiscalyear_id'][1], excel_css.getstyle('style_line_title'))
            wsh.write(baris,12,'12-'+data['form']['fiscalyear_id'][1], excel_css.getstyle('style_line_title'))

            baris +=2
            for line in lines:
                _log.info (line)
                space=''
                l=2
                while l<line['level']:
                    space+='  '
                    l+=1
                if line['level']<=2:
                    wsh.write(baris,0,space+line['name'], excel_css.getstyle('style_reg_bold'))
                    wsh.write(baris,1,line['balance'], excel_css.getstyle('style_reg_number_bold'))
                    wsh.write(baris,2,line['balance_cmp_m2'], excel_css.getstyle('style_reg_number_bold'))
                    wsh.write(baris,3,line['balance_cmp_m3'], excel_css.getstyle('style_reg_number_bold'))
                    wsh.write(baris,4,line['balance_cmp_m4'], excel_css.getstyle('style_reg_number_bold'))
                    wsh.write(baris,5,line['balance_cmp_m5'], excel_css.getstyle('style_reg_number_bold'))
                    wsh.write(baris,6,line['balance_cmp_m6'], excel_css.getstyle('style_reg_number_bold'))
                    wsh.write(baris,7,line['balance_cmp_m7'], excel_css.getstyle('style_reg_number_bold'))
                    wsh.write(baris,8,line['balance_cmp_m8'], excel_css.getstyle('style_reg_number_bold'))
                    wsh.write(baris,9,line['balance_cmp_m9'], excel_css.getstyle('style_reg_number_bold'))
                    wsh.write(baris,10,line['balance_cmp_m10'], excel_css.getstyle('style_reg_number_bold'))
                    wsh.write(baris,11,line['balance_cmp_m11'], excel_css.getstyle('style_reg_number_bold'))
                    wsh.write(baris,12,line['balance_cmp_m12'], excel_css.getstyle('style_reg_number_bold'))
                else:               
                    wsh.write(baris,0,space+line['name'], excel_css.getstyle('style_reg'))
                    wsh.write(baris,1,line['balance'], excel_css.getstyle('style_reg_number'))
                    wsh.write(baris,2,line['balance_cmp_m2'], excel_css.getstyle('style_reg_number'))
                    wsh.write(baris,3,line['balance_cmp_m3'], excel_css.getstyle('style_reg_number'))
                    wsh.write(baris,4,line['balance_cmp_m4'], excel_css.getstyle('style_reg_number'))
                    wsh.write(baris,5,line['balance_cmp_m5'], excel_css.getstyle('style_reg_number'))
                    wsh.write(baris,6,line['balance_cmp_m6'], excel_css.getstyle('style_reg_number'))
                    wsh.write(baris,7,line['balance_cmp_m7'], excel_css.getstyle('style_reg_number'))
                    wsh.write(baris,8,line['balance_cmp_m8'], excel_css.getstyle('style_reg_number'))
                    wsh.write(baris,9,line['balance_cmp_m9'], excel_css.getstyle('style_reg_number'))
                    wsh.write(baris,10,line['balance_cmp_m10'], excel_css.getstyle('style_reg_number'))
                    wsh.write(baris,11,line['balance_cmp_m11'], excel_css.getstyle('style_reg_number'))
                    wsh.write(baris,12,line['balance_cmp_m12'], excel_css.getstyle('style_reg_number'))
                baris+=1
    

 #           elif data['form']['report_type']=='cmp': 

#            elif data['form']['report_type']=='year': 

        wsh.col(0).width = 8400
        wsh.col(1).width = 4400
        wsh.col(2).width = 4400
        wsh.col(3).width = 4400
        wsh.col(4).width = 4400
        wsh.col(5).width = 4400
        wsh.col(6).width = 4400
        wsh.col(7).width = 4400
        wsh.col(8).width = 4400
        wsh.col(9).width = 4400
        wsh.col(10).width = 4400
        wsh.col(11).width = 4400
        wsh.col(12).width = 4400
        f = cStringIO.StringIO()
        wb.save(f)
        out=base64.encodestring(f.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name_x':judul + '.xls'}, context=context)
        ir_model_data = self.pool.get('ir.model.data')

        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_account_report_zhr', 'smcus_new_accounting_report')
        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'smcus.new.accounting.report',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
#            'target': 'new'
        }


smcus_new_accounting_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
