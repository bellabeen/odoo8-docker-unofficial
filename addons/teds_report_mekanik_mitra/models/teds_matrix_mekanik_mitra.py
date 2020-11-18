from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning
from datetime import date, datetime, timedelta,time

class MatrixMeknikMitra(models.Model):
    _name = "teds.matrix.mekanik.mitra"
    _rec_name = "branch_id"

    branch_id = fields.Many2one('wtc.branch','Branch')
    detail_ids = fields.One2many('teds.matrix.mekanik.mitra.detail','matrix_id')

    _sql_constraints = [('mekanik_id_unique', 'unique(branch_id)', 'Master branch tidak boleh duplikat !')]

class MatrixMeknikMitraDetail(models.Model):
    _name = "teds.matrix.mekanik.mitra.detail"

    matrix_id = fields.Many2one('teds.matrix.mekanik.mitra',ondelete='cascade')
    min_ue = fields.Float('Min UE')
    max_ue = fields.Float('Max UE')
    hari_kerja = fields.Float('Hari Kerja')
    jasa = fields.Float('Jasa')
    part = fields.Float('Part')



