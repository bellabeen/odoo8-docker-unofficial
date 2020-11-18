import time
import base64
from datetime import datetime, timedelta
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
import pytz 
import tempfile
import os

class Eksport_file_ahm_pod(osv.osv_memory):
    _name = "eksport.ahm.pod"
    _columns = {
                'name': fields.char('File Name', 35),
                'data_file': fields.binary('File'),
                'date_start':fields.date(string="Start Date"),
                'date_end':fields.date(string="End Date")
                }   
    
    def export_file(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids)[0]
        trx_id = context.get('active_id',False) 
        trx_obj = self.pool.get('sale.order').browse(cr,uid,trx_id,context=context)
        result = self.eksport_distribution(cr, uid, ids, trx_obj,context)
        form_id  = 'view.wizard.eksport.ahm.pod'
 
        view_id = self.pool.get('ir.ui.view').search(cr,uid,[                                     
                                                             ("name", "=", form_id), 
                                                             ("model", "=", 'eksport.ahm.pod'),
                                                             ])
     
        return {
            'name' : _('Export File'),
            'view_type': 'form',
            'view_id' : view_id,
            'view_mode': 'form',
            'res_id': ids[0],
            'res_model': 'eksport.ahm.pod',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True,
            'context': context
        }

    def get_query(self,cr,uid,ids,date_start,date_end):
        result = '' 
        # val = self.browse(cr, uid, ids)[0]
        query = """
            (SELECT left(b.ahm_code || '     ', 5)  --- kode main dealer   
            || left(coalesce(rp.ahm_code,'NONCH')  || '     ', 5)  ---KODE DEALER 
            || left(so.name || '                              ', 30)  ---NOMOR PO DEAELR   
            || left(TO_CHAR((app.approve_date + INTERVAL '7 hours'), 'DDMMYYYY HH24MISS') || '                    ',20) ---TANGGAL FAKTUR      
            || left(p.name_template      || '                         ', 25)  ---PRODUCT
            || right('          '||sol.product_uom_qty || '', 10)  ---QTY\    
            || CASE UPPER(pot.name) WHEN 'HOTLINE' THEN 'H' ELSE 'R' END        
            FROM sale_order so
            INNER JOIN sale_order_line sol ON so.id = sol.order_id
            INNER JOIN wtc_stock_distribution sd on sd.id=so.distribution_id
            INNER JOIN wtc_branch b ON sd.branch_id = b.id
            INNER JOIN product_product as p ON sol.product_id=p.id
            INNER JOIN product_template pt ON p.product_tmpl_id = pt.id
            INNER JOIN product_category pc ON pt.categ_id = pc.id 
            LEFT JOIN res_partner rp on rp.id=sd.dealer_id
            LEFT JOIN wtc_purchase_order_type pot ON sd.type_id = pot.id        
            LEFT JOIN (SELECT transaction_id, MAX(tanggal) as approve_date
            	FROM wtc_approval_line al 
            	WHERE form_id IN (SELECT id FROM ir_model WHERE model = 'sale.order')
            	GROUP BY transaction_id) app ON so.id = app.transaction_id
            WHERE app.approve_date + INTERVAL '7 hours' BETWEEN '%s 00:00:00' AND '%s 23:59:59'     
            AND so.state IN ('approved', 'progress', 'done')
            AND so.division = 'Sparepart'
            AND b.branch_type = 'MD'
            AND sol.product_uom_qty > 0
            AND pc.name NOT ILIKE 'NONHGP%%'
            AND rp.default_code not in ('CKL','CV.TEKNIK','DPP','OTOMAX(UMUM)','U0002','U0003','U0005','U0006','U0009','UMUM') 
            ORDER BY app.approve_date ASC, so.name, p.name_template)
            UNION ALL
            (SELECT left(b.ahm_code || '     ', 5)  --- kode main dealer   
            || left(coalesce(rp.ahm_code,'NONCH')  || '     ', 5)  ---KODE DEALER 
            || left(mo.name || '                              ', 30)  ---NOMOR PO DEAELR   
            || left(TO_CHAR((mo.confirm_date + INTERVAL '7 hours'), 'DDMMYYYY HH24MISS') || '                    ',20) ---TANGGAL FAKTUR      
            || left(p.name_template      || '                         ', 25)  ---PRODUCT
            || right('          '||mol.qty || '', 10)  ---QTY\    
            || CASE UPPER(pot.name) WHEN 'HOTLINE' THEN 'H' ELSE 'R' END        
            FROM wtc_mutation_order mo 
            INNER JOIN wtc_mutation_order_line mol on mol.order_id=mo.id
            INNER JOIN wtc_stock_distribution sd on sd.id=mo.distribution_id
            INNER JOIN product_product as p ON p.id=mol.product_id
            INNER JOIN product_template pt ON p.product_tmpl_id = pt.id
            INNER JOIN product_category pc ON pt.categ_id = pc.id 
            INNER JOIN wtc_branch b on b.id=mo.branch_id
            INNER JOIN res_partner rp on rp.id = sd.dealer_id --3
            LEFT JOIN wtc_purchase_order_type pot ON sd.type_id = pot.id        
            where mo.division='Sparepart' and mo.state in ('confirm','done') 
            and mol.qty > 0
            AND pc.name NOT ILIKE 'NONHGP%%'
            and mo.confirm_date + INTERVAL '7 hours' BETWEEN '%s 00:00:00' and '%s 23:59:59'
            AND b.branch_type = 'MD'
            AND rp.default_code not in ('DLL') 
            ORDER BY mo.confirm_date ASC, mo.name, p.name_template)
        """
        # print '>>>>',query
        # asd
        cr.execute(query % (date_start, date_end, date_start, date_end))
        picks = cr.fetchall()

        result = '' 
        for x in picks:
            if str(x[0]) != 'None':   
                result += str(x[0])
                result += '\r\n';

        filename=result[:3]+time.strftime('%d%m.POD')

        return result, filename
        
    def eksport_distribution(self, cr, uid, ids,trx_obj, context=None):
        val = self.browse(cr, uid, ids)[0]
        date_start = str(val.date_start)
        date_end = str(val.date_end)

        result, filename = self.get_query(cr, uid, ids, date_start, date_end)
        
        out = base64.encodestring(result)
        distribution = self.write(cr, uid, ids, {'data_file':out, 'name': filename}, context=context)

    def eksport_auto_distribution(self, cr, uid, ids, context=None):
        date= self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=None)
        date = str(date.strftime("%Y-%m-%d"))
        # date ='2015-08-20'
        result, filename = self.get_query(cr, uid, ids, date, date)
        
        file = open(os.path.dirname(os.path.abspath(__file__))+'/static/'+filename,'w+')
        file.write(result)
        