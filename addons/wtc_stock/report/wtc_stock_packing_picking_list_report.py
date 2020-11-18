import time
from datetime import datetime
from openerp.report import report_sxw
from openerp.osv import osv
from openerp import pooler
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
import pytz 
from openerp.tools.translate import _
import base64

class stock_picking(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(stock_picking, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'no_urut': self.no_urut,
            'waktu_local': self.waktu_local,
            'qty': self.qty,
            'mutation_order':self.mutation_order,
            'get_sub':self.get_sub,


            

            
        })
        
        self.no = 0
    def no_urut(self):
        self.no+=1
        return self.no

    
    def waktu_local(self):
        tanggal = datetime.now().strftime('%y%m%d')
        menit = datetime.now()
        user = self.pool.get('res.users').browse(self.cr, self.uid, self.uid)
        tz = pytz.timezone(user.tz) if user.tz else pytz.utc
        start = pytz.utc.localize(menit).astimezone(tz)
        start_date = start.strftime("%d-%m-%Y %H:%M")
        return start_date
    
    
    def mutation_order(self):
        obj_picking = self.pool.get('stock.picking').browse(self.cr, self.uid, self.ids)
        nama_dealer=False
        if obj_picking.origin[0:2] == 'MO' :
            obj_mo=self.pool.get('wtc.mutation.order').search(self.cr,self.uid,[('name','=',obj_picking.origin)])
            obj_mo_browse=self.pool.get('wtc.mutation.order').browse(self.cr,self.uid,obj_mo)
            nama_dealer=obj_mo_browse.branch_requester_id
        elif obj_picking.origin[0:2] == 'SO' and obj_picking.branch_id.code == 'MML' :
            nama_dealer=obj_picking.partner_id
        elif obj_picking.origin[0:2] == 'SO' and obj_picking.branch_id.code != 'MML' :
            dsl_obj= self.pool.get('dealer.sale.order').search(self.cr, self.uid,[('name','=',obj_picking.origin)])
            dsl=self.pool.get('dealer.sale.order').browse(self.cr, self.uid,dsl_obj)
            nama_dealer=dsl.partner_id
        return nama_dealer
    
    def qty(self):
        order = self.pool.get('stock.move').search(self.cr, self.uid,[("picking_id", "in", self.ids)])
        valbbn=0
        for line in self.pool.get('stock.move').browse(self.cr, self.uid, order) :
            valbbn += line.product_uom_qty
        return valbbn


    def get_sub(self, branch_id, product_id):
        # branch_id = 1
        # product_id = 67120
        query = """
            select name
            from teds_sub_location
            where branch_id = %s
            and product_id = %s 
            order by priority asc 
            limit 1
            """ % (branch_id, product_id)

        self.cr.execute(query)
        ress = self.cr.fetchone()
        
        
        if ress :
            return ress[0]

        return "-"


        branch = self.pool.get('stock.picking').search(self.cr, self.uid, self.ids).branch_id
        produck = self.pool.get('stock.move').search(self.cr, self.uid, self.ids).product_id



        a = self.pool.get('sub.location.sperapart').search(self.cr, self.uid,branch,produck).name
        sub=self.pool.get('sub.location.sperapart').browse(cr,uid,ids,a)

        return sub

        # produck = self.pool.get('stock.move').search(self.cr, self.uid,[("product_id", "in", self.ids)])
        # saya=Trueaku td coba buat metho444zxcvbzte
        # for a in self.pool.get('stock.move').browse(self.cr, self.uid, produck) :
        #     saya == a.product_id
       
        # return saya


        # order = self.pool.get('stock.move').search(self.cr, self.uid,[("picking_id", "in", self.ids)])
        # valbbn=0
        # for line in self.pool.get('stock.move').browse(self.cr, self.uid, order) :
        #     valbbn += line.product_uom_qty
        # return valbbn


              

report_sxw.report_sxw('report.rml.wtc.stock.packing', 'stock.picking', 'addons/wtc_stock/report/wtc_stock_packing_picking_list_report.rml', parser = stock_picking, header = False)