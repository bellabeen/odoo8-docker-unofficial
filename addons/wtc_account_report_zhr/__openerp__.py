# -*- encoding: utf-8 -*-
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

{
    'name': 'Custom Account Report - Zhr',
    'version': '1.1',
    'depends': ['account','wtc_account_journal'],
    'author': 'Siti Mawaddah',
    'description': """
Custom Account Report
=====================
v1.0 
----
New Account Report Look alike Zhr

v1.1 
-----
Arus Kas, Laporan Laba Rugi dan Neraca

v1.2 
----
add filter branch
    """,
    'website': 'http://www.berbagiopenerp.blogspot.com',
    'category': 'Custom Siti Mawaddah',
    'data': [
        'security/ir.model.access.csv',
        'account_view.xml',
        'wizard/smcus_new_account_financial_report_view.xml',
        'data/smcus.zhr.cash.flow.csv',
        #'data/account.account.csv',
    ],
    'auto_install': False,
    'installable': True,
    'application': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

