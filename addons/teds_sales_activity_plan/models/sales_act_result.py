# -*- coding: utf-8 -*-
from openerp import models, fields, api
class SalesActResult(models.Model):
    _name = 'sales.result'
    #_inherit = 'sales.plan'
    sales_result_line = fields.One2many('sales.result.line', 'sales_result_id', required=True)
    branch_id = fields.Many2one('wtc.branch', 'Branch', required=True)
    month = fields.Selection([('1','Januari'),
                              ('2','Februari'),
                              ('3','Maret'),
                              ('4','April'),
                              ('5','Mei'),
                              ('6','Juni'),
                              ('7','Juli'),
                              ('8','Agustus'),
                              ('9','September'),
                              ('10','Oktober'),
                              ('11','November'),
                              ('12','Desember')], 'Bulan', required=True)
    
    @api.onchange('branch_id')
    def month_change(self):
        self.month = False

class SalesActPlanLine(models.Model):
    _name = 'sales.result.line'
    
    sales_result_id = fields.Many2one('sales.result', required=True)
    titik_keramaian_id = fields.Many2one('titik.keramaian', 'Titik Keramaian',required=True)
    ring_id = fields.Many2one(related='titik_keramaian_id.ring_id', string='Ring name')
    kecamatan_id = fields.Many2one(related='titik_keramaian_id.kecamatan_id', string='Kecamatan')
    act_type_id = fields.Many2one('master.act.type', 'Activity Type', required=True)
    pic_id = fields.Many2one('hr.employee', 'PIC', required=True)
    target_unit = fields.Integer('Target Unit', required=True)
    target_data_cust = fields.Integer('Target Data Customer', required=True)
    actual_unit = fields.Integer('Actual Unit', required=True)
    actual_data_cust = fields.Integer('Actual Data Customer', required=True)
    estimasi_biaya = fields.Float('Estimasi Biaya')
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    
    @api.onchange('titik_keramaian_id')
    def ring_id_change(self):
        self.ring_id = False
        
        dom = {}
        
        titik_keramaian_id = self.titik_keramaian_id.id
        #print titik_keramaian_id
        
        if titik_keramaian_id:
            ring_id_search = self.env['titik.keramaian'].search([('id','=', titik_keramaian_id)]).ring_id.id
            #print ring_id_search
            self.ring_id = ring_id_search
            dom['ring_id']=[('id','=',ring_id_search)]
            return {'domain':dom}
        
    @api.onchange('ring_id')
    def kecamatan_id_change(self):
        self.kecamatan_id = False
        
        dom = {}
        
        titik_keramaian_id = self.titik_keramaian_id.id
        #print titik_keramaian_id
        
        if titik_keramaian_id:
            kec_id_search = self.env['titik.keramaian'].search([('id','=', titik_keramaian_id)]).kecamatan_id.id
            #print kec_id_search
            self.kecamatan_id = kec_id_search
            dom['kecamatan_id']=[('id','=',kec_id_search)]
            return {'domain':dom}