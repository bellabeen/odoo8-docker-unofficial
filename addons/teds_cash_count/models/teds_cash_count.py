from openerp import models, fields, api
from datetime import date, datetime, timedelta,time
from dateutil.relativedelta import relativedelta
from openerp.exceptions import Warning

class CashCount(models.Model):
    _name = "teds.cash.count"
    _order = "date DESC"
    @api.model
    def _get_default_date(self):
        return self.env['wtc.branch'].get_default_date_model()
    
    @api.model
    def _get_default_datetime(self):
        return datetime.now()

    def _get_default_branch(self):
        branch_ids = False
        branch_ids = self.env.user.branch_ids
        if branch_ids and len(branch_ids) == 1 :
            return branch_ids[0].id
        return False

    name = fields.Char('Name')
    branch_id = fields.Many2one('wtc.branch','Branch',default=_get_default_branch)
    kasir = fields.Char('Kasir')
    admin_pos = fields.Char('Admin Pos')
    adh = fields.Char('ADH')
    soh = fields.Char('SOH')
    date = fields.Date('Tanggal',default=_get_default_date)
    cash_detail_ids = fields.One2many('teds.cash.count.detail','cash_count_id',string='Cash',domain=[('type','=','cash')], context={'default_type':'cash'})
    petty_cash_detail_ids = fields.One2many('teds.cash.count.detail','cash_count_id',string='Petty Cash',domain=[('type','=','petty_cash')], context={'default_type':'petty_cash'})
    reimburse_petty_cash_detail_ids = fields.One2many('teds.cash.count.detail','cash_count_id',string='Reimburse Petty Cash',domain=[('type','=','reimburse_petty_cash')], context={'default_type':'reimburse_petty_cash'})
    peneriman_lain_ids = fields.One2many('teds.cash.count.other','cash_count_id','Penerimaan Lain')
    generate_date = fields.Datetime('Generate on')
    post_date = fields.Datetime('Posted on')
    post_uid = fields.Many2one('res.users','Posted by')
    tipe = fields.Selection([('Showroom','Showroom'),('POS','POS')],default='Showroom')
    state = fields.Selection([
        ('draft','Draft'),
        ('rfa','Waiting For Approval'),
        ('approved','Approved'),
        ('posted','Posted'),
        ('cancelled','Cancelled')],default="draft")
    plafon_petty_cash_sr = fields.Float('Plafon Petty Cash SR')
    plafon_petty_cash_ws = fields.Float('Plafon Petty Cash WS')
    plafon_petty_cash_atl_btl = fields.Float('Plafon Petty Cash ATL/BTL')
    fisik_petty_cash_sr = fields.Float('Fisik Petty Cash SR')
    fisik_petty_cash_ws = fields.Float('Fisik Petty Cash WS')
    fisik_petty_cash_atl_btl = fields.Float('Fisik Petty Cash ATL/BTL')
    saldo_pc_sr = fields.Float('Saldo PC SR di Bank Out')
    saldo_pc_ws = fields.Float('Saldo PC WS di Bank Out')
    saldo_pc_atl_btl = fields.Float('Saldo PC ATL/BTL di Bank Out')
    note_ba = fields.Text('Note Berita Acara')
    note_ba_sr = fields.Text('Note Berita Acara SR')
    note_ba_pos = fields.Text('Note Berita Acara POS')
    approved_adh_on = fields.Datetime('Approved ADH on')
    approved_adh_uid = fields.Many2one('res.users','Approved ADH by')
    approved_soh_on = fields.Datetime('Approved SOH on')
    approved_soh_uid = fields.Many2one('res.users','Approved SOH by')
    reason_cancel = fields.Text('Cancel Reason')
    cancel_uid = fields.Many2one('res.users','Cancelled by')
    cancel_date = fields.Datetime('Cancelled on')

    # @api.model
    # def _auto_init(self):
    #     res = super(CashCount, self)._auto_init()
    #     # Bank Transfer
    #     self._cr.execute("""
    #         SELECT indexname 
    #         FROM pg_indexes 
    #         WHERE indexname = 'branch_state_date_wtc_bank_transfer_index'
    #     """)
    #     if not self._cr.fetchone():
    #         self._cr.execute('CREATE INDEX branch_state_date_wtc_bank_transfer_index ON wtc_bank_transfer(branch_id,state,date)')

    #     # Petty Cash
    #     self._cr.execute("""
    #         SELECT indexname 
    #         FROM pg_indexes 
    #         WHERE indexname = 'branch_state_date_wtc_pettycash_index'
    #     """)
    #     if not self._cr.fetchone():
    #         self._cr.execute('CREATE INDEX branch_state_date_wtc_pettycash_index ON wtc_pettycash(branch_id,state,date)')
        
    #     # Reimburse
    #     self._cr.execute("""
    #         SELECT indexname 
    #         FROM pg_indexes 
    #         WHERE indexname = 'branch_state_date_wtc_reimbursed_index'
    #     """)
    #     if not self._cr.fetchone():
    #         self._cr.execute('CREATE INDEX branch_state_date_wtc_reimbursed_index ON wtc_reimbursed (branch_id,state,date_request)')

    #     return res

    @api.model
    def create(self,vals):
        vals['name'] = self.env['ir.sequence'].get_per_branch_date(vals['branch_id'], 'CC')
        return super(CashCount,self).create(vals)

    @api.multi
    def unlink(self):
        for me in self:
            if me.state != 'draft':
                raise Warning("Data selain draft tidak bisa dihapus !")
        return super(CashCount, self).unlink()

    @api.multi
    def action_update_plafon(self):
        self.plafon_petty_cash_sr = self.branch_id.plafon_petty_cash_sr
        self.plafon_petty_cash_ws = self.branch_id.plafon_petty_cash_ws
        self.plafon_petty_cash_atl_btl = self.branch_id.plafon_petty_cash_atl_btl

    @api.multi
    def action_generate_data(self):
        cash_detail_ids = []
        petty_cash_detail_ids = []
        reimburse_petty_cash_detail_ids = []

        self.plafon_petty_cash_sr = self.branch_id.plafon_petty_cash_sr
        self.plafon_petty_cash_ws = self.branch_id.plafon_petty_cash_ws
        self.plafon_petty_cash_atl_btl = self.branch_id.plafon_petty_cash_atl_btl

        # Cash
        query_cash = """
            SELECT bt.name
            , bt.date
            , 'posted' as state
            , btl.description
            , btl.amount
            , UPPER(aj.name) as journal
            , aj.id as journal_id 
            FROM wtc_bank_transfer bt
            INNER JOIN wtc_bank_transfer_line btl ON btl.bank_transfer_id = bt.id
            INNER JOIN account_journal aj ON aj.id = bt.payment_from_id
            WHERE bt.branch_id = %d
            AND bt.state = 'approved'
            AND bt.date = '%s'
            AND aj.type = 'cash'
            ORDER by bt.name ASC
        """ %(self.branch_id.id,self.date)
        self.env.cr.execute(query_cash)
        ress = self.env.cr.dictfetchall()
        for res in ress:
            if 'GC' in res.get('journal'):
                continue
            if self.tipe == 'Showroom':
                if 'POS' in res.get('journal'):
                    continue
            elif self.tipe == 'POS':
                if 'POS' not in res.get('journal'):
                    continue
            cash_detail_ids.append([0,False,{
                'name':res.get('name'),
                'description':res.get('description'),
                'date':res.get('date'),
                'journal_id':res.get('journal_id'),
                'amount':res.get('amount'),
                'journal':res.get('journal'),
                'status':res.get('state','').title(),
            }])

        # Petty Cash
        query_pc = """
            SELECT pc.name
            , pc.date
            , pc.state
            , pcl.name as description
            , pcl.amount_real as amount
            , aj.name as journal
            , aj.id as journal_id 
            FROM wtc_pettycash pc
            INNER JOIN wtc_pettycash_line pcl ON pcl.pettycash_id = pc.id
            INNER JOIN account_journal aj ON aj.id = pc.journal_id
            WHERE pc.branch_id = %d
            AND pc.state = 'posted'
            AND pc.date <= '%s'
            AND aj.type = 'pettycash'
            AND pcl.amount_real > 0
            ORDER BY pc.name ASC
        """ %(self.branch_id.id,self.date)
        self.env.cr.execute(query_pc)
        ress = self.env.cr.dictfetchall()
        for res in ress:
            if 'GC' in res.get('journal'):
                continue
            if self.tipe == 'Showroom':
                if 'POS' in res.get('journal'):
                    continue
            elif self.tipe == 'POS':
                if 'POS' not in res.get('journal'):
                    continue
            petty_cash_detail_ids.append([0,False,{
                'name':res.get('name'),
                'description':res.get('description'),
                'date':res.get('date'),
                'journal_id':res.get('journal_id'),
                'journal':res.get('journal'),
                'status':res.get('state','').title(),
                'amount':res.get('amount'),
            }])

        # Reimburse
        query_rb = """
            SELECT
            r.name
            , r.state
            , r.date_request
            , r.amount_total
            , aj.name as journal
            , aj.id as journal_id 
            FROM wtc_reimbursed r
            INNER JOIN account_journal aj ON aj.id = r.journal_id
            WHERE r.branch_id = %d
            AND r.state in ('request','approved')
            AND r.date_request <= '%s'
            AND aj.type = 'pettycash'
            ORDER BY r.name ASC
         """ %(self.branch_id.id,self.date)
        self.env.cr.execute(query_rb)
        ress = self.env.cr.dictfetchall()
        for res in ress:
            if 'GC' in res.get('journal'):
                continue
            if self.tipe == 'Showroom':
                if 'POS' in res.get('journal'):
                    continue
            elif self.tipe == 'POS':
                if 'POS' not in res.get('journal'):
                    continue
            reimburse_petty_cash_detail_ids.append([0,False,{
                'name':res.get('name'),
                'date':res.get('date_request'),
                'journal_id':res.get('journal_id'),
                'journal':res.get('journal'),
                'status':res.get('state','').title(),
                'amount':res.get('amount_total'),       
            }])
        
        self.write({
            'generate_date':self._get_default_datetime(),
            'cash_detail_ids':cash_detail_ids,
            'petty_cash_detail_ids':petty_cash_detail_ids,
            'reimburse_petty_cash_detail_ids':reimburse_petty_cash_detail_ids,    
        })

    @api.multi
    def action_rfa(self):
        if not self.generate_date:
            raise Warning('Silahkan Generate Data Terlebih Dahulu !')
        # Cek Data Validasi
        for x in self.cash_detail_ids:
            if not x.validasi_id:
                raise Warning('Data Cash masih ada yang belum di validasi !')
        
        for x in self.petty_cash_detail_ids:
            if not x.validasi_id:
                raise Warning('Data Petty Cash masih ada yang belum di validasi !')

        self.write({'state':'rfa'})
    
    @api.multi
    def action_approved(self):
        group_adh = self.env['res.users'].has_group('teds_cash_count.group_teds_cash_count_approved_adh')
        group_soh = self.env['res.users'].has_group('teds_cash_count.group_teds_cash_count_approved_soh')
        
        vals = {}
        if group_soh:
            self.approved_soh_on = self._get_default_datetime()
            self.approved_soh_uid = self._uid
        if group_adh:
            self.approved_adh_on = self._get_default_datetime()
            self.approved_adh_uid = self._uid
        if self.approved_adh_on and self.approved_soh_on:
            self.state = 'approved'
    
    @api.multi
    def action_post(self):
        if not self.generate_date:
            raise Warning('Silahkan Generate Data Terlebih Dahulu !')
        # Cek Data Validasi
        for x in self.cash_detail_ids:
            if not x.validasi_id:
                raise Warning('Data Cash masih ada yang belum di validasi !')
        
        for x in self.petty_cash_detail_ids:
            if not x.validasi_id:
                raise Warning('Data Petty Cash masih ada yang belum di validasi !')
                
        self.write({
            'post_date':self._get_default_datetime(),
            'post_uid':self._uid,
            'state':'posted',    
        })

    @api.multi
    def action_bakso(self):
        form_id = self.env.ref('teds_cash_count.view_teds_cash_count_berita_acara_wizard').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Berita Acara',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teds.cash.count.berita.acara.wizard',
            'context':{'default_cash_count_id':self.id,'default_options':self.tipe},
            'views': [(form_id, 'form')],
            'target':'new'
        }

    @api.multi
    def action_cancel(self):
        form_id = self.env.ref('teds_cash_count.view_teds_cash_count_cancel_wizard').id
        return {
            'name': 'Cancel Cash Count',
            'res_model': 'teds.cash.count',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'views': [(form_id, 'form')],
            'view_mode': 'form',
            'target': 'new',
            'view_type': 'form',
            'res_id': self.id,
        }

    @api.multi
    def action_cancel_submit(self):
        if self.state != 'posted':
            raise Warning('Cash Count tidak bisa dicancel !')
        self.write({
            'state':'cancelled',
            'cancel_uid':self._uid,
            'cancel_date':self._get_default_datetime(),    
        })

    @api.onchange('branch_id')
    def onchange_branch(self):
        if self.branch_id:
            self.kasir = self.branch_id.kasir_id.name
            self.admin_pos = self.branch_id.admin_pos_id.name
            self.adh = self.branch_id.adh_id.name
            self.soh = self.branch_id.pimpinan_id.name


