from openerp import models, fields, api
import openerp.http as http
from openerp.http import request
import time
from datetime import datetime
import itertools
from lxml import etree
from openerp import models,fields, exceptions, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp.osv import osv

class hitungInsentifJson(http.Controller):
    @http.route('/web/webview/hitunginsentif', type='json', auth='user', methods=['POST'])
    def hitungInsentif(self, branch_id, emp_id, start_date, end_date):
        return request.env['teds.hitung.insentif'].hitungInsentifJson(int(branch_id), int(emp_id), start_date, end_date)
        return hi.hitungInsentif()
        return "Hello %d" % (emp_id)

class hitungInsentif(models.Model):
    _name = 'teds.hitung.insentif'
    _description = 'Hitung Insentif'


    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 

    def _get_default_date(self,cr,uid,context):
        return str(self.pool.get('wtc.branch').get_default_date_model(cr,uid,context=context))
        # return tgl[:-25]

    # @api.onchange('branch_id')
    def branch_id_on_change(self):
        if self.branch_id:
            self.name=False
            if not self.branch_id.cluster:
                self.branch_id = False
                warning = {'title': 'Error', 'message':'Bracnh cluster masih kosong, setting dahulu di master Branch'}
                return {'warning':warning}

    # @api.onchange('name')
    def name_on_change(self):
        self.start_date = False
        self.end_date = False
        self.job_name = self.name.job_id.name
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
        self.rupiah_persen_mediator =  False
        self.rupiah_persen_absensi = False
        self.jml_bawahan = False
        self.produktivitas = False
        self.jml_insentif = False

    # @api.onchange('start_date')
    def start_date_on_change(self):
        if self.start_date and self.end_date:
            # qudate ="""
            #         select date(date_trunc('month', date('%s')))start_date, date(date_trunc('month',date('%s'))+'1month'::interval-'1day'::interval)end_date;
            #         """%(self.start_date,self.start_date)
            # self._cr.execute(qudate)
            # tgl = self._cr.fetchall()[0]

            # # self.start_date = tgl[0]
            # # self.end_date = tgl[1]     
            self.hitungInsentif()

    # @api.onchange('end_date')
    def end_date_on_change(self):
        if self.end_date and self.start_date:
            self.hitungInsentif()
            # qudate ="""
            #         select date(date_trunc('month', date('%s')))start_date, date(date_trunc('month',date('%s'))+'1month'::interval-'1day'::interval)end_date;
            #         """%(self.end_date,self.end_date)
            # self._cr.execute(qudate)
            # tgl = self._cr.fetchall()[0]

            # self.start_date = tgl[0]
            # self.end_date = tgl[1]     

    @api.multi
    def hitungInsentifJson(self, branch_id, emp_id, start_date, end_date):
        return self.onchange_hitung_insentif(branch_id, emp_id, start_date, end_date)

    @api.multi
    def onchange_hitung_insentif(self, branch_id, name, start_date, end_date):
        if branch_id and name and start_date and end_date:
            unit_cash = 0
            rupiah_unit_cash = 0
            unit_credit = 0
            rupiah_unit_credit = 0
            total_unit = 0
            rupiah_total_unit = 0
            unit_ar_cash = 0
            ar_cash = 0
            rupiah_unit_ar_cash = 0
            unit_ar_credit = 0
            ar_credit = 0
            rupiah_unit_ar_credit = 0
            reward = 0
            rupiah_reward = 0
            mediator = 0
            rupiah_persen_credit = 0
            rupiah_persen_mediator = 0
            rupiah_persen_absensi = 0
            jml_insentif = 0
            jml_bawahan = 0
            produktivitas = 0
            # cash = 0
            # credit = 0
            # listing_cash = 0
            # listing_credit = 0
            # insentif_cash = 0
            # insentif_credit = 0
            # insentif_ar_cash = 0
            # insentif_ar_credit = 0

            branch_cluster = self.env['wtc.branch'].browse(branch_id).cluster
            emp = self.env['hr.employee'].browse(name)
            user_id = emp.resource_id.user_id.id
            job_name = emp.job_id.name

            return {'value': self.insentifCalculation(branch_id, branch_cluster, user_id, job_name, start_date, end_date)}

            # if job_name == 'SALES COUNTER':
            #     return {'value':self.salesCounter(branch_id, branch_cluster, user_id, job_name,start_date,end_date)}
            # if job_name == 'SALESMAN TETAP' or job_name == 'SALES PAYROLL' or job_name == 'SALESMAN KONTRAK':
            #     return {'value':self.salesPayroll(branch_id, branch_cluster, user_id, job_name,start_date,end_date)}
            # if job_name == 'SALESMAN PARTNER':
            #     return {'value':self.salesPartner(branch_id, branch_cluster, user_id, job_name,start_date,end_date)}
            # if job_name == "KOORDINATOR SALESMAN":
            #     return {'value':self.koordinatorSalesman(branch_id, branch_cluster, user_id, job_name,start_date,end_date)}
            # if job_name == 'SOH':
            # 	return {'value':self.soh(branch_id, branch_cluster, user_id, job_name,start_date,end_date)}

    def insentifCalculation(self, branch_id, branch_cluster, user_id, job_name, start_date, end_date):
        sko_id = -1
        is_soh = 0
        if job_name == 'KOORDINATOR SALESMAN':
            sko_id = user_id
        elif job_name == 'SOH':
            is_soh = 1

        query = """
            SELECT user_id
                , sum(cash_qty) as cash_qty
                , sum(credit_qty) as credit_qty
                , sum(cash_mediator) as cash_mediator
                , sum(credit_mediator) as credit_mediator
                from (
                    SELECT dsoh.user_id
                        , dsoh.branch_id
                        , case when dsoh.finco_id is null then 1 else 0 end cash_qty
                        , case when dsoh.finco_id is not null then 1 else 0 end credit_qty
                        , case when dsoh.partner_komisi_id is not null and dsoh.finco_id is null then 1 else 0 end cash_mediator
                        , case when dsoh.partner_komisi_id is not null and dsoh.finco_id is not null then 1 else 0 end credit_mediator
                    FROM dealer_sale_order dsoh
                    INNER JOIN dealer_sale_order_line dsol ON dsoh.id=dsol.dealer_sale_order_line_id
                    WHERE dsoh.branch_id=%s
                        AND (dsoh.user_id=%s or dsoh.sales_koordinator_id = %s or 1=%s)
                        AND dsoh.date_confirm BETWEEN '%s' AND '%s'
                        AND dsoh.state IN ('progress','done','cancelled')
                UNION ALL
                    SELECT dsoh.user_id
                        , dsoh.branch_id
                        , case when dsoh.finco_id is null then -1 else 0 end cash_qty
                        , case when dsoh.finco_id is not null then -1 else 0 end credit_qty
                        , case when dsoh.partner_komisi_id is not null and dsoh.finco_id is null then -1 else 0 end cash_mediator
                        , case when dsoh.partner_komisi_id is not null and dsoh.finco_id is not null then -1 else 0 end credit_mediator
                    FROM dealer_sale_order dsoh
                    INNER JOIN dealer_sale_order_line dsol ON dsoh.id=dsol.dealer_sale_order_line_id
                    WHERE dsoh.branch_id=%s
                        AND (dsoh.user_id=%s or dsoh.sales_koordinator_id = %s or 1=%s)
                        AND date(dsoh.cancelled_date + interval '7 hours') BETWEEN '%s' AND '%s'
                        AND dsoh.state IN ('cancelled')
                ) sum_table
                GROUP BY user_id
            """ % (branch_id, user_id, sko_id, is_soh, start_date, end_date, branch_id, user_id, sko_id, is_soh, start_date, end_date)
        self._cr.execute(query)
        res = self._cr.fetchone()

        if res:
            cash = 0 if not res[1] else res[1]
            credit = 0 if not res[2] else res[2]
            cash_mediator = 0 if not res[3] else res[3]
            credit_mediator = 0 if not res[4] else res[4]
        else:
            cash = 0
            credit = 0
            cash_mediator = 0
            credit_mediator = 0

        total_unit = cash + credit
        cash_nomed = cash - cash_mediator
        credit_nomed = credit - credit_mediator
        total_unit_mediator = cash_mediator + credit_mediator

        if total_unit == 0:
            raise osv.except_osv(('Perhatian!'), ('Tidak ada penjualan dibulan tersebut'))

        ar_cash = 0
        ar_credit = 0
        if job_name != 'SALESMAN PARTNER':
            query_ar = """
                SELECT dsoh.user_id
                    , SUM(CASE WHEN dsoh.finco_id IS NULL THEN 1 ELSE 0 END) ar_cash
                    , SUM(CASE WHEN dsoh.finco_id IS NOT NULL THEN 1 ELSE 0 END) ar_credit
                FROM dealer_sale_order dsoh
                LEFT JOIN dealer_sale_order_line dsol on dsol.dealer_sale_order_line_id=dsoh.id
                LEFT JOIN account_invoice ai ON ai.transaction_id=dsoh.id AND ai.model_id IN (SELECT id FROM ir_model WHERE model = 'dealer.sale.order') AND ((tipe = 'customer' AND dsoh.finco_id IS NULL) OR (tipe = 'finco' AND dsoh.finco_id IS NOT NULL))
                WHERE dsoh.state IN ('progress','done','cancelled') 
                    AND dsoh.branch_id=%s
                    AND dsoh.user_id=%s
                    AND dsoh.date_confirm BETWEEN '%s' AND '%s'
                    AND ai.state !='paid' 
                GROUP BY dsoh.user_id
                """ % (branch_id, user_id, start_date, end_date)
            self._cr.execute(query_ar)
            res = self._cr.fetchone()
            if res:
                ar_cash = 0 if not res[1] else res[1]
                ar_credit = 0 if not res[2] else res[2]

        # default value
        listing_cash = 0
        listing_credit = 0
        rupiah_persen_mediator = 0
        jml_bawahan = 0
        produktivitas = 0

        if job_name == 'SALES COUNTER':
            rp_listing = self.env['teds.listing.table.insentif'].search([('name','=',job_name),('total','=',total_unit)])
            listing_cash = rp_listing.cash
            listing_credit = rp_listing.credit
            listing_reward = 0

            rupiah_unit_cash = cash_nomed * listing_cash
            rupiah_unit_credit = credit_nomed * listing_credit
        elif job_name == 'SALESMAN TETAP' or job_name == 'SALES PAYROLL' or job_name == 'SALESMAN KONTRAK':
            rp_listing = self.env['teds.listing.table.insentif'].search([('name','=',job_name),('total','=',total_unit),('cluster','=',branch_cluster)])
            listing_cash = rp_listing.cash
            listing_credit = rp_listing.credit
            listing_reward = rp_listing.insentif

            rupiah_unit_cash = cash_nomed * listing_cash 
            rupiah_unit_credit = credit_nomed * listing_credit
        elif job_name == 'SALESMAN PARTNER':
            rupiah_unit_cash = self.env['teds.listing.table.insentif'].search([('name','=','SALESMAN PARTNER'),('type_insentif','=','cash_credit'),('total','=',total_unit)]).akumulasi
            rupiah_unit_credit = self.env['teds.listing.table.insentif'].search([('name','=','SALESMAN PARTNER'),('type_insentif','=','unit_credit_ke'),('total','=',credit)]).akumulasi

            persen_mediator = float(total_unit_mediator) / total_unit
            persen_credit = float(credit) / total_unit

            reward = self.env['teds.listing.table.insentif'].search([('name','=','SALESMAN PARTNER'),('type_insentif','=','reward'),('total','=',total_unit)]).insentif

            rupiah_persen_credit = reward * persen_credit
            rupiah_persen_mediator = rupiah_persen_credit * persen_mediator
            listing_reward = rupiah_persen_credit - rupiah_persen_mediator
        elif job_name == "KOORDINATOR SALESMAN":
            rupiah_unit_cash = self.env['teds.listing.table.insentif'].search([('name','=','KOORDINATOR SALESMAN'),('type_insentif','=','cash_credit'),('total','=',total_unit)]).akumulasi
            rupiah_unit_credit = self.env['teds.listing.table.insentif'].search([('name','=','KOORDINATOR SALESMAN'),('type_insentif','=','unit_credit_ke'),('total','=',credit)]).akumulasi
            listing_reward = self.env['teds.listing.table.insentif'].search([('name','=','KOORDINATOR SALESMAN'),('type_insentif','=','reward'),('total','=',total_unit)]).insentif

            rupiah_unit_cash = 0 if not rupiah_unit_cash else rupiah_unit_cash
            rupiah_unit_credit = 0 if not rupiah_unit_credit else rupiah_unit_credit

            bawahan = """
                select count(DISTINCT(user_id)) jml
                from dealer_sale_order where state in ('progress', 'done','cancelled') and branch_id=%s and 
                date_confirm between '%s' and '%s'  and sales_koordinator_id = %s and user_id != %s
                """%(branch_id,start_date,end_date,user_id,user_id)
            self._cr.execute(bawahan)
            jml_bawahan = self._cr.fetchone()[0] 

            produktivitas = 0
            if jml_bawahan > 0:
                produktivitas = round(total_unit / jml_bawahan) if total_unit else 0
            else:
                produktivitas = 0

            if jml_bawahan >=10:
                reward1 = listing_reward * 0.5
            else:
                reward1 = 0

            if produktivitas >= 8:
                reward2 = listing_reward * 0.5
            else:
                reward2 = 0

            listing_reward = reward1 + reward2
        elif job_name == "SOH":
            rupiah_unit_cash = self.env['teds.listing.table.insentif'].search([('name','=','SOH'),('cluster','=',branch_cluster),('type_insentif','=','cash_credit'),('total','=',total_unit)]).insentif
            rupiah_unit_credit = self.env['teds.listing.table.insentif'].search([('name','=','SOH'),('cluster','=',branch_cluster),('type_insentif','=','unit_credit_ke'),('total','=',credit)]).insentif
            listing_reward = self.env['teds.listing.table.insentif'].search([('name','=','SOH'),('cluster','=',branch_cluster),('type_insentif','=','reward'),('total','=',total_unit)]).insentif

        rupiah_total_unit = rupiah_unit_cash + rupiah_unit_credit
        insentif_reward = listing_reward
        rupiah_unit_ar_cash = ar_cash * listing_cash
        rupiah_unit_ar_credit = ar_credit * listing_credit
        total_insentif = rupiah_unit_cash + rupiah_unit_credit + insentif_reward - (rupiah_unit_ar_cash + rupiah_unit_ar_credit)

        hasil = {
            'unit_cash': cash,
            'rupiah_unit_cash': rupiah_unit_cash,
            'unit_credit': credit,
            'rupiah_unit_credit': rupiah_unit_credit,
            'total_unit': total_unit,
            'rupiah_total_unit': rupiah_total_unit,
            'unit_ar_cash': ar_cash,
            'rupiah_unit_ar_cash': rupiah_unit_ar_cash,
            'unit_ar_credit': ar_credit,
            'rupiah_unit_ar_credit': rupiah_unit_ar_credit ,
            'mediator_cash': cash_mediator,
            'mediator_credit': credit_mediator,
            'total_unit_mediator': total_unit_mediator,
            'reward': total_unit,
            'rupiah_reward': insentif_reward,
            'jml_insentif': total_insentif,
            # partner
            'rupiah_persen_mediator': rupiah_persen_mediator,
            'rupiah_persen_absensi': insentif_reward,
            # sales koordinator
            'jml_bawahan': jml_bawahan,
            'produktivitas': produktivitas,
        }

        if total_insentif == 0:
            raise osv.except_osv(('Perhatian!'), ('Total penjualan %s, tidak mencukupi quota perhitungan')%(total_unit))
        return hasil

    def salesPayroll(self, branch_id, branch_cluster, user_id, job_name,start_date,end_date):
        query = """
                select sum(aa.cash)cash ,sum(aa.credit) credit from
                (select 
                dsoh.user_id,case when dsoh.finco_id is null then 1 else 0 end cash 
                ,case when dsoh.finco_id is not null then 1 else 0 end credit
                from dealer_sale_order_line dsol
                LEFT JOIN dealer_sale_order dsoh on dsoh.id=dsol.dealer_sale_order_line_id
                WHERE dsoh.branch_id=%s and dsoh.user_id=%s and dsoh.date_confirm between '%s' and '%s'
                and dsoh.state in('progress','done','cancelled'))aa
                group by aa.user_id
                """ %(branch_id,user_id,self.start_date,self.end_date)

        self._cr.execute(query)
        res = self._cr.fetchone()

        if res:
            cash_ok = 0 if not res[0] else res[0]
            credit_ok = 0 if not res[1] else res[1]
        else:
            cash_ok = 0
            credit_ok = 0

        query_batal = """
                select sum(aa.cash)cash ,sum(aa.credit) credit from
                (select 
                dsoh.user_id,case when dsoh.finco_id is null then 1 else 0 end cash 
                ,case when dsoh.finco_id is not null then 1 else 0 end credit
                from dealer_sale_order_line dsol
                LEFT JOIN dealer_sale_order dsoh on dsoh.id=dsol.dealer_sale_order_line_id
                WHERE dsoh.branch_id=%s and dsoh.user_id=%s and date(dsoh.cancelled_date + interval '7 hours') between '%s' and '%s'
                and dsoh.state in('cancelled'))aa
                group by aa.user_id
                """ %(branch_id,user_id,self.start_date,self.end_date)

        self._cr.execute(query_batal)
        res_batal = self._cr.fetchone()
        if res_batal:
            cash_batal = 0 if not res_batal[0] else res_batal[0]
            credit_batal = 0 if not res_batal[1] else res_batal[1]
        else:
            cash_batal = 0
            credit_batal = 0

        cash = cash_ok - cash_batal
        credit = credit_ok - credit_batal
        total_unit = cash + credit

        if total_unit == 0:
            raise osv.except_osv(('Perhatian!'), ('Tidak ada penjualan dibulan tersebut'))

        rp_listing = self.env['teds.listing.table.insentif'].search([('name','=',job_name),('total','=',total_unit),('cluster','=',branch_cluster)])
        listing_cash = rp_listing.cash
        listing_credit = rp_listing.credit
        listing_reward = rp_listing.insentif

        sl = 'SL%'
        # ini juga blm per unit.
        query_ar_cash = """
            select dsoh.user_id,count(dsoh.user_id)ar_cash from dealer_sale_order dsoh
            LEFT JOIN dealer_sale_order_line dsol on dsol.dealer_sale_order_line_id=dsoh.id
            LEFT JOIN account_invoice ai on ai.origin=dsoh.name and number like '%s'
            where dsoh.state in('progress','done') and dsoh.branch_id=%s 
            and dsoh.user_id=%s and dsoh.date_confirm between '%s' and '%s'
            and ai.state !='paid' and dsoh.finco_id is null
            GROUP BY dsoh.user_id
                """ %(sl,branch_id,user_id,self.start_date,self.end_date)
        self._cr.execute(query_ar_cash)
        res_ar_cash = self._cr.fetchone()
        if res_ar_cash:
            ar_cash = res_ar_cash[1]
        else:
            ar_cash = 0

        query_ar_credit = """
            select dsoh.user_id,count(dsoh.user_id)ar_credit from dealer_sale_order dsoh
            LEFT JOIN dealer_sale_order_line dsol on dsol.dealer_sale_order_line_id=dsoh.id
            LEFT JOIN account_invoice ai on ai.origin=dsoh.name and number like '%s'
            where dsoh.state in('progress','done') and dsoh.branch_id=%s 
            and dsoh.user_id=%s and dsoh.date_confirm between '%s' and '%s'
            and ai.state !='paid' and dsoh.finco_id is not null
            GROUP BY dsoh.user_id
                """ %(sl,branch_id,user_id,self.start_date,self.end_date)
        self._cr.execute(query_ar_credit)
        res_ar_credit = self._cr.fetchone()
        if res_ar_credit:
            ar_credit = res_ar_credit[1]
        else:
            ar_credit = 0

        query_mediator = """
            select sum(case when finco_id is null then 1 else 0 end) cash_mediator
            ,sum(case when finco_id is not null then 1 else 0 end) credit_mediator
            from dealer_sale_order dsoh
            LEFT JOIN dealer_sale_order_line dsol on dsol.dealer_sale_order_line_id=dsoh.id
            where state in ('progress', 'done','cancelled') and dsoh.partner_komisi_id is not null 
            and branch_id=%s and user_id=%s and date_confirm between '%s' and '%s'
            """ %(branch_id,user_id,self.start_date,self.end_date)

        self._cr.execute(query_mediator)
        res_mediator = self._cr.fetchone()
        if res_mediator:
            cash_mediator_ok = 0 if not res_mediator[0] else res_mediator[0]
            credit_mediator_ok = 0 if not res_mediator[1] else res_mediator[1]
        else:
            cash_mediator_ok = 0
            credit_mediator_ok = 0

        query_mediator_batal = """
            select sum(case when finco_id is null then 1 else 0 end) cash_mediator
            ,sum(case when finco_id is not null then 1 else 0 end) credit_mediator
            from dealer_sale_order dsoh
            LEFT JOIN dealer_sale_order_line dsol on dsol.dealer_sale_order_line_id=dsoh.id
            where state in ('cancelled') and dsoh.partner_komisi_id is not null 
            and branch_id=%s and user_id=%s and date(dsoh.cancelled_date + interval '7 hours') between '%s' and '%s'
            """ %(branch_id,user_id,self.start_date,self.end_date)

        self._cr.execute(query_mediator_batal)
        res_mediator_batal = self._cr.fetchone()
        if res_mediator_batal:
            cash_mediator_batal = 0 if not res_mediator_batal[0] else res_mediator_batal[0]
            credit_mediator_batal = 0 if not res_mediator_batal[1] else res_mediator_batal[1]
        else:
            cash_mediator_batal = 0
            credit_mediator_batal = 0

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
        # print 'cash_mediator',cash_mediator,'credit_mediator',credit_mediator,res_mediator
        # print 'cash_ok',cash_ok,'credit_ok',credit_ok,'cash_batal',cash_batal,'credit_batal',credit_batal
        # print 'cash',cash,'credit',credit,'total_unit',total_unit,'listing_cash',listing_cash,'listing_credit',listing_credit
        # print 'listing_reward',listing_reward,'ar_cash',ar_cash,'ar_credit',ar_credit,'cash_mediator',cash_mediator,'credit_mediator',credit_mediator
        # print 'cash_nomed',cash_nomed,'credit_nomed',credit_nomed,'total_unit_mediator',total_unit_mediator
        # print 'rupiah_unit_cash = cash_nomed * listing_cash ',rupiah_unit_cash,'rupiah_unit_credit = credit_nomed * listing_credit',rupiah_unit_credit
        # print 'rupiah_total_unit = rupiah_unit_cash + rupiah_unit_credit',rupiah_total_unit
        # print 'insentif_reward = listing_reward',insentif_reward
        # print 'rupiah_unit_ar_cash = ar_cash * listing_cash',rupiah_unit_ar_cash
        # print 'rupiah_unit_ar_credit = ar_credit * listing_credit',rupiah_unit_ar_credit
        # print 'total_insentif = rupiah_unit_cash + rupiah_unit_credit + insentif_reward - (rupiah_unit_ar_cash + rupiah_unit_ar_credit)',total_insentif

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
        # self.jml_bawahan = jml_bawahan
        # self.produktivitas = produktivitas
        self.jml_insentif = total_insentif
        # self.job_name = job_name

        if total_insentif == 0:
            raise osv.except_osv(('Perhatian!'), ('Total penjualan %s, tidak mencukupi quota perhitungan')%(total_unit))
        

    @api.multi
    def salesPartner(self):
        branch_id = self.branch_id.id
        branch_cluster = self.branch_id.cluster
        user_id = self.name.resource_id.user_id.id
        job_name = self.name.job_id.name
        start_date = self.start_date[:-3]+"%"

        ar_cash = 0
        rupiah_unit_ar_cash = 0
        ar_credit = 0
        rupiah_unit_ar_credit = 0

        query = """
                select sum(aa.cash)cash ,sum(aa.credit) credit from
                (select 
                dsoh.user_id,case when dsoh.finco_id is null then 1 else 0 end cash 
                ,case when dsoh.finco_id is not null then 1 else 0 end credit
                from dealer_sale_order_line dsol
                LEFT JOIN dealer_sale_order dsoh on dsoh.id=dsol.dealer_sale_order_line_id
                WHERE dsoh.branch_id=%s and dsoh.user_id=%s and dsoh.date_confirm between '%s' and '%s'
                and dsoh.state in('progress','done','cancelled'))aa
                group by aa.user_id
                """ %(branch_id,user_id,self.start_date,self.end_date)

        self._cr.execute(query)
        res = self._cr.fetchone()

        if res:
            cash_ok = 0 if not res[0] else res[0]
            credit_ok = 0 if not res[1] else res[1]
        else:
            cash_ok = 0
            credit_ok = 0

        query_batal = """
                select sum(aa.cash)cash ,sum(aa.credit) credit from
                (select 
                dsoh.user_id,case when dsoh.finco_id is null then 1 else 0 end cash 
                ,case when dsoh.finco_id is not null then 1 else 0 end credit
                from dealer_sale_order_line dsol
                LEFT JOIN dealer_sale_order dsoh on dsoh.id=dsol.dealer_sale_order_line_id
                WHERE dsoh.branch_id=%s and dsoh.user_id=%s and date(dsoh.cancelled_date + interval '7 hours') between '%s' and '%s'
                and dsoh.state in('cancelled'))aa
                group by aa.user_id
                """ %(branch_id,user_id,self.start_date,self.end_date)

        self._cr.execute(query_batal)
        res_batal = self._cr.fetchone()
        if res_batal:
            cash_batal = 0 if not res_batal[0] else res_batal[0]
            credit_batal = 0 if not res_batal[1] else res_batal[1]
        else:
            cash_batal = 0
            credit_batal = 0

        cash = cash_ok - cash_batal
        credit = credit_ok - credit_batal
        total_unit = cash + credit

        if total_unit == 0:
            raise osv.except_osv(('Perhatian!'), ('Tidak ada penjualan dibulan tersebut'))

        rupiah_unit_cash = self.env['teds.listing.table.insentif'].search([('name','=','SALESMAN PARTNER'),('type_insentif','=','cash_credit'),('total','=',total_unit)]).akumulasi
        rupiah_unit_credit = self.env['teds.listing.table.insentif'].search([('name','=','SALESMAN PARTNER'),('type_insentif','=','unit_credit_ke'),('total','=',credit)]).akumulasi

        query_mediator = """
            select sum(case when finco_id is null then 1 else 0 end) cash_mediator
            ,sum(case when finco_id is not null then 1 else 0 end) credit_mediator
            from dealer_sale_order dsoh
            LEFT JOIN dealer_sale_order_line dsol on dsol.dealer_sale_order_line_id=dsoh.id
            where state in ('progress', 'done','cancelled') and dsoh.partner_komisi_id is not null 
            and branch_id=%s and user_id=%s and date_confirm between '%s' and '%s'
            """ %(branch_id,user_id,self.start_date,self.end_date)

        self._cr.execute(query_mediator)
        res_mediator = self._cr.fetchone()
        if res_mediator:
            cash_mediator_ok = 0 if not res_mediator[0] else res_mediator[0]
            credit_mediator_ok = 0 if not res_mediator[1] else res_mediator[1]
        else:
            cash_mediator_ok = 0
            credit_mediator_ok = 0

        query_mediator_batal = """
            select sum(case when finco_id is null then 1 else 0 end) cash_mediator
            ,sum(case when finco_id is not null then 1 else 0 end) credit_mediator
            from dealer_sale_order dsoh
            LEFT JOIN dealer_sale_order_line dsol on dsol.dealer_sale_order_line_id=dsoh.id
            where state in ('cancelled') and dsoh.partner_komisi_id is not null 
            and branch_id=%s and user_id=%s and date(dsoh.cancelled_date + interval '7 hours') between '%s' and '%s'
            """ %(branch_id,user_id,self.start_date,self.end_date)

        self._cr.execute(query_mediator_batal)
        res_mediator_batal = self._cr.fetchone()
        if res_mediator_batal:
            cash_mediator_batal = 0 if not res_mediator_batal[0] else res_mediator_batal[0]
            credit_mediator_batal = 0 if not res_mediator_batal[1] else res_mediator_batal[1]
        else:
            cash_mediator_batal = 0
            credit_mediator_batal = 0
        cash_mediator = cash_mediator_ok - cash_mediator_batal
        credit_mediator = credit_mediator_ok - credit_mediator_batal

        total_unit_mediator = cash_mediator + credit_mediator
        persen_mediator = float(total_unit_mediator) / total_unit
        persen_credit = float(credit) / total_unit

        reward = self.env['teds.listing.table.insentif'].search([('name','=','SALESMAN PARTNER'),('type_insentif','=','reward'),('total','=',total_unit)]).insentif

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
        # self.jml_bawahan = jml_bawahan
        # self.produktivitas = produktivitas
        self.jml_insentif = total_insentif
        # self.job_name = job_name

        if total_insentif == 0:
            raise osv.except_osv(('Perhatian!'), ('Total penjualan %s, tidak mencukupi quota perhitungan')%(total_unit))
        
    @api.multi
    def koordinatorSalesman(self):

        branch_id = self.branch_id.id
        branch_cluster = self.branch_id.cluster
        user_id = self.name.resource_id.user_id.id
        job_name = self.name.job_id.name
        start_date = self.start_date[:-3]+"%"

        query = """
                select aa.user_id,sum(aa.cash)cash ,sum(aa.credit) credit from
                (select 
                dsoh.user_id,case when dsoh.finco_id is null then 1 else 0 end cash 
                ,case when dsoh.finco_id is not null then 1 else 0 end credit
                from dealer_sale_order_line dsol
                LEFT JOIN dealer_sale_order dsoh on dsoh.id=dsol.dealer_sale_order_line_id
                WHERE dsoh.branch_id=%s and (dsoh.user_id=%s or dsoh.sales_koordinator_id = %s) and dsoh.date_confirm between '%s' and '%s'
                and dsoh.state in('progress','done','cancelled'))aa
                group by aa.user_id
                """ %(branch_id,user_id,user_id,self.start_date,self.end_date)
         
        self._cr.execute(query)
        res_jml = self._cr.fetchall()
        cash_ok= 0
        credit_ok = 0

        if res_jml:
            for res in res_jml:
                cash_ok += res[1]
                credit_ok += res[2]
        else:
            cash_ok = 0
            credit_ok = 0

        query_cancel = """
                select aa.user_id,sum(aa.cash)cash ,sum(aa.credit) credit from
                (select 
                dsoh.user_id,case when dsoh.finco_id is null then 1 else 0 end cash 
                ,case when dsoh.finco_id is not null then 1 else 0 end credit
                from dealer_sale_order_line dsol
                LEFT JOIN dealer_sale_order dsoh on dsoh.id=dsol.dealer_sale_order_line_id
                WHERE dsoh.branch_id=%s and (dsoh.user_id=%s or dsoh.sales_koordinator_id = %s) 
                and date(dsoh.cancelled_date + interval '7 hours') between '%s' and '%s'
                and dsoh.state in('cancelled'))aa
                group by aa.user_id
                """ %(branch_id,user_id,user_id,self.start_date,self.end_date)

        self._cr.execute(query_cancel)
        res_cancel = self._cr.fetchall()
        cash_cancel = 0
        credit_cancel = 0
        if res_cancel:
            for cnc in res_cancel:
                cash_cancel += cnc[1]
                credit_cancel += cnc[2]
        else:
            cash_cancel = 0
            credit_cancel = 0

        cash = cash_ok - cash_cancel
        credit = credit_ok - credit_cancel

        total_unit = cash + credit

        if total_unit == 0:
            raise osv.except_osv(('Perhatian!'), ('Tidak ada penjualan dibulan tersebut'))

        rupiah_unit_cash = self.env['teds.listing.table.insentif'].search([('name','=','KOORDINATOR SALESMAN'),('type_insentif','=','cash_credit'),('total','=',total_unit)]).akumulasi
        rupiah_unit_credit = self.env['teds.listing.table.insentif'].search([('name','=','KOORDINATOR SALESMAN'),('type_insentif','=','unit_credit_ke'),('total','=',credit)]).akumulasi
        listing_reward = self.env['teds.listing.table.insentif'].search([('name','=','KOORDINATOR SALESMAN'),('type_insentif','=','reward'),('total','=',total_unit)]).insentif

        rupiah_unit_cash = 0 if not rupiah_unit_cash else rupiah_unit_cash
        rupiah_unit_credit = 0 if not rupiah_unit_credit else rupiah_unit_credit

        bawahan = """
            select count(DISTINCT(user_id)) jml
            from dealer_sale_order where state in ('progress', 'done','cancelled') and branch_id=%s and 
            date_confirm between '%s' and '%s'  and sales_koordinator_id = %s and user_id != %s       
            """%(branch_id,self.start_date,self.end_date,user_id,user_id)
        self._cr.execute(bawahan)
        jml_bawahan = self._cr.fetchone()[0] 

        produktivitas = 0
        if jml_bawahan > 0:
            produktivitas = round(total_unit / jml_bawahan) if total_unit else 0
        else:
            produktivitas = 0

        if jml_bawahan >=10:
            reward1 = listing_reward * 0.5
        else:
            reward1 = 0

        if produktivitas >= 8:
            reward2 = listing_reward * 0.5
        else:
            reward2 = 0

        rupiah_reward = reward1 + reward2

        rupiah_total_unit = rupiah_unit_cash + rupiah_unit_credit
        total_insentif = rupiah_unit_cash + rupiah_unit_credit + rupiah_reward


        self.unit_cash = cash
        self.rupiah_unit_cash = rupiah_unit_cash
        self.unit_credit = credit
        self.rupiah_unit_credit = rupiah_unit_credit
        self.total_unit = total_unit
        self.rupiah_total_unit = rupiah_total_unit
        # self.unit_ar_cash = ar_cash
        # self.rupiah_unit_ar_cash = rupiah_unit_ar_cash
        # self.unit_ar_credit = ar_credit
        # self.rupiah_unit_ar_credit = rupiah_unit_ar_credit 
        self.reward = total_unit
        self.rupiah_reward = rupiah_reward
        # self.mediator = mediator
        self.jml_bawahan = jml_bawahan
        self.produktivitas = produktivitas
        self.jml_insentif = total_insentif
        # self.job_name = job_name
        
        if total_unit == 0:
            raise osv.except_osv(('Perhatian!'), ('Tidak ada penjualan dibulan tersebut'))
        
        if total_insentif == 0:
            raise osv.except_osv(('Perhatian!'), ('Total penjualan %s, tidak mencukupi quota perhitungan')%(total_unit))

    @api.multi
    def soh(self):      
        branch_id = self.branch_id.id
        branch_cluster = self.branch_id.cluster
        user_id = self.name.resource_id.user_id.id
        job_name = self.name.job_id.name
        start_date = self.start_date[:-3]+"%"

        query = """
                select sum(aa.cash)cash ,sum(aa.credit) credit from
                (select 
                dsoh.user_id,case when dsoh.finco_id is null then 1 else 0 end cash 
                ,case when dsoh.finco_id is not null then 1 else 0 end credit
                from dealer_sale_order_line dsol
                LEFT JOIN dealer_sale_order dsoh on dsoh.id=dsol.dealer_sale_order_line_id
                WHERE dsoh.branch_id=%s and dsoh.date_confirm between '%s' and '%s'
                and dsoh.state in('progress','done','cancelled'))aa
                """ %(branch_id,self.start_date,self.end_date)
                
        self._cr.execute(query)
        res = self._cr.fetchone()

        if res:
            cash_ok = 0 if not res[0] else res[0]
            credit_ok = 0 if not res[1] else res[1]
        else:
            cash_ok = 0
            credit_ok = 0

        query_batal = """
                select sum(aa.cash)cash ,sum(aa.credit) credit from
                (select 
                dsoh.user_id,case when dsoh.finco_id is null then 1 else 0 end cash 
                ,case when dsoh.finco_id is not null then 1 else 0 end credit
                from dealer_sale_order_line dsol
                LEFT JOIN dealer_sale_order dsoh on dsoh.id=dsol.dealer_sale_order_line_id
                WHERE dsoh.branch_id=%s and date(dsoh.cancelled_date + interval '7 hours') between '%s' and '%s'
                and dsoh.state in('cancelled'))aa
                """ %(branch_id,self.start_date,self.end_date)

        self._cr.execute(query_batal)
        res_batal = self._cr.fetchone()
        if res_batal:
            cash_batal = 0 if not res_batal[0] else res_batal[0]
            credit_batal = 0 if not res_batal[1] else res_batal[1]
        else:
            cash_batal = 0
            credit_batal = 0

        cash = cash_ok - cash_batal
        credit = credit_ok - credit_batal
        total_unit = cash + credit 

        if total_unit == 0:
            raise osv.except_osv(('Perhatian!'), ('Tidak ada penjualan dibulan tersebut'))

        rupiah_unit_cash = self.env['teds.listing.table.insentif'].search([('name','=','SOH'),('cluster','=',branch_cluster),('type_insentif','=','cash_credit'),('total','=',total_unit)]).insentif
        rupiah_unit_credit = self.env['teds.listing.table.insentif'].search([('name','=','SOH'),('cluster','=',branch_cluster),('type_insentif','=','unit_credit_ke'),('total','=',credit)]).insentif
        rupiah_kelas_cabang = self.env['teds.listing.table.insentif'].search([('name','=','SOH'),('cluster','=',branch_cluster),('type_insentif','=','reward'),('total','=',total_unit)]).insentif
        total_insentif = rupiah_unit_cash + rupiah_unit_credit + rupiah_kelas_cabang

        self.unit_cash = cash
        self.rupiah_unit_cash = rupiah_unit_cash
        self.unit_credit = credit
        self.rupiah_unit_credit = rupiah_unit_credit
        self.total_unit = total_unit
        # self.rupiah_total_unit = rupiah_total_unit
        # self.unit_ar_cash = ar_cash
        # self.rupiah_unit_ar_cash = rupiah_unit_ar_cash
        # self.unit_ar_credit = ar_credit
        # self.rupiah_unit_ar_credit = rupiah_unit_ar_credit 
        # self.reward = total_unit
        # self.rupiah_reward = rupiah_reward
        # self.mediator = mediator
        # self.jml_bawahan = jml_bawahan
        # self.produktivitas = produktivitas
        self.jml_insentif = total_insentif
        # self.job_name = job_name

        if total_insentif == 0:
            raise osv.except_osv(('Perhatian!'), ('Total penjualan %s, tidak mencukupi quota perhitungan')%(total_unit))


    name = fields.Many2one('hr.employee')
    branch_id = fields.Many2one('wtc.branch')
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    job_name = fields.Char('Jabatan')
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

    _defaults = {
                'branch_id' : _get_default_branch,
                # 'start_date' : _get_default_date,
                # 'end_date' : _get_default_date,
              }


    @api.model
    def create(self,values,context=None):
        raise osv.except_osv(('Error!'), ('Tidak dapat di save, Hanya sebagai informasi'))

class wtc_branch(models.Model):
    _inherit = 'wtc.branch'
    cluster=fields.Selection([('A','A'),('B','B'),('C','C')],'Cluster Incentive Sales')