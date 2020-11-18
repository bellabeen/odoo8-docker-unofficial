from openerp import models, fields, api, _
from openerp.osv import osv
from openerp.exceptions import Warning
import fnmatch
import os
import os, sys
import shutil
import time
import smtplib
import ast
from __builtin__ import str
from openerp import workflow, exceptions
from datetime import datetime

class b2b_file_monitoring(models.Model):
    _name = 'b2b.file.monitoring'
    _description = 'Monitoring B2B File'
    _order = 'write_date desc'

    def _compute_lot_show(self):
        for monitoring in self:
            if monitoring.lot_data:
                monitoring.lot_show = monitoring.lot_data.replace(',',',\r\n').replace('{','').replace('}','')

    name = fields.Char(string='Nama File/ID')
    keterangan = fields.Char(string='Keterangan')
    date = fields.Datetime(string='Date')
    qty_1 = fields.Float(string='Qty Invoice/FDO')
    qty_2 = fields.Float(string='Qty SL/PS')
    last_check = fields.Datetime(string='Last Check')
    total_check = fields.Float(string='Total Pengecekan', default=1)
    ext = fields.Char(string="Extension")
    type = fields.Char(string="Type")
    lot_data = fields.Text(string='Lot Data')
    lot_show = fields.Text(string='Lot Data', compute='_compute_lot_show')
    lot_id = fields.Many2one('stock.production.lot',string='Existing lot')
    old_line_ids = fields.Many2many('b2b.file.monitoring.line.old', 'b2b_file_monitoring_old_line_rel', 'monitoring_id', 'old_line_id', string='Existing Line')
    new_line_ids = fields.Many2many('b2b.file.monitoring.line.new', 'b2b_file_monitoring_new_line_rel', 'monitoring_id', 'new_line_id', string='New Line')
    state = fields.Selection([
                    ('draft', 'Draft'),
                    ('done', 'Done'),
                    ],string='Status',default='draft')
    # is_processed = fields.Boolean(string='Sudah di proses?')

    @api.multi
    def configuration_file(self):
        configuration_file = {}
        obj_config=self.env['b2b.configuration.folder'].search([('active','=',True)])
        configuration_file.update({
                            'folder_in':obj_config.folder_in,
                            'folder_proses':obj_config.folder_proses,
                            'folder_archin': obj_config.folder_archin,
                            'folder_error': obj_config.folder_error,
                            #'folder_error': "'"+obj_config.folder_eror+"'",
                             }) 
        return configuration_file
    
    @api.multi
    def move_file(self, filename):
        folder = self.configuration_file()
        try:
            # Cek file masih ada di PROC atau tdk
            file_in_process = os.path.exists(os.path.join(folder['folder_proses'],filename))
            file = os.path.join(folder['folder_proses'], filename)
            if not file_in_process:
                # Cek file di folder in
                file_in_process = os.path.exists(os.path.join(folder['folder_in'],filename))
                file = os.path.join(folder['folder_in'], filename)
            if file_in_process:
                # Proses pemindahan ke folder archin dengan tambahan nama file
                base_file, ext = os.path.splitext(os.path.basename(file))
                try:
                    os.rename(file, os.path.join(folder['folder_archin'],(str(base_file)+'-From-Monitoring-('+str(self.type)+')-'+str(self.id)+str(ext))))
                except Exception as err:
                    # raise exceptions.Warning(err)
                    raise exceptions.Warning('Tidak dapat memindah file! File sudah ada di folder ARCIN.')
            if not file_in_process:
                raise exceptions.Warning('File tidak ditemukan di folder PROC/IN! silahkan periksa apakah file sudah dipindahkan.')
        except Exception as err:
            raise Warning("%s" %err)

    @api.multi
    def move(self):
        self.move_file(self.name)
    
    @api.multi
    def process_remaining_line(self):
        if len(self.new_line_ids) > len(self.old_line_ids):
            # import ipdb; ipdb.set_trace()
            line_ids = []
            b2b_file_id = self.old_line_ids[0].b2b_file_id
            nomor = len(self.old_line_ids)
            for line in self.new_line_ids:
                # Cek apakah line sudah ada di b2b.file.content
                old_line = self.env['b2b.file.content'].search([('b2b_file_id','=',b2b_file_id),('name','=',str(line.name))])
                if not old_line:
                    print ("+1")
                    line_ids.append({
                        'name':line.name,
                        'nomor':nomor,
                        'b2b_file_id':b2b_file_id,
                    })
                    nomor = nomor+1
            # prosess
            if len(line_ids) == 0:
                raise Warning("Tidak terdapat perbedaan antara line baru dan lama.")
            else:
            # SCENARIO 1: B2B file-> state blm done
                # cek state b2b_file
                b2b_file =  self.env['b2b.file'].search([('id','=',b2b_file_id)])
                if b2b_file and b2b_file.state in ('open','error'):
                    for res in line_ids:
                        self.env['b2b.file.content'].create(res)
                    # ubah state monitoring + pindah file ke archin
                    self.state = 'done'
                    self.move_file(self.name)
            # SCENARIO 2: B2B file -> state sudah done
                elif b2b_file and b2b_file.state == 'done':
                    # Cari invoice header dari b2b.file yang sudah done (sudah dibuat inv header+line nya)
                    data = self.old_line_ids[0].name.split(';')
                    inv_line = self.env['b2b.file.inv.line'].search([
                        ('no_ship_list','=', data[5]),
                        ('no_sipb','=', data[6]),
                        ('kode_type','=', data[7]),
                        ('kode_warna','=', data[8]),
                        ('qty','=', data[9]),
                        ('amount','=', data[10]), 
                        ('ppn','=', data[11]),
                        ('pph','=', data[12]),
                        ('discount_quotation','=', data[13]),
                        ('discount_type_cash','=', data[14]),
                        ('discount_other','=', data[15]),
                    ],limit = 1)
                    inv_head = self.env['b2b.file.inv.header'].search([('id','=',inv_line.b2b_file_inv_header_id.id)])
            # SCENARIO 2.1: INVOICE HEADER -> state blm done
                    if inv_head and inv_head.state in ('draft','error'):
                        purchase_line=False
                        for res in line_ids:
                            content = res['name'].split(';')

                            obj_sipb=self.env['b2b.file.sipb'].search([('no_sipb','=',content[6]),
                                                              ('kode_type','=',content[7]),
                                                              ('kode_warna','=',content[8]),
                                                              ])
                            #TODO UBAH MENJADI QUERY
                            obj_warna=self.env['product.attribute.value'].search([('code','=',content[8])]) 
                            obj_product=self.env['product.product'].search([('name','=',content[7]),('attribute_value_ids','=',obj_warna.id)])
                            if not obj_product :
                                obj_product=self.env['product.product'].search([('name','=',content[7])], limit = 1)
                            
                            if obj_product:
                                product_id = obj_product.id
                            else:
                                raise Warning('Product %s tidak ditemukan!' %(content[7]))
                            
                            obj_pucrhase_order=self.env['purchase.order'].search([('name','=',obj_sipb.no_po_md)])
                            if obj_pucrhase_order :
                                obj_purchase_order_content=self.env['purchase.order.content'].search([('order_id','=',obj_pucrhase_order.id),('product_id','=',product_id),])
                                if obj_purchase_order_content :                                                      
                                    purchase_line=obj_purchase_order_content.id
                                
                            inv_header_line = {
                                'no_ship_list' : content[5], 
                                'purchase_order_content_id':purchase_line,
                                'b2b_file_inv_header_id':inv_head.id,
                                'no_sipb' : content[6],
                                'kode_type' : content[7],
                                'kode_warna': content[8],
                                'qty': content[9],
                                'amount': content[10],  
                                'ppn': content[11],
                                'pph': content[12],
                                'discount_quotation': content[13],
                                'discount_type_cash': content[14],
                                'discount_other': content[15],                
                            }
                            inv_line_id = self.env['b2b.file.inv.line'].create(inv_header_line)
                            b2b_file_content = self.env['b2b.file.content'].create(res)
                        self.state = 'done'
                        self.move_file(self.name)
            # SCENARIO 2.2: INVOICE HEADER -> state sudah done
                    elif inv_head and inv_head.state == 'done':
                        raise Warning('Invoice sudah pada status done!')
                    elif not inv_head:
                        raise Warning('Invoice tdk ditemukan')
        else:
            raise Warning("Jumlah invoice line lama lebih banyak/Sama dengan line baru")
    
    @api.multi
    def process_lot_update(self):
        lot = ast.literal_eval(self.lot_data)
        self.lot_id.write(lot)
    
class b2b_file_monitoring_line_old(models.Model):
    _name = 'b2b.file.monitoring.line.old'

    name = fields.Char(string='Name')
    nomor = fields.Integer(string='Nomor')
    monitoring_id = fields.Many2one('b2b.file.monitoring', string='Monitoring id',ondelete='cascade', index=True)
    b2b_file_id = fields.Integer(string='B2B File ID')

class b2b_file_monitoring_line_new(models.Model):
    _name = 'b2b.file.monitoring.line.new'

    name = fields.Char(string='Name')
    nomor = fields.Integer(string='Nomor')
    monitoring_id = fields.Many2one('b2b.file.monitoring', string='Monitoring id',ondelete='cascade', index=True)

    
    
