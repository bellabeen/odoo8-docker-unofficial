from openerp import models, fields, api
from openerp.exceptions import Warning, ValidationError

class NrfsMasterGejala(models.Model):
    _name = "teds.nrfs.master.gejala"
    _description = "NRFS - Master Gejala"

    code = fields.Char(string='Kode')
    name = fields.Char(string='Gejala')

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Kode gejala harus unik!'),
    ]

    @api.model
    def create(self, vals):
        if vals.get('code', False):
            vals['code'] = str(vals['code']).replace(" ","")
        return super(NrfsMasterGejala, self).create(vals)

    @api.model
    def write(self, vals):
        if vals.get('code', False):
            vals['code'] = str(vals['code']).replace(" ","")
        return super(NrfsMasterGejala, self).write(vals)