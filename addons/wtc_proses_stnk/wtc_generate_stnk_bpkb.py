import time
import base64
from datetime import datetime, timedelta
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
import pytz 


class Eksport_file_stnk_bpkb(osv.osv_memory):
    _name = "eksport.stnk.bpkb"
    _columns = {
                'name': fields.char('File Name', 35),
                'data_file': fields.binary('File'),
                'date_start':fields.date(string="Start Date",required=True),
                'date_end':fields.date(string="End Date",required=True)
                }   
    
    def export_file(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids)[0]
        trx_id = context.get('active_id',False) 
        trx_obj = self.pool.get('wtc.penerimaan.stnk').browse(cr,uid,trx_id,context=context)
        result = self.eksport_distribution(cr, uid, ids, trx_obj,context)
        form_id  = 'view.wizard.eksport.stnk.bpkb'
 
        view_id = self.pool.get('ir.ui.view').search(cr,uid,[                                     
                                                             ("name", "=", form_id), 
                                                             ("model", "=", 'eksport.stnk.bpkb'),
                                                             ])
     
        return {
            'name' : _('Export File'),
            'view_type': 'form',
            'view_id' : view_id,
            'view_mode': 'form',
            'res_id': ids[0],
            'res_model': 'eksport.stnk.bpkb',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True,
            'context': context
        }
        
    def eksport_distribution(self, cr, uid, ids,trx_obj, context=None):
        result = '' 
        val = self.browse(cr, uid, ids)[0]
        cr.execute(''' SELECT
                a.name,chassis_no,
                tgl_terima_notice,no_notice,tgl_terima_no_polisi,
                no_polisi,tgl_terima_stnk,no_stnk,tgl_terima_bpkb,
                no_bpkb,
                tgl_penyerahan_stnk,
                tgl_penyerahan_bpkb,
                b.code
                from stock_production_lot as a
                LEFT JOIN wtc_branch as b on a.branch_id=b.id
                where tgl_proses_stnk >=%s
                and tgl_proses_stnk >=%s
                and b.default_supplier_id=3837
            ''',(val.date_start,val.date_end))
        picks = cr.fetchall()
        tangal=time.strftime('%d%m%Y')
        nama = tangal+'.txt'
        for x in picks:
            result += str(x[0])+';'+str(x[1])+';'+str(x[2])+';'+str(x[3])+';'+str(x[4])+';'+str(x[5])+';'+str(x[6])+';'+str(x[7])+';'+str(x[8])+';'+str(x[9])+';'+str(x[10])+';'+str(x[11])+';'+str(x[12])
            result += '\n';
        out = base64.encodestring(result)
        distribution = self.write(cr, uid, ids, {'data_file':out, 'name': nama}, context=context)
