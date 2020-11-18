from openerp import models, fields, api
from datetime import datetime

class StockPicking(models.Model):
    _inherit = "stock.picking"

    def create_packing_only(self,id):
        picking_id = self.browse(id)
        if picking_id.branch_id.branch_type == 'MD' and picking_id.division == 'Unit' and picking_id.picking_type_code == 'incoming' and not picking_id.is_reverse and picking_id.state != 'done' :
            raise osv.except_osv(('Perhatian !'), ("Untuk penerimaan Unit MD silahkan create di menu Showroom > Good Receipt Note MD"))
        packing_draft = self.env['wtc.stock.packing'].search([
            ('picking_id','=',picking_id.id),
            ('state','in',['draft','surat_jalan'])])

        if picking_id.state == 'done' or packing_draft :
            return packing_draft
        
        obj_packing = self.env['wtc.stock.packing']
        obj_packing_line = self.env['wtc.stock.packing.line']
        branch_sender_id = False
        
        if picking_id.picking_type_code == 'interbranch_in' :
            branch_sender_id = picking_id.location_id.branch_id.id
        packing_vals = {
                        'picking_id': picking_id.id,
                        'branch_sender_id': branch_sender_id,
                        'rel_branch_id': picking_id.picking_type_id.branch_id.id,
                        'rel_source_location_id': picking_id.location_id.id,
                        'rel_picking_type_id': picking_id.picking_type_id.id,
                        'rel_destination_location_id': picking_id.location_dest_id.id,
                        'rel_origin': picking_id.origin,
                        'rel_partner_id': picking_id.partner_id.id,
                        'rel_division': picking_id.division,
                        'rel_code': picking_id.picking_type_id.code,
                        'rel_branch_type': picking_id.branch_id.branch_type,
                        }
        
        id_packing = obj_packing.create(packing_vals)
        
        if (picking_id.picking_type_code == 'outgoing' and picking_id.rel_branch_type == 'DL') or picking_id.division == 'Umum' or picking_id.is_reverse :
            ids_move = self.get_ids_move()
            for move in picking_id.move_lines :
                if picking_id.picking_type_code == 'incoming' and not picking_id.is_reverse :
                    current_reserved = 0
                    stock_available = self.get_seharusnya()[move.product_id]
                elif picking_id.is_reverse and not picking_id.is_unconsolidated_reverse:
                    current_reserved = self.get_current_reserved(move.product_id.id, move.location_id.id, ids_move)
                    stock_available = 0
                elif picking_id.is_unconsolidated_reverse:
                    current_reserved = self.get_current_reserved(move.product_id.id, move.location_id.id, ids_move)
                    stock_available = self.get_stock_available_unconsolidated(move.product_id.id, move.location_id.id)   
                elif move.product_id.categ_id.isParentName('Extras') :
                    current_reserved = self.get_current_reserved(move.product_id.id, move.location_id.id, ids_move)
                    stock_available = self.get_stock_available_extras(move.product_id.id, move.location_id.id)
                else :
                    current_reserved = self.get_current_reserved(move.product_id.id, move.location_id.id, ids_move)
                    stock_available = self.get_stock_available(move.product_id.id, move.location_id.id)
                
                packing_line_vals = {
                                     'packing_id': id_packing.id,
                                     'product_id': move.product_id.id,
                                     'quantity': self.get_qty(picking_id, move.product_id, move.product_uom_qty),
                                     'seharusnya': self.get_seharusnya()[move.product_id],
                                     'serial_number_id': move.restrict_lot_id.id,
                                     'engine_number': move.restrict_lot_id.name,
                                     'chassis_number': move.restrict_lot_id.chassis_no,
                                     'source_location_id': move.location_id.id,
                                     'destination_location_id': move.location_dest_id.id,
                                     'tahun_pembuatan': move.restrict_lot_id.tahun,
                                     'ready_for_sale': self.convert_rfs(move.restrict_lot_id.ready_for_sale),
                                     'current_reserved': current_reserved,
                                     'stock_available': stock_available
                                     }
                obj_packing_line.create(packing_line_vals)
    
        return id_packing