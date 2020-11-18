from openerp import models, fields, api
from datetime import timedelta,datetime
import json
import requests


class BranchConfig(models.Model):
    _inherit = "wtc.branch.config"

    config_dgi_id = fields.Many2one('teds.b2b.api.config','Config H1',domain=[('is_dgi','=',True)])
    config_dgi_h23_id = fields.Many2one('teds.b2b.api.config','Config H23',domain=[('is_dgi','=',True)])


class Branch(models.Model):
    _inherit = "wtc.branch"

    md_reference = fields.Char('MD Reference', help='Referensi untuk DGI dengan MD wilayah')
    is_allow_dgi_prsp = fields.Boolean('Is Allow PRSP ?',default=True)
    is_pos_dgi = fields.Boolean('Is Multi POS ?',help="Cabang yang memiliki POS dianggap sebagai Branch untuk DGI")

class B2bApiConfig(models.Model):
    _inherit = "teds.b2b.api.config"

    is_dgi = fields.Boolean('Is DGI ?')
    branch_id = fields.Many2one('wtc.branch','Branch')
    branch_ids = fields.One2many('wtc.branch.config','config_dgi_id','Branches')
    
    def create_log_error_dgi(self,name,url,request_type,error,origin):
        query = """
            SELECT id FROM teds_b2b_dgi_error_log
            WHERE name = '%s'
            AND url = '%s'
            AND request_type = '%s'
            AND error = '%s'
            AND origin = '%s'
            AND date + interval '7 hours' BETWEEN (now() - interval '1 hours') AND now()
            LIMIT 1
        """ %(name,url,request_type,error,origin)
        self._cr.execute (query)
        res =  self._cr.fetchone()
        if not res:
            log_obj =  self.env['teds.b2b.dgi.error.log']
            create = log_obj.suspend_security().create({
                'name':name,
                'url':url,
                'request_type':request_type,
                'error':error,
                'origin':origin
            })
            url = "https://hooks.slack.com/services/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"
            error_slack = "%s %s" %(name,error)
            self.send_nonitication_slack(url,error_slack)

    # Product ID
    def _get_product_unit(self,tipe,warna):
        query_product = """
            SELECT pp.id as prod_id
            FROM product_product pp
            INNER JOIN product_template pt ON pt.id = pp.product_tmpl_id 
            LEFT JOIN product_attribute_value_product_product_rel rel ON rel.prod_id = pp.id
            LEFT JOIN product_attribute_value pav ON pav.id = rel.att_id 
            WHERE name_template = '%s' AND pav.code='%s'
        """ %(tipe,warna)
        self._cr.execute(query_product)
        res = self._cr.fetchone()
        if not res:
            return False
        return res[0]
    
    def _get_product_unit_h23(self,tipe):
        product = self.env['product.product'].suspend_security().search(['|',('kode_tipe_unit','=',tipe),('name','=',tipe)],limit=1).id
        return product
    
    # Salesman ID
    def _get_employee(self,branch_id,idSalesPeople):
        tgl_skrng = datetime.now().date().strftime("%Y-%m-%d") 
        employee = self.env['hr.employee'].suspend_security().search([
            ('branch_id','=',branch_id),
            ('code_md','=',idSalesPeople),
            '|',('tgl_keluar','=',False),
            ('tgl_keluar','>',tgl_skrng)],limit=1)
        return employee

    def _get_employee_multi(self,branch_ids,idSalesPeople):
        tgl_skrng = datetime.now().date().strftime("%Y-%m-%d") 
        employee = self.env['hr.employee'].suspend_security().search([
            ('branch_id','in',branch_ids),
            ('code_md','=',idSalesPeople),
            '|',('tgl_keluar','=',False),
            ('tgl_keluar','>',tgl_skrng)],limit=1)
        return employee