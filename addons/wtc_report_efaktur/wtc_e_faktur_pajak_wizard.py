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

class wtc_e_faktur_pajak(osv.osv_memory):

    _name = "wtc.e.faktur.pajak.wizard"
    _description = "E-Faktur Pajak"

    wbf = {}

    _columns = {
        'state_x': fields.selection( ( ('choose','choose'),('get','get'))), #xls
        'data_x': fields.binary('File', readonly=True),
        'name': fields.char('Filename', 100, readonly=True),
        'start_date': fields.date('Start Date', required=True),
        'end_date': fields.date('End Date', required=True),
        'partner_ids': fields.many2many('res.partner','wtc_report_efaktur_partner_rel','wtc_e_faktur_pajak_wizard_id'),
        'no_faktur': fields.char('No. Faktur'),
        'ref': fields.char('No Transaksi'),
    }

    _defaults = {
        'state_x': lambda *a: 'choose',
    }

    def _get_default(self,cr,uid,date=False,user=False,context=None):
        if date :
            return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)
        else :
            return self.pool.get('res.users').browse(cr, uid, uid)

    def add_workbook_format(self, cr, uid, workbook):
        self.wbf['header'] = workbook.add_format({'bold': 1,'align': 'center','bg_color': '#FFFFDB','font_color': '#000000'})
        self.wbf['header'].set_border()

        self.wbf['header_no'] = workbook.add_format({'bold': 1,'align': 'center','bg_color': '#FFFFDB','font_color': '#000000'})
        self.wbf['header_no'].set_border()
        self.wbf['header_no'].set_align('vcenter')

        self.wbf['header_merged'] = workbook.add_format({'bold': 1,'align': 'center', 'valign': 'vcenter' ,'bg_color': '#FFFFDB','font_color': '#000000'})
        self.wbf['header_merged'].set_border()
        self.wbf['header_merged'].set_align('vcenter')

        self.wbf['footer'] = workbook.add_format({'align':'left'})
        
        self.wbf['content_datetime'] = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss'})
        self.wbf['content_datetime'].set_left()
        self.wbf['content_datetime'].set_right()
                
        self.wbf['content_date'] = workbook.add_format({'num_format': 'yyyy-mm-dd'})
        self.wbf['content_date'].set_left()
        self.wbf['content_date'].set_right() 
        
        self.wbf['title_doc'] = workbook.add_format({'bold': 1,'align': 'left'})
        self.wbf['title_doc'].set_font_size(12)
        
        self.wbf['company'] = workbook.add_format({'align': 'left'})
        self.wbf['company'].set_font_size(11)
        
        self.wbf['content'] = workbook.add_format()
        self.wbf['content'].set_left()
        self.wbf['content'].set_right() 
        
        self.wbf['content_float'] = workbook.add_format({'align': 'right','num_format': '#,##0.00'})
        self.wbf['content_float'].set_right() 
        self.wbf['content_float'].set_left()

        self.wbf['content_number'] = workbook.add_format({'align': 'right'})
        self.wbf['content_number'].set_right() 
        self.wbf['content_number'].set_left() 
        
        self.wbf['content_percent'] = workbook.add_format({'align': 'right','num_format': '0.00%'})
        self.wbf['content_percent'].set_right() 
        self.wbf['content_percent'].set_left() 
                
        self.wbf['total_float'] = workbook.add_format({'bold':1,'bg_color': '#FFFFDB','align': 'right','num_format': '#,##0.00'})
        self.wbf['total_float'].set_top()
        self.wbf['total_float'].set_bottom()            
        self.wbf['total_float'].set_left()
        self.wbf['total_float'].set_right()         
        
        self.wbf['total_number'] = workbook.add_format({'align':'right','bg_color': '#FFFFDB','bold':1})
        self.wbf['total_number'].set_top()
        self.wbf['total_number'].set_bottom()            
        self.wbf['total_number'].set_left()
        self.wbf['total_number'].set_right()
        
        self.wbf['total'] = workbook.add_format({'bold':1,'bg_color': '#FFFFDB','align':'center'})
        self.wbf['total'].set_left()
        self.wbf['total'].set_right()
        self.wbf['total'].set_top()
        self.wbf['total'].set_bottom()
        
        self.wbf['header_detail_space'] = workbook.add_format({})
        self.wbf['header_detail_space'].set_left()
        self.wbf['header_detail_space'].set_right()
        self.wbf['header_detail_space'].set_top()
        self.wbf['header_detail_space'].set_bottom()
                
        self.wbf['header_detail'] = workbook.add_format({'bg_color': '#E0FFC2'})
        self.wbf['header_detail'].set_left()
        self.wbf['header_detail'].set_right()
        self.wbf['header_detail'].set_top()
        self.wbf['header_detail'].set_bottom()
                        
        return workbook

    def excel_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = self.read(cr, uid, ids,context=context)[0]

        return self._print_excel_report(cr, uid, ids, data, context=context)

    def _print_excel_report(self, cr, uid, ids, data, context=None):

        start_date = data['start_date']
        end_date = data['end_date']
        partner_ids = data['partner_ids']
        no_faktur = data['no_faktur']
        ref = data['ref']

        query_where = '';

        if (start_date and end_date) :
            query_where += "AND fp.date BETWEEN '%s' AND '%s'" % (str(start_date), str(end_date))

        if partner_ids :
            query_where += " AND fp.partner_id in %s" % str(
                tuple(partner_ids)).replace(',)', ')')

        if no_faktur :
            query_where += " AND regexp_replace(fp.name, '[^0-9]+', '', 'g') = '%s'" % str(no_faktur)

        if ref : 
            query_where += " AND fp.ref = '%s'" % str(ref) 

        q_header = """
            SELECT fp.id 
                , fp.transaction_id
                , 0 AS SORT_ID
                , 'FK' AS FK
                , '01' AS KD_JENIS_TRANSAKSI
                , '0' AS FG_PENGGANTI
                , regexp_replace(fp.name, '[^0-9]+', '', 'g') AS NOMOR_FAKTUR
                , DATE_PART('month', fp.date) AS MASA_PAJAK
                , DATE_PART('year', fp.date) AS TAHUN_PAJAK
                , TO_CHAR(fp.date, 'DD/MM/YYYY') AS TANGGAL_FAKTUR
                , regexp_replace(COALESCE(rp.npwp, '000000000000000'), '[^0-9]+', '', 'g') AS NPWP 
                , rp.name AS NAMA 
                , regexp_replace(COALESCE(rp.street,''), '\r|\n|\t', ' ', 'g') || regexp_replace(COALESCE(rp.street2,''), '\r|\n|\t', ' ', 'g') || COALESCE(' RT.' || rp.rt,'') || COALESCE(' RW.' || rp.rw,'') || COALESCE(' Kel.' || rp.kelurahan,'') || COALESCE(' Kec.' || rp.kecamatan,'') || COALESCE(' ' || c.name,'') || COALESCE(' ' || cs.name,'') AS ALAMAT_LENGKAP
                , ROUND(fp.untaxed_amount) AS JUMLAH_DPP
                , ROUND(fp.tax_amount)::TEXT AS JUMLAH_PPN
                , 0 AS JUMLAH_PPNBM
                , '' AS ID_KETERANGAN_TAMBAHAN
                , 0 AS FG_UANG_MUKA
                , 0 AS UANG_MUKA_DPP
                , 0 AS UANG_MUKA_PPN
                , 0 UANG_MUKA_PPNBM
                , fp.ref AS REFERENSI
                , rp.pkp as PKP
                , rp.alamat_pkp as ALAMAT_PKP
                , concat(rp.street,' RT/RW ',rp.rt,'/',rp.rw,' Kel. ',rp.kelurahan,' Kec. ',rp.kecamatan)as ALAMAT_PARTNER
                , wb.street as ALAMAAT_BRANCH
                FROM wtc_faktur_pajak_out fp
                LEFT JOIN res_partner rp ON fp.partner_id = rp.id
                LEFT JOIN wtc_city c ON rp.city_id = c.id
                LEFT JOIN res_country_state cs ON rp.state_id = cs.id 
                LEFT JOIN wtc_branch wb on rp.branch_id=wb.id
                WHERE fp.state IN ('print', 'close')
                AND fp.model_id NOT IN (select id FROM ir_model WHERE model = 'wtc.faktur.pajak.other')
                %s
        """ % query_where

        q_sale_order = """
            SELECT fp.id
                , fp.transaction_id
                , sol.id 
                , 'OF'
                , p.name_template AS KODE_OBJEK
                , regexp_replace(pt.description, '\r|\n', ' ', 'g') AS NAMA
                , ROUND(sol.price_unit / 1.1)::TEXT AS HARGA_SATUAN
                , ROUND(sol.product_uos_qty) AS JUMLAH_BARANG
                , ROUND(sol.price_unit / 1.1 * sol.product_uom_qty) AS HARGA_TOTAL
                , ROUND((COALESCE(so.discount_cash,0) + COALESCE(so.discount_lain,0) + COALESCE(so.discount_program,0)) / tent.total_qty * sol.product_uom_qty)::TEXT AS DISKON
                , ROUND((sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty) - (COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty))::TEXT AS DPP
                , ROUND(((sol.price_unit * (1 - COALESCE(sol.discount,0) / 100) / 1.1 * sol.product_uom_qty) - (COALESCE(so.discount_cash,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_lain,0) / tent.total_qty * sol.product_uom_qty) - (COALESCE(so.discount_program,0) / tent.total_qty * sol.product_uom_qty)) * 0.1)::TEXT AS PPN
                , '0' AS TARIF_PPNBM
                , 0 AS PPNBM
                , so.name
                , NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL
                FROM wtc_faktur_pajak_out fp
                INNER JOIN sale_order so ON fp.id = so.faktur_pajak_id --AND fp.model_id IN (SELECT id FROM ir_model WHERE model = 'sale.order')
                INNER JOIN (select tent_so.id, COALESCE(sum(tent_sol.product_uom_qty),0) as total_qty from sale_order tent_so inner join sale_order_line tent_sol on tent_so.id = tent_sol.order_id group by tent_so.id) tent ON so.id = tent.id
                INNER JOIN sale_order_line sol ON so.id = sol.order_id
                LEFT JOIN product_product p ON sol.product_id = p.id
                LEFT JOIN product_template pt ON p.product_tmpl_id = pt.id
                WHERE fp.state IN ('print', 'close')
                %s
        """ % query_where

        q_dealer_sale = """
            SELECT fp.id
                , fp.transaction_id
                , dsol.id 
                , 'OF'
                , p.name_template AS KODE_OBJEK
                , regexp_replace(pt.description, '\r|\n', ' ', 'g') AS NAMA
                , ROUND(dsol.price_unit / 1.1)::TEXT AS HARGA_SATUAN
                , dsol.product_qty AS JUMLAH_BARANG
                , ROUND(dsol.price_unit / 1.1 * dsol.product_qty) AS HARGA_TOTAL
                , ROUND(dsol.discount_total / 1.1)::TEXT AS DISKON
                , ROUND((dsol.price_unit - dsol.discount_total) / 1.1 * dsol.product_qty)::TEXT AS DPP
                , ROUND(((dsol.price_unit - dsol.discount_total) / 1.1 * dsol.product_qty) / 10)::TEXT AS PPN
                , '0' AS TARIF_PPNBM
                , 0 AS PPNBM
                , NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL
                FROM wtc_faktur_pajak_out fp
                INNER JOIN dealer_sale_order dso ON fp.id = dso.faktur_pajak_id AND fp.model_id IN (SELECT id FROM ir_model WHERE model = 'dealer.sale.order')
                INNER JOIN dealer_sale_order_line dsol ON dso.id = dsol.dealer_sale_order_line_id
                LEFT JOIN product_product p ON dsol.product_id = p.id
                LEFT JOIN product_template pt ON p.product_tmpl_id = pt.id
                WHERE fp.state IN ('print', 'close')
                %s
        """ % query_where

        q_work_order = """
            SELECT fp.id
                , fp.transaction_id
                , wol.id 
                , 'OF'
                , p.name_template AS KODE_OBJEK
                , CASE WHEN wol.categ_id = 'Sparepart' THEN p.default_code ELSE regexp_replace(pt.description, '\r|\n', ' ', 'g') END AS NAMA
                , ROUND(wol.price_unit / 1.1)::TEXT AS HARGA_SATUAN
                , CASE WHEN wol.categ_id = 'Sparepart' THEN wol.supply_qty ELSE wol.product_qty END AS JUMLAH_BARANG
                , ROUND(wol.price_unit / 1.1 * CASE WHEN wol.categ_id = 'Sparepart' THEN wol.supply_qty ELSE wol.product_qty END) AS HARGA_TOTAL
                , ROUND(wol.price_unit / 1.1 * CASE WHEN wol.categ_id = 'Sparepart' THEN wol.supply_qty ELSE wol.product_qty END * COALESCE(wol.discount,0) / 100)::TEXT AS DISKON
                , ROUND(wol.price_unit / 1.1 * CASE WHEN wol.categ_id = 'Sparepart' THEN wol.supply_qty ELSE wol.product_qty END * (1 - COALESCE(wol.discount,0) / 100))::TEXT AS DPP
                , ROUND(wol.price_unit / 1.1 * CASE WHEN wol.categ_id = 'Sparepart' THEN wol.supply_qty ELSE wol.product_qty END * (1 - COALESCE(wol.discount,0) / 100) / 10)::TEXT AS PPN
                , '0' AS TARIF_PPNBM
                , 0 AS PPNBM
                , NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL
                FROM wtc_faktur_pajak_out fp
                INNER JOIN wtc_work_order wo ON fp.id = wo.faktur_pajak_id AND fp.model_id IN (SELECT id FROM ir_model WHERE model = 'wtc.work.order')
                INNER JOIN wtc_work_order_line wol ON wo.id = wol.work_order_id
                LEFT JOIN product_product p ON wol.product_id = p.id
                LEFT JOIN product_template pt ON p.product_tmpl_id = pt.id
                WHERE fp.state IN ('print', 'close')
                %s
        """ % query_where

        q_other_rec = """
            SELECT fp.id
                , fp.transaction_id
                , dn.id 
                , 'OF'
                , '' AS KODE_OBJEK
                , COALESCE(dn.name,'') AS NAMA
                , ROUND(fp.untaxed_amount)::TEXT AS HARGA_SATUAN
                , 1 AS JUMLAH_BARANG
                , fp.untaxed_amount AS HARGA_TOTAL
                , '0' AS DISKON
                , ROUND(fp.untaxed_amount)::TEXT AS DPP
                , ROUND(fp.tax_amount)::TEXT AS PPN
                , '0' AS TARIF_PPNBM
                , 0 AS PPNBM
                , NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL
                FROM wtc_faktur_pajak_out fp
                INNER JOIN wtc_dn_nc dn ON fp.id = dn.faktur_pajak_id AND fp.model_id IN (SELECT id FROM ir_model WHERE model = 'wtc.dn.nc')
                WHERE fp.state IN ('print', 'close')
                %s
        """ % query_where

        q_fp_other = """
            SELECT fp.id
                , fp.transaction_id
                , fpo.id 
                , 'OF'
                , '' AS KODE_OBJEK
                , COALESCE(fpo.memo,'') AS NAMA
                , ROUND(fpo.untaxed_amount)::TEXT AS HARGA_SATUAN
                , 1 AS JUMLAH_BARANG
                , ROUND(fpo.untaxed_amount) AS HARGA_TOTAL
                , '0' AS DISKON
                , ROUND(fpo.untaxed_amount)::TEXT AS DPP
                , ROUND(fpo.tax_amount)::TEXT AS PPN
                , '0' AS TARIF_PPNBM
                , 0 AS PPNBM
                , NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL
                FROM wtc_faktur_pajak_out fp
                INNER JOIN wtc_faktur_pajak_other fpo ON fp.transaction_id = fpo.id AND fp.model_id IN (SELECT id FROM ir_model WHERE model = 'wtc.faktur.pajak.other')
                WHERE fp.state IN ('print', 'close')
                AND fpo.pajak_gabungan = TRUE
                %s
        """ % query_where

        q_fp_disposal = """
            SELECT fp.id
                , fp.transaction_id
                , da.id
                , 'OF'
                , '' AS KODE_OBJEK
                , COALESCE(da.name,'') AS NAMA
                , ROUND(da.amount_untaxed)::TEXT AS HARGA_SATUAN
                , 1 AS JUMLAH_BARANG
                , ROUND(da.amount_untaxed) AS HARGA_TOTAL
                , '0' AS DISKON
                , ROUND(da.amount_untaxed)::TEXT AS DPP
                , ROUND(da.amount_tax)::TEXT AS PPN
                , '0' AS TARIF_PPNBM
                , 0 AS PPNBM
                , NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL
                
                FROM wtc_faktur_pajak_out fp
                INNER JOIN wtc_disposal_asset da ON fp.id = da.faktur_pajak_id AND fp.model_id IN (SELECT id FROM ir_model WHERE model = 'wtc.disposal.asset')
                WHERE fp.state IN ('print', 'close')
                %s
        """ % query_where

        query = """
            SELECT * FROM (
                (
                    --HEADER--
                    %s
                ) UNION (
                    --SALE ORDER--
                    %s
                ) UNION (
                    --DEALER SALE ORDER--
                    %s
                ) UNION (
                    --WORK ORDER--
                    %s
                ) UNION (
                    --OTHER RECEIVABLE--
                    %s
                ) UNION (
                    --FP OTHER--
                    %s
                ) UNION (
                    --FP DISPOSAL ASSET--
                    %s
                )
            ) a 
            ORDER BY id, transaction_id, sort_id
            
        """ % (q_header,q_sale_order,q_dealer_sale,q_work_order,q_other_rec,q_fp_other,q_fp_disposal)

        cr.execute (query)
        ress = cr.fetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('eFaktur Pajak')
        worksheet.set_column('B1:B1', 20)
        worksheet.set_column('C1:C1', 20)
        worksheet.set_column('D1:D1', 20)
        worksheet.set_column('E1:E1', 20)
        worksheet.set_column('F1:F1', 20)
        worksheet.set_column('G1:G1', 20)
        worksheet.set_column('H1:H1', 20)
        worksheet.set_column('I1:I1', 20)
        worksheet.set_column('J1:J1', 20)
        worksheet.set_column('K1:K1', 20)
        worksheet.set_column('L1:L1', 20)
        worksheet.set_column('M1:M1', 20)
        worksheet.set_column('N1:N1', 20)
        worksheet.set_column('O1:O1', 20)
        worksheet.set_column('P1:P1', 20)
        worksheet.set_column('Q1:Q1', 20)
        worksheet.set_column('R1:R1', 20)
        worksheet.set_column('S1:S1', 20)
        worksheet.set_column('T1:T1', 20)

        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name

        filename = 'eFaktur Pajak '+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        
        if (start_date and end_date) :
            worksheet.write('A2', 'eFaktur Pajak Periode '+start_date+' - '+end_date , wbf['title_doc'])
        else :
            worksheet.write('A2', 'eFaktur Pajak', wbf['title_doc'])

        row=3
        rowsaldo = row
        row+=1
        #worksheet.write('A%s' % (row+1), 'No' , wbf['header'])
        worksheet.merge_range('A%s:A%s' % (row+1 , row+3), 'No', wbf['header_merged'])
        worksheet.write('B%s' % (row+1), 'FK' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'Kode Jenis Transaksi' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'FG Pengganti' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'Nomor Faktur' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'Masa Pajak' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'Tahun Pajak' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'Tanggal Faktur' , wbf['header'])
        worksheet.write('I%s' % (row+1), 'NPWP' , wbf['header'])
        worksheet.write('J%s' % (row+1), 'Nama' , wbf['header'])
        worksheet.write('K%s' % (row+1), 'Alamat Lengkap' , wbf['header'])
        worksheet.write('L%s' % (row+1), 'Jumlah DDP' , wbf['header'])
        worksheet.write('M%s' % (row+1), 'Jumlah PPN' , wbf['header'])
        worksheet.write('N%s' % (row+1), 'Jumlah PPNBM' , wbf['header'])
        worksheet.write('O%s' % (row+1), 'ID Keterangan Tambahan' , wbf['header'])
        worksheet.write('P%s' % (row+1), 'FG Uang Muka' , wbf['header'])
        worksheet.write('Q%s' % (row+1), 'Uang Muka DDP' , wbf['header'])
        worksheet.write('R%s' % (row+1), 'Uang Muka PPN' , wbf['header'])
        worksheet.write('S%s' % (row+1), 'Uang Muka PPNBM' , wbf['header'])
        worksheet.write('T%s' % (row+1), 'Refrensi' , wbf['header'])
        row+=1
        #worksheet.write('A%s' % (row+1), ' ' , wbf['header'])
        worksheet.write('B%s' % (row+1), 'LT' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'NPWP' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'Nama' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'Jalan' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'Blok' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'Nomor' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'RT' , wbf['header'])
        worksheet.write('I%s' % (row+1), 'RW' , wbf['header'])
        worksheet.write('J%s' % (row+1), 'Kecamatan' , wbf['header'])
        worksheet.write('K%s' % (row+1), 'Kelurahan' , wbf['header'])
        worksheet.write('L%s' % (row+1), 'Kabupaten' , wbf['header'])
        worksheet.write('M%s' % (row+1), 'Propinsi' , wbf['header'])
        worksheet.write('N%s' % (row+1), 'Kode Pos' , wbf['header'])
        worksheet.write('O%s' % (row+1), 'No. Telepon' , wbf['header'])
        worksheet.write('P%s' % (row+1), ' ' , wbf['header'])
        worksheet.write('Q%s' % (row+1), ' ' , wbf['header'])
        worksheet.write('R%s' % (row+1), ' ' , wbf['header'])
        worksheet.write('S%s' % (row+1), ' ' , wbf['header'])
        worksheet.write('T%s' % (row+1), ' ' , wbf['header'])
        row+=1
        #worksheet.write('A%s' % (row+1), ' ' , wbf['header'])
        worksheet.write('B%s' % (row+1), 'OF' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'Kode Objek' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'Nama' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'Harga Satuan' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'Jumlah Barang' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'Harga Total' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'Diskon' , wbf['header'])
        worksheet.write('I%s' % (row+1), 'DPP' , wbf['header'])
        worksheet.write('J%s' % (row+1), 'PPN' , wbf['header'])
        worksheet.write('K%s' % (row+1), 'Tarif PPNBM' , wbf['header'])
        worksheet.write('L%s' % (row+1), 'PPNBM' , wbf['header'])
        worksheet.write('M%s' % (row+1), ' ' , wbf['header'])
        worksheet.write('N%s' % (row+1), ' ' , wbf['header'])
        worksheet.write('O%s' % (row+1), ' ' , wbf['header'])
        worksheet.write('P%s' % (row+1), ' ' , wbf['header'])
        worksheet.write('Q%s' % (row+1), ' ' , wbf['header'])
        worksheet.write('R%s' % (row+1), ' ' , wbf['header'])
        worksheet.write('S%s' % (row+1), ' ' , wbf['header'])
        worksheet.write('T%s' % (row+1), ' ' , wbf['header'])

        row+=2
                
        no = 1     
        row1 = row
        
        total_dpp = 0
        total_ppn = 0
        header_dpp = 0
        header_ppn = 0
        header_row = 0

        for res in ress:
            fk = res[3]
            kd_jenis_trans = res[4]
            fg_pengganti = res[5]
            no_faktur = res[6]
            masa_pajak = res[7]
            thn_pajak = res[8]
            tgl_faktur = res[9]
            npwp = res[10]
            nama = res[11]
            if res[22] == True and not res[23]:
                alamat = res[23]
            elif res[22] == True and res[23]:
                alamat = res[24]
            elif res[22] == False:
                alamat = res[25]
            else:
                alamat = res[12]
            jml_ddp = res[13]
            jml_ppn = res[14]
            jml_ppnbm = res[15]
            id_ket_tambahan = res[16]
            fg_uang_muka = res[17]
            uang_muka_ddp = res[18]
            uang_muka_ppn = res[19]
            uang_muka_ppnbm = res[20]
            refrensi = res[21]
            pkp = res[22]
            alamat_pkp = res[23]
            alamat_res =res[24]
            alamat_branch = res[25]
            
            # Cross check total detil dpp dengan header dpp. Jika ada perbedaan (pembulatan) maka header dpp akan di replace dengan total dari detil.
            # Begitu juga untuk ppn.            
            if fk == 'FK' :
                if header_dpp != total_dpp :
                    worksheet.write('L%s' % header_row, total_dpp, wbf['content_number'])
                if header_ppn != total_ppn :
                    worksheet.write('M%s' % header_row, total_ppn, wbf['content_number'])
                header_row = row
                header_dpp = jml_ddp
                header_ppn = jml_ppn
                total_dpp = 0
                total_ppn = 0
            else :
                tgl_faktur = int(thn_pajak) - int(npwp)
                total_dpp += int(npwp)
                total_ppn += int(nama)

            worksheet.write('A%s' % row, no , wbf['content_number'])
            worksheet.write('B%s' % row, fk , wbf['content'])                    
            worksheet.write('C%s' % row, kd_jenis_trans , wbf['content'])
            worksheet.write('D%s' % row, fg_pengganti , wbf['content'])
            worksheet.write('F%s' % row, masa_pajak , wbf['content_number'])
            worksheet.write('G%s' % row, thn_pajak , wbf['content_number'])
            if fk == 'FK' :
                worksheet.write('E%s' % row, no_faktur , wbf['content'])
                worksheet.write('H%s' % row, tgl_faktur , wbf['content_date'])
                worksheet.write('I%s' % row, npwp , wbf['content']) 
                worksheet.write('J%s' % row, nama , wbf['content'])  
                worksheet.write('K%s' % row, alamat , wbf['content'])
                worksheet.write('M%s' % row, jml_ppn , wbf['content_number'])
            else :
                worksheet.write('E%s' % row, no_faktur , wbf['content_number']) #harga satuan
                worksheet.write('H%s' % row, tgl_faktur , wbf['content_number']) #diskon
                worksheet.write('I%s' % row, npwp , wbf['content_number']) #dpp
                worksheet.write('J%s' % row, nama , wbf['content_number']) #ppn
                worksheet.write('K%s' % row, alamat , wbf['content_number']) #tarif ppnbm
                worksheet.write('M%s' % row, jml_ppn , wbf['content']) #detil referensi
            worksheet.write('L%s' % row, jml_ddp , wbf['content_number'])  
            worksheet.write('N%s' % row, jml_ppnbm , wbf['content_number'])
            worksheet.write('O%s' % row, id_ket_tambahan , wbf['content'])
            worksheet.write('P%s' % row, fg_uang_muka , wbf['content'])
            worksheet.write('Q%s' % row, uang_muka_ddp , wbf['content_number'])
            worksheet.write('R%s' % row, uang_muka_ppn , wbf['content_number'])
            worksheet.write('S%s' % row, uang_muka_ppnbm , wbf['content_number'])
            worksheet.write('T%s' % row, refrensi , wbf['content'])
                                  
            no+=1
            row+=1

        # Cross check total DPP & PPN untuk row terakhir.
        if header_dpp != total_dpp :
            worksheet.write('L%s' % header_row, total_dpp, wbf['content_number'])
        if header_ppn != total_ppn :
            worksheet.write('M%s' % header_row, total_ppn, wbf['content_number'])

        worksheet.autofilter('A7:T%s' % (row))  
        worksheet.freeze_panes(7, 3)

        worksheet.write('A%s'%(row+2), '%s %s' % (str(date),user) , wbf['footer'])  
                   
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_efaktur', 'view_e_faktur_wizard')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.e.faktur.pajak.wizard',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }

wtc_e_faktur_pajak()