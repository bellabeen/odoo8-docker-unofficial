import time
import base64
from datetime import datetime, timedelta
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
import pytz 
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp.sql_db import db_connect
from openerp.tools.config import config

class Eksport_file_permata(osv.osv_memory):
    _name = "eksport.permata"
    
    def _get_default_date(self,cr,uid,context=None):
        return self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context)
        
    _columns = {
                'name': fields.char('File Name', 35),
                'data_file': fields.binary('File'),
                'per_date':fields.date(string="Per Date",required=True)
                }   
    
    def export_file(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids)[0]
        if val.per_date >= self._get_default_date(cr, uid).strftime('%Y-%m-%d') :
            raise except_orm(_('Warning!'), _('hanya bisa generate df sebelum hari ini  !'))
            
        trx_id = context.get('active_id',False) 
        trx_obj = self.pool.get('account.invoice').browse(cr,uid,trx_id,context=context)
        result = self.eksport_distribution(cr, uid, ids, trx_obj,context)
        form_id  = 'view.wizard.eksport.permata'
 
        view_id = self.pool.get('ir.ui.view').search(cr,uid,[                                     
                                                             ("name", "=", form_id), 
                                                             ("model", "=", 'eksport.permata'),
                                                             ])
     
        return {
            'name' : _('Export File'),
            'view_type': 'form',
            'view_id' : view_id,
            'view_mode': 'form',
            'res_id': ids[0],
            'res_model': 'eksport.permata',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True,
            'context': context
        }
        
    def eksport_distribution(self, cr, uid, ids,trx_obj, context=None):
        result = '' 
        val = self.browse(cr, uid, ids)[0]
        conn_str = 'postgresql://' \
           + config.get('report_db_user', False) + ':' \
           + config.get('report_db_password', False) + '@' \
           + config.get('report_db_host', False) + ':' \
           + config.get('report_db_port', False) + '/' \
           + config.get('report_db_name', False)
        conn = db_connect(conn_str, True)
        cur = conn.cursor(False)
        cur.autocommit(True)
        cur.execute('''
                 select '40  ' || 
                right(replace(inv.number, '/', ''),7) as prefix, 
                --sequence 3 digit--
                to_char(date_order + interval '7 hours', 'MMDDYYYY') || 
                '                     ' || 
                right(replace(inv.number, '/', ''),7) ||
                case when (date_order + interval '7 hours') + COALESCE(term_line.days,0) * interval '1 day' < %s then %s
                else to_char((date_order + interval '7 hours') + COALESCE(term_line.days,0) * interval '1 day', 'MMDDYYYY') end || 
                '            ' || 
                to_char((date_order + interval '7 hours') + interval '45 days', 'MMDDYYYY') ||
                left(partner.default_code || '          ',10) || 
                left(partner.name || '                              ',30) || 
                left(coalesce(product.default_code,coalesce(product.name_template,'')) || '               ', 15) || 
                '                    ' || 
                left(pack_line.chassis_number || '                 ',17) ||
                left(pack_line.engine_number || '             ',13) || 
                left(COALESCE(pav.name,'') || '               ',15) ||
                left(sol.price_unit - (COALESCE(so.discount_cash,0) + COALESCE(so.discount_program,0) + COALESCE(so.discount_lain,0)) * 1.1 / solg.total_qty || '          ',10) as suffix
                from sale_order so
                inner join
                (select so.id as so_id, inv.id as inv_id, sum(quantity) as quantity 
                from sale_order so 
                inner join account_invoice inv on so.name = inv.origin and inv.type = 'out_invoice' and inv.state = 'open'
                inner join account_invoice_line invl on inv.id = invl.invoice_id 
                inner join (select move_id, max(reconcile_partial_id) as reconcile_partial_id, max(reconcile_id) as reconcile_id from account_move_line group by move_id) aml on inv.move_id = aml.move_id 
                where so.division = 'Unit' 
                and inv.date_invoice <= %s 
                and aml.reconcile_partial_id is null 
                and aml.reconcile_id is null 
                group by so.id, inv.id) inv_qty on so.id = inv_qty.so_id 
                inner join 
                (select so.id, so.name, max(pick.date_done) as date_done, sum(quantity) as quantity 
                from sale_order so 
                inner join stock_picking pick on so.name = pick.origin and pick.state = 'done' 
                inner join wtc_stock_packing pack on pick.id = pack.picking_id 
                inner join wtc_stock_packing_line pack_line on pack.id = pack_line.packing_id and pack_line.engine_number is not null 
                where so.division = 'Unit' 
                and pick.date_done <= to_timestamp(%s, 'YYYY-MM-DD HH24:MI:SS') + interval '7 hours' 
                group by so.id, so.name) sj_qty on so.id = sj_qty.id
                and inv_qty.quantity = sj_qty.quantity
                and sj_qty.date_done + interval '7 hours' between %s and %s
                inner join stock_picking pick on so.name = pick.origin and pick.state = 'done'
                inner join wtc_stock_packing pack on pick.id = pack.picking_id
                inner join wtc_stock_packing_line pack_line on pack.id = pack_line.packing_id and pack_line.engine_number is not null
                inner join stock_production_lot lot on lot.id = pack_line.serial_number_id
                inner join product_product product on product.id = pack_line.product_id
                left join sale_order_line sol on sol.order_id = so.id and sol.product_id = pack_line.product_id
                left join product_attribute_value_product_product_rel pavpp on product.id = pavpp.prod_id
                left join product_attribute_value pav on pavpp.att_id = pav.id
                left join wtc_branch b on so.branch_id = b.id
                left join res_partner partner on so.partner_id = partner.id
                left join account_payment_term term on so.payment_term = term.id
                left join account_payment_term_line term_line on term.id = term_line.payment_id
                left join account_invoice inv on inv.origin = so.name and inv.type = 'out_invoice'
                left join (select order_id, sum(product_uom_qty) as total_qty from sale_order_line group by order_id) solg on solg.order_id = so.id
                where b.code = 'MML' and so.division = 'Unit' and so.state in ('progress','done')
                --and pick.date_done >=%s and pick.date_done <=%s
                --and inv.type='out_invoice'
                order by so.date_order,so.id
              ''',(val.per_date,
                   (datetime.now()+timedelta(days=1)).strftime('%m%d%Y'),
                   val.per_date,
                   val.per_date+' 23:59:59',
                   val.per_date+' 00:00:00',
                   val.per_date+' 23:59:59',
                   val.per_date,val.per_date))
        picks = cur.fetchall()
        cur.close()
        i=1
        prev_prefix=False
        for x in picks:
            if prev_prefix ==x[0] :
                i+=1
            else:
                i=1
            prev_prefix=x[0]
            if len(str(i)) == 1 :
                        urutan="00"+str(i)
            elif len(str(i)) == 2 :
                urutan="0"+str(i)
            elif len(str(i)) == 3 :
                urutan=str(i)
            result += str(x[0])+urutan+str(x[1])
            result += '\n'
        tangal=time.strftime('%d%m%Y')
        nama = tangal+'.txt'
        out = base64.encodestring(result)
        distribution = self.write(cr, uid, ids, {'data_file':out, 'name': nama}, context=context)


       