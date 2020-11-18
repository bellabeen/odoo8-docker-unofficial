# -*- coding: utf-8 -*-
from openerp import models, fields, api
class MasterRing(models.Model):
	_name = 'master.ring'
	name = fields.Char('Ring name', required=True)