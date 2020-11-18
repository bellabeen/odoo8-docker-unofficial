# -*- coding: utf-8 -*-
from openerp.exceptions import ValidationError
from openerp import models, fields, api
class TedsStockIdeal(models.Model):
    _name = 'stock.ideal'
    _order = 'id desc'
    
    name = fields.Char('Name', required=True)
    branch_id = fields.Many2one('wtc.branch', string='Branch', required=True)
    # period = fields.Date('Period', required=True, copy=False)
    effective_start_date = fields.Date('Effective Start Date', copy=False)
    effective_end_date = fields.Date('Effective End Date', copy=False)
    stock_ideal_line = fields.One2many('stock.ideal.line', 'stock_ideal_id', required=True)
    
    # _sql_constraints = [
    #     ('unique_satu', 'unique(branch_id,effective_start_date )','Master Duplicate !')
    #     ]


    @api.multi
    @api.constrains('effective_start_date','effective_end_date')
    def _check_daterr(self):
        bbb =  self.search([('branch_id', '=', self.branch_id.id),
                            ('effective_start_date','<=',self.effective_start_date),
                            ('effective_end_date','>=', self.effective_end_date)])
        query_where = ""            
        for abc in bbb:
            if abc.effective_start_date:
                query_where += " AND effective_end_date >= '%s' " % (abc.effective_start_date)

            if abc.effective_end_date:
                query_where += " AND effective_start_date <= '%s' " % (abc.effective_end_date)

            if abc.branch_id:
                query_where += " AND branch_id = '%s' " % (abc.branch_id.id)

            query = """
                        SELECT id
                        FROM stock_ideal
                        WHERE 1=1 %s
                        """ % (query_where)
            self._cr.execute (query)
            result = self._cr.fetchall()
 
            if result[0][0] != self.id:
                raise ValidationError('Periode stock sudah ada !')

   

    @api.one
    @api.constrains('effective_start_date','effective_end_date')
    def _check_date(self):
        if self.effective_start_date > self.effective_end_date:
            raise ValidationError('Effective End Date tidak boleh kurang dari Effective Start Date!')
    
 
    @api.one
    #@api.constrains('effective_start_date','effective_end_date')
    def _check_overlap(self):
        find_overlap = []
        find_overlap = self.search([('branch_id', '=', self.branch_id.id),
            '|', '|','|', '&', ('effective_start_date','<=',self.effective_start_date),
            ('effective_end_date','>=', self.effective_end_date),
            '&', ('effective_start_date', '<=', self.effective_start_date),
            ('effective_end_date', '<=', self.effective_end_date),
            '&', ('effective_start_date', '>=', self.effective_start_date),
            ('effective_end_date', '>=', self.effective_end_date),
            '&', ('effective_start_date', '>=', self.effective_start_date),
            ('effective_end_date', '<=', self.effective_end_date)])
        if find_overlap:
            raise ValidationError('Periode stock ideal tidak boleh overlap!')

class TedsStockIdealLine(models.Model):
    _name = 'stock.ideal.line'

    stock_ideal_id = fields.Many2one('stock.ideal', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_category_id = fields.Many2one('product.category', string='Sub Category')
    category_id_show = fields.Many2one(related='product_category_id', string='Sub Category', readonly=True)
    simpart = fields.Boolean('Simpart')
    ideal_bln = fields.Float('Ideal Bulan', digits=(2,1), required=True)
    min_qty = fields.Integer('Min Qty', required=True)
    max_qty = fields.Integer('Max Qty', required=True)

    @api.one
    @api.constrains('ideal_bln','min_qty','max_qty')
    def _check_minus(self):
        if self.ideal_bln < 0 or self.min_qty < 0 or self.max_qty < 0:
            raise ValidationError('Qty harus lebih dari 0!')

    @api.onchange('product_id')
    def _change_product_category(self):
        if self.product_id:
            self.product_category_id = self.product_id.categ_id.id
            self.category_id_show = self.product_category_id

    @api.onchange('min_qty', 'max_qty')
    def _change_ideal_qty(self):
        if self.min_qty > self.max_qty:
            self.max_qty = self.min_qty

    # @api.model
    # def create(self, values):
        # values['product_category_id'] = self.product_id.categ_id.id
        # create_stock_ideal = super(TedsStockIdealLine, self).create(values)
        # return create_stock_ideal



            





