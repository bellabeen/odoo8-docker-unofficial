from openerp import models, fields, api
from datetime import datetime
from openerp.osv import osv
from openerp import workflow

class wtc_cancel_penyerahan_bpkb(models.Model):
    _name = "wtc.cancel.penyerahan.bpkb"
    _description = "Penyerahan BPKB Cancel"
    
    @api.multi
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date()
    
    @api.model
    def _get_default_date_model(self):
        return self.env['wtc.branch'].get_default_date_model()
    
    name = fields.Char('Name')
    state = fields.Selection([
        ('draft','Draft'),
        ('waiting_for_approval','Waiting For Approval'),
        ('approved','Approved'),
        ('confirmed','Confirmed'),
        ], 'State', default='draft')
    branch_id = fields.Many2one('wtc.branch', 'Branch')
    penyerahan_bpkb_id = fields.Many2one('wtc.penyerahan.bpkb', 'Penyerahan BPKB')
    division = fields.Selection([('Unit','Unit')], 'Division')
    date = fields.Date('Date',default=_get_default_date)
    confirm_uid = fields.Many2one('res.users', string="Confirmed by")
    confirm_date = fields.Datetime('Confirmed on')
    approval_ids = fields.One2many('wtc.approval.line', 'transaction_id', string="Approval", domain=[('form_id','=','wtc.cancel.penyerahan.bpkb')])
    approval_state = fields.Selection([
        ('b','Belum Request'),
        ('rf','Request For Approval'),
        ('a','Approved'),
        ('r','Rejected')
        ], 'Approval State', readonly=True, default='b')
    reason = fields.Text('Reason')
    
    _sql_constraints = [
        ('penyerahan_bpkb_id', 'unique(penyerahan_bpkb_id)', 'Transaksi ini sudah pernah diinput sebelumnya !')
        ]
    
    @api.model
    def create(self, values, context=None):
        penyerahan_bpkb_id = self.env['wtc.penyerahan.bpkb'].search([('id','=',values['penyerahan_bpkb_id'])])
        values['name'] = "X" + penyerahan_bpkb_id.name
        values['date'] = self._get_default_date_model()
        res = super(wtc_cancel_penyerahan_bpkb, self).create(values)
        return res

    
    def unlink(self, cr, uid, ids, context=None):
        penyerahan_bpkb_id = self.browse(cr, uid, ids, context=context)
        if penyerahan_bpkb_id.state != 'draft':
            raise osv.except_osv(('Invalid action !'), ('Tidak bisa dihapus jika state bukan Draft !'))
        return super(wtc_cancel_penyerahan_bpkb, self).unlink(cr, uid, ids, context=context)

    @api.multi
    def request_approval(self):
        self.validity_check()
        obj_matrix = self.env['wtc.approval.matrixbiaya']
        obj_matrix.request_by_value(self, 5)
        self.write({'state':'waiting_for_approval', 'approval_state':'rf'})
    
    @api.multi
    def approve(self):
        approval_sts = self.env['wtc.approval.matrixbiaya'].approve(self)
        if approval_sts == 1 :
            self.write({'approval_state':'a','state':'approved'})
        elif approval_sts == 0 :
            raise osv.except_osv(('Perhatian !'), ("User tidak termasuk group Approval !"))
    
    @api.multi
    def validity_check(self):
        if self.penyerahan_bpkb_id.id :
            if self.penyerahan_bpkb_id.state != 'posted' :
                raise osv.except_osv(('Perhatian !'), ("Tidak bisa cancel, status Penyerahan BPKB Posted !"))
            elif self.penyerahan_bpkb_id.state == 'cancel' :
                raise osv.except_osv(('Perhatian !'), ("Penyerahan BPKB sudah dibatalkan!"))
            
        
    @api.multi
    def confirm(self):
        if self.state == 'approved' :
            self.validity_check()
            self.write({'state':'confirmed', 'date':self._get_default_date(), 'confirm_uid':self._uid, 'confirm_date':datetime.now()})
            for bpkb in self.penyerahan_bpkb_id.penyerahan_line:
                bpkb.name.write({'penyerahan_bpkb_id': False,
                                 'tgl_penyerahan_bpkb': False,
                                 'lokasi_bpkb_id': bpkb.lokasi_bpkb_id.id
                                 })
            self.penyerahan_bpkb_id.write({'state':'cancel', 'cancel_uid':self._uid, 'cancel_date':datetime.now()})
        return True