# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-TODAY OpenERP S.A. <http://www.odoo.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from datetime import datetime
from openerp.osv import osv
import time
import string
import sys

class wtc_stock_transfer_details(models.TransientModel):
    _name = 'stock.wtc_transfer_details'
    _description = 'Picking wizard'

    picking_id = fields.Many2one('stock.picking', 'Picking')
    item_ids = fields.One2many('stock.wtc_transfer_details_items', 'transfer_id', 'Items', domain=[('product_id', '!=', False)])
    packop_ids = fields.One2many('stock.wtc_transfer_details_items', 'transfer_id', 'Packs', domain=[('product_id', '=', False)])
    picking_source_location_id = fields.Many2one('stock.location', string="Head source location", related='picking_id.location_id', store=False, readonly=True)
    picking_destination_location_id = fields.Many2one('stock.location', string="Head destination location", related='picking_id.location_dest_id', store=False, readonly=True)

    def default_get(self, cr, uid, fields, context=None):
        if context is None: context = {}
        res = super(wtc_stock_transfer_details, self).default_get(cr, uid, fields, context=context)
        picking_ids = context.get('active_ids', [])
        active_model = context.get('active_model')

        if not picking_ids or len(picking_ids) != 1:
            # Partial Picking Processing may only be done for one picking at a time
            return res
        assert active_model in ('stock.picking'), 'Bad context propagation'
        picking_id, = picking_ids
        picking = self.pool.get('stock.picking').browse(cr, uid, picking_id, context=context)
        jenis_stock = picking.picking_type_id.code
        sourceloc_type = picking.picking_type_id.default_location_src_id.usage
        destloc_type = picking.picking_type_id.default_location_dest_id.usage
        if sourceloc_type == 'transit' :
            picking_type = 'interbranch_in'
        elif destloc_type == 'transit' :
            picking_type = 'interbranch_out'
        else :
            picking_type = 'not_interbranch'
        items = []
        packs = []
        
        if not picking.pack_operation_ids :
            picking.do_prepare_partial()
            
        for op in picking.pack_operation_ids :
            if (jenis_stock == 'incoming' and picking.division == 'Umum') or (jenis_stock == 'outgoing' and picking.division == 'Unit') or (jenis_stock == 'outgoing' and picking.division == 'Umum') or (jenis_stock == 'internal' and picking_type == 'not_interbranch' and picking.division == 'Unit') :
                if jenis_stock == 'incoming' and picking.division == 'Umum' :
                    quantity = 0
                    seharusnya = op.product_qty
                    lot_id = op.lot_id.id
                    engine_number = False
                    chassis_number = False
                    loop = 1
                elif jenis_stock == 'outgoing' and picking.division == 'Unit' :
                    quantity = 1
                    seharusnya = op.product_qty
                    lot_id = op.lot_id.id
                    engine_number = op.lot_id.name
                    chassis_number = op.lot_id.chassis_no
                    loop = int(seharusnya)
                elif jenis_stock == 'outgoing' and picking.division == 'Umum' :
                    quantity = op.product_qty
                    seharusnya = op.product_qty
                    lot_id = op.lot_id.id
                    engine_number = False
                    chassis_number = False
                    loop = 1
                elif jenis_stock == 'internal' and picking_type == 'not_interbranch' and picking.division == 'Unit' :
                    quantity = 1
                    seharusnya = op.product_qty
                    lot_id = op.lot_id.id
                    engine_number = op.lot_id.name
                    chassis_number = op.lot_id.chassis_no
                    loop = int(seharusnya)
                    
                if op.lot_id.ready_for_sale == 'good' :
                    rfs = True
                else :
                    rfs = False
                    
                for x in range(loop) :
                    item = {
                            'packop_id': op.id,
                            'product_id': op.product_id.id,
                            'product_uom_id': op.product_uom_id.id,
                            'quantity': quantity,
                            'seharusnya': seharusnya,
                            'package_id': op.package_id.id,
                            'lot_id': lot_id,
                            'sourceloc_id': op.location_id.id,
                            'destinationloc_id': op.location_dest_id.id,
                            'result_package_id': op.result_package_id.id,
                            'date': op.date,
                            'owner_id': op.owner_id.id,
                            'engine_number' : engine_number,
                            'chassis_number': chassis_number,
                            'tahun_pembuatan': op.lot_id.tahun,
                            'ready_for_sale': rfs,
                            }
                if op.product_id :
                    items.append(item)
                elif op.package_id :
                    packs.append(item)
                res.update(item_ids=items)
                res.update(packop_ids=packs)
            
            else :
                if jenis_stock == 'incoming' and picking.division == 'Unit' :
                    quantity = 1
                    seharusnya = op.product_qty
                    lot_id = op.lot_id.id
                    engine_number = False
                    chassis_number = False
                elif jenis_stock == 'incoming' and picking.division == 'Sparepart' :
                    quantity = op.product_qty
                    seharusnya = op.product_qty
                    lot_id = op.lot_id.id
                    engine_number = False
                    chassis_number = False
                elif jenis_stock == 'outgoing' and picking.division == 'Sparepart' :
                    quantity = op.product_qty
                    seharusnya = op.product_qty
                    lot_id = op.lot_id.id
                    engine_number = False
                    chassis_number = False
                elif jenis_stock == 'internal' and picking_type == 'not_interbranch' and picking.division == 'Sparepart' :
                    quantity = op.product_qty
                    seharusnya = op.product_qty
                    lot_id = op.lot_id.id
                    engine_number = False
                    chassis_number = False
                elif jenis_stock == 'internal' and picking_type == 'not_interbranch' and picking.division == 'Umum' :
                    quantity = op.product_qty
                    seharusnya = op.product_qty
                    lot_id = op.lot_id.id
                    engine_number = False
                    chassis_number = False
                elif jenis_stock == 'internal' and picking_type == 'interbranch_out' and picking.division == 'Unit' :
                    quantity = 1
                    seharusnya = op.product_qty
                    lot_id = op.lot_id.id
                    engine_number = op.lot_id.name
                    chassis_number = op.lot_id.chassis_no
                elif jenis_stock == 'internal' and picking_type == 'interbranch_out' and picking.division == 'Sparepart' :
                    quantity = op.product_qty
                    seharusnya = op.product_qty
                    lot_id = op.lot_id.id
                    engine_number = False
                    chassis_number = False
                elif jenis_stock == 'internal' and picking_type == 'interbranch_out' and picking.division == 'Umum' :
                    quantity = op.product_qty
                    seharusnya = op.product_qty
                    lot_id = op.lot_id.id
                    engine_number = False
                    chassis_number = False
                elif jenis_stock == 'internal' and picking_type == 'interbranch_in' and picking.division == 'Unit' :
                    quantity = 1
                    seharusnya = op.product_qty
                    lot_id = op.lot_id.id
                    engine_number = False
                    chassis_number = False
                elif jenis_stock == 'internal' and picking_type == 'interbranch_in' and picking.division == 'Sparepart' :
                    quantity = op.product_qty
                    seharusnya = op.product_qty
                    lot_id = op.lot_id.id
                    engine_number = False
                    chassis_number = False
                elif jenis_stock == 'internal' and picking_type == 'interbranch_in' and picking.division == 'Umum' :
                    quantity = op.product_qty
                    seharusnya = op.product_qty
                    lot_id = op.lot_id.id
                    engine_number = False
                    chassis_number = False
                
                item = {
                        'packop_id': op.id,
                        'product_id': op.product_id.id,
                        'product_uom_id': op.product_uom_id.id,
                        'quantity': quantity,
                        'seharusnya': seharusnya,
                        'package_id': op.package_id.id,
                        'lot_id': lot_id,
                        'sourceloc_id': op.location_id.id,
                        'destinationloc_id': op.location_dest_id.id,
                        'result_package_id': op.result_package_id.id,
                        'date': op.date,
                        'owner_id': op.owner_id.id,
                        'engine_number' : engine_number,
                        'chassis_number': chassis_number
                        }
                if op.product_id:
                    items.append(item)
                elif op.package_id:
                    packs.append(item)
                res.update(item_ids=[])
                res.update(packop_ids=packs)
        return res

    @api.multi
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date()
    
    @api.one
    def do_detailed_transfer(self) :
        move = {}
        error_message = False
        code = self.picking_id.picking_type_id.code
        sourceloc_type = self.picking_id.picking_type_id.default_location_src_id.usage
        destloc_type = self.picking_id.picking_type_id.default_location_dest_id.usage
        if sourceloc_type == 'transit' :
            picking_type = 'interbranch_in'
        elif destloc_type == 'transit' :
            picking_type = 'interbranch_out'
        else :
            picking_type = 'not_interbranch'
        try :
            if not self.item_ids :
                error_message = "Tidak bisa ditransfer, silahkan tambahkan produk !"
                raise
            
            for x in self.picking_id.move_lines :
                move[x.product_id] = move.get(x.product_id,0) + x.product_uom_qty
            for x in self.item_ids :
                move[x.product_id] = move.get(x.product_id,0) - x.quantity
                if move[x.product_id] < 0 :
                    error_message = "Cek kembali produk dan quantity yang Anda input !"
                    raise
                
            for x in self.item_ids :
                if x.product_id.categ_id.isParentName('Unit'):
                    if not x.engine_number or not x.chassis_number :
                        error_message = "Lengkapi data Nomor Engine & Chassis Motor !"
                        raise
                    
            if code == 'internal' :
                obj_loc = self.env['stock.location'].browse(self.picking_destination_location_id.id)
                if obj_loc.maximum_qty <> -1 :
                    quantity = 0
                    for x in self.item_ids :
                        quantity += x.quantity
                    for x in self.env['stock.quant'].search([('location_id','=',self.picking_destination_location_id.id)]) :
                        quantity += x.qty
                    
                    if quantity > obj_loc.maximum_qty :
                        quantity = 0
                        error_message = "Quantity melebihi jumlah maksimum lokasi !"
                        raise
                    
            if code == 'incoming' :
                if self.picking_id.division == 'Unit' :
                    engine = []
                    chassis = []
                    for x in self.item_ids :
                        engine.append(str(x.engine_number))
                        chassis.append(str(x.chassis_number))
                    engine.sort()
                    chassis.sort()
                    a = ""
                    b = ""
                    for x in engine :
                        if a == x :
                            error_message = "Ditemukan engine number duplicate %s!" %a
                            raise
                        a = x
                    for y in chassis :
                        if b == y :
                            error_message = "Ditemukan chassis number duplicate %s!" %b
                            raise
                        b = y
            
            if code == 'internal' and destloc_type == 'transit' :
                obj_mo_id = self.env['wtc.mutation.order'].browse(self.picking_id.transaction_id)
                branch_id = obj_mo_id.sudo().branch_requester_id
                warehouse = branch_id.warehouse_id
                if not warehouse :
                    error_message = "Silahkan setting warehouse untuk branch '%s' terlebih dahulu" %branch_id.name
                    raise
                if not warehouse.interbranch_in_type_id :
                    error_message = "Silahkan setting 'Interbranch In Type' untuk warehouse '%s' terlebih dahulu" %warehouse.name
                    raise
                if not warehouse.interbranch_in_type_id.default_location_dest_id :
                    error_message = "Tidak ditemukan 'Default Destination Location'\nuntuk warehouse '%s' dan type picking '%s'" %(warehouse.name,warehouse.interbranch_in_type_id.name)
                    raise
            
            if self.picking_id.division == "Unit" and code <> "incoming" :
                for x in self.item_ids :
                    obj_lot = self.env['stock.production.lot'].search([('name','=',x.lot_id.name)])
                    obj_lot.write({'location_id':x.destinationloc_id.id,'picking_id':self.picking_id.id,'branch_id':self.picking_id.branch_id.id})
                    
            processed_ids = []
            # Create new and update existing pack operations
            tgl = self._get_default_date()
            for lstits in [self.item_ids, self.packop_ids]:
                for prod in lstits:
                    if prod.chassis_number :
                        if len(prod.chassis_number) == 14 :
                            chassis_number = prod.chassis_number
                            chassis_code = ''
                        elif len(prod.chassis_number) == 17 :
                            chassis_number = prod.chassis_number[3:18]
                            chassis_code = prod.chassis_number[:3]

                    if code == "incoming" and self.picking_id.division == "Unit" :
                        if prod.ready_for_sale :
                            rfs = 'good'
                        else :
                            rfs = 'not_good'
                        lot_exist = self.env['stock.production.lot'].search([('name','=',prod.engine_number)])
                        if lot_exist :
                            lot_exist.unlink()
                        prod.lot_id = self.env['stock.production.lot'].create({
                                                                               'name':prod.engine_number,
                                                                               'chassis_no':chassis_number,
                                                                               'chassis_code':chassis_code,
                                                                               'product_id':prod.product_id.id,
                                                                               'branch_id':self.picking_id.branch_id.id,
                                                                               'division':self.picking_id.division,
                                                                               'po_date':self.picking_id.date,
                                                                               'receive_date':tgl,
                                                                               'supplier_id':self.picking_id.partner_id.id,
                                                                               'picking_id':self.picking_id.id,
                                                                               'state':'intransit',
                                                                               'location_id': prod.destinationloc_id.id,
                                                                               'tahun': prod.tahun_pembuatan,
                                                                               'ready_for_sale': rfs
                                                                               })
                    pack_datas = {
                        'product_id': prod.product_id.id,
                        'product_uom_id': prod.product_uom_id.id,
                        'product_qty': prod.quantity,
                        'package_id': prod.package_id.id,
                        'lot_id': prod.lot_id.id,
                        'location_id': prod.sourceloc_id.id,
                        'location_dest_id': prod.destinationloc_id.id,
                        'result_package_id': prod.result_package_id.id,
                        'date': prod.date if prod.date else self._get_default_date(),
                        'owner_id': prod.owner_id.id,
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
            
        except :
            if not error_message :
                error_message = sys.exc_info()[1]
            if error_message :
                raise osv.except_osv(_('Perhatian !'), _(error_message))
        
        finally :
            self.item_ids.unlink()
            if not error_message :
                # Execute the transfer of the picking
                self.picking_id.do_transfer()
            self._cr.commit()
        
        return True
    
    @api.multi
    def wizard_view(self):
        view = self.env.ref('wtc_stock.view_stock_enter_transfer_details')

        return {
            'name': _('Enter transfer details'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.wtc_transfer_details',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': self.ids[0],
            'context': self.env.context,
        }

class wtc_stock_transfer_details_items(models.TransientModel):
    _name = 'stock.wtc_transfer_details_items'
    _description = 'Picking wizard items'

    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
    
    @api.multi
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date()
        
    transfer_id = fields.Many2one('stock.wtc_transfer_details', 'Transfer')
    packop_id = fields.Many2one('stock.pack.operation', 'Operation')
    product_id = fields.Many2one('product.product', 'Product')
    product_uom_id = fields.Many2one('product.uom', 'Product Unit of Measure')
    engine_number = fields.Char('Engine Number')
    chassis_number = fields.Char('Chassis Number')
    quantity = fields.Float('Quantity', digits=(5,0), default = 1)
    package_id = fields.Many2one('stock.quant.package', 'Source package', domain="['|', ('location_id', 'child_of', sourceloc_id), ('location_id','=',False)]")
    lot_id = fields.Many2one('stock.production.lot', 'Lot/Serial Number')
    sourceloc_id = fields.Many2one('stock.location', 'Source Location', required=True)
    destinationloc_id = fields.Many2one('stock.location', 'Destination Location', required=True)
    result_package_id = fields.Many2one('stock.quant.package', 'Destination package', domain="['|', ('location_id', 'child_of', destinationloc_id), ('location_id','=',False)]")
    date = fields.Datetime('Date')
    owner_id = fields.Many2one('res.partner', 'Owner', help="Owner of the quants")
    branch_id = fields.Many2one('wtc.branch', 'Branch', default=_get_default_branch)
    division = fields.Selection([
                                 ('Unit','Unit'),
                                 ('Sparepart','Sparepart'),
                                 ('Umum','Umum')
                                 ], 'Division')
    seharusnya = fields.Float('Seharusnya', digits=(5,0))
    rel_division = fields.Selection(related='transfer_id.picking_id.division', string='Division')
    rel_code = fields.Selection(related='transfer_id.picking_id.picking_type_id.code', string='Code')
    tahun_pembuatan = fields.Char('Tahun Pembuatan', size=4, default=time.strftime('%Y'))
    ready_for_sale = fields.Boolean('Ready For Sale', default=True)
    
    @api.multi
    def split_quantities(self) :
        if self.transfer_id.picking_id.picking_type_id.code == "incoming" :
            if self.division == "Sparepart" :
                for det in self:
                    new_id = det.copy(context=self.env.context)
                    new_id.quantity = 1
                    new_id.engine_number = False
                    new_id.chassis_number = False
                    new_id.packop_id = False
            else :
                for det in self :
                    if det.quantity > 1 :
                        det.quantity = (det.quantity - 1)
                        new_id = det.copy(context=self.env.context)
                        new_id.quantity = 1
                        new_id.packop_id = False
        else :
            raise osv.except_osv(('Warning'), ("Maaf untuk transfer out tidak bisa displit"))
        if self and self[0]:
            return self[0].transfer_id.wizard_view()
        
    @api.multi
    def put_in_pack(self):
        newpack = None
        for packop in self:
            if not packop.result_package_id:
                if not newpack:
                    newpack = self.pool['stock.quant.package'].create(self._cr, self._uid, {'location_id': packop.destinationloc_id.id if packop.destinationloc_id else False}, self._context)
                packop.result_package_id = newpack
        if self and self[0]:
            return self[0].transfer_id.wizard_view()
    
    @api.onchange('tahun_pembuatan')
    def tahun_pembuatan_change(self):
        war = {}
        if self.tahun_pembuatan and not self.tahun_pembuatan.isdigit() :
            self.tahun_pembuatan = False
            war = {'title':'Perhatian', 'message':'Tahun Pembuatan hanya boleh angka'}
        return {'warning':war} 
    
    @api.onchange('engine_number','product_id')
    def engine_number_change(self):
        warning={}
        picking_id = self.transfer_id.picking_id
        code = picking_id.picking_type_id.code
        categ_id = self.product_id.categ_id
        sourceloc_type = self.transfer_id.picking_id.picking_type_id.default_location_src_id.usage
        destloc_type = self.transfer_id.picking_id.picking_type_id.default_location_dest_id.usage
        if sourceloc_type == 'transit' :
            picking_type = 'interbranch_in'
        elif destloc_type == 'transit' :
            picking_type = 'interbranch_out'
        else :
            picking_type = 'not_interbranch'
        
        if (code == 'incoming' and picking_id.division == 'Unit') or (code == 'internal' and picking_id.division == 'Unit' and destloc_type == 'transit') or (code == 'internal' and picking_id.division == 'Unit' and sourceloc_type == 'transit') :
            if self.engine_number and (not self.product_id or categ_id.isParentName('Unit')):
                self.engine_number = self.engine_number.replace(" ", "")
                self.engine_number = self.engine_number.upper()
                if len(self.engine_number) != 12 :
                    self.engine_number=False
                    warning['title']=_('Engine Number Salah !')
                    warning['message']=_('Silahkan periksa kembali Engine Number yang Anda input')
                    return {'warning':warning}
                for x in range(len(self.engine_number)) :
                    if self.engine_number[x] in string.punctuation :
                        self.engine_number=False
                        warning['title']=_('Perhatian !')
                        warning['message']=_('Engine Number hanya boleh huruf dan angka')
                        return {'warning':warning}
            
                if code == 'incoming' and picking_id.division == 'Unit' :
                    if self.product_id :
                        obj_prod = self.env['product.template']
                        obj_id = obj_prod.search([('name','=',self.product_id.name)])
                        if obj_id :
                            self.quantity = 1
                            if self.product_id.kd_mesin :
                                self.product_id.kd_mesin = self.product_id.kd_mesin.replace(' ','')
                                pjg = len(self.product_id.kd_mesin)
                                if self.product_id.kd_mesin != self.engine_number[:pjg] :
                                    self.engine_number=False
                                    warning['title']=_('Perhatian !')
                                    warning['message']=_('Engine Number tidak sama dengan kode mesin di Produk')
                                    return {'warning':warning}
                            else :
                                self.engine_number = False
                                warning['title']=_('Perhatian !')
                                warning['message']=_('Silahkan isi kode mesin %s di master product terlebih dahulu' %self.product_id.description)
                                return {'warning':warning}
                        else :
                            self.engine_number = False
                            warning['title']=_('Perhatian !')
                            warning['message']=_('Tidak ditemukan nama product %s di master produk' %self.product_id.name)
                            return {'warning':warning}
                        obj_sn = self.env['stock.production.lot']
                        obj_cek = obj_sn.search([('name','=',self.engine_number)])
                        if obj_cek:
                            self.engine_number=False
                            warning['title']=_('Perhatian !')
                            warning['message']=_('Engine Number sudah pernah ada.')
                            return {'warning':warning}
                elif code == 'internal' and picking_id.division == 'Unit' and destloc_type == 'transit' :
                    product_ids = picking_id.get_product_ids()
                    serial = self.env['stock.production.lot'].search([('name','=',self.engine_number),
                                                                      ('product_id','in',product_ids),
                                                                      ('state','=','stock'),
                                                                      ('location_id','child_of',self.sourceloc_id.id)])
                    if serial :
                        self.chassis_number = serial.chassis_no
                        self.product_id = serial.product_id.id
                        self.product_uom_id = serial.product_id.uom_id.id
                        self.lot_id = serial.id
                        self.sourceloc_id = serial.location_id
                        self.tahun_pembuatan = serial.tahun
                        if serial.ready_for_sale == 'good' :
                            self.ready_for_sale = True
                        else :
                            self.ready_for_sale = False
                    else :
                        warning['title']=_('Perhatian !')
                        warning['message']=_('Tidak ditemukan engine number %s di lokasi %s\nuntuk produk yg akan ditransfer' %(self.engine_number,self.sourceloc_id.name))
                        self.engine_number = False
                        self.chassis_number = False
                        self.product_id = False
                        self.lot_id = False
                        return {'warning':warning}
                elif code == 'internal' and picking_id.division == 'Unit' and sourceloc_type == 'transit' :
                    lots = []
                    for x in picking_id.move_lines :
                        lots.append(x.restrict_lot_id.name)
                    if self.engine_number in lots :
                        serial = self.env['stock.production.lot'].search([('name','=',self.engine_number)])
                        self.chassis_number = serial.chassis_no
                        self.product_id = serial.product_id.id
                        self.product_uom_id = serial.product_id.uom_id.id
                        self.lot_id = serial.id
                        self.tahun_pembuatan = serial.tahun
                        if serial.ready_for_sale == 'good' :
                            self.ready_for_sale = True
                        else :
                            self.ready_for_sale = False
                    else :
                        warning['title']=_('Perhatian !')
                        warning['message']=_('Tidak ditemukan engine number %s untuk produk yg akan ditransfer' %self.engine_number)
                        self.engine_number = False
                        self.chassis_number = False
                        self.product_id = False
                        self.lot_id = False
                        return {'warning':warning}
        else :
            if self.lot_id :
                self.engine_number=self.lot_id.name
            else :
                self.engine_number=False
        return {'warning':warning}
    
    @api.onchange('chassis_number','product_id')
    def chassis_number_change(self) :
        warning = {}
        if self.transfer_id.picking_id.picking_type_id.code == 'incoming':
            if self.chassis_number and (not self.product_id or self.product_id.categ_id.isParentName('Unit')):
                self.chassis_number = self.chassis_number.replace(" ", "")
                self.chassis_number = self.chassis_number.upper()
                if len(self.chassis_number) == 14 or (len(self.chassis_number) == 17 and self.chassis_number[:2] == 'MH') :
                    self.chassis_number = self.chassis_number
                else :
                    self.chassis_number=False
                    warning['title']=_('Chassis Number Salah !')
                    warning['message']=_('Silahkan periksa kembali Chassis Number yang Anda input')
                    return {'warning':warning}
                for x in range(len(self.chassis_number)) :
                    if self.chassis_number[x] in string.punctuation :
                        self.chassis_number=False
                        warning['title']=_('Perhatian !')
                        warning['message']=_('Chassis Number hanya boleh huruf dan angka')
                        return {'warning':warning}
                obj_sn = self.env['stock.production.lot']
                obj_cek = obj_sn.search([('chassis_no','=',self.chassis_number)])
                if obj_cek :
                    self.chassis_number=False
                    warning['title']=_('Perhatian !')
                    warning['message']=_('Chassis Number sudah pernah ada.')
                    return {'warning':warning}
            else :
                self.chassis_number=False
        else :
            if self.lot_id :
                self.chassis_number=self.lot_id.chassis_no
            else :
                self.chassis_number=False
        return {'warning':warning}
    
    @api.onchange('quantity','product_id')
    def quantity_change(self):
        if self.product_id.categ_id.isParentName('Unit'):
            self.quantity = 1
        else :
            self.engine_number = False
            self.chassis_number = False
    
    @api.onchange('product_id')
    def product_id_change(self):
        domain={}
        self.seharusnya = False
        self.product_uom_id = self.product_id.uom_id
        for x in self.transfer_id.picking_id.move_lines :
            if x.product_id.id == self.product_id.id :
                self.seharusnya = x.product_uom_qty
        if self.transfer_id.picking_id.picking_type_id.code == 'outgoing':
            if self.lot_id :
                self.product_id = self.lot_id.product_id.id
        product_ids = self.transfer_id.picking_id.get_product_ids()
        domain['product_id'] = [('id','in',product_ids)]
        return {'domain':domain}
    
    @api.multi
    def source_package_change(self, sourcepackage):
        result = {}
        if sourcepackage:
            pack = self.env['stock.quant.package'].browse(sourcepackage)
            result['sourceloc_id'] = pack.location_id and pack.location_id.id
        return {'value': result, 'domain': {}, 'warning':{} }
