from openerp import models, fields, api
from datetime import datetime,date
from openerp.exceptions import except_orm, Warning, RedirectWarning
import calendar
import numpy as np
import logging
_logger = logging.getLogger(__name__)


class ReportWeeklyKonsolidate(models.Model):
    _name = "teds.report.weekly.konsolidate"

    def _get_bulan(self):
        return date.today().month
    
    def _get_tahun(self):
        return date.today().year

    @api.depends('end_date')
    def _compute_is_over_date(self):
        for me in self:
            if me.end_date < date.today().strftime('%Y-%m-%d'):
                me.is_over_date = True

    name = fields.Char('Name')
    bulan = fields.Selection([
        ('1','January'),
        ('2','February'),
        ('3','March'),
        ('4','April'),
        ('5','May'),
        ('6','June'),
        ('7','July'),
        ('8','August'),
        ('9','September'),
        ('10','October'),
        ('11','November'),
        ('12','December')], 'Bulan', required=True)
    tahun = fields.Char('Tahun', default=_get_tahun,required=True)
    weekly = fields.Selection([
        ('0','Week 1'),
        ('1','Week 2'),
        ('2','Week 3'),
        ('3','Week 4'),
        ('4','Week 5'),
    ])
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    area_id = fields.Many2one('teds.report.weekly.master.area','Area',ondelete='cascade')
    dealer_ids = fields.One2many('teds.report.weekly.konsolidate.dealer','konsolidate_id')
    state = fields.Selection([('draft','Draft'),('confirmed','Confirmed')],default='draft')
    is_over_date = fields.Boolean('Is Over Date ?',compute='_compute_is_over_date')

    _sql_constraints = [('unique_bulan_tahun_weekly,area', 'unique(bulan,tahun,weekly,area_id)', 'Weekly bulan tidak boleh duplikat !')]

    
    @api.model
    def create(self,vals):
        bulan = int(vals['bulan'])
        tahun = int(vals['tahun'])
        nama_bln = calendar.month_name[bulan]
        weekly = ""
        if vals.get('weekly'):
            if vals['weekly'] == '0':
                weekly = 'Week 1'
            if vals['weekly'] == '1':
                weekly = 'Week 2'
            if vals['weekly'] == '2':
                weekly = 'Week 3'
            if vals['weekly'] == '3':
                weekly = 'Week 4'
            if vals['weekly'] == '4':
                weekly = 'Week 5'

        vals['name'] = "%s - %s %s"%(weekly,nama_bln,tahun)
        return super(ReportWeeklyKonsolidate,self).create(vals)

    @api.multi
    def unlink(self):
        for me in self :
            raise Warning('Data tidak bisa dihapus !')
        return super(ReportWeeklyKonsolidate, self).unlink()

    def action_konsolidate_weekly_server(self):
        tree_id = self.env.ref('teds_report_weekly.view_teds_report_weekly_konsolidate_tree').id
        form_id = self.env.ref('teds_report_weekly.view_teds_report_weekly_konsolidate_form').id
        
        domain = []
        cek_group = self.env['res.users'].has_group('teds_report_weekly.group_teds_konsolidate_weekly_allow')
        if not cek_group:
            query = """
                SELECT id  
                FROM teds_report_weekly_konsolidate
                WHERE area_id in (
                    SELECT DISTINCT(area_id) FROM teds_area_user_report_weekly WHERE user_id = %d
                )
            """ %(self._uid)
            self._cr.execute (query)
            ress =  self._cr.fetchall()  
            tahun = date.today().year
            month = date.today().month
            day = date.today().day
            week = self.get_week_of_month(tahun,month,day)   
            end_date = str(self.get_weekly(month,tahun,week).get('end_date'))
            domain = [
                ('id','in',ress),
                ('start_date','<=',date.today().strftime('%Y-%m-%d')),
                ('end_date','<=',end_date)]

        return {
            'type': 'ir.actions.act_window',
            'name': 'Konsolidate Weekly',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'teds.report.weekly.konsolidate',
            'domain': domain,
            'context':{'search_default_state_draft':1},
            'views': [(tree_id, 'tree'), (form_id, 'form')],
        }

    @api.onchange('area_id')
    def ocnhange_area(self):
        self.dealer_ids = False
    
    @api.onchange('bulan','tahun','weekly')
    def onchange_start_end_date(self):
        if self.bulan and self.tahun and self.weekly:
            periode = self.get_weekly(self.bulan,self.tahun,self.weekly)
            self.start_date = periode.get('start_date')
            self.end_date = periode.get('end_date')

    @api.onchange('area_id')
    def onchange_area(self):
        self.dealer_ids = False
        ids = []
        if self.area_id:
            for dealer in self.area_id.dealer_ids:
                ids.append([0,False,{
                    'type':dealer.type,
                    'branch_id':dealer.branch_id.id,
                    'name':dealer.name,
                }])
        self.dealer_ids = ids

    def get_week_of_month(self,year, month, day):
        x = np.array(calendar.monthcalendar(year, month))
        week_of_month = np.where(x==day)[0][0] - 1
        return(week_of_month)

    def get_weekly(self,bulan,tahun,weekly):
        ids = []
        cal= calendar.Calendar()
        datas = cal.monthdatescalendar(int(tahun),int(bulan))
        if len(datas) == 6:
            datas = datas[int(weekly)+1]
        else:
            datas = datas[int(weekly)]
        for data in datas:
            if int(data.month) == int(bulan):
                ids.append(data)
        max_date = max(ids)
        start_date = max_date.replace(day=1).strftime("%Y-%m-%d")
        return {'start_date':start_date,'end_date':max_date}

    @api.multi
    def action_generate_weekly(self):
        areas = self.env['teds.report.weekly.master.area'].search([])
        if areas:
            bulan = self._get_bulan()
            tahun = self._get_tahun()
            for area in areas:
                ids = []
                for dealer in area.dealer_ids:
                    ids.append([0,False,{
                        'type':dealer.type,
                        'branch_id':dealer.branch_id.id,
                        'name':dealer.name,
                    }])
                weekly = ['0','1','2','3','4']
                for week in weekly:
                    periode = self.get_weekly(bulan,tahun,week)
                    if periode:
                        vals = {
                            'bulan':str(bulan),
                            'tahun':str(tahun),
                            'weekly':week,
                            'start_date':periode.get('start_date'),
                            'end_date':periode.get('end_date'),
                            'area_id':area.id,
                            'dealer_ids':ids,
                        }
                        self.create(vals)
                    else:
                        _logger.warning("Report Weekly Periode Start End Date not found !")

        else:
            _logger.warning("Report Weekly Area not found !")


    @api.multi
    def action_unit_sales_cabang(self):
        tahun = date.today().year
        month = date.today().month
        day = date.today().day
        week = self.get_week_of_month(tahun,month,day)   
        end_date = str(self.get_weekly(month,tahun,week).get('end_date'))

        query = """
            SELECT sum(dsol.product_qty) as quantity
            , dso.branch_id
            , konsolidate.id as konsolidate_id
            FROM dealer_sale_order dso
            INNER JOIN dealer_sale_order_line dsol ON dsol.dealer_sale_order_line_id = dso.id
            INNER JOIN (
            SELECT rwkd.branch_id
            , rwk.start_date
            , rwk.end_date
            , rwkd.id
            FROM teds_report_weekly_konsolidate rwk
            INNER JOIN teds_report_weekly_konsolidate_dealer rwkd ON rwkd.konsolidate_id = rwk.id
            WHERE rwk.state = 'draft'
            AND rwk.end_date <= '%s'
            AND rwkd.type = 'Cabang'
            ) konsolidate ON konsolidate.branch_id = dso.branch_id
            WHERE dso.state in ('progress','done')
            AND dso.date_order BETWEEN konsolidate.start_date and konsolidate.end_date
            GROUP BY dso.branch_id,konsolidate.id
        """%(end_date)
        self.env.cr.execute(query)
        ress = self.env.cr.dictfetchall() 
        for res in ress:
            konsolidate_id = res.get('konsolidate_id')
            total = res.get('quantity')
            update = """
                UPDATE teds_report_weekly_konsolidate_dealer
                SET total = %s
                WHERE id = %d
            """ %(total,konsolidate_id)
            self.env.cr.execute(update)
    
    @api.multi
    def action_set_to_draft(self):
        self.state = 'draft'

    @api.multi
    def action_confirm_weekly(self):
        query = """
            SELECT id
            FROM teds_report_weekly_konsolidate
            WHERE state = 'draft'
            AND end_date < now()::date
        """
        self.env.cr.execute(query)
        ress = self.env.cr.fetchall()
        if ress:
            self.action_unit_sales_cabang()
            ids = str(tuple([res[0] for res in ress])).replace(',)', ')')
            update = """
                UPDATE teds_report_weekly_konsolidate
                SET state = 'confirmed'
                WHERE id in %s
            """ %(ids)
            self.env.cr.execute(update)
    
    @api.multi
    def action_confirm(self):
        self.action_unit_sales_cabang()
        self.write({'state':'confirmed'})
     
    def _get_data_dealer(self,month,tahun,weekly,cabang,area_id):
        data = """
            SELECT d.id
            FROM teds_report_weekly_konsolidate k
            INNER JOIN teds_report_weekly_konsolidate_dealer d ON d.konsolidate_id = k.id
            WHERE k.bulan = '%s'
            AND k.tahun = '%s'
            AND k.weekly = '%s'
            AND d.name = '%s'
            AND k.area_id = %d
        """ %(month,tahun,weekly,cabang,area_id)
        self.env.cr.execute(data)
        res = self.env.cr.fetchone() 
        if res:
            return res[0]
        return res
        

