import time
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from datetime import date, datetime, timedelta
from openerp import SUPERUSER_ID
import base64
import xlrd


class ImportAbsensiSales(osv.osv_memory):
    _name = "wtc.import.absensi.sales"
    _columns = {
                'name': fields.char('File Name', 16),
                'data_file': fields.binary('File'),
                }   
    def import_excel(self, cr, uid, ids, context=None):
        obj_absensi = self.pool.get('wtc.absensi.sales') 
        val = self.browse(cr, uid, ids)[0]
        data = base64.decodestring(val.data_file)
        excel = xlrd.open_workbook(file_contents = data)  
        sh = excel.sheet_by_index(0)  
        for rx in range(1,sh.nrows):  
            nip=[sh.cell(rx, ry).value for ry in range(sh.ncols)] [0]
            nip = str(nip).replace(' ', '').upper()
            bulan=[sh.cell(rx, ry).value for ry in range(sh.ncols)] [1]
            total_absensi=[sh.cell(rx, ry).value for ry in range(sh.ncols)] [2]
            jumlah_hari_kerja=[sh.cell(rx, ry).value for ry in range(sh.ncols)] [3]
            sp=[sh.cell(rx, ry).value for ry in range(sh.ncols)] [4]
    
            check_obj_absensi=obj_absensi.search(cr, uid,[('nip','=',nip),('bulan','=',bulan)])
            if not check_obj_absensi :       
                absensi = {
                    'nip':nip,
                    'bulan':bulan,
                    'total_absensi':total_absensi,
                    'jumlah_hari_kerja':jumlah_hari_kerja,
                    'sp':sp           
                }
                create=obj_absensi.create(cr,uid,absensi)
            else :
                #absensi_id=obj_absensi.browse(cr,uid,check_obj_absensi)
                obj_absensi.write(cr,uid,check_obj_absensi,{'total_absensi': total_absensi,'jumlah_hari_kerja':jumlah_hari_kerja,'sp':sp}, context=context)
        return True