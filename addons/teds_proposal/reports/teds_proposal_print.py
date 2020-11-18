import pytz
from datetime import datetime
from openerp import models, fields, api

class PrintProposal(models.AbstractModel):
    _name = 'report.teds_proposal.print_proposal_pdf'

    def _get_amounts(self):
        proposal_id = self.env.context.get('active_id', 0)
        get_amount_query = """
            SELECT
                tp.id AS proposal_id,
                tpl.amount_transfer,
                tpl.amount_cash,
                tpl.amount_total,
                tpl.amount_paid,
                COALESCE(tps.amount_sponsor,0) AS amount_sponsor
            FROM teds_proposal tp
            JOIN (
                SELECT
                    proposal_id,
                    COALESCE(SUM(CASE WHEN jenis_pembayaran = 'T' THEN amount_total END),0) AS amount_transfer,
                    COALESCE(SUM(CASE WHEN jenis_pembayaran = 'C' THEN amount_total END),0) AS amount_cash,
                    COALESCE(SUM(amount_total),0) AS amount_total,
                    COALESCE(SUM(amount_paid),0) AS amount_paid
                FROM teds_proposal_line
                GROUP BY proposal_id
            ) tpl ON tp.id = tpl.proposal_id
            LEFT JOIN (
                SELECT 
                    proposal_id,
                    SUM(amount) as amount_sponsor
                FROM teds_proposal_sponsor
                GROUP BY proposal_id
            ) tps ON tps.proposal_id = tp.id
            WHERE tp.id = %d
        """ % (proposal_id)
        self._cr.execute(get_amount_query)
        amount_ress = self._cr.dictfetchone()
        return amount_ress

    def _get_approvers(self):
        proposal_id = self.env.context.get('active_id', 0)
        proposal_model_id = self.env['ir.model'].suspend_security().search([('model','=','teds.proposal')],limit=1).id
        get_approver_query = """
            SELECT DISTINCT ON (al.limit)
                al.limit,
                p.name AS approved_by,
                TO_CHAR(al.tanggal, 'YYYY-MM-DD HH24:MI:SS') AS approved_on,
                'APPROVED BY SYSTEM' AS approved_st
            FROM wtc_approval_line al
            JOIN res_users u ON al.pelaksana_id = u.id
            JOIN res_partner p ON u.partner_id = p.id
            WHERE al.form_id = %d AND al.transaction_id = %d
            AND al.limit IN (2000000,5000000,10000000)
            AND al.sts = '2'
            ORDER BY al.limit
        """ % (proposal_model_id, proposal_id)
        self._cr.execute(get_approver_query)
        approver_ress = self._cr.dictfetchall()
        approver = [['','',''],['','',''],['','','']]
        idx = 0
        tz = pytz.timezone(self.env.context.get('tz')) if self.env.context.get('tz') else pytz.utc
        for x in approver_ress:
            approver[idx][0] = x['approved_by']
            approver[idx][1] = pytz.utc.localize(datetime.strptime(x['approved_on'], '%Y-%m-%d %H:%M:%S')).astimezone(tz).strftime("%d-%m-%Y")
            approver[idx][2] = x['approved_st']
            idx += 1
        return approver

    @api.model
    def render_html(self, docids, data=None):
        docs = self.env[self.env.context.get('active_model')].browse(self.env.context.get('active_ids', []))
        docargs = {
            'docs': docs, # objek teds.proposal(current_id)
            'data': data['form'], # data lengkap pada form aktif
            'user': data['user'], # nama user
            'amounts': self._get_amounts,
            'approvers': self._get_approvers
        }
        return self.env['report'].render('teds_proposal.print_proposal_pdf', docargs)