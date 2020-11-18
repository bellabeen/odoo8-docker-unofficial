from openerp import models, fields, api, _
from openerp.osv import osv

class wtc_listing_incentive_sales(models.Model):
    _name = "wtc.listing.incentive.sales"
    _description = "Incentive Sales"
    
    @api.model
    def create(self,values):
        if not values['listing_incentive_sales_lines'] :
            raise osv.except_osv(('Perhatian !'), ('Tidak ada detail, tidak bisa disave!'))
        obj_check=self.search([('sales_force','=',values['sales_force']),('cluster','=',values['cluster'])])
        if obj_check :
            raise osv.except_osv(('Perhatian !'), ('Untuk Listing Incentive Seles %s dan Cluster %s Sudah Pernah diBuat' % (obj_check.sales_force,obj_check.cluster)))
        return  super(wtc_listing_incentive_sales,self).create(values)
    
    
    sales_force=fields.Selection([('salesman','Salesman'),('sales_counter','Sales Counter'),('sales_partner','Sales Partner')
                        ,('sales_koordinator','Sales Koordinator')],'Sales Force',required=True)
    cluster=fields.Selection([(' ',' '),('A','A'),('B','B'),('C','C')],'Cluster',required=True)
    listing_incentive_sales_lines=fields.One2many('wtc.listing.incentive.sales.line','listing_incentive_sales_id')
    
    
class wtc_listing_incentive_sales_line(models.Model):
    _name = "wtc.listing.incentive.sales.line"
    _description = "Incentive Sales Line"
    
    qty=fields.Float('Qty',required=True)
    cash=fields.Float('Cash')
    credit=fields.Float('Credit')
    reward=fields.Float('Reward')
    listing_incentive_sales_id=fields.Many2one('wtc.listing.incentive.sales')
    

class wtc_absensi(models.Model):
    _name = "wtc.absensi"
    _description = "Absensi"
    
    nip=fields.Char('Nip')
    bulan=fields.Char('Bulan')
    total_absensi=fields.Integer('Total Absensi')
    jumlah_hari_kerja=fields.Integer('Jumlah Hari Kerja')
    sp=fields.Integer('Sp')
    
    
    
    
class wtc_branch(models.Model):
    _inherit = 'wtc.branch'
    cluster=fields.Selection([('A','A'),('B','B'),('C','C')],'Cluster Incentive Sales')
    
    
