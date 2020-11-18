from openerp import models, fields, api, _
from datetime import datetime, timedelta
import os

class wtc_interface_fico(models.Model):
    _name = "wtc.interface.fico"
    _description = "FICO Interface"

    name_jit = fields.Char('File Name JIT', lenght=100)
    name_rec = fields.Char('File Name REC', lenght=100)
    date = fields.Date(string="Date",required=True)
    file_jit = fields.Text('File JIT')
    file_rec = fields.Text('File REC')
    tgl_awal = fields.Date(string="Date START",required=True)
    tgl_akhir = fields.Date(string="Date END",required=True)

    @api.multi
    def export(self):
        query = """
            SELECT max(date)
            FROM wtc_interface_fico
        """
        self._cr.execute(query)
        result = self._cr.fetchall()

        date_max = datetime.strptime('2016-02-29', "%Y-%m-%d").date()
        if len(result[0]) > 0:
            res = result[0]
            date_max = datetime.strptime(res[0], "%Y-%m-%d").date()+timedelta(days = 1)
        date_curr = self.env['wtc.branch'].get_default_date().date()
        total_days = (date_curr - date_max).days

        for day_number in range(total_days):
            date = (date_max + timedelta(days = day_number))
            file_jit = self.export_jit(date)
            file_rec = self.export_rec(date)
            path = '/opt/odoo/TDM/fico_out/'
            name_jit = "JIT-" + datetime.strftime(date, "%Y%m%d") + ".txt"
            name_rec = "JIT-REC-" + datetime.strftime(date, "%Y%m%d") + ".txt"

            self.create({
                'date': date,
                'name_jit': path+name_jit,
                'name_rec': path+name_rec,
                'file_jit': file_jit,
                'file_rec': file_rec,
                })

            jit = open(path+name_jit, 'w+b')
            jit.write(file_jit)
            jit.close()

            rec = open(path+name_rec, 'w+b')
            rec.write(file_rec)
            rec.close()

    @api.model
    def export_jit(self, date, move_ids=[]):
        if isinstance(move_ids, (long, int)) :
            move_ids = [move_ids]

        where_clause_am = ''
        where_clause_aml = ''

        if len(move_ids) > 0 :
            where_clause_am = "where am.id in %s " % str(tuple(move_ids)).replace(',)', ')')
            where_clause_aml = "where aml.move_id in %s " % str(tuple(move_ids)).replace(',)', ')')
        elif date :
            where_clause_am = "where am.date = '%s' " % date
            where_clause_aml = "where aml.date = '%s' " % date

        query = """
            SELECT content
            FROM (
            (
            select am.id as id
            , 0 as seq
            , 'HS|15||' || 
            am.id || '|' || 
            fy.code || '|' || 
            right(ap.code, 2) || '|' || 
            to_char(am.date, 'MM/DD/YY') || '|' || 
            coalesce(aj.code,'') || '|JIT|' || 
            regexp_replace(coalesce(am.name,''), '[\n\r|]+', ' ', 'g') || '|' || 
            regexp_replace(coalesce(am.ref, coalesce(am.name,'')), '[\n\r|]+', ' ', 'g') || '||||||||||||' as content
            from account_move am
            inner join account_period ap on am.period_id = ap.id
            inner join account_fiscalyear fy on ap.fiscalyear_id = fy.id
            inner join account_journal aj on am.journal_id = aj.id

            %s

            order by am.id
            )
            UNION
            (
            select id
            , seq
            , prefix || row_number() over (partition by id) || suffix as content
            from 
            (select 
            aml.move_id as id
            , aml.id as seq
            , 'IS' || '|' ||
            '15' || '|' ||
            profit_centre || '|' || 
            aml.move_id || '|' as prefix
            , '|' || fy.code  || '|' || 
            right(ap.code, 2) || '|' || 
            aa.code || '|' || 
            case when aml.credit > 0 then 'C' else 'D' end || '|' || 
            regexp_replace(coalesce(aml.name,''), '[\n\r|]+', ' ', 'g') || '|' || 
            (coalesce(aml.debit,0) + coalesce(aml.credit,0))::varchar(255) || '|' || 
            '1' || '|' || '' || '|' || 
            coalesce(ai.number, '') || '|' || 
            coalesce(to_char(ai.date_invoice, 'MM/DD/YY'),'') || '|' || 
            case when aa.type in ('payable', 'receivable') and aml.date is not null then (coalesce(aml.date_maturity, aml.date) - aml.date)::varchar(255) else '' end || '|' || 
            case when aa.type = 'payable' then coalesce(rp.default_code || '-' || rp.name, '') else '' end || '|' || 
            case when aa.type = 'receivable' then coalesce(rp.default_code || '-' || rp.name, '') else '' end || '|' || 
            aml.id || '|' || 
            case when aa.type = 'liquidity' then coalesce(aj.name,'') else '' end || '|' || 
            '' || '|' || 
            '' || '|' as suffix

            from account_move_line aml
            inner join wtc_branch b on aml.branch_id = b.id
            inner join account_period ap on aml.period_id = ap.id
            inner join account_fiscalyear fy on ap.fiscalyear_id = fy.id
            inner join account_account aa on aml.account_id = aa.id
            inner join account_journal aj on aml.journal_id = aj.id
            left join res_partner rp on aml.partner_id = rp.id
            left join account_invoice ai on aml.move_id = ai.move_id and aa.type in ('receivable', 'payable')

            %s

            order by aml.move_id, aml.id
            ) a
            )
            ) b
            ORDER BY id, seq
        """ % (where_clause_am, where_clause_aml)
        self._cr.execute(query)
        ress = self._cr.fetchall()
        content = ""
        for res in ress :
#            content += res[0] #+ '\n\r'
             c=str(res[0].encode('ascii','ignore').decode('ascii')) if res[0] != None else ''
#            c.replace("\r","").replace("\n","")
             content += c+ '\r\n'
        return content

    @api.model
    def export_rec(self, date):
        query = """
            select to_char(amr.create_date, 'MM/DD/YY') || '|' ||
            coalesce(amr.name,'') || '|' ||
            aml.id as content
            from account_move_reconcile amr
            inner join account_move_line aml on amr.id = aml.reconcile_id or amr.id = aml.reconcile_partial_id
            where amr.create_date = '%s'
            order by amr.id, aml.id
        """ % (date)

        self._cr.execute(query)
        ress = self._cr.fetchall()
        content = ""
        for res in ress :
	    c=str(res[0].encode('ascii','ignore').decode('ascii')) if res[0] != None else ''
#           c.replace("\r","").replace("\n","")
#            content += res[0] #+ '\n\r'
            content += c + '\r\n'

        return content
    
    def wizard_cek_so_done(self,cr,uid,ids,context=None):  
        obj_claim_kpb = self.browse(cr,uid,ids)
        obj_ir_view = self.pool.get("ir.ui.view")
        obj_ir_view_search= obj_ir_view.search(cr,uid,[("name", "=", 'dealer.sale.order.proses.done'), ("model", "=", 'wtc.interface.fico'),])
        obj_ir_view_browse = obj_ir_view.browse(cr,uid,obj_ir_view_search)
        return {
            'name': 'Print Pelunasan Leasing',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.interface.fico',
            'type': 'ir.actions.act_window',
            'view_id' : obj_ir_view_browse.id,
            'nodestroy': True,
            'target': 'new',
            'res_id': obj_claim_kpb.id
            } 
        
    @api.multi
    def dso_cek_done(self):
        self.env['dealer.sale.order'].set_done_for_dsp(self.tgl_awal,self.tgl_akhir)
