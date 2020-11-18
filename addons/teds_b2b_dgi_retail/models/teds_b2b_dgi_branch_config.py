from openerp import models, fields, api
from openerp.exceptions import Warning

class B2bDgiBranchConfig(models.TransientModel):
    _name = "teds.b2b.dgi.branch.config"
    
    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()

    branch_id = fields.Many2one('wtc.branch', string='Branch')
    type_dgi = fields.Selection([('H1','H1'),('H23','H23')],string="Type")
    config_id = fields.Many2one('teds.b2b.api.config','Config',domain=[('is_dgi','=',True)])
    
    # Params Set
    date = fields.Date('Date',default=_get_default_date)
    no_prospect = fields.Char('ID Prospect',help="Nomor Prospect Main Dealer")
    no_spk = fields.Char('ID SPK',help="Nomor SPK Main Dealer")
    no_wo = fields.Char('ID Work Order',help="Nomor PKB Main Dealer")
    type_h23 = fields.Selection([('PKB','PKB'),('PRSL','Part Sales')],default='PKB')
    
    # Multi POS 
    is_pos_dgi = fields.Boolean('Is Multi POS ?')

    @api.onchange('no_wo')
    def onchange_no_wo(self):
        if self.no_wo:
            self.no_wo = self.no_wo.strip()
    
    @api.onchange('no_prospect')
    def onchange_spk(self):
        if self.no_prospect:
            self.no_spk = False
    
    @api.onchange('no_spk')
    def onchange_prospect(self):
        if self.no_spk:
            self.no_prospect = False


    @api.onchange('branch_id','type_dgi')
    def onchange_config(self):
        if self.branch_id and self.type_dgi:
            branch_config = self.env['wtc.branch.config'].suspend_security().search([
                ('branch_id','=',self.branch_id.id)],limit=1)
            config_dgi_id = False
            if self.type_dgi == 'H1':
                config_dgi_id  = branch_config.config_dgi_id
            elif self.type_dgi == 'H23':
                config_dgi_id = branch_config.config_dgi_h23_id
            if not config_dgi_id:
                self.branch_id = False
                warning = {'title':'Perhatian !','message':'Branch Config DGI belum di setting !'}
                return {'warning':warning}

            self.config_id = config_dgi_id.id
            self.is_pos_dgi = self.branch_id.is_pos_dgi

    def _get_data_order(self):
        return False
    
    def _get_data_work_order(self):
        return False
        
    @api.multi
    def action_execute_order(self):
        if not self.config_id:
            raise Warning("Config tidak ada !")
        if self.type_dgi == 'H1':
            if not self.no_prospect and not self.no_spk:
                raise Warning("Pilih salah satu pencarian berdasarkan ID SPK atau ID Prospect !")
            data = self._get_data_order()
        else:
            data = self._get_data_work_order()
        if not data:
            raise Warning("Data Order tidak tersedia !")
