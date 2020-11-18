# -*- coding: utf-8 -*-
from openerp import models, fields, api
class RingKecamatan(models.Model):
	_name = 'ring.kecamatan'
	branch_id = fields.Many2one('wtc.branch', string='Branch', required=True)
	ring_kecamatan_line = fields.One2many('ring.kecamatan.line', 
										'ring_kecamatan_id', required=True)
	
class RingKecamatanLine(models.Model):
	_name = 'ring.kecamatan.line'
	ring_kecamatan_id = fields.Many2one('ring.kecamatan', required=True)
	kecamatan_id = fields.Many2one('wtc.kecamatan', string='Kecamatan',required=True)
	#name = fields.Many2one('master.ring', 'Ring name', required=True)
	ring_id = fields.Many2one('master.ring', 'Ring name', required=True)