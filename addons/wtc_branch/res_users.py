# -*- coding: utf-8 -*-
from openerp import models, fields
from lxml import etree


class res_users(models.Model):
    _inherit = 'res.users'

    branch_ids = fields.Many2many(string='Branches', related='area_id.branch_ids')
    area_id = fields.Many2one('wtc.area','Area',context={'user_preference':True},help='Area for this user.')
    dealer_id = fields.Many2one('res.partner',string='Dealer',domain="[('dealer','!=',False)]",context={'user_preference':True})
    branch_ids_show = fields.Many2many(related='area_id.branch_ids',string='Branches')
    area_id_show = fields.Many2one(related='area_id',string='Area',context={'user_preference':True},help='Area for this user.')
    dealer_id_show = fields.Many2one(related='dealer_id',string='Dealer',domain="[('dealer','!=',False)]",context={'user_preference':True})
    
    def __init__(self, pool, cr):
        """ Override of __init__ to add access rights on
        store fields. Access rights are disabled by
        default, but allowed on some specific fields defined in
        self.SELF_{READ/WRITE}ABLE_FIELDS.
        """
        init_res = super(res_users, self).__init__(pool, cr)
        # duplicate list to avoid modifying the original reference
        self.SELF_WRITEABLE_FIELDS = list(self.SELF_WRITEABLE_FIELDS)
        self.SELF_WRITEABLE_FIELDS.append('area_id')
        self.SELF_WRITEABLE_FIELDS.append('branch_ids')
        self.SELF_WRITEABLE_FIELDS.append('dealer_id')
        # duplicate list to avoid modifying the original reference
        self.SELF_READABLE_FIELDS = list(self.SELF_READABLE_FIELDS)
        self.SELF_READABLE_FIELDS.append('area_id')
        self.SELF_READABLE_FIELDS.append('branch_ids')
        self.SELF_READABLE_FIELDS.append('dealer_id')
        return init_res

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(res_users, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        user_id = self.pool.get('res.users').browse(cr,uid,uid)
        section_obj = self.pool.get('crm.case.section').search(cr,uid,['|',
                                                                       ('user_id','=',user_id.id),
                                                                       ('member_ids','in',user_id.id)
                                                                       ])
        sec_ids=[]
        if section_obj :
            section_id = self.pool.get('crm.case.section').browse(cr,uid,section_obj)
            sec_ids=[b.id for b in section_id]  
              
        doc = etree.XML(res['arch'])
        nodes_branch = doc.xpath("//field[@name='default_section_id']")
        for node in nodes_branch:
            node.set('domain', '[("id", "in", '+ str(sec_ids)+')]')
        res['arch'] = etree.tostring(doc)
        return res
    
    def create(self,cr,uid,vals,context=None):
        user_id = super(res_users, self).create(cr, uid, vals, context=context)
        user = self.browse(cr, uid, user_id, context=context)
        if not user.partner_id.email :
            user.partner_id.write({'email': user.login,'notify_email':'none'})
        return user_id            
        