from datetime import date, datetime, timedelta
import base64
import xlrd
from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, ValidationError
import openerp.addons.decimal_precision as dp

class MasterActBudgetCategory(models.Model):
    _name = "teds.master.act.budget.category"
    _description = "Master Kategori Activity Budget"

    code = fields.Char(string='Kode Kategori')
    name = fields.Char(string='Nama Kategori')
    active = fields.Boolean(string='Aktif?', default=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', "Kode kategori harus unik.")]

class MasterActBudget(models.Model):
    _name = "teds.master.act.budget"
    _description = "Master Activity Budget"

    def _get_year(self):
        current_year = 2019
        two_next_year = int(current_year)+2
        years_available = []

        for x in range(current_year, two_next_year):
            elem = ("{}".format(x), "{}".format(x))
            years_available.append(elem)

        # print years_available
        return years_available

    year = fields.Selection(_get_year, string='Tahun')
    name = fields.Char(string='Kode Budget')
    department_id = fields.Many2one('hr.department', string='Departemen', ondelete='restrict')
    category_id = fields.Many2one('teds.master.act.budget.category', string='Kategori', ondelete='restrict')
    activity = fields.Text(string='Keterangan Aktivitas')
    amount_avb = fields.Float(string='Available Budget', digits=dp.get_precision('Product Price'))
    amount_init = fields.Float(string='Initial Budget', digits=dp.get_precision('Product Price'))

    # @api.constrains('year','category_id')
    # def _check_multiple_others(self):
    #     over_category_id = self.env.ref('teds_master_act_budget.teds_master_act_budget_category_over').id
    #     if self.category_id == over_category_id:
    #         act_count = self.search_count([
    #             ('year','=',self.year),
    #             ('category_id','=',over_category_id),
    #             ('department_id','=',self.department_id.id)
    #         ])
    #         if act_count > 1:
    #             raise ValidationError('Master budget %s untuk departemen %s di tahun %s sudah ada.' % (self.category_id.name, self.department_id.name, self.year))

    # @api.onchange('category_id')
    # def _onchange_category(self):
    #     over_category_id = self.env.ref('teds_master_act_budget.teds_master_act_budget_category_over').id
    #     if self.category_id == over_category_id:
    #         self.activity = False

    @api.model
    def create(self, vals):
        category_code = self.env['teds.master.act.budget.category'].browse(vals['category_id']).code
        prefix = 'TDM/MD/%s/%s' % (vals['year'], category_code)
        vals['name'] = self.env['ir.sequence'].get_per_department(vals['department_id'], prefix)
        return super(MasterActBudget, self).create(vals)

    @api.multi
    def copy(self):
        raise Warning('Perhatian!\nTidak bisa duplikat data.')

class MasterActBudgetUpload(models.TransientModel):
    _name = "teds.master.act.budget.upload.wizard"
    _description = "Upload Master Activity Budget"

    @api.multi
    def _get_default_date(self):
        return date.today()

    master_file = fields.Binary(string='File Master')
    date_upload = fields.Date(string='Tanggal', default=_get_default_date, readonly=True)
    success_msg = fields.Char()
    error_msg = fields.Html()
    state = fields.Selection([
        ('choose','choose'),
        ('get','get')
    ], default='choose')

    @api.multi
    def action_upload(self):
        # URUTAN KOLOM: tahun, kode departemen, kategori budget, keterangan aktivitas
        data = base64.decodestring(self.master_file)
        excel = xlrd.open_workbook(file_contents = data)  
        sh = excel.sheet_by_index(0)
        # success message
        self.success_msg = ""
        # error message
        self.error_msg = ""
        # import ipdb
        # ipdb.set_trace()
        # LoV budget category
        category_obj = self.env['teds.master.act.budget.category']
        category_master = [k.code for k in category_obj.search([])]
        # looping on excel row
        for rx in range(1,sh.nrows): 
            year = ""
            # when year interpreted by xlrd as text
            if sh.cell(rx,0).ctype == 1: # XL_CELL_TEXT
                year = str(sh.cell(rx,0).value).strip()
                # validate year character
                if not year.isdigit():
                    self.error_msg += '(Baris %d) Tahun <strong>%s</strong> tidak valid.<br/>' % (rx+1, year)
                    continue
            # when year interpreted by xlrd as number (float)
            elif sh.cell(rx,0).ctype == 2: # XL_CELL_NUMBER
                # float to int
                year = str(int(sh.cell(rx,0).value))
            # validate year length
            if len(year) != 4:
                self.error_msg += '(Baris %d) Tahun <strong>%s</strong> tidak valid.<br/>' % (rx+1, year)
                continue
            # ipdb.set_trace()
            dept_code = str(sh.cell(rx, 1).value)
            category_code = str(sh.cell(rx, 2).value)
            activity = str(sh.cell(rx, 3).value)
            amount_avb = str(sh.cell(rx, 4).value)
            # ipdb.set_trace()
            # search for dept code
            dept_obj = self.env['hr.department'].sudo().search([
                ('department_code','=',dept_code)
            ],limit=1)
            if not dept_obj:
                self.error_msg += '(Baris %d) Departemen dengan kode <strong>%s</strong> tidak ditemukan.<br/>' % (rx+1, dept_code)
                continue
            # validate category_code
            if category_code.upper() not in category_master:
                self.error_msg += '(Baris %d) Kategori <strong>%s</strong> tidak valid.<br/>' % (rx+1, category_code.upper())
                continue
            # validate activity
            if len(activity) <= 0:
                self.error_msg += '(Baris %d) Keterangan aktivitas kosong.<br/>' % (rx+1)
                continue
            # validate amount_avb
            try:
                if float(amount_avb) <= 0:
                    self.error_msg += '(Baris %d) Available Budget kurang dari sama dengan nol.<br/>' % (rx+1)
                    continue
            except ValueError:
                self.error_msg += '(Baris %d) Available Budget <strong>%s</strong> tidak valid.<br/>' % (rx+1, amount_avb)
                continue
            # ipdb.set_trace()
            act_vals = {
                'year': year,
                'department_id': dept_obj.id,
                'category_id': category_obj.search([('code','=',category_code.upper())], limit=1).id,
                'activity': activity,
                'amount_avb': amount_avb,
                'amount_init': amount_avb
            }
            # create_act = False
            try:
                self.env['teds.master.act.budget'].create(act_vals)
            except ValidationError as e:
                # import ipdb
                # ipdb.set_trace()
                self._cr.rollback()
                self.error_msg += "%s<br />" % e[1]
                continue
            
            self._cr.commit()
        # ipdb.set_trace()
        if not self.error_msg:
            self.success_msg += "Data berhasil diupload seluruhnya."

        form_id = self.env.ref('teds_master_act_budget.view_teds_master_act_budget_upload_wizard').id
        self.write({'state': 'get'})
        return {
            'name': 'Hasil Upload',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.master.act.budget.upload.wizard',
            'res_id': self.ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }