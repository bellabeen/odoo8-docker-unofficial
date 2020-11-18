from openerp import models, fields, api

class B2bApiURL(models.Model):
    _name = "teds.b2b.api.url"

    config_id = fields.Many2one('teds.b2b.api.config',string="Config")
    type = fields.Selection([
        ('authorization','Authorization')],string="Type")
    url = fields.Char('URL')
    is_relative = fields.Boolean('Relative')

    _sql_constraints = [('config_type', 'unique(config_id,type)', 'Type tidak boleh duplikat !')]