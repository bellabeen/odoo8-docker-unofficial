from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning
from datetime import date, datetime, timedelta,time

class PengirimanBPKB(models.Model):
    _name = "teds.pengiriman.bpkb"

    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()

    name = fields.Char('No Refrence')
    branch_id = fields.Many2one('wtc.branch','Branch')
    source_location_id = fields.Many2one('wtc.lokasi.bpkb','Source Location')
    destination_branch_id = fields.Many2one('res.partner','Destination Branch',domain="[('branch','=',True)]")
    destination_location_id = fields.Many2one('wtc.lokasi.bpkb','Destination Location')
    date = fields.Date('Tanggal',default=_get_default_date)
    division = fields.Selection([('Unit','Unit')],default='Unit')
    state = fields.Selection([
        ('draft','Draft'),
        ('on_prosess','On Prosses'),
        ('processed','Processed'),
        ('done','Done')],default='draft')
    detail_ids = fields.One2many('teds.pengiriman.bpkb.line','pengiriman_id')
    pengiriman_by = fields.Selection([('SAP','SAP'),('Cabang','Cabang')],string="Pengiriman By")
    no_resi = fields.Char('No Resi')
    nama_kurir = fields.Char('Nama Kurir')

    # Leadtime
    proses_uid = fields.Many2one('res.users','Proses by')
    proses_date = fields.Datetime('Proses on')
    sending_uid = fields.Many2one('res.users','Sending by')
    sending_by = fields.Datetime('Sending on')
    receipt_uid = fields.Many2one('res.users','Receipt by')
    receipt_date = fields.Datetime('Receipt on')

    mutasi_id = fields.Many2one('wtc.mutasi.bpkb','No Mutasi')

    @api.model
    def create(self,vals):
        vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'], 'RBP')
        return super(PengirimanBPKB,self).create(vals)

    @api.onchange('branch_id')
    def onchange_source_location(self):
        self.source_location_id = False

    @api.onchange('pengiriman_by')
    def onchange_pengiriman_by(self):
        self.nama_kurir = False
        self.no_resi = False
    
    @api.onchange('source_location_id')
    def onchange_detail(self):
        self.detail_ids = False
    
    @api.onchange('destination_location_id','source_location_id')
    def onchange_destination_location(self):
        warning = ''
        if self.destination_location_id and self.source_location_id:
            if self.destination_location_id == self.source_location_id:
                warning = {'title':'Perhatian !','message':'Destination dan Source Location tidak boleh sama !'}
                self.destination_location_id = False
        return {'warning':warning}

    @api.multi
    def action_on_proses(self):
        if self.state != 'draft':
            raise Warning('Silahkan refresh !')
        self.write({'state':'on_prosess'})

    @api.multi
    def action_proses(self):
        if self.state != 'on_prosess':
            raise Warning('Silahkan refresh !')

        form_id = self.env.ref('teds_pengajuan_pengiriman_bpkb.view_teds_pengiriman_bpkb_proses_form').id
        return {
            'name': ('Proses'),
            'res_model': 'teds.pengiriman.bpkb',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'views': [(form_id, 'form')],
            'view_mode': 'form',
            'target': 'new',
            'view_type': 'form',
            'res_id': self.id,
        }

    @api.multi
    def action_proses_bpkb_form(self):
        self.write({
            'state':'processed',
            'proses_uid':self._uid,
            'proses_date':self._get_default_date()
        })
    
    @api.multi
    def action_received(self):
        if self.state != 'processed':
            raise Warning('Silahkan refresh !')
        mutasi_line = []
        for line in self.detail_ids:
            if line.lot_id.lokasi_bpkb_id != self.source_location_id:
                raise Warning('No mesin %s sudah melakukan perubahan lokasi ! \n Lokasi BPKB sekarang %s '%(line.lot_id.name,line.lot_id.lokasi_bpkb_id.name))
            mutasi_line.append([0,False,{'name':line.lot_id.id}])

        vals_mutasi = {
            'branch_id':self.branch_id.id,
            'division':self.division,
            'destination_branch_id':self.branch_id.id,
            'source_location_id':self.source_location_id.id,
            'destination_location_id':self.destination_location_id.id,
            'mutasi_line':mutasi_line
        }
        mutasi_id = self.env['wtc.mutasi.bpkb'].create(vals_mutasi)
        mutasi_id.post_mutasi()
        self.write({
            'state':'done',
            'receipt_uid':self._uid,
            'receipt_date':self._get_default_date(),
            'mutasi_id':mutasi_id.id    
        })

    @api.multi
    def action_penerimaan_bpkb_print(self):
        datas = self.read()[0]
        return self.env['report'].get_action(self,'teds_pengajuan_pengiriman_bpkb.teds_penerimaan_bpkb_print', data=datas)


class PengirimanBPKBLine(models.Model):
    _name = "teds.pengiriman.bpkb.line"

    pengiriman_id = fields.Many2one('teds.pengiriman.bpkb','Pengiriman BPKB',ondelete='cascade')
    lot_id = fields.Many2one('stock.production.lot','No Engine',domain="[('lokasi_bpkb_id','=',parent.source_location_id)]")
    customer_bpkb_id = fields.Many2one('res.partner','Customer BPKB',related='lot_id.customer_stnk')
    no_bpkb = fields.Char('No BPKB',related='lot_id.no_bpkb')
