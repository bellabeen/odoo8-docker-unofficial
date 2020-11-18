from openerp import models, fields, api
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp.report import report_sxw
from openerp.osv import osv

class StockPacking(models.Model):
    _inherit = "wtc.stock.packing"
    
    @api.multi
    def action_report_packing_surat_jalan(self): 
        datas = self.read()[0]   
        return self.env['report'].get_action(self,'teds_stock_packing.surat_jalan', data=datas)


class StockPackingSuratJalanQwebData(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(StockPackingSuratJalanQwebData, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'no_urut': self.no_urut,
            'qty': self.qty,
            'jumlah_cetakan': self.jumlah_cetakan,
            'mutation_order':self.mutation_order,
            'mutation_order_partner':self.mutation_order_partner,
            'invoice':self.invoice,
            'order_po':self.order_po,
            'print_user':self.print_user,
            'waktu_local':self.waktu_local,
        })
        
        self.no = 0
    def no_urut(self):
        self.no+=1
        return self.no

    def print_user(self):
        user = self.pool.get('res.users').browse(self.cr, self.uid, self.uid).name
        return user

    def waktu_local(self):
        tanggal = (datetime.now() + relativedelta(hours=7)).strftime('%d-%m-%Y %H:%M')
        return tanggal
    
    
    def order_po(self):
        packing_id=self.pool.get('wtc.stock.packing').browse(self.cr, self.uid, self.ids).picking_id.id
        obj_picking = self.pool.get('stock.picking').browse(self.cr, self.uid, packing_id)
        order_po = False
        if obj_picking.origin[0:2] == 'MO' :
            obj_mo=self.pool.get('wtc.mutation.order').search(self.cr,self.uid,[('name','=',obj_picking.origin)])
            obj_mo_browse=self.pool.get('wtc.mutation.order').browse(self.cr,self.uid,obj_mo)
            order_po = obj_mo_browse.sudo().dms_po_name
        return order_po

    def mutation_order(self):
        packing_id=self.pool.get('wtc.stock.packing').browse(self.cr, self.uid, self.ids).picking_id.id
        obj_picking = self.pool.get('stock.picking').browse(self.cr, self.uid, packing_id)
        nama_dealer=["",""]
        if obj_picking.origin[0:2] == 'MO' :
            obj_mo=self.pool.get('wtc.mutation.order').search(self.cr,self.uid,[('name','=',obj_picking.origin)])
            obj_mo_browse=self.pool.get('wtc.mutation.order').browse(self.cr,self.uid,obj_mo)
            nama_dealer=[obj_mo_browse.sudo().branch_requester_id.name,obj_mo_browse.sudo().branch_requester_id.street]
        elif obj_picking.origin[0:2] == 'SO' and obj_picking.branch_id.branch_type == 'MD' :
            nama_dealer = [obj_picking.partner_id.name,obj_picking.partner_id.street]
        elif obj_picking.origin[0:2] == 'SO' and obj_picking.branch_id.branch_type != 'MD' :
            dsl_obj= self.pool.get('dealer.sale.order').search(self.cr, self.uid,[('name','=',obj_picking.origin)])
            dsl=self.pool.get('dealer.sale.order').browse(self.cr, self.uid,dsl_obj)
            nama_dealer = [dsl.partner_id.name,dsl.partner_id.street]

        return nama_dealer

    def mutation_order_partner(self):
        partner = self.mutation_order()
        return partner.name_get().pop()[1]
    
    def invoice(self):
        no_invoice="-"
        origin =self.pool.get('wtc.stock.packing').browse(self.cr, self.uid, self.ids).rel_origin
        # obj_picking = self.pool.get('stock.picking').browse(self.cr, self.uid, a)
        obj_inv=self.pool.get('account.invoice').search(self.cr, self.uid,[('origin','=',origin),('type','=','out_invoice')],limit=1)
        inv=self.pool.get('account.invoice').browse(self.cr, self.uid,obj_inv).number
        no_invoice=inv
        return no_invoice
    
    def jumlah_cetakan(self):
        obj_model = self.pool.get('ir.model')
        obj_model_id = obj_model.search(self.cr, self.uid,[ ('model','=','wtc.stock.packing') ])[0]
        obj_ir = self.pool.get('ir.actions.report.xml').search(self.cr, self.uid,[('report_name','=','rml.wtc.stock.packing.surat.jalan')])
        obj_ir_id = self.pool.get('ir.actions.report.xml').browse(self.cr, self.uid,obj_ir).id
        obj_jumlah_cetak=self.pool.get('wtc.jumlah.cetak').search(self.cr,self.uid,[('report_id','=',obj_ir_id),('model_id','=',obj_model_id),('transaction_id','=',self.ids[0])])
        if not obj_jumlah_cetak :
            jumlah_cetak_id = {
            'model_id':obj_model_id,
            'transaction_id': self.ids[0],
            'jumlah_cetak': 1,
            'report_id':obj_ir_id                            
            }
            jumlah_cetak=1
            move=self.pool.get('wtc.jumlah.cetak').create(self.cr,self.uid,jumlah_cetak_id)
        else :
            obj_jumalah=self.pool.get('wtc.jumlah.cetak').browse(self.cr,self.uid,obj_jumlah_cetak)
            jumlah_cetak=obj_jumalah.jumlah_cetak+1
            self.pool.get('wtc.jumlah.cetak').write(self.cr, self.uid,obj_jumalah.id, {'jumlah_cetak': jumlah_cetak})
        return jumlah_cetak
    
    
    
    def qty(self):
        order = self.pool.get('wtc.stock.packing.line').search(self.cr, self.uid,[("packing_id", "in", self.ids)])
        valbbn=0
        for line in self.pool.get('wtc.stock.packing.line').browse(self.cr, self.uid, order) :
            valbbn += line.quantity
        return valbbn

class StockPackingSuratJalanQweb(osv.AbstractModel):
    _name = 'report.teds_stock_packing.surat_jalan'
    _inherit = 'report.abstract_report'
    _template = 'teds_stock_packing_print.teds_stock_packing_sj_qweb'
    _wrapped_report_class = StockPackingSuratJalanQwebData


