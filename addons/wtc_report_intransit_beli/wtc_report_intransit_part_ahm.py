import time
import cStringIO
import xlsxwriter
from cStringIO import StringIO
import base64
import tempfile
import os
from openerp.osv import fields, osv
from openerp.tools.translate import _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from xlsxwriter.utility import xl_rowcol_to_cell
import logging
import re
import pytz
_logger = logging.getLogger(__name__)
from lxml import etree

class wtc_report_intransit_part_ahm(osv.osv_memory):
   
    _inherit = "wtc.report.intransit.beli"

    wbf = {}

    def _print_excel_report_intransit_part_ahm(self, cr, uid, ids, data, context=None):
        fp = self._create_excel_file(cr, uid, ids, data, context=context)
        fp.close()
        return True

    def _create_excel_file(self, cr, uid, ids, data, context=None):
        query = self._query_intransit_part_ahm(
            branch_ids=data['branch_ids'] if 'branch_ids' in data else None,
            partner_ids=data['partner_ids'] if 'partner_ids' in data else None,
            division=data['division'] if 'division' in data else None,
            start_date=data['start_date'] if 'start_date' in data else None,
            end_date=data['end_date'] if 'end_date' in data else None,
        )

        cr.execute (query)
        ress = cr.fetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('Stock Intransit Part AHM')
        worksheet.set_column('B1:B1', 13)
        worksheet.set_column('C1:C1', 10)
        worksheet.set_column('D1:D1', 20)
        worksheet.set_column('E1:E1', 25)
        worksheet.set_column('F1:F1', 29)
        worksheet.set_column('G1:G1', 20)
        worksheet.set_column('H1:H1', 20)
        worksheet.set_column('I1:I1', 20)
        worksheet.set_column('J1:J1', 20)
        worksheet.set_column('K1:K1', 20)

        date = self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name

        filename = 'Report Intransit Part AHM '+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Laporan Stock Intransit Sparepart AHM' , wbf['title_doc'])

        row=4

        worksheet.write('A%s' % (row), 'No' , wbf['header'])
        worksheet.write('B%s' % (row), 'Branch Code' , wbf['header'])
        worksheet.write('C%s' % (row), 'Branch Name' , wbf['header'])
        worksheet.write('D%s' % (row), 'Division' , wbf['header'])
        worksheet.write('E%s' % (row), 'Supplier Code' , wbf['header'])
        worksheet.write('F%s' % (row), 'Supplier Name' , wbf['header'])
        worksheet.write('G%s' % (row), 'No PS' , wbf['header'])
        worksheet.write('H%s' % (row), 'No Picking' , wbf['header'])
        worksheet.write('I%s' % (row), 'Upload Date' , wbf['header'])
        worksheet.write('J%s' % (row), 'Product Name' , wbf['header'])
        worksheet.write('K%s' % (row), 'Qty' , wbf['header'])
        worksheet.write('L%s' % (row), 'HPP' , wbf['header'])
        worksheet.write('M%s' % (row), 'Subtotal' , wbf['header'])

        row+=1
        no = 1
        row1 = row

        total_qty = 0
        total_amt = 0

        for res in ress:
            branch_code = res[0].encode('ascii','ignore').decode('ascii') if res[0] != None else ''
            branch_name = res[1].encode('ascii','ignore').decode('ascii') if res[1] != None else ''
            division = res[2].encode('ascii','ignore').decode('ascii') if res[2] != None else ''
            supplier_code = res[3].encode('ascii','ignore').decode('ascii') if res[3] != None else ''
            supplier_name = res[4].encode('ascii','ignore').decode('ascii') if res[4] != None else ''
            no_ps = res[5].encode('ascii','ignore').decode('ascii') if res[5] != None else ''
            no_picking = res[6].encode('ascii','ignore').decode('ascii') if res[6] != None else ''
            date = datetime.strptime(res[7], "%Y-%m-%d").date() if res[7] else ''
            product_name = res[8].encode('ascii','ignore').decode('ascii') if res[8] != None else ''
            qty = res[9]
            hpp = res[10]

            worksheet.write('A%s' % row, no , wbf['content_number'])
            worksheet.write('B%s' % row, branch_code , wbf['content'])
            worksheet.write('C%s' % row, branch_name, wbf['content'])
            worksheet.write('D%s' % row, division, wbf['content'])
            worksheet.write('E%s' % row, supplier_code, wbf['content'])
            worksheet.write('F%s' % row, supplier_name, wbf['content'])
            worksheet.write('G%s' % row, no_ps, wbf['content'])
            worksheet.write('H%s' % row, no_picking, wbf['content'])
            worksheet.write('I%s' % row, date, wbf['content_date'])
            worksheet.write('J%s' % row, product_name, wbf['content'])
            worksheet.write('K%s' % row, qty, wbf['content_number'])
            worksheet.write('L%s' % row, hpp, wbf['content_float'])
            worksheet.write('M%s' % row, qty*hpp, wbf['content_float'])
            
            no+=1
            row+=1

            total_qty += qty
            total_amt += (qty*hpp)

        worksheet.autofilter('A%s:K%s' % (row1-1,row))  
        #worksheet.freeze_panes(13, 3)

        #TOTAL
        worksheet.merge_range('A%s:J%s' % (row,row), '', wbf['total'])
        worksheet.write_formula('K%s' % (row),'{=subtotal(9,K%s:K%s)}' % (row1, row-1), wbf['total_number'], total_qty)
        worksheet.write('L%s'%(row), '', wbf['total'])
        worksheet.write_formula('M%s' % (row),'{=subtotal(9,M%s:M%s)}' % (row1, row-1), wbf['total_float'], total_amt)

        worksheet.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])  
        workbook.close()
        out = base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        # fp.close()

        return fp

    def excel_report_daily_ahm(self, cr, uid, ids, data, context=None):
        date = self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")     
        filename = 'Intransit_Beli_Sparepart_AHM_'+str(date)+'.xlsx'        
        data = {
            'product_ids': [],
            'location_ids': [],
            'branch_ids': [40],
        }
        fp = self._create_excel_file(cr, uid, ids, data, context=context)
        path = '/opt/odoo/TDM/intransit_part_daily/'
        file = open(path+filename, 'w+b')
        file.write(fp.getvalue())
        fp.close()

    def _query_intransit_part_ahm(self, **kwargs):
        """
        This function will return query in string format.
        This function is intend to reach modularity,
        so another task can ask or perform this function
        such as resapi and print report
        """
        branch_ids = kwargs['branch_ids'] if 'branch_ids' in kwargs else None
        partner_ids = kwargs['partner_ids'] if 'partner_ids' in kwargs else None
        division = kwargs['division'] if 'division' in kwargs else None
        start_date = kwargs['start_date'] if 'start_date' in kwargs else None
        end_date = kwargs['end_date'] if 'end_date' in kwargs else None
        
        query = """
            select b.code as branch_code
            , b.name as branch_name
            , sp.division as division
            , rp.default_code as supplier_code
            , rp.name as supplier_name
            , sp.origin as no_ps
            , sp.name as no_picking
            , (sm.create_date + interval '7 hours')::timestamp::date as upload_date
            , p.name_template as product_name
            , sm.product_uom_qty as product_qty
            , sm.price_unit / 1.1 as hpp
            from stock_picking sp
            inner join stock_move sm on sp.id = sm.picking_id
            left join wtc_branch b on sp.branch_id = b.id
            left join res_partner rp on rp.id = sp.partner_id
            left join stock_picking_type spt on sp.picking_type_id = spt.id 
            left join product_product p on sm.product_id = p.id
            where spt.code = 'incoming'
            and sp.state = 'assigned'
            and rp.default_code = 'AHM'
            and sp.division = 'Sparepart'
            and sp.branch_id in %s

            order by b.code, rp.default_code, sp.origin, p.name_template, sm.product_uom_qty desc
            """ % (str(tuple(branch_ids)).replace(',)', ')'))

        return query