class CashCountDetail(models.Model):
    _name = "teds.cash.count.detail"

    @api.multi
    @api.depends('amount','amount_fisik')
    def _compute_selisih(self):
        for me in self:
            if me.amount and me.amount_fisik:
                me.selisih = me.amount - me.amount_fisik


    cash_count_id = fields.Many2one('teds.cash.count','Cash Count',ondelete='cascade')
    name = fields.Char('Name')
    journal_id = fields.Many2one('account.journal','Journal')
    journal = fields.Char('Journal',index=True)
    status = fields.Char('Status')
    date = fields.Date('Date')
    description = fields.Char('Description')
    amount = fields.Float('Amount Sistem')
    amount_fisik = fields.Float('Amount Fisik')
    selisih = fields.Float('Amount Selisih',compute='_compute_selisih')
    keterangan = fields.Char('Keterangan')
    type = fields.Selection([
        ('cash','Cash'),
        ('petty_cash','Petty Cash'),
        ('reimburse_petty_cash','Reimburse Petty Cash')],index=True)
    validasi_id = fields.Many2one('teds.cash.count.validasi','Validasi',domain="[('type','=',type)]")

    @api.onchange('validasi_id')
    def onchange_validasi(self):
        if self.validasi_id:
            self.keterangan = self.validasi_id.note
            
