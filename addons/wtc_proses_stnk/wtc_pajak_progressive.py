from datetime import datetime
from openerp import models, fields, api
from openerp import workflow
from openerp.osv import osv
from openerp.exceptions import except_orm, Warning, RedirectWarning



class wtc_pajak_progressive(models.Model):
  _name = "wtc.pajak.progressive"
  description = "Pajak Progressive"

  STATE_SELECTION = [
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled','Cancelled')
    ]

  @api.multi
  def _get_default_date(self):
    return datetime.now()

  @api.onchange('branch_id')
  def birojasa_change(self):
    domain = {}
    birojasa = []
    if self.branch_id :
      birojasa_srch = self.env['wtc.harga.birojasa'].search([
        ('branch_id','=', self.branch_id.id)])
      for val in birojasa_srch:
        birojasa.append(val.birojasa_id.id)
      self.biro_jasa_id = False
    domain['biro_jasa_id'] = [('id','in',birojasa)]
    return {'domain': domain}
    # else:
    #   self.biro_jasa_id = False
    #   return{'domain': {'biro_jasa_id':[('id','=',False)]}}

  @api.one
  def confirm_invoice(self):
    for line in self.pajak_progressive_line_ids:
      line.create_invoice_line(self.name,self.branch_id,self.division,self.tanggal)
     
    self.write({'state':'confirmed','confirm_uid':self._uid,'confirm_date':self._get_default_date()})

  name = fields.Char('No Reference',size=20, readonly=True) 
  state = fields.Selection(STATE_SELECTION, 'State', readonly=True, default='draft')        
  branch_id = fields.Many2one('wtc.branch', string='Branch', required=True, domain=[('pajak_progressive','=',True)])
  biro_jasa_id = fields.Many2one('res.partner','Biro Jasa')
  division = fields.Selection([('Unit','Unit')], 'Division', change_default=True, select=True, required=True, default='Unit')
  tanggal = fields.Date('Tanggal', default = _get_default_date, readonly=True)
  pajak_progressive_line_ids = fields.One2many('wtc.pajak.progressive.line', 'pajak_progressive_id', string='Tabel Pajak Progressive')
  confirm_uid = fields.Many2one('res.users', string="Confirmed by")
  confirm_date = fields.Datetime('Confirmed on')  
  cancel_uid = fields.Many2one('res.users', string="Cancelled by")
  cancel_date = fields.Datetime('Cancelled on')
  
  # @api.multi
  # def wkf_action_cancel(self):
  #   lot_pool = self.env['stock.production.lot']
  #   for x in self.pajak_progressive_line_ids:
  #     lot_search = lot_pool.search([
  #       ('id','=',x.lot_id.id)
  #       ])
  #     if not lot_search:
  #       raise osv.except_osv(("Perhatian !"),("No Engine Tidak Di Temukan"))
  #     else:
  #       lot_search.write({'inv_pajak_progressive_id': False})#,'proses_biro_jasa_id':False,'tgl_proses_birojasa':False})
  #   self.write({'state':'cancelled','cancel_uid':self._uid,'cancel_date':datetime.now()})
  #   return True

  @api.model
  def create(self,vals):
    if not vals['pajak_progressive_line_ids']:
      raise Warning(('Perhatian !'), ('Tidak ada proses pajak progressive'))    
    lot_pajak =[]
    for x in self.pajak_progressive_line_ids:
      lot_pajak.append(x.pop(2))
    lot_pool = self.env['stock.production.lot']
    pajak_pool = self.env['wtc.pajak.progressive.line']
    vals['name'] = self.env['ir.sequence'].get_per_branch(vals['branch_id'],'PPR')
    
    vals['tanggal'] = self._get_default_date()
 
    pajak_id = super(wtc_pajak_progressive,self).create(vals)

    if pajak_id:
      for x in lot_pajak:
        lot_search = lot_pool.search([
          ('id','=',x['lot_id'])
          ])
        lot_browse = lot_pool.browse(lot_search)
        lot_browse.write({'pajak_progressive_id':pajak_id,})
        pajak_pool.create({
          'lot_id':lot_browse.id,
          'pajak_progressive_id': pajak_id,
          'customer_stnk': lot_browse.customer_stnk.id,
          'pajak_progressive': x['pajak_progressive'],
          })
    return pajak_id

  @api.multi
  def write(self,vals):
    res = super(wtc_pajak_progressive,self).write(vals)
    if not self.pajak_progressive_line_ids:
      raise Warning(('Perhatian !'), ('Tidak ada proses pajak progressive')) 
    return res

  @api.multi
  def unlink(self):
    if self.state != 'draft':
      raise Warning(('Invalid action !'),('Tidak bisa dihapus jika state bukan Draft !'))
    return super(wtc_pajak_progressive,self).unlink()





