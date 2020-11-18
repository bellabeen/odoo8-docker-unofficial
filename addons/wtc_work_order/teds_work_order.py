from openerp import models, fields, api
import time
from datetime import datetime

class WorkOrder(models.Model):
    _inherit = "wtc.work.order"

    @api.onchange('type','branch_id')
    def onchange_type_new(self):
        self.payment_term = False
        self.kpb_ke = False
        self.type_customer = False
        self.prev_work_order_id = False
        item_ids = []
        if self.type and self.branch_id:
            if self.type == 'WAR':
                query = """
                   SELECT  id as work_order
                   FROM wtc_work_order 
                   WHERE date + cast(warranty as int)>current_date-1
                   AND branch_id = %d
                   AND state = 'done'
                """%(self.branch_id.id)
                self._cr.execute (query)
                ress =  self._cr.fetchall()
                item_ids = [res[0] for res in ress]
        domain = {'prev_work_order_id':[('id','in',item_ids)]}
        return {'domain':domain}

    @api.multi
    def action_clocking_reset(self):
        self.write({
            'state_wo':'in_progress', 
            'start':False,
            'date_break': False,
            'end_break':False,
            'finish':False 
        })

    @api.multi
    def button_dummy(self):
        price_tax = 0
        price_subtotal = 0
        for line in self.work_lines:
            price = line.price_unit * (1-(line.discount or 0.0) / 100.0)    
            taxes = line.tax_id.compute_all(price,line.product_qty,line.product_id)
            if taxes.get('taxes',False):
                price_tax += taxes.get('taxes',0)[0].get('amount',0)
                price_subtotal += taxes.get('total',0)
        amount_total = price_subtotal + price_tax
        update = """
            UPDATE wtc_work_order
            SET amount_untaxed = %d
            , amount_tax = %d
            , amount_total = %d
            WHERE id = %d
        """ %(price_subtotal,price_tax,amount_total,self.id)
        self._cr.execute(update)

    type_customer = fields.Selection([
        ('AHASS','AHASS'),
        ('Perorangan','Perorangan'),
        ('Non AHASS','Non AHASS')],string="Type Customer")
    
    @api.onchange('customer_id','type')
    def ocnhange_customerId(self):
        if self.type == 'SLS' and self.customer_id:
            self.driver_id = self.customer_id.id


class StartStop(models.Model):
    _inherit = "wtc.start.stop.wo"

    
    @api.onchange('work_order_id')
    def onchnage_wo_mekanik(self):
        ids = []
        if self.branch_id:
            ids_job = self.env['hr.job'].search([('sales_force','=','mechanic')])
            if ids_job:
                ids_employee = self.env['hr.employee'].search([
                    ('job_id','in',[job.id for job in ids_job]),
                    ('branch_id','=',self.branch_id.id)])
                ids = [employee.user_id.id for employee in ids_employee]
        domain = {'mekanik_id':[('id','=',ids)]}
        return {'domain':domain}

    
    @api.onchange('mekanik_id')
    def onchnage_mekanik(self):
        if self.mekanik_id :
            obj_employee = self.env['hr.employee']
            obj_search_empl = obj_employee.search([('user_id','=',self.mekanik_id.id)],limit=1)
            self.employee_id = obj_search_empl.id

   