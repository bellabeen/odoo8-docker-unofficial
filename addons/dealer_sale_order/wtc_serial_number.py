from openerp.osv import fields, osv

class wtc_serial_number(osv.osv):
    _inherit='stock.production.lot'
    _columns={
		'sale_order_reserved': fields.many2one('dealer.sale.order', string='Sales Order Reserved'),
		'dealer_sale_order_id': fields.many2one('dealer.sale.order',string='Dealer Sales Order'),
        'move_lines_invoice_bbn_id': fields.many2one('account.move.line',string='Entries Invoice BBN'),        
    }
