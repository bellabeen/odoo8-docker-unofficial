import time
from datetime import datetime, timedelta,date
from openerp.report import report_sxw
from openerp import models, fields, api

class ProsesBirojasaTracking(models.TransientModel):
    _name = "teds.proses.birojasa.tracking"

    name = fields.Char('No PRBJ')
    options = fields.Selection([('No PRBJ','No PRBJ'),('Periode','Periode')],string="Options")
    status = fields.Selection([
        ('Outstanding HO','Outstanding HO'),
        ('Outstanding Pajak','Outstanding Pajak'),
        ('Outstanding Finance','Outstanding Finance'),
        ('Outstanding ALL','Outstanding ALL')],string="Status")
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    branch_ids = fields.Many2many('wtc.branch', 'teds_proses_birojasa_tracking_branch_rel', 'tracking_id','branch_id', string='Branch')
    birojasa_ids = fields.Many2many('res.partner','teds_proses_birojasa_tracking_birojasa_rel','tracking_id','birojasa_id',string="Birojasa",domain=[('biro_jasa','=',True)])
    detail_ids = fields.One2many('teds.proses.birojasa.tracking.detail','tracking_id')
    is_report = fields.Boolean('Is Report ?')

    @api.onchange('options')
    def onchange_options(self):
        self.name = False
        self.start_date = False
        self.end_date = False
        self.branch_ids = False
        self.birojasa_ids = False
        self.status = False


    @api.multi
    def action_submit(self):
        self.detail_ids = False
        self.is_report = False

        query_where = " WHERE 1=1"

        if self.name:
            query_where +=  " AND name = '%s'" %(self.name)
        if self.start_date:
            query_where +=  " AND tanggal >= '%s'" %(self.start_date)
        if self.end_date:
            query_where +=  " AND tanggal <= '%s'" %(self.end_date)

        if self.branch_ids:
            branch = [b.id for b in self.branch_ids]
            query_where += " AND branch_id in %s" % str(tuple(branch)).replace(',)', ')')
        if self.birojasa_ids:
            birojasa = [b.id for b in self.birojasa_ids]
            query_where += " AND partner_id in %s" % str(tuple(birojasa)).replace(',)', ')')

        if self.status:
            if self.status == 'Outstanding HO':
                query_where += " AND tgl_terima_document_ho IS NULL"
            elif self.status == 'Outstanding Pajak':
                query_where += " AND tgl_terima_document_pajak IS NULL"
            elif self.status == 'Outstanding Finance':
                query_where += " AND tgl_terima_document_finance IS NULL"
            elif self.status == 'Outstanding ALL':
                query_where += " AND tgl_terima_document_ho IS NULL AND tgl_terima_document_pajak IS NULL AND tgl_terima_document_finance IS NULL"


        query = """
            SELECT branch_id
            , partner_id
            , name
            , tanggal
            , tgl_dok
            , amount_total
            , tgl_terima_document_ho
            , tgl_terima_document_pajak
            , tgl_terima_document_finance
            , confirm_date
            , CASE WHEN state = 'draft' THEN 'Draft'
                WHEN state = 'waiting_for_approval' THEN 'Waiting For Approval'
                WHEN state = 'confirmed' THEN 'Approved'
                WHEN state = 'approved' THEN 'Process Confirmed'
                WHEN state = 'except_invoice' THEN 'Invoice Exception'
                WHEN state = 'done' THEN 'Done'
                WHEN state = 'cancel' THEN 'Cancelled'
                ELSE '' END as state
            FROM wtc_proses_birojasa
            %s
        """ %(query_where)
        self._cr.execute (query)
        ress =  self._cr.dictfetchall()
        ids = []
        for res in ress:
            ids.append([0,False,{
                'branch_id':res.get('branch_id'),
                'birojasa_id':res.get('partner_id'),
                'name':res.get('name'),
                'date':res.get('tanggal'),
                'total':res.get('amount_total'),
                'tanggal_dokumen':res.get('tgl_dok'),
                'tgl_terima_document_ho':res.get('tgl_terima_document_ho'),
                'tgl_terima_document_pajak':res.get('tgl_terima_document_pajak'),
                'tgl_terima_document_finance':res.get('tgl_terima_document_finance'),
                'tgl_confirm':res.get('confirm_date'),
                'state':res.get('state'),
            }])
        if len(ids) > 0:
            self.write({
                'detail_ids':ids,
                'is_report':True    
            })

    @api.multi
    def action_print_excel(self):
        datas = self.read()[0]
        return self.env['report'].get_action(self,'teds_proses_birojasa.teds_proses_birojasa_tracking_print', data=datas)





