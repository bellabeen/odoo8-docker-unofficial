from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning
from datetime import date, datetime, timedelta,time

class PartHotlineCancel(models.Model):
    _name = "teds.part.hotline.cancel"

    def _get_default_branch(self):
        branch_ids = False
        branch_ids = self.env.user.branch_ids
        if branch_ids and len(branch_ids) == 1 :
            return branch_ids[0].id
        return False
   
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()
    
    def _get_default_datetime(self):
        return self.env['wtc.branch'].get_default_datetime_model()
    name = fields.Char('Name')
    branch_id = fields.Many2one('wtc.branch','Branch',default=_get_default_branch)
    hotline_id = fields.Many2one('teds.part.hotline','No Part Hotline')
    approval_ids = fields.One2many('wtc.approval.line','transaction_id',string="Table Approval",domain=[('form_id','=',_name)])
    approval_state = fields.Selection([
        ('b','Belum Request'),
        ('rf','Request For Approval'),
        ('a','Approved'),
        ('r','Reject')],'Approval State', readonly=True,default='b')
    confirm_uid = fields.Many2one('res.users','Confirm by')
    confirm_date = fields.Datetime('Confirm on')
    division = fields.Selection([('Sparepart','Sparepart')],default='Sparepart')
    date = fields.Date('Date',default=_get_default_date)
    state = fields.Selection([
        ('draft','Draft'),
        ('waiting_for_approval','Waiting For Approval'),
        ('approved','Approved'),
        ('confirmed','Confirmed')],default='draft')
    reason = fields.Text('Reason')    

    @api.model
    def create(self,vals):
        hotline = self.env['teds.part.hotline'].search([('id','=',vals['hotline_id'])])
        vals['name'] = "X" + hotline.name
        return super(PartHotlineCancel,self).create(vals)

    @api.multi
    def unlink(self):
        for x in self :
            if x.state != 'draft' :
                raise Warning('Transaksi yang berstatus selain Draft tidak bisa dihapus.')
        return super(PartHotline, self).unlink()
        
    
    @api.multi
    def action_rfa(self):
        self._cek_hotline()
        vals = {'state':'approved','approval_state':'a'}
        total_value = 20000000
        obj_matrix = self.env['wtc.approval.matrixbiaya']
        obj_matrix.request_by_value(self,total_value)
        vals['state'] = 'waiting_for_approval'
        vals['approval_state'] = 'rf'
        self.write(vals)

    @api.multi
    def action_approved(self):
        self._cek_hotline()
        approval_sts = self.env['wtc.approval.matrixbiaya'].approve(self)
        if approval_sts == 1:
            self.write({'approval_state':'a','state':'approved'})
        elif approval_sts == 0:
            raise Warning('Perhatian !\n User tidak termasuk group approval')
        return True

    @api.multi
    def action_confirm(self):
        self._cek_hotline()
        self.hotline_id.write({
            'state':'cancel',
            'cancel_uid':self._uid,
            'cancel_date':self._get_default_datetime(),
        })
        self.write({
            'state':'confirmed',
            'confrim_date':self._get_default_datetime(),
            'confirm_uid':self._uid,    
        })


    def _cek_hotline(self):
        po_obj = self.env['purchase.order'].sudo().search([
            ('branch_id','=',self.branch_id.id),
            ('part_hotline_id','=',self.hotline_id.id)])
        for po in po_obj:
            if po.state != 'cancel':
                raise Warning('Part Hotline %s sudah melakukan Purchase Order %s, silahkan di batalkan terlebih dahulu !'%(self.hotline_id.name,po.name))
        wo_obj = self.env['wtc.work.order'].sudo().search([
            ('branch_id','=',self.branch_id.id),
            ('part_hotline_id','=',self.hotline_id.id)])
        for wo in wo_obj:
            if wo.state != 'cancel':
                raise Warning('Part Hotline %s sudah melakukan Work Order %s, silahkan di batalkan terlebih dahulu !'%(self.hotline_id.name,wo.name))
