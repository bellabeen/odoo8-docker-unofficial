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

class report_stnk_bpkb(osv.osv_memory):
   
    _name = "report.stnk.bpkb"
    _description = "Report STNK BPKB"

    wbf = {}

    def _get_default(self,cr,uid,date=False,user=False,context=None):
        if date :
            return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)
        else :
            return self.pool.get('res.users').browse(cr, uid, uid)
        
    def _get_branch_ids(self, cr, uid, context=None):
        branch_ids_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
        branch_ids = [b.id for b in branch_ids_user]
        return branch_ids
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(report_stnk_bpkb, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        categ_ids = self.pool.get('product.category').get_child_ids(cr,uid,view_id,'Unit')
        branch_ids_user=self.pool.get('res.users').browse(cr,uid,uid).branch_ids
        branch_ids=[b.id for b in branch_ids_user]
        
        doc = etree.XML(res['arch'])
        nodes_stnk_loc = doc.xpath("//field[@name='loc_stnk_ids']")
        nodes_bpkb_loc = doc.xpath("//field[@name='loc_bpkb_ids']")       
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
        for node in nodes_stnk_loc:
            node.set('domain', '[("branch_id", "=", '+ str(branch_ids)+')]')
        for node in nodes_branch:
            node.set('domain', '[("id", "=", '+ str(branch_ids)+')]')
        for node in nodes_bpkb_loc:
            node.set('domain', '[("branch_id", "=", '+ str(branch_ids)+')]')
        res['arch'] = etree.tostring(doc)
        return res
        
    _columns = {
        'state_x': fields.selection( ( ('choose','choose'),('get','get'))), #xls
        'data_x': fields.binary('File', readonly=True),
        'name': fields.char('Filename', 100, readonly=True),
        'option' : fields.selection([('track','Track STNK BPKB'),('lead_time','Lead Time STNK BPKB'),('stock_stnk','Stock STNK'),('stock_bpkb','Stock BPKB')],string='Option'),
        'branch_ids': fields.many2many('wtc.branch', 'report_stnk_bpkb_rel', 'report_stnk_bpkb_wizard_id','branch_id', 'Branch', copy=False),
        'lot_ids': fields.many2many('stock.production.lot', 'report_lot_rel', 'report_stnk_bpkb_wizard_id','lot_id', 'Engine No', copy=False, ),
        'loc_stnk_ids': fields.many2many('wtc.lokasi.stnk', 'report_lokasi_stnk_rel', 'report_stnk_bpkb_wizard_id','stnk_id', 'Lokasi STNK', copy=False),
        'loc_bpkb_ids': fields.many2many('wtc.lokasi.bpkb', 'report_lokasi_bpkb_rel', 'report_stnk_bpkb_wizard_id','bpkb_id', 'Lokasi BPKB', copy=False),\
        'partner_ids': fields.many2many('res.partner', 'report_partner_rel', 'report_stnk_bpkb_wizard_id','partner_id', 'Customer', copy=False,domain="[('customer','!=',False)]"),
        'birojasa_ids': fields.many2many('res.partner', 'report_birojasa_rel', 'report_stnk_bpkb_wizard_id','partner_id', 'Biro Jasa', copy=False,domain="[('biro_jasa','!=',False)]"),
        'finco_ids': fields.many2many('res.partner', 'report_finco_rel', 'report_stnk_bpkb_wizard_id','partner_id', 'Finco', copy=False,domain="[('finance_company','!=',False)]"),     
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'status_lead_time': fields.selection([('all','All'),('complete','Complete'),('outstanding','Outstanding')],string="Status")
    
    }

    _defaults = {
        'state_x': lambda *a: 'choose',
        'options':'track',  
    }
    
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
        if len(data['branch_ids']) == 0 :
            data.update({'branch_ids': self._get_branch_ids(cr, uid, context)})
        if data['option'] == 'track' : 
            return self._print_excel_report_track(cr, uid, ids, data, context=context)
        elif data['option'] == 'lead_time' :
            return self._print_excel_report_lead_time(cr, uid, ids, data, context=context)
        elif data['option'] == 'stock_stnk' :
            return self._print_excel_report_stock_stnk(cr, uid, ids, data, context=context)
        elif data['option'] == 'stock_bpkb' :
            return self._print_excel_report_stock_bpkb(cr, uid, ids, data, context=context)
    
    def _print_excel_report_track(self, cr, uid, ids, data, context=None):
        
        branch_ids = data['branch_ids']
        partner_ids = data['partner_ids']
        loc_stnk_ids = data['loc_stnk_ids']
        loc_bpkb_ids = data['loc_bpkb_ids']
        lot_ids = data['lot_ids']
        birojasa_ids = data['birojasa_ids']
        finco_ids = data['finco_ids']
        start_date = data['start_date']
        end_date = data['end_date']

        query = """
            select  
            b.name as nama_branch,  
            c.name as lokasi_stnk , 
            d.name as lokasi_bpkb,  
            e.default_code as code_nama_customer,  
            e.name as nama_customer,  
            a.name as engine_no,  
            a.chassis_no as chassis_no,
            f.name as location_name,  
            g.name as supplier_name,  
            h.default_code as code_stnk_name,  
            h.name as stnk_name,  
            a.state as state,  
            i.name as finco_name,  
            j.name as birojasa_name,  
            k.name as sale_order,  
            a.invoice_date as tgl_sale_order,  
            z.name as purchase_order,  
            a.po_date as tgl_purchase_order,  
            l.name as no_permohonan_faktur,  
            a.tgl_faktur as tgl_faktur,  
            m.name as no_penerimaan_faktur,  
            a.tgl_terima as tgl_terima,  
            a.faktur_stnk as no_faktur,  
            a.tgl_cetak_faktur as tgl_cetak_faktur,  
            n.name as no_proses_stnk,  
            a.tgl_proses_stnk as tgl_proses_stnk,  
            o.name as no_proses_birojasa,  
            a.tgl_proses_birojasa as tgl_proses_birojasa,  
            p.name as no_penyerahan_faktur,  
            a.tgl_penyerahan_faktur as tgl_penyerahan_faktur, 
            q.name as no_penerimaan_stnk,   
            r.name as no_penerimaan_notice,  
            s.name as no_penerimaan_no_polisi,  
            t.name as no_penerimaan_bpkb,  
            a.no_notice as no_notice,  
            a.no_bpkb as no_bpkb,   
            a.no_polisi as no_polisi,                         
            a.no_stnk as no_stnk,  
            a.tgl_notice as tgl_notice,  
            a.tgl_stnk as tgl_stnk,  
            a.tgl_bpkb as tgl_bpkb,  
            a.no_urut_bpkb as no_urut_bpkb,  
            a.tgl_terima_stnk as tgl_terima_stnk,  
            a.tgl_terima_bpkb as tgl_terima_bpkb,              
            a.tgl_terima_notice as tgl_terima_notice,  
            a.tgl_terima_no_polisi as tgl_terima_no_polisi,  
            u.name as no_penyerahan_stnk,  
            w.name as no_penyerahan_notice,  
            x.name as no_penyerahan_polisi, 
            v.name as no_penyerahan_bpkb,               
            a.tgl_penyerahan_stnk as tgl_penyerahan_stnk,  
            a.tgl_penyerahan_notice as tgl_penyerahan_notice,  
            a.tgl_penyerahan_plat as tgl_penyerahan_plat,  
            a.tgl_penyerahan_bpkb as tgl_penyerahan_bpkb,  
            y.name as no_pengurusan_stnk_bpkb,  
            a.tgl_pengurusan_stnk_bpkb as tgl_pengurusan_stnk_bpkb,
            invoice.number as invoice_bbn,
            pt.description as desc_type,
		    pp.name_template as kode_type

            From stock_production_lot a 
            LEFT JOIN account_invoice invoice ON invoice.id = a.invoice_bbn
            LEFT JOIN wtc_branch b ON b.id = a.branch_id 
            LEFT JOIN wtc_lokasi_stnk c ON c.id = a.lokasi_stnk_id 
            LEFT JOIN wtc_lokasi_bpkb d ON d.id = a.lokasi_bpkb_id 
            LEFT JOIN res_partner e ON e.id = a.customer_id 
            LEFT JOIN stock_location f ON f.id = a.location_id 
            LEFT JOIN res_partner g ON g.id = a.supplier_id 
            LEFT JOIN res_partner h ON h.id = a.customer_stnk 
            LEFT JOIN res_partner i ON i.id = a.finco_id 
            LEFT JOIN res_partner j ON j.id = a.biro_jasa_id 
            LEFT JOIN dealer_sale_order k ON k.id = a.dealer_sale_order_id 
            LEFT JOIN wtc_permohonan_faktur l ON l.id = a.permohonan_faktur_id 
            LEFT JOIN wtc_penerimaan_faktur m ON m.id = a.penerimaan_faktur_id 
            LEFT JOIN wtc_proses_stnk n ON n.id = a.proses_stnk_id 
            LEFT JOIN wtc_proses_birojasa o ON o.id = a.proses_biro_jasa_id 
            LEFT JOIN wtc_penyerahan_faktur p ON p.id = a.penyerahan_faktur_id 
            LEFT JOIN wtc_penerimaan_stnk q ON q.id = a.penerimaan_stnk_id 
            LEFT JOIN wtc_penerimaan_stnk r ON r.id = a.penerimaan_notice_id 
            LEFT JOIN wtc_penerimaan_stnk s ON s.id = a.penerimaan_no_polisi_id 
            LEFT JOIN wtc_penerimaan_bpkb t ON t.id = a.penerimaan_bpkb_id 
            LEFT JOIN wtc_penyerahan_stnk u ON u.id = a.penyerahan_stnk_id 
            LEFT JOIN wtc_penyerahan_bpkb v ON v.id = a.penyerahan_bpkb_id 
            LEFT JOIN wtc_penyerahan_stnk w ON w.id = a.penyerahan_notice_id 
            LEFT JOIN wtc_penyerahan_stnk x ON x.id = a.penyerahan_polisi_id 
            LEFT JOIN wtc_pengurusan_stnk_bpkb y ON y.id = a.pengurusan_stnk_bpkb_id 
            LEFT JOIN purchase_order z ON z.id = a.purchase_order_id

            LEFT JOIN product_product pp ON pp.id=a.product_id
            LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id 
            LEFT JOIN product_attribute_value_product_product_rel pprel ON pprel.prod_id = pp.id
            LEFT JOIN product_attribute_value ppv ON ppv.id = pprel.att_id 

            """
        query_where = " WHERE a.name is not Null "
        if lot_ids :
            query_where +=" AND  a.id in %s" % str(
                tuple(lot_ids)).replace(',)', ')')            
        if branch_ids :
            query_where +=" AND  a.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        if partner_ids :
            query_where+=" AND  a.customer_id  in %s" % str(
                tuple(partner_ids)).replace(',)', ')')
        if loc_stnk_ids :
            query_where+=" AND  a.lokasi_stnk_id  in %s" % str(
                tuple(loc_stnk_ids)).replace(',)', ')')
        if loc_bpkb_ids :
            query_where+=" AND  a.lokasi_bpkb_id  in %s" % str(
                tuple(loc_bpkb_ids)).replace(',)', ')')   
        if birojasa_ids :
            query_where+=" AND  a.biro_jasa_id  in %s" % str(
                tuple(birojasa_ids)).replace(',)', ')')    
        if finco_ids :
            query_where+=" AND  a.finco_id  in %s" % str(
                tuple(finco_ids)).replace(',)', ')')  
        if start_date :
            query_where+=" AND k.date_order >= '%s'" % str(start_date)
        if end_date :
            query_where+=" AND k.date_order <= '%s'" % str(end_date)

        query_order = " order by b.code "     
        
        cr.execute (query+query_where+query_order)
        ress = cr.fetchall()

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf
        
        #WKS 1
        worksheet = workbook.add_worksheet('Track STNK BPKB')
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
        worksheet.set_column('U1:U1', 20)
        worksheet.set_column('V1:V1', 20)
        worksheet.set_column('W1:W1', 20)        
        worksheet.set_column('X1:X1', 20)
        worksheet.set_column('Y1:Y1', 20)
        worksheet.set_column('Z1:Z1', 20)
        
        worksheet.set_column('AA1:AA1', 20)
        worksheet.set_column('AB1:AB1', 20)
        worksheet.set_column('AC1:AC1', 20)
        worksheet.set_column('AD1:AD1', 20)
        worksheet.set_column('AE1:AE1', 20)
        worksheet.set_column('AF1:AF1', 20)
        worksheet.set_column('AG1:AG1', 20)
        worksheet.set_column('AH1:AH1', 20)
        worksheet.set_column('AI1:AI1', 20)
        worksheet.set_column('AJ1:AJ1', 20)
        worksheet.set_column('AK1:AK1', 20)
        worksheet.set_column('AL1:AL1', 20)
        worksheet.set_column('AM1:AM1', 20)
        worksheet.set_column('AN1:AN1', 20)
        worksheet.set_column('AO1:AO1', 20)
        worksheet.set_column('AP1:AP1', 20)
        worksheet.set_column('AQ1:AQ1', 20)
        worksheet.set_column('AR1:AR1', 20)
        worksheet.set_column('AS1:AS1', 20)
        worksheet.set_column('AT1:AT1', 20)
        worksheet.set_column('AU1:AU1', 20)
        worksheet.set_column('AV1:AV1', 20)
        worksheet.set_column('AW1:AW1', 20)        
        worksheet.set_column('AX1:AX1', 20)
        worksheet.set_column('AY1:AY1', 20)
        worksheet.set_column('AZ1:AZ1', 20)
                     
        worksheet.set_column('BA1:BA1', 20)
        worksheet.set_column('BB1:BB1', 20)
        worksheet.set_column('BC1:BC1', 20)
        worksheet.set_column('BD1:BD1', 20)
        worksheet.set_column('BE1:BE1', 20)
        worksheet.set_column('BF1:BF1', 20)
                             
        get_date = self._get_default(cr, uid, date=True, context=context)
        date = get_date.strftime("%Y-%m-%d %H:%M:%S")
        date_date = get_date.strftime("%Y-%m-%d")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        filename = 'Report Track STNK BPKB '+str(date)+'.xlsx'  
        
        #WKS 1      
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report Track STNK BPKB' , wbf['title_doc'])
        worksheet.write('A3', 'Tanggal : %s'%(str(date)) , wbf['company'])
        worksheet.write('A4', 'Periode : %s s/d %s'%(str(start_date),str(end_date)) , wbf['company'])
        
        row=4   
        rowsaldo = row
        row+=1
        
        worksheet.write('A%s' % (row+1), 'No' , wbf['header_no'])
        worksheet.write('B%s' % (row+1), 'Cabang Penjual' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'Engine No' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'Chassis No' , wbf['header'])
        worksheet.write('E%s' % (row+1), 'Partner Code' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'Partner Name' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'Lokasi STNK' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'Lokasi BPKB' , wbf['header'])
        worksheet.write('I%s' % (row+1), 'Lokasi Stock' , wbf['header'])
        worksheet.write('J%s' % (row+1), 'Supplier' , wbf['header'])
        worksheet.write('K%s' % (row+1), 'Code Customer STNK' , wbf['header'])
        worksheet.write('L%s' % (row+1), 'Customer STNK' , wbf['header'])
        worksheet.write('M%s' % (row+1), 'State' , wbf['header'])
        worksheet.write('N%s' % (row+1), 'Finance Company' , wbf['header'])
        worksheet.write('O%s' % (row+1), 'Birojasa' , wbf['header'])                
        worksheet.write('P%s' % (row+1), 'No Sales Order' , wbf['header'])
        worksheet.write('Q%s' % (row+1), 'Tgl Sales Order' , wbf['header'])
        worksheet.write('R%s' % (row+1), 'No Purchase Order' , wbf['header'])
        worksheet.write('S%s' % (row+1), 'Tgl Purchase Order' , wbf['header'])
        worksheet.write('T%s' % (row+1), 'No Permohonan Faktur' , wbf['header'])
        worksheet.write('U%s' % (row+1), 'Tgl Mohon Faktur' , wbf['header'])
        worksheet.write('V%s' % (row+1), 'No Penerimaan Faktur' , wbf['header'])
        worksheet.write('W%s' % (row+1), 'Tgl Terima Faktur' , wbf['header'])
        worksheet.write('X%s' % (row+1), 'No Faktur' , wbf['header'])
        worksheet.write('Y%s' % (row+1), 'Tgl Cetak Faktur' , wbf['header'])
        worksheet.write('Z%s' % (row+1), 'No Penyerahan Faktur' , wbf['header'])

        worksheet.write('AA%s' % (row+1), 'Tgl Penyerahan Faktur' , wbf['header_no'])
        worksheet.write('AB%s' % (row+1), 'No Proses STNK' , wbf['header'])
        worksheet.write('AC%s' % (row+1), 'Tgl Proses STNK' , wbf['header'])
        worksheet.write('AD%s' % (row+1), 'No Tagihan Birojasa' , wbf['header'])
        worksheet.write('AE%s' % (row+1), 'Tgl Tagihan Birojasa' , wbf['header'])
        worksheet.write('AF%s' % (row+1), 'No Penerimaan STNK' , wbf['header'])
        worksheet.write('AG%s' % (row+1), 'No Penerimaan Notice' , wbf['header'])
        worksheet.write('AH%s' % (row+1), 'No Penerimaan Plat' , wbf['header'])
        worksheet.write('AI%s' % (row+1), 'No Penerimaan BPKB' , wbf['header'])
        worksheet.write('AJ%s' % (row+1), 'No Notice' , wbf['header'])
        worksheet.write('AK%s' % (row+1), 'No BPKB' , wbf['header'])
        worksheet.write('AL%s' % (row+1), 'No Polisi' , wbf['header'])
        worksheet.write('AM%s' % (row+1), 'No STNK' , wbf['header'])
        worksheet.write('AN%s' % (row+1), 'Tgl JTP Notice' , wbf['header'])
        worksheet.write('AO%s' % (row+1), 'Tgl JTP STNK' , wbf['header'])                
        worksheet.write('AP%s' % (row+1), 'Tgl Jadi BPKB' , wbf['header'])
        worksheet.write('AQ%s' % (row+1), 'No Urut BPKB' , wbf['header'])
        worksheet.write('AR%s' % (row+1), 'Tgl Terima STNK' , wbf['header'])
        worksheet.write('AS%s' % (row+1), 'Tgl Terima BPKB' , wbf['header'])
        worksheet.write('AT%s' % (row+1), 'Tgl Terima Notice' , wbf['header'])
        worksheet.write('AU%s' % (row+1), 'Tgl Terima Plat' , wbf['header'])
        worksheet.write('AV%s' % (row+1), 'No Penyerahan STNK' , wbf['header'])
        worksheet.write('AW%s' % (row+1), 'No Penyerahan Notice' , wbf['header'])
        worksheet.write('AX%s' % (row+1), 'No Penyerahan Plat' , wbf['header'])
        worksheet.write('AY%s' % (row+1), 'No Penyerahan BPKB' , wbf['header'])
        worksheet.write('AZ%s' % (row+1), 'Tgl Penyerahan STNK' , wbf['header'])
        
        worksheet.write('BA%s' % (row+1), 'Tgl Penyerahan Notice' , wbf['header_no'])
        worksheet.write('BB%s' % (row+1), 'Tgl Penyerahan Plat' , wbf['header'])
        worksheet.write('BC%s' % (row+1), 'Tgl Penyerahan BPKB' , wbf['header'])
        worksheet.write('BD%s' % (row+1), 'No Pengurusan STNK BPKB' , wbf['header'])
        worksheet.write('BE%s' % (row+1), 'Tgl Pengurusan STNK BPKB' , wbf['header'])
        worksheet.write('BF%s' % (row+1), 'No Invoice' , wbf['header'])
        worksheet.write('BG%s' % (row+1), 'Desc Type' , wbf['header'])
        worksheet.write('BH%s' % (row+1), 'Kode Type' , wbf['header'])
                                            
        row+=2         
        no = 0
        row1 = row
          
        for res in ress:
            nama_branch = str(res[0].encode('ascii','ignore').decode('ascii')) if res[0] != None else ''
            lokasi_stnk = str(res[1].encode('ascii','ignore').decode('ascii')) if res[1] != None else ''
            lokasi_bpkb = str(res[2].encode('ascii','ignore').decode('ascii')) if res[2] != None else ''
            code_nama_customer = str(res[3].encode('ascii','ignore').decode('ascii')) if res[3] != None else ''                        
            nama_customer = str(res[4].encode('ascii','ignore').decode('ascii')) if res[4] != None else ''
            engine_no = str(res[5].encode('ascii','ignore').decode('ascii')) if res[5] != None else ''
            chassis_no = str(res[6].encode('ascii','ignore').decode('ascii')) if res[6] != None else ''
            location_name = str(res[7].encode('ascii','ignore').decode('ascii')) if res[7] != None else ''
            supplier_name = str(res[8].encode('ascii','ignore').decode('ascii')) if res[8] != None else ''
            code_stnk_name = str(res[9].encode('ascii','ignore').decode('ascii')) if res[9] != None else ''                        
            stnk_name = str(res[10].encode('ascii','ignore').decode('ascii')) if res[10] != None else ''
            state = str(res[11].encode('ascii','ignore').decode('ascii')) if res[11] != None else ''
            finco_name = str(res[12].encode('ascii','ignore').decode('ascii')) if res[12] != None else ''
            birojasa_name = str(res[13].encode('ascii','ignore').decode('ascii')) if res[13] != None else ''
            sale_order = str(res[14].encode('ascii','ignore').decode('ascii')) if res[14] != None else ''
            tgl_sale_order = datetime.strptime(res[15], "%Y-%m-%d").date() if res[15] != None else ''
            purchase_order = str(res[16].encode('ascii','ignore').decode('ascii')) if res[16] != None else ''
            tgl_purchase_order = datetime.strptime(res[17], "%Y-%m-%d").date() if res[17] != None else ''
            no_permohonan_faktur = str(res[18].encode('ascii','ignore').decode('ascii')) if res[18] != None else ''
            tgl_faktur = datetime.strptime(res[19], "%Y-%m-%d").date() if res[19] != None else ''
            no_penerimaan_faktur = str(res[20].encode('ascii','ignore').decode('ascii')) if res[20] != None else ''
            tgl_terima = datetime.strptime(res[21], "%Y-%m-%d").date() if res[21] != None else ''
            no_faktur = str(res[22].encode('ascii','ignore').decode('ascii')) if res[22] != None else ''
            tgl_cetak_faktur = datetime.strptime(res[23], "%Y-%m-%d").date() if res[23] != None else ''
            no_proses_stnk = str(res[24].encode('ascii','ignore').decode('ascii')) if res[24] != None else ''
            tgl_proses_stnk = datetime.strptime(res[25], "%Y-%m-%d").date() if res[25] != None else ''
            no_proses_birojasa = str(res[26].encode('ascii','ignore').decode('ascii')) if res[26] != None else ''
            tgl_proses_birojasa = datetime.strptime(res[27], "%Y-%m-%d").date() if res[27] != None else ''
            no_penyerahan_faktur = str(res[28].encode('ascii','ignore').decode('ascii')) if res[28] != None else ''
            tgl_penyerahan_faktur = datetime.strptime(res[29], "%Y-%m-%d").date() if res[29] != None else ''                      
            no_penerimaan_stnk = str(res[30].encode('ascii','ignore').decode('ascii')) if res[30] != None else ''
            no_penerimaan_notice = str(res[31].encode('ascii','ignore').decode('ascii')) if res[31] != None else ''
            no_penerimaan_no_polisi = str(res[32].encode('ascii','ignore').decode('ascii')) if res[32] != None else ''
            no_penerimaan_bpkb = str(res[33].encode('ascii','ignore').decode('ascii')) if res[33] != None else ''
            no_notice = str(res[34].encode('ascii','ignore').decode('ascii')) if res[34] != None else ''
            no_bpkb = str(res[35].encode('ascii','ignore').decode('ascii')) if res[35] != None else ''
            no_polisi = str(res[36].encode('ascii','ignore').decode('ascii')) if res[36] != None else ''
            no_stnk = str(res[37].encode('ascii','ignore').decode('ascii')) if res[37] != None else ''
            tgl_notice = datetime.strptime(res[38], "%Y-%m-%d").date() if res[38] != None else ''
            tgl_stnk = datetime.strptime(res[39], "%Y-%m-%d").date() if res[39] != None else ''
            tgl_bpkb = datetime.strptime(res[40], "%Y-%m-%d").date() if res[40] != None else ''
            no_urut_bpkb = str(res[41].encode('ascii','ignore').decode('ascii')) if res[41] != None else ''
            tgl_terima_stnk = datetime.strptime(res[42], "%Y-%m-%d").date() if res[42] != None else ''
            tgl_terima_bpkb = datetime.strptime(res[43], "%Y-%m-%d").date() if res[43] != None else ''
            tgl_terima_notice = datetime.strptime(res[44], "%Y-%m-%d").date() if res[44] != None else ''
            tgl_terima_no_polisi = datetime.strptime(res[45], "%Y-%m-%d").date() if res[45] != None else ''       
            no_penyerahan_stnk = str(res[46].encode('ascii','ignore').decode('ascii')) if res[46] != None else ''
            no_penyerahan_notice = str(res[47].encode('ascii','ignore').decode('ascii')) if res[47] != None else ''
            no_penyerahan_polisi = str(res[48].encode('ascii','ignore').decode('ascii')) if res[48] != None else ''
            no_penyerahan_bpkb = str(res[49].encode('ascii','ignore').decode('ascii')) if res[49] != None else ''
            tgl_penyerahan_stnk = datetime.strptime(res[50], "%Y-%m-%d").date() if res[50] != None else ''
            tgl_penyerahan_notice = datetime.strptime(res[51], "%Y-%m-%d").date() if res[51] != None else ''
            tgl_penyerahan_plat = datetime.strptime(res[52], "%Y-%m-%d").date() if res[52] != None else ''
            tgl_penyerahan_bpkb = datetime.strptime(res[53], "%Y-%m-%d").date() if res[53] != None else ''
            no_pengurusan_stnk_bpkb = str(res[54].encode('ascii','ignore').decode('ascii')) if res[54] != None else ''
            tgl_pengurusan_stnk_bpkb = datetime.strptime(res[55], "%Y-%m-%d").date() if res[54] != None else ''
            invoice_bbn = str(res[56].encode('ascii','ignore').decode('ascii')) if res[56] != None else ''
            desc_type = str(res[57].encode('ascii','ignore').decode('ascii')) if res[57] != None else ''
            kode_type = str(res[57].encode('ascii','ignore').decode('ascii')) if res[57] != None else ''
            no += 1         
          
            worksheet.write('A%s' % row, no , wbf['content_number'])                    
            worksheet.write('B%s' % row, nama_branch , wbf['content'])
            worksheet.write('C%s' % row, engine_no , wbf['content'])
            worksheet.write('D%s' % row, chassis_no , wbf['content'])
            worksheet.write('E%s' % row, code_nama_customer , wbf['content'])
            worksheet.write('F%s' % row, nama_customer , wbf['content'])
            worksheet.write('G%s' % row, lokasi_stnk , wbf['content'])
            worksheet.write('H%s' % row, lokasi_bpkb , wbf['content'])  
            worksheet.write('I%s' % row, location_name, wbf['content'])
            worksheet.write('J%s' % row, supplier_name , wbf['content'])
            worksheet.write('K%s' % row, code_stnk_name , wbf['content'])
            worksheet.write('L%s' % row, stnk_name , wbf['content'])
            worksheet.write('M%s' % row, state , wbf['content'])
            worksheet.write('N%s' % row, finco_name , wbf['content'])
            worksheet.write('O%s' % row, birojasa_name , wbf['content'])
            worksheet.write('P%s' % row, sale_order , wbf['content'])
            worksheet.write('Q%s' % row, tgl_sale_order , wbf['content_date']) 
            worksheet.write('R%s' % row, purchase_order , wbf['content']) 
            worksheet.write('S%s' % row, tgl_purchase_order , wbf['content_date']) 
            worksheet.write('T%s' % row, no_permohonan_faktur , wbf['content']) 
            worksheet.write('U%s' % row, tgl_faktur , wbf['content_date'])
            worksheet.write('V%s' % row, no_penerimaan_faktur , wbf['content'])
            worksheet.write('W%s' % row, tgl_terima , wbf['content_date'])
            worksheet.write('X%s' % row, no_faktur , wbf['content'])
            worksheet.write('Y%s' % row, tgl_cetak_faktur , wbf['content_date'])
            worksheet.write('Z%s' % row, no_penyerahan_faktur , wbf['content'])
            
            worksheet.write('AA%s' % row, tgl_penyerahan_faktur , wbf['content_date'])                    
            worksheet.write('AB%s' % row, no_proses_stnk , wbf['content'])
            worksheet.write('AC%s' % row, tgl_proses_stnk , wbf['content_date'])
            worksheet.write('AD%s' % row, no_proses_birojasa , wbf['content'])
            worksheet.write('AE%s' % row, tgl_proses_birojasa , wbf['content_date'])
            worksheet.write('AF%s' % row, no_penerimaan_stnk , wbf['content'])
            worksheet.write('AG%s' % row, no_penerimaan_notice , wbf['content'])
            worksheet.write('AH%s' % row, no_penerimaan_no_polisi , wbf['content'])  
            worksheet.write('AI%s' % row, no_penerimaan_bpkb , wbf['content'])
            worksheet.write('AJ%s' % row, no_notice , wbf['content'])
            worksheet.write('AK%s' % row, no_bpkb , wbf['content'])
            worksheet.write('AL%s' % row, no_polisi , wbf['content'])
            worksheet.write('AM%s' % row, no_stnk , wbf['content'])
            worksheet.write('AN%s' % row, tgl_notice , wbf['content_date'])
            worksheet.write('AO%s' % row, tgl_stnk , wbf['content_date'])
            worksheet.write('AP%s' % row, tgl_bpkb , wbf['content_date'])
            worksheet.write('AQ%s' % row, no_urut_bpkb , wbf['content']) 
            worksheet.write('AR%s' % row, tgl_terima_stnk , wbf['content_date']) 
            worksheet.write('AS%s' % row, tgl_terima_bpkb , wbf['content_date']) 
            worksheet.write('AT%s' % row, tgl_terima_notice , wbf['content_date']) 
            worksheet.write('AU%s' % row, tgl_terima_no_polisi , wbf['content_date'])
            worksheet.write('AV%s' % row, no_penyerahan_stnk , wbf['content'])
            worksheet.write('AW%s' % row, no_penyerahan_notice , wbf['content'])
            worksheet.write('AX%s' % row, no_penyerahan_polisi , wbf['content'])
            worksheet.write('AY%s' % row, no_penyerahan_bpkb , wbf['content'])
            worksheet.write('AZ%s' % row, tgl_penyerahan_stnk , wbf['content_date'])
            
            worksheet.write('BA%s' % row, tgl_penyerahan_notice , wbf['content_date'])                    
            worksheet.write('BB%s' % row, tgl_penyerahan_plat , wbf['content_date'])
            worksheet.write('BC%s' % row, tgl_penyerahan_bpkb , wbf['content_date'])
            worksheet.write('BD%s' % row, no_pengurusan_stnk_bpkb , wbf['content'])
            worksheet.write('BE%s' % row, tgl_pengurusan_stnk_bpkb , wbf['content_date'])
            worksheet.write('BF%s' % row, invoice_bbn , wbf['content'])
            worksheet.write('BG%s' % row, desc_type , wbf['content'])
            worksheet.write('BH%s' % row, kode_type , wbf['content'])
          
            row+=1
            
        worksheet.autofilter('A6:BF%s' % (row))  
        worksheet.freeze_panes(5, 3)
        
        #TOTAL                 
        worksheet.write('A%s'%(row+1), '%s %s' % (str(date),user) , wbf['footer'])  
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'wtc_report_stnk_bpkb', 'view_report_stnk_bpkb')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'report.stnk.bpkb',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }
report_stnk_bpkb()