class CashCountOther(models.Model):
    _name = "teds.cash.count.other"

    cash_count_id = fields.Many2one('teds.cash.count','Cash Count')
    name = fields.Char('Description')
    amount = fields.Float('Amount')
    keterangan = fields.Char('Keterangan')


class CashCountBeritaAcaraWizard(models.TransientModel):
    _name = "teds.cash.count.berita.acara.wizard"

    cash_count_id = fields.Many2one('teds.cash.count','Cash Count')
    options = fields.Selection([('ALL','ALL'),('POS','POS'),('Showroom','Showroom')])
    note = fields.Text('Note')

    @api.onchange('cash_count_id','options')
    def onchange_note(self):
        if self.cash_count_id and self.options:
            if self.options == 'POS':
                self.note = self.cash_count_id.note_ba_pos
            elif self.options == 'Showroom':
                self.note = self.cash_count_id.note_ba_sr
            else:
                self.note = self.cash_count_id.note_ba

    @api.multi
    def action_submit(self):
        active_ids = self.env.context.get('active_ids', [])
        user = self.env['res.users'].browse(self._uid).name

        # Cash
        saldo_fisik_cash = 0
        cash_detail = []

        # Petty Cash SR
        plafon_petty_cash_sr = self.cash_count_id.plafon_petty_cash_sr
        saldo_sistem_petty_cash_sr = 0
        saldo_fisik_petty_cash_sr = self.cash_count_id.fisik_petty_cash_sr
        saldo_pc_sr = self.cash_count_id.saldo_pc_sr
        saldo_sistem_reimburse_sr = 0
        petty_cash_sr_detail = []
        reimburse_petty_cash_sr_detail = []

        # Petty Cash WS
        plafon_petty_cash_ws = self.cash_count_id.plafon_petty_cash_ws
        saldo_sistem_petty_cash_ws = 0
        saldo_fisik_petty_cash_ws = self.cash_count_id.fisik_petty_cash_ws
        saldo_pc_ws = self.cash_count_id.saldo_pc_ws
        saldo_sistem_reimburse_ws = 0
        petty_cash_ws_detail = []
        reimburse_petty_cash_ws_detail = []
    
        # Petty Cash ATL/BTL
        plafon_petty_cash_atl_btl = self.cash_count_id.plafon_petty_cash_atl_btl
        saldo_sistem_petty_cash_atl_btl = 0
        saldo_fisik_petty_cash_atl_btl = self.cash_count_id.fisik_petty_cash_atl_btl
        saldo_pc_atl_btl = self.cash_count_id.saldo_pc_atl_btl
        saldo_sistem_reimburse_atl_btl = 0
        petty_cash_atl_btl_detail = []
        reimburse_petty_cash_atl_btl_detail = []
        
        # Penerimaan Lain
        saldo_fisik_other = 0
        other_detail = []

        for x in self.cash_count_id.cash_detail_ids:
            if self.options == 'POS':
                if 'POS' in x.journal:
                    if x.validasi_id.name == 'Belum disetor ke bank':
                        cash_detail.append({
                            'name':x.name,
                            'journal':x.journal,
                            'amount':x.amount,
                            'amount_fisik':x.amount_fisik,
                            'selisih':x.selisih,
                        })
                        saldo_fisik_cash += x.amount

            elif self.options == 'Showroom':
                if 'POS' in x.journal:
                    continue
                if x.validasi_id.name == 'Belum disetor ke bank':
                    cash_detail.append({
                        'name':x.name,
                        'journal':x.journal,
                        'amount':x.amount,
                        'amount_fisik':x.amount_fisik,
                        'selisih':x.selisih,
                    })
                    saldo_fisik_cash += x.amount

            else:
                if x.validasi_id.name == 'Belum disetor ke bank':
                    cash_detail.append({
                        'name':x.name,
                        'journal':x.journal,
                        'amount':x.amount,
                        'amount_fisik':x.amount_fisik,
                        'selisih':x.selisih,
                    })
                    saldo_fisik_cash += x.amount

        for x in self.cash_count_id.petty_cash_detail_ids:
            if 'SR' in x.journal:
                petty_cash_sr_detail.append({
                    'name':x.name,
                    'journal':x.journal,
                    'description':x.description,
                    'date':x.date,
                    'amount':x.amount,
                    'validasi':x.validasi_id.name,
                    'keterangan':x.keterangan,
                })
                saldo_sistem_petty_cash_sr += x.amount

            elif 'WS' in x.journal:
                petty_cash_ws_detail.append({
                    'name':x.name,
                    'journal':x.journal,
                    'description':x.description,
                    'date':x.date,
                    'amount':x.amount,
                    'validasi':x.validasi_id.name,
                    'keterangan':x.keterangan,
                })
                saldo_sistem_petty_cash_ws += x.amount
            
            elif 'ATLBTL' in x.journal:
                petty_cash_atl_btl_detail.append({
                    'name':x.name,
                    'journal':x.journal,
                    'description':x.description,
                    'date':x.date,
                    'amount':x.amount,
                    'validasi':x.validasi_id.name,
                    'keterangan':x.keterangan,
                })
                saldo_sistem_petty_cash_atl_btl += x.amount

        for x in self.cash_count_id.reimburse_petty_cash_detail_ids:
            if 'SR' in x.journal:
                reimburse_petty_cash_sr_detail.append({
                    'name':x.name,
                    'journal':x.journal,
                    'date':x.date,
                    'amount':x.amount,    
                })
                saldo_sistem_reimburse_sr += x.amount 

            elif 'WS' in x.journal:
                reimburse_petty_cash_ws_detail.append({
                    'name':x.name,
                    'journal':x.journal,
                    'date':x.date,
                    'amount':x.amount,    
                })
                saldo_sistem_reimburse_ws += x.amount
            
            elif 'ATLBTL' in x.journal:
                reimburse_petty_cash_atl_btl_detail.append({
                    'name':x.name,
                    'journal':x.journal,
                    'date':x.date,
                    'amount':x.amount,    
                })
                saldo_sistem_reimburse_atl_btl += x.amount


        for x in self.cash_count_id.peneriman_lain_ids:
            other_detail.append({
                'name':x.name,
                'amount':x.amount,
                'keterangan':x.keterangan,    
            })
            saldo_fisik_other += x.amount
            

        if self.options == 'POS':
            self.cash_count_id.note_ba_pos = self.note
            
        elif self.options == 'Showroom':
            self.cash_count_id.note_ba_sr = self.note
        else:
            self.cash_count_id.note_ba = self.note


        total_saldo_sistem_petty_cash_sr = (plafon_petty_cash_sr - saldo_pc_sr - saldo_sistem_petty_cash_sr - saldo_sistem_reimburse_sr)
        total_saldo_sistem_petty_cash_ws = (plafon_petty_cash_ws - saldo_pc_ws - saldo_sistem_petty_cash_ws - saldo_sistem_reimburse_ws)
        total_saldo_sistem_petty_cash_atl_btl = (plafon_petty_cash_atl_btl - saldo_pc_atl_btl - saldo_sistem_petty_cash_atl_btl - saldo_sistem_reimburse_atl_btl)
        total_saldo_fisik = saldo_fisik_cash + saldo_fisik_petty_cash_sr + saldo_fisik_petty_cash_ws + saldo_fisik_petty_cash_atl_btl + saldo_fisik_other
        
        selisih_petty_cash_sr = total_saldo_sistem_petty_cash_sr - saldo_fisik_petty_cash_sr
        selisih_petty_cash_ws = total_saldo_sistem_petty_cash_ws - saldo_fisik_petty_cash_ws
        selisih_petty_cash_atl_btl = total_saldo_sistem_petty_cash_atl_btl - saldo_fisik_petty_cash_atl_btl

        datas = {
            'name':self.cash_count_id.name,
            'branch':self.cash_count_id.branch_id.name,
            'lokasi':'Pos & Showroom',
            'tanggal':self.cash_count_id.date,
            'saldo_fisik_cash':saldo_fisik_cash,
            'cash_detail':cash_detail,
            'plafon_petty_cash_sr':plafon_petty_cash_sr,
            'saldo_sistem_petty_cash_sr':saldo_sistem_petty_cash_sr,
            'saldo_fisik_petty_cash_sr':saldo_fisik_petty_cash_sr,
            'saldo_pc_sr':saldo_pc_sr,
            'selisih_petty_cash_sr':selisih_petty_cash_sr,
            'saldo_sistem_reimburse_sr':saldo_sistem_reimburse_sr,
            'petty_cash_sr_detail':petty_cash_sr_detail,
            'reimburse_petty_cash_sr_detail':reimburse_petty_cash_sr_detail,
            'plafon_petty_cash_ws':plafon_petty_cash_ws,
            'saldo_sistem_petty_cash_ws':saldo_sistem_petty_cash_ws,
            'saldo_fisik_petty_cash_ws':saldo_fisik_petty_cash_ws,
            'saldo_pc_ws':saldo_pc_ws,
            'selisih_petty_cash_ws':selisih_petty_cash_ws,
            'saldo_sistem_reimburse_ws':saldo_sistem_reimburse_ws,
            'petty_cash_ws_detail':petty_cash_ws_detail,
            'reimburse_petty_cash_ws_detail':reimburse_petty_cash_ws_detail,
            'plafon_petty_cash_atl_btl':plafon_petty_cash_atl_btl,
            'saldo_sistem_petty_cash_atl_btl':saldo_sistem_petty_cash_atl_btl,
            'saldo_fisik_petty_cash_atl_btl':saldo_fisik_petty_cash_atl_btl,
            'saldo_pc_atl_btl':saldo_pc_atl_btl,
            'selisih_petty_cash_atl_btl':selisih_petty_cash_atl_btl,
            'saldo_sistem_reimburse_atl_btl':saldo_sistem_reimburse_atl_btl,
            'petty_cash_atl_btl_detail':petty_cash_atl_btl_detail,
            'reimburse_petty_cash_atl_btl_detail':reimburse_petty_cash_atl_btl_detail,
            'note':self.note,
            'options':self.options,
            'kasir':self.cash_count_id.kasir,
            'admin_pos':self.cash_count_id.admin_pos,
            'adh':self.cash_count_id.adh,
            'soh':self.cash_count_id.soh,
            'total_saldo_sistem_petty_cash_sr':total_saldo_sistem_petty_cash_sr,
            'total_saldo_sistem_petty_cash_ws':total_saldo_sistem_petty_cash_ws,
            'total_saldo_sistem_petty_cash_atl_btl':total_saldo_sistem_petty_cash_atl_btl,
            'total_saldo_fisik':total_saldo_fisik,
            'saldo_fisik_other':saldo_fisik_other,
            'other_detail':other_detail,
            'total_saldo_sistem_all':saldo_fisik_cash+total_saldo_sistem_petty_cash_sr+total_saldo_sistem_petty_cash_ws+total_saldo_sistem_petty_cash_atl_btl,
            'create_uid':self.cash_count_id.create_uid.name,
            'approved_adh_uid':self.cash_count_id.approved_adh_uid.name,
            'approved_soh_uid':self.cash_count_id.approved_soh_uid.name,
            'create_date':self.cash_count_id.create_date,
            'approved_adh_on':self.cash_count_id.approved_adh_on,
            'approved_soh_on':self.cash_count_id.approved_soh_on,

        }
        return self.env['report'].get_action(self,'teds_cash_count.teds_cash_count_print_berita_acara', data=datas)