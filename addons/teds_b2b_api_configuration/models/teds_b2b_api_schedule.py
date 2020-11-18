from openerp import models, fields, api
from openerp.exceptions import Warning

class B2bApiSchedule(models.Model):
    _name = "teds.b2b.api.schedule"

    name = fields.Char('Schedule')
    detail_ids = fields.One2many('teds.b2b.api.schedule.detail','schedule_id')

class B2bApiScheduleDetail(models.Model):
    _name = "teds.b2b.api.schedule.detail"

    schedule_id = fields.Many2one('teds.b2b.api.schedule','Schedule',ondelete='cascade')
    jam = fields.Char("Jam")
    menit = fields.Char('Menit')
    time = fields.Char('Time')

    _sql_constraints = [('jam_menit_unique', 'unique(jam,menit,schedule_id)', 'Jam Menit tidak boleh duplikat !.')]

    @api.constrains('jam')
    def _constrains_jam(self):
        if not self.jam.isdigit():
            raise Warning('Jam tidak boleh mengandung karakter !')
        if not self.menit.isdigit():
            raise Warning('Menit tidak boleh mengandung karakter !')

