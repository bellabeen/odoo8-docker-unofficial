from openerp import models, fields, api

class wtc_incentive_finco_line(models.Model):
    _name = 'wtc.incentive.finco.line'
    _description = 'Incentive Finco'

    partner_id = fields.Many2one('res.partner','Partner',required=True,ondelete="cascade")
    name = fields.Char('Name',required=True)
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    active = fields.Boolean('Active',default=True)
    incentive_finco_detail_ids = fields.One2many('wtc.incentive.finco.line.detail', 'incentive_finco_line_id', 'Details')
    is_include_ppn = fields.Boolean('Include PPN', default=True)
    
class wtc_incentive_fincoy_line_detail(models.Model):
    _name = 'wtc.incentive.finco.line.detail'

    @api.cr_uid_ids_context
    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 


    incentive_finco_line_id = fields.Many2one('wtc.incentive.finco.line','Incentive Line',required=True)
    branch_id = fields.Many2one('wtc.branch','Branch',required=True, default=_get_default_branch)
    incentive = fields.Float('Incentive',required=True)
