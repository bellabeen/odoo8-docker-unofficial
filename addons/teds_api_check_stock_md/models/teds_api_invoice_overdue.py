from datetime import timedelta,datetime,date
from openerp import models, fields, api
from dateutil.relativedelta import relativedelta

class ApiCheckStockMD(models.Model):
    _inherit = "teds.api.check.stock"

    @api.multi
    def overdue_invoice(self,vals):
        dealer_code = vals.get('dealer_code')
        jenis = vals.get('jenis')

             
        invoice_total = 0
        credit_limit_sparepart = 0
        ids = []
        if dealer_code:
            partner = self.env['res.partner'].sudo().search([('default_code','=',dealer_code)],limit=1)     
            if partner:
                credit_limit_sparepart = partner.credit_limit_sparepart

                obj_inv = self.env['account.invoice']
                tipe='md_sale_sparepart'
                    
                domain = [
                    ('partner_id', 'child_of',partner.id),
                    ('division','=','Sparepart'),
                    ('state','=','open'),
                    ('tipe','=',tipe),
                ]
                invoice_ids = obj_inv.search(domain,order='date_due ASC')
                for inv in invoice_ids:
                    if inv.amount_total <= 0:
                        continue
                    over = False
                    if datetime.strptime(inv.date_due,'%Y-%m-%d').date() < date.today():
                        over = True
                    if jenis == 'overdue':
                        date_overdue = date.today() + relativedelta(days=3)
                        if datetime.strptime(inv.date_due,'%Y-%m-%d').date() <= date_overdue:
                            ids.append({
                                'name':inv.number,
                                'date':inv.date_invoice,
                                'due_date':inv.date_due,
                                'total':inv.amount_total,
                                'over':over
                            })
                    elif jenis == 'outstanding':
                        date_outstanding = date.today() + relativedelta(days=7)
                        if datetime.strptime(inv.date_due,'%Y-%m-%d').date() <= date_outstanding:
                           ids.append({
                                'name':inv.number,
                                'date':inv.date_invoice,
                                'due_date':inv.date_due,
                                'total':inv.amount_total,
                                'over':over
                            })
                           
                    
                    invoice_total += inv.residual

        sisa_plafon = credit_limit_sparepart - invoice_total
        data = {
            'invoice_total':invoice_total,
            'credit_limit_sparepart':credit_limit_sparepart,
            'sisa_plafon':sisa_plafon,
            'detail':ids
        }
        return {'data':data}