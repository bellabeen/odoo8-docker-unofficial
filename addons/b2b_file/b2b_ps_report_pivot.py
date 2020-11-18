from openerp import api, fields, models, tools

from openerp.osv import osv


class b2b_file_ps_report_pivot(models.Model):
    _name = "b2b.file.ps.report.pivot"
    _description = "Report File PS Pivot"
    _auto = False


# Jumlah PS ( ambil dr kode ps)
# Jumlah Qty PO
# Jumlah Qty PS

# Kode PS
# status
# kode_sparepart
# kode_dus

# Order by tgl_po
# Order by tgl ps

# filter by status
  
    kode_ps = fields.Char(string='Kode PS')
    qty_ps = fields.Float(string=' Total Qty PS')
    detail_ps = fields.Float(string='Qty PS')
    detail_po = fields.Float(string='Qty PO')
    qty_po = fields.Float(string='Total Qty PO')
    kode_sparepart = fields.Char(string='Kode Sparepart')
    tanggal_ps = fields.Date(string='Tanggal PS')
    status = fields.Selection([('packed at ahm','Packed at AHM'),('on intransit','On Intransit'),('received by md','Received by MD')], required=True)
    jumlah_status = fields.Float(string='Jumlah Status', readonly=True)
    
    
   
    def init(self,cr):
        tools.drop_view_if_exists(cr, 'b2b_file_ps_report_pivot')
        cr.execute("""
            create view b2b_file_ps_report_pivot as (
                select
                    min(ps.id) as id,
                    ps.kode_ps as kode_ps,
                    ps.kode_sparepart as kode_sparepart,
                    ps.qty_ps as detail_ps,
                    ps.qty_po as detail_po,
                    sum(ps.qty_ps) as qty_ps,
                    sum(ps.qty_po) as qty_po,
                    ps.status as status,
                    count(distinct ps.status) as jumlah_status,
                    ps.tanggal_ps as tanggal_ps

                from b2b_file_ps ps   
                group by
                    ps.tanggal_ps,
                    ps.kode_ps,
                    ps.kode_sparepart,
                    ps.status,
                    ps.qty_po,                 
                    ps.qty_ps                 
            )
        """)


