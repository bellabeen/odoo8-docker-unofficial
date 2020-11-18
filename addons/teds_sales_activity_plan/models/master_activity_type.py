# -*- coding: utf-8 -*-
from openerp import models, fields, api
class MasterActType(models.Model):
	_name = 'master.act.type'
	name = fields.Char('Activity Type', required=True)
	code = fields.Char('Code', required=True)