import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp import netsvc

class wtc_work_order(osv.osv):
    _inherit = "wtc.work.order"      
    _columns = {
                'approval_ids': fields.one2many('wtc.approval.line','transaction_id',string="Table Approval",domain=[('form_id','=',_inherit)]),
                'approval_state': fields.selection([('b','Belum Request'),('rf','Request For Approval'),('a','Approved'),('r','Reject')],'Approval State', readonly=True),  
    }
    
    _defaults ={
                'approval_state':'b'
                }
    
    
    def wkf_request_approval(self, cr, uid, ids, context=None):
        obj_po = self.browse(cr, uid, ids, context=context)
        obj_matrix = self.pool.get("wtc.approval.matrixbiaya")
        if not obj_po.work_lines:
            raise osv.except_osv(('Perhatian !'), ("Produk belum diisi"))
        discount = 0.0
        msg=''
        for line in obj_po.work_lines :
            if int(line.product_qty) <= 0:
                raise osv.except_osv(('Perhatian !'), ("Product Qty tidak boleh 0 !"))
            if line.state == 'draft' :
                if line.categ_id == 'Sparepart':
                    if line.product_id.categ_id.name in ('OIL','GMO'):
                        curr_discount = line.discount * 200
                    else:
                        curr_discount = line.discount * 44
                else :
                    curr_discount = line.discount * 18

                if discount < curr_discount:
                    discount = curr_discount
                
                if line.categ_id == 'Sparepart':
                    obj_wo_line = self.pool.get('wtc.work.order.line').browse(cr,uid,line.id,{'state': 'draft'})                
                    obj_location = self.pool.get('stock.location')
                    ids_location = obj_location.search(cr,uid,[('branch_id','=',obj_po.branch_id.id),('usage','=','internal')])
                    
                    query="""
                            select sum(q.qty) as quantity from stock_quant q 
                            where q.product_id = %s and q.location_id in %s 
                            and q.reservation_id is Null 
                            and q.consolidated_date is not Null """ %(obj_wo_line.product_id.id,str(tuple(ids_location)).replace(',)', ')'))
                    cr.execute(query)
                    qty_avb = cr.fetchall()[0][0]
                    if qty_avb < obj_wo_line.product_qty:
                        msg=1
                self.pool.get('wtc.work.order.line').write(cr,uid,line.id,{'state': 'confirmed'})
            else:
                if line.categ_id == 'Sparepart':
                    if line.product_id.categ_id.name in ('OIL','GMO'):
                        curr_discount = line.discount * 200
                    else:
                        curr_discount = line.discount * 44
                else :
                    curr_discount = line.discount * 18

                if discount < curr_discount:
                    discount = curr_discount


        if msg == 1:
            raise osv.except_osv(('Perhatian !'), ("Qty available tidak mencukupi"))
        obj_matrix.request_by_value(cr, uid, ids, obj_po, discount)
        self.write(cr, uid, ids, {'state': 'waiting_for_approval','approval_state':'rf'})
        return True
           
    def wkf_approval(self, cr, uid, ids, context=None):
        obj_po = self.browse(cr, uid, ids, context=context)
        if not obj_po.work_lines:
            raise osv.except_osv(('Perhatian !'), ("produk belum diisi"))
        approval_sts = self.pool.get("wtc.approval.matrixbiaya").approve(cr, uid, ids, obj_po)
        if approval_sts == 1:
            self.write(cr, uid, ids, {'date':self._get_default_date(cr,uid,context),'approval_state':'a'})
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
        
class wtc_reason_reject_approval(osv.osv_memory):
    _name = "wtc.reason.reject.approval.wo"
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