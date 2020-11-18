from openerp import models, fields, api
from openerp.exceptions import Warning, ValidationError

class NrfsMasterPenangananUnit(models.Model):
    _name = "teds.nrfs.master.penanganan.unit"
    _description = "NRFS - Master Penanganan Unit"

    code = fields.Char(string='Kode')
    name = fields.Char(string='Aktivitas Penanganan di MD')
    master_type = fields.Selection([
        ('vendor','Vendor'),
        ('md','MD')
    ], string='Showed on')

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Nilai penanganan unit harus unik!'),
    ]

    @api.model
    def create(self, vals):
        if vals.get('code', False):
            vals['code'] = str(vals['code']).replace(" ","")
        return super(NrfsMasterPenangananUnit, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('code', False):
            vals['code'] = str(vals['code']).replace(" ","")
        return super(NrfsMasterPenangananUnit, self).write(vals)