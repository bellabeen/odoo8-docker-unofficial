import time
import base64
from datetime import datetime, timedelta
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
import pytz 
import os

class Eksport_file_ahm_rec(osv.osv_memory):
    _name = "eksport.ahm.rec"
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
        form_id  = 'view.wizard.eksport.ahm.rec'
 
        view_id = self.pool.get('ir.ui.view').search(cr,uid,[                                     
                                                             ("name", "=", form_id), 
                                                             ("model", "=", 'eksport.ahm.rec'),
                                                             ])
     
        return {
            'name' : _('Export File'),
            'view_type': 'form',
            'view_id' : view_id,
            'view_mode': 'form',
            'res_id': ids[0],
            'res_model': 'eksport.ahm.rec',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True,
            'context': context
        }
        
    def eksport_distribution(self, cr, uid, ids,trx_obj, context=None):
        result = '' 
        val = self.browse(cr, uid, ids)[0]
        cr.execute('''
                 SELECT pac.name,
                 pac.date as tgl_tr,
                 pick.origin,
                 pr.name_template,
                 move.product_qty
                 FROM stock_picking as pick
                 LEFT JOIN wtc_stock_packing as pac
                 ON pick.id=pac.picking_id
                 LEFT JOIN res_partner as parner
                 ON parner.id=pick.partner_id
                 LEFT JOIN  wtc_branch as branch
                 ON branch.id=pick.branch_id
                 
                 LEFT JOIN stock_move as move
                 ON pick.id=move.picking_id
                 
                 left join product_product as pr
                 ON pr.id=move.product_id
                 
                  LEFT JOIN product_template t 
                ON pr.product_tmpl_id = t.id
                
                LEFT JOIN product_category c 
                ON t.categ_id = c.id 
                 
                 WHERE pick.division='Sparepart'
                 and parner.default_code='AHM'
                 and branch.code='MML'
                 and pick.state='done'
                  and c.name NOT IN ('NONHGP-ASPIRA','NONHGP-BLAZE','NONHGP-FEDERAL','NONHGP-OTHERS')
                 and pick.date_done >=%s and pick.date_done <=%s
        
                 
            ''',(val.date_start+' 00:00:00',val.date_end+' 23:59:59'))
        picks = cr.fetchall()
        tangal=time.strftime('H2Z%d%m%Y')
        nama = tangal+'.REC'
        
        
        for x in picks:
            
            po=self.pool.get('b2b.file.ps').search(cr,uid,[("kode_ps","=",x[2] ),
                                                           ("kode_sparepart","=",x[3])],limit=1)
            po2 = self.pool.get('b2b.file.ps').browse(cr,uid,po)
            
            if len(str(x[0])) > 30 :
                no_ps_md=x[0][:30]
            elif len(str(x[0])) < 30 :
                no_ps_md=x[0].ljust(30)
                
            tgl_transaksi=x[1][8:]+x[1][5:7]+x[1][0:4]+' '+'120000'
            
            if len(tgl_transaksi) > 20 :
                tgl_transaksi_fix=tgl_transaksi[:20]
            elif len(tgl_transaksi) < 20 :
                tgl_transaksi_fix=tgl_transaksi.ljust(20)
                
                
            if len(str(x[2])) > 15 :
                ps=x[2][:15]
            elif len(str(x[2])) <= 15 :
                ps=x[2].ljust(15)
            
            kode_sup='AHM            '
            
            if len(str(x[3])) > 25 :
                kode_sparepart=x[3][:25]
            elif len(str(x[3])) <= 25 :
                kode_sparepart=x[3].ljust(25)
                
            if len(str(x[4])) > 10 :
                qty=str(x[4])[:10]
            elif len(str(x[4])) < 10 :
                qty=str(x[4]).ljust(10)
                
            qty_fix= '{:>10}'.format(int(x[4]))
            
            if len(po2.kode_po_md) > 30 :
                kode_po_md=po2.kode_po_md[:30]
            elif len(po2.kode_po_md) < 30 :
                kode_po_md=po2.kode_po_md.ljust(30)
         
            ps2 = (ps.encode('ascii','ignore').decode('ascii'))
            kode_po_md2 = (kode_po_md.encode('ascii','ignore').decode('ascii'))
            kode_sparepart2 = (kode_sparepart.encode('ascii','ignore').decode('ascii'))
                   
            result += 'H2Z  '+no_ps_md+tgl_transaksi_fix+ps2+kode_sup+kode_po_md2+kode_sparepart2+qty_fix
            result += '\n';
        out = base64.encodestring(result)
        distribution = self.write(cr, uid, ids, {'data_file':out, 'name': nama}, context=context)


    def eksport_auto_distribution(self, cr, uid, ids):
        date= self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=None)
        
        date_start = str(date.strftime("%Y-%m-%d"))
        date_end = str(date.strftime("%Y-%m-%d"))

        result = '' 
        
        cr.execute('''
                 SELECT pac.name,
                 pac.date as tgl_tr,
                 pick.origin,
                 pr.name_template,
                 move.product_qty
                 FROM stock_picking as pick
                 LEFT JOIN wtc_stock_packing as pac
                 ON pick.id=pac.picking_id
                 LEFT JOIN res_partner as parner
                 ON parner.id=pick.partner_id
                 LEFT JOIN  wtc_branch as branch
                 ON branch.id=pick.branch_id
                 
                 LEFT JOIN stock_move as move
                 ON pick.id=move.picking_id
                 
                 left join product_product as pr
                 ON pr.id=move.product_id
                 
                  LEFT JOIN product_template t 
                ON pr.product_tmpl_id = t.id
                
                LEFT JOIN product_category c 
                ON t.categ_id = c.id 
                 
                 WHERE pick.division='Sparepart'
                 and parner.default_code='AHM'
                 and branch.code='MML'
                 and pick.state='done'
                  and c.name NOT IN ('NONHGP-ASPIRA','NONHGP-BLAZE','NONHGP-FEDERAL','NONHGP-OTHERS')
                 and pick.date_done >=%s and pick.date_done <=%s
        
                 
            ''',(date_start+' 00:00:00',date_end+' 23:59:59'))
            # (date_start+' 00:00:00',date_end+' 23:59:59'))
        picks = cr.fetchall()
        tangal=time.strftime('H2Z%d%m%Y')
        nama = tangal+'.REC'
        
        if picks:
            for x in picks:
                
                po=self.pool.get('b2b.file.ps').search(cr,uid,[("kode_ps","=",x[2] ),
                                                            ("kode_sparepart","=",x[3])],limit=1)
                po2 = self.pool.get('b2b.file.ps').browse(cr,uid,po)
                
                if len(str(x[0])) > 30 :
                    no_ps_md=x[0][:30]
                elif len(str(x[0])) < 30 :
                    no_ps_md=x[0].ljust(30)
                    
                tgl_transaksi=x[1][8:]+x[1][5:7]+x[1][0:4]+' '+'120000'
                
                if len(tgl_transaksi) > 20 :
                    tgl_transaksi_fix=tgl_transaksi[:20]
                elif len(tgl_transaksi) < 20 :
                    tgl_transaksi_fix=tgl_transaksi.ljust(20)
                    
                    
                if len(str(x[2])) > 15 :
                    ps=x[2][:15]
                elif len(str(x[2])) <= 15 :
                    ps=x[2].ljust(15)
                
                kode_sup='AHM            '
                
                if len(str(x[3])) > 25 :
                    kode_sparepart=x[3][:25]
                elif len(str(x[3])) <= 25 :
                    kode_sparepart=x[3].ljust(25)
                    
                if len(str(x[4])) > 10 :
                    qty=str(x[4])[:10]
                elif len(str(x[4])) < 10 :
                    qty=str(x[4]).ljust(10)
                    
                qty_fix= '{:>10}'.format(int(x[4]))
                
                if len(po2.kode_po_md) > 30 :
                    kode_po_md=po2.kode_po_md[:30]
                elif len(po2.kode_po_md) < 30 :
                    kode_po_md=po2.kode_po_md.ljust(30)
            
                ps2 = (ps.encode('ascii','ignore').decode('ascii'))
                kode_po_md2 = (kode_po_md.encode('ascii','ignore').decode('ascii'))
                kode_sparepart2 = (kode_sparepart.encode('ascii','ignore').decode('ascii'))
                    
                result += 'H2Z  '+no_ps_md+tgl_transaksi_fix+ps2+kode_sup+kode_po_md2+kode_sparepart2+qty_fix
                result += '\n';

        # out = base64.encodestring(result)
        # distribution = self.write(cr, uid, ids, {'data_file':out, 'name': nama}, context=context)
            
            file = open(os.path.dirname(os.path.abspath(__file__))+'/static/'+nama,'w+')
            file.write(result)

