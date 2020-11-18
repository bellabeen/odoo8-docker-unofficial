from openerp import models, fields, api, _, SUPERUSER_ID
import time
from datetime import datetime
from openerp.osv import osv
import string
import openerp.addons.decimal_precision as dp

class wtc_stock_packing(models.Model):
    _name = "wtc.stock.packing"
    _description = "Stock Packing"
    
    def _is_reverse(self):
        reverse_incoming = self.rel_code == 'outgoing' and self.rel_destination_location_id.usage == 'supplier'
        reverse_outgoing = self.rel_code == 'incoming' and self.rel_source_location_id.usage == 'customer'
        self.is_reverse = reverse_incoming or reverse_outgoing
    
    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()
    
    name = fields.Char('Packing')
    state = fields.Selection([
                              ('draft','Draft'),
                              ('surat_jalan','Surat Jalan'),
                              ('posted','Posted'),
                              ('cancelled','Cancelled'),
                              ], 'State', default='draft')
    picking_id = fields.Many2one('stock.picking', 'Picking')
    branch_id = fields.Many2one('wtc.branch', 'Branch')
    division = fields.Selection([('Unit','Unit')], string='Division')
    picking_type_id = fields.Many2one('stock.picking.type', 'Picking Type')
    source_location_id = fields.Many2one('stock.location', 'Source Location')
    destination_location_id = fields.Many2one('stock.location', 'Destination Location')
    rel_picking_type_id = fields.Many2one('stock.picking.type', string='Picking Type')
    rel_branch_id = fields.Many2one('wtc.branch', string='Branch')
    rel_source_location_id = fields.Many2one('stock.location', string='Source Location')
    rel_destination_location_id = fields.Many2one('stock.location', string='Destination Location')
    nrfs_location = fields.Many2one('stock.location', 'NRFS Location')
    rel_origin = fields.Char(string='Source Document')
    rel_partner_id = fields.Many2one('res.partner', string='Partner')
    branch_sender_id = fields.Many2one('wtc.branch', 'Branch Sender')
    expedition_id = fields.Many2one('res.partner','Expedition')
    kota_penerimaan = fields.Selection([
                              ('lampung','Lampung'),
                              ], 'Kota Penerimaan')
    plat_number_id = fields.Many2one('wtc.plat.number.line','Plat Number')
    driver_id = fields.Many2one('wtc.driver.line','Driver')
    date = fields.Date('Date')
    rel_division = fields.Selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum')], string='Division')
    rel_code = fields.Char(string='Code')
    rel_branch_type = fields.Char(string='Branch Type')
    is_reverse = fields.Boolean(compute='_is_reverse', string="Is Reverse", method=True)
    packing_line = fields.One2many('wtc.stock.packing.line', 'packing_id', 'Packing Line')
    packing_line2 = fields.One2many('wtc.stock.packing.line', 'packing_id', 'Packing Line')
    packing_line3 = fields.One2many('wtc.stock.packing.line', 'packing_id', 'Packing Line')
    packing_line4 = fields.One2many('wtc.stock.packing.line', 'packing_id', 'Packing Line')
    packing_line5 = fields.One2many('wtc.stock.packing.line', 'packing_id', 'Packing Line')
    packing_line6 = fields.One2many('wtc.stock.packing.line', 'packing_id', 'Packing Line')
    packing_line7 = fields.One2many('wtc.stock.packing.line', 'packing_id', 'Packing Line')
    packing_line8 = fields.One2many('wtc.stock.packing.line', 'packing_id', 'Packing Line')
    rel_serial_number_id = fields.Char(related='packing_line.serial_number_id.name', string='Serial Number')
    move_id = fields.Many2one('account.move', 'Journal Item')
    surat_jalan = fields.Boolean(string="Surat Jalan")
    date_in = fields.Date(string='Date In')
    
    def print_wizard(self,cr,uid,ids,context=None):
        obj_claim_kpb = self.browse(cr,uid,ids)
        obj_ir_view = self.pool.get("ir.ui.view")
        obj_ir_view_search= obj_ir_view.search(cr,uid,[("name", "=", 'wtc.stock.packing.wizard.print'), ("model", "=", 'wtc.stock.packing'),])
        obj_ir_view_browse = obj_ir_view.browse(cr,uid,obj_ir_view_search)
        return {
            'name': 'Print',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.stock.packing',
            'type': 'ir.actions.act_window',
            'view_id' : obj_ir_view_browse.id,
            'nodestroy': True,
            'target': 'new',
            'res_id': obj_claim_kpb.id
            }
    
    def write(self, cr, uid, ids, vals, context=None):
        packing_id = self.browse(cr, uid, ids, context=context)
        if packing_id.state=='posted':
            raise osv.except_osv(('Perhatian !'), ("Transaksi sudah di post oleh user lain !"))
        #<!-- 1 incoming-unit-dealer, incoming-unit-maindealer-new -->
            #if (packing_id.rel_code == 'incoming' and packing_id.rel_division == 'Unit' and packing_id.rel_branch_type == 'DL' and not packing_id.is_reverse) or not packing_id.picking_id :
            #     vals.get('packing_line', []).sort(reverse=True)
            #     vals.pop('packing_line2',None)
            #     vals.pop('packing_line3',None)
            #     vals.pop('packing_line4',None)
            #     vals.pop('packing_line5',None)
            #     vals.pop('packing_line6',None)
            #     vals.pop('packing_line7',None)
            #     vals.pop('packing_line8',None)
            # #<!-- 2 outgoing-unit-dealer, interbranch_out-unit-dealer, interbranch_in-unit-dealer -->
            #elif packing_id.rel_code in ('outgoing','interbranch_out','interbranch_in') and packing_id.rel_division == 'Unit' and packing_id.rel_branch_type == 'DL' and not packing_id.is_reverse :
            #     vals.get('packing_line2', []).sort(reverse=True)
            #     vals.pop('packing_line',None)
            #     vals.pop('packing_line3',None)
            #     vals.pop('packing_line4',None)
            #     vals.pop('packing_line5',None)
            #     vals.pop('packing_line6',None)
            #     vals.pop('packing_line7',None)
            #     vals.pop('packing_line8',None)
            # #<!-- 3 incoming-sparepart-dealer, incoming-umum-dealer, incoming-sparepart-maindealer, incoming-umum-maindealer -->
            #elif packing_id.rel_code == 'incoming' and packing_id.rel_division in ('Sparepart','Umum') and not packing_id.is_reverse :
            #     vals.get('packing_line3', []).sort(reverse=True)
            #     vals.pop('packing_line',None)
            #     vals.pop('packing_line2',None)
            #     vals.pop('packing_line4',None)
            #     vals.pop('packing_line5',None)
            #     vals.pop('packing_line6',None)
            #     vals.pop('packing_line7',None)
            #     vals.pop('packing_line8',None)
            # #<!-- 4 outgoing-sparepart-dealer, outgoing-umum-dealer, interbranch_out-sparepart-dealer, interbranch_out-umum-dealer, interbranch_in-sparepart-dealer, interbranch_in-umum-dealer,
            # #outgoing-sparepart-maindealer, outgoing-umum-maindealer, interbranch_out-sparepart-maindealer, interbranch_out-umum-maindealer, interbranch_in-sparepart-maindealer, interbranch_in-umum-maindealer -->
            #elif packing_id.rel_code in ('outgoing','interbranch_out','interbranch_in') and packing_id.rel_division in ('Sparepart','Umum') and not packing_id.is_reverse :
            #     vals.get('packing_line4', []).sort(reverse=True)
            #     vals.pop('packing_line',None)
            #     vals.pop('packing_line2',None)
            #     vals.pop('packing_line3',None)
            #     vals.pop('packing_line5',None)
            #     vals.pop('packing_line6',None)
            #     vals.pop('packing_line7',None)
            #     vals.pop('packing_line8',None)
            # #<!-- 5 reverse-incoming-unit-dealer, reverse-outgoing-unit-dealer, reverse-incoming-unit-maindealer, reverse-outgoing-unit-maindealer -->
            #if ((packing_id.rel_code in ('incoming','outgoing') and packing_id.rel_branch_type == 'DL') or (packing_id.rel_code in ('incoming','outgoing') and packing_id.rel_branch_type == 'MD')) and packing_id.rel_division == 'Unit' and packing_id.is_reverse :
            #     vals.get('packing_line5', []).sort(reverse=True)
            #     vals.pop('packing_line',None)
            #     vals.pop('packing_line2',None)
            #     vals.pop('packing_line3',None)
            #     vals.pop('packing_line4',None)
            #     vals.pop('packing_line6',None)
            #     vals.pop('packing_line7',None)
            #     vals.pop('packing_line8',None)
            # #<!-- 6 reverse-incoming-sparepart-dealer, reverse-incoming-umum-dealer, reverse-outgoing-sparepart-dealer, reverse-outgoing-umum-dealer, reverse-outgoing-sparepart-maindealer, reverse-outgoing-umum-maindealer -->
            #elif ((packing_id.rel_code in ('incoming','outgoing') and packing_id.rel_division in ('Sparepart','Umum') and packing_id.rel_branch_type == 'DL') or (packing_id.rel_code in ('incoming','outgoing') and packing_id.rel_division in ('Sparepart','Umum') and packing_id.rel_branch_type == 'MD')) and packing_id.is_reverse :
            #     vals.get('packing_line6', []).sort(reverse=True)
            #     vals.pop('packing_line',None)
            #     vals.pop('packing_line2',None)
            #     vals.pop('packing_line3',None)
            #     vals.pop('packing_line4',None)
            #     vals.pop('packing_line5',None)
            #     vals.pop('packing_line7',None)
            #     vals.pop('packing_line8',None)
            # #<!-- 7 incoming-unit-maindealer -->
            #elif packing_id.rel_code == 'incoming' and packing_id.rel_division == 'Unit' and packing_id.rel_branch_type == 'MD' and not packing_id.is_reverse :
            #     vals.get('packing_line7', []).sort(reverse=True)
            #     vals.pop('packing_line',None)
            #     vals.pop('packing_line2',None)
            #     vals.pop('packing_line3',None)
            #     vals.pop('packing_line4',None)
            #     vals.pop('packing_line5',None)
            #     vals.pop('packing_line6',None)
            #     vals.pop('packing_line8',None)
            # #<!-- 8 outgoing-unit-maindealer, interbranch_out-unit-maindealer, interbranch_in-unit-maindealer -->
            #elif packing_id.rel_code in ('outgoing','interbranch_out','interbranch_in') and packing_id.rel_division == 'Unit' and packing_id.rel_branch_type == 'MD' and not packing_id.is_reverse :
            #     vals.get('packing_line8', []).sort(reverse=True)
            #     vals.pop('packing_line',None)
            #     vals.pop('packing_line2',None)
            #     vals.pop('packing_line3',None)
            #     vals.pop('packing_line4',None)
            #     vals.pop('packing_line5',None)
            #     vals.pop('packing_line6',None)
            #     vals.pop('packing_line7',None)
        
        if packing_id.rel_code == 'interbranch_out' and packing_id.rel_division == 'Unit' and packing_id.rel_branch_type == 'DL' and not packing_id.is_reverse :
            filter_ids_move = packing_id.picking_id.filter_ids_move()
            obj_quant = self.pool.get('stock.quant')
            obj_packing_line = self.pool.get('wtc.stock.packing.line')
            for line in vals.get('packing_line', []) :
                if line[0] == 1 and line[2].get('serial_number_id') or line[0] == 2 :
                    packing_line = obj_packing_line.browse(cr, uid, line[1])
                    id_quant = obj_quant.search(cr, SUPERUSER_ID, [('lot_id','=',packing_line.serial_number_id.id)])
                    obj_quant.write(cr, SUPERUSER_ID, id_quant, {'reservation_id':False})
                if line[0] == 1 and line[2].get('serial_number_id') or line[0] == 0 :
                    id_quant = obj_quant.search(cr, SUPERUSER_ID, [('lot_id','=',line[2].get('serial_number_id'))])
                    prod_id = line[2].get('product_id')
                    if not prod_id :
                        prod_id = obj_packing_line.browse(cr, SUPERUSER_ID, line[1]).product_id.id
                    obj_quant.write(cr, SUPERUSER_ID, id_quant, {'reservation_id':filter_ids_move[prod_id][0]})
                    
        elif packing_id.rel_code in ('outgoing','interbranch_out') and packing_id.rel_branch_type == 'MD' and packing_id.rel_division == 'Unit' and not packing_id.is_reverse :
            filter_ids_move = packing_id.picking_id.filter_ids_move()
            obj_quant = self.pool.get('stock.quant')
            obj_packing_line = self.pool.get('wtc.stock.packing.line')
            
            for line in vals.get('packing_line', []) :
                if line[0] == 1 and line[2].get('serial_number_id') or line[0] == 2 :
                    packing_line = obj_packing_line.browse(cr, uid, line[1])
                    id_quant = obj_quant.search(cr, SUPERUSER_ID, [('lot_id','=',packing_line.serial_number_id.id)])
                    obj_quant.write(cr, SUPERUSER_ID, id_quant, {'reservation_id':False})
                if line[0] == 1 and line[2].get('serial_number_id') or line[0] == 0 :
                    id_quant = obj_quant.search(cr, SUPERUSER_ID, [('lot_id','=',line[2].get('serial_number_id'))])
                    prod_id = line[2].get('product_id')
                    if not prod_id :
                        prod_id = obj_packing_line.browse(cr, SUPERUSER_ID, line[1]).product_id.id
                    obj_quant.write(cr, SUPERUSER_ID, id_quant, {'reservation_id':filter_ids_move[prod_id][0]})
        
        elif packing_id.rel_code == 'outgoing' and packing_id.rel_branch_type == 'DL' and packing_id.rel_division == 'Unit' and packing_id.is_reverse :
            filter_ids_move = packing_id.picking_id.filter_ids_move()
            obj_quant = self.pool.get('stock.quant')
            obj_packing_line = self.pool.get('wtc.stock.packing.line')
            for line in vals.get('packing_line', []) :
                if line[0] == 1 and line[2].get('serial_number_id') or line[0] == 2 :
                    packing_line = obj_packing_line.browse(cr, uid, line[1])
                    if packing_line.serial_number_id:
                        id_quant = obj_quant.search(cr, SUPERUSER_ID, [('lot_id','=',packing_line.serial_number_id.id)])
                        if id_quant:
                            obj_quant.write(cr, SUPERUSER_ID, id_quant, {'reservation_id':False})
                if line[0] == 1 and line[2].get('serial_number_id') or line[0] == 0 :
                    id_quant = obj_quant.search(cr, SUPERUSER_ID, [('lot_id','=',line[2].get('serial_number_id'))])
                    prod_id = line[2].get('product_id')
                    if not prod_id :
                        prod_id = obj_packing_line.browse(cr, SUPERUSER_ID, line[1]).product_id.id
                    obj_quant.write(cr, SUPERUSER_ID, id_quant, {'reservation_id':filter_ids_move[prod_id][0]})
                    
        if packing_id.rel_code in ('outgoing','interbranch_out') or packing_id.is_reverse :
            self.renew_available_and_reserved(cr, uid, ids, context)
        return super(wtc_stock_packing, self).write(cr, uid, ids, vals, context=context)
    
    @api.one
    def renew_available_and_reserved(self):
        ids_move = self.picking_id.get_ids_move()
        for packing_line in self.packing_line :
            if self.is_reverse and not self.picking_id.is_unconsolidated_reverse:
                stock_available = 0
                current_reserved = self.picking_id.get_current_reserved(packing_line.product_id.id,packing_line.source_location_id.id,ids_move)
            elif packing_line.product_id.categ_id.isParentName('Extras') :
                stock_available = self.picking_id.get_stock_available_extras(packing_line.product_id.id, packing_line.source_location_id.id)
                current_reserved = self.picking_id.get_current_reserved(packing_line.product_id.id,packing_line.source_location_id.id,ids_move)
            
            elif self.picking_id.is_unconsolidated_reverse:
                stock_available = self.picking_id.get_stock_available_unconsolidated(packing_line.product_id.id, packing_line.source_location_id.id)
                current_reserved = self.picking_id.get_current_reserved(packing_line.product_id.id,packing_line.source_location_id.id,ids_move)
            else :
                stock_available = self.picking_id.get_stock_available(packing_line.product_id.id, packing_line.source_location_id.id)
                current_reserved = self.picking_id.get_current_reserved(packing_line.product_id.id,packing_line.source_location_id.id,ids_move)
            packing_line.write({'stock_available':stock_available, 'current_reserved':current_reserved})
    
    @api.multi
    def _is_over_qty(self):
        todo_move = {}
        qty = {}
        for packing_line in self.packing_line :
            if packing_line.quantity <= 0 :
                raise osv.except_osv(('Perhatian !'), ("Quantity tidak boleh nol atau kurang dari 1 !"))
            if packing_line.serial_number_id and packing_line.quantity > 1:
                raise osv.except_osv(('Perhatian !'), ("Quantity %s tidak boleh lebih dari 1 !")%(packing_line.serial_number_id.name))
            qty[packing_line.product_id] = qty.get(packing_line.product_id,0) + packing_line.quantity
            if qty[packing_line.product_id] > packing_line.seharusnya :
                raise osv.except_osv(('Perhatian !'), ("Quantity product '%s' melebihi qty seharusnya\nsilahkan cek kembali !" %packing_line.product_id.name))
            if packing_line.product_id not in todo_move :
                todo_move[packing_line.product_id] = {packing_line.source_location_id : 0}
            else :
                todo_move[packing_line.product_id].update({packing_line.source_location_id : 0})
        
        if self.rel_code in ('outgoing','interbranch_out','interbranch_in') or self.is_reverse :
            for packing_line in self.packing_line :
                todo_move[packing_line.product_id][packing_line.source_location_id] += packing_line.quantity
                if todo_move[packing_line.product_id][packing_line.source_location_id] > (packing_line.stock_available + packing_line.current_reserved) :
                    raise osv.except_osv(('Perhatian !'), ("Quantity product '%s' melebihi current reserve dan stock available\nsilahkan cek kembali Quantity: %s, Current Reverse: %s, Stock Available: %s!" %(packing_line.product_id.name,todo_move[packing_line.product_id][packing_line.source_location_id],packing_line.current_reserved,packing_line.stock_available)))
    
    @api.multi
    def _check_serial_number(self):
        for packing_line in self.packing_line :
            if self.is_reverse or (self.rel_code in ('outgoing','interbranch_out','interbranch_in') and self.rel_division == 'Unit') or (self.rel_code == 'incoming' and self.rel_branch_type == 'MD') :
                if packing_line.product_id.categ_id.isParentName('Unit') and not packing_line.serial_number_id :
                    raise osv.except_osv(('Perhatian !'), ("Silahkan isi Serial Number untuk produk '%s'" %packing_line.product_id.name))
        return True
    
    @api.multi
    def _update_lot(self, picking_id):
        if self.rel_division == "Unit" or not self.picking_id :
            if self.rel_code == "interbranch_out" and not self.is_reverse :
                for packing_line in self.packing_line :
                    packing_line.serial_number_id.write({'location_id':packing_line.destination_location_id.id,'picking_id':self.picking_id.id,'branch_id':self.rel_branch_id.id,'ready_for_sale':packing_line.convert_rfs(packing_line.rel_ready_for_sale) or packing_line.convert_rfs(packing_line.ready_for_sale),'performance_hpp':packing_line.performance_hpp})
            elif self.rel_code in ("outgoing","interbranch_in") and not self.is_reverse :
                for packing_line in self.packing_line :
                    if self.rel_code == 'outgoing' and self.rel_branch_type == 'MD' :
                        packing_line.serial_number_id.write({'location_id':packing_line.destination_location_id.id,'picking_id':self.picking_id.id,'branch_id':self.rel_branch_id.id,'ready_for_sale':packing_line.convert_rfs(packing_line.rel_ready_for_sale) or packing_line.convert_rfs(packing_line.ready_for_sale),'state':'sold','dealer_id':packing_line.packing_id.rel_partner_id.id,'sales_md_date':packing_line.packing_id.picking_id.date,'do_md_date':self._get_default_date()})
                    else :
                        packing_line.serial_number_id.write({'location_id':self.get_destination_location(packing_line.ready_for_sale, packing_line.rel_ready_for_sale, packing_line.destination_location_id.id),'picking_id':self.picking_id.id,'branch_id':self.rel_branch_id.id,'ready_for_sale':packing_line.convert_rfs(packing_line.rel_ready_for_sale) or packing_line.convert_rfs(packing_line.ready_for_sale),'in_date': self._get_default_date()})
            elif self.rel_code == 'incoming' and self.is_reverse :
                for packing_line in self.packing_line :
                    packing_line.serial_number_id.write({'location_id':self.get_destination_location(packing_line.ready_for_sale, packing_line.rel_ready_for_sale, packing_line.destination_location_id.id),'picking_id':self.picking_id.id,'branch_id':self.rel_branch_id.id,'ready_for_sale':packing_line.convert_rfs(packing_line.rel_ready_for_sale) or packing_line.convert_rfs(packing_line.ready_for_sale),'state':'stock'})
            elif self.branch_id.branch_type == 'MD' and not self.picking_id :
                for packing_line in self.packing_line :

                    
                    packing_line.serial_number_id.write({
                        'location_id':self.get_destination_location(packing_line.ready_for_sale, packing_line.rel_ready_for_sale, packing_line.destination_location_id.id),
                        'picking_id':picking_id.id,
                        'receipt_id':picking_id.id,
                        'ready_for_sale':packing_line.convert_rfs(packing_line.ready_for_sale),
                        'state':'stock',
                        'po_date':picking_id.date,
                        'receive_date':self._get_default_date(),
                        'supplier_id':picking_id.partner_id.id,
                        'expedisi_id':self.expedition_id.id,
                        'freight_cost':packing_line.freight_cost,
                        
                        })
            elif self.branch_id.branch_type == 'MD' and self.is_reverse:
                 for packing_line in self.packing_line :
                    packing_line.serial_number_id.write({
                         'state':'stock',
                         'location_id':packing_line.destination_location_id.id
                         })
    
    @api.multi
    def _delete_lot(self):
        if self.rel_code == 'outgoing' and self.is_reverse :
            for packing_line in self.packing_line :
                if packing_line.serial_number_id:
                    packing_line.write({'engin_number':'X'+packing_line.serial_number_id.name,'chassis_number':'X'+packing_line.serial_number_id.chassis_no})
                    packing_line.serial_number_id.write({'state':'cancelled','name':'X'+packing_line.serial_number_id.name,'chassis_no':'X'+packing_line.serial_number_id.chassis_no})
                    
    @api.multi
    def _update_sj_name_packing_line(self,name):
        if (self.rel_branch_id.branch_type!='MD') or (self.rel_branch_id.branch_type=='MD' and self.rel_code not in ('outgoing','interbranch_out')):
            for packing_line in self.packing_line:
                packing_line.write({'surat_jalan_name':name})
                
    @api.multi
    def _update_packing(self):
        if self.name :
            self.write({'state':'posted', 'date':self._get_default_date()})
        else :
            sequence = self.env['ir.sequence'].get_id(self.rel_picking_type_id.sequence_id.id or self.picking_type_id.sequence_id.id)
            self.write({'name':sequence, 'state':'posted', 'date':self._get_default_date()})
            
    @api.multi
    def _write_quants(self):
        if (self.rel_code == 'incoming' and self.rel_branch_type == 'MD' and not self.is_reverse) or (self.picking_type_id.code == 'incoming' and self.branch_id.branch_type == 'MD') :
            if self.picking_id and (self.picking_id.partner_id.id!=self.picking_id.branch_id.default_supplier_id.id):
                return True

            for packing_line in self.packing_line :
                if packing_line.product_id.categ_id.isParentName('Unit'):
                    quant_id = self.env['stock.quant'].sudo().search([('lot_id','=',packing_line.serial_number_id.id)])
                    quant_id.sudo().write({'consolidated_date':self._get_default_date(), 'cost':quant_id.cost + packing_line.serial_number_id.freight_cost})
                elif packing_line.product_id.categ_id.isParentName('Sparepart'):
                    quant_ids = self.env['stock.quant'].sudo().search([
                        ('product_id','=',packing_line.product_id.id),
                        ('qty','=',packing_line.quantity),
                        ('location_id','=',packing_line.destination_location_id.id),
                        ('consolidated_date','=',False)
                        ])
                    move_id = self.env['stock.move'].search([('picking_id','=',packing_line.packing_id.picking_id.id),('product_id','=',packing_line.product_id.id)])
                    for quant_id in quant_ids :
                        quant_id.sudo().write({'consolidated_date':self._get_default_date(), 'cost':move_id.price_unit/1.1*quant_id.qty})
    
    @api.multi
    def _check_freight_cost(self):
        if self.branch_id.branch_type == 'MD' and not self.picking_id :
            for packing_line in self.packing_line :
                    freight_cost = self.branch_id.get_freight_cost_md(self.expedition_id.id,packing_line.product_id.id,self.kota_penerimaan,self.branch_id.id)
                    if freight_cost != 0 :
                        packing_line.write({'freight_cost':freight_cost})
                    else :
                        raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan harga Ekspedisi untuk Product '%s' !" %packing_line.product_id.name))
    
    @api.multi
    def _prepare_account_move_line(self, id_journal, picking_id):
        jurnal_hutang_ekspedisi_id = self.env['account.journal'].search([('id','=',id_journal)])
        if not jurnal_hutang_ekspedisi_id.default_credit_account_id :
            raise osv.except_osv(('Perhatian !'), ("Silahkan isi Default Credit Account utk Jurnal Hutang Ekspedisi '%s' !" %self.branch_id.name))
        id_valuation_account = False
        id_uom = False
        qty = 0
        freight_cost = 0
        for packing_line in self.packing_line :
            if not id_valuation_account :
                id_valuation_account = packing_line.product_id.categ_id.property_stock_valuation_account_id.id
            qty += packing_line.quantity
            freight_cost += packing_line.freight_cost
        if not id_valuation_account :
            raise osv.except_osv(('Perhatian !'), ("Silahkan isi Stock Valuation Account utk kategori produk yang akan ditransfer !"))
        debit_line_vals = {
            'branch_id': self.branch_id.id,
            'division': self.division,
            'name': "Hutang Ekspedisi '%s'" %self.name,
            'quantity': qty,
            'ref': picking_id.name,
            'date':self._get_default_date(),
            'partner_id': self.expedition_id.id,
            'debit': freight_cost,
            'credit': 0,
            'account_id': id_valuation_account,
            }
        credit_line_vals = {
            'branch_id': self.branch_id.id,
            'division': self.division,
            'name': "Hutang Ekspedisi '%s'" %self.name,
            'quantity': qty,
            'ref': picking_id.name,
            'date': self._get_default_date(),
            'partner_id': self.expedition_id.id,
            'debit': 0,
            'credit': freight_cost,
            'account_id': jurnal_hutang_ekspedisi_id.default_credit_account_id.id,
            }
        return [(0, 0, debit_line_vals), (0, 0, credit_line_vals)]
    
    @api.multi
    def _create_journal_freight_cost(self, picking_id):
        if self.picking_type_id.code == 'incoming' and self.division == 'Unit' and self.branch_id.branch_type == 'MD' :
            branch_config_id = self.env['wtc.branch.config'].search([('branch_id','=',self.branch_id.id)])
            id_journal = branch_config_id.freight_cost_journal_id.id
            if not id_journal :
                raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan Jurnal Hutang Ekspedisi untuk '%s'\nsilahkan isi di Branch Config !" %self.branch_id.name))
            move_lines = self._prepare_account_move_line(id_journal, picking_id)
            period_id = self.env['account.period'].find(dt=self._get_default_date().date())
            account_move_vals = {
               'name': self.name, 
               'journal_id': id_journal,
               'line_id': move_lines,
               'period_id': period_id.id,
               'date':self._get_default_date(),
               'ref': picking_id.name
               }
            return self.env['account.move'].create(account_move_vals)
    
    @api.multi
    def _create_stock_move(self, picking_id, packing_lines):
        todo_moves = []
        for packing_line in packing_lines :
            if not packing_line.purchase_line_id :
                if not packing_line.serial_number_id.purchase_order_id :
                    raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan No PO utk Serial Number '%s' !"%packing_line.serial_number_id.name))
                for order_line in packing_line.serial_number_id.purchase_order_id.order_line :
                    if packing_line.product_id == order_line.product_id :
                        packing_line.purchase_line_id = order_line.id
                        break
            move_vals = {
                'branch_id': packing_line.purchase_line_id.order_id.branch_id.id,
                'categ_id': packing_line.purchase_line_id.product_id.categ_id.id,
                'name': packing_line.purchase_line_id.name or '',
                'product_id': packing_line.purchase_line_id.product_id.id,
                'product_uom': packing_line.purchase_line_id.product_uom.id,
                'product_uos': packing_line.purchase_line_id.product_uom.id,
                'product_uom_qty': packing_line.quantity,
                'product_uos_qty': packing_line.quantity,
                'date': packing_line.purchase_line_id.order_id.date_order,
                'date_expected': packing_line.purchase_line_id.order_id.end_date,
                'location_id': packing_line.purchase_line_id.order_id.picking_type_id.default_location_src_id.id,
                'location_dest_id': packing_line.purchase_line_id.order_id.location_id.id,
                'picking_id': picking_id.id,
                'partner_id': packing_line.purchase_line_id.order_id.dest_address_id.id or packing_line.purchase_line_id.order_id.partner_id.id,
                'move_dest_id': False,
                'state': 'draft',
                'purchase_line_id': packing_line.purchase_line_id.id,
                'company_id': packing_line.purchase_line_id.order_id.company_id.id,
                'price_unit': packing_line.serial_number_id.hpp*1.1,
                'picking_type_id': packing_line.purchase_line_id.order_id.picking_type_id.id,
                'procurement_id': False,
                'origin': packing_line.purchase_line_id.order_id.name,
                'route_ids': packing_line.purchase_line_id.order_id.picking_type_id.warehouse_id and [(6, 0, [x.id for x in packing_line.purchase_line_id.order_id.picking_type_id.warehouse_id.route_ids])] or [],
                'warehouse_id':packing_line.purchase_line_id.order_id.picking_type_id.warehouse_id.id,
                'invoice_state': packing_line.purchase_line_id.order_id.invoice_method == 'picking' and '2binvoiced' or 'none',
                }
            stock_move_id = self.env['stock.move'].create(move_vals)
            todo_moves.append(stock_move_id.id)
        todo_moves = self.env['stock.move'].search([('id','in',todo_moves)]).action_confirm()
        self.env['stock.move'].search([('id','in',todo_moves)]).force_assign()
    
    @api.multi
    def _create_picking(self):
        order = self.packing_line[0].serial_number_id.purchase_order_id
        picking_vals = {
            'picking_type_id': self.picking_type_id.id,
            'partner_id': order.dest_address_id.id or order.partner_id.id,
            'date': order.date_order,
            'start_date': order.start_date,
            'end_date': order.end_date,
            'origin': False,
            'branch_id': self.branch_id.id,
            'division': self.division,
            # 'transaction_id': order.id,
            # 'model_id': self.pool.get('ir.model').search(cr,uid,[('model','=',order.__class__.__name__)])[0],
            }
        picking_id = self.env['stock.picking'].create(picking_vals)
        self._create_stock_move(picking_id, self.packing_line)
        return picking_id
    
    @api.multi
    def _check_lot_state(self, serial_number_id):
        if serial_number_id.state != 'intransit' :
            raise osv.except_osv(('Perhatian !'), ("Serial Number '%s' statusnya bukan intransit\nSerial Number mungkin sudah diterima sebelumnya dengan Packing yg berbeda !" %serial_number_id.name))
    
    @api.multi
    def _write_account_move(self, picking_id):
        move_ids = self.env['account.move'].search([('ref','=',picking_id.name)])
        if move_ids :
            move_ids.write({'name':self.name})
    
    @api.multi
    def get_destination_location(self, rfs, rel_rfs, id_dest_location):
        if (self.picking_type_id.code in ('incoming','interbranch_in') and self.division == 'Unit') or (self.rel_code in ('incoming','interbranch_in') and self.rel_division == 'Unit'):
            if self.rel_branch_type == 'DL' and ((self.rel_code == 'interbranch_in' and not self.is_reverse) or (self.rel_code == 'incoming' and self.is_reverse)):
                if not rel_rfs :
                    if not self.nrfs_location :
                        raise osv.except_osv(('Perhatian !'), ("Silahkan isi NRFS Location terlebih dahulu !"))
                    return self.nrfs_location.id
            else :
                if not rfs :
                    if not self.nrfs_location :
                        raise osv.except_osv(('Perhatian !'), ("Silahkan isi NRFS Location terlebih dahulu !"))
                    return self.nrfs_location.id
        return id_dest_location
    
    @api.multi
    def _create_nrfs(self):
        pass
    
    @api.one
    def post_md(self):
        if not self.packing_line :
            raise osv.except_osv(('Perhatian !'), ("Tidak bisa di Post, silahkan tambahkan produk !"))
        if self.state == 'draft' and self.branch_id.branch_type == 'MD' and self.picking_type_id.code == 'incoming' and self.division == 'Unit' and not self.picking_id and not self.is_reverse :
           
            for packing_line in self.packing_line :
                self._check_lot_state(packing_line.serial_number_id)
            
            self._check_freight_cost()
            picking_id = self._create_picking()
            self._update_lot(picking_id)
            
            processed_ids = []
            # Create new and update existing pack operations
            for prod in self.packing_line :
                pack_datas = {
                    'product_id': prod.product_id.id,
                    'product_uom_id': prod.product_id.uom_id.id,
                    'product_qty': prod.quantity,
                    'lot_id': prod.serial_number_id.id,
                    'location_id': prod.source_location_id.id,
                    'location_dest_id': self.get_destination_location(prod.ready_for_sale, prod.rel_ready_for_sale, prod.destination_location_id.id),
                    'date': self._get_default_date(),
                    'owner_id': picking_id.owner_id.id,
                }
                if prod.packop_id :
                    prod.packop_id.write(pack_datas)
                    processed_ids.append(prod.packop_id.id)
                else:
                    pack_datas['picking_id'] = picking_id.id
                    packop_id = self.env['stock.pack.operation'].create(pack_datas)
                    processed_ids.append(packop_id.id)
            # Delete the others
            packops = self.env['stock.pack.operation'].search(['&', ('picking_id', '=', picking_id.id), '!', ('id', 'in', processed_ids)])
            for packop in packops :
                packop.unlink()
            
            # Execute the transfer of the picking
            period_id = self.env['account.period'].find(dt=self._get_default_date().date())
            picking_id.with_context(force_period=period_id.id).do_transfer()
            
            sequence = self.env['ir.sequence'].get_id(self.rel_picking_type_id.sequence_id.id or self.picking_type_id.sequence_id.id)
            self.write({'name':sequence, 'date':self._get_default_date()})
            
            move_id = self._create_journal_freight_cost(picking_id)
            self._write_account_move(picking_id)
            self._write_quants()
            self._create_nrfs()
            self.write({'move_id':move_id.id, 'picking_id':picking_id.id,'state':'posted', })
        return True
    
   
    

    @api.one
    def post(self):
        if not self.date_in and self.rel_partner_id.default_code == 'AHM' :
            raise osv.except_osv(('Perhatian !'), ("Tidak bisa di Post, silahkan tambahkan Date In !"))
        if not self.packing_line :
            raise osv.except_osv(('Perhatian !'), ("Tidak bisa di Post, silahkan tambahkan produk !"))
        
        if self.state in ('draft','surat_jalan'):
            if self.rel_code in ('outgoing','interbranch_out') or self.is_reverse :
                self.renew_available_and_reserved()
            
            ids_product = self.picking_id.get_product_ids()
            for packing_line in self.packing_line :
                if packing_line.product_id.id not in ids_product :
                    raise osv.except_osv(('Perhatian !'), ("Product '%s' tidak ada di daftar transfer !" %packing_line.product_id.name))
            
            self._check_serial_number()
            ids_reserve_lot = self.picking_id.get_reserve_lot_quant_ids()
            if self.rel_division == 'Unit' and ((self.is_reverse) or (self.rel_code == 'interbranch_in' or (self.rel_code == 'outgoing' and self.rel_branch_type == 'DL'))) :
                for packing_line in self.packing_line :
                    if packing_line.product_id.categ_id.isParentName('Unit') and packing_line.serial_number_id.id not in ids_reserve_lot :
                        raise osv.except_osv(('Perhatian !'), ("Serial Number '%s' tidak ada di daftar transfer yg sudah dibooking !" %packing_line.serial_number_id.name))
            elif self.rel_division == 'Unit' and self.rel_code == 'interbranch_out' and self.rel_branch_type == 'DL' :
                for packing_line in self.packing_line :
                    if packing_line.serial_number_id.id not in packing_line.get_lot_available_dealer(packing_line.product_id.id,packing_line.source_location_id.id) and packing_line.serial_number_id.id not in ids_reserve_lot :
                        raise osv.except_osv(('Perhatian !'), ("Serial Number '%s' tidak ditemukan di daftar Serial Number available !" %packing_line.serial_number_id.name))
            elif self.rel_division == 'Unit' and self.rel_code in ('outgoing','interbranch_out') and self.rel_branch_type == 'MD' :
                for packing_line in self.packing_line :
                    if packing_line.serial_number_id.id not in self.get_lot_available_md() and packing_line.serial_number_id.id not in ids_reserve_lot :
                        raise osv.except_osv(('Perhatian !'), ("Serial Number '%s' tidak ditemukan di daftar Serial Number available !" %packing_line.serial_number_id.name))
            
            force_valuation_amount = 0
            if self.rel_division in ('Unit', 'Sparepart') and self.rel_code == 'incoming' and not self.is_reverse :
                if self.rel_branch_type == 'DL':
                    force_valuation_amount = 0.01 
                elif self.rel_branch_type == 'MD' and self.picking_id and self.picking_id.partner_id!=self.branch_id.default_supplier_id:
                    force_valuation_amount = 0.01                   
            if self.picking_id.is_unconsolidated_reverse:
                force_valuation_amount = 0.01
            # elif self.rel_branch_type == 'MD' :
            #     force_valuation_amount = 1 #lot.HPP
            
            self._is_over_qty()
            self._update_lot(self.picking_id)
            
            processed_ids = []
            # Create new and update existing pack operations
            for lstits in [self.packing_line]:
                for prod in lstits :
               
                    if prod.chassis_number :
                        if len(prod.chassis_number) == 14 :
                            chassis_number = prod.chassis_number
                            chassis_code = False
                        elif len(prod.chassis_number) == 17 :
                            chassis_number = prod.chassis_number[3:18]
                            chassis_code = prod.chassis_number[:3]
                    
                    if self.rel_code == "incoming" and self.rel_division == "Unit" and self.rel_branch_type == 'DL' and not self.is_reverse :
                        prod.serial_number_id = self.env['stock.production.lot'].create({
                                                                                         'name':prod.engine_number,
                                                                                         'chassis_no':chassis_number,
                                                                                         'chassis_code':chassis_code,
                                                                                         'product_id':prod.product_id.id,
                                                                                         'branch_id':self.picking_id.branch_id.id,
                                                                                         'division':self.picking_id.division,
                                                                                         'purchase_order_id':self.picking_id.transaction_id,
                                                                                         'po_date':self.picking_id.date,
                                                                                         'receive_date':self._get_default_date(),
                                                                                         'supplier_id':self.picking_id.partner_id.id,
                                                                                         'expedisi_id':self.expedition_id.id,
                                                                                         'receipt_id':self.picking_id.id,
                                                                                         'picking_id':self.picking_id.id,
                                                                                         'state':'intransit',
                                                                                         'location_id': self.get_destination_location(prod.ready_for_sale, prod.rel_ready_for_sale, prod.destination_location_id.id),
                                                                                         'tahun': prod.tahun_pembuatan,
                                                                                         'ready_for_sale': prod.convert_rfs(prod.ready_for_sale)
                                                                                         })
                    
                    pack_datas = {
                        'product_id': prod.product_id.id,
                        'product_uom_id': prod.product_id.uom_id.id,
                        'product_qty': prod.quantity,
                        'lot_id': prod.serial_number_id.id,
                        'location_id': prod.source_location_id.id,
                        'location_dest_id': self.get_destination_location(prod.ready_for_sale, prod.rel_ready_for_sale, prod.destination_location_id.id),
                        'date': prod.packing_id.date if prod.packing_id.date else self._get_default_date(),
                        'owner_id': prod.packing_id.picking_id.owner_id.id,
                    }
                    if prod.packop_id:
                        prod.packop_id.write(pack_datas)
                        processed_ids.append(prod.packop_id.id)
                    else:
                        pack_datas['picking_id'] = self.picking_id.id
                        packop_id = self.env['stock.pack.operation'].create(pack_datas)
                        processed_ids.append(packop_id.id)
            # Delete the others
            packops = self.env['stock.pack.operation'].search(['&', ('picking_id', '=', self.picking_id.id), '!', ('id', 'in', processed_ids)])
            for packop in packops:
                packop.unlink()
            
            # Execute the transfer of the picking
            period_id = self.env['account.period'].find(dt=self._get_default_date().date())
            self.picking_id.with_context(force_valuation_amount=force_valuation_amount, force_period=period_id.id, unconsolidated_reverse = self.picking_id.is_unconsolidated_reverse).do_transfer()
            self._delete_lot()
            self._update_packing()
            self._write_account_move(self.picking_id)
            self._write_quants()
        return True
    
    @api.multi
    def action_cancel(self):
        self.write({'state':'cancelled'})
    
    @api.multi    
    def create_surat_jalan(self):
        if not self.packing_line :
            raise osv.except_osv(('Perhatian !'), ("Tidak bisa Create Surat Jalan, silahkan tambahkan produk !"))
        sequence = self.env['ir.sequence'].get_id(self.rel_picking_type_id.sequence_id.id or self.picking_type_id.sequence_id.id)
        self.write({'name':sequence, 'state':'surat_jalan', 'date':self._get_default_date()})
    
    @api.onchange('rel_source_location_id','rel_destination_location_id')
    def packing_line_change(self):
        self.packing_line = self.packing_line2 = self.packing_line3 = self.packing_line4 = False
    
    @api.onchange('expedition_id','branch_id')
    def expedition_id_change(self):
        domain = {}
        domain['expedition_id'] = [('id','in',self.branch_id.get_ids_expedition())]
        self.plat_number_id = False
        self.driver_id = False
        return {'domain':domain}
    
    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Tidak bisa dihapus jika status bukan 'Draft' !"))
        return super(wtc_stock_packing, self).unlink(cr, uid, ids, context=context)
    
    @api.multi
    def get_lot_available_md(self):
        location_ids = self.env['stock.location'].search([('id','child_of',self.rel_source_location_id.id)])
        ids_location = []
        for location in location_ids :
            ids_location.append(location.id)
        ids_product = self.picking_id.get_product_ids()
        ids_lot_available = []
        self._cr.execute("""
        SELECT
            l.id
        FROM
            stock_quant q
        JOIN
            stock_production_lot l on l.id = q.lot_id
        WHERE
            q.product_id in %s and q.location_id in %s and l.state = 'stock' and l.ready_for_sale='good' and q.reservation_id is Null and q.consolidated_date is not Null
        ORDER BY
            q.in_date desc
        """,(tuple(ids_product,),tuple(ids_location,)))
        for id_lot in self._cr.fetchall() :
            ids_lot_available.append(id_lot[0])
        return ids_lot_available
    
    @api.onchange('picking_type_id')
    def picking_type_id_change(self):
        if self.picking_type_id :
            self.source_location_id = self.picking_type_id.default_location_src_id.id
            self.destination_location_id = self.picking_type_id.default_location_dest_id.id
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.search(['|',('name', operator, name),('rel_origin', operator, name)] + args, limit=limit)
        return recs.name_get() 
    
    @api.cr_uid_ids_context
    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        result = []

        for packing in self.browse(cr, uid, ids, context=context):
            result.append((packing.id, (str(packing.name) or '')+' ('+str(packing.rel_origin) +')'))
        return result
    
