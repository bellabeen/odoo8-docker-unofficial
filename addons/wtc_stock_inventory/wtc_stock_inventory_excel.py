from openerp.osv import fields, osv
from datetime import datetime
import time
import cStringIO
import xlsxwriter
from cStringIO import StringIO
import pytz
import base64
import tempfile
import os

class wtc_stock_inventory_excel(osv.osv):
    _inherit = 'stock.inventory'

    wbf = {}

    def action_export(self,cr,uid,ids,context=None):
        if context is None:
            context = {}
        data = self.browse(cr,uid,ids)
        return self._print_excel_report(cr, uid, ids, data, context=context)
    

    def add_workbook_format(self, cr, uid, workbook):      
        self.wbf['header'] = workbook.add_format({'bold': 1,'align': 'center','bg_color': '#FFFFDB','font_color': '#000000'})
        self.wbf['header'].set_border()

        self.wbf['header_no'] = workbook.add_format({'bold': 1,'align': 'center','bg_color': '#FFFFDB','font_color': '#000000'})
        self.wbf['header_no'].set_border()
        self.wbf['header_no'].set_align('vcenter')
                
        self.wbf['footer'] = workbook.add_format({'align':'left'})
        
        self.wbf['content_datetime'] = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss'})
        self.wbf['content_datetime'].set_left()
        self.wbf['content_datetime'].set_right()
                
        self.wbf['content_date'] = workbook.add_format({'num_format': 'yyyy-mm-dd'})
        self.wbf['content_date'].set_left()
        self.wbf['content_date'].set_right() 
        
        self.wbf['title_doc'] = workbook.add_format({'bold': 1,'align': 'left'})
        self.wbf['title_doc'].set_font_size(12)

        self.wbf['title_datetime'] = workbook.add_format({'bold': 1,'align': 'left', 'num_format': 'yyyy-mm-dd hh:mm:ss'})
        self.wbf['title_datetime'].set_font_size(12)
        
        self.wbf['company'] = workbook.add_format({'align': 'left'})
        self.wbf['company'].set_font_size(11)
        
        self.wbf['content'] = workbook.add_format()
        self.wbf['content'].set_left()
        self.wbf['content'].set_right() 
        
        self.wbf['sign'] = workbook.add_format({'bold': 1,'align': 'center'})
        
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
        
        return workbook

    def _print_excel_report(self, cr, uid, ids, data, context=None):

        if data.division == 'Unit':
            query = """
                SELECT lot.name AS engine_no
                , lot.chassis_no
                , sil.product_name || ' (' || COALESCE(pav.name,'') || ')' AS kode_barang
                , pt.description AS deskripsi
                , q.cost AS cost
                , sil.theoretical_qty AS qty
                , sil.id AS sil_id
                FROM stock_inventory_line sil
                left join stock_production_lot lot on sil.prod_lot_id = lot.id
                LEFT JOIN product_product prod ON prod.id = sil.product_id  
                LEFT JOIN product_template pt ON pt.id = prod.product_tmpl_id  
                LEFT JOIN product_attribute_value_product_product_rel pavpp ON pavpp.prod_id = sil.product_id  
                LEFT JOIN product_attribute_value pav ON pav.id = pavpp.att_id  

                LEFT JOIN stock_quant q on q.lot_id = sil.prod_lot_id

                WHERE inventory_id = %s
            """ % (data.id)
        else :
            query = """
                SELECT sil.product_name AS engine_no
                , '' as chassis_no
                , sil.product_name AS kode_barang
                , sil.product_code AS deskripsi
                , pphbc.cost AS cost
                , sil.theoretical_qty AS qty
                , sil.id as sil_id
                FROM stock_inventory_line sil
                INNER JOIN stock_inventory si ON sil.inventory_id = si.id
                LEFT JOIN stock_location loc ON loc.id = si.location_id
                LEFT JOIN (
                    SELECT warehouse_id
                    , product_id
                    , max(datetime) AS datetime
                    , max(id) AS id
                    FROM product_price_history_branch
                    WHERE datetime <= '%s'
                    GROUP BY warehouse_id, product_id
                    ORDER BY datetime DESC
                ) pphb ON pphb.warehouse_id = loc.warehouse_id AND pphb.product_id = sil.product_id
                LEFT JOIN product_price_history_branch pphbc ON pphbc.id = pphb.id
                WHERE inventory_id = %s
                ORDER BY engine_no
            """ % (data.date, data.id)
                            
        cr.execute (query)
        ress = cr.fetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)
        
        user = self.pool.get('res.users').browse(cr, uid, uid)
        tz = pytz.timezone(user.tz) if user.tz else pytz.utc
        date_tz = pytz.utc.localize(datetime.now()).astimezone(tz)
        date = date_tz.strftime("%Y-%m-%d %H:%M:%S")
        date= datetime.strptime(date, '%Y-%m-%d %H:%M:%S')        
        filename = 'Inventory Adjustment '+str(date)+'.xlsx'
        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        worksheet = workbook.add_worksheet('IA')
        worksheet.set_column('B1:B1', 20)
        worksheet.set_column('C1:C1', 20)
        worksheet.set_column('D1:D1', 20)
        worksheet.set_column('E1:E1', 40)
        worksheet.set_column('F1:F1', 20)
        worksheet.set_column('G1:G1', 15)
        worksheet.set_column('H1:H1', 25)
        worksheet.set_column('I1:I1', 15)
        worksheet.set_column('J1:J1', 25)
        worksheet.set_column('K1:K1', 15)
        worksheet.set_column('L1:L1', 25)
        worksheet.set_column('M1:M1', 15)
        worksheet.set_column('N1:N1', 25)
        worksheet.set_column('O1:O1', 15)
        worksheet.set_column('P1:P1', 25)
        worksheet.set_column('Q1:Q1', 20)
        
        company_name = self.pool.get('res.users').browse(cr, uid, uid).company_id.name
        worksheet.write('C1', company_name, wbf['company'])
        worksheet.write('C2', 'Inventory Adjustment', wbf['title_doc'])
        worksheet.write('C3', 'Lokasi', wbf['title_doc'])
        worksheet.write('D3', data.location_id.branch_id.name, wbf['title_doc'])
        worksheet.write('C4', 'Nomor Sistem', wbf['title_doc'])
        worksheet.write('D4', data.name, wbf['title_doc'])
        worksheet.write('C5', 'Divisi', wbf['title_doc'])
        worksheet.write('D5', data.division, wbf['title_doc'])
        worksheet.write('C6', 'Tanggal Start SO', wbf['title_doc'])
        worksheet.write('D6', data.date, wbf['title_datetime'])
        
        row=8
        rowsaldo = 6
        row+=1
        worksheet.merge_range('A%s:A%s' % (row, (row+1)), 'ID', wbf['header'])
        if data.division=='Unit':
            worksheet.merge_range('B%s:B%s' % (row,(row+1)), 'Nomor Mesin' , wbf['header'])
            worksheet.merge_range('C%s:C%s' % (row,(row+1)), 'Nomor Rangka' , wbf['header'])
        else:
            worksheet.merge_range('B%s:B%s' % (row,(row+1)), 'Kode Barang' , wbf['header'])
            worksheet.merge_range('C%s:C%s' % (row,(row+1)), '' , wbf['header'])
        worksheet.merge_range('D%s:D%s' % (row,(row+1)), 'Kode Barang' , wbf['header'])
        worksheet.merge_range('E%s:E%s' % (row,(row+1)), 'Nama Barang' , wbf['header'])
        worksheet.merge_range('F%s:F%s' % (row,(row+1)), 'Satuan' , wbf['header'])
        worksheet.merge_range('G%s:G%s' % (row,(row+1)), 'Jumlah' , wbf['header'])
        worksheet.merge_range('H%s:H%s' % (row,(row+1)), 'Total Harga' , wbf['header'])
        worksheet.merge_range('I%s:J%s' % (row,row), 'Fisik Baik' , wbf['header'])
        worksheet.write('I%s' % (row+1), 'Jumlah' , wbf['header'])
        worksheet.write('J%s' % (row+1), 'Total Harga' , wbf['header'])
        worksheet.merge_range('K%s:L%s' % (row,row), 'Fisik Rusak' , wbf['header'])
        worksheet.write('K%s' % (row+1), 'Jumlah' , wbf['header'])
        worksheet.write('L%s' % (row+1), 'Total Harga' , wbf['header'])
        worksheet.merge_range('M%s:N%s' % (row,row), 'Total Fisik' , wbf['header'])
        worksheet.write('M%s' % (row+1), 'Jumlah' , wbf['header'])
        worksheet.write('N%s' % (row+1), 'Total Harga' , wbf['header'])
        worksheet.merge_range('O%s:P%s' % (row,row), 'Selisih' , wbf['header'])
        worksheet.write('O%s' % (row+1), 'Jumlah' , wbf['header'])
        worksheet.write('P%s' % (row+1), 'Total Harga' , wbf['header'])
        worksheet.merge_range('Q%s:Q%s' % (row,(row+1)), 'Keterangan' , wbf['header'])
             
        row+=2
        firstrow = row

        for res in ress:
            engine_no = str(res[0].encode('ascii','ignore').decode('ascii')) if res[0] != None else ''
            chassis_no = str(res[1].encode('ascii','ignore').decode('ascii')) if res[1] != None else ''
            kode_barang = str(res[2].encode('ascii','ignore').decode('ascii')) if res[2] != None else ''
            deskripsi = str(res[3].encode('ascii','ignore').decode('ascii')) if res[3] != None else ''
            cost = res[4] if res[4] != None else 0
            qty = res[5] if res[5] != None else 0
            sil_id = res[6] if res[6] != None else 0

            worksheet.write_number('A%s' % (row), sil_id, wbf['content_number'])
            worksheet.write_string('B%s' % (row), engine_no , wbf['content'])
            worksheet.write_string('C%s' % (row), chassis_no , wbf['content'])
            worksheet.write_string('D%s' % (row), kode_barang , wbf['content'])
            worksheet.write_string('E%s' % (row), deskripsi, wbf['content'])
            worksheet.write_number('F%s' % (row), cost, wbf['content_float'])
            worksheet.write_number('G%s' % (row), qty, wbf['content_float'])
            worksheet.write_formula('H%s' % (row), '=F%s*G%s' % (row, row), wbf['content_float'])

            worksheet.write_formula('J%s' % (row), '=F%s*I%s' % (row, row), wbf['content_float'])

            worksheet.write_formula('L%s' % (row), '=F%s*K%s' % (row, row), wbf['content_float'])
            worksheet.write_formula('M%s' % (row), '=I%s+K%s' % (row, row), wbf['content_float'])
            worksheet.write_formula('N%s' % (row), '=F%s*M%s' % (row, row), wbf['content_float'])
            worksheet.write_formula('O%s' % (row), '=G%s-M%s' % (row, row), wbf['content_float'])
            worksheet.write_formula('P%s' % (row), '=H%s-N%s' % (row, row), wbf['content_float'])
            worksheet.write_formula('Q%s' % (row), '=IF(O%s=0,"",IF(O%s>0,"Sel Kurang",IF(O%s<0,"Sel Lebih","")))' % (row, row, row), wbf['content'])

            row+=1

        #TOTAL ON TOP AREA
        worksheet.write_formula('F%s' % (rowsaldo), '=SUM(F%s:F%s)' % (firstrow, row), wbf['total_number'])
        worksheet.write_formula('G%s' % (rowsaldo), '=SUM(G%s:G%s)' % (firstrow, row), wbf['total_float'])
        worksheet.write_formula('H%s' % (rowsaldo), '=SUM(H%s:H%s)' % (firstrow, row), wbf['total_number'])
        worksheet.write_formula('I%s' % (rowsaldo), '=SUM(I%s:I%s)' % (firstrow, row), wbf['total_float'])
        worksheet.write_formula('J%s' % (rowsaldo), '=SUM(J%s:J%s)' % (firstrow, row), wbf['total_number'])
        worksheet.write_formula('K%s' % (rowsaldo), '=SUM(K%s:K%s)' % (firstrow, row), wbf['total_float'])
        worksheet.write_formula('L%s' % (rowsaldo), '=SUM(L%s:L%s)' % (firstrow, row), wbf['total_number'])
        worksheet.write_formula('M%s' % (rowsaldo), '=SUM(M%s:M%s)' % (firstrow, row), wbf['total_float'])
        worksheet.write_formula('N%s' % (rowsaldo), '=SUM(N%s:N%s)' % (firstrow, row), wbf['total_number'])
        worksheet.write_formula('O%s' % (rowsaldo), '=SUM(O%s:O%s)' % (firstrow, row), wbf['total_float'])
       
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'data_x':out}, context=context)
        fp.close()

        return True
