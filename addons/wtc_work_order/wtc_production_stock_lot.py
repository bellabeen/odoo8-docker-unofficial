from openerp import api, fields, models, SUPERUSER_ID
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning


class wtc_production_stock_lot(models.Model):
    _inherit = 'stock.production.lot'
    
    driver_id = fields.Many2one('res.partner','Driver')
     

    @api.multi
    def name_onchange(self,product_id,name):
        dom = {}
        product_ids = self.env['product.category'].get_child_ids('Unit')
        dom['product_id']=[('categ_id','in',product_ids)]
        if name :
            name = name.replace(' ', '').upper()
            return {'value' : {'name':name,'state':'workshop'},'domain':dom }
        
    @api.multi
    def chassis_onchange(self,chassis_no):
        if chassis_no :
            chassis_no = chassis_no.replace(' ', '').upper()
            return {'value' : {'chassis_no':chassis_no}}
        
    @api.multi
    def no_pol_onchange(self,no_polisi):
        if no_polisi :
            no_polisi = no_polisi.replace(' ', '').upper()
            return {'value' : {'no_polisi':no_polisi}}
    
    @api.multi
    def kode_buku_onchange(self,kode_buku):
        if kode_buku :
            kode_buku = kode_buku.replace(' ', '').upper()
            return {'value' : {'kode_buku':kode_buku}}
        
    @api.multi
    def nama_buku_onchange(self,nama_buku):
        if nama_buku :
            nama_buku = nama_buku.replace(' ', '').upper()
            return {'value' : {'nama_buku':nama_buku}}
    
    
    work_order_ids = fields.One2many('wtc.work.order','lot_id',string="Work Orders",readonly=True)

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            name = record.name
            if record.no_polisi:
                name = "%s - %s" % (record.no_polisi, name)
            res.append((record.id, name))
        return res

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        if name:
            args = ['|',('name', operator, name),('no_polisi', operator, name)] + args
        categories = self.search(args, limit=limit)
        return categories.name_get()
    
    
class wtc_res_partner_wo(models.Model):
    _inherit = 'res.partner'
    
    @api.multi
    def name_wo_onchange(self,name):
        if name :
            name = name.title()
            return {'value' : {'name':name} }


    @api.multi        
    def mobile_wo_onchange(self,mobile):
        if mobile :
            if len(mobile) < 6 :
                raise except_orm(_('Perhatian !'), _('Mobile Tidak boleh kurang dari 6 digit !.'))
            else :
                cek = mobile.isdigit()
            if not cek :
                raise except_orm(_('Perhatian !'), _("Mobile hanya boleh angka !"))
        return {'mobile' : {'mobile':mobile} }
         