class ReportWeeklyKonsolidateDealer(models.Model):
    _name = "teds.report.weekly.konsolidate.dealer"

    @api.depends('total')
    def _compute_ranking(self):
        for me in self:
            ress = self.search([('konsolidate_id','=',me.konsolidate_id.id)])
            data = {}
            for res in ress:
                data[res.name] = res.total
            result = {key: rank for rank, key in enumerate(sorted(data, key=data.get, reverse=True), 1)}
            me.ranking = result.get(me.name)

    
    @api.depends('konsolidate_id')
    def _compute_lm(self):
        for me in self:
            total = 0
            ranking = 0
            if me.konsolidate_id:
                month = int(me.konsolidate_id.bulan)-1
                tahun = int(me.konsolidate_id.tahun)
                if int(me.konsolidate_id.bulan) == 1:
                    month = 12
                    tahun = tahun-1
                weekly = me.konsolidate_id.weekly
                cabang = me.name
                area_id = me.konsolidate_id.area_id.id
                res = self.env['teds.report.weekly.konsolidate']._get_data_dealer(month,tahun,weekly,cabang,area_id)
                if res:
                    obj = self.browse(res)
                    total = obj.total
                    ranking = obj.ranking
        
            me.total_lm = total
            me.ranking_lm = ranking
        


    konsolidate_id = fields.Many2one('teds.report.weekly.konsolidate','Konsolidate',ondelete='cascade')
    type = fields.Selection([('Cabang','Cabang'),('Non Cabang','Non Cabang')])
    branch_id = fields.Many2one('wtc.branch','Branch',index=True)
    name = fields.Char('Name',index=True)
    total = fields.Float('Unit Sales')
    ranking = fields.Integer('Ranking',compute='_compute_ranking',readonly=True)
    ranking_lm = fields.Integer('Ranking Last Month',compute='_compute_lm',readonly=True)
    total_lm = fields.Float('Total Last Month',compute='_compute_lm',readonly=True)


