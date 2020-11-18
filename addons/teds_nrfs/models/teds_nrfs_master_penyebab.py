from openerp import models, fields, api
from openerp.exceptions import Warning, ValidationError

class NrfsMasterPenyebab(models.Model):
    _name = "teds.nrfs.master.penyebab"
    _description = "NRFS - Master Penyebab"

    code = fields.Char(string='Kode')
    name = fields.Char(string='Penyebab')

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Kode penyebab harus unik!'),
    ]

    @api.model
    def create(self, vals):
        if vals.get('code', False):
            vals['code'] = str(vals['code']).replace(" ","")
        return super(NrfsMasterPenyebab, self).create(vals)

    @api.model
    def write(self, vals):
        if vals.get('code', False):
            vals['code'] = str(vals['code']).replace(" ","")
        return super(NrfsMasterPenyebab, self).write(vals)