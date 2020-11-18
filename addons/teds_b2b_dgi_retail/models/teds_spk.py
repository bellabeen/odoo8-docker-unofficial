from openerp import models, fields, api

class SPK(models.Model):
    _inherit = "dealer.spk"

    md_reference_spk = fields.Char('MD Refrence SPK',index=True,help="ID SPK Main Dealer")
    md_reference_prospect = fields.Char('MD Refrence Prospect',index=True,help="ID Prospect Main Dealer")
    md_reference_lsng = fields.Char('MD Refrence Leasing',index=True,help="ID Leasing Main Dealer")
    note_log = fields.Text('Note Log')

class DealerSaleOrder(models.Model):
    _inherit = "dealer.sale.order"

    md_reference_prospect = fields.Char('MD Refrence Prospect',index=True,help="ID Prospect Main Dealer")
    md_reference_spk = fields.Char('MD Refrence SPK',index=True,help="ID SPK Main Dealer")
    md_reference_lsng = fields.Char('MD Refrence Leasing',index=True,help="ID Leasing Main Dealer")
    dgi_status_inv = fields.Selection([('draft','Draft'),('error','Error'),('done','Done')],default='draft',index=True) 
    
    