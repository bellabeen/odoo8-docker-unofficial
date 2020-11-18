from openerp import models, fields, api, _, SUPERUSER_ID
import time
from datetime import datetime
from openerp.osv import osv
import string
import openerp.addons.decimal_precision as dp

class wtc_surat_jalan(models.Model):
    _name = "wtc.surat.jalan"
    _description = "Surat Jalan"
    
    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()
    
    name = fields.Char('Surat Jalan')
    date = fields.Date('Date')
    state = fields.Selection([
                              ('draft','Draft'),
                              ('posted','Posted'),
                              ('cancelled','Cancelled'),
                              ], 'State', default='draft')
    branch_id = fields.Many2one('wtc.branch', 'Branch')
    division = fields.Selection([('Unit','Unit')], string='Division')
    picking_type_id = fields.Many2one('stock.picking.type', 'Picking Type')
    partner_id = fields.Many2one('res.partner','Partner')
    surat_jalan_lines = fields.One2many('wtc.surat.jalan.line','surat_jalan_id','Surat Jalan Line')
    cancel_uid = fields.Many2one('res.users',string="Cancelled by")
    cancel_date = fields.Datetime('Cancelled on')
    post_uid = fields.Many2one('res.users',string="Posted by")
    post_date = fields.Datetime('Posted on')
    
    @api.multi
    def get_sequence(self,branch_id,context=None):
        doc_code = self.env['wtc.branch'].browse(branch_id).doc_code
        seq_name = 'DVN/{0}'.format(doc_code)
        seq = self.env['ir.sequence']
        ids = seq.sudo().search([('name','=',seq_name)])
        if not ids:
            prefix = '/%(y)s/%(month)s/'
            prefix = seq_name + prefix
            ids = seq.create({'name':seq_name,
                                 'implementation':'standard',
                                 'prefix':prefix,
                                 'padding':5})
        
        return seq.get_id(ids.id)
    
    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Tidak bisa dihapus jika status bukan 'Draft' !"))
        return super(wtc_surat_jalan, self).unlink(cr, uid, ids, context=context)
    
    @api.multi
    def check_surat_jalan(self,packing_id):
        if all(line.surat_jalan_name!=False for line in packing_id.packing_line):
            packing_id.write({'surat_jalan':True})
    
    @api.multi
    def post_surat_jalan(self,context=None):
        self.name = self.get_sequence(self.branch_id.id,context)
        for lines in self.surat_jalan_lines:
            packing_line = self.env['wtc.stock.packing.line'].search([('packing_id','=',lines.packing_id.id),('serial_number_id','=',lines.lot_id.id)])
            if packing_line and packing_line.surat_jalan_name:
                raise osv.except_osv(('Perhatian !'), ("Unit %s di packing %s sudah diproses di surat jalan %s !") (lines.lot_id.name,lines.packing_id.name,packing_line.surat_jalan_name))
            elif not packing_line:
                raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan Unit %s di packing %s!") (lines.lot_id.name,lines.packing_id.name))
            else:
                packing_line.write({'surat_jalan_name':self.name})
            self.check_surat_jalan(lines.packing_id)
        self.state = 'posted'
        self.date=self._get_default_date()
        self.post_uid = self._uid
        self.post_date = datetime.now()
        
class wtc_surat_jalan_line(models.Model):
    _name = "wtc.surat.jalan.line"
    _description = "Stock Packing Line"
    
    surat_jalan_id = fields.Many2one('wtc.surat.jalan','Surat Jalan')
    packing_id = fields.Many2one('wtc.stock.packing','No. Packing')
    lot_id = fields.Many2one('stock.production.lot','Serial Number')
    product_id = fields.Many2one('product.product','Product')
    no_invoice = fields.Char('Surat Jalan')
    
    _sql_constraints = [('unique_lot_id', 'unique(surat_jalan_id,lot_id)', 'Ditemukan engine number duplicate, silahkan cek kembali !')]
    
    @api.onchange('packing_id','lot_id')
    def change_packing_lot(self):
        domain = {}
        lot_ids = []
        packing_line = self.env['wtc.stock.packing.line'].search([('packing_id','=',self.packing_id.id),('surat_jalan_name','=',False)])
        for line in packing_line:
            lot_ids.append(line.serial_number_id.id)
        domain['lot_id'] = [('id','in',lot_ids)]
        if self.lot_id:
            self.product_id=self.lot_id.product_id.id
            inv=self.env['account.invoice'].search([('origin','=',self.packing_id.picking_id.origin),('type','=','out_invoice')])
            self.no_invoice=inv.number
        return {'domain':domain}
    
    
    