class ProsesBirojasaTrackingDetail(models.TransientModel):
    _name = "teds.proses.birojasa.tracking.detail"

    @api.depends('date')
    def _compute_tgl_jtp(self):
        for me in self:
            if me.date:
                me.tgl_jtp = datetime.strptime(me.date, '%Y-%m-%d') + timedelta(days=7)
    
    @api.depends('date','tanggal_dokumen')
    def _compute_lt_cabang(self):
        for me in self:
            if me.date and me.tanggal_dokumen:
                me.leadtime_cabang = (datetime.strptime(me.date,'%Y-%m-%d') - datetime.strptime(me.tanggal_dokumen,'%Y-%m-%d')).days
    
    @api.depends('date','tgl_terima_document_ho')
    def _compute_lt_ho(self):
        for me in self:
            leadtime = 0
            if me.date and me.tgl_terima_document_ho:
                leadtime = (datetime.strptime(me.tgl_terima_document_ho,'%Y-%m-%d') - datetime.strptime(me.date,'%Y-%m-%d')).days
            me.leadtime_ho = leadtime

    @api.depends('tgl_terima_document_ho','tgl_terima_document_pajak')
    def _compute_lt_pajak(self):
        for me in self:
            leadtime = 0
            if me.tgl_terima_document_ho and me.tgl_terima_document_pajak:
                leadtime = (datetime.strptime(me.tgl_terima_document_pajak,'%Y-%m-%d') - datetime.strptime(me.tgl_terima_document_ho,'%Y-%m-%d')).days
            me.leadtime_pajak = leadtime    
    @api.depends('date','tanggal_dokumen')
    def _compute_lt_finace(self):
        for me in self:
            leadtime = 0
            if me.tgl_terima_document_pajak and me.tgl_terima_document_finance:
                leadtime = (datetime.strptime(me.tgl_terima_document_finance,'%Y-%m-%d') - datetime.strptime(me.tgl_terima_document_pajak,'%Y-%m-%d')).days
            me.leadtime_finance = leadtime
    

    @api.depends('tgl_jtp','tgl_confirm','state')
    def _compute_ket(self):
        for me in self:
            if (me.tgl_confirm > me.tgl_jtp) and me.state in ('Process Confirmed','Done'):
                me.keterangan = 'Tidak Sesuai'
            elif (me.tgl_confirm <= me.tgl_jtp) and me.state in ('Process Confirmed','Done'):
                me.keterangan = 'Sesuai'
                

    tracking_id = fields.Many2one('teds.proses.birojasa.tracking','tracking_id')
    branch_id = fields.Many2one('wtc.branch','Branch')
    birojasa_id = fields.Many2one('res.partner','Birojasa')
    name = fields.Char('No PRBJ')
    date = fields.Date('Tgl PRBJ')
    tgl_jtp = fields.Date('Tgl JTP',compute='_compute_tgl_jtp')
    total = fields.Float('Total')
    tanggal_dokumen = fields.Date('Tgl Dokumen')
    leadtime_cabang = fields.Integer('L-T Cabang',compute='_compute_lt_cabang')
    tgl_terima_document_ho = fields.Date('Terima HO')
    leadtime_ho = fields.Integer('L-T HO',compute='_compute_lt_ho')
    tgl_terima_document_pajak = fields.Date('Terima Pajak')
    leadtime_pajak = fields.Integer('L-T Pajak',compute='_compute_lt_pajak')
    tgl_terima_document_finance = fields.Date('Terima Finance')
    leadtime_finance = fields.Integer('L-T Finance',compute='_compute_lt_finace')
    tgl_confirm = fields.Date('Tgl Confirm')
    state = fields.Char('State')
    keterangan = fields.Char('Ket',compute='_compute_ket')
