import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp import netsvc
import openerp.addons.decimal_precision as dp
from openerp import workflow

class dealer_sale_order_approval_diskon(osv.osv):
    _name = "dealer.sale.order.summary.diskon"   
    
    def _amount_average(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if context is None:
            context = {}
        for approval in self.browse(cr, uid, ids, context=context):
            total_average = approval.beban_ps + approval.beban_bb + approval.beban_bb + approval.beban_po + approval.beban_hc
            
            res[approval.id]['amount_average']=total_average
        return res
       
    _columns = {
                'dealer_sale_order_id': fields.many2one('dealer.sale.order'),
                'product_id': fields.many2one('product.product','Product'),
                'product_qty': fields.integer('Qty'),
                'beban_ps': fields.float('Subsidi Dealer'),
                'beban_bb' : fields.float('Barang Bonus'),
                'beban_po': fields.float('Potongan'),
                'beban_hc': fields.float('Hutang Komisi'),
                'amount_average': fields.float('Amount Average'),
                  
    }
class dealer_sale_order(osv.osv):
    
    _inherit = "dealer.sale.order"      
    _columns = {
                'approval_ids': fields.one2many('wtc.approval.line','transaction_id',string="Table Approval",domain=[('form_id','=',_inherit)]),
                'approval_state': fields.selection([('b','Belum Request'),('rf','Request For Approval'),('a','Approved'),('r','Reject')],'Approval State', readonly=True),  
    }
    
    _defaults ={
                'approval_state':'b'
                }
    
    def _check_sale_order(self,cr,uid,ids,sale_order):
        for order_line in sale_order.dealer_sale_order_line:
            if sale_order.finco_id:
                if not order_line.finco_tgl_po:
                    raise osv.except_osv(('Perhatian !'), ("Tanggal PO belum diisi!"))
                elif not order_line.finco_no_po:
                    raise osv.except_osv(('Perhatian !'), ("No. PO Belum diisi!"))
                elif order_line.finco_tenor <= 0:
                    raise osv.except_osv(('Perhatian !'), ("Ttenor Harus lebih dari 0!"))
                elif order_line.cicilan <=0:
                    raise osv.except_osv(('Perhatian !'), ("Cicilan harus lebih dari 0!"))
                
                elif order_line.is_bbn =='T':
                    raise osv.except_osv(('Perhatian !'), ("Penjualan credit harus pilih BBN!"))
                
                elif order_line.uang_muka <=0:
                    raise osv.except_osv(('Perhatian !'), ("Penjualan credit uang muka harus diisi"))
                
                
            if not order_line.tax_id:
                raise osv.except_osv(('Perhatian !'), ("Pajak harus diisi!"))
            
            if sale_order.partner_komisi_id:
                if not order_line.hutang_komisi_id:
                    raise osv.except_osv(('Perhatian !'), ("Hutang Komisi Belum diisi!"))
            
            if order_line.is_bbn=='Y':
                if order_line.price_bbn<=0:
                    raise osv.except_osv(('Perhatian !'), ("Harga BBN tidak boleh 0!"))
                elif not order_line.biro_jasa_id:
                    raise osv.except_osv(('Perhatian !'), ("Biro Jasa belum dipilih!"))
            
            if not sale_order.finco_id:
                if order_line.uang_muka >0:
                    raise osv.except_osv(('Perhatian !'), ("Penjualan cash uang muka harus 0!"))
            
            if order_line.hutang_komisi_id or order_line.amount_hutang_komisi:
                if not sale_order.partner_komisi_id:
                    raise osv.except_osv(('Perhatian !'), ("Jika hutang komisi diisi maka mediator harus diisi!"))
                
            if order_line.discount_po<0:
                raise osv.except_osv(('Perhatian !'), ("Diskon tidak boleh minus!"))
        self.check_hl(cr,uid,ids)
            
        return True
   
    def wkf_request_approval(self, cr, uid, ids, context=None):
        sale_order = self.browse(cr, uid, ids, context=context)
        obj_matrix = self.pool.get("wtc.approval.matrixdiscount")
        if not sale_order.dealer_sale_order_line:
            raise osv.except_osv(('Perhatian !'), ("Produk belum diisi"))
        
        cek_order = self._check_sale_order(cr, uid, ids, sale_order)
        hasil = []
        
        summary_diskon = self._set_diskon_summary(cr,uid,ids,sale_order.dealer_sale_order_line)
        
        for key, value in summary_diskon.items():
            product_template_id = self.pool.get('product.product').browse(cr,uid,key).product_tmpl_id
            obj_matrix.request(cr, uid, ids, sale_order,sale_order['summary_diskon_ids'], 'amount_average','product_id')
        
        self.write(cr, uid, ids, {'state': 'waiting_for_approval','approval_state':'rf'})
        return True
           
    def wkf_approval(self, cr, uid, ids, context=None):
        obj_so = self.browse(cr, uid, ids, context=context)
        if not obj_so.summary_diskon_ids:
            raise osv.except_osv(('Perhatian !'), ("produk belum diisi"))
        for summary in obj_so.summary_diskon_ids:
            
            approval_sts = self.pool.get("wtc.approval.matrixdiscount").approve(cr, uid, ids, obj_so, summary.product_id)
            if approval_sts == 1:
                self.write(cr, uid, ids, {'approval_state':'a','state':'approved'})
            elif approval_sts == 0:
                raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group approval"))
   
        return True

    def has_approved(self, cr, uid, ids, *args):
        obj_po = self.browse(cr, uid, ids)
        return obj_po.approval_state == 'a'

    def has_rejected(self, cr, uid, ids, *args):
        obj_po = self.browse(cr, uid, ids)
        if obj_po.approval_state == 'r':
            self.write(cr, uid, ids, {'state':'draft'})
            return True
        return False

    def wkf_set_to_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'r'})
    
    def wkf_set_to_draft_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'b'}) 
    
    def wkf_cancel_approval_dso(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft','approval_state':'b'})                  
        
class dealer_sale_order_reason_reject_approval(osv.osv_memory):
    _name = "dealer.sale.order.reason.reject.approval.so"
    _columns = {
                'reason':fields.text('Reason')
                }
    
    def wtc_reject_approval(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids, context=context)
        user = self.pool.get("res.users").browse(cr, uid, uid)['groups_id']
        
        po_id = context.get('active_id',False) #When you call any wizard then in this function ids parameter contain the list of ids of the current wizard record. So, to get the purchase order ID you have to get it from context.
        
        line = self.pool.get("wtc.work.order").browse(cr,uid,po_id,context=context)
        objek = False
        for x in line.approval_ids :
            for y in user:
                    if y == x.group_id :
                        objek = True
                        for z in line.approval_ids :
                            if z.reason == False :
                                z.write({
                                        'reason':val.reason,
                                        'value':line.amount_total,
                                        'sts':'3',
                                        'pelaksana_id':uid,
                                        'tanggal':datetime.today()
                                        }) 
        
                                self.pool.get("wtc.work.order").write(cr, uid, po_id, {'state':'draft','approval_state':'r'})
        if objek == False :
            raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group approval"))
                                                      
        return True    