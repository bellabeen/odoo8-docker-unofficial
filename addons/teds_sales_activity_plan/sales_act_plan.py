# -*- coding: utf-8 -*-
from openerp import models, fields, api
class SalesActPlan(models.Model):
    _name = 'sales.plan'
    name = fields.Char('Sales Activity Plan')
    sales_activity_line = fields.One2many('sales.plan.line', 'sales_activity_id', required=True)
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
                              ('12','Desember')], 'Bulan')
    
    
class SalesActPlanLine(models.Model):
    _name = 'sales.plan.line'
    
    sales_activity_id = fields.Many2one('sales.plan', required=True)
    titik_keramaian_id = fields.Many2one('titik.keramaian', 'Titik Keramaian',
                                      required=True)
    ring_id = fields.Many2one(related='titik_keramaian_id.ring_id', string='Ring name')
    kecamatan_id = fields.Many2one(related='titik_keramaian_id.kecamatan_id', string='Kecamatan')
    act_type_id = fields.Many2one('master.act.type', 'Activity Type', required=True)
    pic_id = fields.Many2one('hr.employee', 'PIC', required=True)
    plan = fields.Selection([('1','Ada'),('2','Tidak Ada')], 'Plan', required=True)
    target_unit = fields.Integer('Target Unit', required=True)
    target_data_cust = fields.Integer('Target Data Customer', required=True)