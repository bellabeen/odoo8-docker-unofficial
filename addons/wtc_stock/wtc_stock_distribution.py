import time
import base64
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
import pytz 

class Eksport_distribution(osv.osv_memory):
    _name = "eksport.distribution"
    _columns = {
                'name': fields.char('File Name', 35),
                'data_file': fields.binary('File'),
                'date_start':fields.date(string="Start Date",required=True),
                'date_end':fields.date(string="End Date",required=True)
                }   
    
    def export_file(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids)[0]
        trx_id = context.get('active_id',False) 
        trx_obj = self.pool.get('wtc.stock.packing').browse(cr,uid,trx_id,context=context)
        result = self.eksport_distribution(cr, uid, ids, trx_obj,context)
        form_id  = 'view.wizard.eksport.distribution'
 
        view_id = self.pool.get('ir.ui.view').search(cr,uid,[                                     
                                                             ("name", "=", form_id), 
                                                             ("model", "=", 'eksport.distribution'),
                                                             ])
     
        return {
            'name' : _('Export File'),
            'view_type': 'form',
            'view_id' : view_id,
            'view_mode': 'form',
            'res_id': ids[0],
            'res_model': 'eksport.distribution',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True,
            'context': context
        }
        
        
        
    def export_file_picking(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids)[0]
        trx_id = context.get('active_id',False) 
        trx_obj = self.pool.get('stock.picking').browse(cr,uid,trx_id,context=context)
        result = self.eksport_picking(cr, uid, ids, trx_obj,context)
        form_id  = 'view.wizard.eksport.distribution'
 
        view_id = self.pool.get('ir.ui.view').search(cr,uid,[                                     
                                                             ("name", "=", form_id), 
                                                             ("model", "=", 'eksport.distribution'),
                                                             ])
     
        return {
            'name' : _('Export File'),
            'view_type': 'form',
            'view_id' : view_id,
            'view_mode': 'form',
            'res_id': ids[0],
            'res_model': 'eksport.distribution',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True,
            'context': context
        }
        
        
        
    def eksport_distribution(self, cr, uid, ids,trx_obj, context=None):
        result = ''
        val = self.browse(cr, uid, ids)[0]
        cr.execute('''
                    SELECT 
                    b.name as no_surat_jalan,
                    c.chassis_number,
                    c.engine_number,
                    p.name_template,
                    v.code,
                    f.dealer_code,
                    par.dealer_code,
                    b.date,
                    a.name as no_picking, 
                    inv.number as no_invoice,
                    a.origin as no_transaksi
                    from stock_picking  as a
                    LEFT JOIN wtc_stock_packing as b
                    ON a.id=b.picking_id
                    LEFT JOIN wtc_stock_packing_line AS c
                    on c.packing_id=b.id
                    Left join account_invoice inv on inv.origin = a.origin and inv.type='out_invoice'
                    LEFT JOIN wtc_mutation_order as d
                    on d.name=a.origin
                    LEFT JOIN wtc_branch AS e
                    ON e.id=d.branch_requester_id
                    LEFT JOIN res_partner as par
                    ON par.default_code=e.code
                    LEFT JOIN res_partner as f
                    ON f.id=a.partner_id
                    LEFT JOIN  product_product p
                    ON p.id=c.product_id
                    LEFT join product_attribute_value_product_product_rel pv on p.id = pv.prod_id
                    LEFT join product_attribute_value v on pv.att_id = v.id
                    where  a.picking_type_id in (
                    SELECT id from stock_picking_type where code in ('outgoing','interbranch_out') and branch_id in (select id FROM wtc_branch where code='MML')
                    ) 
                    and b.date >=%s and b.date <=%s
                    and a.division='Unit'  and b.state='posted' 
                    order by a.origin desc
              ''',(val.date_start,val.date_end))
 
        picks = cr.fetchall()
        for x in picks:
            if x[10][0:2] == 'SO':
                kode_dealer=x[5]
            else :
                kode_dealer=x[6]
            date =x[7]
            bulan = str(date[5:7])
            tanggal = str(date[8:10])
            tahun = str(date[2:4])
            new_date = tanggal+'-'+bulan+'-'+tahun    
            
            result += str(x[0])+';'+str(x[1])+';'+str(x[2][0:5])+' '+str(x[2][5:12])+';'+str(x[3])+';'+str(x[4])+';'+str(kode_dealer)+';'+new_date+';'+str(x[8])+';'+str(x[9])+';'+str(x[10])
            result += '\n'
        tangal=time.strftime('%d%m%Y')
        nama = tangal+'.txt'
        out = base64.encodestring(result)
        distribution = self.write(cr, uid, ids, {'data_file':out, 'name': nama}, context=context)
            
            
    def eksport_picking(self, cr, uid, ids,trx_obj, context=None):
        result = ''
        val = self.browse(cr, uid, ids)[0]
        obj_picking_type = self.pool.get('stock.picking.type')
        picking_type_id = obj_picking_type.search(cr,uid,[('code','in',['outgoing','interbranch_out'])])
        branch=self.pool.get('wtc.branch').search(cr,uid,[('code','=','MML')])
    
        
        object_picking=self.pool.get('stock.picking').search(cr,uid,[
                                                                      ('picking_type_id','in',picking_type_id),
                                                                      ('division','=','Unit'),
                                                                      ('branch_id','in',branch),
                                                                      ('date','>=',val.date_start),
                                                                      ('date','<=',val.date_end),
                                                                      ('state','not in',('draft','cancel')),
                                                                      ])
        obj_packing_browse=self.pool.get('stock.picking').browse(cr,uid,object_picking)
        
        aralis_code=' '
        for y in obj_packing_browse :
            mutation_order=False
            if y.model_id.model :
                mutation_order=self.pool.get(y.model_id.model).browse(cr,uid,y.transaction_id)
                if y.model_id.model == 'wtc.mutation.order' :
                    aralis_code=mutation_order.branch_requester_id.partner_id.dealer_code
                else :
                    aralis_code=mutation_order.partner_id.dealer_code   
            else :
                aralis_code=y.partner_id.dealer_code 
            for x in y.move_lines :
                date = y.date
                bulan = str(date[5:7])
                tanggal = str(date[8:10])
                tahun = str(date[2:4])
                new_date = tanggal+'-'+bulan+'-'+tahun
                file=str(date[:4])+bulan+tanggal
                result += str(y.origin)+';'+str(x.product_id.name)+';'+str(x.product_id.attribute_value_ids.code)+';'+str(x.product_qty)+';'+str(new_date)+';'+str(y.name)+';'+str(aralis_code)+';'
                result += '\n'
                file=str(date[:4])+bulan+tanggal
            nama = 'PIC'+file+'.pick'
            out = base64.encodestring(result)
            distribution = self.write(cr, uid, ids, {'data_file':out, 'name': nama}, context=context)