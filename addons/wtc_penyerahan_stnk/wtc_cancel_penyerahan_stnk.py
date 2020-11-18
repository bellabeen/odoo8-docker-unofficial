from openerp import models, fields, api
from datetime import datetime
from openerp.osv import osv
from openerp import workflow

class wtc_cancel_penyerahan_stnk(models.Model):
    _name = "wtc.cancel.penyerahan.stnk"
    _description = "Penyerahan STNK Cancel"
    
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
    penyerahan_stnk_id = fields.Many2one('wtc.penyerahan.stnk', 'Penyerahan STNK')
    division = fields.Selection([('Unit','Unit')], 'Division')
    date = fields.Date('Date',default=_get_default_date)
    confirm_uid = fields.Many2one('res.users', string="Confirmed by")
    confirm_date = fields.Datetime('Confirmed on')
    approval_ids = fields.One2many('wtc.approval.line', 'transaction_id', string="Approval", domain=[('form_id','=','wtc.cancel.penyerahan.stnk')])
    approval_state = fields.Selection([
        ('b','Belum Request'),
        ('rf','Request For Approval'),
        ('a','Approved'),
        ('r','Rejected')
        ], 'Approval State', readonly=True, default='b')
    reason = fields.Text('Reason')
    lokasi_stnk_id = fields.Many2one('wtc.lokasi.stnk', 'Location STNK')
    
    _sql_constraints = [
        ('penyerahan_stnk_id', 'unique(penyerahan_stnk_id)', 'Transaksi ini sudah pernah diinput sebelumnya !')
        ]
    
    @api.model
    def create(self, values, context=None):
        penyerahan_stnk_id = self.env['wtc.penyerahan.stnk'].search([('id','=',values['penyerahan_stnk_id'])])
        values['name'] = "X" + penyerahan_stnk_id.name
        values['date'] = self._get_default_date_model()
        res = super(wtc_cancel_penyerahan_stnk, self).create(values)
        return res

    
    def unlink(self, cr, uid, ids, context=None):
        penyerahan_stnk_id = self.browse(cr, uid, ids, context=context)
        if penyerahan_stnk_id.state != 'draft':
            raise osv.except_osv(('Invalid action !'), ('Tidak bisa dihapus jika state bukan Draft !'))
        return super(wtc_cancel_penyerahan_stnk, self).unlink(cr, uid, ids, context=context)

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
        if self.penyerahan_stnk_id.id :
            if self.penyerahan_stnk_id.state != 'posted' :
                raise osv.except_osv(('Perhatian !'), ("Tidak bisa cancel, status Penyerahan STNK Posted !"))
            elif self.penyerahan_stnk_id.state == 'cancel' :
                raise osv.except_osv(('Perhatian !'), ("Penyerahan STNK sudah dibatalkan!"))
         

    @api.onchange('branch_id')
    def onchange_location_id(self):
        if self.branch_id :
            domain={}
            obj_lokasi = self.env['wtc.lokasi.stnk'].search([('branch_id','=',self.branch_id.id)])
            lokasi_ids=[lokasi.id for lokasi in obj_lokasi]
            domain['lokasi_stnk_id']=[('id','in',lokasi_ids)]
            return {'domain':domain}


    @api.multi
    def confirm(self):
        if self.state == 'approved' :
            self.validity_check()
            self.write({'state':'confirmed', 'date':self._get_default_date(), 'confirm_uid':self._uid, 'confirm_date':datetime.now()})
            for stnk in self.penyerahan_stnk_id.penyerahan_line: 
                stnk.name.write({'penyerahan_stnk_id': False,
                            'penyerahan_notice_id': False,
                            'penyerahan_polisi_id': False,
                            'tgl_penyerahan_stnk': False,
                            'tgl_penyerahan_plat': False,
                            'tgl_penyerahan_notice': False,
                            'lokasi_stnk_id': self.lokasi_stnk_id.id
                            })
   
            self.penyerahan_stnk_id.write({'state':'cancel','cancel_uid':self._uid, 'cancel_date':datetime.now()})
        return True