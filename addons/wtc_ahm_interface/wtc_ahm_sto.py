import time
import base64
from datetime import datetime, timedelta
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
import pytz 
import os

class Eksport_file_ahm_sto(osv.osv_memory):
    _name = "eksport.ahm.sto"
    _columns = {
                'name': fields.char('File Name', 35),
                'data_file': fields.binary('File'),
                'date_start':fields.date(string="Start Date"),
                'date_end':fields.date(string="End Date")
                }   
    
    def _get_default(self,cr,uid,date=False,user=False,context=None):
        if date :
            return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)
        else :
            return self.pool.get('res.users').browse(cr, uid, uid)
    
    def export_file(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids)[0]
        
        trx_id = context.get('active_id',False) 
        trx_obj = self.pool.get('sale.order').browse(cr,uid,trx_id,context=context)
        result = self.eksport_distribution(cr, uid, ids, trx_obj,context)
        form_id  = 'view.wizard.eksport.ahm.sto'
 
        view_id = self.pool.get('ir.ui.view').search(cr,uid,[                                     
                                                             ("name", "=", form_id), 
                                                             ("model", "=", 'eksport.ahm.sto'),
                                                             ])
      
      
        return {
            'name' : _('Export File'),
            'view_type': 'form',
            'view_id' : view_id,
            'view_mode': 'form',
            'res_id': ids[0],
            'res_model': 'eksport.ahm.sto',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True,
            'context': context
        }
        
    def eksport_distribution(self, cr, uid, ids,trx_obj, context=None):
        val = self.browse(cr, uid, ids)[0]
        date= self._get_default(cr, uid, date=True, context=context)
        date_str = str(date.strftime("%d%m%Y"))
        
        query = """
            select 'H2Z  '                                                              --kode main dealer
            || '%s'     """ % date_str + """                                            --tanggal stock dilaporkan
            || left(t.name || '                         ', 25)                          --part number
            || left(trim(to_char(SUM(q.qty),'9999999999'),' ') || '          ', 10)     --qty stock
            || left(trim(to_char(ppb.cost,'9999999999'), ' ') || '          ', 10)      --harga pokok
            || left(trim(to_char(t.list_price, '9999999999'), ' ') || '          ', 10) --harga jual

            from stock_quant q
            INNER JOIN stock_location l ON q.location_id = l.id AND l.usage = 'internal'
            LEFT JOIN (select a.quant_id, max(a.move_id) as move_id from stock_quant_move_rel a 
            inner join stock_move b on a.move_id = b.id where b.state = 'done' group by a.quant_id) qm ON q.id = qm.quant_id
            LEFT JOIN wtc_branch b ON l.branch_id = b.id
            LEFT JOIN stock_move m ON qm.move_id = m.id
            LEFT JOIN stock_picking sp ON m.picking_id = sp.id
            LEFT JOIN product_product p ON q.product_id = p.id
            LEFT JOIN product_template t ON p.product_tmpl_id = t.id
            LEFT JOIN product_category c ON t.categ_id = c.id 
            LEFT JOIN product_category c2 ON c.parent_id = c2.id 
            LEFT JOIN product_price_branch ppb ON ppb.product_id = q.product_id and ppb.warehouse_id = l.warehouse_id and q.consolidated_date is not null
            WHERE 1=1 and (c.name = 'Sparepart' or c2.name = 'Sparepart') AND  b.code='MML' 
            and c.name NOT ILIKE 'NONHGP%'
            group by t.name, ppb.cost, t.list_price
            """
        
        cr.execute(query)
        
        picks = cr.fetchall()
        filename=time.strftime('H2Z%d%m.STO')
        
        result = '' 
        for x in picks:
            if str(x[0]) != 'None':   
                result += str(x[0])
                result += '\r\n';
        out = base64.encodestring(result)
        distribution = self.write(cr, uid, ids, {'data_file':out, 'name': filename}, context=context)

    def eksport_auto_distribution(self, cr, uid, ids):
        print '>>>> Ready to generate STO <<<<<<<<<<'
        date= self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=None)
        
        # date_start = str(date.strftime("%Y-%m-%d"))
        # date_end = str(date.strftime("%Y-%m-%d"))
        date_str = str(date.strftime("%d%m%Y"))

        query = """
            select 'H2Z  '                                                              --kode main dealer
            || '%s'     """ % date_str + """                                            --tanggal stock dilaporkan
            || left(t.name || '                         ', 25)                          --part number
            || left(trim(to_char(SUM(q.qty),'9999999999'),' ') || '          ', 10)     --qty stock
            || left(trim(to_char(ppb.cost,'9999999999'), ' ') || '          ', 10)      --harga pokok
            || left(trim(to_char(t.list_price, '9999999999'), ' ') || '          ', 10) --harga jual

            from stock_quant q
            INNER JOIN stock_location l ON q.location_id = l.id AND l.usage = 'internal'
            LEFT JOIN (select a.quant_id, max(a.move_id) as move_id from stock_quant_move_rel a 
            inner join stock_move b on a.move_id = b.id where b.state = 'done' group by a.quant_id) qm ON q.id = qm.quant_id
            LEFT JOIN wtc_branch b ON l.branch_id = b.id
            LEFT JOIN stock_move m ON qm.move_id = m.id
            LEFT JOIN stock_picking sp ON m.picking_id = sp.id
            LEFT JOIN product_product p ON q.product_id = p.id
            LEFT JOIN product_template t ON p.product_tmpl_id = t.id
            LEFT JOIN product_category c ON t.categ_id = c.id 
            LEFT JOIN product_category c2 ON c.parent_id = c2.id 
            LEFT JOIN product_price_branch ppb ON ppb.product_id = q.product_id and ppb.warehouse_id = l.warehouse_id and q.consolidated_date is not null
            WHERE 1=1 and (c.name = 'Sparepart' or c2.name = 'Sparepart') AND  b.code='MML' 
            and c.name NOT ILIKE 'NONHGP%'
            group by t.name, ppb.cost, t.list_price
            """
        
        cr.execute(query)
        
        picks = cr.fetchall()
        filename=time.strftime('H2Z%d%m.STO')
        result = '' 
        if picks:
            for x in picks:
                if str(x[0]) != 'None':   
                    result += str(x[0])
                    result += '\n';
        # out = base64.encodestring(result)
        # distribution = self.write(cr, uid, ids, {'data_file':out, 'name': filename}, context=context)
            file = open(os.path.dirname(os.path.abspath(__file__))+'/static/'+filename,'w+')
            file.write(result)
            