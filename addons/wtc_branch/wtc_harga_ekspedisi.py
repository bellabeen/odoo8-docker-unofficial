import time
from datetime import datetime
from openerp import models, fields, api
from openerp.osv import osv
from string import whitespace

class wtc_branch_harga_ekspedisi(models.Model):
    _inherit = 'wtc.branch'
    harga_ekspedisi_ids = fields.One2many('wtc.harga.ekspedisi','branch_id',string="Harga Ekspedisi")
    
class wtc_harga_ekspedisi(models.Model):
    _name = "wtc.harga.ekspedisi"
    _description = 'Harga Ekspedisi'

    branch_id = fields.Many2one('wtc.branch',string="Branch")
    ekspedisi_id = fields.Many2one('res.partner',domain=[('forwarder','=',True)],string="Ekspedisi")
    default_ekspedisi = fields.Boolean(string="Default")
    kota_penerimaan = fields.Selection([
                              ('lampung','Lampung'),
                              ], 'Kota Penerimaan', default='lampung')
    harga_ekspedisi_id = fields.Many2one('wtc.pricelist.expedition',string="Harga Ekspedisi")
    
    _sql_constraints = [
                        ('unique_ekspedisi', 'unique(branch_id,ekspedisi_id,kota_penerimaan)', "'Ekspedisi' tidak boleh ada yang sama !"),  
                        ]
    
class wtc_pricelist_expedition(models.Model):
    _name = "wtc.pricelist.expedition"
    _description = "Pricelist Expedition"
    
    name = fields.Char('Name',required=True)
    active = fields.Boolean('Active',default=True)
    pricelist_expedition_line_ids = fields.One2many('wtc.pricelist.expedition.line','pricelist_expedition_id',string="Pricelist Expedition Lines", copy=True)
    
class wtc_pricelist_expedition_line(models.Model):
    _name = "wtc.pricelist.expedition.line"
    _description = 'Pricelist Expedition Line'

    pricelist_expedition_id = fields.Many2one('wtc.pricelist.expedition', 'Pricelist Expedition', required=True, select=True, ondelete='cascade')
    name = fields.Char('Name',required=True)
    start_date = fields.Date('Start Date',required=True)
    end_date = fields.Date('End Date',required=True)
    active = fields.Boolean('Active',default=True)
    pricelist_expedition_line_detail_ids = fields.One2many('wtc.pricelist.expedition.line.detail','pricelist_expedition_line_id',string='Pricelist Expedition Line Details', required=True, copy=True)

    @api.onchange('start_date','end_date')
    def onchange_end_date(self):
        warning = {}
        if self.start_date and self.end_date :
            if self.end_date <= self.start_date :
                self.end_date = False
                warning = {
                           'title': ('Perhatian !'),
                           'message': ('End Date tidak boleh lebih kecil dari Start Date'),
                           }
        return {'warning':warning}
    
    def _check_date(self, cr, uid, ids, context=None):
        pricelist_expedition_line_id = self.browse(cr, uid, ids, context=context)
        ids_pricelist_expedition_line = self.pool.get('wtc.pricelist.expedition.line').search(cr,uid,[
                                                                                                      ('pricelist_expedition_id','=',pricelist_expedition_line_id.pricelist_expedition_id.id),
                                                                                                      ('active','=',True),
                                                                                                      ('id','!=',pricelist_expedition_line_id.id),
                                                                                                      ])
        if ids_pricelist_expedition_line :
            pricelist_expedition_line_ids = self.pool.get('wtc.pricelist.expedition.line').browse(cr,uid,ids_pricelist_expedition_line)
            for pricelist_expedition_line in pricelist_expedition_line_ids :
                if pricelist_expedition_line_id.start_date <= pricelist_expedition_line.end_date :
                    return False
        return True

    _constraints = [
                    (_check_date, 'You cannot have 2 pricelist versions that overlap!', ['start_date', 'end_date', 'active'])
                    ]
    
class wtc_pricelist_expedition_line_detail(models.Model):
    _name = 'wtc.pricelist.expedition.line.detail'
    _description = 'Pricelist Expedition Line Detail'

    pricelist_expedition_line_id = fields.Many2one('wtc.pricelist.expedition.line', string='Pricelist Expedition Line', select=True, ondelete='cascade')
    product_template_id = fields.Many2one('product.template','Product',required=True)
    cost = fields.Float('Cost',required=True)

    _sql_constraints = [
                        ('unique_product', 'unique(pricelist_expedition_line_id,product_template_id)', 'Ditemukan produk duplicate, mohon cek kembali !'),
                        ]
    
    @api.onchange('product_template_id')
    def product_change(self):
        domain = {}
        categ_unit = self.env['product.category'].get_child_ids('Unit')
        categ_sparepart = self.env['product.category'].get_child_ids('Sparepart')
        categ_umum = self.env['product.category'].get_child_ids('Umum')
        categ_ids = categ_unit + categ_sparepart + categ_umum
        domain['product_template_id'] = [('categ_id','in',categ_ids)]
        return {'domain':domain}
    