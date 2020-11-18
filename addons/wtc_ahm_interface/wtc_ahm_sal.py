import time
import base64
from datetime import datetime, timedelta
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
import pytz 
import os

class Eksport_file_ahm_sal(osv.osv_memory):
    _name = "eksport.ahm.sal"
    _columns = {
                'name': fields.char('File Name', 35),
                'data_file': fields.binary('File'),
                'date_start':fields.date(string="Start Date" ),
                'date_end':fields.date(string="End Date" )
                }   
    
    def export_file(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids)[0]
        trx_id = context.get('active_id',False) 
        trx_obj = self.pool.get('sale.order').browse(cr,uid,trx_id,context=context)
        result = self.eksport_distribution(cr, uid, ids, trx_obj,context)
        form_id  = 'view.wizard.eksport.ahm.sal'
 
        view_id = self.pool.get('ir.ui.view').search(cr,uid,[                                     
                                                             ("name", "=", form_id), 
                                                             ("model", "=", 'eksport.ahm.sal'),
                                                             ])
        # print">>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<",view_id
     
        return {
            'name' : _('Export File'),
            'view_type': 'form',
            'view_id' : view_id,
            'view_mode': 'form',
            'res_id': ids[0],
            'res_model': 'eksport.ahm.sal',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True,
            'context': context
        }
   
    def get_query(self,cr,uid,ids,date_start,date_end):
        query = """ 
            (SELECT LEFT(b.ahm_code || '     ', 5)  --- kode main dealer
            || left(inv.number || '                              ', 30)  ---NO FAKTUR
            || left(TO_CHAR((inv.date_invoice + INTERVAL '7 hours'), 'DDMMYYYY HH24MISS') || '                    ',20) ---TANGGAL FAKTUR
            || left(COALESCE(rp.ahm_code, 'NONCH') || '     ', 5)  ---KODE DEALER
            || left(spick.picking_name || '               ', 15)  ---NO PICKING SHEET
            || left(so.name || '                              ', 30)  ---NOMOR PO DEAELR
            || left(p.name_template || '                         ', 25)  ---PRODUCT
            || right('          ' || invl.quantity || '', 10)  ---QTY
            || right('               ' || invl.quantity * invl.price_unit || '', 15)  ---QTY 
            || right('               ' || ROUND(invl.price_subtotal * 1.1, 2) || '', 15)  ---QTY 
            || right('               '|| ROUND(cast(invl.force_cogs * invl.quantity as numeric), 2) || '', 15)  ---QTY
            FROM account_invoice inv
            INNER JOIN account_invoice_line invl on invl.invoice_id=inv.id
            INNER JOIN sale_order so on so.id=inv.transaction_id AND inv.model_id IN (SELECT id FROM ir_model WHERE model = 'sale.order')
            INNER JOIN wtc_stock_distribution sd on sd.id=so.distribution_id
            INNER JOIN wtc_branch b ON sd.branch_id = b.id
            INNER JOIN product_product as p ON invl.product_id=p.id
            INNER JOIN product_template pt ON p.product_tmpl_id = pt.id
            INNER JOIN product_category pc ON pt.categ_id = pc.id 
            LEFT JOIN res_partner rp on rp.id=sd.dealer_id
            LEFT JOIN (SELECT transaction_id, MIN(name) as picking_name
                FROM stock_picking
                WHERE model_id IN (SELECT id FROM ir_model WHERE model = 'sale.order')
                GROUP BY transaction_id) spick ON inv.transaction_id = spick.transaction_id
            WHERE inv.state IN ('open','paid') 
            AND pc.name NOT ILIKE 'NONHGP%%'
            AND inv.date_invoice BETWEEN '%s' and '%s'
            and sd.division='Sparepart'
            AND b.branch_type = 'MD'
            AND invl.quantity > 0
            AND rp.default_code not in ('CKL','CV.TEKNIK','DPP','OTOMAX(UMUM)','U0002','U0003','U0005','U0006','U0009','UMUM') 
            ORDER BY inv.date_invoice ASC, inv.number, p.name_template)
            UNION ALL
            (SELECT LEFT(branch.ahm_code || '     ', 5)  --- kode main dealer
            || left(mo.name || '                              ', 30)  ---NO FAKTUR
            || left(TO_CHAR((mo.confirm_date + INTERVAL '7 hours'), 'DDMMYYYY HH24MISS') || '                    ',20) ---TANGGAL FAKTUR
            || left(COALESCE(rp.ahm_code, 'NONCH') || '     ', 5)  ---KODE DEALER
            || left(sp.picking_name || '               ', 15)  ---NO PICKING SHEET
            || left(mo.name || '                              ', 30)  ---NOMOR PO DEAELR
            || left(p.name_template || '                         ', 25)  ---PRODUCT
            || right('          ' || mol.qty || '', 10)  ---QTY
            || right('               ' || mol.qty * mol.unit_price || '', 15)  ---QTY 
            || right('               ' || ROUND(cast((((mol.unit_price )-(mol.unit_price* ((0)/100)))*mol.qty)/1.1 as numeric),2) || '', 15)  ---QTY 
            || right('               '|| ROUND(cast(ppb.cost * mol.qty as numeric), 2) || '', 15)  ---QTY
            from wtc_mutation_order mo 
            INNER JOIN wtc_mutation_order_line mol on mol.order_id=mo.id
            INNER JOIN wtc_stock_distribution sd on sd.id=mo.distribution_id
            INNER JOIN (SELECT transaction_id, MIN(spick.name) as picking_name
                FROM stock_picking spick
                INNER JOIN stock_picking_type spt ON spick.picking_type_id = spt.id AND spt.code IN ('interbranch_out', 'outgoing')
                WHERE model_id IN (SELECT id FROM ir_model WHERE model = 'wtc.mutation.order')
                GROUP BY transaction_id) sp ON mo.id = sp.transaction_id --2
            INNER JOIN product_product as p ON p.id=mol.product_id
            INNER JOIN product_template pt ON p.product_tmpl_id = pt.id
            INNER JOIN product_category pc ON pt.categ_id = pc.id 
            INNER JOIN wtc_branch branch on branch.id=mo.branch_id
            INNER JOIN wtc_branch cab on cab.id=mo.branch_requester_id
            INNER JOIN res_partner rp on rp.id = sd.dealer_id --3
            INNER JOIN product_price_branch ppb on ppb.product_id=p.id AND ppb.warehouse_id = branch.warehouse_id
            where mo.division='Sparepart' and mo.state in ('confirm','done') 
            and mol.qty > 0
            AND pc.name NOT ILIKE 'NONHGP%%'
            and mo.confirm_date + INTERVAL '7 hours' BETWEEN '%s 00:00:00' and '%s 23:59:59'
            AND rp.default_code not in ('DLL') 
            AND branch.branch_type = 'MD')
            """ 
        # print '>>>>',query
        # asd
        cr.execute(query % (date_start,date_end,date_start,date_end))
        picks = cr.fetchall()

        result = '' 
        if picks:
            for x in picks:
                result += str(x[0])
                result += '\r\n';
            
        filename=result[:3]+time.strftime('%d%m.SAL')

        return result, filename
        
    def eksport_distribution(self, cr, uid, ids,trx_obj, context=None):
        val = self.browse(cr, uid, ids)[0]
        date_start = str(val.date_start)
        date_end = str(val.date_end)

        result, filename = self.get_query(cr, uid, ids, date_start, date_end)
        
        out = base64.encodestring(result)
        distribution = self.write(cr, uid, ids, {'data_file':out, 'name': filename}, context=context)

    def eksport_auto_distribution(self, cr, uid, ids, context=None):
        date= self.pool.get('wtc.branch').get_default_date(cr,uid,ids).date()
        date = str(date.strftime("%Y-%m-%d"))
        # date ='2015-08-20'
        result, filename = self.get_query(cr, uid, ids, date, date)
        
        file = open(os.path.dirname(os.path.abspath(__file__))+'/static/'+filename,'w+')
        file.write(result)
