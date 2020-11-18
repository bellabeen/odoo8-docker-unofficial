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
# csv
import itertools
import csv
import codecs
from openerp.osv import orm, fields

# csv
class AccountUnicodeWriter(object):

    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = StringIO()
        # created a writer with Excel formating settings
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        row = (x or u'' for x in row)

        encoded_row = [
            c.encode("utf-8") if isinstance(c, unicode) else c for c in row]

        self.writer.writerow(encoded_row)
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        data = self.encoder.encode(data)
        self.stream.write(data)
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)
# akhircsv


class teds_generate_invoice(osv.osv_memory):
    _name = "teds.generate.invoice"
    _description = "Generate Invoice"

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
   
    _columns = {

        'state_x': fields.selection( ( ('choose','choose'),('get','get'))), #xls
        'data_x': fields.binary('File', readonly=True),
        'name': fields.char('Filename', 100, readonly=True),
        'division': fields.selection([('Unit','Unit'),('Sparepart','Sparepart')], 'Division', required=True, change_default=True, select=True),
        'start_date':fields.date('Start Date',required=1),
        'end_date':fields.date('End Date',required=1),
     
       
    }

    _defaults = {
        'state_x': lambda *a: 'choose',
        'option': 'h1',
        # 'options': lambda *a: 'stock',
        # 'location_status': lambda *a: 'all',
      
    }
    


    def csv_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
            
        data = self.read(cr, uid, ids,context=context)[0]
        # if len(data['branch_ids']) == 0 :
        #     data.update({'branch_ids': self._get_branch_ids(cr, uid, context)})
        if data['division'] == 'Sparepart' :
            self._print_csv_export_invoice(cr, uid, ids, data, context=context)
        else :
            self._print_csv_export_invoice_unit(cr, uid,ids,data,context=context)
      
      
        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'teds_generate_invoice', 'view_generate_invoice')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download .txt'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.generate.invoice',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }
       

    def _print_csv_export_invoice(self, cr, uid, ids, data, context=None):
        
        data = self.read(cr, uid, ids,context=context)[0]
        this = self.browse(cr, uid, ids)[0]
        rows = self._get_rows_invoice(cr, uid, ids, data, context)       
        file_data = StringIO()
        try:
            writer = AccountUnicodeWriter(file_data)
            writer.writerows(rows)
            file_value = file_data.getvalue()
            out=base64.encodestring(file_value)
            filename = 'Export Invoice Sparepart'
            self.write(cr, uid, ids,
                       {'state_x':'get', 'data_x':out, 'name': filename +".txt"},
                       context=context)
        finally:
            file_data.close()



    def _print_csv_export_invoice_unit(self, cr, uid, ids, data, context=None):
        
        data = self.read(cr, uid, ids,context=context)[0]
        this = self.browse(cr, uid, ids)[0]
        rows = self._get_rows_invoice_unit(cr, uid, ids, data, context)       
        file_data = StringIO()
        try:
            writer = AccountUnicodeWriter(file_data)
            writer.writerows(rows)
            file_value = file_data.getvalue()
            out=base64.encodestring(file_value)
            filename = 'Export Invoice Unit'
            self.write(cr, uid, ids,
                       {'state_x':'get', 'data_x':out, 'name': filename +".txt"},
                       context=context)
        finally:
            file_data.close()


   


teds_generate_invoice()
