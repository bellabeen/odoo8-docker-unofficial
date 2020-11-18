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

import time
from openerp.osv import osv
from openerp.report import report_sxw
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class wtc_work_order_wip(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(wtc_work_order_wip, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'tgl_tarik': self._get_default_date,
            'get_pricelist': self._get_pricelist,
            'lines_a': self._lines_a,
            'no_urut': self.no_urut,
            
        })

        self.no = 0
    def no_urut(self):
        self.no+=1
        return self.no

    def _get_pricelist(self, pricelist_id):
        pricelist = self.pool.get('product.pricelist').read(self.cr, self.uid, [pricelist_id], ['name'], context=self.localcontext)[0]
        return pricelist['name']
    
    def _get_default_date(self):
        date_now =  datetime.now()+ relativedelta(hours=7)
        return date_now.strftime('%Y-%m-%d %H:%M')
 
    def _lines_a(self, accounts):
        branch_id = accounts['branch_id']
        WHERE = " WHERE wo.state in ('waiting_for_approval','confirmed','approved','finished')"
        if branch_id:
            WHERE += " AND wo.branch_id = %d" %(branch_id)
        query = """
            SELECT wo.name as name
                , to_char(wo.date, 'DD Mon YYYY') as date
                , wo.no_pol as no_pol
                , lot.name as no_engine
                , pt.name as tipe
                , wo.state as state
                , wo.state_wo as state_wo
                , wol.categ_id as division
                , '[' || COALESCE(prod.default_code,'') ||'] '|| COALESCE(tmpl.name,'') as jasa_service
                , wol.product_qty
                , wol.supply_qty
            FROM wtc_work_order wo
            INNER JOIN wtc_work_order_line wol ON wol.work_order_id = wo.id
            INNER JOIN product_product prod ON prod.id = wol.product_id
            INNER JOIN product_template tmpl ON tmpl.id = prod.product_tmpl_id
            INNER JOIN stock_production_lot lot ON lot.id = wo.lot_id
            INNER JOIN product_product pp ON pp.id = lot.product_id
            INNER JOIN product_template pt ON pt.id = pp.product_tmpl_id
            %s
        """ %(WHERE)
        self.cr.execute(query)
        ress = self.cr.dictfetchall()
        data = {}
        result = []
        for res in ress:
            name = res.get('name',False)
            jasa = '-'
            part = '-'
            jasa_service = res['jasa_service']
            division = res['division']
            if division == 'Sparepart':
                part = jasa_service
            else:
                jasa = jasa_service
            state = None
            if res['state']:
                state = res['state'].replace('_',' ').title() 
            state_wo = None
            if res['state_wo']:
                state_wo = res['state_wo'].replace('_',' ').title()
            if not data.get(name):
                data[name] = [{
                    'name':name,
                    'date':res['date'],
                    'no_pol':res['no_pol'],
                    'no_engine':res['no_engine'],
                    'tipe':res['tipe'],
                    'part':part,
                    'jasa':jasa,
                    'state':state,
                    'state_wo':state_wo,
                    'product_qty':res['product_qty'],
                    'supply_qty':res['supply_qty']
                }]
            else:
                data[name].append({
                    'name':None,
                    'date':None,
                    'no_pol':None,
                    'no_engine':None,
                    'tipe':None,
                    'state':None,
                    'state_wo':None,
                    'jasa':jasa,
                    'part':part,
                    'product_qty':res['product_qty'],
                    'supply_qty':res['supply_qty']
                })
        no = 1
        for x in data.values():
            for y in x:
                if y.get('name'):
                    y['no'] = no
                    no += 1
                else:
                    y['no'] = None
                result.append(y)
        return result
        
class report_wtc_work_order_wip(osv.AbstractModel):
    _name = 'report.wtc_work_order.wtc_work_order_wip_report'
    _inherit = 'report.abstract_report'
    _template = 'wtc_work_order.wtc_work_order_wip_report'
    _wrapped_report_class = wtc_work_order_wip

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
