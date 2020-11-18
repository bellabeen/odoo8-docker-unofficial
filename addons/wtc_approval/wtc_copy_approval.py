from openerp import models, fields, api
from openerp.osv import osv

class wtc_copy_approval(models.TransientModel):
    _name = "wtc.copy.approval"
    _description = "Copy Approval"
    _rec_name = "approval_type"
    
    def _get_form(self):
        form_ids = self.env['wtc.approval.config'].search([], order='name')
        selection = [('all','All')]
        for form_id in form_ids :
            selection.append((str(form_id.id),form_id.name))
        return selection
    
    approval_type = fields.Selection([('all','All'),('matrix_biaya','Approval Matrix Biaya'),('matrix_discount','Approval Matrix Discount')], string='Approval Type')
    division = fields.Selection([('all','All'),('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum'),('Finance','Finance')], string='Division')
    form_id = fields.Selection(_get_form, string='Form')
    branch_from_id = fields.Many2one('wtc.branch', string='Branch From')
    branch_to_id = fields.Many2one('wtc.branch', string='Branch To')
    
    _defaults = {
        'approval_type': 'all',
        'form_id': 'all',
        'division': 'all'
        }
    
    @api.multi
    def create_approval_matrixbiaya(self, biaya_header_ids, id_branch_from, id_branch_to):
        if biaya_header_ids :
            obj_biaya_header = self.env['wtc.approval.matrixbiaya.header']
            obj_biaya = self.env['wtc.approval.matrixbiaya']
            for biaya_header_id in biaya_header_ids :
                obj_biaya_header.search([('branch_id','=',id_branch_to),('form_id','=',biaya_header_id.form_id.id),('division','=',biaya_header_id.division)]).unlink()
                new_biaya_id = biaya_header_id.copy({'branch_id':id_branch_to, 'approval_line':[]})
                biaya_id = obj_biaya.search([('header_id','=',biaya_header_id.id)])
                biaya_id.copy({'header_id': new_biaya_id.id, 'branch_id':id_branch_to})
        else :
            raise osv.except_osv("Perhatian", "Tidak ditemukan Approval Matrix Biaya '%s' untuk Form dan Division yg dipilih !" %self.env['wtc.branch'].browse(id_branch_from).name)
    
    @api.multi
    def create_approval_matrixdiscount(self, disc_header_ids, id_branch_from, id_branch_to):
        if disc_header_ids :
            obj_disc_header = self.env['wtc.approval.matrixdiscount.header']
            obj_disc = self.env['wtc.approval.matrixdiscount']
            for disc_header_id in disc_header_ids :
                obj_disc_header.search([('branch_id','=',id_branch_to),('division','=',disc_header_id.division),('form_id','=',disc_header_id.form_id.id),('product_template_id','=',disc_header_id.product_template_id.id)]).unlink()
                new_disc_id = disc_header_id.copy({'branch_id':self.branch_to_id.id, 'wtc_approval_md_ids':[]})
                disc_id = obj_disc.search([('wtc_approval_md_id','=',disc_header_id.id)])
                disc_id.copy({'wtc_approval_md_id': new_disc_id.id, 'branch_id':id_branch_to})
        else :
            raise osv.except_osv("Perhatian", "Tidak ditemukan Approval Matrix Discount '%s' untuk Form dan Division yg dipilih !" %self.env['wtc.branch'].browse(id_branch_from).name)
    
    @api.multi
    def action_copy(self):
        if self.branch_from_id == self.branch_to_id :
            raise osv.except_osv("Perhatian", "Branch From dan Branch To tidak boleh sama !")
        
        search_form_id = ('form_id','!=',False)
        if self.form_id != 'all' :
            search_form_id = ('form_id','=',int(self.form_id))
        search_division = ('division','!=',False)
        if self.division != 'all' :
            search_division = ('division','=',self.division)
        
        if self.approval_type == 'matrix_biaya' or self.approval_type == 'all' :
            obj_biaya_header = self.env['wtc.approval.matrixbiaya.header']
            biaya_header_ids = obj_biaya_header.search([('branch_id','=',self.branch_from_id.id),search_form_id,search_division])
            self.create_approval_matrixbiaya(biaya_header_ids, self.branch_from_id.id, self.branch_to_id.id)
        if self.approval_type == 'matrix_discount' or self.approval_type == 'all' :
            obj_disc_header = self.env['wtc.approval.matrixdiscount.header']
            disc_header_ids = obj_disc_header.search([('branch_id','=',self.branch_from_id.id),search_form_id,search_division])
            self.create_approval_matrixdiscount(disc_header_ids, self.branch_from_id.id, self.branch_to_id.id)
            