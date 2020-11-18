from openerp import api, fields, models, SUPERUSER_ID
from openerp.tools.translate import _

class wtc_area(models.Model):
    _name = 'wtc.area'
    _inherit = ['mail.thread']
    _rec_name='code'

    code = fields.Char('Code',required=True)
    description = fields.Char('Description',required=True)
    branch_ids = fields.Many2many('wtc.branch','wtc_area_cabang_rel','area_id','branch_id','Branches',required=True)
    
    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            tit = "[%s] %s" % (record.code, record.description)
            res.append((record.id, tit))
        return res
    
    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Code tidak boleh ada yang sama.'),  
    ]
    
#     @api.model
#     def create(self,vals,context=None):
#         branch_id = []
#         for x in vals['branch_ids'] :
#             branch_id.append(x[2])
#         branch_name = ''
#         area_id = super(wtc_area, self).create(vals)
#         
#         for code in branch_id :
#             for id in code :
#                 branch_code = self.env['wtc.branch'].search([('id','=',id)])                
#                 branch_name += ('- '+str(branch_code.name)+'<br/>')
#                 
#         msg = _("Add Branches : <br/> %s") % \
#                 (str(branch_name))
#         area_id.message_post(body=msg)                        
#         return area_id    
#     
#     @api.multi
#     def write(self,vals,context=None):
#         if vals.get('branch_ids',False):
#             print "branch _ids",vals['branch_ids']
#             branch_id = []
#             for x in vals['branch_ids'] :
#                 branch_id.append(x[2])
#             branch_name = ''
#             for code in branch_id :
#                 for id in code :
#                     branch_code = self.env['wtc.branch'].search([('id','=',id)])                
#                     branch_name += ('- '+str(branch_code.name)+'<br/>')
#                     
#             msg = _("Update Branches : <br/> %s") % \
#                     (str(branch_name))
#             self.message_post(body=msg)             
#         return super(wtc_area,self).write(vals)        