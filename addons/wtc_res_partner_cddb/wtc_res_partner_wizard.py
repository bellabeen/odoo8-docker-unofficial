import time
from datetime import datetime
from openerp.osv import fields, osv
from lxml import etree
from openerp.osv.orm import setup_modifiers
  
class wtc_res_partner_wizard(osv.osv):
    _inherit = 'res.partner'       
    _columns = {
                'kartukeluarga_ids' : fields.one2many('wtc.kartu.keluarga','customer_id',string="Kartu Keluarga"),
                'cddb_line' : fields.one2many('wtc.cddb','customer_id','CDDB'),
                'mobile': fields.char('Mobile'),

    }     
    
    def create(self,cr,uid,vals,context=None):
        if context.get('form_name',False) == 'Finco':
            vals['finance_company'] = True
            vals['customer'] = True
        elif context.get('form_name',False) == 'Customers' :
            vals['direct_customer'] = True
            vals['customer'] = True
        elif context.get('form_name',False) == 'Branch' :
            vals['branch'] = True
        if vals.get('biro_jasa',False) :
            vals['supplier'] = True
            vals['customer'] = True
        res = super(wtc_res_partner_wizard,self).create(cr,uid,vals,context=context)
        return res
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(wtc_res_partner_wizard, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        if view_type == 'search' :
        
            branch_ids_user=self.pool.get('res.users').browse(cr,uid,uid).branch_ids
            branch_ids=[b.id for b in branch_ids_user]
            doc = etree.XML(res['arch'])
            nodes_branch = doc.xpath("//filter[@name='branch_ids']")
            for node in nodes_branch:
                node.set('domain', '[("branch_id", "in", '+ str(branch_ids)+'),("direct_customer","=",True)]')
            res['arch'] = etree.tostring(doc)           
        return res    
            