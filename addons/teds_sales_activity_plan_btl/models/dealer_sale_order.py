from openerp import models, fields, api
from datetime import date, datetime, timedelta,time

class DealerSaleOrder(models.Model):
    _inherit = "dealer.sale.order"

    jaringan_penjualan = fields.Selection([
        ('Showroom','Showroom'),
        ('POS','POS'),
        ('Chanel/Mediator','Chanel/Mediator')],string="Jaringan Penjualan")
    sumber_penjualan_id = fields.Many2one('teds.act.type.sumber.penjualan','Sumber Penjualan')
    is_btl = fields.Boolean(related='sumber_penjualan_id.is_btl',string='BTL',readonly=True)
    activity_plan_id = fields.Many2one('teds.sales.plan.activity.line','Activity',domain=[('id','=',0)])
    titik_keramaian_id = fields.Many2one('titik.keramaian','Titik Keramaian',related='activity_plan_id.titik_keramaian_id',store=True,readonly=True)

    @api.onchange('jaringan_penjualan','sumber_penjualan_id','branch_id')
    def onchange_activity_plan(self):
        ids = []
        if self.jaringan_penjualan and self.sumber_penjualan_id and self.branch_id:
            now_date = date.today()
            now_month = now_date.month
            now_year = now_date.year
            query = """
                SELECT spl.id
                FROM teds_sales_plan_activity sp
                INNER JOIN teds_sales_plan_activity_line spl ON spl.activity_id = sp.id
                WHERE sp.branch_id = %s 
                AND sp.bulan = '%s'
                AND sp.tahun = '%s'
                AND spl.jaringan_penjualan = '%s'
                AND spl.act_type_id = %s
                AND spl.state = 'done'
            """ %(self.branch_id.id,now_month,now_year,self.jaringan_penjualan,self.sumber_penjualan_id.id)
            self._cr.execute (query)
            ress =  self._cr.fetchall()
            ids = [res[0] for res in ress]
        domain = {'activity_plan_id':[('id','in',ids)]}
        return {'domain':domain}

    @api.onchange('jaringan_penjualan')
    def onchange_jaringan_penjualan(self):
        self.sumber_penjualan_id = False

    @api.onchange('sumber_penjualan_id')
    def onchange_sumber_penjualan(self):
        self.activity_plan_id = False
        self.sales_source_location = False
    
