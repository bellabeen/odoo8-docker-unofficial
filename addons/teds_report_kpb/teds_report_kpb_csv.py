import itertools
import tempfile
from cStringIO import StringIO
import base64
import csv
import codecs
from openerp.osv import orm, fields
from openerp.tools.translate import _


class AccountCSVExport(orm.TransientModel):
    _inherit = "wtc.report.kpb"

    wbf = {}

    def _get_rows_account(self, cr, uid, ids,data, context=None):
        """
        Return list to generate rows of the CSV file
        """
       
        kpb = data['kpb']      
        start_date = data['start_date']
        end_date = data['end_date']
        branch_ids = data['branch_ids']
        jenis_oli = data['jenis_oli']
        state = data['state']

        
        tz = '7 hours'
        query_where = ""

        if branch_ids :
            query_where += " AND wo.branch_id in %s " % str(tuple(branch_ids)).replace(',)', ')') 
        if start_date :
            query_where += " AND wo.tanggal_pembelian >= '%s' " % (start_date)
        if end_date :
            query_where += " AND wo.tanggal_pembelian <= '%s' "  % (end_date)
        if jenis_oli :
            query_where += " and wo.jenis_oli = '%s' " %(jenis_oli)
        if kpb :
            query_where += " and wo.kpb_ke = '%s' " %(kpb)   
        if state :
            query_where += " and wo.state = '%s' " %(state) 
        query="""
                select wo.name as no_pkb,
                wb.ahass_code as ahass_code,
                stl.name as enggine,
                stl.chassis_no as chassis,
                rp.name as customer,
                wb.name as branch,
                wb.code as code,
                wo.kode_buku,
                wo.nama_buku,
                wo.tanggal_pembelian,
                wo.date,
                wo.kpb_ke,
                wo.km,
                wo.tipe_buku,
                wo.jenis_oli
                from wtc_work_order wo
                left join stock_production_lot stl ON wo.lot_id = stl.id 
                left join res_partner rp ON wo.customer_id = rp.id
                left join wtc_branch wb ON wo.branch_id = wb.id
                where wo.type='KPB'
                 %s
            """ %(query_where)
 
        cr.execute (query)
        res = cr.fetchall()

        rows = []

        for line in res:
            no_pkb            = str(line[0]) if line[0] != None else ''
            ahass_code        = str(line[1]) if line[1] != None else ''
            enggine           = str(line[2]) if line[2] != None else ''
            chassis           = str(line[3]).replace("MH1", "") if line[3] != None else '' 
            branch            = str(line[5]) if line[5] != None else ''
            jenis_dealer      = str(line[6]) if line[6] != None else ''
            kode_buku         = str(line[7]) if line[7] != None else ''
            # nama_buku         = str(line[8]) if line[8] != None else ''
            tanggal_pembelian = str(line[9]) if line[9] != None else ''
            tanggal_service   = str(line[10]) if line[10] != None else ''
            kpb_ke            = str(line[11]) if line[11] != None else ''
            km                = str(line[12]) if line[12] != None else ''
            tipe_buku         = str(line[13]) if line[13] != None else ''
            jenis_oli         = str(line[14]) if line[14] != None else ''

            hasil=no_pkb+";"+ahass_code+";"+enggine+";"+chassis+";"+line[4]+";"+branch+";"+jenis_dealer+";"+kode_buku+";"+tanggal_pembelian+";"+tanggal_service+";"+kpb_ke+";"+km+";"+tipe_buku+";"+jenis_oli
            rows.append(list(
              {
              hasil
              })
              )
        return rows






