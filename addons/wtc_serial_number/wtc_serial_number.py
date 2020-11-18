import datetime
from openerp.osv import fields, osv
from openerp.exceptions import Warning

tgl= datetime.datetime.now()
thn = tgl.year

class serial_number(osv.osv):
    _inherit ='stock.production.lot'
    
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
        
    _columns={
              'chassis_no':fields.char('Chassis Number',required=True),
              'chassis_code':fields.char('Chassis Code'),
              'branch_id': fields.many2one('wtc.branch','Branch'),
              'division':fields.selection([('Unit','Unit')], 'Division'),
              'state': fields.selection([('intransit', 'Intransit'),('titipan','Titipan'),('stock', 'Stock'), ('reserved','Reserved'),('sold','Sold'), ('paid', 'Paid'),('sold_offtr','Sold.offtr'),('paid_offtr','Paid.offtr'),('workshop','Workshop'),('cancelled','Cancel')], 'State'),
              'state_stnk': fields.selection([('mohon_faktur', 'Mohon Faktur'),('terima_faktur','Terima Faktur'),('proses_stnk','Proses STNK')], 'State STNK', track_visibility='always'),
              'tahun': fields.char('Tahun Pembuatan', size=4),
              'sale_order_id': fields.many2one('sale.order', string='Sales Order',readonly=True),
              'customer_invoice_id': fields.many2one('account.invoice',string='Customer Invoice',readonly=True),
              'receipt_id': fields.many2one('stock.picking', 'Receipt'),
              'picking_id': fields.many2one('stock.picking', 'Picking'),
              'location_id': fields.many2one('stock.location','Location'),
              'ready_for_sale': fields.selection([('good','Good'),('not_good','Not Good')], 'Ready For Sale'),
              'in_date': fields.date('Incoming Date'),
              
              #PURCHASE
              'purchase_order_id': fields.many2one('purchase.order','PO Number'),
              'po_date': fields.date('PO Date'),
              'supplier_id':fields.many2one('res.partner','Supplier'),
              'expedisi_id':fields.many2one('res.partner','Supplier Expedisi'),
              'receive_date':fields.date('Receive Date'),
              'freight_cost':fields.float('Freight Cost'),
              'supplier_invoice_id': fields.many2one('account.invoice',string='Supplier Invoice',readonly=True),
              
              # SALES MD
              'dealer_id':fields.many2one('res.partner','Dealer'),
              'sales_md_date': fields.date('Sales MD Date'),
              'do_md_date':fields.date('DO MD Date'),
              'tgl_cetak_faktur':fields.date('Tanggal Cetak Faktur'),
              'tgl_mohon_faktur':fields.date('Tanggal Mohon Faktur'),
              # SALES DEALER
              'invoice_date':fields.date('Invoice Date'),
              'do_date':fields.date('DO Date'),
              'tgl_faktur':fields.date('Tanggal Mohon Faktur'),
              'faktur_stnk':fields.char('No Faktur STNK', size=128),
              'tgl_terima':fields.date('Tanggal Terima'),
              'customer_id':fields.many2one('res.partner','Customer',domain=[('customer','=',True)]),
              'finco_id':fields.many2one('res.partner','Code Finance Company',domain=[('finance_company','=',True)]),
              'reserved': fields.boolean('Reserved'),
              'customer_reserved': fields.many2one('res.partner','Customer Reserved'),
              'customer_stnk': fields.many2one('res.partner','Customer STNK',domain=[('customer','=',True)]),
              'jenis_penjualan':fields.selection([('1','Cash'),('2','Credit')],'Jenis Penjualan'),
              'dp':fields.float('DP'),
              'tenor':fields.float('Tenor'),
              'cicilan':fields.float('Cicilan'),
              #STNK & BPKB
              'biro_jasa_id':fields.many2one('res.partner','Biro Jasa',domain=[('biro_jasa','=',True)]),
              'no_polisi':fields.char('No Polisi',size=128),
              'tgl_notice':fields.date('Tgl JTP Notice'),
              'no_notice':fields.char('No Notice', size=128),
              'tgl_stnk':fields.date('Tgl JTP STNK'),
              'no_stnk':fields.char('No STNK',size=128),
              'tgl_bpkb':fields.date('Tgl Jadi BPKB'),
              'no_bpkb':fields.char('No BPKB',size=128),
              #WORKSHOP
              'kode_buku':fields.char('Kode Buku Service'),
              'nama_buku':fields.char('Nama Buku Service'), 
              'no_sipb':fields.char('No SIPB'),
              'no_ship_list':fields.char('No Ship List'),
              'tgl_ship_list':fields.date("Tgl Ship List"),
              'no_faktur':fields.char('No Faktur'),
             
             }

    
    _sql_constraints = [
        ('unique_name', 'unique(name)', 'Ditemukan Serial Number duplicate !'),
        ('unique_chassis', 'unique(chassis_no)', 'Ditemukan Chassis Number duplicate !'),
        ]
        
    _defaults={
               #'tahun': thn,
               'branch_id': _get_default_branch,
               }   
    
    def unlink(self,cr,uid,ids,context=None):
        for item in self.browse(cr, uid, ids, context=context):
                raise osv.except_osv(('Perhatian !'), ("Tidak boleh menghapus lot"))
        return False

    def create(self, cr, uid, vals, context=None):
        self.check_lot(cr,uid,vals.get('name',False),vals.get('chassis_no',False),context)
        res = super(serial_number,self).create(cr,uid,vals,context=context)
        return res

    def write(self, cr, uid, ids, vals, context=None):
        engine_no = vals.get('name',False)
        chassis_no = vals.get('chassis_no',False)

        if engine_no or chassis_no:
            old_vals = self.browse(cr, uid, ids, context)
            for old in old_vals:
                cek_engine = engine_no if engine_no != old.name else False
                cek_chassis = chassis_no if chassis_no != old.chassis_no else False
                self.check_lot(cr, uid, cek_engine, cek_chassis, context)
        res = super(serial_number, self).write(cr,uid,ids,vals,context=context)
        return res
                         
    def tahun_change(self, cr, uid, ids, tahun, context=None):
        val = {}
        war = {}
        if tahun and not tahun.isdigit():
            val['tahun'] = False
            war = {'title':'Perhatian !', 'message':'Tahun Perakitan hanya boleh angka'}
            
        return {'value':val, 'warning':war}

    def check_lot(self,cr,uid,engine_no=False,chassis_no=False,context=None):
        warning = ''
        if engine_no :
            check_exist = self.search(cr,uid,[('name','=',engine_no)],context=context)
            if check_exist :
                warning += 'No Engine "%s"'%engine_no

        if chassis_no :
            check_exist = self.search(cr,uid,[('chassis_no','=',chassis_no)],context=context)
            if check_exist :
                if warning :
                    warning += ' & No Chassis "%s"'%chassis_no
                else :
                    warning = 'No Chassis "%s"'%chassis_no

        if warning :
            warning += ' telah terdaftar dalam master serial number, silakan cek kembali data Anda!'
            raise Warning(warning)



