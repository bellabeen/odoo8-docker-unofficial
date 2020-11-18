from openerp import models, fields, api

class MasterResultLeadActivity(models.Model):
    _name = "teds.master.result.lead.activity"
    _order = 'sequence, id'

    name = fields.Char('Result')
    keterangan = fields.Char('Keterangan')
    sequence = fields.Integer('Sequence')
    is_end_proses = fields.Boolean('End Proses')
    minat = fields.Selection([
        ('all','All'),
        ('cold', 'Cold'),
        ('medium', 'Medium'),
        ('hot', 'Hot'),
        ('lose', 'Lose')],string="Minat")

    _sql_constraints = [('name_unique', 'unique(name)', 'Result sudah dibuat.')]