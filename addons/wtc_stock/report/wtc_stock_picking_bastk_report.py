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
            'nama_konsumen': self.nama_konsumen,
            'creator':self.creator,
            'nama_adh':self.nama_adh,
            'print_by':self.print_by,
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
    
    def nama_konsumen(self):
        obj_packing = self.pool.get('wtc.stock.packing').browse(self.cr, self.uid, self.ids).rel_origin
        invoice2 = self.pool.get('dealer.sale.order').search(self.cr, self.uid,[ ('name','=',obj_packing) ])
        name_nya = self.pool.get('dealer.sale.order').browse(self.cr, self.uid, invoice2)
        return name_nya
    
    def creator(self):
        packing = self.pool.get('wtc.stock.packing').browse(self.cr, self.uid, self.ids)
        return packing
    
    def print_by(self):
        user = self.pool.get('res.users').browse(self.cr, self.uid, self.uid)
        return user.name
    
    def nama_adh(self):
        branch_id = self.pool.get('wtc.stock.packing').browse(self.cr, self.uid, self.ids).rel_branch_id.id
        emp = self.pool.get('hr.employee').search(self.cr,self.uid,[
            ('branch_id','=',branch_id),
            ('job_id.name','=','ADMINISTRATION HEAD'),
            ('tgl_keluar','=',False)],limit=1)
        adh = self.pool.get('hr.employee').browse(self.cr, self.uid, emp).name
        return adh
    
# report_sxw.report_sxw('report.rml.wtc.stock.picking.bastk', 'wtc.stock.packing', 'addons/wtc_stock/report/wtc_stock_picking_bastk_report.rml', parser = wtc_stock_packing, header = False)
class report_wtc_picking_bastk_report(osv.AbstractModel):
    _name = 'report.wtc_stock.wtc_picking_bastk_report'
    _inherit = 'report.abstract_report'
    _template = 'wtc_stock.wtc_picking_bastk_report'
    _wrapped_report_class = wtc_stock_packing