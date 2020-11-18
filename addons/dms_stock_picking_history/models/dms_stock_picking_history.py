from openerp import models, fields, api
from datetime import datetime, timedelta

class StockPickingHistory(models.Model):
    _name = "dms.stock.picking.history"
    _rec_name = "no_po_dms"

    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date()

    picking_id = fields.Many2one('stock.picking','No Picking',index=True)
    distribution_id = fields.Many2one('wtc.stock.distribution','No Distribution')
    no_po_dms = fields.Char('No Purchase Order DMS')
    origin  = fields.Char('Origin')
    date = fields.Date('Date',default=_get_default_date)
    unfield_dms_name = fields.Char('Unfield DMS')
    no_invoice = fields.Char('No Invoice')
    tgl_invoice = fields.Date('Tgl Invoice')
    division = fields.Selection([
        ('Unit','Unit'),
        ('Sparepart','Sparepart')])
    state = fields.Selection([
        ('draft','Draft'),
        ('done','Done'),
        ('error','Error')],default='draft',index=True)
    status_api = fields.Selection([
        ('draft','Draft'),
        ('done','Done'),
        ('error','Error')],default='draft',index=True)

    @api.multi
    def get_data_stock_picking(self):
        picking_query = """
            SELECT * FROM ( 
                SELECT 
                pic.id as picking_id
                , pic.division as division
                , pic.transaction_id as transaction
                , model.model as model
                , CASE WHEN model.model = 'wtc.mutation.order' THEN (
                SELECT dms_po_name
                FROM wtc_mutation_order
                WHERE id = pic.transaction_id
                ) 
                WHEN model.model = 'sale.order' THEN (
                SELECT dms_po_name
                FROM sale_order
                WHERE id = pic.transaction_id
                )
                END as no_po_dms
                FROM stock_picking as pic
                INNER JOIN wtc_branch b ON b.id = pic.branch_id
                INNER JOIN ir_model as model ON model.id = pic.model_id
                INNER  JOIN res_partner as part ON part.id = pic.partner_id
                WHERE pic.state in ('assigned','done')
                AND b.branch_type = 'MD'
                AND model.model in ('wtc.mutation.order','sale.order')
                AND pic.division in ('Unit','Sparepart') 
                AND pic.date > '2020-05-01 00:00:00'
                AND pic.id not in (select picking_id from dms_stock_picking_history)
                ORDER BY pic.id ASC
                LIMIT 100
            ) data WHERE no_po_dms is not null
        """
        self._cr.execute(picking_query)
        ress = self._cr.dictfetchall()
        if ress:
            for res in ress:
                picking_id = res.get('picking_id')
                division = res.get('division')
                transaction_id = res.get('transaction')
                model_name = res.get('model')
                
                picking_obj = self.env['stock.picking'].sudo().browse(picking_id)

                sale_and_mutation_order = self.env[model_name].sudo().search([('id','=',transaction_id)],limit=1)
                if not sale_and_mutation_order:
                    continue

                distribution_id = sale_and_mutation_order.distribution_id.id
                dms_po_origin = sale_and_mutation_order.distribution_id.dms_po_name

                if not dms_po_origin:
                    continue

                no_inv = False
                tgl_invoice = False
                if model_name == 'sale.order':
                    if sale_and_mutation_order.invoice_ids:
                        no_inv = sale_and_mutation_order.invoice_ids[0].number
                        tgl_invoice = sale_and_mutation_order.invoice_ids[0].date_invoice

                create = self.create({
                    'picking_id':picking_id,
                    'distribution_id':distribution_id,
                    'no_po_dms':dms_po_origin,
                    'division':division,
                    'no_invoice':no_inv,
                    'tgl_invoice':tgl_invoice,
                    'origin':sale_and_mutation_order.name
                })

                

