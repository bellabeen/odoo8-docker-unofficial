from openerp import models, fields, api
from datetime import datetime
import time

class ApiManualExecute(models.TransientModel):
    _name = "teds.api.manual.execute.api"

    jenis_api = fields.Selection([
        ('account_invoice', 'Account Invoice'),
        ('dealer_sale_order', 'Dealer Sale Order'),
        ('penerimaan_stnk', 'Penerimaan STNK'),
        ('penerimaan_bpkb', 'Penerimaan BPKB'),
        ('penyerahan_stnk', 'Penyerahan STNK'),
        ('penyerahan_bpkb', 'Penyerahan BPKB'),
        ('stock_picking_to_hoki', 'Surat Jalan'),
        ('stock_picking_whi', 'Penerimaan Cabang WHI'),
        ('stock_distribution_qty_approved', 'QTY Approved'),
        ('work_order', 'Work Order')
        ], string='Jenis API', required=True)
    name= fields.Char('No Transaksi', required=True)


    @api.multi
    def action_proses(self):
        if self.jenis_api == 'account_invoice' :
            self.env['account.invoice'].api_dms_account_invoice_manual(self.name)
        if self.jenis_api == 'stock_picking_to_hoki' :
            self.env['wtc.stock.packing'].api_dms_stock_picking_to_hoki_manual(self.name)
        if self.jenis_api == 'work_order' :
            self.env['wtc.work.order'].api_teds_work_order_manual(self.name)
        if self.jenis_api == 'stock_distribution_qty_approved' :
            self.env['wtc.stock.distribution'].api_stock_distribution_qty_approved_manual(self.name)
        






    

