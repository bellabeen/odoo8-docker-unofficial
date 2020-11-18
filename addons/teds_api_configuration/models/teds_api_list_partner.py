from openerp import api, fields, models, SUPERUSER_ID
from openerp.tools.translate import _

class TedsApiListPartner(models.Model):
    _name = 'teds.api.list.partner'

    name = fields.Char('Name',required=True)
    partner_ids = fields.Many2many('res.partner','teds_api_list_partner_rel','api_list_partner_id','parter_id','Branches',required=True
    , domain="['|','|',('ahass','=',True),('dealer','=',True),('branch','=',True)]")
   

   