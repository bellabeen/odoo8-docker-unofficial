import time
from datetime import datetime
from openerp.report import report_sxw
from openerp.osv import osv
from openerp import pooler
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
import pytz 
from openerp.tools.translate import _
import base64

class wtc_stock_packing(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(wtc_stock_packing, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'no_urut': self.no_urut,
            'waktu_local': self.waktu_local,
            'serial_number_ids' : self.serial_number_ids,
            'in_date': self.get_in_date,
            'loc_name': self.get_location_name
        })
        self.no = 0
    def no_urut(self):
        self.no+=1
        return self.no
    
    def waktu_local(self):
        tanggal = datetime.now().strftime('%y%m%d')
        menit = datetime.now()
        user = self.pool.get('res.users').browse(self.cr, self.uid, self.uid)
        tz = pytz.timezone(user.tz) if user.tz else pytz.utc
        start = pytz.utc.localize(menit).astimezone(tz)
        start_date = start.strftime("%d-%m-%Y %H:%M")
        return start_date
    
    def get_in_date(self, id_lot):
        quant_id = self.pool.get('stock.quant').browse(self.cr, self.uid, id_lot)
        return quant_id.in_date
    
    def get_location_name(self, location_id):
        name_get = location_id.name_get()
        loc_name = name_get[0][1]
        return loc_name
    
    def serial_number_ids(self):
        packing_id = self.pool.get('wtc.stock.packing').browse(self.cr, self.uid, self.ids)
        ids_serial_number = packing_id.get_lot_available_md()
        serial_number_ids = self.pool.get('stock.production.lot').browse(self.cr, self.uid, ids_serial_number)
        return serial_number_ids
    
report_sxw.report_sxw('report.rml.print.surat.jalan', 'wtc.stock.packing', 'addons/wtc_stock/report/wtc_print_serial_number.rml', parser = wtc_stock_packing, header = False)
