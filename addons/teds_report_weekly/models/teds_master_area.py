from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning

class ReportWkeelyMasterArea(models.Model):
    _name = "teds.report.weekly.master.area"

    def _get_main_dealer(self):
        results = self.env['teds.report.weekly.master.main.dealer'].search([])
        data = []
        for result in results:
            data.append((result.name,result.name))
        return data

    name = fields.Char('Kabupaten')
    main_dealer = fields.Selection(_get_main_dealer,'Main Dealer')
    user_ids = fields.Many2many('res.users','teds_area_user_report_weekly','area_id','user_id','Users')
    dealer_ids = fields.One2many('teds.report.weekly.dealer','area_id')

    _sql_constraints = [('unique_name', 'unique(name)', 'Kabupaten tidak boleh duplikat !')]

    @api.model
    def create(self,vals):
        if vals.get('name'):
            vals['name'] = vals['name'].upper()
        if not vals.get('dealer_ids'):
            raise Warning("Dealer harus diisi !") 
        return super(ReportWkeelyMasterArea,self).create(vals)
    
    @api.multi
    def write(self,vals):
        if vals.get('name'):
            vals['name'] = vals['name'].upper()
        write = super(ReportWkeelyMasterArea,self).write(vals)
        if not self.dealer_ids:
            raise Warning('Dealer harus diisi !')
        return write
    
    @api.multi
    def name_get(self, context=None):
        if context is None:
            context = {}
        res = []
        for record in self :
            name = "[%s] %s" % (record.name, record.main_dealer)
            res.append((record.id, name))
        return res

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        if name:
            # Be sure name_search is symetric to name_get
            args = ['|',('name', operator, name),('main_dealer', operator, name)] + args
        categories = self.search(args, limit=limit)
        return categories.name_get()

class ReportWkeelyDealer(models.Model):
    _name = "teds.report.weekly.dealer"

    area_id = fields.Many2one('teds.report.weekly.master.area','Area',ondelete='cascade')
    type = fields.Selection([('Cabang','Cabang'),('Non Cabang','Non Cabang')],string="Type")
    branch_id = fields.Many2one('wtc.branch','Branch',index=True)
    name = fields.Char('Name')


    @api.onchange('type')
    def onchange_type(self):
        self.branch_id = False

    @api.onchange('branch_id')
    def onchange_branch(self):
        self.name = False
        if self.branch_id:
            self.name = self.branch_id.name.upper()