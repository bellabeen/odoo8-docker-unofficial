from openerp import models, fields, api
import openerp.http as http
from openerp.http import request
import time
from datetime import datetime,date
from dateutil.relativedelta import relativedelta
from openerp.exceptions import except_orm, Warning, RedirectWarning


class InsentiveSales(models.TransientModel):
    _name = "teds.insentif.salesman.wizard"

    def _get_default_start_date(self):
        now = (date.today() - relativedelta(months=1)).replace(day=1)
        return now
    
    def _get_default_end_date(self):
        bln = date.today().replace(day=1)
        now = bln - relativedelta(days=1)
        return now

    employee_id = fields.Many2one('hr.employee','Sales Force')
    branch_id = fields.Many2one('wtc.branch','Branch')
    start_date = fields.Date('Start Date',default=_get_default_start_date)
    end_date = fields.Date('End Date',default=_get_default_end_date)
    job_name = fields.Char('Jabatan',related='employee_id.job_id.name',readonly=True)
    unit_cash = fields.Integer('Unit Cash')
    rupiah_unit_cash = fields.Integer('Rp Cash')
    unit_credit = fields.Integer('Unit Credit')
    rupiah_unit_credit = fields.Integer('Rp Credit')
    # unit_credit_ke = fields.Integer('Unit Credit Ke')
    total_unit = fields.Integer('Total Unit')
    rupiah_total_unit = fields.Integer('Rp Total Unit')
    unit_ar_cash =fields.Integer('Unit AR Cash')
    rupiah_unit_ar_cash =fields.Integer('Rp Unit AR Cash')
    unit_ar_credit =fields.Integer('Unit AR Credit')
    rupiah_unit_ar_credit =fields.Integer('Rp Unit AR Credit')
    reward = fields.Integer('Reward')
    rupiah_reward = fields.Integer('Rp Reward')
    mediator_cash = fields.Integer('Mediator Cash')
    mediator_credit = fields.Integer('Mediator Credit')
    total_unit_mediator = fields.Integer('Total Unit Mediator')
    rupiah_persen_credit = fields.Integer('Rp % Credit')
    rupiah_persen_mediator = fields.Integer('Rp % Mediator')
    rupiah_persen_absensi = fields.Integer('Rp % Absensi')
    jml_bawahan = fields.Integer('Jml Bawahan')
    produktivitas = fields.Integer('Produktivitas')
    jml_insentif = fields.Integer('Jml Insentif')
    is_report = fields.Boolean('Is Report')

    @api.onchange('employee_id')
    def onchange_is_report(self):
        self.is_report = False
    
    @api.onchange('branch_id')
    def onchange_employee(self):
        self.employee_id = False
        self.is_report = False
        ids = []
        if self.branch_id:
            jobs = self.env['hr.job'].search([('sales_force','in',('sales_counter','salesman','sales_partner','sales_koordinator','soh'))])
            empl = self.env['hr.employee'].sudo().search([
                ('branch_id','=',self.branch_id.id),
                ('job_id','in',[j.id for j in jobs]),
                ('tgl_keluar','=',False)])
            ids = [e.id for e in empl]
        domain = {'employee_id':[('id','in',ids)]}
        return {'domain':domain}

    @api.multi
    def action_hitung_insentif(self):
        self.unit_cash = False
        self.rupiah_unit_cash = False
        self.unit_credit = False
        self.rupiah_unit_credit = False
        self.total_unit = False
        self.rupiah_total_unit = False
        self.unit_ar_cash = False
        self.rupiah_unit_ar_cash = False
        self.unit_ar_credit = False
        self.rupiah_unit_ar_credit = False
        self.reward = False
        self.rupiah_reward = False
        self.mediator_cash = False
        self.mediator_credit = False
        self.total_unit_mediator = False
        self.rupiah_persen_credit = False
        self.rupiah_persen_mediator = False
        self.rupiah_persen_absensi = False
        self.jml_bawahan = False
        self.produktivitas = False
        self.jml_insentif = False

        if not self.branch_id.cluster:
            raise Warning('Branch Cluster belum disetting, silahkan setting di master branch !')

        if self.employee_id.job_id.sales_force == 'sales_counter':
            self.salesCounter()
        elif self.employee_id.job_id.sales_force == 'salesman':
            self.salesPayroll()
        elif self.employee_id.job_id.sales_force == 'sales_partner':
            self.salesPartner()
        elif self.employee_id.job_id.sales_force == 'sales_koordinator':
            self.koordinatorSalesman()
        elif self.employee_id.job_id.sales_force == 'soh':
            self.soh()

        self.is_report = True

    @api.multi
    def salesCounter(self):
        branch_id = self.branch_id.id
        branch_cluster = self.branch_id.cluster
        user_id = self.employee_id.resource_id.user_id.id
        job_name = self.job_name.upper()
        
        query = """
            SELECT sum(aa.cash)cash 
            , sum(aa.credit) credit 
            FROM (
                SELECT dsoh.user_id
                , CASE WHEN dsoh.finco_id IS NULL THEN 1 ELSE 0 END cash 
                , CASE WHEN dsoh.finco_id IS NOT NULL THEN 1 ELSE 0 END credit
                FROM dealer_sale_order_line dsol
                LEFT JOIN dealer_sale_order dsoh ON dsoh.id = dsol.dealer_sale_order_line_id
                WHERE dsoh.branch_id = %s 
                AND dsoh.user_id = %s 
                AND dsoh.date_confirm BETWEEN '%s' AND '%s'
                AND dsoh.state IN ('progress','done','cancelled')
            ) aa
            GROUP BY aa.user_id
        """ %(branch_id,user_id,self.start_date,self.end_date)

        self._cr.execute(query)
        res = self._cr.fetchone()

        cash_ok = 0
        credit_ok = 0
        if res:
            cash_ok = 0 if not res[0] else res[0]
            credit_ok = 0 if not res[1] else res[1]

        query_batal = """
            SELECT sum(aa.cash)cash 
            , sum(aa.credit) credit 
            FROM (
                SELECT dsoh.user_id
                , CASE WHEN dsoh.finco_id IS NULL THEN 1 ELSE 0 END cash 
                , CASE WHEN dsoh.finco_id IS NOT NULL THEN 1 ELSE 0 END credit
                FROM dealer_sale_order_line dsol
                LEFT JOIN dealer_sale_order dsoh ON dsoh.id = dsol.dealer_sale_order_line_id
                WHERE dsoh.branch_id = %s AND dsoh.user_id = %s 
                AND date(dsoh.cancelled_date + interval '7 hours') BETWEEN '%s' AND '%s'
                AND dsoh.state IN ('cancelled')
            )aa
            GROUP BY aa.user_id
        """ %(branch_id,user_id,self.start_date,self.end_date)

        self._cr.execute(query_batal)
        res_batal = self._cr.fetchone()
        cash_batal = 0
        credit_batal = 0
        if res_batal:
            cash_batal = 0 if not res_batal[0] else res_batal[0]
            credit_batal = 0 if not res_batal[1] else res_batal[1]

        cash = cash_ok - cash_batal
        credit = credit_ok - credit_batal

        total_unit = cash + credit

        if total_unit == 0:
            raise Warning('Tidak ada penjualan pada periode tersebut !')

        rp_listing = self.env['teds.listing.table.insentif'].search([
            ('name','=',job_name),
            ('total','=',total_unit)],limit=1)
        
        listing_cash = rp_listing.cash
        listing_credit = rp_listing.credit

        sl = 'SL%'
        # ini juga blm per unit.
        query_ar_cash = """
            SELECT dsoh.user_id
            , count(dsoh.user_id)ar_cash 
            FROM dealer_sale_order dsoh
            LEFT JOIN dealer_sale_order_line dsol ON dsol.dealer_sale_order_line_id = dsoh.id
            LEFT JOIN account_invoice ai ON ai.origin = dsoh.name AND number like '%s'
            WHERE dsoh.state IN ('progress','done','cancelled') 
            AND dsoh.branch_id = %s 
            AND dsoh.user_id = %s 
            AND dsoh.date_confirm BETWEEN '%s' AND '%s'
            AND ai.state !='paid' 
            AND dsoh.finco_id IS NULL
            GROUP BY dsoh.user_id
        """ %(sl,branch_id,user_id,self.start_date,self.end_date)
        self._cr.execute(query_ar_cash)
        res_ar_cash = self._cr.fetchone()
        
        ar_cash = 0
        if res_ar_cash:
            ar_cash = res_ar_cash[1]

        query_ar_credit = """
            SELECT dsoh.user_id
            , count(dsoh.user_id) ar_credit 
            FROM dealer_sale_order dsoh
            LEFT JOIN dealer_sale_order_line dsol ON dsol.dealer_sale_order_line_id = dsoh.id
            LEFT JOIN account_invoice ai ON ai.origin = dsoh.name AND number like '%s'
            WHERE dsoh.state IN ('progress','done','cancelled') 
            AND dsoh.branch_id = %s 
            AND dsoh.user_id = %s 
            AND dsoh.date_confirm BETWEEN '%s' AND '%s'
            AND ai.state !='paid' 
            AND dsoh.finco_id IS NOT NULL
            GROUP BY dsoh.user_id
        """ %(sl,branch_id,user_id,self.start_date,self.end_date)
        self._cr.execute(query_ar_credit)
        res_ar_credit = self._cr.fetchone()
        
        ar_credit = 0
        if res_ar_credit:
            ar_credit = res_ar_credit[1]

        query_mediator = """
            SELECT sum(CASE WHEN finco_id IS NULL THEN 1 ELSE 0 END) cash_mediator
            , sum(CASE WHEN finco_id IS NOT NULL THEN 1 ELSE 0 END) credit_mediator
            FROM dealer_sale_order dsoh
            LEFT JOIN dealer_sale_order_line dsol ON dsol.dealer_sale_order_line_id = dsoh.id
            WHERE state IN ('progress', 'done','cancelled') 
            AND branch_id = %s 
            AND user_id = %s 
            AND date_confirm BETWEEN '%s' AND '%s' 
            AND dsoh.partner_komisi_id IS NOT NULL
        """ %(branch_id,user_id,self.start_date,self.end_date)

        self._cr.execute(query_mediator)
        res_mediator = self._cr.fetchone()
        
        cash_mediator_ok = 0
        credit_mediator_ok = 0
        if res_mediator:
            cash_mediator_ok = 0 if not res_mediator[0] else res_mediator[0]
            credit_mediator_ok = 0 if not res_mediator[1] else res_mediator[1]

        query_mediator_batal = """
            SELECT sum(CASE WHEN finco_id IS NULL THEN 1 ELSE 0 END) cash_mediator
            , sum(CASE WHEN finco_id IS NOT NULL THEN 1 ELSE 0 END) credit_mediator
            FROM dealer_sale_order dsoh
            LEFT JOIN dealer_sale_order_line dsol ON dsol.dealer_sale_order_line_id = dsoh.id
            WHERE state IN ('cancelled') 
            AND branch_id = %s 
            AND user_id = %s 
            AND date(dsoh.cancelled_date + interval '7 hours') BETWEEN '%s' AND '%s' 
            AND dsoh.partner_komisi_id IS NOT NULL
        """ %(branch_id,user_id,self.start_date,self.end_date)

        self._cr.execute(query_mediator_batal)
        res_mediator_batal = self._cr.fetchone()
        
        cash_mediator_batal = 0
        credit_mediator_batal = 0
        if res_mediator_batal:
            cash_mediator_batal = 0 if not res_mediator_batal[0] else res_mediator_batal[0]
            credit_mediator_batal = 0 if not res_mediator_batal[1] else res_mediator_batal[1]

        cash_mediator = cash_mediator_ok - cash_mediator_batal
        credit_mediator = credit_mediator_ok - credit_mediator_batal

        cash_nomed = cash - cash_mediator
        credit_nomed = credit - credit_mediator
        total_unit_mediator = cash_mediator + credit_mediator
        rupiah_unit_cash = cash_nomed * listing_cash 
        rupiah_unit_credit = credit_nomed * listing_credit
        rupiah_total_unit = rupiah_unit_cash + rupiah_unit_credit
        rupiah_unit_ar_cash = ar_cash * listing_cash
        rupiah_unit_ar_credit = ar_credit * listing_credit
        total_insentif = rupiah_unit_cash + rupiah_unit_credit - (rupiah_unit_ar_cash + rupiah_unit_ar_credit)

        self.unit_cash = cash
        self.rupiah_unit_cash = rupiah_unit_cash
        self.unit_credit = credit
        self.rupiah_unit_credit = rupiah_unit_credit
        self.total_unit = total_unit
        self.rupiah_total_unit = rupiah_total_unit
        self.unit_ar_cash = ar_cash
        self.rupiah_unit_ar_cash = rupiah_unit_ar_cash
        self.unit_ar_credit = ar_credit
        self.rupiah_unit_ar_credit = rupiah_unit_ar_credit 
        self.mediator_cash = cash_mediator
        self.mediator_credit = credit_mediator
        self.total_unit_mediator = total_unit_mediator
        self.jml_insentif = total_insentif
        
        if total_insentif == 0:
            raise Warning('Total penjualan %s, tidak mencukupi quota perhitungan' %(total_unit))
        

    @api.multi
    def salesPayroll(self):
        branch_id = self.branch_id.id
        branch_cluster = self.branch_id.cluster
        user_id = self.employee_id.resource_id.user_id.id
        job_name = self.job_name.upper()
        
        query = """
            SELECT sum(aa.cash)cash 
            , sum(aa.credit) credit 
            FROM (
                SELECT dsoh.user_id
                , CASE WHEN dsoh.finco_id IS NULL THEN 1 ELSE 0 END cash 
                , CASE WHEN dsoh.finco_id IS NOT NULL THEN 1 ELSE 0 END credit
                FROM dealer_sale_order_line dsol
                LEFT JOIN dealer_sale_order dsoh ON dsoh.id = dsol.dealer_sale_order_line_id
                WHERE dsoh.branch_id = %s 
                AND dsoh.user_id = %s 
                AND dsoh.date_confirm BETWEEN '%s' AND '%s'
                AND dsoh.state in ('progress','done','cancelled')
            )aa
            GROUP BY aa.user_id
        """ %(branch_id,user_id,self.start_date,self.end_date)

        self._cr.execute(query)
        res = self._cr.fetchone()

        cash_ok = 0
        credit_ok = 0
        if res:
            cash_ok = 0 if not res[0] else res[0]
            credit_ok = 0 if not res[1] else res[1]

        query_batal = """
            SELECT sum(aa.cash)cash 
            , sum(aa.credit) credit 
            FROM (
                SELECT dsoh.user_id
                , CASE WHEN dsoh.finco_id IS NULL THEN 1 ELSE 0 END cash 
                , CASE WHEN dsoh.finco_id IS NOT NULL THEN 1 ELSE 0 END credit
                FROM dealer_sale_order_line dsol
                LEFT JOIN dealer_sale_order dsoh ON dsoh.id = dsol.dealer_sale_order_line_id
                WHERE dsoh.branch_id = %s 
                AND dsoh.user_id = %s 
                AND date(dsoh.cancelled_date + interval '7 hours') BETWEEN '%s' AND '%s'
                AND dsoh.state IN ('cancelled')
            )aa
            GROUP BY aa.user_id
        """ %(branch_id,user_id,self.start_date,self.end_date)

        self._cr.execute(query_batal)
        res_batal = self._cr.fetchone()
    
        cash_batal = 0
        credit_batal = 0
        if res_batal:
            cash_batal = 0 if not res_batal[0] else res_batal[0]
            credit_batal = 0 if not res_batal[1] else res_batal[1]

        cash = cash_ok - cash_batal
        credit = credit_ok - credit_batal
        total_unit = cash + credit

        if total_unit == 0:
            raise Warning('Tidak ada penjualan pada periode tersebut !')

        rp_listing = self.env['teds.listing.table.insentif'].search([
            ('name','=',job_name),
            ('total','=',total_unit),
            ('cluster','=',branch_cluster)],limit=1)
        
        listing_cash = rp_listing.cash
        listing_credit = rp_listing.credit
        listing_reward = rp_listing.insentif

        sl = 'SL%'
        # ini juga blm per unit.
        query_ar_cash = """
            SELECT dsoh.user_id
            , count(dsoh.user_id)ar_cash 
            FROM dealer_sale_order dsoh
            LEFT JOIN dealer_sale_order_line dsol ON dsol.dealer_sale_order_line_id = dsoh.id
            LEFT JOIN account_invoice ai ON ai.origin = dsoh.name AND number like '%s'
            WHERE dsoh.state IN ('progress','done') 
            AND dsoh.branch_id = %s 
            AND dsoh.user_id = %s 
            AND dsoh.date_confirm BETWEEN '%s' AND '%s'
            AND ai.state !='paid' 
            AND dsoh.finco_id IS NULL
            GROUP BY dsoh.user_id
        """ %(sl,branch_id,user_id,self.start_date,self.end_date)
        self._cr.execute(query_ar_cash)
        res_ar_cash = self._cr.fetchone()
        
        ar_cash = 0
        if res_ar_cash:
            ar_cash = res_ar_cash[1]

        query_ar_credit = """
            SELECT dsoh.user_id
            , count(dsoh.user_id) ar_credit 
            FROM dealer_sale_order dsoh
            LEFT JOIN dealer_sale_order_line dsol ON dsol.dealer_sale_order_line_id = dsoh.id
            LEFT JOIN account_invoice ai ON ai.origin = dsoh.name AND number like '%s'
            WHERE dsoh.state IN ('progress','done') 
            AND dsoh.branch_id = %s 
            AND dsoh.user_id = %s 
            AND dsoh.date_confirm BETWEEN '%s' AND '%s'
            AND ai.state !='paid' AND dsoh.finco_id IS NOT NULL
            GROUP BY dsoh.user_id
        """ %(sl,branch_id,user_id,self.start_date,self.end_date)
        self._cr.execute(query_ar_credit)
        res_ar_credit = self._cr.fetchone()
    
        ar_credit = 0
        if res_ar_credit:
            ar_credit = res_ar_credit[1]

        query_mediator = """
            SELECT sum(CASE WHEN finco_id IS NULL THEN 1 ELSE 0 end) cash_mediator
            , sum(CASE WHEN finco_id IS NOT NULL THEN 1 ELSE 0 end) credit_mediator
            FROM dealer_sale_order dsoh
            LEFT JOIN dealer_sale_order_line dsol ON dsol.dealer_sale_order_line_id = dsoh.id
            WHERE state IN ('progress', 'done','cancelled') 
            AND dsoh.partner_komisi_id IS NOT NULL 
            AND branch_id = %s 
            AND user_id = %s 
            AND date_confirm BETWEEN '%s' and '%s'
        """ %(branch_id,user_id,self.start_date,self.end_date)

        self._cr.execute(query_mediator)
        res_mediator = self._cr.fetchone()
        
        cash_mediator_ok = 0
        credit_mediator_ok = 0
        if res_mediator:
            cash_mediator_ok = 0 if not res_mediator[0] else res_mediator[0]
            credit_mediator_ok = 0 if not res_mediator[1] else res_mediator[1]

        query_mediator_batal = """
            SELECT sum(CASE WHEN finco_id IS NULL THEN 1 ELSE 0 END) cash_mediator
            , sum(CASE WHEN finco_id IS NOT NULL THEN 1 ELSE 0 END) credit_mediator
            FROM dealer_sale_order dsoh
            LEFT JOIN dealer_sale_order_line dsol ON dsol.dealer_sale_order_line_id = dsoh.id
            WHERE state IN ('cancelled') 
            AND dsoh.partner_komisi_id IS NOT NULL 
            AND branch_id = %s 
            AND user_id = %s 
            AND date(dsoh.cancelled_date + interval '7 hours') BETWEEN '%s' AND '%s'
        """ %(branch_id,user_id,self.start_date,self.end_date)

        self._cr.execute(query_mediator_batal)
        res_mediator_batal = self._cr.fetchone()
    
        cash_mediator_batal = 0
        credit_mediator_batal = 0
        if res_mediator_batal:
            cash_mediator_batal = 0 if not res_mediator_batal[0] else res_mediator_batal[0]
            credit_mediator_batal = 0 if not res_mediator_batal[1] else res_mediator_batal[1]

        cash_mediator = cash_mediator_ok - cash_mediator_batal
        credit_mediator =  credit_mediator_ok - credit_mediator_batal
        cash_nomed = cash - cash_mediator
        credit_nomed = credit - credit_mediator
        total_unit_mediator = (cash_mediator_ok - cash_mediator_batal) + (credit_mediator_ok - credit_mediator_batal)

        rupiah_unit_cash = cash_nomed * listing_cash 
        rupiah_unit_credit = credit_nomed * listing_credit
        rupiah_total_unit = rupiah_unit_cash + rupiah_unit_credit
        insentif_reward = listing_reward
        rupiah_unit_ar_cash = ar_cash * listing_cash
        rupiah_unit_ar_credit = ar_credit * listing_credit
        total_insentif = rupiah_unit_cash + rupiah_unit_credit + insentif_reward - (rupiah_unit_ar_cash + rupiah_unit_ar_credit)
        
        self.unit_cash = cash
        self.rupiah_unit_cash = rupiah_unit_cash
        self.unit_credit = credit
        self.rupiah_unit_credit = rupiah_unit_credit
        self.total_unit = total_unit
        self.rupiah_total_unit = rupiah_total_unit
        self.unit_ar_cash = ar_cash
        self.rupiah_unit_ar_cash = rupiah_unit_ar_cash
        self.unit_ar_credit = ar_credit
        self.rupiah_unit_ar_credit = rupiah_unit_ar_credit 
        self.reward = total_unit
        self.rupiah_reward = insentif_reward
        self.mediator_cash = cash_mediator
        self.mediator_credit = credit_mediator
        self.total_unit_mediator = total_unit_mediator
        self.jml_insentif = total_insentif
        
        if total_insentif == 0:
            raise Warning('Total penjualan %s, tidak mencukupi quota perhitungan' %(total_unit))
        

    @api.multi
    def salesPartner(self):
        branch_id = self.branch_id.id
        branch_cluster = self.branch_id.cluster
        user_id = self.employee_id.resource_id.user_id.id
        job_name = self.job_name.upper()
        
        ar_cash = 0
        rupiah_unit_ar_cash = 0
        ar_credit = 0
        rupiah_unit_ar_credit = 0

        query = """
            SELECT sum(aa.cash)cash 
            , sum(aa.credit) credit 
            FROM (
                SELECT dsoh.user_id
                , CASE WHEN dsoh.finco_id IS NULL THEN 1 ELSE 0 END cash 
                , CASE WHEN dsoh.finco_id IS NOT NULL THEN 1 ELSE 0 END credit
                FROM dealer_sale_order_line dsol
                LEFT JOIN dealer_sale_order dsoh ON dsoh.id = dsol.dealer_sale_order_line_id
                WHERE dsoh.branch_id = %s 
                AND dsoh.user_id = %s 
                AND dsoh.date_confirm BETWEEN '%s' AND '%s'
                AND dsoh.state IN ('progress','done','cancelled')
            )aa
            GROUP BY aa.user_id
        """ %(branch_id,user_id,self.start_date,self.end_date)

        self._cr.execute(query)
        res = self._cr.fetchone()

        cash_ok = 0
        credit_ok = 0
        if res:
            cash_ok = 0 if not res[0] else res[0]
            credit_ok = 0 if not res[1] else res[1]

        query_batal = """
            SELECT sum(aa.cash)cash 
            , sum(aa.credit) credit 
            FROM (
                SELECT dsoh.user_id
                , CASE WHEN dsoh.finco_id IS NULL THEN 1 ELSE 0 END cash 
                , CASE WHEN dsoh.finco_id IS NOT NULL THEN 1 ELSE 0 END credit
                FROM dealer_sale_order_line dsol
                LEFT JOIN dealer_sale_order dsoh ON dsoh.id = dsol.dealer_sale_order_line_id
                WHERE dsoh.branch_id = %s 
                AND dsoh.user_id = %s 
                AND date(dsoh.cancelled_date + interval '7 hours') BETWEEN '%s' AND '%s'
                AND dsoh.state IN ('cancelled')
            )aa
            GROUP BY aa.user_id
        """ %(branch_id,user_id,self.start_date,self.end_date)

        self._cr.execute(query_batal)
        res_batal = self._cr.fetchone()
  
        cash_batal = 0
        credit_batal = 0
        if res_batal:
            cash_batal = 0 if not res_batal[0] else res_batal[0]
            credit_batal = 0 if not res_batal[1] else res_batal[1]

        cash = cash_ok - cash_batal
        credit = credit_ok - credit_batal
        total_unit = cash + credit

        if total_unit == 0:
            raise Warning('Tidak ada penjualan pada periode tersebut !')

        rupiah_unit_cash = self.env['teds.listing.table.insentif'].search([
            ('name','=','SALESMAN PARTNER'),
            ('type_insentif','=','cash_credit'),
            ('total','=',total_unit)],limit=1).akumulasi
        rupiah_unit_credit = self.env['teds.listing.table.insentif'].search([
            ('name','=','SALESMAN PARTNER'),
            ('type_insentif','=','unit_credit_ke'),
            ('total','=',credit)],limit=1).akumulasi

        query_mediator = """
            SELECT sum(CASE WHEN finco_id IS NULL THEN 1 ELSE 0 END) cash_mediator
            , sum(CASE WHEN finco_id IS NOT NULL THEN 1 ELSE 0 END) credit_mediator
            FROM dealer_sale_order dsoh
            LEFT JOIN dealer_sale_order_line dsol ON dsol.dealer_sale_order_line_id = dsoh.id
            WHERE state IN ('progress', 'done','cancelled') 
            AND dsoh.partner_komisi_id IS NOT NULL 
            AND branch_id = %s 
            AND user_id = %s 
            AND date_confirm BETWEEN '%s' AND '%s'
        """ %(branch_id,user_id,self.start_date,self.end_date)

        self._cr.execute(query_mediator)
        res_mediator = self._cr.fetchone()
    
        cash_mediator_ok = 0
        credit_mediator_ok = 0
        if res_mediator:
            cash_mediator_ok = 0 if not res_mediator[0] else res_mediator[0]
            credit_mediator_ok = 0 if not res_mediator[1] else res_mediator[1]

        query_mediator_batal = """
            SELECT sum(CASE WHEN finco_id IS NULL THEN 1 ELSE 0 END) cash_mediator
            , sum(CASE WHEN finco_id IS NOT NULL THEN 1 ELSE 0 END) credit_mediator
            FROM dealer_sale_order dsoh
            LEFT JOIN dealer_sale_order_line dsol ON dsol.dealer_sale_order_line_id = dsoh.id
            WHERE state IN ('cancelled') 
            AND dsoh.partner_komisi_id IS NOT NULL 
            AND branch_id = %s 
            AND user_id = %s 
            AND date(dsoh.cancelled_date + interval '7 hours') BETWEEN '%s' AND '%s'
        """ %(branch_id,user_id,self.start_date,self.end_date)

        self._cr.execute(query_mediator_batal)
        res_mediator_batal = self._cr.fetchone()
        
        cash_mediator_batal = 0
        credit_mediator_batal = 0
        if res_mediator_batal:
            cash_mediator_batal = 0 if not res_mediator_batal[0] else res_mediator_batal[0]
            credit_mediator_batal = 0 if not res_mediator_batal[1] else res_mediator_batal[1]
        
        cash_mediator = cash_mediator_ok - cash_mediator_batal
        credit_mediator = credit_mediator_ok - credit_mediator_batal

        total_unit_mediator = cash_mediator + credit_mediator
        persen_mediator = float(total_unit_mediator) / total_unit
        persen_credit = float(credit) / total_unit

        reward = self.env['teds.listing.table.insentif'].search([
            ('name','=','SALESMAN PARTNER'),
            ('type_insentif','=','reward'),
            ('total','=',total_unit)],limit=1).insentif

        rupiah_total_unit = rupiah_unit_cash + rupiah_unit_credit
        rupiah_persen_credit = reward * persen_credit
        rupiah_persen_mediator = rupiah_persen_credit * persen_mediator
        rupiah_absensi = rupiah_persen_credit - rupiah_persen_mediator
        rupiah_reward = rupiah_absensi
        total_insentif = rupiah_unit_cash + rupiah_unit_credit + rupiah_reward

        self.unit_cash = cash
        self.rupiah_unit_cash = rupiah_unit_cash
        self.unit_credit = credit
        self.rupiah_unit_credit = rupiah_unit_credit
        self.total_unit = total_unit
        self.rupiah_total_unit = rupiah_total_unit
        self.unit_ar_cash = ar_cash
        self.rupiah_unit_ar_cash = rupiah_unit_ar_cash
        self.unit_ar_credit = ar_credit
        self.rupiah_unit_ar_credit = rupiah_unit_ar_credit 
        self.reward = total_unit
        self.rupiah_reward = rupiah_reward
        self.mediator_cash = cash_mediator
        self.mediator_credit = credit_mediator
        self.total_unit_mediator = total_unit_mediator
        self.rupiah_persen_mediator = rupiah_persen_mediator
        self.rupiah_persen_absensi = rupiah_absensi
        self.jml_insentif = total_insentif
        
        if total_insentif == 0:
            raise Warning('Total penjualan %s, tidak mencukupi quota perhitungan' %(total_unit))


    @api.multi
    def koordinatorSalesman(self):
        branch_id = self.branch_id.id
        branch_cluster = self.branch_id.cluster
        user_id = self.employee_id.resource_id.user_id.id
        job_name = self.job_name.upper()
        
        query = """
            SELECT aa.user_id
            , sum(aa.cash)cash 
            , sum(aa.credit) credit 
            FROM (
                SELECT dsoh.user_id
                , CASE WHEN dsoh.finco_id IS NULL THEN 1 ELSE 0 END cash 
                , CASE WHEN dsoh.finco_id IS NOT NULL THEN 1 ELSE 0 END credit
                FROM dealer_sale_order_line dsol
                LEFT JOIN dealer_sale_order dsoh ON dsoh.id = dsol.dealer_sale_order_line_id
                WHERE dsoh.branch_id = %s 
                AND (dsoh.user_id = %s OR dsoh.sales_koordinator_id = %s) 
                AND dsoh.date_confirm BETWEEN '%s' AND '%s'
                AND dsoh.state IN ('progress','done','cancelled')
            )aa
            GROUP BY aa.user_id
        """ %(branch_id,user_id,user_id,self.start_date,self.end_date)
     
        self._cr.execute(query)
        res_jml = self._cr.fetchall()
        cash_ok= 0
        credit_ok = 0

        cash_ok = 0
        credit_ok = 0
        if res_jml:
            for res in res_jml:
                cash_ok += res[1]
                credit_ok += res[2]

        query_cancel = """
            SELECT aa.user_id
            , sum(aa.cash)cash 
            , sum(aa.credit) credit 
            FROM (
                SELECT dsoh.user_id
                , CASE WHEN dsoh.finco_id IS NULL THEN 1 ELSE 0 END cash 
                , CASE WHEN dsoh.finco_id IS NOT NULL THEN 1 ELSE 0 END credit
                FROM dealer_sale_order_line dsol
                LEFT JOIN dealer_sale_order dsoh ON dsoh.id = dsol.dealer_sale_order_line_id
                WHERE dsoh.branch_id = %s 
                AND (dsoh.user_id = %s OR dsoh.sales_koordinator_id = %s) 
                AND date(dsoh.cancelled_date + interval '7 hours') BETWEEN '%s' AND '%s'
                AND dsoh.state IN ('cancelled')
            )aa
            GROUP BY aa.user_id
        """ %(branch_id,user_id,user_id,self.start_date,self.end_date)

        self._cr.execute(query_cancel)
        res_cancel = self._cr.fetchall()
        
        cash_cancel = 0
        credit_cancel = 0
        if res_cancel:
            for cnc in res_cancel:
                cash_cancel += cnc[1]
                credit_cancel += cnc[2]

        cash = cash_ok - cash_cancel
        credit = credit_ok - credit_cancel

        total_unit = cash + credit

        if total_unit == 0:
            raise osv.except_osv('Tidak ada penjualan pada periode tersebut !')

        rupiah_unit_cash = self.env['teds.listing.table.insentif'].search([
            ('name','=','KOORDINATOR SALESMAN'),
            ('type_insentif','=','cash_credit'),
            ('total','=',total_unit)],limit=1).akumulasi
        rupiah_unit_credit = self.env['teds.listing.table.insentif'].search([
            ('name','=','KOORDINATOR SALESMAN'),
            ('type_insentif','=','unit_credit_ke'),
            ('total','=',credit)],limit=1).akumulasi
        listing_reward = self.env['teds.listing.table.insentif'].search([
            ('name','=','KOORDINATOR SALESMAN'),
            ('type_insentif','=','reward'),
            ('total','=',total_unit)],limit=1).insentif

        rupiah_unit_cash = 0 if not rupiah_unit_cash else rupiah_unit_cash
        rupiah_unit_credit = 0 if not rupiah_unit_credit else rupiah_unit_credit

        bawahan = """
            SELECT count(DISTINCT(user_id)) jml
            FROM dealer_sale_order 
            WHERE state IN ('progress', 'done','cancelled') 
            AND branch_id = %s 
            AND date_confirm BETWEEN '%s' AND '%s'  
            AND sales_koordinator_id = %s 
            AND user_id != %s       
        """%(branch_id,self.start_date,self.end_date,user_id,user_id)
        self._cr.execute(bawahan)
        jml_bawahan = self._cr.fetchone()[0] 

        produktivitas = 0
        if jml_bawahan > 0:
            produktivitas = round(total_unit / jml_bawahan) if total_unit else 0
        
        reward1 = 0
        if jml_bawahan >=10:
            reward1 = listing_reward * 0.5
        
        reward2 = 0
        if produktivitas >= 8:
            reward2 = listing_reward * 0.5
    
        rupiah_reward = reward1 + reward2

        rupiah_total_unit = rupiah_unit_cash + rupiah_unit_credit
        total_insentif = rupiah_unit_cash + rupiah_unit_credit + rupiah_reward


        self.unit_cash = cash
        self.rupiah_unit_cash = rupiah_unit_cash
        self.unit_credit = credit
        self.rupiah_unit_credit = rupiah_unit_credit
        self.total_unit = total_unit
        self.rupiah_total_unit = rupiah_total_unit
        self.reward = total_unit
        self.rupiah_reward = rupiah_reward
        self.jml_bawahan = jml_bawahan
        self.produktivitas = produktivitas
        self.jml_insentif = total_insentif
        
        if total_unit == 0:
            raise Warning('Tidak ada penjualan pada periode tersebut !')
        
        if total_insentif == 0:
            raise Warning('Total penjualan %s, tidak mencukupi quota perhitungan' %(total_unit))


    @api.multi
    def soh(self):      
        branch_id = self.branch_id.id
        branch_cluster = self.branch_id.cluster
        user_id = self.employee_id.resource_id.user_id.id
        job_name = self.job_name.upper()
        
        query = """
            SELECT sum(aa.cash)cash ,sum(aa.credit) credit 
            FROM (
                SELECT dsoh.user_id
                , CASE WHEN dsoh.finco_id IS NULL THEN 1 ELSE 0 END cash 
                , CASE WHEN dsoh.finco_id IS NOT NULL THEN 1 ELSE 0 END credit
                FROM dealer_sale_order_line dsol
                LEFT JOIN dealer_sale_order dsoh ON dsoh.id = dsol.dealer_sale_order_line_id
                WHERE dsoh.branch_id = %s 
                AND dsoh.date_confirm BETWEEN '%s' AND '%s'
                AND dsoh.state IN ('progress','done','cancelled')
            )aa
        """ %(branch_id,self.start_date,self.end_date)
            
        self._cr.execute(query)
        res = self._cr.fetchone()

        cash_ok = 0
        credit_ok = 0
        if res:
            cash_ok = 0 if not res[0] else res[0]
            credit_ok = 0 if not res[1] else res[1]
        
        query_batal = """
            SELECT sum(aa.cash)cash 
            , sum(aa.credit) credit 
            FROM (
                SELECT dsoh.user_id
                , CASE WHEN dsoh.finco_id IS NULL THEN 1 ELSE 0 END cash 
                , CASE WHEN dsoh.finco_id IS NOT NULL THEN 1 ELSE 0 END credit
                FROM dealer_sale_order_line dsol
                LEFT JOIN dealer_sale_order dsoh ON dsoh.id = dsol.dealer_sale_order_line_id
                WHERE dsoh.branch_id = %s 
                AND date(dsoh.cancelled_date + interval '7 hours') BETWEEN '%s' AND '%s'
                AND dsoh.state IN ('cancelled')
            )aa
        """ %(branch_id,self.start_date,self.end_date)

        self._cr.execute(query_batal)
        res_batal = self._cr.fetchone()

        cash_batal = 0
        credit_batal = 0
        if res_batal:
            cash_batal = 0 if not res_batal[0] else res_batal[0]
            credit_batal = 0 if not res_batal[1] else res_batal[1]


        cash = cash_ok - cash_batal
        credit = credit_ok - credit_batal
        total_unit = cash + credit 

        if total_unit == 0:
            raise Warning('Tidak ada penjualan pada periode tersebut !')

        rupiah_unit_cash = self.env['teds.listing.table.insentif'].search([
            ('name','=','SOH'),
            ('cluster','=',branch_cluster),
            ('type_insentif','=','cash_credit'),
            ('total','=',total_unit)],limit=1).insentif
        rupiah_unit_credit = self.env['teds.listing.table.insentif'].search([
            ('name','=','SOH'),
            ('cluster','=',branch_cluster),
            ('type_insentif','=','unit_credit_ke'),
            ('total','=',credit)],limit=1).insentif
        rupiah_kelas_cabang = self.env['teds.listing.table.insentif'].search([
            ('name','=','SOH'),
            ('cluster','=',branch_cluster),
            ('type_insentif','=','reward'),
            ('total','=',total_unit)],limit=1).insentif
        total_insentif = rupiah_unit_cash + rupiah_unit_credit + rupiah_kelas_cabang

        self.unit_cash = cash
        self.rupiah_unit_cash = rupiah_unit_cash
        self.unit_credit = credit
        self.rupiah_unit_credit = rupiah_unit_credit
        self.total_unit = total_unit
        self.jml_insentif = total_insentif

        if total_insentif == 0:
            raise osv.except_osv('Total penjualan %s, tidak mencukupi quota perhitungan' %(total_unit))