from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from datetime import datetime
from openerp import workflow
from openerp.tools.translate import _


class wtc_approval_config(models.Model):
    _name ="wtc.approval.config"
    
    name = fields.Char(string="Name")
    form_id = fields.Many2one('ir.model',string="Form")
    code = fields.Selection([
        (' ',' '),
        ('payment','Payment'),
        ('receipt','Receipt'),
        ('purchase','Purchase'),
        ('sale','Sale'),
        ('cancel','Cancel')],string="Code",default=' ')
    type = fields.Selection([('biaya','Biaya'),('discount','Discount')])
    
    _sql_constraints = [
    ('unique_name_form_id', 'unique(form_id,code,type)', 'Master sudah ada !'),
]      
    
    @api.onchange('type')
    def change_form_id(self):
        domain ={}
        if self.type == 'discount' :
            domain['form_id'] = [('model','=','dealer.sale.order')]
            form = self.env['ir.model'].search([
                                                ('model','=','dealer.sale.order')
                                                ])
            self.form_id = form.id
        elif self.type == 'biaya' :
            domain['form_id'] = [('model','!=','dealer.sale.order')]
            self.form_id = False
        elif not self.type :
            self.form_id = False
        return {'domain':domain}