class wtc_pajak_progressive_line(models.Model):
  _name = "wtc.pajak.progressive.line"

  @api.multi
  def _check_amount(self):
    for ppl in self:
      if ppl.pajak_progressive <= 0:
        return False
    return True

  name = fields.Char('Name')
  pajak_progressive_id = fields.Many2one('wtc.pajak.progressive', 'Proses Pajak Progressive')
  lot_id = fields.Many2one('stock.production.lot','No Engine', required=True, domain="[('inv_pajak_progressive_id','=',False),('tgl_proses_stnk','!=',False),('proses_biro_jasa_id','=',False),('state_stnk','=','proses_stnk'),('branch_id','=',parent.branch_id),('biro_jasa_id','=',parent.biro_jasa_id)]",change_default=True)
  # proses_biro_jasa_id = fields.Many2one('wtc.proses.birojasa','Proses Biro Jasa')
  customer_stnk_id = fields.Many2one(related='lot_id.customer_stnk',relation='res.partner',readonly=True,string='Customer STNK')
  pajak_progressive = fields.Float('Pajak Progresif')
  invoice_id = fields.Many2one('account.invoice', 'Invoice')
  status = fields.Selection([('draft','Draft'),('confirmed','Confirmed'),('cancelled','Cancelled')],'Status',default='draft')
  cancel_uid = fields.Many2one('res.users', string="Cancelled by")
  cancel_date = fields.Datetime('Cancelled on')

  _sql_constraints = [
    ('unique_pajak_progressive_id', 'unique(pajak_progressive_id,lot_id)', 'Detail Engine tidak boleh sama, mohon dicek kembali !'),
  ]
  _constraints = [
    (_check_amount, 'Nilai amount tidak boleh negatif (-) atau 0.00 !', ['pajak_progressive']),
  ]    

  @api.multi
  def name_get(self, context=None):
    if context is None:
        context = {}
    res = []
    for record in self :
        name = record.name
        if record.lot_id:
            name = "[%s] %s" % (record.lot_id.name, name)
        res.append((record.id, name))
    return res

  @api.model
  def name_search(self, name, args=None, operator='ilike', limit=100):
    args = args or []
    if name:
        # Be sure name_search is symetric to name_get
        args = ['|',('name', operator, name),('lot_id.name', operator, name)] + args
    categories = self.search(args, limit=limit)
    return categories.name_get()

  @api.onchange('lot_id','branch_id','biro_jasa_id')
  def onchange_engine(self):
    for line in self.pajak_progressive_id:
      branch = line.branch_id.id
      birojasa = line.biro_jasa_id
      if not branch or not birojasa:
        raise Warning(('No Branch Definned !'), ('Sebelum menambahkan pajak progressive, input Branch dan Birojasa terlebih dahulu !'))  
  
  @api.multi
  def create_invoice_line(self,name,branch_id,division,tanggal):
    config = self.env['wtc.branch.config'].search([
      ('branch_id','=', branch_id.id)
    ])
    obj_inv = self.env['account.invoice']
    progressive_debit_account = config.tagihan_birojasa_progressive_journal_id.default_debit_account_id.id 
    progressive_credit_account = config.tagihan_birojasa_progressive_journal_id.default_credit_account_id.id                
    journal_progressive = config.tagihan_birojasa_progressive_journal_id.id
      
    journal_PP = config.tagihan_birojasa_progressive_journal_id
    obj_model_id = self.env['ir.model'].search([ ('model','=',self.__class__.__name__) ]) 
    if  not journal_PP:
      raise Warning(('Warning !'), ('Journal Pajak Progressive Belum di Buat, Setting Terlebih Dahulu !')) 

    for line in self.lot_id:
      if not line.tgl_proses_stnk or not line.proses_stnk_id:
        raise Warning(('Perhatian !'), ('Engine %s, Belum melakukan proses STNK, coba periksa kembali !')%(line.name)) 

      if line.inv_pajak_progressive_id:
        raise Warning(('Perhatian !'), ('Engine %s sudah memiliki Invoice Pajak Progressive, coba periksa kembali !')%(line.name))

      if line.proses_biro_jasa_id:
        raise Warning(('Perhatian !'), ('Engine %s sudah melakukan proses biro jasa, coba periksa kembali !')%(line.name))  
      
      if self.pajak_progressive > 0.00:
        line_name = self.env['ir.sequence'].get_per_branch(branch_id.id,'PPD')
        customer_name = str(line.customer_id.name)
        engine_no = str(line.name)
        string = "Pajak Progressive a/n \'%s\', No Engine \'%s\' !" %(customer_name,engine_no)
        inv_pajak_progressive_id = obj_inv.sudo().create({
          'name': string,
          'qq_id': line.customer_stnk.id,
          'origin': line_name,
          'branch_id': branch_id.id,
          'division': division,
          'partner_id': line.customer_id.id,
          'date_invoice': tanggal,
          'reference_type': 'none',
          'transaction_id': self.id,
          'model_id': obj_model_id.id,
                  
          'account_id': progressive_debit_account,
          'type': 'out_invoice',
          'journal_id': journal_progressive,
          'invoice_line':[[0,False,{
            'account_id':progressive_credit_account,
            'partner_id':line.customer_id.id,
            'name': string,
            'quantity': 1,
            'origin': line_name,
            'price_unit':self.pajak_progressive  or 0.00,
          }]]
          })
        inv_pajak_progressive_id.signal_workflow('invoice_open') 
        pajak_progressive_id = inv_pajak_progressive_id
        line.write({'inv_pajak_progressive_id':pajak_progressive_id.id})
    
        self.write({'name':line_name,'invoice_id': pajak_progressive_id.id,'status':'confirmed'})


  

        