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

class wtc_report_stnk_bpkb(osv.osv_memory):
   
    _inherit = "report.stnk.bpkb"

    wbf = {}

    def _print_excel_report_lead_time(self, cr, uid, ids, data, context=None):
        
        branch_ids = data['branch_ids']
        partner_ids = data['partner_ids']
        loc_stnk_ids = data['loc_stnk_ids']
        loc_bpkb_ids = data['loc_bpkb_ids']
        lot_ids = data['lot_ids']
        birojasa_ids = data['birojasa_ids']
        finco_ids = data['finco_ids']
        start_date = data['start_date']
        end_date = data['end_date']
        status_lead_time = data['status_lead_time']

        query = """
                    SELECT dso.date_order as date_order
                    , lot.name as no_engine
                    , lot.chassis_no as no_chassis
                    , partner.default_code as code_customer
                    , partner.name as customer_name
                    , anpartner.default_code as code_an_stnk
                    , anpartner.name as an_stnk_name
                    , lot.tgl_faktur as tgl_mohon_faktur
                    , age(lot.tgl_faktur,dso.date_order) as lt_mohon_faktur
                    , lot.tgl_terima as tgl_terima_faktur
                    , lot.tgl_cetak_faktur as tgl_cetak_faktur
                    , lot.faktur_stnk as no_faktur
                    , age(lot.tgl_terima,dso.date_order) as lt_terima_faktur
                    , lot.tgl_proses_stnk as tgl_proses_stnk
                    , birojasa.name as birojasa
                    , age(lot.tgl_proses_stnk,dso.date_order) as lt_proses_stnk
                    , lot.tgl_proses_birojasa as tgl_tagihan_birojasa
                    , age(lot.tgl_proses_birojasa,dso.date_order) as lt_tagihan_birojasa
                    , lot.tgl_terima_notice as tgl_terima_notice
                    , lot.no_notice as no_notice
                    , lot.tgl_notice as tgl_jtp_notice
                    , age(lot.tgl_terima_notice,dso.date_order) as lt_terima_notice
                    , lot.tgl_terima_stnk as tgl_terima_stnk
                    , lot.no_stnk as no_stnk
                    , lot.tgl_stnk as tgl_jtp_stnk
                    , age(lot.tgl_terima_stnk,dso.date_order) as lt_terima_stnk
                    , lot.tgl_terima_no_polisi as tgl_terima_plat
                    , lot.no_polisi as no_plat
                    , age(lot.tgl_terima_no_polisi,dso.date_order) as lt_terima_plat
                    , lot.tgl_terima_bpkb as tgl_terima_bpkb
                    , lot.no_bpkb as no_bpkb
                    , lot.tgl_bpkb as tgl_jadi_bpkb
                    , lot.no_urut_bpkb as no_urut
                    , age(lot.tgl_terima_bpkb,dso.date_order) as lt_terima_bpkb
                    , lot.tgl_penyerahan_notice as tgl_penyerahan_notice
                    , age(lot.tgl_penyerahan_notice,dso.date_order) as lt_penyerahan_notice
                    , lot.tgl_penyerahan_stnk as tgl_penyerahan_stnk
                    , age(lot.tgl_penyerahan_stnk,dso.date_order) as lt_penyerahan_stnk
                    , lot.tgl_penyerahan_plat as tgl_penyerahan_plat
                    , age(lot.tgl_penyerahan_plat,dso.date_order) as lt_penyerahan_plat
                    , lot.tgl_penyerahan_bpkb as tgl_penyerahan_bpkb
                    , age(lot.tgl_penyerahan_bpkb,dso.date_order) as lt_penyerahan_bpkb
                    , dso.name as no_dso
                    , partner.mobile
                    , b.code as branch_code
                    , b.name as branch_name
                    , '['||city.code||']'|| city.name as area
                    , to_char(dso.date_order,'MM') as bulan_so
                    , to_char(dso.date_order,'YYYY') as tahun_so
                    , supplier.name as main_dealer
                    , finco.name as finco
                    , peny_bpkb.penerima as penerima_bpkb
                    , '' as tgl_bayar_prbj
                    FROM stock_production_lot lot
                    INNER JOIN dealer_sale_order dso ON dso.id = lot.dealer_sale_order_id
                    INNER JOIN res_partner partner ON partner.id = lot.customer_id
                    LEFT JOIN res_partner anpartner ON anpartner.id = lot.customer_stnk
                    LEFT JOIN res_partner birojasa ON birojasa.id = lot.biro_jasa_id
                    INNER JOIN wtc_branch b ON b.id = dso.branch_id
                    LEFT JOIN wtc_city city ON city.id = anpartner.city_id
                    LEFT JOIN res_partner supplier ON supplier.id = b.default_supplier_id
                    LEFT JOIN res_partner finco ON finco.id = lot.finco_id
                    LEFT JOIN wtc_penyerahan_bpkb peny_bpkb ON peny_bpkb.id = lot.penyerahan_bpkb_id
            """
        
        query_where = " WHERE lot.biro_jasa_id is not null  "
        if lot_ids :
            query_where +=" AND  lot.id in %s" % str(
                tuple(lot_ids)).replace(',)', ')')            
        if branch_ids :
            query_where +=" AND  lot.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        if partner_ids :
            query_where+=" AND  lot.customer_id  in %s" % str(
                tuple(partner_ids)).replace(',)', ')')
        if loc_stnk_ids :
            query_where+=" AND  lot.lokasi_stnk_id  in %s" % str(
                tuple(loc_stnk_ids)).replace(',)', ')')
        if loc_bpkb_ids :
            query_where+=" AND  lot.lokasi_bpkb_id  in %s" % str(
                tuple(loc_bpkb_ids)).replace(',)', ')')   
        if birojasa_ids :
            query_where+=" AND  lot.biro_jasa_id  in %s" % str(
                tuple(birojasa_ids)).replace(',)', ')')    
        if finco_ids :
            query_where+=" AND  lot.finco_id  in %s" % str(
                tuple(finco_ids)).replace(',)', ')')    
        if start_date :
            query_where+=" AND dso.date_order >= '%s'" % str(start_date)
        if end_date :
            query_where+=" AND dso.date_order <= '%s'" % str(end_date)

        if status_lead_time:
            if status_lead_time == 'complete':
                query_where += """ 
                    AND lot.tgl_faktur IS NOT NULL
                    AND lot.tgl_terima IS NOT NULL IS NOT NULL
                    AND lot.tgl_cetak_faktur IS NOT NULL
                    AND lot.tgl_proses_stnk IS NOT NULL
                    AND lot.tgl_proses_birojasa IS NOT NULL
                    AND lot.tgl_terima_notice IS NOT NULL
                    AND lot.tgl_terima_stnk IS NOT NULL
                    AND lot.tgl_terima_no_polisi IS NOT NULL
                    AND lot.tgl_terima_bpkb IS NOT NULL
                    AND lot.tgl_penyerahan_notice IS NOT NULL
                    AND lot.tgl_penyerahan_stnk IS NOT NULL
                    AND lot.tgl_penyerahan_plat IS NOT NULL
                    AND lot.tgl_penyerahan_bpkb IS NOT NULL
                """
            elif status_lead_time == 'outstanding':
                query_where += """ AND (
                    tgl_faktur IS NULL
                    OR lot.tgl_terima IS NOT NULL IS NULL
                    OR lot.tgl_cetak_faktur IS NULL
                    OR lot.tgl_proses_stnk IS NULL
                    OR lot.tgl_proses_birojasa IS NULL
                    OR lot.tgl_terima_notice IS NULL
                    OR lot.tgl_terima_stnk IS NULL
                    OR lot.tgl_terima_no_polisi IS NULL
                    OR lot.tgl_terima_bpkb IS NULL
                    OR lot.tgl_penyerahan_notice IS NULL
                    OR lot.tgl_penyerahan_stnk IS NULL
                    OR lot.tgl_penyerahan_plat IS NULL
                    OR lot.tgl_penyerahan_bpkb IS NULL
                    )
                """
          
        query_order="order by no_engine"
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
        worksheet.set_column('D1:D1', 23)
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
        worksheet.set_column('AW1:AW1', 14)
        worksheet.set_column('AX1:AX1', 14)
        worksheet.set_column('AY1:AY1', 27)
        worksheet.set_column('AZ1:AZ1', 27)
        worksheet.set_column('BA1:BA1', 25)
        worksheet.set_column('BB1:BB1', 20)
         
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
        worksheet.write('B%s' % (row+1), 'Code Cabang' , wbf['header'])
        worksheet.write('C%s' % (row+1), 'Nama Cabang' , wbf['header'])
        worksheet.write('D%s' % (row+1), 'Area' , wbf['header'])
        
        worksheet.write('E%s' % (row+1), 'Engine No' , wbf['header'])
        worksheet.write('F%s' % (row+1), 'Chassis No' , wbf['header'])
        worksheet.write('G%s' % (row+1), 'Partner Code' , wbf['header'])
        worksheet.write('H%s' % (row+1), 'Partner Name' , wbf['header'])
        worksheet.write('I%s' % (row+1), 'Code AN STNK' , wbf['header'])
        worksheet.write('J%s' % (row+1), 'Nama STNK' , wbf['header'])
        worksheet.write('K%s' % (row+1), 'Tgl Mohon Faktur' , wbf['header'])
        worksheet.write('L%s' % (row+1), 'L-T Mohon Faktur' , wbf['header'])
        worksheet.write('M%s' % (row+1), 'Tgl Terima Faktur' , wbf['header'])
        worksheet.write('N%s' % (row+1), 'Tgl Cetak Faktur' , wbf['header'])
        worksheet.write('O%s' % (row+1), 'No Faktur' , wbf['header'])
        worksheet.write('P%s' % (row+1), 'L-T Terima Faktur' , wbf['header'])
        worksheet.write('Q%s' % (row+1), 'Tgl Proses STNK' , wbf['header'])
        worksheet.write('R%s' % (row+1), 'Birojasa' , wbf['header'])                
        worksheet.write('S%s' % (row+1), 'L-T Proses STNK' , wbf['header'])
        worksheet.write('T%s' % (row+1), 'Tgl Tagihan Birojasa' , wbf['header'])
        worksheet.write('U%s' % (row+1), 'L-T Tagihan Birojasa' , wbf['header'])
        worksheet.write('V%s' % (row+1), 'Tgl Terima Notice' , wbf['header'])
        worksheet.write('W%s' % (row+1), 'No Notice' , wbf['header'])
        worksheet.write('X%s' % (row+1), 'Tgl JTP Notice' , wbf['header'])
        worksheet.write('Y%s' % (row+1), 'L-T Terima Notice' , wbf['header'])
        worksheet.write('Z%s' % (row+1), 'Tgl Terima STNK' , wbf['header'])
        worksheet.write('AA%s' % (row+1), 'No STNK' , wbf['header'])
        worksheet.write('AB%s' % (row+1), 'TGL JTP STNK' , wbf['header'])
        worksheet.write('AC%s' % (row+1), 'L-T Terima STNK' , wbf['header'])

        worksheet.write('AD%s' % (row+1), 'Tgl Terima Plat' , wbf['header_no'])
        worksheet.write('AE%s' % (row+1), 'No Plat' , wbf['header'])
        worksheet.write('AF%s' % (row+1), 'L-T Terima Plat' , wbf['header'])
        worksheet.write('AG%s' % (row+1), 'Tgl Terima BPKB' , wbf['header'])
        worksheet.write('AH%s' % (row+1), 'No BPKB' , wbf['header'])
        worksheet.write('AI%s' % (row+1), 'Tgl Jadi BPKB' , wbf['header'])
        worksheet.write('AJ%s' % (row+1), 'No Urut' , wbf['header'])
        worksheet.write('AK%s' % (row+1), 'L-T Terima BPKB' , wbf['header'])
        worksheet.write('AL%s' % (row+1), 'Tgl Penyerahan Notice' , wbf['header'])
        worksheet.write('AM%s' % (row+1), 'L-T Penyerahan Notice' , wbf['header'])
        worksheet.write('AN%s' % (row+1), 'Tgl Penyerahan STNK' , wbf['header'])
        worksheet.write('AO%s' % (row+1), 'L-T Penyerahan STNK' , wbf['header'])
        worksheet.write('AP%s' % (row+1), 'Tgl Penyerahan Plat' , wbf['header'])
        worksheet.write('AQ%s' % (row+1), 'L-T Penyerahan Plat' , wbf['header'])
        worksheet.write('AR%s' % (row+1), 'Tgl Penyerahan BPKB' , wbf['header'])                
        worksheet.write('AS%s' % (row+1), 'L-T Penyerahan BPKB' , wbf['header'])
        worksheet.write('AT%s' % (row+1), 'Tgl SO' , wbf['header'])                
        worksheet.write('AU%s' % (row+1), 'No SO' , wbf['header'])
        worksheet.write('AV%s' % (row+1), 'Mobile' , wbf['header'])
        # Request HO Admin 03082020
        worksheet.write('AW%s' % (row+1), 'Bulan' , wbf['header'])
        worksheet.write('AX%s' % (row+1), 'Tahun' , wbf['header'])
        worksheet.write('AY%s' % (row+1), 'Main Dealer' , wbf['header'])
        worksheet.write('AZ%s' % (row+1), 'Finance Company' , wbf['header'])
        worksheet.write('BA%s' % (row+1), 'Nama Penerima BPKB' , wbf['header'])
        worksheet.write('BB%s' % (row+1), 'Tanggal Bayar PRBJ' , wbf['header'])
                                            
        row+=2         
        no = 0
        row1 = row
          
        for res in ress:
            no_engine = str(res[1].encode('ascii','ignore').decode('ascii')) if res[1] != None else ''
            no_chassis = str(res[2].encode('ascii','ignore').decode('ascii')) if res[2] != None else ''
            code_customer = str(res[3].encode('ascii','ignore').decode('ascii')) if res[3] != None else ''
            customer_name = str(res[4].encode('ascii','ignore').decode('ascii')) if res[4] != None else ''
            code_an_stnk = str(res[5].encode('ascii','ignore').decode('ascii')) if res[5] != None else ''
            an_stnk_name = str(res[6].encode('ascii','ignore').decode('ascii')) if res[6] != None else ''
            tgl_mohon_faktur = datetime.strptime(res[7], "%Y-%m-%d").date() if res[7] != None else ''
            lt_mohon_faktur = str(res[8]).replace('days, 0:00:00', '')  if res[8] != None else ''
            tgl_terima_faktur = datetime.strptime(res[9], "%Y-%m-%d").date() if res[9] != None else ''
            tgl_cetak_faktur = datetime.strptime(res[10], "%Y-%m-%d").date() if res[10] != None else ''
            no_faktur = str(res[11].encode('ascii','ignore').decode('ascii')) if res[11] != None else ''
            lt_terima_faktur = str(res[12]) if res[12] != None else ''
            tgl_proses_stnk = datetime.strptime(res[13], "%Y-%m-%d").date() if res[13] != None else ''
            birojasa = str(res[14].encode('ascii','ignore').decode('ascii')) if res[14] != None else ''
            lt_proses_stnk = str(res[15]) if res[15] != None else ''
            tgl_tagihan_birojasa = datetime.strptime(res[16], "%Y-%m-%d").date() if res[16] != None else ''
            lt_tagihan_birojasa = str(res[17]) if res[17] != None else ''
            tgl_terima_notice = datetime.strptime(res[18], "%Y-%m-%d").date() if res[18] != None else ''
            no_notice = str(res[19].encode('ascii','ignore').decode('ascii')) if res[19] != None else ''
            tgl_jtp_notice = datetime.strptime(res[20], "%Y-%m-%d").date() if res[20] != None else ''
            lt_terima_notice = str(res[21]) if res[21] != None else ''
            tgl_terima_stnk = datetime.strptime(res[22], "%Y-%m-%d").date() if res[22] != None else ''
            no_stnk = str(res[23].encode('ascii','ignore').decode('ascii')) if res[23] != None else ''
            tgl_jtp_stnk = datetime.strptime(res[24], "%Y-%m-%d").date() if res[24] != None else ''
            lt_terima_stnk = str(res[25]) if res[25] != None else ''
            tgl_terima_plat = datetime.strptime(res[26], "%Y-%m-%d").date() if res[26] != None else ''
            no_plat = str(res[27].encode('ascii','ignore').decode('ascii')) if res[27] != None else ''
            lt_terima_plat = str(res[28]) if res[28] != None else ''
            tgl_terima_bpkb = datetime.strptime(res[29], "%Y-%m-%d").date() if res[29] != None else ''
            no_bpkb = str(res[30].encode('ascii','ignore').decode('ascii')) if res[30] != None else ''
            tgl_jadi_bpkb = datetime.strptime(res[31], "%Y-%m-%d").date() if res[31] != None else ''
            no_urut = str(res[32].encode('ascii','ignore').decode('ascii')) if res[32] != None else ''
            lt_terima_bpkb = str(res[33]) if res[33] != None else ''
            tgl_penyerahan_notice = datetime.strptime(res[34], "%Y-%m-%d").date() if res[34] != None else ''
            lt_penyerahan_notice = str(res[35]) if res[35] != None else ''
            tgl_penyerahan_stnk = datetime.strptime(res[36], "%Y-%m-%d").date() if res[36] != None else ''
            lt_penyerahan_stnk = str(res[37]) if res[37] != None else ''
            tgl_penyerahan_plat = datetime.strptime(res[38], "%Y-%m-%d").date() if res[38] != None else ''
            lt_penyerahan_plat = str(res[39]) if res[39] != None else ''
            tgl_penyerahan_bpkb = datetime.strptime(res[40], "%Y-%m-%d").date() if res[40] != None else ''
            lt_penyerahan_bpkb = str(res[41]) if res[41] != None else ''
            tgl_so=res[0]
            no_so=res[42]
            mobile=res[43]
            branch_code = res[44]
            branch_name = res[45]
            area = res[46]
            
            # Request HO Admin 03082020
            bulan_so = res[47]
            tahun_so = res[48]
            main_dealer = res[49]
            nama_finco = res[50]
            nama_penerima_bpkb = res[51]
            tgl_bayar_prbj = res[52]

            no += 1         
          
            worksheet.write('A%s' % row, no , wbf['content_number'])                    
            worksheet.write('B%s' % row, branch_code , wbf['content'])
            worksheet.write('C%s' % row, branch_name , wbf['content'])
            worksheet.write('D%s' % row, area , wbf['content'])
            
            worksheet.write('E%s' % row, no_engine , wbf['content'])
            worksheet.write('F%s' % row, no_chassis , wbf['content'])
            worksheet.write('G%s' % row, code_customer , wbf['content'])
            worksheet.write('H%s' % row, customer_name , wbf['content'])
            worksheet.write('I%s' % row, code_an_stnk , wbf['content'])
            worksheet.write('J%s' % row, an_stnk_name , wbf['content'])
            worksheet.write('K%s' % row, tgl_mohon_faktur , wbf['content_date'])  
            worksheet.write('L%s' % row, lt_mohon_faktur, wbf['content'])
            worksheet.write('M%s' % row, tgl_terima_faktur , wbf['content_date'])
            worksheet.write('N%s' % row, tgl_cetak_faktur , wbf['content_date'])
            worksheet.write('O%s' % row, no_faktur , wbf['content'])
            worksheet.write('P%s' % row, lt_terima_faktur , wbf['content'])
            worksheet.write('Q%s' % row, tgl_proses_stnk , wbf['content_date'])
            worksheet.write('R%s' % row, birojasa , wbf['content'])
            worksheet.write('S%s' % row, lt_proses_stnk , wbf['content'])
            worksheet.write('T%s' % row, tgl_tagihan_birojasa, wbf['content_date']) 
            worksheet.write('U%s' % row, lt_tagihan_birojasa , wbf['content']) 
            worksheet.write('V%s' % row, tgl_terima_notice , wbf['content_date']) 
            worksheet.write('W%s' % row, no_notice , wbf['content']) 
            worksheet.write('X%s' % row, tgl_jtp_notice , wbf['content_date'])
            worksheet.write('Y%s' % row, lt_terima_notice , wbf['content'])
            worksheet.write('Z%s' % row, tgl_terima_stnk , wbf['content_date'])
            worksheet.write('AA%s' % row, no_stnk , wbf['content'])
            worksheet.write('AB%s' % row, tgl_jtp_stnk , wbf['content_date'])
            worksheet.write('AC%s' % row, lt_terima_stnk , wbf['content'])
            
            worksheet.write('AD%s' % row, tgl_terima_plat , wbf['content_date'])                    
            worksheet.write('AE%s' % row, no_plat , wbf['content'])
            worksheet.write('AF%s' % row, lt_terima_plat , wbf['content'])
            worksheet.write('AG%s' % row, tgl_terima_bpkb , wbf['content_date'])
            worksheet.write('AH%s' % row, no_bpkb , wbf['content'])
            worksheet.write('AI%s' % row, tgl_jadi_bpkb , wbf['content_date'])
            worksheet.write('AJ%s' % row, no_urut , wbf['content'])
            worksheet.write('AK%s' % row, lt_terima_bpkb , wbf['content'])  
            worksheet.write('AL%s' % row, tgl_penyerahan_notice , wbf['content_date'])
            worksheet.write('AM%s' % row, lt_penyerahan_notice , wbf['content'])
            worksheet.write('AN%s' % row, tgl_penyerahan_stnk , wbf['content_date'])
            worksheet.write('AO%s' % row, lt_penyerahan_stnk , wbf['content'])
            worksheet.write('AP%s' % row, tgl_penyerahan_plat , wbf['content_date'])
            worksheet.write('AQ%s' % row, lt_penyerahan_plat , wbf['content'])
            worksheet.write('AR%s' % row, tgl_penyerahan_bpkb , wbf['content_date'])
            worksheet.write('AS%s' % row, lt_penyerahan_bpkb , wbf['content'])        
            worksheet.write('AT%s' % row, tgl_so , wbf['content'])     
            worksheet.write('AU%s' % row, no_so , wbf['content'])   
            worksheet.write('AV%s' % row, mobile , wbf['content'])
            # Request HO Admin 03082020
            worksheet.write('AW%s' % row, bulan_so , wbf['content'])
            worksheet.write('AX%s' % row, tahun_so , wbf['content'])
            worksheet.write('AY%s' % row, main_dealer , wbf['content'])
            worksheet.write('AZ%s' % row, nama_finco , wbf['content'])
            worksheet.write('BA%s' % row, nama_penerima_bpkb , wbf['content'])
            worksheet.write('BB%s' % row, tgl_bayar_prbj , wbf['content'])
            row+=1
            
        worksheet.autofilter('A6:BB%s' % (row))  
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