class wtc_stock_packing_line(models.Model):
    _name = "wtc.stock.packing.line"
    _description = "Stock Packing Line"
    _rec_name = "product_id"
    
    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()
        
    packing_id = fields.Many2one('wtc.stock.packing', 'Packing')
    product_id = fields.Many2one('product.product', 'Product')
    rel_division = fields.Selection(related='packing_id.rel_division', string='Division')
    rel_code = fields.Char(related='packing_id.rel_code', string='Code')
    rel_is_reverse = fields.Boolean(related='packing_id.is_reverse', string='Is Reverse')
    rel_source_location_id = fields.Many2one(related='packing_id.rel_source_location_id', string='Source Location')
    rel_destination_location_id = fields.Many2one(related='packing_id.rel_destination_location_id', string='Destination Location')
    source_location_id = fields.Many2one('stock.location', 'Source Location')
    destination_location_id = fields.Many2one('stock.location', 'Destinaiton Location')
    current_reserved = fields.Float('Current Reserved', digits_compute=dp.get_precision('Product Unit of Measure'))
    rel_current_reserved = fields.Float(related='current_reserved', string='Current Reserved')
    stock_available = fields.Float('Stock Available', digits_compute=dp.get_precision('Product Unit of Measure'))
    rel_stock_available = fields.Float(related='stock_available', string='Stock Available')
    packop_id = fields.Many2one('stock.pack.operation', 'Operation')
    quantity = fields.Float('Qty', digits_compute=dp.get_precision('Product Unit of Measure'))
    seharusnya = fields.Float('Seharusnya', digits_compute=dp.get_precision('Product Unit of Measure'))
    rel_seharusnya = fields.Float(related='seharusnya', string='Seharusnya')
    serial_number_id = fields.Many2one('stock.production.lot', 'Serial Number')
    engine_number = fields.Char('Engine Number')
    chassis_number = fields.Char('Chassis Number')
    tahun_pembuatan = fields.Char('Tahun Pembuatan', size=4)
    rel_tahun_pembuatan = fields.Char(related='serial_number_id.tahun', string='Tahun Pembuatan')
    ready_for_sale = fields.Boolean('Ready For Sale')
    rel_ready_for_sale = fields.Boolean(related='ready_for_sale', string='Ready For Sale')
    performance_hpp = fields.Float('Performance HPP', digits_compute=dp.get_precision('Product Price'))
    freight_cost = fields.Float('Freight Cost', digits_compute=dp.get_precision('Product Price'))
    rel_branch_type = fields.Char(related='packing_id.rel_branch_type', string='Branch Type')
    no_ship_list = fields.Char('No Ship List')
    no_faktur = fields.Char('No Faktur')
    purchase_line_id = fields.Many2one('purchase.order.line', 'Purchase Line')
    surat_jalan_name = fields.Char('Surat Jalan')

   
    _sql_constraints = [
        ('unique_engine_number', 'unique(packing_id,engine_number)', 'Ditemukan engine number duplicate, silahkan cek kembali !'),
        ('unique_chassis_number', 'unique(packing_id,chassis_number)', 'Ditemukan chassis number duplicate, silahkan cek kembali !'),
        ]
    
    @api.multi
    def convert_rfs(self, rfs):
        result = False
        if rfs == 'good' :
            result = True
        elif rfs == True :
            result = 'good'
        elif rfs == False :
            result = 'not_good'
        return result
    
    @api.multi
    def get_lot_available_dealer(self, id_product, id_location):
        ids_lot_available = []
        self._cr.execute("""
        SELECT
            l.id
        FROM
            stock_quant q
        JOIN
            stock_production_lot l on l.id = q.lot_id
        WHERE
            q.product_id = %s and q.location_id = %s and l.state = 'stock' and q.reservation_id is Null and q.consolidated_date is not Null
        ORDER BY
            q.in_date desc
        """,(id_product,id_location))
        for id_lot in self._cr.fetchall() :
            ids_lot_available.append(id_lot[0])
        return ids_lot_available
    
    @api.multi
    def get_lot_available_dealer_unconsolidated(self, id_product, id_location):
        ids_lot_available = []
        self._cr.execute("""
        SELECT
            l.id
        FROM
            stock_quant q
        JOIN
            stock_production_lot l on l.id = q.lot_id
        WHERE
            q.product_id = %s and q.location_id = %s and l.state = 'intransit' and q.reservation_id is Null and q.consolidated_date is Null
        ORDER BY
            q.in_date desc
        """,(id_product,id_location))
        for id_lot in self._cr.fetchall() :
            ids_lot_available.append(id_lot[0])
        return ids_lot_available
    
    @api.multi
    def _get_lot_intransit(self):
        ids_lot_intransit = []
        branch_id = self.env['wtc.branch'].search([('branch_type','=','MD')])
        serial_number_ids = self.env['stock.production.lot'].search([
            ('branch_id','=',branch_id.id),
            ('state','=','intransit'),
            ])
        for lot in serial_number_ids :
            ids_lot_intransit.append(lot.id)
        return ids_lot_intransit
    
    @api.multi
    def get_qty_max(self, seharusnya, available, reserved):
        qty_max = seharusnya
        if self.rel_code <> 'incoming' :
            if (available + reserved) < seharusnya :
                qty_max = available + reserved
        return qty_max
    
    @api.multi
    def is_punctuation(self, words):
        for n in range(len(words)) :
            if words[n] in string.punctuation :
                return True
        return False
    
    @api.multi
    def _get_suggested_location(self, id_product_tmpl, id_attribute_value, id_destination_location):
        id_location = id_destination_location
        return id_location
    
    @api.onchange('seharusnya')
    def change_default(self):
        self.ready_for_sale = True
      
    @api.onchange('product_id','serial_number_id')
    def change_product_id(self):
        domain = {}
        product_ids = self.packing_id.picking_id.get_product_ids()
        domain['product_id'] = [('id','in',product_ids)]
          
        if self.serial_number_id :
            self.product_id = self.serial_number_id.product_id.id
        elif not self.serial_number_id and self.rel_division == 'Unit' and self.rel_code in ['incoming','outgoing','interbranch_out','interbranch_in'] and self.packing_id.rel_branch_type == 'MD' and not self.rel_is_reverse :
            self.product_id = False
        return {'domain':domain}
      
    @api.onchange('engine_number','serial_number_id')
    def change_engine_number(self):
        warning={}
        picking_id = self.packing_id.picking_id
        if self.rel_code == 'incoming' and self.rel_branch_type == 'DL' and not self.rel_is_reverse :
            if self.engine_number :
                self.engine_number = self.engine_number.replace(" ", "")
                self.engine_number = self.engine_number.upper()
                if len(self.engine_number) != 12 :
                    self.engine_number = False
                    warning = {'title':'Engine Number Salah !','message':"Silahkan periksa kembali Engine Number yang Anda input"}
                    return {'warning':warning}
                  
                if self.is_punctuation(self.engine_number) :
                    warning = {'title':'Perhatian !','message':"Engine Number hanya boleh huruf dan angka"}
                    return {'warning':warning}
                  
                if self.packing_id.rel_branch_type == 'DL' :
                    if self.product_id :
                        product_id = self.env['product.template'].search([('name','=',self.product_id.name)])
                        if product_id.kd_mesin :
                            pjg = len(product_id.kd_mesin)
                            if product_id.kd_mesin != self.engine_number[:pjg] :
                                self.engine_number = False
                                warning = {'title':'Perhatian !','message':"Engine Number tidak sama dengan kode mesin di Produk"}
                                return {'warning':warning}
                              
                        else :
                            self.engine_number = False
                            warning = {'title':'Perhatian !','message':"Silahkan isi kode mesin '%s' di master product terlebih dahulu" %self.product_id.description}
                            return {'warning':warning}
                          
                        engine_exist = self.env['stock.production.lot'].search([('name','=',self.engine_number)])
                        if engine_exist:
                            self.engine_number=False
                            warning = {'title':'Perhatian !','message':"Engine Number sudah pernah ada"}
                            return {'warning':warning}
                          
        else :
            if self.serial_number_id :
                self.engine_number = self.serial_number_id.name
            else :
                self.engine_number = False
      
    @api.onchange('chassis_number','serial_number_id')
    def change_chassis_number(self):
        warning = {}
        if self.rel_code == 'incoming' and self.packing_id.rel_branch_type == 'DL' and not self.rel_is_reverse :
            if self.chassis_number :
                self.chassis_number = self.chassis_number.replace(" ", "")
                self.chassis_number = self.chassis_number.upper()
                if len(self.chassis_number) == 14 or (len(self.chassis_number) == 17 and self.chassis_number[:2] == 'MH') :
                    self.chassis_number = self.chassis_number
                else :
                    self.chassis_number = False
                    warning = {'title':'Chassis Number Salah !','message':"Silahkan periksa kembali Chassis Number yang Anda input"}
                    return {'warning':warning}
                  
                if self.is_punctuation(self.chassis_number) :
                    self.chassis_number = False
                    warning = {'title':'Perhatian','message':"Chassis Number hanya boleh huruf dan angka"}
                    return {'warning':warning}
                  
                chassis_exist = self.env['stock.production.lot'].search([('chassis_no','=',self.chassis_number)])
                if chassis_exist :
                    self.chassis_number = False
                    warning = {'title':'Perhatian','message':"Chassis Number sudah pernah ada"}
                    return {'warning':warning}
        else :
            if self.serial_number_id :
                self.chassis_number = self.serial_number_id.chassis_no
            else :
                self.chassis_number = False
      
    @api.onchange('serial_number_id','product_id','source_location_id')
    def change_serial_number_id(self):
        domain = {}
        ids_serial_number = []
        
        if self.rel_code == 'interbranch_out' and self.rel_branch_type == 'DL' and not self.rel_is_reverse :
            if self.product_id and self.source_location_id :
                ids_serial_number = self.get_lot_available_dealer(self.product_id.id, self.source_location_id.id)
        elif (self.rel_code in ('interbranch_in','outgoing') and self.rel_branch_type == 'DL') or self.rel_is_reverse:
            if self.packing_id.picking_id.is_unconsolidated_reverse and self.product_id:
                ids_serial_number = self.get_lot_available_dealer_unconsolidated(self.product_id.id, self.source_location_id.id)
            else:
                product_serial_number = self.packing_id.picking_id.filter_restrict_lot_ids()
                if self.product_id in product_serial_number :
                    ids_serial_number = product_serial_number[self.product_id]
            
        #elif self.rel_code == 'incoming' and self.packing_id.rel_branch_type == 'MD' and not self.rel_is_reverse :
        elif self.packing_id.branch_id.branch_type == 'MD' and self.packing_id.division == 'Unit' and self.packing_id.picking_type_id.code == 'incoming' and not self.packing_id.picking_id :
            ids_serial_number = self._get_lot_intransit()
        elif self.rel_code in ('outgoing','interbranch_out') and self.rel_branch_type == 'MD' and not self.rel_is_reverse :
            ids_serial_number = self.packing_id.get_lot_available_md()
        elif self.rel_code == 'interbranch_in' and self.rel_branch_type == 'MD' and not self.rel_is_reverse :
            ids_serial_number = self.packing_id.picking_id.get_reserve_lot_quant_ids()
        domain['serial_number_id'] = [('id','in',ids_serial_number)]
        return {'domain':domain}
      
    @api.onchange('product_id','source_location_id')
    def change_serial_number_id2(self):
        if self.rel_code == 'interbranch_out' and self.rel_branch_type == 'DL' :
            self.serial_number_id = False
      
    @api.onchange('source_location_id')
    def change_source_location_id(self):
        if not self.source_location_id or self.packing_id.is_reverse and self.rel_code in ('incoming','interbranch_in') or not self.packing_id.picking_id :
            # Tambah Custom Type Branch Location Disini
            rel_origin = self.packing_id.rel_origin
            list_type = ['Topup']
            tipe_origin = False
            if rel_origin:
                origin_split = rel_origin.split('/')
                if origin_split[0] == 'MO':
                    mo_obj = self.env['wtc.mutation.order'].sudo().search([('name','=',rel_origin)],limit=1)
                    if mo_obj:
                        tipe_origin = mo_obj.distribution_id.type_id
                elif origin_split[0] == 'SO':
                    so_obj = self.env['sale.order'].sudo().search([('name','=',rel_origin)],limit=1)                
                    if so_obj:
                        tipe_origin = so_obj.distribution_id.type_id
            if tipe_origin and self.packing_id.rel_branch_id.branch_type == 'MD':
                if tipe_origin.name in list_type:
                    loc_type = self.env['teds.branch.config.location'].sudo().search([
                        ('branch_id','=',self.packing_id.rel_branch_id.id),
                        ('division','=',self.packing_id.rel_division),
                        ('type_id','=',tipe_origin.id)],limit=1)
                    domain = {'source_location_id':[('id','=',loc_type.location_id.id)]}
                    self.source_location_id = loc_type.location_id.id
                    return {'domain':domain}
                else:
                    self.source_location_id = self.rel_source_location_id.id or self.packing_id.source_location_id.id
        
            else:
                #Aslinya ini tab spasi#
                self.source_location_id = self.rel_source_location_id.id or self.packing_id.source_location_id.id
        
        if self.rel_code in ('outgoing','interbranch_out') and self.rel_division == 'Unit' and self.rel_branch_type == 'MD' and not self.rel_is_reverse :
            if self.serial_number_id :
                self.source_location_id = self.serial_number_id.location_id.id
      
    @api.onchange('destination_location_id','product_id')
    def change_destination_location_id(self):
        if not self.destination_location_id or self.packing_id.is_reverse and self.rel_code in ('outgoing','interbranch_out') :
            # Tambah Custom Type Branch Location Disini
            rel_origin = self.packing_id.rel_origin
            list_type = ['Hotline']
            tipe_origin = False
            if rel_origin:
                origin_split = rel_origin.split('/')
                if origin_split[0] == 'PO':
                    po_obj = self.env['purchase.order'].sudo().search([('name','=',rel_origin)],limit=1)
                    if po_obj:
                        tipe_origin = po_obj.purchase_order_type_id
                if origin_split[0] == 'MO':
                    mo_obj = self.env['wtc.mutation.order'].sudo().search([('name','=',rel_origin)],limit=1)
                    if mo_obj:
                        tipe_origin = mo_obj.distribution_id.type_id
            if tipe_origin and self.packing_id.rel_branch_id.branch_type != 'MD':
                if tipe_origin.name in list_type and self.rel_code in ('incoming','interbranch_in'):
                    loc_type = self.env['teds.branch.config.location'].sudo().search([
                        ('branch_id','=',self.packing_id.rel_branch_id.id),
                        ('division','=',self.packing_id.rel_division),
                        ('type_id','=',tipe_origin.id)],limit=1)
                    domain = {'destination_location_id':[('id','=',loc_type.location_id.id)]}
                    self.destination_location_id = loc_type.location_id.id
                    return {'domain':domain}
                else:
                    self.destination_location_id = self.rel_destination_location_id.id or self.packing_id.destination_location_id.id
            else:
                #Aslinya ini tab spasi#
                self.destination_location_id = self.rel_destination_location_id.id or self.packing_id.destination_location_id.id
#         elif (self.rel_code == 'incoming' and self.rel_branch_type == 'MD') or not self.packing_id.picking_id :            
#             self.destination_location_id = self._get_suggested_location(self.product_id.product_tmpl_id.id, self.product_id.attribute_value_ids.id, self.rel_destination_location_id.id or self.packing_id.destination_location_id.id)
      
    @api.onchange('rel_source_location_id')
    def change_rel_source_location_id(self):
        if not self.rel_source_location_id and not self.packing_id.picking_id :
            self.rel_source_location_id = self.packing_id.source_location_id.id
      
    @api.onchange('rel_destination_location_id')
    def change_rel_destination_location_id(self):
        if not self.rel_destination_location_id and not self.packing_id.picking_id :
            self.rel_destination_location_id = self.packing_id.destination_location_id.id
      
    @api.onchange('quantity','product_id')
    def change_quantity(self):
        if self.product_id.categ_id.isParentName('Unit'):
            self.quantity = 1
        else :
            qty_max = self.get_qty_max(self.seharusnya, self.stock_available, self.current_reserved)
            if self.quantity > qty_max :
                self.quantity = qty_max
                warning = {'title':'Perhatian','message':"Quantity melebihi jumlah maksimal '%d'" %qty_max}
                return {'warning':warning}
            elif self.quantity < 0 :
                self.quantity = qty_max
                warning = {'title':'Perhatian','message':'Quantity tidak boleh kurang dari nol'}
                return {'warning':warning}
      
    @api.onchange('tahun_pembuatan','serial_number_id')
    def change_tahun_pembuatan(self):
        warning = {}
        if self.tahun_pembuatan and not self.tahun_pembuatan.isdigit() :
            self.tahun_pembuatan = False
            warning = {'title':'Perhatian', 'message':'Tahun Pembuatan hanya boleh angka'}
            return {'warning':warning}
          
        if self.rel_code == 'incoming' and not self.tahun_pembuatan :
            self.tahun_pembuatan = self._get_default_date().strftime('%Y')
        if self.serial_number_id :
            self.tahun_pembuatan = self.serial_number_id.tahun
      
    @api.onchange('serial_number_id')
    def change_ready_for_sale(self):
        if self.serial_number_id :
            self.ready_for_sale = self.convert_rfs(self.serial_number_id.ready_for_sale)
      
    @api.onchange('product_id')
    def change_seharusnya(self):
        seharusnya = self.packing_id.picking_id.get_seharusnya()
        if self.product_id in seharusnya :
            self.seharusnya = seharusnya[self.product_id]
        else :
            self.seharusnya = 0
      
    @api.onchange('product_id','source_location_id')
    def change_current_reserved(self):
        if self.rel_code in ('outgoing','interbranch_out','interbranch_in') or self.packing_id.is_reverse :
            ids_move = self.packing_id.picking_id.get_ids_move()
            if self.product_id and self.source_location_id :
                self.current_reserved = self.packing_id.picking_id.get_current_reserved(self.product_id.id, self.source_location_id.id, ids_move)
      
    @api.onchange('product_id','source_location_id')
    def change_stock_available(self):
        if self.packing_id.is_reverse and not self.packing_id.picking_id.is_unconsolidated_reverse:
            self.stock_available = 0
        elif self.rel_code == 'incoming' :
            self.stock_available = self.seharusnya
        else :
            if self.product_id and self.source_location_id :
                ids_move = self.packing_id.picking_id.get_ids_move()
                if self.product_id.categ_id.isParentName('Extras') :
                    self.stock_available = self.packing_id.picking_id.get_stock_available_extras(self.product_id.id, self.source_location_id.id)
                elif self.packing_id.picking_id.is_unconsolidated_reverse:
                    self.stock_available = self.packing_id.picking_id.get_stock_available_unconsolidated(self.product_id.id, self.source_location_id.id)
                else:
                    self.stock_available = self.packing_id.picking_id.get_stock_available(self.product_id.id, self.source_location_id.id)
      
    @api.onchange('product_id')
    def change_performance_hpp(self):
        if self.rel_code == 'interbranch_out' and self.rel_division == 'Unit' and self.packing_id.rel_branch_id.branch_type == 'MD' :
            mutation_order_id = self.env['wtc.mutation.order'].search([('id','=',self.packing_id.picking_id.transaction_id)])
            self.performance_hpp = 0
            for mo_line in mutation_order_id.order_line :
                if self.product_id == mo_line.product_id :
                    self.performance_hpp = mo_line.performance_hpp
                    break
                  
    @api.onchange('product_id')
    def freight_cost_change(self):
        if not self.packing_id.picking_id :
            if not self.packing_id.expedition_id :
                raise osv.except_osv(('Perhatian !'), ("Silahkan pilih Ekspedisi terlebih dahulu !"))
            if not self.packing_id.branch_id :
                raise osv.except_osv(('Perhatian !'), ("Silahkan input Branch terlebih dahulu !"))
            if not self.packing_id.division :
                raise osv.except_osv(('Perhatian !'), ("Silahkan pilih Division terlebih dahulu !"))
            if not self.packing_id.picking_type_id :
                raise osv.except_osv(('Perhatian !'), ("Silahkan pilih Picking Type terlebih dahulu !"))
            #self.freight_cost = self.packing_id.branch_id.get_freight_cost(self.packing_id.expedition_id.id,self.product_id.id)
              
    @api.onchange('purchase_line_id','no_ship_list','serial_number_id')
    def change_purchase_line_id_ship_list(self):
        if self.serial_number_id :
            self.no_ship_list = self.serial_number_id.no_ship_list
            self.no_faktur = self.serial_number_id.no_faktur
            for order_line in self.serial_number_id.sudo().purchase_order_id.order_line :
                if order_line.product_id == self.serial_number_id.product_id :
                    self.purchase_line_id = order_line.id
                    break
        else :
            self.purchase_line_id = False
            self.no_ship_list = False
            self.no_faktur = False
          